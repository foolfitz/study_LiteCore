#!/usr/bin/env python3
"""M3 page honesty: specs/SPEC-M3-page-honesty.md §4 as amended by §7.

Finding 107 (leaving with unsaved edits asks nothing), finding 106 (a held
Ctrl+S saves once per key repeat), and the owner's ruling A (a read-only file
opens view-only), measured through the real Files -> editor route, in a fresh
browser per arm; U6 drives the page without a host (download mode), served from
dist/ by web/serve.py.

How "asked" is observed (§7.2): after the open, the runner wraps
Event.prototype.preventDefault and the BeforeUnloadEvent returnValue setter and
appends every beforeunload call, with who made it (from the stack), to
localStorage under this cell's own nonce; a last listener appends `fired`.
localStorage, not sessionStorage: it is the same origin after the navigation
whatever COOP does to the browsing context group.  No `fired` = the cell does not
count.  Chrome also shows the dialog over CDP (a trusted click first gives the
page the activation a dialog needs); Firefox under WebDriver classic accepts
the prompt by itself, so there only the recorder speaks.

    python3 wasm_sdk_probe/tools/check_m3_page_honesty.py --label shakedown --arms U1 --browsers chrome --repeats 1
    python3 wasm_sdk_probe/tools/check_m3_page_honesty.py --label counted
    python3 wasm_sdk_probe/tools/check_m3_page_honesty.py --score findings/evidence/m3-page-honesty/runs/<file>.json
"""
from __future__ import annotations

import argparse
import copy
import json
import secrets
import subprocess
import sys
import tempfile
import time
import hashlib
import re
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_host_entry import CTRL_S, MARKER, host_record, paragraph_texts, server_file  # noqa: E402
from check_m3_locks import (  # noqa: E402
    BAR, CENTER, OTHER, RO_NAME, LockChrome, Server, chrome_download_dir, downloaded, edit, edited, insert_marker,
    login, open_from_files, save, wire)
from check_m3_skeleton_open import (  # noqa: E402
    DEFAULT_DDEV, FIXTURE, NAME, ROUTE, Instance, binding_fields, host_binding, product_state, state_until)
from probe_m3_gate0_coep import DIST, firefox_profile, sha256_file, utc_now, wait_until  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import DOC_WINDOW_JS, POINT_AT, PRESS, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-page-honesty"
ODT = "application/vnd.oasis.opendocument.text"
BOTH = ("chrome", "firefox")
# Bindings for a counted run, written down before it (spec §7.6 style): the page,
# the session subclass that holds the view-only gate, and the host version.
# Written 2026-09-29 (spec §7.11), before the re-shakedown and counted runs.
# Re-pointed 2026-10-15 (task 10-15c P4, before binding v20) to host 0.2.23's page (shell v72, engine v20).  The previous pin was
# d761f1cee9d26c50c0b152348d74c3d05f540e9228927815d93ad6ec161e7dcd (SPEC-M3-autosave §9.19, 0.2.13/v62; the 0.2.13 and 0.2.14 counts ran on it).
PAGE_SHA256: str | None = "605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f"   # host 0.2.26 (engine v21, shell v74, finding 154's host rule), 2026-10-17; was 901dd6a6 (0.2.24, v73, finding 145), ccb67a52 (0.2.23, v72), d761f1ce (autosave §9.19, 0.2.13), 8909564e (production-ui §17 C′), 36c2b18b (§16 R⁗), 18c8afbe (§15 R‴), 537d62d7 (§14 R′), e00ab76a (§13.5), e97d6e03
SESSION_SHA256: str | None = "f1509ff22e6e2d8d945cfd803d293fd4cf102cece27618f54825571a2e1ef3a8"   # shell v74 (0.2.26); was f47c80ec (link-batch §17, 0.2.23), 62a2a20e (§14 R′), ee3e53a2, 3f5f754b
# SPEC-M3-zstd Z3: re-counted on host 0.2.5 (7420418), written 2026-09-30 before that run.
HOST_VERSION = "0.2.26"   # engine v21 + finding 154; was 0.2.24 (finding 145), 0.2.23 (link-batch §17), 0.2.14, 0.2.13, 0.2.12, 0.2.11, 0.2.10, 0.2.9, 0.2.8, 0.2.7
# The host commit too (review 2026-09-29, implementation): a version string alone
# lets a changed host with an unchanged info.xml through.
HOST_COMMIT: str | None = "3c01876"   # 0.2.26; was 1479e56 (finding 145), 2ccf1a9 (link-batch §17), 237f2cb, e028517, b245ae7, 6b53c2e, d87960d, 069de55, 4140e00, 0488586
# arm -> (cells, browsers, rounds in a counted run)
PLAN = {
    "U0": ("U0", BOTH, 3), "U1": ("U1", BOTH, 3), "Uwin": ("U-window", BOTH, 3), "U2": ("U2", BOTH, 3),
    "U3": ("U3", BOTH, 3), "U4": ("U4", BOTH, 3), "U5": ("U5", BOTH, 3), "U7": ("U7", BOTH, 3),
    "U6a": ("U6 first half", BOTH, 3), "U6b": ("U6 second half", BOTH, 3),
    "Kheld": ("K-held", BOTH, 3), "Ksep": ("K-sep", BOTH, 3), "Ktwo": ("K-two", BOTH, 3),
    "Vro": ("V1 V2 V4 V5 V6 V7", BOTH, 3), "Vrw": ("V2 writable control", BOTH, 3),
}

RECORDER = """(() => {
  const key = 'm3honesty:' + ARG_NONCE;
  const put = (entry) => {
    const list = JSON.parse(localStorage.getItem(key) || '[]');
    list.push({ ...entry, at: Math.round(performance.now()) });
    localStorage.setItem(key, JSON.stringify(list));
  };
  const who = () => {
    const stack = new Error().stack || '';
    if (stack.includes('m3honesty-runner')) return 'runner';
    if (stack.includes('litecore-editor.js')) return 'host';
    if (stack.includes('e2-editor-app.js')) return 'page';
    return 'other: ' + stack.split('\\n').slice(0, 4).join(' | ');
  };
  const prevent = Event.prototype.preventDefault;
  Event.prototype.preventDefault = function () {
    if (this.type === 'beforeunload') put({ what: 'preventDefault', who: who() });
    return prevent.call(this);
  };
  const desc = Object.getOwnPropertyDescriptor(BeforeUnloadEvent.prototype, 'returnValue');
  Object.defineProperty(BeforeUnloadEvent.prototype, 'returnValue', {
    configurable: true, enumerable: desc.enumerable,
    get() { return desc.get.call(this); },
    set(value) { put({ what: 'returnValue', value: String(value), who: who() }); desc.set.call(this, value); },
  });
  addEventListener('beforeunload', () => {
    const raw = document.documentElement.getAttribute('data-litecore');
    const guards = raw ? (JSON.parse(raw).guards || []) : null;
    const pending = document.querySelector('#s-pending');
    // A handler PROPERTY asks by its return value, with neither preventDefault
    // nor the returnValue setter: record that one exists at all.
    put({ what: 'fired', lastGuard: guards && guards.length ? guards[guards.length - 1] : null,
          guards: guards ? guards.length : null, pending: pending ? pending.textContent : null,
          handlerProperty: typeof window.onbeforeunload === 'function' });
  });
  put({ what: 'installed' });
  return true;
})()"""
READ_RECORD = "(() => { const k = 'm3honesty:' + ARG_NONCE; const v = localStorage.getItem(k); localStorage.removeItem(k); return v; })()"
# U0's own question: a function whose source names itself, so the recorder can
# tell it from the page's and the host's.
RUNNER_ASKS = ("(() => { addEventListener('beforeunload', new Function('event',"
               " \"event.preventDefault(); event.returnValue = 'm3honesty-runner';\\n//# sourceURL=m3honesty-runner.js\"));"
               " return true; })()")
DATA = "(() => document.documentElement.getAttribute('data-litecore'))()"
PATH = "(() => location.pathname + location.search)()"
LATENCY = "(() => document.querySelector('#s-latency').textContent)()"
SINK_TOP = "(() => Math.round(document.querySelector('#sink').getBoundingClientRect().top * 100) / 100)()"
CONTROLS = """(() => [...document.querySelectorAll('#toolbar button')].map((b, i) => ({
  i, action: b.dataset.action || null, id: b.id || null, disabled: b.disabled, hidden: b.hidden,
  mutates: b.dataset.mutates ?? null, text: b.textContent.trim() })))()"""
TEXT_FIELD = "(() => ({ disabled: document.querySelector('#text').disabled, sinkReadOnly: document.querySelector('#sink').readOnly }))()"
# Counts the page's own save completions: `run("儲存")` writes 「儲存 N ms」 once per save.
COUNT_SAVES = """(() => { window.__m3saves = 0; const node = document.querySelector('#s-latency');
  new MutationObserver(() => { if (/^儲存 \\d+ ms$/.test(node.textContent)) window.__m3saves += 1; })
    .observe(node, { childList: true, characterData: true, subtree: true }); return true; })()"""
HELD = """(() => { const sink = document.querySelector('#sink'); sink.focus(); window.__m3held = [];
  for (let i = 0; i < 30; i++) setTimeout(() => window.__m3held.push(sink.dispatchEvent(new KeyboardEvent('keydown', {
    key: 's', code: 'KeyS', ctrlKey: true, repeat: i > 0, bubbles: true, cancelable: true })) === false), i * 33);
  return true; })()"""
# Two evaluates, so a task passes between the presses: the first press's save
# takes the session's bytes in a microtask, and a marker inserted in the SAME
# task would be in both saves -- then "the last bytes carry the marker" holds
# even if the second save re-sent the first's bytes (review 2026-09-29,
# implementation).  Save #1 is read back from the file's versions and must NOT
# carry the marker.
SEP_KEY = """sink.dispatchEvent(new KeyboardEvent('keydown', { key: 's', code: 'KeyS', ctrlKey: true,
    bubbles: true, cancelable: true })) === false"""
