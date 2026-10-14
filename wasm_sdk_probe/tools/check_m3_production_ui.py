#!/usr/bin/env python3
"""SPEC-M3-production-ui §4: findings 109 and 110 and the production UI, on the M3 host.

One browser per arm, a fresh login each, against the `litecore` dev instance.
The document is the owner's (its sha256 goes into the report; it is not in the
repo), uploaded fresh as `m3-109 測試.odt` for every arm.  Clicks go through the
page's own pointer handler (POINT_AT, like every M3 runner); KEYS ARE REAL KEYS
(Chrome: CDP Input.dispatchKeyEvent; Firefox: WebDriver actions) -- the page
acts on the browser's own beforeinput/keydown, and that is the path 109 sat on.

On v19 (spec §13) the two boundary places of 0.2.7 are Writer's own key, not
refusals, and the refusals left on this document are its two ends:

  Kdel  A1-2' K  type a marker, click the end of the heading, Delete, wait, save;
                 no reopen, and the server's paragraph text (marker removed) is
                 the native key arm's (R-host E02)
  Kbs   A1-2' K  the same at the first body paragraph's start, Backspace TWICE
                 (Writer's first removes the indent; R-host Q01's second save)
  Rbs   A1-2' R  type a marker, the first line + Home, Backspace: refused and
                 reopened, the server's text (marker removed) is the original's
  Rdel  A1-2' R  the last line + End, type the marker THERE, Delete: the same
  Bctl  A1-2  positive control: type, Backspace mid-text
  S     A2-1, A2-2  the product stylesheet touches nothing outside its container
  P     A3-1, A3-2, A2-3  what is visible, the keys, the unsaved mark, closing
  B3x   A1-5  three boundary refusals in one page load (B1, spec §9): the third
              meets the Worker generation ceiling, is not restarted, and its
              content reaches the server without a save; then the notice's reload.
              All three at the document's start on v19.
  Bdel, Bbs: 0.2.7's arms (v8).  Scored as they were, so their reports re-score;
              no longer run (their positions are v8's layout).

  check_m3_production_ui.py --out REPORT [--arms Kdel,Kbs,...] [--browsers chrome,firefox]
                            [--rounds N] [--doc ODT] [--counted]
  check_m3_production_ui.py --score REPORT [--expect-red]
  check_m3_production_ui.py --red-cases REPORT

Never run two M3 runners at once: every arm clears the whole oc_files_lock table.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import subprocess
import sys
import time
import traceback
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_locks import HOST_DONE, LockChrome, Server, login, open_from_files  # noqa: E402
from check_m3_page_honesty import READ_RECORD, RECORDER, chrome_wait_dialog  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, READ_STATE, Instance  # noqa: E402
from odt_paragraphs import paragraph_texts_from_xml  # noqa: E402
from probe_m3_gate0_coep import DIST, firefox_profile, sha256_file, utc_now, wait_until  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import POINT_AT, PRESS, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
SCRATCH = PROJECT / "build" / "scratch-m3-production-ui"   # snap Firefox cannot see /tmp
# The owner's document, copied here (gitignored) from the dev instance; not in the repo.
DOC = SCRATCH / "PMPC指南.odt"
NAME = "m3-109 測試.odt"
MARK = "zqx"
# B3x: one marker per refusal, so the server's file says which refusal's content
# arrived.  None of them is in the owner's document (checked per run: `serverBefore`).
MARKS3 = ("zqa", "zqb", "zqc")
BOTH = ("chrome", "firefox")
# Bindings for a counted run (spec §4), written before it.  None = not yet bound.
# Spec §13.5, written 2026-10-09 before any counted run on host 0.2.8 (v19); the
# 0.2.7 values (spec §11) were page e97d6e03, session 3f5f754b, 0488586, v55 2470765a.
# Re-pointed 2026-10-15 (task 10-15c P4, before binding v20) to host 0.2.23's page (shell v72, engine v20).  The previous pin was
# d761f1cee9d26c50c0b152348d74c3d05f540e9228927815d93ad6ec161e7dcd (autosave §9.19, 0.2.13/v62; the 0.2.13 and 0.2.14 counts ran on it).
PAGE_SHA256: str | None = "ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e"   # host 0.2.23 (v72), 2026-10-15; was d761f1ce (autosave §9.19, 0.2.13), 8909564e (§17 C′), 36c2b18b (§16 R⁗), 18c8afbe (§15 R‴), 537d62d7 (§14 R′), e00ab76a (§13.5)
SESSION_SHA256: str | None = "62a2a20e4c66f630d77caf5bb75973e28aa58b0d8c7bf4cb0e35fa44b6a6fc5c"   # §14 R′; was ee3e53a2
HOST_VERSION: str | None = "0.2.14"   # autosave §9.24; was 0.2.13, 0.2.12
HOST_COMMIT: str | None = "237f2cb"   # autosave §9.24; was e028517, b245ae7
SHELL_BUNDLE_SHA256: str | None = "318b3bf252d585eda43c12577423aeb67995c8487f24688547ec09d2f45839e6"   # v63; was v62 75e29eb2, v61 f48df85b, v60 784a1d93, v59 ad65480a, v58 a6f9331a, v57 1aed21b1
DOC_SHA256: str | None = "7b336879547df057ae6d38e907f221b40c90c37cd65d2df5afceceb91941657e"
# 0.2.7's places, calibrated on v8's layout (findings/evidence/109/README.md):
# inside the first body paragraph; the blank right of the heading 「一、序言」;
# the first body paragraph's first-line indent.  Kept for the record; v19's
# document is 308480 twips tall against v8's ~257000 and these land on other lines.
IN_TEXT_V8, HEADING_END_V8, PARA_START_V8 = ("0.5", "0.0115"), ("0.693", "0.00728"), ("0.127", "0.00927")
# v19's places (spec §13.2): fractions of 12474 x 308480 twips from the native
# carets of round R-host (findings/evidence/merge-native/PREDICTION-R-host.md),
# x-40 twips for a Delete place, x+40 for a Backspace place, y at mid-line --
# the merge runner's rule.  v19's caret equals native's on this document (X6).
IN_TEXT = ("0.5", "0.010373")               # y 3200: the first body paragraph, about its third line
HEADING_END = ("0.225910", "0.006219")      # E02 (2858, 1658, 521): X6 clicked here on v19, keyed false
PARA_START = ("0.155363", "0.008270")       # Q01 (1898, 2377, 348)
FIRST_LINE = ("0.116883", "0.006219")       # Q02 (1418, 1658, 521), then Home
LAST_LINE = ("0.836781", "0.990622")        # Q03 (10478, 305449, 276), then End
# Paragraph text sequences (odt_paragraphs, json.dumps(ensure_ascii=False), sha256)
# of the references, spec §13.3: the owner's document as uploaded (211
# paragraphs), and Writer's key arm at the heading's end = its two Backspaces at
# the body's start (R-host r1..r3 E02 key, r1..r3 Q01 key2: 210 paragraphs, all
# six the same).  The server's file is compared with its marker removed.
ORIGINAL_SEQ = "d646dda7c887a8b6830d245ab6a678f38c02488171a0d5ff2ca26064d99180e4"
MERGED_SEQ = "1f53faf461e0349178353f4728a38b139e6b154525822405e51f34a3f104f06e"
KEY_ARMS = {"Kdel": ("Delete", 1), "Kbs": ("Backspace", 2)}
REFUSAL_ARMS = ("Rbs", "Rdel")
KEEP_ACTIONS = ["undo", "redo", "set-bold", "set-italic", "set-underline", "set-strikethrough",
                "set-paragraph-heading", "set-paragraph-body", "set-list-unordered", "set-list-ordered",
                "set-list-none", "save"]
KEEP_IDS = ["clear-format", "litecore-host-close", "litecore-host-download", "notice-action"]
TEXT_PLACES = "#litecore-host-title, #litecore-host-unsaved, #state-pill, #notice, #litecore-host-bar"

# Every change of the page's state, as the DOM shows it, with the toolbar's
# disabled count -- A1-3 is asked of each sample.
TIMELINE = """(() => { const t0 = performance.now(); const log = window.__m3ui = [];
  const read = () => ({ t: Math.round(performance.now() - t0),
    state: document.querySelector('#state-pill').dataset.state,
    gen: document.querySelector('#s-generation').textContent,
    rev: document.querySelector('#s-revision').textContent,
    cp: document.querySelector('#s-checkpoint').textContent,
    disabled: [...document.querySelectorAll('#toolbar button')].filter(b => b.disabled).length,
    buttons: document.querySelectorAll('#toolbar button').length,
    toast: document.querySelector('#toast').textContent });
  let last = '';
  const tick = () => { const r = read(); const k = JSON.stringify({ ...r, t: 0 }); if (k !== last) { log.push(r); last = k; } };
  new MutationObserver(tick).observe(document.body, { attributes: true, childList: true, characterData: true, subtree: true });
  tick(); return true; })()"""
READ_TIMELINE = "(() => window.__m3ui || null)()"
GEN = "(() => document.querySelector('#s-generation').textContent)()"
# Review 2026-10-06 item 11: every longhand the browser itself lists, not a hand
# enumeration (CLAUDE.md §1, form two); `props` in the report says how many.
STYLE_BEFORE = """(() => { const props = [...getComputedStyle(document.body)];
  const node = [...document.querySelectorAll('style')].find(s => s.textContent.includes('--accent:'));
  if (!node) return { error: 'no product stylesheet' };
  const all = [...document.querySelectorAll('body, body *')];
  window.__m3style = { node, all, props, before: all.map(e => { const s = getComputedStyle(e); return props.map(p => s.getPropertyValue(p)); }) };
  node.sheet.disabled = true; return { elements: all.length, props: props.length, scoped: node.textContent.includes('@scope') }; })()"""
STYLE_AFTER = """(() => { const { node, all, props, before } = window.__m3style;
  const after = all.map(e => { const s = getComputedStyle(e); return props.map(p => s.getPropertyValue(p)); });
  node.sheet.disabled = false;
  const root = document.getElementById('litecore-editor-root');
  const outside = [], inside = [];
  all.forEach((e, i) => { const diff = props.filter((p, k) => before[i][k] !== after[i][k]);
    if (!diff.length) return;
    const rec = { tag: e.tagName.toLowerCase(), id: e.id || null, cls: String(e.className || '').slice(0, 40), diff };
    (root && root.contains(e) ? inside : outside).push(rec); });
  // Review 2026-10-06 item 10: a scoping that skipped `:root` leaves every var(--…)
  // unresolved and still changes elements inside, so ask the container itself.
  const accent = root ? getComputedStyle(root).getPropertyValue('--accent').trim() : null;
  return { outsideCount: outside.length, outside: outside.slice(0, 30), insideCount: inside.length,
           inside: inside.slice(0, 5), accent }; })()"""
BODY_BG = """(() => { const s = getComputedStyle(document.body);
  return { color: s.backgroundColor, image: s.backgroundImage.slice(0, 200) }; })()"""
INVENTORY = """(() => { const KEEP_ACTIONS = ARG_ACTIONS, KEEP_IDS = ARG_IDS, PLACES = ARG_PLACES;
  const root = document.getElementById('litecore-editor-root');
  if (!root) return { error: 'no editor root' };
  const visible = (e) => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && parseFloat(s.opacity) > 0; };
  const excluded = (e) => e.closest('#paper, #toast');
  const kept = (e) => !!e && (KEEP_ACTIONS.includes(e.dataset.action) || KEEP_IDS.includes(e.id));
  const name = (e) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.dataset.action ? '[' + e.dataset.action + ']' : '')
    + (e.className && typeof e.className === 'string' ? '.' + e.className.split(' ')[0] : '');
  const controls = [...root.querySelectorAll('button, select, input, textarea')].filter(e => !excluded(e) && visible(e));
  const badControls = controls.filter(e => !kept(e)).map(name);
  const badText = []; const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) { const t = walker.currentNode; const text = t.textContent.trim(); if (!text) continue;
    const p = t.parentElement; if (excluded(p) || !visible(p)) continue;
    if (p.closest(PLACES) || kept(p.closest('button, select, input, textarea'))) continue;
    badText.push({ text: text.slice(0, 40), in: name(p) }); }
  const close = document.getElementById('litecore-host-close'); const title = document.getElementById('litecore-host-title');
  return { controls: controls.map(name), badControls, badText,
           title: title ? title.textContent : null, closeVisible: !!close && visible(close) }; })()"""
UNSAVED_SHOWN = "(() => { const e = document.getElementById('litecore-host-unsaved'); return e ? !e.hidden && e.getBoundingClientRect().width > 0 : null; })()"
HOST = "(() => JSON.parse(document.documentElement.getAttribute('data-litecore') || 'null'))()"
PATH = "(() => location.pathname + location.search)()"
HAS_ROOT = "(() => !!document.getElementById('litecore-editor-root'))()"
CLOSE = "(() => { document.querySelector('#litecore-host-close').click(); return true; })()"
# B1 (spec §9): what the page says at the Worker generation ceiling, and its one button.
# `hostSave` is read IN THE SAME EVALUATION as `limit`: a page that said `saved`
# before the host's write landed would otherwise pass, because the server is
# read seconds later (review 2026-10-06b item 1).
LIMIT = """(() => { const n = document.querySelector('#notice'), a = document.querySelector('#notice-action');
  const host = JSON.parse(document.documentElement.getAttribute('data-litecore') || 'null');
  const last = host && host.saves && host.saves.length ? host.saves[host.saves.length - 1] : null;
  return { limit: n.dataset.limit ?? null, show: n.dataset.show ?? null, rescue: n.dataset.rescue ?? null,
           text: document.querySelector('#notice-text').textContent, action: a.textContent, disabled: a.disabled,
           hostSave: last ? { settled: last.settled ?? null, outcome: last.outcome ?? null, saves: host.saves.length } : null }; })()"""
NOTICE_ACTION = "(() => { document.querySelector('#notice-action').click(); return true; })()"


# ------------------------------------------------------------------ browsers

def new_session(kind: str):
    if kind == "chrome":
        session = LockChrome("cold")
        # No network events: a save's Network.requestWillBeSent carries the PUT
        # body, and this document's (573 KB, JSON-escaped to 1.37 MB) is past the
        # CDP socket's 1 MiB frame limit -- the first shakedown died there on
        # every arm that saved.  Each arm is a fresh profile, so the first load is
        # cold whatever the cache setting.
        session.call("Network.disable")
        session.call("Emulation.setDeviceMetricsOverride",
                     {"width": 1850, "height": 980, "deviceScaleFactor": 1, "mobile": False})
        return session
    SCRATCH.mkdir(parents=True, exist_ok=True)
    session = FirefoxSession("cold", profile_dir=firefox_profile(SCRATCH / f"ff-{time.monotonic_ns()}"))
    session.command("POST", "/window/rect", {"width": 1850, "height": 1080})
    return session


CDP_KEYS = {"Delete": ("Delete", "Delete", 46), "Backspace": ("Backspace", "Backspace", 8),
            "Enter": ("Enter", "Enter", 13), "Home": ("Home", "Home", 36), "End": ("End", "End", 35)}
WD_KEYS = {"Delete": "", "Backspace": "", "Enter": "", "Shift": "", "Home": "\ue011", "End": "\ue010"}


def press(session, kind: str, key: str, shift: bool = False) -> None:
    """One real key.  `key` is a name in CDP_KEYS or one lowercase letter."""
    if kind == "chrome":
        if key in CDP_KEYS:
            name, code, vk = CDP_KEYS[key]
            text = None
        else:
            name, code, vk, text = key, f"Key{key.upper()}", ord(key.upper()), key
        mods = 8 if shift else 0
        for phase in (("rawKeyDown", "char", "keyUp") if text else ("rawKeyDown", "keyUp")):
            params = {"type": phase, "key": name, "code": code, "windowsVirtualKeyCode": vk,
                      "nativeVirtualKeyCode": vk, "modifiers": mods}
            if phase == "char":
                params["text"] = text
            session.call("Input.dispatchKeyEvent", params)
        return
    value = WD_KEYS.get(key, key)
    actions = ([{"type": "keyDown", "value": WD_KEYS["Shift"]}] if shift else []) + [
        {"type": "keyDown", "value": value}, {"type": "keyUp", "value": value}] + (
        [{"type": "keyUp", "value": WD_KEYS["Shift"]}] if shift else [])
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": actions}]})
    session.command("DELETE", "/actions")


def state(session) -> dict[str, Any]:
    return evaluate(session, READ_STATE) or {}


def until(session, predicate, limit: float) -> dict[str, Any] | None:
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        seen = state(session)
        if predicate(seen):
            return seen
        time.sleep(0.15)
    return None


def quiet(session, limit: float = 30) -> dict[str, Any]:
    """Until the queue has been empty and the session ready for half a second."""
    deadline, since, seen = time.monotonic() + limit, None, {}
    while time.monotonic() < deadline:
        seen = state(session)
        if seen.get("state") == "ready" and str(seen.get("pending")) == "0":
            since = since or time.monotonic()
            if time.monotonic() - since >= 0.5:
                return seen
        else:
            since = None
        time.sleep(0.15)
    return {**seen, "timedOut": True}


def click(session, at: tuple[str, str]) -> dict[str, Any]:
    before = state(session)
    evaluate(session, POINT_AT.replace("ARG_X", at[0]).replace("ARG_Y", at[1]))
    placed = until(session, lambda s: "定位游標" in (s.get("latency") or "") and s.get("latency") != before.get("latency"), 30)
    return {"latency": (placed or {}).get("latency"), "timedOut": placed is None, "settled": quiet(session)}


def keyed(session, kind: str, key: str, shift: bool = False) -> dict[str, Any]:
    """A key that should change the document by exactly one revision."""
    before = quiet(session)
    generation = evaluate(session, GEN)   # READ_STATE has no generation
    press(session, kind, key, shift)
    time.sleep(0.6)
    after = quiet(session)
    return {"key": ("Shift+" if shift else "") + key, "revBefore": before.get("revision"),
            "revAfter": after.get("revision"), "genBefore": generation,
            "genAfter": evaluate(session, GEN), "latency": after.get("latency")}


def save_and_settle(session, limit: float = 60) -> dict[str, Any]:
    before = len((evaluate(session, HOST) or {}).get("saves") or [])
    evaluate(session, PRESS.replace("ARG_ACTION", "save"))
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        saves = (evaluate(session, HOST) or {}).get("saves") or []
        if len(saves) > before and saves[-1].get("settled") is True:
            time.sleep(0.5)
            return {"saves": len(saves), "outcome": saves[-1].get("outcome"), "state": state(session)}
        time.sleep(0.3)
    return {"saves": before, "timedOut": True, "state": state(session)}


def marks(odt: bytes, mark: str = MARK) -> int:
    with zipfile.ZipFile(io.BytesIO(odt)) as archive:
        return archive.read("content.xml").decode("utf-8").count(mark)


def sequence_sha256(texts: list[str]) -> str:
    return hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode("utf-8")).hexdigest()


def first_difference_index(a: list[str], b: list[str]) -> int | None:
    """The first paragraph index where two sequences differ (None: equal).  An
    index, not the text: the reports carry none of the owner's text."""
    for index, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return index
    return None if len(a) == len(b) else min(len(a), len(b))


