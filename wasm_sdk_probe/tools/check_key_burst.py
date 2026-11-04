#!/usr/bin/env python3
"""SPEC-P-key-burst section 3: Writer key bursts, K1-K6, on a mirror.

The mirror is dist/ with the page sources and the v2 session under test; an observer counts what crossed to the
engine and every toast the page showed.  Real keys (tools/v21_input.py: Chrome CDP, Firefox WebDriver), a fresh
test-docs/t1-plain-zh.odt per cell, a click on the paper, Ctrl+Home, the input, quiet, the toolbar's save, the saved
Blob read.

  check_key_burst.py --out DIR [--browsers chrome,firefox] [--subject live|baseline] [--mutation no-seal|no-merge]

  --subject live       editor-shell-v2/narrow-editor-v2-session.js from the working tree (default)
  --subject baseline   dist/editor-shell-v2/narrow-editor-v2-session.js (generation 90): K1 must be red
  --mutation NAME      one named change to the live session; its clause must be red

Verdicts: KB_HOLDS (live, every check in every browser); KB_RED; for a red case RED_AS_NAMED or RED_MISSED.
Exit 0 for KB_HOLDS and RED_AS_NAMED.  --out must not exist.  Nothing under dist/ is written.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_writer_zoom as z  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import v21_input as real  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from r7_support import evaluate  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
SESSION = "editor-shell-v2/narrow-editor-v2-session.js"
DOCUMENT = PROJECT / "test-docs/t1-plain-zh.odt"
NOTICE = "有字沒有輸入"
TOASTS = """<script>
(() => { const seen = window.__toasts = [];
  document.addEventListener('DOMContentLoaded', () => { const t = document.querySelector('#toast');
    new MutationObserver(() => { const s = t.textContent; if (s && seen.at(-1) !== s) seen.push(s); })
      .observe(t, {childList: true, characterData: true, subtree: true}); }); })();
