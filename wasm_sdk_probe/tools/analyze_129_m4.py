#!/usr/bin/env python3
"""Read the raw arms-<browser>.jsonl / calibration-<browser>.json of tools/probe_129_m4_wasm.py and tabulate.

Nothing here measures anything.  It compares the '#' positions the probe stored with the native reference
(findings/evidence/129/native/) EXACTLY and BY RULE, and summarises timings, toasts and the extra arms.

  analyze_129_m4.py ROUND_DIR      writes ROUND_DIR/analysis.json and ROUND_DIR/summary.md

BY RULE (WASM lays out with other glyph metrics, so wrap offsets differ from native).  The rule is the
native result described in terms of THIS browser's wrap offsets, not an absolute offset:
  native S1 (soft wrap at spaces): W = first wrap offset (native 101), W2 = second (native: line 3 starts at 201)
  native token (mid-word wrap):    B = first wrap offset (native 89), B2 (native 180), B3 (native 270)
  for the shapes whose point is at the wrap offset (s1, s1d, m1d):
    Left  = W-1      Right = W+1     Up = 0 (start of the paragraph's first line)     Home = W (start of line 2)
    End   = W2-1 for S1 (before the trailing space), B2 for the token (no space)       Down(ref) = W2 / B2
    Down(emu), native s1d: the offset on line 2 whose caret x is nearest to the x of the END of line 1; native m1d: B3.
  every other shape (p2-*, s2..s5): the exact native flat index.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import probe_129_m4_wasm as m4  # noqa: E402

KEYS = m4.KEYS
SHAPES = ["p2-forward", "p2-backward", "s1", "s2", "s3", "s4", "s5", "s1d", "m1d"]
OLD = ["p2-forward", "p2-backward"]
BRIEF = ["s1", "s2", "s3", "s4", "s5"]
DRAG = ["s1d", "m1d"]
LIMIT_MS = 200


def load(rd: Path):
    arms, cal, report = {}, {}, {}
    for b in ("chrome", "firefox"):
        f = rd / f"arms-{b}.jsonl"
        if f.exists():
            # split on "\n" only: the probe wrote U+2028 (a text:line-break) raw into some paragraph texts and
            # str.splitlines() would cut those lines in two
            arms[b] = [json.loads(l) for l in f.read_text().split("\n") if l.strip()]
        c = rd / f"calibration-{b}.json"
        if c.exists():
            cal[b] = json.loads(c.read_text())
        r = rd / f"report-{b}.json"
        if r.exists():
            report[b] = json.loads(r.read_text())
    return arms, cal, report


def rule_values(shape: str, cal: dict) -> dict:
    """Expected flat indices BY RULE for the wrap shapes of this browser, or None for exact-native shapes."""
    if shape in ("s1", "s1d"):
        w = cal["s1Walk"]["wrapOffsets"]
        W, W2 = w[0], w[1]
        line2 = [(i, c["x"]) for i, c in enumerate(cal["s1Walk"]["carets"]) if c and W <= i < W2]
        x_end = cal["shapes"]["stops"][0]["end"]["x"]
        nearest = min(line2, key=lambda t: abs(t[1] - x_end))[0]
        ref = {"Left": W - 1, "Right": W + 1, "Up": 0, "Down": W2, "Home": W, "End": W2 - 1}
        emu = dict(ref, Down=nearest) if shape == "s1d" else dict(ref)
        return {"ref": ref, "emu": emu, "W": W, "W2": W2}
    if shape == "m1d":
        w = cal["m1Walk"]["wrapOffsets"]
        B, B2, B3 = w[0], w[1], w[2]
        ref = {"Left": B - 1, "Right": B + 1, "Up": 0, "Down": B2, "Home": B, "End": B2}
        emu = dict(ref, Down=B3)
        return {"ref": ref, "emu": emu, "B": B, "B2": B2, "B3": B3}
    return None


def stats(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {"n": len(xs), "min": min(xs), "median": statistics.median(xs), "max": max(xs)}


def main() -> int:
    rd = Path(sys.argv[1])
    arms, cal, report = load(rd)
    native = m4.load_native()
    out: dict = {"browsers": sorted(arms), "perBrowser": {}}
    L: list[str] = []
    P = L.append
    for b in sorted(arms):
        rows = arms[b]
        pb: dict = {}
        out["perBrowser"][b] = pb
        P(f"## {b} ({(report.get(b) or {}).get('version')})")
        P("")
        P(f"started {report[b]['startedAtUtc']}, completed {report[b]['completedAtUtc']} (UTC); loadavg {report[b]['loadavgStart']} -> {report[b]['loadavgEnd']}; "
          f"MemAvailable {report[b]['memoryStartMb']['MemAvailable']} -> {report[b]['memoryEndMb']['MemAvailable']} MB, SwapFree {report[b]['memoryStartMb']['SwapFree']} -> {report[b]['memoryEndMb']['SwapFree']} MB")
        P("")
        kinds = Counter((r["kind"], r["status"]) for r in rows)
        pb["byKindStatus"] = {f"{k}/{s}": n for (k, s), n in kinds.items()}
        P(f"arms by kind/status: {pb['byKindStatus']}")
        m4rows = [r for r in rows if r["kind"] == "m4"]
        pb["notFresh"] = [r["arm"] for r in m4rows if not r.get("fresh")]
        pb["selectionMismatch"] = [r["arm"] for r in m4rows if r["status"] == "selection-mismatch"]
        pb["notCounted"] = [(r["arm"], r["status"]) for r in m4rows if r["status"] != "counted"]
        P(f"not fresh: {pb['notFresh']}; selection-mismatch: {pb['selectionMismatch']}; other not counted: {pb['notCounted']}")
        # wrap offsets
        c = cal[b]
        if not m4rows:
            ctl = [r for r in rows if r["kind"] == "control"]
            by = defaultdict(list)
            for r in ctl:
                by[r["arm"]].append((r["timing"].get("moveDoneMs"), r["moved"]))
            pb["control"] = {k: v for k, v in by.items()}
            pb["controlStats"] = {k: {"moved": sorted({m for _, m in v}), "ms": stats([t for t, _ in v])} for k, v in by.items()}
            P("control only (collapsed caret on the patched page, no click; key -> the move's latency record):")
            for k, v in pb["controlStats"].items():
                P(f"  - {k}: caret moved {v['moved']}, ms {v['ms']}")
            P("")
            continue
        pb["wrap"] = {"s1": c["s1Walk"]["wrapOffsets"], "token": c["m1Walk"]["wrapOffsets"], "s1Lines": c["s1Lines"],
                      "stopsShapes": [(s["start"]["y"], s["end"]["x"]) for s in c["shapes"]["stops"]]}
        P(f"wrap offsets: S1 {pb['wrap']['s1']} (native 101, line 3 starts at 201); token {pb['wrap']['token']} (native 89, 180, 270); S1 lines: {c['s1Lines']} (native 5)")
        P("")
        # --- the per-shape table
        table = {}
        P("### where `#` landed: WASM against native ref / emu (flat index in the whole document text)")
        P("")
        P("| shape | key | WASM | native ref | native emu | = ref (exact) | = emu (exact) | by rule: ref / emu | note |")
        P("|---|---|---|---|---|---|---|---|---|")
        for shape in SHAPES:
            rules = rule_values(shape, c)
            for key in KEYS:
                r = next((x for x in m4rows if x["shape"] == shape and x["key"] == key), None)
                if r is None or "hash" not in r:
                    P(f"| {shape} | {key} | (no result: {r['status'] if r else 'missing'}) | | | | | | |")
                    continue
                idx = r["hash"]["flatIndex"]
                ref = native.get((shape, key, "ref"))
                emu = native.get((shape, key, "emu"))
                eq_ref = bool(ref) and idx == ref[0]
                eq_emu = bool(emu) and idx == emu[0]
                rule_ref = rule_emu = None
                if rules:
                    rule_ref = idx == rules["ref"][key]
                    rule_emu = idx == rules["emu"][key]
                else:
                    rule_ref, rule_emu = eq_ref, eq_emu
                note = ""
                if rules:
                    note = f"rule: ref {rules['ref'][key]}, emu {rules['emu'][key]}"
                table[f"{shape}/{key}"] = {"wasm": idx, "nativeRef": ref, "nativeEmu": emu, "eqRef": eq_ref, "eqEmu": eq_emu,
                                           "ruleRef": rule_ref, "ruleEmu": rule_emu, "ruleValues": ({"ref": rules["ref"][key], "emu": rules["emu"][key]} if rules else None),
                                           "excerpt": r["hash"].get("excerpt")}
                P(f"| {shape} | {key} | {idx} | {ref[0] if ref else '-'} | {emu[0] if emu else '-'} | {eq_ref} | {eq_emu} | {rule_ref} / {rule_emu} | {note} |")
        pb["table"] = table
        P("")
        # --- bottom lines
        def cells(shapes):
            return [table[f"{s}/{k}"] for s in shapes for k in KEYS if f"{s}/{k}" in table]
        old = cells(OLD)
        brief = cells(BRIEF)
        drag = cells(DRAG)
        pb["bottomLine"] = {
            "oldArmsEqualNativeRef": f"{sum(c['eqRef'] for c in old)}/{len(old)}",
            "briefExactRef": f"{sum(c['eqRef'] for c in brief)}/{len(brief)}",
            "briefByRuleRef": f"{sum(c['ruleRef'] or c['eqRef'] for c in brief)}/{len(brief)}",
            "briefNotExact": [k for k, v in table.items() if k.split('/')[0] in BRIEF and not v["eqRef"]],
            "dragKeysNonDownByRule": f"{sum(table[f'{s}/{k}']['ruleRef'] for s in DRAG for k in KEYS if k != 'Down' and f'{s}/{k}' in table)}/{sum(1 for s in DRAG for k in KEYS if k != 'Down' and f'{s}/{k}' in table)}",
            "dragDownFollowsRef": [s for s in DRAG if f"{s}/Down" in table and table[f"{s}/Down"]["ruleRef"]],
            "dragDownFollowsEmu": [s for s in DRAG if f"{s}/Down" in table and table[f"{s}/Down"]["ruleEmu"] and not table[f"{s}/Down"]["ruleRef"]],
        }
        P(f"bottom line: {json.dumps(pb['bottomLine'])}")
        P("")
        # --- timing and toasts
        P("### timing (keydown -> latency record), m4 arms")
        P("")
        mv = [r["timing"].get("moveDoneMs") for r in m4rows if r.get("timing")]
        ck = [r["timing"].get("clickDoneMs") for r in m4rows if r.get("timing")]
        pb["timing"] = {"moveDoneMs": stats(mv), "clickDoneMs": stats(ck)}
        slow = [(r["arm"], r["timing"]["moveDoneMs"], r["timing"]["clickDoneMs"]) for r in m4rows
                if r.get("timing") and (r["timing"].get("moveDoneMs") or 0) >= LIMIT_MS]
        pb["slowArms"] = slow
        moved = {}
        for r in m4rows:
            if r.get("timing") and r.get("afterKey"):
                moved[r["arm"]] = r["beforeKey"]["caret"] != r["afterKey"]["caret"]
        pb["slowArmsMoved"] = {a: moved.get(a) for a, _, _ in slow}
        pb["fastArmsMoved"] = dict(Counter(moved[r["arm"]] for r in m4rows if r.get("timing") and (r["timing"].get("moveDoneMs") or 0) < LIMIT_MS and r["arm"] in moved))
        split = {"moved": [], "notMoved": []}
        for r in m4rows:
            t = r.get("timing") or {}
            if t.get("moveDoneMs") is not None and t.get("clickDoneMs") is not None and r["arm"] in moved:
                split["moved" if moved[r["arm"]] else "notMoved"].append((t["moveDoneMs"], t["clickDoneMs"], round(t["moveDoneMs"] - t["clickDoneMs"], 1)))
        pb["timingSplit"] = {k: {"n": len(v), "keyToMoveDone": stats([x[0] for x in v]), "keyToClickDone": stats([x[1] for x in v]),
                                 "clickDoneToMoveDone": stats([x[2] for x in v])} for k, v in split.items()}
        P(f"split by whether the key moved the caret: {json.dumps(pb['timingSplit'])}")
        P(f"move done: {pb['timing']['moveDoneMs']}; click done (the 定位游標 record): {pb['timing']['clickDoneMs']}")
        P(f"arms with move >= {LIMIT_MS} ms: {len(slow)}; of those, the key moved the caret: {Counter(pb['slowArmsMoved'].values())}; arms < {LIMIT_MS} ms by 'moved the caret': {pb['fastArmsMoved']}")
        for a, mvms, ckms in slow:
            P(f"  - {a}: move {mvms} ms, click {ckms} ms")
        tm = [(r["arm"], r["toasts"]) for r in m4rows if r.get("toasts")]
        pb["m4ArmsWithToast"] = tm
        pb["m4PillStopped"] = [r["arm"] for r in m4rows if "stopped" in (r.get("pillStates") or [])]
        P(f"toasts in m4 arms (whole arm after the open): {len(tm)} arms {tm[:3]}; pill 'stopped' in: {pb['m4PillStopped']}")
        sw = [r.get("swapDuringArm", {}) for r in m4rows]
        pb["swapDuringArms"] = {"pswpinMin": min(s.get("pswpin", 0) for s in sw), "pswpinMax": max(s.get("pswpin", 0) for s in sw),
                                "pswpoutMin": min(s.get("pswpout", 0) for s in sw), "pswpoutMax": max(s.get("pswpout", 0) for s in sw),
                                "armsWithNoSwapActivity": sum(1 for s in sw if not s.get("pswpin") and not s.get("pswpout"))}
        P(f"swap pages during arms: {pb['swapDuringArms']}")
        P("")
        # --- shift
        sh = {r["arm"]: r for r in rows if r["kind"] == "shift"}
        pb["shift"] = {}
        if "m4-shift-collapsed" in sh:
            r = sh["m4-shift-collapsed"]
            pb["shift"]["collapsed"] = {"caretMoved": r["caretBefore"] != r["caretAfter"], "revision": [r["revisionBefore"], r["revisionAfter"]],
                                        "hash": r["hash"], "toasts": r["toasts"], "keydowns": r["keydowns"], "latencyRecords": r["latencyRecords"],
                                        "collapsedAfter": r["selectionCollapsedAfter"]}
        if "m4-shift-range" in sh:
            r = sh["m4-shift-range"]
            pb["shift"]["range"] = {"textBefore": r["before"]["text"], "textAfter": r["after"]["text"],
                                    "sameCaret": r["before"]["caret"] == r["after"]["caret"],
                                    "sameSelection": r["before"]["selection"] == r["after"]["selection"],
                                    "revision": [r["before"]["revision"], r["after"]["revision"]], "toasts": r["toasts"],
                                    "keydowns": r["keydowns"], "latencyRecords": r["latencyRecords"],
                                    "toolbar": [r["before"]["toolbar"], r["after"]["toolbar"]]}
        P(f"shift arms: {json.dumps(pb['shift'], ensure_ascii=False)}")
        P("")
        # --- red
        red = [r for r in rows if r["kind"] == "red"]
        pb["red"] = [{"arm": r["arm"], "refused": r.get("refusedWithDeveloperSentence"), "toast": (r.get("toasts") or [[None, None]])[0][1],
                      "latency": r["afterKey"]["latency"], "selectionOk": r["selection"]["matches"]} for r in red]
        P("red control: " + json.dumps(pb["red"], ensure_ascii=False))
        P("")
        # --- reach
        reach = [r for r in rows if r["kind"] == "reach"]
        pb["reach"] = [{"arm": r["arm"], "farX": r["far"]["x"], "lineEndX": r["lineEnd"]["x"], "caret": [r["after"]["caret"]["x"], r["after"]["caret"]["y"]],
                        "selectionEnd": [r["after"]["selectionEnd"]["x"], r["after"]["selectionEnd"]["y"]] if r["after"]["selectionEnd"] else None,
                        "text": r["after"]["text"]} for r in reach]
        P("reach (the page's own drag; where the visible caret ends): ")
        for x in pb["reach"]:
            P(f"  - {x}")
        P("")
        # --- control
        ctl = [r for r in rows if r["kind"] == "control"]
        by = defaultdict(list)
        for r in ctl:
            by[r["arm"]].append((r["timing"].get("moveDoneMs"), r["moved"]))
        pb["control"] = {k: v for k, v in by.items()}
        if ctl:
            P("control (collapsed caret, no click): " + json.dumps(pb["control"]))
            P("")
    # cross-checks: browsers within this round, and this round against another one (argv[2])
    cross: dict = {}
    bs = sorted(b for b in out["perBrowser"] if "table" in out["perBrowser"][b])
    if len(bs) == 2:
        t0, t1 = out["perBrowser"][bs[0]]["table"], out["perBrowser"][bs[1]]["table"]
        diff = [k for k in t0 if k in t1 and t0[k]["wasm"] != t1[k]["wasm"]]
        cross["browsersSameLanding"] = f"{len(t0) - len(diff)}/{len(t0)}"
        cross["browsersDiffer"] = diff
        P(f"## cross-check: {bs[0]} vs {bs[1]} landing index equal in {cross['browsersSameLanding']} cells; differ: {diff}")
        P("")
    if len(sys.argv) > 2:
        other, ocal, orep = load(Path(sys.argv[2]))
        for b in bs:
            if b not in other:
                continue
            ot = {}
            for r in other[b]:
                if r["kind"] == "m4" and "hash" in r:
                    ot[f"{r['shape']}/{r['key']}"] = r["hash"]["flatIndex"]
            t = out["perBrowser"][b]["table"]
            diff = [k for k in t if k in ot and t[k]["wasm"] != ot[k]]
            cross.setdefault("otherRound", {})[b] = {"compared": len([k for k in t if k in ot]), "differ": diff,
                                                      "wrapOffsetsSame": ocal[b]["s1Walk"]["wrapOffsets"] == cal[b]["s1Walk"]["wrapOffsets"]
                                                      and ocal[b]["m1Walk"]["wrapOffsets"] == cal[b]["m1Walk"]["wrapOffsets"]}
            P(f"## cross-check: {b} this round against {sys.argv[2]}: {cross['otherRound'][b]}")
            P("")
    out["cross"] = cross
    (rd / "analysis.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    (rd / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
