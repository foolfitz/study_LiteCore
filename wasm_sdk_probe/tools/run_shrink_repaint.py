#!/usr/bin/env python3
"""Finding 118: a document that loses a page, on the product page.  Red case and verification.

Written 2026-10-08.  Not a criterion run.  The shape (fable's ruling on 117, section 3):
grow the document to two pages, then shrink it back to one, and read what the page did.
v8 refuses a boundary delete, so the shrink is the page's own Undo; the subject is the
repaint after the size change, not how the size changed.

  1. open FIXTURE: R0 run 4's `undo-limit-105.odt` cut to its first 52 paragraphs ("S01"
     and 51 blank).  On v18, M2-4 measured 53 such paragraphs at two pages and 52 at one
     (the size reply changed at press 55 of 105, `findings/evidence/v18/diag-117/`);
  2. the toolbar's paragraph break (caret where the open left it), then quiet;
  3. the toolbar's Undo, then quiet;
  4. the merge runner's instrumented observer logged every paint (request rectangle,
     canvas rows, reply height, `documentSizeChanged`, painted fraction) and every toast.

Red (finding 118 present): a TILE_NOT_PAINTED toast after the Undo, and paints after it
still asking for the one-page height into the two-page canvas's rows.  Green: no toast,
and the last paint's rows are the one-page canvas's (about half the two-page rows).

  run_shrink_repaint.py --browser chrome --profile e2-editor-v8 --page dist --out R.json
  run_shrink_repaint.py --browser chrome --profile e2-editor-v18 --page cutover --out R.json

`--page dist` serves dist/'s page as it is (it must already point at --profile: that is
the shipped page); `--page cutover` serves the cutover source repointed at --profile, as
the merge runner does.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_e2_c_product_path as pp  # noqa: E402
import run_merge_wasm_shakedown as mw  # noqa: E402

HERE = pp.PROJECT
SOURCE = HERE / "test-docs/merge/odt/undo-limit-105.odt"
SOURCE_SHA = "09b5ced0e619f825"
KEEP = 52
EMPTY = b'<text:p text:style-name="Standard"/>'
CLICK = "(() => {{ const b = document.querySelector('[data-action=\"{0}\"]'); if (!b || b.disabled) return false; b.click(); return true; }})()"


def fixture(keep: int = KEEP) -> bytes:
    """The first `keep` paragraphs of SOURCE, every other part byte-identical, zip entries in order."""
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest()[:16] != SOURCE_SHA:
        raise SystemExit(f"{SOURCE} is not the fixture M2-4 ran")
    zin = zipfile.ZipFile(io.BytesIO(raw))
    content = zin.read("content.xml")
    empties = content.count(EMPTY)
    if content.count(b"<text:p") != empties + 1 or empties < keep - 1:
        raise SystemExit("the fixture is not 'S01' followed by empty paragraphs")
    head, tail = content.split(EMPTY, 1)[0], content.rsplit(EMPTY, 1)[1]
    cut = head + EMPTY * (keep - 1) + tail
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zout:
        for info in zin.infolist():
            data = cut if info.filename == "content.xml" else zin.read(info.filename)
            zout.writestr(info, data, compress_type=info.compress_type)
    return out.getvalue()


def wait_paint(session, height: int, limit: float = 30) -> tuple[list, bool]:
    """Drain until a successful paint reply reports `height`; everything drained is returned."""
    seen, deadline = [], time.monotonic() + limit
    while time.monotonic() < deadline:
        seen += mw.drain(session)
        if any(e.get("k") == "p" and e.get("ok") and e.get("docH") == height for e in seen):
            return seen, True
        time.sleep(0.2)
    return seen, False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--page", choices=("dist", "cutover"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--keep", type=int, default=KEEP,
                    help="paragraphs kept; 107 = the uncut M2-4 fixture, the positive control for the open path")
    args = ap.parse_args()
    root = HERE / "dist"
    manifest = root / "profiles" / args.profile / "sdk-manifest.json"
    if args.page == "cutover":
        lagging = pp.shell_lagging_source(root)
        if lagging:
            raise SystemExit(f"served from dist/ but not their source: {lagging}")
        page, _, wasm = pp.repointed_page(pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8"),
                                          args.profile, manifest)
    else:
        page = (root / "e2-editor-app.js").read_text(encoding="utf-8")
        if f'"./profiles/{args.profile}/sdk-worker.js"' not in page:
            raise SystemExit(f"dist's page does not point at {args.profile}")
        wasm = (json.loads(manifest.read_text()).get("editorContract") or {}).get("wasmSha256") or ""
    html = (root / "e2-editor.html").read_text(encoding="utf-8")
    anchor = '<script type="module" src="./e2-editor-app.js"></script>'
    if html.count(anchor) != 1:
        raise SystemExit("the page's module script is not where the instrument expects it")
    instrumented = html.replace(anchor, mw.OBSERVER + anchor)
    doc = fixture(args.keep)
    mirror = Path(tempfile.mkdtemp(prefix="shrink-")) / "root"
    pp.build_mirror(root, mirror, {"e2-editor-app.js": page.encode("utf-8"),
                                   "e2-editor.html": instrumented.encode("utf-8")})
    # NOT as an override: `build_mirror` writes an override only where it meets that
    # path in dist/, so a new file passed there is silently never written.  It was
    # (2026-10-08, first P1/P2): the fetch got serve.py's 404 page and the engine
    # opened that HTML -- a 37,325-twip-wide web layout on v8 and v18 alike.
    target = mirror / "shrink-52.odt"
    if target.exists() or mirror.is_symlink():
        raise SystemExit(f"refusing to write {target}")
    target.write_bytes(doc)
    report = {"finding": 118, "browser": args.browser, "profile": args.profile, "page": args.page,
              "pageSha256": hashlib.sha256(page.encode()).hexdigest(), "wasm": wasm[:16],
              "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
              "observerRunner": hashlib.sha256(Path(mw.__file__).read_bytes()).hexdigest()[:16],
              "fixtureSha256": hashlib.sha256(doc).hexdigest(), "paragraphs": args.keep,
              "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port),
                               "--root", str(mirror)], cwd=HERE,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = (pp.ChromeSession if args.browser == "chrome" else pp.FirefoxSession)("cold")
        pp.navigate(session, base)
        report["boot"] = pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        report["shims"] = pp.evaluate(session, pp.INSTALL)
        report["open"] = mw.open_fixture(session, "./shrink-52.odt", "shrink-52.odt")
        report["opened"], report["openedAtOnePage"] = wait_paint(session, 17406)
        mw.quiet(session)
        report["sizeOpened"] = mw.obs(session).get("size")
        pp.evaluate(session, pp.CLEAR_TOASTS)
        report["breakClicked"] = pp.evaluate(session, CLICK.format("insert-paragraph-break"))
        report["grown"], report["grewToTwoPages"] = wait_paint(session, 34528)
        report["grownQuiet"] = mw.quiet(session)
        report["grown"] += mw.drain(session)
        report["sizeGrown"] = mw.obs(session).get("size")
        report["undoClicked"] = pp.evaluate(session, CLICK.format("undo"))
        report["shrunk"], report["shrankToOnePage"] = wait_paint(session, 17406)
        time.sleep(1.0)
        report["shrunkQuiet"] = mw.quiet(session)
        report["shrunk"] += mw.drain(session)
        report["sizeShrunk"] = mw.obs(session).get("size")
        report["toasts"] = pp.evaluate(session, pp.READ_TOASTS)
    except Exception as error:  # noqa: BLE001 -- recorded, never read as a verdict
        report["error"] = f"{type(error).__name__}: {error}"
    finally:
        report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if session is not None:
            try:
                session.close()
            except Exception as error:  # noqa: BLE001
                report["closeError"] = f"{type(error).__name__}: {error}"
        server.terminate()
        server.wait(timeout=10)
    paints = lambda key: [{k: e.get(k) for k in ("ok", "h", "rows", "docH", "changed", "painted")}
                          for e in report.get(key) or [] if e.get("k") == "p" and e.get("ok")]
    grown, shrunk = paints("grown"), paints("shrunk")
    two_page_rows = next((p["rows"] for p in reversed(grown) if p["docH"] == 34528 and not p["changed"]), None)
    last = shrunk[-1] if shrunk else None
    unpainted = any(re.search("TILE_NOT_PAINTED", t or "") for t in report.get("toasts") or [])
    report["summary"] = {"grewToTwoPages": report.get("grewToTwoPages"),
                         "shrankToOnePage": report.get("shrankToOnePage"),
                         "twoPageRows": two_page_rows, "lastPaintAfterShrink": last,
                         "tileNotPaintedToast": unpainted,
                         "staleCanvasAfterShrink": bool(last and two_page_rows and last["rows"] == two_page_rows)}
    s = report["summary"]
    measured = s["grewToTwoPages"] and s["shrankToOnePage"] and two_page_rows and last and "error" not in report
    s["verdict"] = ("NOT MEASURED" if not measured else
                    "RED (118 present)" if (unpainted or s["staleCanvasAfterShrink"]) else "GREEN")
    args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    print(json.dumps(s, ensure_ascii=False))
    print("VERDICT " + s["verdict"])
    return {"GREEN": 0, "RED (118 present)": 1}.get(s["verdict"], 3)


if __name__ == "__main__":
    sys.exit(main())
