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

C's keying (2026-10-15, task 10-15c P1) is a second TEST AUTHORITY: the judge reads whether the profile carries C
from `PROFILES/<profile>/probe.wasm` and requires every non-red report to have bound those bytes, so the green case
serves a synthetic engine file (`FAKE_WASM`, no C) under a temporary `PROFILES`, and the binding's `wasmSha256` is
that file's sha256.  The C cases swap in `FAKE_WASM_C` (the same bytes plus the fragment the engine emits) and
rebind every report to it.  The witnesses below (`V19Witness`, `V20Witness`) are keyed on the real served engines.

    python3 -m unittest tests.test_judge_counted_m2
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import judge_counted_m2 as j  # noqa: E402
import run_merge_wasm_shakedown as m  # noqa: E402

V18 = m.HERE.parent / "findings/evidence/v18"
PROFILE = "e2-editor-v18"
# The synthetic engines (module docstring): without C, and with the fragment the engine emits for C's completion.
FAKE_WASM = b"\0asm synthetic e2-editor-v18 engine for the judge's tests: no C\n"
FAKE_WASM_C = FAKE_WASM + m.BOUNDARY_NOOP_FRAGMENT + b"\n"
assert m.BOUNDARY_NOOP_FRAGMENT not in FAKE_WASM
BINDING = {key: f"{i:x}" * 64 for i, key in enumerate(m.BOUND_KEYS, start=1)}
BINDING["eshapeSha256"] = j.sha256(m.ESHAPE)
BINDING["wasmSha256"] = hashlib.sha256(FAKE_WASM).hexdigest()
BINDING_C = {**BINDING, "wasmSha256": hashlib.sha256(FAKE_WASM_C).hexdigest()}
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
        # C's keying authority: the synthetic engine the binding names, under a PROFILES of the test's own.
        cls.profiles, j.PROFILES = j.PROFILES, Path(cls.tmp.name) / "profiles"
        (j.PROFILES / PROFILE).mkdir(parents=True)
        cls.wasm = j.PROFILES / PROFILE / "probe.wasm"

    @classmethod
    def tearDownClass(cls):
        m.BINDING = cls.binding
        j.PROFILES = cls.profiles
        cls.tmp.cleanup()

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name))
        shutil.copytree(self.green, self.dir, dirs_exist_ok=True)
        self.wasm.write_bytes(FAKE_WASM)
        m.BINDING = dict(BINDING)

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
        # codex B2: each browser consistent with itself, the two not with each other.  The other candidate's
        # engine is the same bytes (another wasm stops at C's keying first: test_a_report_bound_to_other_bytes).
        other = {**BINDING, "workerSha256": "e" * 64, "sessionSha256": "d" * 64}
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
            # A binding of another schema names no engine either, so each browser stops at C's keying as well.
            self.assertEqual(self.judge(j.BROWSERS)[:2],
                             (3, "VERDICT NOT DONE: ['chrome reports', 'firefox reports', 'all identity']"))
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

    # ---- C (2026-10-15, task 10-15c P1): the keying, and the no-op's clauses ----------------------------------
    def m2_3_line(self, lines: list) -> str:
        return next(x for x in lines if x.startswith("M2-3 "))

    def test_the_keying_names_the_served_engine(self):
        _, _, lines = self.judge()
        self.assertIn(f"keyed on {self.wasm} ({BINDING['wasmSha256'][:16]}): C not declared, "
                      "nothing-selected expects refused", lines[1])

    def test_a_report_bound_to_other_bytes_is_not_done(self):
        # The expectation was read from one file; a report that ran other bytes is not judged by it.
        self.edit("counted-chrome", lambda r: r["bound"].update(wasmSha256="f" * 64))
        code, last, lines = self.judge()
        self.assertEqual(code, 3, last)
        self.assertIn("chrome reports", last)
        self.assertIn("is not the keyed", "\n".join(lines))
        self.assertNotIn("M2-3       PASS", "\n".join(lines))        # nothing judged, not "the rest passed"

    def test_no_engine_to_read_is_not_done(self):
        self.wasm.unlink()
        code, last, _ = self.judge()
        self.assertEqual(code, 3)
        self.assertIn("cannot be read", last)

    def declare_c(self, browsers=("chrome",)) -> None:
        """The profile under test now carries C: the engine file and every report's binding say so."""
        self.wasm.write_bytes(FAKE_WASM_C)
        m.BINDING = dict(BINDING_C)
        for name in [f"{k}-{b}" for k in ("counted", "counted-control", "m2-1b", "m2-4", "red") for b in browsers]:
            def rebind(report, red=name.startswith("red")):
                report["binding"] = BINDING_C
                report["bound"] = {**RED_BOUND, **{k: v for k, v in BINDING_C.items() if k not in m.PROFILE_BOUND}} \
                    if red else BINDING_C
            self.edit(name, rebind)

    def test_red_a_refusal_judged_under_c(self):
        # R2 of 7e6c9acd: v18's C29/C30 refused and reopened; on a profile that declares C that is red.
        self.declare_c()
        _, _, lines = self.judge()
        self.assertIn("keyed on", lines[1])
        self.assertIn("C declared, nothing-selected expects verified-boundary-noop", lines[1])
        line = self.m2_3_line(lines)
        self.assertTrue(line.split()[1] == "FAIL", line)
        self.assertEqual(line.count("('FAIL', 'C29 r"), 3, line)
        self.assertEqual(line.count("('FAIL', 'C30 r"), 3, line)
        self.assertIn("'outcome'", line)

    def as_noop(self, name: str, browser: str) -> None:
        """C29/C30 of a v18 report re-recorded as the runner since 7e6c9acd records a no-op (synthetic, like the
        green M2-4): no reopen, generation and revision unchanged, no toast, the caret where the placement left
        it, and the document saved after the key -- the same bytes the refusal path kept after its reopen,
        original + marker -- as `<case>-r<n>-after-key.odt` with its content named in `afterKeyDocument`."""
        docs = self.dir / f"{name}.docs"

        def convert(report):
            for record in report["cases"]:
                if record["case"] not in ("C29", "C30"):
                    continue
                placed = record["place"]
                x, y, w, h = placed["engineCaret"]
                record.update(outcome=m.BOUNDARY_NOOP, generation=[record["generation"][0]] * 2, toasts=[],
                              afterKey={**record["afterKey"], "revision": record["beforeKey"]["revision"]},
                              caretAfterKey={"caret": {"x": x, "y": y, "width": w, "height": h},
                                             "generation": placed["caretGeneration"]})
                for key in ("toastWindow", "stage", "reopenedDocument"):
                    record.pop(key, None)
                stem = f"{record['case']}-r{record['round']}"
                (docs / f"{stem}-reopened.odt").rename(docs / f"{stem}-after-key.odt")
                parts = m.odt_parts((docs / f"{stem}-after-key.odt").read_bytes())
                record["afterKeyDocument"] = {"saved": True, "paragraphs": len(parts["paragraphs"]),
                                              "sha": parts["sha"]}
        self.edit(name, convert)

    def green_under_c(self, browsers=j.BROWSERS) -> None:
        self.declare_c(browsers)
        for browser in browsers:
            self.as_noop(f"counted-{browser}", browser)
            self.as_noop(f"counted-control-{browser}", browser)

    def test_green_a_no_op_under_c(self):
        self.green_under_c()
        code, last, lines = self.judge(j.BROWSERS)
        self.assertEqual(code, 0, "\n".join(lines))
        self.assertTrue(last.startswith("VERDICT PASS (chrome, firefox"), last)
        text = "\n".join(lines)
        self.assertIn("'after-key': [69, 69], 'follow': [63, 63], 'reopened': [9, 9]", text)   # the kept counts follow C
        self.assertIn("15 records (expected 15", self.m2_3_line(lines))

    def test_red_a_no_op_whose_caret_moved(self):
        self.green_under_c(("chrome",))
        self.edit("counted-chrome", lambda r: self.record(r, "C30", 2)["caretAfterKey"]["caret"].update(x=1))
        code, last, lines = self.judge()
        self.assertEqual((code, last), (1, "VERDICT FAIL: ['chrome M2-3']"))
        self.assertIn("'caretUnchanged'", self.m2_3_line(lines))

    def test_red_a_no_op_from_another_worker(self):
        self.green_under_c(("chrome",))
        self.edit("counted-chrome", lambda r: self.record(r, "C29", 3)["caretAfterKey"].update(generation=99))
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-3']"))

    def test_red_a_no_op_that_changed_the_revision(self):
        self.green_under_c(("chrome",))
        self.edit("counted-chrome", lambda r: self.record(r, "C29", 1)["afterKey"].update(revision="3"))
        code, last, lines = self.judge()
        self.assertEqual((code, last), (1, "VERDICT FAIL: ['chrome M2-3']"))
        self.assertIn("'revision'", self.m2_3_line(lines))

    def test_red_a_no_op_with_a_toast(self):
        self.green_under_c(("chrome",))
        self.edit("counted-chrome", lambda r: self.record(r, "C30", 1).update(toasts=["重繪失敗"]))
        code, last, _ = self.judge()
        self.assertEqual(code, 1)
        self.assertIn("chrome M2-3", last)

    def test_red_a_no_op_that_lost_the_marker(self):
        original = (m.EVIDENCE / "r0c/round-20261006T144628Z/docs/original.odt").read_bytes()
        self.green_under_c(("chrome",))
        (self.dir / "counted-chrome.docs/C29-r2-after-key.odt").write_bytes(original)
        parts = m.odt_parts(original)
        self.edit("counted-chrome", lambda r: self.record(r, "C29", 2)["afterKeyDocument"].update(
            sha=parts["sha"], paragraphs=len(parts["paragraphs"])))   # as the runner would have recorded it
        code, last, lines = self.judge()
        self.assertEqual(code, 1)
        self.assertIn("chrome M2-3", last)
        self.assertIn("'markerOnce'", self.m2_3_line(lines))

    def test_red_a_refusal_on_a_c_profile(self):
        # The product refused where C says no-op: red on the no-op's own clauses, as 7e6c9acd's R2.
        self.green_under_c(("chrome",))
        self.edit("counted-chrome", lambda r: self.record(r, "C29", 1).update(
            outcome="refused", generation=["1", "2"]))
        # The paired control did not reopen, so the pair is red as well (as a refused merge is).
        self.assertEqual(self.judge()[:2], (1, "VERDICT FAIL: ['chrome M2-3', 'chrome control']"))

    def test_a_no_op_without_the_caret_read_is_not_done(self):
        # A runner before 7e6c9acd did not read the caret after the key: open, never inferred.
        self.green_under_c(("chrome",))
        self.edit("counted-chrome", lambda r: self.record(r, "C30", 3).pop("caretAfterKey"))
        code, last, lines = self.judge()
        self.assertEqual((code, last), (3, "VERDICT NOT DONE: ['chrome M2-3']"))
        self.assertIn("('NOT DONE', 'C30 r3', ['caretUnchanged'])", self.m2_3_line(lines))

    def test_a_no_op_document_the_report_did_not_save_is_not_done(self):
        original = (m.EVIDENCE / "r0c/round-20261006T144628Z/docs/original.odt").read_bytes()
        self.green_under_c(("chrome",))
        for side in ("counted-chrome", "counted-control-chrome"):      # both, so the pair stays equal
            (self.dir / f"{side}.docs/C29-r2-after-key.odt").write_bytes(original)
        self.assertEqual(self.judge()[:2], (3, "VERDICT NOT DONE: ['chrome M2-3']"))

    def test_under_c_everything_but_c29_and_c30_is_as_before(self):
        # The keying moves two cases' expectation and nothing else: the same v18 reports, keyed on C, are red on
        # exactly the refusal records of C29/C30, the control is open on its kept counts (a refusal keeps a
        # reopened document where a no-op keeps one after the key), and nothing else moves.
        self.declare_c(("chrome",))
        code, last, lines = self.judge()
        self.assertEqual(code, 1)
        self.assertEqual(last, "VERDICT FAIL: ['chrome M2-3']; NOT DONE: ['chrome control']", last)
        for name in ("M2-1", "barrier", "M2-2", "M2-1b", "M2-4", "red", "M2-0"):
            self.assertEqual(set(self.verdict(lines, name)), {"PASS"}, name)
        control = next(x for x in lines if x.startswith("control "))
        self.assertIn("differ 0", control)
        self.assertIn("'after-key': [63, 63], 'follow': [63, 63], 'reopened': [15, 15]} (expected "
                      "{'after-key': 69, 'follow': 63, 'reopened': 9})", control)


