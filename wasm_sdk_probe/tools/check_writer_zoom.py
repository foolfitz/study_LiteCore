#!/usr/bin/env python3
"""SPEC-P-demo-batch-1 section 3: the Writer page's toolbar zoom, Z0-Z8.

On a mirror of dist/ with the live page sources and an observer on the Worker.
Real pointer and keys; the desk is positioned by script only as setup, and every
measured input is a real one.  The observer records what crossed to the engine,
which is what Z2 (the engine painted at the new width, nothing was stretched) and
Z7 (no edit reached the engine) are read from.

Every check is recorded and the run goes on past a red one.

  check_writer_zoom.py --out DIR [--browsers chrome,firefox] [--mutation NAME] [--document ODT]
  --document: t3-long.odt by default.  r7-compat/l1-layout-table-image.odt carries a comment, and Writer's
  reported width then moves with the paint scale (the comment sidebar; the owner's hand test of host 0.2.56).
  --mutation applies one named source change and exits 0 only if its clause turns red.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import statistics
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_e2_c_product_path as pp  # noqa: E402
import v21_input as real  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
APP = PROJECT / "web/e2-editor-app.js"
HTML = PROJECT / "web/e2-editor.html"
DOCUMENT = PROJECT / "test-docs/t3-long.odt"
QUIET = 1.0
TWIPS = 15
CAP = 2400
TEXT_P = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p"
EDITS = {"editorActionV1", "editorActionV2", "insertText", "replaceSelection", "undo", "redo"}

OBSERVER = """<script>
(() => {
  const rec = window.__z = {requests: [], posted: {}, responses: 0, caret: null, doc: null, widths: [], blobs: [], workers: 0};
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) { super(url, options); rec.workers += 1;
      this.addEventListener('message', ev => { const m = ev.data;
        if (m?.kind === 'response') { rec.responses += 1;
          const row = rec.posted[m.requestId];
          if (row) { row.ms = performance.now() - row.at; row.ok = m.ok; delete rec.posted[m.requestId]; }
          const r = m.result;
          // The open's reply names the size as width/height (document-sdk.js DocumentHandle); the page lays out for it first.
          if (row?.op === 'open' && r && typeof r.width === 'number') { rec.doc = {width: r.width, height: r.height};
            if (!rec.widths.includes(r.width)) rec.widths.push(r.width); }
          if (r && typeof r.documentWidthTwips === 'number') { rec.doc = {width: r.documentWidthTwips, height: r.documentHeightTwips};
            if (!rec.widths.includes(r.documentWidthTwips)) rec.widths.push(r.documentWidthTwips); } }
        if (m?.kind === 'event' && m.event === 'editor-state' && m.caret) rec.caret = m.caret;
      }); }
    postMessage(m, ...rest) {
      if (m?.kind === 'request') { const row = {op: m.operation, action: m.payload?.action ?? null, at: performance.now()};
        if (m.operation === 'paint') row.canvasWidthPx = m.payload.canvasWidthPx;
        rec.requests.push(row); rec.posted[m.requestId] = row; }
      return super.postMessage(m, ...rest); }
  };
  const create = URL.createObjectURL.bind(URL);
  URL.createObjectURL = blob => { if (blob instanceof Blob) rec.blobs.push(blob); return create(blob); };
  const click = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () { if (this.hasAttribute('download')) return; return click.call(this); };
})();
</script>"""

STATE = """(() => { const q = s => document.querySelector(s), d = q('#desk'), p = q('#paper'), c = q('#canvas');
  const dr = d.getBoundingClientRect(), pr = p.getBoundingClientRect(), z = window.__z;
  return {desk: {left: dr.left, top: dr.top, clientWidth: d.clientWidth, clientHeight: d.clientHeight,
                 scrollLeft: d.scrollLeft, scrollTop: d.scrollTop, scrollWidth: d.scrollWidth, scrollHeight: d.scrollHeight},
    paper: {left: pr.left, top: pr.top, width: pr.width, height: pr.height, styleWidth: p.style.width},
    canvas: {width: c.width, height: c.height, window: c.dataset.window, bands: c.dataset.bands},
    label: q('#zoom-reset')?.textContent ?? null, zoomOutDisabled: q('#zoom-out')?.disabled ?? null,
    zoomInDisabled: q('#zoom-in')?.disabled ?? null, dpr: devicePixelRatio,
    pill: q('#state-pill')?.dataset.state, revision: q('#s-revision')?.textContent, toast: q('#toast')?.textContent,
    requests: z.requests.length, responses: z.responses, caret: z.caret, doc: z.doc, widths: z.widths, workers: z.workers, blobs: z.blobs.length,
    paints: z.requests.filter(r => r.op === 'paint').length,
    lastPaintWidth: [...z.requests].reverse().find(r => r.op === 'paint')?.canvasWidthPx ?? null}; })()"""
BLOB = """(async () => { const b = window.__z.blobs.at(-1); const u = new Uint8Array(await b.arrayBuffer());
  let s = ''; for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode(...u.subarray(i, i + 8192)); return btoa(s); })()"""
PLACE = """(() => { const d = document.querySelector('#desk'), p = document.querySelector('#paper');
  const dr = d.getBoundingClientRect(), pr = p.getBoundingClientRect();
  d.scrollLeft += pr.left + ARG_X - (dr.left + d.clientWidth / 2);
  d.scrollTop += pr.top + ARG_Y - (dr.top + d.clientHeight / 2);
  return true; })()"""

MUTATIONS = {
    "no-side-follow": ("Z4", APP, "      el.desk.scrollLeft += x - (view.left + el.desk.clientWidth / 2);\n", "      ;\n"),
    "no-centre": ("Z5", APP, "  el.desk.scrollTop += after.top + fractionY * after.height - middleY;\n", ""),
    "no-flex-none": ("Z6", HTML, "position: relative; flex: none; margin-inline: auto;", "position: relative;"),
    "stretched": ("Z2", APP, "  const backingWidth = Math.min(MAX_BACKING_WIDTH,\n"
                  "                                Math.round(cssWidth * (globalThis.devicePixelRatio || 1)));\n",
                  "  const backingWidth = Math.min(MAX_BACKING_WIDTH,\n"
                  "                                Math.round(Math.min(available, 900) * (globalThis.devicePixelRatio || 1)));\n"),
}


def steps_from_source() -> list[int]:
    """Z1's levels, read from the page: a level added there is measured here."""
    found = re.search(r"const ZOOM_STEPS = \[([0-9, ]+)\];", APP.read_text(encoding="utf-8"))
    return [int(x) for x in found.group(1).split(",")]


