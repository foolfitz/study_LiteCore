"""The merge WASM runner's clauses (SPEC-M3-paragraph-merge 22.1), offline.

The comparator red cases spec 10.2 asks for (one per assertion) and the two
the review of 5555e554 found missing: the marker check that inverted when the
marker was lost (B3), and "not changed" said after the key went out.  Built
from the native R0c data, so a clause is tested against the references it
will meet in a run.

    python3 -m unittest tests.test_merge_wasm_clauses
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_merge_wasm_shakedown as m  # noqa: E402

CASES = m.tool_cases(frame_cell=False)
DOCS = m.EVIDENCE / "r0c/round-20261006T144628Z/docs"
SAVED_TOAST = "已存出 11.9 KB"


def observed_merge(case: str, *, key_doc: Path | None = None, comment: str | None = None,
                   presses: int = 0) -> dict:
    """What the runner records for a correct merge, built from the native arms."""
    spec = CASES[case]
    key_doc = key_doc or spec["key"]
    return {"outcome": "verified-key-undo",
            "keyUndo": {"comment": spec["nativeComment"] if comment is None else comment,
                        "restorePresses": presses},
            "generation": ["1", "1"], "toasts": [], "toastsAtEnd": [SAVED_TOAST, SAVED_TOAST],
            "afterKeyDocument": m.compare(key_doc.read_bytes(), spec["key"], False),
            "followDocument": m.compare(spec["follow"].read_bytes(), spec["follow"], False)}


def verdict(clauses: dict) -> bool:
    return all(v for v in clauses.values() if v is not None)


class MergeClauses(unittest.TestCase):
    def test_the_native_key_arm_passes(self):
        for case in ("C01", "C03", "I02", "C11", "Y01"):
            clauses = m.merge_clauses(observed_merge(case), CASES[case])
            self.assertTrue(verdict(clauses), (case, clauses))
            if CASES[case]["decision"] == "typed-merge":
                self.assertIsNone(clauses["afterKeyBytes"], "spec 12: typed text compares by text")
            else:
                self.assertTrue(clauses["afterKeyBytes"], case)

    def test_red_the_select_arm_is_not_the_key(self):
        # 10.2: C03's native select-arm document as what the page saved.
        clauses = m.merge_clauses(observed_merge("C03", key_doc=DOCS / "r1-C03-select.odt"),
                                  CASES["C03"])
        self.assertFalse(clauses["afterKeyText"])
        self.assertFalse(clauses["afterKeyBytes"])
        self.assertFalse(verdict(clauses))

    def test_red_a_different_undo_comment(self):
        clauses = m.merge_clauses(observed_merge("C11", comment="Delete paragraph"), CASES["C11"])
        self.assertFalse(clauses["comment"])
        self.assertFalse(verdict(clauses))

    def test_red_a_restore_press(self):
        # 22.1: the E shape has none; a 2 is the replaced prescription back.
        clauses = m.merge_clauses(observed_merge("I02", presses=2), CASES["I02"])
        self.assertFalse(clauses["restorePresses"])
        self.assertFalse(verdict(clauses))

    def test_red_a_toast_after_the_typed_z(self):
        # Review 2026-10-08 (codex B5): `toasts` is read before the first save; this one came after the `Z`.
        observed = observed_merge("C01")
        observed["toastsAtEnd"] = [SAVED_TOAST, "重繪失敗：TILE_NOT_PAINTED", SAVED_TOAST]
        clauses = m.merge_clauses(observed, CASES["C01"])
        self.assertTrue(clauses["noToast"])
        self.assertFalse(clauses["noToastThroughFollow"])
        for missing in (None, [SAVED_TOAST]):
            observed["toastsAtEnd"] = missing
            self.assertFalse(m.merge_clauses(observed, CASES["C01"])["noToastThroughFollow"], missing)


def observed_refusal(case: str, toasts: list[str], *, generation=("1", "2"), later=None,
                     checkpoint="有（r2）") -> dict:
    spec = CASES[case]
    _, stage, posted = spec["expected"]
    return {"outcome": "refused", "stage": stage, "keyPosted": posted,
            "generation": [generation[0], generation[1] if later is None else later],
            "toastWindow": {"closed": True, "generation": generation[1], "toasts": toasts},
            "beforeKey": {"revision": "2"}, "afterKey": {"checkpoint": checkpoint}}


class RefusalClauses(unittest.TestCase):
    def setUp(self):
        self.original = m.odt_parts(CASES["C17"]["original"].read_bytes())["paragraphs"]
        target = m.native_cases("boundaries")["C01"]["search"]
        self.expected = [p + m.MARKER if p == target else p for p in self.original]
        self.reopen = ["這裡目前還不能這樣刪除。文件沒有被改動，正在重新載入…",
                       "這裡目前還不能這樣刪除。文件沒有被改動，已重新載入。"]

    def test_a_kept_marker_passes(self):
        clauses = m.refusal_clauses(observed_refusal("C17", self.reopen), CASES["C17"],
                                    self.expected, self.expected)
        self.assertTrue(verdict(clauses), clauses)

    def test_red_a_lost_marker(self):
        # B3: the page reopened the original without the marker.
        clauses = m.refusal_clauses(observed_refusal("C17", self.reopen), CASES["C17"],
                                    self.expected, list(self.original))
        self.assertFalse(clauses["reopenedText"])
        self.assertFalse(clauses["markerSurvived"])

    def test_red_not_changed_after_the_key_went_out(self):
        said = ["這一下刪除送出了，但沒能確認它做了什麼，正在重新載入…",
                "文件沒有被改動，已重新載入。"]
        clauses = m.refusal_clauses(observed_refusal("C15", said), CASES["C15"],
                                    self.expected, self.expected)
        self.assertFalse(clauses["noUnchanged"])

    def test_red_a_third_toast(self):
        toasts = [self.reopen[0], "重繪失敗：ENGINE_DISPOSED：engine is disposed", self.reopen[1]]
        clauses = m.refusal_clauses(observed_refusal("C17", toasts), CASES["C17"],
                                    self.expected, self.expected)
        self.assertFalse(clauses["onlyTheReopenToasts"])

    def test_red_a_repeated_reopen_sentence(self):
        # The count, not only the wording: a duplicated sentence (two repaint
        # loops at once, review N4) is a toast the user did not need.
        toasts = [self.reopen[0], self.reopen[1], self.reopen[1]]
        clauses = m.refusal_clauses(observed_refusal("C17", toasts), CASES["C17"],
                                    self.expected, self.expected)
        self.assertFalse(clauses["onlyTheReopenToasts"])

    def test_red_no_reopen(self):
        clauses = m.refusal_clauses(observed_refusal("C17", self.reopen, generation=("1", "1")),
                                    CASES["C17"], self.expected, self.expected)
        self.assertFalse(clauses["generation"])

    # Review 2026-10-08.
    def test_red_a_second_reopen_after_the_window(self):
        # opus S5: the window closed at generation 2, the session was reopened again before the save.
        clauses = m.refusal_clauses(observed_refusal("C17", self.reopen, later="3"),
                                    CASES["C17"], self.expected, self.expected)
        self.assertFalse(clauses["generation"])

    def test_red_two_toasts_that_are_not_the_reopen_pair(self):
        # codex B8: two end sentences, two starts, the pair reversed, or two leads.
        other = ["這一下刪除送出了，但沒能確認它做了什麼，正在重新載入…", self.reopen[1]]
        for toasts in ([self.reopen[1], self.reopen[1]], [self.reopen[0], self.reopen[0]],
                       list(reversed(self.reopen)), other, ["重新載入", "重新載入"]):
            clauses = m.refusal_clauses(observed_refusal("C17", toasts), CASES["C17"],
                                        self.expected, self.expected)
            self.assertFalse(clauses["onlyTheReopenToasts"], toasts)


ROOT = (b'<office:document-content xmlns:b="u2" xmlns:a="u1" office:version="1.4">'
        b'<office:body><office:text><office:forms form:automatic-focus="false" '
        b'form:apply-design-mode="false"/><text:p>ab<text:soft-page-break/>cd</text:p>'
        b'</office:text></office:body></office:document-content>')


class Reduction(unittest.TestCase):
    """Spec 24: M2-0's three operations, and nothing they should not do."""

    def test_the_three_differences_reduce_away(self):
        other = (ROOT.replace(b'xmlns:b="u2" xmlns:a="u1"', b'xmlns:a="u1" xmlns:b="u2"')
                 .replace(b'<office:forms form:automatic-focus="false" '
                          b'form:apply-design-mode="false"/>', b"")
                 .replace(b"ab<text:soft-page-break/>cd", b"abc<text:soft-page-break/>d"))
        self.assertNotEqual(ROOT, other)
        self.assertEqual(m.reduce_content(ROOT), m.reduce_content(other))

    def test_red_a_namespace_value_text_or_attribute_still_differs(self):
        for changed in (ROOT.replace(b'"u2"', b'"u3"'), ROOT.replace(b"cd</text:p>", b"cx</text:p>"),
                        ROOT.replace(b'office:version="1.4"', b'office:version="1.3"'),
                        ROOT.replace(b"<text:p>", b'<text:p text:style-name="P1">')):
            self.assertNotEqual(m.reduce_content(ROOT), m.reduce_content(changed))

    def test_no_case_collapses(self):
        # 10.2: the reduction is refused if it makes any case's native
        # before-key and key-arm documents equal.
        self.assertEqual(m.reduction_collapses(), [])

    def test_no_root_is_an_error(self):
        with self.assertRaises(ValueError):
            m.reduce_content(b"<office:document-styles/>")


