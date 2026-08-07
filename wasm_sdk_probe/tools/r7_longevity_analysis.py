#!/usr/bin/env python3
"""Pure R7-D longevity analysis using the preregistered memory gates."""

from __future__ import annotations

import math
import statistics
from typing import Any


def available(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def preferred_process_bytes(sample: dict[str, Any]) -> int | float | None:
    """Prefer PSS, fall back to RSS, and never turn unavailable into zero."""
    if available(sample.get("pssBytes")):
        return sample["pssBytes"]
    if available(sample.get("rssBytes")):
        return sample["rssBytes"]
    return None


def block_medians(values: list[int | float], block_size: int) -> list[float]:
    if block_size < 1:
        raise ValueError("block_size must be positive")
    return [
        float(statistics.median(values[offset:offset + block_size]))
        for offset in range(0, len(values), block_size)
        if len(values[offset:offset + block_size]) == block_size
    ]


def robust_slope(values: list[int | float]) -> float | None:
    """Return the Theil-Sen median slope in bytes per block."""
    if len(values) < 2:
        return None
    slopes = [
        (float(values[j]) - float(values[i])) / (j - i)
        for i in range(len(values))
        for j in range(i + 1, len(values))
    ]
    return float(statistics.median(slopes))


def _continuous_growth(blocks: list[float], limit: float) -> bool:
    if len(blocks) < 4:
        return False
    deltas = [blocks[index] - blocks[index - 1] for index in range(1, len(blocks))]
    return any(all(delta > limit for delta in deltas[offset:offset + 3])
               for offset in range(len(deltas) - 2))


def _series(samples: list[dict[str, Any]], key: str) -> list[float]:
    return [float(sample[key]) for sample in samples if available(sample.get(key))]


def analyse_memory(samples: list[dict[str, Any]], thresholds: dict[str, Any]) -> dict[str, Any]:
    """Analyse post-close lifecycle samples against one browser threshold row."""
    post_close = [sample for sample in samples if sample.get("checkpoint") == "post-close"]
    post_close.sort(key=lambda item: (item.get("cycle", 0), item.get("monotonicSeconds", 0)))
    # Only one process sample per completed cycle is used for the cycle gate.
    per_cycle: dict[int, dict[str, Any]] = {}
    for sample in post_close:
        if isinstance(sample.get("cycle"), int):
            per_cycle[sample["cycle"]] = sample
    ordered = [per_cycle[cycle] for cycle in sorted(per_cycle)]
    process_values = [value for sample in ordered
                      if (value := preferred_process_bytes(sample)) is not None]
    warmup = int(thresholds["warmupCycles"])
    block_size = int(thresholds["blockSize"])
    analysed_process = process_values[warmup:]
    blocks = block_medians(analysed_process, block_size)
    slope = robust_slope(blocks)
    growth = (blocks[-1] - blocks[0]) if len(blocks) >= 2 else None
    growth_ratio = (growth / blocks[0]) if growth is not None and blocks[0] > 0 else None

    process_gate = {
        "metric": "pss-preferred-rss-fallback",
        "available": len(process_values) == len(ordered) and bool(process_values),
        "cycleSamples": len(process_values),
        "warmupCycles": warmup,
        "blockSize": block_size,
        "blockMediansBytes": blocks,
        "robustSlopeBytesPerBlock": slope,
        "postCloseGrowthBytes": growth,
        "postCloseGrowthRatio": growth_ratio,
        "continuousThreeBlockGrowth": _continuous_growth(
            blocks, float(thresholds["maxBlockMedianSlopeBytes"])
        ),
    }
    process_gate["pass"] = (
        process_gate["available"]
        and len(ordered) >= int(thresholds["cycleCount"])
        and len(blocks) >= 2
        and growth is not None
        and growth <= float(thresholds["maxPostCloseGrowthBytes"])
        and growth_ratio is not None
        and growth_ratio <= float(thresholds["maxPostCloseGrowthRatio"])
        and slope is not None
        and slope <= float(thresholds["maxBlockMedianSlopeBytes"])
        and not process_gate["continuousThreeBlockGrowth"]
    )

    wasm_values = _series(ordered[warmup:], "wasmHeapBytes")
    wasm_blocks = block_medians(wasm_values, block_size) if wasm_values else []
    wasm_steps = [wasm_blocks[index] - wasm_blocks[index - 1]
                  for index in range(1, len(wasm_blocks))]
    wasm_gate = {
        "status": "checked" if len(wasm_values) == len(ordered[warmup:]) and wasm_values
        else "unavailable",
        "blockMediansBytes": wasm_blocks,
        "maxStepBytes": max(wasm_steps, default=None),
        "pass": None,
    }
    if wasm_gate["status"] == "checked":
        wasm_gate["pass"] = (
            (wasm_gate["maxStepBytes"] or 0) <= float(thresholds["maxWasmHeapStepBytes"])
            and not _continuous_growth(wasm_blocks, 0)
        )

    worker_values = [sample.get("workersAfterClose") for sample in ordered]
    worker_gate = {
        "available": bool(worker_values) and all(isinstance(value, int) for value in worker_values),
        "maximum": max(worker_values) if worker_values and all(isinstance(value, int) for value in worker_values) else None,
    }
    worker_gate["pass"] = worker_gate["available"] and (
        worker_gate["maximum"] <= int(thresholds["maxWorkersAfterClose"])
    )

    tile_values = _series(ordered, "tileCacheBytes")
    tile_gate = {
        "status": "checked" if len(tile_values) == len(ordered) and tile_values else "unavailable",
        "maximumBytes": max(tile_values, default=None),
        "lastBytes": tile_values[-1] if tile_values else None,
        "pass": (tile_values[-1] == 0) if len(tile_values) == len(ordered) and tile_values else None,
    }

    return {
        "schemaVersion": 1,
        "cycleCount": len(ordered),
        "process": process_gate,
        "wasm": wasm_gate,
        "workers": worker_gate,
        "tileCache": tile_gate,
        # Missing optional instrumentation is explicitly recorded but does not
        # turn an otherwise observable process/Worker gate into a false pass.
        "pass": process_gate["pass"] and worker_gate["pass"]
        and wasm_gate["pass"] is not False and tile_gate["pass"] is not False,
    }

