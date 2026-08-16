#!/usr/bin/env python3
"""Judge the D4 heap follow-up offline.

The question is not "is there a leak".  It is **whether the product can report
the number at all**, because a relink queue item was opened on the claim that it
cannot -- and a relink mints a new identity.

Criteria: findings/evidence/sdk-e2/e2-c-validation/d4/heap/PREDICTION.md
(P-H1..P-H5 registered before the harness; P-H6..P-H8 in addendum A1, after a
scratch smoke run and before any recorded round).

Three answers, never two: HELD, FAILED, NOT_MEASURED.  A prediction whose data
never arrived is not a prediction that failed, and neither is it one that held.

Usage:
  analyze_e2_c_d4_heap.py RUN_DIR [RUN_DIR ...] [--output F]
  analyze_e2_c_d4_heap.py --self-test RUN_DIR [RUN_DIR ...]
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

MB = 1024 * 1024
# The value the build fixes by construction: -sTOTAL_MEMORY=1GB, no
# ALLOW_MEMORY_GROWTH.  Written here as a constant so that a build which ever
# stops being fixed makes P-H6 fail loudly instead of passing quietly.
FIXED_TOTAL_MEMORY = 1024 * MB
FRESH_SPREAD_LIMIT = 2 * MB       # P-H4 / P-H8
PSS_SLOPE_DELTA_LIMIT = 2 * MB    # P-H5
EXPECTED_CYCLES = 8


def slope(values: list[float]) -> float | None:
    """Least squares slope over the cycle index, per session.

    Same computation as `analyze_e2_c_d4.py`; two points minimum, because one
    sample has no slope and must not be reported as zero.
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
    return sum((x - mean_x) * (y - mean_y)
               for x, y in zip(xs, values)) / denominator


def per_cycle_pss(samples: list[dict]) -> list[int]:
    """The smaller of each cycle's two samples, as the frozen matrix requires."""
    by_cycle: dict[int, list[int]] = {}
    for sample in samples:
        cycle, checkpoint = sample.get("cycle"), sample.get("checkpoint")
        if not isinstance(cycle, int) or cycle < 1:
            continue
        if checkpoint not in ("quiescent", "settled"):
            continue
        if sample.get("pssBytes") is not None:
            by_cycle.setdefault(cycle, []).append(sample["pssBytes"])
    return [min(values) for _, values in sorted(by_cycle.items()) if values]


def load(run: Path) -> dict:
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    result["_run"] = str(run)
    return result


def instances(result: dict) -> dict[str, list[dict]]:
    """Stage events grouped by the engine instance that emitted them.

    The grouping matters: `sbrk` is only meaningfully monotone WITHIN one WASM
    instance, and the fresh arm makes a new one every cycle.
    """
    grouped: dict[str, list[dict]] = {}
    for stage in result.get("stages") or []:
        grouped.setdefault(str(stage.get("engine")), []).append(stage)
    return grouped


def status(condition: bool | None) -> str:
    if condition is None:
        return "NOT_MEASURED"
    return "HELD" if condition else "FAILED"


