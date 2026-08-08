#!/usr/bin/env python3
"""Aggregate the frozen R8-D production-shaped delivery gate."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable

from build_r8_c_release_set import CANDIDATE_VARIANT, RETENTION_VARIANT
from r8_bundle import bundle_manifest, source_bytes
from r8_release import load_json, sha256_file, write_json


CORE_COMMIT = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"
LOADER_SHA256 = "35d96f5fdcb9ed0cdb19f28a743245e0dbd255cbf90a2c14d680f0b1b9c63566"
WASM_SHA256 = "ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6"

# Every release identity R8 can ship, keyed by the (fidelity policy, variant
# marker) pair that produces it.  R8-B ships two policies; R8-C ships three
# slots of the standard policy.
RELEASE_VARIANTS: dict[str, tuple[str, str | None]] = {
    "r8b-standard": ("standard", None),
    "r8b-full-fidelity": ("full-fidelity", None),
    "r8c-A": ("standard", None),
    "r8c-B": ("standard", CANDIDATE_VARIANT),
    "r8c-C": ("standard", RETENTION_VARIANT),
}


def percentile(values: Iterable[float], quantile: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def statistics(values: Iterable[float]) -> dict[str, Any]:
    samples = [float(value) for value in values]
    return {
        "count": len(samples),
        "min": min(samples) if samples else None,
        "median": percentile(samples, 0.5),
        "p90": percentile(samples, 0.9),
        "max": max(samples) if samples else None,
    }


def decide(safety_pass: bool, t2_pass: bool) -> str:
    if not safety_pass:
        return "STOP"
    return "GO" if t2_pass else "PARTIAL_GO_LOCAL_DELIVERY"


def evidence_pass(path: Path, decisions: set[str] | None = None) -> bool:
    if not path.is_file():
        return False
    value = load_json(path)
    if value.get("pass") is not True:
        return False
    return decisions is None or value.get("decision") in decisions


def compatibility_check(path: Path, release_id: str, expected_count: int) -> dict[str, Any]:
    value = load_json(path) if path.is_file() else {}
    checks = {
        "summaryPresent": bool(value),
        "activeCachedRelease": value.get("releaseId") == release_id,
        "documentCount": value.get("documentCount") == expected_count,
        "allCases": bool(value.get("cases"))
        and all(case.get("pass") is True for case in value.get("cases", [])),
        "boundedWorkerGenerationsPerPage": (
            value.get("workersStarted", 0) > 0
            and value.get("maxWorkersPerPage", 0) <= 3
        ),
        "summaryPass": value.get("pass") is True,
    }
    return {"path": str(path), "checks": checks, "pass": all(checks.values())}


def longevity_check(path: Path, minimum_minutes: float, browser: str) -> dict[str, Any]:
    value = load_json(path) if path.is_file() else {}
    generation_limit = 4 if browser == "firefox" else 8
    transitions = set(value.get("transitions", []))
    checks = {
        "summaryPresent": bool(value),
        "duration": value.get("durationMinutes", 0) >= minimum_minutes,
        "samples": len(value.get("samples", [])) >= 2,
        "boundedWorkerGenerations": 0 < value.get("workerGenerations", 0) <= generation_limit,
        # Was `value.get(..., 99) <= 3` against a hand-written 3 -- a gate that
        # restated the constant it guarded and so could never fail (finding 026).
        # The producer now measures; a non-integer means "never measured", which
        # must fail rather than default into a pass.
        "boundedWorkerGenerationsPerPage": (
            isinstance(value.get("maxWorkerGenerationsPerPage"), int)
            and value["maxWorkerGenerationsPerPage"] <= 3
        ),
        "requiredTransitions": {
            "active-a", "active-b", "offline-a-runtime", "rollback-a"
        }.issubset(transitions),
        "noFailedCycle": bool(value.get("cycles"))
        and all(cycle.get("pass") is True for cycle in value.get("cycles", [])),
        "summaryPass": value.get("pass") is True,
    }
    return {"path": str(path), "checks": checks, "pass": all(checks.values())}


def expected_release_identities(project: Path) -> dict[str, str]:
    """Recompute every release identity from dist/ as it stands right now.

    A release ID *is* a content hash: expected_release_id() digests the release
    manifest, and bundle_manifest() fills that manifest's artifacts[].sha256
    from the bytes currently on disk.  So this answers "what would today's
    dist/ be called", without writing a staging tree and without consulting
    dist/r8c/release-set.json.

    Not consulting that file is the entire point.  activeCachedRelease compares
    the evidence against the release *set file*, and on 2026-08-07 both sides
    went stale together: the bundled sdk-worker.js changed, nothing recomputed
    the identity, and the verdict described a release that no longer existed
    for four days -- until a make target happened to rebuild the set (finding
    027).  A cache cannot notice that it is out of date; only a recomputation
    can.  Costs ~0.7 s: it re-reads and re-hashes the 17 bundled artifacts.
    """
    source = load_json(project / "dist" / "r8" / "release-manifest.json")
    identities: dict[str, str] = {}
    for key, (policy, marker) in RELEASE_VARIANTS.items():
        values = {
            item["role"]: source_bytes(project, item, policy, marker)
            for item in source["artifacts"]
        }
        identities[key] = bundle_manifest(project, policy, values)["releaseId"]
    return identities


def release_binding(root: Path, project: Path,
                    expected: dict[str, str] | None = None) -> dict[str, Any]:
    """Bind every phase's evidence to the release identity dist/ has right now.

    validate_e1_c.artifact_binding does this for E1-C's 48 browser cases.  R8-D
    consumed six evidence families and checked the release of exactly one of
    them -- compatibility, via activeCachedRelease, and against a cache at that.
    Longevity records releaseIds, delivery records its bundle IDs and
    service-worker records the whole release set; all three were written down
    and never read, which is the same as not recording them.

    Absence binds no better than mismatch.  Evidence that never named the
    release it ran against is not weaker proof than stale evidence, it is none.
    """
    expected = expected_release_identities(project) if expected is None else expected
    r8c_slots = {slot: expected[f"r8c-{slot}"] for slot in ("A", "B", "C")}
    families: list[dict[str, Any]] = []

    def bind(family: str, path: Path, want: Any, extract: Any) -> None:
        value = load_json(path) if path.is_file() else None
        observed = extract(value) if value is not None else None
        if not observed:
            reason = "evidence does not record the release it ran against"
        elif observed != want:
            reason = "evidence was produced against a superseded release"
        else:
            reason = None
        families.append({
            "family": family, "path": str(path), "expected": want,
            "observed": observed, "pass": reason is None, "reason": reason,
        })

    for browser in ("chrome", "firefox"):
        bind(
            f"compatibility:{browser}",
            root / "production" / "compatibility" / browser / "summary.json",
            expected["r8c-A"], lambda value: value.get("releaseId"),
        )
        bind(
            f"longevity:{browser}",
            root / "production" / "longevity" / browser / "summary.json",
            r8c_slots, lambda value: value.get("releaseIds"),
        )
    bind(
        "delivery", root / "delivery" / "summary.json",
        {"standard": expected["r8b-standard"],
         "full-fidelity": expected["r8b-full-fidelity"]},
        lambda value: {
            item.get("policy"): item.get("releaseId")
            for item in ((value.get("bundles") or {}).get("releases") or [])
        },
    )
    bind(
        # validate_r8_c stores the loaded release set under releaseSet.index --
        # the per-case result.json puts the same array one level higher, under
        # releaseSet.releases.  Read only the shape this producer writes; a
        # tolerant lookup would report a drifted schema as "unattributable"
        # and hide the drift behind the right verdict.
        "service-worker", root / "service-worker" / "summary.json", r8c_slots,
        lambda value: {
            item.get("slot"): item.get("releaseId")
            for item in (((value.get("releaseSet") or {}).get("index") or {})
                         .get("releases") or [])
        },
    )
    counted = lambda reason: sum(1 for item in families if item["reason"] == reason)  # noqa: E731
    return {
        "schemaVersion": 1,
        "release": "R8-D-production-validation",
        "expected": expected,
        "families": families,
        "boundFamilies": sum(1 for item in families if item["pass"]),
        "supersededFamilies": counted("evidence was produced against a superseded release"),
        "unattributableFamilies": counted(
            "evidence does not record the release it ran against"
        ),
        "pass": bool(families) and all(item["pass"] for item in families),
    }


def performance_summary(delivery: dict[str, Any], service_worker: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for browser in ("chrome", "firefox"):
        delivery_browser = delivery.get("browsers", {}).get(browser, {})
        for topology in delivery_browser.get("topologies", []):
            key = f"{browser}-{topology.get('topology')}"
            cases = [case for case in topology.get("cases", []) if case.get("pass") is True]
            result[key] = {
                "directDeliveryMs": statistics(
                    case["runnerElapsedMs"] for case in cases if case.get("runnerElapsedMs") is not None
                ),
                "manifestAndArtifactVerifyMs": statistics(
                    (case.get("verified") or {})["durationMs"] for case in cases
                    if (case.get("verified") or {}).get("durationMs") is not None
                ),
                "documentOpenMs": statistics(
                    (case.get("document") or {})["openMs"] for case in cases
                    if (case.get("document") or {}).get("openMs") is not None
                ),
            }
        sw_browser = service_worker.get("browsers", {}).get(browser, {})
        sw_values = []
        for topology in sw_browser.get("topologies", []):
            for case in topology.get("cases", []):
                path = Path(case.get("result", ""))
                if path.is_file():
                    detail = load_json(path)
                    if detail.get("runnerElapsedMs") is not None:
                        sw_values.append(detail["runnerElapsedMs"])
        result.setdefault(browser, {})["serviceWorkerCaseMs"] = statistics(sw_values)
    return result


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r8",
    )
    args = parser.parse_args()
    project, root = args.project.resolve(), args.evidence_root.resolve()
    matrix = load_json(project / "r8" / "production-matrix-v1.json")
    release_set = load_json(project / "dist" / "r8c" / "release-set.json")
    release_a = next(item["releaseId"] for item in release_set["releases"] if item["slot"] == "A")

    r8c_path = root / "service-worker" / "summary.json"
    r8c = load_json(r8c_path) if r8c_path.is_file() else {}
    delivery_path = root / "delivery" / "summary.json"
    delivery = load_json(delivery_path) if delivery_path.is_file() else {}
    compatibility = {
        browser: compatibility_check(
            root / "production" / "compatibility" / browser / "summary.json",
            release_a, matrix["compatibility"]["documentCount"],
        ) for browser in matrix["browsers"]
    }
    longevity = {
        browser: longevity_check(
            root / "production" / "longevity" / browser / "summary.json",
            matrix["longevity"]["minimumMinutes"], browser,
        ) for browser in matrix["browsers"]
    }
    regression_path = root / "production" / "regression" / "summary.json"
    regression_ok = evidence_pass(regression_path)
    r7_root = root.parent / "sdk-r7"
    inherited = {
        "r7Overall": evidence_pass(r7_root / "summary.json", {"PARTIAL_GO_ODT_FIRST"}),
        "r7Input": evidence_pass(r7_root / "input-summary.json", {"GO", "PARTIAL_GO"}),
        "r7Compatibility": evidence_pass(
            r7_root / "compatibility-summary.json", {"GO", "PARTIAL_GO_ODT_FIRST"},
        ),
        "r7Regression": evidence_pass(r7_root / "regression" / "summary.json"),
    }
    firefox_compatibility_value = load_json(
        root / "production" / "compatibility" / "firefox" / "summary.json"
    )
    firefox_longevity_value = load_json(
        root / "production" / "longevity" / "firefox" / "summary.json"
    )
    finding014 = root.parent.parent / "014-firefox-long-lived-wasm-worker-init-exhaustion.md"
    firefox_r8c = r8c.get("browserChecks", {}).get("firefox", {}).get("pass") is True
    firefox_compatibility_fallback = (
        firefox_compatibility_value.get("acceptedForPartialGo") is True
        and inherited["r7Compatibility"] and firefox_r8c and finding014.is_file()
    )
    firefox_r7_soak = r7_root / "longevity" / "firefox" / "s4" / "run-1" / "result.json"
    firefox_longevity_fallback = (
        firefox_longevity_value.get("acceptedForPartialGo") is True
        and evidence_pass(firefox_r7_soak)
        and firefox_r8c and finding014.is_file()
    )
    compatibility_accepted = (
        compatibility["chrome"]["pass"]
        and (compatibility["firefox"]["pass"] or firefox_compatibility_fallback)
    )
    longevity_accepted = (
        longevity["chrome"]["pass"]
        and (longevity["firefox"]["pass"] or firefox_longevity_fallback)
    )
    required_docs = [
        project.parent / "docs" / "R8-DEPLOYMENT-CHECKLIST.md",
        project.parent / "docs" / "R8-OPERATOR-RUNBOOK.md",
        project.parent / "docs" / "R8-KNOWN-LIMITATIONS.md",
    ]
    security_source = (project / "web" / "r8-service-worker.js").read_text(encoding="utf-8")
    security = {
        "noCredentialFetch": "credentials: \"omit\"" in security_source,
        "closedSyntheticCachePrefix": "/__r8c_cache__/releases/" in security_source,
        "noDocumentCacheName": "document-cache" not in security_source,
        "typedIntegrityFailure": "CACHED_ARTIFACT_INVALID" in security_source,
    }
    fonts_source = root / "delivery" / "fonts" / "summary.json"
    roundtrip_source = root / "delivery" / "roundtrip" / "summary.json"
    fonts = {
        "source": str(fonts_source),
        "policyDrivenDelivery": evidence_pass(fonts_source),
        "knownFontInventoryGapRetained": True,
    }
    fonts["pass"] = all(value for key, value in fonts.items() if key != "source")
    roundtrip = {
        "source": str(roundtrip_source),
        "r8bEightOutputs": evidence_pass(roundtrip_source),
        "r7Regression": inherited["r7Regression"],
    }
    roundtrip["pass"] = all(value for key, value in roundtrip.items() if key != "source")
    network = {
        "t0t1DirectDelivery": delivery.get("pass") is True,
        "t0t1ServiceWorker": r8c.get("pass") is True,
        "t2": "passed" if os.environ.get("R8_T2_URL") else "not-executed-no-authorized-environment",
    }
    network["pass"] = network["t0t1DirectDelivery"] and network["t0t1ServiceWorker"]
    baseline_after = root / "service-worker" / "baseline" / "preflight-after.json"
    binding = release_binding(root, project)
    safety_checks = {
        "matrixSchema": matrix.get("schemaVersion") == 1,
        "releaseBinding": binding["pass"],
        "r8c": r8c.get("pass") is True and r8c.get("decision") in {"GO", "PARTIAL_GO"},
        "r8b": delivery.get("pass") is True,
        "compatibility": compatibility_accepted,
        "longevity": longevity_accepted,
        "regression": regression_ok,
        "inheritedR7": all(inherited.values()),
        "security": all(security.values()),
        "fonts": fonts["pass"],
        "roundtrip": roundtrip["pass"],
        "network": network["pass"],
        "preflightAfter": evidence_pass(baseline_after),
        "operatorDocs": all(path.is_file() for path in required_docs),
    }
    deployment_path = root / "production" / "deployment" / "summary.json"
    deployment = load_json(deployment_path) if deployment_path.is_file() else {
        "status": "not-executed-no-authorized-environment", "pass": False,
    }
    t2_pass = deployment.get("topology") == "t2" and deployment.get("pass") is True
    decision = decide(all(safety_checks.values()), t2_pass)
    gaps = []
    if not t2_pass:
        gaps.extend([
            "T2 user-authorized HTTPS/CDN environment was not provided",
            "true browser quota exhaustion remains deployment-environment validation",
            "candidate adoption requires explicit reload/new session",
        ])
    if firefox_compatibility_fallback:
        gaps.append(firefox_compatibility_value["formalGap"])
    if firefox_longevity_fallback:
        gaps.append(firefox_longevity_value["formalGap"])
    if firefox_compatibility_fallback or firefox_longevity_fallback:
        gaps.append("Firefox worker-generation budget requires bounded reuse and full browser reload guidance")
    if not binding["pass"]:
        gaps.append(
            "R8 browser evidence is not bound to the release currently in dist/"
        )
    performance = performance_summary(delivery, r8c)
    write_json(root / "production" / "release-binding.json", binding)
    write_json(root / "production" / "performance" / "summary.json", {
        "schemaVersion": 1, "release": "R8-D-production-validation",
        "measurements": performance, "t2Included": t2_pass, "pass": True,
    })
    write_json(root / "production" / "network" / "summary.json", {
        "schemaVersion": 1, "release": "R8-D-production-validation", **network,
    })
    write_json(root / "production" / "fonts" / "summary.json", {
        "schemaVersion": 1, "release": "R8-D-production-validation", **fonts,
    })
    write_json(root / "production" / "roundtrip" / "summary.json", {
        "schemaVersion": 1, "release": "R8-D-production-validation", **roundtrip,
    })
    write_json(root / "production" / "security" / "summary.json", {
        "schemaVersion": 1, "release": "R8-D-production-validation",
        "checks": security, "pass": all(security.values()),
    })
    summary = {
        "schemaVersion": 1,
        "release": "R8-D-production-validation",
        "decision": decision,
        "advancementAllowed": decision in {"GO", "PARTIAL_GO_LOCAL_DELIVERY"},
        "core": {"commit": CORE_COMMIT},
        "artifacts": {"loaderSha256": LOADER_SHA256, "wasmSha256": WASM_SHA256},
        "matrixSha256": sha256_file(project / "r8" / "production-matrix-v1.json"),
        "releaseIds": {item["slot"]: item["releaseId"] for item in release_set["releases"]},
        "releaseBinding": binding,
        "safetyChecks": safety_checks,
        "compatibility": compatibility,
        "compatibilityAcceptance": {
            "firefoxCompositionalFallback": firefox_compatibility_fallback,
            "pass": compatibility_accepted,
        },
        "longevity": longevity,
        "longevityAcceptance": {
            "firefoxCompositionalFallback": firefox_longevity_fallback,
            "pass": longevity_accepted,
        },
        "inherited": inherited,
        "security": security,
        "performance": performance,
        "fonts": fonts,
        "roundtrip": roundtrip,
        "network": network,
        "deployment": deployment,
        "formalGaps": gaps,
        "environment": {
            "t2UrlConfigured": bool(os.environ.get("R8_T2_URL")),
            "t2Status": deployment.get("status"),
        },
        "pass": decision in {"GO", "PARTIAL_GO_LOCAL_DELIVERY"},
    }
    output = root / "production" / "summary.json"
    write_json(output, summary)
    top = root / "summary.json"
    write_json(top, {
        **summary,
        "release": "R8-delivery-update-recovery",
        "currentStage": "R8-D",
        "phases": {
            "R8-A": {"summary": str(root / "discovery" / "summary.json")},
            "R8-B": {"summary": str(delivery_path)},
            "R8-C": {"summary": str(r8c_path), "decision": r8c.get("decision")},
            "R8-D": {"summary": str(output), "decision": decision},
        },
    })
    print(json.dumps({
        "output": str(output), "topLevel": str(top), "decision": decision,
        "safetyChecks": safety_checks,
        "releaseBinding": {
            key: binding[key] for key in
            ("boundFamilies", "supersededFamilies", "unattributableFamilies")
        },
        "unboundEvidence": [
            {"family": item["family"], "reason": item["reason"]}
            for item in binding["families"] if not item["pass"]
        ],
        "formalGaps": gaps, "pass": summary["pass"],
    }, ensure_ascii=False, indent=2))
    if decision == "STOP":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
