from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import validate_finding_012_native_26_8 as validator


CORE_COMMIT = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"


class Finding012Native268Test(unittest.TestCase):
    def test_cross_runtime_reproduction_routes_to_core_fix(self) -> None:
        result = validator.decide_same_commit(
            native_decision="NATIVE_LOK_REPRODUCED",
            wasm_decisions={
                "chrome": "WASM_DOCUMENT_DESTROY_BLOCKED",
                "firefox": "WASM_DOCUMENT_DESTROY_BLOCKED",
            },
            native_core_commit=CORE_COMMIT,
            expected_core_commit=CORE_COMMIT,
        )

        self.assertEqual(result["decision"], "CROSS_RUNTIME_DOCUMENT_DESTROY_REPRODUCED")
        self.assertEqual(result["candidateLayer"], "shared-libreofficekit-document-destroy")
        self.assertEqual(result["nextAction"], "core-fix")
        self.assertTrue(result["pass"])
        self.assertFalse(result["fixed"])
        self.assertFalse(result["r7Pass"])

    def test_native_non_reproduction_routes_to_wasm_fix(self) -> None:
        result = validator.decide_same_commit(
            native_decision="NOT_REPRODUCED_SYSTEM_NATIVE",
            wasm_decisions={
                "chrome": "WASM_DOCUMENT_DESTROY_BLOCKED",
                "firefox": "WASM_DOCUMENT_DESTROY_BLOCKED",
            },
            native_core_commit=CORE_COMMIT,
            expected_core_commit=CORE_COMMIT,
        )

        self.assertEqual(result["decision"], "EMSCRIPTEN_SPECIFIC_DOCUMENT_DESTROY")
        self.assertEqual(result["candidateLayer"], "emscripten-document-teardown")
        self.assertEqual(result["nextAction"], "wasm-fix")
        self.assertTrue(result["pass"])

    def test_commit_mismatch_is_inconclusive(self) -> None:
        result = validator.decide_same_commit(
            native_decision="NOT_REPRODUCED_SYSTEM_NATIVE",
            wasm_decisions={
                "chrome": "WASM_DOCUMENT_DESTROY_BLOCKED",
                "firefox": "WASM_DOCUMENT_DESTROY_BLOCKED",
            },
            native_core_commit="different",
            expected_core_commit=CORE_COMMIT,
        )

        self.assertEqual(result["decision"], "INCONCLUSIVE_VERSION_MISMATCH")
        self.assertFalse(result["pass"])


if __name__ == "__main__":
    unittest.main()
