"""tools/judge_v21_shakedown_item1.py: its self-test (every red, refusal and non-vacuity case of ARMS-item1.md
and spec §12.3) as a unit test, and the places where the item-1 runner and judge must agree.

No browser: the runner is imported, never run.
"""
import argparse
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import judge_v21_shakedown_item1 as judge  # noqa: E402
import run_v21_shakedown_item1 as runner  # noqa: E402


class Judge(unittest.TestCase):
    def test_self_test_passes(self):
        with redirect_stdout(io.StringIO()) as out:
            code = judge.self_test(verbose=False)
        self.assertEqual(code, 0, out.getvalue())

    def test_every_criterion_has_a_red_case(self):
        _, docs = judge.synthetic()
        covered = {criterion for _, criterion, _, _ in judge.mutations(docs)}
        self.assertEqual(covered, set(judge.CRITERIA))

    def test_spec_12_3_clauses_have_both_kinds_of_red(self):
        """D14 and E0 each have a FAIL case and a NOT_ESTABLISHED case; D11b's dirty half has both."""
        _, docs = judge.synthetic()
        kinds = {}
        for name, criterion, expected, _ in judge.mutations(docs):
            key = "D11b dirty" if name.startswith("D11b dirty") else criterion
            kinds.setdefault(key, set()).add(expected)
        for key in ("D14", "E0", "D11b dirty"):
            self.assertEqual(kinds.get(key), {judge.FAIL, judge.NE}, key)


class RunnerAndJudgeAgree(unittest.TestCase):
    def test_d6_is_recorded_as_not_runnable_without_a_browser(self):
        args = argparse.Namespace(rounds=3, only="", d8="a,b,c,d,e")
        result = runner.run_arm(None, "d6", args, None)
        self.assertEqual(result, {"arm": "d6", "rounds": [], "notRun": judge.D6_NOT_RUNNABLE})

    def test_d14_shape(self):
        self.assertIn("d14", runner.ARMS)
        self.assertEqual(runner.D14_FIXTURES, judge.D14_FIXTURES)
        self.assertLess(runner.D14_PLAN_MS, judge.D14_WINDOW_MS)

    def test_the_entry_read_carries_what_e0_reads(self):
        for field in ("exists", "hidden", "visibleOpeners", "controlVisible"):
            self.assertIn(field, runner.ENTRY_READ)


if __name__ == "__main__":
    unittest.main()
