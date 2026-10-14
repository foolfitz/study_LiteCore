#!/usr/bin/env python3
"""Read-only counts for the 10-14g/10-14k clause table, from a 129-B round's arms-*.jsonl (no judgement, facts only).

Usage: clause_counts.py ROUND_DIR [ROUND_DIR ...]
Per browser and round: m4 arms, toolbar shape after the key (m4 arms), arms with a toast / a pp toast / pill 'stopped',
red-control arms that refused, key-to-move split by whether the key moved the caret (so the 200/400 ms limits can be read
off).  Exits 1 when a file is missing or holds no m4 arm (a count over nothing would read as 'zero').
"""
import collections
import json
import sys
from pathlib import Path


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    bad = False
    for rnd in map(Path, argv[1:]):
        print(f"## {rnd.name}")
        for b in ("chrome", "firefox"):
            arms = [json.loads(x) for x in (rnd / f"arms-{b}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
            m4 = [a for a in arms if a.get("kind") == "m4"]
            red = [a for a in arms if a.get("kind") == "red"]
            if not m4:
                print(f"{b}: NO m4 ARMS")
                bad = True
                continue
            shapes = collections.Counter(((a.get("afterKey") or {}).get("toolbar") or {}).get("shape") for a in m4)
            toast = [a["arm"] for a in m4 if a.get("toasts")]
            pptoast = [a["arm"] for a in m4 if a.get("ppToasts")]
            stopped = [a["arm"] for a in m4 if "stopped" in (a.get("pillStates") or [])]
            moved = [(a["timing"].get("moveDoneMs"), a["arm"]) for a in m4
                     if a["afterKey"]["caret"] != a["beforeKey"]["caret"] and a["timing"].get("moveDoneMs") is not None]
            still = [(a["timing"].get("moveDoneMs"), a["arm"]) for a in m4
                     if a["afterKey"]["caret"] == a["beforeKey"]["caret"] and a["timing"].get("moveDoneMs") is not None]
            nokey = [a["arm"] for a in m4 if a["timing"].get("moveDoneMs") is None]
            swap = sum(1 for a in m4 if (a.get("swapDuringArm") or {}).get("pswpin") or (a.get("swapDuringArm") or {}).get("pswpout"))
            print(f"{b}: m4 arms {len(m4)}; toolbar after key {dict(shapes)}; arms with toast {len(toast)} {toast}; "
                  f"with pp toast {len(pptoast)}; pill stopped {len(stopped)}; arms with no key record {len(nokey)}")
            if moved:
                print(f"  keys that moved the caret: {len(moved)}, moveDoneMs {min(moved)[0]}..{max(moved)[0]} (limit 200)")
            if still:
                print(f"  keys that did not move it: {len(still)}, moveDoneMs {min(still)[0]}..{max(still)[0]} (limit 400)")
            print(f"  red arms {len(red)}, refused {sum(1 for a in red if a.get('refused') or ('EDITOR_FORMAT_GESTURE_UNSUPPORTED' in json.dumps(a.get('toasts') or [], ensure_ascii=False)))}; "
                  f"m4 arms with swap activity {swap}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
