#!/usr/bin/env python3
"""121's browser witness (SPEC-M3-autosave §9.12): a drag 0.3 -> 0.5, then Backspace / Delete.  Per selection arm:
the latency line read after the key is 「刪除選取 N ms」, no toast, the shape after the key is `collapsed`, and the
shape after the drag was a range (else the arm proves nothing).  Exit 0 = every arm holds in both browsers.

  read_121_witness.py REPORT.json
"""
import json
import re
import sys

r = json.load(open(sys.argv[1]))
bad, seen = [], {}
for run in r.get("runs") or []:
    b = run.get("browser")
    for arm in run.get("selection") or []:
        key = arm.get("arm")
        seen.setdefault(b, set()).add(key)
        log = arm.get("log") or []
        lat = [e.get("latency") for e in log if e.get("latency")]
        shapes = [e.get("shape") for e in log if e.get("shape")]
        drag = (arm.get("afterDrag") or {}).get("shape")
        ok_lat = any(re.fullmatch(r"刪除選取 \d+ ms", x or "") for x in lat)
        last = shapes[-1] if shapes else None
        print(f"{b} {key}: afterDrag {drag} latency {sorted(set(lat))} toasts {arm.get('toasts')} last shape {last} gens {arm.get('gens')}")
        if drag in (None, "collapsed") or not ok_lat or arm.get("toasts") != [] or last != "collapsed":
            bad.append(f"{b} {key}")
for b in ("chrome", "firefox"):
    if seen.get(b) != {"selection+Backspace", "selection+Delete"}:
        bad.append(f"{b}: arms {sorted(seen.get(b, []))}")
print("121-witness", "PASS" if not bad else "FAIL", bad)
sys.exit(1 if bad else 0)
