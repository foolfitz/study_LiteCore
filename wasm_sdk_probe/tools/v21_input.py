#!/usr/bin/env python3
"""S-4 (keys, pointer, drag): real input for the v21 shakedown.  Agent M's clipboard half is separate.

Arms: ARMS.md S-4; ARMS-item1.md §2.3.  Chrome: CDP `Input.dispatchKeyEvent` / `Input.dispatchMouseEvent`.
Firefox: geckodriver (WebDriver) key and pointer actions.  A synthetic KeyboardEvent or PointerEvent
is never dispatched from here.

  key(session, browser, name, mods=())          one press (keydown/keyup); name in KEYS or one character
  chain(session, browser, presses)              presses back to back, no wait (Firefox: ONE action chain)
  hold(session, browser, name, mods, hold_ms, flagged)
                                                flagged: one keydown, repeats (`repeat: true`) every 30 ms
                                                from 500 ms, one keyup.  Unflagged: a press, then from
                                                500 ms a keyup+keydown pair every 30 ms (`repeat: false`)
  click(session, browser, x, y)                 primary-button click at a viewport point
  drag(session, browser, a, b, steps=4)         press at a, move in steps, release at b
  paper_point(session, x_tw, y_tw, h_tw)        twips -> viewport point via #paper and the document size
  schedule(steps)                               [(t_ms, callable)] on the monotonic clock; returns the
                                                actual send times
"""
from __future__ import annotations

import time

# name -> (CDP key, CDP code, Windows VK, WebDriver key)
KEYS = {
    "ArrowLeft": ("ArrowLeft", "ArrowLeft", 37, ""),
    "ArrowUp": ("ArrowUp", "ArrowUp", 38, ""),
    "ArrowRight": ("ArrowRight", "ArrowRight", 39, ""),
    "ArrowDown": ("ArrowDown", "ArrowDown", 40, ""),
    "Home": ("Home", "Home", 36, ""),
    "End": ("End", "End", 35, ""),
    "Backspace": ("Backspace", "Backspace", 8, ""),
    "Delete": ("Delete", "Delete", 46, ""),
    "Enter": ("Enter", "Enter", 13, ""),
    "Escape": ("Escape", "Escape", 27, ""),
}
MODS_CDP = {"alt": 1, "ctrl": 2, "meta": 4, "shift": 8}
MODS_WD = {"alt": "", "ctrl": "", "meta": "", "shift": ""}
HOLD_DELAY_MS, HOLD_INTERVAL_MS = 500, 30


def _cdp_params(name: str, mods) -> tuple[dict, str | None]:
    bits = sum(MODS_CDP[m] for m in mods)
    if name in KEYS:
        key, code, vk, _ = KEYS[name]
        return {"key": key, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk,
                "modifiers": bits}, None
    if len(name) != 1:
        raise ValueError(f"unknown key {name!r}")
    if name.isupper():
        bits |= MODS_CDP["shift"]
    vk = ord(name.upper())
    code = f"Key{name.upper()}" if name.isalpha() else ""
    text = name if not ({"ctrl", "meta", "alt"} & set(mods)) else None
    return {"key": name, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk,
            "modifiers": bits}, text


def _cdp_press(session, name: str, mods) -> None:
    params, text = _cdp_params(name, mods)
    session.call("Input.dispatchKeyEvent", {**params, "type": "rawKeyDown"})
    if text is not None:
        session.call("Input.dispatchKeyEvent", {**params, "type": "char", "text": text})
    session.call("Input.dispatchKeyEvent", {**params, "type": "keyUp"})


def _wd_value(name: str) -> str:
    return KEYS[name][3] if name in KEYS else name


def _wd_press_actions(name: str, mods) -> list[dict]:
    value = _wd_value(name)
    down = [{"type": "keyDown", "value": MODS_WD[m]} for m in mods]
    up = [{"type": "keyUp", "value": MODS_WD[m]} for m in reversed(list(mods))]
    return down + [{"type": "keyDown", "value": value}, {"type": "keyUp", "value": value}] + up


def _wd_perform(session, actions: list[dict]) -> None:
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": actions}]})
    session.command("DELETE", "/actions")


def key(session, browser: str, name: str, mods=()) -> None:
    if browser == "chrome":
        _cdp_press(session, name, mods)
    else:
        _wd_perform(session, _wd_press_actions(name, mods))


def chain(session, browser: str, presses: list[tuple[str, tuple]]) -> None:
    """Presses back to back.  Chrome: consecutive CDP calls.  Firefox: one action chain, no pauses."""
    if browser == "chrome":
        for name, mods in presses:
            _cdp_press(session, name, mods)
        return
    actions: list[dict] = []
    for name, mods in presses:
        actions += _wd_press_actions(name, mods)
    _wd_perform(session, actions)


def _times(hold_ms: int) -> list[int]:
    return [0] + list(range(HOLD_DELAY_MS, hold_ms + 1, HOLD_INTERVAL_MS))


