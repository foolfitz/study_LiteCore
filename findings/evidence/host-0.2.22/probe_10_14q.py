#!/usr/bin/env python3
"""Task 10-14n/10-14o/10-14q: the owner's two symptoms on host 0.2.20 / the fixes for 0.2.21 and 0.2.22, on the owner's own path.

10-14q adds `hold-2s-in-text`: a 2 s hold of Backspace with the caret inside text, the repeats FLAGGED as the
driver sends them (WebDriver/CDP), and the summary counts the deletes the engine answered after the key-up (finding 144).

10-14o adds the control arm `burst-1s-in-text` (the same burst with the caret inside text: every press deletes).

Files -> open -> the editor route, then real input (WebDriver actions in Firefox,
CDP input events in Chrome): mouse-wheel scrolling for the page number, a real
pointer click on the first line, Home, Backspace.  Nothing synthetic is dispatched
into the page; the page is only READ (DOM state, plus a post-hoc hook on
Worker.prototype.postMessage that logs every request/response/event with the
page's clock, so the engine's answers are timed from the page).

Fixtures are uploaded into a folder this probe creates and deletes.  No product
byte is touched.

  probe_10_14n.py --out DIR --browser firefox --doc long60 --arms page-number,press-after-click-home
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import traceback
import urllib.parse
from pathlib import Path
from typing import Any

TOOLS = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
sys.path.insert(0, str(TOOLS))
import check_m3_production_ui as ui  # noqa: E402
import probe_hand_test_0212 as held  # noqa: E402
from check_m3_locks import login, open_from_files  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, Instance  # noqa: E402
from create_long_document import build as build_long_document  # noqa: E402
from probe_m3_gate0_coep import utc_now  # noqa: E402
from r7_support import evaluate  # noqa: E402

INSTRUMENT = r"""(() => {
  if (window.__n) return 'already';
  const t0 = performance.now(); const now = () => Math.round((performance.now() - t0) * 10) / 10;
  const N = window.__n = { t0Epoch: Date.now(), log: [], workers: [], protocolVersion: null, documentHandle: null, requests: new Map() };
  const log = (e) => { e.t = now(); N.log.push(e); };
  const sel = (s) => (s && typeof s === 'object') ? { collapsed: s.collapsed ?? null, n: Array.isArray(s.rectangles) ? s.rectangles.length : null } : null;
  const seen = (w, data) => {
    if (!data || typeof data !== 'object') return;
    if (data.kind === 'event') {
      if (data.event === 'editor-state') log({ k: 'ev', w, caret: data.caret ?? null, seq: data.sourceSequence ?? null, dsc: data.documentSizeChangedCount ?? null, rev: data.revision ?? null, source: data.source ?? null, sel: sel(data.selection) });
      else log({ k: 'ev', w, event: data.event, detail: JSON.stringify(data).slice(0, 300) });
      return;
    }
    if (data.kind !== 'response') return;
    const rq = N.requests.get(data.requestId) || {}; N.requests.delete(data.requestId);
    const v = data.ok ? data.result : data.error;
    const e = { k: 'rs', w, rq: data.requestId, op: rq.op ?? null, action: rq.action ?? null, ok: data.ok,
                sinceRq: rq.t != null ? Math.round((now() - rq.t) * 10) / 10 : null };
    if (!data.ok) e.err = (v && typeof v === 'object') ? { code: v.code ?? null, message: String(v.message ?? '').slice(0, 240), mergeKey: v.mergeKey ?? v.details?.mergeKey ?? null } : String(v).slice(0, 240);
    if (v && typeof v === 'object') {
      if (rq.op === 'pageRectangles') { e.parts = v.parts ?? null; e.nRects = typeof v.rectangles === 'string' ? v.rectangles.split(';').length : (Array.isArray(v.rectangles) ? v.rectangles.length : null); e.rev = v.revision ?? null; e.docH = v.documentHeightTwips ?? null; if (rq.ask) { e.ask = true; e.rects = typeof v.rectangles === 'string' ? v.rectangles.slice(0, 200) : null; } }
      else if (rq.op === 'paint') { e.changed = v.documentSizeChanged ?? null; e.docH = v.documentHeightTwips ?? null; }
      else if (/^editor/.test(rq.op || '')) { e.completion = v.completion ?? null; e.changed = v.changed ?? null; e.rev = v.revision ?? null; e.beforeRev = v.beforeRevision ?? null; e.boundaryNoop = v.boundaryNoop ?? null; e.keyUndo = v.keyUndo ? { restorePresses: v.keyUndo.restorePresses ?? null, comment: v.keyUndo.comment ?? null } : null; e.stateCaret = v.state?.caret ?? null; e.stateSel = sel(v.state?.selection); e.selectionType = v.selectionType ?? v.state?.selectionType ?? null; }
      else if (rq.op === 'open' || v.documentHandle !== undefined) { e.docH = v.height ?? null; if (v.documentHandle !== undefined && N.documentHandle === null) N.documentHandle = v.documentHandle; }
    }
    log(e);
  };
  const proto = Worker.prototype, post = proto.postMessage;
  proto.postMessage = function (message, transfer) {
    let w = N.workers.indexOf(this);
    if (w < 0) { w = N.workers.push(this) - 1; this.addEventListener('message', (ev) => { try { seen(w, ev.data); } catch (err) { log({ k: 'hookError', err: String(err) }); } }); log({ k: 'worker', w }); }
    if (message && message.kind === 'request') {
      const prior = N.requests.get(message.requestId) || {};
      if (message.protocolVersion !== undefined && !prior.ask) N.protocolVersion = message.protocolVersion;
      if (message.payload && message.payload.documentHandle !== undefined && !prior.ask) N.documentHandle = message.payload.documentHandle;
      N.requests.set(message.requestId, { ...prior, op: message.operation, action: message.payload?.action, t: now() });
      log({ k: 'rq', w, rq: message.requestId, op: message.operation, action: message.payload?.action ?? null });
    }
    return post.call(this, message, transfer);
  };
  const $ = (s) => document.querySelector(s);
  const pill = $('#state-pill'), lat = $('#s-latency'), gen = $('#s-generation'), rev = $('#s-revision'), pend = $('#s-pending'),
        toast = $('#toast'), notice = $('#notice'), ps = $('#page-status'), desk = $('#desk'), sink = $('#sink');
  const read = () => ({ state: pill.dataset.state, label: pill.textContent, latency: lat.textContent, gen: gen.textContent, rev: rev.textContent,
    pending: pend.textContent, toast: toast.classList.contains('show') ? toast.textContent : null, limit: notice.dataset.limit ?? null,
    ps: (!ps || ps.hidden) ? null : ps.textContent, psHidden: ps ? ps.hidden : null, scroll: desk.scrollTop, sinkDisabled: sink.disabled,
    focus: document.activeElement === sink ? 'sink' : (document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : null) });
  let last = '';
  const tick = () => { const r = read(); const k = JSON.stringify(r); if (k !== last) { last = k; log({ k: 'st', ...r }); } };
  new MutationObserver(tick).observe(document.body, { attributes: true, childList: true, characterData: true, subtree: true });
  desk.addEventListener('scroll', tick, { passive: true });
  window.addEventListener('keydown', (e) => log({ k: 'kd', key: e.key, repeat: e.repeat, ctrl: e.ctrlKey,
    focus: document.activeElement === sink ? 'sink' : (document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : null), sinkDisabled: sink.disabled }), true);
  window.addEventListener('keyup', (e) => log({ k: 'ku', key: e.key }), true);
  window.addEventListener('pointerdown', (e) => log({ k: 'pd', x: e.clientX, y: e.clientY, target: e.target && (e.target.id || e.target.tagName) }), true);
  window.addEventListener('wheel', (e) => log({ k: 'wheel', dy: e.deltaY, target: e.target && (e.target.id || e.target.tagName) }), { capture: true, passive: true });
  sink.addEventListener('beforeinput', (e) => log({ k: 'bi', type: e.inputType }), true);
  window.__nread = read; window.__nnow = now;
  tick(); return 'installed';
})()"""
LOG_LENGTH = "(() => window.__n.log.length)()"
READ_LOG = "(() => window.__n.log.slice(ARG_FROM))()"
STATE_NOW = "(() => window.__nread())()"
ASK_RECTS = """(() => { const N = window.__n; const w = N.workers[N.workers.length - 1]; if (!w || N.documentHandle === null) return null;
  const id = 900000 + Math.floor(Math.random() * 100000);
  N.requests.set(id, { op: 'pageRectangles', ask: true, t: window.__nnow() });
  w.postMessage({ protocolVersion: N.protocolVersion, kind: 'request', requestId: id, operation: 'pageRectangles', payload: { documentHandle: N.documentHandle } });
  return id; })()"""
ASK_ANSWER = "(() => window.__n.log.find((e) => e.k === 'rs' && e.rq === ARG_ID) || null)()"
GEOMETRY = """(() => { const $ = (s) => document.querySelector(s);
  const ps = $('#page-status') || Object.assign(document.createElement('div'), { hidden: true }), desk = $('#desk'), root = $('#litecore-editor-root'), paper = $('#paper'), sb = $('.statusbar');
  const r = ps.getBoundingClientRect(), d = desk.getBoundingClientRect(), p = paper.getBoundingClientRect(), cs = getComputedStyle(ps);
  const at = (r.width && r.height) ? document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) : null;
  return { present: !!$('#page-status'), hidden: ps.hidden, text: ps.textContent, display: cs.display, visibility: cs.visibility, opacity: cs.opacity, fontSize: cs.fontSize,
    color: cs.color, background: cs.backgroundColor, rect: [r.left, r.top, r.width, r.height].map(Math.round),
    inViewport: r.height > 0 && r.top >= 0 && r.bottom <= window.innerHeight,
    elementAtCentre: at ? (at.id || String(at.className) || at.tagName) : null,
    desk: { top: Math.round(d.top), bottom: Math.round(d.bottom), scrollTop: desk.scrollTop, clientHeight: desk.clientHeight, scrollHeight: desk.scrollHeight },
    paper: { top: Math.round(p.top), height: Math.round(p.height), width: Math.round(p.width), left: Math.round(p.left) },
    statusbarDisplay: sb ? getComputedStyle(sb).display : null,
    root: root ? Math.round(root.getBoundingClientRect().height) : null, inner: [window.innerWidth, window.innerHeight],
    content: (() => { const c = document.getElementById('content') || document.querySelector('#content-vue, main'); if (!c) return null; const cr = c.getBoundingClientRect(); const ccs = getComputedStyle(c); return { id: c.id, rect: [cr.left, cr.top, cr.width, cr.height].map(Math.round), overflow: ccs.overflow, radius: ccs.borderRadius, margin: ccs.margin }; })(),
    pageScroll: { scrollHeight: document.documentElement.scrollHeight, clientHeight: document.documentElement.clientHeight, bodyScrollHeight: document.body.scrollHeight },
    psTextRect: (() => { const r = document.createRange(); r.selectNodeContents(ps); const b = r.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map((v) => Math.round(v * 10) / 10); })(),
    scope: typeof CSSScopeRule, hostScope: (JSON.parse(document.documentElement.getAttribute('data-litecore') || '{}')).scope ?? null,
    resources: performance.getEntriesByType('resource').map((e) => e.name).filter((n) => /sdk-manifest|sdk-worker|probe\\.wasm/.test(n)).slice(0, 6) }; })()"""
SCREENSHOT_NOTE = "(() => ({ scroll: document.querySelector('#desk').scrollTop, ps: document.querySelector('#page-status').textContent }))()"

OURS = "probe_|judge_|check_m3|run_e2_c|run_merge|run_v20|probe_10_14n"

# Where the first text line is, as fractions of #paper (x of the page width, y of the
# whole document's height): the long fixture from its page rectangle (284, 284, 11906,
# 16838), a 0.7874 in (1134 twips) top margin and 60 pages of 17122 twips pitch
# (document height 1027604 twips, read from the engine in the first run); the owner
# text from check_m3_production_ui.FIRST_LINE (Q02).
FIRST_LINE_FRACTIONS = {
    "long60": (2018 / 11906, 1598 / 1027604),
    "owner16630": (2018 / 11906, 1598 / 1027604),
    "pmpc": (float(ui.FIRST_LINE[0]), float(ui.FIRST_LINE[1])),
    "owner7340": (float(ui.FIRST_LINE[0]), float(ui.FIRST_LINE[1])),
}
DOC_KIND = {"value": "long60"}


def sh(argv: list[str]) -> str:
    return subprocess.run(argv, capture_output=True, text=True, timeout=30).stdout.strip()


def preflight() -> dict[str, Any]:
    wallet = sh(["busctl", "--user", "get-property", "org.freedesktop.secrets",
                 "/org/freedesktop/secrets/collection/kdewallet", "org.freedesktop.Secret.Collection", "Locked"])
    # this probe's own process and the shell that queued it are not "ours running"
    ours = [line for line in sh(["pgrep", "-af", OURS]).splitlines()
            if "pgrep" not in line and not any(own in line for own in ("probe_10_14n", "probe_10_14o", "probe_10_14q"))]
    out = {"at": utc_now(), "kwalletLocked": wallet, "pgrepChrome": sh(["pgrep", "-c", "chrome"]),
           "chromeBrowserProcesses": sh(["pgrep", "-fc", "/opt/google/chrome/chrome( |$)"]),
           "pgrepFirefox": sh(["pgrep", "-c", "firefox"]), "oursRunning": ours,
           "load": Path("/proc/loadavg").read_text().split()[:3]}
    if wallet.strip() == "b true":
        raise SystemExit(f"KWallet is locked: {out}")
    if ours:
        raise SystemExit(f"something of ours is running: {ours}")
    return out


# ---------------------------------------------------------------- real input

def wheel(session, kind: str, x: int, y: int, dy: int) -> None:
    """One mouse-wheel scroll at viewport point (x, y)."""
    if kind == "chrome":
        session.call("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": x, "y": y, "deltaX": 0, "deltaY": dy})
        return
    session.command("POST", "/actions", {"actions": [{"type": "wheel", "id": "wheel", "actions": [
        {"type": "scroll", "x": x, "y": y, "deltaX": 0, "deltaY": dy, "origin": "viewport"}]}]})
    session.command("DELETE", "/actions")


def real_click(session, kind: str, x: float, y: float) -> None:
    """A real primary-button click at viewport point (x, y)."""
    if kind == "chrome":
        base = {"x": x, "y": y, "button": "left", "clickCount": 1}
        session.call("Input.dispatchMouseEvent", {**base, "type": "mouseMoved", "button": "none"})
        session.call("Input.dispatchMouseEvent", {**base, "type": "mousePressed"})
        session.call("Input.dispatchMouseEvent", {**base, "type": "mouseReleased"})
        return
    session.command("POST", "/actions", {"actions": [{"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"},
        "actions": [{"type": "pointerMove", "x": int(x), "y": int(y), "origin": "viewport"},
                    {"type": "pointerDown", "button": 0}, {"type": "pointerUp", "button": 0}]}]})
    session.command("DELETE", "/actions")


def burst_key(session, kind: str, key: str, hold_ms: int, delay_ms: int = 500, interval_ms: int = 30) -> dict[str, Any]:
    """A held key as an X server WITHOUT detectable autorepeat delivers it: a press,
    then from `delay_ms` on a RELEASE+PRESS pair every `interval_ms` (so every
    keydown has repeat === false), and a release at the end."""
    times = [0] + list(range(delay_ms, hold_ms + 1, interval_ms))
    release = times[-1] + interval_ms // 2
    if kind == "chrome":
        name, code, vk = ui.CDP_KEYS[key]
        base = {"key": name, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk, "modifiers": 0}
        start, sent = time.monotonic(), []
        for i, at in enumerate(times):
            wait = start + at / 1000 - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            if i:
                session.call("Input.dispatchKeyEvent", {**base, "type": "keyUp"})
            sent.append(round((time.monotonic() - start) * 1000, 1))
            session.call("Input.dispatchKeyEvent", {**base, "type": "rawKeyDown"})
        wait = start + release / 1000 - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        session.call("Input.dispatchKeyEvent", {**base, "type": "keyUp"})
        return {"scheduledMs": times, "releaseMs": release, "sentMs": sent, "presses": len(times)}
    value = ui.WD_KEYS[key]
    actions: list[dict[str, Any]] = []
    previous = 0
    for i, at in enumerate(times):
        if at > previous:
            actions.append({"type": "pause", "duration": at - previous})
        if i:
            actions.append({"type": "keyUp", "value": value})
        actions.append({"type": "keyDown", "value": value})
        previous = at
    actions += [{"type": "pause", "duration": release - previous}, {"type": "keyUp", "value": value}]
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": actions}]})
    session.command("DELETE", "/actions")
    return {"scheduledMs": times, "releaseMs": release, "presses": len(times)}


def ctrl_key(session, kind: str, key: str) -> None:
    if kind == "chrome":
        name, code, vk = ui.CDP_KEYS[key]
        for phase in ("rawKeyDown", "keyUp"):
            session.call("Input.dispatchKeyEvent", {"type": phase, "key": name, "code": code, "windowsVirtualKeyCode": vk,
                                                    "nativeVirtualKeyCode": vk, "modifiers": 2})
        return
    ctrl = ""
    value = ui.WD_KEYS.get(key, key)
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": [
        {"type": "keyDown", "value": ctrl}, {"type": "keyDown", "value": value}, {"type": "keyUp", "value": value}, {"type": "keyUp", "value": ctrl}]}]})
    session.command("DELETE", "/actions")


# ---------------------------------------------------------------- reading

def log_from(session, start: int) -> list[dict[str, Any]]:
    return evaluate(session, READ_LOG.replace("ARG_FROM", str(start))) or []


def ask_rectangles(session, limit: float = 30) -> dict[str, Any] | None:
    ask_id = evaluate(session, ASK_RECTS)
    if ask_id is None:
        return None
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        answer = evaluate(session, ASK_ANSWER.replace("ARG_ID", str(ask_id)))
        if answer:
            return answer
        time.sleep(0.2)
    return {"timedOut": True, "askId": ask_id}


def settle(session, quiet_s: float = 3.0, limit: float = 90) -> dict[str, Any]:
    """Until the session has been ready with an empty queue for quiet_s, or the limit notice settled."""
    started, since, seen = time.monotonic(), None, {}
    while time.monotonic() - started < limit:
        seen = evaluate(session, STATE_NOW) or {}
        if seen.get("limit") in ("saved", "failed", "lost", "clean", "pending"):
            return {"by": "limit", "limit": seen.get("limit"), "afterS": round(time.monotonic() - started, 2), "last": seen}
        if seen.get("state") == "ready" and str(seen.get("pending")) == "0":
            since = since or time.monotonic()
            if time.monotonic() - since >= quiet_s:
                return {"by": "ready", "afterS": round(time.monotonic() - started, 2), "last": seen}
        else:
            since = None
        time.sleep(0.1)
    return {"by": "timeout", "afterS": round(time.monotonic() - started, 2), "last": seen}


def first_line_point(session, rects_answer: dict[str, Any] | None) -> dict[str, Any]:
    """Viewport coordinates of the first page's first text line: the fixture's known
    fractions of #paper when it has them, else the engine's own first page rectangle."""
    geometry = evaluate(session, GEOMETRY)
    paper = geometry["paper"]
    known = FIRST_LINE_FRACTIONS.get(DOC_KIND["value"])
    if known:
        x = paper["left"] + paper["width"] * known[0]
        y = paper["top"] + paper["height"] * known[1]
        return {"geometry": geometry, "point": [round(x, 1), round(y, 1)], "fractions": known}
    doc_h = rects_answer.get("docH") if rects_answer else None
    first = None
    if rects_answer and rects_answer.get("rects"):
        try:
            first = [int(v) for v in rects_answer["rects"].split(";")[0].split(",")]
        except ValueError:
            first = None
    if first is None or not doc_h:
        return {"geometry": geometry, "point": None}
    x_twips = first[0] + 1134 + 600            # inside the text column
    y_twips = first[1] + 1134 + 180            # the first line (a 2 cm top margin; a larger margin puts this in the margin, which Writer maps to the first line)
    x = paper["left"] + paper["width"] * (x_twips / 11906)
    y = paper["top"] + paper["height"] * (y_twips / doc_h)
    return {"geometry": geometry, "point": [round(x, 1), round(y, 1)], "twips": [x_twips, y_twips], "docH": doc_h}


