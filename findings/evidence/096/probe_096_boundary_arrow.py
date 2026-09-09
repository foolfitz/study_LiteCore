#!/usr/bin/env python3
"""Finding 096: does a boundary arrow press kill the session, and on which engines?

REGISTERED FIRST, MEASURED SECOND.  The protocol this probe executes is
`handoff/tasks/TASK-2026-09-09-096-which-profiles-kill-the-session.md`,
committed (`a0f098b5`) before this file existed.  Nothing here may widen it.

THIS PROBE MAY NOT NAME A CAUSE.  It answers one question -- does the session
enter a dead state after an arrow key pressed at a document boundary, and on
which of e2-editor-v13 / v12 / v8 -- and banks what the engine said while it
happened.  Why it happens is not measured here.

THE USER'S PATH, NOT THE HARNESS'S.  The owner pressed real arrow keys, so keys
go through `Input.dispatchKeyEvent` (rawKeyDown/keyUp with a real virtual key
code), the caret is placed by a canvas pointerdown, and the document is handed
to the product's own `#file` input as a real file on disk.  A synthesised
KeyboardEvent or a `session.action("move-line-up")` would measure a path nobody
walks; this tree has paid for that twice.

ASK THE ENGINE, NOT THE PAGE.  `#s-latency`, the state pill and the toast are
the page's observations.  So every attempt also banks, RAW:

  * every CDP event on the page target, buffered rather than discarded --
    `ChromeSession.call` throws away every message whose id does not match while
    it waits for its own, which has already cost this tree one wrong conclusion
    (`induce_worker_failure`, 2026-08-27);
  * the document worker's own console and uncaught errors, reached through
    `Target.setAutoAttach` (the worker cannot be found by asking for it);
  * every toast, through the MutationObserver `INSTALL` puts on `#toast`;
  * the state-pill transition trace, recorded by a MutationObserver in the page
    so the ordering carries page timestamps rather than poll times.

Usage:
  probe_096_boundary_arrow.py --profile e2-editor-v13 [--direction up]
                              [--attempts 5] [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
sys.path.insert(0, str(PROJECT / "tools"))

from r7_support import evaluate, wait_page                          # noqa: E402
from run_browser_probe import ChromeSession, free_port              # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate                # noqa: E402
from run_e2_c_product_path import (                                 # noqa: E402
    DEAD_STATES, INSTALL, LINE_INK, POINT_AT, READ_TOASTS,
    build_mirror, caret_click_fractions, repointed_page,
)

OWNER_DOCUMENT = Path("/home/jiajun/Documents/SLAT/e20-專訪瓦特老師.odt")
OWNER_DOCUMENT_SHA256 = \
    "63bf89cb5d7eb8913fd2e691f5d93b0d42d8715ca9ef8c61cd331048831c53d5"

# The owner's sentence, quoted for comparison and NOT used as the predicate.
OWNER_NOTICE = "引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。"

# Events that arrive by the thousand and answer nothing here.  Everything else
# is banked verbatim.  Named rather than filtered by a positive list, so a new
# CDP domain shows up in the evidence instead of being silently dropped.
NOISE = {
    "Network.dataReceived",
    "Network.requestWillBeSentExtraInfo",
    "Network.responseReceivedExtraInfo",
    "Runtime.executionContextCreated",
    "Runtime.executionContextDestroyed",
    "Page.frameStartedLoading", "Page.frameStoppedLoading",
    "Page.lifecycleEvent", "Page.domContentEventFired", "Page.loadEventFired",
    "Page.frameResized",
}
EVENT_CAP = 4000


# ---------------------------------------------------------------- the session

class BufferingSession(ChromeSession):
    """A ChromeSession that keeps the events its `call` is not waiting for.

    The base class's `call` drops them on the floor.  That is fine for a runner
    that only wants answers; it is fatal for a probe whose subject is what the
    engine SAID while an operation was in flight.
    """

    def __init__(self, cache_mode: str):
        self.events: list[dict] = []
        self.dropped = 0
        self.worker_sessions: dict[str, dict] = {}
        super().__init__(cache_mode)

    def _keep(self, message: dict) -> None:
        method = message.get("method")
        if not method or method in NOISE:
            return
        # BOOKKEEPING ONLY -- no socket i/o, because this runs inside `call`'s
        # receive loop.  Opening a document REPLACES the document worker: the
        # first shakedown's liveness probe was addressed to a session that had
        # been detached at the open, and Chrome answered "Session with given id
        # not found".  A map that is not maintained is a map that measures the
        # worker nobody is using.
        if method == "Target.attachedToTarget":
            params = message.get("params") or {}
            self.worker_sessions[params["sessionId"]] = params["targetInfo"]
        elif method == "Target.detachedFromTarget":
            self.worker_sessions.pop(
                (message.get("params") or {}).get("sessionId"), None)
        if len(self.events) >= EVENT_CAP:
            self.dropped += 1
            return
        message["_t"] = round(time.monotonic() - self._t0, 3) \
            if hasattr(self, "_t0") else None
        self.events.append(message)

    def call(self, method, params=None, timeout=180, session_id=None):
        self.next_id += 1
        message_id = self.next_id
        message = {"id": message_id, "method": method, "params": params or {}}
        if session_id is not None:
            message["sessionId"] = session_id
        self.websocket.send(json.dumps(message))
        while True:
            response = json.loads(self.websocket.recv(timeout=timeout))
            if response.get("id") != message_id:
                self._keep(response)
                continue
            if "error" in response:
                raise RuntimeError(f"CDP {method}: {response['error']}")
            return response.get("result", {})

    def pump(self, seconds: float) -> None:
        """Read the socket for a while so events arrive even when nothing is asked."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                self._keep(json.loads(self.websocket.recv(timeout=0.25)))
            except Exception:                       # noqa: BLE001 -- quiet socket
                pass

    def attach_workers(self, settle: float = 4.0) -> dict:
        """Reach the document worker, and enable its console.

        `Target.getTargets` reports eight worker targets with EMPTY urls and
        `attachToTarget` on them is never answered (measured 2026-08-27).
        `setAutoAttach` with flatten is the route that works, and the url is in
        the EVENT.  Sent by hand because `call` would consume the attachments
        while waiting for its own answer -- the same reason
        `induce_worker_failure` sends it by hand.
        """
        self.next_id += 1
        message_id = self.next_id
        self.websocket.send(json.dumps(
            {"id": message_id, "method": "Target.setAutoAttach",
             "params": {"autoAttach": True, "flatten": True,
                        "waitForDebuggerOnStart": False}}))
        attached, answered = [], False
        deadline = time.monotonic() + settle
        while time.monotonic() < deadline:
            try:
                message = json.loads(self.websocket.recv(timeout=0.5))
            except Exception:                       # noqa: BLE001
                continue
            if message.get("method") == "Target.attachedToTarget":
                attached.append(message["params"])
                self._keep(message)
            elif message.get("id") == message_id:
                answered = True
            else:
                self._keep(message)
        enabled = []
        for entry in attached:
            info = entry["targetInfo"]
            sid = entry["sessionId"]
            self.worker_sessions[sid] = info
            if info.get("type") not in ("worker", "shared_worker",
                                        "service_worker"):
                continue
            for domain in ("Runtime.enable", "Log.enable"):
                try:
                    self.call(domain, {}, session_id=sid)
                    enabled.append({"sessionId": sid, "domain": domain,
                                    "url": info.get("url")})
                except Exception as error:          # noqa: BLE001 -- reported
                    enabled.append({"sessionId": sid, "domain": domain,
                                    "url": info.get("url"),
                                    "error": f"{type(error).__name__}: {error}"})
        self._enabled = {e["sessionId"] for e in enabled if "error" not in e}
        return {"answered": answered,
                "attached": [{"sessionId": a["sessionId"],
                              "type": a["targetInfo"].get("type"),
                              "url": a["targetInfo"].get("url")}
                             for a in attached],
                "enabled": enabled}

    def sync_workers(self) -> list[dict]:
        """Enable the console on any worker that has appeared since the last call.

        `setAutoAttach` stays on, so a worker created later arrives as an EVENT
        and `_keep` records it -- but nothing has turned its console on yet.
        Called after the document is opened, because that is exactly when the
        engine's worker is replaced.
        """
        self.pump(0.5)
        added = []
        for sid, info in list(self.worker_sessions.items()):
            if sid in getattr(self, "_enabled", set()):
                continue
            if info.get("type") != "worker":
                continue
            for domain in ("Runtime.enable", "Log.enable"):
                try:
                    self.call(domain, {}, session_id=sid, timeout=15)
                    added.append({"sessionId": sid, "domain": domain,
                                  "url": info.get("url")})
                except Exception as error:          # noqa: BLE001 -- reported
                    added.append({"sessionId": sid, "domain": domain,
                                  "url": info.get("url"),
                                  "error": f"{type(error).__name__}: {error}"})
            self._enabled = getattr(self, "_enabled", set()) | {sid}
        return added