def view_rows(s):
    doc_rows = int(s["canvas"]["window"].split()[0])
    paper, desk = s["paper"], s["desk"]
    scale = doc_rows / paper["height"]
    top = max(desk["top"], paper["top"]) - paper["top"]
    bottom = min(desk["top"] + desk["clientHeight"], paper["top"] + paper["height"]) - paper["top"]
    return math.floor(top * scale), math.ceil(bottom * scale)


def covered(s) -> bool:
    """The rows in view are all held by bands painted since the last layout."""
    if not s["canvas"]["window"]:
        return False
    start, end = view_rows(s)
    bands = sorted((int(b.split(":")[1]), int(b.split(":")[1]) + int(b.split(":")[2]))
                   for b in (s["canvas"]["bands"] or "").split())
    at = start
    for top, stop in bands:
        if top > at:
            break
        at = max(at, stop)
    return at >= end


def middle_twips(s):
    desk, paper = s["desk"], s["paper"]
    return ((desk["left"] + desk["clientWidth"] / 2 - paper["left"]) / paper["width"] * s["doc"]["width"],
            (desk["top"] + desk["clientHeight"] / 2 - paper["top"]) / paper["height"] * s["doc"]["height"])


class Run:
    def __init__(self, session, browser, record):
        self.session, self.browser, self.record = session, browser, record

    def state(self):
        return evaluate(self.session, STATE)

    def check(self, name, passed, actual=None):
        self.record["checks"].append({"id": name, "pass": bool(passed), "actual": actual})

    def wait(self, predicate, limit=40):
        until, s = time.monotonic() + limit, None
        while time.monotonic() < until:
            s = self.state()
            if predicate(s):
                return s
            time.sleep(0.15)
        return s

    def settled(self, limit=40):
        return self.wait(lambda s: s["requests"] == s["responses"] and covered(s) and s["pill"] == "ready", limit)

    def press(self, selector):
        box = evaluate(self.session, pp.BUTTON_BOX.replace("ARG_SELECTOR", selector))
        real.click(self.session, self.browser, box["x"], box["y"])

    def open(self, raw):
        navigate(self.session, self.record["base"])
        self.wait(lambda s: s["pill"] == "ready", 240)
        workers = self.state()["workers"]
        evaluate(self.session, pp.OPEN_BYTES.replace("ARG_B64", base64.b64encode(raw).decode()).replace("ARG_NAME", DOCUMENT.name))
        self.wait(lambda s: s["workers"] > workers and s["pill"] == "ready", 120)
        time.sleep(1.0)
        return self.settled()

    def click_paper(self, x_twips, y_twips):
        """Bring the point to the middle of the desk, click it, wait for the engine's caret."""
        s = self.state()
        evaluate(self.session, PLACE.replace("ARG_X", repr(x_twips / s["doc"]["width"] * s["paper"]["width"]))
                 .replace("ARG_Y", repr(y_twips / s["doc"]["height"] * s["paper"]["height"])))
        s = self.settled()
        real.click(self.session, self.browser,
                   s["paper"]["left"] + x_twips / s["doc"]["width"] * s["paper"]["width"],
                   s["paper"]["top"] + y_twips / s["doc"]["height"] * s["paper"]["height"])
        time.sleep(0.5)
        return self.wait(lambda n: n["requests"] == n["responses"] and n["caret"], 20)

    def go_to(self, percent):
        """Real presses, up or down, to a level; None is the fit."""
        if percent is None:
            self.press("#zoom-reset")
            time.sleep(0.3)
            return self.settled()
        for _ in range(12):
            s = self.state()
            shown = int(s["label"].rstrip("%"))
            if shown == percent:
                return self.settled()
            self.press("#zoom-in" if shown < percent else "#zoom-out")
            self.wait(lambda n: n["label"] != s["label"], 15)
            self.settled()
        return self.state()