# ---------------------------------------------------------------- arms

def arm_page_number(session, kind: str, record: dict[str, Any]) -> None:
    g0 = evaluate(session, GEOMETRY)
    record["geometryAtOpen"] = g0
    record["askAtOpen"] = ask_rectangles(session)
    desk = g0["desk"]
    cx = g0["inner"][0] // 2
    cy = (desk["top"] + desk["bottom"]) // 2
    steps = []
    start = evaluate(session, LOG_LENGTH)
    for i in range(14):
        wheel(session, kind, cx, cy, 700)
        time.sleep(0.6)
        g = evaluate(session, GEOMETRY)
        steps.append({"i": i, "dy": 700, "scrollTop": g["desk"]["scrollTop"], "hidden": g["hidden"], "text": g["text"],
                      "rect": g["rect"], "inViewport": g["inViewport"], "display": g["display"]})
        if i == 6:
            record.setdefault("_shots", []).append(("mid", session.screenshot()))
    for i in range(3):
        wheel(session, kind, cx, cy, 3000)
        time.sleep(0.6)
        g = evaluate(session, GEOMETRY)
        steps.append({"i": 14 + i, "dy": 3000, "scrollTop": g["desk"]["scrollTop"], "hidden": g["hidden"], "text": g["text"],
                      "rect": g["rect"], "inViewport": g["inViewport"]})
    wheel(session, kind, cx, cy, -40000)
    time.sleep(0.8)
    g = evaluate(session, GEOMETRY)
    steps.append({"i": "top", "dy": -40000, "scrollTop": g["desk"]["scrollTop"], "hidden": g["hidden"], "text": g["text"], "rect": g["rect"]})
    record["steps"] = steps
    record["scrollLog"] = log_from(session, start)
    record["askAfterScroll"] = ask_rectangles(session)
    record["geometryAtEnd"] = evaluate(session, GEOMETRY)