</script>"""

MUTATIONS = {
    "no-seal": ("K3", '    if (label !== "commit-text") this.typedBurst?.seal();\n', ""),
    "no-merge": ("K1", "    && !TYPED_BURST_REFUSED.test(text);\n", "    && false;\n"),
}
REDS = {"baseline": "K1"}

ALNUM = "abcdefghijklmnopqrstuvwxyz0123456789"
CELLS = [
    # id, presses, how (chain | paced ms), expected text in front of the first paragraph, undo after
    ("K1/burst-14", list("qwertyuiop1234"), "chain", "qwertyuiop1234", False),
    ("K1/burst-40", list(ALNUM + " xyz"), "chain", ALNUM + " xyz", False),
    ("K2/paced-30ms-60", list((ALNUM * 2)[:60]), 30, (ALNUM * 2)[:60], False),
    ("K3/order", ["a", "b", "c", "Backspace", "d", "e", "ArrowLeft", "x"], "chain", "abdxe", False),
    ("K6/undo-burst", list("ab cd ef gh"), "chain", None, True),
    ("K6/undo-paced-150ms", list("ab cd ef gh"), 150, None, True),
]


def paced(session, browser, presses, interval_ms):
    if browser == "chrome":
        start = time.monotonic()
        for i, name in enumerate(presses):
            wait = start + i * interval_ms / 1000 - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            real._cdp_press(session, name, ())
        return
    actions: list[dict] = []
    for i, name in enumerate(presses):
        if i:
            actions.append({"type": "pause", "duration": interval_ms})
        actions += real._wd_press_actions(name, ())
    real._wd_perform(session, actions)


def quiet(run, hold_s=1.5, limit=90):
    """Every request answered and nothing new for hold_s: the queued input has all reached the engine."""
    until, last, since = time.monotonic() + limit, None, time.monotonic()
    while time.monotonic() < until:
        s = run.state()
        key = (s["requests"], s["responses"], s["revision"])
        if key != last:
            last, since = key, time.monotonic()
        elif s["requests"] == s["responses"] and s["pill"] == "ready" and time.monotonic() - since >= hold_s:
            return s
        time.sleep(0.1)
    return run.state()


def save(run):
    blobs = run.state()["blobs"]
    run.press('#toolbar button[data-action="save"]')
    s = run.wait(lambda n: n["blobs"] > blobs, 60)
    return base64.b64decode(evaluate(run.session, z.BLOB)) if s["blobs"] > blobs else None


def cell(run, raw, original, spec):
    cid, presses, how, expected, undo = spec
    s = run.open(raw)
    run.click_paper(s["doc"]["width"] * 0.3, s["doc"]["height"] * 0.1)
    real.key(run.session, run.browser, "Home", ("ctrl",))
    quiet(run)
    start = run.state()["requests"]
    toasts = evaluate(run.session, "window.__toasts.length")
    if how == "chain":
        real.chain(run.session, run.browser, [(p, ()) for p in presses])
    else:
        paced(run.session, run.browser, presses, how)
    quiet(run)
    if undo:
        real.key(run.session, run.browser, "z", ("ctrl",))
        quiet(run)
    saved = save(run)
    rows = evaluate(run.session, f"window.__z.requests.slice({start}).map(r => r.op)")
    shown = evaluate(run.session, f"window.__toasts.slice({toasts})")
    paragraphs = z.odt_text(saved) if saved else None
    out = {"id": cid, "presses": len(presses), "how": how, "insertText": rows.count("insertText"),
           "toasts": shown, "first": paragraphs[0] if paragraphs else None,
           "restUnchanged": paragraphs is not None and paragraphs[1:] == original[1:]}
    if expected is not None:
        out["expectedFirst"] = expected + original[0]
    return out


def judge(run, cells, original):
    by = {c["id"]: c for c in cells}
    for c in cells:
        if "expectedFirst" in c:
            run.check(c["id"], c["first"] == c["expectedFirst"] and c["restUnchanged"],
                      {k: c[k] for k in ("first", "expectedFirst", "restUnchanged", "insertText")})
        if c["id"].split("/")[0] in ("K1", "K2", "K3"):
            run.check(f"K4/{c['id']}", not any(NOTICE in t for t in c["toasts"]), c["toasts"])
    burst = by.get("K1/burst-40")
    if burst:
        run.check("K5/burst-40-merged", burst["insertText"] < burst["presses"],
                  {"insertText": burst["insertText"], "presses": burst["presses"]})
    a, b = by.get("K6/undo-burst"), by.get("K6/undo-paced-150ms")
    if a and b:
        run.check("K6/undo-same-as-paced", a["first"] is not None and a["first"] == b["first"]
                  and a["restUnchanged"] and b["restUnchanged"],
                  {"burst": a["first"], "paced": b["first"], "original": original[0]})


def run_browser(record, raw, original):
    session = None
    try:
        session = common.open_browser(record["browser"], (1400, 1000))
        record["version"] = getattr(session, "version", None)
        run = z.Run(session, record["browser"], record)
        for spec in CELLS:
            try:
                record["cells"].append(cell(run, raw, original, spec))
            except Exception:  # noqa: BLE001 -- a crash is a result; the next cell opens its own document
                record["cells"].append({"id": spec[0], "fatal": traceback.format_exc()})
            c = record["cells"][-1]
            print(record["browser"], c["id"], c.get("first"), c.get("insertText"), c.get("toasts"),
                  (c.get("fatal") or "").strip().splitlines()[-1:] or "", file=sys.stderr, flush=True)
        judge(run, [c for c in record["cells"] if "fatal" not in c], original)
        for c in record["cells"]:
            if "fatal" in c:
                run.check(c["id"], False, "fatal")
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
    finally:
        if session is not None:
            record["cleanup"] = common.close_browser(session)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--subject", choices=("live", "baseline"), default="live")
    parser.add_argument("--mutation", choices=sorted(MUTATIONS))
    args = parser.parse_args()
    if args.mutation and args.subject != "live":
        raise SystemExit("a mutation applies to the live session")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw = DOCUMENT.read_bytes()
    original = z.odt_text(raw)
    session_path = (common.DIST if args.subject == "baseline" else PROJECT) / SESSION
    session_src = session_path.read_text(encoding="utf-8")
    if args.mutation:
        _, old, new = MUTATIONS[args.mutation]
        if session_src.count(old) != 1:
            raise SystemExit(f"mutation anchor gone: {args.mutation}")
        session_src = session_src.replace(old, new)
    html = z.HTML.read_text(encoding="utf-8")
    app = z.APP.read_text(encoding="utf-8")
    report = {"argv": sys.argv, "tool": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "document": {"name": DOCUMENT.name, "sha256": hashlib.sha256(raw).hexdigest()},
              "subject": args.subject, "mutation": args.mutation,
              "sources": {"e2-editor.html": hashlib.sha256(html.encode()).hexdigest(),
                          "e2-editor-app.js": hashlib.sha256(app.encode()).hexdigest(),
                          SESSION: {"from": str(session_path.relative_to(PROJECT)),
                                    "sha256": hashlib.sha256(session_src.encode()).hexdigest()}},
              "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="key-burst-", dir=PROJECT / "build"))
    try:
        with common.browser_lock("check_key_burst"):
            pre = common.pre_run_checks()
            report["preRun"] = {k: pre[k] for k in ("refuse", "loadavg")}
            if pre["refuse"]:
                raise SystemExit(f"pre-run refused: {pre['refuse']}")
            pp.build_mirror(common.DIST, scratch / "m", {
                "e2-editor.html": common.inject(html, [z.OBSERVER, TOASTS]).encode(),
                "e2-editor-app.js": app.encode(),
                SESSION: session_src.encode()})
            with common.served(scratch / "m") as base:
                for browser in args.browsers.split(","):
                    record = {"browser": browser, "base": base, "cells": [], "checks": []}
                    report["runs"].append(record)
                    run_browser(record, raw, original)
                    print(browser, sum(c["pass"] for c in record["checks"]), "/", len(record["checks"]),
                          [c["id"] for c in record["checks"] if not c["pass"]],
                          (record.get("fatal") or "").strip().splitlines()[-1:] or "", file=sys.stderr, flush=True)
                    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                                                     encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    checks = [c for r in report["runs"] for c in r["checks"]]
    fatal = [r for r in report["runs"] if r.get("fatal")]
    red = sorted({f"{r['browser']}:{c['id']}" for r in report["runs"] for c in r["checks"] if not c["pass"]})
    report["red"] = red
    clause = MUTATIONS[args.mutation][0] if args.mutation else REDS.get(args.subject)
    if clause:
        # Red where named, in every browser run, and not because a browser died.
        named = all(any(c["id"].startswith(clause + "/") and not c["pass"] for c in r["checks"]) for r in report["runs"])
        report["verdict"] = "RED_AS_NAMED" if report["runs"] and named and not fatal else "RED_MISSED"
    else:
        report["verdict"] = "KB_HOLDS" if checks and all(c["pass"] for c in checks) and not fatal else "KB_RED"
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], red, file=sys.stderr)
    return 0 if report["verdict"] in ("KB_HOLDS", "RED_AS_NAMED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
