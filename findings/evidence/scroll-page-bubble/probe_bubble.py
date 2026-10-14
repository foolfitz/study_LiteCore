#!/usr/bin/env python3
"""SPEC-M3-scroll-page-bubble §5, the browser half without a host: N1-N6, D1, K1, Z1.

Built on findings/evidence/host-0.2.21/probe_10_14o.py (the 10-14n instrument): the
same dist/ mirror served by web/serve.py, the same real input (WebDriver actions in
Firefox, CDP input events in Chrome), the same post-hoc hook on Worker.postMessage.
This file adds: the bubble and #a11y-para to the instrument's state read, a log entry
per scroll event of #desk, a screenshot per wheel step (the thumb is read from pixels,
bubble_geometry.py), and five arms:

  bubble-wheel   the 10-14n page-number steps (14 x 700, 3 x 3000, top) -> N1-N5
  bubble-reduce  3 wheel steps under prefers-reduced-motion: reduce -> N6
  bubble-drag    a real pointer drag of the scrollbar thumb -> D1
  bubble-keys    click the first line, Home, ArrowDown x 60 -> K1
  bubble-short   --doc blank: a tall window (nothing to scroll), then a short one -> Z1

  probe_bubble.py --out DIR --browser firefox --doc long60 --arms bubble-wheel,bubble-reduce,bubble-drag,bubble-keys
  probe_bubble.py --out DIR --browser firefox --doc blank --arms bubble-short
  probe_bubble.py --out DIR2 --browser firefox --doc long60 --arms bubble-wheel,bubble-drag --css-bar '#7d7d7d transparent'
  probe_bubble.py --out DIR3 --browser chrome --doc long60 --mode host          (H1/H2: the owner's path on the host)

--mode host (added 2026-10-15 for H1/H2) walks the owner's path the way probe_10_14n/o do:
login, a folder this probe creates (`probe-bubble-<stamp>`), one uploaded copy of the
fixture PER ARM (so no arm reopens a file whose lock the previous arm's session still
holds), Files -> the row -> the editor route, the same arms, `static` (host version,
commit, buildId, served page from the host's engine MANIFEST) at the start and
`staticAfter` at the end, the folder deleted after.  Every step read also records the
host's `#content` box and the `#page-status` box at full precision (H2).  Reports are
`report-host-<browser>-<doc>.json`.  Nothing of the owner's is touched.

--css-bar (Firefox only) is an instrument accommodation, recorded in the report as `cssBar`:
headless Firefox 157 paints NO thumb for its default (GTK-themed) bar in a WebDriver
screenshot -- at rest, under the pointer and 0.2 s after a real wheel (measured on a static
page with the product's desk geometry, 2026-10-14) -- so N2's thumb reader has nothing to
read; with `scrollbar-color` set on the scroller Firefox paints a 6 px thumb it can read.
The host colours its bars the same way (K4: thumb rgb(125,125,125) in both browsers), so
this is the bar the product route shows.  The product places the bubble from
offsetWidth - clientWidth, which scrollbar-color does not change (12 px before and after).

Never --write; no product byte is touched; the owner's browsers are not ours.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "host-0.2.21"))
TOOLS = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
sys.path.insert(0, str(TOOLS))
import probe_10_14o as base  # noqa: E402
import check_m3_production_ui as ui  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
from bubble_geometry import thumb_centre  # noqa: E402
from check_m3_locks import login, open_from_files  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, Instance  # noqa: E402
from create_long_document import build as build_long_document  # noqa: E402
from probe_m3_gate0_coep import DIST, firefox_profile, sha256_file, utc_now  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import navigate as smoke_navigate  # noqa: E402

SCRATCH = Path("/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/30f3fb46-c713-4ab4-a4a4-79969d084998/scratchpad")

# ---------------------------------------------------------------- the instrument, extended

BUBBLE_READ = """(() => { const b = document.querySelector('#scroll-bubble'); if (!b) return null;
    const r = b.getBoundingClientRect(); const cs = getComputedStyle(b);
    let visible = null; try { visible = b.checkVisibility({ opacityProperty: true, visibilityProperty: true, checkOpacity: true, checkVisibilityCSS: true }); } catch (e) { visible = String(e); }
    return { shown: b.dataset.shown ?? null, text: b.textContent, rect: [r.left, r.top, r.width, r.height].map((v) => Math.round(v * 10) / 10),
             opacity: b.style.opacity, visibility: b.style.visibility, computedOpacity: cs.opacity, transition: cs.transitionDuration,
             visible, ariaHidden: b.getAttribute('aria-hidden'), role: b.getAttribute('role'), ariaLive: b.getAttribute('aria-live'),
             tabindex: b.getAttribute('tabindex'), pointerEvents: cs.pointerEvents, position: cs.position, parent: b.parentElement ? (b.parentElement.id || b.parentElement.tagName) : null }; })()"""


def _replace_once(text: str, find: str, replace: str, what: str) -> str:
    if text.count(find) != 1:
        raise SystemExit(f"the base instrument drifted: {what} found {text.count(find)} times")
    return text.replace(find, replace)


assert BUBBLE_READ.startswith("(() => {") and BUBBLE_READ.endswith("})()")
BUBBLE_FN = BUBBLE_READ[1:-3]   # the IIFE's function: `() => { ... }`
INSTRUMENT = base.INSTRUMENT
INSTRUMENT = _replace_once(
    INSTRUMENT, "  const read = () => ({",
    "  const a11y = $('#a11y-para');\n  const bubbleRead = " + BUBBLE_FN + ";\n  const read = () => ({",
    "read()")
INSTRUMENT = _replace_once(
    INSTRUMENT, "scroll: desk.scrollTop, sinkDisabled: sink.disabled,",
    "scroll: desk.scrollTop, sinkDisabled: sink.disabled, bubble: bubbleRead(), a11y: a11y ? a11y.textContent : null,",
    "the state fields")
INSTRUMENT = _replace_once(
    INSTRUMENT, "  desk.addEventListener('scroll', tick, { passive: true });",
    "  desk.addEventListener('scroll', () => log({ k: 'sc', scrollTop: desk.scrollTop }), { passive: true });\n"
    "  desk.addEventListener('scroll', tick, { passive: true });",
    "the scroll listener")

EXTRA = """(() => { const desk = document.querySelector('#desk'); const d = desk.getBoundingClientRect(); const cs = getComputedStyle(desk);
  return { deskBox: { top: d.top, bottom: d.bottom, left: d.left, right: d.right, offsetWidth: desk.offsetWidth, clientWidth: desk.clientWidth,
                      clientLeft: desk.clientLeft, direction: cs.direction, scrollTop: desk.scrollTop, scrollHeight: desk.scrollHeight, clientHeight: desk.clientHeight },
           bubble: BUBBLE_READ,
           live: [...document.querySelectorAll('[aria-live], [role="status"], [role="alert"]')].map((e) => [e.id || e.tagName, e.textContent]),
           active: document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : null,
           reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
           pageStatus: (() => { const p = document.querySelector('#page-status'); return p ? { hidden: p.hidden, text: p.textContent } : null; })(),
           contentBox: (() => { const c = document.getElementById('content') || document.querySelector('#content-vue, main'); if (!c) return null;
                                const r = c.getBoundingClientRect(); return { id: c.id || c.tagName, left: r.left, top: r.top, right: r.right, bottom: r.bottom }; })(),
           pageStatusBox: (() => { const p = document.querySelector('#page-status'); if (!p) return null; const r = p.getBoundingClientRect();
                                   return { hidden: p.hidden, left: r.left, top: r.top, right: r.right, bottom: r.bottom }; })() }; })()""".replace("BUBBLE_READ", BUBBLE_READ)

CSS_BAR = """(() => { const d = document.querySelector('#desk'); const before = { offsetWidth: d.offsetWidth, clientWidth: d.clientWidth };
  d.style.scrollbarColor = 'ARG_COLOR'; const cs = getComputedStyle(d);
  return { set: 'ARG_COLOR', computedScrollbarColor: cs.scrollbarColor, computedScrollbarWidth: cs.scrollbarWidth,
           before, after: { offsetWidth: d.offsetWidth, clientWidth: d.clientWidth } }; })()"""

OURS_NOT = ("pgrep", "probe_bubble", "probe_10_14n", "probe_10_14o")


def preflight() -> dict[str, Any]:
    wallet = base.sh(["busctl", "--user", "get-property", "org.freedesktop.secrets",
                      "/org/freedesktop/secrets/collection/kdewallet", "org.freedesktop.Secret.Collection", "Locked"])
    ours = [line for line in base.sh(["pgrep", "-af", base.OURS]).splitlines() if not any(n in line for n in OURS_NOT)]
    out = {"at": utc_now(), "kwalletLocked": wallet, "pgrepChrome": base.sh(["pgrep", "-c", "chrome"]),
           "chromeBrowserProcesses": base.sh(["pgrep", "-fc", "/opt/google/chrome/chrome( |$)"]),
           "pgrepFirefox": base.sh(["pgrep", "-c", "firefox"]), "oursRunning": ours,
           "load": Path("/proc/loadavg").read_text().split()[:3]}
    if wallet.strip() == "b true":
        raise SystemExit(f"KWallet is locked: {out}")
    if ours:
        raise SystemExit(f"something of ours is running: {ours}")
    return out


def geometry(session) -> dict[str, Any]:
    g = evaluate(session, base.GEOMETRY)
    g.update(evaluate(session, EXTRA))
    return g


def new_session(kind: str, reduce: bool):
    if kind == "chrome":
        session = ui.new_session(kind)
        if reduce:
            session.call("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
        return session
    if not reduce:
        return ui.new_session(kind)
    ui.SCRATCH.mkdir(parents=True, exist_ok=True)
    session = FirefoxSession("cold", profile_dir=firefox_profile(ui.SCRATCH / f"ff-{time.monotonic_ns()}"),
                             extra_prefs={"ui.prefersReducedMotion": 1})
    session.command("POST", "/window/rect", {"width": 1850, "height": 1080})
    return session


def resize(session, kind: str, height: int) -> None:
    if kind == "chrome":
        session.call("Emulation.setDeviceMetricsOverride", {"width": 1850, "height": height, "deviceScaleFactor": 1, "mobile": False})
        return
    session.command("POST", "/window/rect", {"width": 1850, "height": height})


ARROW_DOWN = {"chrome": ("ArrowDown", "ArrowDown", 40), "firefox": ""}


def press_arrow_down(session, kind: str) -> None:
    if kind == "chrome":
        name, code, vk = ARROW_DOWN["chrome"]
        for phase in ("rawKeyDown", "keyUp"):
            session.call("Input.dispatchKeyEvent", {"type": phase, "key": name, "code": code, "windowsVirtualKeyCode": vk,
                                                    "nativeVirtualKeyCode": vk, "modifiers": 0})
        return
    value = ARROW_DOWN["firefox"]
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": [
        {"type": "keyDown", "value": value}, {"type": "keyUp", "value": value}]}]})
    session.command("DELETE", "/actions")


def centre_of_desk(g: dict[str, Any]) -> tuple[int, int]:
    return g["inner"][0] // 2, (g["desk"]["top"] + g["desk"]["bottom"]) // 2


def step_read(session, i, dy, record, shot: bool) -> dict[str, Any]:
    g = geometry(session)
    step = {"i": i, "dy": dy, "scrollTop": g["deskBox"]["scrollTop"], "pageStatus": g["pageStatus"], "bubble": g["bubble"],
            "deskBox": g["deskBox"], "active": g["active"], "content": g.get("contentBox"), "pageStatusBox": g.get("pageStatusBox")}
    if shot:
        png = session.screenshot()
        label = f"step{i}"
        record.setdefault("_shots", []).append((label, png))
        step["shot"] = label
        step["thumb"] = thumb_centre(png, {"top": g["deskBox"]["top"], "bottom": g["deskBox"]["bottom"], "right": g["deskBox"]["right"]})
    return step


# ---------------------------------------------------------------- arms

def arm_wheel(session, kind: str, record: dict[str, Any], plan=((700, 14), (3000, 3)), shots: bool = True) -> None:
    g0 = geometry(session)
    record["geometryAtOpen"] = g0
    record["askAtOpen"] = base.ask_rectangles(session)
    cx, cy = centre_of_desk(g0)
    record["liveBefore"], record["activeBefore"] = g0["live"], g0["active"]
    start = evaluate(session, base.LOG_LENGTH)
    steps = []
    i = 0
    for dy, n in plan:
        for _ in range(n):
            base.wheel(session, kind, cx, cy, dy)
            time.sleep(0.6)
            steps.append(step_read(session, i, dy, record, shots))
            i += 1
    base.wheel(session, kind, cx, cy, -40000)
    time.sleep(0.6)
    steps.append(step_read(session, "top", -40000, record, shots))
    record["steps"] = steps
    time.sleep(2.0)
    record["afterTwoSeconds"] = geometry(session)
    record["scrollLog"] = base.log_from(session, start)
    record["liveAfter"], record["activeAfter"] = record["afterTwoSeconds"]["live"], record["afterTwoSeconds"]["active"]
    record["askAfterScroll"] = base.ask_rectangles(session)


def arm_reduce(session, kind: str, record: dict[str, Any]) -> None:
    arm_wheel(session, kind, record, plan=((700, 3),), shots=False)


def arm_drag(session, kind: str, record: dict[str, Any]) -> None:
    g0 = geometry(session)
    record["geometryAtOpen"] = g0
    desk = g0["deskBox"]
    png = session.screenshot()
    record.setdefault("_shots", []).append(("before-drag", png))
    thumb = thumb_centre(png, {"top": desk["top"], "bottom": desk["bottom"], "right": desk["right"]})
    record["thumbBefore"] = thumb
    if thumb is None:
        record["notEstablished"] = "no thumb read from the screenshot before the drag"
        return
    rail = desk["offsetWidth"] - desk["clientWidth"]
    x = desk["right"] - (rail / 2 if rail > 0 else 5)
    y = thumb["centre"]
    record["dragFrom"] = [x, y]
    record["liveBefore"], record["activeBefore"] = g0["live"], g0["active"]
    start = evaluate(session, base.LOG_LENGTH)
    during = []
    if kind == "chrome":
        session.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "button": "none"})
        session.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "buttons": 1, "clickCount": 1})
        for i in range(1, 11):
            time.sleep(0.05)
            session.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y + 10 * i, "button": "left", "buttons": 1})
            if i % 3 == 0:
                g = geometry(session)
                during.append({"i": i, "scrollTop": g["deskBox"]["scrollTop"], "bubble": g["bubble"]})
        session.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y + 100, "button": "left", "buttons": 0, "clickCount": 1})
    else:
        actions = [{"type": "pointerMove", "x": int(x), "y": int(y), "origin": "viewport"}, {"type": "pointerDown", "button": 0}]
        for i in range(1, 11):
            actions += [{"type": "pause", "duration": 50}, {"type": "pointerMove", "x": int(x), "y": int(y + 10 * i), "origin": "viewport"}]
        actions += [{"type": "pointerUp", "button": 0}]
        session.command("POST", "/actions", {"actions": [{"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"}, "actions": actions}]})
        session.command("DELETE", "/actions")
    record["during"] = during
    time.sleep(0.3)
    g = geometry(session)
    record["afterRelease"] = {"scrollTop": g["deskBox"]["scrollTop"], "bubble": g["bubble"], "pageStatus": g["pageStatus"],
                              "deskBox": g["deskBox"], "content": g.get("contentBox"), "pageStatusBox": g.get("pageStatusBox")}
    png = session.screenshot()
    record["_shots"].append(("after-drag", png))
    record["thumbAfter"] = thumb_centre(png, {"top": desk["top"], "bottom": desk["bottom"], "right": desk["right"]})
    time.sleep(2.0)
    record["afterTwoSeconds"] = geometry(session)
    record["scrollLog"] = base.log_from(session, start)
    record["liveAfter"], record["activeAfter"] = record["afterTwoSeconds"]["live"], record["afterTwoSeconds"]["active"]


def arm_keys(session, kind: str, record: dict[str, Any]) -> None:
    base.to_start(session, kind, record, "click-home")
    g0 = geometry(session)
    record["geometryAtStart"] = g0
    record["liveBefore"], record["activeBefore"] = g0["live"], g0["active"]
    start = evaluate(session, base.LOG_LENGTH)
    for _ in range(60):
        press_arrow_down(session, kind)
        time.sleep(0.06)
    record["pressed"] = 60
    time.sleep(0.6)
    record["afterKeys"] = geometry(session)
    time.sleep(2.0)
    record["afterTwoSeconds"] = geometry(session)
    record["settle"] = base.settle(session, 1.5, 60)
    record["scrollLog"] = base.log_from(session, start)
    record["liveAfter"], record["activeAfter"] = record["afterTwoSeconds"]["live"], record["afterTwoSeconds"]["active"]
    record["summary"] = base.summarize(record["scrollLog"])


def arm_short(session, kind: str, record: dict[str, Any]) -> None:
    g0 = geometry(session)
    record["geometryNormal"] = g0
    cx, cy = centre_of_desk(g0)
    resize(session, kind, 1700 if kind == "chrome" else 1800)
    time.sleep(1.2)
    g1 = geometry(session)
    record["geometryTall"] = g1
    start = evaluate(session, base.LOG_LENGTH)
    tall = []
    for i in range(3):
        base.wheel(session, kind, cx, cy, 700)
        time.sleep(0.6)
        tall.append(step_read(session, i, 700, record, False))
    record["tallSteps"] = tall
    record["tallLog"] = base.log_from(session, start)
    resize(session, kind, 980 if kind == "chrome" else 1080)
    time.sleep(1.2)
    g2 = geometry(session)
    record["geometryBack"] = g2
    cx, cy = centre_of_desk(g2)
    start = evaluate(session, base.LOG_LENGTH)
    base.wheel(session, kind, cx, cy, 700)
    time.sleep(0.6)
    record["backStep"] = step_read(session, "back", 700, record, True)
    record["backLog"] = base.log_from(session, start)


ARMS = {"bubble-wheel": arm_wheel, "bubble-reduce": arm_reduce, "bubble-drag": arm_drag, "bubble-keys": arm_keys, "bubble-short": arm_short}


def run_arm(arm: str, kind: str, name: str, out_dir: Path, nohost: dict[str, Any] | None, css_bar: str | None = None,
            instance: Instance | None = None, folder: str | None = None) -> dict[str, Any]:
    mode = "nohost" if nohost else "host"
    record: dict[str, Any] = {"arm": arm, "browser": kind, "doc": name, "startedAt": utc_now(), "mode": mode, "preflight": preflight()}
    session = new_session(kind, reduce=(arm == "bubble-reduce"))
    record["version"] = getattr(session, "version", None)
    try:
        if nohost:
            t_open = time.monotonic()
            smoke_navigate(session, nohost["url"])
            pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
            evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./fixture.odt").replace("ARG_NAME", name))
            record["landed"] = pp.wait_for(session, lambda s: (s.get("doc") or "") == name and s.get("state") == "ready", 300)
            record["secondsToOpened"] = round(time.monotonic() - t_open, 2)
        else:
            # the owner's path, as probe_10_14n/o walk it: login, Files, the row, the editor route
            record["login"] = login(session, instance.base, "admin", instance.password)
            open_from_files(session, instance.base, folder, name, record)
        record["opened"] = ui.quiet(session, 180)
        record["instrument"] = evaluate(session, INSTRUMENT)
        if css_bar:
            record["cssBar"] = evaluate(session, CSS_BAR.replace("ARG_COLOR", css_bar))
        record["geometryAfterOpen"] = geometry(session)
        # the hook learns the document handle from the page's own requests: nudge one paint (as 10-14n)
        cx, cy = centre_of_desk(record["geometryAfterOpen"])
        for _ in range(3):
            base.wheel(session, kind, cx, cy, 1200)
            time.sleep(0.25)
        time.sleep(0.6)
        base.wheel(session, kind, cx, cy, -40000)
        time.sleep(0.6)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and evaluate(session, "(() => window.__n.documentHandle)()") is None:
            time.sleep(0.3)
        record["nudgeSettled"] = base.settle(session, 1.0, 30)
        time.sleep(1.5)   # the nudge's bubble is gone before the arm's log starts
        record["documentHandle"] = evaluate(session, "(() => window.__n.documentHandle)()")
        ARMS[arm](session, kind, record)
        for label, png in record.pop("_shots", []):
            path = out_dir / f"{kind}-{arm}-{label}.png"
            path.write_bytes(png)
            record.setdefault("screenshots", []).append(path.name)
        path = out_dir / f"{kind}-{arm}-end.png"
        path.write_bytes(session.screenshot())
        record.setdefault("screenshots", []).append(path.name)
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
        try:
            record["stateAtFatal"] = evaluate(session, base.STATE_NOW)
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
    parser.add_argument("--browser", default="firefox", choices=["firefox", "chrome"])
    parser.add_argument("--doc", default="long60", choices=["long60", "blank"])
    parser.add_argument("--arms", default="bubble-wheel,bubble-reduce,bubble-drag,bubble-keys")
    parser.add_argument("--css-bar", default=None, metavar="SCROLLBAR_COLOR",
                        help="Firefox only: set scrollbar-color on #desk after the page is open so headless Firefox paints a thumb "
                             "the screenshot can read (see the module docstring); recorded in the report as cssBar")
    parser.add_argument("--mode", default="nohost", choices=["nohost", "host"],
                        help="host: the owner's path on the ddev instance (login, Files, the editor route), one uploaded copy per arm")
    parser.add_argument("--keep-folder", action="store_true", help="host: leave the probe's folder on the instance")
    args = parser.parse_args()
    base.DOC_KIND["value"] = args.doc
    arms = [a for a in args.arms.split(",") if a]
    unknown = sorted(set(arms) - set(ARMS))
    if unknown:
        parser.error(f"unknown arms {unknown}")
    if args.css_bar and args.browser != "firefox":
        parser.error("--css-bar is for Firefox only (Chrome paints its default bar in a headless screenshot)")
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().replace(":", "").replace("-", "")[:15]
    if args.doc == "long60":
        doc, name = build_long_document(60), "probe-bubble-long60.odt"
    else:
        doc, name = (DIST / "blank.odt").read_bytes(), "probe-bubble-blank.odt"
    try:
        static = ui.static_facts(DEFAULT_DDEV)
    except Exception:  # noqa: BLE001
        static = {"error": traceback.format_exc()[-800:]}
    report: dict[str, Any] = {"probe": "probe_bubble.py", "startedAt": utc_now(), "static": static, "mode": args.mode,
                              "browser": args.browser, "doc": {"name": name, "sha256": hashlib.sha256(doc).hexdigest(), "bytes": len(doc)},
                              "arms": arms, "cssBar": args.css_bar, "runs": []}
    report_name = f"report-{args.mode}-{args.browser}-{args.doc}.json"
    nohost = server = instance = folder = None
    names = {arm: name for arm in arms}
    if args.mode == "nohost":
        mirror = SCRATCH / f"mirror-bubble-{stamp}"
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
        report["nohost"] = {**nohost, "servedPage": sha256_file(mirror / "e2-editor-app.js"),
                            "servedSession": sha256_file(mirror / "editor-shell-v2" / "narrow-editor-v2-session.js"),
                            "profile": pp.product_profile(mirror)}
    else:
        instance = Instance(DEFAULT_DDEV)
        folder = f"probe-bubble-{stamp}"
        status, _ = instance.dav("MKCOL", folder)
        uploads = {}
        for arm in arms:
            # one copy per arm: a fresh session reopening the SAME file finds the previous session's lock still
            # held (423, the host's notice bar); the copies keep every arm on the owner's plain path
            names[arm] = f"probe-bubble-{args.doc}-{arm}.odt"
            put, _ = instance.dav("PUT", f"{folder}/{names[arm]}", doc, {"Content-Type": "application/vnd.oasis.opendocument.text"})
            uploads[names[arm]] = put
        report["host"] = {"base": instance.base, "folder": folder, "mkcol": status, "uploads": uploads,
                          "hostVersion": static.get("hostVersion"), "hostCommit": static.get("hostCommit"), "buildId": static.get("buildId"),
                          "servedPage": static.get("servedPage"), "servedSession": static.get("servedSession")}
    try:
        for arm in arms:
            run = run_arm(arm, args.browser, names[arm], args.out, nohost, css_bar=args.css_bar, instance=instance, folder=folder)
            report["runs"].append(run)
            (args.out / report_name).write_text(json.dumps(report, ensure_ascii=False, indent=1))
            brief = {k: run.get(k) for k in ("afterRelease", "notEstablished", "pressed", "cssBar", "secondsToOpened") if k in run}
            if run.get("host"):
                brief["lock"] = (run["host"].get("lock") or {}).get("state")
            if "steps" in run:
                brief["steps"] = [(s["i"], s["scrollTop"], (s["bubble"] or {}).get("shown"), (s["bubble"] or {}).get("text"),
                                   (s.get("thumb") or {}).get("centre")) for s in run["steps"]]
            print(args.browser, args.mode, arm, "FATAL" if run.get("fatal") else "", json.dumps(brief, ensure_ascii=False)[:1500], flush=True)
            if run.get("fatal"):
                print(run["fatal"][-1500:], flush=True)
    finally:
        if nohost:
            report["nohost"]["servedPageAtEnd"] = sha256_file(mirror / "e2-editor-app.js")
            server.terminate()
            server.wait(timeout=10)
        else:
            if not args.keep_folder:
                status, _ = instance.dav("DELETE", folder)
                report["host"]["deletedFolder"] = status
            try:
                report["staticAfter"] = ui.static_facts(DEFAULT_DDEV)
            except Exception:  # noqa: BLE001
                report["staticAfter"] = {"error": traceback.format_exc()[-800:]}
            report["host"]["servedPageAtEnd"] = report["staticAfter"].get("servedPage")
        report["endedAt"] = utc_now()
        (args.out / report_name).write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