def to_start(session, kind: str, record: dict[str, Any], how: str) -> None:
    """Put the caret at the document start the way a user would."""
    g = evaluate(session, GEOMETRY)
    cx = g["inner"][0] // 2
    cy = (g["desk"]["top"] + g["desk"]["bottom"]) // 2
    wheel(session, kind, cx, cy, -40000)
    time.sleep(0.5)
    rects = ask_rectangles(session) if how != "click-home-fast" else None
    record["askBeforeClick"] = rects
    point = first_line_point(session, rects)
    record["firstLine"] = point
    if how in ("click-home", "click-home-fast"):
        if not point["point"]:
            raise RuntimeError("no first-line point")
        real_click(session, kind, *point["point"])
        record["clickState"] = ui.until(session, lambda s: "定位游標" in (s.get("latency") or ""), 40)
        if how == "click-home":
            record["clickSettled"] = settle(session, 1.5, 60)
        ui.press(session, kind, "Home")
        time.sleep(0.6 if how == "click-home" else 0.3)
        if how == "click-home":
            record["homeSettled"] = settle(session, 1.5, 60)
    elif how == "ctrl-home":
        if point["point"]:
            real_click(session, kind, *point["point"])
            record["clickState"] = ui.until(session, lambda s: "定位游標" in (s.get("latency") or ""), 40)
            record["clickSettled"] = settle(session, 1.5, 60)
        # the owner looks for page numbers first: scroll down several pages, then Ctrl+Home
        for _ in range(6):
            wheel(session, kind, cx, cy, 1500)
            time.sleep(0.2)
        time.sleep(0.6)
        record["scrolledBeforeCtrlHome"] = evaluate(session, STATE_NOW)
        ctrl_key(session, kind, "Home")
        time.sleep(0.6)
        record["ctrlHomeSettled"] = settle(session, 1.5, 60)
    elif how == "click-in-text":
        # the fourth body line of page 1, mid-line: a Backspace here deletes a character
        fr = FIRST_LINE_FRACTIONS.get(DOC_KIND["value"]) or (0.17, 0.0016)
        geometry = point["geometry"]
        paper = geometry["paper"]
        x = paper["left"] + paper["width"] * 0.45
        y = paper["top"] + paper["height"] * (fr[1] + 1500 / 1027604)
        record["inTextPoint"] = [round(x, 1), round(y, 1)]
        real_click(session, kind, x, y)
        record["clickState"] = ui.until(session, lambda s: "定位游標" in (s.get("latency") or ""), 40)
        record["clickSettled"] = settle(session, 1.5, 60)
    elif how == "none":
        record["noPlacement"] = evaluate(session, STATE_NOW)


