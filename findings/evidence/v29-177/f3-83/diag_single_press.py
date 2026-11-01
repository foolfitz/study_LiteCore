#!/usr/bin/env python3
"""The decisive diagnostic for F3-83's moved cell.  Not F3 and not a count.

Prediction, written before this ran: `format_arm` in run_e2_c_product_path.py presses the format button twice, at :6765 and :6834,
3-10 ms apart.  v28 answered too slowly for the cache to move between them, so both asked for ON.  v29 answers in 3 ms, the second
press reads the new cache and asks for OFF.  Remove the first press and nothing else, here in memory: every cell must equal F3-82,
Firefox three times and Chrome once.  If the cell still moves, this explanation is wrong.
  diag_single_press.py --browser firefox --out DIR
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "wasm_sdk_probe/tools"))
import run_v83_f3_clipboard as r  # noqa: E402

TAIL = '                "return b ? !b.disabled : null; })()")\n'
PRESS = '            evaluate(session, PRESS.replace("ARG_ACTION", action))\n'
NEXT = '            # WAIT ON THE COMPLETION SIGNAL, AND RECORD THE STATE CACHE.\n'
r.REPLACEMENTS = r.REPLACEMENTS + (("diag-single-press", TAIL + PRESS + NEXT, TAIL + NEXT),)
raise SystemExit(r.main())
