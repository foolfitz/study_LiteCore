#!/usr/bin/env python3
"""Judge finding 093 step 1's native calibration against the registered criteria.

The criteria are NOT in this file's judgement -- they are in
`findings/evidence/093/step1-native-geometry/ACCEPTANCE.md`, commit `bcb7caf4`,
written before either half of the probe existed.  This file implements them and
nothing else.  It reads a capture; it never runs anything, so the run and the
criteria stay separable and either can be re-run against the other's output.

Three answers and two red cases:

  Q1  the unit `XAccessibleComponent::getBounds()` returns
  Q2  the origin it is relative to
  Q3  whether the twips conversion lines up with LOK's caret rectangle

  R-1 shifted pairing -- every row re-judged against a far-away paragraph's
      caret; every one of those MUST fail, or the agreement in Q3 is structural
  R-2 non-constancy -- the converted tops must differ between rows

Usage:
  analyze_f093_native_geometry.py RUN_DIR
  analyze_f093_native_geometry.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# --- the registered constants.  Changing one of these is moving the criteria. -
T_CONTAIN_LINES = 0.5   # C1: half a line of slack at each edge
T_ALIGN_LINES = 2.0     # C2: two lines of top-alignment slack
MIN_ROWS = 8            # the probed set must be at least this big
SHIFT = 10              # R-1: pair row i with row i+SHIFT's caret
UNIT_TOLERANCE = 0.02   # Q1: 2%
HUNDREDTH_MM_PER_TWIP = 2540.0 / 1440.0
O3_PIXEL_TOLERANCE = 1  # O-3: the screen offset must be constant to within 1 px


def load(run_dir: Path):
    records = []
    with (run_dir / "captures.jsonl").open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    context = json.loads((run_dir / "context.json").read_text())
    return records, context


def band(rect):
    return rect["y"], rect["y"] + rect["h"]


def judge_row(para_twips, caret):
    """C1 and C2 for one (paragraph bounds, caret rectangle) pair."""
    para_top, para_bottom = band(para_twips)
    caret_top = caret["y"]
    caret_h = caret["h"]
    caret_bottom = caret_top + caret_h
    t_contain = T_CONTAIN_LINES * caret_h
    t_align = T_ALIGN_LINES * caret_h
    c1 = (caret_top >= para_top - t_contain) and (caret_bottom <= para_bottom + t_contain)
    c2 = abs(caret_top - para_top) <= t_align
    return {
        "paraTop": para_top,
        "paraBottom": para_bottom,
        "caretTop": caret_top,
        "caretHeight": caret_h,
        "dTop": caret_top - para_top,
        "dBottom": para_bottom - caret_bottom,
        "tContainTwips": t_contain,
        "tAlignTwips": t_align,
        "C1": c1,
        "C2": c2,
        "pass": c1 and c2,
    }


def analyse(run_dir: Path):
    records, context = load(run_dir)
    report = {
        "schemaVersion": 1,
        "finding": "093",
        "step": "option-B-step-1-native-calibration",
        "acceptance": context.get("acceptance"),
        "runDir": str(run_dir),
        "coreBuild": context.get("coreBuild"),
        "fixtureSha256": context.get("fixtureSha256"),
    }
    problems = []

    env = next((r for r in records if r.get("record") == "environment"), None)
    snapshots = {r["arm"]: r["snapshot"] for r in records if r.get("record") == "snapshot"}
    targets = [r for r in records if r.get("record") == "target"]

    report["environment"] = env
    if not env or not env.get("a11yAvailable"):
        problems.append("accessibility was not available in this build")

    first = snapshots.get("before-first-target")
    last = snapshots.get("after-last-target")
    if not first or not first.get("available"):
        report["problems"] = problems + ["no usable full snapshot"]
        report["verdict"] = "VOID"
        return report

    device = first["device"]
    report["device"] = device
    report["paragraphCount"] = first["paragraphCount"]
    report["root"] = first.get("root")

    # ---- Q1: the unit ------------------------------------------------------
    paras = [p for p in first["paragraphs"] if "raw" in p and "twipsFresh" in p]
    non_empty = [p for p in paras if p["raw"]["h"] > 0 and p["twipsFresh"]["h"] > 0]
    if len(non_empty) < 2:
        problems.append("fewer than two paragraphs carry a non-empty rectangle")
        raw_span = twip_span = 0
    else:
        raw_span = (non_empty[-1]["raw"]["y"] + non_empty[-1]["raw"]["h"]
                    - non_empty[0]["raw"]["y"])
        twip_span = (non_empty[-1]["twipsFresh"]["y"] + non_empty[-1]["twipsFresh"]["h"]
                     - non_empty[0]["twipsFresh"]["y"])
    ratio = (raw_span / twip_span) if twip_span else None

    dpi_reads = {
        "GetDPIX": device["dpiX"],
        "GetDPIY": device["dpiY"],
        "LogicToPixel(1440 twips).Width": device["pxPerInchX"],
        "LogicToPixel(1440 twips).Height": device["pxPerInchY"],
    }
    dpi_agree = len(set(dpi_reads.values())) == 1
    dpi = device["pxPerInchX"] if dpi_agree else None

    def near(value, target):
        return target != 0 and abs(value - target) / abs(target) <= UNIT_TOLERANCE

    unit = "unknown"
    if ratio is not None:
        candidates = []
        for name, expected in (
            ("output-device-pixels", (dpi / 1440.0) if dpi else None),
            ("twips", 1.0),
            ("hundredth-mm", HUNDREDTH_MM_PER_TWIP),
        ):
            if expected is not None and near(ratio, expected):
                candidates.append(name)
        if len(candidates) == 1:
            unit = candidates[0]
        elif candidates:
            unit = "ambiguous:" + "+".join(candidates)
    report["Q1_unit"] = {
        "rawSpan": raw_span,
        "twipSpan": twip_span,
        "ratio": ratio,
        "dpiReads": dpi_reads,
        "dpiReadsAgree": dpi_agree,
        "dpi": dpi,
        "expectedIfPixels": (dpi / 1440.0) if dpi else None,
        "expectedIfHundredthMM": HUNDREDTH_MM_PER_TWIP,
        "verdict": unit,
    }
    if not dpi_agree:
        problems.append("the DPI reads disagree; no single DPI is named")

    # ---- rows: pair each target with the paragraph its marker names --------
    rows = []
    for index, target in enumerate(targets):
        snap = target.get("snapshot") or {}
        cand = [p for p in snap.get("paragraphs", []) if p.get("markerMatch")]
        row = {
            "index": index,
            "marker": target["marker"],
            "found": target.get("found"),
            "caretValid": target.get("caretValid"),
            "caret": target.get("caret"),
            "markerMatches": len(cand),
        }
        if not target.get("caretValid"):
            row["error"] = "no caret"
        elif len(cand) != 1:
            row["error"] = f"{len(cand)} paragraphs match the marker"
        else:
            para = cand[0]
            row.update({
                "paragraphIndex": para["index"],
                "focusedAgreesWithMarker": bool(para.get("focused")),
                "parentIsWalkRoot": bool(para.get("parentIsWalkRoot")),
                "textHead": para.get("textHead"),
                "raw": para.get("raw"),
                "twipsFresh": para.get("twipsFresh"),
                "twipsDevice": para.get("twipsDevice"),
                "hundredthMM": para.get("hundredthMM"),
                "screen": para.get("screen"),
            })
            row["green"] = judge_row(para["twipsFresh"], target["caret"])
        rows.append(row)

    usable = [r for r in rows if "green" in r]
    if len(usable) < MIN_ROWS:
        problems.append(f"only {len(usable)} usable rows, acceptance requires {MIN_ROWS}")

    # ---- Q2: the origin ----------------------------------------------------
    o1 = all(r.get("parentIsWalkRoot") for r in usable) and bool(usable)
    tops = [r["twipsFresh"]["y"] for r in usable]
    o2_monotonic = all(b > a for a, b in zip(tops, tops[1:])) and bool(tops)
    window_twips = device["outputHeightTwips"]
    o2_beyond = bool(tops) and max(tops) > 2 * window_twips
    offsets = {(p["screen"]["x"] - p["raw"]["x"], p["screen"]["y"] - p["raw"]["y"])
               for p in paras if "screen" in p and "raw" in p}
    if not offsets:
        o3 = False
    else:
        xs = [o[0] for o in offsets]
        ys = [o[1] for o in offsets]
        o3 = ((max(xs) - min(xs)) <= O3_PIXEL_TOLERANCE
              and (max(ys) - min(ys)) <= O3_PIXEL_TOLERANCE)
    report["Q2_origin"] = {
        "O1_parentIsWalkRoot_allRows": o1,
        "O2_monotonic": o2_monotonic,
        "O2_lastTopTwips": max(tops) if tops else None,
        "O2_windowHeightTwips": window_twips,
        "O2_beyondWindow": o2_beyond,
        "O3_screenMinusRawOffsets": sorted(offsets),
        "O3_constant": bool(o3),
        "verdict": ("document-absolute" if (o1 and o2_monotonic and o2_beyond and o3)
                    else "not-established"),
    }

    # ---- Q3: the correspondence -------------------------------------------
    green_pass = [r for r in usable if r["green"]["pass"]]
    d_tops = [r["green"]["dTop"] for r in usable]
    constant_bias = bool(d_tops) and (max(d_tops) - min(d_tops)
                                      <= T_CONTAIN_LINES * min(r["caret"]["h"] for r in usable))
    report["Q3_correspondence"] = {
        "rows": len(usable),
        "passed": len(green_pass),
        "dTopTwipsMin": min(d_tops) if d_tops else None,
        "dTopTwipsMax": max(d_tops) if d_tops else None,
        "dTopSpreadIsWithinHalfALine": constant_bias,
        "verdict": ("lines-up" if (usable and len(green_pass) == len(usable)
                                   and len(usable) >= MIN_ROWS)
                    else "does-not-line-up"),
    }

    # ---- R-1: the shifted pairing must go red ------------------------------
    shifted = []
    for i, row in enumerate(usable):
        other = usable[(i + SHIFT) % len(usable)]
        if other is row:
            continue
        verdict = judge_row(row["twipsFresh"], other["caret"])
        shifted.append({
            "paragraphOf": row["marker"],
            "caretOf": other["marker"],
            "paragraphIndexGap": abs(row["paragraphIndex"] - other["paragraphIndex"]),
            **verdict,
        })
    red_leaks = [s for s in shifted if s["pass"]]
    gaps = [s["paragraphIndexGap"] for s in shifted]
    report["R1_shifted_pairing"] = {
        "shift": SHIFT,
        "pairs": len(shifted),
        "pairsThatPassed": len(red_leaks),
        "minParagraphIndexGap": min(gaps) if gaps else None,
        "wentRed": bool(shifted) and not red_leaks,
        "leaks": red_leaks[:3],
    }

    # ---- R-3: the tightest red case there is -------------------------------
    #
    # ADDED AFTER the run, and NOT gating -- said plainly because it matters.
    # R-1 is the red case the acceptance registered, and it separates paragraphs
    # by tens of thousands of twips, which is easy.  R-3 asks the hardest
    # version of the same question with no extra run: judge each row's caret
    # against the bounds of the paragraph IMMEDIATELY BEFORE and AFTER the one
    # it belongs to.  Neighbours are one paragraph pitch apart, which in this
    # fixture is the same order as C2's own tolerance, so this can legitimately
    # come out amber -- and if it does, that is a stated limit of C2's
    # resolution rather than a defect in the agreement.
    by_index = {p["index"]: p for p in first["paragraphs"] if "twipsFresh" in p}
    neighbours = []
    for row in usable:
        for delta in (-1, 1):
            other = by_index.get(row["paragraphIndex"] + delta)
            if not other:
                continue
            verdict = judge_row(other["twipsFresh"], row["caret"])
            neighbours.append({"caretOf": row["marker"], "delta": delta,
                               "neighbourIndex": other["index"], **verdict})
    neighbour_leaks = [n for n in neighbours if n["pass"]]
    report["R3_neighbour_pairing"] = {
        "gating": False,
        "registeredInAdvance": False,
        "pairs": len(neighbours),
        "pairsThatPassed": len(neighbour_leaks),
        "wentRed": bool(neighbours) and not neighbour_leaks,
        "leaks": neighbour_leaks[:4],
    }

    # ---- how much room the green answer had --------------------------------
    if usable:
        worst = max(abs(r["green"]["dTop"]) for r in usable)
        allowed = min(r["green"]["tAlignTwips"] for r in usable)
        report["marginToTolerance"] = {
            "worstAbsDTopTwips": worst,
            "tightestTAlignTwips": allowed,
            "timesInsideTolerance": (allowed / worst) if worst else None,
        }

    # ---- R-2: the probe must be able to print a different value ------------
    distinct_tops = len({r["twipsFresh"]["y"] for r in usable})
    report["R2_non_constancy"] = {
        "distinctParagraphTops": distinct_tops,
        "rows": len(usable),
        "ok": distinct_tops == len(usable) and len(usable) > 1,
    }

    # ---- geometry stability across the walk --------------------------------
    if last and last.get("available"):
        before = {p["index"]: p.get("twipsFresh") for p in first["paragraphs"]}
        after = {p["index"]: p.get("twipsFresh") for p in last["paragraphs"]}
        moved = [k for k in before if k in after and before[k] != after[k]]
        report["geometryStable"] = {"comparedParagraphs": len(before),
                                    "moved": len(moved), "ok": not moved}
    else:
        report["geometryStable"] = {"ok": None, "note": "no closing snapshot"}

    report["rows"] = rows
    report["shiftedRows"] = shifted
    report["problems"] = problems

    ok = (not problems
          and report["Q1_unit"]["verdict"] != "unknown"
          and report["Q2_origin"]["verdict"] == "document-absolute"
          and report["Q3_correspondence"]["verdict"] == "lines-up"
          and report["R1_shifted_pairing"]["wentRed"]
          and report["R2_non_constancy"]["ok"])
    report["verdict"] = "PASS" if ok else "FAIL"
    return report


def human(report):
    out = []
    out.append(f"verdict: {report['verdict']}")
    q1 = report.get("Q1_unit", {})
    out.append(f"Q1 unit        : {q1.get('verdict')}  (ratio raw/twips = {q1.get('ratio')})")
    out.append(f"                 dpi reads {q1.get('dpiReads')} agree={q1.get('dpiReadsAgree')}")
    q2 = report.get("Q2_origin", {})
    out.append(f"Q2 origin      : {q2.get('verdict')}  O1={q2.get('O1_parentIsWalkRoot_allRows')} "
               f"O2mono={q2.get('O2_monotonic')} O2beyond={q2.get('O2_beyondWindow')} "
               f"O3={q2.get('O3_constant')}")
    q3 = report.get("Q3_correspondence", {})
    out.append(f"Q3 lines up    : {q3.get('verdict')}  {q3.get('passed')}/{q3.get('rows')} rows, "
               f"dTop {q3.get('dTopTwipsMin')}..{q3.get('dTopTwipsMax')} twips")
    r1 = report.get("R1_shifted_pairing", {})
    out.append(f"R-1 red case   : wentRed={r1.get('wentRed')} "
               f"({r1.get('pairsThatPassed')} of {r1.get('pairs')} leaked)")
    r3 = report.get("R3_neighbour_pairing", {})
    out.append(f"R-3 neighbours : wentRed={r3.get('wentRed')} "
               f"({r3.get('pairsThatPassed')} of {r3.get('pairs')} leaked) "
               f"[reported, not gating, not registered in advance]")
    m = report.get("marginToTolerance", {})
    out.append(f"margin         : worst |dTop| {m.get('worstAbsDTopTwips')} twips vs "
               f"tolerance {m.get('tightestTAlignTwips')} twips "
               f"({m.get('timesInsideTolerance')}x inside)")
    r2 = report.get("R2_non_constancy", {})
    out.append(f"R-2 non-const  : ok={r2.get('ok')} ({r2.get('distinctParagraphTops')} distinct tops)")
    if report.get("problems"):
        out.append("problems: " + "; ".join(report["problems"]))
    out.append("")
    out.append(f"{'marker':<12} {'para':>5} {'paraTop':>9} {'paraBot':>9} "
               f"{'caretTop':>9} {'caretH':>7} {'dTop':>7} {'C1':>3} {'C2':>3}")
    for row in report.get("rows", []):
        if "green" not in row:
            out.append(f"{row['marker']:<12} -- {row.get('error')}")
            continue
        g = row["green"]
        out.append(f"{row['marker']:<12} {row['paragraphIndex']:>5} {g['paraTop']:>9} "
                   f"{g['paraBottom']:>9} {g['caretTop']:>9} {g['caretHeight']:>7} "
                   f"{g['dTop']:>7} {str(g['C1']):>3} {str(g['C2']):>3}")
    return "\n".join(out)


# --------------------------------------------------------------------------
# The judge has to be able to be wrong.  These fixtures are synthetic and exist
# so that "it said PASS" is not the only evidence the judge can produce.
def self_test() -> int:
    failures = []

    def verify(name, condition):
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}")
        if not condition:
            failures.append(name)

    caret = {"x": 1000, "y": 5000, "w": 10, "h": 240}
    verify("an exactly-aligned paragraph passes both",
           judge_row({"x": 0, "y": 5000, "w": 9000, "h": 240}, caret)["pass"])
    verify("a paragraph one line above still passes C2 (2-line tolerance)",
           judge_row({"x": 0, "y": 4760, "w": 9000, "h": 480}, caret)["C2"])
    verify("a paragraph three lines above fails C2",
           not judge_row({"x": 0, "y": 4280, "w": 9000, "h": 240}, caret)["C2"])
    verify("a paragraph that does not contain the caret fails C1",
           not judge_row({"x": 0, "y": 8000, "w": 9000, "h": 240}, caret)["C1"])
    verify("a whole-document rectangle passes C1 but fails C2",
           judge_row({"x": 0, "y": 0, "w": 9000, "h": 100000}, caret)["C1"]
           and not judge_row({"x": 0, "y": 0, "w": 9000, "h": 100000}, caret)["C2"])
    verify("half a line of slack is honoured at the bottom edge",
           judge_row({"x": 0, "y": 5000, "w": 9000, "h": 120}, caret)["C1"])
    verify("more than half a line past the bottom edge is not",
           not judge_row({"x": 0, "y": 5000, "w": 9000, "h": 100}, caret)["C1"])
    verify("the tolerances scale with the reported line height",
           judge_row({"x": 0, "y": 4300, "w": 9000, "h": 1000},
                     {"x": 0, "y": 5000, "w": 10, "h": 500})["C2"]
           and not judge_row({"x": 0, "y": 4300, "w": 9000, "h": 1000}, caret)["C2"])
    print(f"\nself-test: {8 - len(failures)}/8 checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.run_dir:
        parser.error("RUN_DIR is required")
    report = analyse(Path(args.run_dir))
    text = json.dumps(report, indent=2) if args.json else human(report)
    print(text)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