# ------------------------------------------------------------------- the page

READ_FRAME = """(() => {
const q = (s) => document.querySelector(s);
const sink = q('#sink'), desk = q('#desk'), canvas = q('#canvas');
const pill = q('#state-pill'), notice = q('#notice');
return {
  sinkTop: sink ? sink.offsetTop : null,
  sinkLeft: sink ? sink.offsetLeft : null,
  sinkHeight: sink ? sink.offsetHeight : null,
  activeDescendant: sink ? sink.getAttribute('aria-activedescendant') : null,
  deskScrollTop: desk ? desk.scrollTop : null,
  deskScrollHeight: desk ? desk.scrollHeight : null,
  deskClientHeight: desk ? desk.clientHeight : null,
  canvasHeight: canvas ? canvas.height : null,
  canvasWidth: canvas ? canvas.width : null,
  state: pill ? pill.dataset.state : null,
  stateLabel: pill ? pill.textContent : null,
  noticeShow: notice ? notice.dataset.show : null,
  noticeRescue: notice ? (notice.dataset.rescue || null) : null,
  noticeText: q('#notice-text') ? q('#notice-text').textContent : null,
  noticeAction: q('#notice-action') ? q('#notice-action').textContent : null,
  noticeDisabled: q('#notice-action') ? q('#notice-action').disabled : null,
  latency: q('#s-latency') ? q('#s-latency').textContent : null,
  revision: q('#s-revision') ? q('#s-revision').textContent : null,
  pending: q('#s-pending') ? q('#s-pending').textContent : null,
  checkpoint: q('#s-checkpoint') ? q('#s-checkpoint').textContent : null,
  activeElement: document.activeElement ? document.activeElement.id : null,
};
})()"""

