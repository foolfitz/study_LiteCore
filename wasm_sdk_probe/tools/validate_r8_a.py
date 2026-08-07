#!/usr/bin/env python3
"""Aggregate and decide the R8-A delivery discovery checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from r8_release import (
    canonical_json_bytes,
    load_json,
    sha256_file,
    validate_release_manifest,
    write_json,
)
from validate_r8_preflight import THRESHOLDS


def load_or_missing(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "missing": True, "pass": False}
    return load_json(path)


def browser_contract(summary: dict[str, Any]) -> dict[str, Any]:
    topologies = summary.get("topologies", []) if isinstance(summary, dict) else []
    by_name = {item.get("topology"): item for item in topologies if isinstance(item, dict)}
    checks = {
        "summaryPass": summary.get("pass") is True,
        "exactTopologies": set(by_name) == {"t0", "t1"},
        "initial": all(by_name.get(name, {}).get("initial", {}).get("pass") is True for name in ("t0", "t1")),
        "restart": all(by_name.get(name, {}).get("restart", {}).get("pass") is True for name in ("t0", "t1")),
        "headers": all(by_name.get(name, {}).get("headers", {}).get("pass") is True for name in ("t0", "t1")),
        "faults": all(
            by_name.get(name, {}).get("initial", {}).get("faults", {}).get("pass") is True
            for name in ("t0", "t1")
        ),
        "largeCache": all(
            by_name.get(name, {}).get("initial", {}).get("cache", {}).get("pass") is True
            and by_name.get(name, {}).get("restart", {}).get("cache", {}).get("pass") is True
            for name in ("t0", "t1")
        ),
        "storageEstimate": all(
            by_name.get(name, {}).get("initial", {}).get("storage", {}).get("before", {}).get("available") is True
            for name in ("t0", "t1")
        ),
    }
    return {"checks": checks, "pass": all(checks.values()), "topologies": by_name}


def decide(checks: dict[str, bool], formal_gaps: dict[str, str]) -> str:
    if not all(checks.values()):
        return "STOP"
    return "PARTIAL_GO" if any(value not in {"none", "not-required"} for value in formal_gaps.values()) else "GO"


def aggregate(project: Path, evidence_root: Path) -> dict[str, Any]:
    project = project.resolve()
    workspace = project.parent
    evidence_root = evidence_root.resolve()
    manifest_path = project / "dist" / "r8" / "release-manifest.json"
    schema_path = project / "r8" / "release-schema-v1.json"
    manifest = load_or_missing(manifest_path)
    manifest_validation = (
        validate_release_manifest(manifest, project / "dist")
        if manifest.get("missing") is not True else manifest
    )
    write_json(evidence_root / "release-graph" / "release-manifest.json", manifest)
    write_json(evidence_root / "release-graph" / "validation.json", manifest_validation)

    artifacts = manifest.get("artifacts", []) if isinstance(manifest, dict) else []
    required = [item for item in artifacts if item.get("required") is True]
    optional = [item for item in artifacts if item.get("required") is False]
    inventory = {
        "schemaVersion": 1,
        "releaseId": manifest.get("releaseId"),
        "manifestCanonicalSha256": hashlib.sha256(canonical_json_bytes(manifest)).hexdigest(),
        "manifestFileSha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
        "schemaSha256": sha256_file(schema_path) if schema_path.is_file() else None,
        "artifactCount": len(artifacts),
        "requiredArtifactCount": len(required),
        "optionalArtifactCount": len(optional),
        "requiredRawBytes": sum(item.get("rawBytes", 0) for item in required),
        "optionalRawBytes": sum(item.get("rawBytes", 0) for item in optional),
        "maxArtifactRawBytes": max((item.get("rawBytes", 0) for item in artifacts), default=0),
        "roles": [item.get("role") for item in artifacts],
    }
    inventory["checks"] = {
        "manifestUnderLimit": manifest_path.is_file()
        and manifest_path.stat().st_size <= THRESHOLDS["manifestMaxBytes"],
        "requiredGraphUnderLimit": inventory["requiredRawBytes"] <= THRESHOLDS["requiredGraphMaxRawBytes"],
        "maxArtifactUnderLimit": inventory["maxArtifactRawBytes"] <= THRESHOLDS["artifactMaxRawBytes"],
        "closedRoles": len(inventory["roles"]) == len(set(inventory["roles"])) == 17,
    }
    inventory["pass"] = all(inventory["checks"].values()) and manifest_validation.get("pass") is True
    write_json(evidence_root / "release-graph" / "inventory.json", inventory)

    browser_summaries = {
        browser: load_or_missing(evidence_root / "browser" / browser / "summary.json")
        for browser in ("chrome", "firefox")
    }
    browser_contracts = {
        browser: browser_contract(summary)
        for browser, summary in browser_summaries.items()
    }

    headers_items = []
    compression_items = []
    cache_items = []
    fault_items = []
    for browser, contract in browser_contracts.items():
        for topology in ("t0", "t1"):
            item = contract["topologies"].get(topology, {})
            initial = item.get("initial", {})
            restart = item.get("restart", {})
            headers_items.append({
                "browser": browser,
                "topology": topology,
                "headers": item.get("headers", {}),
                "pass": item.get("headers", {}).get("pass") is True,
            })
            gzip_probe = initial.get("faults", {}).get("gzip", {})
            compression_items.append({
                "browser": browser,
                "topology": topology,
                "gzip": gzip_probe,
                "pass": gzip_probe.get("ok") is True
                and gzip_probe.get("text") == "R8-DELIVERY-CANARY-v1\n",
            })
            cache_items.append({
                "browser": browser,
                "topology": topology,
                "initial": initial.get("cache", {}),
                "restart": restart.get("cache", {}),
                "storage": initial.get("storage", {}),
                "pass": initial.get("cache", {}).get("pass") is True
                and restart.get("cache", {}).get("pass") is True,
            })
            fault_items.append({
                "browser": browser,
                "topology": topology,
                "faults": initial.get("faults", {}),
                "pass": initial.get("faults", {}).get("pass") is True,
            })

    baseline_before = load_or_missing(evidence_root / "baseline" / "preflight-before.json")
    baseline_after = load_or_missing(evidence_root / "baseline" / "preflight-after.json")
    thresholds = load_or_missing(evidence_root / "thresholds.json")
    threshold_pass = thresholds == THRESHOLDS
    brotli_available = baseline_before.get("tools", {}).get("brotli") is not None

    headers_summary = {"items": headers_items, "pass": all(item["pass"] for item in headers_items)}
    compression_summary = {
        "identity": "covered-by-release-graph",
        "gzip": compression_items,
        "brotli": "available" if brotli_available else "unavailable-local-cli",
        "pass": all(item["pass"] for item in compression_items),
    }
    cache_summary = {
        "items": cache_items,
        "realQuotaPressure": "not-executed-browser-policy",
        "pass": all(item["pass"] for item in cache_items),
    }
    fault_summary = {"items": fault_items, "pass": all(item["pass"] for item in fault_items)}
    write_json(evidence_root / "headers" / "summary.json", headers_summary)
    write_json(evidence_root / "compression" / "summary.json", compression_summary)
    write_json(evidence_root / "cache-storage" / "summary.json", cache_summary)
    write_json(evidence_root / "fault-feasibility" / "summary.json", fault_summary)

    r7_compatibility_path = workspace / "findings" / "evidence" / "sdk-r7" / "compatibility-summary.json"
    r7_compatibility = load_or_missing(r7_compatibility_path)
    font_fixture = next(
        (item for item in r7_compatibility.get("fidelity", []) if item.get("id") == "l1-hyperlink-font-odt"),
        {},
    )
    by_role = {item.get("role"): item for item in artifacts}
    manifest_capabilities = set(manifest.get("capabilities", []))
    font_summary = {
        "policy": "locale-mandatory-cjk-explicit-optional-fallback",
        "publicFontInventory": "not-observable",
        "cjkRequired": by_role.get("cjk-data", {}).get("required") is True
        and by_role.get("cjk-metadata", {}).get("required") is True,
        "fallbackOptional": by_role.get("fallback-data", {}).get("required") is False
        and by_role.get("fallback-metadata", {}).get("required") is False,
        "noAdvertisedFontInventoryCapability": not any("font" in item for item in manifest_capabilities),
        "r7FontFixture": font_fixture,
    }
    font_summary["pass"] = (
        font_summary["cjkRequired"]
        and font_summary["fallbackOptional"]
        and font_summary["noAdvertisedFontInventoryCapability"]
        and font_fixture.get("pass") is True
        and font_fixture.get("font") == "degraded-known"
    )
    write_json(evidence_root / "fonts" / "summary.json", font_summary)

    checks = {
        "preflightBefore": baseline_before.get("pass") is True,
        "preflightAfter": baseline_after.get("pass") is True,
        "thresholdsFrozen": threshold_pass,
        "releaseGraph": inventory["pass"],
        "chromeT0T1": browser_contracts["chrome"]["pass"],
        "firefoxT0T1": browser_contracts["firefox"]["pass"],
        "headers": headers_summary["pass"],
        "gzip": compression_summary["pass"],
        "cacheRestart": cache_summary["pass"],
        "faultFeasibility": fault_summary["pass"],
        "fontPolicy": font_summary["pass"],
    }
    formal_gaps = {
        "brotliPrecompression": "none" if brotli_available else "unavailable-local-cli",
        "realQuotaPressure": "not-executed-browser-policy",
        "documentFontInventory": "not-observable-public-sdk",
        "t2HttpsDeployment": "not-required-in-r8-a",
    }
    decision = decide(checks, formal_gaps)
    summary = {
        "schemaVersion": 1,
        "release": "R8-A-delivery-discovery",
        "decision": decision,
        "checks": checks,
        "formalGaps": formal_gaps,
        "releaseGraph": inventory,
        "browsers": {
            browser: {"checks": value["checks"], "pass": value["pass"]}
            for browser, value in browser_contracts.items()
        },
        "evidence": {
            "preflightBefore": str(evidence_root / "baseline" / "preflight-before.json"),
            "preflightAfter": str(evidence_root / "baseline" / "preflight-after.json"),
            "releaseGraph": str(evidence_root / "release-graph" / "inventory.json"),
            "headers": str(evidence_root / "headers" / "summary.json"),
            "compression": str(evidence_root / "compression" / "summary.json"),
            "cacheStorage": str(evidence_root / "cache-storage" / "summary.json"),
            "faults": str(evidence_root / "fault-feasibility" / "summary.json"),
            "fonts": str(evidence_root / "fonts" / "summary.json"),
        },
        "nextAction": "r8-b-planning" if decision in {"GO", "PARTIAL_GO"} else "r8-a-remediation",
        "pass": decision in {"GO", "PARTIAL_GO"},
    }
    return summary


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r8" / "discovery",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r8" / "discovery" / "summary.json",
    )
    args = parser.parse_args()

    summary = aggregate(args.project, args.evidence_root)
    write_json(args.output.resolve(), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