SEP_FIRST = ("(() => { const sink = document.querySelector('#sink'); window.__m3sep = performance.now();"
             " return " + SEP_KEY + "; })()")
SEP_SECOND = ("(() => { const sink = document.querySelector('#sink');"
              " document.querySelector('#text').value = ARG_MARKER;"
              " document.querySelector('#toolbar button[data-action=\"insert-text\"]').click();"
              " const second = " + SEP_KEY + ";"
              " return { second, spanMs: Math.round(performance.now() - window.__m3sep) }; })()")
# The second press lands while the first save is under way: when the page
# shows 「儲存 N ms」 (the session's bytes taken) and before the host has
# answered the PUT.  Pressed in the same task as the first (as before) it was
# true by construction that it came before the answer, and a debounce keyed on
# "a save in progress" passed (review 2026-09-29, implementation).
PAIR_AT = ("(() => { const node = document.querySelector('#s-latency'); window.__m3pair = null;"
           " const v = () => JSON.parse(document.documentElement.getAttribute('data-litecore'));"
           " new MutationObserver((records, observer) => {"
           "  if (!/^儲存 \\d+ ms$/.test(node.textContent)) return; observer.disconnect();"
           "  const secondAt = Date.now() - v().started; const second = " + CTRL_S.strip() + ";"
           "  window.__m3pair = { secondAt, second, savesAtSecond: v().saves.length }; })"
           " .observe(node, { childList: true, characterData: true, subtree: true });"
           " document.querySelector('#toolbar button[data-action=\"save\"]').click(); return true; })()")
SAVES = """(() => { const v = document.documentElement.getAttribute('data-litecore');
  const s = v && JSON.parse(v).saves; return s ? [s.length, s.every(x => x.settled === true)] : [0, true]; })()"""
ARROW_DOWN = """(() => document.querySelector('#sink').dispatchEvent(new KeyboardEvent('keydown', {
  key: 'ArrowDown', code: 'ArrowDown', bubbles: true, cancelable: true })) === false)()"""
KEY = """(() => { const sink = document.querySelector('#sink'); sink.focus();
  return sink.dispatchEvent(new KeyboardEvent('keydown', ARG_INIT)) === false; })()"""
# run_e2_c_product_path.DRAG, inlined (that module is 7000 lines to import for one string).
# Fractions of #paper, dispatched on #canvas: SPEC-M3-production-ui §17.11.
DRAG = """(() => {
const canvas = document.querySelector('#canvas');
const box = document.querySelector('#paper').getBoundingClientRect();
const at = (fx, fy) => ({ x: box.left + box.width * fx, y: box.top + box.height * fy });
const a = at(ARG_X1, ARG_Y1);
const b = at(ARG_X2, ARG_Y2);
const send = (type, point, buttons) => canvas.dispatchEvent(new PointerEvent(type, {
  clientX: point.x, clientY: point.y, button: 0, buttons, pointerId: 1, bubbles: true }));
send('pointerdown', a, 1);
send('pointermove', { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, 1);
send('pointermove', b, 1);
send('pointerup', b, 0);
return true;
})()"""
# The document's text lines, from the canvas ink, read right after the open
# (before any caret is drawn): bands of rows with more than two dark opaque
# pixels, at least five rows tall (the page's one-row edges drop out).  V4 and
# the census aim at the FIRST line.  y 0.28 is below this fixture's text, so a
# click there puts the caret on the LAST line, and ArrowDown on the last line is
# finding 096: the shipped v8 engine answers nothing, the action times out after
# 30 s and the session goes to recoverable-error -- both V arms of the first
# shakedown (2026-09-29T091816) died that way before the census began.
#
# SPEC-M3-production-ui §17.11: the scan is of the canvas, which on a windowed
# page is rows [top, top + rows) of the document, so the bands are put back into
# the document's rows (`off` = winTop) and `mid` is a fraction of the document
# (`H` = docRows).  On the P page off is 0 and H is h: the read is unchanged.
TEXT_LINES = """(() => {""" + DOC_WINDOW_JS + """
const c = document.querySelector('#canvas');
const read = (win) => { const w = c.width, h = c.height, off = win.top, H = win.docRows;
const d = c.getContext('2d').getImageData(0, 0, w, h).data; const rows = [];
for (let y = 0; y < h; y++) { let n = 0; for (let x = 0; x < w; x++) { const i = (y * w + x) * 4;
  if (d[i+3] > 128 && d[i] < 100 && d[i+1] < 100 && d[i+2] < 100) n++; } rows.push(n); }
const bands = []; let start = -1;
for (let y = 0; y <= h; y++) { const on = y < h && rows[y] > 2; if (on && start < 0) start = y;
  if (!on && start >= 0) { if (y - start >= 5) bands.push({ a: start + off, b: y - 1 + off, mid: +(((start + off + y - 1 + off) / 2) / H).toFixed(4) });
    start = -1; } }
return { h: H, w, bands }; };
const win = __docWindow();
if (__docRowsHeld(win, win.top, win.top + win.rows, false)) return read(win);
return __docRowsCover(win.top, win.top + win.rows).then(({ w, waited }) => Object.assign(read(w), { windowWait: waited }));
})()"""


def first_line(session, record: dict[str, Any]) -> str:
    record["lines"] = evaluate(session, TEXT_LINES)
    bands = (record["lines"] or {}).get("bands") or []
    if len(bands) < 2:
        raise RuntimeError(f"fewer than two text lines on the canvas: {record['lines']}")
    record["lineY"] = str(bands[0]["mid"])
    return record["lineY"]


# What a textarea's own editing sends first: the page and the input adapter act on beforeinput.
BEFOREINPUT = """(() => { const sink = document.querySelector('#sink'); sink.focus();
  return sink.dispatchEvent(new InputEvent('beforeinput', { inputType: ARG_TYPE, bubbles: true,
  cancelable: true })) === false; })()"""
PASTE = """(() => { const sink = document.querySelector('#sink'); sink.focus(); const data = new DataTransfer();
  data.setData('text/plain', 'P'); return sink.dispatchEvent(new ClipboardEvent('paste',
  { clipboardData: data, bubbles: true, cancelable: true })) === false; })()"""
# U-window: leave in the gap between the session's save and the host's.
WINDOW_TRAP = """(() => { const node = document.querySelector('#s-latency');
  const count = () => JSON.parse(document.documentElement.getAttribute('data-litecore')).saves.length;
  const baseline = count(); window.__m3trap = null;
  new MutationObserver((records, observer) => {
    if (/^儲存 \\d+ ms$/.test(node.textContent) && count() === baseline) {
      observer.disconnect(); window.__m3trap = { at: performance.now(), saves: count() };
      location.href = ARG_URL;
    }
  }).observe(node, { childList: true, characterData: true, subtree: true });
  document.querySelector('#toolbar button[data-action="save"]').click(); return baseline; })()"""


# ------------------------------------------------------------------ leaving

def chrome_wait_dialog(session: LockChrome, wait: float) -> dict[str, Any] | None:
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        try:
            message = json.loads(session.websocket.recv(timeout=max(0.1, deadline - time.monotonic())))
        except TimeoutError:
            return None
        if message.get("method") == "Page.javascriptDialogOpening":
            return message["params"]
        if message.get("method") in session.KEEP:
            session.events.append(message)
    return None


def leave(session, kind: str, expression: str, record: dict[str, Any], key: str, nonce: str,
          wait: float = 5.0) -> dict[str, Any]:
    """Run `expression` (which navigates), see what happened, read and clear the
    recorder.  Chrome: a dialog is dismissed (the user stays)."""
    result: dict[str, Any] = {}
    if kind == "chrome":
        session.next_id += 1
        session.websocket.send(json.dumps({"id": session.next_id, "method": "Runtime.evaluate",
                                           "params": {"expression": expression}}))
        result["dialog"] = chrome_wait_dialog(session, wait)
        if result["dialog"]:
            session.call("Page.handleJavaScriptDialog", {"accept": False})
        time.sleep(1.5)
    else:
        try:
            evaluate(session, expression)
        except Exception as error:  # noqa: BLE001 -- a navigation may cut the script's answer off
            result["evaluateError"] = f"{type(error).__name__}: {error}"
        time.sleep(4)
    result["pathAfter"] = wait_until(session, PATH, 20)
    raw = wait_until(session, READ_RECORD.replace("ARG_NONCE", json.dumps(nonce)), 10)
    result["record"] = json.loads(raw) if isinstance(raw, str) else {"missing": raw}
    record.setdefault("leaves", {})[key] = result
    return result


def install_recorder(session, record: dict[str, Any]) -> str:
    nonce = secrets.token_hex(8)
    record["nonce"] = nonce
    record["recorder"] = evaluate(session, RECORDER.replace("ARG_NONCE", json.dumps(nonce)))
    return nonce


def activate(session, kind: str, record: dict[str, Any]) -> None:
    # A trusted click on something inert, for user activation.  It was `#text`
    # until host 0.2.6 hid that field (SPEC-M3-production-ui §3.4): a hidden
    # element's box is 0x0, so the click landed at (0,0), on Nextcloud's header.
    # The state pill is visible on every host and has no handler.
    if kind == "chrome":
        record.setdefault("activations", []).append(session.real_click("#state-pill"))


def settled(session, count: int, quiet: float = 1.0, timeout: float = 180) -> Any:
    deadline, last, since = time.monotonic() + timeout, None, time.monotonic()
    while time.monotonic() < deadline:
        seen = evaluate(session, SAVES)
        if seen != last:
            last, since = seen, time.monotonic()
        elif isinstance(seen, list) and seen[0] >= count and seen[1] and time.monotonic() - since >= quiet:
            return seen
        time.sleep(0.25)
    return {"timedOut": True, "last": last}


