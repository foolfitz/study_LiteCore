#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 P1: the four alignment buttons on the Writer page.

On a mirror of dist/ with real keys and a real pointer, on the N1 fixture.  Each arm places the caret or the selection, presses the
button, saves, and reads the ODT: the paragraphs the arm covers carry the alignment, no other paragraph moved.  Then Ctrl+Z, and the
saved document equals the one before the press.  Every check is recorded and the run goes on past a red one.

  check_writer_align.py --out DIR [--browsers chrome,firefox] [--profile NAME]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile
import io

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_writer_zoom as z  # noqa: E402
from check_writer_zoom import common, evaluate, pp, real  # noqa: E402
from check_writer_shift_lines import WATCH  # noqa: E402

FIXTURE = z.PROJECT.parent / "findings/evidence/demo-batch-3/native-writer-align/align-fixture.odt"
ALIGN = {"left": ("set-align-left", "left"), "center": ("set-align-center", "center"), "right": ("set-align-right", "right"),
         "justify": ("set-align-justify", "justify")}
# paragraph index (arrow-downs from the start), keys to shape the selection, paragraphs covered
ARMS = {"caret-plain": (1, [], [1]), "range-single": (1, [("End", ("shift",))], [1]),
        "range-cross": (1, [("ArrowDown", ("shift",)), ("ArrowDown", ("shift",))], [1, 2, 3]),
        "caret-heading": (2, [], [2]), "caret-list": (3, [], [3]), "caret-already-centred": (4, [], [4]),
        "caret-empty-mid": (5, [], [5]), "caret-empty-last": (7, [], [7])}
FO = "{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}text-align"
STYLE = "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}"
TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"


def aligns(raw: bytes) -> list:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    styles = {}
    for style in root.iter(STYLE + "style"):
        props = style.find(STYLE + "paragraph-properties")
        styles[style.get(STYLE + "name")] = props.get(FO) if props is not None else None
    return [styles.get(p.get(TEXT + "style-name")) for p in root.iter() if p.tag in (TEXT + "p", TEXT + "h")]


class Page(z.Run):
    def quiet(self):
        time.sleep(.45)
        return self.wait(lambda s: s["requests"] == s["responses"] and s["pill"] == "ready", 30)

    def key(self, name, mods=()):
        real.key(self.session, self.browser, name, mods)
        self.quiet()

    def save(self):
        before = self.state()["blobs"]
        self.press('[data-action="save"]')
        self.wait(lambda s: s["blobs"] > before and s["pill"] == "ready", 30)
        return base64.b64decode(evaluate(self.session, z.BLOB))

    def toasts(self):
        return evaluate(self.session, "window.__s.toasts.length")

    def place(self, paragraph):
        self.key("Home", ("ctrl",))
        for _ in range(paragraph):
            self.key("ArrowDown")


def run_one(record, raw, out):
    session = None
    try:
        session = common.open_browser(record["browser"], (1400, 1000))
        record["version"] = getattr(session, "version", None)
        page = Page(session, record["browser"], record)
        page.open(raw)
        page.click_paper(1500, 1500)
        page.quiet()
        base = aligns(page.save())
        page.check("setup/fixture-reads-as-written", len(base) == 8 and base[4] == "center" and base.count(None) == 7, base)
        offered = evaluate(session, "[...document.querySelectorAll('[data-action^=\"set-align-\"]')].map(b => [b.dataset.action, b.hidden])")
        page.check("setup/four-buttons-shown", len(offered) == 4 and not any(hidden for _, hidden in offered), offered)
        for arm, (paragraph, shape, covered) in ARMS.items():
            for name, (action, value) in ALIGN.items():
                cell = f"P1/{arm}/{name}"
                toasts = page.toasts()
                page.place(paragraph)
                for key, mods in shape:
                    page.key(key, mods)
                page.press(f'[data-action="{action}"]')
                page.quiet()
                saved = aligns(page.save())
                expected = [value if i in covered else was for i, was in enumerate(base)]
                page.check(cell + "/saved", saved == expected, {"saved": saved, "expected": expected})
                page.check(cell + "/no-red-toast", page.toasts() == toasts, evaluate(session, "window.__s.toasts.at(-1) ?? null"))
                if saved != base:
                    page.key("z", ("ctrl",))
                after = aligns(page.save())
                page.check(cell + "/undo-one-step", after == base, after)
                if after != base:  # do not let one red colour every later cell
                    page.open(raw)
                    page.click_paper(1500, 1500)
                    page.quiet()
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
    raw = FIXTURE.read_bytes()
    page = z.APP.read_text(encoding="utf-8")
    if args.profile:
        page = pp.repointed_page(page, args.profile, z.PROJECT / "dist/profiles" / args.profile / "sdk-manifest.json")[0]
    report = {"argv": sys.argv, "tool": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "profile": args.profile,
              "page": hashlib.sha256(page.encode()).hexdigest(), "document": hashlib.sha256(raw).hexdigest(), "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="writer-align-", dir=z.PROJECT / "build"))
    try:
        with common.browser_lock("check_writer_align"):
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
    report["verdict"] = "P1_HOLDS" if held else "P1_RED"
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], file=sys.stderr)
    return 0 if held else 1


if __name__ == "__main__":
    raise SystemExit(main())
