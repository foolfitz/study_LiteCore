#!/usr/bin/env python3
"""The v21 WASM shakedown, item 2 (paste as Markdown): the runner.

Arms: findings/evidence/link-batch-v21/shakedown/ARMS-item2.md (draft + rulings §9), ARMS.md (S-1..S-11),
spec §11.2 and §12.2.  Population: findings/evidence/link-batch-v21/shakedown/item2/population.json
(tools/v21_item2_population.py), regenerated and compared before anything starts.  Written after the arms
were committed (8f1dbf0a).  Never a count: every report says `"counted": false`.  The whole invocation
holds the S-9 browser-run lock.

Arms (`--arms`, comma-separated) and the page each runs on:
  m1        M1 (+ M2 from its M8 instance, M10a from every instance): the dialog, the empty template  (main)
  m3        M3 refusals on R-dialog and R-sdk, each with DM-9 C's undo reader; per-route positive control (main)
  m3size    M3's four size arms (SDK-L, SDK-L+1 on R-sdk; ENG-65536, ENG-65537 on R-worker)           (main)
  m4        M4, every population instance                                                            (main)
  m6        M6: the 64 KiB corpus through the dialog, busy -> ready, one Undo   (main page, its own browser)
  m7a, m7b  M7: the existing check re-armed (DM-15 A); C1 by a real Ctrl+V                             (main)
  m8        M8-v20 (DM-19 A) on the final page repointed to v20, with the v21 positive control  (v20 + main)
  m9        M9 clean, dirty, inject (DM-16 A)                                                           (main)
  m10       M10b, M10c (shipped worker) and M10d                                                       (main)
  m11       M11 dirty and cancel (M11-autosave is a host arm: not run here)                            (main)
  record    the task-checkbox record arm                                                               (main)
  m3bytes   M3's seven raw-byte items through S-10's carrier (spec §12.2 (a))           (bytes: non-shipped)
  trace     DM-6's records on the trace worker: M6's CORE_LOG count, M10b/c's selection precondition,
            the record arm's callbacks                                                  (trace: non-shipped)
  m5        M5 with S-11: proxy (loopback forced through it), target listeners, Chrome CDP   (proxy browser)

  run_v21_shakedown_item2.py --browser chrome --arms m1,m3 --rounds 1 --out DIR [--smoke]

The runner records; `judge_v21_shakedown_item2.py` decides.  Saved documents are kept beside the report
(`docs/`), every report flushes per instance, and a step that cannot be done as the arm says is recorded
as `runnerError` for that instance (the judge reads it as not done), never as a product result.
"""
from __future__ import annotations

import argparse
import base64
import signal
import gzip
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r7_support  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import run_merge_wasm_shakedown as mws  # noqa: E402
import run_v20_shakedown as v20  # noqa: E402
import fodt_to_odt  # noqa: E402
import v21_clipboard as clip  # noqa: E402
import v21_engine_read as er  # noqa: E402
import v21_input as inp  # noqa: E402
import v21_item2_compare as cmp  # noqa: E402
import v21_item2_fixtures as fx  # noqa: E402
import v21_item2_observer as obs2  # noqa: E402
import v21_item2_population as population  # noqa: E402
import v21_network as net  # noqa: E402
import v21_page_hook as hook  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v21_workers as workers  # noqa: E402

PROJECT = common.PROJECT
REPO = common.REPO
POPULATION = REPO / "findings/evidence/link-batch-v21/shakedown/item2/population.json"
CORPUS = PROJECT / "tests/markdown_paste_corpus"
NATIVE = REPO / "findings/evidence/link-batch-v21/native/markdown-paste"
ARMS = ("m1", "m3", "m3size", "m4", "m6", "m7a", "m7b", "m8", "m9", "m10", "m11", "record", "m3bytes",
        "trace", "m5")
KEY_ACTION = {"ArrowDown": "move-line-down", "ArrowUp": "move-line-up", "ArrowRight": "move-character-right",
              "ArrowLeft": "move-character-left", "Home": "move-line-home", "End": "move-line-end"}
EMPTY = "v21-i2-empty.odt"
DIALOG_BUTTON = '#toolbar [data-action="paste-markdown"]'
MARKER = "Q"
M11_TYPED = "# 打字 ABC"                # ARMS-item2 M11-cancel, verbatim, then Backspace, ArrowLeft, Enter
M11_EXPECTED = "# 打字 A\nB"            # what those keys leave in the textarea
M9_MARKER = "M9MARK"                 # ARMS-item2 M9-dirty, verbatim
# Round 3's native click points (native/markdown-paste/round-3/README.md): the image's centre, and the frame's
# LEFT BORDER's middle line (ARMS-item2 M10c: "on the frame's left border"), not the frame's centre.
M10_CLICKS = {"image": (1985, 1985), "frame": (2002, 6803)}
M10_RECTS = {"image": [1418, 1418, 1133, 1133], "frame": [1985, 5953, 3401, 1700]}   # round 3's GRAPHIC_SELECTION
M9_CARET = (2004, 1694, 276)            # round 2 T2-sec-M2 cursorAtPaste
M9_START_LINE = (1418 + 300, 1418, 276)  # inside "Start paragraph"
# A drag starts and ends just right of the engine carets read at the two ends, inside the text the caret
# begins (ARMS-item2 M10d: "from inside A1's text to inside B1's text").  20 twips is about 1.3 px at
# 100 %, less than half of any glyph in the fixtures, so the nearest boundary is still the caret, but more
# than the pixel rounding of the pointer event (dev-r2 ended 1 twip LEFT of B1's start and selected inside
# A1 only: witness-item2 #4).
DRAG_INSET_TW = 20
FLUSH = {"fn": lambda: None}
SAVES = {"n": 0}
M3_BY_PATH: dict[str, dict] = {}   # every M3 item, also when --limit shortens M3 (development)
PASS_SHA: dict[str, str] = {}     # every M1 item's sha256, also when --limit shortens M1 (development)
BOX = """(() => { const b = document.querySelector(ARG); if (!b) return null; const r = b.getBoundingClientRect();
return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height, hidden: !!b.hidden,
         disabled: !!b.disabled }; })()"""
DIALOG_OPEN = "(() => { const d = document.querySelector('#markdown-dialog'); return !!(d && d.open); })()"
MESSAGE = """(() => { const m = document.querySelector('#markdown-message');
return m ? { hidden: m.hidden, text: m.textContent } : null; })()"""
NOTICE = """(() => { const n = document.querySelector('#notice'); const b = document.querySelector('#notice-action');
return { show: n ? n.dataset.show : null, label: b ? b.textContent : null }; })()"""
FOCUS_SINK = "document.querySelector('#sink').focus({ preventScroll: true });"
ACTIVE = "(() => document.activeElement && document.activeElement.id)()"


def type_char(session, browser: str, ch: str) -> None:
    """One trusted key for one character.  Chrome: S-4's `v21_input.key` sends a character that is not a
    letter or digit with the Windows key code of its code point, and `#` is 35, End: the keydown runs as
    End and the character is dropped (smoke R3, diag: `#` never reached the textarea).  Such a character
    goes as CDP `keyDown` with `text` and no key code instead, still a trusted key event."""
    if browser == "chrome" and not (ch.isascii() and ch.isalnum()) and ch not in inp.KEYS:
        session.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": ch, "text": ch, "unmodifiedText": ch})
        session.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": ch})
        return
    inp.key(session, browser, ch)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class StepError(RuntimeError):
    """A step could not be done as the arm says: recorded with the instance, never judged as product."""


# ------------------------------------------------------------------ inputs served from the mirror

def mirror_files(pop: dict) -> dict[str, bytes]:
    files = {}
    for path in sorted(p for p in CORPUS.rglob("*") if p.is_file()):
        files["md-corpus/" + path.relative_to(CORPUS).as_posix()] = path.read_bytes()
    for name, raw in fx.outputs().items():
        target = "md-corpus/gen/" + name if name.endswith(".md") else "v21-i2-" + name
        files[target] = raw
    files[EMPTY] = (NATIVE / "tool/inputs/empty-template.odt").read_bytes()
    for key, entry in pop["M4"]["fixtures"].items():
        raw = (REPO / key).read_bytes()
        odt = fodt_to_odt.convert(raw) if key.endswith(".fodt") else raw
        if sha256_bytes(odt) != entry["odtSha256"]:
            raise SystemExit(f"{key}: converted bytes differ from the population's pin")
        files[entry["odtName"]] = odt
    return files


# ------------------------------------------------------------------ browser and context

