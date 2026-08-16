#!/usr/bin/env python3
"""Judge finding 048's boundary round offline.

The question: of the 22–28 ms between a click and the caret moving, how much is
ours (postMessage, worker dispatch, the synchronous post into wasm) and how much
is on the engine's side of the worker boundary?

Criteria: findings/evidence/048/boundary/PREDICTION.md, registered before the
harness existed.

**This tool does not attribute the engine-side remainder to anything.**  Native
measured core's own click handling at 0.6 ms, so subtracting leaves a residue --
and a residue is not an attribution.  Finding 040 is the precedent: a condition
an Emscripten build never sets, blamed on the wrong layer for weeks.

Usage:
  analyze_f048_boundary.py RUN_DIR [RUN_DIR ...] [--output F]
  analyze_f048_boundary.py --self-test RUN_DIR [RUN_DIR ...]
"""

from __future__ import annotations

import argparse
import copy
import json
import statistics
import sys
from pathlib import Path

CALIBRATION_MEDIAN_LIMIT_MS = 3.0     # P-048B-1
TRANSPORT_MULTIPLE_LIMIT = 2.0        # P-048B-2
ENGINE_SIDE_FLOOR_MS = 10.0           # P-048B-3
ENGINE_SIDE_SHARE_FLOOR = 0.70        # P-048B-3
TOTAL_BAND_MS = (15.0, 40.0)          # P-048B-4
MIN_INVALIDATED = 8                   # P-048B-5


def load(run: Path) -> dict:
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    result["_run"] = str(run)
    return result


def landed(click: dict) -> bool:
    """Did the click reach the line it aimed at?

    The caret's reported y is the TOP of its line box while the click aims at
    the middle, so equality is the wrong test -- the same geometry lesson the
    D3 corpus round paid three cells for.  Overlap of the caret box with the
    click point is what "landed" means.
    """
    caret_y, height = click.get("caretY"), click.get("caretHeight")
    asked = click.get("askedY")
    if caret_y is None or asked is None:
        return False
    span = height if isinstance(height, (int, float)) and height > 0 else 1
    return caret_y <= asked <= caret_y + span


def summarise(result: dict) -> dict:
    calibration = [entry["roundTripMs"] for entry in result.get("calibration") or []]
    clicks = result.get("clicks") or []
    usable = [click for click in clicks
              if click.get("invalidatedAfterMs") is not None and landed(click)]
    excluded = [{"index": click.get("index"),
                 "reason": ("no invalidation"
                            if click.get("invalidatedAfterMs") is None
                            else "caret did not land on the clicked line"),
                 "caretY": click.get("caretY"), "askedY": click.get("askedY")}
                for click in clicks if click not in usable]

    def median(values):
        return statistics.median(values) if values else None

    return {
        "run": result["_run"],
        "browser": result.get("browserName"),
        "artifact": (result.get("artifact") or {}).get("wasmSha256"),
        "attributionConsistent": (result.get("attribution") or {}).get("consistent"),
        "calibrationCount": len(calibration),
        "calibrationMedianMs": median(calibration),
        "clicks": len(clicks),
        "usableClicks": len(usable),
        # Printed, never silent: a round that drops half its clicks and reports
        # a tidy median has hidden the interesting half.
        "excludedClicks": excluded,
        "transportMedianMs": median([c["transportMs"] for c in usable]),
        "transportMaxMs": max((c["transportMs"] for c in usable), default=None),
        "engineSideMedianMs": median([c["engineSideMs"] for c in usable]),
        "totalMedianMs": median([c["invalidatedAfterMs"] for c in usable]),
        "engineSideShare": (
            median([c["engineSideMs"] / c["invalidatedAfterMs"] for c in usable
                    if c["invalidatedAfterMs"]])),
        "invalidationsPerClick": [c.get("invalidations") for c in clicks],
    }


def status(condition: bool | None) -> str:
    if condition is None:
        return "NOT_MEASURED"
    return "HELD" if condition else "FAILED"


