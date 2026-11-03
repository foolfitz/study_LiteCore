#!/usr/bin/env python3
"""v20's first shakedown on WASM: the arms of findings/evidence/link-batch/v20-shakedown/ARMS.md.

Written 2026-10-14 (task 10-14e part A), AFTER ARMS.md was committed and before any run.  Not a
counted runner: nothing is bound to v20; every report says `"counted": false`.

What it serves: `dist/` mirrored into a temporary directory (`run_e2_c_product_path.build_mirror`),
with the v67 page REPOINTED to the candidate profile by the same `repointed_page` function that
`build_cutover_page.py` uses, and an observer script before the page's module (the merge runner's
instrument shape: a `Worker` wrapper writing what it saw into hidden DOM nodes -- DOM, not globals,
because Firefox evaluates in a Marionette sandbox).  The shell served must BE its source
(`shell_lagging_source`), or the runner refuses.

Arms (ARMS.md names):
  p1-60     page number per position, 60-page fixture (positions generated from the engine's rectangles)
  p1-mixed  the same on the mixed-page fixture (run at a reduced window: --window 1400x560)
  p2        add a page with real Enter presses, delete it with real Backspace presses; M at +2 s
  p3        scroll the whole 60-page document; pageRectangles requests during the scroll
  c1        verified-boundary-noop at the document start and end (R0c's C29/C30), 3 rounds, with an
            engine-side selection read >= 500 ms after each completion; plus the recorded indent position
  e2        caretBefore on every refusal reachable (C15, C16, C17, F01, F02) and the hold across a merge
  p2c       the discriminating arm: the lok event log on a TRACE WORKER served from the mirror only
            (--trace-worker; dist/ untouched; the report names the served worker's sha256)

  run_v20_shakedown.py --browser chrome --arms p1-60,p3,p2,c1,e2 --out REPORT.json
  run_v20_shakedown.py --browser chrome --arms p1-mixed --window 1400x560 --out REPORT.json
  run_v20_shakedown.py --browser chrome --arms p2c --trace-worker --out REPORT.json

Point-to-page rule (ARMS.md P1): INSIDE A RECTANGLE on the y axis; x is ignored because the region the
page intersects is the whole document width; a y in the 284-twip gap is inside no rectangle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r7_support  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import run_merge_wasm_shakedown as mws  # noqa: E402
import create_mixed_page_document as mixed  # noqa: E402
from create_long_document import build as build_long_document  # noqa: E402
from build_merge_trace_profile import ANCHOR as TRACE_ANCHOR, PATCH as TRACE_PATCH  # noqa: E402

HERE = pp.PROJECT
ARMS = ("p1-60", "p1-mixed", "p2", "p3", "c1", "e2", "p2c")
DEFAULT_PROFILE = "e2-editor-v20"
LONG_PAGES = 60
STATUS_SETTLE_S = 0.25          # the scroll event and the page's recompute are asynchronous
P2_CAP = 60                     # Enter presses at most before P2-a gives up
P2_AFTER_S = 2.0                # §10.8: M must be right 2 s after the last input
C1_ROUNDS = 3
C1_READ_AFTER_S = 0.5           # §10.5: the engine read is at least 500 ms after the completion
C1_POSITIONS = ("C29", "C30")   # R0c's nothing-selected cases: document start (Backspace), end (Delete)
E2_CASES = ("C15", "C16", "C17", "F01", "F02")
E2_HOLD_START = "I01"           # Delete held from the end of `M12 number one` (ARMS.md said M13's end;
                                # that position has no native caret to verify placement against, I01 has)
HOLD_MS, HOLD_DELAY_MS, HOLD_INTERVAL_MS = 5000, 500, 30
LONE_WINDOW_MS = 25             # finding 048: the click's acknowledgement window is 22-28 ms
ASK_BASE = 0x7F000000           # requestIds the SDK never issues (it counts from 1); uint32 for ccall
LOK_NAMES = {0: "INVALIDATE_TILES", 1: "INVALIDATE_VISIBLE_CURSOR", 2: "TEXT_SELECTION",
             3: "TEXT_SELECTION_START", 4: "TEXT_SELECTION_END", 5: "CURSOR_VISIBLE", 8: "STATE_CHANGED",
             13: "DOCUMENT_SIZE_CHANGED", 14: "SET_PART", 16: "UNO_COMMAND_RESULT", 35: "RULER_UPDATE",
             39: "CONTEXT_CHANGED", 73: "VERTICAL_RULER_UPDATE"}
NOT_LONE_IDS = (0, 1, 2, 3, 4)  # a size change beside any of these is not a lone flush

# ------------------------------------------------------------------ the instrument

OBSERVER = r"""<script>
(() => {
  const Native = window.Worker;
  const KEEP = 64;
  // Summary node: the merge runner's shape (its `place()` reads workers, size, caret, carets), plus
  // the document handle and per-operation request counts.
  const obs = { workers: 0, responses: [], responsesSeen: 0, caret: null, carets: 0, size: null,
                documentHandle: null, requestCounts: {}, asks: 0, error: null,
                traceBytes: 0, traceDropped: 0, protocolVersion: null };
  const TRACE_CAP = 4000;   // entries kept between drains; the CDP frame limit is 1 MiB (run 2 hit it)
  const node = document.createElement("script");
  node.type = "application/json"; node.id = "merge-observer";
  let queued = false;
  const flush = () => { queued = false; node.textContent = JSON.stringify(obs); };
  const later = () => { if (!queued) { queued = true; setTimeout(flush, 0); } };
  // Drained log on this page's clock; the runner reads #v20-trace and acknowledges with data-cut.
  const trace = { seq: 0, entries: [] };
  const tnode = document.createElement("script");
  tnode.type = "application/json"; tnode.id = "v20-trace";
  let tqueued = false;
  const tflush = () => {
    tqueued = false;
    const cut = Number(tnode.dataset.cut ?? -1);
    trace.entries = trace.entries.filter((e) => e.s > cut);
    if (trace.entries.length > TRACE_CAP) {
      obs.traceDropped += trace.entries.length - TRACE_CAP;
      trace.entries = trace.entries.slice(trace.entries.length - TRACE_CAP);
    }
    tnode.textContent = JSON.stringify(trace.entries);
    obs.traceBytes = Math.max(obs.traceBytes, tnode.textContent.length); later();
  };
  const log = (entry) => {
    entry.s = trace.seq++; entry.t = Math.round(performance.now() * 10) / 10;
    trace.entries.push(entry);
    if (!tqueued) { tqueued = true; setTimeout(tflush, 0); }
  };
  let current = null;   // the newest document worker, for the ask channel
  document.addEventListener("DOMContentLoaded", () => {
    document.head.appendChild(node); flush();
    document.head.appendChild(tnode); tflush();
    const toastNode = document.querySelector("#toast");
    if (toastNode) new MutationObserver((records) => {
      for (const record of records) {
        for (const added of record.addedNodes) if (added.textContent) log({ k: "t", text: added.textContent });
        if (record.type === "characterData" && record.target.data) log({ k: "t", text: record.target.data });
      }
    }).observe(toastNode, { childList: true, characterData: true, subtree: true });
    const ps = document.querySelector("#page-status");
    if (ps) new MutationObserver(() => log({ k: "ps", text: ps.textContent, hidden: ps.hidden }))
      .observe(ps, { childList: true, characterData: true, subtree: true, attributes: true });
    // The ask channel: the runner writes a JSON request into a data attribute and dispatches an
    // event; the request goes to the product's own worker with a requestId the SDK never issues,
    // so the SDK drops the reply (document-sdk.js: no pending entry) and this log keeps it.
    document.documentElement.addEventListener("v20-ask", () => {
      try {
        const ask = JSON.parse(document.documentElement.dataset.v20ask || "null");
        if (!ask || !current) { log({ k: "ask", error: ask ? "no worker" : "no request" }); return; }
        current.requests.set(ask.requestId, { operation: ask.operation, ask: true });
        // The worker refuses a message without the protocol version (PROTOCOL_MISMATCH, sdk-worker.js
        // onmessage); the version is copied from the page's own requests, never assumed.
        current.worker.postMessage({ protocolVersion: obs.protocolVersion, kind: "request",
                                     requestId: ask.requestId, operation: ask.operation,
                                     payload: ask.payload || {} });
        obs.asks += 1; later();
        log({ k: "ask", rq: ask.requestId, op: ask.operation, g: current.generation });
      } catch (error) { log({ k: "ask", error: String(error) }); }
    });
  });
  const sel = (s) => (s && typeof s === "object")
    ? { collapsed: s.collapsed ?? null, n: Array.isArray(s.rectangles) ? s.rectangles.length : null,
        observed: s.observed ?? null }
    : null;
  const stateOf = (st) => (st && typeof st === "object")
    ? { caret: st.caret ?? null, seq: st.sourceSequence ?? null, dsc: st.documentSizeChangedCount ?? null,
        rev: st.revision ?? null, sel: sel(st.selection) }
    : null;
  function seen(data, generation, requests) {
    if (!data || typeof data !== "object") return;
    if (data.kind === "event") {
      if (data.event === "merge-trace") {
        log({ k: "mt", g: generation, tw: typeof data.tw === "number" ? data.tw - performance.timeOrigin : null,
              type: data.type ?? null, id: data.id ?? null, rq: data.requestId ?? null,
              completion: data.completion ?? null, code: data.code ?? null });
        return;
      }
      if (data.event === "editor-state") {
        if (data.caret) {
          obs.caret = { generation, t: performance.now(), caret: data.caret, sourceSequence: data.sourceSequence ?? null };
          obs.carets += 1; later();
        }
        log({ k: "ev", g: generation, caret: data.caret ?? null, seq: data.sourceSequence ?? null,
              dcs: data.documentChangeSequence ?? null, dsc: data.documentSizeChangedCount ?? null,
              rev: data.revision ?? null, source: data.source ?? null, sel: sel(data.selection) });
        return;
      }
      if (data.event === "engine-error" || data.event === "diagnostic")
        log({ k: "ev", g: generation, event: data.event, detail: JSON.stringify(data).slice(0, 400) });
      return;
    }
    if (data.kind !== "response") return;
    const request = (requests && requests.get(data.requestId)) || {};
    if (requests) requests.delete(data.requestId);
    const value = data.ok ? data.result : data.error;
    const entry = { k: "rs", g: generation, rq: data.requestId, op: request.operation ?? null,
                    action: request.action ?? null, ok: data.ok };
    if (!data.ok) entry.err = (value && typeof value === "object")
      ? { code: value.code ?? null, message: String(value.message ?? "").slice(0, 200) } : String(value).slice(0, 200);
    if (request.ask) {
      entry.ask = true;
      entry.result = (data.ok && value && typeof value === "object")
        ? { sel: sel(value.selection), selectionType: value.selectionType ?? null, caret: value.caret ?? null,
            seq: value.sourceSequence ?? null, dsc: value.documentSizeChangedCount ?? null, rev: value.revision ?? null }
        : entry.err;
    }
    if (value && typeof value === "object") {
      if (value.documentHandle !== undefined && typeof value.width === "number") {
        obs.documentHandle = value.documentHandle;
        obs.size = { w: value.width, h: value.height, from: "open", generation }; later();
        entry.documentHandle = value.documentHandle; entry.w = value.width; entry.h = value.height;
      }
      if (typeof value.documentWidthTwips === "number") {
        const size = { w: value.documentWidthTwips, h: value.documentHeightTwips, from: "paint", generation };
        if (!obs.size || obs.size.w !== size.w || obs.size.h !== size.h || obs.size.generation !== generation) {
          obs.size = size; later();
        }
        entry.docW = value.documentWidthTwips; entry.docH = value.documentHeightTwips;
      }
      if (request.operation === "pageRectangles") {
        entry.rects = typeof value.rectangles === "string" ? value.rectangles : null;
        entry.parts = value.parts ?? null; entry.rev = value.revision ?? null;
        if (!data.ok) { entry.code = value.code ?? null; entry.message = value.message ?? null; }
      } else if (request.operation === "paint") {
        entry.changed = value.documentSizeChanged ?? null;
        if (!data.ok) entry.code = value.code ?? null;
      } else if (request.ask) {
        // handled above, before the object test
      } else if (/^editor/.test(request.operation || "")) {
        entry.completion = value.completion ?? null; entry.changed = value.changed ?? null;
        entry.rev = value.revision ?? null; entry.beforeRev = value.beforeRevision ?? null;
        entry.boundaryNoop = value.boundaryNoop ?? null;
        entry.keyUndo = value.keyUndo ? { comment: value.keyUndo.comment ?? null,
                                          restorePresses: value.keyUndo.restorePresses ?? null } : null;
        entry.state = stateOf(value.state);
        if (!data.ok) {
          entry.code = value.code ?? null; entry.message = value.message ?? null;
          entry.mergeKey = value.mergeKey ?? value.details?.mergeKey ?? null;
          entry.caretBefore = value.caretBefore ?? value.details?.caretBefore ?? null;
          entry.details = value.details ? Object.keys(value.details) : null;
        }
      }
    }
    log(entry);
    const editor = /^editorAction/.test(request.operation || "");
    const marked = value && typeof value === "object" && (value.keyUndo || value.mergeKey || value.completion);
    if (!(marked || (editor && !data.ok))) return;
    obs.responses.push({ n: obs.responsesSeen, t: performance.now(), generation, ok: data.ok,
      operation: request.operation ?? null, action: request.action ?? value?.action ?? null,
      completion: value?.completion ?? null, keyUndo: value?.keyUndo ?? null,
      code: value?.code ?? null, message: value?.message ?? null,
      mergeKey: value?.mergeKey ?? value?.details?.mergeKey ?? null });
    obs.responsesSeen += 1;
    if (obs.responses.length > KEEP) obs.responses.shift();
    later();
  }
  function Wrapped(url, options) {
    const worker = new Native(url, options);
    if (options && options.name === "oxoffice-document-engine") {
      obs.workers += 1;
      const generation = obs.workers;
      const requests = new Map();
      current = { worker, generation, requests };
      const post = worker.postMessage.bind(worker);
      worker.postMessage = (message, transfer) => {
        if (message && message.kind === "request") {
          if (message.protocolVersion !== undefined && !requests.get(message.requestId)?.ask)
            obs.protocolVersion = message.protocolVersion;
          requests.set(message.requestId, { ...(requests.get(message.requestId) || {}),
                                            operation: message.operation, action: message.payload?.action,
                                            y: message.payload?.yTwips, h: message.payload?.heightTwips });
          const key = `${generation}:${message.operation}`;
          obs.requestCounts[key] = (obs.requestCounts[key] || 0) + 1; later();
          log({ k: "rq", g: generation, rq: message.requestId, op: message.operation,
                action: message.payload?.action ?? null });
        }
        return post(message, transfer);
      };
      worker.addEventListener("message", (event) => {
        try { seen(event.data, generation, requests); }
        catch (error) { obs.error = String(error); later(); }
      });
      later();
    }
    return worker;
  }
  Wrapped.prototype = Native.prototype;
  window.Worker = Wrapped;
})();
</script>
"""
READ_TRACE_LEN = "(() => { const n = document.getElementById('v20-trace'); return n ? n.textContent.length : -1; })()"
READ_TRACE_SLICE = "(() => { const n = document.getElementById('v20-trace'); return n ? n.textContent.slice(ARG_A, ARG_B) : null; })()"
TRACE_CHUNK = 400000          # bytes per CDP reply; the websocket client closes on a frame over 1 MiB (run 2)
STATS = {"maxTraceReadBytes": 0, "traceReads": 0}
CUT_TRACE = "(() => {{ const n = document.getElementById('v20-trace'); if (n) n.dataset.cut = '{0}'; return true; }})()"
ASK = ("(() => { document.documentElement.dataset.v20ask = ARG_JSON; "
       "document.documentElement.dispatchEvent(new Event('v20-ask')); return true; })()")
GEOMETRY = """(() => {
const desk = document.querySelector('#desk'), paper = document.querySelector('#paper');
const ps = document.querySelector('#page-status');
const d = desk.getBoundingClientRect(), p = paper.getBoundingClientRect();
const w = (document.querySelector('#canvas').dataset.window || '').trim().split(/\\s+/).map(Number);
return { scrollTop: desk.scrollTop, clientHeight: desk.clientHeight, scrollHeight: desk.scrollHeight,
         deskTop: d.top, deskBottom: d.bottom, paperTop: p.top, paperBottom: p.bottom,
         paperHeight: p.height, paperWidth: p.width, docRows: w.length === 3 ? w[0] : null,
         text: ps ? ps.textContent : null, hidden: ps ? ps.hidden : null,
         innerWidth: window.innerWidth, innerHeight: window.innerHeight, dpr: window.devicePixelRatio };
})()"""
# Scroll so that document fraction ARG_F sits at the vertical middle of the desk's view.
SCROLL_CENTRE = """(() => {
const desk = document.querySelector('#desk'), paper = document.querySelector('#paper');
const d = desk.getBoundingClientRect(), p = paper.getBoundingClientRect();
const offset = p.top - d.top + desk.scrollTop;
desk.scrollTop = Math.max(0, Math.round(offset + p.height * ARG_F - desk.clientHeight / 2));
return desk.scrollTop;
})()"""
SCROLL_BY = """(() => { const desk = document.querySelector('#desk');
desk.scrollTop = Math.max(0, Math.min(desk.scrollHeight, desk.scrollTop + (ARG_DY)));
return { scrollTop: desk.scrollTop, scrollHeight: desk.scrollHeight, clientHeight: desk.clientHeight }; })()"""
WD_KEYS = {"Enter": "", "ArrowDown": "", "ArrowUp": "", "Home": "", "End": "",
           "Backspace": "", "Delete": "", "ArrowLeft": "", "ArrowRight": ""}
CDP_KEYS = {"Enter": ("Enter", "Enter", 13), "ArrowDown": ("ArrowDown", "ArrowDown", 40),
            "ArrowUp": ("ArrowUp", "ArrowUp", 38), "ArrowLeft": ("ArrowLeft", "ArrowLeft", 37),
            "ArrowRight": ("ArrowRight", "ArrowRight", 39), **mws.CDP_KEYS}
TRACE = {"last": -1}
# Set by main(): writes the report as it stands.  Called after every round, case and phase, so a
# hung page (the first Chrome run lost its C1 data to a 180 s CDP silence) leaves what was measured.
FLUSH = {"fn": lambda: None}


# ------------------------------------------------------------------ small helpers

def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def pre_run_checks() -> dict:
    """ARMS.md's pre-run protocol, recorded rather than assumed."""
    def run(cmd: list[str]) -> str:
        try:
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            return (done.stdout + done.stderr).strip()
        except Exception as error:  # noqa: BLE001
            return f"unreadable: {error}"
    ours = [line for line in run(["pgrep", "-af", "probe_|check_m3|run_e2_c|run_merge"]).splitlines()
            if "pgrep" not in line and str(os.getpid()) not in line.split(" ", 1)[0]]
    return {"kwalletLocked": run(["busctl", "--user", "get-property", "org.freedesktop.secrets",
                                 "/org/freedesktop/secrets/collection/kdewallet",
                                 "org.freedesktop.Secret.Collection", "Locked"]),
            "chromeProcesses": run(["pgrep", "-c", "chrome"]),
            "oursRunning": ours, "at": now_iso()}


