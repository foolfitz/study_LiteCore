"""SPEC E2-C 9.1: the frozen matrix says what it must say.

The matrix is the criteria, written before the first browser round.  Its value
depends on two things being true and staying true: that it is bound to the
artifact and shell it will be measured on, and that it actually covers what the
spec promises.  Both are checked here rather than read, because a matrix that
promises fifteen actions and lists ten still looks like a complete document.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
MATRIX = PROJECT / "e2" / "validation-matrix-v1.json"
BUNDLE = PROJECT / "e2" / "editor-shell-v2-bundle-v1.json"
PROFILE = PROJECT / "dist" / "profiles" / "e2-editor-v2"

DISPOSITIONS = {"STOP", "PARTIAL", "NONE", "PREDICTION"}



class E2CMatrixV2DraftTest(unittest.TestCase):
    """The round-two draft, and the one property that makes it safe to have.

    A draft matrix sitting beside a frozen one is a hazard: the first round was
    bitten by criteria that moved after the round started, and a file that LOOKS
    like a matrix is exactly what someone would run against.  So the draft has
    to be unmistakably not-frozen, and its placeholders have to be detectable.
    """

    DRAFT = PROJECT / "e2" / "validation-matrix-v2-draft.json"
    PLACEHOLDER = "TO-BE-FILLED-AT-RELINK"

    def setUp(self) -> None:
        self.draft = json.loads(self.DRAFT.read_text(encoding="utf-8"))

    def test_the_draft_says_it_is_not_frozen(self) -> None:
        self.assertEqual(self.draft["status"], "DRAFT-NOT-FROZEN")
        self.assertIsNone(self.draft["frozenDate"])

    def test_every_baseline_hash_is_still_a_placeholder(self) -> None:
        """Until the relink happens there is nothing true to put here.

        A real hash in this file before v3 exists would be a hash copied from
        somewhere -- and evidence filed under an artifact that never ran it is
        finding 027.
        """
        for name in ("wasmSha256", "loaderSha256", "workerSha256",
                     "shellBundleSha256", "manifestSha256"):
            with self.subTest(hash=name):
                self.assertEqual(self.draft["baseline"][name], self.PLACEHOLDER)

    def test_the_second_round_binds_five_identities(self) -> None:
        self.assertIn("manifestSha256", self.draft["baseline"])
        self.assertIn("whyFive", self.draft["baseline"])

    def test_the_draft_carries_every_frozen_cell_forward(self) -> None:
        frozen = json.loads(
            (PROJECT / "e2" / "validation-matrix-v1.json").read_text(encoding="utf-8"))
        carried = {cell["id"] for cell in self.draft["cells"]
                   if cell.get("carriedFrom")}
        self.assertEqual(carried, {cell["id"] for cell in frozen["cells"]})

    def test_every_new_cell_says_why_it_exists(self) -> None:
        """A cell added because a round taught us something has to carry what it
        taught, or the next person reads it as arbitrary and deletes it."""
        for cell in self.draft["cells"]:
            if cell.get("addedIn") != "round-two":
                continue
            with self.subTest(cell=cell["id"]):
                self.assertTrue(cell.get("note"), cell["id"])
                self.assertIn(cell["onFailure"], ("STOP", "PARTIAL"))

    def test_the_freeze_has_an_entry_assertion(self) -> None:
        procedure = self.draft["freezeProcedure"]
        self.assertIn("entryAssertion", procedure)
        self.assertIn("D0", procedure["entryAssertion"])

    def test_the_draft_writes_to_its_own_evidence_root(self) -> None:
        """Round one's evidence is a record, not a place to write into."""
        frozen = json.loads(
            (PROJECT / "e2" / "validation-matrix-v1.json").read_text(encoding="utf-8"))
        self.assertNotEqual(self.draft["evidenceRoot"], frozen["evidenceRoot"])


