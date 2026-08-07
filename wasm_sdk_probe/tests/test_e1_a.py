from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from validate_e1_a import CORE_ACTIONS, FORMAT_ACTIONS, decide  # noqa: E402


def result(browser: str, safe_format: bool = True):
    operations = []
    for action in sorted(CORE_ACTIONS | FORMAT_ACTIONS):
        for repetition in range(1, 4):
            mutation = action in {"delete-backward", "delete-forward", "insert-paragraph-break", "insert-line-break", "undo", "redo"}
            operations.append({
                "family": "format" if action in FORMAT_ACTIONS else "mutation",
                "name": action,
                "repetition": repetition,
                "expectation": "positive",
                "status": "passed",
                "result": {
                    "beforeRevision": repetition,
                    "revision": repetition + 1,
                    "changed": True if mutation else (True if safe_format else None),
                    "completion": "uno-command-result" if mutation or action in FORMAT_ACTIONS else "documented-callback-during-dispatch",
                },
            })
    for name in ("stale-revision", "unsupported-action"):
        operations.append({"family": "negative", "name": name, "status": "passed"})
    return {
        "browser": browser,
        "events": [{"event": "editor-state"}],
        "rawCallbackExposed": False,
        "operations": operations,
    }


class E1DecisionTest(unittest.TestCase):
    def test_complete_safe_matrix_goes_to_e1_b(self) -> None:
        decision = decide([result("chrome"), result("firefox")], True)
        self.assertEqual(decision["decision"], "GO_TO_E1_B")

    def test_unknown_mutation_stops(self) -> None:
        values = [result("chrome"), result("firefox")]
        target = next(item for item in values[0]["operations"] if item["name"] == "delete-forward")
        target["result"] = {"changed": None, "completion": "mutation-outcome-unknown"}
        self.assertEqual(decide(values, True)["decision"], "STOP_OR_RESCOPE")

    def test_safe_essential_matrix_with_reduced_navigation_is_partial_go(self) -> None:
        values = [result("chrome"), result("firefox")]
        reduced = {
            "move-line-up", "move-line-down", "move-line-home", "move-line-end",
            "redo",
            "set-paragraph-body", "set-paragraph-heading",
            "set-list-none", "set-list-unordered", "set-list-ordered",
        }
        for value in values:
            value["operations"] = [
                item for item in value["operations"] if item["name"] not in reduced
            ]
        decision = decide(values, True)
        self.assertTrue(decision["properties"]["essentialActions"])
        self.assertFalse(decision["properties"]["coreActions"])
        self.assertEqual(decision["decision"], "PARTIAL_GO_TO_E1_B")


if __name__ == "__main__":
    unittest.main()