def hold(session, browser: str, name: str, mods=(), hold_ms: int = 1000, flagged: bool = True) -> dict:
    times = _times(hold_ms)
    release = times[-1] + HOLD_INTERVAL_MS // 2
    if browser == "chrome":
        params, _ = _cdp_params(name, mods)
        start, sent = time.monotonic(), []
        for i, at in enumerate(times):
            wait = start + at / 1000 - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            if i and not flagged:
                session.call("Input.dispatchKeyEvent", {**params, "type": "keyUp"})
            sent.append(round((time.monotonic() - start) * 1000, 1))
            session.call("Input.dispatchKeyEvent", {**params, "type": "rawKeyDown",
                                                    "autoRepeat": bool(flagged and i > 0)})
        wait = start + release / 1000 - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        session.call("Input.dispatchKeyEvent", {**params, "type": "keyUp"})
        return {"presses": len(times), "flagged": flagged, "releaseMs": release, "sentMs": sent}
    value = _wd_value(name)
    actions = [{"type": "keyDown", "value": MODS_WD[m]} for m in mods]
    previous = 0
    for i, at in enumerate(times):
        if at > previous:
            actions.append({"type": "pause", "duration": at - previous})
        if i and not flagged:
            actions.append({"type": "keyUp", "value": value})
        actions.append({"type": "keyDown", "value": value})
        previous = at
    actions += [{"type": "pause", "duration": release - previous}, {"type": "keyUp", "value": value}]
    actions += [{"type": "keyUp", "value": MODS_WD[m]} for m in reversed(list(mods))]
    _wd_perform(session, actions)
    return {"presses": len(times), "flagged": flagged, "releaseMs": release}


def _cdp_mouse(session, kind: str, x: float, y: float, buttons: int) -> None:
    params = {"type": kind, "x": x, "y": y, "button": "left" if kind != "mouseMoved" else ("left" if buttons else "none"),
              "buttons": buttons, "clickCount": 1 if kind != "mouseMoved" else 0}
    session.call("Input.dispatchMouseEvent", params)


def _wd_pointer(session, actions: list[dict]) -> None:
    session.command("POST", "/actions", {"actions": [{"type": "pointer", "id": "mouse",
                                                      "parameters": {"pointerType": "mouse"}, "actions": actions}]})
    session.command("DELETE", "/actions")


def click(session, browser: str, x: float, y: float) -> None:
    if browser == "chrome":
        _cdp_mouse(session, "mouseMoved", x, y, 0)
        _cdp_mouse(session, "mousePressed", x, y, 1)
        _cdp_mouse(session, "mouseReleased", x, y, 0)
        return
    _wd_pointer(session, [{"type": "pointerMove", "x": int(round(x)), "y": int(round(y)), "origin": "viewport"},
                          {"type": "pointerDown", "button": 0}, {"type": "pointerUp", "button": 0}])


def drag(session, browser: str, a: tuple[float, float], b: tuple[float, float], steps: int = 4) -> None:
    points = [(a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps) for i in range(1, steps + 1)]
    if browser == "chrome":
        _cdp_mouse(session, "mouseMoved", a[0], a[1], 0)
        _cdp_mouse(session, "mousePressed", a[0], a[1], 1)
        for x, y in points:
            time.sleep(0.05)
            _cdp_mouse(session, "mouseMoved", x, y, 1)
        _cdp_mouse(session, "mouseReleased", b[0], b[1], 0)
        return
    actions = [{"type": "pointerMove", "x": int(round(a[0])), "y": int(round(a[1])), "origin": "viewport"},
               {"type": "pointerDown", "button": 0}]
    for x, y in points:
        actions += [{"type": "pause", "duration": 50},
                    {"type": "pointerMove", "x": int(round(x)), "y": int(round(y)), "origin": "viewport", "duration": 20}]
    actions.append({"type": "pointerUp", "button": 0})
    _wd_pointer(session, actions)


PAPER_RECT = """(() => { const r = document.querySelector('#paper').getBoundingClientRect();
const d = document.querySelector('#desk').getBoundingClientRect();
return { left: r.left, top: r.top, width: r.width, height: r.height, deskTop: d.top, deskBottom: d.bottom }; })()"""

SCROLL_TO_FRACTION = """(() => { const desk = document.querySelector('#desk'), paper = document.querySelector('#paper');
const d = desk.getBoundingClientRect(), p = paper.getBoundingClientRect();
const y = p.top - d.top + desk.scrollTop + p.height * ARG_F;
if (y < desk.scrollTop + 40 || y > desk.scrollTop + desk.clientHeight - 40)
  desk.scrollTop = Math.max(0, Math.round(y - desk.clientHeight / 2));
return desk.scrollTop; })()"""


def paper_point(session, evaluate, x_tw: float, y_tw: float, h_tw: float, size: dict) -> tuple[float, float]:
    """The viewport point of the twips point (x, y + h/2): MWS place's fractions (run_merge_wasm_shakedown
    :686-687), mapped through #paper's bounding box.  Scrolls the desk first when the point is outside
    the visible part of the desk, so a real click lands on the paper."""
    fy = (y_tw + h_tw / 2) / size["h"]
    evaluate(session, SCROLL_TO_FRACTION.replace("ARG_F", repr(fy)))
    time.sleep(0.25)
    rect = evaluate(session, PAPER_RECT)
    return (rect["left"] + rect["width"] * x_tw / size["w"], rect["top"] + rect["height"] * fy)


def schedule(steps: list[tuple[int, object]]) -> list[float]:
    """Run each callable at its offset (ms) on the monotonic clock; return when each was actually sent."""
    start, sent = time.monotonic(), []
    for at, action in steps:
        wait = start + at / 1000 - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        sent.append(round((time.monotonic() - start) * 1000, 1))
        action()
    return sent
