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

# SPEC-M3-production-ui §17.11: the document's rows, and the part of them the
# canvas holds.  Release C′ draws only a window of the document -- `data-window`
# on #canvas is `docRows winTop W`, `data-bands` the cached bands as
# `index:top:rows:label`, `data-changes` the page's change counter -- and #paper
# is the document's size.  The P page has none of these attributes and its
# canvas IS the document, so every conversion here is the identity there: no
# scroll, no wait, the same synchronous read.
#
# `__docRowsHeld(w, first, last, current)`: rows [first, last) are in the window
# and under cached bands (with `current`, bands labelled with the counter).
# `__docRowsCover(first, last)`: scroll the desk to centre those rows when they
# are outside the window, then wait up to 15 s for their bands to be drawn
# against the latest change.  Reached only on a windowed page, and only when the
# rows are not already held: a reader that waited for "current" every time
# would pad every keystroke-to-ink measurement with its own wait.
DOC_WINDOW_JS = """
const __docWindow = () => {
  const c = document.querySelector('#canvas');
  const p = (c.dataset.window || '').trim().split(/\\s+/).map(Number);
  if (p.length === 3 && p.every(Number.isInteger))
    return { windowed: true, docRows: p[0], top: p[1], rows: p[2] };
  return { windowed: false, docRows: c.height, top: 0, rows: c.height };
};
const __docRowsHeld = (w, first, last, current) => {
  if (!w.windowed) return true;
  if (first < w.top || last > w.top + w.rows) return false;
  const c = document.querySelector('#canvas');
  const changes = Number(c.dataset.changes);
  const bands = (c.dataset.bands || '').trim().split(/\\s+/).filter(Boolean)
    .map((s) => s.split(':').map(Number))
    .filter((b) => b.length === 4 && (!current || b[3] === changes))
    .sort((a, b) => a[1] - b[1]);
  let at = first;
  for (const [, top, rows] of bands) {
    if (top > at) break;
    if (top + rows > at) at = top + rows;
    if (at >= last) return true;
  }
  return at >= last;
};
const __docRowsCover = async (first, last) => {
  let w = __docWindow();
  if (first < w.top || last > w.top + w.rows) {
    const desk = document.querySelector('#desk');
    const paper = document.querySelector('#paper').getBoundingClientRect();
    const view = desk.getBoundingClientRect();
    const centre = paper.top + paper.height * ((first + last) / 2) / w.docRows;
    desk.scrollTop += centre - (view.top + view.height / 2);
  }
  const deadline = performance.now() + 15000;
  while (performance.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 50));
    w = __docWindow();
    if (__docRowsHeld(w, first, last, true)) return { w, waited: 'current' };
  }
  return { w: __docWindow(), waited: 'timeout' };
};
"""

# Through the page's own handlers: a PointerEvent on the canvas and a click on
# the toolbar.  Driving the session object directly would test the session,
# which already has unit tests, and skip the wiring this run exists for.
#
# The point is a fraction of #paper, the document's own box (§17.11): on the P
# page #paper holds nothing in flow but the canvas, so the two boxes are one;
# on C′ the canvas is a window and only #paper spans the document.  Dispatched
# on #canvas either way -- the P page listens there, C′ listens on #paper and
# the event bubbles up to it -- and not scrolled into view first, because the
# page converts through #paper's box wherever the point is.
POINT_AT = """(() => {
const canvas = document.querySelector('#canvas');
const box = document.querySelector('#paper').getBoundingClientRect();
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
