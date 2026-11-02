#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 S1 (finding 179): Shift+Up/Down/Home/End/Left/Right extend the selection on the product page.

On a mirror of dist/ with real keys.  What the engine reported is read at the Worker, not from the page.  Every check is
recorded and the run goes on past a red one.

  check_writer_shift_lines.py --out DIR [--browsers chrome,firefox] [--profile NAME]

--profile repoints the page the way build_cutover_page.py does; without it the live page is measured.  A new directory each
time: --out refuses an existing one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_writer_zoom as z  # noqa: E402
from check_writer_zoom import common, evaluate, pp, real  # noqa: E402

KEYS = ("ArrowUp", "ArrowDown", "Home", "End", "ArrowLeft", "ArrowRight")
WATCH = """<script>
(() => { const rec = window.__s = {toasts: [], selection: null, actions: []};
  addEventListener('DOMContentLoaded', () => { const t = document.querySelector('#toast');
    new MutationObserver(() => { if (t.textContent && t.classList.contains('bad')) rec.toasts.push(t.textContent); })
      .observe(t, {childList: true, characterData: true, subtree: true, attributes: true}); });
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) { super(url, options);
      this.addEventListener('message', ev => { const m = ev.data;
        const state = m?.kind === 'response' ? m.result?.state : (m?.kind === 'event' && m.event === 'editor-state') ? m : null;
        if (state?.selection) rec.selection = state.selection;
        if (m?.kind === 'response') { const row = rec.actions.find(r => r.id === m.requestId); if (row) { row.ok = m.ok; row.code = m.error?.code ?? null; } } }); }
    postMessage(m, ...rest) {
      if (m?.kind === 'request' && m.operation === 'editorActionV2')
        rec.actions.push({id: m.requestId, action: m.payload.action, extend: m.payload.extendSelection, ok: null, code: null});
      return super.postMessage(m, ...rest); } };
})();
</script>"""
READ = "(() => { const s = window.__s; return {toasts: s.toasts.length, last: s.toasts.at(-1) ?? null, selection: s.selection, action: s.actions.at(-1) ?? null, actions: s.actions.length}; })()"


def extent(selection):
    rects = (selection or {}).get("rectangles") or []
    return sum((r.get("width") or 0) * (r.get("height") or 0) for r in rects)


def settle(run):
    time.sleep(0.5)
    return run.wait(lambda n: n["requests"] == n["responses"], 20)


def place(run, s):
    """A caret inside a multi-line paragraph, not on its first line and not at a line end."""
    s = run.click_paper(s["doc"]["width"] * 0.3, 7485 + 830)
    settle(run)
    return s


def run_one(record, raw, out):
    session = None
    try:
        session = common.open_browser(record["browser"], (1400, 1000))
        record["version"] = getattr(session, "version", None)
        run = z.Run(session, record["browser"], record)
        s = run.open(raw)
        record["doc"] = s["doc"]
        for key in KEYS:
            s = place(run, run.state())
            before = evaluate(session, READ)
            if extent(before["selection"]) != 0:
                run.check(f"S1/{key}/starts-collapsed", False, before)
            real.key(session, record["browser"], key, ("shift",))
            settle(run)
            after = evaluate(session, READ)
            run.check(f"S1/{key}/no-red-toast", after["toasts"] == before["toasts"], {"last": after["last"]})
            run.check(f"S1/{key}/engine-answered-ok", after["actions"] == before["actions"] + 1 and after["action"]["ok"] is True
                      and after["action"]["extend"] is True, after["action"])
            run.check(f"S1/{key}/selection-is-a-range", extent(after["selection"]) > 0, after["selection"])
            real.key(session, record["browser"], "ArrowRight" if key in ("ArrowDown", "End", "ArrowRight") else "ArrowLeft")
            settle(run)
            done = evaluate(session, READ)
            run.check(f"S1/{key}/plain-key-collapses", extent(done["selection"]) == 0 and done["toasts"] == after["toasts"], done["selection"])
        s = place(run, run.state())
        real.key(session, record["browser"], "ArrowDown", ("shift",))
        settle(run)
        one = extent(evaluate(session, READ)["selection"])
        real.key(session, record["browser"], "ArrowDown", ("shift",))
        settle(run)
        two = extent(evaluate(session, READ)["selection"])
        run.check("S1/second-press-grows", two > one > 0, {"one": one, "two": two})
        (out / f"{record['browser']}-after.png").write_bytes(session.screenshot())
    except Exception:
        record["fatal"] = traceback.format_exc()
    finally:
        if session is not None:
            record["cleanup"] = common.close_browser(session)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--profile")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw = z.DOCUMENT.read_bytes()
    page = z.APP.read_text(encoding="utf-8")
    if args.profile:
        page = pp.repointed_page(page, args.profile, z.PROJECT / "dist/profiles" / args.profile / "sdk-manifest.json")[0]
    report = {"argv": sys.argv, "tool": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "profile": args.profile,
              "page": hashlib.sha256(page.encode()).hexdigest(), "document": hashlib.sha256(raw).hexdigest(), "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="shift-lines-", dir=z.PROJECT / "build"))
    try:
        with common.browser_lock("check_writer_shift_lines"):
            pre = common.pre_run_checks()
            report["preRun"] = {k: pre[k] for k in ("refuse", "loadavg")}
            if pre["refuse"]:
                raise SystemExit(f"pre-run refused: {pre['refuse']}")
            pp.build_mirror(common.DIST, scratch / "m", {
                "e2-editor.html": common.inject(z.HTML.read_text(encoding="utf-8"), [z.OBSERVER, WATCH]).encode(),
                "e2-editor-app.js": page.encode()})
            with common.served(scratch / "m") as base:
                for browser in args.browsers.split(","):
                    record = {"browser": browser, "base": base, "checks": []}
                    report["runs"].append(record)
                    run_one(record, raw, out)
                    print(browser, sum(c["pass"] for c in record["checks"]), "/", len(record["checks"]),
                          sorted({c["id"] for c in record["checks"] if not c["pass"]}),
                          (record.get("fatal") or "").strip().splitlines()[-1:] or "", file=sys.stderr, flush=True)
                    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    checks = [c for r in report["runs"] for c in r["checks"]]
    held = bool(checks) and all(c["pass"] for c in checks) and not any(r.get("fatal") for r in report["runs"])
    report["verdict"] = "S1_HOLDS" if held else "S1_RED"
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], file=sys.stderr)
    return 0 if held else 1


if __name__ == "__main__":
    raise SystemExit(main())
