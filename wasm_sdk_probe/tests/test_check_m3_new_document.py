"""check_m3_new_document.py offline (SPEC-M3-new-document section 4; the section 34.3 review of 2026-10-14):
the committed 0.2.19 report is green under this tree's scorer, every red case goes red ON ITS OWN RULE, each fix
of the review has the red case the old code passed, the count's engine binding is what decides on a later host,
and the owner's settings are never restored from a value that was not read.

The committed report is bound to host 0.2.19 (`afbaf3c`).  The module's bindings are replaced by the report's
own for the duration of a test (a TEST AUTHORITY, as tests/test_judge_counted_m2.py does with `m.BINDING`), so
these tests survive the count's rebinding to a later host (0.2.23 since 2026-10-15, task 10-15c P3; the two
tests of the "not written" default set that state themselves).  Nothing here talks to ddev, a browser or the host.

    python3 -m unittest tests.test_check_m3_new_document
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_m3_new_document as cm  # noqa: E402

REPORT = Path(__file__).resolve().parents[2] / "findings" / "evidence" / "new-document" / "runs" / "2026-10-14T035226Z.json"
BASE = json.loads(REPORT.read_text())
NEXT_HOST = {"hostCommit": "1234567", "hostVersion": "0.2.20", "buildId": "a" * 16, "servedPage": "9" * 64}


def run(report: dict, arm: str, browser: str = "chrome") -> dict:
    return next(r for r in report["runs"] if r["arm"] == arm and r["browser"] == browser)


def bound_to(report: dict, **more):
    """The module's bindings set to this report's host (and `more`), for one test."""
    static = report["hostStatic"]
    values = {"HOST_COMMIT": static["hostCommit"], "HOST_VERSION": static["hostVersion"],
              "MANIFEST_SHA256": static["blankManifestSha256"], **more}
    return mock.patch.multiple(cm, **values)


def next_host(report: dict) -> dict:
    """The committed report as a 0.2.20 count would record it: host moved, engine v20, a host diff
    outside 0.2.19's allowed paths.  Nothing else changes."""
    later = copy.deepcopy(report)
    later["hostStatic"].update(NEXT_HOST, changedOutsideAllowed=["js/litecore-editor.js"])
    return later


def strict(report: dict) -> dict:
    return cm.score(report, strict=True)


def quiet_red_cases(path: Path) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cm.red_cases(path)
    return code, out.getvalue()


class TheCommittedReport(unittest.TestCase):
    def test_green_and_every_red_case_red_on_its_rule(self):
        with bound_to(BASE):
            self.assertTrue(strict(BASE)["works"])
            code, text = quiet_red_cases(REPORT)
        self.assertEqual(code, 0, text)
        self.assertEqual(len(cm.RED_CASES), 39)
        self.assertEqual(text.count("\nRED  "), 39, text)
        self.assertNotIn("MISS", text)
        self.assertNotIn("SKIP", text)

    def test_a_case_that_fires_only_a_neighbour_is_a_miss(self):
        # Before the review `red_cases` asked only `not works`: a case named for N2 that in fact
        # trips N3 satisfied it, so a deleted N2 clause left the self-test green (opus Q5).
        neighbour = ("N2-fires-only-n3", lambda r: run(r, "EN")["create"]["host"]["fetched"].update(sha256="1" * 64))
        with bound_to(BASE), mock.patch.object(cm, "RED_CASES", [neighbour]):
            code, text = quiet_red_cases(REPORT)
        self.assertEqual(code, 1)
        self.assertIn("MISS  N2-fires-only-n3", text)

    def test_rules_fired_reads_cells_and_static_problems(self):
        result = {"runs": {"TW/chrome": {"N2": ["x"], "N3": ["y"]}, "EN/chrome": "PASS"},
                  "problems": ["N9 binding engineBuildId not written", "N7(b)'s red case is not recorded as red",
                               "binding hostCommit 0 != 1", "N9/N10 blank/ is not what the generator makes"]}
        self.assertEqual(cm.rules_fired(result), {"N2", "N3", "N9", "N7"})


