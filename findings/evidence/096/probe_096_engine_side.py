#!/usr/bin/env python3
"""Finding 096: after the session dies, does the ENGINE thread still answer?

REGISTERED FIRST, MEASURED SECOND.  The protocol this probe executes is
`handoff/tasks/TASK-2026-09-09-096-does-the-engine-thread-still-answer.md`,
committed before this file existed.  Nothing here may widen it.

WHAT IT ADDS to `probe_096_boundary_arrow.py`, which it imports and reuses for
everything else (the gesture, the predicate, the arms, the document).  All three
additions live INSIDE THE LIVE WORKER'S OWN REALM, because the page, the shell
and the SDK are the layers the banked evidence already shows are blocked:

  1. a wrapper on `globalThis.__probe_on_event` -- the engine's ONLY route into
     JavaScript (`emitJson`, src/probe_engine.cpp:1032-1045, looked up at call
     time, so a wrapper installed later is called).  Raw JSON strings, banked
     verbatim, with the buffer index marked before every press.
  2. a pass-through wrapper on `self.postMessage`, so the worker's own replies
     are visible from inside the worker.
  3. three injected requests, delivered by dispatching a MessageEvent on the
     worker's global (the worker listens with `self.addEventListener("message")`,
     sdk-worker.js:1571):
       C  f096ControlNoSuchOperation -- the INJECTION-ROUTE CONTROL.  Answered
          UNKNOWN_OPERATION by the worker without touching the engine at all.
          It separates "the engine did not answer" from "my injection never
          arrived", which are otherwise the same silence.
       G  editorGetStateV2 -- goes through the engine's command queue and is
          executed by handleEditorGetState, which answers synchronously and does
          NOT touch gEditorPending.  Its reply carries sourceSequence.
       P  editorActionV2 -- the POSITIVE CONTROL.  handleEditorAction's first
          test after requireDocument is `gEditorPending.requestId != 0` -> BUSY.
          It MUST answer BUSY; anything else voids the attempt (it is not
          reinterpreted).

THIS PROBE MAY NOT NAME A CAUSE beyond what the registered table licenses.
Narrowing three explanations to two is a result; picking one because it reads
well is not.

Usage:
  probe_096_engine_side.py --profile e2-editor-v8 [--direction up]
                           [--attempts 5] [--out FILE] [--label run]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT / "tools"))

_spec = importlib.util.spec_from_file_location(
    "probe_096_boundary_arrow", HERE / "probe_096_boundary_arrow.py")
BASE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BASE)

from r7_support import evaluate, wait_page                          # noqa: E402
from run_browser_probe import free_port                             # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate                # noqa: E402
from run_e2_c_product_path import (                                 # noqa: E402
    DEAD_STATES, INSTALL, LINE_INK, POINT_AT, READ_TOASTS,
    build_mirror, caret_click_fractions, repointed_page,
)

# Ids the SDK cannot issue: `document-sdk.js:_nextId` counts from 1 upward and
# wraps at 0xffffffff, and a session spends a few hundred.
RID_CONTROL = 4000000000
RID_GETSTATE = 4000000001
RID_ACTION = 4000000002
RIDS = (RID_CONTROL, RID_GETSTATE, RID_ACTION)

# ------------------------------------------------------- the worker-realm code

INSTALL_WORKER = """
(() => {
if (globalThis.__f096b) return JSON.stringify({installed: "already"});
const CAP = 2000, RAWCAP = 20000;
const RIDS = [4000000000, 4000000001, 4000000002];
const box = { t0: performance.now(), engine: [], engineDropped: 0,
              posted: [], postedDropped: 0, marks: [], sent: [] };
globalThis.__f096b = box;

// THE ENGINE'S ONLY ROUTE INTO JAVASCRIPT.  emitJson does
// MAIN_THREAD_EM_ASM(... globalThis.__probe_on_event(eventJson) ...), and the
// lookup happens at call time, so wrapping the global after the module booted
// is enough.  Raw strings, not parsed objects: a payload, not a summary of one.
const priorEvent = globalThis.__probe_on_event;
box.hadEventHandler = typeof priorEvent;
if (typeof priorEvent === "function") {
  globalThis.__probe_on_event = function (raw) {
    try {
      if (box.engine.length < CAP) {
        const s = String(raw);
        box.engine.push({ ms: Math.round(performance.now() - box.t0),
                          len: s.length, truncated: s.length > RAWCAP,
                          raw: s.length > RAWCAP ? s.slice(0, RAWCAP) : s });
      } else { box.engineDropped += 1; }
    } catch (e) { box.engineDropped += 1; }
    return priorEvent.apply(this, arguments);
  };
}

// PASS-THROUGH.  Responses to the injected ids reach the page's SDK, which
// drops a response whose requestId it does not know (`if (!entry) return;`).
const priorPost = globalThis.postMessage.bind(globalThis);
box.hadPostMessage = typeof globalThis.postMessage;
globalThis.postMessage = function (msg, transfer) {
  try {
    if (box.posted.length < CAP) {
      const rid = msg && msg.requestId;
      const mine = RIDS.indexOf(rid) >= 0;
      let body = null;
      if (mine) { body = JSON.parse(JSON.stringify(msg)); }
      else if (msg && msg.kind === "response" && msg.ok === false) {
        body = JSON.parse(JSON.stringify(msg.error || null));
      }
      box.posted.push({ ms: Math.round(performance.now() - box.t0),
                        kind: msg && msg.kind, event: msg && msg.event,
                        type: msg && msg.type, requestId: rid,
                        ok: msg && msg.ok, mine: mine, body: body });
    } else { box.postedDropped += 1; }
  } catch (e) { box.postedDropped += 1; }
  return priorPost(msg, transfer);
};
return JSON.stringify({ installed: "yes",
                        hadEventHandler: box.hadEventHandler,
                        hadPostMessage: box.hadPostMessage });
})()
"""

# Which realm is the LIVE document worker.  Asked rather than assumed: sessions
# from earlier attempts linger in the map and answer "Session with given id not
# found", and a worker that never loaded the module has no __probe_on_event.
IDENTIFY_WORKER = """
(() => {
let pendingSize = null, pendingErr = null;
try { pendingSize = pending.size; } catch (e) { pendingErr = String(e); }
return JSON.stringify({
  probeOnEvent: typeof globalThis.__probe_on_event,
  instrumented: !!globalThis.__f096b,
  pendingSize: pendingSize, pendingError: pendingErr,
  location: String(self.location && self.location.href),
  now: Math.round(performance.now()),
});
})()
"""

MARK = """
(() => {
const b = globalThis.__f096b;
if (!b) return JSON.stringify({marked: false});
b.marks.push({ label: ARG_LABEL, engineIndex: b.engine.length,
               postedIndex: b.posted.length,
               ms: Math.round(performance.now() - b.t0) });
return JSON.stringify(b.marks[b.marks.length - 1]);
})()
"""

# The wedged request's own payload, read out of the worker's `pending` map --
# a top-level `const` of a CLASSIC worker script (`new Worker(url, {name})`,
# document-sdk.js:67), so it is a global lexical binding this evaluate can see.
READ_PENDING = """
(() => {
try {
  const out = [];
  for (const [id, v] of pending.entries()) {
    let payload = null;
    try { payload = JSON.parse(JSON.stringify(v.payload || {})); }
    catch (e) { payload = { unserialisable: String(e) }; }
    out.push({ requestId: id, operation: v.operation, payload: payload });
  }
  return JSON.stringify({ ok: true, entries: out });
} catch (e) {
  return JSON.stringify({ ok: false, error: String((e && e.stack) || e) });
}
})()
"""

INJECT = """
(() => {
const b = globalThis.__f096b;
const msg = ARG_MESSAGE;
if (b) b.sent.push({ ms: Math.round(performance.now() - b.t0), msg: msg });
try {
  self.dispatchEvent(new MessageEvent("message", { data: msg }));
  return JSON.stringify({ dispatched: true });
} catch (e) {
  return JSON.stringify({ dispatched: false,
                          error: String((e && e.stack) || e) });
}
})()
"""

COLLECT = """
(() => {
const b = globalThis.__f096b;
if (!b) return JSON.stringify({ present: false });
return JSON.stringify({ present: true, engine: b.engine,
                        engineDropped: b.engineDropped, posted: b.posted,
                        postedDropped: b.postedDropped, marks: b.marks,
                        sent: b.sent });
})()
"""

REPLIES_FOR = """
(() => {
const b = globalThis.__f096b;
if (!b) return JSON.stringify([]);
return JSON.stringify(b.posted.filter((p) => p.requestId === ARG_RID));
})()
"""


# ------------------------------------------------------------------- utilities

def worker_eval(session, sid: str, expression: str, timeout: float = 25.0):
    """One Runtime.evaluate in a worker's own realm.  Bounded, and the bound is
    itself an observation: `callStatus` runs the ccall on the worker's JS
    thread, and a call into wasm that does not return is not the same thing as
    an engine that does not answer."""
    started = time.monotonic()
    try:
        result = session.call("Runtime.evaluate",
                              {"expression": expression, "returnByValue": True,
                               "awaitPromise": False},
                              timeout=timeout, session_id=sid)
    except Exception as error:                      # noqa: BLE001 -- reported
        return {"returned": False,
                "error": f"{type(error).__name__}: {error}",
                "seconds": round(time.monotonic() - started, 2)}
    entry = {"returned": True, "seconds": round(time.monotonic() - started, 2)}
    payload = result.get("result", {})
    if result.get("exceptionDetails"):
        entry["exceptionDetails"] = result["exceptionDetails"]
    value = payload.get("value")
    entry["raw"] = value
    if isinstance(value, str):
        try:
            entry["value"] = json.loads(value)
        except Exception:                           # noqa: BLE001
            entry["value"] = None
    return entry


def live_worker(session) -> dict:
    """Ask every attached worker session which one is the live engine worker."""
    report = []
    chosen = None
    for sid, info in list(session.worker_sessions.items()):
        if info.get("type") != "worker":
            continue
        answer = worker_eval(session, sid, IDENTIFY_WORKER, timeout=12.0)
        entry = {"sessionId": sid, "url": info.get("url"),
                 "answered": answer.get("returned"),
                 "value": answer.get("value"),
                 "error": answer.get("error"),
                 "seconds": answer.get("seconds")}
        report.append(entry)
        if (answer.get("returned")
                and (answer.get("value") or {}).get("probeOnEvent") == "function"):
            chosen = sid
    return {"sessions": report, "chosen": chosen}


def mark(session, sid: str, label: str) -> dict:
    return worker_eval(session, sid,
                       MARK.replace("ARG_LABEL", json.dumps(label)),
                       timeout=12.0)


def inject(session, sid: str, message: dict, rid: int,
           dispatch_timeout: float, reply_wait: float) -> dict:
    """Dispatch one request into the worker's own realm and wait for its reply."""
    record = {"requestId": rid, "message": message}
    started = time.monotonic()
    record["dispatch"] = worker_eval(
        session, sid, INJECT.replace("ARG_MESSAGE",
                                     json.dumps(message, ensure_ascii=False)),
        timeout=dispatch_timeout)
    if not record["dispatch"].get("returned"):
        # THE DISPATCH ITSELF DID NOT RETURN.  Registered as its own shape in
        # the protocol: the worker's JS thread is blocked inside the wasm submit
        # path, which the banked `workerLiveness` evaluate could not see.
        record["answered"] = False
        record["why"] = "the dispatching Runtime.evaluate did not return"
        record["seconds"] = round(time.monotonic() - started, 2)
        return record
    deadline = time.monotonic() + reply_wait
    replies: list = []
    while time.monotonic() < deadline:
        poll = worker_eval(session, sid,
                           REPLIES_FOR.replace("ARG_RID", str(rid)),
                           timeout=12.0)
        if not poll.get("returned"):
            record["pollError"] = poll.get("error")
            break
        replies = poll.get("value") or []
        if replies:
            break
        time.sleep(0.3)
    record["seconds"] = round(time.monotonic() - started, 2)
    record["replies"] = replies
    record["answered"] = bool(replies)
    if replies:
        body = (replies[0] or {}).get("body") or {}
        record["ok"] = body.get("ok")
        if body.get("ok") is False:
            record["code"] = (body.get("error") or {}).get("code")
            record["message"] = (body.get("error") or {}).get("message")
        else:
            record["result"] = body.get("result")
    return record


