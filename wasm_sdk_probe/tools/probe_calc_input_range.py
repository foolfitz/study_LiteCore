#!/usr/bin/env python3
"""Exercise grid entry and rectangular selection through real browser input."""
import json
import time

import run_calc_editor_browser as browser
from r7_support import evaluate
from run_browser_probe import ChromeSession


def press(session, key, shift=False):
    codes = {"F2": (113, "F2", "\ue032"), "Enter": (13, "Enter", "\ue007"),
             "Escape": (27, "Escape", "\ue00c"), "ArrowRight": (39, "ArrowRight", "\ue014"),
             "ArrowLeft": (37, "ArrowLeft", "\ue012"), "ArrowDown": (40, "ArrowDown", "\ue015"),
             "ArrowUp": (38, "ArrowUp", "\ue013")}
    code, name, webdriver = codes[key]
    if isinstance(session, ChromeSession):
        for kind in ("keyDown", "keyUp"):
            session.call("Input.dispatchKeyEvent", {"type": kind, "key": name, "code": name,
                         "windowsVirtualKeyCode": code, "modifiers": 8 if shift else 0})
    else:
        keys = ([{"type": "keyDown", "value": "\ue008"}] if shift else [])
        keys += [{"type": "keyDown", "value": webdriver}, {"type": "keyUp", "value": webdriver}]
        if shift: keys += [{"type": "keyUp", "value": "\ue008"}]
        session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": keys}]})


def insert(session, text):
    if isinstance(session, ChromeSession):
        session.call("Input.insertText", {"text": text})
    else:
        element = session.command("GET", "/element/active")["element-6066-11e4-a52e-4f735466cecf"]
        session.command("POST", f"/element/{element}/value", {"text": text})


def exercise(session, out, run):
    def check(name, passed, actual):
        run["checks"].append({"id": name, "pass": bool(passed), "actual": actual})
    browser.select(session, "B2")
    original = evaluate(session, "window.__calcEditor.state")
    press(session, "F2")
    time.sleep(.25)
    state = evaluate(session, "window.__calcEditor.state")
    check("F2-preserves-existing-input", state["editing"] == "inline" and state["draft"] == original["cell"]["input"], state)
    press(session, "Escape")
    press(session, "ArrowRight", shift=True)
    time.sleep(.25)
    state = evaluate(session, "window.__calcEditor.state")
    check("shift-right-selects-range", state.get("selection", {}).get("multiple") is True and state["cell"]["column"] == 1, state)
    insert(session, "replacement")
    time.sleep(.25)
    state = evaluate(session, "window.__calcEditor.state")
    check("direct-input-replaces-only-draft", state["editing"] == "inline" and state["draft"] == "replacement" and state["revision"] == original["revision"], state)
    press(session, "Escape")


if __name__ == "__main__":
    browser.exercise = exercise
    raise SystemExit(browser.main())
