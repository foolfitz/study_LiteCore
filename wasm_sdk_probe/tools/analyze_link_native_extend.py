#!/usr/bin/env python3
"""Read the raw arms-r*.jsonl of tools/link_native_extend_signatures.cpp and tabulate.

Nothing here measures anything: it compares what the probe stored.  Re-run in one line:

    python3 -I tools/analyze_link_native_extend.py RUN_DIR

Writes RUN_DIR/analysis.json and RUN_DIR/tables.md and prints the verdicts.
Exit status: 0 = analysed; 2 = no round files, a round with zero measured arms, or a
round that is missing arms another round has (override: --allow-partial for the
latter only); 3 = the probe reported a fatal line (document load, discovery).

Abbreviations: SEL=TEXT_SELECTION, CUR=INVALIDATE_VISIBLE_CURSOR,
SS=TEXT_SELECTION_START, SE=TEXT_SELECTION_END, TILES=INVALIDATE_TILES,
STATE=STATE_CHANGED.  "SEL0" is a TEXT_SELECTION whose payload is empty ("" or "EMPTY").
The "core" sequence is the SEL / CUR / SS / SE callbacks only (in arrival order);
the "all" sequence is every callback type.  INTERMITTENT = the type sequence differs
between rounds; it is reported for both sequences and never resolved by majority.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PREFIX = "LOK_CALLBACK_"
ABBR = {
    "TEXT_SELECTION": "SEL",
    "INVALIDATE_VISIBLE_CURSOR": "CUR",
    "TEXT_SELECTION_START": "SS",
    "TEXT_SELECTION_END": "SE",
    "INVALIDATE_TILES": "TILES",
    "STATE_CHANGED": "STATE",
}
CORE = {"SEL", "CUR", "SS", "SE"}
SHAPES = ["caret-mid", "range-fwd", "range-bwd", "range-one", "range-cross", "range-kbd", "doc-start",
          "doc-end", "empty-para", "wrap-line-end", "cjk-mid", "heading-mid", "list-mid", "cell-end"]
RANGE_SHAPES = ["range-fwd", "range-bwd", "range-cross", "range-kbd"]
KEYS = ["Left", "Right", "Up", "Down", "Home", "End"]
EMPTY_SEL = {"", "EMPTY"}
LATE_MS = 300.0


def short(t: str) -> str:
    t = t[len(PREFIX):] if t.startswith(PREFIX) else t
    return ABBR.get(t, t)


def load(run_dir: Path, allow_partial: bool):
    files = sorted(run_dir.glob("arms-r*.jsonl"))
    if not files:
        print(f"REFUSED: no arms-r*.jsonl in {run_dir}", file=sys.stderr)
        sys.exit(2)
    rounds = {}
    fatals = []
    discover = {}
    for f in files:
        measured, inter = {}, {}
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if "fatal" in r:
                fatals.append((f.name, r))
                continue
            arm = r.get("arm", "")
            if arm == "meta":
                continue
            if arm.startswith("discover"):
                discover.setdefault(f.name, []).append(r)
            elif r.get("kind") == "interaction":
                inter[arm] = r
            else:
                measured[arm] = r
        if not measured:
            print(f"REFUSED: {f.name} has zero measured arms", file=sys.stderr)
            sys.exit(2)
        rounds[f.name] = {"measured": measured, "inter": inter}
    if fatals:
        for name, r in fatals:
            print(f"FATAL line in {name}: {r}", file=sys.stderr)
        sys.exit(3)
    union = set()
    for r in rounds.values():
        union |= set(r["measured"]) | set(r["inter"])
    missing = {n: sorted(union - set(r["measured"]) - set(r["inter"])) for n, r in rounds.items()}
    if any(missing.values()) and not allow_partial:
        for n, m in missing.items():
            if m:
                print(f"REFUSED: {n} is missing {len(m)} arms (first: {m[:3]}); use --allow-partial", file=sys.stderr)
        sys.exit(2)
    return rounds, discover


def sel_label(cb: dict) -> str:
    s = short(cb["type"])
    if s == "SEL" and cb["payload"] in EMPTY_SEL:
        return "SEL0"
    return s


def digest(arm: dict) -> dict:
    cbs = arm["callbacks"]
    post = [c for c in cbs if c["tMs"] >= 0]
    pre = [c for c in cbs if c["tMs"] < 0]
    all_seq = [short(c["type"]) for c in post]
    core_cbs = [c for c in post if short(c["type"]) in CORE]
    core_seq = [short(c["type"]) for c in core_cbs]
    core_disp = [sel_label(c) for c in core_cbs]
    idx_sel = [i for i, s in enumerate(core_seq) if s == "SEL"]
    idx_cur = [i for i, s in enumerate(core_seq) if s == "CUR"]
    if idx_sel and idx_cur:
        order = "CUR-after-SEL" if idx_cur[-1] > idx_sel[-1] else "CUR-before-SEL"
    else:
        order = "n/a"
    before, after = arm["before"], arm["after"]
    shape = arm["shapeMake"]
    exp_cursor = shape["expectedCursorRect"]
    shape_ok = (before["getTextSelection"] == shape["expectedSelection"]
                and (not exp_cursor or before["INVALIDATE_VISIBLE_CURSOR"] == exp_cursor))
    home_end_ok = None
    if arm["shift"] and arm["key"] in ("Home", "End") and shape["haveExpectHomeEnd"]:
        want = shape["expectShiftHome"] if arm["key"] == "Home" else shape["expectShiftEnd"]
        home_end_ok = after["getTextSelection"] == want
    return {
        "arm": arm["arm"], "shape": arm["shape"], "key": arm["key"], "shift": arm["shift"], "kind": arm["kind"],
        "allSeq": all_seq, "coreSeq": core_seq, "coreDisp": core_disp,
        "nSel": core_seq.count("SEL"), "nSel0": core_disp.count("SEL0"), "nCur": core_seq.count("CUR"),
        "order": order,
        "lastAnyMs": max((c["tMs"] for c in post), default=None),
        "lastCoreMs": max((c["tMs"] for c in core_cbs), default=None),
        "coreAfter300": any(c["tMs"] > LATE_MS for c in core_cbs),
        "anyAfter300": any(c["tMs"] > LATE_MS for c in post),
        "preWindowCallbacks": [(short(c["type"]), c["tMs"]) for c in pre],
        "selBefore": before["getTextSelection"], "selAfter": after["getTextSelection"],
        "curBefore": before["INVALIDATE_VISIBLE_CURSOR"], "curAfter": after["INVALIDATE_VISIBLE_CURSOR"],
        "selChangedText": before["getTextSelection"] != after["getTextSelection"],
        "curChanged": before["INVALIDATE_VISIBLE_CURSOR"] != after["INVALIDATE_VISIBLE_CURSOR"],
        "selPayloads": [c["payload"] for c in core_cbs if short(c["type"]) == "SEL"],
        "postReturnMs": arm["postReturnMs"], "windowMs": arm["windowMs"],
        "shapeOk": shape_ok, "homeEndOk": home_end_ok, "shapeSettleMs": shape["settleMs"],
        "firstCbMs": min((c["tMs"] for c in post), default=None),
    }


def same(vals):
    return all(v == vals[0] for v in vals)


def fmt_vals(vals, f=str):
    return f(vals[0]) if same(vals) else "/".join(f(v) for v in vals)


def fmt_ms(v):
    return "-" if v is None else f"{v:.0f}"


def interaction_pass(r: dict):
    step = r["step"]
    got = r["afterStep"]["getTextSelection"]
    if step == "a":
        ok = (got == "" and r["afterStep"]["INVALIDATE_VISIBLE_CURSOR"] == r["expectedCursorRect"]
              and r["shiftHomeAfterClick"] == r["expectedShiftHomeAfterClick"])
    else:
        ok = got == r["expectedSelection"]
    return ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    allow_partial = "--allow-partial" in sys.argv
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    run_dir = Path(args[0])
    rounds, discover = load(run_dir, allow_partial)
    names = sorted(rounds)
    digests = {n: {a: digest(r) for a, r in rounds[n]["measured"].items()} for n in names}
    arms_all = sorted({a for n in names for a in digests[n]})

    def cell(arm):
        return [digests[n][arm] for n in names if arm in digests[n]]

    out = {"rounds": names, "cells": {}, "predictions": {}, "controls": {}, "interaction": {},
           "shapeChecks": {}, "discover": discover}

    # ---- per cell ------------------------------------------------------------
    for arm in arms_all:
        ds = cell(arm)
        d0 = ds[0]
        out["cells"][arm] = {
            "shape": d0["shape"], "key": d0["key"], "shift": d0["shift"], "kind": d0["kind"],
            "coreSeqPerRound": [" ".join(d["coreDisp"]) for d in ds],
            "allSeqPerRound": [" ".join(d["allSeq"]) for d in ds],
            "intermittentCore": not same([d["coreSeq"] for d in ds]),
            "intermittentAll": not same([d["allSeq"] for d in ds]),
            "payloadKindDiffers": same([d["coreSeq"] for d in ds]) and not same([d["coreDisp"] for d in ds]),
            "nSel": [d["nSel"] for d in ds], "nCur": [d["nCur"] for d in ds],
            "order": [d["order"] for d in ds],
            "lastAnyMs": [d["lastAnyMs"] for d in ds], "lastCoreMs": [d["lastCoreMs"] for d in ds],
            "coreAfter300": [d["coreAfter300"] for d in ds], "anyAfter300": [d["anyAfter300"] for d in ds],
            "selChangedText": [d["selChangedText"] for d in ds], "curChanged": [d["curChanged"] for d in ds],
            "selBefore": [d["selBefore"] for d in ds], "selAfter": [d["selAfter"] for d in ds],
            "selPayloads": [d["selPayloads"] for d in ds],
            "shapeOk": [d["shapeOk"] for d in ds], "homeEndOk": [d["homeEndOk"] for d in ds],
            "preWindowCallbacks": [d["preWindowCallbacks"] for d in ds],
            "firstCbMs": [d["firstCbMs"] for d in ds], "postReturnMs": [d["postReturnMs"] for d in ds],
        }

    keyed = [a for a in arms_all if out["cells"][a]["kind"] in ("shift", "plain")]
    shift_arms = [a for a in keyed if out["cells"][a]["shift"]]
    plain_arms = [a for a in keyed if not out["cells"][a]["shift"]]

    # ---- controls (window contamination) -------------------------------------
    for a in arms_all:
        if out["cells"][a]["kind"] != "control":
            continue
        ds = cell(a)
        out["controls"][a] = {
            "callbacksInWindowPerRound": [len(d["allSeq"]) for d in ds],
            "preWindowPerRound": [len(d["preWindowCallbacks"]) for d in ds],
            "shapeSettleMsPerRound": [d["shapeSettleMs"] for d in ds],
        }
    controls_empty = all(sum(c["callbacksInWindowPerRound"]) == 0 and sum(c["preWindowPerRound"]) == 0
                         for c in out["controls"].values()) and bool(out["controls"])

    # ---- shape checks ---------------------------------------------------------
    bad_shape = sorted({a for a in keyed + list(out["controls"]) if not all(out["cells"][a]["shapeOk"])})
    bad_he = sorted({a for a in keyed if any(v is False for v in out["cells"][a]["homeEndOk"])})
    cap_hit = sorted({a for a in arms_all for d in cell(a) if d["shapeSettleMs"] < 0})
    out["shapeChecks"] = {"shapeNotAsExpected": bad_shape, "homeEndSelectionNotAsExpected": bad_he,
                          "settleCapHit": cap_hit}

    # ---- predictions ----------------------------------------------------------
    pa_fail = [a for a in shift_arms
               if any(ch and n == 0 for ch, n in zip(out["cells"][a]["selChangedText"], out["cells"][a]["nSel"]))]
    pa_changed = [a for a in shift_arms if any(out["cells"][a]["selChangedText"])]
    pa_cur_only = [a for a in shift_arms if not any(out["cells"][a]["selChangedText"]) and any(out["cells"][a]["curChanged"])]
    out["predictions"]["P-a"] = {
        "claim": "every Shift+key that changes the selection emits >= 1 TEXT_SELECTION",
        "held": not pa_fail, "failingCells": pa_fail, "cellsWhereSelectionTextChanged": len(pa_changed),
        "cellsCursorChangedButSelectionTextSame": pa_cur_only}

    edge = {"shift-Left@doc-start": "Shift+Left at doc-start", "shift-Right@doc-end": "Shift+Right at doc-end",
            "shift-Up@doc-start": "Shift+Up on the first line", "shift-Down@doc-end": "Shift+Down on the last line"}
    extra_edge = ["shift-Home@doc-start", "shift-End@doc-end"]
    pb = {}
    for a in list(edge) + extra_edge:
        if a not in out["cells"]:
            continue
        c = out["cells"][a]
        pb[a] = {"coreSeqPerRound": c["coreSeqPerRound"], "allSeqPerRound": c["allSeqPerRound"],
                 "selChangedText": c["selChangedText"], "curChanged": c["curChanged"]}
    pb_core = all(not out["cells"][a]["coreSeqPerRound"][i] for a in edge if a in out["cells"]
                  for i in range(len(names)))
    pb_strict = all(not out["cells"][a]["allSeqPerRound"][i] for a in edge if a in out["cells"]
                    for i in range(len(names)))
    out["predictions"]["P-b"] = {
        "claim": "Shift+Left at doc-start, Shift+Right at doc-end, Shift+Up on the first line, Shift+Down on the last line emit nothing",
        "heldNoSelCurSsSe": pb_core, "heldNoCallbackOfAnyType": pb_strict, "cells": pb}

    pc_arm = "shift-Left@range-one"
    pc = {}
    if pc_arm in out["cells"]:
        c = out["cells"][pc_arm]
        pc = {"coreSeqPerRound": c["coreSeqPerRound"], "selPayloadsPerRound": c["selPayloads"],
              "selBefore": c["selBefore"], "selAfter": c["selAfter"]}
        held = all(p and p[-1] in EMPTY_SEL for p in c["selPayloads"])
    else:
        held = False
    out["predictions"]["P-c"] = {"claim": "Shift+Left on range-one emits TEXT_SELECTION with an EMPTY payload",
                                 "held": held, "cell": pc}

    # ---- interaction ----------------------------------------------------------
    inter_names = sorted({a for n in names for a in rounds[n]["inter"]})
    inter_fail = []
    for a in inter_names:
        rows = []
        for n in names:
            r = rounds[n]["inter"].get(a)
            if not r:
                continue
            ok = interaction_pass(r)
            rows.append({"round": n, "pass": ok, "afterFirstSelection": r["afterFirstKey"]["getTextSelection"],
                         "afterStepSelection": r["afterStep"]["getTextSelection"],
                         "afterStepCursor": r["afterStep"]["INVALIDATE_VISIBLE_CURSOR"],
                         "expectedSelection": r["expectedSelection"], "expectedCursorRect": r["expectedCursorRect"],
                         "shiftHomeAfterClick": r["shiftHomeAfterClick"],
                         "coreSeqStep": [short(c["type"]) for c in r["callbacksStep"] if short(c["type"]) in CORE],
                         "firstKeyCoreSeq": [short(c["type"]) for c in r["callbacksFirstKey"]
                                             if c["tMs"] >= 0 and short(c["type"]) in CORE]})
            if not ok:
                inter_fail.append((a, n))
        out["interaction"][a] = rows
    out["predictions"]["P-d"] = {"claim": "interaction arms (a)-(c) all pass", "held": not inter_fail and bool(inter_names),
                                 "failing": inter_fail, "armsPerRound": len(inter_names)}

    # ---- order / count / empty / intermittent --------------------------------
    def rounds_where(a, pred):
        c = out["cells"][a]
        return [i + 1 for i, v in enumerate(zip(*[c[k] for k in ("order", "nSel", "nCur", "coreSeqPerRound")])) if pred(*v)]

    order_late = {a: rounds_where(a, lambda o, ns, nc, s: o == "CUR-after-SEL") for a in keyed}
    order_late = {a: r for a, r in order_late.items() if r}
    order_early = {a: rounds_where(a, lambda o, ns, nc, s: o == "CUR-before-SEL") for a in keyed}
    order_early = {a: r for a, r in order_early.items() if r}
    multi_sel = {a: rounds_where(a, lambda o, ns, nc, s: ns > 1) for a in keyed}
    multi_sel = {a: r for a, r in multi_sel.items() if r}
    multi_cur = {a: rounds_where(a, lambda o, ns, nc, s: nc > 1) for a in keyed}
    multi_cur = {a: r for a, r in multi_cur.items() if r}
    no_sel = {a: rounds_where(a, lambda o, ns, nc, s: ns == 0) for a in keyed}
    no_sel = {a: r for a, r in no_sel.items() if r}
    nothing_core = {a: rounds_where(a, lambda o, ns, nc, s: not s) for a in keyed}
    nothing_core = {a: r for a, r in nothing_core.items() if r}
    nothing_any = {a: [i + 1 for i, s in enumerate(out["cells"][a]["allSeqPerRound"]) if not s] for a in keyed}
    nothing_any = {a: r for a, r in nothing_any.items() if r}
    inter_core = sorted(a for a in arms_all if out["cells"][a]["intermittentCore"])
    inter_all_only = sorted(a for a in arms_all if out["cells"][a]["intermittentAll"] and not out["cells"][a]["intermittentCore"])
    payload_kind = sorted(a for a in arms_all if out["cells"][a]["payloadKindDiffers"])
    late_core = {a: [i + 1 for i, v in enumerate(out["cells"][a]["coreAfter300"]) if v] for a in keyed}
    late_core = {a: r for a, r in late_core.items() if r}
    out["findings"] = {"lastCurAfterLastSel": order_late, "lastCurBeforeLastSel": order_early,
                       "moreThanOneSel": multi_sel, "moreThanOneCur": multi_cur, "noSelAtAll": no_sel,
                       "noCoreCallbackAtAll": nothing_core, "noCallbackOfAnyType": nothing_any,
                       "intermittentCore": inter_core, "intermittentAllTypesOnly": inter_all_only,
                       "payloadKindDiffersOnly": payload_kind, "coreCallbackAfter300ms": late_core,
                       "controlsEmpty": controls_empty}

    (run_dir / "analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- tables.md ------------------------------------------------------------
    L = []
    L.append(f"Rounds: {len(names)} ({', '.join(names)}).  Window: 1500 ms after the key's KEYINPUT post.")
    L.append("Abbreviations: SEL=TEXT_SELECTION (SEL0 = empty payload), CUR=INVALIDATE_VISIBLE_CURSOR, "
             "SS/SE=TEXT_SELECTION_START/END, STATE=STATE_CHANGED, TILES=INVALIDATE_TILES.")
    L.append("`seq` = SEL/CUR/SS/SE callbacks in arrival order; `others` = counts of the other types in the window.")
    L.append("`order` = whether the LAST CUR comes after the LAST SEL.  `last ms` = last SEL/CUR/SS/SE callback / last callback of any type.")
    L.append("Per-round values are joined with `/` when they differ.\n")

    def row_for(a):
        c = out["cells"][a]
        ds = cell(a)
        if c["intermittentCore"]:
            seq = "**INTERMITTENT** " + " ; ".join(f"r{i+1}: {s or '-'}" for i, s in enumerate(c["coreSeqPerRound"]))
        else:
            seq = c["coreSeqPerRound"][0] or "-"
            if c["payloadKindDiffers"]:
                seq = "**PAYLOAD-KIND DIFFERS** " + " ; ".join(f"r{i+1}: {s or '-'}" for i, s in enumerate(c["coreSeqPerRound"]))
        others = {}
        for d in ds[:1]:
            for t in d["allSeq"]:
                if t not in CORE:
                    others[t] = others.get(t, 0) + 1
        oth = ",".join(f"{k}x{v}" for k, v in sorted(others.items())) or "-"
        if c["intermittentAll"] and not c["intermittentCore"]:
            oth += " (all-types sequence differs between rounds)"
        chg = "text" if any(c["selChangedText"]) else ("cursor-only" if any(c["curChanged"]) else "none")
        return (f"| {c['shape']} | {c['key']} | `{seq}` | {fmt_vals(c['nSel'])} | {fmt_vals(c['nCur'])} | "
                f"{fmt_vals(c['order'])} | {fmt_vals([fmt_ms(v) for v in c['lastCoreMs']])} / "
                f"{fmt_vals([fmt_ms(v) for v in c['lastAnyMs']])} | {chg} | {oth} |")

    hdr = ("| shape | key | seq | #SEL | #CUR | order | last ms (core / any) | selection changed | others |\n"
           "|---|---|---|---|---|---|---|---|---|")
    L.append("## Table 1. Shift+key on every shape\n")
    L.append(hdr)
    for s in SHAPES:
        for k in KEYS:
            a = f"shift-{k}@{s}"
            if a in out["cells"]:
                L.append(row_for(a))
    L.append("\n## Table 2. Plain key on a range (item 3)\n")
    L.append(hdr)
    for s in RANGE_SHAPES:
        for k in KEYS:
            a = f"plain-{k}@{s}"
            if a in out["cells"]:
                L.append(row_for(a))

    L.append("\n## Table 3. Window control (no key)\n")
    L.append("| arm | callbacks in the 1500 ms window per round | callbacks in the 500 ms before the post | shape settle ms per round |\n|---|---|---|---|")
    for a, c in sorted(out["controls"].items()):
        L.append(f"| {a} | {c['callbacksInWindowPerRound']} | {c['preWindowPerRound']} | {[round(v) for v in c['shapeSettleMsPerRound']]} |")

    L.append("\n## Table 4. Interaction arms (question 7)\n")
    L.append("| arm | round | pass | selection after the first key | selection after the step | cursor after the step | expected |\n|---|---|---|---|---|---|---|")
    for a in inter_names:
        for i, row in enumerate(out["interaction"][a]):
            exp = repr(row["expectedSelection"]) + (f", cursor {row['expectedCursorRect']}, Shift+Home text {row['shiftHomeAfterClick']!r}" if a.endswith("-a") else "")
            L.append(f"| {a} | r{i+1} | {'PASS' if row['pass'] else '**FAIL**'} | {row['afterFirstSelection']!r} | "
                     f"{row['afterStepSelection']!r} | {row['afterStepCursor']} | {exp} |")

    L.append("\n## Table 5. Findings lists (cells; `rN` = rounds in which it held)\n")

    def lst(title, d):
        L.append(f"- **{title}** ({len(d)}): " + ("; ".join(f"{a} [r{','.join(map(str, r))}]" for a, r in sorted(d.items())) or "none"))

    lst("last CUR comes AFTER the last SEL", order_late)
    lst("last CUR comes BEFORE the last SEL", order_early)
    lst("more than one SEL", multi_sel)
    lst("more than one CUR", multi_cur)
    lst("no SEL at all", no_sel)
    lst("no SEL/CUR/SS/SE at all", nothing_core)
    lst("no callback of any type", nothing_any)
    lst("a SEL/CUR/SS/SE callback later than 300 ms", late_core)
    L.append(f"- **INTERMITTENT (core sequence differs between rounds)** ({len(inter_core)}): "
             + ("; ".join(inter_core) or "none"))
    L.append(f"- **all-types sequence differs between rounds, core sequence identical** ({len(inter_all_only)}): "
             + ("; ".join(inter_all_only) or "none"))
    L.append(f"- **SEL payload kind (empty vs not) differs between rounds, type sequence identical** ({len(payload_kind)}): "
             + ("; ".join(payload_kind) or "none"))
    L.append(f"- shape not as expected before the key: {bad_shape or 'none'}; Shift+Home/End selection not as expected: {bad_he or 'none'}; "
             f"settle cap hit: {cap_hit or 'none'}")

    L.append("\n## Table 6. Prediction verdicts\n")
    pa = out["predictions"]["P-a"]
    L.append(f"- P-a: {'HELD' if pa['held'] else 'FAILED'}; selection text changed in {pa['cellsWhereSelectionTextChanged']} of {len(shift_arms)} Shift cells; "
             f"failing: {pa['failingCells'] or 'none'}; cursor changed but selection text same: {pa['cellsCursorChangedButSelectionTextSame'] or 'none'}")
    pbv = out["predictions"]["P-b"]
    L.append(f"- P-b: no SEL/CUR/SS/SE in the four edge cells: {'HELD' if pbv['heldNoSelCurSsSe'] else 'FAILED'}; "
             f"no callback of any type: {'HELD' if pbv['heldNoCallbackOfAnyType'] else 'FAILED'}")
    for a, c in pbv["cells"].items():
        L.append(f"  - {a}: core {c['coreSeqPerRound']}, all {c['allSeqPerRound']}, selection text changed {c['selChangedText']}, cursor changed {c['curChanged']}")
    pcv = out["predictions"]["P-c"]
    L.append(f"- P-c: {'HELD' if pcv['held'] else 'FAILED'}; cell {pc_arm}: {pcv['cell']}")
    pdv = out["predictions"]["P-d"]
    L.append(f"- P-d: {'HELD' if pdv['held'] else 'FAILED'}; interaction arms per round {pdv['armsPerRound']}; failing: {pdv['failing'] or 'none'}")
    (run_dir / "tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---- stdout ----------------------------------------------------------------
    print(f"rounds={len(names)} cells={len(arms_all)} controlsEmpty={controls_empty}")
    print("P-a", "HELD" if pa["held"] else f"FAILED {pa['failingCells']}")
    print("P-b", "HELD(no SEL/CUR/SS/SE)" if pbv["heldNoSelCurSsSe"] else "FAILED", "| any-type:", "HELD" if pbv["heldNoCallbackOfAnyType"] else "FAILED")
    print("P-c", "HELD" if pcv["held"] else "FAILED", pcv["cell"].get("selPayloadsPerRound"))
    print("P-d", "HELD" if pdv["held"] else f"FAILED {pdv['failing']}")
    print("intermittent(core):", inter_core)
    print("intermittent(all-only):", inter_all_only)
    print("wrote", run_dir / "analysis.json", run_dir / "tables.md")


if __name__ == "__main__":
    main()
