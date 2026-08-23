#!/usr/bin/env python3
"""Which text bands merge on the accessibility core, and where?

Measured 2026-08-23: the canvas ink scan finds 9 bands for 9 paragraphs on the
shipped core and **7 for 9** on the accessibility core, every run, on all three
profiles built from it. Two pairs merge.

That number is what breaks the product path there: the aim goes to the wrong
paragraph, checks that cannot say WHICH paragraph they clicked report
NOT_ESTABLISHED, and `format_arm` -- which presses a toggle exactly once and
relies on the alternation -- ends up a step out of phase, which is why bold
comes back INVERTED rather than absent.

FINDING 072 IS THE PRECEDENT: a correctly drawn caret bridged the gap between
two lines and `text_bands()` merged them. Its remedy (EXCLUDE_CARET) is in and
clearly does not cover whatever is bridging here. So the question this asks is
narrow: WHICH pairs merged, and how wide is the ink that joins them.

It matters because of what it would mean: if the accessibility core draws
something extra -- a focus rectangle, say -- then the DOCUMENT is fine and the
harness is measuring itself. That is the "harness path is not the user's path"
rule pointing the other way for once.

Usage:
  probe_band_merge.py --profile e2-editor-v4 --out FILE
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from probe_a11y_gate0 import gate_mirror, wait_until  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

# The page-border detection, replayed so its inputs are visible.  `INK_ROWS`
# calls a column a border when it is inked down more than 20% of the canvas
# height, then clips everything outside the outermost pair.  If that fails, the
# renderer's off-page strips come in and both merge lines and inflate every
# band's horizontal extent -- which is what collapses density.
BORDER_SCAN = """(() => {
const canvas = document.querySelector('#canvas');
const w = canvas.width, h = canvas.height;
const data = canvas.getContext('2d').getImageData(0, 0, w, h).data;
const columnTotals = new Int32Array(w);
for (let y = 0; y < h; y += 1)
  for (let x = 0; x < w; x += 1) {
    const i = (y * w + x) * 4;
    if (data[i+3] > 128 && data[i] < 100 && data[i+1] < 100 && data[i+2] < 100)
      columnTotals[x] += 1;
  }
const border = [];
for (let x = 0; x < w; x += 1) if (columnTotals[x] > h * 0.20) border.push(x);
const top = [...columnTotals].map((c, x) => ({ x, rows: c, frac: +(c / h).toFixed(3) }))
  .sort((a, b) => b.rows - a.rows).slice(0, 8);
return { w, h, borderColumns: border.length,
         borderRange: border.length ? [border[0], border[border.length - 1]] : null,
         wouldClip: border.length ? (border[border.length - 1] - border[0] > w * 0.5) : false,
         topColumns: top };
})()"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--no-caret-exclusion", action="store_true",
                        help="leave the drawn caret in the scan, finding 072's "
                             "reproduction switch -- here to ask whether the "
                             "extra ink is the caret at all")
    args = parser.parse_args()

    pp.EXCLUDE_CARET = not args.no_caret_exclusion
    record = {"schemaVersion": 1, "release": "band-merge",
              "profile": args.profile,
              "caretExcluded": pp.EXCLUDE_CARET}

    scratch = Path(tempfile.mkdtemp(prefix="bands-"))
    record["mirror"] = gate_mirror(scratch, args.profile)
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", record["mirror"]["root"]],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session = ChromeSession("cold")
    try:
        navigate(session, base)
        state = wait_until(session, lambda s: s.get("state") == "ready", 180)
        record["booted"] = state.get("state")
        if state.get("state") != "ready":
            record["outcome"] = "NOT_ESTABLISHED"
            return finish(record, args)
        time.sleep(1.5)
        # AT REST FIRST, then with a caret placed where the product path puts
        # one before its inline-format arms (y=0.24).
        #
        # The rest reading came back 9-for-9 on BOTH cores, so the 7-for-9 the
        # product path reports is not a property of the core at rest -- it
        # appears once the page has been driven. Finding 072's mechanism is a
        # drawn caret bridging the gap between two lines, and its remedy
        # (EXCLUDE_CARET) is already on, so this asks whether the caret still
        # bridges on this core despite the exclusion.
        scan0, bands0 = pp.stable_bands(session)
        record["atRest"] = {"bandCount": len(bands0),
                            "centres": [round(b.get("centreFraction", 0), 4)
                                        for b in bands0]}
        clicks = pp.caret_click_fractions(
            evaluate(session, pp.LINE_INK.replace("ARG_Y", "0.24")) or {})
        pp.place_caret_and_settle(session, pp.POINT_AT, clicks["near"], "0.24")
        time.sleep(1.5)
        scan, bands = pp.stable_bands(session)
        record["afterCaret"] = {"bandCount": len(bands),
                                "centres": [round(b.get("centreFraction", 0), 4)
                                            for b in bands]}
        # DOES IT COME BACK?  The two top bands vanish on the accessibility
        # core after a caret placement, and everything else keeps its exact
        # centreFraction -- so the view did not scroll, the ink is gone.  A
        # transient repaint gap and a persistent blank region are different
        # defects and only one of them is finding 062's shape, so this asks
        # rather than assumes.
        # THE CLASSIFICATION, REPLAYED WITH THE REJECTS VISIBLE.
        #
        # `text_bands` drops a band whose density falls outside
        # [0.15, 0.9) and the dropped one does not come back in the return
        # value, so "7 bands" cannot say WHY two are missing. This recomputes
        # the same steps from the same scan and reports every candidate --
        # including the ones the filter removes -- because the difference
        # between "the ink is gone" and "the ink was classified away" is the
        # whole question, and reading only the survivors cannot tell them
        # apart. (It could not: the ink is present, measured.)
        raw = evaluate(session, pp.INK_ROWS.replace(
            "ARG_EXCLUDE_CARET", "true" if pp.EXCLUDE_CARET else "false")) or {}
        counts = raw.get("counts") or []
        runs, start = [], None
        for y, c in enumerate(counts):
            if c > 0 and start is None:
                start = y
            elif c <= 0 and start is not None:
                runs.append({"top": start, "bottom": y - 1}); start = None
        if start is not None:
            runs.append({"top": start, "bottom": len(counts) - 1})
        merged = []
        for run in runs:
            if merged and run["top"] - merged[-1]["bottom"] <= pp.BAND_MERGE_GAP:
                merged[-1]["bottom"] = run["bottom"]
            else:
                merged.append(dict(run))
        cands = []
        for b in merged:
            rows = range(b["top"], b["bottom"] + 1)
            firsts = [raw["firsts"][y] for y in rows if raw["firsts"][y] >= 0]
            if not firsts:
                continue
            maxInk = max(counts[y] for y in rows)
            first = min(firsts); last = max(raw["lasts"][y] for y in rows)
            extent = last - first + 1
            cands.append({
                "top": b["top"], "bottom": b["bottom"],
                "height": b["bottom"] - b["top"] + 1,
                "density": round(maxInk / extent, 4),
                "kept": 0.15 <= (maxInk / extent) < 0.9,
                "centreFraction": round((b["top"] + b["bottom"]) / 2
                                        / raw.get("height", 1), 4)})
        record["classification"] = {
            "rawRuns": len(runs), "afterMerge": len(merged),
            "bandMergeGap": pp.BAND_MERGE_GAP,
            "rawGaps": sorted(runs[i + 1]["top"] - runs[i]["bottom"]
                              for i in range(len(runs) - 1))[:12],
            "candidates": cands}

        # THE ROW PROFILE where the merge happens, so the extra ink can be
        # described rather than guessed at.  A thin run spanning few columns is
        # a caret-shaped artifact; one spanning the text width is an underline
        # or a highlight; several scattered ones are something else again.
        # `counts` is inked pixels in the row, `first`/`last` its horizontal
        # extent -- together they say the SHAPE without anyone squinting at a
        # screenshot.
        lo, hi = 78, 138
        record["rowProfile"] = [
            {"y": y, "count": counts[y],
             "first": raw["firsts"][y], "last": raw["lasts"][y]}
            for y in range(lo, min(hi, len(counts)))]
        record["caretReportedByScan"] = raw.get("caret")
        # THE DATUM THAT WAS THERE ALL ALONG.  `INK_ROWS` reports whether it
        # found the page border and clipped to it; the off-page strips it warns
        # about in its own comment are exactly what we measured leaking in. Not
        # recording this earlier meant inferring from densities what the scan
        # was willing to state outright.
        record["clipped"] = raw.get("clipped")
        record["borderScan"] = evaluate(session, BORDER_SCAN)

        record["recovery"] = []
        for wait in (4, 8, 16):
            time.sleep(wait)
            _s, later = pp.stable_bands(session)
            top = evaluate(session, pp.LINE_INK.replace("ARG_Y", "0.0985")) or {}
            record["recovery"].append({
                "afterSeconds": wait,
                "bandCount": len(later),
                "inkAtTopBand": top.get("available"),
                "centres": [round(b.get("centreFraction", 0), 4) for b in later],
            })
        record["scan"] = {k: scan.get(k) for k in ("width", "height")}
        record["bandCount"] = len(bands)
        record["bands"] = [
            {"index": i, "first": b.get("first"), "last": b.get("last"),
             "height": (b.get("last") or 0) - (b.get("first") or 0),
             "centreFraction": round(b.get("centreFraction", 0), 5)}
            for i, b in enumerate(bands)]
        # The gaps are the measurement: a merge shows up as one band whose
        # height is about two bands plus the gap that used to separate them.
        record["gaps"] = [
            {"between": [i, i + 1],
             "gap": (bands[i + 1].get("first") or 0) - (bands[i].get("last") or 0)}
            for i in range(len(bands) - 1)]
        record["outcome"] = "SEE_BANDS"
    finally:
        try:
            session.close()
        finally:
            server.terminate()
    return finish(record, args)


def finish(record, args) -> int:
    text = json.dumps(record, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
