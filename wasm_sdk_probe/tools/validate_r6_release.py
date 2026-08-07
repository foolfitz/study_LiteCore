#!/usr/bin/env python3
"""Aggregate R6-A/B/C, round-trip, regression and workspace evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def browser_flow_pass(path: Path) -> bool:
    data = load(path)
    return bool(data["samples"] and all(item["run"].get("pass") for item in data["samples"]))


def edit_regression_pass(path: Path) -> bool:
    data = load(path)
    details = data["scenarios"][0].get("details", {})
    return bool(
        data.get("pass")
        and details.get("manualEditAfterAccept", {}).get("bytes", 0) > 0
        and details.get("manualUndo", {}).get("localBytesAvailable") is False
        and details.get("versionCount") == 2
    )


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    evidence = workspace / "findings/evidence/sdk-r6"
    regression = evidence / "regression"

    discovery = load(evidence / "discovery/summary.json")
    reader = {
        browser: load(evidence / f"browser/r6-a/reader-{browser}-summary.json")
        for browser in ("chrome", "firefox")
    }
    contract = load(evidence / "contract/summary.json")
    reference = {
        combination: load(evidence / f"browser/r6-c/reference-{combination}-summary.json")
        for combination in ("chrome-chrome", "firefox-firefox", "chrome-firefox")
    }
    roundtrip = load(evidence / "roundtrip/summary.json")
    preflight = load(evidence / "baseline/preflight-after.json")
    r5_artifacts = load(regression / "r5-artifacts.json")
    r3_roundtrip = load(regression / "r3-roundtrip.json")
    r1_roundtrip = load(regression / "r1-roundtrip.json")

    regression_checks = {
        "r5UnitAbiProfileAndArtifactContract": r5_artifacts.get("decision") == "GO",
        "r5ReviewChrome": browser_flow_pass(
            regression / "r5-review/chrome-t1-plain-zh-cold-summary.json"
        ),
        "r5ReviewFirefox": browser_flow_pass(
            regression / "r5-review/firefox-t1-plain-zh-cold-summary.json"
        ),
        "r5ReaderChrome": browser_flow_pass(
            regression / "r5-reader/chrome-t1-plain-zh-cold-summary.json"
        ),
        "r5ReaderFirefox": browser_flow_pass(
            regression / "r5-reader/firefox-t1-plain-zh-cold-summary.json"
        ),
        "providerChrome": load(
            regression / "r5-provider/chrome-r4-conformance.json"
        )["conformance"]["pass"],
        "providerFirefox": load(
            regression / "r5-provider/firefox-r4-conformance.json"
        )["conformance"]["pass"],
        "r3Abi": load(
            regression / "r3-conformance/chrome-r3-conformance.json"
        )["conformance"]["pass"],
        "r3SemanticFlow": browser_flow_pass(
            regression / "r3-flow/chrome-t1-plain-zh-cold-summary.json"
        ),
        "r3Roundtrip": r3_roundtrip["pass"],
        "r2LifecycleCrash": load(
            regression / "r2/chrome-t1-plain-zh-r2-conformance.json"
        )["conformance"]["pass"],
        "r1Legacy": browser_flow_pass(
            regression / "r1/chrome-t1-plain-zh-cold-summary.json"
        ),
        "r1Roundtrip": all(item["pass"] for item in r1_roundtrip["documents"]),
    }
    checks = {
        "r6ADiscovery": discovery["pass"] and discovery["decision"] == "GO",
        "r6AReaderChrome3of3": reader["chrome"]["pass"]
        and len(reader["chrome"]["samples"]) == 3,
        "r6AReaderFirefox3of3": reader["firefox"]["pass"]
        and len(reader["firefox"]["samples"]) == 3,
        "r6BDomain12of12": contract["domain"]["passed"] == 12
        and contract["domain"]["pass"],
        "r6BHttp12of12": contract["http"]["passed"] == 12
        and contract["http"]["pass"],
        "r6BAdaptersEquivalent": contract["adaptersEquivalent"],
        "r6CChromeChrome3of3": reference["chrome-chrome"]["pass"]
        and reference["chrome-chrome"]["requestedSamples"] == 3,
        "r6CFirefoxFirefox3of3": reference["firefox-firefox"]["pass"]
        and reference["firefox-firefox"]["requestedSamples"] == 3,
        "r6CMixedRequiredScenarios": reference["chrome-firefox"]["pass"]
        and {"s1", "s2", "s3", "s5"}.issubset(reference["chrome-firefox"]["scenarios"]),
        "r6CEditAfterAcceptChrome": edit_regression_pass(
            evidence / "browser/r6-c/edit-regression/chrome-alice/reference-chrome-firefox-1.json"
        ),
        "r6CEditAfterAcceptFirefox": edit_regression_pass(
            evidence / "browser/r6-c/edit-regression/firefox-alice/reference-firefox-chrome-1.json"
        ),
        "r6CRoundtrip": roundtrip["pass"],
        "r1ToR5Regression": all(regression_checks.values()),
        "coreAndR5ArtifactsUnchanged": preflight["pass"],
    }
    result = {
        "schemaVersion": 1,
        "release": "R6",
        "decision": "GO" if all(checks.values()) else "STOP",
        "checks": checks,
        "regressions": regression_checks,
        "counts": {
            "r6AReaderSamples": sum(len(value["samples"]) for value in reader.values()),
            "r6BConformanceScenarios": contract["domain"]["passed"] + contract["http"]["passed"],
            "r6CFullScenarioRuns": (
                reference["chrome-chrome"]["requestedSamples"]
                + reference["firefox-firefox"]["requestedSamples"]
            ),
            "r6CMixedRuns": reference["chrome-firefox"]["requestedSamples"],
            "r6CManualEditRegressions": 2,
            "r6COdtPdfSamples": len(roundtrip["samples"]),
        },
        "artifacts": {
            "coreCommit": preflight["core"]["head"],
            "writerReviewLoaderSha256": preflight["artifacts"][0]["sha256"],
            "writerReviewWasmSha256": preflight["artifacts"][1]["sha256"],
            "desktopLibreOffice": roundtrip["desktopVersion"],
        },
        "knownLimitation": {
            "finding": 12,
            "status": "open",
            "scope": "t2-styled close timeout after discovery operations; required t1/t3 paths pass",
        },
        "pass": all(checks.values()),
    }
    output = evidence / "summary.json"
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["pass"]:
        raise SystemExit("R6 release validation failed")


if __name__ == "__main__":
    main()