def server_marks(server: Server, uploaded: bytes | None = None) -> dict[str, Any]:
    status, raw = server.instance.dav("GET", NAME)
    out = {"status": status, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "marks": marks(raw),
           "marks3": {mark: marks(raw, mark) for mark in MARKS3}}
    # Spec §13.3: the paragraph text sequence with the marker removed, as a hash.
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            texts = [p.replace(MARK, "") for p in paragraph_texts_from_xml(archive.read("content.xml"))]
        out.update(seqSha256=sequence_sha256(texts), paragraphs=len(texts))
        if uploaded is not None:
            with zipfile.ZipFile(io.BytesIO(uploaded)) as archive:
                out["firstDiffFromUploaded"] = first_difference_index(
                    texts, paragraph_texts_from_xml(archive.read("content.xml")))
    except Exception:  # noqa: BLE001 -- recorded; the score reads a missing hash as a failure
        out["seqError"] = traceback.format_exc().strip().splitlines()[-1]
    return out


# ------------------------------------------------------------------ arms

def run_arm(arm: str, kind: str, server: Server, doc: bytes) -> dict[str, Any]:
    base = server.instance.base
    record: dict[str, Any] = {"arm": arm, "browser": kind, "startedAt": utc_now()}
    record["clearedLocks"] = server.clear_locks()
    record["upload"] = server.upload(server.admin, NAME, doc)
    record["fileId"] = server.fileid(server.admin, NAME)
    session = new_session(kind)
    record["version"] = getattr(session, "version", None)
    try:
        record["login"] = login(session, base, "admin", server.instance.password)
        if arm == "S":
            navigate(session, base + "/apps/files/files?dir=/", timeout=120)
            wait_until(session, "(() => !!document.querySelector('[data-cy-files-list-row-name]'))()", 60)
            record["filesBody"] = evaluate(session, BODY_BG)
        open_from_files(session, base, "", NAME, record)
        record["opened"] = quiet(session, 60)
        if arm == "Bctl":
            run_boundary(arm, kind, session, server, record)
        elif arm in KEY_ARMS:
            run_key(arm, kind, session, server, record, doc)
        elif arm in REFUSAL_ARMS:
            run_refusal(arm, kind, session, server, record, doc)
        elif arm == "B3x":
            record["serverBefore"] = server_marks(server)
            run_three_refusals(kind, session, server, record)
        elif arm == "S":
            record["editorBody"] = evaluate(session, BODY_BG)
            record["styleBefore"] = evaluate(session, STYLE_BEFORE)
            time.sleep(1.0)   # past any transition the change started
            record["style"] = evaluate(session, STYLE_AFTER)
        elif arm == "P":
            run_production(kind, session, server, record)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            record.setdefault("closeError", traceback.format_exc())
        record["completedAt"] = utc_now()
    return record