def arm_owner_sequence(session, kind: str, record: dict[str, Any]) -> None:
    """Open, look for the page number by wheeling down a dozen screens and back,
    click the first line, Backspace.  No settle between the steps."""
    g = evaluate(session, GEOMETRY)
    cx, cy = g["inner"][0] // 2, (g["desk"]["top"] + g["desk"]["bottom"]) // 2
    seen = []
    for _ in range(12):
        wheel(session, kind, cx, cy, 700)
        time.sleep(0.25)
        seen.append(evaluate(session, "(() => { const p = document.querySelector('#page-status'); return [document.querySelector('#desk').scrollTop, (!p || p.hidden) ? null : p.textContent]; })()"))
    wheel(session, kind, cx, cy, -40000)
    time.sleep(0.4)
    record["pageNumbersSeen"] = seen
    arm_backspace(session, kind, record, "click-home-fast")


def arm_backspace(session, kind: str, record: dict[str, Any], placement: str, presses: int = 1,
                  gap_ms: int = 400, hold_ms: int = 0, type_after_ms: int | None = None, burst_ms: int = 0) -> None:
    to_start(session, kind, record, placement)
    record["stateBeforeKey"] = evaluate(session, STATE_NOW)
    record["askBeforeKey"] = ask_rectangles(session) if placement != "click-home-fast" else None
    start = evaluate(session, LOG_LENGTH)
    t_key = time.monotonic()
    if burst_ms:
        record["sent"] = burst_key(session, kind, "Backspace", burst_ms)
    elif hold_ms:
        held.OPTIONS.update(holdMs=hold_ms, holdDelayMs=500, holdIntervalMs=30)
        record["sent"] = held.hold_key(session, kind, "Backspace")
    else:
        for i in range(presses):
            if i:
                time.sleep(gap_ms / 1000)
            ui.press(session, kind, "Backspace")
        record["sent"] = {"presses": presses, "gapMs": gap_ms}
    if type_after_ms is not None:
        time.sleep(type_after_ms / 1000)
        ui.press(session, kind, "q")
        record["sent"]["typedAfterMs"] = type_after_ms
    record["settle"] = settle(session, 3.0, 120)
    record["settle"]["wallSinceKeyS"] = round(time.monotonic() - t_key, 2)
    record["log"] = log_from(session, start)
    record["askAfterKey"] = ask_rectangles(session)
    record["limit"] = evaluate(session, ui.LIMIT)
    record["host"] = evaluate(session, ui.HOST)
    record["summary"] = summarize(record["log"])


