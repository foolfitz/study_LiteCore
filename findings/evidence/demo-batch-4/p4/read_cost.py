#!/usr/bin/env python3
"""The bridge's cost on Wasm, which the runbook's step 6 asks to read.  Native is 8 ms for 100 paragraphs and 329 ms for 1,000, worse than linear
(native-caret-read/large), and two reads go with each press.  So the worst press the page allows is a selection of 500 paragraphs.

For n in 100, 250, 500: a document of n paragraphs cut from the long fixture, Ctrl+A, press bullet, press bullet again, heading 2 from the menu, each
by the real pointer; the page's own latency label, the time until the page is quiet, and the state.  A caret arm on the same document: one paragraph.
Not P4 and not a gate: the number the runbook wants a person to read.
  read_cost.py --out DIR [--browsers chrome,firefox]
"""
import argparse
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "wasm_sdk_probe/tools"))
import check_writer_toggle as t  # noqa: E402
from check_writer_toggle import BULLET, common, evaluate  # noqa: E402

LABEL = "document.querySelector('#s-latency')?.textContent ?? ''"


def cut(n):
    source = zipfile.ZipFile(t.EVIDENCE / "long-fixture.odt")
    content = source.read("content.xml").decode()
    spans = list(re.finditer(r"<text:p\b.*?</text:p>", content, re.S))
    kept = content[:spans[0].start()] + "".join(m.group(0) for m in spans[:n]) + content[spans[-1].end():]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for info in source.infolist():
            data = kept.encode() if info.filename == "content.xml" else source.read(info.filename)
            z.writestr(zipfile.ZipInfo(info.filename, (2026, 11, 3, 0, 0, 0)), data, zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED)
    return out.getvalue()


def timed(page, name, go, rows):
    start = time.monotonic()
    go()
    page.quiet()
    rows.append({"press": name, "label": evaluate(page.session, LABEL), "untilQuietS": round(time.monotonic() - start - .45, 3),
                 "pill": evaluate(page.session, "document.querySelector('#state-pill').dataset.state")})
    print(json.dumps(rows[-1], ensure_ascii=False), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--browsers", default="chrome,firefox")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    page_js = t.pp.repointed_page(t.z.APP.read_text(encoding="utf-8"), "e2-editor-v32", t.z.PROJECT / "dist/profiles/e2-editor-v32/sdk-manifest.json")[0]
    html = t.z.HTML.read_text(encoding="utf-8")
    scratch = Path(tempfile.mkdtemp(prefix="read-cost-", dir=t.z.PROJECT / "build"))
    result = []
    try:
        with common.browser_lock("check_writer_toggle"):
            t.pp.build_mirror(common.DIST, scratch / "m", {"e2-editor.html": common.inject(html, [t.z.OBSERVER, t.WATCH]).encode(), "e2-editor-app.js": page_js.encode()})
            with common.served(scratch / "m") as base:
                for browser in args.browsers.split(","):
                    session = common.open_browser(browser, (1400, 1000))
                    try:
                        page = t.Page(session, browser, {"browser": browser, "base": base, "checks": []})
                        for n in (100, 250, 500):
                            rows = []
                            print(browser, n, flush=True)
                            t.fresh(page, cut(n))
                            timed(page, "caret-bullet", lambda: page.press(BULLET), rows)
                            timed(page, "caret-bullet-off", lambda: page.press(BULLET), rows)
                            page.key("a", ("ctrl",))
                            timed(page, "all-bullet", lambda: page.press(BULLET), rows)
                            timed(page, "all-bullet-off", lambda: page.press(BULLET), rows)
                            timed(page, "all-h2", lambda: page.level("toggle-heading-2"), rows)
                            result.append({"browser": browser, "paragraphs": n, "rows": rows})
                    finally:
                        common.close_browser(session)
                    (args.out / "read-cost.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


main()
