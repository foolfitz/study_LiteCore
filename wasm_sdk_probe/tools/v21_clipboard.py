#!/usr/bin/env python3
"""S-4, the clipboard half (Agent M): a real clipboard, a trusted Ctrl+V, and the read-back that decides
whether the dialog route carried an item intact (spec §12.2 (c); ARMS-item2.md DM-2 A with A1).

The shape is tools/probe_paste_latency.py's, which both browsers executed on 2026-10-14 ([observed]
findings/evidence/paste-latency/README.md:30-31): Chrome gets clipboard permission through CDP
(`Browser.grantPermissions`) and the page writes with `navigator.clipboard.writeText`; Firefox runs with
the pref `dom.events.testing.asyncClipboard` (FIREFOX_PREFS, passed when the session is created) and the
same call writes its headless clipboard; then a trusted Ctrl+V (CDP `Input.dispatchKeyEvent`, WebDriver
key actions).  Nothing synthetic is dispatched.

  FIREFOX_PREFS
  grant(session, browser, origin)        Chrome: the permission; Firefox: nothing to do (the pref)
  write_from_url(session, url)           the page fetches `url`, decodes it as UTF-8 (fatal), writes the
                                         clipboard, and reads it back -> {ok, utf16, utf8, sha256, same}
  write_text(session, text)              the same for a short literal text (markers)
  press_ctrl_v(session, browser)         the trusted chord
  readback(session, selector)            {utf16, utf8, sha256} of the element's `value`, computed in the
                                         page (the text never crosses CDP)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r7_support  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

FIREFOX_PREFS = {"dom.events.testing.asyncClipboard": True}

_DIGEST = """const digest = async (text) => { const bytes = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return { utf16: text.length, utf8: bytes.byteLength,
           sha256: [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, "0")).join("") }; };"""

WRITE = """(async () => { %s
  const node = document.getElementById("v21-clip") || Object.assign(document.createElement("script"),
    { type: "application/json", id: "v21-clip" });
  if (!node.isConnected) document.head.appendChild(node);
  node.textContent = "";
  try {
    const text = ARG_SOURCE;
    await navigator.clipboard.writeText(text);
    const back = await navigator.clipboard.readText();
    const wrote = await digest(text), read = await digest(back);
    node.textContent = JSON.stringify({ ok: true, ...wrote, readBack: read, same: wrote.sha256 === read.sha256 });
  } catch (error) { node.textContent = JSON.stringify({ ok: false, error: String(error).slice(0, 300) }); }
})();""" % _DIGEST
FROM_URL = 'new TextDecoder("utf-8", { fatal: true }).decode(await (await fetch(%s, { cache: "no-cache" })).arrayBuffer())'
READ_CLIP = "(() => { const n = document.getElementById('v21-clip'); return n ? n.textContent : null; })()"

READBACK = """(async () => { %s
  const node = document.getElementById("v21-readback") || Object.assign(document.createElement("script"),
    { type: "application/json", id: "v21-readback" });
  if (!node.isConnected) document.head.appendChild(node);
  node.textContent = "";
  const element = document.querySelector(ARG_SELECTOR);
  node.textContent = JSON.stringify(element ? await digest(element.value ?? "") : { missing: true });
})();""" % _DIGEST
READ_READBACK = "(() => { const n = document.getElementById('v21-readback'); return n ? n.textContent : null; })()"


def grant(session, browser: str, origin: str) -> dict:
    if browser != "chrome":
        return {"firefoxPref": FIREFOX_PREFS}
    out = {}
    try:
        session.call("Browser.grantPermissions",
                     {"origin": origin, "permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]})
        out["granted"] = True
    except RuntimeError as error:
        out["granted"] = str(error)
    try:
        session.call("Page.bringToFront")
    except RuntimeError as error:
        out["bringToFront"] = str(error)
    return out


def _poll(session, expression: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        raw = pp.evaluate(session, expression)
        if raw:
            return json.loads(raw)
        time.sleep(0.1)
    return {"ok": False, "error": f"no answer in {timeout} s"}


def write_from_url(session, url: str, timeout: float = 20.0) -> dict:
    r7_support.run_in_page(session, WRITE.replace("ARG_SOURCE", FROM_URL % json.dumps(url)))
    return _poll(session, READ_CLIP, timeout)


def write_text(session, text: str, timeout: float = 20.0) -> dict:
    r7_support.run_in_page(session, WRITE.replace("ARG_SOURCE", json.dumps(text)))
    return _poll(session, READ_CLIP, timeout)


def press_ctrl_v(session, browser: str) -> None:
    """tools/probe_paste_latency.py:243-255, the chord both browsers turned into a trusted paste."""
    if browser == "chrome":
        ctrl = {"key": "Control", "code": "ControlLeft", "windowsVirtualKeyCode": 17, "nativeVirtualKeyCode": 17,
                "modifiers": 2}
        v = {"key": "v", "code": "KeyV", "windowsVirtualKeyCode": 86, "nativeVirtualKeyCode": 86, "modifiers": 2}
        session.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", **ctrl})
        session.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", **v})
        session.call("Input.dispatchKeyEvent", {"type": "keyUp", **v})
        session.call("Input.dispatchKeyEvent", {"type": "keyUp", **ctrl})
        return
    actions = [{"type": "keyDown", "value": ""}, {"type": "keyDown", "value": "v"},
               {"type": "keyUp", "value": "v"}, {"type": "keyUp", "value": ""}]
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": actions}]})
    session.command("DELETE", "/actions")


def readback(session, selector: str, timeout: float = 10.0) -> dict:
    r7_support.run_in_page(session, READBACK.replace("ARG_SELECTOR", json.dumps(selector)))
    return _poll(session, READ_READBACK, timeout)
