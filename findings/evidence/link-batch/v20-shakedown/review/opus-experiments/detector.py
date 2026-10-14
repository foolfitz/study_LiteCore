#!/usr/bin/env python3
"""P2-c's lone-flush detector (run_v20_shakedown.lok_summary, HEAD) on review 6 appendix A's timeline:
the lone size bump at 3 ms after the click, the click's own caret callback at 22..28 ms (finding 048)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "head" / "wasm_sdk_probe" / "tools"))
sys.dont_write_bytecode = True
import run_v20_shakedown as R

def ev(i, t): return {"k": "mt", "type": "lok", "id": i, "tw": float(t)}
for ack in (22, 24, 25, 26, 28):
    s = R.lok_summary([ev(13, 3.0), ev(1, 3.0 + ack)])   # 13 alone in its flush; the click's caret ack later
    print(f"lone 13 at 3 ms, click's INVALIDATE_VISIBLE_CURSOR at +{ack} ms -> lone {len(s['lone'])}, flanked {s['flanked']}")
for comp in (8, 14, 5):
    s = R.lok_summary([ev(13, 100.0), ev(comp, 100.2)])
    print(f"13 with only id {comp} in the same flush -> lone {len(s['lone'])}")
s = R.lok_summary([ev(13, 100.0), ev(0, 100.2)])
print(f"13 with only id 0 (tiles, no caret) in the same flush -> lone {len(s['lone'])} (seq still advances with the caret unmoved)")
print("NOT_LONE_IDS", R.NOT_LONE_IDS, "LONE_WINDOW_MS", R.LONE_WINDOW_MS)