V19_X7 = m.HERE.parent / "findings/evidence/v19/x7-counted-m2"
WITNESS_COMMIT = "b8324a85"      # the commit that landed v19's X7 reports; the runner they ran is that commit's
RUNNER_PATH = "wasm_sdk_probe/tools/run_merge_wasm_shakedown.py"


def runner_sha_at(commit: str) -> str | None:
    """The runner file as of `commit`, materialised from git, hashed as the judge hashes the live one."""
    done = subprocess.run(["git", "-C", str(m.HERE.parent), "show", f"{commit}:{RUNNER_PATH}"],
                          capture_output=True)
    return hashlib.sha256(done.stdout).hexdigest()[:16] if done.returncode == 0 and done.stdout else None


def binding_at(commit: str) -> dict | None:
    """The runner's `BINDING` as of `commit`, read from git as a literal (the file is not imported)."""
    done = subprocess.run(["git", "-C", str(m.HERE.parent), "show", f"{commit}:{RUNNER_PATH}"],
                          capture_output=True)
    if done.returncode != 0 or not done.stdout:
        return None
    for node in ast.parse(done.stdout).body:
        target = node.target if isinstance(node, ast.AnnAssign) else (
            node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else None)
        if isinstance(target, ast.Name) and target.id == "BINDING" and node.value is not None:
            return ast.literal_eval(node.value)
    return None


