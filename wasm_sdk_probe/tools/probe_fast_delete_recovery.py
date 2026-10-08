#!/usr/bin/env python3
"""What the user is left with when a fast Backspace fails on a large document.

Seen once in finding 111's owner-document run (`findings/evidence/111/browser/
owner-chrome.json`, round 6, Backspace at a 0 ms gap): the delete failed with
`EDITOR_STATE_UNAVAILABLE: selection text became visible without its required
typed callback` (the selection barrier's negative deadline, probe_engine.cpp
~:3888), and every later trial in that page typed nothing (revision 0 -> 0).

Read from the source, not measured: that code carries no barrier detail, so
`recoveryFor` answers "rollback" (paragraph-editor-client.js
`formatFailureDisposition`'s fallback), `_blockQueueIfDispatched` blocks the
queue in `recoverable-error`, and no checkpoint is taken before a delete -- so
the only exit may discard what was typed since the last save.  This probe
measures it, on the shipped standalone page (dist/, v19), changing no product
byte.

Every attempt in a FRESH page (a failure poisons the page, which is the second
thing to characterise): open the owner's document, click the end of 「一、序言」,
End, then real keys X, Y, Backspace at once.  On an ordinary attempt the verdict
is kept and the next attempt starts.  On a failed delete (`上次操作` ends in
失敗):

  1. the state, the notice (shown, rescue, label, disabled, text), the
     checkpoint field, the toast;
  2. the product's save button: did bytes come out, and do they hold X;
  3. the notice's button, if enabled: what opens, and does the reopened (then
     saved) document hold X;
  4. one more real key `Q` after that: does typing still reach the document;
  5. opening the document again through the page's file input, click, `Q`:
     does typing reach the new document.

  probe_fast_delete_recovery.py --browser chrome --out REPORT.json
      [--attempts 60] [--failures 3] [--same-page]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import odt_paragraphs  # noqa: E402
import probe_111_overtake as p111  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
DIST = HERE / "dist"
DOC, FIRST, CLICK = p111.DOCUMENTS["owner"]
NOTICE = """(() => { const n = document.querySelector('#notice'), a = document.querySelector('#notice-action');
  const t = document.querySelector('#notice-text');
  return { show: n ? (n.dataset.show ?? null) : null, rescue: n ? (n.dataset.rescue ?? null) : null,
           limit: n ? (n.dataset.limit ?? null) : null, hidden: n ? n.hidden : null,
           text: t ? t.textContent : null, action: a ? a.textContent : null, disabled: a ? a.disabled : null,
           sinkDisabled: document.querySelector('#sink') ? document.querySelector('#sink').disabled : null,
           generation: (document.querySelector('#s-generation') || {}).textContent ?? null }; })()"""
PRESS_NOTICE = "(() => { const a = document.querySelector('#notice-action'); if (!a || a.disabled) return false; a.click(); return true; })()"


def first_paragraph(raw: bytes | None) -> dict | None:
    if raw is None:
        return None
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        texts = odt_paragraphs.paragraph_texts_from_xml(archive.read("content.xml"))
    head = texts[0] if texts else ""
    # Only the heading (plus what was typed) leaves this function: the rest is the owner's text.
    return {"first": head if head.startswith(FIRST[:2]) else f"<{len(head)} chars>",
            "holdsX": "X" in head, "holdsQ": "Q" in "".join(texts[:2]), "paragraphs": len(texts)}


def save_bytes(session, timeout: float = 30) -> bytes | None:
    index = pp.evaluate(session, pp.SAVE_COUNT) or 0
    pp.evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
    if not pp.wait_saves(session, index + 1, timeout):
        return None
    saved = pp.evaluate(session, pp.READ_SAVE.replace("ARG_INDEX", str(index)))
    return base64.b64decode(saved["b64"]) if saved else None


def state(session) -> dict:
    return pp.evaluate(session, pp.READ_STATE) or {}


def boot(session, base: str) -> None:
    pp.navigate(session, base)
    pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
    pp.evaluate(session, pp.INSTALL)


def open_and_place(session, browser: str, name: str) -> bool:
    pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./probe-owner.odt").replace("ARG_NAME", name))
    opened = pp.wait_for(session, lambda s: (s.get("doc") or "") == name and s.get("state") == "ready", 180)
    p111.quiet(session)
    before = state(session).get("latency")
    pp.evaluate(session, pp.POINT_AT.replace("ARG_X", CLICK[0]).replace("ARG_Y", CLICK[1]))
    pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or "") and s.get("latency") != before, 30)
    p111.quiet(session)
    p111.burst(session, browser, ["End"], 0)
    p111.quiet(session)
    return bool(opened)


def after_failure(session, browser: str, out: dict) -> None:
    out["state"] = state(session)
    out["notice"] = pp.evaluate(session, NOTICE)
    raw = save_bytes(session, 20)
    out["save"] = {"bytes": len(raw) if raw else None, "doc": first_paragraph(raw), "stateAfter": state(session)}
    out["pressedNotice"] = pp.evaluate(session, PRESS_NOTICE)
    if out["pressedNotice"]:
        time.sleep(1.0)
        settled = pp.wait_for(session, lambda s: s.get("state") == "ready", 60)
        p111.quiet(session)
        out["afterNotice"] = {"state": state(session), "notice": pp.evaluate(session, NOTICE)}
        raw = save_bytes(session, 30)
        out["afterNotice"]["doc"] = first_paragraph(raw)
        out["afterNotice"]["settled"] = bool(settled)
        revision = state(session).get("revision")
        p111.burst(session, browser, ["Q"], 0)
        p111.quiet(session, 15)
        out["afterNotice"]["typingQ"] = [revision, state(session).get("revision")]
    # The page's own file input, as the 111 probe did after the failure.
    open_and_place(session, browser, "probe-owner-reopened.odt")
    revision = state(session).get("revision")
    p111.burst(session, browser, ["Q"], 0)
    p111.quiet(session, 15)
    out["reopenedByFileInput"] = {"typingQ": [revision, state(session).get("revision")],
                                  "notice": pp.evaluate(session, NOTICE), "state": state(session)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--attempts", type=int, default=60)
    ap.add_argument("--failures", type=int, default=3)
    ap.add_argument("--same-page", action="store_true",
                    help="boot the page once (and again after each failure) and open every attempt's document "
                         "through the page's file input, as the 111 run did -- the one failure seen so far came "
                         "after some sixty opens in one page")
    args = ap.parse_args()
    mirror = Path(tempfile.mkdtemp(prefix="probe-fdr-")) / "root"
    pp.build_mirror(DIST, mirror, {})
    (mirror / "probe-owner.odt").write_bytes(DOC.read_bytes())
    report = {"probe": "probe_fast_delete_recovery.py", "browser": args.browser,
              "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
              "page": hashlib.sha256((DIST / "e2-editor-app.js").read_bytes()).hexdigest(),
              "documentSha256": hashlib.sha256(DOC.read_bytes()).hexdigest(),
              "samePage": args.same_page,
              "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "attempts": []}
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port),
                               "--root", str(mirror)], cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    failures = 0
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        session = (pp.ChromeSession if args.browser == "chrome" else pp.FirefoxSession)("cold")
        report["version"] = getattr(session, "version", None)
        booted = False
        for number in range(1, args.attempts + 1):
            out: dict = {"n": number}
            try:
                if not (args.same_page and booted):
                    boot(session, base)
                    booted = True
                    out["booted"] = True
                out["opened"] = open_and_place(session, args.browser, f"probe-owner-{number}.odt")
                pp.evaluate(session, p111.KEYLOG)
                p111.burst(session, args.browser, ["X", "Y", "Backspace"], 0)
                time.sleep(2.0)
                p111.quiet(session, 20)
                out["keydowns"] = pp.evaluate(session, p111.READ_KEYLOG)
                seen = state(session)
                out["latency"] = seen.get("latency")
                out["failed"] = (seen.get("latency") or "").endswith("失敗")
                if out["failed"]:
                    failures += 1
                    booted = False   # a failure poisons the page: the next attempt starts fresh
                    out["toast"] = seen.get("toast")
                    after_failure(session, args.browser, out)
                else:
                    raw = save_bytes(session, 30)
                    texts = None
                    if raw:
                        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                            texts = odt_paragraphs.paragraph_texts_from_xml(archive.read("content.xml"))
                    out["verdict"] = "no-save" if texts is None else next(
                        (v for v, h in p111.expected(FIRST)["Backspace"].items() if texts[:1] == h), "other")
            except Exception as error:  # noqa: BLE001 -- recorded, the run goes on
                out["error"] = f"{type(error).__name__}: {error}"
            report["attempts"].append(out)
            print(f"{number:3d} {'FAILED ' + str(out.get('toast'))[:70] if out.get('failed') else out.get('verdict') or out.get('error')}",
                  flush=True)
            args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
            if failures >= args.failures:
                break
    finally:
        report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if session is not None:
            try:
                session.close()
            except Exception as error:  # noqa: BLE001
                report["closeError"] = str(error)
        server.terminate()
        server.wait(timeout=10)
        args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps({"attempts": len(report["attempts"]), "failures": failures}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
