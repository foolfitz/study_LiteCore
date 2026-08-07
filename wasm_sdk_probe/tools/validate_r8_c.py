#!/usr/bin/env python3
"""Aggregate the frozen R8-C Service Worker correctness and recovery gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from r8_release import load_json, sha256_file, write_json
from validate_r8_c_preflight import validate_release_set


T0_REQUIRED = {
    "fresh-1", "fresh-2", "fresh-3",
    "warm-1", "warm-2", "warm-3",
    "offline-ready-1", "offline-ready-2", "offline-ready-3",
    "offline-cold-no-release", "offline-entry-missing",
    "online-repair-a", "online-repair-health",
    "update-multi-client-1",
    "update-stage-b-2", "update-activate-b-2", "update-rollback-a-2",
    "update-stage-b-3", "update-activate-b-3", "update-rollback-a-3",
    "interrupt-manifest-verified", "recover-manifest-verified",
    "interrupt-artifact-cached", "recover-artifact-cached",
    "interrupt-metadata-before-ready", "recover-metadata-before-ready",
    "interrupt-activation-prepared", "recover-activation-prepared",
    "storage-write-failure", "metadata-corrupt",
    "activate-b-health-failure", "verify-corrupt-b",
    "activate-c", "evict-bounded", "rollback-b", "rollback-offline",
}
T1_REQUIRED = {
    "fresh-1", "warm-1", "warm-2", "warm-3",
    "offline-ready-1", "offline-cold-no-release", "offline-entry-missing",
    "online-repair-a", "online-repair-health",
    "update-stage-b-1", "update-activate-b-1", "update-rollback-a-1",
    "interrupt-manifest-verified", "recover-manifest-verified",
    "interrupt-artifact-cached", "recover-artifact-cached",
    "interrupt-metadata-before-ready", "recover-metadata-before-ready",
    "interrupt-activation-prepared", "recover-activation-prepared",
    "storage-write-failure", "metadata-corrupt",
    "activate-b-health-failure", "verify-corrupt-b",
    "activate-c", "evict-bounded", "rollback-b", "rollback-offline",
}


def topology_checks(summary: dict[str, Any], topology: str) -> dict[str, bool]:
    topology_summary = next(
        (item for item in summary.get("topologies", []) if item.get("topology") == topology),
        {},
    )
    cases = {item.get("caseId"): item for item in topology_summary.get("cases", [])}
    required = T0_REQUIRED if topology == "t0" else T1_REQUIRED
    return {
        "suite-full": summary.get("suite") == "full",
        "topology-summary": topology_summary.get("pass") is True,
        "required-cases": all(
            cases.get(case_id, {}).get("pass") is True
            and cases.get(case_id, {}).get("gatePass") is True
            for case_id in required
        ),
        "no-failed-case": bool(cases) and all(
            item.get("pass") is True and item.get("gatePass") is True
            for item in cases.values()
        ),
    }


def decide(safety_pass: bool, partial_gaps: list[str]) -> str:
    if not safety_pass:
        return "STOP"
    return "PARTIAL_GO" if partial_gaps else "GO"


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r8" / "service-worker",
    )
    args = parser.parse_args()
    project, root = args.project.resolve(), args.evidence_root.resolve()
    browsers: dict[str, Any] = {}
    browser_checks: dict[str, Any] = {}
    for browser in ("chrome", "firefox"):
        path = root / "browser" / browser / "summary.json"
        summary = load_json(path) if path.is_file() else {}
        checks = {topology: topology_checks(summary, topology) for topology in ("t0", "t1")}
        browsers[browser] = summary
        browser_checks[browser] = {
            "topologies": checks,
            "pass": bool(summary) and all(all(values.values()) for values in checks.values()),
        }
    preflight = {}
    for phase in ("before", "after"):
        path = root / "baseline" / f"preflight-{phase}.json"
        preflight[phase] = path.is_file() and load_json(path).get("pass") is True
    release_set = validate_release_set(project)
    safety_checks = {
        "releaseSet": release_set["pass"],
        "chrome": browser_checks["chrome"]["pass"],
        "firefox": browser_checks["firefox"]["pass"],
        "preflightBefore": preflight["before"],
        "preflightAfter": preflight["after"],
    }
    partial_gaps = [
        "true browser quota exhaustion is unavailable as a safe deterministic control",
        "candidate adoption requires explicit reload/new session; no hot engine swap",
    ]
    decision = decide(all(safety_checks.values()), partial_gaps)
    summary = {
        "schemaVersion": 1,
        "release": "R8-C-service-worker",
        "decision": decision,
        "advancementAllowed": decision in {"GO", "PARTIAL_GO"},
        "safetyChecks": safety_checks,
        "partialGaps": partial_gaps,
        "releaseSetSha256": sha256_file(project / "dist" / "r8c" / "release-set.json"),
        "releaseSet": release_set,
        "browserChecks": browser_checks,
        "browsers": browsers,
        "pass": decision in {"GO", "PARTIAL_GO"},
    }
    output = root / "summary.json"
    write_json(output, summary)
    top = root.parent / "summary.json"
    current = load_json(top) if top.is_file() else {"schemaVersion": 1, "phases": {}}
    current.update({
        "release": "R8-delivery-update-recovery",
        "currentStage": "R8-C",
        "decision": decision,
        "advancementAllowed": summary["advancementAllowed"],
        "partialGaps": partial_gaps,
        "pass": summary["pass"],
    })
    current.setdefault("phases", {})["R8-C"] = {
        "summary": str(output), "decision": decision,
    }
    write_json(top, current)
    print(json.dumps({
        "output": str(output), "decision": decision,
        "safetyChecks": safety_checks, "partialGaps": partial_gaps,
        "pass": summary["pass"],
    }, ensure_ascii=False, indent=2))
    if decision == "STOP":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