class List(unittest.TestCase):
    def test_the_list_is_the_tool_closed_population(self):
        counts = {}
        for spec in CASES.values():
            counts[spec["criterion"]] = counts.get(spec["criterion"], 0) + 1
        self.assertEqual(counts, {"M2-1": 20, "M2-3": 5, "barrier": 1})   # spec 25

    def test_an_unknown_decision_stops(self):
        with self.assertRaises(SystemExit):
            m.expectation("something-new")
        with self.assertRaises(SystemExit):
            m.expectation("something-new", boundary_noop=True)


# C (SPEC-M3-link-batch 10.5, 10.7; task 2026-10-14i): the `nothing-selected` cases expect the no-op on a
# profile whose engine declares it, and the refusal on every other; nothing else in the list moves.
CASES_UNDER_C = m.tool_cases(frame_cell=False, boundary_noop=True)
PROFILES = m.HERE / "dist" / "profiles"


class KeyingOnC(unittest.TestCase):
    def test_the_default_is_the_refusal(self):
        # What the v19-bound reader and every caller that passes nothing mean (34.1).
        self.assertEqual(m.expectation("nothing-selected"), ("M2-3", ("refused", "nothing-selected", False)))
        self.assertEqual(CASES["C29"]["expected"], ("refused", "nothing-selected", False))
        self.assertEqual(CASES["C30"]["expected"], ("refused", "nothing-selected", False))

    def test_under_c_only_the_nothing_selected_cases_move(self):
        self.assertEqual(m.expectation("nothing-selected", True), ("M2-3", (m.BOUNDARY_NOOP, None, None)))
        self.assertEqual({c for c in CASES if CASES[c]["expected"] != CASES_UNDER_C[c]["expected"]},
                         {"C29", "C30"})
        self.assertEqual({c: s["criterion"] for c, s in CASES.items()},
                         {c: s["criterion"] for c, s in CASES_UNDER_C.items()})     # the population is the same
        for decision in ("merge", "typed-merge", "barrier", "refused-k1-x", "refused-k2-x", "key-noop"):
            self.assertEqual(m.expectation(decision), m.expectation(decision, True), decision)

    def test_a_no_op_case_types_the_marker(self):
        self.assertTrue(m.types_marker(CASES_UNDER_C["C29"]["expected"]))
        self.assertTrue(m.types_marker(CASES["C29"]["expected"]))
        self.assertFalse(m.types_marker(CASES["C01"]["expected"]))

    def test_the_declaration_is_the_emitted_fragment(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "with.wasm").write_bytes(b"\0asm" + b"x" * 100 + m.BOUNDARY_NOOP_FRAGMENT + b"y" * 100)
        (tmp / "without.wasm").write_bytes(b"\0asm" + b"x" * 100 + b"verified-boundary-noop" + b"y" * 100)
        self.assertTrue(m.boundary_noop_declared(tmp / "with.wasm"))
        # The bare name is not the declaration: only the fragment the engine emits is.
        self.assertFalse(m.boundary_noop_declared(tmp / "without.wasm"))

    @unittest.skipUnless((PROFILES / "e2-editor-v19/probe.wasm").is_file()
                         and (PROFILES / "e2-editor-v20/probe.wasm").is_file(), "the two profiles are not served")
    def test_red_v19_does_not_declare_and_v20_does(self):
        self.assertFalse(m.boundary_noop_declared(PROFILES / "e2-editor-v19/probe.wasm"))
        self.assertTrue(m.boundary_noop_declared(PROFILES / "e2-editor-v20/probe.wasm"))