@unittest.skipUnless(V19_X7.is_dir() and m.LIMIT_ROUND.is_dir(), "v19's X7 reports or R0 run 4's documents missing")
class V19Witness(unittest.TestCase):
    """Spec 34.1 (b), fable's ruling of 2026-10-08 (v19/x7-counted-m2/fable-ruling-control.md): the committed v19
    X7 reports (b8324a85) are the witness.  Judged with the COMMITTED binding, not the test authority above.  The
    reader before the fix printed `VERDICT FAIL: ['chrome control', 'firefox control']` on them (judge-output.txt
    there): the only false field was `toastsAtEnd`, `已存出 14.2 KB` against `已存出 14.3 KB`.

    Re-judged at the run's commit (the judge's docstring: "re-judging later means checking out the commit the
    counted run used").  Since 7e6c9acd the runner file has moved (73b2e9ff -> d185cb50), so the judge's
    `thisRunner` clause -- the live runner's hash against every report's `runner` -- read NOT DONE on these
    reports by construction (task 10-15c P2; the two tests below were red from 7e6c9acd to this commit).  Only the
    runner's IDENTITY is materialised here, as of WITNESS_COMMIT via git, and it must be the hash every report
    names, or the class is skipped; the functions the judge borrows from the runner are the live ones.  The judge's
    rule is not changed: a counted verdict still needs this tree's runner.  The runner's `BINDING` is materialised
    the same way (2026-10-15, SPEC-M3-link-batch §17.2): the v20 binding moved the live one off v19, so the
    `identity` clause read NOT DONE on these reports by construction, the same defect one constant over; it must
    equal the `binding` every report carries, or the class is skipped.  C's keying reads the served v19 engine
    (`dist/profiles/e2-editor-v19/probe.wasm`, bound as `1aafd4f9...`), which does not carry C, so the expectation
    is the refusal and the verdicts are as recorded (judge-output.txt there)."""

    @classmethod
    def setUpClass(cls):
        witness = runner_sha_at(WITNESS_COMMIT)
        named = {json.loads(p.read_text()).get("runner") for p in V19_X7.glob("*.json")}
        if witness is None or named != {witness}:
            raise unittest.SkipTest(f"the runner at {WITNESS_COMMIT} ({witness}) is not what the reports name {named}")
        binding = binding_at(WITNESS_COMMIT)
        carried = {json.dumps(json.loads(p.read_text()).get("binding"), sort_keys=True) for p in V19_X7.glob("*.json")}
        if binding is None or carried != {json.dumps(binding, sort_keys=True)}:
            raise unittest.SkipTest(f"the BINDING at {WITNESS_COMMIT} is not the binding the reports carry")
        cls.patch = mock.patch.object(j, "RUNNER_SHA", witness)
        cls.patch.start()
        cls.binding_patch = mock.patch.object(m, "BINDING", binding)
        cls.binding_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.binding_patch.stop()
        cls.patch.stop()

    def judge(self, directory: Path) -> tuple[int, str, list]:
        code, lines = j.judge(directory, "e2-editor-v19", list(j.BROWSERS), False)
        return code, lines[-1], lines

    def copy(self, change) -> Path:
        target = Path(tempfile.mkdtemp(prefix="judge-v19-witness-")) / "x7"
        self.addCleanup(shutil.rmtree, target.parent)
        shutil.copytree(V19_X7, target)
        change(target)
        return target

    @staticmethod
    def edit(directory: Path, name: str, case: str, round_no: int, toasts) -> None:
        path = directory / f"{name}.json"
        report = json.loads(path.read_text())
        record = next(c for c in report["cases"] if c["case"] == case and c["round"] == round_no)
        record["toastsAtEnd"] = toasts(record["toastsAtEnd"])
        path.write_text(json.dumps(report, ensure_ascii=False))

    def control_lines(self, lines: list) -> list[str]:
        return [line for line in lines if line.startswith("control ")]

    def test_a_the_witness_passes(self):
        code, last, lines = self.judge(V19_X7)
        self.assertEqual(code, 0, "\n".join(lines))
        self.assertTrue(last.startswith(f"VERDICT PASS (chrome, firefox; runner {j.RUNNER_SHA}"), last)
        chrome, firefox = self.control_lines(lines)
        self.assertIn("differ 0; 2 pairs equal up to the KB figure", chrome)
        self.assertIn("differ 0; 3 pairs equal up to the KB figure", firefox)

    def test_b_a_repaint_failure_in_one_arm_is_still_red(self):
        target = self.copy(lambda d: self.edit(d, "counted-chrome", "C03", 1,
                                               lambda t: [t[0], "重繪失敗：TILE_NOT_PAINTED", *t[1:]]))
        code, last, lines = self.judge(target)
        self.assertEqual(code, 1)
        self.assertIn("chrome control", last)
        self.assertTrue(self.control_lines(lines)[0].split()[1] == "FAIL", lines)

    def test_c_one_arm_with_a_single_save_is_red(self):
        target = self.copy(lambda d: self.edit(d, "counted-control-chrome", "C03", 1, lambda t: t[:1]))
        code, last, _ = self.judge(target)
        self.assertEqual((code, last), (1, "VERDICT FAIL: ['chrome control']"))

    def test_d_another_toast_differing_in_a_digit_is_red(self):
        def change(d):
            self.edit(d, "counted-chrome", "C01", 1, lambda t: [*t, "某訊息 1"])
            self.edit(d, "counted-control-chrome", "C01", 1, lambda t: [*t, "某訊息 2"])
        code, last, lines = self.judge(self.copy(change))
        self.assertEqual(code, 1)
        self.assertIn("chrome control", last)
        self.assertTrue(self.control_lines(lines)[0].split()[1] == "FAIL", lines)

    def test_e_the_live_runner_is_still_the_rule(self):
        # P2 fixed the test, not the judge: without the materialised identity the same reports are NOT DONE.
        with mock.patch.object(j, "RUNNER_SHA", hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()[:16]):
            code, last, _ = self.judge(V19_X7)
        self.assertEqual((code, last), (3, "VERDICT NOT DONE: ['all identity']"))


