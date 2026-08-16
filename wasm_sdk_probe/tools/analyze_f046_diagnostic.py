#!/usr/bin/env python3
"""Judge the 046 diagnostic readback round offline.

The round reads the barrier's own record off the **frozen** engine: a diagnostic
profile is `probe.wasm` copied byte-for-byte from `e2-editor-v2` with only the
worker's projection swapped for the raw event.

Criteria: findings/evidence/046/diagnostic-readback/PREDICTION.md, registered
before the profile was built.

The load-bearing prediction is P-046D-5: the same arms must reach the same
OUTCOMES as the product-profile round.  If they do not, the profile is not the
product path and nothing measured here transfers -- so this analyzer takes both
round directories and compares them.

Usage:
  analyze_f046_diagnostic.py --diagnostic DIR [DIR ...] --product DIR [DIR ...]
  analyze_f046_diagnostic.py --self-test --diagnostic ... --product ...
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

EMPTY_ARMS = ("A1-empty-click", "A2-empty-selectrange")
CONTROL = "A3-text-click"
FROZEN_WASM = "572035accd0f27544ed485d994f065bcad2b73d5d21eafbf361c8cc11630c0a5"


def load(run: Path) -> dict:
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    result["_run"] = str(run)
    return result


def barrier(arm: dict) -> dict:
    return ((arm.get("result") or {}).get("formatBarrier")) or {}


def outcome(arm: dict) -> tuple:
    """What HAPPENED, as opposed to what could be seen about it."""
    return (arm.get("accepted"), barrier(arm).get("failureShape"),
            barrier(arm).get("route"), arm.get("sessionState"))


def status(condition: bool | None) -> str:
    if condition is None:
        return "NOT_MEASURED"
    return "HELD" if condition else "FAILED"


def judge(diagnostic: list[dict], product: list[dict]) -> dict:
    arms = [(result, name, arm) for result in diagnostic
            for name, arm in (result.get("arms") or {}).items()]

    def named(name: str) -> list[dict]:
        return [arm for _, key, arm in arms if key == name]

    empty = [arm for _, name, arm in arms if name in EMPTY_ARMS]

    def readback(arm: dict) -> dict:
        return barrier(arm).get("readback") or {}

    def containment(arm: dict) -> dict:
        return barrier(arm).get("containment") or {}

    findings: dict[str, dict] = {}

    findings["P-046D-1"] = {
        "claim": "the disputed arms carry a non-empty readback.html",
        "observed": [{"bytes": readback(arm).get("bytes"),
                      "htmlLength": len(readback(arm).get("html") or "")}
                     for arm in empty],
        "status": status(
            all((readback(arm).get("bytes") or 0) > 0 and readback(arm).get("html")
                for arm in empty) if empty else None),
    }

    findings["P-046D-2"] = {
        "claim": "the disputed arms read parsed:true, blockCount:0, itemCount>=2 "
                 "-- the 'multiBlock with no block in it' combination",
        "observed": [{"parsed": readback(arm).get("parsed"),
                      "blockCount": readback(arm).get("blockCount"),
                      "itemCount": readback(arm).get("itemCount"),
                      "multiBlock": readback(arm).get("multiBlock")}
                     for arm in empty],
        "status": status(
            all(readback(arm).get("parsed") is True
                and readback(arm).get("blockCount") == 0
                and (readback(arm).get("itemCount") or 0) >= 2
                for arm in empty) if empty else None),
    }

    findings["P-046D-3"] = {
        "claim": "the disputed arms show containment checked and NOT held",
        "observed": [{"checked": containment(arm).get("checked"),
                      "held": containment(arm).get("held"),
                      "selectionTop": containment(arm).get("selectionTop"),
                      "selectionBottom": containment(arm).get("selectionBottom"),
                      "restoreCentre": containment(arm).get("restoreCentre")}
                     for arm in empty],
        "status": status(
            all(containment(arm).get("checked") is True
                and containment(arm).get("held") is False
                for arm in empty) if empty else None),
    }

    controls = named(CONTROL)
    findings["P-046D-4"] = {
        "claim": "the control reads parsed:true, blockCount:1, containment held",
        "observed": [{"parsed": readback(arm).get("parsed"),
                      "blockCount": readback(arm).get("blockCount"),
                      "held": containment(arm).get("held"),
                      "accepted": arm.get("accepted")}
                     for arm in controls],
        "status": status(
            all(readback(arm).get("parsed") is True
                and readback(arm).get("blockCount") == 1
                and containment(arm).get("held") is True
                for arm in controls) if controls else None),
    }

    # P-046D-5: same arms, same outcomes, across the two profiles.
    comparisons = []
    for browser in sorted({r.get("browserName") for r in diagnostic}):
        left = next((r for r in diagnostic if r.get("browserName") == browser), None)
        right = next((r for r in product if r.get("browserName") == browser), None)
        if not left or not right:
            continue
        for name in sorted(set(left.get("arms") or {})
                           & set(right.get("arms") or {})):
            same = outcome(left["arms"][name]) == outcome(right["arms"][name])
            comparisons.append({
                "browser": browser, "arm": name, "same": same,
                "diagnostic": outcome(left["arms"][name]),
                "product": outcome(right["arms"][name]),
            })
    findings["P-046D-5"] = {
        "claim": "every arm reaches the SAME outcome on both profiles -- "
                 "swapping the projection changes what can be seen, not what "
                 "happens",
        "observed": [entry for entry in comparisons if not entry["same"]] or "all same",
        "comparisons": len(comparisons),
        "status": status(all(entry["same"] for entry in comparisons)
                         if comparisons else None),
    }

    frozen = all((run.get("artifact") or {}).get("wasmSha256") == FROZEN_WASM
                 for run in diagnostic)

    # ---- what the two blockers become -------------------------------------
    empty_readback_occurred = any(
        readback(arm).get("parsed") is True
        and readback(arm).get("blockCount") == 0 for _, _, arm in arms)
    reorder_would_change = any(
        containment(arm).get("checked") is True
        and containment(arm).get("held") is False
        and readback(arm).get("multiBlock") is True for _, _, arm in arms)

    return {
        "schemaVersion": 1,
        "release": "finding-046-diagnostic-readback",
        "predictionFile": "findings/evidence/046/diagnostic-readback/PREDICTION.md",
        "evidenceClass": "diagnostic",
        "engineIsFrozenShipping": frozen,
        "runs": [{"run": r["_run"], "browser": r.get("browserName"),
                  "profile": (r.get("artifact") or {}).get("profile"),
                  "wasmSha256": (r.get("artifact") or {}).get("wasmSha256"),
                  "matrixEntryAssertion": r.get("matrixEntryAssertion")}
                 for r in diagnostic],
        "findings": findings,
        "held": [name for name, entry in findings.items()
                 if entry["status"] == "HELD"],
        "failed": [name for name, entry in findings.items()
                   if entry["status"] == "FAILED"],
        "queueDisposition": {
            # 3b names a shape for "an empty readback".  If no arm produces one,
            # the shape has nothing to name on the fixture that motivated it.
            "emptyReadbackOccurred": empty_readback_occurred,
            # The reorder only changes cells where BOTH conditions hold; if
            # containment holds wherever multiBlock fires, it is a no-op there.
            "reorderWouldChangeADisputedCell": reorder_would_change,
        },
    }


def self_test(diagnostic: list[Path], product: list[Path]) -> int:
    raw_d = [load(run) for run in diagnostic]
    raw_p = [load(run) for run in product]
    baseline = judge(copy.deepcopy(raw_d), copy.deepcopy(raw_p))
    failures: list[str] = []
    ran: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        ran.append(name)
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    def rejudge(mutate_d=None, mutate_p=None) -> dict:
        cloned_d, cloned_p = copy.deepcopy(raw_d), copy.deepcopy(raw_p)
        if mutate_d:
            mutate_d(cloned_d)
        if mutate_p:
            mutate_p(cloned_p)
        return judge(cloned_d, cloned_p)

    check("baseline: the method's own control (P-046D-5) holds",
          baseline["findings"]["P-046D-5"]["status"] == "HELD",
          str(baseline["findings"]["P-046D-5"]["observed"])[:200])
    check("baseline: the engine is the frozen shipping one",
          baseline["engineIsFrozenShipping"] is True)

    def outcome_differs(results):
        for result in results:
            arm = (result.get("arms") or {}).get("A1-empty-click")
            if arm:
                arm["accepted"] = True

    check("an arm that behaves differently on the two profiles kills the method",
          rejudge(mutate_d=outcome_differs)["findings"]["P-046D-5"]["status"]
          == "FAILED")

    def zero_block_readback(results):
        for result in results:
            for name in EMPTY_ARMS:
                arm = (result.get("arms") or {}).get(name)
                if arm:
                    arm["result"]["formatBarrier"]["readback"].update(
                        {"parsed": True, "blockCount": 0, "itemCount": 2})

    mutated = rejudge(mutate_d=zero_block_readback)
    check("a genuine zero-block readback would move P-046D-2 to HELD",
          mutated["findings"]["P-046D-2"]["status"] == "HELD")
    check("and it would flip the queue disposition for 3b",
          mutated["queueDisposition"]["emptyReadbackOccurred"] is True
          and baseline["queueDisposition"]["emptyReadbackOccurred"] is False)

    def containment_fails(results):
        for result in results:
            for name in EMPTY_ARMS:
                arm = (result.get("arms") or {}).get(name)
                if arm:
                    arm["result"]["formatBarrier"]["containment"]["held"] = False

    mutated = rejudge(mutate_d=containment_fails)
    check("a containment failure would move P-046D-3 to HELD",
          mutated["findings"]["P-046D-3"]["status"] == "HELD")
    check("and it would make the reorder change a disputed cell",
          mutated["queueDisposition"]["reorderWouldChangeADisputedCell"] is True
          and baseline["queueDisposition"]["reorderWouldChangeADisputedCell"]
          is False)

    def not_frozen(results):
        for result in results:
            result["artifact"]["wasmSha256"] = "0" * 64

    check("a profile built on a different engine is caught",
          rejudge(mutate_d=not_frozen)["engineIsFrozenShipping"] is False)

    def control_reads_nothing(results):
        for result in results:
            arm = (result.get("arms") or {}).get(CONTROL)
            if arm:
                arm["result"]["formatBarrier"]["readback"]["parsed"] = False

    check("a control that reads nothing takes P-046D-4 away",
          rejudge(mutate_d=control_reads_nothing)["findings"]["P-046D-4"]["status"]
          == "FAILED")

    print(f"\nself-test: {len(ran) - len(failures)}/{len(ran)} "
          "checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnostic", nargs="+", type=Path, required=True)
    parser.add_argument("--product", nargs="+", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.diagnostic, args.product)
    summary = judge([load(run) for run in args.diagnostic],
                    [load(run) for run in args.product])
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