def observed_noop(case: str, *, outcome=m.BOUNDARY_NOOP, generation=("1", "1"), revision=("2", "2"),
                  toasts=(), caret=None) -> dict:
    spec = CASES_UNDER_C[case]
    placed = {"engineCaret": list(spec["nativeCaret"]), "caretGeneration": 17}
    out = {"outcome": outcome, "generation": list(generation), "toasts": None if toasts is None else list(toasts),
           "beforeKey": {"revision": revision[0]}, "afterKey": {"revision": revision[1]}, "place": placed}
    if caret is not None:
        out["caretAfterKey"] = caret
    return out


class NoopClauses(unittest.TestCase):
    """C's no-op, every clause with its red case (AGENTS.md 6)."""

    def setUp(self):
        self.original = m.odt_parts(CASES["C29"]["original"].read_bytes())["paragraphs"]
        self.expected = m.original_plus_marker(CASES_UNDER_C["C29"], m.native_cases("boundaries")["C01"])
        target = m.native_cases("boundaries")["C01"]["search"]
        self.assertEqual(self.expected, [p + m.MARKER if p == target else p for p in self.original])
        self.caret = {"generation": 17, "caret": dict(zip(("x", "y", "width", "height"), CASES["C29"]["nativeCaret"]))}

    def test_the_no_op_passes(self):
        clauses = m.noop_clauses(observed_noop("C29", caret=self.caret), CASES_UNDER_C["C29"],
                                 self.expected, self.expected)
        self.assertTrue(verdict(clauses), clauses)
        self.assertEqual([k for k, v in clauses.items() if v is None], [])

    def test_a_record_without_the_caret_leaves_that_clause_open(self):
        # The eight part-B reports of the v20 shakedown: the runner did not read the caret after the key.
        clauses = m.noop_clauses(observed_noop("C29"), CASES_UNDER_C["C29"], self.expected, self.expected)
        self.assertIsNone(clauses["caretUnchanged"])
        self.assertTrue(verdict(clauses), clauses)

    def test_red_a_refusal_on_a_profile_that_declares_c(self):
        clauses = m.noop_clauses(observed_noop("C29", outcome="refused", generation=("1", "2"),
                                              toasts=["x，正在重新載入…", "x，已重新載入。"]),
                                 CASES_UNDER_C["C29"], self.expected, self.expected)
        self.assertFalse(clauses["outcome"])
        self.assertFalse(clauses["generation"])
        self.assertFalse(clauses["noToast"])

    def test_red_a_merge_at_the_boundary(self):
        # The product did something: another completion, and a document that is not original + marker.
        changed = [p for p in self.expected if p != "M29 last"]
        clauses = m.noop_clauses(observed_noop("C30", outcome="verified-key-undo", revision=("2", "3")),
                                 CASES_UNDER_C["C30"], self.expected, changed)
        self.assertFalse(clauses["outcome"])
        self.assertFalse(clauses["revision"])
        self.assertFalse(clauses["unchangedText"])

    def test_red_a_lost_marker(self):
        # B3: original without the marker reads as "original", which is not original + marker.
        clauses = m.noop_clauses(observed_noop("C29"), CASES_UNDER_C["C29"], self.expected, list(self.original))
        self.assertFalse(clauses["unchangedText"])
        self.assertFalse(clauses["markerSurvived"])

    def test_red_a_toast(self):
        clauses = m.noop_clauses(observed_noop("C29", toasts=["重繪失敗：TILE_NOT_PAINTED"]),
                                 CASES_UNDER_C["C29"], self.expected, self.expected)
        self.assertFalse(clauses["noToast"])
        self.assertFalse(m.noop_clauses(observed_noop("C29", toasts=None), CASES_UNDER_C["C29"],
                                        self.expected, self.expected)["noToast"])

    def test_red_a_missing_revision(self):
        out = observed_noop("C29")
        out["beforeKey"] = {}
        self.assertFalse(m.noop_clauses(out, CASES_UNDER_C["C29"], self.expected, self.expected)["revision"])

    def test_red_the_caret_moved_or_another_worker(self):
        moved = {"generation": 17, "caret": {**self.caret["caret"], "x": self.caret["caret"]["x"] + 1}}
        other = {"generation": 18, "caret": dict(self.caret["caret"])}
        for caret in (moved, other, {}, {"generation": 17, "caret": None}):
            clauses = m.noop_clauses(observed_noop("C29", caret=caret), CASES_UNDER_C["C29"],
                                     self.expected, self.expected)
            self.assertFalse(clauses["caretUnchanged"], caret)
            self.assertFalse(verdict(clauses))

    def test_red_the_no_op_on_a_profile_that_does_not_declare_c(self):
        # The keying's red case: the same recorded no-op, judged as the profile v19 is -- a refusal expected.
        # It is red on every refusal clause; nothing in the no-op clauses is consulted.
        out = {**observed_noop("C29", caret=self.caret), "toastWindow": {"closed": False, "generation": "1",
                                                                         "toasts": []},
               "afterKey": {"revision": "2", "checkpoint": "無"}}
        clauses = m.refusal_clauses(out, CASES["C29"], self.expected, self.expected)
        self.assertFalse(verdict(clauses))
        self.assertEqual({k for k, v in clauses.items() if v is False},
                         {"outcome", "stage", "keyPosted", "generation", "toastWindowClosed",
                          "checkpointRevision", "onlyTheReopenToasts"})