def run_boundary(arm: str, kind: str, session, server: Server, record: dict[str, Any]) -> None:
    """Bctl only since spec §13 (0.2.7's Bdel and Bbs went through here too)."""
    evaluate(session, TIMELINE)
    record["genOpened"] = evaluate(session, GEN)
    record["inText"] = click(session, IN_TEXT)
    record["typed"] = [keyed(session, kind, ch) for ch in MARK]
    record["key"] = keyed(session, kind, "Backspace")
    record["genAfter"] = evaluate(session, GEN)
    record["save"] = save_and_settle(session, 60)
    record["timeline"] = evaluate(session, READ_TIMELINE)
    record["server"] = server_marks(server)


def wait_reopened(session, record: dict[str, Any]) -> dict[str, Any]:
    """After a key that should be refused: back to ready on its own in a new
    Worker (109's fix), or stuck (109), or never refused -- each ends this wait."""
    time.sleep(1.0)
    seen = until(session, lambda s: s.get("state") == "ready" and str(s.get("pending")) == "0"
                 and evaluate(session, GEN) != record["genOpened"], 60) or state(session)
    time.sleep(1.0)
    return seen


def run_key(arm: str, kind: str, session, server: Server, record: dict[str, Any], doc: bytes) -> None:
    """A1-2' K (spec §13.3): Writer's own key at a boundary, no reopen.

    The marker goes in first (unsaved work at the moment of the key: 109's
    shape), then the boundary key, once (Kdel) or twice (Kbs: Writer's first
    Backspace there removes the indent, the second joins).
    """
    key, count = KEY_ARMS[arm]
    evaluate(session, TIMELINE)
    record["genOpened"] = evaluate(session, GEN)
    record["inText"] = click(session, IN_TEXT)
    record["typed"] = [keyed(session, kind, ch) for ch in MARK]
    record["placed"] = click(session, HEADING_END if arm == "Kdel" else PARA_START)
    record["presses"] = []
    for _ in range(count):
        record["presses"].append(keyed(session, kind, key))
        time.sleep(1.0)
    record["genAfter"] = evaluate(session, GEN)
    record["save"] = save_and_settle(session, 60)
    record["timeline"] = evaluate(session, READ_TIMELINE)
    record["server"] = server_marks(server, doc)


