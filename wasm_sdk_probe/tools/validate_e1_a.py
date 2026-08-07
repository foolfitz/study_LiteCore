#!/usr/bin/env python3
"""Aggregate E1-A browser evidence into the spec checkpoint decision."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from e1_support import inspect_odt, write_json


CORE_ACTIONS = {
    "move-character-left", "move-character-right", "move-line-up", "move-line-down",
    "move-line-home", "move-line-end", "delete-backward", "delete-forward",
    "insert-paragraph-break", "insert-line-break", "undo", "redo",
}
ESSENTIAL_ACTIONS = {
    "move-character-left", "move-character-right",
    "delete-backward", "delete-forward",
    "insert-paragraph-break", "insert-line-break", "undo",
}
MUTATION_ACTIONS = {
    "delete-backward", "delete-forward", "insert-paragraph-break", "insert-line-break",
    "undo", "redo",
}
FORMAT_ACTIONS = {
    "set-bold", "set-italic", "set-paragraph-body", "set-paragraph-heading",
    "set-list-none", "set-list-unordered", "set-list-ordered",
}


def latest_result(base: Path) -> Path:
    attempts = sorted(path for path in base.glob("attempt-*") if path.is_dir())
    directory = attempts[-1] if attempts else base
    return directory / "result.json"


def forward_delete_unknown_evidence(results: list[dict[str, Any]]) -> dict[str, Any]:
    checks = []
    for browser in ("chrome", "firefox"):
        candidates = [
            item for item in results
            if item.get("browser") == browser
            and item.get("fixture") == "plain-grapheme"
        ]
        result = candidates[-1] if candidates else {}
        attempts = [
            item for item in result.get("operations", [])
            if item.get("name") == "delete-forward"
            and item.get("expectation") == "positive"
        ]
        timeout = bool(
            attempts
            and attempts[0].get("status") == "failed"
            and (attempts[0].get("error") or {}).get("code") == "TIMEOUT"
        )
        output_path = Path((result.get("output") or {}).get("path", ""))
        inspected = inspect_odt(output_path) if output_path.is_file() else {"text": ""}
        text = inspected.get("text", "")
        mutation_observed = (
            "E1-PLAIN-STARTBCASCII" in text
            and "E1-PLAIN-STARTABCASCII" not in text
        )
        checks.append({
            "browser": browser,
            "timeoutAfterDispatch": timeout,
            "savedOutput": str(output_path),
            "savedMutationObserved": mutation_observed,
            "pass": timeout and mutation_observed,
        })
    return {
        "reason": "FORWARD_DELETE_MUTATION_OUTCOME_UNKNOWN",
        "checks": checks,
        "confirmed": len(checks) == 2 and all(item["pass"] for item in checks),
    }


def action_safe(entries: list[dict[str, Any]], action: str) -> bool:
    matching = [item for item in entries if item.get("name") == action and item.get("expectation") == "positive"]
    if len(matching) < 3 or any(item.get("status") != "passed" for item in matching):
        return False
    for item in matching:
        result = item.get("result") or {}
        completion = result.get("completion", "")
        if action in MUTATION_ACTIONS | FORMAT_ACTIONS:
            if (
                result.get("changed") is not True
                or result.get("revision") != result.get("beforeRevision", -2) + 1
                or completion in {"mutation-outcome-unknown", "dispatch-return-only"}
            ):
                return False
        elif completion == "dispatch-return-only":
            return False
    return True


def decide(results: list[dict[str, Any]], roundtrip_pass: bool) -> dict[str, Any]:
    by_browser: dict[str, list[dict[str, Any]]] = defaultdict(list)
    typed_state = True
    no_raw = True
    negatives = True
    for result in results:
        browser = result["browser"]
        by_browser[browser].extend(result.get("operations", []))
        typed_state = typed_state and bool(result.get("events"))
        no_raw = no_raw and result.get("rawCallbackExposed") is False
        negative = {item.get("name"): item for item in result.get("operations", []) if item.get("family") == "negative"}
        negatives = negatives and all(
            negative.get(name, {}).get("status") == "passed"
            for name in ("stale-revision", "unsupported-action")
        )
    action_matrix = {
        browser: {
            action: action_safe(entries, action)
            for action in sorted(CORE_ACTIONS | FORMAT_ACTIONS)
        }
        for browser, entries in by_browser.items()
    }
    browsers_complete = set(action_matrix) == {"chrome", "firefox"}
    core = browsers_complete and all(
        action_matrix[browser][action]
        for browser in ("chrome", "firefox")
        for action in CORE_ACTIONS
    )
    essential = browsers_complete and all(
        action_matrix[browser][action]
        for browser in ("chrome", "firefox")
        for action in ESSENTIAL_ACTIONS
    )
    format_core = browsers_complete and all(
        action_matrix[browser][action]
        for browser in ("chrome", "firefox")
        for action in ("set-bold", "set-italic")
    )
    paragraph_or_list = browsers_complete and all(
        any(action_matrix[browser][action] for action in (
            "set-paragraph-body", "set-paragraph-heading",
            "set-list-none", "set-list-unordered", "set-list-ordered",
        ))
        for browser in ("chrome", "firefox")
    )
    safety = typed_state and no_raw and negatives and roundtrip_pass
    if core and format_core and paragraph_or_list and safety:
        decision = "GO_TO_E1_B"
    elif essential and safety:
        decision = "PARTIAL_GO_TO_E1_B"
    else:
        decision = "STOP_OR_RESCOPE"
    return {
        "actionMatrix": action_matrix,
        "properties": {
            "typedEditorState": typed_state,
            "noRawCallbackExposed": no_raw,
            "typedNegativeCases": negatives,
            "roundtrip": roundtrip_pass,
            "coreActions": core,
            "essentialActions": essential,
            "boldItalic": format_core,
            "paragraphOrList": paragraph_or_list,
        },
        "decision": decision,
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--browser-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "discovery" / "browser",
    )
    parser.add_argument(
        "--roundtrip", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "discovery" / "roundtrip" / "summary.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "discovery" / "summary.json",
    )
    args = parser.parse_args()
    results = []
    missing = []
    for browser in ("chrome", "firefox"):
        for fixture in ("plain-grapheme", "multi-paragraph", "styled-list", "table-boundary", "r7-t2-styled"):
            path = latest_result(args.browser_root / browser / fixture)
            if path.is_file():
                results.append(json.loads(path.read_text(encoding="utf-8")))
            else:
                missing.append(str(path))
    roundtrip = json.loads(args.roundtrip.read_text(encoding="utf-8")) if args.roundtrip.is_file() else {"pass": False}
    decision = decide(results, roundtrip.get("pass") is True)
    early_stop = forward_delete_unknown_evidence(results)
    stopped_early = early_stop["confirmed"] and bool(missing)
    result = {
        "schemaVersion": 1,
        "release": "E1-A-editing-discovery",
        "results": len(results),
        "missing": missing,
        "earlyStopEvidence": early_stop,
        **decision,
        "stoppedEarly": stopped_early,
        "complete": (len(results) == 10 and not missing) or stopped_early,
    }
    write_json(args.output.resolve(), result)
    print(json.dumps({"output": str(args.output.resolve()), "complete": result["complete"], "decision": result["decision"]}))
    if not result["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