class Schedules(unittest.TestCase):
    """Spec 30.2: a criterion run's cases and rounds come from the tool list alone."""

    def test_each_mode(self):
        self.assertEqual(m.mode_schedule("counted", CASES), (list(CASES), 3))
        self.assertEqual(m.mode_schedule("m2-1b", CASES), (["Y01", "Y02"], 10))
        self.assertEqual(m.mode_schedule("m2-1-red", CASES), (["C01", "C02", "C03"], 1))
        self.assertEqual(m.mode_schedule("m2-4", CASES), ([], 1))

    def test_red_no_typed_merge_case_stops(self):
        without = {c: s for c, s in CASES.items() if s["decision"] != "typed-merge"}
        with self.assertRaises(SystemExit):
            m.mode_schedule("m2-1b", without)

    def test_bound_to_v19_after_v56(self):
        # Spec 7 / 30.1: the binding is written after shell generation v56 is frozen; until then no report could
        # say "counted": true.  Was `test_nothing_is_bound_before_v56` (BINDING is None) until the commit that set
        # BINDING, 2026-10-08.  Not compared with the live tree: the cutover rewrites web/e2-editor-app.js.
        self.assertIsNotNone(m.BINDING)
        self.assertEqual(tuple(m.BINDING), m.BOUND_KEYS)
        for key, value in m.BINDING.items():
            self.assertRegex(value, r"^[0-9a-f]{64}$", key)
        self.assertTrue(m.BINDING["wasmSha256"].startswith("1aafd4f9"))        # e2-editor-v19
        self.assertTrue(m.BINDING["workerSha256"].startswith("00882139"))