def run_refusal(arm: str, kind: str, session, server: Server, record: dict[str, Any], doc: bytes) -> None:
    """A1-2' R (spec §13.3): a refusal at one of the document's two ends.

    Rbs: marker mid-text, then the first line + Home + Backspace.  Rdel: the
    last line + End FIRST, the marker typed there, then Delete -- typing earlier
    in the document could push the last line down a line before the click.
    """
    evaluate(session, TIMELINE)
    record["genOpened"] = evaluate(session, GEN)
    if arm == "Rbs":
        record["inText"] = click(session, IN_TEXT)
        record["typed"] = [keyed(session, kind, ch) for ch in MARK]
        record["placed"] = click(session, FIRST_LINE)
        record["moved"] = keyed(session, kind, "Home")
        press(session, kind, "Backspace")
    else:
        record["placed"] = click(session, LAST_LINE)
        record["moved"] = keyed(session, kind, "End")
        record["typed"] = [keyed(session, kind, ch) for ch in MARK]
        press(session, kind, "Delete")
    record["afterKey"] = wait_reopened(session, record)
    record["genAfter"] = evaluate(session, GEN)
    record["save"] = save_and_settle(session, 60)
    record["timeline"] = evaluate(session, READ_TIMELINE)
    record["server"] = server_marks(server, doc)


def run_three_refusals(kind: str, session, server: Server, record: dict[str, Any]) -> None:
    """A1-5 (spec §9.3).  Three boundary refusals; the third meets the ceiling.

    No click after a reopen: the next marker is typed straight away, so a page
    that did not give the input sink its focus back drops it (spec §9.5 (3)).
    No save is pressed: whatever reaches the server, the rescue put there.
    """
    evaluate(session, TIMELINE)
    record["genOpened"] = evaluate(session, GEN)
    record["inText"] = click(session, IN_TEXT)
    record["refusals"] = []
    # Spec §13.2: on v19 the only refusals on this document are at its ends; all
    # three at the start.  After a reopen the next marker lands at the start
    # (the caret is there), so the click is followed by Home, which does not
    # depend on which side of the marker the click fell.
    for index, mark in enumerate(MARKS3):
        key = "Backspace"
        step: dict[str, Any] = {"mark": mark, "key": key, "genBefore": evaluate(session, GEN)}
        step["typed"] = [keyed(session, kind, ch) for ch in mark]
        step["placed"] = click(session, FIRST_LINE)
        step["moved"] = keyed(session, kind, "Home")
        pressed = time.monotonic()
        press(session, kind, key)
        if index < 2:
            time.sleep(1.0)
            step["after"] = until(session, lambda s, before=step["genBefore"]: s.get("state") == "ready"
                                  and str(s.get("pending")) == "0" and evaluate(session, GEN) != before, 60) or state(session)
            time.sleep(1.0)
        else:
            # Spec §9.3: `data-limit` is `saved` within 10 s of the key.
            seen = None
            while time.monotonic() - pressed < 10.0:
                seen = evaluate(session, LIMIT)
                if (seen or {}).get("limit") == "saved":
                    step["limitAfter"] = round(time.monotonic() - pressed, 2)
                    break
                time.sleep(0.15)
            step["limit"] = seen
            step["after"] = state(session)
        step["genAfter"] = evaluate(session, GEN)
        record["refusals"].append(step)
    # The host's own unsaved mark follows the page's watchUnsaved answer (and
    # anything it stranded): hidden = the page says nothing is unsaved AND the
    # host holds nothing.
    rescued_at = time.monotonic()
    hidden = None
    while time.monotonic() - rescued_at < 3.0:
        if evaluate(session, UNSAVED_SHOWN) is False:
            hidden = round(time.monotonic() - rescued_at, 2)
            break
        time.sleep(0.1)
    record["unsavedHiddenAfter"] = hidden
    record["timeline"] = evaluate(session, READ_TIMELINE)
    record["hostBefore"] = evaluate(session, HOST)
    record["server"] = server_marks(server)
    # The notice's button reloads the page; the host must not ask.  Chrome needs
    # user activation for a beforeunload dialog to show at all, as in P.
    if kind == "chrome":
        record["activation"] = session.real_click("#state-pill")
    record["reload"] = leave_by_close(session, kind, record, "reload", NOTICE_ACTION)
    record["reloaded"] = quiet(session, 90)
    record["genReloaded"] = evaluate(session, GEN)
    record["hostAfter"] = evaluate(session, HOST)


