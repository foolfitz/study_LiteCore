from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from validate_e1_b import ESSENTIAL_OPERATIONS, FORMAT_OPERATIONS, decide  # noqa: E402


def browser(name: str, formats: bool = True):
    passed = ESSENTIAL_OPERATIONS | (FORMAT_OPERATIONS if formats else set())
    return {
        "browserName": name,
        "operations": [{"name": operation, "status": "passed"} for operation in passed],
        "states": [{"state": "ready"}, {"state": "busy"}, {"state": "ready"}],
    }


class E1BDecisionTest(unittest.TestCase):
    def test_full_safe_matrix_goes_to_e1_c(self) -> None:
        result = decide([browser("chrome"), browser("firefox")], True, True, True)
        self.assertEqual(result["decision"], "GO_TO_E1_C")

    def test_missing_format_is_partial_go(self) -> None:
        result = decide([
            browser("chrome", formats=False), browser("firefox", formats=False)
        ], True, True, True)
        self.assertEqual(result["decision"], "PARTIAL_GO_TO_E1_C")

    def test_escape_hatch_or_recovery_failure_stops(self) -> None:
        result = decide([browser("chrome"), browser("firefox")], False, True, True)
        self.assertEqual(result["decision"], "STOP_OR_RESCOPE")
        failed = browser("firefox")
        failed["states"].append({"state": "restart-required"})
        result = decide([browser("chrome"), failed], True, True, True)
        self.assertEqual(result["decision"], "STOP_OR_RESCOPE")


if __name__ == "__main__":
    unittest.main()