LIMIT = m.limit_reference() if m.LIMIT_ROUND.is_dir() else None


@unittest.skipIf(LIMIT is None, "R0 run 4's documents are not under build/")
class LimitClauses(unittest.TestCase):
    """Spec 30.2 M2-4, built from R0 run 4's own documents."""

    def observed(self, *, presses=None, final=None, toasts=None, generation=("1", "1"), control=False):
        if presses is None:
            presses = [{"press": n, "ok": True, "completion": "verified-key-undo", "comment": "Delete paragraph",
                        "restorePresses": 0, "actionsAfter": min(n, m.LIMIT_STEPS),
                        "keyToUndoMs": 40, "keyToResponseMs": 140.5}
                       for n in range(1, m.LIMIT_PRESSES + 1)]
        final = LIMIT["final"] if final is None else final
        return {"presses": presses, "generation": list(generation), "toasts": [] if toasts is None else toasts,
                "toastsAtEnd": [SAVED_TOAST],
                "control": control, "finalDocument": m.compare(final.read_bytes(), LIMIT["final"], False)}

    def test_the_reference(self):
        self.assertEqual(LIMIT["caret"], [1791, 1418, 0, 276])
        self.assertEqual(LIMIT["fixtureSha256"][:8], "09b5ced0")

    def test_the_native_run_passes(self):
        clauses = m.limit_clauses(self.observed())
        self.assertTrue(verdict(clauses), clauses)

    def test_red_stopped_early(self):
        presses = self.observed()["presses"][:50]
        presses[-1] = {**presses[-1], "ok": False, "completion": None}
        clauses = m.limit_clauses(self.observed(presses=presses))
        self.assertFalse(clauses["presses"])
        self.assertFalse(clauses["everyPressVerified"])

    def test_red_the_limit_never_reached(self):
        presses = [{**p, "actionsAfter": min(p["actionsAfter"], 99)} for p in self.observed()["presses"]]
        self.assertFalse(m.limit_clauses(self.observed(presses=presses))["limitReached"])

    def test_red_the_count_falls_after_the_limit(self):
        presses = self.observed()["presses"]
        presses[102] = {**presses[102], "actionsAfter": 99}
        self.assertFalse(m.limit_clauses(self.observed(presses=presses))["limitReached"])

    def test_red_one_other_comment(self):
        presses = self.observed()["presses"]
        presses[103] = {**presses[103], "comment": "Delete “b”"}
        self.assertFalse(m.limit_clauses(self.observed(presses=presses))["comment"])

    def test_red_the_document_after_104_presses(self):
        doc = m.LIMIT_ROUND / "docs" / f"r1-{m.LIMIT_CASE}-key104.odt"
        clauses = m.limit_clauses(self.observed(final=doc))
        self.assertFalse(clauses["finalBytes"])
        self.assertFalse(clauses["finalText"])

    def test_red_a_toast_and_a_reopen(self):
        clauses = m.limit_clauses(self.observed(toasts=["已重新載入"], generation=("1", "2")))
        self.assertFalse(clauses["noToast"])
        self.assertFalse(clauses["generation"])

    def test_the_control_leaves_the_instrument_clauses_open(self):
        presses = [{"press": n, "settledBefore": True} for n in range(1, m.LIMIT_PRESSES + 1)]
        clauses = m.limit_clauses(self.observed(presses=presses, control=True))
        self.assertEqual({k for k, v in clauses.items() if v is None},
                         {"everyPressVerified", "comment", "restorePresses", "limitReached", "latency"})
        self.assertTrue(verdict(clauses), clauses)

    # Spec 31.2: every press under LATENCY_BOUND_MS, the runner's and the engine's number both.
    def test_red_one_press_at_the_bound(self):
        for field in ("keyToUndoMs", "keyToResponseMs"):
            presses = self.observed()["presses"]
            presses[54] = {**presses[54], field: m.LATENCY_BOUND_MS}
            self.assertFalse(m.limit_clauses(self.observed(presses=presses))["latency"], field)

    def test_red_a_negative_number(self):
        # Review 2026-10-08 (codex S2): a time before the key is not an answer to it.
        for value in (-1, -0.5, float("nan"), float("-inf")):
            presses = self.observed()["presses"]
            presses[3] = {**presses[3], "keyToResponseMs": value}
            self.assertFalse(m.limit_clauses(self.observed(presses=presses))["latency"], value)

    def test_red_a_toast_at_the_save(self):
        observed = self.observed()
        observed["toastsAtEnd"] = ["重繪失敗：TILE_NOT_PAINTED", SAVED_TOAST]
        self.assertFalse(m.limit_clauses(observed)["noToastThroughSave"])

    def test_red_a_missing_number(self):
        for field in ("keyToUndoMs", "keyToResponseMs"):
            presses = self.observed()["presses"]
            presses[0] = {**presses[0], field: None}
            self.assertFalse(m.limit_clauses(self.observed(presses=presses))["latency"], field)

    def test_red_the_v18_reports(self):
        # The five reports spec 31.2 names as its red cases; two of them say `pass: true` under the old clauses.
        v18 = m.HERE.parent / "findings/evidence/v18"
        for name in ("m2-shakedown/m2-4-chrome.json", "m2-shakedown/m2-4-firefox.json",
                     "diag-117/m2-4-chrome.json", "finding-118/p4-m2-4-fixed-chrome.json",
                     "finding-118/p4-m2-4-fixed-firefox.json"):
            presses = json.loads((v18 / name).read_text())["cases"][0]["presses"]
            self.assertEqual(len(presses), m.LIMIT_PRESSES, name)
            self.assertFalse(m.limit_clauses(self.observed(presses=presses))["latency"], name)


