#!/usr/bin/env python3
"""The owner's hand test of host 0.2.12 (2026-10-12): two of its observations, reproduced.

  (1) "delete / backspace 刪去文字的時候會有殘影"
  (2) "將文字反白選取的時候，使用方向鍵會報錯"
  plus a baseline for the request "shift + 方向鍵 = 選取文字" (what Shift+Arrow does today).

Not a counted runner; no product byte is touched.  The owner's document (the
gitignored copy the production-UI runner uses) is uploaded as PROBE_NAME, so the
owner's own files are not edited.

(1) Hypothesis H2, from the page source: after a change every band in the window
is stale, a pass paints the bands under the view in DOCUMENT order, and a key that
arrives mid-pass ends the pass (`renderAgain`), so the next one starts at the top
of the view again.  The caret overlay moves at once (`paint()` on the state
update).  So the band holding the caret shows the old text for as long as every
band above it in the view takes -- and under repeated keys, possibly until the keys
stop.  On a Backspace the old text is the character just deleted, with the caret
already left of it: the ghost.

The reading is STATE, not pixels: `#canvas[data-bands]` says, per cached band,
the change counter it was asked at (`label`), and is written right after the band
is painted (publishWindow after paintBand); `#canvas[data-changes]` is the
counter; the sink rides the caret.  Per key: the time from the caret moving to the
caret's band carrying a label at least the counter's value once that key's
operation finished.  Arms: the caret in the FIRST band under the view (H2
predicts a short lag, one band) and in the SECOND (H2 predicts a longer one, and
starvation under rapid keys).  A positive control for the reading: under H2 the
second arm's lag exceeds the first's; if both are equal, H2 is not what is seen.

Pixels are asked one question only: after type-then-delete-the-same, with the
caret back where it was, are the view's pixels the same as before typing (a
PERSISTENT ghost), and are they the same as after a forced full repaint.

(2) A range selected by a drag through the page's own pointer handler, then one
arrow key; the toast, the state, the Worker generation and the latency line are
recorded.  Done for ArrowLeft, ArrowDown and End, each after a fresh selection.

  probe_hand_test_0212.py --out DIR [--browsers chrome,firefox]
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_m3_production_ui as ui  # noqa: E402
from check_m3_locks import Server, login, open_from_files  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, Instance  # noqa: E402
from probe_m3_gate0_coep import utc_now  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import PRESS  # noqa: E402
from run_e2_c_product_path import DRAG  # noqa: E402

PROBE_NAME = "probe-hand-0212.odt"
ARMS: set[str] = set()
# Per-run settings from the command line (SPEC-M3-autosave §9.12: 131-B takes 6 bursts; 121's witness takes
# Backspace and Delete on a selection).  Defaults are what the probe always did.
OPTIONS: dict[str, Any] = {"rapidRounds": 2, "selectionKeys": ("ArrowLeft", "ArrowDown", "End"), "ghostRapidKeys": 4}
MARK8 = "zqxzqxzq"
ui.CDP_KEYS.update({"ArrowLeft": ("ArrowLeft", "ArrowLeft", 37), "ArrowUp": ("ArrowUp", "ArrowUp", 38),
                    "ArrowRight": ("ArrowRight", "ArrowRight", 39), "ArrowDown": ("ArrowDown", "ArrowDown", 40)})
ui.WD_KEYS.update({"ArrowLeft": "", "ArrowUp": "", "ArrowRight": "", "ArrowDown": ""})

INSTRUMENT = """(() => {
  const canvas = document.querySelector('#canvas'), sink = document.querySelector('#sink'),
        paper = document.querySelector('#paper'), toastEl = document.querySelector('#toast'),
        pill = document.querySelector('#state-pill'), toolbar = document.querySelector('#toolbar');
  const t0 = performance.now(); window.__h_t0 = t0; const log = window.__h = [];
  const now = () => Math.round((performance.now() - t0) * 10) / 10;
  const win = () => (canvas.dataset.window || '0 0 0').split(' ').map(Number);
  const caretRow = () => { const [docRows] = win(); const h = paper.clientHeight || 1;
    return Math.round((parseFloat(sink.style.top) || 0) * docRows / h); };
  const bands = () => (canvas.dataset.bands || '').split(' ').filter(Boolean).map((s) => s.split(':').map(Number));
  const caretBand = () => { const r = caretRow();
    const b = bands().find(([, top, rows]) => r >= top && r < top + rows); return b ? { index: b[0], label: b[3] } : null; };
  const rec = (what) => log.push({ t: now(), what, changes: Number(canvas.dataset.changes), caretRow: caretRow(),
    caretBand: caretBand(), bands: canvas.dataset.bands, sink: [sink.style.left, sink.style.top],
    state: pill.dataset.state, shape: toolbar.dataset.selectionShape,
    gen: document.querySelector('#s-generation').textContent,
    latency: document.querySelector('#s-latency').textContent,
    toast: toastEl.classList.contains('show') ? toastEl.textContent : null });
  new MutationObserver(() => rec('sink')).observe(sink, { attributes: true, attributeFilter: ['style'] });
  new MutationObserver(() => rec('canvas')).observe(canvas, { attributes: true,
    attributeFilter: ['data-bands', 'data-changes', 'data-window'] });
  new MutationObserver(() => rec('toast')).observe(toastEl, { attributes: true, childList: true,
    characterData: true, subtree: true });
  new MutationObserver(() => rec('shape')).observe(toolbar, { attributes: true, attributeFilter: ['data-selection-shape'] });
  sink.addEventListener('keydown', (e) => rec('keydown:' + (e.shiftKey ? 'Shift+' : '') + e.key), true);
  rec('installed'); return true; })()"""
# Chrome only, before the first navigation: every message to and from a Worker
# the page creates, with performance.now() -- whether a paint waits behind other
# requests in the document Worker, or takes its time by itself.
WORKER_TRACE = """(() => { const T = window.__wm = []; const P = Worker.prototype.postMessage;
  Worker.prototype.postMessage = function (m, t) { try { if (m && m.kind)
    T.push({ t: performance.now(), d: 'out', k: m.kind, id: m.requestId, op: m.operation,
      region: m.operation === 'paint' && m.payload ? [m.payload.yTwips, m.payload.heightTwips, m.payload.canvasWidthPx,
        m.payload.canvasHeightPx] : undefined }); } catch (e) {}
    return P.call(this, m, t); };
  const W = window.Worker;
  window.Worker = function (url, opts) { const w = new W(url, opts);
    w.addEventListener('message', (e) => { const m = e.data; try { T.push({ t: performance.now(), d: 'in',
      k: m && m.kind, id: m && m.requestId, ev: m && m.event, ok: m && m.ok,
      err: m && m.ok === false ? JSON.stringify(m.error || m).slice(0, 400) : undefined }); } catch (x) {} });
    return w; };
  window.Worker.prototype = W.prototype;
  try { new PerformanceObserver((list) => { for (const e of list.getEntries())
    T.push({ t: e.startTime, d: 'longtask', k: 'longtask', dur: e.duration }); }).observe({ type: 'longtask', buffered: true }); }
  catch (e) { T.push({ t: performance.now(), d: 'longtask', k: 'unsupported' }); } })()"""
READ_WM = "(() => ({ t0: window.__h_t0 ?? null, wm: (window.__wm || []).slice(ARG_FROM) }))()"
MARK_WM = "(() => (window.__wm || []).length)()"
MARK_LOG = "(() => { const n = window.__h.length; return n; })()"
READ_LOG = "(() => window.__h.slice(ARG_FROM))()"

# Where things are, in the desk's terms, read once per arm.
GEOMETRY = """(() => { const c = document.querySelector('#canvas'), desk = document.querySelector('#desk'),
  paper = document.querySelector('#paper'), sink = document.querySelector('#sink');
  const [docRows, winTop, rows] = (c.dataset.window || '0 0 0').split(' ').map(Number);
  const pr = paper.getBoundingClientRect(), vr = desk.getBoundingClientRect(); const scale = docRows / pr.height;
  return { docRows, winTop, rows, canvasWidth: c.width, dpr: devicePixelRatio, scrollTop: desk.scrollTop,
    deskHeight: desk.clientHeight, paperHeight: pr.height,
    view: [Math.floor((Math.max(vr.top, pr.top) - pr.top) * scale), Math.ceil((Math.min(vr.bottom, pr.bottom) - pr.top) * scale)],
    caretRow: Math.round((parseFloat(sink.style.top) || 0) * docRows / (paper.clientHeight || 1)),
    bands: c.dataset.bands, changes: Number(c.dataset.changes) }; })()"""
# Scroll the desk so that the caret sits at FRACTION of the view's height.
SCROLL_CARET_TO = """(() => { const desk = document.querySelector('#desk'), sink = document.querySelector('#sink'),
  paper = document.querySelector('#paper');
  const caretCss = (parseFloat(sink.style.top) || 0) + paper.offsetTop;
  desk.scrollTop = Math.max(0, caretCss - desk.clientHeight * ARG_F); return desk.scrollTop; })()"""
# The view's rows of the canvas, kept for a later comparison.
SNAP = """(() => { const c = document.querySelector('#canvas'), desk = document.querySelector('#desk'),
  paper = document.querySelector('#paper');
  const [docRows, winTop, h] = c.dataset.window.split(' ').map(Number);
  const pr = paper.getBoundingClientRect(), vr = desk.getBoundingClientRect(); const scale = docRows / pr.height;
  const top = Math.max(0, Math.floor((Math.max(vr.top, pr.top) - pr.top) * scale) - winTop);
  const bottom = Math.min(h, Math.ceil((Math.min(vr.bottom, pr.bottom) - pr.top) * scale) - winTop);
  window.__snap = window.__snap || {};
  window.__snap['ARG_NAME'] = { winTop, top, bottom, width: c.width,
    data: c.getContext('2d').getImageData(0, top, c.width, bottom - top).data };
  return { winTop, top, bottom, width: c.width }; })()"""
# Differing pixels between two snaps, with their bounding box (canvas rows).
DIFF = """(() => { const a = window.__snap['ARG_A'], b = window.__snap['ARG_B'];
  if (!a || !b) return { error: 'missing snap' };
  if (a.winTop !== b.winTop || a.top !== b.top || a.bottom !== b.bottom || a.width !== b.width)
    return { error: 'different geometry', a: [a.winTop, a.top, a.bottom, a.width], b: [b.winTop, b.top, b.bottom, b.width] };
  let n = 0, x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1;
  for (let i = 0; i < a.data.length; i += 4) {
    if (a.data[i] !== b.data[i] || a.data[i + 1] !== b.data[i + 1] || a.data[i + 2] !== b.data[i + 2] || a.data[i + 3] !== b.data[i + 3]) {
      n += 1; const p = i / 4, x = p % a.width, y = a.top + Math.floor(p / a.width);
      x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); } }
  return { differing: n, box: n ? [x0, y0, x1, y1] : null, pixels: a.data.length / 4 }; })()"""


# 128-B's host-segment cell (SPEC-M3-autosave §9.4, review 1 item 3): a key typed while a manual save's host
# part is out must be drawn before that part ends.  Locally the host part is ~100 ms, too short to type into, so
# every PUT the page sends is held ARG_MS before it goes out (the host calls the global `fetch` at call time,
# litecore js/litecore-editor.js `send()`).  ARG_HOLD true also holds every `paint` request to a Worker while a
# PUT is out and sends them when it is answered: the user-visible effect of the draft's remedy A (defer repaints
# while `run()` is out) -- the red control, made without changing a page byte.
SLOW_PUT = """(() => { const t = () => performance.now() - window.__h_t0;
  if (!window.__origFetch) { window.__origFetch = window.fetch; window.__origPost = Worker.prototype.postMessage; }
  const F = window.__origFetch, P = window.__origPost, st = window.__put = { holdPaints: ARG_HOLD, out: 0, puts: [], heldPaints: 0 };
  const queue = [];
  Worker.prototype.postMessage = function (m, tr) {
    if (st.holdPaints && st.out > 0 && m && m.operation === 'paint') { st.heldPaints += 1; queue.push([this, m, tr]); return; }
    return P.call(this, m, tr); };
  window.fetch = function (input, init) {
    const method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    if (method !== 'PUT') return F.apply(this, arguments);
    const rec = { held: t() }; st.puts.push(rec); st.out += 1;
    return new Promise((r) => setTimeout(r, ARG_MS)).then(() => { rec.sent = t(); return F.call(window, input, init); })
      .finally(() => { rec.answered = t(); st.out -= 1;
        if (st.out === 0) for (const [w, m, tr] of queue.splice(0)) P.call(w, m, tr); }); };
  return true; })()"""
UNSLOW_PUT = """(() => { if (window.__origFetch) { window.fetch = window.__origFetch; Worker.prototype.postMessage = window.__origPost; }
  return window.__put || null; })()"""
PUT_STATE = "(() => window.__put ? { out: window.__put.out, puts: window.__put.puts.slice(), heldPaints: window.__put.heldPaints } : null)()"
HOSTSEG_KEY = "q"
HOSTSEG_HOLD_MS = 3000


def hostseg_arm(name: str, kind: str, session, hold_paints: bool) -> dict[str, Any]:
    """A manual save; while its PUT is held, ONE real key; was the caret's band fresh before the PUT was answered?"""
    rec: dict[str, Any] = {"arm": name, "holdPaints": hold_paints, "holdMs": HOSTSEG_HOLD_MS}
    rec["click"] = ui.click(session, ui.IN_TEXT)
    time.sleep(1.0)
    rec["quietBefore"] = ui.quiet(session)
    host_before = evaluate(session, ui.HOST) or {}
    rec["savesBefore"] = len(host_before.get("saves") or [])
    evaluate(session, SLOW_PUT.replace("ARG_MS", str(HOSTSEG_HOLD_MS)).replace("ARG_HOLD", "true" if hold_paints else "false"))
    start = evaluate(session, MARK_LOG)
    evaluate(session, PRESS.replace("ARG_ACTION", "save"))
    deadline, seen = time.monotonic() + 30, None
    while time.monotonic() < deadline:
        seen = evaluate(session, PUT_STATE)
        if seen and seen["out"] > 0:
            break
        time.sleep(0.02)
    rec["putSeen"] = seen
    if not seen or seen["out"] <= 0:
        rec["error"] = "no PUT was held within 30 s of pressing save"
        evaluate(session, UNSLOW_PUT)
        return rec
    time.sleep(0.3)
    ui.press(session, kind, HOSTSEG_KEY)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        seen = evaluate(session, PUT_STATE)
        host = evaluate(session, ui.HOST) or {}
        saves = host.get("saves") or []
        if seen["out"] == 0 and len(saves) > rec["savesBefore"] and saves[-1].get("settled") is True:
            break
        time.sleep(0.05)
    time.sleep(1.0)
    rec["settled"] = ui.quiet(session)
    rec["put"] = evaluate(session, UNSLOW_PUT)
    host = evaluate(session, ui.HOST) or {}
    rec["save"] = (host.get("saves") or [None])[-1]
    log = evaluate(session, READ_LOG.replace("ARG_FROM", str(start)))
    rec["log"] = log
    rec["lag"] = lag_per_key(log)
    return rec


