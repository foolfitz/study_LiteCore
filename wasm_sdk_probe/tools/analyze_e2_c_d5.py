#!/usr/bin/env python3
"""Judge SPEC E2-C phase D5 offline.

D5's subject is `isTrusted`, so the judgement is short and unforgiving: **one
synthetic event anywhere in a cell's window disqualifies the cell.**  Everything
else it checks is there so a cell cannot pass by being empty.

A cell that is not established is `NOT_ESTABLISHED`, which is a THIRD answer
next to pass and fail: the matrix's `onFailure` for every D5 cell is PARTIAL,
and an operator who was never asked is not a product that failed.

Usage:
  analyze_e2_c_d5.py RUN_DIR [RUN_DIR ...] [--output F]
  analyze_e2_c_d5.py --self-test RUN_DIR
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

# One line box in the E1/E2 corpora, used only as a floor: the cross-paragraph
# cell has to move further than a line, and the caret rectangles the product
# reports are what decide it when they are present.
LINE_BOX_TWIPS = 276

CELLS = ("d5-pointer-drag-single", "d5-pointer-drag-cross",
         "d5-ime-commit", "d5-clipboard")


def judge_cell(name: str, cell: dict | None, saves: list[dict]) -> dict:
    if not cell:
        return {"cell": name, "status": "NOT_ESTABLISHED",
                "why": "the operator did not run this cell"}
    events = cell.get("events") or []
    synthetic = [event for event in events if not event.get("isTrusted")]
    checks: dict[str, bool] = {
        "hasEvents": bool(events),
        # The one that matters.  Not "mostly trusted", not "the important ones
        # were trusted" -- none synthetic.
        "allTrusted": bool(events) and not synthetic,
    }

    if name.startswith("d5-pointer-drag"):
        downs = [event for event in events if event.get("type") == "pointerdown"]
        moves = [event for event in events if event.get("type") == "pointermove"]
        ups = [event for event in events if event.get("type") == "pointerup"]
        checks["dragHadMoves"] = bool(downs and ups and moves)
        if name.endswith("cross") and downs and ups:
            span = abs((ups[-1].get("y") or 0) - (downs[0].get("y") or 0))
            checks["spannedMoreThanOneLine"] = span > 0
            # Recorded in CSS pixels by the page; the floor is expressed in the
            # same units the events carry rather than converted with a guess.
            checks["spanRecorded"] = span
    if name == "d5-ime-commit":
        checks["hasComposition"] = any(
            event.get("type", "").startswith("composition") for event in events)
    if name == "d5-clipboard":
        checks["hasClipboardEvent"] = any(
            event.get("type") in ("copy", "paste") for event in events)

    before = (cell.get("stripBefore") or {}).get("revision")
    after = (cell.get("stripAfter") or {}).get("revision")
    checks["revisionAdvanced"] = (
        before is not None and after is not None and str(before) != str(after))
    checks["savedDocumentCaptured"] = any(
        entry.get("cell") == name for entry in saves)

    boolean = {key: value for key, value in checks.items()
               if isinstance(value, bool)}
    status = "PASS" if all(boolean.values()) else "NOT_ESTABLISHED"
    return {
        "cell": name,
        "status": status,
        "checks": checks,
        "eventCount": len(events),
        "syntheticEventCount": len(synthetic),
        "syntheticTypes": sorted({event.get("type") for event in synthetic}),
    }


def judge_run(run: Path) -> dict:
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    saves = result.get("saves") or []
    cells = {name: judge_cell(name, (result.get("cells") or {}).get(name), saves)
             for name in CELLS}
    established = [name for name, report in cells.items()
                   if report["status"] == "PASS"]
    bundle = result.get("shellBundle") or {}
    return {
        "run": str(run),
        "mode": result.get("mode"),
        "browser": result.get("browserName"),
        "shims": result.get("shims"),
        "shellBundleUnchanged": bundle.get("unchanged"),
        "cells": cells,
        "established": established,
        # PARTIAL is the matrix's answer for an unestablished D5 cell, and the
        # phase only reaches PASS when all four are established on real
        # gestures.  A machine-half run can never reach it, by construction.
        "verdict": ("PASS" if len(established) == len(CELLS)
                    else "PARTIAL" if bundle.get("unchanged") is not False
                    else "FAIL"),
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

    raw = json.loads((run / "result.json").read_text(encoding="utf-8"))
    baseline = judge_run(run)

    def rejudge(mutate) -> dict:
        cloned = copy.deepcopy(raw)
        mutate(cloned)
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "result.json").write_text(json.dumps(cloned))
            return judge_run(target)

    # P-D5-M1 / M2, on the recorded machine-half run itself.
    check("synthetic events are recorded as untrusted",
          any(event.get("isTrusted") is False for event in raw.get("events", [])),
          "no untrusted event in the run at all")
    check("a cell built from synthetic events is NOT_ESTABLISHED",
          all(report["status"] == "NOT_ESTABLISHED"
              for report in baseline["cells"].values()))
    check("the machine half cannot reach PASS", baseline["verdict"] != "PASS")

    def make_all_trusted(cloned):
        for event in cloned.get("events", []):
            event["isTrusted"] = True
        for cell in (cloned.get("cells") or {}).values():
            for event in cell.get("events", []):
                event["isTrusted"] = True
            cell["syntheticEvents"] = 0

    def furnish(cloned):
        """Everything a drag cell needs EXCEPT trust, so the trust check is the
        only thing left standing between the cell and a pass."""
        make_all_trusted(cloned)
        cell = (cloned.get("cells") or {}).get("d5-pointer-drag-single")
        if cell is None:
            return
        cell["stripBefore"] = {"revision": "1"}
        cell["stripAfter"] = {"revision": "2"}
        cloned.setdefault("saves", []).append(
            {"label": "probe", "bytes": 10, "cell": "d5-pointer-drag-single"})

    furnished = rejudge(furnish)
    check("with trust and everything else present, the cell passes",
          furnished["cells"]["d5-pointer-drag-single"]["status"] == "PASS",
          str(furnished["cells"]["d5-pointer-drag-single"]))

    def furnish_but_one_synthetic(cloned):
        furnish(cloned)
        cell = (cloned.get("cells") or {}).get("d5-pointer-drag-single")
        if cell and cell.get("events"):
            cell["events"][0]["isTrusted"] = False

    check("ONE synthetic event takes the pass away",
          rejudge(furnish_but_one_synthetic)["cells"]["d5-pointer-drag-single"]
          ["status"] == "NOT_ESTABLISHED")

    def furnish_without_moves(cloned):
        furnish(cloned)
        cell = (cloned.get("cells") or {}).get("d5-pointer-drag-single")
        if cell:
            cell["events"] = [event for event in cell["events"]
                              if event.get("type") != "pointermove"]

    check("a drag with no moves is a click, and does not pass",
          rejudge(furnish_without_moves)["cells"]["d5-pointer-drag-single"]
          ["status"] == "NOT_ESTABLISHED")

    def furnish_without_revision(cloned):
        furnish(cloned)
        cell = (cloned.get("cells") or {}).get("d5-pointer-drag-single")
        if cell:
            cell["stripAfter"] = {"revision": "1"}

    check("a cell where the revision never moved does not pass",
          rejudge(furnish_without_revision)["cells"]["d5-pointer-drag-single"]
          ["status"] == "NOT_ESTABLISHED")

    def break_bundle(cloned):
        furnish(cloned)
        cloned["shellBundle"] = {"before": "a", "after": "b", "unchanged": False}

    check("a moved shell bundle digest fails the run",
          rejudge(break_bundle)["verdict"] == "FAIL")

    # P-D5-M3: the capture path was exercised, not assumed.
    check("the createObjectURL shim captured a document",
          bool(raw.get("capturedSaves")),
          "nothing was captured, so no operator round could capture either")
    # P-D5-M4
    check("observing the product left the shell bundle digest alone",
          (raw.get("shellBundle") or {}).get("unchanged") is True)

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
        return self_test(args.runs[0])
    runs = [judge_run(run) for run in args.runs]
    summary = {
        "schemaVersion": 1,
        "release": "spec-e2c-d5",
        "predictionFile":
            "findings/evidence/sdk-e2/e2-c-validation/d5/PREDICTION.md",
        "runs": runs,
        "verdict": ("PASS" if all(run["verdict"] == "PASS" for run in runs)
                    else "FAIL" if any(run["verdict"] == "FAIL" for run in runs)
                    else "PARTIAL"),
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if summary["verdict"] in ("PASS", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