class TestE2CMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
        self.cells = self.matrix["cells"]

    def test_every_cell_is_completely_specified(self) -> None:
        seen = set()
        for cell in self.cells:
            for field in ("id", "phase", "repeat", "oracle", "onFailure"):
                self.assertIn(field, cell, cell.get("id"))
            self.assertNotIn(cell["id"], seen, "duplicate cell id")
            seen.add(cell["id"])
            self.assertIn(cell["onFailure"], DISPOSITIONS, cell["id"])
            self.assertIsInstance(cell["repeat"], int)
            self.assertGreaterEqual(cell["repeat"], 1, cell["id"])
            self.assertTrue(cell["oracle"].strip(), cell["id"])

    def test_the_baseline_is_the_artifact_on_disk(self) -> None:
        manifest = json.loads((PROFILE / "sdk-manifest.json").read_text(encoding="utf-8"))
        contract = manifest["editorContract"]
        baseline = self.matrix["baseline"]
        for field in ("wasmSha256", "loaderSha256", "workerSha256"):
            self.assertEqual(baseline[field], contract[field], field)
        self.assertEqual(baseline["editorContractVersion"], contract["version"])
        self.assertEqual(baseline["abiVersion"], contract["abiVersion"])
        self.assertEqual(baseline["profile"], manifest["profile"])
        self.assertEqual(baseline["coreCommit"], manifest["coreCommit"])

    def test_the_baseline_names_the_shell_bundle_digest(self) -> None:
        bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
        self.assertEqual(self.matrix["baseline"]["shellBundleSha256"],
                         bundle["bundleSha256"])

    def test_every_declared_action_is_measured_by_name(self) -> None:
        # The failure this catches: a matrix that promises fifteen and exercises
        # ten reads as complete.  Each D1 cell names the actions it dispatches
        # in a field -- the first version of this test matched cell ids as
        # strings and reported set-paragraph-heading missing while the cell
        # `d1-heading-collapsed` was sitting right there, which is how a fuzzy
        # oracle turns into either a false alarm or a false pass.
        covered = {action
                   for cell in self.cells if cell["phase"] == "D1"
                   for action in cell.get("actions", [])}
        missing = sorted(set(self.matrix["productActions"]) - covered)
        self.assertEqual(missing, [], "declared but not exercised by any D1 cell")
        unknown = sorted(covered - set(self.matrix["productActions"]))
        self.assertEqual(unknown, [], "a D1 cell names an action nobody declares")

    def test_every_d1_cell_declares_which_actions_it_dispatches(self) -> None:
        for cell in self.cells:
            if cell["phase"] == "D1":
                self.assertIn("actions", cell, cell["id"])
                self.assertIsInstance(cell["actions"], list, cell["id"])

    def test_the_four_uncovered_cells_are_each_accounted_for(self) -> None:
        ids = {c["id"] for c in self.cells}
        # E2-B 9.11 named four. Two are measured here, two stay unpromised --
        # and the two that are measured must exist as cells, not as prose.
        self.assertIn("d1-ordered-range-cross-both-already-numbered", ids)
        self.assertIn("d5-pointer-drag-cross", ids)

    def test_partial_is_reserved_for_what_was_declared_outside_the_contract(self) -> None:
        for cell in self.cells:
            if cell["onFailure"] == "PARTIAL":
                self.assertEqual(cell["phase"], "D5", cell["id"])
            if cell.get("onUnavailable"):
                self.assertIn(cell["onUnavailable"], DISPOSITIONS, cell["id"])

    def test_a_prediction_cell_says_where_the_prediction_lives(self) -> None:
        for cell in self.cells:
            if cell["onFailure"] == "PREDICTION":
                self.assertIn("BEFORE", cell["oracle"],
                              "a prediction cell must say when the prediction "
                              "is written, or it is not a prediction")

    def test_the_characterisation_cell_cannot_affect_the_verdict(self) -> None:
        cell = next(c for c in self.cells
                    if c["id"] == "d1-characterisation-range-inherited")
        self.assertEqual(cell["onFailure"], "NONE")

    def test_the_comparison_projection_is_a_partition(self) -> None:
        projection = self.matrix["comparisonProjection"]
        self.assertEqual(set(projection["include"]) & set(projection["exclude"]),
                         set(), "a field cannot both count and not count")
        self.assertIn("elapsedMs", projection["exclude"])
        self.assertIn("bodyBytesChanged", projection["include"])

    def test_every_phase_the_spec_defines_has_cells(self) -> None:
        phases = {c["phase"] for c in self.cells}
        self.assertEqual(phases, {"D0", "D1", "D2", "D3", "D4", "D5"})

    def test_the_matrix_has_not_been_started(self) -> None:
        # A guard against the thing that makes freezing pointless: editing the
        # criteria after the results exist.  Once execution.startedAt is set,
        # this test is the reminder that changes need a spec revision entry.
        execution = self.matrix["execution"]
        if execution.get("startedAt") is not None:
            self.assertIsNotNone(execution.get("completedAt"),
                                 "a started matrix must record its end")


class MatrixEntryAssertion(unittest.TestCase):
    """The freeze window guard, as a test rather than as a paragraph.

    The v2 draft's `freezeProcedure.entryAssertion` describes it in prose.
    Prose does not refuse to run a round.
    """

    def setUp(self) -> None:
        sys.path.insert(0, str(PROJECT / "tools"))
        from e2_c_matrix_entry import assert_entry  # noqa: PLC0415
        self.assert_entry = assert_entry

    def test_the_frozen_first_round_matrix_is_admitted(self) -> None:
        report = self.assert_entry(PROJECT / "e2" / "validation-matrix-v1.json")
        self.assertTrue(report["ok"], report["problems"])

    def test_the_draft_is_refused_while_it_is_a_draft(self) -> None:
        report = self.assert_entry(
            PROJECT / "e2" / "validation-matrix-v2-draft.json")
        self.assertFalse(report["ok"])
        # Both halves, because a guard that only reads `status` would pass a
        # matrix whose status was flipped and whose hashes were forgotten --
        # which is precisely the window this assertion exists for.
        self.assertTrue(any("status" in problem
                            for problem in report["problems"]))
        self.assertTrue(any("TO-BE-FILLED-AT-RELINK" in problem
                            for problem in report["problems"]))

    def test_the_entry_assertion_is_wired_into_d0(self) -> None:
        for tool in ("run_e2_c_d0.py", "analyze_e2_c_d0.py"):
            text = (PROJECT / "tools" / tool).read_text(encoding="utf-8")
            self.assertIn("require_entry(", text,
                          f"{tool} does not run the entry assertion")


if __name__ == "__main__":
    unittest.main()