class Binding(unittest.TestCase):
    """Spec 7 / 30.2: what makes a report counted; the red case runs v8 and the same page source."""

    BINDING = {**{k: k.lower() for k in m.BOUND_KEYS}, "wasmSha256": "w19", "workerSha256": "k19",
               "pageSha256": "p19"}

    def test_the_candidate(self):
        self.assertTrue(m.is_counted("counted", dict(self.BINDING), self.BINDING))
        self.assertTrue(m.is_counted("m2-4", dict(self.BINDING), self.BINDING))

    def test_red_any_value_differs_on_the_candidate(self):
        for key in self.BINDING:
            self.assertFalse(m.is_counted("m2-1b", {**self.BINDING, key: "other"}, self.BINDING), key)

    def test_the_red_case_on_v8(self):
        v8 = {**self.BINDING, "wasmSha256": "w8", "workerSha256": "k8", "pageSha256": "p8"}
        self.assertTrue(m.is_counted("m2-1-red", v8, self.BINDING))
        for key in set(m.BOUND_KEYS) - set(m.PROFILE_BOUND):
            self.assertFalse(m.is_counted("m2-1-red", {**v8, key: "other"}, self.BINDING), key)
        self.assertFalse(m.is_counted("m2-1-red", {k: v for k, v in v8.items() if k != "eshapeSha256"},
                                      self.BINDING))

    def test_red_another_schema(self):
        # Review 2026-10-08 (codex B3): two equal dicts without the binding's keys are not a binding.
        for mode in ("counted", "m2-1-red"):
            self.assertFalse(m.is_counted(mode, {"irrelevant": 1}, {"irrelevant": 1}), mode)
            short = {k: v for k, v in self.BINDING.items() if k != "nativeSha256"}
            self.assertFalse(m.is_counted(mode, short, short), mode)

    def test_nothing_counts_unbound_or_in_a_shakedown(self):
        self.assertFalse(m.is_counted("counted", dict(self.BINDING), None))
        self.assertFalse(m.is_counted("shakedown", dict(self.BINDING), self.BINDING))