def quiet_state(session, limit: float = 30) -> dict[str, Any]:
    """Until the page's queue is empty (pending 0) for half a second."""
    deadline, since = time.monotonic() + limit, None
    state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state = product_state(session)
        if str(state.get("pending")) in ("0", "—"):
            since = since or time.monotonic()
            if time.monotonic() - since >= 0.5:
                return state
        else:
            since = None
        time.sleep(0.15)
    return {**state, "timedOut": True}


# ------------------------------------------------------------------ arms

def new_session(kind: str, scratch: Path, downloads: Path | None = None):
    if kind == "chrome":
        session = LockChrome("cold")
        if downloads is not None:
            chrome_download_dir(session, downloads)
        return session
    prefs = {}
    if downloads is not None:
        prefs = {"browser.download.folderList": 2, "browser.download.dir": str(downloads),
                 "browser.download.useDownloadDir": True,
                 "browser.download.always_ask_before_handling_new_types": False,
                 "browser.helperApps.neverAsk.saveToDisk": ODT}
    return FirefoxSession("cold", profile_dir=firefox_profile(scratch / f"ff-{time.monotonic_ns()}"), extra_prefs=prefs)


def run_host_arm(arm: str, kind: str, server: Server, scratch: Path) -> dict[str, Any]:
    """U0-U5, U7, U-window and the K cells: admin opens their own file."""
    base = server.instance.base
    files = base + "/apps/files/"
    record: dict[str, Any] = {"arm": arm, "browser": kind, "startedAt": utc_now()}
    record["clearedLocks"] = server.clear_locks()
    record["reset"] = {"upload": server.upload(server.admin, NAME), "fileId": server.fileid(server.admin, NAME)}
    server.copies(server.admin, "", NAME[:-4], remove=True)
    record["serverBefore"] = server.content(server.admin, NAME)
    session = new_session(kind, scratch)
    record["version"] = getattr(session, "version", None)
    try:
        record["login"] = login(session, base, "admin", server.instance.password)
        open_from_files(session, base, "", NAME, record)
        record["opened"] = record.get("host")
        record["afterOpen"] = server.props(server.admin, NAME)
        nonce = install_recorder(session, record)
        go = f"(() => {{ location.href = {json.dumps(files)}; return true; }})()"
        if arm == "U0":
            record["runnerAsks"] = evaluate(session, RUNNER_ASKS)
            activate(session, kind, record)
            leave(session, kind, go, record, "leave", nonce)
        elif arm == "U1":
            edit(session, record)
            activate(session, kind, record)
            leave(session, kind, go, record, "leave1", nonce)
            if kind == "chrome":
                record["hostAfterLeave1"] = host_record(session)
                record["serverAfterLeave1"] = server.props(server.admin, NAME)
                activate(session, kind, record)
                leave(session, kind, go, record, "leave2", nonce)
                record["hostAfterLeave2"] = host_record(session)
                record["serverAfterLeave2"] = server.props(server.admin, NAME)
                save(session, record, 1)
                record["host"] = host_record(session)
                record["serverAfterSave"] = server.content(server.admin, NAME)
                record["copiesAfterSave"] = server.copies(server.admin, "", NAME[:-4], remove=False)
                activate(session, kind, record)
                leave(session, kind, go, record, "leave3", nonce)
        elif arm == "Uwin":
            edit(session, record)
            activate(session, kind, record)
            expression = WINDOW_TRAP.replace("ARG_URL", json.dumps(files))
            leave(session, kind, expression, record, "leave", nonce, wait=20)
            if kind == "chrome":
                record["trap"] = evaluate(session, "(() => window.__m3trap)()")
                record["settledAfter"] = settled(session, 1)
                record["host"] = host_record(session)
                record["serverAfter"] = server.content(server.admin, NAME)
        elif arm in ("U2", "U3"):
            edit(session, record)
            save(session, record, 1)
            if arm == "U3":
                insert_marker(session, record)
            record["host"] = host_record(session)
            activate(session, kind, record)
            leave(session, kind, go, record, "leave", nonce)
        elif arm == "U4":
            fileid = record["reset"]["fileId"]
            edit(session, record)
            record["refusedUnlock"] = server.other.call("refused unlock", "DELETE",
                                                        f"/ocs/v2.php/apps/files_lock/lock/{fileid}",
                                                        form={"lockType": 0})["status"]
            record["afterRefused"] = server.props(server.admin, NAME)
            save(session, record, 1)
            record["host"] = host_record(session)
            activate(session, kind, record)
            leave(session, kind, go, record, "leave", nonce)
        elif arm == "U5":
            activate(session, kind, record)
            leave(session, kind, go, record, "leave", nonce)
        elif arm == "U7":
            activate(session, kind, record)
            expression = ("(() => { " + PRESS.replace("ARG_ACTION", "set-paragraph-heading").strip()
                          + "; location.href = " + json.dumps(files) + "; return true; })()")
            leave(session, kind, expression, record, "leave", nonce)
        elif arm == "Kheld":
            edit(session, record)
            record["counter"] = evaluate(session, COUNT_SAVES)
            before = evaluate(session, SAVES)[0]
            record["held"] = evaluate(session, HELD)
            time.sleep(1.2)
            record["settled"] = settled(session, before + 1, quiet=5.0)
            record["prevented"] = evaluate(session, "(() => window.__m3held)()")
            record["pageSaves"] = evaluate(session, "(() => window.__m3saves)()")
            record["savesBefore"] = before
            record["host"] = host_record(session)
        elif arm == "Ksep":
            # Save #1 is a version named after its mtime, so it is at or after this.
            record["versionsSince"] = since = int(time.time()) - 2
            edit(session, record)
            before = evaluate(session, SAVES)[0]
            first = evaluate(session, SEP_FIRST)
            record["separate"] = {"first": first, **(evaluate(session, SEP_SECOND.replace("ARG_MARKER", json.dumps(MARKER))) or {})}
            record["settled"] = settled(session, before + 2, quiet=5.0)
            record["savesBefore"] = before
            record["host"] = host_record(session)
            record["serverAfter"] = server_file(server.instance, NAME)
            record["versions"] = versions(server, NAME, since)
        elif arm == "Ktwo":
            edit(session, record)
            before = evaluate(session, SAVES)[0]
            record["pairArmed"] = evaluate(session, PAIR_AT)
            record["settled"] = settled(session, before + 2, quiet=3.0)
            record["pair"] = evaluate(session, "(() => window.__m3pair)()")
            record["savesBefore"] = before
            record["host"] = host_record(session)
        record["serverAfterArm"] = server.content(server.admin, NAME)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        if kind == "chrome":
            # A CDP socket that died fails this run, not the whole report (spec §7.12).
            try:
                record["davRequests"] = wire(session.drain())
            except Exception:  # noqa: BLE001
                record.setdefault("fatal", traceback.format_exc())
        session.close()
        record["copiesAfter"] = server.copies(server.admin, "", NAME[:-4], remove=True)
        record["completedAt"] = utc_now()
    return record


def versions(server: Server, name: str, since: int | None = None) -> list[dict[str, Any]]:
    """The versions Nextcloud keeps of the file, with their bytes' hash and
    paragraph texts (K-sep reads save #1 back from here). Only those named (mtime
    seconds) at or after `since`: the file keeps every run's versions (1,645 on
    2026-09-29), and reading all of them left the CDP socket unread for minutes
    until its keepalive dropped it (spec §7.12). Too late a `since` can only hide
    save #1, which K-sep scores as red."""
    client = server.admin
    fileid = server.fileid(client, name)

    def raw(method: str, path: str, body: bytes | None = None, headers: dict[str, str] | None = None):
        request = urllib.request.Request(client.base + path, data=body, method=method, headers=headers or {})
        request.add_header("Authorization", client.auth)
        try:
            with urllib.request.urlopen(request, context=client.tls, timeout=60) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    collection = f"/remote.php/dav/versions/{client.user}/versions/{fileid}"
    status, data = raw("PROPFIND", collection, b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop>'
                       b"<d:getlastmodified/></d:prop></d:propfind>", {"Depth": "1", "Content-Type": "application/xml"})
    found, skipped = [], 0
    for href in re.findall(r"<d:href>([^<]+)</d:href>", data.decode("utf-8", "replace")):
        if urllib.parse.unquote(href).rstrip("/").endswith(f"/versions/{fileid}"):
            continue
        stamp = href.rstrip("/").rsplit("/", 1)[-1]
        if since is not None and stamp.isdigit() and int(stamp) < since:
            skipped += 1
            continue
        got, body = raw("GET", href)
        entry = {"href": href.rsplit("/", 1)[-1], "status": got}
        if got == 200:
            entry["sha256"] = hashlib.sha256(body).hexdigest()
            try:
                entry["texts"] = paragraph_texts(body)
            except Exception as error:  # noqa: BLE001 -- recorded
                entry["texts"] = f"unreadable: {error}"
        found.append(entry)
    return [{"collection": status, "since": since, "olderSkipped": skipped}] + found