def drain(session) -> list:
    length = pp.evaluate(session, READ_TRACE_LEN)
    if not isinstance(length, int) or length <= 0:
        return []
    STATS["traceReads"] += 1
    STATS["maxTraceReadBytes"] = max(STATS["maxTraceReadBytes"], length)
    parts = [pp.evaluate(session, READ_TRACE_SLICE.replace("ARG_A", str(a)).replace("ARG_B", str(a + TRACE_CHUNK)))
             for a in range(0, length, TRACE_CHUNK)]
    raw = "".join(p for p in parts if isinstance(p, str))
    try:
        entries = [e for e in (json.loads(raw) if raw else []) if e.get("s", -1) > TRACE["last"]]
    except json.JSONDecodeError:
        # the node was rewritten between the slices; read it again whole on the next drain
        STATS["tornReads"] = STATS.get("tornReads", 0) + 1
        return []
    if entries:
        TRACE["last"] = max(e["s"] for e in entries)
        pp.evaluate(session, CUT_TRACE.format(TRACE["last"]))
    return entries


def press(session, browser: str, key: str) -> None:
    """One real key (a name in CDP_KEYS/WD_KEYS, or a letter); the merge runner's shape."""
    if browser == "chrome":
        if key in CDP_KEYS:
            name, code, vk = CDP_KEYS[key]
            phases, text = ("rawKeyDown", "keyUp"), None
        else:
            name, code, vk, text = key, f"Key{key.upper()}", ord(key.upper()), key
            phases = ("rawKeyDown", "char", "keyUp")
        for phase in phases:
            params = {"type": phase, "key": name, "code": code, "windowsVirtualKeyCode": vk,
                      "nativeVirtualKeyCode": vk, "modifiers": 0}
            if phase == "char":
                params["text"] = text
            session.call("Input.dispatchKeyEvent", params)
        return
    value = WD_KEYS.get(key, key)
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": [
        {"type": "keyDown", "value": value}, {"type": "keyUp", "value": value}]}]})
    session.command("DELETE", "/actions")