class RecordingChrome(pp.ChromeSession):
    """ChromeSession that keeps `Page.javascriptDialogOpening` events (the base class reads and drops every
    event): a page that opens a dialog (a beforeunload prompt, an alert) pauses its renderer, every later
    evaluate waits for its 180 s timeout, and the run learns nothing about why.  Seen in a development run."""

    def call(self, method, params=None, timeout=180, session_id=None):
        self.next_id += 1
        message_id = self.next_id
        message = {"id": message_id, "method": method, "params": params or {}}
        if session_id is not None:
            message["sessionId"] = session_id
        self.websocket.send(json.dumps(message))
        while True:
            response = json.loads(self.websocket.recv(timeout=timeout))
            if "id" not in response:
                method_name = response.get("method")
                if method_name == "Page.javascriptDialogOpening":
                    DIALOGS.append({"at": common.now_iso(), **{k: response["params"].get(k) for k in ("type", "message", "url")}})
                elif method_name == "Log.entryAdded" and response["params"]["entry"].get("level") == "error":
                    entry = response["params"]["entry"]
                    CONSOLE.append({"at": common.now_iso(), "source": entry.get("source"),
                                    "text": str(entry.get("text"))[:400], "url": str(entry.get("url") or "")[-80:]})
                elif method_name == "Runtime.exceptionThrown":
                    details = response["params"].get("exceptionDetails", {})
                    CONSOLE.append({"at": common.now_iso(), "source": "exception",
                                    "text": str((details.get("exception") or {}).get("description") or details.get("text"))[:600]})
                del CONSOLE[:-200]
                continue
            if response.get("id") != message_id:
                continue
            if "error" in response:
                raise RuntimeError(f"CDP {method}: {response['error']}")
            return response.get("result", {})


DIALOGS: list[dict] = []
ASK_MISSES: list[dict] = []       # engine-state asks that went unanswered once (then asked again)
CONSOLE: list[dict] = []          # console errors and uncaught exceptions the page reports (Chrome)


def dismiss_dialog(session, browser: str) -> dict | None:
    """Accept a JavaScript dialog if one is open (Chrome: Page.handleJavaScriptDialog; Firefox: WebDriver
    alert).  Returns what was dismissed, None when nothing was open.  The dialog itself is recorded."""
    try:
        if browser == "chrome":
            session.call("Page.handleJavaScriptDialog", {"accept": True}, timeout=10)
        else:
            text = session.command("GET", "/alert/text")
            session.command("POST", "/alert/accept", {})
            DIALOGS.append({"at": common.now_iso(), "type": "webdriver-alert", "message": text})
        return DIALOGS[-1] if DIALOGS else {"type": "unknown"}
    except Exception:  # noqa: BLE001 -- "no dialog is showing" is the ordinary answer
        return None


def navigate(session, browser: str, url: str, timeout: float = 180) -> bool:
    """Navigate, answering the page's own leave prompt if it comes (§34.4 witness: smoke/witness-item2/ #3).

    Leaving a page with unsaved work raises the page's beforeunload prompt (finding 107's guard), and a
    headless Chrome waits on it forever; a listener that stops the page's handler did not stop it
    (dev-r2).  The measurement on that page is over, so the prompt is accepted and the load records it,
    as item 1's runner does.  Firefox: WebDriver navigation accepts the prompt itself.  Returns True when
    a prompt was accepted."""
    if browser != "chrome":
        pp.navigate(session, url)
        return False
    session.next_id += 1
    nav_id = session.next_id
    session.websocket.send(json.dumps({"id": nav_id, "method": "Page.navigate", "params": {"url": url}}))
    accepted = False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        message = json.loads(session.websocket.recv(timeout=timeout))
        if message.get("method") == "Page.javascriptDialogOpening":
            DIALOGS.append({"at": common.now_iso(), "answeredBy": "navigate",
                            **{k: message["params"].get(k) for k in ("type", "message", "url")}})
            session.next_id += 1
            session.websocket.send(json.dumps({"id": session.next_id, "method": "Page.handleJavaScriptDialog",
                                               "params": {"accept": True}}))
            accepted = True
            continue
        if "id" not in message and message.get("method") in getattr(session, "KEEP", ()):
            # S-11's proxied Chrome keeps these for M5's CDP record and enables attached workers.
            session.events.append(message)
            if message["method"] == "Target.attachedToTarget":
                session._enable_attached(message["params"])
            continue
        if message.get("id") == nav_id:
            if "error" in message:
                raise RuntimeError(f"CDP Page.navigate: {message['error']}")
            break
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            if pp.evaluate(session, "(() => document.readyState === 'complete')()"):
                return accepted
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.2)
    raise StepError("the page did not finish loading")


def open_browser(browser: str, proxy_port: int | None = None, window=(1400, 1000)):
    if browser == "chrome":
        session = net.ProxiedChrome(proxy_port) if proxy_port else RecordingChrome("cold")
        if not proxy_port:
            session.call("Log.enable")
        session.call("Emulation.setDeviceMetricsOverride",
                     {"width": window[0], "height": window[1], "deviceScaleFactor": 1, "mobile": False})
        return session
    os.environ["MOZ_HEADLESS_WIDTH"] = str(window[0])
    os.environ["MOZ_HEADLESS_HEIGHT"] = str(window[1])
    prefs = dict(clip.FIREFOX_PREFS)
    if proxy_port:
        prefs.update(net.firefox_prefs(proxy_port))
    return pp.FirefoxSession("cold", extra_prefs=prefs)


