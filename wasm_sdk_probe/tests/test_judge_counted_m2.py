"""The counted-M2 reader (`tools/judge_counted_m2.py`), offline: its green case and its red cases.

No counted run exists (2026-10-08), so THE GREEN CASE IS SYNTHETIC, built in a temporary directory from real
v18 reports (none of them edited in place):
  counted / counted-control  <- v18/merge/shakedown-B.json / control-B.json: F01/F02 and the text-frame M2-0
                                dropped, round 1 copied as round 3 (records and kept documents);
  m2-1b                      <- v18/m2-shakedown/m2-1b-B.json, unchanged but for identity;
  m2-4                       <- v18/finding-118/p4-m2-4-fixed-B.json with EVERY PRESS'S TWO LATENCIES REPLACED
                                (40 / 140.5 ms): no real report is green under spec 31.2;
  red                        <- v18/m2-shakedown/red-B.json.
Identity is normalised on every copy (one runner = this tree's runner file, one binding equal to what was
served, mode, counted), and `m.BINDING` is replaced by that binding for the duration of the tests (a TEST
AUTHORITY: nothing is bound in the tree).  Fields the runner gained in the review of 2026-10-08 are added to
the copies: `toastsAtEnd` (the save confirmations only) and an empty `<stem>.stderr.txt` per report.
The real red cases of spec 31.2 are the five v18 M2-4 reports, put in unedited but for identity.

    python3 -m unittest tests.test_judge_counted_m2
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import judge_counted_m2 as j  # noqa: E402
import run_merge_wasm_shakedown as m  # noqa: E402

V18 = m.HERE.parent / "findings/evidence/v18"
PROFILE = "e2-editor-v18"
BINDING = {key: f"{i:x}" * 64 for i, key in enumerate(m.BOUND_KEYS, start=1)}
BINDING["eshapeSha256"] = j.sha256(m.ESHAPE)
RED_BOUND = {**BINDING, "wasmSha256": "8" * 64, "workerSha256": "9" * 64, "pageSha256": "a" * 64}
SAVED = "已存出 11.9 KB"
FRAME = {"F01", "F02"}
SPEC_31_2_RED = ("m2-shakedown/m2-4-{}.json", "diag-117/m2-4-chrome.json", "finding-118/p4-m2-4-fixed-{}.json")


def identity(report: dict, kind: str) -> dict:
    report = copy.deepcopy(report)
    red = kind == "red"
    report.update({"mode": j.MODES[kind], "runner": j.RUNNER_SHA, "counted": True, "binding": BINDING,
                   "bound": RED_BOUND if red else BINDING, "caseList": "tool", "frameCell": False,
                   "ownerDocument": False, "control": kind == "control", "instrumented": kind != "control"})
    report["candidate"] = {**report["candidate"], "profile": j.RED_PROFILE if red else PROFILE,
                           "pageSha256": (RED_BOUND if red else BINDING)["pageSha256"]}
    for case in report["cases"]:
        if "toastWindow" not in case and "toastsAtEnd" not in case:
            case["toastsAtEnd"] = [SAVED] * (1 if kind == "m2-4" else 2)
    return report


def put(target: Path, name: str, report: dict, docs: Path) -> None:
    (target / f"{name}.json").write_text(json.dumps(report, ensure_ascii=False))
    (target / f"{name}.stderr.txt").write_text("")
    shutil.copytree(docs, target / f"{name}.docs")


def tool_run(source: Path, kind: str, target: Path, name: str) -> None:
    """A shakedown of the tool list (2 rounds) as the counted run's 3."""
    report = json.loads(source.read_text())
    report["cases"] = [c for c in report["cases"] if c["case"] not in FRAME]
    report["cases"] += [{**copy.deepcopy(c), "round": 3} for c in report["cases"] if c["round"] == 1]
    report["m2_0"] = [r for r in report["m2_0"] if r["fixture"] != "text-frame"]
    report["rounds"] = 3
    put(target, name, identity(report, kind), source.with_suffix(".docs"))
    docs = target / f"{name}.docs"
    for path in list(docs.glob("*-r1-*.odt")):
        shutil.copy(path, docs / path.name.replace("-r1-", "-r3-"))
    for path in docs.glob("*text-frame*"):
        path.unlink()
    for path in docs.glob("F0*"):
        path.unlink()
    # The reopened documents' content hash, which the runner records since the review of 2026-10-08.
    path = target / f"{name}.json"
    report = json.loads(path.read_text())
    for case in report["cases"]:
        kept = docs / f"{case['case']}-r{case['round']}-reopened.odt"
        if "reopenedDocument" in case and kept.is_file():
            case["reopenedDocument"]["sha"] = m.odt_parts(kept.read_bytes())["sha"]
    path.write_text(json.dumps(report, ensure_ascii=False))