def summarize(log: list[dict[str, Any]]) -> dict[str, Any]:
    downs = [e for e in log if e["k"] == "kd"]
    states = [e for e in log if e["k"] == "st"]
    first = downs[0]["t"] if downs else None
    rel = lambda t: None if t is None or first is None else round(t - first, 1)  # noqa: E731
    busy_from = None
    ready_after = []
    gens, toasts, labels = [], [], []
    prev = None
    for e in states:
        if e["gen"] not in gens:
            gens.append(e["gen"])
        if e["toast"] and e["toast"] not in toasts:
            toasts.append(e["toast"])
        if prev is not None and e["latency"] != prev["latency"]:
            labels.append({"t": rel(e["t"]), "latency": e["latency"], "state": e["state"]})
        if prev is not None and e["state"] != prev["state"]:
            if e["state"] == "busy" and first is not None and e["t"] >= first and busy_from is None:
                busy_from = e["t"]
            if e["state"] == "ready" and prev["state"] != "ready" and first is not None and e["t"] >= first:
                ready_after.append(rel(e["t"]))
        prev = e
    responses = [{"t": rel(e["t"]), "op": e.get("op"), "action": e.get("action"), "ok": e.get("ok"), "sinceRq": e.get("sinceRq"),
                  "completion": e.get("completion"), "changed": e.get("changed"), "boundaryNoop": e.get("boundaryNoop"),
                  "err": e.get("err"), "rev": e.get("rev"), "beforeRev": e.get("beforeRev")}
                 for e in log if e["k"] == "rs" and (e.get("op") or "").startswith("editor")]
    requests = [{"t": rel(e["t"]), "op": e.get("op"), "action": e.get("action")} for e in log if e["k"] == "rq" and (e.get("op") or "") != "paint"]
    ups = [e for e in log if e["k"] == "ku"]
    release = ups[-1]["t"] if ups else None
    deletes = [e for e in log if e["k"] == "rs" and (e.get("op") or "").startswith("editor") and e.get("completion") == "verified-selection-delete"]
    after_release = [round(e["t"] - release, 1) for e in deletes if release is not None and e["t"] > release]
    label_deletes = [e for e in states if (e["latency"] or "").startswith(("⌫ 刪除 ", "⌦ 刪除 ")) and "失敗" not in (e["latency"] or "")]
    return {"keydowns": len(downs), "repeatsFlagged": sum(1 for e in downs if e.get("repeat")),
            "releaseMs": rel(release), "verifiedDeletes": len(deletes),
            "deletesAfterRelease": len(after_release), "deletesAfterReleaseMs": after_release,
            "lastDeleteAfterReleaseMs": (after_release[-1] if after_release else None),
            "keydownFocus": sorted({str(e["focus"]) for e in downs}),
            "beforeinputs": sum(1 for e in log if e["k"] == "bi"),
            "busyFromMs": rel(busy_from), "readyAgainMs": ready_after, "generations": gens, "toasts": toasts,
            "latencyLabels": labels, "editorResponses": responses, "nonPaintRequests": requests,
            "stateChanges": [{"t": rel(e["t"]), "state": e["state"], "pending": e["pending"], "rev": e["rev"], "gen": e["gen"]}
                             for e in states if first is not None and e["t"] >= first - 50][:80]}