class Ctx:
    def __init__(self, session, browser: str, base: str, docs: Path, identity: dict):
        self.session, self.browser, self.base, self.docs, self.identity = session, browser, base, docs, identity
        self.trace = er.Trace(session)
        self.hlog = hook.HookLog(session)
        self.ilog = obs2.Log(session)
        self.capture = None
        self.saves = 0

    def ev(self, expr):
        return pp.evaluate(self.session, expr)

    def drain(self):
        self.trace.drain()
        self.hlog.drain()
        self.ilog.drain()

    def load(self) -> dict:
        t0 = time.monotonic()
        dismissed = dismiss_dialog(self.session, self.browser)
        if dismissed is not None:
            raise StepError(f"a JavaScript dialog was open when the next instance began: {dismissed}")
        accepted = navigate(self.session, self.browser, self.base)
        boot = pp.wait_for(self.session, lambda s: s.get("state") in ("ready", "expired", "stopped"), 300)
        er.install(self.session)
        self.trace.reset(); self.hlog.reset(); self.ilog.reset()
        self.drain()
        return {"state": (boot or {}).get("state"), "seconds": round(time.monotonic() - t0, 1),
                "leaveDialogAccepted": accepted}

    def open(self, name: str, observe: bool = True) -> dict:
        opened = mws.open_fixture(self.session, f"./{name}", name)
        if not opened.get("opened"):
            raise StepError(f"{name} did not open: {opened}")
        self.drain()
        self.capture = hook.capture_check(self.session, self.hlog)
        if not self.capture.get("ok"):
            raise StepError(f"S-3 capture failed: {self.capture}")
        out = {"opened": True, "capture": self.capture}
        if observe:
            out["observed"] = self.wait_observed()
        return out

    def handle(self):
        return hook.state(self.session, self.hlog).get("documentHandle")

    def ask(self) -> dict:
        asked = er.ask_state(self.trace, self.handle())
        if not asked.get("answered"):
            # One unanswered ask lost an M3 instance in the smoke (R2): ask once more, and keep the miss.
            ASK_MISSES.append({"at": common.now_iso(), "asked": asked.get("asked")})
            asked = er.ask_state(self.trace, self.handle())
        return (asked.get("result") or {}) if asked.get("answered") and asked.get("ok") else {"unanswered": asked}

    def rev(self):
        return self.ask().get("rev")

    def wait_observed(self, cap: float = 10.0) -> dict:
        t0 = time.monotonic()
        while time.monotonic() - t0 < cap:
            result = self.ask()
            if (result.get("sel") or {}).get("observed") is True:
                return {"observed": True, "afterMs": round((time.monotonic() - t0) * 1000)}
            time.sleep(0.4)
        return {"observed": False, "afterMs": round((time.monotonic() - t0) * 1000)}

    def state(self) -> dict:
        return hook.state(self.session, self.hlog)

    def quiet(self, limit: float = 60) -> dict:
        state = mws.quiet(self.session, limit)
        self.drain()
        return state

    def save(self, label: str) -> dict:
        raw = er.save(self.session)
        self.drain()
        if raw is None:
            return {"saved": False}
        SAVES["n"] += 1
        path = self.docs / f"{SAVES['n']:05d}-{re.sub(r'[^A-Za-z0-9_.+-]', '_', label)}.odt"
        if path.exists():
            raise SystemExit(f"refusing to overwrite a kept document: {path}")
        path.write_bytes(raw)
        return {"saved": True, "file": path.relative_to(self.docs.parent).as_posix(), "sha256": sha256_bytes(raw),
                "bytes": len(raw), "raw": raw}

    def mark(self) -> int:
        self.drain()
        return len(self.ilog.all)

    def wait_rs(self, mark: int, predicate, limit: float = 20.0) -> dict | None:
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            self.ilog.drain()
            hit = next((e for e in self.ilog.all[mark:] if e.get("k") == "rs" and predicate(e)), None)
            if hit:
                return hit
            time.sleep(0.05)
        return None

    def requests_since(self, mark: int) -> list[dict]:
        self.drain()
        return [{"op": e.get("op"), "action": e.get("action"), "rewritten": e.get("rewritten")}
                for e in self.ilog.all[mark:] if e.get("k") == "rq"]

    def focus_sink(self) -> None:
        r7_support.run_in_page(self.session, FOCUS_SINK)
        time.sleep(0.1)

    def key(self, name: str, mods=()) -> None:
        inp.key(self.session, self.browser, name, mods)

    def move(self, name: str) -> dict:
        mark = self.mark()
        self.key(name)
        action = KEY_ACTION[name]
        hit = self.wait_rs(mark, lambda e: e.get("op") == "editorActionV2" and e.get("action") == action)
        if hit is None or not hit.get("ok"):
            raise StepError(f"{name}: no successful {action}: {hit}")
        return hit

    def type_text(self, text: str) -> dict:
        self.focus_sink()
        mark = self.mark()
        for ch in text:
            type_char(self.session, self.browser, ch)
            time.sleep(0.05)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            self.ilog.drain()
            done = [e for e in self.ilog.all[mark:] if e.get("k") == "rs" and e.get("op") == "insertText"]
            if len(done) >= len(text):
                break
            time.sleep(0.1)
        self.quiet()
        return {"insertTexts": len([e for e in self.ilog.all[mark:] if e.get("k") == "rs" and e.get("op") == "insertText"]),
                "ok": all(e.get("ok") for e in self.ilog.all[mark:] if e.get("k") == "rs" and e.get("op") == "insertText")}

    def ctrl_z(self) -> dict:
        self.focus_sink()
        mark = self.mark()
        self.key("z", ("ctrl",))
        hit = self.wait_rs(mark, lambda e: e.get("op") == "undo", 20)
        self.quiet()
        return {"response": hit}

    def size(self) -> dict:
        seen = mws.obs(self.session) or {}
        size = seen.get("size") or {}
        if size.get("generation") != seen.get("workers") or not size.get("w"):
            raise StepError(f"no document size from the current worker: {size}")
        return size

    def click_twips(self, x: float, y: float) -> dict:
        mark = self.mark()
        px, py = inp.paper_point(self.session, pp.evaluate, x, y, 0, self.size())
        inp.click(self.session, self.browser, px, py)
        hit = self.wait_rs(mark, lambda e: e.get("op") in ("editorPlaceCaretV2", "click"), 15)
        self.quiet()
        return {"twips": [x, y], "point": [round(px, 1), round(py, 1)], "response": hit}

    def drag_twips(self, a: tuple, b: tuple) -> dict:
        mark = self.mark()
        size = self.size()
        pa = inp.paper_point(self.session, pp.evaluate, a[0], a[1], 0, size)
        pb = inp.paper_point(self.session, pp.evaluate, b[0], b[1], 0, size)
        inp.drag(self.session, self.browser, pa, pb)
        hit = self.wait_rs(mark, lambda e: e.get("op") == "editorSelectRangeV2", 15)
        time.sleep(0.4)
        self.quiet()
        return {"from": [round(v, 1) for v in pa], "to": [round(v, 1) for v in pb], "response": hit}

    def real_click(self, selector: str) -> dict:
        box = self.ev(BOX.replace("ARG", json.dumps(selector)))
        if not box or box["w"] == 0 or box["hidden"]:
            return {"clicked": False, "box": box}
        inp.click(self.session, self.browser, box["x"], box["y"])
        return {"clicked": True, "box": {k: box[k] for k in ("x", "y", "disabled")}}

    # -- the routes
    def dialog(self, text_url: str | None, expected_sha: str | None, timeout: float = 60) -> dict:
        """R-dialog: real click, real clipboard + trusted Ctrl+V into the textarea, read back, real 插入."""
        mark = self.mark()
        hmark = len(self.hlog.all)
        out = {"route": "dialog", "button": self.real_click(DIALOG_BUTTON)}
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not self.ev(DIALOG_OPEN):
            time.sleep(0.1)
        out["dialogOpen"] = bool(self.ev(DIALOG_OPEN))
        if not out["dialogOpen"]:
            raise StepError(f"the dialog did not open: {out['button']}")
        out["focus"] = self.ev(ACTIVE)
        if text_url is not None:
            out["clipboard"] = clip.write_from_url(self.session, text_url)
            if self.ev(ACTIVE) != "markdown-text":
                r7_support.run_in_page(self.session, "document.querySelector('#markdown-text').focus();")
                out["refocused"] = True
            clip.press_ctrl_v(self.session, self.browser)
            time.sleep(0.4)
        out["readback"] = clip.readback(self.session, "#markdown-text")
        out["inputIntact"] = (out["readback"].get("sha256") == expected_sha) if expected_sha else None
        out["insertMark"] = self.mark()                 # ilog index (this load) just before the 插入 click
        out["insertClickPageT"] = self.ev("(() => performance.now())()")
        t_click = time.monotonic()
        out["insert"] = self.real_click("#markdown-insert")
        outcome = None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.drain()
            paste = next((e for e in self.hlog.all[hmark:] if e.get("k") == "paste"), None)
            if paste is None:
                message = self.ev(MESSAGE) or {}
                if message and not message.get("hidden") and message.get("text"):
                    # The page shows a session refusal's text too, and the hook writes its log into the DOM on
                    # a timer, so the message can be visible before the hook's entry is (smoke R1): give the
                    # hook 1.5 s before calling this the page's own refusal.
                    settle = time.monotonic() + 1.5
                    while paste is None and time.monotonic() < settle:
                        time.sleep(0.1)
                        self.drain()
                        paste = next((e for e in self.hlog.all[hmark:] if e.get("k") == "paste"), None)
                    if paste is None:
                        outcome = {"kind": "page-refusal", "message": message}
                        break
            if paste is not None:
                outcome = {"kind": "session", "entry": paste}
                break
            time.sleep(0.1)
        out["clickToOutcomeS"] = round(time.monotonic() - t_click, 3)
        out["outcome"] = outcome
        time.sleep(0.3)
        out["message"] = self.ev(MESSAGE)
        out["notice"] = self.ev(NOTICE)
        out["dialogOpenAfter"] = bool(self.ev(DIALOG_OPEN))
        if out["dialogOpenAfter"]:
            # Spec 12.2 (d): on a refusal the page keeps the text; read it before closing the dialog.
            out["readbackAfter"] = clip.readback(self.session, "#markdown-text")
            out["cancel"] = self.real_click("#markdown-cancel")
            time.sleep(0.3)
        self.quiet()
        out["requests"] = self.requests_since(mark)
        out["responses"] = [{k: e.get(k) for k in ("op", "ok", "code", "dispatched", "revision", "limitBytes", "message", "t")}
                            for e in self.ilog.all[mark:] if e.get("k") == "rs" and e.get("op") in ("pasteMarkdown", "save")]
        out["pasteRequestT"] = [e.get("t") for e in self.ilog.all[mark:] if e.get("k") == "rq" and e.get("op") == "pasteMarkdown"]
        out["pills"] = [(e.get("state"), e.get("t")) for e in self.ilog.all[mark:] if e.get("k") == "pill"]
        out["ui"] = [{k: e.get(k) for k in ("what", "show", "open", "hidden", "text", "t") if k in e}
                     for e in self.ilog.all[mark:] if e.get("k") == "ui"]
        return out

    def sdk(self, text_url: str, timeout: float = 60) -> dict:
        """R-sdk: the page's own DocumentHandle (S-3)."""
        mark = self.mark()
        answer = hook.call(self.session, self.hlog, "document", "pasteMarkdown", text_url=text_url, timeout=timeout)
        self.quiet()
        return {"route": "sdk", "answer": {k: answer.get(k) for k in ("answered", "ok", "error", "value", "ms")},
                "requests": self.requests_since(mark),
                "responses": [{k: e.get(k) for k in ("op", "ok", "code", "dispatched", "revision", "limitBytes", "message")}
                              for e in self.ilog.all[mark:] if e.get("k") == "rs" and e.get("op") == "pasteMarkdown"]}

    def worker(self, operation: str, text_url: str | None = None, bytes_url: str | None = None,
               timeout: float = 60) -> dict:
        """R-worker / R-bytes: a raw message to the page's worker (the item-2 observer's ask)."""
        answer = obs2.ask(self.session, self.ilog, operation, {"documentHandle": self.handle()},
                          text_url=text_url, bytes_url=bytes_url, timeout=timeout)
        self.quiet()
        entry = answer.get("entry") or {}
        return {"route": "worker" if text_url else "bytes", "operation": operation, "answered": answer["answered"],
                "posted": answer["posted"], "response": {k: entry.get(k) for k in
                                                          ("ok", "code", "dispatched", "operation", "revision", "limitBytes", "message", "error")}}


def doc_compare(a: dict, b_raw: bytes | None, label: str) -> dict:
    if not a.get("saved") or b_raw is None:
        return {"compared": False, "why": f"{label}: a document is missing"}
    try:
        result = cmp.compare(a["raw"], b_raw)
    except Exception as error:  # noqa: BLE001
        return {"compared": False, "why": f"{type(error).__name__}: {error}"[:300]}
    return {"compared": True, **result}


def strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "raw"}


def native_bytes(rel_path: str) -> bytes:
    raw = (REPO / rel_path).read_bytes()
    return gzip.decompress(raw) if rel_path.endswith(".gz") else raw


def url_of(path: str) -> str:
    return "./md-corpus/" + path


# ------------------------------------------------------------------ arms (main page)

