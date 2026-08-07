from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from validate_r8_b import BASE_NEGATIVES, decide, repetition_checks  # noqa: E402


class R8BGateTest(unittest.TestCase):
    def test_repetition_checks_require_three_cold_warm_and_recovery(self) -> None:
        topologies = []
        for topology in ("t0", "t1"):
            cases = [{"caseId": f"{transport}-{mode}-{number}", "pass": True}
                     for transport in ("identity", "gzip")
                     for mode in ("cold", "warm") for number in range(1, 4)]
            negative_names = (*BASE_NEGATIVES, *(("no-cors", "no-corp") if topology == "t1" else ()))
            cases.extend({"caseId": f"negative-{name}", "pass": True,
                          "workersStarted": 0, "documentMutations": 0}
                         for name in negative_names)
            cases.append({"caseId": "known-good-recovery", "pass": True})
            if topology == "t0":
                cases.extend([
                    {"caseId": "fidelity-restart", "pass": True},
                    {"caseId": "handshake-mismatch", "pass": True, "workersStarted": 1},
                    {"caseId": "font-full-fidelity", "pass": True,
                     "policy": "full-fidelity"},
                ])
            topologies.append({"topology": topology, "cases": cases})
        checks = repetition_checks({"topologies": topologies})
        self.assertTrue(all(checks.values()))
        topologies[0]["cases"] = [item for item in topologies[0]["cases"]
                                    if item["caseId"] != "gzip-warm-3"]
        self.assertFalse(repetition_checks({"topologies": topologies})["t0-gzip-warm3"])

    def test_decision_never_hides_safety_failure_or_partial_gap(self) -> None:
        self.assertEqual(decide(False, []), "STOP")
        self.assertEqual(decide(True, ["brotli unavailable"]), "PARTIAL_GO")
        self.assertEqual(decide(True, []), "GO")


if __name__ == "__main__":
    unittest.main()
