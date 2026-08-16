#!/usr/bin/env python3
"""Judge finding 046's browser arm offline.

The question this round settles is not "does the empty paragraph read back
empty".  It is **whether the number the argument rested on was ever a
measurement**: `preBlocks` and `postBlocks`, as reported by the shipped product
projection, on the route these cells actually take.

Criteria: findings/evidence/046/browser-vs-native/PREDICTION.md
(P-046B-1..5 registered before the harness; P-046B-6 in addendum A1, after a
scratch smoke run and before any recorded round.)

Three answers, never two: HELD, FAILED, NOT_MEASURED.

Usage:
  analyze_f046_browser.py RUN_DIR [RUN_DIR ...] [--output F]
  analyze_f046_browser.py --self-test RUN_DIR [RUN_DIR ...]
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

EMPTY_ARMS = ("A1-empty-click", "A2-empty-selectrange")


def load(run: Path) -> dict:
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    result["_run"] = str(run)
    return result


def barrier(arm: dict) -> dict:
    return ((arm.get("result") or {}).get("formatBarrier")) or {}


def caret_y(arm: dict) -> int | None:
    caret = (arm.get("stateBeforeAction") or {}).get("caret") or {}
    return caret.get("y")


def status(condition: bool | None) -> str:
    if condition is None:
        return "NOT_MEASURED"
    return "HELD" if condition else "FAILED"


def judge(results: list[dict]) -> dict:
    arms = [(result, name, arm) for result in results
            for name, arm in (result.get("arms") or {}).items()]

    def by_name(name: str) -> list[tuple[dict, str, dict]]:
        return [entry for entry in arms if entry[1] == name]

    def every(name: str, predicate) -> bool | None:
        found = by_name(name)
        if not found:
            return None
        return all(predicate(arm) for _, _, arm in found)

    findings: dict[str, dict] = {}

    findings["P-046B-1"] = {
        "claim": "the control (a paragraph WITH text) reports preBlocks >= 1",
        "observed": [{"browser": result.get("browserName"),
                      "accepted": arm.get("accepted"),
                      "route": barrier(arm).get("route"),
                      "preBlocks": barrier(arm).get("preBlocks"),
                      "postBlocks": barrier(arm).get("postBlocks")}
                     for result, _, arm in by_name("A3-text-click")],
        "status": status(every("A3-text-click",
                               lambda arm: (barrier(arm).get("preBlocks") or 0) >= 1)),
    }

    findings["P-046B-2"] = {
        "claim": "with the caret CONFIRMED on the empty paragraph, the browser "
                 "still reports preBlocks 0 -- the 048 fix does not explain it",
        "observed": [{"browser": result.get("browserName"), "arm": name,
                      "caretY": caret_y(arm),
                      "preBlocks": barrier(arm).get("preBlocks")}
                     for result, name, arm in arms if name in EMPTY_ARMS],
        "status": status(all(
            barrier(arm).get("preBlocks") == 0 and caret_y(arm) is not None
            for _, name, arm in arms if name in EMPTY_ARMS)
            if any(name in EMPTY_ARMS for _, name, _ in arms) else None),
    }

    def pair(result: dict) -> tuple:
        first, second = (result.get("arms") or {}).get(EMPTY_ARMS[0]) or {}, \
                        (result.get("arms") or {}).get(EMPTY_ARMS[1]) or {}
        return ((barrier(first).get("preBlocks"), barrier(first).get("postBlocks")),
                (barrier(second).get("preBlocks"), barrier(second).get("postBlocks")))

    findings["P-046B-3"] = {
        "claim": "the click gesture and the zero-width selectRange read the same",
        "observed": [{"browser": result.get("browserName"),
                      "click": barrier((result.get("arms") or {}).get(EMPTY_ARMS[0]) or {})
                          .get("failureShape"),
                      "selectRange": barrier((result.get("arms") or {}).get(EMPTY_ARMS[1]) or {})
                          .get("failureShape")}
                     for result in results],
        # Both arms have to BE there.  Comparing two absences and calling them
        # equal is how a prediction survives its own data going missing -- the
        # self-test caught exactly that.
        "status": status(
            all(pair(result)[0] == pair(result)[1] for result in results)
            if results and all(
                barrier((result.get("arms") or {}).get(name) or {})
                for result in results for name in EMPTY_ARMS)
            else None),
    }

    findings["P-046B-4"] = {
        "claim": "the fixture's last empty paragraph behaves like the first one",
        "observed": [{"browser": result.get("browserName"),
                      "shape": barrier(arm).get("failureShape"),
                      "caretY": caret_y(arm)}
                     for result, _, arm in by_name("A4-last-empty-click")],
        "status": status(every(
            "A4-last-empty-click",
            lambda arm: barrier(arm).get("failureShape") == "multi-block-readback")),
    }

    findings["P-046B-5"] = {
        "claim": "no arm reaches a successful action",
        "observed": [{"browser": result.get("browserName"), "arm": name,
                      "accepted": arm.get("accepted")}
                     for result, name, arm in arms if arm.get("accepted")],
        "status": status(not any(arm.get("accepted") for _, _, arm in arms)
                         if arms else None),
    }

    findings["P-046B-6"] = {
        "claim": "a RANGE arm reports preBlocks >= 1 and postBlocks 0 on "
                 "route range-single",
        "observed": [{"browser": result.get("browserName"),
                      "route": barrier(arm).get("route"),
                      "preBlocks": barrier(arm).get("preBlocks"),
                      "postBlocks": barrier(arm).get("postBlocks"),
                      "accepted": arm.get("accepted")}
                     for result, _, arm in by_name("A5-text-range")],
        "status": status(every(
            "A5-text-range",
            lambda arm: barrier(arm).get("route") == "range-single"
            and (barrier(arm).get("preBlocks") or 0) >= 1
            and barrier(arm).get("postBlocks") == 0)),
    }

    # ---- the conclusion the queue item is waiting for ---------------------
    collapsed = [arm for _, _, arm in arms
                 if barrier(arm).get("route") == "collapsed"]
    collapsed_all_zero = bool(collapsed) and all(
        barrier(arm).get("preBlocks") == 0 and barrier(arm).get("postBlocks") == 0
        for arm in collapsed)
    # The load-bearing half: at least one collapsed arm SUCCEEDED and still
    # reported zero.  Without that, "zero" could still mean "read and empty".
    succeeded_collapsed_zero = any(
        arm.get("accepted") and barrier(arm).get("preBlocks") == 0
        for arm in collapsed)
    range_nonzero = any((barrier(arm).get("preBlocks") or 0) >= 1
                        for _, _, arm in arms
                        if barrier(arm).get("route") in ("range-single",
                                                         "range-cross"))

    return {
        "schemaVersion": 1,
        "release": "finding-046-browser-vs-native",
        "predictionFile": "findings/evidence/046/browser-vs-native/PREDICTION.md",
        "runs": [{"run": result["_run"], "browser": result.get("browserName"),
                  "artifact": (result.get("artifact") or {}).get("wasmSha256"),
                  "attributionConsistent":
                      (result.get("attribution") or {}).get("consistent"),
                  "arms": sorted((result.get("arms") or {}))}
                 for result in results],
        "findings": findings,
        "held": [name for name, entry in findings.items()
                 if entry["status"] == "HELD"],
        "failed": [name for name, entry in findings.items()
                   if entry["status"] == "FAILED"],
        "conclusion": {
            "collapsedRouteAlwaysZero": collapsed_all_zero,
            "aSucceededCollapsedArmAlsoReadZero": succeeded_collapsed_zero,
            "aRangeArmReportsNonZero": range_nonzero,
            # Stated as a sentence, because eight prediction verdicts do not add
            # up to one on their own.
            "disagreement": (
                "DISSOLVED-THE-BROWSER-NUMBER-WAS-NEVER-A-READBACK"
                if collapsed_all_zero and succeeded_collapsed_zero
                   and range_nonzero
                else "NOT_ESTABLISHED"),
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

    def arm(results, name):
        for result in results:
            if name in (result.get("arms") or {}):
                return result["arms"][name]
        raise KeyError(name)

    check("baseline: the disagreement is dissolved",
          baseline["conclusion"]["disagreement"].startswith("DISSOLVED"),
          baseline["conclusion"]["disagreement"])

    def control_reads_blocks(results):
        for result in results:
            entry = (result.get("arms") or {}).get("A3-text-click")
            if entry:
                entry["result"]["formatBarrier"]["preBlocks"] = 2

    mutated = rejudge(control_reads_blocks)
    check("a control that DOES report blocks moves P-046B-1 to HELD",
          mutated["findings"]["P-046B-1"]["status"] == "HELD")
    check("and it takes the conclusion away",
          mutated["conclusion"]["disagreement"] == "NOT_ESTABLISHED")

    def range_arm_reads_zero(results):
        for result in results:
            entry = (result.get("arms") or {}).get("A5-text-range")
            if entry:
                entry["result"]["formatBarrier"]["preBlocks"] = 0

    mutated = rejudge(range_arm_reads_zero)
    check("a range arm reading zero takes P-046B-6 away",
          mutated["findings"]["P-046B-6"]["status"] == "FAILED")
    check("and with nothing ever non-zero, the conclusion is NOT_ESTABLISHED",
          mutated["conclusion"]["disagreement"] == "NOT_ESTABLISHED")

    def empty_arm_reads_blocks(results):
        for name in EMPTY_ARMS:
            try:
                arm(results, name)["result"]["formatBarrier"]["preBlocks"] = 1
            except KeyError:
                pass

    check("an empty arm that reports blocks takes P-046B-2 away",
          rejudge(empty_arm_reads_blocks)["findings"]["P-046B-2"]["status"]
          == "FAILED")

    def gestures_diverge(results):
        for result in results:
            entry = (result.get("arms") or {}).get(EMPTY_ARMS[1])
            if entry:
                entry["result"]["formatBarrier"]["preBlocks"] = 3

    check("gestures that read differently take P-046B-3 away",
          rejudge(gestures_diverge)["findings"]["P-046B-3"]["status"] == "FAILED")

    def last_empty_agrees(results):
        for result in results:
            entry = (result.get("arms") or {}).get("A4-last-empty-click")
            if entry:
                entry["result"]["formatBarrier"]["failureShape"] = \
                    "multi-block-readback"

    check("P-046B-4 is scored on the shape, and can reach HELD",
          rejudge(last_empty_agrees)["findings"]["P-046B-4"]["status"] == "HELD",
          "the prediction cannot be moved, so it is not being scored")

    def drop_all_arms(results):
        for result in results:
            result["arms"] = {}

    check("with no arms at all, nothing is HELD and nothing is FAILED",
          rejudge(drop_all_arms)["held"] == []
          and rejudge(drop_all_arms)["failed"] == [])

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
