from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import validate_finding_012_attribution as attribution


class Finding012AttributionTest(unittest.TestCase):
    def test_native_reproduction_requires_destroy_entry_without_return(self) -> None:
        result = attribution.classify_native({
            "t2-original": [
                {"outcome": "timeout", "stages": ["document-destroy-enter"]},
            ],
            "t2-image-unwrapped": [
                {
                    "outcome": "close-pass",
                    "stages": ["document-destroy-enter", "document-destroy-return"],
                },
            ],
        })

        self.assertEqual(result["decision"], "NATIVE_LOK_REPRODUCED")
        self.assertTrue(result["pass"])

    def test_native_non_reproduction_is_version_scoped(self) -> None:
        result = attribution.classify_native({
            "t2-original": [
                {
                    "outcome": "close-pass",
                    "stages": ["document-destroy-enter", "document-destroy-return"],
                },
            ],
            "t2-image-unwrapped": [
                {
                    "outcome": "close-pass",
                    "stages": ["document-destroy-enter", "document-destroy-return"],
                },
            ],
        })

        self.assertEqual(result["decision"], "NOT_REPRODUCED_SYSTEM_NATIVE")
        self.assertTrue(result["pass"])
        self.assertIn("version", result["notValidated"])

    def test_wasm_stage_boundary_confirms_destroy_call_is_entered(self) -> None:
        result = attribution.classify_wasm({
            "t2-original": [
                {"outcome": "timeout", "stages": ["document-destroy-enter"]},
            ],
            "t2-image-unwrapped": [
                {
                    "outcome": "close-pass",
                    "stages": ["document-destroy-enter", "document-destroy-return"],
                },
            ],
        })

        self.assertEqual(result["decision"], "WASM_DOCUMENT_DESTROY_BLOCKED")
        self.assertTrue(result["pass"])

    def test_combined_result_does_not_overclaim_core_root_cause(self) -> None:
        result = attribution.combine_attribution(
            {"decision": "NOT_REPRODUCED_SYSTEM_NATIVE", "pass": True},
            {
                "chrome": {"decision": "WASM_DOCUMENT_DESTROY_BLOCKED", "pass": True},
                "firefox": {"decision": "WASM_DOCUMENT_DESTROY_BLOCKED", "pass": True},
            },
        )

        self.assertEqual(result["decision"], "DOCUMENT_DESTROY_BOUNDARY_CONFIRMED")
        self.assertEqual(result["candidateLayer"], "wasm-build-or-version-specific-document-destroy")
        self.assertFalse(result["fixed"])
        self.assertFalse(result["r7Pass"])
        self.assertIn("same-commit native LibreOfficeKit", result["notValidated"])


if __name__ == "__main__":
    unittest.main()