def hold_key(session, browser: str, key: str, hold_ms: int = HOLD_MS) -> dict:
    """A HELD key the way the OS sends it (probe_hand_test_0212's shape): one press, repeats every
    HOLD_INTERVAL_MS from HOLD_DELAY_MS on, one keyup at the end."""
    times = [0] + list(range(HOLD_DELAY_MS, hold_ms + 1, HOLD_INTERVAL_MS))
    release = times[-1] + HOLD_INTERVAL_MS // 2
    if browser == "chrome":
        name, code, vk = CDP_KEYS[key]
        base = {"key": name, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk, "modifiers": 0}
        start, sent = time.monotonic(), []
        for i, at in enumerate(times):
            wait = start + at / 1000 - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            sent.append(round((time.monotonic() - start) * 1000, 1))
            session.call("Input.dispatchKeyEvent", {**base, "type": "rawKeyDown", "autoRepeat": i > 0})
        wait = start + release / 1000 - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        session.call("Input.dispatchKeyEvent", {**base, "type": "keyUp"})
        return {"scheduledMs": len(times), "releaseMs": release, "sentLastMs": sent[-1]}
    value = WD_KEYS[key]
    actions: list[dict] = []
    previous = 0
    for at in times:
        if at > previous:
            actions.append({"type": "pause", "duration": at - previous})
        actions.append({"type": "keyDown", "value": value})
        previous = at
    actions += [{"type": "pause", "duration": release - previous}, {"type": "keyUp", "value": value}]
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": actions}]})
    session.command("DELETE", "/actions")
    return {"scheduledMs": len(times), "releaseMs": release}


def parse_rects(raw: str | None) -> list[dict] | None:
    """`x, y, w, h; x, y, w, h; ...` in twips, string order kept (never sorted)."""
    if not isinstance(raw, str) or not raw.strip():
        return [] if raw == "" else None
    out = []
    for piece in raw.split(";"):
        numbers = [int(v) for v in re.findall(r"-?\d+", piece)]
        if len(numbers) != 4:
            return None
        out.append({"x": numbers[0], "y": numbers[1], "width": numbers[2], "height": numbers[3]})
    return out


def span_of(rects: list[dict], region: dict) -> dict | None:
    """Writer's rule on whole rectangles: strict overlap on both axes; first and last hit in string order."""
    rx0, ry0 = region["x"], region["y"]
    rx1, ry1 = rx0 + region["width"], ry0 + region["height"]
    hits = [i + 1 for i, r in enumerate(rects)
            if r["x"] < rx1 and rx0 < r["x"] + r["width"] and r["y"] < ry1 and ry0 < r["y"] + r["height"]]
    if not hits:
        return None
    return {"first": hits[0], "last": hits[-1], "count": len(rects)}


def status_text(span: dict | None) -> str | None:
    if span is None:
        return None
    if span["first"] == span["last"]:
        return f"第 {span['first']} 頁，共 {span['count']} 頁"
    return f"第 {span['first']}–{span['last']} 頁，共 {span['count']} 頁"


def region_of(geometry: dict, doc_w: int, doc_h: int) -> dict | None:
    """The desk's view on #paper, in twips -- measured by the runner, not read from the page."""
    if not geometry.get("paperHeight"):
        return None
    top = max(geometry["deskTop"], geometry["paperTop"]) - geometry["paperTop"]
    bottom = min(geometry["deskBottom"], geometry["paperBottom"]) - geometry["paperTop"]
    if bottom <= top:
        return None
    scale = doc_h / geometry["paperHeight"]
    return {"x": 0, "y": top * scale, "width": doc_w, "height": (bottom - top) * scale}


def latest_rects(entries: list) -> dict | None:
    """The newest successful pageRectangles reply in a trace slice."""
    for e in reversed(entries):
        if e.get("k") == "rs" and e.get("op") == "pageRectangles" and e.get("ok"):
            return e
    return None