def hostseg_verdict(rec: dict[str, Any]) -> dict[str, Any]:
    """PASS: the one key came while the PUT was held, and its band was fresh before the PUT was answered."""
    puts = ((rec.get("put") or {}).get("puts") or [])
    lag = rec.get("lag") or []
    if rec.get("error") or len(puts) != 1 or len(lag) != 1 or (rec.get("save") or {}).get("outcome") != "saved":
        return {"verdict": "NOT_JUDGED", "why": rec.get("error") or f"{len(puts)} PUTs, {len(lag)} keys, save {(rec.get('save') or {}).get('outcome')}"}
    put, key = puts[0], lag[0]
    # The target is the counter after THIS key's own change (its document-invalidated), not the highest value
    # in the log: `run()` bumps the counter again when the save's host part ends, and lag_per_key's "done"
    # (the log's maximum) then waits for that -- the first run on 0.2.13 judged both arms FAIL that way.
    log = rec.get("log") or []
    down = next((i for i, r in enumerate(log) if r["what"].startswith("keydown:")), None)
    c0 = log[down]["changes"] if down is not None else None
    own = next((r["changes"] for r in log[down:] if r["changes"] > c0), None) if down is not None else None
    moved = key["tKey"] + key["caretMovedMs"] if key["caretMovedMs"] is not None else key["tKey"]
    first = next((r for r in log[down:] if own is not None and r.get("caretBand")
                  and r["caretBand"]["label"] >= own and r["t"] >= moved), None) if down is not None else None
    fresh = None if first is None else first["t"]
    typed_during = put["held"] < key["tKey"] < put["answered"]
    if not typed_during:
        return {"verdict": "NOT_JUDGED", "why": f"key at {key['tKey']} ms, PUT held {put['held']}..{put['answered']}"}
    drawn_before = fresh is not None and fresh < put["answered"]
    return {"verdict": "PASS" if drawn_before else "FAIL", "keyMs": key["tKey"], "freshMs": fresh,
            "putHeldMs": put["held"], "putAnsweredMs": put["answered"], "caretMovedMs": key["caretMovedMs"],
            "caretBandFreshMs": None if fresh is None else round(fresh - key["tKey"], 1),
            "ownChange": own, "heldPaints": (rec.get("put") or {}).get("heldPaints")}