# The transition trace, recorded IN THE PAGE.  Polling would time the poll, not
# the transition, and 「就緒 → 處理中 → 需要回復」 is a sequence whose gaps are
# the interesting part.
WATCH_STATE = """(() => {
if (window.__f096) return "already";
const q = (s) => document.querySelector(s);
const pill = q('#state-pill'), notice = q('#notice');
const w = { t0: performance.now(), transitions: [] };
window.__f096 = w;
const snap = () => ({
  state: pill ? pill.dataset.state : null,
  noticeShow: notice ? notice.dataset.show : null,
  noticeRescue: notice ? (notice.dataset.rescue || null) : null,
  noticeText: q('#notice-text') ? q('#notice-text').textContent : null,
  latency: q('#s-latency') ? q('#s-latency').textContent : null,
  revision: q('#s-revision') ? q('#s-revision').textContent : null,
  pending: q('#s-pending') ? q('#s-pending').textContent : null,
  checkpoint: q('#s-checkpoint') ? q('#s-checkpoint').textContent : null,
});
const rec = () => {
  const now = snap();
  const last = w.transitions[w.transitions.length - 1];
  const same = last && last.state === now.state
    && last.noticeShow === now.noticeShow && last.noticeRescue === now.noticeRescue;
  if (same) return;
  w.transitions.push(Object.assign({ ms: Math.round(performance.now() - w.t0) }, now));
};
rec();
const o = new MutationObserver(rec);
if (pill) o.observe(pill, { attributes: true, childList: true,
                            characterData: true, subtree: true });
if (notice) o.observe(notice, { attributes: true, childList: true,
                                characterData: true, subtree: true });
return "installed";
})()"""

READ_TRANSITIONS = "(() => (window.__f096 ? window.__f096.transitions : null))()"

