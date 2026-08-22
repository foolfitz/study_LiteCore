#!/usr/bin/env python3
"""Does a defect-independent route into `recoverable-error` exist at all?

`queue-recovery-inducer-depends-on-an-unfixed-defect`.  The recovery coverage is
tied to upstream finding 038 staying broken, and 2026-08-21 measured that the
debt is not hypothetical: on FIREFOX the 038 inducer already does not reproduce,
so `recovery-returns-what-the-product-promised` is NOT_ESTABLISHED there today.

THE VERIFICATION OBLIGATION COMES FIRST (finding 037's lesson, and the queue item
states it): a candidate must be SHOWN to land in `recoverable-error` rather than
being refused by name.  A guard that declines the shape before it can wedge is
how 037 wasted a round.  So this probe measures candidates and writes down what
happened; it wires nothing into the regression net.

The candidate here is the one the plan settled on after fable's adjudication
ruled out the alternatives:

  * `selectRange` with a short `timeoutMs` -- REJECTED as unreachable: the
    product constructs its session without `selectionTimeoutMs`
    (`web/e2-editor-app.js:762`), so it defaults to 5000
    (`editor-shell/editor-session.js:84`) and nothing outside the page can
    change it.  Passing one would mean putting test-only configuration into the
    product.
  * terminating the worker -- REJECTED: `_worker.terminate()` is private and
    reached only inside `restart()`/`dispose()` (`sdk/document-sdk.js:333`), so
    it is not public API, and it is not a selection gesture, so it cannot serve
    `recovery-returns-what-the-product-promised`'s capability clause either.
  * A SELECTION THAT GENUINELY TAKES TOO LONG -- what this probe tries.  TIMEOUT
    is in RECOVERY_ERRORS (`editor-session.js:15-22`), a huge drag in a long
    document is an ordinary thing for a user to do, it needs no product change,
    and it IS a selection gesture on a dirty document.

Usage:
  probe_second_recovery_inducer.py --browser chrome [--pages 40] [--out FILE]
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import subprocess  # noqa: E402

from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from run_e2_c_product_path import (  # noqa: E402
    OPEN_BYTES, PRESS, SET_TEXT, READ_TOAST,
)
from create_long_document import build as build_long_document  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

# The whole canvas, corner to corner, as one drag.  Deliberately the largest
# selection the product can be asked for through its own handlers.
HUGE_DRAG = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const send = (type, fx, fy, buttons) => canvas.dispatchEvent(
  new PointerEvent(type, {
    clientX: box.left + box.width * fx, clientY: box.top + box.height * fy,
    button: 0, buttons, pointerId: 1, bubbles: true }));
send('pointerdown', 0.02, 0.02, 1);
send('pointermove', 0.50, 0.50, 1);
send('pointermove', 0.98, 0.98, 1);
send('pointerup', 0.98, 0.98, 0);
return true;
})()"""

# Is the product OFFERING recovery, or is the button merely in the DOM?
READ_NOTICE = """(() => {
const notice = document.querySelector('#notice');
if (!notice) return { present: false };
const style = getComputedStyle(notice);
return { present: true, shown: style.display !== 'none',
         rescue: notice.getAttribute('data-rescue'),
         text: (notice.textContent || '').trim().slice(0, 200) };
})()"""


def read(session) -> dict:
    return evaluate(session, READ_STATE) or {}


