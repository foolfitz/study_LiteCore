#!/usr/bin/env python3
"""SPEC-P-calc-undo 4.4 NU-2: the Calc undo stack as LOK reports it, on the native driver with callbacks (calc_undo_native.cpp).

One document, one sequence of steps.  After each step the undo and redo lists (getCommandValues .uno:Undo / .uno:Redo) are read, and
around the undos the cell cursor (.uno:CellCursor) and the op 0 geometry of the cells involved.  Undo and redo are posted with
notification and the completion callback is waited for (uno-wait).  This script never compiles.
  probe_calc_undo_stack_native.py --binary build/calc-undo-native/undo/calc-undo-native --out DIR
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import run_calc_cell_native as native
from create_calc_edit_fixture import create
import probe_calc_undo_native as nu

LISTS = [{"action": "command-values", "command": ".uno:Undo"}, {"action": "command-values", "command": ".uno:Redo"}]
CURSOR = {"action": "command-values", "command": ".uno:CellCursor"}


def read(column, row):
    return dict(part=0, column=column, row=row, operation=0, enabled=0, text="")


def wait(command):
    return {"action": "uno-wait", "command": command, "timeoutMs": 3000}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    nu.BINARY = args.binary.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = create(out / "fixture")
    own = out / "stack-fixture.ods"
    shutil.copyfile(fixture, own)
    saved = out / "saved-mid-sequence.ods"
    steps = [
        ("fresh", []),
        ("cursor-to-A1", [{"action": "lok-select", "part": 0, "address": "A1"}]),
        ("undo-on-empty", [wait(".uno:Undo")]),
        ("redo-on-empty", [wait(".uno:Redo")]),
        ("input-F1", [nu.write(5, 0, 1, "ONE")]),
        ("input-F1-same", [nu.write(5, 0, 1, "ONE")]),
        ("range-bold", [nu.ranged(7, enabled=1)]),
        ("range-bold-again", [nu.ranged(7, enabled=1)]),
        ("save", [{"action": "save", "url": saved.as_uri()}]),
        ("cursor-before-undo", [CURSOR]),
        ("undo-1", [wait(".uno:Undo"), CURSOR]),
        # Added after the first run (nu2-stack): there the cursor already sat on F1, so undoing F1's input could not show a move.
        ("cursor-to-A1-again", [{"action": "lok-select", "part": 0, "address": "A1"}]),
        ("undo-2", [wait(".uno:Undo"), CURSOR]),
        ("redo-1", [wait(".uno:Redo"), CURSOR]),
        ("input-F2-after-undo", [nu.write(5, 1, 1, "NEW")]),
        ("redo-after-new-write", [wait(".uno:Redo")]),
        ("geometry", [read(5, 0), read(5, 1), read(0, 0), read(1, 1)]),
    ]
    requests, index = [], []
    for name, actions in steps:
        start = len(requests)
        requests += actions + LISTS
        index.append((name, start, len(actions)))
    replies = nu.run_driver(out, "stack", own, requests)
    observed = []
    for name, start, n in index:
        undo, redo = replies[start + n], replies[start + n + 1]
        observed.append({"step": name, "replies": replies[start:start + n],
                         "undo": [a.get("comment") for a in undo.get("actions", [])],
                         "redo": [a.get("comment") for a in redo.get("actions", [])]})
    by = {o["step"]: o for o in observed}
    counts = {o["step"]: (len(o["undo"]), len(o["redo"])) for o in observed}
    preconditions = {
        "fresh-is-empty": counts["fresh"] == (0, 0),
        "a-write-adds-one": counts["input-F1"] == (1, 0),
        "an-unchanged-write-adds-none": counts["input-F1-same"] == (1, 0) and counts["range-bold-again"] == counts["range-bold"],
        "undo-moves-one-to-redo": counts["undo-1"] == (counts["save"][0] - 1, 1) and counts["undo-2"] == (counts["save"][0] - 2, 2),
        "redo-moves-one-back": counts["redo-1"] == (counts["undo-2"][0] + 1, 1),
        "a-write-after-undo-clears-redo": counts["input-F2-after-undo"][1] == 0,
        "save-keeps-the-stack": counts["save"] == counts["range-bold-again"],
    }
    report = {"binary": str(nu.BINARY), "binarySha256": hashlib.sha256(nu.BINARY.read_bytes()).hexdigest(),
              "toolSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "counts": counts, "preconditions": preconditions, "steps": observed,
              "emptyStack": {"undo": by["undo-on-empty"]["replies"][0], "redo": by["redo-on-empty"]["replies"][0],
                             "redoAfterNewWrite": by["redo-after-new-write"]["replies"][0]},
              "cursor": {k: by[k]["replies"][-1] for k in ("cursor-to-A1", "cursor-before-undo", "undo-1", "cursor-to-A1-again", "undo-2", "redo-1")},
              "geometry": by["geometry"]["replies"]}
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"preconditions": preconditions, "counts": counts, "emptyStack": report["emptyStack"]}, ensure_ascii=False))
    return 0 if all(preconditions.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
