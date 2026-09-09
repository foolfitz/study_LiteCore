#!/usr/bin/env python3
"""Read the banked boundary-arrow reports and print the matrix, every attempt.

`AGENTS.md` §1 form two: the enumeration is generated from the reports, so a
fourth arm added to `findings/evidence/096/boundary-arrow-*.json` appears here
without editing this file, and an arm whose file is missing is reported as
missing rather than silently absent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    files = sorted(HERE.glob("boundary-arrow-*.json"))
    if not files:
        print("no report files under findings/evidence/096/", file=sys.stderr)
        return 1
    rows = []
    for path in files:
        report = json.loads(path.read_text(encoding="utf-8"))
        for entry in report["attempts"]:
            rows.append({
                "profile": report["profile"],
                "wasm": report["wasmSha256"][:16],
                "page": report["pageSha256"][:16],
                "direction": entry["direction"],
                "attempt": entry["attempt"],
                "outcome": entry.get("outcome"),
                "deadState": entry.get("deadState"),
                "rescue": (entry.get("frameAfterWait") or {}).get("noticeRescue"),
                "noticeMatch": entry.get("noticeMatchesOwnerQuote"),
                "boundaryPress": entry.get("firstNonMovingPress"),
                "presses": entry.get("pressesSpent"),
                "waited": entry.get("waitedForDeathSeconds"),
                "scrollRoom": entry.get("scrollRoomPx"),
                "toast": next((t for t in reversed(entry.get("toasts") or [])
                               if "：" in t), None),
                "workerAnswered": [w.get("answered")
                                   for w in (entry.get("workerLiveness") or [])],
                "why": entry.get("why"),
            })
    width = max(len(r["profile"]) for r in rows)
    print(f"{'profile':{width}}  {'wasm':16}  dir   #  outcome              "
          f"state               bnd  pr  wait  room")
    for r in rows:
        print(f"{r['profile']:{width}}  {r['wasm']:16}  {r['direction']:4} "
              f"{r['attempt']:2}  {str(r['outcome']):20} "
              f"{str(r['deadState']):19} {str(r['boundaryPress']):>3} "
              f"{str(r['presses']):>3} {str(r['waited']):>5} "
              f"{str(r['scrollRoom']):>5}")
        if r["why"]:
            print(f"{'':{width}}  {'':16}  why: {r['why']}")
    print()
    tally: dict = {}
    for r in rows:
        key = (r["profile"], r["direction"])
        tally.setdefault(key, {})
        tally[key][r["outcome"]] = tally[key].get(r["outcome"], 0) + 1
    for (profile, direction), counts in sorted(tally.items()):
        total = sum(counts.values())
        repro = counts.get("REPRODUCED", 0)
        print(f"{profile:{width}}  {direction:4}  {repro}/{total} REPRODUCED   {counts}")
    print()
    print("engine-side, last error toast per attempt:")
    seen = set()
    for r in rows:
        if r["toast"] and r["toast"] not in seen:
            seen.add(r["toast"])
            print(f"  {r['profile']} {r['direction']}: {r['toast']}")
    print()
    print("worker JS thread answered a CDP evaluate after the verdict:")
    for r in rows:
        print(f"  {r['profile']} {r['direction']} #{r['attempt']}: "
              f"{r['workerAnswered']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
