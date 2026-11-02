#!/usr/bin/env python3
"""SPEC-P-demo-batch-4: what the shipped page does on the two range shapes N3 points at.  The page on dist/ (e2-editor-v31), real keys and a
real pointer, the levels fixture.  A: three characters selected at a paragraph's start, press the heading button, save: is there a frame?
B: a selection from inside one paragraph across the next, press the heading button: what does the page say, what does the file hold?
Records, no verdict: this is the red side of T6.

  python3 before_v31.py OUT [--browsers chrome,firefox]
"""
import argparse
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "wasm_sdk_probe/tools"))
import check_writer_align as a  # noqa: E402
from check_writer_align import common, evaluate, pp, z  # noqa: E402
import check_writer_toggle as t  # noqa: E402
from check_writer_shift_lines import WATCH  # noqa: E402

HEAD = '[data-action="set-paragraph-heading"]'


def run_browser(browser, base, raw, out):
    record = {"browser": browser}
    session = common.open_browser(browser, (1400, 1000))
    try:
        record["version"] = getattr(session, "version", None)
        page = a.Page(session, browser, {"base": base, "checks": []})
        def state():
            return {"pill": evaluate(session, "document.querySelector('#state-pill').dataset.state"), "toast": evaluate(session, "document.querySelector('#toast').textContent"),
                    "redToasts": evaluate(session, "window.__s.toasts"), "actions": evaluate(session, "window.__s.actions.slice(-2)"),
                    "notice": evaluate(session, "document.querySelector('#notice').textContent"), "latency": evaluate(session, "document.querySelector('#s-latency')?.textContent ?? null")}

        def attempt(name, letter):
            result = state()
            try:
                saved = page.save()
                (out / f"{browser}-{letter}.odt").write_bytes(saved)
                result.update(frames=t.frames(saved), paragraphs=t.shape(saved)[:3])
            except Exception as error:
                result["saveFailed"] = repr(error)[:160]
            (out / f"{browser}-{letter}.png").write_bytes(session.screenshot())
            record[name] = result

        a.fresh(page, raw)
        page.place(t.BODY2)
        page.key("Home")
        for _ in range(3):
            page.key("ArrowRight", ("shift",))
        page.press(HEAD)
        page.quiet()
        attempt("leadingSelection", "a")
        a.fresh(page, raw)
        page.place(t.BODY)
        page.key("Home")
        page.key("ArrowRight")
        page.key("ArrowRight")
        page.key("ArrowDown", ("shift",))
        page.press(HEAD)
        page.quiet()
        attempt("fromInside", "b")
    finally:
        record["cleanup"] = common.close_browser(session)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", type=Path)
    parser.add_argument("--browsers", default="chrome,firefox")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw = t.LEVELS.read_bytes()
    report = {"page": "dist/e2-editor.html", "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="before-v31-", dir=z.PROJECT / "build"))
    try:
        with common.browser_lock("before_v31"):
            html = common.inject((common.DIST / "e2-editor.html").read_text(encoding="utf-8"), [z.OBSERVER, WATCH]).encode()
            pp.build_mirror(common.DIST, scratch / "m", {"e2-editor.html": html})
            with common.served(scratch / "m") as base:
                for browser in args.browsers.split(","):
                    run = run_browser(browser, base, raw, out)
                    report["runs"].append(run)
                    print(json.dumps(run, ensure_ascii=False)[:1400], flush=True)
                    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