def run_download_arm(arm: str, kind: str, scratch: Path) -> dict[str, Any]:
    """U6: the page with no host, from dist/, a document from its own samples."""
    record: dict[str, Any] = {"arm": arm, "browser": kind, "startedAt": utc_now()}
    port = free_port()
    server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
                               "--root", str(DIST)], cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    downloads = scratch / f"downloads-{arm}-{kind}-{time.monotonic_ns()}"
    downloads.mkdir()
    session = None
    try:
        deadline = time.monotonic() + 20
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/e2-editor.html", timeout=2) as answer:
                    if answer.status == 200:
                        break
            except Exception:  # noqa: BLE001 -- not up yet
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.2)
        session = new_session(kind, scratch, downloads)
        record["version"] = getattr(session, "version", None)
        navigate(session, f"http://127.0.0.1:{port}/e2-editor.html", timeout=120)
        record["ready"] = state_until(session, lambda s: s.get("state") == "ready" and s.get("doc"), 180)
        nonce = install_recorder(session, record)
        edit(session, record)
        if arm == "U6b":
            evaluate(session, PRESS.replace("ARG_ACTION", "save"))
            record["saved"] = state_until(session, lambda s: (s.get("latency") or "").startswith("儲存"), 120)
            record["download"] = downloaded(downloads)
        activate(session, kind, record)
        away = f"http://127.0.0.1:{port}/m3-honesty-left"
        leave(session, kind, f"(() => {{ location.href = {json.dumps(away)}; return true; }})()", record, "leave", nonce)
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
    finally:
        if session is not None:
            session.close()
        server.terminate()
        record["completedAt"] = utc_now()
    return record


def census_step(session, kind: str, name: str, act) -> dict[str, Any]:
    before = product_state(session)
    evaluate(session, "(() => { document.querySelector('#toast').textContent = ''; return true; })()")
    try:
        acted = act()
    except Exception as error:  # noqa: BLE001 -- recorded
        acted = f"{type(error).__name__}: {error}"
    time.sleep(0.4)
    after = quiet_state(session)
    return {"item": name, "acted": acted, "revisionBefore": before.get("revision"),
            "revisionAfter": after.get("revision"), "pending": after.get("pending"),
            "state": after.get("state"), "latency": after.get("latency"), "toast": after.get("toast")}


def census(session, kind: str, record: dict[str, Any], writable: bool) -> list[dict[str, Any]]:
    """Every #toolbar button, then the keyboard half.  Read-only: each button's
    `disabled` is removed first (the UI layer failing), so the gate is what is
    tested.  Writable: preconditions are laid out so each change can happen."""
    rows = []
    controls = evaluate(session, CONTROLS)
    record["controlsAtCensus"] = controls

    def click(i: int):
        return lambda: evaluate(session, f"(() => {{ const b = document.querySelectorAll('#toolbar button')[{i}];"
                                         " b.disabled = false; b.hidden = false; b.click(); return true; })()")

    line = record["lineY"]

    def point():
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", line))
        state_until(session, lambda s: "定位游標" in (s.get("latency") or ""), 30)

    def select():
        evaluate(session, DRAG.replace("ARG_X1", "0.2").replace("ARG_Y1", line)
                 .replace("ARG_X2", "0.5").replace("ARG_Y2", line))
        time.sleep(1.0)
        quiet_state(session)

    by_action = {c["action"] or c["id"]: c["i"] for c in controls}
    order = ["insert-text", "delete-backward", "delete-forward", "insert-paragraph-break", "insert-line-break",
             "set-paragraph-heading", "set-paragraph-body", "set-list-unordered", "set-list-ordered", "set-list-none",
             "set-bold", "set-italic", "set-underline", "set-strikethrough", "clear-format", "undo", "redo",
             "move-character-left", "move-character-right", "save", "open-file"]
    # Every control the page has, in this order, then any the order does not name (none expected).
    names = [n for n in order if n in by_action and n != "open-file"] + [
        n for n in by_action if n not in order]
    record["censusOrder"] = names
    point()
    for name in names:
        if name == "insert-text":
            evaluate(session, "(() => { document.querySelector('#text').disabled = false;"
                              " document.querySelector('#text').value = 'ABC'; return true; })()")
        if writable and name in ("set-bold", "set-italic", "set-underline", "set-strikethrough", "clear-format"):
            select()
        if writable and name in ("delete-backward", "insert-paragraph-break", "set-paragraph-heading"):
            point()
        if writable and name == "delete-forward":
            # A character to delete in the same paragraph: at a paragraph's end a
            # forward delete is a structure boundary, refused by contract with
            # the session sent to restart-required (SPEC-E1-C 4.x, finding 016) --
            # measured in the second shakedown, 2026-09-29T093035.
            click(by_action["move-character-left"])()
            quiet_state(session)
        if not writable and name == "save":
            record["putsBeforeSaveClick"] = len((host_record(session).get("saves") or []))
        rows.append(census_step(session, kind, name, click(by_action[name])))
        if name == "save":
            time.sleep(2.0)
    # Not clicked: it opens the file picker, which is a modal the driver cannot
    # dismiss; it is disabled with a host anyway, and exempt by name (§7.3).
    point()
    for label, input_type in (("Enter", "insertLineBreak"), ("Backspace", "deleteContentBackward")):
        rows.append({**census_step(session, kind, label, lambda t=input_type: evaluate(
            session, BEFOREINPUT.replace("ARG_TYPE", json.dumps(t)))), "half": "keyboard"})
    keyboard = [("Ctrl+Z", {"key": "z", "code": "KeyZ", "ctrlKey": True}),
                ("Ctrl+Y", {"key": "y", "code": "KeyY", "ctrlKey": True})]
    for label, init in keyboard:
        init = {**init, "bubbles": True, "cancelable": True}
        rows.append({**census_step(session, kind, label,
                                   lambda init=init: evaluate(session, KEY.replace("ARG_INIT", json.dumps(init)))),
                     "half": "keyboard"})
    if writable:
        select()
    init = {"key": "b", "code": "KeyB", "ctrlKey": True, "bubbles": True, "cancelable": True}
    rows.append({**census_step(session, kind, "Ctrl+B",
                               lambda: evaluate(session, KEY.replace("ARG_INIT", json.dumps(init)))), "half": "keyboard"})
    rows.append({**census_step(session, kind, "paste", lambda: evaluate(session, PASTE)), "half": "keyboard"})
    return rows


def run_view_arm(arm: str, kind: str, server: Server, scratch: Path) -> dict[str, Any]:
    """Vro: lcprobe opens a file shared read-only.  Vrw: the same user, a file
    shared writable -- the census's positive control."""
    base = server.instance.base
    writable = arm == "Vrw"
    target = server.targets["rw" if writable else "ro"]
    admin_path = NAME if writable else RO_NAME
    folder, name = (target.rsplit("/", 1) if "/" in target else ("", target))
    record: dict[str, Any] = {"arm": arm, "browser": kind, "startedAt": utc_now(),
                              "file": {"user": OTHER, "target": target, "adminPath": admin_path}}
    record["clearedLocks"] = server.clear_locks()
    record["reset"] = {"upload": server.upload(server.admin, admin_path),
                       "fileId": server.fileid(server.admin, admin_path)}
    record["serverBefore"] = server.content(server.admin, admin_path)
    session = new_session(kind, scratch)
    record["version"] = getattr(session, "version", None)
    try:
        record["login"] = login(session, base, OTHER, server.other_password)
        open_from_files(session, base, folder, name, record)
        record["opened"] = record.get("host")
        record["afterOpen"] = server.props(server.admin, admin_path)
        nonce = install_recorder(session, record)
        record["textField"] = evaluate(session, TEXT_FIELD)
        # V7 and V4: a caret placed (a state update), then the controls; then a line down.
        # On the first line, not the last: see TEXT_LINES.
        line = first_line(session, record)
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", line))
        record["placed"] = state_until(session, lambda s: "定位游標" in (s.get("latency") or ""), 30)
        record["controls"] = evaluate(session, CONTROLS)
        record["sinkTopBefore"] = evaluate(session, SINK_TOP)
        record["arrowDown"] = evaluate(session, ARROW_DOWN)
        record["movedDown"] = state_until(session, lambda s: "下移一行" in (s.get("latency") or ""), 30)
        record["sinkTopAfter"] = evaluate(session, SINK_TOP)
        if not writable:
            # V5: Ctrl+S on a read-only document.
            record["ctrlS"] = evaluate(session, CTRL_S)
            time.sleep(3)
            record["savesAfterCtrlS"] = len(host_record(session).get("saves") or [])
        record["census"] = census(session, kind, record, writable)
        record["host"] = host_record(session)
        record["serverAfterCensus"] = server.content(server.admin, admin_path)
        if not writable:
            activate(session, kind, record)
            leave(session, kind, f"(() => {{ location.href = {json.dumps(base + '/apps/files/')}; return true; }})()",
                  record, "leave", nonce)
            record["serverAfter"] = server.content(server.admin, admin_path)
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
    finally:
        if kind == "chrome":
            record["davRequests"] = wire(session.drain())
        session.close()
        record["copiesAfter"] = server.copies(server.other, "", name[:-4], remove=True)
        record["completedAt"] = utc_now()
    return record


def run_arm(arm: str, kind: str, server: Server, scratch: Path) -> dict[str, Any]:
    if arm in ("U6a", "U6b"):
        return run_download_arm(arm, kind, scratch)
    if arm in ("Vro", "Vrw"):
        return run_view_arm(arm, kind, server, scratch)
    return run_host_arm(arm, kind, server, scratch)


# ------------------------------------------------------------------ scoring

def asks(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in entries if e.get("what") == "preventDefault"
            or (e.get("what") == "returnValue" and e.get("value"))]


def left_record(run: dict[str, Any], key: str = "leave") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result = (run.get("leaves") or {}).get(key) or {}
    entries = result.get("record")
    return (entries if isinstance(entries, list) else []), result


def asked_by(run: dict[str, Any], key: str, who: str, reason: str | None = None,
             chrome_dialog: bool = True) -> list[str]:
    """The cell asked, and the one who asked is `who` (and nobody else)."""
    entries, result = left_record(run, key)
    bad = []
    if not any(e.get("what") == "fired" for e in entries):
        bad.append(f"{key}: no `fired` record ({result.get('record')!r:.120})")
    askers = sorted({e.get("who") for e in asks(entries)})
    if askers != [who]:
        bad.append(f"{key}: askers {askers}, wanted [{who!r}]")
    if any(e.get("handlerProperty") for e in entries if e.get("what") == "fired"):
        bad.append(f"{key}: an onbeforeunload handler property is set")
    if reason is not None:
        fired = [e for e in entries if e.get("what") == "fired"]
        reasons = ((fired[-1].get("lastGuard") or {}).get("reasons") or []) if fired else []
        if reason not in reasons:
            bad.append(f"{key}: host guard reasons {reasons}, wanted {reason!r}")
    if run["browser"] == "chrome" and chrome_dialog and not result.get("dialog"):
        bad.append(f"{key}: no dialog in Chrome")
    return bad


