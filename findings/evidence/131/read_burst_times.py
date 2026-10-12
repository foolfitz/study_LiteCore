#!/usr/bin/env python3
"""Per-key delete time inside each rapid20 burst (the N of 「⌫ 刪除 N ms」, in order), for proposed finding 132
(SPEC-M3-autosave §9.12: prediction, written before the run -- the 20th key's time on the fixed page exceeds
today's maxima, Chrome 150-250 ms, Firefox 200-300 ms).  Reads a probe_hand_test_0212.py report; prints every number.

  read_burst_times.py REPORT.json
"""
import json
import re
import sys

r = json.load(open(sys.argv[1]))
for run in r.get("runs") or []:
    b = run.get("browser")
    twentieth = []
    for i, x in enumerate((run.get("rapid20") or {}).get("rounds") or []):
        ms = [int(m.group(1)) for e in x.get("latency") or [] if (m := re.fullmatch(r"⌫ 刪除 (\d+) ms", e.get("text", "")))]
        twentieth.append(ms[19] if len(ms) >= 20 else None)
        print(f"{b} burst {i + 1}: {len(ms)} deletes, ms {ms}")
    print(f"{b} 20th key per burst {twentieth}")