class TheReviewFixes(unittest.TestCase):
    """Each mutation read WORKS under the tool at 3b818514 (shown by the scorer copied from
    `git show` in review/DISPOSITION.md); here it must name the rule."""

    def n(self, report: dict, cell: str) -> list[str]:
        with bound_to(BASE):
            result = strict(report)
        self.assertFalse(result["works"])
        return sorted(result["runs"][cell]) if result["runs"][cell] != "PASS" else []

    def test_an_offer_that_was_not_read_is_n5_not_not_offered(self):
        for a11y in ({"offers": None, "text": None, "reason": None, "deferred": None}, {"offers": "garbage", "text": ""}, None):
            r = copy.deepcopy(BASE)
            if a11y is None:
                del run(r, "TW")["reopen"]["a11y"]
            else:
                run(r, "TW")["reopen"]["a11y"] = a11y
            self.assertEqual(self.n(r, "TW/chrome"), ["N5"], a11y)
            with bound_to(BASE):
                self.assertTrue(strict(r)["n5ParagraphTextHalf"]["TW/chrome"].startswith("unknown"))

    def test_a_generation_that_was_never_read_is_n4(self):
        r = copy.deepcopy(BASE)
        for k in run(r, "EN", "firefox")["keys"]:
            k["genBefore"] = k["genAfter"] = None
        self.assertEqual(self.n(r, "EN/firefox"), ["N4"])

    def test_the_saved_document_is_exactly_the_marker(self):
        cached = copy.deepcopy(BASE)
        run(cached, "TW")["savedFile"]["paragraphs"] = ["zqxOLD"]          # the engine opened a cached, non-blank document
        self.assertEqual(self.n(cached, "TW/chrome"), ["N4"])
        extra = copy.deepcopy(BASE)
        run(extra, "EN", "firefox")["savedFile"]["paragraphs"] = ["zqx", "UNEXPECTED TEXT"]   # markCount still 1
        self.assertEqual(self.n(extra, "EN/firefox"), ["N4"])

    def test_the_reopen_lands_on_the_created_file(self):
        r = copy.deepcopy(BASE)
        for x in r["runs"]:   # a save by temp file + MOVE: new fileid at the same path, reopened by name
            new = str(int(x["createdFile"]["fileid"]) + 50000)
            x["savedFile"]["fileid"] = new
            x["reopen"]["landed"] = x["reopen"]["landed"].split("fileId=")[0] + "fileId=" + new
            x["reopen"]["host"]["file"]["id"] = int(new)
        for cell in ("TW/chrome", "TW/firefox", "EN/chrome", "EN/firefox"):
            self.assertEqual(self.n(r, cell), ["N5"], cell)

    def test_a_share_that_allows_creating_is_not_n8(self):
        r = copy.deepcopy(BASE)
        r["readOnly"].update(sharePermissions=31, otherSees="SRGDNVCK")   # the 403 still there
        with bound_to(BASE):
            problems = strict(r)["problems"]
        self.assertEqual([p[:9] for p in problems], ["N8 create"], problems)

    def test_no_runs_or_stopped_is_never_works(self):
        for stopped in (None, "kwallet locked"):
            r = copy.deepcopy(BASE)
            r.update(label="shakedown", runs=[])
            if stopped:
                r["stopped"] = stopped
            result = cm.score(r, strict=False)
            self.assertFalse(result["works"])
            self.assertTrue(any(p.startswith("no complete run") for p in result["problems"]), result)
        self.assertIn("NOT_ESTABLISHED -", cm.one_line(cm.score(dict(BASE, label="shakedown", runs=[]), strict=False)))

    def test_a_restore_whose_occ_failed_is_not_restored_even_if_ok_says_so(self):
        r = copy.deepcopy(BASE)
        r["settingsRestored"]["locale"].update(exit=1)   # readback None == original None; the old scorer trusted `ok`
        with bound_to(BASE):
            problems = strict(r)["problems"]
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("admin settings not restored"), problems)


class TheNextHost(unittest.TestCase):
    """Q3: what of N9 is 0.2.19's acceptance and what the count binds."""

    def test_the_delta_clauses_apply_only_to_0_2_19(self):
        moved = copy.deepcopy(BASE)
        moved["hostStatic"]["buildId"] = "0" * 16
        with bound_to(BASE):
            self.assertTrue(any(p.startswith("N9 engine package") for p in strict(moved)["problems"]))
        later = next_host(BASE)
        loose = cm.score(later, strict=False)["problems"]
        self.assertEqual([p for p in loose if "engine package" in p or "outside the allowed" in p], [], loose)
        # The "not written" state (the module's default until the binding step of 2026-10-15 wrote 0.2.23's).
        with bound_to(later, ENGINE_BUILD_ID=None, PAGE_SHA256=None):
            problems = strict(later)["problems"]
        self.assertEqual(problems, ["N9 binding engineBuildId not written", "N9 binding pageSha256 not written"])

    def test_the_count_binds_the_candidate_engine(self):
        later = next_host(BASE)
        with bound_to(later, ENGINE_BUILD_ID=NEXT_HOST["buildId"], PAGE_SHA256=NEXT_HOST["servedPage"]):
            self.assertTrue(strict(later)["works"])
            other = copy.deepcopy(later)
            other["hostStatic"]["buildId"] = "b" * 16
            self.assertEqual(strict(other)["problems"], [f"N9 binding engineBuildId {'b' * 16} != {'a' * 16}"])

    def test_moving_the_control_values_changes_nothing_on_a_later_host(self):
        # The tautology both seats warned of: CONTROL_HOST_COMMIT at HEAD makes the host diff empty and
        # "unchanged since 0.2.18" would read as "equals the candidate".  On a 0.2.20 report those
        # constants are not consulted at all: the count still refuses until its own binding is written.
        later = next_host(BASE)
        with bound_to(later, CONTROL_BUILD_ID=NEXT_HOST["buildId"], CONTROL_PAGE_SHA256=NEXT_HOST["servedPage"],
                      CONTROL_HOST_COMMIT=NEXT_HOST["hostCommit"], ENGINE_BUILD_ID=None, PAGE_SHA256=None):
            self.assertEqual(strict(later)["problems"], ["N9 binding engineBuildId not written", "N9 binding pageSha256 not written"])

    def test_red_cases_hold_on_a_rebound_host(self):
        later = next_host(BASE)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "counted.json"
            path.write_text(json.dumps(later, ensure_ascii=False))
            with bound_to(later, ENGINE_BUILD_ID=NEXT_HOST["buildId"], PAGE_SHA256=NEXT_HOST["servedPage"]):
                code, text = quiet_red_cases(path)
        self.assertEqual(code, 0, text)
        self.assertIn("RED   N9-other-engine", text)
        self.assertIn("RED   N9-page-moved", text)
        self.assertIn("binding engineBuildId", text)