def judge(results: list[dict]) -> dict:
    debug_runs = [r for r in results if r.get("debug") is True]
    control_runs = [r for r in results if r.get("debug") is False]
    fresh_debug = [r for r in debug_runs if r.get("arm") == "fresh"]
    # Every arm whose engine outlives one cycle.  `shared` (with the search)
    # wedged in both browsers; `shared-nosearch` is the controlled variable that
    # isolated it.  A wedged run is not evidence about memory, so it is
    # EXCLUDED -- and the exclusion is printed, because a silent exclusion reads
    # as coverage.
    shared_all = [r for r in debug_runs
                  if str(r.get("arm") or "").startswith("shared")]
    shared_debug = [r for r in shared_all
                    if not any(c.get("error") for c in (r.get("cycles") or []))]
    shared_wedged = [{
        "run": r["_run"], "browser": r.get("browserName"), "arm": r.get("arm"),
        "firstErrorCycle": next((c.get("cycle") for c in (r.get("cycles") or [])
                                 if c.get("error")), None),
        "errors": [c.get("error", {}).get("code")
                   for c in (r.get("cycles") or []) if c.get("error")],
    } for r in shared_all
        if any(c.get("error") for c in (r.get("cycles") or []))]

    findings: dict[str, dict] = {}

    # ---- P-H1: the number arrives at all ---------------------------------
    per_run = [{
        "run": r["_run"], "browser": r.get("browserName"), "arm": r.get("arm"),
        "stageEvents": len(r.get("stages") or []),
        "allNumeric": all(isinstance(s.get("heapBytes"), (int, float))
                          for s in (r.get("stages") or [])),
    } for r in debug_runs]
    findings["P-H1"] = {
        "claim": "with debug:true, an open yields >=1 stage event carrying a "
                 "numeric heapBytes, in both browsers",
        "runs": per_run,
        "status": status(None if not per_run else
                         all(entry["stageEvents"] >= 1 and entry["allNumeric"]
                             for entry in per_run)),
    }

    # ---- P-H2: every cycle of the fresh arm yields one --------------------
    cycle_reports = []
    for r in fresh_debug:
        cycles = r.get("cycles") or []
        cycle_reports.append({
            "run": r["_run"], "browser": r.get("browserName"),
            "cycles": len(cycles),
            "cyclesWithStageEvents": sum(1 for c in cycles
                                         if (c.get("stageEvents") or 0) >= 1),
            "samplesWithHeap": sum(
                1 for s in (r.get("samples") or [])
                if s.get("wasmHeapBytes") is not None),
        })
    findings["P-H2"] = {
        "claim": "every fresh-arm cycle yields a heap value, so the sampler "
                 "field that has always been null stops being null",
        "runs": cycle_reports,
        "status": status(None if not cycle_reports else all(
            entry["cycles"] == EXPECTED_CYCLES
            and entry["cyclesWithStageEvents"] == EXPECTED_CYCLES
            and entry["samplesWithHeap"] >= EXPECTED_CYCLES
            for entry in cycle_reports)),
    }

    # ---- P-H3 / P-H6: what heapBytes actually is --------------------------
    heap_values = [s.get("heapBytes") for r in debug_runs
                   for s in (r.get("stages") or [])]
    monotone_within_open = all(
        all(a <= b for a, b in zip(events, events[1:]))
        for r in debug_runs
        for events in [[s.get("heapBytes") for s in group]
                       for group in instances(r).values()])
    distinct = sorted({value for value in heap_values
                       if isinstance(value, (int, float))})
    findings["P-H3"] = {
        "claim": "heap values are non-decreasing within one open",
        "status": status(None if not heap_values else monotone_within_open),
        # Said out loud rather than left for a reader to notice: a constant is
        # non-decreasing, so this prediction holding proves nothing on its own.
        "vacuous": len(distinct) <= 1,
        "distinctValues": distinct[:8],
    }
    findings["P-H6"] = {
        "claim": f"heapBytes is exactly {FIXED_TOTAL_MEMORY} everywhere, "
                 "because the build links -sTOTAL_MEMORY=1GB without "
                 "ALLOW_MEMORY_GROWTH",
        "sampleCount": len(heap_values),
        "distinctValues": distinct[:8],
        "status": status(None if not heap_values else
                         all(value == FIXED_TOTAL_MEMORY for value in heap_values)),
    }

    # ---- P-H7: sbrk, the number that can move -----------------------------
    sbrk_reports = []
    monotone = True
    for r in debug_runs:
        for label, group in instances(r).items():
            series = [s.get("sbrk") for s in group
                      if isinstance(s.get("sbrk"), (int, float))]
            if len(series) >= 2 and any(a > b for a, b in zip(series, series[1:])):
                monotone = False
                sbrk_reports.append({"run": r["_run"], "engine": label,
                                     "decreasing": series})
    shared_growth = []
    for r in shared_debug:
        series = [c.get("sbrkAfterCycleBytes") for c in (r.get("cycles") or [])
                  if isinstance(c.get("sbrkAfterCycleBytes"), (int, float))]
        if len(series) >= 2:
            shared_growth.append({
                "run": r["_run"], "browser": r.get("browserName"),
                "first": series[0], "last": series[-1],
                "growthBytes": series[-1] - series[0],
                "slopeBytesPerCycle": slope(series),
            })
    findings["P-H7"] = {
        "claim": "sbrk is non-decreasing within one instance, and in the shared "
                 "arm it is higher after eight documents than after one",
        "decreasingWithinInstance": sbrk_reports,
        "sharedArm": shared_growth,
        "excludedWedgedRuns": shared_wedged,
        "status": status(None if not shared_growth else
                         monotone and all(entry["growthBytes"] > 0
                                          for entry in shared_growth)),
    }

    # ---- P-H4 / P-H8: a fresh instance should look the same every time ----
    def spread(values: list[float]) -> float | None:
        return (max(values) - min(values)) if len(values) >= 2 else None

    fresh_reports = []
    for r in fresh_debug:
        cycles = r.get("cycles") or []
        heaps = [c.get("heapAfterCycleBytes") for c in cycles
                 if isinstance(c.get("heapAfterCycleBytes"), (int, float))]
        sbrks = [c.get("sbrkAfterCycleBytes") for c in cycles
                 if isinstance(c.get("sbrkAfterCycleBytes"), (int, float))]
        fresh_reports.append({
            "run": r["_run"], "browser": r.get("browserName"),
            "heapSpreadBytes": spread(heaps), "sbrkSpreadBytes": spread(sbrks),
            "sbrkPerCycle": sbrks,
        })
    findings["P-H4"] = {
        "claim": "fresh-arm per-cycle heap varies by less than 2 MB",
        "runs": [{k: v for k, v in entry.items() if k != "sbrkPerCycle"}
                 for entry in fresh_reports],
        "status": status(None if not any(
            entry["heapSpreadBytes"] is not None for entry in fresh_reports)
            else all(entry["heapSpreadBytes"] is not None
                     and entry["heapSpreadBytes"] < FRESH_SPREAD_LIMIT
                     for entry in fresh_reports)),
    }
    findings["P-H8"] = {
        "claim": "fresh-arm per-cycle sbrk agrees within 2 MB across cycles",
        "runs": fresh_reports,
        "status": status(None if not any(
            entry["sbrkSpreadBytes"] is not None for entry in fresh_reports)
            else all(entry["sbrkSpreadBytes"] is not None
                     and entry["sbrkSpreadBytes"] <= FRESH_SPREAD_LIMIT
                     for entry in fresh_reports)),
    }

    # ---- P-H5 + the control: is debug:true changing what we measure? ------
    control = [{
        "run": r["_run"], "browser": r.get("browserName"),
        "stageEvents": len(r.get("stages") or []),
    } for r in control_runs]
    findings["control-debug-gate"] = {
        "claim": "a debug:false run of the same page yields ZERO stage events, "
                 "so the gate really is debug and not something else",
        "runs": control,
        "status": status(None if not control else
                         all(entry["stageEvents"] == 0 for entry in control)),
    }

    pairs = []
    for browser in sorted({r.get("browserName") for r in results}):
        with_debug = next((r for r in fresh_debug
                           if r.get("browserName") == browser), None)
        without = next((r for r in control_runs
                        if r.get("browserName") == browser
                        and r.get("arm") == "fresh"), None)
        if not with_debug or not without:
            continue
        on = slope(per_cycle_pss(with_debug.get("samples") or []))
        off = slope(per_cycle_pss(without.get("samples") or []))
        pairs.append({
            "browser": browser,
            "pssSlopeDebugOn": on, "pssSlopeDebugOff": off,
            "deltaBytesPerSession": (None if on is None or off is None
                                     else abs(on - off)),
        })
    # The threshold P-H5 registered turned out to be below this measurement's
    # own noise floor, which only repeats can show.  Every fresh-arm run of a
    # condition is pooled per browser: the spread WITHIN a condition is what a
    # difference BETWEEN conditions has to beat to mean anything.
    noise = []
    for browser in sorted({r.get("browserName") for r in results}):
        by_condition: dict[bool, list[float]] = {True: [], False: []}
        for r in results:
            if r.get("arm") != "fresh" or r.get("browserName") != browser:
                continue
            value = slope(per_cycle_pss(r.get("samples") or []))
            if value is not None:
                by_condition[bool(r.get("debug"))].append(value)
        if len(by_condition[True]) < 2 or len(by_condition[False]) < 2:
            continue
        spread_on = max(by_condition[True]) - min(by_condition[True])
        spread_off = max(by_condition[False]) - min(by_condition[False])
        difference = (sum(by_condition[True]) / len(by_condition[True])
                      - sum(by_condition[False]) / len(by_condition[False]))
        noise.append({
            "browser": browser,
            "runsPerCondition": [len(by_condition[True]),
                                 len(by_condition[False])],
            "withinConditionSpreadBytes": [spread_on, spread_off],
            "betweenConditionMeanDifferenceBytes": difference,
            # Three-valued on purpose: a comparison whose noise swamps its
            # effect has not shown "no effect", it has shown nothing.
            "separation": ("NOT_SEPARATED"
                           if abs(difference) < max(spread_on, spread_off)
                           else "SEPARATED"),
        })

    findings["P-H5"] = {
        "claim": "debug:true does not change what the memory round measures: "
                 "PSS slopes differ by <= 2 MB/session",
        "pairs": pairs,
        "noiseFloor": noise,
        "notes": "Scored against what was registered, not against what the "
                 "repeats later made obvious.  Where `separation` is "
                 "NOT_SEPARATED, the registered 2 MB threshold was below the "
                 "run-to-run spread of the very quantity it compares, so this "
                 "FAILED means 'the control could not be run as written', not "
                 "'debug changed the memory'.",
        "status": status(None if not pairs or any(
            pair["deltaBytesPerSession"] is None for pair in pairs)
            else all(pair["deltaBytesPerSession"] <= PSS_SLOPE_DELTA_LIMIT
                     for pair in pairs)),
    }

    held = [name for name, entry in findings.items() if entry["status"] == "HELD"]
    failed = [name for name, entry in findings.items()
              if entry["status"] == "FAILED"]
    return {
        "schemaVersion": 1,
        "release": "spec-e2c-d4-heap",
        "predictionFile":
            "findings/evidence/sdk-e2/e2-c-validation/d4/heap/PREDICTION.md",
        "runs": [{"run": r["_run"], "browser": r.get("browserName"),
                  "arm": r.get("arm"), "debug": r.get("debug"),
                  "cycles": len(r.get("cycles") or []),
                  "stageEvents": len(r.get("stages") or []),
                  "artifact": (r.get("artifact") or {}).get("wasmSha256"),
                  "attributionConsistent":
                      (r.get("attribution") or {}).get("consistent")}
                 for r in results],
        "findings": findings,
        "held": held,
        "failed": failed,
        # The answer the queue item is waiting for, stated as a sentence rather
        # than left to be inferred from eight prediction verdicts.
        "reachability": (
            "REACHABLE-ON-SHIPPED-ARTIFACT"
            if findings["P-H1"]["status"] == "HELD"
               and findings["P-H2"]["status"] == "HELD"
            else "NOT-REACHABLE" if findings["P-H1"]["status"] == "FAILED"
            else "NOT_MEASURED"),
        # Not a prediction: nobody registered it, and it is not scored as one.
        # It is here because the round produced it and the evidence should not
        # need a reader to notice it in the raw files.
        "observations": [{
            "id": "search-after-reopen-never-returns",
            "what": "On one engine, cycle 1 (open, search, click, insertText, "
                    "save, close) succeeds; cycle 2's search times out after "
                    "30 s and every later search returns BUSY, the worker's own "
                    "in-flight guard.  The opens themselves keep working: all "
                    "six stage events arrive for every cycle.",
            "reproduced": [entry["browser"] for entry in shared_wedged],
            "controlledVariable": "the same loop without the search completes "
                                  "8/8 cycles in both browsers, so this belongs "
                                  "to search after a reopen, not to reopening",
            "notAffectedToday": "the product session builds a fresh engine per "
                                "session, so this is an SDK-level path the "
                                "product does not take",
        }] if shared_wedged else [],
        "movingQuantity": (
            "sbrk" if findings["P-H7"]["status"] == "HELD"
                      and findings["P-H6"]["status"] == "HELD"
            else "UNDETERMINED"),
    }