def ask_state(session, document_handle, timeout: float = 5.0) -> dict:
    """The engine's own state (`editorGetStateV2`, a fresh readSelection in the engine), asked through
    the product's worker; the reply is read from the trace by its requestId."""
    rq = ASK_BASE + int(time.time() * 10) % 0x00FFFFFF
    # Dispatched from the page's OWN global (a <script> element, r7_support.run_in_page's shape), so the
    # event reaches the observer's listener in Firefox too, where evaluate() runs in a Marionette sandbox.
    r7_support.run_in_page(session, ASK.replace("ARG_JSON", json.dumps(json.dumps(
        {"requestId": rq, "operation": "editorGetStateV2", "payload": {"documentHandle": document_handle}}))))
    deadline, collected = time.monotonic() + timeout, []
    while time.monotonic() < deadline:
        slice_ = drain(session)
        collected += slice_
        for e in slice_:
            if e.get("k") == "rs" and e.get("rq") == rq:
                return {"asked": rq, "answered": True, "ok": e.get("ok"), "result": e.get("result"),
                        "entries": collected}
        time.sleep(0.1)
    return {"asked": rq, "answered": False, "entries": collected}


def wait_response(session, predicate, limit: float = 20.0) -> tuple[dict | None, list]:
    """Drain until an entry satisfies `predicate`; everything drained is returned too."""
    deadline, collected = time.monotonic() + limit, []
    while time.monotonic() < deadline:
        slice_ = drain(session)
        collected += slice_
        for e in slice_:
            if predicate(e):
                return e, collected
        time.sleep(0.1)
    return None, collected


def is_delete_answer(e: dict) -> bool:
    return (e.get("k") == "rs" and str(e.get("op") or "").startswith("editorAction")
            and (e.get("action") in mws.DELETE_ACTIONS or not e.get("ok")))


def gen(session) -> str:
    return pp.evaluate(session, mws.GEN)


def toasts(session) -> list:
    return pp.evaluate(session, pp.READ_TOASTS) or []


def open_fixture(session, url: str, name: str) -> dict:
    opened = mws.open_fixture(session, url, name)
    opened["generation"] = gen(session)
    return opened


def build_indent_fixture() -> bytes:
    """Two paragraphs, the first with `fo:text-indent="1cm"`: ruling 6 §15.1's position (iii)."""
    mimetype = "application/vnd.oasis.opendocument.text"
    content = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.2">
 <office:automatic-styles>
  <style:style style:name="PIndent" style:family="paragraph" style:parent-style-name="Standard">
   <style:paragraph-properties fo:text-indent="1cm"/>
  </style:style>
 </office:automatic-styles>
 <office:body><office:text>
  <text:p text:style-name="PIndent">ID01 indented alpha</text:p>
  <text:p text:style-name="Standard">ID02 plain beta</text:p>
 </office:text></office:body>
