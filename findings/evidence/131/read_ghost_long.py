#!/usr/bin/env python3
"""The high/low arms with N rapid Backspaces (probe_hand_test_0212.py --ghost-rapid-keys N): per key, when the
caret moved and when the caret's band carried that key's change (ms from the key), and the stale time between
(staleAfterCaretMs, the deleted text drawn with the caret already past it).  Prints every number.

  read_ghost_long.py REPORT.json
"""
import json
import sys

r = json.load(open(sys.argv[1]))
for run in r.get("runs") or []:
    for arm in ("high", "low"):
        a = run.get(arm) or {}
        keys = a.get("rapid") or []
        if not keys:
            continue
        t0 = keys[0]["tKey"]
        stale = [k.get("staleAfterCaretMs") for k in keys]
        fresh_abs = [None if k.get("caretBandFreshMs") is None else round(k["tKey"] - t0 + k["caretBandFreshMs"], 1) for k in keys]
        moved_abs = [None if k.get("caretMovedMs") is None else round(k["tKey"] - t0 + k["caretMovedMs"], 1) for k in keys]
        print(f"{run['browser']} {arm}: {len(keys)} rapid keys (rapidKeys {a.get('rapidKeys')}), "
              f"last keydown at {round(keys[-1]['tKey'] - t0, 1)} ms, persistent {(a.get('persistent') or {}).get('differing')}")
        print(f"  stale per key {stale}")
        print(f"  caret moved at (from key 1) {moved_abs}")
        print(f"  band fresh at (from key 1)  {fresh_abs}")
        print(f"  max stale {max((s for s in stale if s is not None), default=None)}")