class Pair(unittest.TestCase):
    """Spec 22.3's paired control, as tightened by the review of 2026-10-08 (codex B4)."""

    def reports(self, change=None):
        refusal = {"case": "C15", "round": 1, "generation": ["1", "2"],
                   "toastWindow": {"closed": True, "generation": "2", "toasts": ["a，正在重新載入…", "a，已重新載入。"]}}
        merge = {"case": "C01", "round": 1, "generation": ["2", "2"], "toasts": [],
                 "toastsAtEnd": [SAVED_TOAST, SAVED_TOAST]}
        a = {"control": False, "cases": [json.loads(json.dumps(c)) for c in (refusal, merge)]}
        b = {"control": True, "cases": [json.loads(json.dumps(c)) for c in (refusal, merge)]}
        if change:
            change(b)
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "x.json").write_text(json.dumps(a))
        (tmp / "y.json").write_text(json.dumps(b))
        return m.pair(tmp / "x.json", tmp / "y.json")

    def test_the_same(self):
        paired = self.reports()
        self.assertEqual((paired["pairs"], paired["sameOrder"], paired["differ"]), (2, True, []))

    def test_red_another_transition_with_the_same_end(self):
        paired = self.reports(lambda b: b["cases"][0].update(generation=["2", "2"]))
        self.assertEqual([r["case"] for r in paired["differ"]], ["C15"])

    def test_red_a_window_that_did_not_close(self):
        paired = self.reports(lambda b: b["cases"][0]["toastWindow"].update(closed=False))
        self.assertEqual([r["case"] for r in paired["differ"]], ["C15"])

    def test_red_a_toast_after_the_follow(self):
        paired = self.reports(lambda b: b["cases"][1].update(toastsAtEnd=[SAVED_TOAST, "x", SAVED_TOAST]))
        self.assertEqual([r["case"] for r in paired["differ"]], ["C01"])

    def test_red_another_order(self):
        paired = self.reports(lambda b: b["cases"].reverse())
        self.assertFalse(paired["sameOrder"])