# A burst of deletes (2026-10-12, found by the 128-B run on 0.2.13): a Backspace whose `beforeinput` comes while
# the previous delete's selection barrier is out reads the engine's one-unit RANGE and goes out as
# delete-selection, which the gate then refuses on the collapsed caret.  Counted from the latency line, which
# `run()` rewrites once per action (「⌫ 刪除 N ms」 or 「刪除選取 失敗」).
LATENCY_LOG = """(() => { const el = document.querySelector('#s-latency'); const t0 = window.__h_t0;
  const L = window.__lat = []; new MutationObserver(() => L.push({ t: Math.round((performance.now() - t0) * 10) / 10,
    text: el.textContent })).observe(el, { childList: true, characterData: true, subtree: true }); return true; })()"""
READ_LATENCY = "(() => (window.__lat || []).slice(ARG_FROM))()"
MARK_LATENCY = "(() => (window.__lat || []).length)()"
RAPID_N, RAPID_GAP = 20, 0.05


def rapid_arm(kind: str, session, rounds: int = 2) -> dict[str, Any]:
    rec: dict[str, Any] = {"arm": "rapid20", "n": RAPID_N, "gapS": RAPID_GAP, "rounds": []}
    rec["click"] = ui.click(session, ui.IN_TEXT)
    evaluate(session, SCROLL_CARET_TO.replace("ARG_F", "0.15"))
    time.sleep(1.5)
    ui.quiet(session)
    if evaluate(session, "(() => Array.isArray(window.__lat))()") is not True:
        evaluate(session, LATENCY_LOG)
    for n in range(rounds):
        for ch in (MARK8 * 3)[:RAPID_N]:
            ui.keyed(session, kind, ch)
        time.sleep(1.0)
        ui.quiet(session)
        snap = f"rapid{n}"
        evaluate(session, SNAP.replace("ARG_NAME", snap + "-before"))
        start = evaluate(session, MARK_LATENCY)
        keys_at(session, kind, "Backspace", RAPID_N, RAPID_GAP)
        time.sleep(2.0)
        ui.quiet(session, 60)
        lat = evaluate(session, READ_LATENCY.replace("ARG_FROM", str(start)))
        ok = sum(1 for x in lat if x["text"].startswith("⌫ 刪除 "))
        refused = sum(1 for x in lat if x["text"] == "刪除選取 失敗")
        rec["rounds"].append({"latency": lat, "deleted": ok, "refusedDeleteSelection": refused,
                              "other": sorted({x["text"] for x in lat if not x["text"].startswith("⌫ 刪除 ")
                                               and x["text"] != "刪除選取 失敗"})})
        # Whatever the burst left, delete it one key at a time so the next round starts where this one did.
        for _ in range(refused):
            ui.press(session, kind, "Backspace")
            time.sleep(0.6)
        ui.quiet(session)
    return rec


