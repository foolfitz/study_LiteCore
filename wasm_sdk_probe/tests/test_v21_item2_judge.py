"""tools/judge_v21_shakedown_item2.py: its self-test (every red, refusal and non-vacuity case the item-2 arms
name, ARMS-item2.md §4 and §9) as a unit test, and the cases where a judge must not give a verdict at all.
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import judge_v21_shakedown_item2 as judge  # noqa: E402


class Judge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pop = json.loads(judge.POPULATION.read_text(encoding="utf-8"))

    def test_self_test_passes(self):
        with redirect_stdout(io.StringIO()) as out:
            code = judge.self_test(verbose=False)
        self.assertEqual(code, 0, out.getvalue())

    def test_every_criterion_has_a_red_case(self):
        covered = {criterion for _, criterion, _, _ in judge.red_cases()}
        self.assertEqual(covered, set(judge.CRITERIA))

    def test_a_directory_with_one_browser_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = judge.synthetic(self.pop)
            Path(tmp, "report-chrome.json").write_text(json.dumps(report), encoding="utf-8")
            code, lines = judge.judge_dir(Path(tmp), judge.EXPECT_PAGE, self.pop, report["populationSha256"])
        self.assertEqual(code, 1)
        self.assertIn("firefox: 0 reports (exactly one required)", lines)

    def test_two_browsers_all_pass_is_a_pass_and_a_smoke_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            for browser in ("chrome", "firefox"):
                report = judge.synthetic(self.pop, browser=browser)
                Path(tmp, f"report-{browser}.json").write_text(json.dumps(report), encoding="utf-8")
            code, lines = judge.judge_dir(Path(tmp), judge.EXPECT_PAGE, self.pop, report["populationSha256"])
            self.assertEqual((code, lines[-1]), (0, "VERDICT PASS"))
            smoke = judge.synthetic(self.pop, browser="chrome")
            smoke["smoke"] = True
            Path(tmp, "report-chrome.json").write_text(json.dumps(smoke), encoding="utf-8")
            code, lines = judge.judge_dir(Path(tmp), judge.EXPECT_PAGE, self.pop, report["populationSha256"])
        self.assertEqual(code, 1)
        self.assertTrue(any("smoke report is never judged" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
