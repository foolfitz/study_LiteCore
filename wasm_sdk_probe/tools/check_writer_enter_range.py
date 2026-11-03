#!/usr/bin/env python3
"""SPEC-P-demo-batch-5 P5: Enter over a selection, and the sentence for an empty copy.

On a mirror of dist/ with real keys and a real pointer.  The saved ODT is the answer.  The main criterion is measured, not typed: on every selection shape,
select + Enter + q must save the same document as select + Delete + Enter + q, and that control must differ from the document it started from.

  E1  the shapes, Enter.    E2  the shapes, Shift+Enter, a text:line-break in the file.
  E3  a caret: one insert-paragraph-break, no delete-selection.
  E4  a selection: delete-selection then insert-paragraph-break, with q 10 ms behind Enter landing as it does when it waits.
  E5  Ctrl+Z, at most twice, is back at the document (`L-enter-range-two-undos`).
  E6  every arm ends ready with no red toast.
  E7  copy on a caret and over a frame: a sentence, no code, the document unchanged.

--page-rev reads the page from a git revision: run it on generation 87's page and E1 must go red.  That is the tool's red case, a real old page.

  check_writer_enter_range.py --out DIR [--browsers chrome,firefox] [--profile NAME] [--page-rev REV] [--only E1,E3]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from types import SimpleNamespace
import zipfile
import io

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_writer_toggle as t  # noqa: E402
from check_writer_toggle import BODY, BODY2, H1, ITEM, Page, body, common, evaluate, pp, real, shape, z  # noqa: E402
import diag_v21_dirty_move as dirty  # noqa: E402

KEYS = """<script>
(() => { window.__keys = []; addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === 'q') window.__keys.push([e.key, performance.now()]); }, true); })();
</script>"""
EVIDENCE = t.EVIDENCE
IMAGE = EVIDENCE / "image-valid-fixture.odt"
PILL = "document.querySelector('#state-pill').dataset.state"
RED = "(() => { const t = document.querySelector('#toast'); return t?.classList.contains('bad') || t?.classList.contains('error') ? t.textContent : null; })()"
TOAST = "document.querySelector('#toast')?.textContent ?? ''"
SENTENCE = "沒有可複製的文字"


def actions(page, mark):
    return evaluate(page.session, f"window.__z.requests.slice({mark}).filter(r => r.action).map(r => r.action)")


def mark_of(page):
    return evaluate(page.session, "window.__z.requests.length")


def right(p, times=1, mods=()):
    for _ in range(times):
        p.key("ArrowRight", mods)


def word(p):
    p.place(BODY2)
    p.key("Home")
    right(p, 5, ("shift",))


def across(p):
    p.place(BODY)
    p.key("Home")
    right(p, 2)
    p.key("ArrowDown", ("shift",))


def everything(p):
    p.key("a", ("ctrl",))


def in_heading(p):
    p.place(H1)
    p.key("Home")
    right(p, 2)
    right(p, 3, ("shift",))


def in_item(p):
    p.place(ITEM)
    p.key("Home")
    right(p, 3)
    right(p, 2, ("shift",))


def over_frame(p):
    p.place(1)
    p.key("Home")
    p.key("End", ("shift",))


def in_cell(p):
    p.key("Home", ("ctrl",))
    p.key("ArrowDown")
    p.key("Home")
    right(p, 3, ("shift",))


SHAPES = {"word": ("levels", word), "across": ("levels", across), "everything": ("levels", everything), "in-heading": ("levels", in_heading),
          "in-item": ("levels", in_item), "over-frame": ("image", over_frame), "in-cell": ("table", in_cell)}


def arm(page, raw, select, keys):
    t.fresh(page, raw)
    select(page)
    for name, mods in keys:
        page.key(name, mods)
    page.quiet()
    page.key("q")
    page.quiet()
    state = (evaluate(page.session, PILL), evaluate(page.session, RED))
    return page.save(), state


def e1(page, raws, group, mods):
    for name, (fixture, select) in SHAPES.items():
        raw = raws[fixture]
        t.fresh(page, raw)
        original = page.save()
        pressed, state = arm(page, raw, select, [("Enter", mods)])
        control, control_state = arm(page, raw, select, [("Delete", ()), ("Enter", mods)])
        page.check(f"{group}/{name}/equals-delete-then-enter", body(pressed) == body(control), {"pressed": shape(pressed)[:4], "control": shape(control)[:4]})
        page.check(f"{group}/{name}/control-changed-the-document", body(control) != body(original), {"state": control_state})
        page.check(f"E6/{group}/{name}/ready-no-red", state == ("ready", None), state)
        if mods:
            with zipfile.ZipFile(io.BytesIO(pressed)) as archive:
                page.check(f"{group}/{name}/line-break-in-the-file", b"<text:line-break" in archive.read("content.xml"), None)


def e3(page, raws):
    t.fresh(page, raws["levels"])
    page.place(BODY2)
    mark = mark_of(page)
    page.key("Enter")
    page.quiet()
    got = actions(page, mark)
    page.check("E3/caret-one-break", got == ["insert-paragraph-break"], got)


def e4(page, raws):
    settled, _ = arm(page, raws["levels"], word, [("Enter", ())])
    t.fresh(page, raws["levels"])
    word(page)
    page.quiet()
    mark = mark_of(page)
    evaluate(page.session, "window.__keys.length = 0")
    sent = dirty.timed_keys(SimpleNamespace(browser=page.browser, session=page.session), [(0, "Enter", ()), (10, "q", ())])
    page.quiet()
    got = actions(page, mark)
    seen = evaluate(page.session, "window.__keys")
    gap = round(seen[1][1] - seen[0][1], 1) if len(seen) >= 2 else None
    page.check("E4/order", got[:2] == ["delete-selection", "insert-paragraph-break"], got)
    page.check("E4/gap-under-20-ms", gap is not None and gap < 20, {"gapMs": gap, "sent": sent})
    fast = page.save()
    page.check("E4/q-does-not-overtake-the-break", body(fast) == body(settled), shape(fast)[:4])


def e5(page, raws):
    for name in ("word", "across"):
        fixture, select = SHAPES[name]
        raw = raws[fixture]
        t.fresh(page, raw)
        original = page.save()
        t.fresh(page, raw)
        select(page)
        page.key("Enter")
        page.quiet()
        presses = 0
        for presses in range(1, 4):
            page.key("z", ("ctrl",))
            page.quiet()
            if body(page.save()) == body(original):
                break
        page.check(f"E5/{name}/back-at-the-document", body(page.save()) == body(original) and presses <= 2, {"presses": presses})


def e7(page, raws):
    for name, fixture, select in (("caret", "levels", lambda p: p.place(BODY2)), ("over-frame", "image", over_frame)):
        raw = raws[fixture]
        t.fresh(page, raw)
        select(page)
        before = page.save()
        evaluate(page.session, pp.CLEAR_TOAST)
        evaluate(page.session, pp.COPY)
        page.quiet()
        toast = evaluate(page.session, TOAST)
        page.check(f"E7/{name}/a-sentence", SENTENCE in toast and "CLIPBOARD_" not in toast, toast)
        page.check(f"E7/{name}/unchanged", body(page.save()) == body(before), None)


def run_one(record, raws, out, only):
    session = None
    try:
        session = common.open_browser(record["browser"], (1400, 1000))
        record["version"] = getattr(session, "version", None)
        page = Page(session, record["browser"], record)
        page.open(raws["levels"])
        page.click_paper(1500, 1500)
        page.quiet()
        steps = {"E1": lambda: e1(page, raws, "E1", ()), "E2": lambda: e1(page, raws, "E2", ("shift",)), "E3": lambda: e3(page, raws),
                 "E4": lambda: e4(page, raws), "E5": lambda: e5(page, raws), "E7": lambda: e7(page, raws)}
        for group, step in steps.items():
            if only and group not in only:
                continue
            try:
                step()
            except Exception:
                record["checks"].append({"id": f"{group}/fatal", "pass": False, "actual": traceback.format_exc()[-800:]})
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
    parser.add_argument("--profile", default="e2-editor-v32")
    parser.add_argument("--page-rev")
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raws = {"levels": t.LEVELS.read_bytes(), "table": t.TABLE.read_bytes(), "image": IMAGE.read_bytes()}
    only = set(filter(None, args.only.split(",")))
    source = (subprocess.check_output(["git", "show", f"{args.page_rev}:wasm_sdk_probe/web/e2-editor-app.js"], text=True) if args.page_rev
              else z.APP.read_text(encoding="utf-8"))
    served = pp.repointed_page(source, args.profile, z.PROJECT / "dist/profiles" / args.profile / "sdk-manifest.json")[0]
    html = z.HTML.read_text(encoding="utf-8")
    report = {"argv": sys.argv, "tool": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "profile": args.profile, "pageRev": args.page_rev,
              "page": hashlib.sha256(served.encode()).hexdigest(), "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="writer-enter-", dir=z.PROJECT / "build"))
    try:
        with common.browser_lock("check_writer_enter_range"):
            pre = common.pre_run_checks()
            report["preRun"] = {k: pre[k] for k in ("refuse", "loadavg")}
            if pre["refuse"]:
                raise SystemExit(f"pre-run refused: {pre['refuse']}")
            pp.build_mirror(common.DIST, scratch / "m", {"e2-editor.html": common.inject(html, [z.OBSERVER, t.WATCH, KEYS]).encode(), "e2-editor-app.js": served.encode()})
            with common.served(scratch / "m") as base:
                for browser in args.browsers.split(","):
                    record = {"browser": browser, "base": base, "checks": []}
                    report["runs"].append(record)
                    run_one(record, raws, out, only)
                    print(browser, sum(c["pass"] for c in record["checks"]), "/", len(record["checks"]),
                          sorted({c["id"] for c in record["checks"] if not c["pass"]})[:30], (record.get("fatal") or "").strip().splitlines()[-1:] or "", file=sys.stderr, flush=True)
                    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    checks = [c for r in report["runs"] for c in r["checks"]]
    held = bool(checks) and all(c["pass"] for c in checks) and not any(r.get("fatal") for r in report["runs"])
    report["verdict"] = "P5_HOLDS" if held else "P5_RED"
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], file=sys.stderr)
    return 0 if held else 1


if __name__ == "__main__":
    raise SystemExit(main())
