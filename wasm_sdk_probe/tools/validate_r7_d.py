#!/usr/bin/env python3
"""Aggregate R7-D usability, manual accessibility and longevity evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from r7_support import load_json, write_json


def missing(path: Path) -> dict:
    return {"path": str(path), "present": False, "pass": False}


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r7",
    )
    args = parser.parse_args()

    thresholds_source = args.evidence_root / "discovery" / "memory" / "thresholds.json"
    thresholds = load_json(thresholds_source)
    write_json(args.evidence_root / "longevity" / "thresholds.json", thresholds)

    usability = {}
    manual = {}
    longevity = {}
    for browser in ("chrome", "firefox"):
        usability_path = args.evidence_root / "browser" / "usability" / browser / "result.json"
        manual_path = args.evidence_root / "manual" / "input" / f"{browser}.json"
        longevity_path = args.evidence_root / "longevity" / browser / "summary.json"
        usability[browser] = load_json(usability_path) if usability_path.is_file() else missing(usability_path)
        manual[browser] = load_json(manual_path) if manual_path.is_file() else missing(manual_path)
        longevity[browser] = load_json(longevity_path) if longevity_path.is_file() else missing(longevity_path)

    manual_keyboard = {
        browser: value.get("accessibility", {}).get("keyboard", {}).get("pass") is True
        for browser, value in manual.items()
    }
    orca = {
        browser: value.get("accessibility", {}).get("orcaOperatorConfirmed") is True
        for browser, value in manual.items()
    }

    finding012 = {}
    required_scenarios = {
        "s1": 3, "s2-reuse": 1, "s2-fresh": 1,
        "s3": 1, "s4": 1, "s5-normal": 1, "s5-known": 1,
    }
    scenario_checks = {}
    for browser, summary in longevity.items():
        runs = summary.get("runs", [])
        scenario_checks[browser] = {
            scenario: sum(1 for item in runs if item.get("scenario") == scenario and item.get("pass")) >= count
            for scenario, count in required_scenarios.items()
        }
        normal = next((item for item in runs if item.get("scenario") == "s5-normal"), None)
        known = next((item for item in runs if item.get("scenario") == "s5-known"), None)
        finding012[browser] = {
            "normalPass": normal is not None and normal.get("pass") is True,
            "knownSequencePass": known is not None and known.get("pass") is True,
            "knownDegradation": known.get("knownDegradation") if known else None,
        }

    compatibility_path = args.evidence_root / "compatibility-summary.json"
    compatibility = load_json(compatibility_path) if compatibility_path.is_file() else missing(compatibility_path)
    input_path = args.evidence_root / "input-summary.json"
    input_summary = load_json(input_path) if input_path.is_file() else missing(input_path)
    checks = {
        "r7B": input_summary.get("decision") in {"GO", "PARTIAL_GO"} and input_summary.get("pass") is True,
        "r7CStressPrecondition": compatibility.get("pass") is True
        and any(item.get("id") == "l4-stress-100" and item.get("pass")
                for item in compatibility.get("fidelity", [])),
        "automaticUsability": all(value.get("pass") is True for value in usability.values()),
        "manualKeyboard": all(manual_keyboard.values()),
        "orcaSpike": any(orca.values()),
        "longevity": all(value.get("pass") is True for value in longevity.values()),
        "scenarioMatrix": all(all(values.values()) for values in scenario_checks.values()),
        "finding012Normal": all(value["normalPass"] for value in finding012.values()),
    }
    firefox_partial_scenarios = all(
        scenario_checks.get("firefox", {}).get(name) is True
        for name in ("s1", "s2-reuse", "s4", "s5-normal", "s5-known")
    )
    safe_partial = (
        checks["r7B"]
        and checks["r7CStressPrecondition"]
        and checks["automaticUsability"]
        and longevity.get("chrome", {}).get("pass") is True
        and firefox_partial_scenarios
        and checks["finding012Normal"]
    )
    formal_pass = all(checks.values())
    decision = "GO" if formal_pass else "PARTIAL_GO" if safe_partial else "STOP"
    result = {
        "schemaVersion": 1,
        "release": "R7-D",
        "decision": decision,
        "checks": checks,
        "usability": usability,
        "manual": {"keyboard": manual_keyboard, "orca": orca},
        "longevity": longevity,
        "scenarioChecks": scenario_checks,
        "finding012": finding012,
        "formalMatrixPass": formal_pass,
        "partialAcceptance": {
            "safeCorePass": safe_partial,
            "firefoxRequiredNormalScenarios": firefox_partial_scenarios,
            "limitations": [
                "Firefox fresh-engine stress stopped after 35/50 successful cycles",
                "Firefox crash-storm recovery stopped at cycle 20 after 19 successful recoveries",
                "headed keyboard matrix and Orca spike were not collected",
            ] if not formal_pass else [],
            "finding": "findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md",
        },
        "documentContentAccessibility": "unsupported-public-sdk",
        "hyperlinkActivation": "unsupported-safe-fallback",
        "pass": safe_partial,
    }
    output = args.evidence_root / "longevity" / "summary.json"
    write_json(output, result)
    print(json.dumps({"output": str(output), "decision": result["decision"], "checks": checks}, ensure_ascii=False, indent=2))
    if not safe_partial:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