def not_asked(run: dict[str, Any], key: str = "leave") -> list[str]:
    entries, result = left_record(run, key)
    bad = []
    if not any(e.get("what") == "fired" for e in entries):
        bad.append(f"{key}: no `fired` record ({result.get('record')!r:.120})")
    if asks(entries):
        bad.append(f"{key}: asked by {sorted({e.get('who') for e in asks(entries)})}")
    if any(e.get("handlerProperty") for e in entries if e.get("what") == "fired"):
        bad.append(f"{key}: an onbeforeunload handler property is set")
    if run["browser"] == "chrome" and result.get("dialog"):
        bad.append(f"{key}: a dialog in Chrome")
    return bad


def opened_ready(run: dict[str, Any]) -> list[str]:
    host = run.get("opened") or {}
    steps = host.get("steps") or []
    opened = next((s.get("state") or {} for s in steps if s.get("step") == "opened"), {})
    return [] if opened.get("state") == "ready" else [f"not opened: {opened}"]


def new_saves(run: dict[str, Any]) -> list[dict[str, Any]]:
    saves = (run.get("host") or {}).get("saves") or []
    return saves[run.get("savesBefore", 0):]


def first_attempt(save: dict[str, Any]) -> dict[str, Any]:
    return (save.get("attempts") or [{}])[0]


EDITS = ("U1", "Uwin", "U2", "U3", "U4", "U6a", "U6b", "Kheld", "Ksep", "Ktwo")
LATENCY_OK = {"placed": r"^定位游標 \d+ ms$", "movedDown": r"^下移一行 \d+ ms$"}


def score_arm(run: dict[str, Any]) -> list[str]:
    import re
    arm, kind = run["arm"], run["browser"]
    if run.get("fatal"):
        return [f"fatal: {run['fatal'].strip().splitlines()[-1]}"]
    bad: list[str] = []
    if arm not in ("U6a", "U6b"):
        bad += opened_ready(run)
    elif (run.get("ready") or {}).get("state") != "ready":
        bad.append(f"download-mode page not ready: {run.get('ready')}")
    host = run.get("host") or {}
    if arm in EDITS:
        bad += edited(run)
    if arm == "U0":
        entries, result = left_record(run)
        if not any(e.get("what") == "fired" for e in entries):
            bad.append("no `fired` record")
        askers = sorted({e.get("who") for e in asks(entries)})
        if askers != ["runner"]:
            bad.append(f"askers {askers}, wanted ['runner'] only")
        if kind == "chrome" and not result.get("dialog"):
            bad.append("no dialog in Chrome")
    elif arm == "U1":
        bad += asked_by(run, "leave1", "host", "page")
        if kind == "chrome":
            for n in ("1", "2"):
                after_host = run.get(f"hostAfterLeave{n}") or {}
                after_server = run.get(f"serverAfterLeave{n}") or {}
                if (after_host.get("lock") or {}).get("state") != "held":
                    bad.append(f"after leave{n}: host lock {(after_host.get('lock') or {}).get('state')}")
                if after_server.get("lock") != "1" or after_server.get("token") != (run.get("afterOpen") or {}).get("token"):
                    bad.append(f"after leave{n}: server lock {after_server.get('lock')!r} token changed")
            bad += asked_by(run, "leave2", "host", "page")
            saves = host.get("saves") or []
            attempt = first_attempt(saves[0]) if saves else {}
            if len(saves) != 1 or attempt.get("status") != 204 or not attempt.get("withToken"):
                bad.append(f"save after staying: {[(first_attempt(x).get('status'), first_attempt(x).get('withToken')) for x in saves]}")
            elif (run.get("serverAfterSave") or {}).get("sha256") != saves[0].get("sha256"):
                bad.append("the save did not land on the original")
            if run.get("copiesAfterSave"):
                bad.append(f"copies after the save: {run['copiesAfterSave']}")
            bad += not_asked(run, "leave3")
        else:
            if "/apps/files" not in str((left_record(run, "leave1")[1]).get("pathAfter")):
                bad.append(f"leave1: still at {left_record(run, 'leave1')[1].get('pathAfter')!r} (Firefox accepts the prompt)")
            if (run.get("serverAfterArm") or {}).get("sha256") != (run.get("serverBefore") or {}).get("sha256"):
                bad.append("server file changed")
    elif arm == "Uwin":
        entries, result = left_record(run)
        bad += asked_by(run, "leave", "host", "page")
        fired = [e for e in entries if e.get("what") == "fired"]
        reasons = ((fired[-1].get("lastGuard") or {}).get("reasons") or []) if fired else []
        if "inFlight" in reasons:
            bad.append(f"left while the host's save was in flight {reasons}: not the window")
        if kind == "chrome":
            if not run.get("trap"):
                bad.append("the trap never fired")
            saves = host.get("saves") or []
            if len(saves) != 1 or first_attempt(saves[0]).get("status") != 204:
                bad.append(f"the save did not finish after staying: {[first_attempt(x).get('status') for x in saves]}")
    elif arm == "U2":
        bad += not_asked(run)
        saves = host.get("saves") or []
        if len(saves) != 1 or first_attempt(saves[0]).get("status") != 204:
            bad.append(f"save {[first_attempt(x).get('status') for x in saves]}")
        elif (run.get("serverAfterArm") or {}).get("sha256") != saves[0].get("sha256"):
            bad.append("server bytes are not the save's")
    elif arm == "U3":
        bad += asked_by(run, "leave", "host", "page")
    elif arm == "U4":
        saves = host.get("saves") or []
        copy_ = (saves[0].get("conflictCopy") or {}) if saves else {}
        if run.get("refusedUnlock") != 423:
            bad.append(f"refused unlock {run.get('refusedUnlock')}")
        if len(saves) != 1 or first_attempt(saves[0]).get("status") != 412 or not copy_.get("name") or copy_.get("failed"):
            bad.append(f"save {[first_attempt(x).get('status') for x in saves]} copy {copy_}")
        copies = run.get("copiesAfter") or []
        if len(copies) != 1 or (saves and copies[0].get("sha256") != saves[0].get("sha256")):
            bad.append(f"copies {copies}")
        bad += not_asked(run)
    elif arm == "U5":
        bad += not_asked(run)
    elif arm == "U7":
        bad += asked_by(run, "leave", "host", "page")
        # The cell's claim is WHY it asked: the edit still in the engine, not
        # one that had already landed (that is U1/U3).  The page's own pill,
        # read by the recorder at beforeunload.
        entries, _ = left_record(run)
        fired = [e for e in entries if e.get("what") == "fired"]
        pending = str((fired[-1].get("pending") if fired else None) or "")
        if not (pending.isdigit() and int(pending) > 0):
            bad.append(f"leave: pending {pending!r} at beforeunload, wanted > 0")
    elif arm == "U6a":
        bad += asked_by(run, "leave", "page")
    elif arm == "U6b":
        if (run.get("download") or {}).get("none"):
            bad.append(f"no download {run.get('download')}")
        bad += not_asked(run)
    elif arm == "Kheld":
        prevented = run.get("prevented") or []
        if len(prevented) != 30 or not all(prevented):
            bad.append(f"keydowns prevented {sum(bool(x) for x in prevented)}/{len(prevented)}")
        saves = new_saves(run)
        if len(saves) != 1 or first_attempt(saves[0]).get("status") != 204:
            bad.append(f"host saves {[first_attempt(x).get('status') for x in saves]}")
        if run.get("pageSaves") != 1:
            bad.append(f"page-level saves {run.get('pageSaves')}")
        if isinstance(run.get("settled"), dict):
            bad.append(f"never settled {run['settled']}")
    elif arm == "Ksep":
        sep = run.get("separate") or {}
        if not (sep.get("first") and sep.get("second")) or not (sep.get("spanMs", 999) < 300):
            bad.append(f"presses {sep}")
        saves = new_saves(run)
        if len(saves) != 2 or any(first_attempt(x).get("status") != 204 for x in saves):
            bad.append(f"host saves {[first_attempt(x).get('status') for x in saves]}")
        texts = " ".join((run.get("serverAfter") or {}).get("texts") or [])
        if MARKER not in texts:
            bad.append("the second save does not carry the marker")
        if len(saves) == 2:
            if (run.get("serverAfter") or {}).get("sha256") != saves[1].get("sha256"):
                bad.append("the server's bytes are not the second save's")
            first = [v for v in run.get("versions") or [] if v.get("sha256") and v.get("sha256") == saves[0].get("sha256")]
            if not first:
                bad.append("save #1 is not among the file's versions")
            elif MARKER in " ".join(first[0].get("texts") or []):
                bad.append("save #1 already carries the marker: the presses were not separate")
    elif arm == "Ktwo":
        pair = run.get("pair") or {}
        if pair.get("second") is not True:
            bad.append(f"the second press was never made or not prevented: {pair}")
        saves = new_saves(run)
        if len(saves) != 2 or any(first_attempt(x).get("status") != 204 for x in saves):
            bad.append(f"host saves {[first_attempt(x).get('status') for x in saves]}")
        elif not (isinstance(pair.get("secondAt"), int)
                  and pair["secondAt"] < (first_attempt(saves[0]).get("respondedAt") or -1)):
            bad.append(f"second press at {pair.get('secondAt')} not before the first save's answer "
                       f"{first_attempt(saves[0]).get('respondedAt')}")
    elif arm in ("Vro", "Vrw"):
        bad += score_view(run, re)
    return bad


