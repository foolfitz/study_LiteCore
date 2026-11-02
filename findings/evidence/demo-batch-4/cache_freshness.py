#!/usr/bin/env python3
"""SPEC-P-demo-batch-4 section 4: do listBullet, listNumber and paragraphStyle follow the caret on today's engine?

Finding 021 measured them stale on WASM (2 of 10 fresh) on an older engine; the main loop has not been measured.  The page on dist/,
real keys, the levels fixture.  Each step moves one paragraph with a real arrow key and reads the raw `format` the worker posts with
editor-state, immediately and until `settleMs`, against what the fixture holds at that paragraph.  Observations, no verdict.

  python3 cache_freshness.py OUT [--browsers chrome,firefox] [--rounds 3]
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "wasm_sdk_probe/tools"))
import check_writer_align as a  # noqa: E402
from check_writer_align import common, evaluate, pp, real, z  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixture/levels-fixture.odt"
# arrow-downs from the start: expected (list, level)
PARAGRAPHS = [("none", 0), ("none", 0), ("none", 1), ("none", 2), ("none", 3), ("none", 4), ("ul", 0), ("ul", 0), ("ol", 0),
              ("none", 0), ("none", 0), ("none", 0), ("none", 0)]
WATCH = """<script>
(() => { const rec = window.__f = {format: null, stale: null, at: 0, events: 0};
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) { super(url, options);
      this.addEventListener('message', ev => { const m = ev.data;
        if (m?.kind === 'event' && m.event === 'editor-state' && m.format) {
          rec.format = m.format; rec.stale = m.formatStale ?? m.format?.formatStale ?? null; rec.at = performance.now(); rec.events += 1; } }); }
  };
})();
</script>"""
READ = "({format: window.__f.format, stale: window.__f.stale, at: window.__f.at, events: window.__f.events, now: performance.now()})"


def expected_reading(f, want):
    list_kind, level = want
    if not f:
        return False
    bullet, number, style = f.get("listBullet"), f.get("listNumber"), f.get("paragraphStyle")
    # run-01 read listNumber true on every heading: SelectionHasNumber counts the outline rule (ednumber.cxx:148).  So listNumber says
    # nothing on a heading, and a reading has to be taken with paragraphStyle.
    if (list_kind == "ul") != (bullet is True) or (not level and (list_kind == "ol") != (number is True)):
        return False
    return (style == f"Heading {level}") if level else not str(style or "").startswith("Heading")


def run_browser(browser, base, raw, rounds, settle):
    record = {"browser": browser, "steps": []}
    session = common.open_browser(browser, (1400, 1000))
    try:
        record["version"] = getattr(session, "version", None)
        page = a.Page(session, browser, {"base": base, "checks": []})
        a.fresh(page, raw)
        for round_number in range(rounds):
            for direction in ("down", "up"):
                page.key("Home", ("ctrl",)) if direction == "down" else page.key("End", ("ctrl",))
                walk = list(range(1, len(PARAGRAPHS))) if direction == "down" else list(range(len(PARAGRAPHS) - 2, -1, -1))
                for index in walk:
                    real.key(session, browser, "ArrowDown" if direction == "down" else "ArrowUp", ())
                    start = time.monotonic()
                    first = None
                    while time.monotonic() - start < settle:
                        r = evaluate(session, READ)
                        if expected_reading(r["format"], PARAGRAPHS[index]):
                            first = round(time.monotonic() - start, 3)
                            break
                        time.sleep(0.03)
                    r = evaluate(session, READ)
                    f = r["format"] or {}
                    record["steps"].append({"round": round_number, "direction": direction, "paragraph": index, "want": PARAGRAPHS[index],
                                            "freshAfterS": first, "listBullet": f.get("listBullet"), "listNumber": f.get("listNumber"),
                                            "paragraphStyle": f.get("paragraphStyle"), "formatStale": r["stale"]})
                    page.quiet()
    finally:
        record["cleanup"] = common.close_browser(session)
    steps = record["steps"]
    record["summary"] = {"steps": len(steps), "fresh": sum(s["freshAfterS"] is not None for s in steps),
                         "maxFreshS": max([s["freshAfterS"] for s in steps if s["freshAfterS"] is not None] or [None]),
                         "staleWrong": [s for s in steps if s["freshAfterS"] is None][:12]}
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", type=Path)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--settle", type=float, default=3.0)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw = FIXTURE.read_bytes()
    report = {"page": "dist/e2-editor.html", "fixture": str(FIXTURE.name), "settleS": args.settle, "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="cache-freshness-", dir=z.PROJECT / "build"))
    try:
        with common.browser_lock("cache_freshness"):
            html = common.inject((common.DIST / "e2-editor.html").read_text(encoding="utf-8"), [z.OBSERVER, a.WATCH, WATCH]).encode()
            pp.build_mirror(common.DIST, scratch / "m", {"e2-editor.html": html})
            with common.served(scratch / "m") as base:
                for browser in args.browsers.split(","):
                    run = run_browser(browser, base, raw, args.rounds, args.settle)
                    report["runs"].append(run)
                    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
                    print(browser, json.dumps(run["summary"], ensure_ascii=False)[:1200], flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