def backing_for(css, s):
    return min(CAP, round(css * s["dpr"]))


def laid_out_widths(s):
    """The widths the page may be laid out for: reported by the engine and within 1 percent of the last report.

    The page follows a report only past a few canvas pixels (the 0.2.56 hand test's fix), so with a comment it keeps an
    earlier width; one stuck at the width it opened with, or one that missed a real change (a sidebar is about 27
    percent), falls outside.  Without comments the engine reports one width and this is that width alone.
    """
    last = s["doc"]["width"]
    return [w for w in s["widths"] if abs(w - last) <= 0.01 * last]


def paper_for(percent, s, paper):
    """Whether `paper` is Math.round of the level applied to one of those widths (compared unrounded: Python's round is
    the banker's, the page's Math.round is not -- 1698.5 is 1698 here and 1699 there)."""
    return any(abs(paper - w / TWIPS * percent / 100) <= 0.5 for w in laid_out_widths(s))


def level_checks(run, percent, s, tag):
    # The paper is the level applied to a width the engine reported.  One width for a document without comments (t3), as
    # before; with a comment Writer reports a few, tens of twips apart, depending on the scale it last painted at.
    run.check(f"Z1/{tag}", paper_for(percent, s, s["paper"]["width"]) and s["label"] == f"{percent}%",
              {"paper": s["paper"]["width"], "widths": laid_out_widths(s), "reported": s["widths"], "label": s["label"]})
    backing = backing_for(s["paper"]["width"], s)
    # ... and once covered the page stops asking: no paint for QUIET seconds.  The defect this is red on painted forever.
    time.sleep(QUIET)
    later = run.state()
    run.check(f"Z2/{tag}", s["canvas"]["width"] == backing and s["lastPaintWidth"] == backing and covered(s)
              and later["paints"] == s["paints"],
              {"canvas": s["canvas"]["width"], "expected": backing, "lastPaint": s["lastPaintWidth"],
               "covered": covered(s), "dpr": s["dpr"], "paintsWhileQuiet": later["paints"] - s["paints"]})


