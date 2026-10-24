#!/usr/bin/env python3
"""Non-counted native-X11 keyboard diagnostic on the real Files/host path.

Run inside an isolated Xvfb display, with WAYLAND_DISPLAY unset. Reuses the
existing headed Chrome launcher and host helpers; changes no product or judge.
It records automated observations and does not satisfy owner-only F3-hand.
"""
from __future__ import annotations

import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "wasm_sdk_probe/tools"))
import diag_v21_dirty_move as headed
import run_e2_c_product_path as pp
import run_v21_d2 as d2
import v21_shakedown_common as common
from check_m3_locks import LockChrome
from create_long_document import build as build_document

spec = importlib.util.spec_from_file_location("h154", REPO / "findings/evidence/154/diag_markdown_dialog_on_host.py")
h154 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h154)


class HeadedHostChrome(headed.HeadedChromeSession, LockChrome):
    """Keep host/CDP helper dispatch while dropping only the headless flag."""


class NativeKeyboard:
    """Focus only this Xvfb Chrome window; inject keys through XTEST, not CDP."""

    def __init__(self, pid: int):
        self.x = C.CDLL("libX11.so.6")
        self.xt = C.CDLL("libXtst.so.6")
        self.x.XOpenDisplay.argtypes = [C.c_char_p]
        self.x.XOpenDisplay.restype = C.c_void_p
        self.x.XSetInputFocus.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_ulong]
        self.x.XRaiseWindow.argtypes = [C.c_void_p, C.c_ulong]
        self.x.XFlush.argtypes = [C.c_void_p]
        self.x.XCloseDisplay.argtypes = [C.c_void_p]
        self.x.XStringToKeysym.argtypes = [C.c_char_p]
        self.x.XStringToKeysym.restype = C.c_ulong
        self.x.XKeysymToKeycode.argtypes = [C.c_void_p, C.c_ulong]
        self.x.XKeysymToKeycode.restype = C.c_ubyte
        self.xt.XTestFakeKeyEvent.argtypes = [C.c_void_p, C.c_uint, C.c_int, C.c_ulong]
        self.display = self.x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("Cannot open the isolated X display")
        tree = subprocess.run(["xwininfo", "-root", "-tree"], capture_output=True, text=True, check=True).stdout
        self.window = None
        for xid in re.findall(r'\b(0x[0-9a-f]+)\s+"', tree):
            prop = subprocess.run(["xprop", "-id", xid, "_NET_WM_PID"], capture_output=True, text=True).stdout
            if re.search(rf"=\s*{pid}\s*$", prop):
                self.window = int(xid, 16)
                break
        if self.window is None:
            raise RuntimeError(f"No X11 window belongs to diagnostic Chrome pid {pid}: {tree}")

    def focus(self):
        self.x.XRaiseWindow(self.display, self.window)
        self.x.XSetInputFocus(self.display, self.window, 2, 0)
        self.x.XFlush(self.display)
        time.sleep(0.2)

    def type(self, text: str):
        if not text or not all("a" <= ch <= "z" for ch in text):
            raise ValueError("This diagnostic types only nonempty lowercase ASCII markers")
        for ch in text:
            code = self.x.XKeysymToKeycode(self.display, self.x.XStringToKeysym(ch.encode()))
            if not code:
                raise RuntimeError(f"No native keycode for {ch!r}")
            self.xt.XTestFakeKeyEvent(self.display, code, 1, 0)
            self.xt.XTestFakeKeyEvent(self.display, code, 0, 0)
            self.x.XFlush(self.display)
            time.sleep(0.06)

    def close(self):
        self.x.XCloseDisplay(self.display)


READ = """(() => ({active: document.activeElement && document.activeElement.id,
  hasFocus: document.hasFocus(), open: document.querySelector('#markdown-dialog').open,
  events: window.xvfbKeyEvents || []}))()"""


def click(session, probe, selector):
    at = pp.evaluate(session, f"{h154.CENTER}({json.dumps(selector)})")
    if not at:
        raise RuntimeError(f"No clickable centre: {selector}")
    probe.real_click(session, "chrome", *at)


