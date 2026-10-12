#!/usr/bin/env python3
"""Read the raw jsonl of tools/native_page_rectangles.cpp and print what it shows.

Nothing here measures anything: it parses the strings the probe stored and does
arithmetic on them.  Usage: analyze_native_page_rectangles.py ROUND_DIR
Writes ROUND_DIR/analysis.json and ROUND_DIR/analysis.txt.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

BORDER = 284  # DOCUMENTBORDER, twips (sw/source/uibase/uno/unotxdoc.cxx getDocumentSize adds 2 x this)


def parse_rects(raw: str):
    if not raw or raw == "<null>":
        return []
    out = []
    for item in raw.split("; "):
        parts = [int(p) for p in item.split(", ")]
        assert len(parts) == 4, item
        out.append(tuple(parts))
    return out


def page_status(callbacks, lo, hi):
    """Last `.uno:StatePageNumber=Page N of M` payload with lo <= tMs <= hi."""
    last = None
    for c in callbacks:
        if lo <= c["tMs"] <= hi and c["type"] == "LOK_CALLBACK_STATE_CHANGED":
            m = re.match(r"\.uno:StatePageNumber=Page (\d+) of (\d+)", c["payload"])
            if m:
                last = (int(m.group(1)), int(m.group(2)), c["tMs"])
    return last


def analyse(path: Path):
    recs = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    cbs = [r for r in recs if r["rec"] == "callback"]
    edits = {r["edit"]: r for r in recs if r["rec"] == "edit"}
    sources = {r["phase"]: r for r in recs if r["rec"] == "sources"}
    rects = [r for r in recs if r["rec"] == "rects"]
    timed = [r for r in rects if r["phase"] == "timed"]
    res = {"file": path.name}

    # --- raw string shape and parse -------------------------------------
    first = timed[0]["raw"]
    res["raw_separator_ok"] = bool(re.fullmatch(r"-?\d+(, -?\d+){3}(; -?\d+(, -?\d+){3})*", first))
    r0 = parse_rects(first)
    res["count_settled"] = len(r0)
    res["timed_all_identical"] = all(t["raw"] == first for t in timed)
    res["stability_after_2s_identical"] = next(r for r in rects if r["phase"] == "stability-after-2s")["raw"] == first
    xs, ys, ws, hs = zip(*r0)
    res["x_values"] = sorted(set(xs))
    res["w_values"] = sorted(set(ws))
    res["h_values"] = sorted(set(hs))
    gaps = [ys[i + 1] - (ys[i] + hs[i]) for i in range(len(r0) - 1)]
    res["vertical_gaps"] = sorted(set(gaps))
    res["y_strictly_increasing"] = all(ys[i + 1] > ys[i] for i in range(len(ys) - 1))
    res["first_rect"] = r0[0]
    res["last_rect"] = r0[-1]
    # --- sources ---------------------------------------------------------
    s = sources["settled"]
    res["getParts_settled"] = s["getParts"]
    res["getDocumentSize_settled_twips"] = [s["docWidthTwips"], s["docHeightTwips"]]
    res["docW_equals_pageW_plus_2_border"] = s["docWidthTwips"] == max(ws) + 2 * BORDER
    res["docH_minus_last_bottom"] = s["docHeightTwips"] - (ys[-1] + hs[-1])
    res["getParts_right_after_load"] = sources["right-after-load"]["getParts"]
    ps = page_status(cbs, 0, edits["A"]["tMs"])
    res["StatePageNumber_settle"] = ps
    res["count_equals_getParts_equals_statusM"] = (len(r0) == s["getParts"] == (ps[1] if ps else None))
    # --- cost ------------------------------------------------------------
    ms = [t["ms"] for t in timed]
    res["ms_first"] = ms[0]
    res["ms_other_nine"] = {"min": min(ms[1:]), "median": statistics.median(ms[1:]), "max": max(ms[1:])}
    res["ms_all_ten"] = ms
    res["ms_stability_call_after_2s"] = next(r for r in rects if r["phase"] == "stability-after-2s")["ms"]

    # --- Edit A -----------------------------------------------------------
    a1, a2 = edits["A"]["tMs"], edits["A2"]["tMs"]
    after_a = [r for r in rects if r["phase"] == "after-A"]
    ra = parse_rects(after_a[0]["raw"])
    res["A"] = {
        "count_before": len(r0),
        "count_after": [len(parse_rects(r["raw"])) for r in after_a],
        "getParts_after": sources["after-A"]["getParts"],
        "getDocumentSize_after_twips": [sources["after-A"]["docWidthTwips"], sources["after-A"]["docHeightTwips"]],
        "first_n_rects_unchanged": ra[: len(r0)] == r0,
        "new_rects": ra[len(r0):],
        "new_rect_gap_to_previous": (ra[len(r0)][1] - (ra[len(r0) - 1][1] + ra[len(r0) - 1][3])) if len(ra) > len(r0) else None,
        "StatePageNumber_after": page_status(cbs, a2, 1e12 if "B" not in edits else edits["B"]["tMs"]),
    }
    between_edit_and_dispatch = [c for c in cbs if a1 <= c["tMs"] < a2]
    after_dispatch = [c for c in cbs if a2 <= c["tMs"] < edits["B"]["tMs"]]
    res["A"]["callback_types_goto_to_dispatch"] = sorted({c["type"] for c in between_edit_and_dispatch})
    res["A"]["callback_types_dispatch_to_quiet"] = sorted({c["type"] for c in after_dispatch})
    sizes = [c for c in after_dispatch if c["type"] == "LOK_CALLBACK_DOCUMENT_SIZE_CHANGED"]
    res["A"]["DOCUMENT_SIZE_CHANGED"] = [{"tMs_after_dispatch": round(c["tMs"] - a2, 3), "payload": c["payload"]} for c in sizes]
    ps_after = [c for c in after_dispatch if c["type"] == "LOK_CALLBACK_STATE_CHANGED" and c["payload"].startswith(".uno:StatePageNumber=")]
    res["A"]["StatePageNumber_callbacks_after_dispatch"] = [{"tMs_after_dispatch": round(c["tMs"] - a2, 3), "payload": c["payload"]} for c in ps_after]
    res["A"]["INVALIDATE_TILES"] = [{"tMs_after_dispatch": round(c["tMs"] - a2, 3), "payload": c["payload"]} for c in after_dispatch if c["type"] == "LOK_CALLBACK_INVALIDATE_TILES"]

    # --- Edit B -----------------------------------------------------------
    b = edits["B"]["tMs"]
    after_b = [r for r in rects if r["phase"] == "after-B"]
    rb = [parse_rects(r["raw"]) for r in after_b]
    res["B"] = {
        "count_before": len(ra),
        "count_after": [len(x) for x in rb],
        "rects_identical_to_before": [x == ra for x in rb],
        "raw_identical_to_before": [r["raw"] == after_a[1]["raw"] for r in after_b],
        "getParts_after": sources["after-B"]["getParts"],
        "getDocumentSize_after_twips": [sources["after-B"]["docWidthTwips"], sources["after-B"]["docHeightTwips"]],
    }
    cbs_b = [c for c in cbs if c["tMs"] >= b]
    res["B"]["callback_types"] = sorted({c["type"] for c in cbs_b})
    res["B"]["DOCUMENT_SIZE_CHANGED_count"] = sum(1 for c in cbs_b if c["type"] == "LOK_CALLBACK_DOCUMENT_SIZE_CHANGED")
    res["B"]["INVALIDATE_TILES_count"] = sum(1 for c in cbs_b if c["type"] == "LOK_CALLBACK_INVALIDATE_TILES")
    res["B"]["typing_evidence_cursor_x_changed"] = [c["payload"] for c in cbs_b if c["type"] == "LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR"]
    res["B"]["word_count_callbacks"] = [c["payload"] for c in cbs_b if c["payload"].startswith(".uno:StateWordCount=")]
    return res


def main() -> int:
    rd = Path(sys.argv[1])
    out = {}
    for f in sorted(rd.glob("*-r*.jsonl")):
        out[f.name] = analyse(f)
    (rd / "analysis.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    lines = []
    for name, r in out.items():
        lines.append(f"== {name}")
        lines.append(f"  string shape ok: {r['raw_separator_ok']}; rects settled: {r['count_settled']}; getParts: {r['getParts_settled']} (right after load: {r['getParts_right_after_load']}); StatePageNumber: {r['StatePageNumber_settle']}")
        lines.append(f"  count == getParts == status M: {r['count_equals_getParts_equals_statusM']}")
        lines.append(f"  x values {r['x_values']}, w values {r['w_values']}, h values {r['h_values']}; vertical gaps {r['vertical_gaps']}; y strictly increasing {r['y_strictly_increasing']}")
        lines.append(f"  first {r['first_rect']} last {r['last_rect']}; getDocumentSize {r['getDocumentSize_settled_twips']}; docW == pageW + 2*284: {r['docW_equals_pageW_plus_2_border']}; docH - last bottom: {r['docH_minus_last_bottom']}")
        lines.append(f"  ten timed calls identical: {r['timed_all_identical']}; stability call identical: {r['stability_after_2s_identical']}")
        lines.append(f"  ms first {r['ms_first']:.4f}; other nine min/median/max {r['ms_other_nine']['min']:.4f}/{r['ms_other_nine']['median']:.4f}/{r['ms_other_nine']['max']:.4f}; stability call {r['ms_stability_call_after_2s']:.4f}")
        a = r["A"]
        lines.append(f"  A: count {a['count_before']} -> {a['count_after']}; getParts {a['getParts_after']}; docSize {a['getDocumentSize_after_twips']}; old rects unchanged {a['first_n_rects_unchanged']}; new {a['new_rects']} gap {a['new_rect_gap_to_previous']}")
        lines.append(f"     callbacks GoToEnd->dispatch: {[t.replace('LOK_CALLBACK_', '') for t in a['callback_types_goto_to_dispatch']]}")
        lines.append(f"     callbacks dispatch->quiet:   {[t.replace('LOK_CALLBACK_', '') for t in a['callback_types_dispatch_to_quiet']]}")
        lines.append(f"     DOCUMENT_SIZE_CHANGED: {a['DOCUMENT_SIZE_CHANGED']}; StatePageNumber after dispatch: {a['StatePageNumber_callbacks_after_dispatch']}; INVALIDATE_TILES: {a['INVALIDATE_TILES']}")
        b = r["B"]
        lines.append(f"  B: count {b['count_before']} -> {b['count_after']}; rects identical {b['rects_identical_to_before']}; getParts {b['getParts_after']}; docSize {b['getDocumentSize_after_twips']}")
        lines.append(f"     callbacks: {[t.replace('LOK_CALLBACK_', '') for t in b['callback_types']]}; DOCUMENT_SIZE_CHANGED {b['DOCUMENT_SIZE_CHANGED_count']}; INVALIDATE_TILES {b['INVALIDATE_TILES_count']}")
        lines.append(f"     typing evidence: cursor {b['typing_evidence_cursor_x_changed']}; word count {b['word_count_callbacks']}")
    (rd / "analysis.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
