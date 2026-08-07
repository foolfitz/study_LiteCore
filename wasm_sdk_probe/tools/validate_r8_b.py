#!/usr/bin/env python3
"""Aggregate the frozen R8-B direct-delivery gate without relaxing R8-A limits."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from r8_bundle import validate_bundle_index
from r8_release import load_json, sha256_file, write_json


TRANSPORTS = ("identity", "gzip")
TOPOLOGIES = ("t0", "t1")
BASE_NEGATIVES = (
    "wrong-bytes", "manifest-bad-schema", "manifest-bad-release",
    "manifest-duplicate-role", "manifest-unknown-role", "manifest-path-traversal",
    "manifest-credential-url", "manifest-unknown-scheme", "manifest-missing-role",
    "js-404", "worker-500", "wasm-404", "data-wrong-bytes",
    "metadata-wrong-type", "wrong-encoding", "partial-response",
    "timeout-late-response", "cancel", "stale-release", "redirect-cross-origin", "no-coep",
)


def repetition_checks(summary: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for topology in TOPOLOGIES:
        topology_cases = next((item.get("cases", []) for item in summary.get("topologies", [])
                               if item.get("topology") == topology), [])
        passed = {case.get("caseId") for case in topology_cases if case.get("pass") is True}
        for transport in TRANSPORTS:
            checks[f"{topology}-{transport}-cold3"] = all(
                f"{transport}-cold-{number}" in passed for number in range(1, 4))
            checks[f"{topology}-{transport}-warm3"] = all(
                f"{transport}-warm-{number}" in passed for number in range(1, 4))
        checks[f"{topology}-known-good-recovery"] = "known-good-recovery" in passed
        by_id = {case.get("caseId"): case for case in topology_cases}
        required_negatives = (*BASE_NEGATIVES, *(("no-cors", "no-corp") if topology == "t1" else ()))
        checks[f"{topology}-negative-matrix"] = all(
            (case := by_id.get(f"negative-{identifier}")) is not None
            and case.get("pass") is True and case.get("workersStarted") == 0
            and case.get("documentMutations") == 0
            for identifier in required_negatives
        )
        if topology == "t0":
            checks["t0-fidelity-restart"] = by_id.get("fidelity-restart", {}).get("pass") is True
            checks["t0-handshake-mismatch"] = (
                by_id.get("handshake-mismatch", {}).get("pass") is True
                and by_id.get("handshake-mismatch", {}).get("workersStarted") == 1
            )
            checks["t0-full-fidelity-font"] = (
                by_id.get("font-full-fidelity", {}).get("pass") is True
                and by_id.get("font-full-fidelity", {}).get("policy") == "full-fidelity"
            )
    return checks


def decide(safety_pass: bool, partial_gaps: list[str]) -> str:
    if not safety_pass:
        return "STOP"
    return "PARTIAL_GO" if partial_gaps else "GO"


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument("--evidence-root", type=Path,
                        default=workspace / "findings" / "evidence" / "sdk-r8" / "delivery")
    args = parser.parse_args()
    project, root = args.project.resolve(), args.evidence_root.resolve()
    bundle = validate_bundle_index(project / "dist" / "releases")
    index = load_json(project / "dist" / "releases" / "index.json")
    thresholds = load_json(workspace / "findings" / "evidence" / "sdk-r8"
                           / "discovery" / "thresholds.json")
    browser: dict[str, Any] = {}
    browser_checks: dict[str, bool] = {}
    for name in ("chrome", "firefox"):
        path = root / "browser" / name / "summary.json"
        browser[name] = load_json(path) if path.is_file() else {}
        repetitions = repetition_checks(browser[name]) if browser[name] else {}
        browser_checks[name] = (browser[name].get("suite") == "full"
                                and browser[name].get("pass") is True
                                and repetitions and all(repetitions.values()))
        browser[name]["gateChecks"] = repetitions
    roundtrip_path = root / "roundtrip" / "summary.json"
    roundtrip = load_json(roundtrip_path) if roundtrip_path.is_file() else {}
    preflight_checks = {}
    for phase in ("before", "after"):
        path = root / "baseline" / f"preflight-{phase}.json"
        preflight_checks[phase] = path.is_file() and load_json(path).get("pass") is True
    by_policy = {item["policy"]: item for item in index["releases"]}
    full_bytes = by_policy["full-fidelity"]["requiredRawBytes"]
    frozen_limit = thresholds["requiredGraphMaxRawBytes"]
    safety_checks = {
        "bundle": bundle["pass"],
        "chrome": browser_checks["chrome"],
        "firefox": browser_checks["firefox"],
        "roundtrip": roundtrip.get("pass") is True,
        "preflightBefore": preflight_checks["before"],
        "preflightAfter": preflight_checks["after"],
    }
    partial_gaps = []
    if shutil.which("brotli") is None:
        partial_gaps.append("Brotli CLI unavailable; identity and deterministic gzip only")
    if full_bytes > frozen_limit:
        partial_gaps.append(
            f"full-fidelity required graph {full_bytes} exceeds frozen {frozen_limit}-byte limit"
        )
    safety_pass = all(safety_checks.values())
    decision = decide(safety_pass, partial_gaps)
    write_json(root / "bundles" / "summary.json", {
        "schemaVersion": 1, "index": index, "validation": bundle,
        "pass": bundle["pass"] and index.get("pass") is True,
    })
    negative_evidence = []
    font_evidence = []
    header_evidence = []
    for browser_name, browser_summary in browser.items():
        for topology in browser_summary.get("topologies", []):
            topology_name = topology.get("topology")
            for case in topology.get("cases", []):
                identifier = str(case.get("caseId") or "")
                if identifier.startswith("negative-"):
                    negative_evidence.append({
                        "browser": browser_name, "topology": topology_name,
                        "caseId": identifier, "error": case.get("error"),
                        "workersStarted": case.get("workersStarted"),
                        "documentMutations": case.get("documentMutations"),
                        "pass": case.get("pass"),
                    })
                if identifier == "font-full-fidelity":
                    font_evidence.append({
                        "browser": browser_name, "topology": topology_name,
                        "releaseId": case.get("handshake", {}).get("releaseId"),
                        "policy": case.get("policy"), "document": case.get("document"),
                        "output": case.get("output"), "pass": case.get("pass"),
                    })
                if identifier == "smoke-standard-identity":
                    header_evidence.append({
                        "browser": browser_name, "topology": topology_name,
                        "crossOriginIsolated": case.get("crossOriginIsolated"),
                        "transport": case.get("transport"),
                        "artifactContracts": case.get("verified", {}).get("artifacts"),
                        "pass": case.get("pass"),
                    })
    write_json(root / "negative" / "summary.json", {
        "schemaVersion": 1, "cases": negative_evidence,
        "caseCount": len(negative_evidence),
        "pass": bool(negative_evidence) and all(item["pass"] for item in negative_evidence),
    })
    write_json(root / "fonts" / "summary.json", {
        "schemaVersion": 1, "cases": font_evidence,
        "pass": len(font_evidence) == 2 and all(item["pass"] for item in font_evidence),
    })
    write_json(root / "headers" / "summary.json", {
        "schemaVersion": 1, "smoke": header_evidence,
        "pass": len(header_evidence) == 4 and all(
            item["pass"] and item["crossOriginIsolated"] for item in header_evidence
        ),
    })
    for item in index["releases"]:
        release_root = project / "dist" / "releases" / item["releaseId"]
        write_json(root / "manifests" / f"{item['policy']}.json",
                   load_json(release_root / "release-manifest.json"))
        write_json(root / "compression" / f"{item['policy']}.json",
                   load_json(release_root / "compression-index.json"))
    summary = {
        "schemaVersion": 1, "release": "R8-B-versioned-artifact-delivery",
        "decision": decision, "advancementAllowed": decision in {"GO", "PARTIAL_GO"},
        "safetyChecks": safety_checks, "partialGaps": partial_gaps,
        "thresholds": {"requiredGraphMaxRawBytes": frozen_limit,
                       "fullFidelityRequiredRawBytes": full_bytes,
                       "fullFidelityWithinFrozenLimit": full_bytes <= frozen_limit},
        "bundles": bundle, "releaseIndexSha256": sha256_file(
            project / "dist" / "releases" / "index.json"),
        "browsers": browser, "roundtrip": roundtrip,
        "pass": decision in {"GO", "PARTIAL_GO"},
    }
    output = root / "summary.json"
    write_json(output, summary)
    discovery_summary = root.parent / "discovery" / "summary.json"
    write_json(root.parent / "summary.json", {
        "schemaVersion": 1, "release": "R8-delivery-update-recovery",
        "currentStage": "R8-B", "decision": decision,
        "advancementAllowed": summary["advancementAllowed"],
        "phases": {
            "R8-A": {"summary": str(discovery_summary),
                     "decision": load_json(discovery_summary).get("decision")
                     if discovery_summary.is_file() else None},
            "R8-B": {"summary": str(output), "decision": decision},
        },
        "partialGaps": partial_gaps, "pass": summary["pass"],
    })
    print(json.dumps({"output": str(output), "decision": decision,
                      "safetyChecks": safety_checks, "partialGaps": partial_gaps,
                      "pass": summary["pass"]}, ensure_ascii=False, indent=2))
    if decision == "STOP":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