# UNCAUGHT ERRORS AND UNHANDLED REJECTIONS, recorded rather than inferred.
# The page's own handlers swallow rejections (`void editorAction(...).catch(()=>{})`),
# so a rejection that never reaches a toast would otherwise leave no trace at all.
WATCH_ERRORS = """(() => {
if (window.__f096err) return "already";
const box = { errors: [], rejections: [] };
window.__f096err = box;
window.addEventListener('error', (e) => {
  box.errors.push({ message: String(e.message), filename: e.filename,
                    lineno: e.lineno, colno: e.colno,
                    stack: e.error && e.error.stack ? String(e.error.stack) : null,
                    code: e.error && e.error.code ? String(e.error.code) : null });
});
window.addEventListener('unhandledrejection', (e) => {
  const r = e.reason;
  box.rejections.push({ message: r && r.message ? String(r.message) : String(r),
                        code: r && r.code ? String(r.code) : null,
                        recovery: r && r.recovery ? String(r.recovery) : null,
                        details: (() => { try { return JSON.parse(JSON.stringify(r && r.details)); }
                                          catch (x) { return String(x); } })(),
                        stack: r && r.stack ? String(r.stack) : null });
});
return "installed";
})()"""

READ_ERRORS = "(() => (window.__f096err ? window.__f096err : null))()"

# Rows of ink at one end of the paper.  A row whose dark pixels span more than
# half the canvas is the page frame, not text -- the same discrimination
# LINE_INK makes between a glyph and a border.
INK_ROWS = """(() => {
const canvas = document.querySelector('#canvas');
if (!canvas || !canvas.height) return { available: false };
const w = canvas.width, H = canvas.height;
const rows = Math.min(ARG_ROWS, H);
const y0 = ARG_FROM_END ? (H - rows) : 0;
const data = canvas.getContext('2d').getImageData(0, y0, w, rows).data;
const dark = [];
for (let r = 0; r < rows; r += 1) {
  let n = 0;
  for (let x = 0; x < w; x += 1) {
    const i = (r * w + x) * 4;
    if (data[i+3] > 128 && data[i] < 100 && data[i+1] < 100 && data[i+2] < 100) n += 1;
  }
  dark.push(n);
}
return { available: true, y0, rows, height: H, width: w, dark };
})()"""

CLEAR_LATENCY = """(() => {
document.querySelector('#s-latency').textContent = '';
return true;
})()"""


def text_row(scan: dict, which: str) -> dict:
    """The first (or last) row of TEXT ink, as an absolute canvas y.

    TWO thresholds, and the lower one was forced by a measurement rather than
    by caution.  The first shakedown (2026-09-09, `--label shakedown`) reported
    the first text row 628 px down a 3727 px canvas and a contiguous run of
    1218 rows -- because the paper's LEFT AND RIGHT BORDERS put a handful of
    dark pixels in every row inside the page, so `n > 0` is true of blank line
    spacing too and the run swallowed the whole strip.  A glyph row carries
    scores of dark pixels (measured: 162); two vertical borders carry a
    handful.  `FLOOR` separates them, and it is recorded in the evidence so the
    number is auditable rather than a magic constant.
    """
    if not scan.get("available"):
        return {"found": False, "why": "no canvas"}
    width = scan["width"]
    limit = 0.5 * width          # more than half the width is the page frame
    floor = 20                   # fewer than this is the two vertical borders
    rows = [i for i, n in enumerate(scan["dark"]) if floor <= n < limit]
    if not rows:
        return {"found": False, "why": "no text row in the scanned strip",
                "maxDark": max(scan["dark"]) if scan["dark"] else None,
                "borderLimit": limit}
    if which == "first":
        anchor = rows[0]
        run = [anchor]
        for i in rows[1:]:
            if i - run[-1] <= 2:
                run.append(i)
            else:
                break
    else:
        anchor = rows[-1]
        run = [anchor]
        for i in reversed(rows[:-1]):
            if run[-1] - i <= 2:
                run.append(i)
            else:
                break
    mid = sum(run) // len(run)
    y = scan["y0"] + mid
    return {"found": True, "y": y, "fraction": y / scan["height"],
            "runRows": len(run), "canvasHeight": scan["height"],
            "darkAtRow": scan["dark"][mid], "floor": floor,
            "borderLimit": limit, "textRowsInStrip": len(rows),
            "firstTextRowInStrip": rows[0], "lastTextRowInStrip": rows[-1]}


def press(session, key: str, code: int) -> None:
    for kind in ("rawKeyDown", "keyUp"):
        session.call("Input.dispatchKeyEvent",
                     {"type": kind, "key": key, "code": key,
                      "windowsVirtualKeyCode": code, "nativeVirtualKeyCode": code})


def dead(frame: dict) -> str | None:
    name = (frame or {}).get("state")
    return name if name in DEAD_STATES else None


# ------------------------------------------------------------------ one attempt