def keys_at(session, kind: str, key: str, count: int, gap: float, shift: bool = False) -> None:
    for i in range(count):
        ui.press(session, kind, key, shift)
        if i < count - 1:
            time.sleep(gap)


def lag_per_key(log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For each keydown: when the caret moved, the counter once the key was done
    (the highest value before the next keydown or the end), and when the caret's
    band first carried a label at least that high."""
    downs = [i for i, r in enumerate(log) if r["what"].startswith("keydown:")]
    out = []
    for n, i in enumerate(downs):
        end = downs[n + 1] if n + 1 < len(downs) else len(log)
        window = log[i:end]
        t_key = log[i]["t"]
        moved = next((r["t"] for r in window if r["what"] == "sink" and r["sink"] != log[i]["sink"]), None)
        done = max((r["changes"] for r in window), default=log[i]["changes"])
        # Searched to the END of the log, not this key's window: under rapid keys
        # the band may only catch up after later keys.
        fresh = next((r for r in log[i:] if r.get("caretBand") and r["caretBand"]["label"] >= done
                      and r["t"] >= (moved or t_key)), None)
        out.append({"key": log[i]["what"], "tKey": t_key,
                    "caretMovedMs": None if moved is None else round(moved - t_key, 1),
                    "counterDone": done,
                    "caretBandFreshMs": None if fresh is None else round(fresh["t"] - t_key, 1),
                    "staleAfterCaretMs": None if (fresh is None or moved is None) else round(fresh["t"] - moved, 1),
                    "freshBand": None if fresh is None else fresh["caretBand"]})
    return out


def ghost_arm(name: str, kind: str, session, y: str, caret_at: float, shots: Path) -> dict[str, Any]:
    rec: dict[str, Any] = {"arm": name, "y": y, "caretAt": caret_at}
    rec["click"] = ui.click(session, ("0.5", y))
    rec["scroll"] = evaluate(session, SCROLL_CARET_TO.replace("ARG_F", str(caret_at)))
    time.sleep(1.5)
    ui.quiet(session)
    time.sleep(1.0)
    rec["geometry"] = evaluate(session, GEOMETRY)
    rec["snapBefore"] = evaluate(session, SNAP.replace("ARG_NAME", name + "-before"))
    n_rapid = OPTIONS["ghostRapidKeys"]
    rec["rapidKeys"] = n_rapid
    # Four single presses and n_rapid rapid ones delete what was typed (n_rapid 4: MARK8, as always).
    rec["typed"] = [ui.keyed(session, kind, ch) for ch in (MARK8 * 4)[:4 + n_rapid]]
    rec["geometryTyped"] = evaluate(session, GEOMETRY)
    start = evaluate(session, MARK_LOG)
    wm_start = evaluate(session, MARK_WM)
    # Four single presses, each allowed to settle.
    for _ in range(4):
        ui.press(session, kind, "Backspace")
        time.sleep(1.2)
        ui.quiet(session)
    single = evaluate(session, READ_LOG.replace("ARG_FROM", str(start)))
    rec["single"] = lag_per_key(single)
    rec["singleLog"] = single
    rec["singleWorker"] = evaluate(session, READ_WM.replace("ARG_FROM", str(wm_start)))
    # n_rapid rapid presses (default 4), 50 ms apart (a held key repeats at about 30 ms).
    start = evaluate(session, MARK_LOG)
    if kind == "chrome":
        keys_at(session, kind, "Backspace", n_rapid - 1, 0.05)
        shot = session.screenshot()
        (shots / f"{kind}-{name}-mid-rapid.png").write_bytes(shot)
        ui.press(session, kind, "Backspace")
    else:
        keys_at(session, kind, "Backspace", n_rapid, 0.05)
    time.sleep(1.5)
    rec["settledAfterRapid"] = ui.quiet(session)
    rapid = evaluate(session, READ_LOG.replace("ARG_FROM", str(start)))
    rec["rapid"] = lag_per_key(rapid)
    rec["rapidLog"] = rapid
    time.sleep(1.0)
    rec["geometryAfter"] = evaluate(session, GEOMETRY)
    rec["snapAfter"] = evaluate(session, SNAP.replace("ARG_NAME", name + "-after"))
    rec["persistent"] = evaluate(session, DIFF.replace("ARG_A", name + "-before").replace("ARG_B", name + "-after"))
    if kind == "chrome":
        (shots / f"{kind}-{name}-settled.png").write_bytes(session.screenshot())
    return rec


def selection_arm(kind: str, session, y: str, key: str) -> dict[str, Any]:
    rec: dict[str, Any] = {"arm": "selection+" + key, "y": y}
    rec["click"] = ui.click(session, ("0.5", y))
    evaluate(session, DRAG.replace("ARG_X1", "0.3").replace("ARG_Y1", y).replace("ARG_X2", "0.5").replace("ARG_Y2", y))
    time.sleep(1.5)
    rec["afterDrag"] = {**ui.quiet(session), "shape": evaluate(session, "(() => document.querySelector('#toolbar').dataset.selectionShape)()")}
    start = evaluate(session, MARK_LOG)
    ui.press(session, kind, key)
    time.sleep(3.0)
    rec["settled"] = ui.quiet(session, 60)
    rec["log"] = evaluate(session, READ_LOG.replace("ARG_FROM", str(start)))
    rec["toasts"] = sorted({r["toast"] for r in rec["log"] if r.get("toast")})
    rec["gens"] = sorted({r["gen"] for r in rec["log"]})
    return rec


def shift_arm(kind: str, session, y: str) -> dict[str, Any]:
    rec: dict[str, Any] = {"arm": "shift+ArrowRight", "y": y}
    rec["click"] = ui.click(session, ("0.5", y))
    start = evaluate(session, MARK_LOG)
    keys_at(session, kind, "ArrowRight", 3, 0.6, shift=True)
    time.sleep(1.5)
    rec["settled"] = ui.quiet(session)
    rec["log"] = evaluate(session, READ_LOG.replace("ARG_FROM", str(start)))
    rec["shapes"] = [r["shape"] for r in rec["log"] if r["what"] in ("shape", "sink")]
    return rec


def run_browser(kind: str, server: Server, doc: bytes, out: Path) -> dict[str, Any]:
    base = server.instance.base
    record: dict[str, Any] = {"browser": kind, "startedAt": utc_now()}
    record["clearedLocks"] = server.clear_locks()
    record["upload"] = server.upload(server.admin, PROBE_NAME, doc)
    session = ui.new_session(kind)
    record["version"] = getattr(session, "version", None)
    if kind == "chrome" and ARMS & {"trace"}:
        session.call("Page.addScriptToEvaluateOnNewDocument", {"source": WORKER_TRACE})
        record["workerTrace"] = True
    try:
        record["login"] = login(session, base, "admin", server.instance.password)
        open_from_files(session, base, "", PROBE_NAME, record)
        record["opened"] = ui.quiet(session, 90)
        evaluate(session, INSTRUMENT)
        record["host"] = evaluate(session, ui.HOST)
        # High: the caret in the first band under the view (row ~231, band 0, view at the top).
        if "high" in ARMS:
            record["high"] = ghost_arm("high", kind, session, ui.IN_TEXT[1], 0.15, out)
        # Low: a caret in band 1 with band 0 also under the view.  y 0.0584 is
        # row ~1300 at 900 CSS px; whether it lands in band 1 is read back
        # (`geometry.caretRow`), not assumed.
        if "low" in ARMS:
            record["low"] = ghost_arm("low", kind, session, "0.0584", 0.85, out)
        if "selection" in ARMS:
            record["selection"] = [selection_arm(kind, session, ui.IN_TEXT[1], key)
                               for key in OPTIONS["selectionKeys"]]
        if "shift" in ARMS:
            record["shift"] = shift_arm(kind, session, ui.IN_TEXT[1])
        if "rapid20" in ARMS:
            record["rapid20"] = rapid_arm(kind, session, OPTIONS["rapidRounds"])
        if "hostseg" in ARMS:
            record["hostseg"] = hostseg_arm("hostseg", kind, session, False)
            record["hostseg"]["judged"] = hostseg_verdict(record["hostseg"])
        if "hostseg-red" in ARMS:
            record["hostsegRed"] = hostseg_arm("hostseg-red", kind, session, True)
            record["hostsegRed"]["judged"] = hostseg_verdict(record["hostsegRed"])
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
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
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--arms", default="high,low,selection,shift",
                        help="any of high,low,selection,shift,trace,hostseg,hostseg-red (trace: Chrome's Worker "
                             "message log; hostseg: 128-B's host-segment cell, hostseg-red its red control)")
    parser.add_argument("--rapid-rounds", type=int, default=2, help="bursts in the rapid20 arm")
    parser.add_argument("--ghost-rapid-keys", type=int, default=4, help="rapid Backspaces in the high/low arms")
    parser.add_argument("--selection-keys", default="ArrowLeft,ArrowDown,End",
                        help="the key pressed after each fresh drag selection, one arm per key")
    args = parser.parse_args()
    ARMS.update(args.arms.split(","))
    OPTIONS.update(rapidRounds=args.rapid_rounds, selectionKeys=tuple(args.selection_keys.split(",")),
                   ghostRapidKeys=args.ghost_rapid_keys)
    args.out.mkdir(parents=True, exist_ok=True)
    doc = ui.DOC.read_bytes()
    instance = Instance(DEFAULT_DDEV)
    server = Server(instance, [])
    report: dict[str, Any] = {"probe": "probe_hand_test_0212.py", "startedAt": utc_now(),
                              "static": ui.static_facts(DEFAULT_DDEV), "arms": sorted(ARMS),
                              "options": {**OPTIONS, "selectionKeys": list(OPTIONS["selectionKeys"])}, "runs": []}
    try:
        for kind in args.browsers.split(","):
            run = run_browser(kind, server, doc, args.out)
            report["runs"].append(run)
            (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
            print(kind, "fatal" if run.get("fatal") else "done", flush=True)
    finally:
        server.clear_locks()
        report["completedAt"] = utc_now()
        (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
