#!/usr/bin/env python3
"""Validate finding 012 bounded Worker recovery evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


EXPECTED_ARTIFACT_HASHES = {
    "loader": "35d96f5fdcb9ed0cdb19f28a743245e0dbd255cbf90a2c14d680f0b1b9c63566",
    "wasm": "ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6",
}


def _record_pass(record: dict[str, Any]) -> bool:
    metrics = record.get("metrics") or {}
    close = metrics.get("close") or {}
    recovery = close.get("recovery") or {}
    event_names = [item.get("event") for item in recovery.get("events") or []]
    workers = metrics.get("workers") or {}
    handles = metrics.get("handles") or {}
    return (
        record.get("outcome") == "close-pass"
        and record.get("pass") is True
        and metrics.get("pass") is True
        and close.get("status") == "passed"
        and recovery.get("used") is True
        and event_names.count("document-close-recovery-started") == 1
        and event_names.count("document-close-recovery-complete") == 1
        and "document-close-recovery-failed" not in event_names
        and isinstance(workers.get("created"), int)
        and workers["created"] >= 2
        and workers.get("terminated") == workers["created"]
        and workers.get("active") == 0
        and handles.get("opened") == 1
        and handles.get("closed") == 1
        and handles.get("active") == 0
    )


def decide_remediation(
    records: dict[str, list[dict[str, Any]]],
    attribution_decision: str,
) -> dict[str, Any]:
    checks = {
        browser: {
            "runs": len(records.get(browser, [])),
            "cleanRecoveries": sum(_record_pass(item) for item in records.get(browser, [])),
            "pass": len(records.get(browser, [])) == 3
            and all(_record_pass(item) for item in records.get(browser, [])),
        }
        for browser in ("chrome", "firefox")
    }
    if attribution_decision != "EMSCRIPTEN_SPECIFIC_DOCUMENT_DESTROY":
        return {
            "decision": "ATTRIBUTION_MISMATCH",
            "nextAction": "restore-attribution-evidence",
            "checks": checks,
            "pass": False,
        }
    passed = all(item["pass"] for item in checks.values())
    return {
        "decision": (
            "REMEDIATED_BY_BOUNDED_WORKER_RECYCLE"
            if passed else "REMEDIATION_INCOMPLETE"
        ),
        "nextAction": "r7-regression" if passed else "repair-remediation",
        "checks": checks,
        "pass": passed,
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "012" / "r7-remediation",
    )
    parser.add_argument(
        "--attribution-summary",
        type=Path,
        default=workspace / "findings" / "evidence" / "012"
        / "native-26-8-attribution" / "summary.json",
    )
    parser.add_argument(
        "--r7-summary", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r7" / "summary.json",
    )
    args = parser.parse_args()

    records: dict[str, list[dict[str, Any]]] = {}
    summaries = {}
    for browser in ("chrome", "firefox"):
        summary = load_json(args.evidence_root / browser / "summary.json")
        summaries[browser] = summary
        records[browser] = [load_json(Path(item["result"])) for item in summary["runs"]]
    attribution = load_json(args.attribution_summary)
    decision = decide_remediation(records, str(attribution.get("decision") or ""))
    artifact_checks = {
        name: all(
            record.get("artifactHashes", {}).get(name) == digest
            for items in records.values()
            for record in items
        )
        for name, digest in EXPECTED_ARTIFACT_HASHES.items()
    }
    if not all(artifact_checks.values()):
        decision = {
            **decision,
            "decision": "ARTIFACT_MISMATCH",
            "nextAction": "restore-production-artifact",
            "pass": False,
        }
    r7 = load_json(args.r7_summary) if args.r7_summary.is_file() else {}
    r7_pass = (
        r7.get("pass") is True
        and r7.get("decision") in {"GO", "PARTIAL_GO", "PARTIAL_GO_ODT_FIRST"}
        and r7.get("checks", {}).get("r1ToR6Regression") is True
    )
    if decision.get("pass") is True and r7_pass:
        decision = {**decision, "nextAction": "r7-complete"}
    result = {
        "schemaVersion": 1,
        "release": "finding-012-r7-remediation",
        "verifiedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "strategy": "bounded-close-timeout-worker-restart",
        "attributionEvidence": str(args.attribution_summary),
        "attributionDecision": attribution.get("decision"),
        "artifactChecks": artifact_checks,
        "browserEvidence": {
            browser: str(args.evidence_root / browser / "summary.json")
            for browser in summaries
        },
        "r7Pass": r7_pass,
        **decision,
    }
    write_json(args.evidence_root / "summary.json", result)
    print(json.dumps({
        "decision": result["decision"],
        "nextAction": result["nextAction"],
        "pass": result["pass"],
    }, ensure_ascii=False))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