</office:document-content>
"""
    manifest = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        info = zipfile.ZipInfo("mimetype", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_STORED
        archive.writestr(info, mimetype)
        for name, text in (("content.xml", content), ("META-INF/manifest.xml", manifest)):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, text)
    return buffer.getvalue()


# ------------------------------------------------------------------ the arms

def settle_rects(session, limit: float = 30.0) -> tuple[dict | None, list]:
    """After an open: the first successful pageRectangles reply, then quiet."""
    reply, entries = wait_response(session, lambda e: e.get("k") == "rs" and e.get("op") == "pageRectangles"
                                   and e.get("ok"), limit)
    mws.quiet(session)
    time.sleep(1.0)
    entries += drain(session)
    return latest_rects(entries) or reply, entries


def arm_p1(session, browser: str, url: str, name: str, native_pages: int, out: dict) -> dict:
    out.update({"arm": name, "fixture": url, "nativePages": native_pages, "positions": [], "ok": None})
    out["open"] = open_fixture(session, url, f"{name}.odt")
    reply, entries = settle_rects(session)
    out["pageRectanglesRequestsAtOpen"] = sum(1 for e in entries if e.get("k") == "rq" and e.get("op") == "pageRectangles")
    if reply is None:
        out["verdictNote"] = "no pageRectangles reply after the open"
        return out
    rects = parse_rects(reply.get("rects"))
    out["reply"] = {"parts": reply.get("parts"), "count": len(rects) if rects else None,
                    "docW": reply.get("docW"), "docH": reply.get("docH"), "raw": reply.get("rects")}
    if not rects:
        out["verdictNote"] = "the reply's rectangle string did not parse"
        return out
    doc_w, doc_h = reply["docW"], reply["docH"]
    geometry = pp.evaluate(session, GEOMETRY)
    view_twips = geometry["clientHeight"] * doc_h / geometry["paperHeight"] if geometry.get("paperHeight") else None
    out["view"] = {"deskClientHeightPx": geometry["clientHeight"], "paperHeightPx": geometry["paperHeight"],
                   "paperWidthPx": geometry["paperWidth"], "viewTwips": view_twips,
                   "smallestPageTwips": min(r["height"] for r in rects),
                   "singlePageViewPossible": bool(view_twips and view_twips < min(r["height"] for r in rects)),
                   "innerWidth": geometry["innerWidth"], "innerHeight": geometry["innerHeight"]}
    positions = [("centre", k + 1, r["y"] + r["height"] / 2) for k, r in enumerate(rects)]
    positions += [("boundary", k + 1, (rects[k]["y"] + rects[k]["height"] + rects[k + 1]["y"]) / 2)
                  for k in range(len(rects) - 1)]
    for kind, k, y in positions:
        pp.evaluate(session, SCROLL_CENTRE.replace("ARG_F", repr(y / doc_h)))
        time.sleep(STATUS_SETTLE_S)
        g = pp.evaluate(session, GEOMETRY)
        region = region_of(g, doc_w, doc_h)
        expected = status_text(span_of(rects, region)) if region else None
        inside = [i + 1 for i, r in enumerate(rects) if r["y"] <= y < r["y"] + r["height"]]
        out["positions"].append({
            "kind": kind, "page": k, "yTwips": round(y), "pointInsidePage": inside[0] if inside else None,
            "scrollTop": g["scrollTop"], "regionTwips": {kk: round(v) for kk, v in region.items()} if region else None,
            "expected": expected, "text": g["text"], "hidden": g["hidden"],
            "viewTallerThanPage": bool(view_twips and view_twips >= rects[k - 1]["height"]),
            "pass": (expected is not None and g["hidden"] is False and g["text"] == expected)})
        if len(out["positions"]) % 20 == 0:
            FLUSH["fn"]()
    time.sleep(0.5)
    tail = drain(session)
    out["pageRectanglesRequestsDuringPositions"] = sum(1 for e in tail if e.get("k") == "rq" and e.get("op") == "pageRectangles")
    out["partsEqualsCount"] = reply.get("parts") == len(rects)
    out["ok"] = bool(out["positions"]) and all(p["pass"] for p in out["positions"]) and out["partsEqualsCount"]
    return out


def click_fraction(session, fx: float, fy: float) -> None:
    pp.evaluate(session, pp.POINT_AT.replace("ARG_X", f"{fx:.6f}").replace("ARG_Y", f"{fy:.6f}"))


def wait_action(session, action: str, limit: float = 20.0) -> tuple[dict | None, list]:
    return wait_response(session, lambda e: e.get("k") == "rs" and str(e.get("op") or "").startswith("editorAction")
                         and (e.get("action") == action or not e.get("ok")), limit)


def presses_until(session, browser: str, key: str, action: str, target_count: int, cap: int,
                  stop_when, sink: list | None = None) -> dict:
    """Press `key` one at a time, each one's own answer awaited, until `stop_when(count)` or `cap`.
    Every trace entry drained on the way is appended to `sink` when one is given (P2-c reads the lok
    events of the edit window from it; Chrome p2c run 2 lost them to these drains)."""
    out = {"presses": 0, "answers": [], "firstReplyWithTarget": None, "triggerBeforeIt": None, "count": None,
           "parts": None}
    last_dsc, pending_triggers = None, []
    for n in range(1, cap + 1):
        t0 = time.monotonic()
        press(session, browser, key)
        answer, entries = wait_action(session, action)
        out["presses"] = n
        out["answers"].append({"n": n, "ok": (answer or {}).get("ok"), "completion": (answer or {}).get("completion"),
                               "code": (answer or {}).get("code"), "ms": round((time.monotonic() - t0) * 1000)})
        mws.quiet(session, 15)
        entries += drain(session)
        if sink is not None:
            sink.extend(entries)
        for e in entries:
            if e.get("k") == "rs" and e.get("op") == "paint" and e.get("changed") is True:
                pending_triggers.append({"kind": "paint.documentSizeChanged", "t": e["t"]})
            if e.get("k") == "ev" and e.get("dsc") is not None:
                if last_dsc is not None and e["dsc"] != last_dsc:
                    pending_triggers.append({"kind": "editor-state.documentSizeChangedCount", "t": e["t"],
                                             "from": last_dsc, "to": e["dsc"]})
                last_dsc = e["dsc"]
            if e.get("k") == "rs" and e.get("op") == "pageRectangles" and e.get("ok"):
                rects = parse_rects(e.get("rects"))
                out["count"] = len(rects) if rects is not None else None
                out["parts"] = e.get("parts")   # the reply's own parts, kept beside its count (review: codex 1)
                if out["count"] == target_count and out["firstReplyWithTarget"] is None:
                    out["firstReplyWithTarget"] = {"press": n, "t": e["t"], "parts": e.get("parts")}
                    out["triggerBeforeIt"] = [tr for tr in pending_triggers if tr["t"] <= e["t"]][-3:]
        if answer is None or not answer.get("ok"):
            out["stopped"] = "the key's answer was missing or a refusal"
            break
        if stop_when(out["count"]):
            break
    return out


def at_2s(reply_after: dict | None, pressed: dict, g: dict, expected_m: int) -> dict:
    """ARMS.md P2's +2 s reading: the text, and count/parts from the engine's latest reply -- the one in
    the final wait when there was one, else the last reply seen during the presses, with ITS parts.
    Before the §34.3 review the fallback wrote the count into `partsAt2s`, asserting an equality that
    was never measured (codex 1); `parts` must now equal M, never None."""
    rects = parse_rects(reply_after.get("rects")) if reply_after else None
    if rects is not None:
        count, parts = len(rects), reply_after.get("parts")
    else:
        count, parts = pressed.get("count"), pressed.get("parts")
    return {"textAt2s": g["text"], "hiddenAt2s": g["hidden"], "countAt2s": count, "partsAt2s": parts,
            "expectedM": expected_m,
            "pass": (g["hidden"] is False and isinstance(g["text"], str) and f"共 {expected_m} 頁" in g["text"]
                     and count == expected_m and parts == expected_m)}


def arm_p2(session, browser: str, url: str, out: dict) -> dict:
    out.update({"arm": "p2", "fixture": url})
    out["open"] = open_fixture(session, url, "p2-long60.odt")
    reply, _ = settle_rects(session)
    if reply is None:
        out["verdictNote"] = "no pageRectangles reply after the open"
        return out
    rects = parse_rects(reply.get("rects"))
    doc_w, doc_h = reply["docW"], reply["docH"]
    base = len(rects)
    out["before"] = {"count": base, "parts": reply.get("parts")}
    last = rects[-1]
    # Click below the last page's text (the caret lands on the last line), then End.
    click_fraction(session, 0.3, (last["y"] + min(7000, last["height"] - 1500)) / doc_h)
    pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 30)
    mws.quiet(session)
    press(session, browser, "End")
    mws.quiet(session)
    drain(session)
    out["caretBeforeEdits"] = mws.caret_tuple(mws.obs(session).get("caret"))
    add = presses_until(session, browser, "Enter", "insert-paragraph-break", base + 1, P2_CAP,
                        lambda count: count == base + 1)
    time.sleep(P2_AFTER_S)
    tail = drain(session)
    out["add"] = {**add, **at_2s(latest_rects(tail), add, pp.evaluate(session, GEOMETRY), base + 1)}
    out["add"]["answers"] = out["add"]["answers"][-5:] + [{"total": add["presses"]}]
    FLUSH["fn"]()
    if not add["presses"]:
        out["verdictNote"] = "no Enter press was sent"
        return out
    remove = presses_until(session, browser, "Backspace", "delete-backward", base, add["presses"],
                           lambda count: False)   # the same number of presses, whatever the count says
    time.sleep(P2_AFTER_S)
    tail = drain(session)
    out["remove"] = {**remove, **at_2s(latest_rects(tail), remove, pp.evaluate(session, GEOMETRY), base)}
    out["remove"]["answers"] = out["remove"]["answers"][-5:] + [{"total": remove["presses"]}]
    out["generation"] = gen(session)
    out["toasts"] = toasts(session)[-6:]
    out["ok"] = out["add"]["pass"] and out["remove"]["pass"]
    return out


def arm_p3(session, browser: str, url: str, out: dict) -> dict:
    out.update({"arm": "p3", "fixture": url})
    out["open"] = open_fixture(session, url, "p3-long60.odt")
    reply, _ = settle_rects(session)
    if reply is None:
        out["verdictNote"] = "no pageRectangles reply after the open"
        return out
    pp.evaluate(session, SCROLL_BY.replace("ARG_DY", "-1e9"))   # from the TOP: the first run started where P1 left the desk
    time.sleep(1.0)
    mws.quiet(session)
    start_top = pp.evaluate(session, GEOMETRY)["scrollTop"]
    counts_before = dict(mws.obs(session).get("requestCounts") or {})
    drain(session)
    t_start = pp.evaluate(session, mws.NOW)
    steps, reached_bottom = [], False
    for _ in range(400):
        g = pp.evaluate(session, SCROLL_BY.replace("ARG_DY", "document.querySelector('#desk').clientHeight"))
        steps.append(g["scrollTop"])
        time.sleep(0.15)
        if g["scrollTop"] + g["clientHeight"] >= g["scrollHeight"] - 1:
            reached_bottom = True
            break
    up_steps = 0
    for _ in range(400):
        g = pp.evaluate(session, SCROLL_BY.replace("ARG_DY", "-document.querySelector('#desk').clientHeight"))
        up_steps += 1
        time.sleep(0.15)
        if g["scrollTop"] <= 0:
            break
    time.sleep(2.0)
    t_end = pp.evaluate(session, mws.NOW)
    entries = drain(session)
    requests = [e for e in entries if e.get("k") == "rq" and e.get("op") == "pageRectangles"]
    paints = [e for e in entries if e.get("k") == "rq" and e.get("op") == "paint"]
    triggers = [e for e in entries if (e.get("k") == "rs" and e.get("op") == "paint" and e.get("changed") is True)]
    last_dsc = None
    for e in entries:
        if e.get("k") == "ev" and e.get("dsc") is not None:
            if last_dsc is not None and e["dsc"] != last_dsc:
                triggers.append(e)
            last_dsc = e["dsc"]
    untriggered = [r for r in requests if not any(0 <= r["t"] - tr["t"] <= 2000 for tr in triggers)]
    out.update({"windowMs": [t_start, t_end], "steps": len(steps), "stepsUp": up_steps, "scrollTopAtStart": start_top,
                "reachedBottom": reached_bottom,
                "maxScrollTop": max(steps) if steps else None,
                "pageRectanglesRequestsInWindow": len(requests), "untriggeredRequests": len(untriggered),
                "triggersInWindow": len(triggers), "paintsInWindow": len(paints),
                "requestCountsBefore": counts_before, "requestCountsAfter": mws.obs(session).get("requestCounts"),
                "nonVacuous": bool(paints) and reached_bottom})
    out["ok"] = out["nonVacuous"] and not untriggered
    return out


def place_native(session, browser: str, fixture: str, case: str) -> tuple[dict, dict]:
    spec = mws.native_cases(fixture)[case]
    placed = mws.place(session, browser, spec["nativeCaret"], spec["backward"])
    return spec, placed


def c1_clauses(answer: dict, asked: dict, gen_before: str, gen_after: str, toasts_after_key: list) -> dict:
    """ARMS.md C1's clauses for one completion.  A pure function so that the PREDICATE has red cases,
    not only the judge's reading of its booleans (§34.3 review, opus Q7's structural point)."""
    result = asked.get("result") or {}
    sel = result.get("sel") or {}
    rev, before_rev = answer.get("rev"), answer.get("beforeRev")
    return {
        "completionIsBoundaryNoop": answer.get("ok") is True and answer.get("completion") == "verified-boundary-noop",
        "changedFalse": answer.get("changed") is False,
        # Two absent revisions compared equal before the review (codex 1): both must be present.
        "revisionUnchanged": isinstance(rev, int) and isinstance(before_rev, int) and rev == before_rev,
        "waitedMsPresent": isinstance((answer.get("boundaryNoop") or {}).get("waitedMs"), (int, float)),
        "generationStays1": gen_after == gen_before == "1",
        "engineReadAnswered": asked.get("answered") is True and asked.get("ok") is True,
        # §10.5 names `selectionType` none.  That field is the engine's FRESH readSelection() in
        # handleEditorGetState; `selection.collapsed/rectangles` is appendEditorState's callback cache
        # (probe_engine.cpp:1263), which a late TEXT_SELECTION leaves collapsed -- the L-C-late-K1 case
        # this read exists for.  Before the review only the cache was read (opus 1a).
        "noSelectionAt500ms": (asked.get("ok") is True and result.get("selectionType") == "none"
                               and sel.get("collapsed") is True and sel.get("n") == 0),
        # ARMS says "no toast": nothing appended to the page's toasts from the key to the read.  Before
        # the review this was "no reopen toast among the page's last three" (opus 1b, codex 1).
        "noToast": not toasts_after_key,
    }


def arm_c1(session, browser: str, urls: dict, reload, out: dict) -> dict:
    out.update({"arm": "c1", "rounds": [], "indent": None})
    for round_no in range(1, C1_ROUNDS + 1):
        for case in C1_POSITIONS:
            # A fresh page load only after a reopen: a noop consumes no generation, and the first Chrome
            # run went silent after seven reloads in a row (cause unknown, recorded in the README).
            rec = {"case": case, "round": round_no, "reload": reload() if gen(session) != "1" else None}
            rec["open"] = open_fixture(session, urls["boundaries"], f"c1-{case}-r{round_no}.odt")
            handle = mws.obs(session).get("documentHandle")
            spec, placed = place_native(session, browser, "boundaries", case)
            rec.update({"search": spec["search"], "backward": spec["backward"], "nativeCaret": spec["nativeCaret"],
                        "place": {k: placed.get(k) for k in ("ok", "keyed", "engineCaret", "afterClick")}})
            if not placed["ok"]:
                rec["outcome"] = "placement-mismatch"
                out["rounds"].append(rec)
                continue
            drain(session)
            gen_before = gen(session)
            toasts_before = len(toasts(session))   # the page's toasts accumulate (pp.INSTALL keeps every one)
            key = "Backspace" if spec["backward"] else "Delete"
            t_key = time.monotonic()
            press(session, browser, key)
            answer, entries = wait_response(session, is_delete_answer, 20)
            rec["answerAfterMs"] = round((time.monotonic() - t_key) * 1000)
            rec["answer"] = answer and {k: answer.get(k) for k in ("ok", "action", "completion", "changed", "rev",
                                                                  "beforeRev", "boundaryNoop", "code", "message",
                                                                  "mergeKey", "caretBefore")}
            if answer is None:
                rec["outcome"] = "no-answer"
                out["rounds"].append(rec)
                continue
            time.sleep(C1_READ_AFTER_S + 0.1)
            asked = ask_state(session, handle)
            rec["engineRead"] = {k: asked.get(k) for k in ("asked", "answered", "ok", "result")}
            rec["readAfterCompletionMs"] = round((time.monotonic() - t_key) * 1000 - rec["answerAfterMs"])
            pushes = [e for e in entries + asked.get("entries", []) if e.get("k") == "ev" and e.get("sel")]
            rec["selectionPushesAfterKey"] = [{"t": e["t"], "sel": e["sel"], "seq": e.get("seq")} for e in pushes
                                              if (e["sel"] or {}).get("n")]
            rec["generationAfter"] = gen(session)
            all_toasts = toasts(session)
            rec["toastsBeforeKey"] = toasts_before          # > 0 when the channel is alive (the open's toast)
            rec["toastsAfterKey"] = all_toasts[toasts_before:]
            rec["clauses"] = c1_clauses(answer, asked, gen_before, rec["generationAfter"], rec["toastsAfterKey"])
            rec["waitedMs"] = (answer.get("boundaryNoop") or {}).get("waitedMs")
            rec["outcome"] = "noop" if rec["clauses"]["completionIsBoundaryNoop"] else (
                "refused" if answer.get("ok") is False else answer.get("completion"))
            rec["pass"] = all(rec["clauses"].values())
            out["rounds"].append(rec)
            FLUSH["fn"]()
    # Recorded, not a criterion: L-C-number-or-indent position (iii), Backspace at the start of an
    # indented first paragraph (ruling 6 §15.1).  Placement by click + Home, no native caret.
    try:
        rec = {"reload": reload() if gen(session) != "1" else None,
               "open": open_fixture(session, urls["indent"], "c1-indent.odt")}
        out["indent"] = rec
        handle = mws.obs(session).get("documentHandle")
        click_fraction(session, 0.3, 0.06)
        pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 30)
        mws.quiet(session)
        press(session, browser, "Home")
        mws.quiet(session)
        drain(session)
        rec["caretBeforeKey"] = mws.caret_tuple(mws.obs(session).get("caret"))
        press(session, browser, "Backspace")
        answer, _ = wait_response(session, is_delete_answer, 20)
        rec["answer"] = answer and {k: answer.get(k) for k in ("ok", "completion", "changed", "boundaryNoop", "code", "mergeKey")}
        time.sleep(C1_READ_AFTER_S + 0.1)
        asked = ask_state(session, handle)
        rec["engineRead"] = {k: asked.get(k) for k in ("answered", "ok", "result")}
        rec["caretAfter"] = mws.caret_tuple(mws.obs(session).get("caret"))
        rec["generationAfter"] = gen(session)
    except Exception as error:  # noqa: BLE001 -- recorded; the arm's verdict does not depend on it
        (out["indent"] if isinstance(out.get("indent"), dict) else out.setdefault("indent", {}))["error"] = \
            f"{type(error).__name__}: {error}"
    FLUSH["fn"]()
    judged = [r for r in out["rounds"] if "pass" in r]
    out["placementMismatches"] = sum(1 for r in out["rounds"] if r.get("outcome") == "placement-mismatch")
    out["ok"] = bool(judged) and all(r["pass"] for r in judged) and len(judged) == C1_ROUNDS * len(C1_POSITIONS)
    return out


def reference_caret(entries: list, request_entry: dict) -> dict | None:
    """The last editor-state caret the engine pushed, in the same generation, before the request was posted.
    "Before" is the observer's own order `s`, not the 0.1 ms-rounded clock `t`: a push logged right after
    the request can share its `t` and was taken as the reference before the review (codex 1, E2)."""
    before = [e for e in entries if e.get("k") == "ev" and e.get("caret") and e.get("g") == request_entry.get("g")
              and e.get("s", -1) < request_entry.get("s", -1)]
    return before[-1] if before else None


def caret_equal(a, b) -> bool:
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    return all(a.get(k) == b.get(k) for k in ("x", "y", "width", "height"))


def judge_refusal(entries: list, failed: dict) -> dict:
    request = next((e for e in entries if e.get("k") == "rq" and e.get("rq") == failed.get("rq")
                    and e.get("g") == failed.get("g")), None)
    ref = reference_caret(entries, request) if request else None
    cb = failed.get("caretBefore") or {}
    rect = cb.get("rect") if isinstance(cb, dict) else None
    return {"request": request and {"t": request["t"], "action": request.get("action")},
            "referenceCaret": ref and {"t": ref["t"], "caret": ref["caret"], "seq": ref.get("seq")},
            "caretBefore": failed.get("caretBefore"), "code": failed.get("code"), "mergeKey": failed.get("mergeKey"),
            "clauses": {"caretBeforePresent": isinstance(cb, dict) and bool(cb),
                        "rectNotNull": isinstance(rect, dict),
                        "rectEqualsReference": bool(ref) and caret_equal(rect, ref["caret"]),
                        "sequenceNotAfterReference": (isinstance(cb, dict) and ref is not None
                                                      and isinstance(cb.get("sourceSequence"), int)
                                                      and isinstance(ref.get("seq"), int)
                                                      and cb["sourceSequence"] <= ref["seq"])}}


def arm_e2(session, browser: str, urls: dict, reload, out: dict) -> dict:
    out.update({"arm": "e2", "cases": [], "hold": None})
    for case in E2_CASES:
        spec = mws.tool_cases(frame_cell=True)[case]
        rec = {"case": case, "fixture": spec["fixture"], "search": spec["search"], "backward": spec["backward"],
               "expected": spec["expected"], "nativeDecision": spec["decision"]}
        rec["reload"] = reload()   # every refusal reopens the engine; each case starts at generation 1
        rec["open"] = open_fixture(session, urls[spec["fixture"]], f"e2-{case}.odt")
        _, placed = place_native(session, browser, spec["fixture"], case)
        rec["place"] = {k: placed.get(k) for k in ("ok", "keyed", "engineCaret")}
        if not placed["ok"]:
            rec["outcome"] = "placement-mismatch"
            out["cases"].append(rec)
            continue
        pre = drain(session)
        gen_before = gen(session)
        caret_before_key = mws.caret_tuple(mws.obs(session).get("caret"))
        press(session, browser, "Backspace" if spec["backward"] else "Delete")
        answer, entries = wait_response(session, is_delete_answer, 20)
        entries = pre + entries
        rec["answer"] = answer and {k: answer.get(k) for k in ("ok", "action", "completion", "changed", "code",
                                                              "message", "mergeKey", "caretBefore", "rev", "beforeRev")}
        if answer is None:
            rec["outcome"] = "no-answer"
        elif answer.get("ok"):
            rec["outcome"] = answer.get("completion")
            rec["note"] = ("verbatim, as the task asks: the Part B expectation says a refusal here and v20 "
                           "answered a completion")
        else:
            rec["outcome"] = "refused"
            rec["judge"] = judge_refusal(entries, answer)
            rec["pass"] = all(rec["judge"]["clauses"].values())
            window = mws.toast_window(session, gen_before, 60)
            rec["reopen"] = {"closed": window["closed"], "generation": window["generation"],
                             "toasts": [t for t in window["toasts"] if "重新載入" in (t or "")][-2:]}
            time.sleep(3.0)
            tail = drain(session)
            new_gen_carets = [e for e in tail if e.get("k") == "ev" and e.get("caret")
                              and str(e.get("g")) != str(answer.get("g"))]
            rec["e3Record"] = {"caretBeforeKey": caret_before_key,
                               "caretAfterReopen": mws.caret_tuple(mws.obs(session).get("caret")),
                               "newGenerationPushes": len(new_gen_carets),
                               "stage": ((answer.get("mergeKey") or {}).get("stage"))}
        out["cases"].append(rec)
        FLUSH["fn"]()
    # The hold across a merge: Delete held from I01's native caret (the end of `M12 number one`).
    try:
        rec = {"start": E2_HOLD_START, "reload": reload()}
        rec["open"] = open_fixture(session, urls["boundaries"], "e2-hold.odt")
        spec, placed = place_native(session, browser, "boundaries", E2_HOLD_START)
        rec.update({"search": spec["search"], "nativeCaret": spec["nativeCaret"],
                    "place": {k: placed.get(k) for k in ("ok", "keyed", "engineCaret")}})
        if placed["ok"]:
            pre = drain(session)
            gen_before = gen(session)
            rec["hold"] = hold_key(session, browser, "Delete", HOLD_MS)
            window = mws.toast_window(session, gen_before, 30)
            mws.quiet(session, 30)
            time.sleep(2.0)
            entries = pre + drain(session)
            deletes = [e for e in entries if is_delete_answer(e)]
            rec["deleteAnswers"] = [{"ok": e.get("ok"), "completion": e.get("completion"), "code": e.get("code"),
                                     "stage": (e.get("mergeKey") or {}).get("stage"), "t": e["t"],
                                     "comment": (e.get("keyUndo") or {}).get("comment")} for e in deletes]
            rec["merges"] = sum(1 for e in deletes if e.get("ok") and e.get("completion") == "verified-key-undo")
            failed = next((e for e in deletes if not e.get("ok")), None)
            rec["reopen"] = {"closed": window["closed"], "generation": window["generation"]}
            if failed is not None:
                rec["judge"] = judge_refusal(entries, failed)
                rec["pass"] = all(rec["judge"]["clauses"].values())
                rec["outcome"] = "refused"
            else:
                rec["outcome"] = "hold-reached-no-refusal"
        else:
            rec["outcome"] = "placement-mismatch"
        out["hold"] = rec
    except Exception as error:  # noqa: BLE001
        out["hold"] = {"error": f"{type(error).__name__}: {error}"}
    judged = [c for c in out["cases"] if "pass" in c] + ([out["hold"]] if out["hold"] and "pass" in out["hold"] else [])
    out["refusalsObserved"] = len(judged)
    out["ok"] = bool(judged) and all(c["pass"] for c in judged)
    return out


def lok_summary(entries: list) -> dict:
    """Every id-13 with its neighbours within LONE_WINDOW_MS, on the worker's clock (`tw`)."""
    events = [e for e in entries if e.get("k") == "mt" and e.get("type") == "lok" and isinstance(e.get("id"), int)]
    sized = [e for e in events if e["id"] == 13]
    out = {"lokEvents": len(events), "sizeChanges": len(sized), "lone": [], "flanked": 0,
           "idCounts": {}}
    for e in events:
        out["idCounts"][str(e["id"])] = out["idCounts"].get(str(e["id"]), 0) + 1
    for s in sized:
        tw = s.get("tw")
        if tw is None:
            continue
        near = [e for e in events if e is not s and e.get("tw") is not None and abs(e["tw"] - tw) <= LONE_WINDOW_MS]
        flank = [e["id"] for e in near if e["id"] in NOT_LONE_IDS]
        if flank:
            out["flanked"] += 1
        else:
            out["lone"].append({"tw": round(tw, 1), "neighbours": sorted({e["id"] for e in near}),
                                "neighbourNames": sorted({LOK_NAMES.get(e["id"], str(e["id"])) for e in near})})
    return out