class TheSettings(unittest.TestCase):
    """`user_setting` with a mocked occ: 'not set' is never the same value as a failed read."""

    @staticmethod
    def fake_occ(script):
        """script: list of (returncode, stdout) in call order, or a callable(args) -> (rc, out)."""
        calls = []

        def occ(root, *args):
            calls.append(args)
            rc, out = script(args) if callable(script) else script.pop(0)
            if isinstance(rc, BaseException):
                raise rc
            return subprocess.CompletedProcess(["ddev", "occ", *args], rc, out, "" if rc == 0 else "boom")
        occ.calls = calls
        return occ

    def test_a_failed_first_read_refuses_rather_than_deleting_later(self):
        # The old reader returned None for any non-zero exit (check_m3_new_document.py:139 at 3b818514), so a
        # ddev hiccup on the first read became "not set" and the restore deleted the owner's core/lang.
        occ = self.fake_occ([(1, "")])
        with mock.patch.object(cm, "occ", occ):
            with self.assertRaises(cm.SettingReadError):
                cm.read_settings(Path("/nowhere"))
        self.assertEqual(len(occ.calls), 1)
        self.assertIn("--default-value", occ.calls[0])

    def test_unset_is_none_and_set_is_the_value(self):
        occ = self.fake_occ([(0, cm.UNSET + "\n"), (0, "zh_TW\n")])
        with mock.patch.object(cm, "occ", occ):
            self.assertEqual(cm.read_settings(Path("/nowhere")), {"lang": None, "locale": "zh_TW"})

    def test_restore_ok_needs_exit_zero_and_a_successful_readback(self):
        original = {"lang": "zh_TW", "locale": None}
        # (a) codex Q6: the delete fails and so does its readback -- the old `ok` compared None == None.
        occ = self.fake_occ([(0, ""), (0, "zh_TW\n"), (1, ""), (1, "")])
        with mock.patch.object(cm, "occ", occ):
            restored = cm.restore_settings(Path("/nowhere"), original)
        self.assertTrue(restored["lang"]["ok"])
        self.assertFalse(restored["locale"]["ok"])
        self.assertIn("readError", restored["locale"])
        self.assertFalse(restored["ok"])
        # (b) the delete succeeds, the readback says "not set": restored.
        occ = self.fake_occ([(0, ""), (0, "zh_TW\n"), (0, ""), (0, cm.UNSET + "\n")])
        with mock.patch.object(cm, "occ", occ):
            self.assertTrue(cm.restore_settings(Path("/nowhere"), original)["ok"])
        # (c) the set exits 0 but the readback disagrees: not restored.
        occ = self.fake_occ([(0, ""), (0, "en\n"), (0, ""), (0, cm.UNSET + "\n")])
        with mock.patch.object(cm, "occ", occ):
            restored = cm.restore_settings(Path("/nowhere"), original)
        self.assertFalse(restored["lang"]["ok"])
        self.assertFalse(restored["ok"])

    def test_an_error_on_one_key_still_restores_the_other(self):
        original = {"lang": "zh_TW", "locale": "en_US"}
        boom = subprocess.TimeoutExpired(["ddev"], 300)
        occ = self.fake_occ([(boom, ""), (0, ""), (0, "en_US\n")])
        with mock.patch.object(cm, "occ", occ):
            restored = cm.restore_settings(Path("/nowhere"), original)
        self.assertFalse(restored["lang"]["ok"])
        self.assertIn("TimeoutExpired", restored["lang"]["error"])
        self.assertTrue(restored["locale"]["ok"])
        self.assertFalse(restored["ok"])
        self.assertEqual(len(occ.calls), 3)

    def test_other_runners_sees_a_second_instance_but_not_itself(self):
        lines = ["100 python3 tools/check_m3_new_document.py --label counted",
                 "99 bash -c cd x && python3 tools/check_m3_new_document.py --label counted",
                 "200 python3 tools/check_m3_new_document.py --label shakedown",
                 "300 python3 tools/run_merge_wasm_shakedown.py",
                 "400 pgrep -af probe_|check_m3"]
        others = cm.other_runners(lines, (100, 99))
        self.assertEqual([line.split(" ", 1)[0] for line in others], ["200", "300"])


if __name__ == "__main__":
    unittest.main()