ARMS = {
    "page-number": lambda s, k, r: arm_page_number(s, k, r),
    "press-after-click-home": lambda s, k, r: arm_backspace(s, k, r, "click-home"),
    "press-after-ctrl-home": lambda s, k, r: arm_backspace(s, k, r, "ctrl-home"),
    "press-no-click": lambda s, k, r: arm_backspace(s, k, r, "none"),
    "double-press": lambda s, k, r: arm_backspace(s, k, r, "click-home", presses=2, gap_ms=400),
    "triple-press": lambda s, k, r: arm_backspace(s, k, r, "click-home", presses=3, gap_ms=400),
    "hold-3s": lambda s, k, r: arm_backspace(s, k, r, "click-home", hold_ms=3000),
    "press-then-type": lambda s, k, r: arm_backspace(s, k, r, "click-home", type_after_ms=300),
    "press-early-after-open": lambda s, k, r: arm_backspace(s, k, r, "click-home-fast"),
    "burst-1s": lambda s, k, r: arm_backspace(s, k, r, "click-home", burst_ms=1000),
    "burst-1s-fast": lambda s, k, r: arm_backspace(s, k, r, "click-home-fast", burst_ms=1000),
    "burst-1s-in-text": lambda s, k, r: arm_backspace(s, k, r, "click-in-text", burst_ms=1000),
    "hold-2s-in-text": lambda s, k, r: arm_backspace(s, k, r, "click-in-text", hold_ms=2000),
    "owner-sequence": lambda s, k, r: arm_owner_sequence(s, k, r),
}
EARLY_ARMS = {"press-early-after-open", "owner-sequence", "burst-1s-fast"}