def settle_lok(session, limit: float = 30.0, quiet_s: float = 1.5) -> list:
    """Wait until no lok event has arrived for `quiet_s`; return everything drained."""
    collected, last_change, deadline = [], time.monotonic(), time.monotonic() + limit
    while time.monotonic() < deadline:
        slice_ = drain(session)
        if any(e.get("k") == "mt" for e in slice_):
            last_change = time.monotonic()
        collected += slice_
        if time.monotonic() - last_change >= quiet_s and collected:
            break
        time.sleep(0.2)
    return collected


def arm_p2c(session, browser: str, urls: dict, out: dict) -> dict:
    out.update({"arm": "p2c", "instrumentedWorker": True, "phases": []})
    for label, url in (("long60", urls["long60"]), ("mixed8", urls["mixed8"])):
        phase = {"fixture": label}
        phase["open"] = open_fixture(session, url, f"p2c-{label}.odt")
        entries = settle_lok(session, 40)
        replies = [e for e in entries if e.get("k") == "rs" and e.get("op") == "pageRectangles" and e.get("ok")]
        states = [e for e in entries if e.get("k") == "ev" and e.get("dsc") is not None]
        phase["partsFirst"] = replies[0].get("parts") if replies else None
        phase["partsSettled"] = replies[-1].get("parts") if replies else None
        phase["rectCountsSeen"] = [len(parse_rects(r.get("rects")) or []) for r in replies]
        phase["documentSizeChangedCountAtOpen"] = states[0]["dsc"] if states else None
        phase["documentSizeChangedCountSettled"] = states[-1]["dsc"] if states else None
        phase["lazyLayout"] = (phase["partsFirst"] is not None and phase["partsSettled"] is not None
                               and phase["partsFirst"] < phase["partsSettled"])
        phase["openAndSettle"] = lok_summary(entries)
        if label == "long60":
            # P2-a/b's edits, on the trace worker, to see every size change beside its neighbours.
            rects = parse_rects((replies[-1] if replies else {}).get("rects"))
            if rects:
                doc_h = replies[-1]["docH"]
                last = rects[-1]
                click_fraction(session, 0.3, (last["y"] + min(7000, last["height"] - 1500)) / doc_h)
                pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 30)
                mws.quiet(session)
                press(session, browser, "End")
                mws.quiet(session)
                drain(session)
                edits = []
                base = len(rects)
                add = presses_until(session, browser, "Enter", "insert-paragraph-break", base + 1, P2_CAP,
                                    lambda count: count == base + 1, sink=edits)
                edits += settle_lok(session, 10)
                remove = presses_until(session, browser, "Backspace", "delete-backward", base, add["presses"],
                                       lambda count: False, sink=edits)
                edits += settle_lok(session, 10)
                phase["edits"] = {"enterPresses": add["presses"], "backspacePresses": remove["presses"],
                                  "countAfterAdd": add["count"], "countAfterRemove": remove["count"],
                                  "lokDuringSettles": lok_summary(edits),
                                  "sizeChangeNeighbours": [
                                      {"tw": round(e["tw"], 1), "near": sorted(LOK_NAMES.get(n["id"], str(n["id"]))
                                                                           for n in edits if n.get("k") == "mt"
                                                                           and n.get("type") == "lok" and n is not e
                                                                           and n.get("tw") is not None
                                                                           and abs(n["tw"] - e["tw"]) <= LONE_WINDOW_MS)}
                                      for e in edits if e.get("k") == "mt" and e.get("type") == "lok"
                                      and e.get("id") == 13 and e.get("tw") is not None][:12]}
        out["phases"].append(phase)
        FLUSH["fn"]()
    lone = sum(len(p["openAndSettle"]["lone"]) for p in out["phases"]) + sum(
        len(p.get("edits", {}).get("lokDuringSettles", {}).get("lone", [])) for p in out["phases"])
    seen_any = any(p["openAndSettle"]["lokEvents"] for p in out["phases"])
    out["loneSizeChanges"] = lone
    out["lokEventsSeen"] = seen_any
    out["reading"] = ("ESTABLISHED" if lone else ("NOT_ESTABLISHED" if seen_any else
                                                   "NOT_ESTABLISHED: no lok events seen (the instrument did not run)"))
    return out


