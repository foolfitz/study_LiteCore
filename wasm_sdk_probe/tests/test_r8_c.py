from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from validate_r8_c import T0_REQUIRED, T1_REQUIRED, decide, topology_checks  # noqa: E402


class R8CGateTest(unittest.TestCase):
    def test_topology_gate_requires_every_frozen_case(self) -> None:
        topologies = []
        for topology, required in (("t0", T0_REQUIRED), ("t1", T1_REQUIRED)):
            topologies.append({
                "topology": topology,
                "pass": True,
                "cases": [
                    {"caseId": case_id, "pass": True, "gatePass": True}
                    for case_id in sorted(required)
                ],
            })
        summary = {"suite": "full", "topologies": topologies}
        self.assertTrue(all(topology_checks(summary, "t0").values()))
        topologies[0]["cases"][0]["gatePass"] = False
        self.assertFalse(topology_checks(summary, "t0")["required-cases"])

    def test_decision_keeps_partial_gap_visible(self) -> None:
        self.assertEqual(decide(False, []), "STOP")
        self.assertEqual(decide(True, ["true quota unavailable"]), "PARTIAL_GO")
        self.assertEqual(decide(True, []), "GO")


if __name__ == "__main__":
    unittest.main()
