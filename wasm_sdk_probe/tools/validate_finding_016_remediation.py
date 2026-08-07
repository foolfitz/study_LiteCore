#!/usr/bin/env python3
"""Validate the isolated Finding 016 fixed-command remediation evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from e1_support import write_json


POSITIVE_REQUIREMENTS = {
    "plain-grapheme": {"delete-backward", "delete-forward"},
    "multi-paragraph": {"insert-paragraph-break", "insert-line-break"},
}


def _latest_result(directory: Path) -> dict[str, Any] | None:
    attempts = sorted(directory.glob("attempt-*/result.json"))
    path = attempts[-1] if attempts else directory / "result.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def decide(results: list[dict[str, Any]]) -> dict[str, Any]:
    indexed = {(item.get("browser"), item.get("fixture")): item for item in results}
    checks: dict[str, Any] = {}
    complete = True
    for browser in ("chrome", "firefox"):
        for fixture, actions in POSITIVE_REQUIREMENTS.items():
            result = indexed.get((browser, fixture))
            key = f"{browser}:{fixture}"
            if not result:
                checks[key] = {"pass": False, "reason": "missing result"}
                complete = False
                continue
            operations = result.get("operations", [])
            action_checks = {}
            for action in sorted(actions):
                matches = [
                    item for item in operations
                    if item.get("family") == "remediation-positive"
                    and item.get("name") == action
                ]
                passed = (
                    len(matches) == 3
                    and all(item.get("status") == "passed" for item in matches)
                    and all(item.get("result", {}).get("changed") is True for item in matches)
                    and all(
                        item.get("result", {}).get("completion")
                        == "uno-command-result"
                        for item in matches
                    )
                )
                action_checks[action] = {"count": len(matches), "pass": passed}
                complete = complete and passed
            result_pass = (
                result.get("complete") is True
                and result.get("pass") is True
                and result.get("rawCallbackExposed") is False
                and result.get("mode") == "finding-016-remediation"
                and all(value["pass"] for value in action_checks.values())
            )
            checks[key] = {"pass": result_pass, "actions": action_checks}
            complete = complete and result_pass

        plain = indexed.get((browser, "plain-grapheme"), {})
        boundaries = [
            item for item in plain.get("operations", [])
            if item.get("family") == "remediation-boundary"
        ]
        boundary_pass = (
            len(boundaries) == 6
            and all(item.get("status") == "passed" for item in boundaries)
            and all(
                item.get("error", {}).get("code") == "EDITOR_BOUNDARY_UNSUPPORTED"
                for item in boundaries
            )
        )
        checks[f"{browser}:boundary"] = {
            "pass": boundary_pass,
            "count": len(boundaries),
        }
        complete = complete and boundary_pass

    return {
        "schemaVersion": 1,
        "finding": "016",
        "complete": complete,
        "checks": checks,
        "decision": "REMEDIATION_SUPPORTED" if complete else "STOP_OR_RESCOPE",
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--browser-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "016" / "remediation" / "browser",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=workspace / "findings" / "evidence" / "016" / "remediation" / "summary.json",
    )
    args = parser.parse_args()
    results = []
    for browser in ("chrome", "firefox"):
        for fixture in ("plain-grapheme", "multi-paragraph", "table-boundary"):
            value = _latest_result(args.browser_root / browser / fixture)
            if value:
                results.append(value)
    summary = decide(results)
    write_json(args.output, summary)
    print(json.dumps(summary, ensure_ascii=False))
    if not summary["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
