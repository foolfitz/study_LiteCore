#!/usr/bin/env python3
"""Judge SPEC E2-C phase D4 offline, against thresholds frozen before it ran.

Every number here comes from `e2/validation-matrix-v1.json`, which froze them on
2026-08-15.  They are numbers rather than "no continuous growth" because an
adversarial review pointed out that one GC dip makes a leaking curve look flat,
and that PSS noise can then explain any result at all.

`notValidated` is a THIRD answer, never folded into pass or fail: the matrix's
`onUnavailable` for the memory cell is PARTIAL, so a figure the browser will not
report produces PARTIAL and says which half is missing.

Usage:
  analyze_e2_c_d4.py RUN_DIR [RUN_DIR ...] [--regression F] [--output F]
  analyze_e2_c_d4.py --self-test RUN_DIR
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

MB = 1024 * 1024
# Frozen in e2/validation-matrix-v1.json, cell d4-memory.
PSS_SLOPE_LIMIT = 8 * MB          # per session
WASM_SLOPE_LIMIT = 2 * MB         # per session
WASM_ABSOLUTE_LIMIT = 20 * MB     # tenth cycle vs first
MAX_GENERATIONS = 3               # cell d4-sessions
EXPECTED_CYCLES = 10


def slope(values: list[float]) -> float | None:
    """Least squares slope over the cycle index.

    Reported per session, which is what the threshold is written in.  Needs at
    least two points; one sample has no slope and must not be reported as zero.
    """
    if len(values) < 2:
        return None
    n = len(values)
    xs = list(range(1, n + 1))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denominator


def per_cycle_memory(samples: list[dict]) -> dict[int, dict]:
    """The smaller of each cycle's two samples, as the matrix requires.

    Quiescence and three seconds later; the smaller one is the honest reading
    because the later sample is the one a collector has had a chance to act on.
    """
    by_cycle: dict[int, dict] = {}
    for sample in samples:
        cycle = sample.get("cycle")
        checkpoint = sample.get("checkpoint")
        if not isinstance(cycle, int) or cycle < 1:
            continue
        if checkpoint not in ("quiescent", "settled"):
            continue
        entry = by_cycle.setdefault(cycle, {"pss": [], "rss": [], "wasm": [],
                                            "workers": [], "handles": []})
        if sample.get("pssBytes") is not None:
            entry["pss"].append(sample["pssBytes"])
        if sample.get("rssBytes") is not None:
            entry["rss"].append(sample["rssBytes"])
        if sample.get("wasmHeapBytes") is not None:
            entry["wasm"].append(sample["wasmHeapBytes"])
        entry["workers"].append(sample.get("activeWorkers"))
        entry["handles"].append(sample.get("activeHandles"))
    return {
        cycle: {
            "pssBytes": min(entry["pss"]) if entry["pss"] else None,
            "rssBytes": min(entry["rss"]) if entry["rss"] else None,
            "wasmHeapBytes": min(entry["wasm"]) if entry["wasm"] else None,
            "activeWorkers": entry["workers"],
            "activeHandles": entry["handles"],
        }
        for cycle, entry in sorted(by_cycle.items())
    }


def judge_run(run: Path) -> dict:
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    cycles = result.get("cycles") or []
    memory = per_cycle_memory(result.get("samples") or [])

    generations = [cycle.get("workerGenerations") for cycle in cycles]
    sessions = {
        "cycles": len(cycles),
        "expected": EXPECTED_CYCLES,
        "errors": [cycle.get("error") for cycle in cycles if cycle.get("error")],
        "generations": generations,
        "pass": (len(cycles) == EXPECTED_CYCLES
                 and not any(cycle.get("error") for cycle in cycles)
                 and all(isinstance(value, int) and value <= MAX_GENERATIONS
                         for value in generations)),
    }

    worker_readings = [value for entry in memory.values()
                       for value in entry["activeWorkers"]]
    handle_readings = [value for entry in memory.values()
                       for value in entry["activeHandles"]]
    residuals = {
        "workerReadings": worker_readings,
        "handleReadings": handle_readings,
        "pass": bool(worker_readings) and bool(handle_readings)
                and all(value == 0 for value in worker_readings)
                and all(value == 0 for value in handle_readings),
    }

    pss = [entry["pssBytes"] for entry in memory.values()
           if entry["pssBytes"] is not None]
    wasm = [entry["wasmHeapBytes"] for entry in memory.values()
            if entry["wasmHeapBytes"] is not None]
    pss_slope = slope(pss)
    wasm_slope = slope(wasm)
    memory_report = {
        "pssPerCycleBytes": pss,
        "pssSlopeBytesPerSession": pss_slope,
        "pssSlopeLimit": PSS_SLOPE_LIMIT,
        # Reported, not a cell criterion.  The matrix writes an absolute limit
        # for the WASM heap only; PREDICTION.md's P-D4-3 added one for PSS as
        # well, so the number has to exist for that prediction to be scorable --
        # and it is scored against what was written, not against what the cell
        # requires.
        "pssAbsoluteGrowthBytes": (pss[-1] - pss[0]) if len(pss) >= 2 else None,
        "pssPass": pss_slope is not None and pss_slope <= PSS_SLOPE_LIMIT,
        "pssStatus": "notValidated" if pss_slope is None else (
            "pass" if pss_slope <= PSS_SLOPE_LIMIT else "fail"),
        "wasmHeapPerCycleBytes": wasm,
        "wasmSlopeBytesPerSession": wasm_slope,
        "wasmAbsoluteGrowthBytes": (wasm[-1] - wasm[0]) if len(wasm) >= 2 else None,
        # The measurement the product cannot make.  Nothing in sdk-worker.js
        # reports a WASM heap size, and R7-D's page has carried a
        # `wasmHeapBytes: null` for as long as it has existed -- so this is
        # notValidated for a reason that predates this phase, and the fix is an
        # engine-side field, which is a relink queue item.
        "wasmStatus": "notValidated" if wasm_slope is None else (
            "pass" if (wasm_slope <= WASM_SLOPE_LIMIT
                       and (wasm[-1] - wasm[0]) <= WASM_ABSOLUTE_LIMIT)
            else "fail"),
    }
    if memory_report["wasmStatus"] == "notValidated":
        memory_report["verdict"] = ("PARTIAL" if memory_report["pssPass"]
                                    else "FAIL")
        memory_report["why"] = (
            "no WASM heap figure is obtainable from the product; PSS decided "
            "alone, which the matrix calls PARTIAL, never a pass")
    else:
        memory_report["verdict"] = (
            "PASS" if memory_report["pssPass"] and memory_report["wasmStatus"] == "pass"
            else "FAIL")

    return {
        "run": str(run),
        "browser": result.get("browserName"),
        "profile": result.get("artifact", {}).get("profile"),
        "wasmSha256": result.get("artifact", {}).get("wasmSha256"),
        "attributionConsistent": result.get("attribution", {}).get("consistent"),
        "complete": result.get("complete"),
        "memoryApi": result.get("memoryApi"),
        "cells": {
            "d4-sessions": sessions,
            "d4-residuals": residuals,
            "d4-memory": memory_report,
        },
        # PASS only when both fully-decidable cells pass and memory is not
        # merely PARTIAL.  A run whose memory is PARTIAL is reported as PARTIAL
        # at the top too; the matrix's onFailure for the other cells is STOP.
        "verdict": (
            "FAIL" if not (sessions["pass"] and residuals["pass"]
                           and result.get("complete")
                           and result.get("attribution", {}).get("consistent"))
            else memory_report["verdict"]),
    }


def summarise(runs: list[dict], regression: dict | None) -> dict:
    verdicts = [run["verdict"] for run in runs]
    if regression is not None and not regression.get("pass"):
        overall = "FAIL"
    elif "FAIL" in verdicts:
        overall = "FAIL"
    elif "PARTIAL" in verdicts:
        overall = "PARTIAL"
    else:
        overall = "PASS"
    return {
        "schemaVersion": 1,
        "release": "spec-e2c-d4",
        "predictionFile": "findings/evidence/sdk-e2/e2-c-validation/d4/PREDICTION.md",
        "runs": runs,
        "regression": regression,
        "browsersAgree": len(set(verdicts)) == 1 and len(verdicts) >= 2,
        "verdict": overall,
    }


def self_test(run: Path) -> int:
    failures: list[str] = []
    ran: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        ran.append(name)
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    baseline = judge_run(run)
    check("the recorded run is judged at all", bool(baseline["cells"]))

    raw = json.loads((run / "result.json").read_text(encoding="utf-8"))

    def rejudge(mutate) -> dict:
        cloned = copy.deepcopy(raw)
        mutate(cloned)
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "result.json").write_text(json.dumps(cloned))
            return judge_run(target)

    def set_generation(cloned, value):
        for cycle in cloned["cycles"]:
            cycle["workerGenerations"] = value

    def leak_worker(cloned):
        for sample in cloned["samples"]:
            if sample.get("checkpoint") == "settled":
                sample["activeWorkers"] = 1

    def leak_handle(cloned):
        for sample in cloned["samples"]:
            if sample.get("checkpoint") == "settled":
                sample["activeHandles"] = 2

    def grow_pss(cloned):
        step = 0
        for sample in cloned["samples"]:
            if sample.get("cycle"):
                sample["pssBytes"] = (sample.get("pssBytes") or 0) + step * 20 * MB
                step += 1

    def give_wasm_heap(cloned, growth):
        step = 0
        for sample in cloned["samples"]:
            if sample.get("cycle"):
                sample["wasmHeapBytes"] = 64 * MB + step * growth
                step += 1

    def drop_a_cycle(cloned):
        cloned["cycles"] = cloned["cycles"][:-1]

    check("a fourth generation stops it passing",
          rejudge(lambda c: set_generation(c, 4))["cells"]["d4-sessions"]["pass"] is False)
    check("a residual worker stops it passing",
          rejudge(leak_worker)["cells"]["d4-residuals"]["pass"] is False)
    check("a residual handle stops it passing",
          rejudge(leak_handle)["cells"]["d4-residuals"]["pass"] is False)
    check("a PSS curve that climbs 20 MB per session fails the memory cell",
          rejudge(grow_pss)["cells"]["d4-memory"]["pssPass"] is False)
    check("a missing cycle stops it passing",
          rejudge(drop_a_cycle)["cells"]["d4-sessions"]["pass"] is False)
    # The third answer has to be reachable in BOTH directions, or notValidated
    # is just a nicer word for "we did not look".
    check("a measurable, flat WASM heap leaves notValidated behind",
          rejudge(lambda c: give_wasm_heap(c, 0))["cells"]["d4-memory"]["wasmStatus"]
          == "pass")
    check("a measurable WASM heap growing 4 MB per session fails",
          rejudge(lambda c: give_wasm_heap(c, 4 * MB))["cells"]["d4-memory"]["wasmStatus"]
          == "fail")
    check("with no WASM figure the memory cell is PARTIAL, never PASS",
          baseline["cells"]["d4-memory"]["verdict"] in ("PARTIAL", "FAIL"))
    check("a failed regression sweep fails the summary",
          summarise([baseline], {"pass": False})["verdict"] == "FAIL")

    print(f"\nself-test: {len(ran) - len(failures)}/{len(ran)} "
          "checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--regression", type=Path, default=None)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.self_test:
        return self_test(args.runs[0])

    regression = (json.loads(args.regression.read_text(encoding="utf-8"))
                  if args.regression else None)
    summary = summarise([judge_run(run) for run in args.runs], regression)
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if summary["verdict"] in ("PASS", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