def run_arm(arm: str, kind: str, instance: Instance | None, folder: str, name: str, out_dir: Path, index: int,
            nohost: dict[str, Any] | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {"arm": arm, "browser": kind, "doc": name, "round": index, "startedAt": utc_now(),
                              "mode": "nohost" if nohost else "host", "preflight": preflight()}
    session = ui.new_session(kind)
    record["version"] = getattr(session, "version", None)
    try:
        if nohost:
            from run_e2_c_page_smoke import navigate as smoke_navigate  # noqa: E402
            import run_e2_c_product_path as pp  # noqa: E402
            t_open = time.monotonic()
            smoke_navigate(session, nohost["url"])
            pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
            evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./fixture.odt").replace("ARG_NAME", name))
            record["landed"] = pp.wait_for(session, lambda s: (s.get("doc") or "") == name and s.get("state") == "ready", 300)
            record["secondsToOpened"] = round(time.monotonic() - t_open, 2)
        else:
            record["login"] = login(session, instance.base, "admin", instance.password)
            open_from_files(session, instance.base, folder, name, record)
        if arm in EARLY_ARMS:
            record["opened"] = ui.state(session)
        else:
            record["opened"] = ui.quiet(session, 180)
        record["instrument"] = evaluate(session, INSTRUMENT)
        record["geometryAfterOpen"] = evaluate(session, GEOMETRY)
        if arm not in EARLY_ARMS:
            # the hook learns the document handle from the page's own requests: nudge one paint
            g = record["geometryAfterOpen"]
            cx, cy = g["inner"][0] // 2, (g["desk"]["top"] + g["desk"]["bottom"]) // 2
            # (a scroll inside the three-view window moves no canvas and asks for no paint,
            # §17.9 (g) S1: the nudge has to leave the window)
            for _ in range(3):
                wheel(session, kind, cx, cy, 1200)
                time.sleep(0.25)
            time.sleep(0.6)
            wheel(session, kind, cx, cy, -40000)
            time.sleep(0.6)
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and evaluate(session, "(() => window.__n.documentHandle)()") is None:
                time.sleep(0.3)
            record["nudgeSettled"] = settle(session, 1.0, 30)
        record["documentHandle"] = evaluate(session, "(() => window.__n.documentHandle)()")
        ARMS[arm](session, kind, record)
        shots = record.pop("_shots", [])
        for label, png in shots:
            path = out_dir / f"{kind}-{name.split('.')[0]}-{arm}-{index}-{label}.png"
            path.write_bytes(png)
            record.setdefault("screenshots", []).append(str(path.name))
        png = session.screenshot()
        path = out_dir / f"{kind}-{name.split('.')[0]}-{arm}-{index}-end.png"
        path.write_bytes(png)
        record.setdefault("screenshots", []).append(path.name)
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
        try:
            record["stateAtFatal"] = evaluate(session, STATE_NOW)
        except Exception:  # noqa: BLE001
            pass
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            record.setdefault("closeError", traceback.format_exc())
        record["completedAt"] = utc_now()
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", default="firefox")
    parser.add_argument("--doc", default="long60", choices=["long60", "pmpc", "owner16630", "owner7340"])
    parser.add_argument("--arms", default="page-number,press-after-click-home")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--keep-folder", action="store_true")
    parser.add_argument("--mode", default="host", choices=["host", "nohost"])
    parser.add_argument("--nohost-root", type=Path, default=None,
                        help="nohost: serve this already-prepared tree (e.g. a decompressed engine archive) instead of a dist/ mirror")
    args = parser.parse_args()
    DOC_KIND["value"] = args.doc
    arms = [a for a in args.arms.split(",") if a]
    unknown = sorted(set(arms) - set(ARMS))
    if unknown:
        parser.error(f"unknown arms {unknown}")
    args.out.mkdir(parents=True, exist_ok=True)
    instance = Instance(DEFAULT_DDEV) if args.mode == "host" else None
    stamp = utc_now().replace(":", "").replace("-", "")[:15]
    folder = f"probe-10-14n-{stamp}"
    OWNER_COPIES = Path("/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/30f3fb46-c713-4ab4-a4a4-79969d084998/scratchpad/owner-docs")
    if args.doc == "long60":
        doc = build_long_document(60)
        name = "probe-10-14n-long60.odt"
    elif args.doc == "pmpc":
        doc = ui.DOC.read_bytes()
        name = "probe-10-14n-pmpc.odt"
    else:
        # a read-only GET of the owner's file, taken earlier; uploaded as a COPY under this probe's folder
        fid = args.doc.replace("owner", "")
        doc = (OWNER_COPIES / f"{fid}.odt").read_bytes()
        name = f"probe-10-14n-copy-{fid}.odt"
    report: dict[str, Any] = {"probe": "probe_10_14n.py", "startedAt": utc_now(), "static": ui.static_facts(DEFAULT_DDEV),
                              "mode": args.mode, "browser": args.browser,
                              "doc": {"name": name, "sha256": hashlib.sha256(doc).hexdigest(), "bytes": len(doc)},
                              "folder": folder, "arms": arms, "deskRepeat": held.desk_repeat_settings(), "runs": []}
    report_name = f"report-{args.mode}-{args.browser}-{args.doc}.json"
    nohost = None
    server = None
    if args.mode == "nohost":
        import shutil
        import socket
        import run_e2_c_product_path as pp  # noqa: E402
        from probe_m3_gate0_coep import DIST  # noqa: E402
        if args.nohost_root is not None:
            mirror = args.nohost_root.resolve()
        else:
            mirror = Path("/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/30f3fb46-c713-4ab4-a4a4-79969d084998/scratchpad") / f"mirror-{stamp}"
            shutil.rmtree(mirror, ignore_errors=True)
            pp.build_mirror(DIST, mirror, {})
        (mirror / "fixture.odt").write_bytes(doc)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = subprocess.Popen([sys.executable, str(TOOLS.parent / "web" / "serve.py"), "--port", str(port), "--root", str(mirror)],
                                  cwd=TOOLS.parent, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        nohost = {"url": f"http://127.0.0.1:{port}/e2-editor.html", "mirror": str(mirror)}
        from probe_m3_gate0_coep import sha256_file  # noqa: E402
        report["nohost"] = {**nohost, "servedPage": sha256_file(mirror / "e2-editor-app.js"),
                            "servedSession": sha256_file(mirror / "editor-shell-v2" / "narrow-editor-v2-session.js"),
                            "profile": pp.product_profile(mirror)}
    else:
        status, _ = instance.dav("MKCOL", folder)
        report["mkcol"] = status
        status, _ = instance.dav("PUT", f"{folder}/{name}", doc, {"Content-Type": "application/vnd.oasis.opendocument.text"})
        report["upload"] = status
    try:
        for arm in arms:
            for index in range(args.rounds):
                run = run_arm(arm, args.browser, instance, folder, name, args.out, index, nohost)
                report["runs"].append(run)
                (args.out / report_name).write_text(json.dumps(report, ensure_ascii=False, indent=1))
                brief = run.get("summary") or {k: run.get(k) for k in ("steps",) if k in run}
                print(args.browser, arm, index, "FATAL" if run.get("fatal") else "", json.dumps(brief, ensure_ascii=False)[:1500], flush=True)
                if run.get("fatal"):
                    print(run["fatal"][-1500:], flush=True)
    finally:
        if instance is not None and not args.keep_folder:
            status, _ = instance.dav("DELETE", folder)
            report["deletedFolder"] = status
        if server is not None:
            server.terminate()
            server.wait(timeout=10)
        report["endedAt"] = utc_now()
        (args.out / report_name).write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
