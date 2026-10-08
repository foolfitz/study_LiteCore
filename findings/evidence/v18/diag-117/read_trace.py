#!/usr/bin/env python3
"""Reader for finding 117's diagnosis (PREDICTION.md in this directory): R0, D1-D4.

Written 2026-10-08, BEFORE the diagnostic run.  Reads committed reports of
`tools/run_merge_wasm_shakedown.py` run on `e2-editor-v18-trace117`; runs nothing.

    read_trace.py M2-4-REPORT [--m2-1b M2-1B-REPORT]
    read_trace.py --self-test

Times are the page's clock.  For one press, `tc` is the worker time of the
engine's `editor-action-completed` event and `k` its `keyToUndoMs`, so the key
went out at `tk = tc - k` (k is floored to whole ms by the engine and the emit
is synchronous; MARGIN absorbs both).  An event's offset is `tw - tk`.

Output: one line per question, then `VERDICT ...`.  Exit 0 = every measured
question HIT; 1 = a MISS; 3 = STOP (the instrument is absent or a population
is short: "no callback arrived" must never be read off a trace that recorded
nothing -- the shakedown's `m2-4-chrome.json`, which has no trace, is the red
case and must STOP).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MARGIN = 5.0             # ms either side of tk and tc
SLOW = 1990              # keyToUndoMs at or above: waited out the 2000 ms deadline
FAST_PREDICTED = [1, 3, 55]
PRESSES = 105
M2_1B_N = 20
HEIGHTS = {3: 51650, 2: 34528, 1: 17406}   # twips: N * 16838 + (N + 1) * 284


def completion(window: list) -> dict | None:
    done = [e for e in window if e.get("k") == "e" and e.get("type") == "editor-action-completed"]
    return done[0] if len(done) == 1 else None


def lok_after_key(window: list, done: dict) -> list:
    """lok events strictly after the key (offset > MARGIN) and before the completion."""
    tk = done["tw"] - done["keyToUndoMs"]
    return [{"id": e["id"], "offset": round(e["tw"] - tk, 1), "head": e.get("head")}
            for e in window if e.get("k") == "e" and e.get("type") == "lok"
            and e.get("tw") is not None and MARGIN < e["tw"] - tk <= done["keyToUndoMs"]]


def judge(m24: dict, m21b: dict | None) -> tuple[list[str], dict]:
    lines, verdict = [], {}
    case = next((c for c in m24.get("cases", []) if c.get("criterion") == "M2-4"), None)
    presses = (case or {}).get("presses") or []
    dones = [completion(p.get("trace") or []) for p in presses]
    if len(presses) != PRESSES or any(d is None or d.get("tw") is None for d in dones):
        missing = [p.get("press") for p, d in zip(presses, dones) if d is None]
        lines.append(f"STOP: M2-4 has {len(presses)} presses (want {PRESSES}); presses without exactly "
                     f"one traced completion: {missing[:10]}{'...' if len(missing) > 10 else ''}")
        return lines, {"STOP": True}
    k = [p.get("keyToUndoMs") for p in presses]
    if any(d["keyToUndoMs"] != kk for d, kk in zip(dones, k)):
        lines.append("STOP: a traced completion's keyToUndoMs differs from the reply's")
        return lines, {"STOP": True}
    fast = [p["press"] for p in presses if p["keyToUndoMs"] < 1000]
    slow = [p for p in presses if p["keyToUndoMs"] >= SLOW]
    verdict["R0"] = fast == FAST_PREDICTED and len(slow) == PRESSES - len(FAST_PREDICTED)
    lines.append(f"R0 (117 reproduces on the trace profile): fast {fast}, slow {len(slow)}, "
                 f"other {PRESSES - len(fast) - len(slow)} -> {'HIT' if verdict['R0'] else 'MISS'}")

    after = {p["press"]: lok_after_key(p["trace"], d) for p, d in zip(presses, dones)}
    late = {p["press"]: after[p["press"]] for p in slow if after[p["press"]]}
    verdict["D1"] = not late
    ids: dict = {}
    for events in late.values():
        for e in events:
            ids[e["id"]] = ids.get(e["id"], 0) + 1
    lines.append(f"D1 (no lok event after the key on a slow press): {len(slow) - len(late)} of {len(slow)} "
                 f"slow presses have none; ids on the others {dict(sorted(ids.items()))} -> "
                 f"{'HIT' if verdict['D1'] else 'MISS'}")
    for press in list(late)[:5]:
        lines.append(f"   press {press}: {late[press][:6]}")

    def has(press, wanted, text=None):
        return any(e["id"] == wanted and (text is None or text in (e.get("head") or "")) for e in after[press])
    d2 = {1: has(1, 8, ".uno:Undo"), 3: has(3, 13), 55: has(55, 13)}
    verdict["D2"] = all(d2.values())
    lines.append(f"D2 (press 1: STATE_CHANGED .uno:Undo; 3 and 55: DOCUMENT_SIZE_CHANGED after the key): "
                 f"{d2}; ids after the key: 1 {[e['id'] for e in after[1]]}, 3 {[e['id'] for e in after[3]]}, "
                 f"55 {[e['id'] for e in after[55]]} -> {'HIT' if verdict['D2'] else 'MISS'}")

    toasts = [(p["press"], e.get("text")) for p in presses for e in p["trace"] if e.get("k") == "t"]
    unpainted = [(p["press"], e) for p in presses for e in p["trace"]
                 if e.get("k") == "p" and e.get("ok") and (e.get("painted") or 0) < 0.5]
    paints = sum(1 for p in presses for e in p["trace"] if e.get("k") == "p")
    heights = sorted({e.get("docH") for p in presses for e in p["trace"] if e.get("k") == "p"} - {None})
    strip = [e for press, e in unpainted if press == 55]
    verdict["D3"] = (len(toasts) == 1 and toasts[0][0] == 55 and len(unpainted) == 1 and bool(strip)
                     and strip[0].get("y") == 0 and strip[0].get("h") == HEIGHTS[2]
                     and strip[0].get("docH") == HEIGHTS[1] and strip[0].get("changed") is True)
    if paints == 0:
        lines.append("STOP: no paint was recorded in any press window")
        return lines, {"STOP": True}
    lines.append(f"D3 (one toast, press 55, the strip asked for the 2-page height of a 1-page document): "
                 f"toasts {toasts}; paints {paints}, below one half {[(p, {x: e.get(x) for x in ('y', 'h', 'rows', 'docH', 'changed', 'painted')}) for p, e in unpainted]}; "
                 f"document heights seen {heights} -> {'HIT' if verdict['D3'] else 'MISS'}")

    if m21b is None:
        lines.append("D4: NOT MEASURED (no M2-1b report given)")
        return lines, verdict
    records = [c for c in m21b.get("cases", []) if c.get("outcome") == "verified-key-undo"]
    traced = [(c, completion(c.get("keyTrace") or [])) for c in records]
    if len(records) != M2_1B_N or any(d is None for _, d in traced):
        lines.append(f"STOP: M2-1b has {len(records)} verified records (want {M2_1B_N}) or a record without "
                     "exactly one traced completion")
        verdict["STOP"] = True
        return lines, verdict
    firsts = []
    for c, d in traced:
        events = lok_after_key(c["keyTrace"], d)
        firsts.append((c["case"], d["keyToUndoMs"], events[0]["offset"] if events else None,
                       events[0]["id"] if events else None))
    verdict["D4"] = all(f is not None and k - 15 <= f <= k for _, k, f, _ in firsts)
    lines.append(f"D4 (typed merge: the first lok event after the key arrives within 15 ms before the "
                 f"completion): (case, keyToUndoMs, first offset, id) {firsts} -> "
                 f"{'HIT' if verdict['D4'] else 'MISS'}")
    return lines, verdict


def report(lines: list[str], verdict: dict) -> int:
    for line in lines:
        print(line)
    if verdict.get("STOP"):
        print("VERDICT STOP")
        return 3
    print("VERDICT " + " ".join(f"{q} {'HIT' if v else 'MISS'}" for q, v in verdict.items()))
    return 0 if all(verdict.values()) else 1


def synthetic(late_id: int | None = None, toast_press: int = 55, drop_trace: bool = False) -> dict:
    """A report shaped like the runner's, every prediction true unless told otherwise."""
    presses, t = [], 1000.0
    height = HEIGHTS[3]
    for n in range(1, PRESSES + 1):
        k = 37 if n in FAST_PREDICTED else 2000
        tk = t + 100
        window = [{"k": "e", "type": "lok", "id": 1, "tw": tk - 3, "head": "0, 0, 100, 100"}]
        if n == 1:
            window.append({"k": "e", "type": "lok", "id": 8, "tw": tk + 30, "head": ".uno:Undo=enabled"})
        if n in (3, 55):
            window.append({"k": "e", "type": "lok", "id": 13, "tw": tk + 30, "head": "12474, 0"})
        if late_id is not None and n == 10:
            window.append({"k": "e", "type": "lok", "id": late_id, "tw": tk + 100, "head": ""})
        window.append({"k": "e", "type": "editor-action-completed", "tw": tk + k, "keyToUndoMs": k})
        new = HEIGHTS[2] if n == 3 else HEIGHTS[1] if n == 55 else height
        painted = 0.49 if n == 55 else 0.9
        window.append({"k": "p", "ok": True, "y": 0, "h": height, "rows": 900, "docH": new,
                       "changed": new != height, "painted": painted})
        if n == toast_press:
            window.append({"k": "t", "text": "重繪失敗：TILE_NOT_PAINTED"})
        height = new
        presses.append({"press": n, "keyToUndoMs": k, "trace": [] if drop_trace else window})
        t += 3000
    return {"cases": [{"criterion": "M2-4", "presses": presses}]}


def self_test() -> int:
    cases = [("all predictions hold", synthetic(), 0),
             ("no trace (the shakedown's report shape) STOPs", synthetic(drop_trace=True), 3),
             ("an INVALIDATE_TILES 100 ms after a slow press's key is a D1 MISS", synthetic(late_id=0), 1),
             ("a toast on press 54 is a D3 MISS", synthetic(toast_press=54), 1)]
    bad = 0
    for name, data, want in cases:
        lines, verdict = judge(data, None)
        got = 3 if verdict.get("STOP") else (0 if all(verdict.values()) else 1)
        print(f"{'ok ' if got == want else 'BAD'} exit {got} (want {want}): {name}")
        bad += got != want
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("m24", nargs="?", type=Path)
    ap.add_argument("--m2-1b", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.m24 is None:
        ap.error("an M2-4 report is required")
    m21b = json.loads(args.m2_1b.read_text()) if args.m2_1b else None
    return report(*judge(json.loads(args.m24.read_text()), m21b))


if __name__ == "__main__":
    sys.exit(main())
