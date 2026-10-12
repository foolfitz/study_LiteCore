#!/usr/bin/env python3
"""Read the raw arms-r*.jsonl of tools/f129_native_point_click.cpp and tabulate.

Nothing here measures anything: it compares the strings the probe stored.
Usage: analyze_f129_point_click.py ROUND_DIR [OLD_ARMS_JSONL]
Writes ROUND_DIR/analysis.json and ROUND_DIR/summary.md.

`same` / `differs` compares the whole document text read back after the key and
the typed '#' (SelectAll repeated until stable), ref vs emu.  The landing is the
index of '#' in that text with a short excerpt (newline shown as a down-arrow
return sign, tab as a right-arrow).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

KEYS = ["Left", "Right", "Up", "Down", "Home", "End"]
ALL_SHAPES = ["p2-forward", "p2-backward", "s1", "s2", "s3", "s4", "s5", "s1e", "m1r", "m1e", "s1d", "m1d"]
MADE_UNKNOWN = {"s5", "s1e", "m1r", "m1e", "s1d", "m1d"}  # no expectation of the selection read-back (informational)
# Callback types that advance the engine's sourceSequence per src/probe_engine.cpp
# onLokCallback (INVALIDATE_TILES, INVALIDATE_VISIBLE_CURSOR, TEXT_SELECTION incl.
# the empty payload, TEXT_SELECTION_START/END, CURSOR_VISIBLE).  INFERRED from
# reading that source; the page's placeCaret treats a sourceSequence advance as
# the engine's acknowledgement.
PAGE_RELEVANT = {
    "LOK_CALLBACK_INVALIDATE_TILES",
    "LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR",
    "LOK_CALLBACK_TEXT_SELECTION",
    "LOK_CALLBACK_TEXT_SELECTION_START",
    "LOK_CALLBACK_TEXT_SELECTION_END",
    "LOK_CALLBACK_CURSOR_VISIBLE",
}
GRACE_MS = 400


def vis(s: str) -> str:
    return s.replace("\n", "⏎").replace("\t", "⇥")


def landing(text: str):
    n = text.count("#")
    i = text.find("#")
    if i < 0:
        return None
    lo, hi = max(0, i - 14), min(len(text), i + 15)
    return {"index": i, "hashCount": n, "excerpt": vis(text[lo:i]) + "<#>" + vis(text[i + 1:hi])}


def load(rd: Path):
    arms = []
    discover = []
    for f in sorted(rd.glob("arms-r*.jsonl")):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            r["_file"] = f.name
            (discover if r.get("arm", "").startswith("discover") else arms).append(r)
    return arms, discover


def main() -> int:
    rd = Path(sys.argv[1])
    old_path = Path(sys.argv[2]) if len(sys.argv) > 2 else rd.parent / "round-20261012T020528Z" / "arms.jsonl"
    arms, discover = load(rd)
    # Optional: other folders whose ref / emu arms are compared with this folder's
    # emuend arms (the dragend folder has no ref arms of its own).
    import os
    ref_dirs = [Path(x) for x in os.environ.get("F129_ANALYSIS_REF_DIRS", "").split(":") if x]
    ref_arms = []
    for rdir in ref_dirs:
        a2, _ = load(rdir)
        ref_arms += [dict(a, _from=rdir.name) for a in a2 if a.get("kind") in ("ref", "emu")]
    arms_this_folder = list(arms)
    SHAPES = [sh for sh in ALL_SHAPES if any(a.get("shape") == sh for a in arms)]
    out: dict = {"rounds": sorted({a["round"] for a in arms}), "armCount": len(arms), "shapes": SHAPES,
                "refDirs": [x.name for x in ref_dirs]}
    by = defaultdict(dict)  # (shape, key) -> kind -> round -> arm
    for a in arms + (ref_arms if any(x.get("kind") == "emuend" for x in arms) else []):
        if "fatal" in a:
            out.setdefault("fatal", []).append(a)
            continue
        by[(a["shape"], a["key"])].setdefault(a["kind"], {})[a["round"]] = a

    lines: list[str] = []
    P = lines.append

    # --- instrument checks -------------------------------------------------
    made_bad = [(a["arm"], a["round"], a["made"], a["madeExpected"]) for a in arms
                if "fatal" not in a and a["shape"] not in MADE_UNKNOWN and not a["madeOk"]]
    out["madeMismatches_excluding_s5"] = made_bad
    one_hash = [(a["arm"], a["round"], a["text"].count("#")) for a in arms
                if "fatal" not in a and a["text"].count("#") != 1]
    out["armsWhereHashCountIsNotOne"] = one_hash
    P("## Instrument checks")
    P(f"- arms read: {len(arms)} over rounds {out['rounds']}; fatal arms: {len(out.get('fatal', []))}")
    P(f"- arms whose selection read-back differs from the expectation (shapes {sorted(MADE_UNKNOWN)} excluded, their expectation is unknown): {len(made_bad)}")
    P(f"- arms where the final text does not contain exactly one '#': {len(one_hash)}")
    for name in sorted({d["arm"] for d in discover}):
        wraps = {d["round"]: d["wrapOffset"] for d in discover if d["arm"] == name}
        out.setdefault("wrapOffsets", {})[name] = wraps
        P(f"- wrap offset found by `{name}` per round: {wraps}")
    for d in discover:
        first = d["start"]
        last = d["steps"][-1]["cursor"] if d["steps"] else None
        prev = d["steps"][-2]["cursor"] if len(d["steps"]) > 1 else None
        P(f"  - {d['arm']} round {d['round']}: cursor at start `{first}`; after {d['steps'][-2]['after']} Rights `{prev}`; after {d['steps'][-1]['after']} Rights `{last}`")
        if d["line1Text"]:
            P(f"    line 1 ends with `...{d['line1Text'][-24:]}`")
    P("")

    # --- old arms reproduce the earlier round? ---------------------------------
    old = {}
    if old_path.exists():
        for line in old_path.read_text().splitlines():
            r = json.loads(line)
            old[r["arm"]] = r["text"]
    repro = []
    for key in KEYS:
        for shape, oldprefix in (("p2-forward", "forward"), ("p2-backward", "backward")):
            ref_arms = by[(shape, key)].get("ref", {}) if (shape, key) in by else {}
            for rnd, a in sorted(ref_arms.items()):
                repro.append({"arm": a["arm"], "round": rnd, "oldArm": f"{oldprefix}-{key}",
                              "sameTextAsOldRound": a["text"] == old.get(f"{oldprefix}-{key}")})
    out["oldArmReproduction"] = repro
    P("## The ref arms on the old fixture against `round-20261012T020528Z/arms.jsonl`")
    nsame = sum(1 for r in repro if r["sameTextAsOldRound"])
    P(f"- {nsame} of {len(repro)} (arm, round) pairs give exactly the old round's text ({len(repro) // max(1, len(out['rounds']))} arms x {len(out['rounds'])} rounds; none when this folder has no old-fixture arms)")
    for r in repro:
        if not r["sameTextAsOldRound"]:
            P(f"  - DIFFERS: {r['arm']} round {r['round']} vs old `{r['oldArm']}`")
    P("")

    # --- ref vs emu --------------------------------------------------------------
    table = {}
    P("## ref vs emu (whole-document text after the key and '#'; index = position of '#' in that text)")
    P("")
    for shape in SHAPES:
        P(f"### {shape}")
        has_end = any(by[(shape, k)].get("emuend") for k in KEYS)
        if has_end:
            P("| key | ref landing (index, excerpt) | emu landing | emu vs ref | emuend landing | emuend vs ref | cursor rect after key, ref / emu / emuend | rounds |")
            P("|---|---|---|---|---|---|---|---|")
        else:
            P("| key | ref landing (index, excerpt) | emu landing (index, excerpt) | verdict | cursor rect after key, ref / emu (x, y) | rounds |")
            P("|---|---|---|---|---|---|")
        for key in KEYS:
            refs = by[(shape, key)].get("ref", {})
            emus = by[(shape, key)].get("emu", {})
            rounds = sorted(set(refs) & set(emus))
            verdicts = {}
            lref = lemu = None
            if not rounds:
                P(f"| {key} | no data | no data | no data | | 0 |")
                table[f"{shape}/{key}"] = {"verdict": "no data"}
                continue
            for rnd in rounds:
                same = refs[rnd]["text"] == emus[rnd]["text"]
                verdicts[rnd] = "same" if same else "differs"
                lref = landing(refs[rnd]["text"])
                lemu = landing(emus[rnd]["text"])
            ref_texts = {refs[r]["text"] for r in rounds}
            emu_texts = {emus[r]["text"] for r in rounds}
            consistent = len(ref_texts) == 1 and len(emu_texts) == 1
            def xy(c):
                p = [q.strip() for q in c.split(",")]
                return f"{p[0]},{p[1]}" if len(p) >= 2 else c
            rc = sorted({xy(refs[r]["cursorAfter"]) for r in rounds})
            ec = sorted({xy(emus[r]["cursorAfter"]) for r in rounds})
            vset = set(verdicts.values())
            verdict = vset.pop() if len(vset) == 1 and consistent else ("UNSTABLE " + str(verdicts))
            table[f"{shape}/{key}"] = {"verdict": verdict, "roundVerdicts": verdicts,
                                       "refLanding": lref, "emuLanding": lemu,
                                       "refCursorAfter": rc, "emuCursorAfter": ec,
                                       "refStableAcrossRounds": len(ref_texts) == 1,
                                       "emuStableAcrossRounds": len(emu_texts) == 1,
                                       "refSelectedAfterKey": sorted({refs[r].get("selectedAfterKey") for r in rounds}),
                                       "emuSelectedAfterKey": sorted({emus[r].get("selectedAfterKey") for r in rounds})}
            fmt = lambda l: "-" if not l else f"{l['index']}, `{l['excerpt']}`"
            if has_end:
                ends = by[(shape, key)].get("emuend", {})
                er = sorted(set(refs) & set(ends))
                ev = {r: ("same" if refs[r]["text"] == ends[r]["text"] else "differs") for r in er}
                end_texts = {ends[r]["text"] for r in er}
                evs = set(ev.values())
                everdict = evs.pop() if len(evs) == 1 and len(end_texts) == 1 else "UNSTABLE " + str(ev)
                lend = landing(ends[er[0]]["text"]) if er else None
                ecur = sorted({xy(ends[r]["cursorAfter"]) for r in er})
                table[f"{shape}/{key}"]["emuendVerdict"] = everdict
                table[f"{shape}/{key}"]["emuendLanding"] = lend
                table[f"{shape}/{key}"]["emuendCursorAfter"] = ecur
                table[f"{shape}/{key}"]["emuendClick"] = sorted({(ends[r]["click"]["x"], ends[r]["click"]["y"]) for r in er})
                P(f"| {key} | {fmt(lref)} | {fmt(lemu)} | {verdict} | {fmt(lend)} | {everdict} | {'/'.join(rc)} / {'/'.join(ec)} / {'/'.join(ecur)} | {len(rounds)} |")
            else:
                P(f"| {key} | {fmt(lref)} | {fmt(lemu)} | {verdict} | {'/'.join(rc)} / {'/'.join(ec)} | {len(rounds)} |")
        P("")
    out["refVsEmu"] = table
    # bottom line
    P("## Bottom line, ref vs emu")
    P("| shape | same | differs | unstable |")
    P("|---|---|---|---|")
    agg = {}
    for shape in SHAPES:
        vs = [table[f"{shape}/{k}"].get("verdict", "no data") for k in KEYS]
        s = sum(1 for v in vs if v == "same")
        d = sum(1 for v in vs if v == "differs")
        u = sum(1 for v in vs if v.startswith("UNSTABLE"))
        if any("emuendVerdict" in table[f"{shape}/{k}"] for k in KEYS):
            ev = [table[f"{shape}/{k}"].get("emuendVerdict") for k in KEYS]
            P(f"| {shape} (emuend vs ref) | {sum(1 for v in ev if v == 'same')} | {sum(1 for v in ev if v == 'differs')} | {sum(1 for v in ev if v and v.startswith('UNSTABLE'))} |")
        agg[shape] = {"same": s, "differs": d, "unstable": u,
                      "differsKeys": [k for k in KEYS if table[f"{shape}/{k}"].get("verdict") == "differs"]}
        P(f"| {shape} | {s} | {d}{' (' + ', '.join(agg[shape]['differsKeys']) + ')' if d else ''} | {u} |")
    out["bottomLine"] = agg
    P("")

    # --- click-only --------------------------------------------------------------
    P("## click-only (where the collapse itself lands)")
    P("| shape | landing of '#' after the click alone | click (x, y) | cursor rect at click | selection after click |")
    P("|---|---|---|---|---|")
    co = {}
    for shape in SHAPES:
        rs = by[(shape, "")].get("click-only", {})
        for rnd, a in sorted(rs.items()):
            l = landing(a["text"])
            co[f"{shape}/r{rnd}"] = {"landing": l, "click": a["click"], "cursorAtClick": a["cursorAtClick"],
                                      "selectedAfterClick": a["selectedAfterClick"]}
        if rs:
            a = rs[sorted(rs)[0]]
            texts = {x["text"] for x in rs.values()}
            l = landing(a["text"])
            P(f"| {shape} | {l['index']}, `{l['excerpt']}`{'' if len(texts) == 1 else ' (UNSTABLE across rounds)'} | {a['click']['x']}, {a['click']['y']} | {a['cursorAtClick']} | `{vis(a['selectedAfterClick'])}` |")
    out["clickOnly"] = co
    # emu vs click-only: after the click alone, '#' lands at the click point; compare with where
    # ref-<key> and emu-<key> started from (informational)
    P("")

    # --- s5 (and s4) detail: the cell the click landed in ------------------------------
    P("## Table shapes: what the selection and the click looked like")
    P("| arm group | made (selection read-back) | TABLE_SELECTED / TEXT_SELECTION_START / END at the selection | StateTableCell seen after the click | click-only landing |")
    P("|---|---|---|---|---|")
    tdet = {}
    for shape in ("s4", "s5"):
        rs = [a for a in arms if "fatal" not in a and a["shape"] == shape]
        if not rs:
            continue
        a0 = sorted(rs, key=lambda a: (a["round"], a["arm"]))[0]
        cells = sorted({c["payload"] for a in rs if a["kind"] in ("emu", "click-only")
                        for c in a.get("callbacksAfterClick", []) if c["payload"].startswith(".uno:StateTableCell=")})
        co_arms = [a for a in rs if a["kind"] == "click-only"]
        lc = landing(co_arms[0]["text"]) if co_arms else None
        st = a0["selectionState"]
        P(f"| {shape} | `{vis(a0['made'])}` | table `{st.get('TABLE_SELECTED')}`; start `{st.get('TEXT_SELECTION_START')}`; end `{st.get('TEXT_SELECTION_END')}` | {cells} | {('%d, `%s`' % (lc['index'], lc['excerpt'])) if lc else '-'} |")
        tdet[shape] = {"made": a0["made"], "selectionState": st, "stateTableCellAfterClick": cells,
                       "clickOnlyLanding": lc}
    out["tableDetail"] = tdet
    P("")

    # --- callbacks after the click -------------------------------------------------
    P(f"## Callbacks after the click (times relative to the click; grace {GRACE_MS} ms)")
    P("| arm group | arms | any callback within 400 ms | page-relevant (inferred) within 400 ms | first any (ms, median) | first page-relevant (ms, median) |")
    P("|---|---|---|---|---|---|")
    cb_rows = []
    per_arm = []
    for a in arms:
        if "fatal" in a or a["kind"] not in ("emu", "click-only", "emuend"):
            continue
        if a not in arms_this_folder:
            continue
        cbs = a.get("callbacksAfterClick", [])
        anyc = [c for c in cbs if c["tMs"] <= GRACE_MS]
        rel = [c for c in cbs if c["tMs"] <= GRACE_MS and c["type"] in PAGE_RELEVANT]
        first_any = min((c["tMs"] for c in cbs), default=None)
        first_rel = min((c["tMs"] for c in cbs if c["type"] in PAGE_RELEVANT), default=None)
        per_arm.append({"arm": a["arm"], "round": a["round"], "shape": a["shape"],
                        "anyWithin400": bool(anyc), "pageRelevantWithin400": bool(rel),
                        "firstAnyMs": first_any, "firstPageRelevantMs": first_rel,
                        "types": sorted({c["type"].replace("LOK_CALLBACK_", "") for c in cbs}),
                        "selectedAfterClick": a["selectedAfterClick"]})
    out["clickCallbacksPerArm"] = per_arm
    import statistics
    for shape in SHAPES:
        rows = [r for r in per_arm if r["shape"] == shape]
        if not rows:
            continue
        na = sum(1 for r in rows if r["anyWithin400"])
        nr = sum(1 for r in rows if r["pageRelevantWithin400"])
        fa = [r["firstAnyMs"] for r in rows if r["firstAnyMs"] is not None]
        fr = [r["firstPageRelevantMs"] for r in rows if r["firstPageRelevantMs"] is not None]
        P(f"| {shape} | {len(rows)} | {na}/{len(rows)} | {nr}/{len(rows)} | {statistics.median(fa):.1f} | {statistics.median(fr) if fr else float('nan'):.1f} |")
        cb_rows.append({"shape": shape, "arms": len(rows), "anyWithin400": na, "pageRelevantWithin400": nr})
    tot = len(per_arm)
    P(f"| ALL | {tot} | {sum(1 for r in per_arm if r['anyWithin400'])}/{tot} | {sum(1 for r in per_arm if r['pageRelevantWithin400'])}/{tot} | | |")
    out["clickCallbacksSummary"] = cb_rows
    nodrop = [r["arm"] + f" r{r['round']}" for r in per_arm if r["selectedAfterClick"] != ""]
    P("")
    P(f"- arms where getTextSelection after the click is NOT empty (the selection survived the click): {len(nodrop)} {nodrop[:10]}")
    out["selectionSurvivedClick"] = nodrop
    # type profile within 400 ms for a typical arm per shape
    P("")
    P("Callback types seen after the click, per shape (union over arms, all times):")
    for shape in SHAPES:
        ts = sorted({t for r in per_arm if r["shape"] == shape for t in r["types"]})
        P(f"- {shape}: {', '.join(ts)}")
    P("")
    (rd / "analysis.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    (rd / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