def score_view(run: dict[str, Any], re) -> list[str]:
    bad: list[str] = []
    writable = run["arm"] == "Vrw"
    host = run.get("host") or {}
    for key, pattern in LATENCY_OK.items():
        if not re.match(pattern, (run.get(key) or {}).get("latency") or ""):
            bad.append(f"V4 {key}: {(run.get(key) or {}).get('latency')!r}")
    if not (isinstance(run.get("sinkTopBefore"), (int, float)) and isinstance(run.get("sinkTopAfter"), (int, float))
            and run["sinkTopAfter"] > run["sinkTopBefore"]):
        bad.append(f"V4 caret y {run.get('sinkTopBefore')} -> {run.get('sinkTopAfter')}")
    census_rows = run.get("census") or []
    buttons = [r for r in census_rows if r.get("half") != "keyboard"]
    mutates = {(c["action"] or c["id"]): c.get("mutates") for c in (run.get("controlsAtCensus") or [])}
    # The census covers every control the PAGE lists (not a list in this file),
    # except open-file (§7.3: a modal the driver cannot dismiss).  Without this
    # an empty census passes both arms.
    wanted = set(mutates) - {"open-file"}
    missing = sorted(wanted - {r.get("item") for r in buttons})
    if not wanted or missing or "insert-text" not in wanted:
        bad.append(f"V2 census: {len(wanted)} controls listed, missing {missing}")
    if writable:
        # §7.14: a button the page itself hid at census offers the user no way to it (v21's withheld
        # paste-markdown), so it is not asked to advance; the other direction below still applies to it.
        hidden = {(c["action"] or c["id"]): c.get("hidden") is True for c in (run.get("controlsAtCensus") or [])}
        for row in buttons:
            if (mutates.get(row["item"]) == "1" and row["item"] != "save" and not hidden.get(row["item"])
                    and row["revisionAfter"] == row["revisionBefore"]):
                bad.append(f"V2 control: {row['item']} did not advance ({row['latency']!r})")
            # The other direction: a control that changed the document must be
            # labelled as one, or view-only leaves it enabled and exempt here.
            if row["revisionAfter"] != row["revisionBefore"] and mutates.get(row["item"]) != "1":
                bad.append(f"V2 control: {row['item']} advanced but is labelled mutates={mutates.get(row['item'])!r}")
        return bad
    # V1
    opened = run.get("opened") or {}
    if (opened.get("lock") or {}).get("state") != "readonly" or not opened.get("handedReadOnly"):
        bad.append(f"V1 host lock {(opened.get('lock') or {}).get('state')} handedReadOnly {opened.get('handedReadOnly')}")
    if "只能檢視" not in (run.get("bar") or {}).get("notice", ""):
        bad.append(f"V1 notice {(run.get('bar') or {}).get('notice')!r}")
    after_open = run.get("afterOpen") or {}
    if after_open.get("status") != 207 or after_open.get("lock") != "":
        bad.append(f"V1 server lock {after_open.get('status')} {after_open.get('lock')!r}")
    if run["browser"] == "chrome" and any(r.get("method") == "LOCK" for r in run.get("davRequests") or []):
        bad.append("V1 a LOCK went out")
    # V7
    for control in run.get("controls") or []:
        want = control.get("mutates") == "1"
        if control.get("mutates") not in ("0", "1") or control.get("disabled") != want:
            bad.append(f"V7 {control.get('action') or control.get('id')}: disabled {control.get('disabled')} mutates {control.get('mutates')}")
    text_field = run.get("textField") or {}
    if text_field.get("disabled") is not True or text_field.get("sinkReadOnly") is not True:
        bad.append(f"V7 text field {text_field}")
    # By name, not only disabled == mutates: both come from one expression, so a
    # page that labelled the moves "1" would stay consistent and unclickable.
    moves = {(c.get("action") or c.get("id")): c for c in run.get("controls") or []}
    for name in ("move-character-left", "move-character-right"):
        control = moves.get(name) or {}
        if control.get("mutates") != "0" or control.get("disabled") is not False:
            bad.append(f"V7 move {name}: mutates {control.get('mutates')} disabled {control.get('disabled')}")
    # V5
    if run.get("ctrlS") is not True or run.get("savesAfterCtrlS") != 0:
        bad.append(f"V5 Ctrl+S prevented {run.get('ctrlS')} saves {run.get('savesAfterCtrlS')}")
    if host.get("saves"):
        bad.append(f"V5 host saves {len(host['saves'])}")
    if run.get("copiesAfter"):
        bad.append(f"V5 copies {run['copiesAfter']}")
    # V2 (button half gates)
    for row in buttons:
        if row["revisionAfter"] != row["revisionBefore"] or str(row["pending"]) != "0" or row["state"] != "ready" \
                or not (row["toast"] in ("", None) or "唯讀" in row["toast"]):
            bad.append(f"V2 {row['item']}: rev {row['revisionBefore']}->{row['revisionAfter']} pending {row['pending']} "
                       f"state {row['state']} toast {row['toast']!r}")
    # V6
    bad += not_asked(run)
    if (run.get("serverAfter") or {}).get("sha256") != (run.get("serverBefore") or {}).get("sha256"):
        bad.append("V6 server file changed")
    return bad


def score(report: dict[str, Any], strict: bool) -> dict[str, Any]:
    cells: dict[str, dict[str, Any]] = {}
    u0 = {(r["browser"], r.get("round")): not score_arm(r) for r in report["runs"] if r["arm"] == "U0"}
    rows = []
    for run in report["runs"]:
        problems = score_arm(run)
        if run["arm"].startswith("U") and run["arm"] != "U0" and not u0.get((run["browser"], run.get("round")), False):
            problems = problems + ["U0 did not hold for this browser and round"]
        rows.append({"arm": run["arm"], "browser": run["browser"], "round": run.get("round"), "problems": problems})
        cell = cells.setdefault(f"{run['arm']}/{run['browser']}", {"pass": 0, "runs": 0})
        cell["runs"] += 1
        cell["pass"] += not problems
    # Keyboard half of V2: measured, not gating (§7.3).
    keyboard = [{"browser": r["browser"], "round": r.get("round"), "item": row["item"],
                 "advanced": row["revisionAfter"] != row["revisionBefore"], "arm": r["arm"]}
                for r in report["runs"] if r["arm"] in ("Vro", "Vrw")
                for row in r.get("census") or [] if row.get("half") == "keyboard"]
    static_bad = []
    st = report.get("static") or {}
    if strict:
        if PAGE_SHA256 is None or st.get("page") != {"dist": PAGE_SHA256, "web": PAGE_SHA256, "served": PAGE_SHA256}:
            static_bad.append(f"page {st.get('page')}")
        if SESSION_SHA256 is None or st.get("session") != {"tree": SESSION_SHA256, "dist": SESSION_SHA256,
                                                           "served": SESSION_SHA256}:
            static_bad.append(f"session {st.get('session')}")
        if st.get("hostVersion") != HOST_VERSION:
            static_bad.append(f"host version {st.get('hostVersion')}")
        if HOST_COMMIT is None or not str(report.get("hostRepo") or "").startswith(HOST_COMMIT):
            static_bad.append(f"host commit {str(report.get('hostRepo'))[:12]}, pinned {HOST_COMMIT}")
        if st.get("testStatic") != 0:
            static_bad.append(f"make test-e2-c-static {st.get('testStatic')}")
        for arm, (_, browsers, count) in PLAN.items():
            for browser in browsers:
                if cells.get(f"{arm}/{browser}", {}).get("runs") != count:
                    static_bad.append(f"{arm}/{browser}: {cells.get(f'{arm}/{browser}', {}).get('runs')} runs, plan {count}")
    ok = not static_bad and all(not r["problems"] for r in rows)
    verdict = ("PAGE HONEST" if ok else "NOT YET") if strict else ("clean" if ok else "problems")
    return {"verdict": verdict, "cells": cells, "static": static_bad,
            "failures": [r for r in rows if r["problems"]], "keyboard": keyboard}


# ------------------------------------------------------------------ red cases
# One mutation per criterion, on a clean shakedown run of the arm it targets:
# the case counts only if score_arm names the criterion's own problem (a
# substring of it), not merely any problem.  CHROME/FIREFOX limit a case to the
# browser whose branch the criterion lives in.

def _rec(run: dict, key: str = "leave") -> list[dict]:
    return run["leaves"][key]["record"]


def _set_rec(run: dict, key: str, entries: list[dict]) -> None:
    run["leaves"][key]["record"] = entries


def _fired_entry(run: dict, key: str = "leave") -> dict:
    return [e for e in _rec(run, key) if e.get("what") == "fired"][-1]


def _drop_fired(key: str = "leave"):
    return lambda r: _set_rec(r, key, [e for e in _rec(r, key) if e.get("what") != "fired"])


def _add_ask(who: str, key: str = "leave"):
    return lambda r: _rec(r, key).append({"what": "preventDefault", "who": who})


def _drop_asks(key: str = "leave"):
    return lambda r: _set_rec(r, key, [e for e in _rec(r, key) if not asks([e])])


def _asker(who: str, key: str = "leave"):
    def mutate(r: dict) -> None:
        for e in asks(_rec(r, key)):
            e["who"] = who
    return mutate


def _reasons(reasons: list[str], key: str = "leave"):
    return lambda r: _fired_entry(r, key).update(lastGuard={"at": 1, "reasons": reasons})


def _first_save(r: dict) -> dict:
    return first_attempt(r["host"]["saves"][0])


def _mutating_control(controls: list[dict]) -> dict:
    return next(c for c in controls if c.get("mutates") == "1")


def _row(r: dict, item: str) -> dict:
    return next(x for x in r["census"] if x["item"] == item)


