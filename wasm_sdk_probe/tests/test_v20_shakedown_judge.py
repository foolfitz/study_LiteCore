"""The v20 shakedown judge's red cases (findings/evidence/link-batch/v20-shakedown/ARMS.md), offline.

Every mutation in `judge_v20_shakedown.mutations()` must turn its arm's verdict to the named one,
the synthetic PASS set must pass, P2-c's reader must read a lone size change as ESTABLISHED and an
empty trace as "not run", and the runner's span rule must agree with the native mixed-page string.

    python3 -m unittest tests.test_v20_shakedown_judge
"""
from __future__ import annotations

import copy
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import judge_v20_shakedown as judge  # noqa: E402
import run_v20_shakedown as runner  # noqa: E402


class SelfTest(unittest.TestCase):
    def test_every_red_case_goes_red(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = judge.self_test(verbose=True)
        self.assertEqual(code, 0, buffer.getvalue())

    def test_synthetic_set_passes_and_a_missing_browser_fails(self):
        base = [judge.synthetic_report("chrome"), judge.synthetic_report("firefox")]
        code, lines = judge.judge_reports(copy.deepcopy(base))
        self.assertEqual(code, 0, lines[-1])
        code, lines = judge.judge_reports([judge.synthetic_report("chrome")])
        self.assertEqual(code, 1)
        self.assertTrue(any(line.startswith("[firefox] p1-60: MISSING") for line in lines))

    def test_a_report_about_another_page_is_not_read(self):
        base = [judge.synthetic_report("chrome"), judge.synthetic_report("firefox")]
        code, lines = judge.judge_reports(base, expect_page="0" * 64)
        self.assertEqual(code, 1)
        # Nothing of either report is judged: every bracketed line is the refusal or a MISSING cell.
        self.assertTrue(all(("is not read" in line or line.endswith(": MISSING"))
                            for line in lines if line.startswith("[")), lines)
        self.assertEqual(sum(1 for line in lines if "is not read" in line), 2)

    def test_an_arm_without_a_rule_fails(self):
        base = [judge.synthetic_report("chrome"), judge.synthetic_report("firefox")]
        base[0]["results"]["made-up-arm"] = {"ok": True}
        code, lines = judge.judge_reports(base)
        self.assertEqual(code, 1)
        self.assertTrue(any("made-up-arm: no rule for an arm the runner declares" in line for line in lines))

    def test_parse_rects_refuses_a_torn_string(self):
        self.assertIsNone(runner.parse_rects("284, 284, 11906; 284, 17406, 16838, 11906"))
        self.assertEqual(runner.parse_rects(""), [])
        self.assertEqual(len(runner.parse_rects("284, 284, 11906, 16838; 284, 17406, 16838, 11906")), 2)

    def test_region_of_measures_the_view_on_paper(self):
        geometry = {"deskTop": 100.0, "deskBottom": 900.0, "paperTop": -500.0, "paperBottom": 10000.0,
                    "paperHeight": 10500.0}
        region = runner.region_of(geometry, 12474, 1027604)
        self.assertEqual(region["x"], 0)
        self.assertEqual(region["width"], 12474)
        self.assertAlmostEqual(region["y"], 600 * 1027604 / 10500, places=3)
        self.assertAlmostEqual(region["height"], 800 * 1027604 / 10500, places=3)
        self.assertIsNone(runner.region_of({**geometry, "deskBottom": 50.0}, 12474, 1027604))


if __name__ == "__main__":
    unittest.main()
