#!/usr/bin/env python3
"""Diagnostic, not P4.  P4 run-01's T12 fell over on `page.save()`: the first save made no Blob within the wait.  Is that the press, or does this
fixture not save at all?  Arms, each on a fresh page of the image fixture: `control` saves without a press; `caret-bullet` is T12's first steps;
`plain-paragraph` presses in paragraph 0, which holds no frame.  Each arm records the page's own state, toast and worker traffic.
Added after the first run: the fixture's PNG turned out to have a bad IDAT CRC, so --fixture and --profile separate "this PNG" from "any picture" and
"v32" from "already so".
  diag_t12.py --out DIR [--browser chrome] [--profile e2-editor-v32] [--fixture image-fixture.odt]
"""
import argparse
import base64
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "wasm_sdk_probe/tools"))
import check_writer_toggle as t  # noqa: E402
from check_writer_toggle import BULLET, common, evaluate, a  # noqa: E402

STATE = """(() => { const q = s => document.querySelector(s), z = window.__z, b = q('[data-action="save"]');
  return {pill: q('#state-pill')?.dataset.state, pillText: q('#state-pill')?.textContent, latency: q('#s-latency')?.textContent, toast: q('#toast')?.textContent,
    notice: q('#notice')?.dataset.show, noticeText: q('#notice')?.textContent?.slice(0, 200), blobs: z.blobs.length, requests: z.requests.length, responses: z.responses,
    saveDisabled: b?.disabled ?? null, saveTitle: b?.title ?? null, tail: z.requests.slice(-6).map(r => r.op + (r.action ? ':' + r.action : ''))}; })()"""


def snap(page, name, rows):
    row = dict(evaluate(page.session, STATE), at=name, t=round(time.time(), 2))
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False)[:600], flush=True)


def arm(page, raw, name, before_save):
    rows = []
    t.fresh(page, raw)
    snap(page, "opened", rows)
    before_save(page)
    snap(page, "pressed", rows)
    page.press('[data-action="save"]')
    deadline = time.time() + 45
    while time.time() < deadline:
        s = page.state()
        if s["blobs"] > 0 and s["pill"] == "ready":
            break
        time.sleep(1)
    snap(page, "after-save-wait", rows)
    saved = None
    if rows[-1]["blobs"]:
        saved = t.shape(base64.b64decode(evaluate(page.session, t.z.BLOB)))[:3]
    return {"arm": name, "rows": rows, "saved": saved}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--browser", default="chrome")
    p.add_argument("--profile", default="e2-editor-v32")
    p.add_argument("--fixture", default="image-fixture.odt")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    raw = (t.EVIDENCE / args.fixture).read_bytes()
    page_js = t.pp.repointed_page(t.z.APP.read_text(encoding="utf-8"), args.profile, t.z.PROJECT / "dist/profiles" / args.profile / "sdk-manifest.json")[0]
    html = t.z.HTML.read_text(encoding="utf-8")
    scratch = Path(tempfile.mkdtemp(prefix="diag-t12-", dir=t.z.PROJECT / "build"))
    try:
        with common.browser_lock("check_writer_toggle"):
            t.pp.build_mirror(common.DIST, scratch / "m", {"e2-editor.html": common.inject(html, [t.z.OBSERVER, t.WATCH]).encode(), "e2-editor-app.js": page_js.encode()})
            with common.served(scratch / "m") as base:
                session = common.open_browser(args.browser, (1400, 1000))
                try:
                    page = t.Page(session, args.browser, {"browser": args.browser, "base": base, "checks": []})

                    def press(paragraph):
                        def go(pg):
                            pg.place(paragraph)
                            pg.press(BULLET)
                            pg.quiet()
                        return go
                    out = [arm(page, raw, "control", lambda pg: None), arm(page, raw, "plain-paragraph", press(0)), arm(page, raw, "caret-bullet", press(1))]
                    (args.out / "diag.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                finally:
                    common.close_browser(session)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


main()