CHROME, FIREFOX = ("chrome",), ("firefox",)
ZERO = "0" * 64
RED_CASES = [
    # (arm, browsers or None for both, criterion, expected substring, mutation)
    ("U0", None, "U0 recorder saw the leave", "no `fired` record", _drop_fired()),
    ("U0", None, "U0 only the runner asked", "wanted ['runner'] only", _add_ask("page")),
    ("U0", CHROME, "U0 Chrome showed the dialog", "no dialog in Chrome",
     lambda r: r["leaves"]["leave"].update(dialog=None)),
    ("U1", None, "U1 asked", "leave1: askers", _drop_asks("leave1")),
    ("U1", None, "U1 the host asked, not the page", "leave1: askers", _asker("page", "leave1")),
    ("U1", None, "U1 the host's reason is page", "leave1: host guard reasons", _reasons(["inFlight"], "leave1")),
    ("U1", CHROME, "U1 the lock survives staying", "after leave1: host lock",
     lambda r: r["hostAfterLeave1"]["lock"].update(state="released")),
    ("U1", CHROME, "U1 the server token survives staying", "after leave2: server lock",
     lambda r: r["serverAfterLeave2"].update(token="opaquelocktoken:x")),
    ("U1", CHROME, "U1 asked again on leave2", "leave2: askers", _drop_asks("leave2")),
    ("U1", CHROME, "U1 the save after staying is a 204 with the token", "save after staying",
     lambda r: _first_save(r).update(status=412)),
    ("U1", CHROME, "U1 the save lands on the original", "the save did not land on the original",
     lambda r: r["serverAfterSave"].update(sha256=ZERO)),
    ("U1", CHROME, "U1 no copy after the save", "copies after the save",
     lambda r: r.update(copiesAfterSave=[{"name": "x（衝突副本）.odt"}])),
    ("U1", CHROME, "U1 no ask after saving", "leave3: asked by", _add_ask("host", "leave3")),
    ("U1", FIREFOX, "U1 Firefox: the server file is untouched", "server file changed",
     lambda r: r["serverAfterArm"].update(sha256=ZERO)),
    ("U-window", None, "U-window asked", "leave: askers", _drop_asks()),
    ("U-window", None, "U-window is the window, not the save in flight", "not the window",
     _reasons(["page", "inFlight"])),
    ("U-window", CHROME, "U-window the trap fired", "the trap never fired", lambda r: r.update(trap=None)),
    ("U-window", CHROME, "U-window the save finished after staying", "the save did not finish",
     lambda r: r["host"].update(saves=[])),
    ("U2", None, "U2 not asked", "leave: asked by", _add_ask("host")),
    ("U2", None, "U2 the recorder saw the leave", "no `fired` record", _drop_fired()),
    ("U2", None, "U2 the server holds the save's bytes", "server bytes are not the save's",
     lambda r: r["serverAfterArm"].update(sha256=ZERO)),
    ("U3", None, "U3 asked after the second edit", "leave: askers", _drop_asks()),
    ("U4", None, "U4 the stranger's unlock was refused", "refused unlock", lambda r: r.update(refusedUnlock=200)),
    ("U4", None, "U4 the save went to a conflict copy", "copy {}", lambda r: r["host"]["saves"][0].update(conflictCopy={})),
    ("U4", None, "U4 the copy holds the save's bytes", "copies", lambda r: r["copiesAfter"][0].update(sha256=ZERO)),
    ("U4", None, "U4 not asked", "leave: asked by", _add_ask("host")),
    ("U5", None, "U5 not asked (\"always ask\")", "leave: asked by", _add_ask("host")),
    ("U5", None, "U5 the recorder saw the leave", "no `fired` record", _drop_fired()),
    ("U7", None, "U7 asked", "leave: askers", _drop_asks()),
    ("U7", None, "U7 asked because the edit was still pending", "pending",
     lambda r: _fired_entry(r).update(pending="0")),
    ("U6a", None, "U6 first half: the page asked (download mode)", "leave: askers", _asker("host")),
    ("U6b", None, "U6 second half: a download happened", "no download", lambda r: r.update(download={"none": True})),
    ("U6b", None, "U6 second half: not asked after the download", "leave: asked by", _add_ask("page")),
    ("K-held", None, "K-held every keydown prevented", "keydowns prevented",
     lambda r: r["prevented"].__setitem__(5, False)),
    ("K-held", None, "K-held exactly one host save", "host saves",
     lambda r: r["host"]["saves"].append(copy.deepcopy(r["host"]["saves"][-1]))),
    ("K-held", None, "K-held exactly one page-level save", "page-level saves", lambda r: r.update(pageSaves=2)),
    ("K-sep", None, "K-sep two presses under 300 ms", "presses", lambda r: r["separate"].update(spanMs=400)),
    ("K-sep", None, "K-sep two host saves", "host saves", lambda r: r["host"].update(saves=r["host"]["saves"][:1])),
    ("K-sep", None, "K-sep the second save carries the marker", "marker",
     lambda r: r["serverAfter"].update(texts=[])),
    ("K-two", None, "K-two two host saves", "host saves", lambda r: r["host"].update(saves=r["host"]["saves"][:1])),
    ("K-two", None, "K-two the second press lands before the first save's answer", "second press",
     lambda r: r["pair"].update(secondAt=(_first_save(r).get("respondedAt") or 0) + 1)),
    ("V", None, "V1 no LOCK (host record)", "V1 host lock", lambda r: r["opened"]["lock"].update(state="held")),
    ("V", None, "V1 the host was handed readOnly", "V1 host lock", lambda r: r["opened"].update(handedReadOnly=False)),
    ("V", None, "V1 the read-only notice", "V1 notice", lambda r: r["bar"].update(notice="")),
    ("V", None, "V1 no lock on the server", "V1 server lock", lambda r: r["afterOpen"].update(lock="1")),
    ("V", None, "V1 the lock property answered", "V1 server lock", lambda r: r["afterOpen"].update(lock=None)),
    ("V", CHROME, "V1 no LOCK on the wire", "V1 a LOCK went out",
     lambda r: r.setdefault("davRequests", []).append({"method": "LOCK"})),
    ("V", None, "V7 a mutating control is disabled", "V7 set-bold: disabled False",
     lambda r: next(c for c in r["controls"] if c.get("action") == "set-bold").update(disabled=False)),
    ("V", None, "V7 the moves stay usable (disabled)", "V7 move move-character-left",
     lambda r: next(c for c in r["controls"] if c.get("action") == "move-character-left").update(disabled=True)),
    ("V", None, "V7 the moves stay usable (labelled and disabled as a mutation)", "V7 move move-character-right",
     lambda r: next(c for c in r["controls"] if c.get("action") == "move-character-right").update(
         mutates="1", disabled=True)),
    ("V", None, "V7 the text field is disabled", "V7 text field", lambda r: r["textField"].update(disabled=False)),
    ("V", None, "V7 the text field record is not empty", "V7 text field", lambda r: r.update(textField={})),
    ("V", None, "V5 Ctrl+S prevented and no save", "V5 Ctrl+S", lambda r: r.update(savesAfterCtrlS=1)),
    ("V", None, "V5 no host save", "V5 host saves", lambda r: r["host"].update(saves=[{"attempts": []}])),
    ("V", None, "V5 no copy", "V5 copies", lambda r: r.update(copiesAfter=[{"name": "x.odt"}])),
    ("V", None, "V2 read-only: no revision advanced", "V2 insert-text",
     lambda r: _row(r, "insert-text").update(revisionAfter="1")),
    ("V", None, "V2 read-only: the pill stays ready", "V2 set-bold",
     lambda r: _row(r, "set-bold").update(state="recoverable-error")),
    ("V", None, "V2 read-only: no toast but the read-only one", "V2 undo",
     lambda r: _row(r, "undo").update(toast="復原：EDITOR_NOT_READY")),
    ("V", None, "V2 read-only: the census covers every control", "V2 census",
     lambda r: r.update(census=[x for x in r["census"] if x["item"] != "clear-format"])),
    ("V", None, "V4 a line down", "V4 movedDown", lambda r: r["movedDown"].update(latency="定位游標 30 ms")),
    ("V", None, "V4 the caret went down", "V4 caret y", lambda r: r.update(sinkTopAfter=r["sinkTopBefore"])),
    ("V", None, "V6 not asked", "leave: asked by", _add_ask("host")),
    ("V", None, "V6 the server file is untouched", "V6 server file changed",
     lambda r: r["serverAfter"].update(sha256=ZERO)),
    ("V2 writable control", None, "V2 control: every mutating control advances", "V2 control: set-italic",
     lambda r: _row(r, "set-italic").update(revisionAfter=_row(r, "set-italic")["revisionBefore"])),
    ("V2 writable control", None, "V2 control: the census covers every control", "V2 census",
     lambda r: r.update(census=[x for x in r["census"] if x["item"] != "insert-text"])),
    ("V2 writable control", None, "V2 control: an empty census does not pass", "V2 census",
     lambda r: r.update(census=[], controlsAtCensus=[])),
    ("V2 writable control", None, "V2 control: a control that changed the document is labelled a mutation",
     "V2 control: set-bold advanced but is labelled",
     lambda r: next(c for c in r["controlsAtCensus"] if c.get("action") == "set-bold").update(mutates="0")),
    # §7.14: the exemption for a button hidden at census is that button's own, and only for "must advance".
    ("V2 writable control", None, "V2 control: another button's hidden does not exempt this one",
     "V2 control: set-italic did not advance",
     lambda r: (next(c for c in r["controlsAtCensus"] if c.get("action") == "set-bold").update(hidden=True),
                _row(r, "set-italic").update(revisionAfter=_row(r, "set-italic")["revisionBefore"]))),
    ("V2 writable control", None, "V2 control: a hidden button that changed the document is labelled a mutation",
     "V2 control: set-bold advanced but is labelled",
     lambda r: next(c for c in r["controlsAtCensus"] if c.get("action") == "set-bold").update(hidden=True, mutates="0")),
    # Clauses the implementation review found with no red case.
    ("U1", CHROME, "U1 Chrome showed the dialog on leave1", "leave1: no dialog in Chrome",
     lambda r: r["leaves"]["leave1"].update(dialog=None)),
    ("U1", FIREFOX, "U1 Firefox left the page", "leave1: still at",
     lambda r: r["leaves"]["leave1"].update(pathAfter="/index.php/apps/litecore/r/x/e2-editor.html")),
    ("U1", None, "U1 the edit landed", "smoke", lambda r: r["smoke"]["acted"].update(revision=r["smoke"]["caret"]["revision"])),
    ("U2", CHROME, "U2 no dialog in Chrome", "a dialog in Chrome",
     lambda r: r["leaves"]["leave"].update(dialog={"type": "beforeunload"})),
    ("U2", None, "U2 no onbeforeunload handler property", "handler property",
     lambda r: _fired_entry(r).update(handlerProperty=True)),
    ("U3", CHROME, "U3 Chrome showed the dialog", "leave: no dialog in Chrome",
     lambda r: r["leaves"]["leave"].update(dialog=None)),
    ("U-window", None, "U-window the host's reason is page", "leave: host guard reasons", _reasons(["inFlight"])),
    ("K-held", None, "K-held settled", "never settled", lambda r: r.update(settled={"timedOut": True})),
    ("K-held", None, "K-held the edit landed", "smoke",
     lambda r: r["smoke"]["acted"].update(latency="標題 失敗")),
    ("K-sep", None, "K-sep both presses prevented", "presses", lambda r: r["separate"].update(second=False)),
    ("K-sep", None, "K-sep save #1 is a version without the marker", "save #1 already carries the marker",
     lambda r: next(v for v in r["versions"] if v.get("sha256") == r["host"]["saves"][0]["sha256"]).update(
         texts=["x " + MARKER])),
    ("K-sep", None, "K-sep save #1 was found among the versions", "save #1 is not among",
     lambda r: r.update(versions=[])),
    ("K-sep", None, "K-sep the server holds the second save", "not the second save's",
     lambda r: r["serverAfter"].update(sha256=ZERO)),
    ("K-two", None, "K-two the second press was made and prevented", "the second press was never made",
     lambda r: r.update(pair=None)),
    ("V", None, "V2 read-only: nothing left pending", "pending 1",
     lambda r: _row(r, "set-italic").update(pending="1")),
    ("V", None, "V5 Ctrl+S was prevented", "V5 Ctrl+S", lambda r: r.update(ctrlS=False)),
    ("V", None, "the document opened", "not opened", lambda r: next(
        x for x in r["opened"]["steps"] if x.get("step") == "opened")["state"].update(state="busy")),
]
CELL_OF = {cell: arm for arm, (cell, _, _) in PLAN.items()}
CELL_OF.update({"V": "Vro", **{arm: arm for arm in PLAN}})