def arm_m1(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    out["instances"] = []
    for k in range(1, rounds + 1):
        for item in pop["M1"]:
            rec = {"round": k, "item": item["path"], "sha256": item["sha256"]}
            out["instances"].append(rec)
            try:
                ctx.load()
                mark = ctx.mark()                # M10a: from the open, not after it
                rec["open"] = ctx.open(EMPTY)
                asked = ctx.ask()                # ARMS M1 step 2: caret, selectionType, revision
                rec["before"] = {"rev": asked.get("rev"), "caret": asked.get("caret"), "selectionType": asked.get("selectionType"),
                                 "state": {k2: ctx.state().get(k2) for k2 in ("dirty", "enqueueCount")}}
                ctx.drain()
                observed = [e for e in ctx.trace.all if e.get("k") == "ev" and isinstance(e.get("sel"), dict)]
                rec["lastSelectionObserved"] = observed[-1]["sel"].get("observed") if observed else None
                rec["dialog"] = ctx.dialog(url_of(item["path"]), item["sha256"])
                rec["paperEventsBeforePaste"] = [r for r in ctx.requests_since(mark)
                                                 if r["op"] in ("editorPlaceCaretV2", "editorSelectRangeV2", "click")]
                rec["after"] = {"rev": ctx.rev()}
                saved = ctx.save(f"m1-{k}-{Path(item['path']).stem}")
                rec["saved"] = strip(saved)
                ref = native_bytes(item["reference"]["afterRuns"][0]["path"])
                rec["compare"] = doc_compare(saved, ref, "native reference")
                if item["path"] == "round-1/M8.md" and saved.get("saved"):
                    rec["texts"] = cmp.paragraph_texts(saved["raw"])
                rec["navigatorLanguage"] = ctx.ev("(() => navigator.language)()")
            except StepError as error:
                rec["runnerError"] = str(error)
            except Exception as error:  # noqa: BLE001
                rec["runnerError"] = f"{type(error).__name__}: {error}"
                rec["traceback"] = traceback.format_exc()[-1500:]
            FLUSH["fn"]()


def undo_probe_setup(ctx: Ctx, rec: dict) -> dict:
    """DM-9 C: S0, then one marker (one insertText, revision +1), then S_m."""
    rec["s0"] = strip(s0 := ctx.save("s0"))
    rec["r0"] = ctx.rev()
    rec["marker"] = ctx.type_text(MARKER)
    rec["rMarker"] = ctx.rev()
    rec["sMarker"] = strip(sm := ctx.save("s-marker"))
    return {"s0": s0, "sm": sm}


def undo_probe_finish(ctx: Ctx, rec: dict, docs: dict) -> None:
    rec["rAfter"] = ctx.rev()
    rec["s1"] = strip(s1 := ctx.save("s1"))
    rec["s1EqualsMarker"] = doc_compare(s1, docs["sm"].get("raw"), "S_m")
    rec["undo"] = ctx.ctrl_z()
    rec["rUndo"] = ctx.rev()
    rec["s2"] = strip(s2 := ctx.save("s2"))
    rec["s2EqualsS0"] = doc_compare(s2, docs["s0"].get("raw"), "S0")


def arm_m3(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    out["instances"], out["positiveControls"] = [], []
    for k in range(1, rounds + 1):
        for route in ("dialog", "sdk"):
            pc = {"round": k, "route": route}
            out["positiveControls"].append(pc)
            try:
                ctx.load(); ctx.open(EMPTY)
                docs = undo_probe_setup(ctx, pc)
                m2 = pop["M3"]["positiveControl"]
                pc["paste"] = (ctx.dialog(url_of(m2["path"]), m2["sha256"]) if route == "dialog"
                               else ctx.sdk(url_of(m2["path"])))
                if route == "sdk":
                    ctx.focus_sink()
                undo_probe_finish(ctx, pc, docs)
                pc["s2EqualsMarker"] = doc_compare({"saved": True, "raw": (ctx.docs.parent / pc["s2"]["file"]).read_bytes()}
                                                   if pc["s2"].get("saved") else {}, docs["sm"].get("raw"), "S_m")
            except Exception as error:  # noqa: BLE001
                pc["runnerError"] = f"{type(error).__name__}: {error}"
            FLUSH["fn"]()
            for item in pop["M3"]["items"]:
                if route not in item["routes"]:
                    continue
                rec = {"round": k, "route": route, "item": item["path"], "sha256": item["sha256"],
                       "expectedCode": item["expectedCode"], "expectedLayer": item["layerOnDialogAndSdk"]}
                out["instances"].append(rec)
                try:
                    ctx.load(); ctx.open(EMPTY)
                    docs = undo_probe_setup(ctx, rec)
                    expected_sha = item["sha256"] if item["bytes"] else None
                    rec["attempt"] = (ctx.dialog(url_of(item["path"]) if item["bytes"] else None, expected_sha)
                                      if route == "dialog" else ctx.sdk(url_of(item["path"])))
                    undo_probe_finish(ctx, rec, docs)
                except Exception as error:  # noqa: BLE001
                    rec["runnerError"] = f"{type(error).__name__}: {error}"
                FLUSH["fn"]()


def arm_m3size(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    out["instances"] = []
    for k in range(1, rounds + 1):
        for arm in pop["M3"]["sizeArms"]:
            rec = {"round": k, **arm}
            out["instances"].append(rec)
            try:
                ctx.load(); ctx.open(EMPTY)
                rec["r0"] = ctx.rev()
                url = "./md-corpus/gen/" + arm["corpusFile"]
                rec["attempt"] = ctx.sdk(url) if arm["route"] == "sdk" else ctx.worker("pasteMarkdown", text_url=url)
                rec["r1"] = ctx.rev()
            except Exception as error:  # noqa: BLE001
                rec["runnerError"] = f"{type(error).__name__}: {error}"
            FLUSH["fn"]()


def place_keys(ctx: Ctx, keys: list[str]) -> list[dict]:
    ctx.focus_sink()
    return [{"key": key, "ok": (ctx.move(key) or {}).get("ok")} for key in keys]


def arm_m4(ctx: Ctx, pop: dict, rounds: int, out: dict, only: set | None = None) -> None:
    out["instances"] = []
    fixtures = pop["M4"]["fixtures"]
    for k in range(1, rounds + 1):
        for inst in pop["M4"]["instances"]:
            if only and inst["id"] not in only:
                continue
            rec = {"round": k, "id": inst["id"], "class": inst["class"], "corpus": inst["corpus"]}
            out["instances"].append(rec)
            try:
                fixture = fixtures[inst["fixture"]]
                ctx.load(); rec["open"] = ctx.open(fixture["odtName"])
                rec["R"] = strip(r := ctx.save("m4-R"))
                rec["loadEqualsNative"] = doc_compare(r, native_bytes(inst["nativeBefore"]), "native before")
                ctx.focus_sink()
                for c in inst.get("clicks", []):
                    rec.setdefault("clicks", []).append(ctx.click_twips(c["x"], c["y"]))
                corpus = {"path": inst["corpus"], "sha256": PASS_SHA[inst["corpus"]]}
                if inst["class"] == "range":
                    rec["startKeys"] = place_keys(ctx, inst["startKeys"])
                    a = ctx.ask().get("caret") or {}
                    rec["endKeys"] = place_keys(ctx, inst["endKeys"][len(inst["startKeys"]):])
                    b = ctx.ask().get("caret") or {}
                    rec["drag"] = ctx.drag_twips((a["x"] + DRAG_INSET_TW, a["y"] + a["height"] / 2), (b["x"] + DRAG_INSET_TW, b["y"] + b["height"] / 2))
                    rec["selectionType"] = ctx.ask().get("selectionType")
                    rec["selectionText"] = selection_text(ctx)
                    rec["r0"] = ctx.rev()
                    rec["dialog"] = ctx.dialog(url_of(inst["corpus"]), corpus["sha256"])
                    rec["sdk"] = ctx.sdk(url_of(inst["corpus"]))
                    rec["r1"] = ctx.rev()
                    rec["S1"] = strip(s1 := ctx.save("m4-S1"))
                    rec["s1EqualsR"] = doc_compare(s1, r.get("raw"), "R")
                    continue
                rec["keys"] = place_keys(ctx, inst.get("keys", []))
                rec["caret"] = ctx.ask().get("caret")
                rec["r0"] = ctx.rev()
                rec["dialog"] = ctx.dialog(url_of(inst["corpus"]), corpus["sha256"])
                if inst["class"] == "protected":
                    rec["notice"] = ctx.ev(NOTICE)
                    rec["noticeClick"] = ctx.real_click("#notice-action")
                    rec["afterRollback"] = ctx.quiet(90)
                    rec["S"] = strip(s := ctx.save("m4-S"))
                    rec["sEqualsR"] = doc_compare(s, r.get("raw"), "R")
                    continue
                rec["S1"] = strip(s1 := ctx.save("m4-S1"))
                if "afterEqualsNative" in inst["confirm"]:
                    rec["afterEqualsNative"] = doc_compare(s1, native_bytes(inst["confirm"]["afterEqualsNative"]), "native after")
                rec["undo"] = ctx.ctrl_z()
                rec["S2"] = strip(s2 := ctx.save("m4-S2"))
                rec["s2EqualsR"] = doc_compare(s2, r.get("raw"), "R")
            except Exception as error:  # noqa: BLE001
                rec["runnerError"] = f"{type(error).__name__}: {error}"
            FLUSH["fn"]()


def selection_text(ctx: Ctx) -> str | None:
    """The selected text as the engine reads it: v20's observer keeps only selectionType, so ask through
    the page's own DocumentHandle (S-3): getSelection -> {selectionType, text, revision}."""
    answer = hook.call(ctx.session, ctx.hlog, "document", "getSelection", timeout=15)
    value = answer.get("value") if answer.get("ok") else None
    return value.get("text") if isinstance(value, dict) else None


def arm_m6(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    out["instances"] = []
    limit = pop["M3"]["limitL"]
    corpus = f"m6-{limit}.md"
    raw = fx.m6_corpus(limit)[0]
    for k in range(1, rounds + 1):
        rec = {"round": k, "corpus": corpus, "sha256": sha256_bytes(raw), "bytes": len(raw)}
        out["instances"].append(rec)
        try:
            ctx.load(); ctx.open(EMPTY)
            rec["R"] = strip(r := ctx.save("m6-R"))
            rec["foreignCpu"] = common.foreign_cpu()
            mark = ctx.mark()
            rec["dialog"] = ctx.dialog("./md-corpus/gen/" + corpus, sha256_bytes(raw), timeout=180)
            after_click = ctx.ilog.all[rec["dialog"]["insertMark"]:]
            pills = [e for e in after_click if e.get("k") == "pill"]
            busy = next((e for e in pills if e.get("state") == "busy"), None)
            ready = next((e for e in pills if busy and e.get("s", 0) > busy["s"] and e.get("state") == "ready"), None)
            rec["busyToReadyMs"] = round(ready["t"] - busy["t"], 1) if busy and ready else None
            ended = next((e for e in pills if busy and e.get("s", 0) > busy["s"] and e.get("state") != "busy"), None)
            rec["busySpanMs"] = round(ended["t"] - busy["t"], 1) if busy and ended else None
            rec["busyEndState"] = ended.get("state") if ended else None
            click_t = rec["dialog"].get("insertClickPageT")
            rec["clickToReadyMs"] = round(ready["t"] - click_t, 1) if ready and isinstance(click_t, (int, float)) else None
            rq = next((e for e in after_click if e.get("k") == "rq" and e.get("op") == "pasteMarkdown"), None)
            rs = next((e for e in after_click if e.get("k") == "rs" and e.get("op") == "pasteMarkdown"), None)
            rec["replyMs"] = round(rs["t"] - rq["t"], 1) if rq and rs else None
            rec["pills"] = [(e.get("state"), e.get("t")) for e in pills]
            rec["S1"] = strip(s1 := ctx.save("m6-S1"))
            rec["s1EqualsR"] = doc_compare(s1, r.get("raw"), "R")      # the paste changed the document
            rec["undo"] = ctx.ctrl_z()
            rec["S2"] = strip(s2 := ctx.save("m6-S2"))
            rec["s2EqualsR"] = doc_compare(s2, r.get("raw"), "R")
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()


def arm_m7a(ctx: Ctx, rounds: int, out: dict) -> None:
    out["instances"] = []
    for k in range(1, rounds + 1):
        rec = {"round": k}
        out["instances"].append(rec)
        try:
            ctx.load()                       # the boot document, list-contexts.odt
            rec["doc"] = (pp.evaluate(ctx.session, pp.READ_STATE) or {}).get("doc")
            pp.evaluate(ctx.session, pp.POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
            pp.wait_for(ctx.session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
            pp.evaluate(ctx.session, pp.CLEAR_TOAST)
            before = pp.revision_of(pp.evaluate(ctx.session, pp.READ_STATE))
            result = pp.evaluate(ctx.session, pp.PASTE.replace("ARG_TEXT", pp.PASTE_MARK))
            after = pp.wait_for(ctx.session, lambda s, f=before: pp.revision_of(s) is not None and f is not None
                                and pp.revision_of(s) > f, 20)
            rec.update({"payloadSurvived": bool((result or {}).get("payloadSurvived")),
                        "shimmed": (result or {}).get("shimmed"), "revisionBefore": before,
                        "revisionAfter": pp.revision_of(after) if after else None})
            saved = ctx.save("m7a")
            report = pp.zip_report(saved["raw"]) if saved.get("saved") else {}
            rec["saved"] = strip(saved)
            rec["isAnOdt"] = pp.is_an_odt(report)
            rec["markOccurrences"] = (report.get("content") or "").count(pp.PASTE_MARK)
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()


def arm_m7b(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    out["instances"] = []
    ref = NATIVE / "out/P1-C1-plain/run1/after.fodt.gz"
    c1 = next(i for i in pop["M1"] if i["path"] == "round-1/C1.md")
    for k in range(1, rounds + 1):
        rec = {"round": k, "reference": ref.relative_to(REPO).as_posix()}
        out["instances"].append(rec)
        try:
            ctx.load(); ctx.open(EMPTY)
            caret = ctx.ask().get("caret") or {}
            rec["click"] = ctx.click_twips(caret.get("x", 1418) + 1, caret.get("y", 1418) + caret.get("height", 276) / 2)
            rec["focus"] = ctx.ev(ACTIVE)
            rec["clipboard"] = clip.write_from_url(ctx.session, url_of("round-1/C1.md"))
            ctx.focus_sink()
            rec["r0"] = ctx.rev()
            mark = ctx.mark()
            clip.press_ctrl_v(ctx.session, ctx.browser)
            rec["insertText"] = ctx.wait_rs(mark, lambda e: e.get("op") == "insertText", 20)
            ctx.quiet()
            rec["r1"] = ctx.rev()
            rec["pasteEvents"] = len([e for e in ctx.ilog.all[mark:] if e.get("k") == "rq" and e.get("op") == "insertText"])
            rec["S1"] = strip(s1 := ctx.save("m7b"))
            rec["compare"] = doc_compare(s1, gzip.decompress(ref.read_bytes()), "native C1 text/plain")
            rec["clipboardSha"] = rec["clipboard"].get("sha256") == c1["sha256"]
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()


def arm_m8_page(ctx: Ctx, rounds: int, out: dict, which: str) -> None:
    out.setdefault("instances", [])
    m2 = "./md-corpus/round-1/M2.md"
    for k in range(1, rounds + 1):
        rec = {"round": k, "page": which}
        out["instances"].append(rec)
        try:
            ctx.load(); ctx.open(EMPTY)
            rec["button"] = ctx.ev(BOX.replace("ARG", json.dumps(DIALOG_BUTTON)))
            mark = ctx.mark()
            if which == "v20":
                rec["sdk"] = ctx.sdk(m2)
                rec["requestsAfterSdk"] = ctx.requests_since(mark)
            rec["worker"] = ctx.worker("pasteMarkdown", text_url=m2)
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()


def fixture_odt(pop: dict, basename: str) -> str:
    """The served name of the M4 fixture whose source file is exactly `basename` (header-protected-section.fodt
    also ends in protected-section.fodt: a suffix match picked it in a development run)."""
    found = [entry["odtName"] for key, entry in pop["M4"]["fixtures"].items() if Path(key).name == basename]
    if len(found) != 1:
        raise StepError(f"{len(found)} fixtures named {basename}")
    return found[0]


def m9_place(ctx: Ctx, rec: dict) -> None:
    rec["placeClick"] = ctx.click_twips(M9_CARET[0], M9_CARET[1] + M9_CARET[2] / 2)
    rec["caret"] = ctx.ask().get("caret")


def arm_m9(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    name = fixture_odt(pop, "protected-section.fodt")
    m2 = next(i for i in pop["M1"] if i["path"] == "round-1/M2.md")
    out.update({"clean": [], "dirty": [], "inject": [], "positiveControl": []})
    for k in range(1, rounds + 1):
        for sub in ("positiveControl", "clean", "dirty", "inject"):
            rec = {"round": k}
            out[sub].append(rec)
            try:
                ctx.load(); rec["open"] = ctx.open(name)
                if sub == "positiveControl":
                    rec["click"] = ctx.click_twips(M9_START_LINE[0], M9_START_LINE[1] + M9_START_LINE[2] / 2)
                    rec["caret"] = ctx.ask().get("caret")
                    rec["dialog"] = ctx.dialog(url_of(m2["path"]), m2["sha256"])
                    continue
                if sub == "clean":
                    rec["R"] = strip(r := ctx.save("m9-R"))
                    ctx.load(); ctx.open(name)
                else:
                    rec["startClick"] = ctx.click_twips(M9_START_LINE[0], M9_START_LINE[1] + M9_START_LINE[2] / 2)
                    ctx.focus_sink()
                    rec["end"] = ctx.move("End")
                    rec["typed"] = ctx.type_text(M9_MARKER)
                    rec["afterTyping"] = ctx.state()
                    rec["rAfterTyping"] = ctx.rev()
                # The window starts right after the marker is typed (ARMS M9-dirty: the bank may come from the
                # paste's own checkpoint or from an earlier step), so the placement's requests are in it.
                mark = ctx.mark()
                if sub == "inject":
                    obs2.set_rewrite(ctx.session, True)
                m9_place(ctx, rec)
                rec["r0"] = ctx.rev()
                rec["dialog"] = ctx.dialog(url_of(m2["path"]), m2["sha256"])
                if sub == "inject":
                    obs2.set_rewrite(ctx.session, False)
                    rec["requests"] = ctx.requests_since(mark)
                    rec["saveResponses"] = [{k2: e.get(k2) for k2 in ("ok", "code")} for e in ctx.ilog.all[mark:]
                                            if e.get("k") == "rs" and e.get("op") == "save"]
                    rec["checkpointText"] = (pp.evaluate(ctx.session, pp.READ_STATE) or {}).get("checkpoint")
                    rec["state"] = ctx.state()
                    rec["rev"] = ctx.rev()
                    continue
                rec["requestsToPaste"] = ctx.requests_since(mark)
                rec["checkpointText"] = (pp.evaluate(ctx.session, pp.READ_STATE) or {}).get("checkpoint")
                rec["notice"] = ctx.ev(NOTICE)
                rec["noticeClick"] = ctx.real_click("#notice-action")
                rec["afterRollback"] = ctx.quiet(90)
                rec["S"] = strip(s := ctx.save("m9-S"))
                if sub == "clean":
                    rec["sEqualsR"] = doc_compare(s, r.get("raw"), "R")
                elif s.get("saved"):
                    texts = cmp.paragraph_texts(s["raw"])
                    rec["texts"] = texts
                    rec["markerCount"] = sum(t.count(M9_MARKER) for t in texts)
                    rec["m2Present"] = any("inline code" in t for t in texts)
            except Exception as error:  # noqa: BLE001
                rec["runnerError"] = f"{type(error).__name__}: {error}"
                try:
                    obs2.set_rewrite(ctx.session, False)
                except Exception:  # noqa: BLE001
                    pass
            FLUSH["fn"]()


def arm_m10(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    m2 = next(i for i in pop["M1"] if i["path"] == "round-1/M2.md")
    cells = fixture_odt(pop, "cells.fodt")
    p11 = next(i for i in pop["M4"]["instances"] if i["id"] == "M4-T1-P11-M1")
    out.update({"b": [], "c": [], "d": []})
    for k in range(1, rounds + 1):
        for sub, target in (("b", "image"), ("c", "frame")):
            rec = {"round": k, "click": M10_CLICKS[target]}
            out[sub].append(rec)
            try:
                ctx.load(); ctx.open("v21-i2-m10-selectables.odt")
                rec["R"] = strip(r := ctx.save("m10-R"))
                rec["clicked"] = ctx.click_twips(*M10_CLICKS[target])
                rec["askAfterClick"] = {k2: ctx.ask().get(k2) for k2 in ("selectionType", "sel", "caret")}
                rec["r0"] = ctx.rev()
                rec["dialog"] = ctx.dialog(url_of(m2["path"]), m2["sha256"])
                rec["r1"] = ctx.rev()
                rec["S"] = strip(s := ctx.save("m10-S"))
                rec["sEqualsR"] = doc_compare(s, r.get("raw"), "R")
            except Exception as error:  # noqa: BLE001
                rec["runnerError"] = f"{type(error).__name__}: {error}"
            FLUSH["fn"]()
        rec = {"round": k}
        out["d"].append(rec)
        try:
            ctx.load(); ctx.open(cells)
            rec["R"] = strip(r := ctx.save("m10d-R"))
            rec["startKeys"] = place_keys(ctx, p11["startKeys"])
            a = ctx.ask().get("caret") or {}
            rec["endKeys"] = place_keys(ctx, p11["endKeys"][len(p11["startKeys"]):])
            b = ctx.ask().get("caret") or {}
            rec["drag"] = ctx.drag_twips((a["x"] + DRAG_INSET_TW, a["y"] + a["height"] / 2), (b["x"] + DRAG_INSET_TW, b["y"] + b["height"] / 2))
            rec["selectionType"] = ctx.ask().get("selectionType")
            rec["selectionText"] = selection_text(ctx)
            rec["r0"] = ctx.rev()
            rec["dialog"] = ctx.dialog(url_of(m2["path"]), m2["sha256"])
            rec["sdk"] = ctx.sdk(url_of(m2["path"]))
            rec["r1"] = ctx.rev()
            rec["S"] = strip(s := ctx.save("m10d-S"))
            rec["sEqualsR"] = doc_compare(s, r.get("raw"), "R")
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()


def arm_m11(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    m2 = next(i for i in pop["M1"] if i["path"] == "round-1/M2.md")
    out.update({"dirty": [], "cancel": [], "autosave": {"notRun": "a host arm (ARMS-item2.md M11, DM-18 A): runs "
                                                                   "on host 0.2.25 after the v74 freeze"}})
    for k in range(1, rounds + 1):
        rec = {"round": k}
        out["dirty"].append(rec)
        try:
            ctx.load(); ctx.open(EMPTY)
            rec["before"] = {k2: ctx.state().get(k2) for k2 in ("dirty", "hasUnsavedEdits", "revision")}
            rec["dialog"] = ctx.dialog(url_of(m2["path"]), m2["sha256"])
            rec["after"] = {k2: ctx.state().get(k2) for k2 in ("dirty", "hasUnsavedEdits", "revision")}
            rec["rev"] = ctx.rev()
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()
        rec = {"round": k, "episodes": []}
        out["cancel"].append(rec)
        try:
            ctx.load(); ctx.open(EMPTY)
            rec["S0"] = strip(s0 := ctx.save("m11-S0"))
            rec["e0"] = ctx.state().get("enqueueCount")
            rec["r0"] = ctx.rev()
            for how in ("cancel", "escape"):
                ep = {"how": how}
                mark = ctx.mark()
                ep["button"] = ctx.real_click(DIALOG_BUTTON)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline and not (ctx.ev(DIALOG_OPEN) and ctx.ev(ACTIVE) == "markdown-text"):
                    time.sleep(0.1)
                ep["dialogOpen"] = bool(ctx.ev(DIALOG_OPEN))
                ep["focusBeforeTyping"] = ctx.ev(ACTIVE)      # smoke R3: keys sent before the focus were lost
                for ch in M11_TYPED:
                    type_char(ctx.session, ctx.browser, ch)
                for name in ("Backspace", "ArrowLeft", "Enter"):
                    inp.key(ctx.session, ctx.browser, name)
                time.sleep(0.3)
                ep["textareaBefore"] = clip.readback(ctx.session, "#markdown-text")
                ep["typedAsArm"] = ep["textareaBefore"].get("sha256") == sha256_bytes(M11_EXPECTED.encode("utf-8"))
                if how == "cancel":
                    ep["close"] = ctx.real_click("#markdown-cancel")
                else:
                    inp.key(ctx.session, ctx.browser, "Escape")
                time.sleep(0.5)
                ctx.quiet()
                ep["dialogOpenAfter"] = bool(ctx.ev(DIALOG_OPEN))
                ep["textareaAfter"] = clip.readback(ctx.session, "#markdown-text")
                ep["requests"] = ctx.requests_since(mark)
                ep["enqueueCount"] = ctx.state().get("enqueueCount")
                rec["episodes"].append(ep)
            rec["r1"] = ctx.rev()
            rec["S1"] = strip(s1 := ctx.save("m11-S1"))
            rec["s1EqualsS0"] = doc_compare(s1, s0.get("raw"), "S0")
            mark = ctx.mark()
            rec["control"] = ctx.type_text("x")
            rec["controlRequests"] = ctx.requests_since(mark)
            rec["r2"] = ctx.rev()
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()


CHECKBOX = re.compile(r'loext:checked="(true|false)"')


def arm_record(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    x11 = next(i for i in pop["M1"] if i["path"] == "m0/X11-task-list.md")
    out["instances"] = []
    for k in range(1, rounds + 1):
        rec = {"round": k}
        out["instances"].append(rec)
        try:
            ctx.load(); ctx.open(EMPTY)
            rec["dialog"] = ctx.dialog(url_of(x11["path"]), x11["sha256"])
            rec["S1"] = strip(s1 := ctx.save("record-S1"))
            rec["afterSave"] = {k2: ctx.state().get(k2) for k2 in ("dirty", "hasUnsavedEdits", "revision")}
            rec["keys"] = place_keys(ctx, ["ArrowUp", "ArrowUp", "ArrowUp", "Home"])
            caret = ctx.ask().get("caret") or {}
            rec["caret"] = caret
            rec["rBefore"] = ctx.rev()
            rec["click"] = ctx.click_twips(caret.get("x", 0) + 100, caret.get("y", 0) + caret.get("height", 276) / 2)
            time.sleep(1.0)
            rec["rAfter"] = ctx.rev()
            rec["afterClick"] = {k2: ctx.state().get(k2) for k2 in ("dirty", "hasUnsavedEdits", "revision")}
            rec["S2"] = strip(s2 := ctx.save("record-S2"))
            for name, doc in (("S1", s1), ("S2", s2)):
                if doc.get("saved"):
                    with zipfile.ZipFile(io.BytesIO(doc["raw"])) as archive:
                        content = archive.read("content.xml").decode("utf-8", "replace")
                    rec[name + "Checked"] = CHECKBOX.findall(content)
                    rec[name + "Glyphs"] = [g for g in ("☐", "☒") if g in content]
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()


# ------------------------------------------------------------------ non-shipped workers

def arm_m3bytes(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    out["instances"], out["positiveControl"] = [], []
    for k in range(1, rounds + 1):
        pc = {"round": k}
        out["positiveControl"].append(pc)
        try:
            ctx.load(); ctx.open(EMPTY)
            pc["r0"] = ctx.rev()
            pc["attempt"] = ctx.worker(workers.RAW_BYTES_OPERATION, bytes_url=url_of("round-1/M2.md"))
            pc["r1"] = ctx.rev()
        except Exception as error:  # noqa: BLE001
            pc["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()
        for item in pop["M3"]["items"]:
            if item["routes"] != ["bytes"]:
                continue
            rec = {"round": k, "item": item["path"], "sha256": item["sha256"], "expectedCode": item["expectedCode"]}
            out["instances"].append(rec)
            try:
                ctx.load(); ctx.open(EMPTY)
                rec["S0"] = strip(s0 := ctx.save("bytes-S0"))
                rec["r0"] = ctx.rev()
                rec["attempt"] = ctx.worker(workers.RAW_BYTES_OPERATION, bytes_url=url_of(item["path"]))
                rec["r1"] = ctx.rev()
                rec["S1"] = strip(s1 := ctx.save("bytes-S1"))
                rec["s1EqualsS0"] = doc_compare(s1, s0.get("raw"), "S0")
            except Exception as error:  # noqa: BLE001
                rec["runnerError"] = f"{type(error).__name__}: {error}"
            FLUSH["fn"]()


def rect_of(head) -> list[int] | None:
    """The first four integers of a GRAPHIC_SELECTION payload ("x, y, w, h, ..."), None for "EMPTY"."""
    numbers = re.findall(r"-?\d+", head or "")
    return [int(v) for v in numbers[:4]] if len(numbers) >= 4 else None


def lok_ids(entries: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for e in entries:
        if e.get("k") == "mt" and e.get("type") == "lok":
            counts[str(e.get("id"))] = counts.get(str(e.get("id")), 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: int(kv[0])))


def arm_trace(ctx: Ctx, pop: dict, rounds: int, out: dict) -> None:
    """DM-6 (ii), (iii): records and the M10b/c precondition, on the trace worker."""
    limit = pop["M3"]["limitL"]
    out.update({"m6CoreLog": [], "m10Precondition": [], "record": []})
    m2 = next(i for i in pop["M1"] if i["path"] == "round-1/M2.md")
    for k in range(1, rounds + 1):
        rec = {"round": k}
        out["m6CoreLog"].append(rec)
        try:
            ctx.load(); ctx.open(EMPTY)
            ctx.drain(); mark = len(ctx.trace.all)
            corpus = f"m6-{limit}.md"
            rec["dialog"] = ctx.dialog("./md-corpus/gen/" + corpus, sha256_bytes(fx.m6_corpus(limit)[0]), timeout=180)
            for _ in range(10):
                ctx.drain(); time.sleep(0.5)
            rec["lokIds"] = lok_ids(ctx.trace.all[mark:])
            rec["coreLog"] = rec["lokIds"].get("70", 0)
            rec["traceDropped"] = (mws.obs(ctx.session) or {}).get("traceDropped")
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()
        for target in ("image", "frame"):
            rec = {"round": k, "target": target, "click": M10_CLICKS[target]}
            out["m10Precondition"].append(rec)
            try:
                ctx.load(); ctx.open("v21-i2-m10-selectables.odt")
                ctx.drain(); mark = len(ctx.trace.all); imark = len(ctx.ilog.all)
                rec["clicked"] = ctx.click_twips(*M10_CLICKS[target])
                for _ in range(4):
                    ctx.drain(); time.sleep(0.25)
                rec["lokIds"] = lok_ids(ctx.trace.all[mark:])
                heads = [e for e in ctx.ilog.all[imark:] if e.get("k") == "lok"]
                rec["heads"] = [{"id": e.get("id"), "head": e.get("head")} for e in heads]
                # The precondition is GRAPHIC_SELECTION "with the object's rectangle" (ARMS-item2 M10b/c), not
                # any id-6 event: Writer also sends id 6 with "EMPTY" when a selection ends.
                rec["expectedRect"] = M10_RECTS[target]
                rec["graphicSelection"] = sum(1 for e in heads if e.get("id") == 6
                                              and rect_of(e.get("head")) == M10_RECTS[target])
                rec["graphicSelectionAny"] = rec["lokIds"].get("6", 0)
                rec["textSelection"] = rec["lokIds"].get("2", 0)
                rec["selectionType"] = ctx.ask().get("selectionType")
            except Exception as error:  # noqa: BLE001
                rec["runnerError"] = f"{type(error).__name__}: {error}"
            FLUSH["fn"]()
        rec = {"round": k}
        out["record"].append(rec)
        try:
            x11 = next(i for i in pop["M1"] if i["path"] == "m0/X11-task-list.md")
            ctx.load(); ctx.open(EMPTY)
            ctx.dialog(url_of(x11["path"]), x11["sha256"])
            place_keys(ctx, ["ArrowUp", "ArrowUp", "ArrowUp", "Home"])
            caret = ctx.ask().get("caret") or {}
            ctx.drain(); mark = len(ctx.trace.all); imark = len(ctx.ilog.all)
            rec["click"] = ctx.click_twips(caret.get("x", 0) + 100, caret.get("y", 0) + caret.get("height", 276) / 2)
            for _ in range(6):
                ctx.drain(); time.sleep(0.25)
            rec["lokIds"] = lok_ids(ctx.trace.all[mark:])
            rec["heads"] = [{"id": e.get("id"), "head": e.get("head")} for e in ctx.ilog.all[imark:] if e.get("k") == "lok"]
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"
        FLUSH["fn"]()
    _ = m2


# ------------------------------------------------------------------ M5 (proxy browser)

def arm_m5(browser: str, pop: dict, rounds: int, out: dict, scratch: Path, files: dict, docs: Path) -> None:
    proxy = net.LoggingProxy()
    targets = net.TargetListeners()
    out.update({"proxyPort": proxy.port, "rounds": []})
    identity = common.build_mirror(scratch / "mirror-m5", snippets=[v20.OBSERVER, obs2.SNIPPET, hook.SNIPPET],
                                   extra_files=files)
    out["identity"] = identity
    session = None
    try:
        with common.served(Path(identity["mirror"])) as base:
            mirror_port = int(base.split(":")[2].split("/")[0])
            out["mirrorPort"] = mirror_port
            if mirror_port in net.FORBIDDEN_MIRROR_PORTS:
                raise StepError(f"the mirror's port {mirror_port} is a target port")
            session = open_browser(browser, proxy_port=proxy.port)
            out["browserVersion"] = getattr(session, "version", None)
            ctx = Ctx(session, browser, base, docs, identity)
            if browser == "chrome":
                out["clipboardGrant"] = clip.grant(session, browser, base.rsplit("/", 1)[0])
                session.attach_workers()
            for k in range(1, rounds + 1):
                rnd = {"round": k, "items": []}
                out["rounds"].append(rnd)
                t_start = time.time()
                rnd["load"] = ctx.load()
                ctx.open(EMPTY)
                rnd["positiveControl"] = net.positive_control([e for e in proxy.entries() if e["t"] >= t_start - 1],
                                                              mirror_port)
                t0 = time.time()
                r7_support.run_in_page(session, "fetch('http://127.0.0.1:18765/m5-control', { mode: 'no-cors' }).catch(() => {});")
                time.sleep(1.5)
                rnd["secondControl"] = {"proxy": [e for e in proxy.entries() if e["t"] >= t0 and e.get("port") == 18765],
                                        "listener": [e for e in targets.entries() if e["t"] >= t0]}
                for item in pop["M5"]:
                    m3 = M3_BY_PATH[item["path"]]     # the full population: --limit shortens M3 (witness-item2 #5)
                    for route in ("dialog", "sdk"):
                        rec = {"item": item["path"], "route": route, "targets": item["targets"]}
                        rnd["items"].append(rec)
                        try:
                            ctx.load(); ctx.open(EMPTY)
                            w0 = time.time()
                            rec["attempt"] = (ctx.dialog(url_of(item["path"]), m3["sha256"]) if route == "dialog"
                                              else ctx.sdk(url_of(item["path"])))
                            time.sleep(2.0)
                            w1 = time.time()
                            rec["window"] = [round(w0, 3), round(w1, 3)]
                            rec["outsideMirror"] = net.outside_mirror(proxy.entries() + targets.entries(), mirror_port, w0, w1)
                        except Exception as error:  # noqa: BLE001
                            rec["runnerError"] = f"{type(error).__name__}: {error}"
                        FLUSH["fn"]()
                if browser == "chrome":
                    rnd["cdp"] = net.cdp_requests(session.drain_events())[-400:]
                FLUSH["fn"]()
    finally:
        if session is not None:
            out["close"] = common.close_browser(session)
        out["proxyLog"] = [{k: e.get(k) for k in ("t", "method", "host", "port", "path", "status", "error")}
                           for e in proxy.entries()][-3000:]
        out["listenerLog"] = targets.entries()
        proxy.close()
        targets.close()


# ------------------------------------------------------------------ main

def served_limit(mirror: Path) -> int | None:
    """L as the served SDK states it (ARMS-item2 §1: "the operative SDK limit L as parsed from the served
    sdk/document-sdk.js"); the population's L is parsed from the tree's file."""
    found = re.findall(r"export const MARKDOWN_PASTE_LIMIT_BYTES = (\d+);",
                       (mirror / "sdk/document-sdk.js").read_text(encoding="utf-8"))
    return int(found[0]) if len(found) == 1 else None


PAGE_OF = {"m3bytes": "bytes", "trace": "trace"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true", help="a development run: recorded as a smoke, never judged")
    ap.add_argument("--only", default="", help="M4 instance ids to run (development; the judge refuses it)")
    ap.add_argument("--limit", type=int, default=0, help="the first N items of M1/M3 (development; the judge refuses it)")
    ap.add_argument("--wait-lock", type=float, default=0.0, help="seconds to wait for the S-9 lock (default: refuse)")
    args = ap.parse_args()
    # SIGTERM runs the finally blocks (close the browser, then release the lock): a killed development run
    # once left its headless Chrome alive while the next runner had taken the lock.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    arms = [a for a in args.arms.split(",") if a]
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        raise SystemExit(f"unknown arms {unknown}; known {ARMS}")
    if population.build() != json.loads(POPULATION.read_text(encoding="utf-8")):
        raise SystemExit("the committed population differs from what its sources give now")
    pop = json.loads(POPULATION.read_text(encoding="utf-8"))
    PASS_SHA.update({i["path"]: i["sha256"] for i in pop["M1"]})
    M3_BY_PATH.update({i["path"]: i for i in pop["M3"]["items"]})
    if args.limit:
        pop["M1"] = pop["M1"][:args.limit]
        keep = [i for i in pop["M3"]["items"] if "dialog" in i["routes"]][:args.limit]
        keep += [i for i in pop["M3"]["items"] if i["routes"] == ["bytes"]][:args.limit]
        keep += [i for i in pop["M3"]["items"] if i["path"] in ("round-1/M2.md", "round-1/M8.md", "m0/X11-task-list.md")]
        pop["M3"]["items"] = keep
        pop["M5"] = pop["M5"][:args.limit]
        for need in ("round-1/M2.md", "m0/X11-task-list.md", "round-1/C1.md"):
            if not any(i["path"] == need for i in pop["M1"]):
                pop["M1"].append(next(i for i in json.loads(POPULATION.read_text(encoding="utf-8"))["M1"] if i["path"] == need))
    args.out.mkdir(parents=True, exist_ok=True)
    name = f"report-{args.browser}{'-smoke' if args.smoke else ''}.json"
    report_path = args.out / name
    if report_path.exists():
        raise SystemExit(f"refusing to overwrite {report_path}")
    docs = args.out / f"docs-{args.browser}{'-smoke' if args.smoke else ''}"
    docs.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="v21-item2-"))
    report = {"runner": "run_v21_shakedown_item2.py", "runnerSha256": sha256_bytes(Path(__file__).read_bytes()),
              "counted": False, "smoke": args.smoke, "browser": args.browser, "arms": arms, "rounds": args.rounds,
              "development": {"limit": args.limit, "only": args.only} if (args.limit or args.only) else None,
              "startedAt": common.now_iso(), "populationSha256": sha256_bytes(POPULATION.read_bytes()),
              "comparatorSha256": cmp.self_sha256(), "readerSha256": cmp.reader_sha256(),
              "instruments": {n: sha256_bytes((Path(__file__).parent / n).read_bytes()) for n in
                              ("v21_page_hook.py", "v21_item2_observer.py", "v21_clipboard.py", "v21_network.py",
                               "v21_workers.py", "v21_item2_compare.py", "v21_shakedown_common.py",
                               "v21_engine_read.py", "v21_input.py")},
              "identity": {}, "results": {}, "javascriptDialogs": DIALOGS, "consoleErrors": CONSOLE,
              "askMisses": ASK_MISSES}

    def flush() -> None:
        report_path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    FLUSH["fn"] = flush
    files = mirror_files(pop)
    shipped = workers.shipped_worker_text()
    with common.browser_lock(f"run_v21_shakedown_item2 {args.browser} {','.join(arms)}", wait_s=args.wait_lock) as holder:
        report["lockTakenAt"] = common.now_iso()
        report["lock"] = holder
        # After the lock, not before: a wait for the lock can be long, and the desk is what it is now.
        pre = common.pre_run_checks()
        report["preRun"] = pre
        flush()
        if pre["refuse"]:
            raise SystemExit(f"pre-run checks refuse: {pre['refuse']}")
        if "m6" in arms:
            # ARMS-item2 M6: "Run alone, with the desk checked".  Its own fresh browser, first, nothing else in
            # it (smoke R4: run after M4's 57 loads in the same browser, the paste took 32 s; on a fresh page
            # the same corpus took 0.66 s).
            out = report["results"].setdefault("m6", {"arm": "m6", "page": "m6"})
            t0 = time.monotonic()
            session = None
            try:
                identity = common.build_mirror(scratch / "mirror-m6", snippets=[v20.OBSERVER, obs2.SNIPPET, hook.SNIPPET],
                                               extra_files=files)
                report["identity"]["m6"] = dict(identity)
                report["identity"]["m6"]["limitLServed"] = served_limit(Path(identity["mirror"]))
                with common.served(Path(identity["mirror"])) as base:
                    session = open_browser(args.browser)
                    out["browserVersion"] = getattr(session, "version", None)
                    out["clipboardGrant"] = clip.grant(session, args.browser, base.rsplit("/", 1)[0])
                    arm_m6(Ctx(session, args.browser, base, docs, identity), pop, args.rounds, out)
            except Exception as error:  # noqa: BLE001
                out["runnerError"] = f"{type(error).__name__}: {error}"
                out["traceback"] = traceback.format_exc()[-2000:]
            finally:
                if session is not None:
                    out["close"] = common.close_browser(session)
            out["seconds"] = round(time.monotonic() - t0, 1)
            flush()
        page_arms = [a for a in arms if a not in ("m5", "m8", "m6")]
        pages = {}
        for arm in page_arms:
            pages.setdefault(PAGE_OF.get(arm, "main"), []).append(arm)
        if "m8" in arms:
            pages.setdefault("v20", []).append("m8")
            pages.setdefault("main", []).append("m8")
        session = None
        try:
            if pages:
                session = open_browser(args.browser)
                report["browserVersion"] = getattr(session, "version", None)
            for page, page_arm_list in pages.items():
                kwargs = {}
                if page == "bytes":
                    kwargs["worker_override"] = workers.raw_bytes_carrier(shipped)
                if page == "trace":
                    kwargs["worker_override"] = workers.trace_worker(shipped)
                if page == "v20":
                    kwargs["page_profile"] = "e2-editor-v20"
                identity = common.build_mirror(scratch / f"mirror-{page}",
                                               snippets=[v20.OBSERVER, obs2.SNIPPET, hook.SNIPPET],
                                               extra_files=files, **kwargs)
                report["identity"][page] = dict(identity)       # extraFiles: every corpus/fixture file's sha256
                report["identity"][page]["extraFilesSha256"] = sha256_bytes(json.dumps(identity["extraFiles"], sort_keys=True).encode())
                report["identity"][page]["limitLServed"] = served_limit(Path(identity["mirror"]))
                flush()
                with common.served(Path(identity["mirror"])) as base:
                    ctx = Ctx(session, args.browser, base, docs, identity)
                    report["identity"][page]["clipboard"] = clip.grant(session, args.browser, base.rsplit("/", 1)[0])
                    for arm in page_arm_list:
                        key = arm if arm != "m8" else f"m8-{page}"
                        out = report["results"].setdefault(key, {"arm": arm, "page": page})
                        t0 = time.monotonic()
                        try:
                            if arm == "m1":
                                arm_m1(ctx, pop, args.rounds, out)
                            elif arm == "m3":
                                arm_m3(ctx, pop, args.rounds, out)
                            elif arm == "m3size":
                                arm_m3size(ctx, pop, args.rounds, out)
                            elif arm == "m4":
                                arm_m4(ctx, pop, args.rounds, out, set(filter(None, args.only.split(","))) or None)
                            elif arm == "m6":
                                arm_m6(ctx, pop, args.rounds, out)
                            elif arm == "m7a":
                                arm_m7a(ctx, args.rounds, out)
                            elif arm == "m7b":
                                arm_m7b(ctx, pop, args.rounds, out)
                            elif arm == "m8":
                                arm_m8_page(ctx, args.rounds, out, "v20" if page == "v20" else "v21")
                            elif arm == "m9":
                                arm_m9(ctx, pop, args.rounds, out)
                            elif arm == "m10":
                                arm_m10(ctx, pop, args.rounds, out)
                            elif arm == "m11":
                                arm_m11(ctx, pop, args.rounds, out)
                            elif arm == "record":
                                arm_record(ctx, pop, args.rounds, out)
                            elif arm == "m3bytes":
                                arm_m3bytes(ctx, pop, args.rounds, out)
                            elif arm == "trace":
                                arm_trace(ctx, pop, args.rounds, out)
                        except Exception as error:  # noqa: BLE001
                            out["runnerError"] = f"{type(error).__name__}: {error}"
                            out["traceback"] = traceback.format_exc()[-2000:]
                        out["seconds"] = round(time.monotonic() - t0, 1)
                        flush()
        finally:
            if session is not None:
                report["close"] = common.close_browser(session)
        if "m5" in arms:
            out = report["results"].setdefault("m5", {"arm": "m5", "page": "proxy"})
            t0 = time.monotonic()
            try:
                arm_m5(args.browser, pop, args.rounds, out, scratch, files, docs)
            except Exception as error:  # noqa: BLE001
                out["runnerError"] = f"{type(error).__name__}: {error}"
                out["traceback"] = traceback.format_exc()[-2000:]
            out["seconds"] = round(time.monotonic() - t0, 1)
    report["completedAt"] = common.now_iso()
    flush()
    print(json.dumps({"report": str(report_path), "arms": {k: v.get("seconds") for k, v in report["results"].items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
