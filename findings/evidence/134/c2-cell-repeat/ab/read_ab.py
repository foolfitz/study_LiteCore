#!/usr/bin/env python3
"""DIAGNOSTIC reader for the A/B (ruling-2 conditions 4-5).  Per run: page, on-screen and commit max, keys
>= 100 ms, and the stall signature = the longest gap between consecutive raw.paints inside
[key 8, key 13 + 100 ms] (keys 1-based).  Spike := on-screen >= 100 ms at any of keys 9-13.  Prints the
spike counts per page and the decision line of ruling-2 condition 5.  The exit code is not a verdict."""
import json
import sys
from pathlib import Path

NEW, OLD = "6470dec0", "abe93f45"
here = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent)
runs = sorted(here.glob("run-*-*.json"))
if not runs:
    sys.exit(f"no run-NN-<page>.json under {here}")
spikes = {NEW: 0, OLD: 0}
count = {NEW: 0, OLD: 0}
for path in runs:
    r = json.loads(path.read_text())
    page = str(r.get("page"))[:8]
    if page not in count or path.stem.split("-")[-1] != page or (r.get("servedFromMirror") or {}).get("sha256", "")[:8] != page:
        sys.exit(f"{path.name}: page {page} does not match its name or what the mirror served")
    rows = r.get("rows") or []
    screens = [x.get("onScreenMs") for x in rows]
    commits = [x.get("revisionMs") for x in rows if x.get("revisionMs") is not None]
    slow = [(i + 1, s) for i, s in enumerate(screens) if s is not None and s >= 100]
    spike = any(s is not None and s >= 100 for s in screens[8:13])
    keys = [t for _, t in r["raw"]["keys"]]
    lo, hi = keys[7], keys[12] + 100
    paints = [t for t in r["raw"]["paints"] if lo <= t <= hi]
    gap = max((b - a for a, b in zip(paints, paints[1:])), default=None)
    count[page] += 1
    spikes[page] += spike
    print(f"{path.name} rows {len(rows)} screen max {max(s for s in screens if s is not None)} "
          f"commit max {max(commits) if commits else None} slow>=100 {slow} stall-gap {round(gap, 1) if gap else gap} "
          f"spike {spike}")
print(f"spikes 0.2.15 ({OLD}) {spikes[OLD]}/{count[OLD]}, 0.2.16 ({NEW}) {spikes[NEW]}/{count[NEW]}")
n, o = spikes[NEW], spikes[OLD]
if n < 2:
    line = "A/B VOID: the 0.2.16 arm does not reproduce the counted cell"
elif o >= 2:
    line = "not 134's: both pages spike"
elif o == 0 and n >= 3:
    line = "page implicated: run the same 10 + 10 once more before the owner acts"
else:
    line = "inconclusive: one extension of 10 + 10, once, then report as is"
print("decision (ruling-2 condition 5):", line)