def attempt(session, base: str, direction: str, index: int,
            timeout: float, presses: int, after_still: int,
            death_wait: float) -> dict:
    record: dict = {"attempt": index, "direction": direction,
                    "startedAt": datetime.now(timezone.utc).isoformat()}
    session.events = []
    session.dropped = 0
    session._t0 = time.monotonic()

    navigate(session, base)
    evaluate(session, WATCH_STATE)
    evaluate(session, WATCH_ERRORS)
    evaluate(session, INSTALL)
    record["workers"] = session.attach_workers()

    booted = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        booted = evaluate(session, READ_STATE) or {}
        if booted.get("state") in ("ready", "stopped", "expired"):
            break
        time.sleep(0.4)
    record["boot"] = booted
    if (booted or {}).get("state") != "ready":
        record["outcome"] = "VOID"
        record["why"] = f"page booted to {(booted or {}).get('state')!r}, not ready"
        return finish(session, record)

    # THE OWNER'S OWN FILE, through the product's own file input.
    session.set_file("#file", OWNER_DOCUMENT)
    opened = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        opened = evaluate(session, READ_STATE) or {}
        if opened.get("state") == "ready" and OWNER_DOCUMENT.stem[:6] in (opened.get("doc") or ""):
            break
        if opened.get("state") in DEAD_STATES:
            break
        time.sleep(0.4)
    record["opened"] = opened
    if (opened or {}).get("state") != "ready":
        record["outcome"] = "VOID"
        record["why"] = f"the document did not open: state {(opened or {}).get('state')!r}"
        return finish(session, record)
    time.sleep(4.0)
    # The open replaced the worker; turn its console on before the gesture.
    record["workersAfterOpen"] = session.sync_workers()

    frame = evaluate(session, READ_FRAME) or {}
    record["frameAfterOpen"] = frame
    # LONGER THAN THE VIEWPORT, measured rather than assumed.
    room = (frame.get("deskScrollHeight") or 0) - (frame.get("deskClientHeight") or 0)
    record["scrollRoomPx"] = room
    if room <= 0:
        record["outcome"] = "VOID"
        record["why"] = ("the document is not longer than the viewport "
                         f"(scrollHeight {frame.get('deskScrollHeight')}, "
                         f"clientHeight {frame.get('deskClientHeight')})")
        return finish(session, record)

    which = "first" if direction == "up" else "last"
    scan = evaluate(session, INK_ROWS
                    .replace("ARG_ROWS", "1600")
                    .replace("ARG_FROM_END", "false" if direction == "up" else "true"))
    row = text_row(scan or {}, which)
    record["inkRow"] = row
    record["inkScanSummary"] = {"y0": (scan or {}).get("y0"),
                                "rows": (scan or {}).get("rows"),
                                "height": (scan or {}).get("height"),
                                "width": (scan or {}).get("width"),
                                "maxDark": max((scan or {}).get("dark") or [0])}
    if not row.get("found"):
        record["outcome"] = "VOID"
        record["why"] = row.get("why")
        return finish(session, record)

    y = f"{row['fraction']:.6f}"
    ink = evaluate(session, LINE_INK.replace("ARG_Y", y)) or {}
    fractions = caret_click_fractions(ink)
    record["clickFractions"] = dict(fractions, y=y)
    evaluate(session, CLEAR_LATENCY)
    evaluate(session, POINT_AT.replace("ARG_X", fractions["near"]).replace("ARG_Y", y))
    placed = None
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        placed = evaluate(session, READ_STATE) or {}
        if "定位游標" in (placed.get("latency") or ""):
            break
        time.sleep(0.3)
    record["placement"] = placed
    ok = "定位游標" in ((placed or {}).get("latency") or "") \
        and "失敗" not in ((placed or {}).get("latency") or "")
    if not ok:
        record["outcome"] = "VOID"
        record["why"] = f"the caret could not be placed: latency {(placed or {}).get('latency')!r}"
        return finish(session, record)
    time.sleep(1.0)

    key, code = ("ArrowUp", 38) if direction == "up" else ("ArrowDown", 40)
    record["key"] = {"key": key, "windowsVirtualKeyCode": code,
                     "delivery": "CDP Input.dispatchKeyEvent rawKeyDown/keyUp"}
    before = evaluate(session, READ_FRAME) or {}
    record["frameBeforeFirstPress"] = before
    trace = []
    still = 0
    died_at = None
    for step in range(1, presses + 1):
        prior = evaluate(session, READ_FRAME) or {}
        press(session, key, code)
        # Wait for the caret to move OR for the session to die, whichever first.
        moved = False
        after = prior
        watch = time.monotonic() + 3.0
        while time.monotonic() < watch:
            time.sleep(0.15)
            after = evaluate(session, READ_FRAME) or after
            if dead(after):
                break
            if (after.get("sinkTop") != prior.get("sinkTop")
                    or after.get("sinkLeft") != prior.get("sinkLeft")):
                moved = True
                break
        trace.append({"press": step, "moved": moved,
                      "sinkTop": after.get("sinkTop"),
                      "sinkLeft": after.get("sinkLeft"),
                      "deskScrollTop": after.get("deskScrollTop"),
                      "state": after.get("state"),
                      "latency": after.get("latency"),
                      "pending": after.get("pending"),
                      "revision": after.get("revision")})
        if dead(after):
            died_at = step
            break
        still = 0 if moved else still + 1
        if still >= after_still:
            break
    record["pressTrace"] = trace
    record["pressesSpent"] = len(trace)
    record["pressesAtBoundary"] = still
    # THE BOUNDARY PRESS, named.  The press after which the caret stopped
    # moving is the one delivered AT the end of the document; `diedAtPress` is
    # often null because the death lands during the wait that follows the loop,
    # and "which press was the boundary" must not have to be re-derived by a
    # reader of the trace.
    record["firstNonMovingPress"] = next(
        (t["press"] for t in trace if not t["moved"]), None)

    # THE PRODUCT MAY TAKE ITS TIME.  The owner saw 「處理中」 first and the
    # notice 「不久」 after, so a verdict read at the moment of the press would
    # report a live session that is on its way to being dead.
    waited = 0.0
    frame = evaluate(session, READ_FRAME) or {}
    while waited < death_wait and not dead(frame):
        session.pump(0.5)
        waited += 0.5
        frame = evaluate(session, READ_FRAME) or frame
    record["frameAfterWait"] = frame
    record["waitedForDeathSeconds"] = round(waited, 1)

    # IS THE WORKER'S OWN THREAD STILL RUNNING?
    #
    # The page can only report that nothing came back.  "The worker's JavaScript
    # thread is blocked" and "the worker is idle and the engine behind it never
    # answered" produce exactly the same silence at the page, and this tree's
    # standing lesson is that a screen showing nothing has several
    # indistinguishable causes.  One `Runtime.evaluate` addressed to the
    # worker's own CDP session separates them: a blocked JS thread cannot
    # answer it either.
    #
    # RECORDED, NOT INTERPRETED.  Whatever this says, it is one more
    # observation in the evidence; naming a cause is out of this probe's scope.
    record["workerLiveness"] = worker_liveness(session)

    state_name = dead(frame)
    record["died"] = bool(state_name)
    record["deadState"] = state_name
    record["diedAtPress"] = died_at
    if state_name:
        no_checkpoint = (frame.get("noticeShow") == "1"
                         and frame.get("noticeRescue") == "none")
        record["outcome"] = "REPRODUCED" if no_checkpoint else "DIED_WITH_CHECKPOINT"
        record["noticeMatchesOwnerQuote"] = \
            (frame.get("noticeText") or "").strip() == OWNER_NOTICE
    else:
        record["outcome"] = "NOT_REPRODUCED"
    return finish(session, record)