def red_cases(paths: list[Path]) -> tuple[int, int]:
    runs = [run for path in paths for run in json.loads(path.read_text())["runs"]]
    failures = reds = 0

    def clean(arm: str, browser: str) -> dict | None:
        return next((r for r in runs if r["arm"] == arm and r["browser"] == browser and not score_arm(r)), None)

    for cell, browsers, label, expect, mutate in RED_CASES:
        arm = CELL_OF[cell]
        for browser in browsers or BOTH:
            base = clean(arm, browser)
            if base is None:
                print(f"  MISSING {label} [{browser}]: no clean {arm} run")
                failures += 1
                continue
            mutated = copy.deepcopy(base)
            try:
                mutate(mutated)
            except (KeyError, IndexError, StopIteration, TypeError) as error:
                print(f"  MISSING {label} [{browser}]: the clean run has nothing to mutate ({error!r})")
                failures += 1
                continue
            problems = score_arm(mutated)
            red = any(expect in problem for problem in problems)
            failures += not red
            reds += red
            print(f"  {'red ' if red else 'GREEN'}  {label} [{browser}]" + ("" if red else f"  -> {problems}"))
    # Report level: a U cell does not count in a browser and round whose U0 failed.
    for browser in BOTH:
        u0, u1 = clean("U0", browser), clean("U1", browser)
        if u0 is None or u1 is None:
            print(f"  MISSING U0 gates the U cells [{browser}]: no clean U0/U1")
            failures += 1
            continue
        u0, u1 = copy.deepcopy(u0), copy.deepcopy(u1)
        u0["round"] = u1["round"] = 1
        _drop_fired()(u0)
        rows = score({"runs": [u0, u1], "static": {}}, strict=False)["failures"]
        red = any(r["arm"] == "U1" and "U0 did not hold" in " ".join(r["problems"]) for r in rows)
        failures += not red
        reds += red
        print(f"  {'red ' if red else 'GREEN'}  U0 gates the U cells [{browser}]")
    return reds, failures


def one_line(result: dict[str, Any]) -> str:
    cells = " ".join(f"{k}:{v['pass']}/{v['runs']}" for k, v in sorted(result["cells"].items()))
    return f"VERDICT {result['verdict']}  {cells}" + (f"  static: {result['static']}" if result["static"] else "")


def static_facts(ddev_root: Path) -> dict[str, Any]:
    binding = host_binding(ddev_root)
    app = Path(binding["appDir"])
    manifest = json.loads((app / "engine" / "MANIFEST.json").read_text())
    files = manifest.get("files", manifest)
    info = (app / "appinfo" / "info.xml").read_text()
    version = info.split("<version>", 1)[1].split("</version>", 1)[0] if "<version>" in info else None
    return {
        "page": {"dist": sha256_file(DIST / "e2-editor-app.js"), "web": sha256_file(PROJECT / "web" / "e2-editor-app.js"),
                 "served": (files.get("e2-editor-app.js") or {}).get("sha256")},
        "session": {"tree": sha256_file(PROJECT / "editor-shell-v2" / "narrow-editor-v2-session.js"),
                    "dist": sha256_file(DIST / "editor-shell-v2" / "narrow-editor-v2-session.js"),
                    "served": (files.get("editor-shell-v2/narrow-editor-v2-session.js") or {}).get("sha256")},
        "hostVersion": version, "engineBuildId": manifest.get("buildId"),
    }, binding


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--label", choices=("shakedown", "counted"))
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--repeats", type=int, default=None, help="shakedown only")
    parser.add_argument("--arms", default=",".join(PLAN), help="shakedown only: a counted run runs the plan")
    parser.add_argument("--score", type=Path)
    parser.add_argument("--red-cases", type=Path, nargs="+", metavar="REPORT",
                        help="each mutation must turn its own criterion red, on clean runs pooled from REPORTs")
    args = parser.parse_args()
    if args.red_cases:
        reds, failures = red_cases(args.red_cases)
        print(f"red cases: {reds} red, {failures} not red or missing")
        return 0 if failures == 0 else 1
    if args.score:
        report = json.loads(args.score.read_text())
        result = score(report, strict=report.get("label") == "counted")
        print(one_line(result))
        for failure in result["failures"]:
            print(f"  {failure['arm']}/{failure['browser']} r{failure['round']}: {failure['problems']}")
        return 0 if result["verdict"] in ("PAGE HONEST", "clean") else 1
    if not args.label:
        parser.error("--label or --score")
    counted = args.label == "counted"
    static, binding = static_facts(args.ddev_root)
    if counted:
        if binding["hostDirty"]:
            print(f"refusing a counted run: the host repo has uncommitted changes:\n{binding['hostDirty']}")
            return 2
        if PAGE_SHA256 is None or SESSION_SHA256 is None or HOST_COMMIT is None:
            print("refusing a counted run: PAGE_SHA256 / SESSION_SHA256 / HOST_COMMIT are not written down yet")
            return 2
        static["testStatic"] = subprocess.run(["make", "-C", str(PROJECT), "test-e2-c-static"],
                                              capture_output=True, text=True).returncode
    instance = Instance(args.ddev_root)
    log: list[dict[str, Any]] = []
    server = Server(instance, log)
    report: dict[str, Any] = {
        "runner": Path(__file__).name, "runnerSha256": sha256_file(Path(__file__)), "label": args.label,
        "spec": "specs/SPEC-M3-page-honesty.md", "startedAt": utc_now(), "static": static,
        **binding_fields(binding), "baseUrl": instance.base,
        "original": {"source": str(FIXTURE.relative_to(DIST)), "sha256": sha256_file(FIXTURE)}, "runs": [],
    }
    arms = list(PLAN) if counted else args.arms.split(",")
    browsers = args.browsers.split(",")
    rounds = 3 if counted else (args.repeats or 1)
    out = EVIDENCE / ("runs" if counted else "shakedown") / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        report["setup"] = server.setup()
        with tempfile.TemporaryDirectory(prefix="m3-honesty-", dir=PROJECT / "build") as scratch:
            for index in range(rounds):
                for arm in arms:
                    for browser in browsers:
                        if browser not in PLAN[arm][1]:
                            continue
                        print(f"round {index + 1} {arm} {browser}", flush=True)
                        run = run_arm(arm, browser, server, Path(scratch))
                        run["round"] = index + 1
                        report["runs"].append(run)
                        problems = score_arm(run)
                        print(f"  {'ok' if not problems else problems}", flush=True)
                        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    finally:
        server.teardown()
        report["completedAt"] = utc_now()
        report["httpLog"] = log
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    result = score(report, strict=counted)
    report["score"] = result
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(REPO))
    print(one_line(result))
    return 0 if result["verdict"] in ("PAGE HONEST", "clean") else 1


if __name__ == "__main__":
    sys.exit(main())
