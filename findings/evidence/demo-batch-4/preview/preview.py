#!/usr/bin/env python3
"""SPEC-P-demo-batch-4: the page's new controls before the link.  A mirror of dist/ with the live page and shell sources on the v31 engine,
with the page's one `offers` test for the six toggles replaced by true.  (A doctored manifest will not do: the worker pushes each declared
action's mask to the binary, and v31 refuses ids it does not have.)  So the controls show and the state reads are real, and a toggle
cannot be pressed: this measures T9 (what the toolbar shows) and T10 (the menu), and takes pictures.  Nothing here is evidence about the
actions.

  python3 preview.py OUT [--browsers chrome,firefox]
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "wasm_sdk_probe/tools"))
import check_writer_toggle as t  # noqa: E402
from check_writer_toggle import common, evaluate, pp, z  # noqa: E402
from check_writer_shift_lines import WATCH  # noqa: E402

SHELL = ["narrow-editor-v2-client.js", "narrow-editor-v2-session.js", "paragraph-editor-client.js", "paragraph-editor-session.js"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", type=Path)
    parser.add_argument("--browsers", default="chrome,firefox")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    app = z.APP.read_text(encoding="utf-8")
    gate = "EDITOR_TOGGLE_ACTIONS.every((action) => session?.offers?.(action) === true)"
    assert app.count(gate) == 1
    overrides = {"e2-editor.html": common.inject(z.HTML.read_text(encoding="utf-8"), [z.OBSERVER, WATCH]).encode(),
                 "e2-editor-app.js": app.replace(gate, "Boolean(session?.document)").encode()}
    # run-02 was red on one cell, a body paragraph reached from another body paragraph: no broadcast, and the arrow key's reply went through
    # v31's projection, which drops the three fields.  That is delta item 2 of the v32 worker, so the v32 worker goes in here.
    overrides["profiles/e2-editor-v31/sdk-worker.js"] = (z.PROJECT / "sdk/v32-paragraph-read-worker.js").read_bytes()
    for name in SHELL:
        overrides[f"editor-shell-v2/{name}"] = (z.PROJECT / "editor-shell-v2" / name).read_bytes()
    report = {"runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="toggle-preview-", dir=z.PROJECT / "build"))
    raw = t.LEVELS.read_bytes()
    try:
        with common.browser_lock("toggle_preview"):
            pp.build_mirror(common.DIST, scratch / "m", overrides)
            with common.served(scratch / "m") as base:
                for browser in args.browsers.split(","):
                    record = {"browser": browser, "base": base, "checks": []}
                    report["runs"].append(record)
                    session = common.open_browser(browser, (1400, 1000))
                    try:
                        record["version"] = getattr(session, "version", None)
                        page = t.Page(session, browser, record)
                        page.open(raw)
                        page.click_paper(1500, 1500)
                        page.quiet()
                        t.t9(page, raw)
                        t.t10(page, raw)
                        t.fresh(page, raw)
                        page.place(t.H3)
                        page.press("#heading-menu-button")
                        (out / f"{browser}-menu.png").write_bytes(session.screenshot())
                    finally:
                        record["cleanup"] = common.close_browser(session)
                    print(browser, sum(c["pass"] for c in record["checks"]), "/", len(record["checks"]),
                          [(c["id"], c["actual"]) for c in record["checks"] if not c["pass"]][:8], flush=True)
                    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