def main():
    out = Path(__file__).resolve().parent / "xvfb-focus"
    out.mkdir(exist_ok=False)
    report = {"kind": "non-counted diagnostic", "counted": False, "ownerF3HandSatisfied": False,
              "startedAt": common.now_iso(), "display": os.environ.get("DISPLAY"),
              "waylandDisplay": os.environ.get("WAYLAND_DISPLAY"), "rounds": [],
              "toolSha256": common.sha256_file(Path(__file__)),
              "hostIdentity": d2.host_identity(d2.load_probe().DEFAULT_DDEV)}
    path = out / "report.json"
    probe = d2.load_probe()
    instance = probe.Instance(probe.DEFAULT_DDEV)
    folder = "xvfb-focus-" + time.strftime("%Y%m%dT%H%M%S")
    report["folder"] = folder

    def flush():
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")

    try:
        with common.browser_lock("host-0233 native Xvfb focus diagnostic", wait_s=30) as holder:
            report["lock"] = holder
            report["mkcol"] = instance.dav("MKCOL", folder)[0]
            for n in range(1, 4):
                rnd = {"round": n}
                report["rounds"].append(rnd)
                session = keyboard = None
                name = f"native-focus-{n}.odt"
                remote = f"{folder}/{name}"
                try:
                    rnd["upload"] = instance.dav("PUT", remote, build_document(1),
                                                 {"Content-Type": "application/vnd.oasis.opendocument.text"})[0]
                    session = HeadedHostChrome("cold")
                    session.call("Network.disable")
                    window = session.call("Browser.getWindowForTarget")["windowId"]
                    session.call("Browser.setWindowBounds", {"windowId": window,
                                 "bounds": {"left": 0, "top": 0, "width": 1500, "height": 1100}})
                    session.call("Emulation.setDeviceMetricsOverride", {
                        "width": 1400, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
                    rnd["browserArgv"] = session.argv
                    rnd["browserVersion"] = session.version
                    rnd["login"] = probe.login(session, instance.base, "admin", instance.password)
                    probe.open_from_files(session, instance.base, folder, name, rnd)
                    rnd["opened"] = probe.ui.quiet(session, 180)
                    pp.evaluate(session, probe.INSTRUMENT)
                    keyboard = NativeKeyboard(session.process.pid)
                    keyboard.focus()
                    rnd["nativeWindow"] = hex(keyboard.window)
                    pp.evaluate(session, "(() => { window.xvfbKeyEvents = []; document.addEventListener('keydown', e => "
                                "window.xvfbKeyEvents.push({key:e.key, trusted:e.isTrusted, target:e.target.id}), true); return true; })()")
                    rnd["closedBefore"] = h154.closed_reading(session, "chrome", probe)
                    rnd["insertDialog"] = h154.open_reading(session, "chrome", probe)
                    keyboard.type("xvfbpasted")
                    rnd["insertInput"] = pp.evaluate(session, "document.querySelector('#markdown-text').value")
                    click(session, probe, "#markdown-insert")
                    rnd["afterInsert"] = probe.ui.quiet(session)
                    rnd["focusAfterInsert"] = pp.evaluate(session, READ)
                    keyboard.type("xvfbafterinsert")
                    rnd["typedAfterInsert"] = probe.ui.quiet(session)
                    rnd["cancelDialog"] = h154.open_reading(session, "chrome", probe)
                    keyboard.type("discardedxvfb")
                    rnd["cancelInput"] = pp.evaluate(session, "document.querySelector('#markdown-text').value")
                    rnd["cancel"] = h154.cancel(session, "chrome", probe)
                    rnd["focusAfterCancel"] = pp.evaluate(session, READ)
                    keyboard.type("xvfbaftercancel")
                    rnd["typedAfterCancel"] = probe.ui.quiet(session)
                    rnd["finalNativeEvents"] = pp.evaluate(session, READ)
                    rnd["save"] = probe.ui.save_and_settle(session)
                    status, body = instance.dav("GET", remote)
                    rnd["getStatus"] = status
                    texts = d2.texts_of(body)
                    rnd["savedTexts"] = texts
                    saved = "\n".join(texts)
                    rnd["observed"] = {
                        "headed": "--headless=new" not in session.argv,
                        "nativeKeysTrusted": bool(rnd["finalNativeEvents"]["events"]) and all(
                            e["trusted"] for e in rnd["finalNativeEvents"]["events"]),
                        "insertMarkerSaved": "xvfbafterinsert" in saved,
                        "cancelMarkerSaved": "xvfbaftercancel" in saved,
                        "cancelledTextAbsent": "discardedxvfb" not in saved,
                        "markdownInserted": "xvfbpasted" in saved,
                        "saveLanded": rnd["save"].get("outcome") == "saved" and status == 200,
                    }
                    rnd["screenshot"] = h154.shot(session, out, f"round-{n}.png")
                    print(f"round {n}: {json.dumps(rnd['observed'])}", flush=True)
                except Exception:
                    rnd["error"] = traceback.format_exc()
                    print(f"round {n} ERROR: {rnd['error']}", flush=True)
                finally:
                    if keyboard is not None:
                        keyboard.close()
                    if session is not None:
                        rnd["browserClose"] = common.close_browser(session)
                    flush()
            report["deleteFolder"] = instance.dav("DELETE", folder)[0]
    finally:
        report["completedAt"] = common.now_iso()
        flush()
    return 0 if len(report["rounds"]) == 3 and all(
        r.get("observed") and all(r["observed"].values()) for r in report["rounds"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
