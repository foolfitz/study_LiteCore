from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from run_r8_discovery import profile_temp_parent  # noqa: E402
from validate_r8_a import browser_contract, decide  # noqa: E402


def topology(name: str) -> dict:
    return {
        "topology": name,
        "initial": {
            "pass": True,
            "faults": {"pass": True},
            "cache": {"pass": True},
            "storage": {"before": {"available": True}},
        },
        "restart": {
            "pass": True,
            "cache": {"pass": True},
        },
        "headers": {"pass": True},
        "pass": True,
    }


class R8ADecisionTest(unittest.TestCase):
    def test_persistent_profile_parent_is_under_project_dist(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r8-profile-parent-test-") as temporary:
            project = Path(temporary) / "wasm_sdk_probe"
            expected = project / "dist" / "r8"
            self.assertEqual(profile_temp_parent(project), expected)
            self.assertTrue(expected.is_dir())

    def test_complete_browser_contract_requires_t0_t1_and_restart(self) -> None:
        summary = {"topologies": [topology("t0"), topology("t1")], "pass": True}
        result = browser_contract(summary)
        self.assertTrue(result["pass"], result["checks"])

    def test_missing_restart_fails_browser_contract(self) -> None:
        t1 = topology("t1")
        t1["restart"]["cache"]["pass"] = False
        t1["restart"]["pass"] = False
        summary = {"topologies": [topology("t0"), t1], "pass": False}
        result = browser_contract(summary)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["restart"])
        self.assertFalse(result["checks"]["largeCache"])

    def test_all_checks_with_environment_gap_is_partial_go(self) -> None:
        decision = decide(
            {"manifest": True, "chrome": True, "firefox": True},
            {"brotli": "unavailable-local-cli", "quota": "not-executed-browser-policy"},
        )
        self.assertEqual(decision, "PARTIAL_GO")

    def test_all_checks_without_gaps_is_go(self) -> None:
        self.assertEqual(decide({"all": True}, {"gap": "none"}), "GO")

    def test_failed_check_is_stop_even_when_gaps_are_known(self) -> None:
        self.assertEqual(
            decide({"manifest": True, "firefox": False}, {"brotli": "unavailable-local-cli"}),
            "STOP",
        )


if __name__ == "__main__":
    unittest.main()