def run_production(kind: str, session, server: Server, record: dict[str, Any]) -> None:
    base = server.instance.base
    record["inventory"] = evaluate(session, INVENTORY.replace("ARG_ACTIONS", json.dumps(KEEP_ACTIONS))
                                   .replace("ARG_IDS", json.dumps(KEEP_IDS)).replace("ARG_PLACES", json.dumps(TEXT_PLACES)))
    record["unsavedAtOpen"] = evaluate(session, UNSAVED_SHOWN)
    record["inText"] = click(session, IN_TEXT)
    # The unsaved mark's clock starts AT THE KEY (spec §4 A3-2, "打字後 1.5 秒內").
    # Review 2026-10-06 item 13: starting it after keyed() -- which itself waits
    # past the host's 0.5 s poll -- made `shown` 0.0 by construction.  So this
    # key is pressed raw and the mark watched from the press; keyed()'s record
    # is assembled around it.
    before = quiet(session)
    generation = evaluate(session, GEN)
    typed_at = time.monotonic()
    press(session, kind, "a")
    shown = None
    while time.monotonic() - typed_at < 1.5:
        if evaluate(session, UNSAVED_SHOWN) is True:
            shown = round(time.monotonic() - typed_at, 2)
            break
        time.sleep(0.05)
    after = quiet(session)
    record["keys"] = [{"key": "a", "revBefore": before.get("revision"), "revAfter": after.get("revision"),
                       "genBefore": generation, "genAfter": evaluate(session, GEN), "latency": after.get("latency")}]
    record["unsavedShownAfter"] = shown
    # Mid-paragraph only: Backspace right after Shift+Enter would delete the line
    # break, which the barrier refuses like a paragraph boundary (spec §7).
    record["keys"] += [keyed(session, kind, "Backspace"), keyed(session, kind, "Delete"),
                       keyed(session, kind, "Enter"), keyed(session, kind, "Enter", shift=True)]
    record["save"] = save_and_settle(session, 60)
    saved_at = time.monotonic()
    hidden = None
    while time.monotonic() - saved_at < 3.0:
        if evaluate(session, UNSAVED_SHOWN) is False:
            hidden = round(time.monotonic() - saved_at, 2)
            break
        time.sleep(0.1)
    record["unsavedHiddenAfter"] = hidden
    # Closing with nothing unsaved: to Files, the lock released.
    record["closeClean"] = leave_by_close(session, kind, record, "clean")
    record["closeClean"]["hasEditor"] = evaluate(session, HAS_ROOT)
    record["closeClean"]["unlocked"] = server.wait_unlocked(server.admin, NAME, 10)
    # Closing with an edit nobody saved: asked; staying keeps the page.
    open_from_files(session, base, "", NAME, record.setdefault("reopen", {}))
    quiet(session, 60)
    if kind == "chrome":
        record["activation"] = session.real_click("#state-pill")
    click(session, IN_TEXT)
    record["dirtyKey"] = keyed(session, kind, "b")
    record["closeDirty"] = leave_by_close(session, kind, record, "dirty")
    record["closeDirty"]["hasEditor"] = evaluate(session, HAS_ROOT)


def leave_by_close(session, kind: str, record: dict[str, Any], key: str, expression: str = CLOSE) -> dict[str, Any]:
    nonce = f"{key}-{time.monotonic_ns()}"
    evaluate(session, RECORDER.replace("ARG_NONCE", json.dumps(nonce)))
    result: dict[str, Any] = {}
    if kind == "chrome":
        session.next_id += 1
        session.websocket.send(json.dumps({"id": session.next_id, "method": "Runtime.evaluate",
                                           "params": {"expression": expression}}))
        result["dialog"] = chrome_wait_dialog(session, 5.0)
        if result["dialog"]:
            session.call("Page.handleJavaScriptDialog", {"accept": False})
        time.sleep(2.0)
    else:
        try:
            evaluate(session, expression)
        except Exception as error:  # noqa: BLE001 -- the navigation can cut the answer off
            result["evaluateError"] = f"{type(error).__name__}: {error}"
        time.sleep(4)
    result["path"] = wait_until(session, PATH, 20)
    raw = wait_until(session, READ_RECORD.replace("ARG_NONCE", json.dumps(nonce)), 10)
    result["record"] = json.loads(raw) if isinstance(raw, str) else {"missing": raw}
    return result


# ------------------------------------------------------------------ static facts

def static_facts(root: Path) -> dict[str, Any]:
    git = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, text=True).stdout.strip()  # noqa: E731
    manifest = json.loads((root / "engine" / "MANIFEST.json").read_text())
    files = manifest.get("files") or {}
    info = (root / "appinfo" / "info.xml").read_text()
    return {"hostCommit": git("rev-parse", "--short", "HEAD"), "hostDirty": git("status", "--porcelain").splitlines(),
            "hostVersion": re.search(r"<version>([^<]+)</version>", info).group(1),
            "buildId": manifest.get("buildId"),
            "servedPage": (files.get("e2-editor-app.js") or {}).get("sha256"),
            "servedSession": (files.get("editor-shell-v2/narrow-editor-v2-session.js") or {}).get("sha256"),
            "distPage": sha256_file(DIST / "e2-editor-app.js"),
            "shellBundle": shell_bundle()}


def shell_bundle() -> dict[str, Any]:
    """The frozen generation's own tool, asked its question (no --write): exit 0
    means the tree and dist/ are exactly what the named manifest records."""
    answer = subprocess.run([sys.executable, str(PROJECT / "tools" / "build_e2_c_shell_bundle.py")],
                            capture_output=True, text=True)
    try:
        said = json.loads(answer.stdout)
    except json.JSONDecodeError:
        said = {"unparsed": answer.stdout[-400:]}
    return {"exit": answer.returncode, "manifest": said.get("manifest"), "sha256": said.get("bundleSha256"),
            "problems": said.get("problems")}


# ------------------------------------------------------------------ scoring

