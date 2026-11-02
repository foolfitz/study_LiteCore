#!/usr/bin/env python3
"""SPEC-P-demo-batch-4 section 2: can an applied heading or list be taken off, on the product page?

The page on dist/ (a mirror), real keys and a real pointer, on the align fixture.  Each arm starts from the fixture, presses its
buttons in order, saves after each press and reads the paragraph's shape from the ODT: tag, outline level, whether it sits in a list,
and of which kind.  A read of what the file holds, not of what the page says.  Records, no verdict: this answers a question.

  python3 heading_list_cancel.py OUT [--browsers chrome,firefox]
"""
import argparse
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "wasm_sdk_probe/tools"))
import check_writer_align as a  # noqa: E402
from check_writer_align import common, evaluate, pp, z  # noqa: E402

TEXT = a.TEXT
HEAD, BODY, BULLET, NUMBER, NONE = ("set-paragraph-heading", "set-paragraph-body", "set-list-unordered", "set-list-ordered", "set-list-none")
# name: (paragraph index, presses)
ARMS = {
    "heading-pressed-again": (1, [HEAD, HEAD]),
    "heading-then-body": (1, [HEAD, BODY]),
    "bullet-pressed-again": (1, [BULLET, BULLET]),
    "bullet-then-remove": (1, [BULLET, NONE]),
    "number-pressed-again": (1, [NUMBER, NUMBER]),
    "number-then-remove": (1, [NUMBER, NONE]),
    "bullet-then-number": (1, [BULLET, NUMBER]),
    "existing-heading-then-body": (2, [BODY]),
    "existing-list-then-remove": (3, [NONE]),
    "heading-and-bullet-then-both-off": (1, [HEAD, BULLET, NONE, BODY]),
}
VISIBLE = """[...document.querySelectorAll('#toolbar [data-action]')].filter(b => /set-paragraph|set-list/.test(b.dataset.action)).map(b => {
  const r = b.getBoundingClientRect(), s = getComputedStyle(b);
  return {action: b.dataset.action, tip: b.dataset.tip, shown: r.width > 0 && s.display !== 'none' && s.visibility !== 'hidden',
          inWindow: r.right <= innerWidth, pressed: b.getAttribute('aria-pressed')}; })"""


def shape(raw, index):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    parents = {child: parent for parent in root.iter() for child in parent}
    paragraphs = [p for p in root.iter() if p.tag in (TEXT + "p", TEXT + "h")]
    p, list_node, walk = paragraphs[index], None, paragraphs[index]
    while walk in parents:
        walk = parents[walk]
        if walk.tag == TEXT + "list":
            list_node = walk
            break
    return {"text": "".join(p.itertext()), "tag": p.tag.split("}")[1], "level": p.get(TEXT + "outline-level"),
            "style": p.get(TEXT + "style-name"), "inList": list_node is not None,
            "listStyle": list_node.get(TEXT + "style-name") if list_node is not None else None}


def run_browser(browser, base, raw, out):
    record = {"browser": browser, "arms": {}}
    session = common.open_browser(browser, (1400, 1000))
    try:
        record["version"] = getattr(session, "version", None)
        for name, (paragraph, presses) in ARMS.items():
            page = a.Page(session, browser, {"base": base, "checks": []})
            a.fresh(page, raw)
            if name == "heading-pressed-again":
                record["buttons"] = evaluate(session, VISIBLE)
            page.place(paragraph)
            steps = [{"press": None, "shape": shape(page.save(), paragraph)}]
            for action in presses:
                toasts = page.toasts()
                page.press(f'[data-action="{action}"]')
                page.quiet()
                steps.append({"press": action, "shape": shape(page.save(), paragraph), "redToast": page.toasts() != toasts,
                              "lastToast": evaluate(session, "window.__s.toasts.at(-1) ?? null")})
            record["arms"][name] = steps
            print(browser, name, [(s["press"], s["shape"]["tag"], s["shape"]["level"], s["shape"]["inList"]) for s in steps], flush=True)
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
    raw = a.FIXTURE.read_bytes()
    report = {"page": "dist/e2-editor-app.js", "profileFrom": "the page's own worker URL", "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="heading-list-cancel-", dir=z.PROJECT / "build"))
    try:
        with common.browser_lock("heading_list_cancel"):
            html = common.inject((common.DIST / "e2-editor.html").read_text(encoding="utf-8"), [z.OBSERVER, a.WATCH]).encode()
            pp.build_mirror(common.DIST, scratch / "m", {"e2-editor.html": html})
            with common.served(scratch / "m") as base:
                for browser in args.browsers.split(","):
                    report["runs"].append(run_browser(browser, base, raw, out))
                    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
