from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

import validate_e1_c  # noqa: E402
from run_e1_c import LIFECYCLE_WARMUP_CYCLES, PLANS  # noqa: E402
from validate_e1_c import decide, desktop_required, text_expectations  # noqa: E402


class E1CMatrixTest(unittest.TestCase):
    def test_frozen_case_counts_match_the_spec(self) -> None:
        self.assertEqual(len(PLANS["integration"]), 3)
        self.assertEqual(len(PLANS["recovery"]), 6)
        self.assertEqual(len(PLANS["corpus"]), 5)
        self.assertEqual(len(PLANS["lifecycle"]), 10)
        self.assertEqual(sum(len(value) for value in PLANS.values()), 24)
        matrix = json.loads((PROJECT / "e1" / "validation-matrix-v1.json").read_text())
        self.assertEqual(matrix["thresholds"]["integrationRepetitionsPerBrowser"], 3)
        self.assertEqual(matrix["thresholds"]["crashBarriersPerBrowser"], 4)
        self.assertEqual(matrix["thresholds"]["boundaryRestartCasesPerBrowser"], 2)
        self.assertEqual(matrix["thresholds"]["editSaveReopenSessionsPerBrowser"], 10)
        self.assertEqual(LIFECYCLE_WARMUP_CYCLES, 10)
        self.assertEqual(matrix["thresholds"]["lifecycleWarmupCycles"], 10)

    def test_integration_output_has_exactly_once_and_cancel_expectations(self) -> None:
        required, forbidden = text_expectations({
            "result": {"case": {
                "phase": "integration", "scenario": "integration",
                "fixture": "plain-grapheme", "repetition": 3,
            }}
        })
        self.assertIn("臺灣中文游標測E1C-REPLACE", required)
        self.assertIn("E1C-CANCEL", forbidden)
        self.assertIn("<b>forbidden</b>", forbidden)

    def test_desktop_scope_is_frozen_to_16_outputs(self) -> None:
        entries = []
        for browser in ("chrome", "firefox"):
            for phase, cases in PLANS.items():
                for case in cases:
                    entries.append({
                        "result": {"case": {
                            "phase": phase,
                            "scenario": case.scenario,
                            "fixture": case.fixture,
                            "repetition": case.repetition,
                        }}
                    })
        self.assertEqual(sum(desktop_required(entry) for entry in entries), 16)

    def test_e1_matrices_agree_with_the_validators_that_gate_them(self) -> None:
        """Both E1 matrices record a baseline.coreCommit that nothing read.

        finding 029: a claim nobody compares cannot fail, so it cannot notice
        going stale.  The validators gate the measured core HEAD against their
        own module constants, so a frozen matrix could disagree with them
        indefinitely.  Compare the copies -- within E1 only.  E1/R6/R7/R8 freeze
        independent baselines and are allowed to differ from one another, so
        there is deliberately no cross-release assertion here.
        """
        import validate_e1_preflight  # noqa: PLC0415

        for name, expected in (
            ("validation-matrix-v1.json", validate_e1_c.CORE_BASELINE_HEAD),
            ("discovery-matrix-v1.json", validate_e1_preflight.CORE_COMMIT),
        ):
            with self.subTest(matrix=name):
                matrix = json.loads((PROJECT / "e1" / name).read_text())
                self.assertEqual(matrix["baseline"]["coreCommit"], expected)


class E1CDecisionTest(unittest.TestCase):
    @staticmethod
    def decision(manual: dict):
        return decide(True, True, True, True, True, True, True, manual)

    def test_all_machine_and_trusted_manual_gates_produce_e1_go(self) -> None:
        result = self.decision({"complete": True, "pass": True})
        self.assertEqual(result["decision"], "E1_GO_ODT_EDITOR")
        self.assertTrue(result["complete"])

    def test_automatic_pass_waits_for_the_two_bounded_manual_runs(self) -> None:
        result = self.decision({"complete": False, "pass": False})
        self.assertEqual(result["decision"], "E1_AUTOMATIC_GO_MANUAL_PENDING")
        self.assertFalse(result["complete"])

    def test_manual_failure_is_partial_but_machine_safety_failure_stops(self) -> None:
        partial = self.decision({"complete": True, "pass": False})
        self.assertEqual(partial["decision"], "E1_PARTIAL_GO_ODT_EDITOR")
        stopped = decide(
            False, True, True, True, True, True, True, {"complete": True, "pass": True},
        )
        self.assertEqual(stopped["decision"], "E1_STOP_OR_RESCOPE")

    def test_unbound_evidence_stops_even_with_a_trusted_manual_round(self) -> None:
        # A relink invalidates the whole matrix, not only the manual half.  Every
        # other gate passing must not be able to carry stale browser evidence to a
        # GO, and it must not be downgraded to PARTIAL either -- PARTIAL means the
        # machine phases described the shipped artifact and only trusted input was
        # missing, which is exactly what an unbound run cannot claim.
        result = decide(
            True, False, True, True, True, True, True, {"complete": True, "pass": True},
        )
        self.assertEqual(result["decision"], "E1_STOP_OR_RESCOPE")
        self.assertFalse(result["automaticPass"])


class E1CArtifactBindingTest(unittest.TestCase):
    LIVE = {
        "loaderSha256": "aa" * 32,
        "wasmSha256": "bb" * 32,
        "workerSha256": "cc" * 32,
    }

    @staticmethod
    def case(contract: dict | None):
        artifact = {"profile": "e1-editor-v1"}
        if contract is not None:
            artifact["editorContract"] = contract
        return {
            "phase": "integration", "browser": "chrome", "case": "integration-01",
            "resultPath": "/dev/null", "result": {"artifact": artifact},
        }

    def bind(self, cases: list[dict]):
        with mock.patch.object(
            validate_e1_c, "profile_inventory", return_value=dict(self.LIVE),
        ):
            return validate_e1_c.artifact_binding(cases, PROJECT)

    def test_evidence_matching_the_live_artifact_binds(self) -> None:
        result = self.bind([self.case(dict(self.LIVE))])
        self.assertTrue(result["pass"])
        self.assertEqual(result["boundCases"], 1)

    def test_one_superseded_hash_is_enough_to_fail(self) -> None:
        stale = {**self.LIVE, "wasmSha256": "dd" * 32}
        result = self.bind([self.case(dict(self.LIVE)), self.case(stale)])
        self.assertFalse(result["pass"])
        self.assertEqual(result["supersededCases"], 1)
        self.assertEqual(result["boundCases"], 1)

    def test_evidence_that_names_no_artifact_does_not_bind(self) -> None:
        result = self.bind([self.case(None)])
        self.assertFalse(result["pass"])
        self.assertEqual(result["unattributableCases"], 1)

    def test_no_cases_at_all_is_not_a_pass(self) -> None:
        self.assertFalse(self.bind([])["pass"])


if __name__ == "__main__":
    unittest.main()