class Teardown(unittest.TestCase):
    """Handoff 10-08d Next 2: the browser is closed even when the last observer read fails."""

    class Session:
        def __init__(self):
            self.closed = 0

        def evaluate(self, *_):
            raise ConnectionError("CDP dropped")

        def close(self):
            self.closed += 1

    def test_the_browser_is_closed_when_the_read_fails(self):
        session, report = self.Session(), {}
        original = m.obs
        m.obs = lambda s: (_ for _ in ()).throw(ConnectionError("CDP dropped"))
        try:
            m.teardown(session, report)
        finally:
            m.obs = original
        self.assertEqual(session.closed, 1)
        self.assertEqual(report["observerAtEnd"], {"error": "ConnectionError: CDP dropped"})

    def test_a_normal_end(self):
        session, report = self.Session(), {}
        original = m.obs
        m.obs = lambda s: {"responses": [1], "responsesSeen": 1}
        try:
            m.teardown(session, report)
        finally:
            m.obs = original
        self.assertEqual(session.closed, 1)
        self.assertEqual(report["observerAtEnd"], {"responsesSeen": 1})

    def test_a_close_that_raises(self):
        # Review 2026-10-08 (codex S3): the caller's server and report steps run after this.
        class Raising(self.Session):
            def close(self):
                raise RuntimeError("geckodriver gone")
        report = {}
        original = m.obs
        m.obs = lambda s: {"responsesSeen": 1}
        try:
            m.teardown(Raising(), report)
        finally:
            m.obs = original
        self.assertEqual(report["teardownError"], "RuntimeError: geckodriver gone")

    def test_no_session(self):
        report = {}
        m.teardown(None, report)
        self.assertEqual(report, {})


if __name__ == "__main__":
    unittest.main()
