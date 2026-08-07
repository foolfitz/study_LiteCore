import unittest

from tools.validate_finding_012_remediation import decide_remediation


def passing_record() -> dict:
    return {
        "outcome": "close-pass",
        "pass": True,
        "metrics": {
            "pass": True,
            "close": {
                "status": "passed",
                "recovery": {
                    "used": True,
                    "events": [
                        {"event": "document-close-recovery-started"},
                        {"event": "document-close-recovery-complete"},
                    ],
                },
            },
            "workers": {"created": 2, "terminated": 2, "active": 0},
            "handles": {"opened": 1, "closed": 1, "active": 0},
        },
    }


class RemediationDecisionTest(unittest.TestCase):
    def test_two_browsers_three_clean_recoveries_pass(self) -> None:
        result = decide_remediation(
            {
                "chrome": [passing_record() for _ in range(3)],
                "firefox": [passing_record() for _ in range(3)],
            },
            "EMSCRIPTEN_SPECIFIC_DOCUMENT_DESTROY",
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["decision"], "REMEDIATED_BY_BOUNDED_WORKER_RECYCLE")
        self.assertEqual(result["nextAction"], "r7-regression")

    def test_missing_recovery_event_fails(self) -> None:
        record = passing_record()
        record["metrics"]["close"]["recovery"]["events"].pop()
        result = decide_remediation(
            {
                "chrome": [record, passing_record(), passing_record()],
                "firefox": [passing_record() for _ in range(3)],
            },
            "EMSCRIPTEN_SPECIFIC_DOCUMENT_DESTROY",
        )
        self.assertFalse(result["pass"])
        self.assertEqual(result["decision"], "REMEDIATION_INCOMPLETE")

    def test_missing_browser_fails(self) -> None:
        result = decide_remediation(
            {"chrome": [passing_record() for _ in range(3)]},
            "EMSCRIPTEN_SPECIFIC_DOCUMENT_DESTROY",
        )
        self.assertFalse(result["pass"])

    def test_prior_attribution_must_match(self) -> None:
        result = decide_remediation(
            {
                "chrome": [passing_record() for _ in range(3)],
                "firefox": [passing_record() for _ in range(3)],
            },
            "INCONCLUSIVE",
        )
        self.assertFalse(result["pass"])
        self.assertEqual(result["decision"], "ATTRIBUTION_MISMATCH")


if __name__ == "__main__":
    unittest.main()
