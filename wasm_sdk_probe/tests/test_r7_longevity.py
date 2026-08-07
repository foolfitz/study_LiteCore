from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from tools.r7_longevity_analysis import analyse_memory, block_medians, preferred_process_bytes, robust_slope
from tools.run_r7_longevity import merge_fresh_metrics, offset_cycle_state


THRESHOLDS = {
    "warmupCycles": 10,
    "blockSize": 10,
    "cycleCount": 50,
    "maxPostCloseGrowthBytes": 512 * 1024 * 1024,
    "maxPostCloseGrowthRatio": 0.35,
    "maxBlockMedianSlopeBytes": 64 * 1024 * 1024,
    "maxWasmHeapStepBytes": 256 * 1024 * 1024,
    "maxWorkersAfterClose": 0,
}


def samples(step: int = 1024 * 1024, *, wasm: bool = True, plateau: bool = True) -> list[dict]:
    result = []
    for cycle in range(1, 51):
        item = {
            "checkpoint": "post-close", "cycle": cycle,
            "monotonicSeconds": float(cycle),
            "pssBytes": 1024 * 1024 * 1024 + (min(cycle, 20) if plateau else cycle) * step,
            "rssBytes": 2 * 1024 * 1024 * 1024,
            "workersAfterClose": 0,
        }
        if wasm:
            item["wasmHeapBytes"] = 1024 * 1024 * 1024
        result.append(item)
    return result


class LongevityAnalysisTest(unittest.TestCase):
    def test_helpers(self) -> None:
        self.assertEqual(preferred_process_bytes({"pssBytes": 7, "rssBytes": 9}), 7)
        self.assertIsNone(preferred_process_bytes({"pssBytes": None, "rssBytes": None}))
        self.assertEqual(block_medians([1, 2, 3, 4], 2), [1.5, 3.5])
        self.assertEqual(robust_slope([10, 20, 30]), 10)

    def test_plateau_passes(self) -> None:
        result = analyse_memory(samples(), THRESHOLDS)
        self.assertTrue(result["pass"])
        self.assertEqual(result["process"]["metric"], "pss-preferred-rss-fallback")

    def test_monotonic_leak_fails(self) -> None:
        result = analyse_memory(samples(step=80 * 1024 * 1024, plateau=False), THRESHOLDS)
        self.assertFalse(result["pass"])
        self.assertFalse(result["process"]["pass"])

    def test_missing_optional_metrics_stay_unavailable(self) -> None:
        result = analyse_memory(samples(wasm=False), THRESHOLDS)
        self.assertEqual(result["wasm"]["status"], "unavailable")
        self.assertIsNone(result["wasm"]["maxStepBytes"])
        self.assertTrue(result["pass"])

    def test_fresh_batch_cycle_offsets_and_exact_aggregation(self) -> None:
        self.assertEqual(
            offset_cycle_state({"cycle": 10, "block": 1}, 20),
            {"cycle": 30, "block": 3},
        )
        batches = []
        for batch in range(1, 11):
            metrics = {
                "scenario": "s2-fresh", "pass": True,
                "lifecycle": [{"cycle": cycle, "pass": True} for cycle in range(1, 6)],
                "workers": {"created": 5, "terminated": 5, "crashes": 0, "active": 0},
                "handles": {"opened": 5, "closed": 5, "active": 0},
                "sampleState": {"cycle": 5, "block": 1},
            }
            batches.append({"batch": batch, "metrics": metrics, "result": f"batch-{batch}.json"})
        merged = merge_fresh_metrics(batches, 50)
        self.assertTrue(merged["pass"])
        self.assertEqual([item["cycle"] for item in merged["lifecycle"]], list(range(1, 51)))
        self.assertEqual(merged["workers"]["created"], 50)
        self.assertEqual(merged["sampleState"]["cycle"], 50)


if __name__ == "__main__":
    unittest.main()
