#!/usr/bin/env python3
"""A11y gate 0: does LOK emit a focused paragraph on WASM?

Roadmap section 3.3 puts ONE question at this gate.  This probe asks it and
nothing else.  Criteria are fixed in `handoff/a11y-gate-0/PREDICTION.md`, written
2026-08-21 BEFORE the patch and before any rebuild -- read that first.

PREPARED, NOT RUN.  It cannot pass on today's core: `SwEditWin::CreateAccessible`
returns {} whenever ENABLE_WASM_STRIP_ACCESSIBILITY is set
(`sw/source/uibase/docvw/edtwin.cxx:6532-6542`), and on 26.8's Emscripten no flag
combination clears it (finding 057).  So the probe REFUSES to run against a build
whose `config_wasm_strip.h` still sets the macro -- see G0-1.  That refusal is the
point: a run against an unpatched build measures nothing, and a number from it
would be worse than no number.

Nothing new is added to the engine.  It already reports every field this needs
(`probe_engine.cpp:1090-1100`) and already probes `getA11yFocusedParagraph`
(`:1835`); what has never existed is a build where the call sites are compiled in.

Usage:
  probe_a11y_gate0.py --browser chrome [--profile e2-editor-v4] [--out FILE]
  probe_a11y_gate0.py --check-build-only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from run_e2_c_product_path import (  # noqa: E402
    LINE_INK, POINT_AT, caret_click_fractions, place_caret_and_settle,
    stable_bands,
)

PROJECT = Path(__file__).resolve().parent.parent

# The engine already publishes this; the worker forwards the editor state.  Read
# it through the page's own session rather than adding a field.
READ_A11Y = """(() => {
const el = document.querySelector('#s-a11y');
if (el && el.dataset && el.dataset.json) return JSON.parse(el.dataset.json);
return { unavailableToProbe:
  'the page does not surface the engine accessibility block; read it from the '
  + 'editor state instead -- see PREDICTION.md G0-2' };
})()"""


def build_provides_accessibility() -> dict:
    """G0-1, and it runs BEFORE a browser starts.

    Delegated to the standing guard rather than reimplemented:
    `check_core_build_provides.py` already reads
    `config_host/config_wasm_strip.h` for ENABLE_WASM_STRIP_ACCESSIBILITY, and
    it is RED today -- which is the honest state, not a problem to route around.
    """
    guard = PROJECT / "tools" / "check_core_build_provides.py"
    completed = subprocess.run([sys.executable, str(guard)],
                               capture_output=True, text=True)
    return {
        "guard": "tools/check_core_build_provides.py",
        "exitCode": completed.returncode,
        "provides": completed.returncode == 0,
        "stdout": completed.stdout[-2000:],
        "stderr": completed.stderr[-800:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"),
                        default="chrome")
    parser.add_argument("--profile", default="e2-editor-v4")
    parser.add_argument("--fixture", default="list-contexts.odt")
    parser.add_argument("--out", default=None)
    parser.add_argument("--check-build-only", action="store_true")
    parser.add_argument("--i-know-the-macro-is-set", action="store_true",
                        help="run anyway; the result is stamped UNMEASURABLE "
                             "and may not be quoted as a gate outcome")
    args = parser.parse_args()

    record: dict = {
        "schemaVersion": 1,
        "release": "a11y-gate-0",
        "question": "does LOK emit a focused paragraph on WASM?",
        "criteria": "handoff/a11y-gate-0/PREDICTION.md (written 2026-08-21, "
                    "before the patch and before any rebuild)",
        "patch": "handoff/a11y-gate-0/PATCH.md",
        "browser": args.browser,
        "profile": args.profile,
        "placements": [],
    }

    record["G0_1_buildProvidesAccessibility"] = build_provides_accessibility()
    if args.check_build_only:
        return finish(record, args)

    if not record["G0_1_buildProvidesAccessibility"]["provides"]:
        record["outcome"] = "REFUSED"
        record["why"] = (
            "G0-1 fails: this core build still sets "
            "ENABLE_WASM_STRIP_ACCESSIBILITY, so SwEditWin::CreateAccessible "
            "returns {} and there is nothing for the gate to measure. Apply "
            "handoff/a11y-gate-0/PATCH.md and rebuild core first. A run here "
            "would produce a number about the patch not having been applied.")
        if not args.i_know_the_macro_is_set:
            return finish(record, args)
        record["outcome"] = "UNMEASURABLE"

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(PROJECT / "dist")],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
    session = session_class("cold")
    try:
        navigate(session, base)
        state = wait_until(session, lambda s: s.get("state") == "ready", 180)
        record["booted"] = state.get("state")
        if state.get("state") != "ready":
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = "the page never reached ready"
            return finish(record, args)

        # THREE paragraphs, and three is the point (PREDICTION G0-2).  One
        # reading cannot tell "a focused paragraph" from "an event that fires":
        # a callback reporting the same thing everywhere would pass a
        # single-placement check.  This is the positive control, and it is here
        # because three checks on 2026-08-21 passed or abstained for want of one.
        scan, bands = stable_bands(session)
        targets = [b for b in bands if (b["last"] - b["first"]) > 40][:3]
        record["bandsFound"] = len(bands)
        record["targetsUsed"] = len(targets)
        if len(targets) < 3:
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = ("fewer than three text bands to aim at, so the "
                             "readings cannot be shown to differ BY PARAGRAPH")
            return finish(record, args)

        for index, band in enumerate(targets):
            ink = evaluate(session, LINE_INK.replace(
                "ARG_Y", f"{band['centreFraction']:.5f}")) or {}
            clicks = caret_click_fractions(ink)
            place_caret_and_settle(session, POINT_AT, clicks["near"],
                                   f"{band['centreFraction']:.5f}")
            time.sleep(1.0)
            record["placements"].append({
                "index": index,
                "yFraction": round(band["centreFraction"], 5),
                "state": (wait_until(session, lambda s: True, 5) or {}).get("state"),
                "a11y": evaluate(session, READ_A11Y),
            })

        record["outcome"] = record.get("outcome") or "SEE_PLACEMENTS"
        record["howToJudge"] = (
            "PASS requires >= 2 DISTINCT paragraph identities across the three "
            "placements, each matching the paragraph actually targeted. A "
            "callback that fires with the same reading every time is an event, "
            "not a focused paragraph. FAIL = no callback, nothing "
            "paragraph-shaped, or one reading for all three. On FAIL: STOP "
            "(roadmap 3.3) -- do not start the shell half, and report the "
            "result to M3's positioning.")
        record["doNotConclude"] = (
            "If nothing comes back, 'core does not support it' is ONE "
            "hypothesis. Check first that the engine enabled it "
            "(`enabled`/`unavailable`) and that the worker FORWARDS the field "
            "-- an engine field nobody forwards does not exist, and that has "
            "bitten this tree twice in one afternoon. Do not name a layer "
            "without measuring it (040, 048, 062).")
    finally:
        try:
            if session is not None:
                session.close()
        finally:
            server.terminate()
    return finish(record, args)


def wait_until(session, predicate, timeout, poll=0.5):
    deadline = time.monotonic() + timeout
    state = evaluate(session, READ_STATE) or {}
    while time.monotonic() < deadline:
        if predicate(state):
            return state
        time.sleep(poll)
        state = evaluate(session, READ_STATE) or {}
    return state


def finish(record: dict, args) -> int:
    text = json.dumps(record, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