def wait_for(session, predicate, timeout, poll=0.5):
    deadline = time.monotonic() + timeout
    state = read(session)
    while time.monotonic() < deadline:
        if predicate(state):
            return state
        time.sleep(poll)
        state = read(session)
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"),
                        default="chrome")
    parser.add_argument("--pages", type=int, default=40)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    record: dict = {
        "schemaVersion": 1,
        "release": "second-recovery-inducer-probe",
        "evidenceClass": "diagnostic",
        "why": "verification obligation for "
               "queue-recovery-inducer-depends-on-an-unfixed-defect: show a "
               "candidate LANDS in recoverable-error rather than being refused "
               "by name, before anything is wired into the regression net",
        "browser": args.browser,
        "pages": args.pages,
        "candidate": "a whole-canvas drag in a long, dirty document -- a "
                     "selection readback that genuinely exceeds the session's "
                     "5000 ms selection timeout, which is TIMEOUT and therefore "
                     "in RECOVERY_ERRORS",
        "steps": [],
    }

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(PROJECT / "dist")],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
    session = session_class("cold")
    try:
        navigate(session, base)
        booted = wait_for(session, lambda s: s.get("state") in
                          ("ready", "stopped", "expired"), 180)
        record["steps"].append({"step": "boot", "state": booted.get("state")})
        if booted.get("state") != "ready":
            record["outcome"] = "NOT_ESTABLISHED"
            record["why_not"] = "the page never reached ready"
            return finish(record, args)

        payload = build_long_document(args.pages)
        evaluate(session, OPEN_BYTES
                 .replace("ARG_B64", base64.b64encode(payload).decode("ascii"))
                 .replace("ARG_NAME", "second-inducer.odt"))
        opened = wait_for(session,
                          lambda s: (s.get("doc") or "") == "second-inducer.odt"
                          and s.get("state") == "ready", 300)
        record["steps"].append({"step": "open-long", "pages": args.pages,
                                "state": opened.get("state"),
                                "doc": opened.get("doc")})
        if opened.get("state") != "ready":
            record["outcome"] = "NOT_ESTABLISHED"
            record["why_not"] = "the long document never opened"
            return finish(record, args)

        # DIRTY, because the capability clause on
        # `recovery-returns-what-the-product-promised` is about a selection
        # gesture on a document with unsaved work.
        evaluate(session, SET_TEXT.replace("ARG_TEXT", "SECONDINDUCERDIRTY"))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
        dirty = wait_for(session, lambda s: s.get("state") == "ready", 60)
        record["steps"].append({"step": "dirty", "state": dirty.get("state"),
                                "revision": dirty.get("revision"),
                                "checkpoint": dirty.get("checkpoint")})

        before_notice = evaluate(session, READ_NOTICE)
        evaluate(session, HUGE_DRAG)
        landed = wait_for(
            session,
            lambda s: s.get("state") in ("recoverable-error", "restart-required"),
            120)
        time.sleep(2.0)
        record["steps"].append({
            "step": "huge-drag",
            "stateAfter": landed.get("state"),
            "latency": landed.get("latency"),
            "toast": evaluate(session, READ_TOAST),
            "noticeBefore": before_notice,
            "noticeAfter": evaluate(session, READ_NOTICE),
            "checkpoint": landed.get("checkpoint"),
        })

        reached = landed.get("state") in ("recoverable-error", "restart-required")
        notice = record["steps"][-1]["noticeAfter"] or {}
        record["reachedRecoverableError"] = reached
        record["noticeOffered"] = bool(notice.get("shown"))
        record["outcome"] = (
            "USABLE" if reached and notice.get("shown")
            else "REACHED_BUT_NOT_OFFERED" if reached
            else "DID_NOT_REACH")
        record["verdict"] = {
            "USABLE": "this candidate lands in recoverable-error AND the "
                      "product offers its recovery button, so it can serve as "
                      "the second inducer",
            "REACHED_BUT_NOT_OFFERED": "the state was reached but the product "
                                       "does not OFFER recovery there, so it "
                                       "cannot serve notice-action-recovers-"
                                       "the-session -- which is finding 053's "
                                       "shape and would be a finding of its own",
            "DID_NOT_REACH": "the selection did not time out, so this candidate "
                             "is NOT an inducer. Recorded as a failed "
                             "prediction, not retried until something says why",
        }[record["outcome"]]
    finally:
        try:
            if session is not None:
                session.close()
        finally:
            server.terminate()
    return finish(record, args)


def finish(record: dict, args) -> int:
    text = json.dumps(record, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