def worker_liveness(session, timeout: float = 12.0) -> list[dict]:
    """One trivial evaluation inside each attached document worker."""
    out = []
    for sid, info in list(session.worker_sessions.items()):
        if info.get("type") != "worker":
            continue
        entry = {"sessionId": sid, "url": info.get("url")}
        started = time.monotonic()
        try:
            result = session.call(
                "Runtime.evaluate",
                {"expression": "JSON.stringify({now: Math.round(performance.now()),"
                               " post: typeof self.postMessage,"
                               " onmsg: typeof self.onmessage})",
                 "returnByValue": True},
                timeout=timeout, session_id=sid)
            entry["answered"] = True
            entry["result"] = result.get("result", {}).get("value")
        except Exception as error:                  # noqa: BLE001 -- reported
            entry["answered"] = False
            entry["error"] = f"{type(error).__name__}: {error}"
        entry["seconds"] = round(time.monotonic() - started, 2)
        out.append(entry)
    return out


def finish(session, record: dict) -> dict:
    """Everything the engine and the page said, raw."""
    try:
        record["transitions"] = evaluate(session, READ_TRANSITIONS)
    except Exception as error:                      # noqa: BLE001 -- reported
        record["transitions"] = f"{type(error).__name__}: {error}"
    for key, script in (("toasts", READ_TOASTS), ("pageErrors", READ_ERRORS)):
        try:
            record[key] = evaluate(session, script)
        except Exception as error:                  # noqa: BLE001
            record[key] = f"{type(error).__name__}: {error}"
    session.pump(1.0)
    worker_ids = {sid for sid, info in session.worker_sessions.items()
                  if info.get("type") == "worker"}
    record["cdpEvents"] = session.events
    record["cdpEventsDropped"] = session.dropped
    record["cdpEventsFromWorker"] = [e for e in session.events
                                     if e.get("sessionId") in worker_ids]
    record["workerTargets"] = session.worker_sessions
    record["completedAt"] = datetime.now(timezone.utc).isoformat()
    return record