def synthetic_m2_4(report: dict) -> dict:
    report = copy.deepcopy(report)
    for press in report["cases"][0]["presses"]:
        press.update({"keyToUndoMs": 40, "keyToResponseMs": 140.5})
    return report


def build(target: Path, browser: str) -> None:
    tool_run(V18 / f"merge/shakedown-{browser}.json", "counted", target, f"counted-{browser}")
    tool_run(V18 / f"merge/control-{browser}.json", "control", target, f"counted-control-{browser}")
    for kind, source, edit in (("m2-1b", f"m2-shakedown/m2-1b-{browser}.json", None),
                               ("m2-4", f"finding-118/p4-m2-4-fixed-{browser}.json", synthetic_m2_4),
                               ("red", f"m2-shakedown/red-{browser}.json", None)):
        report = json.loads((V18 / source).read_text())
        docs = (V18 / source).with_suffix(".docs")
        for case in report["cases"]:
            kept = docs / f"{case['case']}-r{case['round']}-reopened.odt"
            if "reopenedDocument" in case and kept.is_file():
                case["reopenedDocument"]["sha"] = m.odt_parts(kept.read_bytes())["sha"]
        put(target, f"{kind}-{browser}", identity(edit(report) if edit else report, kind), docs)


class Reader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding, m.BINDING = m.BINDING, dict(BINDING)        # the test authority (module docstring)
        cls.tmp = tempfile.TemporaryDirectory(prefix="judge-counted-m2-")
        cls.green = Path(cls.tmp.name) / "green"
        cls.green.mkdir()
        for browser in j.BROWSERS:
            build(cls.green, browser)

    @classmethod
    def tearDownClass(cls):
        m.BINDING = cls.binding
        cls.tmp.cleanup()

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name))
        shutil.copytree(self.green, self.dir, dirs_exist_ok=True)

    def edit(self, name: str, change) -> None:
        path = self.dir / f"{name}.json"
        report = json.loads(path.read_text())
        change(report)
        path.write_text(json.dumps(report, ensure_ascii=False))

    def record(self, report: dict, case: str, round_no: int) -> dict:
        return next(c for c in report["cases"] if c["case"] == case and c["round"] == round_no)

    def judge(self, browsers=("chrome",), uncounted=False) -> tuple[int, str, list]:
        code, lines = j.judge(self.dir, PROFILE, list(browsers), uncounted)
        return code, lines[-1], lines

    def verdict(self, lines: list, name: str) -> list[str]:
        return [line.split()[1] if line.split()[1] != "NOT" else "NOT DONE" for line in lines
                if line.startswith(f"{name} ")]

    # ---- green ----------------------------------------------------------------------------------------------
    def test_green_both_browsers(self):
        code, last, lines = self.judge(j.BROWSERS)
        self.assertEqual(code, 0, "\n".join(lines))
        self.assertTrue(last.startswith(f"VERDICT PASS (chrome, firefox; runner {j.RUNNER_SHA}"), last)
        text = "\n".join(lines)
        self.assertIn("60 completions (expected 60)", text)          # non-vacuity, printed
        self.assertIn("'after-key': [63, 63], 'follow': [63, 63], 'reopened': [15, 15]", text)

    def test_green_uncounted_is_never_0(self):
        code, last, _ = self.judge(j.BROWSERS, uncounted=True)
        self.assertEqual((code, last), (4, "VERDICT PASS (NOT A COUNTED VERDICT: uncounted)"))

    # ---- review 2026-10-08: identity ------------------------------------------------------------------------
    def test_one_browser_is_never_a_counted_pass(self):
        # opus B1, codex B1.
        code, last, _ = self.judge(("chrome",))
        self.assertEqual((code, last), (4, "VERDICT PASS (NOT A COUNTED VERDICT: browsers ['chrome'])"))

    def test_red_firefox_ran_another_candidate(self):
        # codex B2: each browser consistent with itself, the two not with each other.
        other = {**BINDING, "wasmSha256": "e" * 64, "sessionSha256": "d" * 64}
        for kind in ("counted", "counted-control", "m2-1b", "m2-4", "red"):
            def swap(report):
                report["binding"] = other
                report["bound"] = {**other, **({k: RED_BOUND[k] for k in m.PROFILE_BOUND} if kind == "red" else {})}
            self.edit(f"{kind}-firefox", swap)
        code, last, _ = self.judge(j.BROWSERS)
        self.assertEqual((code, last), (3, "VERDICT NOT DONE: ['all identity']"))

    def test_nothing_is_counted_while_nothing_is_committed(self):
        # opus B2: the reports' own binding is not an authority.
        saved, m.BINDING = m.BINDING, None
        try:
            self.assertEqual(self.judge(j.BROWSERS)[:2], (3, "VERDICT NOT DONE: ['all identity']"))
        finally:
            m.BINDING = saved

    def test_red_a_binding_of_another_schema(self):
        # codex B3.
        for name in [f"{k}-{b}" for k in ("counted", "counted-control", "m2-1b", "m2-4", "red") for b in j.BROWSERS]:
            self.edit(name, lambda r: r.update(binding={"irrelevant": 1}, bound={"irrelevant": 1}))
        saved, m.BINDING = m.BINDING, {"irrelevant": 1}
        try:
            self.assertEqual(self.judge(j.BROWSERS)[:2], (3, "VERDICT NOT DONE: ['all identity']"))
        finally:
            m.BINDING = saved

    def test_another_runner_file(self):
        for name in [f"{k}-{b}" for k in ("counted", "counted-control", "m2-1b", "m2-4", "red") for b in j.BROWSERS]:
            self.edit(name, lambda r: r.update(runner="0123456789abcdef"))
        self.assertEqual(self.judge(j.BROWSERS)[:2], (3, "VERDICT NOT DONE: ['all identity']"))

    def test_a_missing_stderr_is_not_done_when_counted(self):
        (self.dir / "m2-4-chrome.stderr.txt").unlink()
        self.assertEqual(self.judge()[:2], (3, "VERDICT NOT DONE: ['chrome identity']"))
        self.assertEqual(self.judge(uncounted=True)[0], 4)

    # ---- spec 31.2's red cases: the five v18 M2-4 reports, unedited but for identity --------------------------
    def test_red_the_v18_m2_4_reports(self):
        sources = [s.format(b) for s in SPEC_31_2_RED for b in j.BROWSERS if "{}" in s or b == "chrome"]
        self.assertEqual(len(set(sources)), 5)
        for source in sorted(set(sources)):
            browser = "firefox" if "firefox" in source else "chrome"
            with self.subTest(source=source):
                shutil.rmtree(self.dir / f"m2-4-{browser}.docs")
                put(self.dir, f"m2-4-{browser}", identity(json.loads((V18 / source).read_text()), "m2-4"),
                    (V18 / source).with_suffix(".docs"))
                code, last, lines = self.judge([browser])
                self.assertEqual(code, 1, "\n".join(lines))
                self.assertEqual(last, f"VERDICT FAIL: ['{browser} M2-4']")
                line = next(x for x in lines if x.startswith("M2-4 "))
                self.assertIn("'slow': 102", line)
                self.assertIn("'latency'", line)

    # ---- M2-1 -----------------------------------------------------------------------------------------------
    def test_red_another_comment(self):
        self.edit("counted-chrome", lambda r: self.record(r, "C02", 2)["keyUndo"].update(comment="Delete “x”"))
        code, last, _ = self.judge()
        self.assertEqual((code, last), (1, "VERDICT FAIL: ['chrome M2-1']"))

    def test_red_a_restore_press(self):
        self.edit("counted-chrome", lambda r: self.record(r, "I02", 3)["keyUndo"].update(restorePresses=2))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-1']"))

    def test_red_the_select_arm_as_the_document(self):
        # Spec 10.2's comparator red: C03's native select arm is not its key arm.  Recorded as the runner
        # would have recorded it, so only the comparison can catch it.
        select = (m.EVIDENCE / "r0c/round-20261006T144628Z/docs/r1-C03-select.odt").read_bytes()
        key = m.EVIDENCE / "r0c/round-20261006T144628Z/docs/r1-C03-key.odt"
        self.assertNotEqual(m.odt_parts(select)["content"], m.odt_parts(key.read_bytes())["content"])
        (self.dir / "counted-chrome.docs/C03-r2-after-key.odt").write_bytes(select)
        self.edit("counted-chrome", lambda r: self.record(r, "C03", 2).update(
            afterKeyDocument=m.compare(select, key, False)))
        code, last, lines = self.judge()
        # The paired control sees the other text as well (spec 22.3 compares paragraph text).
        self.assertEqual((code, last), (1, "VERDICT FAIL: ['chrome M2-1', 'chrome control']"))
        self.assertIn("afterKeyBytes", next(x for x in lines if x.startswith("M2-1 ")))

    def test_a_kept_document_the_report_did_not_compare_is_not_done(self):
        select = (m.EVIDENCE / "r0c/round-20261006T144628Z/docs/r1-C03-select.odt").read_bytes()
        for side in ("counted-chrome", "counted-control-chrome"):     # both, so the pair stays equal
            (self.dir / f"{side}.docs/C03-r2-after-key.odt").write_bytes(select)
        self.assertEqual(self.judge()[:2], (3, "VERDICT NOT DONE: ['chrome M2-1']"))

    def test_red_a_refused_merge(self):
        def refuse(report):
            record = self.record(report, "C08", 1)
            record.update(outcome="refused", stage="key-deadline", keyPosted=True, keyUndo=None,
                          generation=["1", "2"])
        self.edit("counted-chrome", refuse)
        code, last, _ = self.judge()
        # M2-1 fails on the record; M2-2 has 59 completions and one record with no engine number.
        self.assertEqual((code, last),
                         (1, "VERDICT FAIL: ['chrome M2-1', 'chrome control']; NOT DONE: ['chrome M2-2']"))

    def test_red_the_barrier_merged_by_key(self):
        self.edit("counted-chrome", lambda r: self.record(r, "G01", 3).update(outcome="verified-key-undo"))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome barrier']"))

    def test_a_missing_record_is_not_done(self):
        # From both sides: with the control's record kept, the pair's order differs too (a FAIL).
        for side in ("counted-chrome", "counted-control-chrome"):
            self.edit(side, lambda r: r["cases"].remove(self.record(r, "D12", 2)))
        code, last, _ = self.judge()
        self.assertEqual(code, 3)
        self.assertIn("chrome M2-1", last)

    def test_an_extra_record_is_not_done(self):
        for side, source in (("counted-chrome", "shakedown"), ("counted-control-chrome", "control")):
            extra = json.loads((V18 / f"merge/{source}-chrome.json").read_text())["cases"]
            self.edit(side, lambda r: r["cases"].append(next(c for c in extra if c["case"] == "F01")))
        code, last, _ = self.judge()
        self.assertEqual(code, 3, last)
        for name in ("M2-1", "M2-3", "barrier", "control"):
            self.assertIn(f"chrome {name}", last)

    # ---- M2-2 -----------------------------------------------------------------------------------------------
    def test_red_one_completion_at_the_bound(self):
        for field in ("engine", "runner"):
            with self.subTest(field=field):
                self.setUp()
                def slow(report):
                    record = self.record(report, "D04", 3)
                    if field == "engine":
                        record["keyUndo"]["keyToUndoMs"] = j.BOUND_MS
                    else:
                        record["keyToResponseMs"] = float(j.BOUND_MS)
                self.edit("counted-chrome", slow)
                self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-2']"))

    def test_a_missing_number_is_not_done(self):
        self.edit("counted-chrome", lambda r: self.record(r, "C01", 1).update(keyToResponseMs=None))
        self.assertEqual(self.judge()[:2], (3, "VERDICT NOT DONE: ['chrome M2-2']"))

    def test_red_m2_1b_slow(self):
        self.edit("m2-1b-chrome", lambda r: r["cases"][7]["keyUndo"].update(keyToUndoMs=1200))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-2']"))

    # ---- M2-3 -----------------------------------------------------------------------------------------------
    def test_red_another_stage(self):
        self.edit("counted-chrome", lambda r: self.record(r, "C15", 1).update(stage="anchor-mismatch"))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-3']"))

    def test_red_the_marker_lost(self):
        original = (m.EVIDENCE / "r0c/round-20261006T144628Z/docs/original.odt").read_bytes()
        (self.dir / "counted-chrome.docs/C29-r2-reopened.odt").write_bytes(original)
        self.edit("counted-chrome", lambda r: self.record(r, "C29", 2)["reopenedDocument"].update(
            sha=m.odt_parts(original)["sha"]))                  # as the runner would have recorded it
        code, last, lines = self.judge()
        self.assertEqual((code, last), (1, "VERDICT FAIL: ['chrome M2-3', 'chrome control']"))
        self.assertIn("markerOnce", next(x for x in lines if x.startswith("M2-3 ")))

    def test_red_a_third_toast(self):
        self.edit("counted-chrome", lambda r: self.record(r, "C17", 3)["toastWindow"]["toasts"].append("重繪失敗"))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-3', 'chrome control']"))

    def test_red_not_changed_after_the_key_went_out(self):
        def say(report):
            toasts = self.record(report, "C16", 2)["toastWindow"]["toasts"]
            toasts[1] = toasts[1] + "文件沒有被改動。"
        self.edit("counted-chrome", say)
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-3', 'chrome control']"))

    # ---- M2-1b ----------------------------------------------------------------------------------------------
    def test_red_m2_1b_reopened(self):
        def refuse(report):
            report["cases"][3].update(outcome="refused", generation=["1", "2"])
        self.edit("m2-1b-chrome", refuse)
        code, last, _ = self.judge()
        self.assertEqual(code, 1)
        self.assertIn("chrome M2-1b", last)

    def test_m2_1b_short_is_not_done(self):
        self.edit("m2-1b-chrome", lambda r: r["cases"].pop())
        code, last, _ = self.judge()
        self.assertEqual(code, 3)
        self.assertIn("chrome M2-1b", last)

    # ---- M2-4 (synthetic green) -----------------------------------------------------------------------------
    def test_red_m2_4_one_press_at_the_bound(self):
        self.edit("m2-4-chrome", lambda r: r["cases"][0]["presses"][54].update(keyToUndoMs=j.BOUND_MS))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-4']"))

    def test_m2_4_a_missing_number_is_not_done(self):
        self.edit("m2-4-chrome", lambda r: r["cases"][0]["presses"][0].update(keyToResponseMs=None))
        self.assertEqual(self.judge()[:2], (3, "VERDICT NOT DONE: ['chrome M2-4']"))

    def test_red_m2_4_limit_never_reached(self):
        def cap(report):
            for press in report["cases"][0]["presses"]:
                press["actionsAfter"] = min(press["actionsAfter"], 99)
        self.edit("m2-4-chrome", cap)
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-4']"))

    def test_red_m2_4_a_toast(self):
        self.edit("m2-4-chrome", lambda r: r["cases"][0].update(toasts=["重繪失敗"]))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-4']"))

    def test_red_m2_4_stopped_early(self):
        self.edit("m2-4-chrome", lambda r: r["cases"][0].update(presses=r["cases"][0]["presses"][:104]))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-4']"))

    # ---- M2-0, red case, control ----------------------------------------------------------------------------
    def test_red_m2_0(self):
        after = (self.dir / "counted-chrome.docs/C01-r1-after-key.odt").read_bytes()
        reference = m.FIXTURES["boundaries"][1] / "docs/original.odt"
        (self.dir / "counted-chrome.docs/m2-0-boundaries.odt").write_bytes(after)
        def record(report):
            next(r for r in report["m2_0"] if r["fixture"] == "boundaries")["document"] = m.compare(
                after, reference, False)
        self.edit("counted-chrome", record)
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-0']"))

    def test_red_the_red_case_merged(self):
        self.edit("red-chrome", lambda r: r["cases"][1].update(outcome="verified-key-undo", generation=["1", "1"]))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome red']"))

    def test_red_a_red_case_never_placed(self):
        self.edit("red-chrome", lambda r: r["cases"][0].update(outcome="placement-mismatch",
                                                               place={"ok": False}))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome red']"))

    def test_red_the_control_saw_another_document(self):
        # C08's text, not C01's: C01 (Delete) and C02 (Backspace) merge the same two paragraphs.
        other = (self.dir / "counted-control-chrome.docs/C08-r2-follow.odt").read_bytes()
        (self.dir / "counted-control-chrome.docs/C02-r2-follow.odt").write_bytes(other)
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome control']"))

    # ---- review 2026-10-08: clauses -------------------------------------------------------------------------
    def test_a_reopened_document_the_report_did_not_save_is_not_done(self):
        # opus NOTE 6: the same paragraph count, another content.
        original = (m.EVIDENCE / "r0c/round-20261006T144628Z/docs/original.odt").read_bytes()
        for side in ("counted-chrome", "counted-control-chrome"):
            (self.dir / f"{side}.docs/C29-r2-reopened.odt").write_bytes(original)
        self.assertEqual(self.judge()[:2], (3, "VERDICT NOT DONE: ['chrome M2-3']"))

    def test_red_a_toast_after_the_typed_z(self):
        # codex B5.  The control did not see it, so the pair is red as well.
        self.edit("counted-chrome", lambda r: self.record(r, "C09", 2).update(
            toastsAtEnd=[SAVED, "重繪失敗：TILE_NOT_PAINTED", SAVED]))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-1', 'chrome control']"))

    def test_a_report_without_the_end_toasts_is_not_done(self):
        for side in ("counted-chrome", "counted-control-chrome"):
            self.edit(side, lambda r: self.record(r, "C09", 2).pop("toastsAtEnd"))
        self.assertEqual(self.judge()[:2], (3, "VERDICT NOT DONE: ['chrome M2-1']"))

    def test_red_m2_4_a_toast_at_the_save(self):
        self.edit("m2-4-chrome", lambda r: r["cases"][0].update(toastsAtEnd=["重繪失敗：X", SAVED]))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-4']"))

    def test_red_the_reopen_pair(self):
        # codex B8: two end sentences on both sides, so the pair agrees and only the clause can see it.
        def two_ends(report):
            window = self.record(report, "C29", 1)["toastWindow"]
            window["toasts"] = [window["toasts"][1], window["toasts"][1]]
        for side in ("counted-chrome", "counted-control-chrome"):
            self.edit(side, two_ends)
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-3']"))

    def test_red_a_second_reopen_after_the_window(self):
        # opus S5, on both sides.
        for side in ("counted-chrome", "counted-control-chrome"):
            self.edit(side, lambda r: self.record(r, "C30", 3)["generation"].__setitem__(
                1, str(int(self.record(r, "C30", 3)["generation"][0]) + 2)))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-3']"))

    def test_red_the_control_reopened_from_elsewhere(self):
        # codex B4: the same end generation, another transition; and a window that did not close.
        for change in (lambda c: c.update(generation=[c["generation"][1], c["generation"][1]]),
                       lambda c: c["toastWindow"].update(closed=False)):
            with self.subTest():
                self.setUp()
                self.edit("counted-control-chrome", lambda r: change(self.record(r, "C15", 2)))
                self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome control']"))

    def test_red_the_control_in_another_order(self):
        self.edit("counted-control-chrome", lambda r: r["cases"].reverse())
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome control']"))

    def test_red_a_negative_latency(self):
        # codex S2.
        self.edit("counted-chrome", lambda r: self.record(r, "D08", 1).update(keyToResponseMs=-500.0))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-2']"))

    def test_another_m2_4_reference_is_not_done(self):
        # opus S6: the native document under build/ is pinned by its content hash.
        saved, j.LIMIT_REFERENCE_SHA16 = j.LIMIT_REFERENCE_SHA16, "0" * 16
        try:
            code, last, _ = self.judge()
        finally:
            j.LIMIT_REFERENCE_SHA16 = saved
        self.assertEqual(code, 3)
        self.assertIn("chrome reports", last)

    # ---- identity -------------------------------------------------------------------------------------------
    def test_not_bound_is_not_done(self):
        for name, change in (("m2-1b-chrome", lambda r: r.update(counted=False)),
                             ("m2-4-chrome", lambda r: r["bound"].update(wasmSha256="0" * 64)),
                             ("red-chrome", lambda r: r["bound"].update(pageSourceSha256="0" * 64)),
                             ("counted-chrome", lambda r: r.update(runner="another0000000")),
                             ("counted-control-chrome", lambda r: r.update(binding=None))):
            with self.subTest(name=name):
                self.setUp()
                self.edit(name, change)
                code, last, _ = self.judge()
                self.assertEqual(code, 3, last)
                self.assertIn("identity", last)

    def test_a_missing_report_leaves_what_it_carries_not_done(self):
        (self.dir / "m2-4-chrome.json").unlink()
        code, last, _ = self.judge()
        self.assertEqual(code, 3)
        for name in ("reports", "M2-0", "M2-4"):
            self.assertIn(f"chrome {name}", last)

    def test_the_runner_teardown_error_is_not_done(self):
        self.edit("counted-chrome", lambda r: r.update(observerAtEnd={"error": "ConnectionClosedError"}))
        self.assertEqual(self.judge()[:2], (3, "VERDICT NOT DONE: ['chrome identity']"))


if __name__ == "__main__":
    unittest.main()