def score_run(run: dict[str, Any]) -> list[str]:
    arm, bad = run["arm"], []
    if run.get("fatal"):
        return ["fatal: " + run["fatal"].strip().splitlines()[-1]]
    if arm in ("Bdel", "Bbs", "B3x") + REFUSAL_ARMS:
        if arm == "B3x":
            bad += score_three_refusals(run)
        else:
            if run.get("genOpened") != "1" or run.get("genAfter") != "2":
                bad.append(f"generation {run.get('genOpened')} -> {run.get('genAfter')}: no refusal-and-reopen happened")
            server = run.get("server") or {}
            if not server.get("marks"):
                bad.append(f"the server's file has no {MARK!r} (saves {run.get('save', {}).get('saves')})")
            if arm in REFUSAL_ARMS:   # spec §13.3 A1-2' R
                if server.get("marks") and server.get("marks") != 1:
                    bad.append(f"A1-2' R: the server's file has {server.get('marks')} markers, one was typed")
                if server.get("seqSha256") != ORIGINAL_SEQ:
                    bad.append(f"A1-2' R: the server's text (marker removed) is not the original's: first difference at "
                               f"paragraph {server.get('firstDiffFromUploaded')}, {server.get('paragraphs')} paragraphs "
                               f"{server.get('seqError') or ''}")
        samples = run.get("timeline") or []
        blocked = [s for s in samples if s.get("state") not in ("ready", "busy")]
        if not blocked:
            bad.append("A1-3: no sample outside ready/busy")
        for sample in blocked:
            if sample.get("disabled") != sample.get("buttons"):
                bad.append(f"A1-3: {sample.get('state')} at {sample.get('t')} ms with "
                           f"{sample.get('disabled')}/{sample.get('buttons')} buttons disabled")
                break
    elif arm in KEY_ARMS:
        bad += score_key(run)
    elif arm == "Bctl":
        key = run.get("key") or {}
        if not (str(key.get("revBefore", "")).isdigit() and str(key.get("revAfter", "")).isdigit()
                and int(key["revAfter"]) == int(key["revBefore"]) + 1):
            bad.append(f"control: revision {key.get('revBefore')} -> {key.get('revAfter')}")
        if run.get("genAfter") != run.get("genOpened"):
            bad.append(f"control: generation {run.get('genOpened')} -> {run.get('genAfter')}")
    elif arm == "S":
        style = run.get("style") or {}
        if style.get("outsideCount") != 0:
            bad.append(f"A2-1: {style.get('outsideCount')} elements outside the container change: {style.get('outside', [])[:3]}")
        if not style.get("insideCount"):
            bad.append("A2-1: nothing inside the container changes (vacuous)")
        if not style.get("accent"):
            bad.append("A2-1: the container does not resolve the sheet's --accent (its :root was not scoped)")
        if (run.get("styleBefore") or {}).get("props", 0) < 100:
            bad.append(f"A2-1: compared {(run.get('styleBefore') or {}).get('props')} properties (the browser's list is hundreds)")
        if run.get("filesBody") != run.get("editorBody"):
            bad.append(f"A2-2: body {run.get('editorBody')} != Files {run.get('filesBody')}")
    elif arm == "P":
        inventory = run.get("inventory") or {}
        if inventory.get("error") or inventory.get("badControls") or inventory.get("badText"):
            bad.append(f"A3-1: controls {inventory.get('badControls')} text {(inventory.get('badText') or [])[:4]} {inventory.get('error') or ''}")
        for key in run.get("keys") or []:
            ok = (str(key.get("revBefore", "")).isdigit() and str(key.get("revAfter", "")).isdigit()
                  and int(key["revAfter"]) == int(key["revBefore"]) + 1 and key.get("genAfter") == key.get("genBefore"))
            if not ok:
                bad.append(f"A3-2: {key.get('key')} revision {key.get('revBefore')} -> {key.get('revAfter')}, "
                           f"generation {key.get('genBefore')} -> {key.get('genAfter')}")
        if run.get("unsavedShownAfter") is None or run.get("unsavedHiddenAfter") is None:
            bad.append(f"A3-2: unsaved mark shown {run.get('unsavedShownAfter')} hidden {run.get('unsavedHiddenAfter')}")
        if not inventory.get("closeVisible") or inventory.get("title") != NAME:
            bad.append(f"A2-3: title {inventory.get('title')!r}, close visible {inventory.get('closeVisible')}")
        clean = run.get("closeClean") or {}
        path = clean.get("path") or ""
        clean_entries = clean.get("record") if isinstance(clean.get("record"), list) else []
        # Anchored: the first shakedown landed on /apps/files/index.php/apps/files/files/<id>
        # and an unanchored search called that a pass (spec §7).
        if (not re.match(rf"(/index\.php)?/apps/files/files/{run.get('fileId')}\?", path) or not re.search(r"dir=(%2F|/)(&|$)", path)
                or "openfile" in path or clean.get("hasEditor") is not False or clean.get("dialog")
                or any(e.get("what") in ("preventDefault", "returnValue") for e in clean_entries)):
            bad.append(f"A2-3 clean: path {path!r} editor {clean.get('hasEditor')} dialog {bool(clean.get('dialog'))} "
                       f"asked {[e.get('who') for e in clean_entries if e.get('what') == 'preventDefault']}")
        if not (clean.get("unlocked") or {}).get("released"):
            bad.append(f"A2-3 clean: lock not released in 10 s ({(clean.get('unlocked') or {}).get('polls', [])[-1:]})")
        # Asked, and by the host for the page's reason (the recorder, as in the
        # page-honesty runner).  Chrome: the dialog is dismissed, so the user
        # stays.  Firefox's driver accepts the prompt, so it leaves.
        dirty = run.get("closeDirty") or {}
        entries = dirty.get("record") if isinstance(dirty.get("record"), list) else []
        asked = sorted({e.get("who") for e in entries if e.get("what") == "preventDefault"})
        fired = [e for e in entries if e.get("what") == "fired"]
        reasons = ((fired[-1].get("lastGuard") or {}).get("reasons") or []) if fired else []
        stayed = (bool(dirty.get("dialog")) and dirty.get("hasEditor") is True if run["browser"] == "chrome"
                  else "/apps/files" in (dirty.get("path") or ""))
        if asked != ["host"] or "page" not in reasons or not stayed:
            bad.append(f"A2-3 dirty: askers {asked}, reasons {reasons}, dialog {bool(dirty.get('dialog'))}, "
                       f"path {dirty.get('path')!r}, editor {dirty.get('hasEditor')}")
    return bad


def digits(*values: Any) -> bool:
    return all(str(v if v is not None else "").isdigit() for v in values)


