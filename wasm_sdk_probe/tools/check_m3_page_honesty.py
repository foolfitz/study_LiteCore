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
import json
import secrets
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_host_entry import CTRL_S, MARKER, host_record, server_file  # noqa: E402
from check_m3_locks import (  # noqa: E402
    BAR, CENTER, OTHER, RO_NAME, LockChrome, Server, chrome_download_dir, downloaded, edit, insert_marker,
    login, open_from_files, save, wire)
from check_m3_skeleton_open import (  # noqa: E402
    DEFAULT_DDEV, FIXTURE, NAME, ROUTE, Instance, binding_fields, host_binding, product_state, state_until)
from probe_m3_gate0_coep import DIST, firefox_profile, sha256_file, utc_now, wait_until  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import POINT_AT, PRESS, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-page-honesty"
ODT = "application/vnd.oasis.opendocument.text"
BOTH = ("chrome", "firefox")
# Bindings for a counted run, written down before it (spec §7.6 style): the page,
# the session subclass that holds the view-only gate, and the host version.
PAGE_SHA256: str | None = None
SESSION_SHA256: str | None = None
HOST_VERSION = "0.2.3"
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
    put({ what: 'fired', lastGuard: guards && guards.length ? guards[guards.length - 1] : null,
          guards: guards ? guards.length : null });
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
SEPARATE = """(() => { const sink = document.querySelector('#sink'); const t0 = performance.now();
  const key = () => sink.dispatchEvent(new KeyboardEvent('keydown', { key: 's', code: 'KeyS', ctrlKey: true,
    bubbles: true, cancelable: true })) === false;
  const first = key();
  document.querySelector('#text').value = ARG_MARKER;
  document.querySelector('#toolbar button[data-action="insert-text"]').click();
  const second = key();
  return { first, second, spanMs: Math.round(performance.now() - t0) }; })()"""
PAIR_AT = ("(() => { const v = JSON.parse(document.documentElement.getAttribute('data-litecore'));"
           " const button = document.querySelector('#toolbar button[data-action=\"save\"]'); button.click();"
           " const secondAt = Date.now() - v.started; const second = " + CTRL_S.strip() + ";"
           " return { secondAt, second }; })()")
SAVES = """(() => { const v = document.documentElement.getAttribute('data-litecore');
  const s = v && JSON.parse(v).saves; return s ? [s.length, s.every(x => x.settled === true)] : [0, true]; })()"""
ARROW_DOWN = """(() => document.querySelector('#sink').dispatchEvent(new KeyboardEvent('keydown', {
  key: 'ArrowDown', code: 'ArrowDown', bubbles: true, cancelable: true })) === false)()"""
KEY = """(() => { const sink = document.querySelector('#sink'); sink.focus();
  return sink.dispatchEvent(new KeyboardEvent('keydown', ARG_INIT)) === false; })()"""
# run_e2_c_product_path.DRAG, inlined (that module is 7000 lines to import for one string).
DRAG = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
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
    if kind == "chrome":
        record.setdefault("activations", []).append(session.real_click("#text"))


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
            edit(session, record)
            before = evaluate(session, SAVES)[0]
            record["separate"] = evaluate(session, SEPARATE.replace("ARG_MARKER", json.dumps(MARKER)))
            record["settled"] = settled(session, before + 2, quiet=5.0)
            record["savesBefore"] = before
            record["host"] = host_record(session)
            record["serverAfter"] = server_file(server.instance, NAME)
        elif arm == "Ktwo":
            edit(session, record)
            before = evaluate(session, SAVES)[0]
            record["pair"] = evaluate(session, PAIR_AT)
            record["settled"] = settled(session, before + 2, quiet=3.0)
            record["savesBefore"] = before
            record["host"] = host_record(session)
        record["serverAfterArm"] = server.content(server.admin, NAME)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        if kind == "chrome":
            record["davRequests"] = wire(session.drain())
        session.close()
        record["copiesAfter"] = server.copies(server.admin, "", NAME[:-4], remove=True)
        record["completedAt"] = utc_now()
    return record


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

    def point():
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        state_until(session, lambda s: "定位游標" in (s.get("latency") or ""), 30)

    def select():
        evaluate(session, DRAG.replace("ARG_X1", "0.2").replace("ARG_Y1", "0.28")
                 .replace("ARG_X2", "0.5").replace("ARG_Y2", "0.28"))
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
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
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
        elif (run.get("serverAfterArm") or {}).get("sha256") != (run.get("serverBefore") or {}).get("sha256"):
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
    elif arm == "Ktwo":
        pair = run.get("pair") or {}
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
    if writable:
        for row in buttons:
            if mutates.get(row["item"]) == "1" and row["item"] != "save" and row["revisionAfter"] == row["revisionBefore"]:
                bad.append(f"V2 control: {row['item']} did not advance ({row['latency']!r})")
        return bad
    # V1
    opened = run.get("opened") or {}
    if (opened.get("lock") or {}).get("state") != "readonly" or not opened.get("handedReadOnly"):
        bad.append(f"V1 host lock {(opened.get('lock') or {}).get('state')} handedReadOnly {opened.get('handedReadOnly')}")
    if "只能檢視" not in (run.get("bar") or {}).get("notice", ""):
        bad.append(f"V1 notice {(run.get('bar') or {}).get('notice')!r}")
    if (run.get("afterOpen") or {}).get("lock") not in ("", None):
        bad.append(f"V1 server lock {(run.get('afterOpen') or {}).get('lock')!r}")
    if run["browser"] == "chrome" and any(r.get("method") == "LOCK" for r in run.get("davRequests") or []):
        bad.append("V1 a LOCK went out")
    # V7
    for control in run.get("controls") or []:
        want = control.get("mutates") == "1"
        if control.get("mutates") not in ("0", "1") or control.get("disabled") != want:
            bad.append(f"V7 {control.get('action') or control.get('id')}: disabled {control.get('disabled')} mutates {control.get('mutates')}")
    if not all((run.get("textField") or {}).values()):
        bad.append(f"V7 text field {run.get('textField')}")
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
    args = parser.parse_args()
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
        if PAGE_SHA256 is None or SESSION_SHA256 is None:
            print("refusing a counted run: PAGE_SHA256 / SESSION_SHA256 are not written down yet")
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