def ladder(run, steps, positions=True):
    """Every level, up and then down, by real presses from a position inside the document."""
    s = run.settled()
    if positions:
        evaluate(run.session, real.SCROLL_TO_FRACTION.replace("ARG_F", "0.4"))
        s = run.settled()
    line = (s["caret"] or {}).get("height") or 420
    for direction, selector, order in (("up", "#zoom-in", steps), ("down", "#zoom-out", steps[::-1])):
        for percent in order:
            before = run.state()
            shown = int(before["label"].rstrip("%"))
            if (direction == "up" and percent <= shown) or (direction == "down" and percent >= shown):
                continue
            middle = middle_twips(before)
            run.press(selector)
            run.wait(lambda n: n["label"] != before["label"], 15)
            s = run.settled()
            level_checks(run, percent, s, f"{direction}-{percent}")
            if positions:
                after = middle_twips(s)
                run.check(f"Z5/{direction}-{percent}", abs(after[1] - middle[1]) <= line,
                          {"beforeY": middle[1], "afterY": after[1], "lineTwips": line})
    return s


def odt_text(raw: bytes) -> list[str]:
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(raw)).read("content.xml"))
    return ["".join(p.itertext()) for p in root.iter(TEXT_P)]


def wide_run(run, raw, steps, out, name):
    s = run.open(raw)
    desk_width = s["desk"]["clientWidth"]
    expected = min(max(320, desk_width - 40), 900)
    rows = [backing_for(expected, s) * s["doc"]["height"] / w for w in laid_out_widths(s)]
    run.check("Z0/fit", abs(s["paper"]["width"] - expected) < 1 and s["canvas"]["width"] == backing_for(expected, s)
              and any(abs(int(s["canvas"]["window"].split()[0]) - r) <= 0.5 for r in rows),
              {"paper": s["paper"]["width"], "expected": expected, "canvas": s["canvas"], "docRows": rows})
    revision, start = s["revision"], s["requests"]
    # A caret first: its height is Z5's line, and Z3's point comes from where it landed.
    s = run.click_paper(s["doc"]["width"] * 0.3, s["doc"]["height"] * 0.4)
    target = (s["caret"]["x"] + 60, s["caret"]["y"] + s["caret"]["height"] / 2)
    ladder(run, steps)
    run.go_to(None)
    reference = run.click_paper(*target)["caret"]
    for percent in steps:
        run.go_to(percent)
        caret = run.click_paper(*target)["caret"]
        run.check(f"Z3/{percent}", (caret["x"], caret["y"]) == (reference["x"], reference["y"]),
                  {"caret": caret, "reference": reference})
    # Z8: the end of a long document at the largest level.
    run.go_to(steps[-1])
    evaluate(run.session, "(() => { const d = document.querySelector('#desk'); d.scrollTop = d.scrollHeight; return true; })()")
    time.sleep(0.5)
    s = run.settled(60)
    run.check("Z8/end-of-long-document", covered(s) and s["desk"]["scrollTop"] > 0,
              {"scrollTop": s["desk"]["scrollTop"], "window": s["canvas"]["window"], "bands": s["canvas"]["bands"]})
    (out / f"{name}-200-end.png").write_bytes(run.session.screenshot())
    run.go_to(None)
    s = run.settled()
    requests = evaluate(run.session, f"window.__z.requests.slice({start}).map(r => r.op)")
    edits = sorted(set(requests) & EDITS)
    run.check("Z7/no-edit-reached-the-engine", not edits and s["revision"] == revision and s["pill"] == "ready",
              {"operations": sorted(set(requests)), "edits": edits, "revision": [revision, s["revision"]]})
    blobs = s["blobs"]
    run.press('#toolbar button[data-action="save"]')
    s = run.wait(lambda n: n["blobs"] > blobs, 60)
    saved = base64.b64decode(evaluate(run.session, BLOB)) if s["blobs"] > blobs else None
    run.check("Z7/saved-text-equals-the-original", saved is not None and odt_text(saved) == odt_text(raw),
              {"paragraphs": len(odt_text(saved)) if saved else None})