# ------------------------------------------------------------------ an attempt

def attempt(session, base: str, direction: str, index: int, args) -> dict:
    record: dict = {"attempt": index, "direction": direction,
                    "startedAt": datetime.now(timezone.utc).isoformat()}
    session.events = []
    session.dropped = 0
    session._t0 = time.monotonic()

    navigate(session, base)
    evaluate(session, BASE.WATCH_STATE)
    evaluate(session, BASE.WATCH_ERRORS)
    evaluate(session, INSTALL)
    record["workers"] = session.attach_workers()

    booted = None
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        booted = evaluate(session, READ_STATE) or {}
        if booted.get("state") in ("ready", "stopped", "expired"):
            break
        time.sleep(0.4)
    record["boot"] = booted
    if (booted or {}).get("state") != "ready":
        record["outcome"] = "VOID"
        record["why"] = f"page booted to {(booted or {}).get('state')!r}"
        return BASE.finish(session, record)

    session.set_file("#file", BASE.OWNER_DOCUMENT)
    opened = None
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        opened = evaluate(session, READ_STATE) or {}
        if (opened.get("state") == "ready"
                and BASE.OWNER_DOCUMENT.stem[:6] in (opened.get("doc") or "")):
            break
        if opened.get("state") in DEAD_STATES:
            break
        time.sleep(0.4)
    record["opened"] = opened
    if (opened or {}).get("state") != "ready":
        record["outcome"] = "VOID"
        record["why"] = f"the document did not open: {(opened or {}).get('state')!r}"
        return BASE.finish(session, record)
    time.sleep(4.0)
    record["workersAfterOpen"] = session.sync_workers()

    # THE LIVE WORKER, asked rather than assumed, and instrumented BEFORE the
    # first press so that the presses that DO move the caret are the
    # instrument's own non-emptiness check.
    found = live_worker(session)
    record["workerIdentity"] = found
    sid = found.get("chosen")
    if not sid:
        record["outcome"] = "VOID"
        record["why"] = "no attached worker realm carried __probe_on_event"
        return BASE.finish(session, record)
    record["workerSessionId"] = sid
    record["install"] = worker_eval(session, sid, INSTALL_WORKER, timeout=20.0)
    if not record["install"].get("returned") \
            or (record["install"].get("value") or {}).get("installed") != "yes":
        record["outcome"] = "VOID"
        record["why"] = "the worker-realm instrumentation did not install"
        return BASE.finish(session, record)

    frame = evaluate(session, BASE.READ_FRAME) or {}
    record["frameAfterOpen"] = frame
    room = (frame.get("deskScrollHeight") or 0) - (frame.get("deskClientHeight") or 0)
    record["scrollRoomPx"] = room
    if room <= 0:
        record["outcome"] = "VOID"
        record["why"] = "the document is not longer than the viewport"
        return BASE.finish(session, record)

    which = "first" if direction == "up" else "last"
    scan = evaluate(session, BASE.INK_ROWS
                    .replace("ARG_ROWS", "1600")
                    .replace("ARG_FROM_END", "false" if direction == "up" else "true"))
    row = BASE.text_row(scan or {}, which)
    record["inkRow"] = row
    if not row.get("found"):
        record["outcome"] = "VOID"
        record["why"] = row.get("why")
        return BASE.finish(session, record)

    y = f"{row['fraction']:.6f}"
    ink = evaluate(session, LINE_INK.replace("ARG_Y", y)) or {}
    fractions = caret_click_fractions(ink)
    record["clickFractions"] = dict(fractions, y=y)
    evaluate(session, BASE.CLEAR_LATENCY)
    mark(session, sid, "before-caret-click")
    evaluate(session, POINT_AT.replace("ARG_X", fractions["near"]).replace("ARG_Y", y))
    placed = None
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        placed = evaluate(session, READ_STATE) or {}
        if "定位游標" in (placed.get("latency") or ""):
            break
        time.sleep(0.3)
    record["placement"] = placed
    latency = (placed or {}).get("latency") or ""
    if "定位游標" not in latency or "失敗" in latency:
        record["outcome"] = "VOID"
        record["why"] = f"the caret could not be placed: {latency!r}"
        record["worker"] = worker_eval(session, sid, COLLECT, timeout=30.0)
        return BASE.finish(session, record)
    time.sleep(1.0)

    key, code = ("ArrowUp", 38) if direction == "up" else ("ArrowDown", 40)
    record["key"] = {"key": key, "windowsVirtualKeyCode": code,
                     "delivery": "CDP Input.dispatchKeyEvent rawKeyDown/keyUp"}
    trace = []
    still = 0
    died_at = None
    for step in range(1, args.presses + 1):
        prior = evaluate(session, BASE.READ_FRAME) or {}
        marked = mark(session, sid, f"press-{step}")
        BASE.press(session, key, code)
        moved = False
        after = prior
        watch = time.monotonic() + 3.0
        while time.monotonic() < watch:
            time.sleep(0.15)
            after = evaluate(session, BASE.READ_FRAME) or after
            if BASE.dead(after):
                break
            if (after.get("sinkTop") != prior.get("sinkTop")
                    or after.get("sinkLeft") != prior.get("sinkLeft")):
                moved = True
                break
        trace.append({"press": step, "moved": moved,
                      "engineIndexBefore": (marked.get("value") or {}).get("engineIndex"),
                      "postedIndexBefore": (marked.get("value") or {}).get("postedIndex"),
                      "sinkTop": after.get("sinkTop"),
                      "sinkLeft": after.get("sinkLeft"),
                      "state": after.get("state"),
                      "latency": after.get("latency"),
                      "pending": after.get("pending"),
                      "revision": after.get("revision")})
        if BASE.dead(after):
            died_at = step
            break
        still = 0 if moved else still + 1
        if still >= args.after_still:
            break
    record["pressTrace"] = trace
    record["pressesSpent"] = len(trace)
    record["pressesAtBoundary"] = still
    record["firstNonMovingPress"] = next(
        (t["press"] for t in trace if not t["moved"]), None)

    waited = 0.0
    frame = evaluate(session, BASE.READ_FRAME) or {}
    while waited < args.death_wait and not BASE.dead(frame):
        session.pump(0.5)
        waited += 0.5
        frame = evaluate(session, BASE.READ_FRAME) or frame
    record["frameAfterWait"] = frame
    record["waitedForDeathSeconds"] = round(waited, 1)
    mark(session, sid, "after-verdict")

    state_name = BASE.dead(frame)
    record["died"] = bool(state_name)
    record["deadState"] = state_name
    record["diedAtPress"] = died_at
    if state_name:
        no_checkpoint = (frame.get("noticeShow") == "1"
                         and frame.get("noticeRescue") == "none")
        record["outcome"] = "REPRODUCED" if no_checkpoint else "DIED_WITH_CHECKPOINT"
        record["noticeMatchesOwnerQuote"] = \
            (frame.get("noticeText") or "").strip() == BASE.OWNER_NOTICE
    else:
        record["outcome"] = "NOT_REPRODUCED"

    # ------------------------------------------------------- the three injections
    record["workerLiveness"] = BASE.worker_liveness(session)
    record["pendingInWorker"] = worker_eval(session, sid, READ_PENDING, timeout=15.0)

    wedged = None
    entries = ((record["pendingInWorker"].get("value") or {}).get("entries") or [])
    for entry in entries:
        if entry.get("operation") == "editorActionV2":
            wedged = entry
            break
    record["wedgedRequest"] = wedged

    action = "move-line-up" if direction == "up" else "move-line-down"
    handle = ((wedged or {}).get("payload") or {}).get("documentHandle")
    revision = ((wedged or {}).get("payload") or {}).get("expectedRevision")
    record["injectionInputs"] = {"action": action, "documentHandle": handle,
                                 "expectedRevision": revision,
                                 "source": "the worker's own pending map"}

    injections = {}
    # C first: without it, "the engine did not answer" and "my injection never
    # arrived" are the same silence.
    injections["control"] = inject(
        session, sid,
        {"protocolVersion": 1, "kind": "request", "requestId": RID_CONTROL,
         "operation": "f096ControlNoSuchOperation", "payload": {}},
        RID_CONTROL, args.dispatch_timeout, args.reply_wait)

    if handle is not None and revision is not None:
        injections["getState"] = inject(
            session, sid,
            {"protocolVersion": 1, "kind": "request", "requestId": RID_GETSTATE,
             "operation": "editorGetStateV2",
             "payload": {"documentHandle": handle}},
            RID_GETSTATE, args.dispatch_timeout, args.reply_wait)
        injections["action"] = inject(
            session, sid,
            {"protocolVersion": 1, "kind": "request", "requestId": RID_ACTION,
             "operation": "editorActionV2",
             "payload": {"documentHandle": handle, "expectedRevision": revision,
                         "action": action, "extendSelection": False,
                         "enabled": False}},
            RID_ACTION, args.dispatch_timeout, args.reply_wait)
    else:
        injections["getState"] = {"skipped": "no wedged editorActionV2 payload"}
        injections["action"] = {"skipped": "no wedged editorActionV2 payload"}
    record["injections"] = injections

    record["worker"] = worker_eval(session, sid, COLLECT, timeout=60.0)
    record["cell"] = classify(record)
    return BASE.finish(session, record)