def score_key(run: dict[str, Any]) -> list[str]:
    """A1-2' K (spec §13.3)."""
    bad = []
    if MERGED_SEQ == ORIGINAL_SEQ:
        bad.append("A1-2' K: the reference equals the original (vacuous)")
    presses = run.get("presses") or []
    want = KEY_ARMS[run["arm"]][1]
    if len(presses) != want:
        bad.append(f"A1-2' K: {len(presses)} presses recorded, the arm presses {want}")
    generations = [run.get("genOpened"), run.get("genAfter")] + [
        g for p in presses for g in (p.get("genBefore"), p.get("genAfter"))]
    if any(g != "1" for g in generations):
        bad.append(f"A1-2' K: generations {generations}: a Worker was reopened")
    for number, p in enumerate(presses, 1):
        latency = p.get("latency") or ""
        if latency.endswith("失敗") or not re.search(r"[0-9]+ ms$", latency):
            bad.append(f"A1-2' K: press {number}'s last operation reads {latency!r}")
        if not (digits(p.get("revBefore"), p.get("revAfter")) and int(p["revAfter"]) > int(p["revBefore"])):
            bad.append(f"A1-2' K: press {number} revision {p.get('revBefore')} -> {p.get('revAfter')}")
    samples = run.get("timeline") or []
    stopped = [s for s in samples if s.get("state") not in ("ready", "busy")]
    if not samples:
        bad.append("A1-2' K: no timeline (vacuous)")
    elif stopped:
        bad.append(f"A1-2' K: the session stopped: {stopped[0].get('state')} at {stopped[0].get('t')} ms")
    server = run.get("server") or {}
    if server.get("marks") != 1:
        bad.append(f"A1-2' K: the server's file has {server.get('marks')} markers, one was typed "
                   f"(saves {run.get('save', {}).get('saves')})")
    if server.get("seqSha256") != MERGED_SEQ:
        bad.append(f"A1-2' K: the server's text (marker removed) is not Writer's key arm's: first difference from "
                   f"the uploaded document at paragraph {server.get('firstDiffFromUploaded')}, "
                   f"{server.get('paragraphs')} paragraphs {server.get('seqError') or ''}")
    return bad


def score_three_refusals(run: dict[str, Any]) -> list[str]:
    """A1-5 (spec §9.3)."""
    bad = []
    before = (run.get("serverBefore") or {}).get("marks3") or {}
    if set(before) != set(MARKS3) or any(before.values()):
        bad.append(f"A1-5: the uploaded document already has markers {before} (vacuous)")
    steps = run.get("refusals") or []
    generations = [(s.get("genBefore"), s.get("genAfter")) for s in steps]
    if generations != [("1", "2"), ("2", "3"), ("3", "3")]:
        bad.append(f"A1-5: generations {generations}, want 1->2, 2->3, 3->3")
    last = steps[-1] if len(steps) == 3 else {}
    if (last.get("after") or {}).get("state") != "restart-required":
        bad.append(f"A1-5: after the third refusal the state is {(last.get('after') or {}).get('state')!r}")
    seen = last.get("limit") or {}
    if seen.get("limit") != "saved":
        bad.append(f"A1-5: the notice says {seen.get('limit')!r} 10 s after the key, not 'saved'")
    elif (seen.get("hostSave") or {}).get("settled") is not True or (seen.get("hostSave") or {}).get("outcome") != "saved":
        bad.append(f"A1-5: the notice said 'saved' while the host's last save was {seen.get('hostSave')}")
    present = (run.get("server") or {}).get("marks3") or {}
    missing = [mark for mark in MARKS3 if not present.get(mark)]
    if missing:
        bad.append(f"A1-5: the server's file lacks {missing} (no save was pressed)")
    if run.get("unsavedHiddenAfter") is None:
        bad.append("A1-5: the host still showed unsaved work 3 s after the rescue")
    reload = run.get("reload") or {}
    entries = reload.get("record") if isinstance(reload.get("record"), list) else []
    asked = sorted({e.get("who") for e in entries if e.get("what") == "preventDefault"})
    if asked or reload.get("dialog"):
        bad.append(f"A1-5: the reload was guarded: askers {asked}, dialog {bool(reload.get('dialog'))}")
    if not any(e.get("what") == "fired" for e in entries):
        bad.append(f"A1-5: the recorder saw no beforeunload, so 'not asked' means nothing ({reload.get('record')!r:.80})")
    fetched = ((run.get("hostAfter") or {}).get("fetched") or {}).get("sha256")
    if run.get("genReloaded") != "1" or (run.get("reloaded") or {}).get("state") != "ready":
        bad.append(f"A1-5: after the reload generation {run.get('genReloaded')}, state {(run.get('reloaded') or {}).get('state')}")
    if not fetched or fetched != (run.get("server") or {}).get("sha256"):
        bad.append("A1-5: the reloaded page did not open the server's rescued bytes")
    lock = ((run.get("hostAfter") or {}).get("lock") or {}).get("state")
    if lock != "held":
        bad.append(f"A1-5: after the reload the host's lock is {lock!r}, not held")
    return bad


def score(report: dict[str, Any]) -> dict[str, Any]:
    cells: dict[str, dict[str, Any]] = {}
    for run in report["runs"]:
        cell = cells.setdefault(f"{run['arm']}/{run['browser']}", {"runs": 0, "pass": 0, "failures": []})
        cell["runs"] += 1
        problems = score_run(run)
        cell["pass"] += not problems
        if problems:
            cell["failures"].append(problems)
    # Review 2026-10-06 item 14: a document that already had the marker would
    # pass A1-2 with nothing typed.
    doc_clean = (report.get("doc") or {}).get("marks") == 0
    return {"cells": cells, "docClean": doc_clean,
            "allPass": all(c["pass"] == c["runs"] for c in cells.values()) and bool(cells) and doc_clean}


def counted_bindings(static: dict[str, Any]) -> list[str]:
    bad = []
    for key, want in (("servedPage", PAGE_SHA256), ("distPage", PAGE_SHA256), ("servedSession", SESSION_SHA256),
                      ("hostVersion", HOST_VERSION), ("hostCommit", HOST_COMMIT)):
        if want is None or (static.get(key) or "")[:len(want)] != want:
            bad.append(f"{key} is {static.get(key)!r}, the spec binds {want!r}")
    if static.get("hostDirty"):
        bad.append(f"host tree is dirty: {static['hostDirty'][:5]}")
    shell = static.get("shellBundle") or {}
    if shell.get("exit") != 0 or shell.get("sha256") != SHELL_BUNDLE_SHA256:
        bad.append(f"shell generation: {shell}, the spec binds {SHELL_BUNDLE_SHA256}")
    return bad


