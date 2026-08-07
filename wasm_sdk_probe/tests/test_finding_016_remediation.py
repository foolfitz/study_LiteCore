from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from validate_finding_016_remediation import decide  # noqa: E402


def browser_result(browser: str, fixture: str):
    actions = {
        "plain-grapheme": ("delete-backward", "delete-forward"),
        "multi-paragraph": ("insert-paragraph-break", "insert-line-break"),
        "table-boundary": (),
    }[fixture]
    operations = []
    for action in actions:
        for repetition in range(1, 4):
            operations.append({
                "family": "remediation-positive",
                "name": action,
                "repetition": repetition,
                "status": "passed",
                "result": {
                    "changed": True,
                    "completion": "uno-command-result",
                },
            })
    if fixture == "plain-grapheme":
        for action in ("delete-backward", "delete-forward"):
            for repetition in range(1, 4):
                operations.append({
                    "family": "remediation-boundary",
                    "name": action,
                    "repetition": repetition,
                    "status": "passed",
                    "error": {"code": "EDITOR_BOUNDARY_UNSUPPORTED"},
                })
    return {
        "browser": browser,
        "fixture": fixture,
        "mode": "finding-016-remediation",
        "complete": True,
        "pass": True,
        "rawCallbackExposed": False,
        "operations": operations,
    }


class Finding016RemediationTest(unittest.TestCase):
    def test_two_browser_matrix_supports_remediation(self) -> None:
        results = [
            browser_result(browser, fixture)
            for browser in ("chrome", "firefox")
            for fixture in ("plain-grapheme", "multi-paragraph", "table-boundary")
        ]
        self.assertEqual(decide(results)["decision"], "REMEDIATION_SUPPORTED")

    def test_unknown_delete_outcome_stops(self) -> None:
        results = [
            browser_result(browser, fixture)
            for browser in ("chrome", "firefox")
            for fixture in ("plain-grapheme", "multi-paragraph", "table-boundary")
        ]
        target = next(
            item for item in results[0]["operations"]
            if item["family"] == "remediation-positive"
        )
        target["result"]["changed"] = None
        self.assertEqual(decide(results)["decision"], "STOP_OR_RESCOPE")


if __name__ == "__main__":
    unittest.main()
