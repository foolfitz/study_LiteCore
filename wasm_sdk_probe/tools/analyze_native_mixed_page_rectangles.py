#!/usr/bin/env python3
"""Read the raw jsonl of tools/native_page_rectangles.cpp run on the mixed-page fixture.

Nothing here measures anything: it parses the strings the probe stored and does
arithmetic on them, against the page table of tools/create_mixed_page_document.py
(imported, so the expected sizes are the generator's own and cannot drift from it).

Predictions judged (fixed before the first run; see
findings/evidence/link-batch/page-rectangles/README.md, "Mixed-page round"):

  P-M1  8 rectangles, getParts() = 8
  P-M2  each rectangle's w x h equals its page style's size in twips
        (1 cm = 566.93 twips) within 1 %; pages 2, 3, 7 are wider than tall
  P-M3  y strictly increases in string order, with a gap between consecutive pages
  P-M4  (open) how x relates across pages of different widths: described, not judged

Usage:
  analyze_native_mixed_page_rectangles.py ROUND_DIR      writes analysis.json + analysis.txt
  analyze_native_mixed_page_rectangles.py --self-test    synthetic green, and each mutation red
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path

TWIPS_PER_CM = 566.93        # the brief's figure (1440 / 2.54 = 566.929...)
TOLERANCE = 0.01             # 1 %
BORDER = 284                 # DOCUMENTBORDER, twips (see page-rectangles/README.md)
SHAPE = re.compile(r"-?\d+(, -?\d+){3}(; -?\d+(, -?\d+){3})*")


def load_generator():
    path = Path(__file__).with_name("create_mixed_page_document.py")
    spec = importlib.util.spec_from_file_location("create_mixed_page_document", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_pages():
    gen = load_generator()
    out = []
    for n, master, width, height, _orientation in gen.PAGES:
        out.append({"page": n, "style": gen.PAGE_NAMES[n],
                    "w_cm": float(width[:-2]), "h_cm": float(height[:-2])})
    return out


def parse_rects(raw: str):
    if not raw or raw == "<null>":
        return []
    out = []
    for item in raw.split("; "):
        parts = [int(p) for p in item.split(", ")]
        if len(parts) != 4:
            raise ValueError(f"not four numbers: {item!r}")
        out.append(tuple(parts))
    return out


def analyse_run(path: Path, pages):
    recs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    sources = {r["phase"]: r for r in recs if r["rec"] == "sources"}
    rects = [r for r in recs if r["rec"] == "rects"]
    timed = [r for r in rects if r["phase"] == "timed"]
    res: dict = {"file": path.name}
    res["has_end_record"] = any(r["rec"] == "end" for r in recs)
    first = timed[0]["raw"]
    res["settled_raw"] = first
    res["raw_shape_ok"] = bool(SHAPE.fullmatch(first))
    res["timed_all_identical"] = all(t["raw"] == first for t in timed)
    res["stability_after_2s_identical"] = next(
        r for r in rects if r["phase"] == "stability-after-2s")["raw"] == first
    rs = parse_rects(first)
    res["rects"] = [list(r) for r in rs]
    res["count"] = len(rs)
    res["getParts_right_after_load"] = sources["right-after-load"]["getParts"]
    res["getParts_settled"] = sources["settled"]["getParts"]
    res["docSize_settled_twips"] = [sources["settled"]["docWidthTwips"],
                                    sources["settled"]["docHeightTwips"]]

    # P-M1
    res["P-M1"] = (len(rs) == len(pages) == res["getParts_settled"] == res["getParts_right_after_load"])

    # P-M2 (page i of the fixture <-> rectangle i in string order)
    per_page = []
    ok2 = len(rs) == len(pages)
    for i, page in enumerate(pages):
        if i >= len(rs):
            ok2 = False
            break
        x, y, w, h = rs[i]
        ew, eh = page["w_cm"] * TWIPS_PER_CM, page["h_cm"] * TWIPS_PER_CM
        w_err, h_err = (w - ew) / ew, (h - eh) / eh
        wide = w > h
        want_wide = page["w_cm"] > page["h_cm"]
        row_ok = abs(w_err) <= TOLERANCE and abs(h_err) <= TOLERANCE and wide == want_wide
        ok2 = ok2 and row_ok
        per_page.append({"page": page["page"], "style": page["style"], "x": x, "y": y, "w": w, "h": h,
                         "expected_w": round(ew, 1), "expected_h": round(eh, 1),
                         "w_err_pct": round(100 * w_err, 3), "h_err_pct": round(100 * h_err, 3),
                         "wider_than_tall": wide, "expected_wider_than_tall": want_wide, "ok": row_ok})
    res["per_page"] = per_page
    res["P-M2"] = ok2

    # P-M3
    ys = [r[1] for r in rs]
    hs = [r[3] for r in rs]
    res["y_strictly_increasing"] = all(ys[i + 1] > ys[i] for i in range(len(ys) - 1))
    gaps = [ys[i + 1] - (ys[i] + hs[i]) for i in range(len(rs) - 1)]
    res["vertical_gaps"] = gaps
    res["P-M3"] = res["y_strictly_increasing"] and all(g > 0 for g in gaps) and len(rs) > 1

    # P-M4 (described only)
    xs = [r[0] for r in rs]
    ws = [r[2] for r in rs]
    centres2 = [2 * x + w for x, w in zip(xs, ws)]   # twice the centre, integer
    rights = [x + w for x, w in zip(xs, ws)]
    res["x_values"] = xs
    res["x_left_aligned"] = len(set(xs)) == 1
    res["x_centred_on_common_axis"] = (max(centres2) - min(centres2)) <= 2
    res["x_right_aligned"] = len(set(rights)) == 1
    res["twice_centre_values"] = centres2

    # document size against the rectangles (descriptive)
    dw, dh = res["docSize_settled_twips"]
    res["docW_minus_widest"] = dw - max(ws) if ws else None
    res["docH_minus_last_bottom"] = dh - (ys[-1] + hs[-1]) if rs else None
    res["min_x"] = min(xs) if xs else None

    # after the probe's edits (A appends a page break at the end; B types a character)
    for phase in ("after-A", "after-B"):
        reads = [r["raw"] for r in rects if r["phase"] == phase]
        src = sources.get(phase)
        res[phase] = {"raw_reads": reads, "getParts": src["getParts"] if src else None,
                      "count": len(parse_rects(reads[0])) if reads else None,
                      "first_n_unchanged": bool(reads) and reads[0].startswith(first),
                      "identical_to_settled": bool(reads) and reads[0] == first,
                      "second_read_identical": len(reads) > 1 and reads[0] == reads[1]}
        if reads:
            extra = parse_rects(reads[0])[len(rs):]
            res[phase]["extra_rects"] = [list(e) for e in extra]
    status = None
    for r in recs:
        if (r["rec"] == "callback" and r["type"] == "LOK_CALLBACK_STATE_CHANGED"
                and r["phase"] == "settle"):
            m = re.match(r"\.uno:StatePageNumber=(Page \d+ of \d+)", r["payload"])
            if m:
                status = m.group(1)
    res["StatePageNumber_settle"] = status
    ms = [t["ms"] for t in timed]
    res["ms_first"] = ms[0]
    res["ms_others_max"] = max(ms[1:])
    return res


def analyse_round(round_dir: Path):
    pages = expected_pages()
    files = sorted(round_dir.glob("mixed-r*.jsonl"))
    runs = [analyse_run(f, pages) for f in files]
    summary = {"runs": [r["file"] for r in runs], "n_runs": len(runs)}
    for key in ("P-M1", "P-M2", "P-M3"):
        summary[key] = bool(runs) and all(r[key] for r in runs)
    summary["settled_strings_identical_across_runs"] = len({r["settled_raw"] for r in runs}) == 1
    summary["all_runs_have_end_record"] = all(r["has_end_record"] for r in runs)
    summary["exit_codes"] = [(p.name, p.read_text().strip()) for p in sorted(round_dir.glob("mixed-r*.exit"))]
    summary["P-M4"] = {
        "x_left_aligned_all_runs": all(r["x_left_aligned"] for r in runs),
        "x_centred_on_common_axis_all_runs": all(r["x_centred_on_common_axis"] for r in runs),
        "x_right_aligned_all_runs": all(r["x_right_aligned"] for r in runs),
        "x_values_first_run": runs[0]["x_values"] if runs else None,
    }
    return {"summary": summary, "runs": runs}


def render_text(analysis) -> str:
    s = analysis["summary"]
    out = []
    out.append(f"runs: {s['n_runs']}  exit codes: {s['exit_codes']}")
    out.append(f"settled rectangle strings identical across runs: {s['settled_strings_identical_across_runs']}")
    for key in ("P-M1", "P-M2", "P-M3"):
        out.append(f"{key}: {'HELD' if s[key] else 'FAILED'}")
    out.append(f"P-M4 (described): {json.dumps(s['P-M4'])}")
    for r in analysis["runs"]:
        out.append("")
        out.append(f"== {r['file']} ==")
        out.append(f"settled: {r['settled_raw']}")
        out.append(f"count {r['count']}  getParts right-after-load {r['getParts_right_after_load']}  "
                   f"settled {r['getParts_settled']}  docSize {r['docSize_settled_twips']}  "
                   f"StatePageNumber {r['StatePageNumber_settle']}")
        out.append(f"timed calls identical: {r['timed_all_identical']}  after 2 s identical: {r['stability_after_2s_identical']}  "
                   f"first call {r['ms_first']:.4f} ms, other nine max {r['ms_others_max']:.4f} ms")
        out.append("page style               x      y      w      h    exp_w   exp_h  w_err%  h_err%  wide  ok")
        for p in r["per_page"]:
            out.append(f"{p['page']}  {p['style']:<19} {p['x']:>5} {p['y']:>7} {p['w']:>6} {p['h']:>6} "
                       f"{p['expected_w']:>8} {p['expected_h']:>7} {p['w_err_pct']:>7} {p['h_err_pct']:>7}  "
                       f"{str(p['wider_than_tall']):<5} {p['ok']}")
        out.append(f"vertical gaps {r['vertical_gaps']}  y strictly increasing {r['y_strictly_increasing']}")
        out.append(f"x: {r['x_values']}  left-aligned {r['x_left_aligned']}  "
                   f"centred-on-axis {r['x_centred_on_common_axis']} (2x+w = {r['twice_centre_values']})  "
                   f"right-aligned {r['x_right_aligned']}")
        out.append(f"docW - widest page {r['docW_minus_widest']}  docH - last bottom {r['docH_minus_last_bottom']}")
        for phase in ("after-A", "after-B"):
            a = r[phase]
            out.append(f"{phase}: count {a['count']} getParts {a['getParts']} first-8-unchanged {a['first_n_unchanged']} "
                       f"identical-to-settled {a['identical_to_settled']} extra {a.get('extra_rects')}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Self-test: a synthetic probe output that satisfies every prediction must be
# judged green, and each mutation must turn the verdict it targets red.
# ---------------------------------------------------------------------------

def synthetic_run(mutation: str | None = None):
    pages = expected_pages()
    rects = []
    y = BORDER
    for page in pages:
        w, h = round(page["w_cm"] * TWIPS_PER_CM), round(page["h_cm"] * TWIPS_PER_CM)
        rects.append([BORDER, y, w, h])
        y += h + BORDER
    parts = len(pages)
    if mutation == "drop-last-rect":
        rects = rects[:-1]
    if mutation == "page4-is-a4":
        rects[3][2] = round(21 * TWIPS_PER_CM)
    if mutation == "page2-portrait":
        rects[1][2], rects[1][3] = rects[1][3], rects[1][2]
    if mutation == "page5-overlaps-page4":
        rects[4][1] = rects[3][1] + 10
    if mutation == "getParts-7":
        parts = 7
    raw = "; ".join(", ".join(str(v) for v in r) for r in rects)
    recs = [{"rec": "start"},
            {"rec": "sources", "phase": "right-after-load", "getParts": parts, "docWidthTwips": 0, "docHeightTwips": 0},
            {"rec": "sources", "phase": "settled", "getParts": parts, "docWidthTwips": 1, "docHeightTwips": 1}]
    for i in range(10):
        recs.append({"rec": "rects", "phase": "timed", "index": i, "ms": 0.01, "raw": raw})
    recs.append({"rec": "rects", "phase": "stability-after-2s", "index": 0, "ms": 0.01, "raw": raw})
    for phase in ("after-A", "after-B"):
        recs.append({"rec": "sources", "phase": phase, "getParts": parts, "docWidthTwips": 1, "docHeightTwips": 1})
        for i in range(2):
            recs.append({"rec": "rects", "phase": phase, "index": i, "ms": 0.01, "raw": raw})
    recs.append({"rec": "end"})
    return "\n".join(json.dumps(r) for r in recs) + "\n"


def self_test() -> int:
    failures = 0
    cases = [(None, {"P-M1": True, "P-M2": True, "P-M3": True}),
             ("drop-last-rect", {"P-M1": False}),
             ("page4-is-a4", {"P-M2": False}),
             ("page2-portrait", {"P-M2": False}),
             ("page5-overlaps-page4", {"P-M3": False}),
             ("getParts-7", {"P-M1": False})]
    for mutation, want in cases:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "mixed-r1.jsonl").write_text(synthetic_run(mutation))
            got = analyse_round(d)["summary"]
        ok = all(got[k] == v for k, v in want.items())
        print(f"  {'ok  ' if ok else 'FAIL'}  {mutation or 'unmutated synthetic run'}: "
              + ", ".join(f"{k} {'HELD' if got[k] else 'FAILED'}" for k in ("P-M1", "P-M2", "P-M3")))
        failures += 0 if ok else 1
    print(f"\nself-test: {len(cases) - failures}/{len(cases)} cases judged as expected")
    return 1 if failures else 0


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        return self_test()
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    round_dir = Path(sys.argv[1])
    analysis = analyse_round(round_dir)
    (round_dir / "analysis.json").write_text(json.dumps(analysis, indent=1) + "\n")
    text = render_text(analysis)
    (round_dir / "analysis.txt").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