def judge(results: list[dict]) -> dict:
    runs = [summarise(result) for result in results]

    def every(predicate) -> bool | None:
        usable = [run for run in runs if run["usableClicks"] > 0]
        if not usable:
            return None
        return all(predicate(run) for run in usable)

    findings = {
        "P-048B-1": {
            "claim": "the getState round trip has a median <= 3 ms",
            "observed": [(run["browser"], run["calibrationMedianMs"]) for run in runs],
            "status": status(
                all(run["calibrationMedianMs"] is not None
                    and run["calibrationMedianMs"] <= CALIBRATION_MEDIAN_LIMIT_MS
                    for run in runs) if runs else None),
        },
        "P-048B-2": {
            "claim": "the click's own round trip is within 2x of that floor -- "
                     "posting the mouse event is not where the wait is",
            "observed": [(run["browser"], run["transportMedianMs"],
                          run["calibrationMedianMs"]) for run in runs],
            "status": status(every(
                lambda run: run["transportMedianMs"] is not None
                and run["calibrationMedianMs"]
                and run["transportMedianMs"]
                <= TRANSPORT_MULTIPLE_LIMIT * run["calibrationMedianMs"])),
        },
        "P-048B-3": {
            "claim": "the engine side is >= 10 ms and >= 70% of the total",
            "observed": [(run["browser"], run["engineSideMedianMs"],
                          run["engineSideShare"]) for run in runs],
            "status": status(every(
                lambda run: (run["engineSideMedianMs"] or 0) >= ENGINE_SIDE_FLOOR_MS
                and (run["engineSideShare"] or 0) >= ENGINE_SIDE_SHARE_FLOOR)),
        },
        "P-048B-4": {
            "claim": f"the total lands in {TOTAL_BAND_MS[0]}-{TOTAL_BAND_MS[1]} ms, "
                     "the band the D3 caret probe measured",
            "observed": [(run["browser"], run["totalMedianMs"]) for run in runs],
            "status": status(every(
                lambda run: run["totalMedianMs"] is not None
                and TOTAL_BAND_MS[0] <= run["totalMedianMs"] <= TOTAL_BAND_MS[1])),
        },
        "P-048B-5": {
            "claim": "at least 8 of 10 clicks produce a cursor invalidation",
            "observed": [(run["browser"], run["usableClicks"], run["clicks"])
                         for run in runs],
            "status": status(all(run["usableClicks"] >= MIN_INVALIDATED
                                 for run in runs) if runs else None),
        },
    }

    split_established = (findings["P-048B-2"]["status"] == "HELD"
                         and findings["P-048B-3"]["status"] == "HELD")
    return {
        "schemaVersion": 1,
        "release": "finding-048-boundary",
        "predictionFile": "findings/evidence/048/boundary/PREDICTION.md",
        "runs": runs,
        "findings": findings,
        "held": [name for name, entry in findings.items()
                 if entry["status"] == "HELD"],
        "failed": [name for name, entry in findings.items()
                   if entry["status"] == "FAILED"],
        "conclusion": {
            "side": ("ENGINE-SIDE-OF-THE-WORKER-BOUNDARY" if split_established
                     else "NOT_ESTABLISHED"),
            # Said in the output, not left to a reader's restraint.
            "mayNotConclude": "which layer on that side.  Core's own click "
                              "handling is 0.6 ms natively, so subtracting "
                              "leaves a residue -- and a residue is not an "
                              "attribution (finding 040's precedent).  The next "
                              "controlled variable is an engine-side timestamp, "
                              "which needs a diagnostic build.",
        },
    }


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

    check("baseline: the split is established",
          baseline["conclusion"]["side"] == "ENGINE-SIDE-OF-THE-WORKER-BOUNDARY",
          baseline["conclusion"]["side"])

    def transport_is_the_wait(results):
        for result in results:
            for click in result["clicks"]:
                total = click["invalidatedAfterMs"] or 0
                click["transportMs"] = total * 0.9
                click["engineSideMs"] = total * 0.1

    mutated = rejudge(transport_is_the_wait)
    check("a round where the transport IS the wait takes P-048B-2 away",
          mutated["findings"]["P-048B-2"]["status"] == "FAILED")
    check("and the conclusion with it",
          mutated["conclusion"]["side"] == "NOT_ESTABLISHED")

    def engine_side_is_small(results):
        for result in results:
            for click in result["clicks"]:
                click["engineSideMs"] = 1.0
                click["invalidatedAfterMs"] = 20.0

    check("an engine side of 1 ms takes P-048B-3 away",
          rejudge(engine_side_is_small)["findings"]["P-048B-3"]["status"]
          == "FAILED")

    def slow_transport_floor(results):
        for result in results:
            for entry in result["calibration"]:
                entry["roundTripMs"] = 25.0

    check("a transport floor of 25 ms takes P-048B-1 away",
          rejudge(slow_transport_floor)["findings"]["P-048B-1"]["status"]
          == "FAILED")

    def out_of_band(results):
        for result in results:
            for click in result["clicks"]:
                click["invalidatedAfterMs"] = 400.0

    check("a total outside the measured band takes P-048B-4 away",
          rejudge(out_of_band)["findings"]["P-048B-4"]["status"] == "FAILED")

    def no_invalidations(results):
        for result in results:
            for click in result["clicks"]:
                click["invalidatedAfterMs"] = None
                click["engineSideMs"] = None

    mutated = rejudge(no_invalidations)
    check("clicks that produce no invalidation take P-048B-5 away",
          mutated["findings"]["P-048B-5"]["status"] == "FAILED")
    check("and the deltas become NOT_MEASURED rather than zero",
          mutated["findings"]["P-048B-3"]["status"] == "NOT_MEASURED")

    def caret_never_landed(results):
        for result in results:
            for click in result["clicks"]:
                click["caretY"] = (click.get("askedY") or 0) + 10_000

    check("clicks whose caret never landed are excluded, not averaged in",
          rejudge(caret_never_landed)["runs"][0]["usableClicks"] == 0)

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
