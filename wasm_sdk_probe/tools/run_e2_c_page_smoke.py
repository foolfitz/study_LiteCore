#!/usr/bin/env python3
"""Load the E2-C product page and touch it.

Not a measurement: no verdict, no evidence.  It exists because a page can pass
`node --check`, boot to a toolbar, and still be unable to do anything -- which
is precisely what happened to demo-structure, whose caret placement called a
method the product client does not have.  Booting was checked; touching was
not.

So this checks the touch: place a caret through the page's own pointer handler,
press a paragraph button through the page's own toolbar handler, and report
what the status bar says afterwards.  The events are synthesised, which is
enough to prove the wiring and NOT enough for SPEC E2-C D5 -- that one needs a
trusted pointer event and therefore a human.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

READ_STATE = """(() => {
const pill = document.querySelector('#state-pill');
return {
  state: pill ? pill.dataset.state : null,
  label: pill ? pill.textContent : null,
  revision: document.querySelector('#s-revision').textContent,
  pending: document.querySelector('#s-pending').textContent,
  checkpoint: document.querySelector('#s-checkpoint').textContent,
  latency: document.querySelector('#s-latency').textContent,
  doc: document.querySelector('#s-doc').textContent,
  toast: document.querySelector('#toast').textContent,
  buttons: [...document.querySelectorAll('#toolbar button[data-action]')]
    .map((b) => ({ action: b.dataset.action, disabled: b.disabled })),
};
})()
"""

# Through the page's own handlers: a PointerEvent on the canvas and a click on
# the toolbar.  Driving the session object directly would test the session,
# which already has unit tests, and skip the wiring this run exists for.
POINT_AT = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const x = box.left + box.width * ARG_X;
const y = box.top + box.height * ARG_Y;
canvas.dispatchEvent(new PointerEvent('pointerdown', {
  clientX: x, clientY: y, button: 0, buttons: 1, pointerId: 1, bubbles: true }));
canvas.dispatchEvent(new PointerEvent('pointerup', {
  clientX: x, clientY: y, button: 0, buttons: 0, pointerId: 1, bubbles: true }));
return true;
})()
"""

PRESS = """(() => {
const button = document.querySelector('#toolbar button[data-action="ARG_ACTION"]');
if (!button) return false;
button.click();
return true;
})()
"""


def navigate(session, url, timeout=180):
    """Go to a page that is NOT a probe page.

    ChromeSession.navigate waits for `globalThis.__probe_metrics`, which every
    harness page sets and no product page should: the product must not carry a
    field that exists only so a runner can tell it has loaded.  So this drives
    the same primitives and waits on readyState instead.
    """
    if isinstance(session, ChromeSession):
        session.call("Page.navigate", {"url": url})
    else:
        session.navigate(url)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if evaluate(session, "(() => document.readyState === 'complete')()"):
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("the page did not finish loading")


def wait_for(session, predicate, timeout, poll=0.5):
    deadline = time.monotonic() + timeout
    state = None
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if state and predicate(state):
            return state
        time.sleep(poll)
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--fixture", default="list-contexts")
    parser.add_argument("--action", default="set-paragraph-heading")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    report: dict = {"browser": args.browser, "steps": []}
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        navigate(session, base)

        booted = wait_for(session, lambda s: s.get("state") in ("ready", "stopped",
                                                               "expired"),
                          args.timeout)
        report["steps"].append({"step": "boot", "state": booted})
        if not booted or booted.get("state") != "ready":
            report["ok"] = False
            report["failedAt"] = "boot"
            return finish(report)

        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        caret = wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""),
                         60)
        report["steps"].append({"step": "place-caret", "state": caret})
        if not caret or "失敗" in (caret.get("latency") or ""):
            report["ok"] = False
            report["failedAt"] = "place-caret"
            return finish(report)

        before = int(caret["revision"]) if caret["revision"].isdigit() else None
        evaluate(session, PRESS.replace("ARG_ACTION", args.action))
        acted = wait_for(
            session,
            lambda s: s.get("revision") != caret["revision"]
            or "失敗" in (s.get("latency") or ""),
            120)
        report["steps"].append({"step": args.action, "state": acted})
        after = int(acted["revision"]) if acted and acted["revision"].isdigit() else None
        report["revisionBefore"] = before
        report["revisionAfter"] = after
        report["ok"] = (after is not None and before is not None
                        and after == before + 1
                        and "失敗" not in (acted.get("latency") or ""))
        if not report["ok"]:
            report["failedAt"] = args.action
        return finish(report)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


def finish(report: dict) -> int:
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