V20_MERGE = m.HERE.parent / "findings/evidence/link-batch/v20-shakedown/merge"
V20_WASM = m.HERE / "dist/profiles/e2-editor-v20/probe.wasm"
V19_WASM = m.HERE / "dist/profiles/e2-editor-v19/probe.wasm"
V20_KINDS = {"counted": "shakedown", "counted-control": "control", "m2-1b": "m2-1b", "m2-4": "m2-4"}


def v20_witness_ready() -> bool:
    if not (V20_MERGE.is_dir() and V20_WASM.is_file() and V19_WASM.is_file() and m.LIMIT_ROUND.is_dir()):
        return False
    bound = {json.loads((V20_MERGE / f"{src}-{b}.json").read_text())["bound"]["wasmSha256"]
             for src in V20_KINDS.values() for b in j.BROWSERS}
    return bound == {j.sha256(V20_WASM)}


@unittest.skipUnless(v20_witness_ready(), "part B's v20 merge reports, or the engines they and v19 bound, missing")
class V20Witness(unittest.TestCase):
    """Spec 34.4's witness for C (task 10-15c P1): part B's eight v20 shakedown reports (runner 73b2e9ff, commit
    83ea8eb8), which recorded `pass: false` on exactly the four C29/C30 records of every shakedown and control
    report because the expectation table mapped `nothing-selected` to the refusal on a profile that ships C.
    Staged under the counted file names, `--uncounted` (they are not bound and have two rounds, not three), keyed
    on the served v20 engine every one of them bound (`313b08d5...`).  Runner 73b2e9ff took the refusal path on a
    no-op, so what it recorded is mapped onto what the no-op path records -- explicitly, as the committed
    re-judge (`re-expectation/rejudge.py`) did: `toasts` <- `toastWindow.toasts`, the document saved after the
    key <- `<case>-r<n>-reopened.odt` kept as `-after-key.odt`, `afterKeyDocument` <- `reopenedDocument`;
    `caretAfterKey` stays absent, so `caretUnchanged` is not established.  Nothing else is edited."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="judge-v20-witness-")
        cls.dir = Path(cls.tmp.name) / "merge"
        cls.dir.mkdir()
        for browser in j.BROWSERS:
            for target, source in V20_KINDS.items():
                report = json.loads((V20_MERGE / f"{source}-{browser}.json").read_text())
                docs = cls.dir / f"{target}-{browser}.docs"
                shutil.copytree(V20_MERGE / f"{source}-{browser}.docs", docs)
                for record in report["cases"]:
                    if record["case"] not in ("C29", "C30") or "toastWindow" not in record:
                        continue
                    stem = f"{record['case']}-r{record['round']}"
                    record["toasts"] = record["toastWindow"]["toasts"]
                    record["afterKeyDocument"] = record["reopenedDocument"]
                    shutil.copy(docs / f"{stem}-reopened.odt", docs / f"{stem}-after-key.odt")
                (cls.dir / f"{target}-{browser}.json").write_text(json.dumps(report, ensure_ascii=False))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def judge(self, wasm: Path = V20_WASM) -> tuple[int, str, list]:
        code, lines = j.judge(self.dir, "e2-editor-v20", list(j.BROWSERS), True, wasm)
        return code, lines[-1], lines

    def m2_3_lines(self, lines: list) -> list[str]:
        return [x for x in lines if x.startswith("M2-3 ")]

    def test_a_the_four_no_op_records_are_no_longer_red(self):
        code, last, lines = self.judge()
        self.assertIn("C declared, nothing-selected expects verified-boundary-noop", lines[1])
        self.assertEqual(code, 3, last)                       # two rounds of three, no red report: not a verdict
        self.assertTrue(last.startswith("VERDICT NOT DONE"), last)
        for line in self.m2_3_lines(lines):
            self.assertNotIn("'FAIL'", line)
            self.assertEqual(line.count("('NOT DONE', 'C29 r"), 2, line)
            self.assertEqual(line.count("('NOT DONE', 'C30 r"), 2, line)
            self.assertEqual(line.count("['caretUnchanged']"), 4, line)     # the one open clause, nothing false

    def test_b_under_the_refusal_table_the_same_records_are_red(self):
        # What the judge printed before P1 (and runner 73b2e9ff recorded): the same bytes, the old expectation.
        with mock.patch.object(m, "boundary_noop_declared", lambda wasm: False):
            code, last, lines = self.judge()
        self.assertEqual(code, 1, last)
        self.assertIn("nothing-selected expects refused", lines[1])
        for line in self.m2_3_lines(lines):
            self.assertEqual(line.split()[1], "FAIL", line)
            self.assertEqual(line.count("('FAIL', 'C29 r") + line.count("('FAIL', 'C30 r"), 4, line)
            self.assertIn("'outcome'", line)

    def test_c_keyed_on_v19s_engine_nothing_is_judged(self):
        code, last, lines = self.judge(V19_WASM)
        self.assertEqual(code, 3, last)
        self.assertIn("is not the keyed", "\n".join(lines))
        self.assertEqual(self.m2_3_lines(lines), [])


if __name__ == "__main__":
    unittest.main()