# ------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--profile", default=DEFAULT_PROFILE)
    ap.add_argument("--arms", default="p1-60,p3,p2,c1,e2")
    ap.add_argument("--window", default="1400x1000")
    ap.add_argument("--trace-worker", action="store_true",
                    help="serve, in the mirror only, the profile's worker with finding 117's trace patch")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    arms = [a for a in args.arms.split(",") if a]
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        raise SystemExit(f"unknown arms {unknown}; known: {ARMS}")
    if "p2c" in arms and not args.trace_worker:
        raise SystemExit("p2c needs --trace-worker (the shipped worker drops the lok events)")
    if args.trace_worker and arms != ["p2c"]:
        raise SystemExit("--trace-worker serves diagnostic bytes; run p2c alone on it")
    window = tuple(int(v) for v in args.window.split("x"))
    pre = pre_run_checks()
    if pre["oursRunning"]:
        raise SystemExit(f"another runner of ours is active: {pre['oursRunning']}")

    root = HERE / "dist"
    source = pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8")
    lagging = pp.shell_lagging_source(root)
    if lagging:
        raise SystemExit(f"served from dist/ but not their source: {lagging}; run `make` for them")
    manifest = root / "profiles" / args.profile / "sdk-manifest.json"
    page, pin_before, wasm = pp.repointed_page(source, args.profile, manifest)
    html = (root / "e2-editor.html").read_text(encoding="utf-8")
    anchor = '<script type="module" src="./e2-editor-app.js"></script>'
    if html.count(anchor) != 1:
        raise SystemExit("the page's module script is not where the instrument expects it")
    overrides = {"e2-editor-app.js": page.encode("utf-8"),
                 "e2-editor.html": html.replace(anchor, OBSERVER + anchor).encode("utf-8")}
    worker_path = root / "profiles" / args.profile / "sdk-worker.js"
    worker_served_sha = mws.sha256_of(worker_path)
    if args.trace_worker:
        worker = worker_path.read_text(encoding="utf-8")
        if worker.count(TRACE_ANCHOR) != 1:
            raise SystemExit("the worker's handleCEvent anchor is not there exactly once")
        # The builder's placement (build_merge_trace_profile.py:77): BEFORE the switch, after the requestId
        # line.  Chrome p2c run 1 put it after the anchor, inside `case "ready"`, and logged nothing.
        patched = worker.replace(TRACE_ANCHOR, TRACE_ANCHOR.replace("  switch (event.type) {",
                                                                    TRACE_PATCH + "  switch (event.type) {"),
                                 1).encode("utf-8")
        overrides[f"profiles/{args.profile}/sdk-worker.js"] = patched
        worker_served_sha = sha256_bytes(patched)
    mirror = Path(tempfile.mkdtemp(prefix="v20-shakedown-")) / "root"
    pp.build_mirror(root, mirror, overrides)
    fixtures = {"long60": build_long_document(LONG_PAGES), "mixed8": mixed.build(),
                "indent": build_indent_fixture(),
                "boundaries": mws.FIXTURES["boundaries"][0].read_bytes(),
                "text-frame": mws.FIXTURES["text-frame"][0].read_bytes()}
    urls = {}
    for name, raw in fixtures.items():
        target = mirror / f"v20-{name}.odt"
        if target.exists():
            raise SystemExit(f"refusing to overwrite {target}")
        target.write_bytes(raw)
        urls[name] = f"./v20-{name}.odt"
    profile_hashes = {f: mws.sha256_of(root / "profiles" / args.profile / f)
                      for f in ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json")}
    report = {"runner": "run_v20_shakedown.py", "runnerSha256": sha256_bytes(Path(__file__).read_bytes())[:16],
              "counted": False, "browser": args.browser, "arms": arms, "window": window,
              "startedAt": now_iso(), "preRun": pre,
              "identity": {"profile": args.profile, "profileHashes": profile_hashes,
                           "workerServedSha256": worker_served_sha, "instrumentedWorker": args.trace_worker,
                           "pageSourceSha256": sha256_bytes(source.encode("utf-8")),
                           "pageServedSha256": sha256_bytes(page.encode("utf-8")),
                           "pinBefore": pin_before, "pinAfter": wasm[:16],
                           "htmlSha256": sha256_bytes(html.encode("utf-8")),
                           "shellSha256": mws.shell_digest(root), "restOfShellEqualsSource": True,
                           "fixtures": {n: sha256_bytes(raw) for n, raw in fixtures.items()}},
              "results": {}}
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port),
                               "--root", str(mirror)], cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        if args.browser == "chrome":
            session = pp.ChromeSession("cold")
            session.call("Emulation.setDeviceMetricsOverride",
                         {"width": window[0], "height": window[1], "deviceScaleFactor": 1, "mobile": False})
        else:
            os.environ["MOZ_HEADLESS_WIDTH"] = str(window[0])
            os.environ["MOZ_HEADLESS_HEIGHT"] = str(window[1])
            session = pp.FirefoxSession("cold")
        report["browserVersion"] = getattr(session, "version", None)

        def reload() -> dict:
            """A fresh page load: new worker generation 1, new observer nodes, the trace cursor reset."""
            t0 = time.monotonic()
            pp.navigate(session, base)
            boot = pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
            shims = pp.evaluate(session, pp.INSTALL)
            TRACE["last"] = -1
            return {"state": (boot or {}).get("state"), "shims": shims, "seconds": round(time.monotonic() - t0, 1),
                    "generation": gen(session)}

        def flush() -> None:
            args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))

        FLUSH["fn"] = flush
        report["boot"] = reload()
        for arm in arms:
            t0 = time.monotonic()
            result = report["results"][arm] = {"arm": arm}
            flush()
            try:
                if arm == "p1-60":
                    arm_p1(session, args.browser, urls["long60"], "p1-60", LONG_PAGES, result)
                elif arm == "p1-mixed":
                    arm_p1(session, args.browser, urls["mixed8"], "p1-mixed", 8, result)
                elif arm == "p2":
                    arm_p2(session, args.browser, urls["long60"], result)
                elif arm == "p3":
                    arm_p3(session, args.browser, urls["long60"], result)
                elif arm == "c1":
                    arm_c1(session, args.browser, urls, reload, result)
                elif arm == "e2":
                    arm_e2(session, args.browser, urls, reload, result)
                else:
                    arm_p2c(session, args.browser, urls, result)
            except Exception as error:  # noqa: BLE001 -- recorded with the arm, the run goes on
                result["runnerError"] = f"{type(error).__name__}: {error}"
            result["seconds"] = round(time.monotonic() - t0, 1)
            result["traceStats"] = dict(STATS)
            try:
                result["stateAfter"] = pp.evaluate(session, pp.READ_STATE)
            except Exception as error:  # noqa: BLE001 -- a silent page: recorded, and the run stops
                result["stateAfterError"] = f"{type(error).__name__}: {error}"
                report["abortedAfter"] = arm
                flush()
                break
            flush()
    finally:
        report["completedAt"] = now_iso()
        if session is not None:
            try:
                report["observerAtEnd"] = {k: v for k, v in mws.obs(session).items() if k != "responses"}
            except Exception as error:  # noqa: BLE001
                report["observerAtEnd"] = {"error": str(error)}
            try:
                session.close()
            except Exception as error:  # noqa: BLE001
                report["closeError"] = str(error)
            process = getattr(session, "process", None)
            if process is not None and process.poll() is None:   # a browser that would not close
                process.kill()
                report["browserKilled"] = True
        server.terminate()
        server.wait(timeout=10)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    summary = {arm: (r.get("ok") if "ok" in r else r.get("reading", r.get("runnerError"))) for arm, r in report["results"].items()}
    print(json.dumps({"browser": args.browser, "page": report["identity"]["pageServedSha256"][:16], **summary},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