# ---------------------------------------------------------------------------


def self_test(runs: list[Path]) -> int:
    raw = [load(run) for run in runs]
    baseline = judge(copy.deepcopy(raw))
    failures: list[str] = []
    ran: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        ran.append(name)
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    def rejudge(mutate) -> dict:
        cloned = copy.deepcopy(raw)
        mutate(cloned)
        return judge(cloned)

    def debug_run(results):
        return next(r for r in results if r.get("debug") is True)

    def fresh_run(results):
        return next(r for r in results
                    if r.get("debug") is True and r.get("arm") == "fresh")

    def shared_run(results):
        """A shared-arm run the analyzer actually uses.

        The wedged `shared` rounds are excluded from P-H7 by design, so
        mutating one of those would prove nothing -- the mutation has to land
        on a run that is currently load-bearing.
        """
        return next(r for r in results
                    if r.get("debug") is True
                    and str(r.get("arm") or "").startswith("shared")
                    and not any(c.get("error") for c in (r.get("cycles") or [])))

    check("baseline: P-H1 held", baseline["findings"]["P-H1"]["status"] == "HELD",
          str(baseline["findings"]["P-H1"]["status"]))

    def drop_stages(results):
        for r in results:
            r["stages"] = []
            for cycle in r.get("cycles") or []:
                cycle["stageEvents"] = 0

    check("removing every stage event moves P-H1 off HELD",
          rejudge(drop_stages)["findings"]["P-H1"]["status"] != "HELD")

    def one_cycle_silent(results):
        run = fresh_run(results)
        run["stages"] = [s for s in run["stages"] if s.get("cycle") != 2]
        for cycle in run["cycles"]:
            if cycle.get("cycle") == 2:
                cycle["stageEvents"] = 0

    check("one silent cycle takes P-H2 away",
          rejudge(one_cycle_silent)["findings"]["P-H2"]["status"] == "FAILED")

    def move_heap(results):
        debug_run(results)["stages"][0]["heapBytes"] = FIXED_TOTAL_MEMORY + 4096

    check("a single different heapBytes takes P-H6 away",
          rejudge(move_heap)["findings"]["P-H6"]["status"] == "FAILED")

    def sbrk_goes_backwards(results):
        run = debug_run(results)
        engine = run["stages"][0].get("engine")
        group = [s for s in run["stages"] if s.get("engine") == engine]
        if len(group) >= 2:
            group[-1]["sbrk"] = (group[0]["sbrk"] or 0) - 4096

    check("a decreasing sbrk within one instance takes P-H7 away",
          rejudge(sbrk_goes_backwards)["findings"]["P-H7"]["status"] == "FAILED")

    def shared_flat(results):
        for cycle in shared_run(results)["cycles"]:
            cycle["sbrkAfterCycleBytes"] = 287248384

    check("a shared arm whose sbrk never moves takes P-H7 away",
          rejudge(shared_flat)["findings"]["P-H7"]["status"] == "FAILED")

    def fresh_drifts(results):
        cycles = fresh_run(results)["cycles"]
        if cycles:
            cycles[-1]["sbrkAfterCycleBytes"] = (
                (cycles[0].get("sbrkAfterCycleBytes") or 0) + 50 * MB)

    check("a fresh instance drifting 50 MB takes P-H8 away",
          rejudge(fresh_drifts)["findings"]["P-H8"]["status"] == "FAILED")

    def control_speaks(results):
        control = next((r for r in results if r.get("debug") is False), None)
        if control is not None:
            control["stages"] = [{"engine": "fresh-1", "cycle": 1,
                                  "stage": "open.begin",
                                  "heapBytes": FIXED_TOTAL_MEMORY,
                                  "sbrk": 1, "atMs": 1}]

    check("a debug:false run that emits stage events takes the control away",
          rejudge(control_speaks)["findings"]["control-debug-gate"]["status"]
          == "FAILED")

    # P-H5 is already FAILED on the recorded data, so a mutation that makes it
    # fail again would demonstrate nothing.  The informative direction is the
    # other one: make the two conditions agree and the prediction must HOLD.
    # (This is the same trap as a substring check that a disabled guard still
    # satisfies -- a check that cannot change is not a check.)
    def pss_conditions_agree(results):
        template = None
        for r in results:
            if r.get("arm") != "fresh":
                continue
            if template is None:
                template = copy.deepcopy(r.get("samples") or [])
            else:
                r["samples"] = copy.deepcopy(template)

    check("making both conditions identical moves P-H5 to HELD",
          rejudge(pss_conditions_agree)["findings"]["P-H5"]["status"] == "HELD",
          "P-H5 could not be moved off FAILED at all")

    def pss_diverges(results):
        run = fresh_run(results)
        for index, sample in enumerate(run.get("samples") or []):
            if sample.get("pssBytes") is not None:
                sample["pssBytes"] += index * 40 * MB

    check("and a climbing PSS on one condition keeps it FAILED",
          rejudge(pss_diverges)["findings"]["P-H5"]["status"] == "FAILED")

    check("the reachability sentence follows P-H1 rather than being fixed",
          rejudge(drop_stages)["reachability"] != baseline["reachability"],
          f"baseline={baseline['reachability']}")

    print(f"\nself-test: {len(ran) - len(failures)}/{len(ran)} "
          "checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.runs)
    summary = judge([load(run) for run in args.runs])
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if not summary["failed"] else 0  # verdicts, not a gate


if __name__ == "__main__":
    sys.exit(main())