# --------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="e2-editor-v13")
    parser.add_argument("--direction", action="append",
                        choices=("up", "down"), default=None)
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--presses", type=int, default=40)
    parser.add_argument("--after-still", type=int, default=6)
    parser.add_argument("--death-wait", type=float, default=90.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--viewport", default="1920x1080")
    parser.add_argument("--out")
    parser.add_argument("--label", default="run")
    args = parser.parse_args()
    directions = args.direction or ["up", "down"]

    root = PROJECT / "dist"
    manifest = root / "profiles" / args.profile / "sdk-manifest.json"
    source = (PROJECT / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
    page, pin_before, wasm = repointed_page(source, args.profile, manifest)
    import hashlib
    page_sha = hashlib.sha256(page.encode("utf-8")).hexdigest()

    document_sha = hashlib.sha256(OWNER_DOCUMENT.read_bytes()).hexdigest()
    report = {
        "schemaVersion": 1,
        "finding": "096",
        "evidenceClass": "diagnostic",
        "label": args.label,
        "protocol": "handoff/tasks/TASK-2026-09-09-096-which-profiles-kill-the-"
                    "session.md (commit a0f098b5), registered before this probe "
                    "was written",
        "mayNotNameACause": True,
        "profile": args.profile,
        "pageSha256": page_sha,
        "pagePinBefore": pin_before,
        "wasmSha256": wasm,
        "document": str(OWNER_DOCUMENT),
        "documentSha256": document_sha,
        "documentSha256Expected": OWNER_DOCUMENT_SHA256,
        "documentIsTheOwners": document_sha == OWNER_DOCUMENT_SHA256,
        "viewport": args.viewport,
        "attemptsPerDirection": args.attempts,
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "attempts": [],
    }

    import tempfile
    scratch = Path(tempfile.mkdtemp(prefix=f"f096-{args.profile}-"))
    mirror = scratch / "root"
    build_mirror(root, mirror, {"e2-editor-app.js": page.encode("utf-8")})
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(mirror)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report["servedFrom"] = str(mirror)
    report["port"] = port
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session = BufferingSession("cold")
        report["browser"] = session.version
        width, _, height = args.viewport.partition("x")
        session.call("Emulation.setDeviceMetricsOverride",
                     {"width": int(width), "height": int(height),
                      "deviceScaleFactor": 1, "mobile": False})
        session.call("Log.enable")
        for direction in directions:
            for index in range(1, args.attempts + 1):
                entry = attempt(session, base, direction, index, args.timeout,
                                args.presses, args.after_still, args.death_wait)
                entry["profile"] = args.profile
                report["attempts"].append(entry)
                print(f"[{args.profile}] {direction} #{index}: "
                      f"{entry.get('outcome')} state={entry.get('deadState')} "
                      f"presses={entry.get('pressesSpent')}",
                      file=sys.stderr, flush=True)
                if args.out:        # incremental: a long matrix must not be lost
                    Path(args.out).write_text(
                        json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    finally:
        if session is not None:
            session.close()
        server.terminate()
        server.wait(timeout=10)

    report["completedAt"] = datetime.now(timezone.utc).isoformat()
    counts: dict = {}
    for entry in report["attempts"]:
        key = f"{entry['direction']}:{entry.get('outcome')}"
        counts[key] = counts.get(key, 0) + 1
    report["counts"] = counts
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    print(json.dumps(counts, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
