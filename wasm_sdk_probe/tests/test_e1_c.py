from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

import validate_e1_c  # noqa: E402
from run_e1_c import LIFECYCLE_WARMUP_CYCLES, PLANS  # noqa: E402
from validate_e1_c import (  # noqa: E402
    EXPECTED_CASES,
    decide,
    desktop_required,
    expected_cases_for_matrix,
    matrix_contract,
    resolve_matrix_path,
    shell_bundle_digest,
    shell_bundle_inventory,
    text_expectations,
    workspace_preflight,
)


MATRIX_V1 = PROJECT / "e1" / "validation-matrix-v1.json"
MATRIX_V2 = PROJECT / "e1" / "validation-matrix-v2.json"


class E1CMatrixTest(unittest.TestCase):
    def test_frozen_case_counts_match_the_spec(self) -> None:
        self.assertEqual(len(PLANS["integration"]), 3)
        self.assertEqual(len(PLANS["recovery"]), 7)
        self.assertEqual(len(PLANS["corpus"]), 5)
        self.assertEqual(len(PLANS["lifecycle"]), 10)
        self.assertEqual(sum(len(value) for value in PLANS.values()), 25)
        self.assertEqual(
            [case.name for case in PLANS["recovery"]], EXPECTED_CASES["recovery"],
        )
        v1 = json.loads(MATRIX_V1.read_text())
        v2 = json.loads(MATRIX_V2.read_text())
        self.assertEqual(v1["thresholds"]["integrationRepetitionsPerBrowser"], 3)
        self.assertEqual(v1["thresholds"]["crashBarriersPerBrowser"], 4)
        self.assertEqual(v2["thresholds"]["crashBarriersPerBrowser"], 5)
        self.assertEqual(v2["thresholds"]["boundaryRestartCasesPerBrowser"], 2)
        self.assertEqual(v2["thresholds"]["editSaveReopenSessionsPerBrowser"], 10)
        self.assertEqual(LIFECYCLE_WARMUP_CYCLES, 10)
        self.assertEqual(v2["thresholds"]["lifecycleWarmupCycles"], 10)

    def test_v1_keeps_current_cases_while_v2_selects_the_next_matrix(self) -> None:
        v1 = json.loads(MATRIX_V1.read_text())
        v2 = json.loads(MATRIX_V2.read_text())
        self.assertEqual(len(expected_cases_for_matrix(v1)["recovery"]), 6)
        self.assertEqual(len(expected_cases_for_matrix(v2)["recovery"]), 7)
        self.assertEqual(
            resolve_matrix_path(PROJECT, Path("validation-matrix-v2.json")), MATRIX_V2,
        )
        self.assertEqual(
            resolve_matrix_path(PROJECT, Path("e1/validation-matrix-v2.json")), MATRIX_V2,
        )

    def test_each_matrix_crash_barrier_matches_its_crash_scenarios(self) -> None:
        for path in (MATRIX_V1, MATRIX_V2):
            with self.subTest(matrix=path.name):
                contract = matrix_contract(json.loads(path.read_text()))
                self.assertTrue(contract["pass"], contract)

    def test_checkpoint_recovery_uses_four_explicit_content_markers(self) -> None:
        required, forbidden = text_expectations({
            "result": {"case": {
                "phase": "recovery", "scenario": "crash-after-checkpoint",
                "fixture": "plain-grapheme", "repetition": 1,
            }}
        })
        self.assertIn("E1C-CKPT-MUST-SURVIVE", required)
        self.assertEqual({
            "E1C-CKPT-MUST-NOT-RETURN",
            "E1C-CKPT-PREEDIT-FORBIDDEN",
            "E1C-CKPT-QUEUED",
        }, set(forbidden))

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
        self.assertEqual(sum(desktop_required(entry) for entry in entries), 18)

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
            ("validation-matrix-v2.json", validate_e1_c.CORE_BASELINE_HEAD),
            ("discovery-matrix-v1.json", validate_e1_preflight.CORE_COMMIT),
        ):
            with self.subTest(matrix=name):
                matrix = json.loads((PROJECT / "e1" / name).read_text())
                self.assertEqual(matrix["baseline"]["coreCommit"], expected)

    def test_shell_bundle_manifest_covers_loaded_and_excluded_modules(self) -> None:
        inventory = shell_bundle_inventory(PROJECT)
        self.assertTrue(inventory["pass"], inventory)
        self.assertEqual(
            inventory["expectedBundleSha256"],
            "f9b1a52f3ff2e2a3f35eae4366993f40b2035f309509aac0a3b7b6864a8cfeb9",
        )
        excluded = {item["path"]: item["reason"] for item in inventory["excluded"]}
        self.assertEqual(set(excluded), {"editor-shell/recovery-notice.js"})
        self.assertIn("not imported by the E1-C validation page", excluded[
            "editor-shell/recovery-notice.js"
        ])

    def test_shell_bundle_digest_changes_with_one_module_byte(self) -> None:
        inventory = shell_bundle_inventory(PROJECT)
        hashes = {
            item["path"]: item["sourceSha256"] for item in inventory["included"]
        }
        original = shell_bundle_digest(hashes)
        mutated = dict(hashes)
        mutated["editor-shell/editor-client.js"] = "0" + str(
            mutated["editor-shell/editor-client.js"]
        )[1:]
        self.assertNotEqual(shell_bundle_digest(mutated), original)

    def test_shell_bundle_source_and_dist_are_byte_identical(self) -> None:
        inventory = shell_bundle_inventory(PROJECT)
        mismatches = [
            {
                "path": item["path"],
                "sourceSha256": item["sourceSha256"],
                "distSha256": item["distSha256"],
            }
            for item in inventory["included"]
            if item["sourceSha256"] != item["distSha256"]
        ]
        self.assertEqual([], mismatches, f"source/dist shell divergence: {mismatches}")

    def test_shell_bundle_diagnoses_source_dist_divergence_by_side(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            clone = Path(directory)
            for name in ("e1", "editor-shell", "input", "sdk", "reader-shell"):
                shutil.copytree(PROJECT / name, clone / name)
            (clone / "web").mkdir()
            shutil.copy2(
                PROJECT / "web" / "e1-editor-validation-app.js",
                clone / "web" / "e1-editor-validation-app.js",
            )
            (clone / "dist").mkdir()
            shutil.copytree(PROJECT / "dist" / "editor-shell", clone / "dist" / "editor-shell")
            shutil.copytree(PROJECT / "dist" / "input", clone / "dist" / "input")
            target = clone / "editor-shell" / "editor-client.js"
            target.write_bytes(target.read_bytes() + b" ")
            inventory = shell_bundle_inventory(clone)
        self.assertFalse(inventory["pass"])
        self.assertIn({
            "path": "editor-shell/editor-client.js",
            "side": "source",
            "observed": inventory["included"][0]["sourceSha256"],
            "expected": inventory["included"][0]["expectedSha256"],
        }, inventory["differences"])

    def test_v2_workspace_preflight_binds_the_shell_bundle(self) -> None:
        matrix = json.loads(MATRIX_V2.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline"
            baseline.mkdir()
            (baseline / "core-status-before.txt").write_text("\n".join([
                validate_e1_c.CORE_BASELINE_HEAD,
                *validate_e1_c.CORE_BASELINE_STATUS,
                "",
            ]))
            available = {"available": True, "returnCode": 0}
            with mock.patch.object(validate_e1_c, "command_version", return_value=available):
                matched = workspace_preflight(PROJECT, root, matrix, "before")
                stale = json.loads(json.dumps(matrix))
                stale["baseline"]["shellBundleSha256"] = "00" * 32
                mismatched = workspace_preflight(PROJECT, root, stale, "before")
        self.assertTrue(matched["profile"]["artifacts"]["shellBundle"]["pass"])
        self.assertTrue(matched["pass"])
        self.assertFalse(mismatched["profile"]["artifacts"]["shellBundle"]["pass"])
        self.assertFalse(mismatched["pass"])


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

    def bind(self, cases: list[dict], matrix: dict | None = None):
        with mock.patch.object(
            validate_e1_c, "profile_inventory", return_value=dict(self.LIVE),
        ):
            return validate_e1_c.artifact_binding(cases, PROJECT, matrix)

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

    def test_v2_binding_requires_the_per_case_shell_bundle_hash(self) -> None:
        shell_hash = "ee" * 32
        matrix = {"baseline": {"shellBundleSha256": shell_hash}}
        live = {**self.LIVE, "shellBundleSha256": shell_hash}
        missing = self.case(dict(self.LIVE))
        present = self.case(dict(self.LIVE))
        present["result"]["artifact"]["shellBundleSha256"] = shell_hash
        with mock.patch.object(validate_e1_c, "profile_inventory", return_value=live):
            self.assertFalse(validate_e1_c.artifact_binding([missing], PROJECT, matrix)["pass"])
            self.assertTrue(validate_e1_c.artifact_binding([present], PROJECT, matrix)["pass"])


if __name__ == "__main__":
    unittest.main()
