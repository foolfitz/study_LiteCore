from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from validate_r8_d import (  # noqa: E402
    compatibility_check,
    decide,
    longevity_check,
    performance_summary,
    percentile,
    release_binding,
    statistics,
)

EXPECTED_IDENTITIES = {
    "r8b-standard": "id-a", "r8b-full-fidelity": "id-full",
    "r8c-A": "id-a", "r8c-B": "id-b", "r8c-C": "id-c",
}


def write_bound_evidence(root: Path) -> None:
    """The six families R8-D consumes, each naming the current release."""
    slots = {"A": "id-a", "B": "id-b", "C": "id-c"}
    for browser in ("chrome", "firefox"):
        for name, value in (
            ("compatibility", {"releaseId": "id-a"}),
            ("longevity", {"releaseIds": slots}),
        ):
            path = root / "production" / name / browser / "summary.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value), encoding="utf-8")
    delivery = root / "delivery" / "summary.json"
    delivery.parent.mkdir(parents=True, exist_ok=True)
    delivery.write_text(json.dumps({"bundles": {"releases": [
        {"policy": "standard", "releaseId": "id-a"},
        {"policy": "full-fidelity", "releaseId": "id-full"},
    ]}}), encoding="utf-8")
    service_worker = root / "service-worker" / "summary.json"
    service_worker.parent.mkdir(parents=True, exist_ok=True)
    service_worker.write_text(json.dumps({"releaseSet": {"index": {"releases": [
        {"slot": slot, "releaseId": value} for slot, value in slots.items()
    ]}}}), encoding="utf-8")


class R8DGateTest(unittest.TestCase):
    def test_decision_distinguishes_local_delivery_from_full_go(self) -> None:
        self.assertEqual(decide(False, False), "STOP")
        self.assertEqual(decide(True, False), "PARTIAL_GO_LOCAL_DELIVERY")
        self.assertEqual(decide(True, True), "GO")

    def test_statistics_are_deterministic(self) -> None:
        self.assertEqual(percentile([1, 2, 3, 4], 0.5), 2.5)
        self.assertEqual(statistics([1, 2, 3])["p90"], 2.8)
        self.assertEqual(statistics([])["count"], 0)

    def test_compatibility_requires_closed_active_release_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "summary.json"
            path.write_text(json.dumps({
                "releaseId": "release-a", "documentCount": 2,
                "workersStarted": 10, "maxWorkersPerPage": 3,
                "cases": [{"pass": True}, {"pass": True}], "pass": True,
            }), encoding="utf-8")
            self.assertTrue(compatibility_check(path, "release-a", 2)["pass"])
            value = json.loads(path.read_text(encoding="utf-8"))
            value["releaseId"] = "mixed-release"
            path.write_text(json.dumps(value), encoding="utf-8")
            self.assertFalse(compatibility_check(path, "release-a", 2)["pass"])

    def test_longevity_requires_duration_transitions_and_bounded_generations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "summary.json"
            path.write_text(json.dumps({
                "durationMinutes": 30, "workerGenerations": 3,
                "maxWorkerGenerationsPerPage": 3,
                "transitions": ["active-a", "active-b", "offline-a-runtime", "rollback-a"],
                "samples": [{}, {}], "cycles": [{"pass": True}], "pass": True,
            }), encoding="utf-8")
            self.assertTrue(longevity_check(path, 30, "firefox")["pass"])
            value = json.loads(path.read_text(encoding="utf-8"))
            value["workerGenerations"] = 5
            path.write_text(json.dumps(value), encoding="utf-8")
            self.assertFalse(longevity_check(path, 30, "firefox")["pass"])

    def test_release_binding_fails_on_stale_and_on_unnamed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_bound_evidence(root)
            bound = release_binding(root, root, expected=EXPECTED_IDENTITIES)
            self.assertTrue(bound["pass"])
            self.assertEqual(bound["boundFamilies"], 6)

            # A superseded release must fail even though the evidence itself
            # still says pass -- this is the four-day drift of finding 027.
            path = root / "service-worker" / "summary.json"
            path.write_text(json.dumps({"releaseSet": {"index": {"releases": [
                {"slot": "A", "releaseId": "id-superseded"},
                {"slot": "B", "releaseId": "id-b"}, {"slot": "C", "releaseId": "id-c"},
            ]}}}), encoding="utf-8")
            stale = release_binding(root, root, expected=EXPECTED_IDENTITIES)
            self.assertFalse(stale["pass"])
            self.assertEqual(stale["supersededFamilies"], 1)

            # Recording no release at all must fail too, not default into a
            # pass: an unattributable result is not weaker proof, it is none.
            path.write_text(json.dumps({"pass": True}), encoding="utf-8")
            silent = release_binding(root, root, expected=EXPECTED_IDENTITIES)
            self.assertFalse(silent["pass"])
            self.assertEqual(silent["unattributableFamilies"], 1)

    def test_performance_summary_skips_expected_null_case_details(self) -> None:
        delivery = {"browsers": {"chrome": {"topologies": [{
            "topology": "t0",
            "cases": [
                {"pass": True, "runnerElapsedMs": 10, "verified": None, "document": None},
                {"pass": True, "runnerElapsedMs": 20,
                 "verified": {"durationMs": 4}, "document": {"openMs": 6}},
            ],
        }]}}}
        summary = performance_summary(delivery, {"browsers": {}})
        self.assertEqual(summary["chrome-t0"]["directDeliveryMs"]["count"], 2)
        self.assertEqual(summary["chrome-t0"]["manifestAndArtifactVerifyMs"]["count"], 1)
        self.assertEqual(summary["chrome-t0"]["documentOpenMs"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