def classify(record: dict) -> dict:
    """Read the registered table back; do not compose a new one.

    Every branch here is a row of §2.1 / §2.2 of
    TASK-2026-09-09-096-does-the-engine-thread-still-answer.md.
    """
    out: dict = {}
    inj = record.get("injections") or {}
    control = inj.get("control") or {}
    get_state = inj.get("getState") or {}
    action = inj.get("action") or {}

    out["controlAnswered"] = bool(control.get("answered"))
    out["controlCode"] = control.get("code")
    out["getStateAnswered"] = bool(get_state.get("answered"))
    out["actionAnswered"] = bool(action.get("answered"))
    out["actionCode"] = action.get("code")
    out["getStateDispatchReturned"] = \
        (get_state.get("dispatch") or {}).get("returned")

    if record.get("outcome") != "REPRODUCED":
        out["engineCell"] = "NOT_APPLICABLE"
        out["why"] = "the attempt did not reproduce 096"
        return out
    if not out["controlAnswered"]:
        out["engineCell"] = "VOID_INSTRUMENT"
        out["why"] = ("the injection-route control was not answered; nothing "
                      "about the engine is licensed")
        return out
    if out["getStateDispatchReturned"] is False:
        out["engineCell"] = "DISPATCH_DID_NOT_RETURN"
        out["why"] = ("the worker's JS thread did not return from the wasm "
                      "submit path; same family as (c), reported as its own shape")
        return out
    if out["actionAnswered"] and out["actionCode"] != "BUSY":
        out["engineCell"] = "VOID_POSITIVE_CONTROL"
        out["why"] = (f"the positive control answered {out['actionCode']!r}, "
                      "not BUSY")
        return out
    if out["getStateAnswered"] and out["actionAnswered"]:
        out["engineCell"] = "C_EXCLUDED"
        out["why"] = ("the engine thread popped and executed both injected "
                      "commands after the verdict")
    elif not out["getStateAnswered"] and not out["actionAnswered"]:
        out["engineCell"] = "C_SURVIVES"
        out["why"] = ("the control answered and neither engine command did; "
                      "(a) and (b) are downstream of a loop that is not "
                      "running and become undecidable here, not excluded")
        return out
    else:
        out["engineCell"] = "SPLIT_NO_CELL"
        out["why"] = "exactly one of the two engine commands answered"
        return out

    # ---- (a) vs (b), from the engine-event capture
    #
    # TWO CHANGES FORCED BY SHAKEDOWN 1, both before any counted attempt and
    # both recorded in the protocol's execution record (AGENTS.md §9).
    #
    # 1. THE WINDOW ENDS AT THE VERDICT, not at the end of the buffer.  The
    #    first shakedown was classified `B` by exactly two events -- the replies
    #    to this probe's OWN injections, at ms 31747 and 32049 against a verdict
    #    at ms 31743.  A false B produced by the instrument.
    # 2. THE DISCRIMINATOR IS `lok`, not "any engine emission".  `tile`,
    #    `clicked` and `editor-state-result` are answers to commands, not core
    #    broadcasts.  `onLokCallback` (src/probe_engine.cpp:2372-2381) emits one
    #    `{"type":"lok","id":<type>,"payload":<verbatim>}` line for EVERY LOK
    #    callback -- unconditionally, before the type switch and outside every
    #    #ifdef.  It is the exact boundary the question is about, and it already
    #    ships: the protocol's §2.3 said a trampoline log would need an engine
    #    edit and a relink, and it was wrong.
    worker = (record.get("worker") or {}).get("value") or {}
    events = worker.get("engine") or []
    marks = {m.get("label"): m for m in (worker.get("marks") or [])}
    boundary = record.get("firstNonMovingPress")
    out["engineEventsTotal"] = len(events)
    out["engineEventsDropped"] = worker.get("engineDropped")
    out["boundaryPress"] = boundary
    if not events:
        out["abCell"] = "VOID_NO_CAPTURE"
        out["why2"] = "the wrapper saw no engine events at all"
        return out

    # THE POSITIVE COMPARISON: what a press that DID move the caret broadcast.
    # A probe that cannot print a different value is not a probe.
    moving_windows = []
    for step in (record.get("pressTrace") or []):
        if not step.get("moved"):
            continue
        start = step.get("engineIndexBefore")
        nxt = marks.get(f"press-{step['press'] + 1}") \
            or marks.get("after-verdict")
        end = nxt.get("engineIndex") if nxt else len(events)
        if start is None or end is None or end <= start:
            continue
        window = events[start:end]
        moving_windows.append({
            "press": step["press"],
            "events": len(window),
            "lokIds": _lok_ids(window),
            "types": _types(window),
            "completions": _completions(window),
        })
    out["movingPresses"] = moving_windows
    out["movingPressesBroadcast"] = any(w["lokIds"] for w in moving_windows)
    if not out["movingPressesBroadcast"]:
        out["abCell"] = "VOID_NO_CAPTURE"
        out["why2"] = ("no LOK callback is attributable to a press that moved "
                       "the caret, so the capture proves nothing")
        return out

    start = (marks.get(f"press-{boundary}") or {}).get("engineIndex") \
        if boundary else None
    end = (marks.get("after-verdict") or {}).get("engineIndex")
    if start is None or end is None:
        out["abCell"] = "VOID_NO_CAPTURE"
        out["why2"] = "the boundary or verdict mark is missing"
        return out
    after = events[start:end]
    out["windowIndices"] = [start, end]
    out["engineEventsInWindow"] = len(after)
    out["engineEventTypesInWindow"] = _types(after)
    out["lokIdsInWindow"] = _lok_ids(after)
    out["sourceSequenceAfterVerdict"] = (
        ((record.get("injections") or {}).get("getState") or {})
        .get("result") or {}).get("sourceSequence")

    wedged_id = (record.get("wedgedRequest") or {}).get("requestId")
    completed = [e for e in after if _is_json(e.get("raw"))
                 and json.loads(e["raw"]).get("type") == "editor-action-completed"
                 and json.loads(e["raw"]).get("requestId") == wedged_id]
    if completed:
        out["abCell"] = "NONE_OF_THEM"
        out["why2"] = ("the engine emitted editor-action-completed for the "
                       "wedged request; the answer was lost above the engine")
        return out
    if not out["lokIdsInWindow"]:
        out["abCell"] = "A"
        out["why2"] = ("core did not invoke the registered LOK callback once "
                       "between the boundary press and the verdict, while the "
                       "same session's moving presses did invoke it")
        return out
    parse_errors = [e for e in after if _is_json(e.get("raw"))
                    and json.loads(e["raw"]).get("type")
                    == "editor-callback-parse-error"]
    if parse_errors:
        out["abCell"] = "B_PARSE"
        out["why2"] = ("a LOK callback arrived and this build could not read "
                       "its payload, so the completion was never attempted")
        return out
    out["abCell"] = "B"
    out["why2"] = ("core invoked the LOK callback after the boundary press "
                   "and the wedged request was not completed")
    return out


