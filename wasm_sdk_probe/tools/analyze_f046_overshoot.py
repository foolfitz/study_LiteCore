#!/usr/bin/env python3
"""Judge the 046 overshoot characterisation offline.

One question decides what the defect is worth: is the barrier's selection
overshoot about the paragraph being EMPTY, or about the caret sitting at a
paragraph edge?  The second would be an ordinary gesture -- click at the end of
a line, press the bullet button -- and a much larger defect.

Criteria: findings/evidence/046/overshoot/PREDICTION.md, registered before the
harness existed.

Usage:
  analyze_f046_overshoot.py RUN_DIR [RUN_DIR ...] [--output F]
  analyze_f046_overshoot.py --self-test RUN_DIR [RUN_DIR ...]
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

FROZEN_WASM = "572035accd0f27544ed485d994f065bcad2b73d5d21eafbf361c8cc11630c0a5"
EMPTY_CELL = "empty-mid"
EDGE_CELLS = ("text-end", "isolated-end")
NON_EMPTY_CELLS = ("text-mid", "text-start", "text-end", "isolated-mid",
                   "isolated-end", "between-mid", "bullet-one-mid")


def load(run: Path) -> dict:
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    result["_run"] = str(run)
    return result


def barrier(cell: dict) -> dict:
    return ((cell.get("result") or {}).get("formatBarrier")) or {}


def readback(cell: dict) -> dict:
    return barrier(cell).get("readback") or {}


def containment(cell: dict) -> dict:
    return barrier(cell).get("containment") or {}


def blocks(cell: dict):
    return readback(cell).get("blockCount")


def status(condition: bool | None) -> str:
    if condition is None:
        return "NOT_MEASURED"
    return "HELD" if condition else "FAILED"


def judge(results: list[dict]) -> dict:
    cells = [(result, name, cell) for result in results
             for name, cell in (result.get("cells") or {}).items()
             # A cell whose caret never landed says nothing about the barrier.
             if not cell.get("error")]

    def named(name: str) -> list[dict]:
        return [cell for _, key, cell in cells if key == name]

    def every(names, predicate) -> bool | None:
        found = [cell for _, key, cell in cells if key in names]
        if not found:
            return None
        return all(predicate(cell) for cell in found)

    findings = {
        "P-OV-1": {
            "claim": "the control (mid-text) reads one block and succeeds",
            "observed": [{"blocks": blocks(c), "accepted": c.get("accepted")}
                         for c in named("text-mid")],
            "status": status(every(("text-mid",),
                                   lambda c: blocks(c) == 1 and c.get("accepted"))),
        },
        "P-OV-2": {
            "claim": "the empty paragraph reads two blocks and fails multi-block",
            "observed": [{"blocks": blocks(c), "accepted": c.get("accepted"),
                          "shape": barrier(c).get("failureShape")}
                         for c in named(EMPTY_CELL)],
            "status": status(every(
                (EMPTY_CELL,),
                lambda c: blocks(c) == 2 and c.get("accepted") is False
                and barrier(c).get("failureShape") == "multi-block-readback")),
        },
        "P-OV-3": {
            "claim": "a caret PAST THE LAST CHARACTER of a paragraph with text "
                     "reads one block -- the overshoot is about emptiness, not "
                     "about being at an edge",
            "observed": [{"cell": key, "blocks": blocks(cell),
                          "caretX": (cell.get("caret") or {}).get("x"),
                          "caretPastText": cell.get("caretPastText"),
                          "accepted": cell.get("accepted")}
                         for _, key, cell in cells if key in EDGE_CELLS],
            # The premise has to hold too: a cell whose caret did NOT end up
            # past the text is not testing an edge, and saying so is the
            # difference between a measurement and a coincidence.
            "premiseHeld": every(EDGE_CELLS,
                                 lambda c: c.get("caretPastText") is True),
            "status": status(every(EDGE_CELLS, lambda c: blocks(c) == 1)),
        },
        "P-OV-4": {
            "claim": "a caret at the START of a paragraph reads one block",
            "observed": [{"blocks": blocks(c)} for c in named("text-start")],
            "status": status(every(("text-start",), lambda c: blocks(c) == 1)),
        },
        "P-OV-5": {
            "claim": "being inside a list does not by itself cause the overshoot",
            "observed": [{"blocks": blocks(c), "accepted": c.get("accepted")}
                         for c in named("bullet-one-mid")],
            "status": status(every(("bullet-one-mid",), lambda c: blocks(c) == 1)),
        },
        "P-OV-6": {
            "claim": "every overshooting cell still reports containment held -- "
                     "containment cannot catch an overshoot",
            "observed": [{"cell": key, "blocks": blocks(cell),
                          "held": containment(cell).get("held")}
                         for _, key, cell in cells if (blocks(cell) or 0) >= 2],
            "status": status(
                all(containment(cell).get("held") is True
                    for _, _, cell in cells if (blocks(cell) or 0) >= 2)
                if any((blocks(cell) or 0) >= 2 for _, _, cell in cells) else None),
        },
    }

    overshooting = sorted({key for _, key, cell in cells if (blocks(cell) or 0) >= 2})
    non_empty_clean = all(blocks(cell) == 1 for _, key, cell in cells
                          if key in NON_EMPTY_CELLS)
    return {
        "schemaVersion": 1,
        "release": "finding-046-overshoot",
        "predictionFile": "findings/evidence/046/overshoot/PREDICTION.md",
        "evidenceClass": "diagnostic",
        "engineIsFrozenShipping": all(
            (r.get("artifact") or {}).get("wasmSha256") == FROZEN_WASM
            for r in results),
        "runs": [{"run": r["_run"], "browser": r.get("browserName"),
                  "cells": len(r.get("cells") or {}),
                  "matrixEntryAssertion": r.get("matrixEntryAssertion")}
                 for r in results],
        "findings": findings,
        "held": [k for k, v in findings.items() if v["status"] == "HELD"],
        "failed": [k for k, v in findings.items() if v["status"] == "FAILED"],
        "overshootingCells": overshooting,
        "scope": (
            "EMPTY-PARAGRAPH-ONLY"
            if overshooting == [EMPTY_CELL] and non_empty_clean
            else "WIDER-THAN-EMPTY-PARAGRAPHS" if overshooting
            else "NOT_OBSERVED"),
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

    check("baseline: the scope is empty-paragraph-only",
          baseline["scope"] == "EMPTY-PARAGRAPH-ONLY", baseline["scope"])
    check("baseline: the engine is the frozen shipping one",
          baseline["engineIsFrozenShipping"] is True)

    def edge_overshoots(results):
        for result in results:
            cell = (result.get("cells") or {}).get("text-end")
            if cell:
                cell["result"]["formatBarrier"]["readback"]["blockCount"] = 2
                cell["accepted"] = False

    mutated = rejudge(edge_overshoots)
    check("an edge cell that overshoots takes P-OV-3 away",
          mutated["findings"]["P-OV-3"]["status"] == "FAILED")
    check("and it widens the scope -- the sentence follows the data",
          mutated["scope"] == "WIDER-THAN-EMPTY-PARAGRAPHS")

    def edge_caret_never_reached_the_end(results):
        for result in results:
            cell = (result.get("cells") or {}).get("text-end")
            if cell:
                cell["caretPastText"] = False

    check("an edge cell whose caret did not reach the end loses its premise",
          rejudge(edge_caret_never_reached_the_end)["findings"]["P-OV-3"]
          ["premiseHeld"] is False)

    def empty_stops_overshooting(results):
        for result in results:
            cell = (result.get("cells") or {}).get(EMPTY_CELL)
            if cell:
                cell["result"]["formatBarrier"]["readback"]["blockCount"] = 1
                cell["accepted"] = True

    mutated = rejudge(empty_stops_overshooting)
    check("an empty cell that stops overshooting takes P-OV-2 away",
          mutated["findings"]["P-OV-2"]["status"] == "FAILED")
    check("and the scope becomes NOT_OBSERVED rather than staying put",
          mutated["scope"] == "NOT_OBSERVED")

    def containment_catches_it(results):
        for result in results:
            cell = (result.get("cells") or {}).get(EMPTY_CELL)
            if cell:
                cell["result"]["formatBarrier"]["containment"]["held"] = False

    check("a containment that DOES catch the overshoot takes P-OV-6 away",
          rejudge(containment_catches_it)["findings"]["P-OV-6"]["status"]
          == "FAILED")

    def all_cells_error(results):
        for result in results:
            for cell in (result.get("cells") or {}).values():
                cell["error"] = {"code": "CARET_NOT_AT_ANCHOR"}

    mutated = rejudge(all_cells_error)
    check("cells that failed their caret gate are excluded, not counted",
          mutated["held"] == [] and mutated["scope"] == "NOT_OBSERVED")

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