def narrow_run(run, raw, steps, out, name):
    s = run.open(raw)
    opened = s["paper"]["width"]
    # Spec append 1: green here with or without the fix, the mirror's desk already has its vertical scrollbar when this document
    # opens.  Z10's red is the host's first open (host-0.2.46/host_batch.py); these two only guard the mirror's own path.
    run.check("Z10/fit-has-no-side-scroll", s["desk"]["scrollWidth"] <= s["desk"]["clientWidth"],
              {"desk": s["desk"], "paper": s["paper"]})
    (out / f"{name}-narrow-fit.png").write_bytes(run.session.screenshot())
    run.go_to(steps[-1])
    s = run.go_to(None)
    run.check("Z10/fit-returns-to-the-width-it-opened-at", abs(s["paper"]["width"] - opened) < 1,
              {"opened": opened, "returned": s["paper"]["width"], "label": s["label"]})
    run.go_to(steps[-1])
    s = run.settled()
    evaluate(run.session, "(() => { document.querySelector('#desk').scrollLeft = 0; return true; })()")
    s = run.settled()
    run.check("Z6/left-edge-reachable", s["paper"]["left"] >= s["desk"]["left"] and paper_for(steps[-1], s, s["paper"]["width"])
              and s["desk"]["scrollWidth"] > s["desk"]["clientWidth"],
              {"paper": s["paper"], "desk": s["desk"], "widths": laid_out_widths(s)})
    (out / f"{name}-narrow-left-edge.png").write_bytes(run.session.screenshot())

    def visible(s):
        x = s["paper"]["left"] + s["caret"]["x"] / s["doc"]["width"] * s["paper"]["width"]
        return s["desk"]["left"] <= x <= s["desk"]["left"] + s["desk"]["clientWidth"], x

    real.click(run.session, run.browser, s["desk"]["left"] + 260, s["desk"]["top"] + 240)
    time.sleep(0.6)
    run.wait(lambda n: n["requests"] == n["responses"] and n["caret"], 20)
    for label, key in (("end", "End"), ("typed", "x"), ("home", "Home")):
        real.key(run.session, run.browser, key)
        time.sleep(0.6)
        s = run.settled()
        seen, x = visible(s)
        run.check(f"Z4/{label}", seen, {"caretX": x, "deskLeft": s["desk"]["left"], "deskWidth": s["desk"]["clientWidth"],
                                        "scrollLeft": s["desk"]["scrollLeft"], "caret": s["caret"]})


def typing_cost(run, raw, percent):
    """One-off, not a gate (spec section 3): what the engine answers while the paper is large."""
    s = run.open(raw)
    if percent is not None:
        run.go_to(percent)
    s = run.click_paper(s["doc"]["width"] * 0.3, s["doc"]["height"] * 0.2)
    start = s["requests"]
    for ch in "abcdefghijklmnopqrstuvwxyzabcd":
        real.key(run.session, run.browser, ch)
        time.sleep(0.08)
    time.sleep(1.0)
    run.settled(30)
    rows = evaluate(run.session, f"window.__z.requests.slice({start})")
    typed = [r["ms"] for r in rows if r["op"] != "paint" and r.get("ms") is not None and r["op"] not in ("editorGetStateV2", "pageRectangles")]
    paints = [r["ms"] for r in rows if r["op"] == "paint" and r.get("ms") is not None]
    return {"percent": percent, "typedMedianMs": statistics.median(typed) if typed else None, "typedCount": len(typed),
            "paintMedianMs": statistics.median(paints) if paints else None, "paintCount": len(paints),
            "operations": sorted({r["op"] for r in rows})}


