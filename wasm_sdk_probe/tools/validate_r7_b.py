#!/usr/bin/env python3
"""Aggregate R7-B automatic and consolidated headed-manual evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from r7_support import load_json, write_json


EXPECTED_METHODS = {"chewing", "cangjie", "pinyin"}


def validate_manual(path: Path, browser: str) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "status": "pending", "pass": False}
    value = load_json(path)
    commits = value.get("commits", [])
    methods = {
        item.get("inputMethod") for item in commits
        if item.get("metadata", {}).get("source") == "composition"
    }


def validate_single_ime_manual(path: Path, browser: str) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "status": "pending", "pass": False}
    value = load_json(path)
    composition = [
        item for item in value.get("commits", [])
        if item.get("metadata", {}).get("source") == "composition"
    ]
    searches = [
        item for item in value.get("searches", []) if item.get("searchable", True)
    ]
    checks = {
        "schema": value.get("schemaVersion") == 1
        and value.get("release") == "R7-A-headed-manual",
        "browser": ("Chrome/" if browser == "chrome" else "Firefox/")
        in value.get("browser", ""),
        "artifact": value.get("artifact", {}).get("profile") == "writer-review",
        "chewingCommits": len(composition) >= 2
        and "Chewing" in value.get("operatorInputMethod", ""),
        "cancel": value.get("cancelProbe", {}).get("pass") is True
        and value.get("cancelProbe", {}).get("requestDelta") == 0,
        "trustedNativePaste": value.get("trustedNativePasteCount", 0) >= 1,
        "clipboard": value.get("clipboardWrite", {}).get("status") == "passed"
        and value.get("clipboardRead", {}).get("status") == "passed"
        and value.get("clipboardRead", {}).get("commitDelta") == 1,
        "searches": bool(searches) and all(item.get("found") is True for item in searches),
        "output": value.get("output", {}).get("bytes", 0) > 0
        and len(value.get("output", {}).get("sha256", "")) == 64,
        "reportedPass": value.get("pass") is True,
    }
    return {
        "path": str(path), "status": "partial-pass" if all(checks.values()) else "failed",
        "coverage": ["chewing"], "missingMethods": ["cangjie", "pinyin"],
        "checks": checks, "pass": all(checks.values()),
    }
    cancellations = {
        item.get("inputMethod") for item in value.get("cancelProbes", [])
        if item.get("pass") is True and item.get("requestDelta") == 0
    }
    searches = value.get("searches", [])
    checks = {
        "schema": value.get("schemaVersion") == 1
        and value.get("release") == "R7-B-headed-manual",
        "browser": ("Chrome/" if browser == "chrome" else "Firefox/")
        in value.get("browser", ""),
        "artifact": value.get("artifact", {}).get("profile") == "writer-review",
        "threeImeCommits": EXPECTED_METHODS.issubset(methods),
        "threeImeCancel": EXPECTED_METHODS.issubset(cancellations),
        "trustedNativePaste": value.get("trustedNativePasteCount", 0) >= 1,
        "clipboard": value.get("clipboard", {}).get("write", {}).get("status") == "passed"
        and value.get("clipboard", {}).get("read", {}).get("status") == "passed"
        and value.get("clipboard", {}).get("read", {}).get("commitDelta") == 1,
        "searches": bool(searches) and all(item.get("found") is True for item in searches),
        "output": value.get("output", {}).get("bytes", 0) > 0
        and len(value.get("output", {}).get("sha256", "")) == 64,
        "reportedPass": value.get("pass") is True,
    }
    return {
        "path": str(path), "status": "passed" if all(checks.values()) else "failed",
        "checks": checks, "pass": all(checks.values()),
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r7",
    )
    parser.add_argument("--require-manual", action="store_true")
    args = parser.parse_args()
    automatic = {}
    for browser in ("chrome", "firefox"):
        path = args.evidence_root / "browser" / "input" / browser / "summary.json"
        automatic[browser] = load_json(path) if path.is_file() else {
            "path": str(path), "pass": False
        }
    manual = {
        browser: validate_manual(
            args.evidence_root / "manual" / "input" / f"{browser}.json", browser
        )
        for browser in ("chrome", "firefox")
    }
    single_ime_manual = {
        browser: validate_single_ime_manual(
            args.evidence_root / "discovery" / "input" / f"{browser}-manual-pass.json",
            browser,
        )
        for browser in ("chrome", "firefox")
    }
    automatic_pass = all(item.get("pass") is True for item in automatic.values())
    manual_pending = any(item["status"] == "pending" for item in manual.values())
    manual_pass = all(item["pass"] for item in manual.values())
    single_ime_pass = all(item["pass"] for item in single_ime_manual.values())
    if not automatic_pass:
        decision = "STOP"
    elif manual_pass:
        decision = "GO"
    elif single_ime_pass:
        decision = "PARTIAL_GO"
    elif manual_pending:
        decision = "PENDING_MANUAL"
    else:
        decision = "STOP"
    result = {
        "schemaVersion": 1,
        "release": "R7-B",
        "decision": decision,
        "automatic": automatic,
        "manual": manual,
        "singleImeManual": single_ime_manual,
        "limitations": [] if manual_pass else [
            "Fcitx5 Cangjie and Pinyin headed evidence not collected"
        ],
        "pass": automatic_pass and (manual_pass or single_ime_pass),
    }
    output = args.evidence_root / "input-summary.json"
    write_json(output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if decision == "STOP" or (args.require_manual and not result["pass"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