# One mutation per criterion, on a passing report: every one must turn it red.
MUTATIONS = [
    # Spec §13.3 (v19): the refusal arms moved to the document's ends, the
    # boundary keys became Writer's own (K).  0.2.7's Bdel/Bbs mutations were
    # these four on those arms; re-check 0.2.7's reports with that commit's runner.
    ("A1-2' R marker missing", "Rdel", lambda r: r["server"].update(marks=0)),
    ("A1-2' R no reopen", "Rbs", lambda r: r.update(genAfter="1")),
    ("A1-2' R the refusal changed the text", "Rbs", lambda r: r["server"].update(seqSha256=MERGED_SEQ)),
    ("A1-2' R two markers", "Rdel", lambda r: r["server"].update(marks=2)),
    ("A1-3 a blocked sample with a live button", "Rdel",
     lambda r: r["timeline"].append({"state": "restart-required", "t": 1, "disabled": 0, "buttons": 21})),
    ("A1-3 no blocked sample", "Rbs", lambda r: r.update(timeline=[s for s in r["timeline"] if s.get("state") in ("ready", "busy")])),
    ("A1-2' K reopened", "Kdel", lambda r: r.update(genAfter="2")),
    ("A1-2' K the second press in a new Worker", "Kbs", lambda r: r["presses"][1].update(genAfter="2")),
    ("A1-2' K stopped", "Kbs",
     lambda r: r["timeline"].append({"state": "restart-required", "t": 1, "disabled": 21, "buttons": 21})),
    ("A1-2' K a press failed", "Kbs", lambda r: r["presses"][0].update(latency="⌫ 刪除 失敗")),
    ("A1-2' K a press changed nothing", "Kdel", lambda r: r["presses"][0].update(revAfter=r["presses"][0]["revBefore"])),
    ("A1-2' K one press short", "Kbs", lambda r: r["presses"].pop()),
    ("A1-2' K the text is the original's (v8 refused and kept it)", "Kdel",
     lambda r: r["server"].update(seqSha256=ORIGINAL_SEQ)),
    ("A1-2' K marker missing", "Kbs", lambda r: r["server"].update(marks=0)),
    ("A1-2 control did not delete", "Bctl", lambda r: r["key"].update(revAfter=r["key"]["revBefore"])),
    ("A2-1 a header element changes", "S", lambda r: r["style"].update(outsideCount=1)),
    ("A2-1 vacuous", "S", lambda r: r["style"].update(insideCount=0)),
    ("A2-1 :root not scoped", "S", lambda r: r["style"].update(accent="")),
    ("A2-1 a hand-picked property list", "S", lambda r: r["styleBefore"].update(props=18)),
    ("A2-2 body differs", "S", lambda r: r.update(editorBody={"color": "rgb(244, 246, 248)", "image": "none"})),
    ("A3-1 a developer control shows", "P", lambda r: r["inventory"]["badControls"].append("button[delete-forward]")),
    ("A3-1 developer text shows", "P", lambda r: r["inventory"]["badText"].append({"text": "修訂", "in": "span"})),
    ("A3-2 Enter did nothing", "P", lambda r: r["keys"][3].update(revAfter=r["keys"][3]["revBefore"])),
    ("A3-2 unsaved mark never shown", "P", lambda r: r.update(unsavedShownAfter=None)),
    ("A2-3 close reopened the file", "P", lambda r: r["closeClean"].update(path=r["closeClean"]["path"] + "&openfile=true")),
    ("A2-3 close landed on a doubled path", "P",
     lambda r: r["closeClean"].update(path="/apps/files/index.php" + r["closeClean"]["path"])),
    ("A2-3 dirty close not asked", "P", lambda r: r["closeDirty"].update(record=[])),
    ("A1-5 a fourth Worker", "B3x", lambda r: r["refusals"][2].update(genAfter="4")),
    ("A1-5 third marker missing", "B3x", lambda r: r["server"]["marks3"].update({MARKS3[2]: 0})),
    ("A1-5 second marker missing (focus not given back)", "B3x", lambda r: r["server"]["marks3"].update({MARKS3[1]: 0})),
    ("A1-5 the rescue failed", "B3x", lambda r: r["refusals"][2]["limit"].update(limit="failed")),
    ("A1-5 'saved' before the write landed", "B3x",
     lambda r: r["refusals"][2]["limit"]["hostSave"].update(settled=False)),
    ("A1-5 the rescue went to a copy", "B3x", lambda r: r["refusals"][2]["limit"]["hostSave"].update(outcome="copy")),
    ("A1-5 no lock after the reload", "B3x", lambda r: r["hostAfter"]["lock"].update(state="released")),
    ("A1-5 the session died", "B3x", lambda r: r["refusals"][2]["after"].update(state="recoverable-error")),
    ("A1-5 still unsaved", "B3x", lambda r: r.update(unsavedHiddenAfter=None)),
    ("A1-5 the reload was asked", "B3x", lambda r: r["reload"]["record"].append({"what": "preventDefault", "who": "host"})),
    ("A1-5 the recorder saw nothing", "B3x", lambda r: r["reload"].update(record=[])),
    ("A1-5 the reload opened other bytes", "B3x", lambda r: r["hostAfter"]["fetched"].update(sha256="0" * 64)),
    ("A1-5 markers were already there", "B3x", lambda r: r["serverBefore"]["marks3"].update({MARKS3[0]: 1})),
]


def red_cases(report: dict[str, Any]) -> tuple[int, int, list[str]]:
    red, total, notes = 0, 0, []
    for name, arm, mutate in MUTATIONS:
        for index, run in enumerate(report["runs"]):
            if run["arm"] != arm or score_run(run):
                continue
            total += 1
            mutated = copy.deepcopy(run)
            mutate(mutated)
            if score_run(mutated):
                red += 1
            else:
                notes.append(f"STAYED GREEN: {name} on run {index}")
            break
        else:
            notes.append(f"no passing {arm} run to mutate for {name!r}")
    return red, total, notes


# ------------------------------------------------------------------ main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--arms", default="Kdel,Kbs,Rbs,Rdel,Bctl,S,P,B3x")
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--doc", type=Path, default=DOC)
    parser.add_argument("--counted", action="store_true")
    parser.add_argument("--score", type=Path)
    parser.add_argument("--expect-red", action="store_true")
    parser.add_argument("--red-cases", type=Path)
    args = parser.parse_args()
    if args.score:
        result = score(json.loads(args.score.read_text()))
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0 if result["allPass"] != args.expect_red else 1
    if args.red_cases:
        red, total, notes = red_cases(json.loads(args.red_cases.read_text()))
        print(f"red cases: {red}/{total}", *notes, sep="\n")
        return 0 if red == total == len(MUTATIONS) else 1
    stale = [arm for arm in args.arms.split(",") if arm in ("Bdel", "Bbs")]
    if stale:
        print(f"{stale}: 0.2.7's arms, on v8's layout; spec §13 replaced them (Kdel, Kbs, Rbs, Rdel)")
        return 2
    instance = Instance(DEFAULT_DDEV)
    static = static_facts(DEFAULT_DDEV)
    doc = args.doc.read_bytes()
    if args.counted and hashlib.sha256(doc).hexdigest() != DOC_SHA256:
        print(f"refusing a counted run: the document is {hashlib.sha256(doc).hexdigest()}, the spec binds {DOC_SHA256}")
        return 2
    if args.counted and (problems := counted_bindings(static)):
        print("refusing a counted run:", *problems, sep="\n  ")
        return 2
    report: dict[str, Any] = {"spec": "specs/SPEC-M3-production-ui.md §4", "startedAt": utc_now(), "counted": args.counted,
                              # Review 2026-10-06 item 17: which scorer wrote this report.
                              "runner": "check_m3_production_ui.py", "runnerSha256": sha256_file(Path(__file__)),
                              "static": static, "doc": {"name": args.doc.name, "bytes": len(doc),
                                                        "sha256": hashlib.sha256(doc).hexdigest(), "marks": marks(doc)},
                              "runs": []}
    server = Server(instance, [])
    try:
        for _ in range(args.rounds):
            for kind in args.browsers.split(","):
                for arm in args.arms.split(","):
                    run = run_arm(arm, kind, server, doc)
                    report["runs"].append(run)
                    problems = score_run(run)
                    print(f"{arm:5s} {kind:8s} {'PASS' if not problems else 'FAIL'} {problems[:2]}", flush=True)
                    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    finally:
        server.clear_locks()
        report["completedAt"] = utc_now()
        report["score"] = score(report)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report["score"]["cells"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
