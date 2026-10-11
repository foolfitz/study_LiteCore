#!/usr/bin/env python3
"""Read the witness (PREDICTION.md's rule, written before the run) from committed reports.

A witness-red cell: FAIL in the witness and PASS in all three 0.2.11 rounds of the same browser.
Every other movement (any cell whose witness outcome is not among the three reference outcomes) is listed
apart and is not witness-red.  Opens no browser, writes nothing.

    judge_witness.py WITNESS.json REF_r1.json REF_r2.json REF_r3.json

Exit 0: no witness-red cell.  1: at least one.  2: REFUSED (a report unreadable, browsers differ, check ids
differ, the witness incomplete).  The verdict is the SUMMARY line.
"""
from __future__ import annotations

import json
import sys


def load(path: str) -> dict:
    report = json.loads(open(path, encoding="utf-8").read())
    return report


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__)
        return 2
    try:
        witness, refs = load(argv[1]), [load(p) for p in argv[2:]]
    except (OSError, ValueError) as error:
        print(f"SUMMARY REFUSED {error}")
        return 2
    browsers = {r.get("browser") for r in [witness, *refs]}
    ids = [[c["id"] for c in r.get("checks") or []] for r in [witness, *refs]]
    if len(browsers) != 1:
        print(f"SUMMARY REFUSED browsers differ {sorted(map(str, browsers))}")
        return 2
    if any(i != ids[0] for i in ids) or not ids[0]:
        print("SUMMARY REFUSED check ids differ (or are empty) between the witness and the references")
        return 2
    if witness.get("complete") is not True:
        print(f"SUMMARY REFUSED the witness is not complete (complete={witness.get('complete')!r})")
        return 2
    outcome = lambda r: {c["id"]: c.get("outcome") for c in r["checks"]}
    w, rs = outcome(witness), [outcome(r) for r in refs]
    red, moved = [], []
    for cid in ids[0]:
        ref = [r[cid] for r in rs]
        if w[cid] == "FAIL" and all(o == "PASS" for o in ref):
            red.append((cid, ref))
        elif w[cid] not in ref:
            moved.append((cid, w[cid], ref))
    print(f"browser {browsers.pop()}  cells {len(ids[0])}  witness ok={witness.get('ok')} "
          f"verdict={witness.get('verdict')!r}")
    for cid, ref in red:
        print(f"WITNESS-RED  {cid}  witness FAIL  0.2.11 {'/'.join(ref)}")
    for cid, got, ref in moved:
        print(f"moved (not red)  {cid}  witness {got}  0.2.11 {'/'.join(map(str, ref))}")
    print(f"SUMMARY witness-red {len(red)}  other movements {len(moved)}")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