def run_one(record, raw, steps, out, config):
    session = None
    window = config.get("window", (1400, 1000))
    try:
        session = common.open_browser(record["browser"], window)
        record["version"] = getattr(session, "version", None)
        if config.get("dpr"):
            session.call("Emulation.setDeviceMetricsOverride",
                         {"width": window[0], "height": window[1], "deviceScaleFactor": config["dpr"], "mobile": False})
        run = Run(session, record["browser"], record)
        name = f"{record['browser']}-{record['arm']}"
        if record["arm"] == "wide":
            wide_run(run, raw, steps, out, name)
        elif record["arm"] == "narrow":
            narrow_run(run, raw, steps, out, name)
        elif record["arm"] == "dpr2":
            run.open(raw)
            ladder(run, steps, positions=False)
        else:
            record["cost"] = typing_cost(run, raw, config.get("percent"))
    except Exception:  # noqa: BLE001 -- a crash is a result; keep the cells already read
        record["fatal"] = traceback.format_exc()
    finally:
        if session is not None:
            record["cleanup"] = common.close_browser(session)


def main() -> int:
    global DOCUMENT
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--mutation", choices=sorted(MUTATIONS))
    parser.add_argument("--arms", help="only these arms, comma separated; a partial run is a diagnostic, never a verdict")
    parser.add_argument("--document", type=Path, default=DOCUMENT)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    DOCUMENT = args.document.resolve()
    raw, steps = DOCUMENT.read_bytes(), steps_from_source()
    sources = {APP.name: APP.read_text(encoding="utf-8"), HTML.name: HTML.read_text(encoding="utf-8")}
    report = {"argv": sys.argv, "tool": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "document": {"name": DOCUMENT.name, "sha256": hashlib.sha256(raw).hexdigest()}, "steps": steps,
              "sources": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in sources.items()},
              "mutation": args.mutation, "runs": []}
    arms = [("wide", {}), ("narrow", {"window": (900, 800)})]
    if args.mutation:
        clause, path, old, new = MUTATIONS[args.mutation]
        if sources[path.name].count(old) != 1:
            raise SystemExit(f"mutation anchor gone: {args.mutation}")
        sources[path.name] = sources[path.name].replace(old, new)
    else:
        arms += [("dpr2", {"dpr": 2}), ("cost-fit", {"percent": None}), ("cost-200", {"percent": 200})]
    if args.arms:
        arms = [a for a in arms if a[0] in args.arms.split(",")]
    scratch = Path(tempfile.mkdtemp(prefix="writer-zoom-", dir=PROJECT / "build"))
    try:
        with common.browser_lock("check_writer_zoom"):
            pre = common.pre_run_checks()
            report["preRun"] = {k: pre[k] for k in ("refuse", "loadavg")}
            if pre["refuse"]:
                raise SystemExit(f"pre-run refused: {pre['refuse']}")
            pp.build_mirror(common.DIST, scratch / "m", {
                "e2-editor.html": common.inject(sources[HTML.name], [OBSERVER]).encode(),
                "e2-editor-app.js": sources[APP.name].encode()})
            with common.served(scratch / "m") as base:
                for browser in args.browsers.split(","):
                    for arm, config in arms:
                        if browser != "chrome" and (arm == "dpr2" or arm.startswith("cost")):
                            continue
                        record = {"browser": browser, "arm": arm, "base": base, "checks": []}
                        report["runs"].append(record)
                        run_one(record, raw, steps, out, config)
                        print(browser, arm, sum(c["pass"] for c in record["checks"]), "/", len(record["checks"]),
                              [c["id"] for c in record["checks"] if not c["pass"]], record.get("cost", ""),
                              (record.get("fatal") or "").strip().splitlines()[-1:] or "", file=sys.stderr, flush=True)
                        (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    checks = [c for r in report["runs"] for c in r["checks"]]
    fatal = [r for r in report["runs"] if r.get("fatal")]
    if args.mutation:
        clause = MUTATIONS[args.mutation][0]
        red = sorted({c["id"] for c in checks if not c["pass"]})
        report["verdict"] = "MUTATION_CAUGHT" if any(i.startswith(clause + "/") for i in red) else "MUTATION_MISSED"
        report["red"] = red
    else:
        report["verdict"] = "Z_HOLDS" if checks and all(c["pass"] for c in checks) and not fatal else "Z_RED"
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], report.get("red", ""), file=sys.stderr)
    return 0 if report["verdict"] in ("Z_HOLDS", "MUTATION_CAUGHT") else 1


if __name__ == "__main__":
    raise SystemExit(main())