def _decode(window: list) -> list:
    out = []
    for entry in window:
        if _is_json(entry.get("raw")):
            out.append(json.loads(entry["raw"]))
    return out


def _types(window: list) -> list:
    return sorted({o.get("type") for o in _decode(window)})


def _lok_ids(window: list) -> list:
    return sorted({o.get("id") for o in _decode(window)
                   if o.get("type") == "lok"})


def _completions(window: list) -> list:
    return [o.get("completion") for o in _decode(window)
            if o.get("type") in ("editor-action-completed",
                                 "editor-caret-placed",
                                 "editor-selection-completed")]


def _is_json(text) -> bool:
    if not isinstance(text, str):
        return False
    try:
        json.loads(text)
        return True
    except Exception:                               # noqa: BLE001
        return False


# --------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="e2-editor-v8")
    parser.add_argument("--direction", action="append",
                        choices=("up", "down"), default=None)
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--presses", type=int, default=40)
    parser.add_argument("--after-still", type=int, default=6)
    parser.add_argument("--death-wait", type=float, default=90.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--dispatch-timeout", type=float, default=25.0)
    parser.add_argument("--reply-wait", type=float, default=25.0)
    parser.add_argument("--viewport", default="1920x1080")
    parser.add_argument("--out")
    parser.add_argument("--label", default="run")
    args = parser.parse_args()
    directions = args.direction or ["up", "down"]

    root = PROJECT / "dist"
    manifest = root / "profiles" / args.profile / "sdk-manifest.json"
    source = (PROJECT / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
    page, pin_before, wasm = repointed_page(source, args.profile, manifest)
    page_sha = hashlib.sha256(page.encode("utf-8")).hexdigest()
    document_sha = hashlib.sha256(BASE.OWNER_DOCUMENT.read_bytes()).hexdigest()

    report = {
        "schemaVersion": 1,
        "finding": "096",
        "evidenceClass": "diagnostic",
        "label": args.label,
        "protocol": "handoff/tasks/TASK-2026-09-09-096-does-the-engine-thread-"
                    "still-answer.md, registered before this probe was written",
        "question": "after the session dies, does the engine thread still "
                    "answer, and did anything reach it around the press?",
        "mayNotNameACause": True,
        "profile": args.profile,
        "pageSha256": page_sha,
        "pagePinBefore": pin_before,
        "wasmSha256": wasm,
        "document": str(BASE.OWNER_DOCUMENT),
        "documentSha256": document_sha,
        "documentIsTheOwners": document_sha == BASE.OWNER_DOCUMENT_SHA256,
        "viewport": args.viewport,
        "attemptsPerDirection": args.attempts,
        "injectedRequestIds": {"control": RID_CONTROL,
                               "getState": RID_GETSTATE, "action": RID_ACTION},
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "attempts": [],
    }

    scratch = Path(tempfile.mkdtemp(prefix=f"f096e-{args.profile}-"))
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
        session = BASE.BufferingSession("cold")
        report["browser"] = session.version
        width, _, height = args.viewport.partition("x")
        session.call("Emulation.setDeviceMetricsOverride",
                     {"width": int(width), "height": int(height),
                      "deviceScaleFactor": 1, "mobile": False})
        session.call("Log.enable")
        for direction in directions:
            for index in range(1, args.attempts + 1):
                entry = attempt(session, base, direction, index, args)
                entry["profile"] = args.profile
                report["attempts"].append(entry)
                cell = entry.get("cell") or {}
                print(f"[{args.profile}] {direction} #{index}: "
                      f"{entry.get('outcome')} engine={cell.get('engineCell')} "
                      f"ab={cell.get('abCell')} "
                      f"control={cell.get('controlCode')} "
                      f"action={cell.get('actionCode')}",
                      file=sys.stderr, flush=True)
                if args.out:
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
        cell = entry.get("cell") or {}
        key = (f"{entry['direction']}:{entry.get('outcome')}:"
               f"{cell.get('engineCell')}:{cell.get('abCell')}")
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
