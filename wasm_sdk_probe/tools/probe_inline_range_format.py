#!/usr/bin/env python3
"""Can the engine apply an inline format to a SELECTION, and to exactly it?

FINDING 078. The shipped manifest offers `set-bold`, `set-italic`,
`set-underline` and `set-strikethrough` for `collapsed` only, so a user who
selects text and presses bold is refused before dispatch. That restriction is
honest -- range dispatch was characterised for the PARAGRAPH actions and not for
these, and `build_e2_b_profile.py` declines to declare a gesture nobody
measured.

This is that measurement. It runs against `e2-inline-range`, a diagnostic
profile packaged from the SHIPPED v4 artifact -- byte-identical loader, wasm and
worker, `f923cfa5...` -- with the range gestures granted in the manifest and
nowhere else. No relink: the binary already implements the dispatch, the mask
withheld it, and that asymmetry is what makes this measurable at all.

THE ORACLE DOES NOT COME FROM THE PAGE. Two independent paths have to agree:

  * how many characters are selected -- from the ENGINE, through the product's
    copy path, which reports `已複製 N 字`;
  * how many characters came back bold -- from the SAVED DOCUMENT's own
    content.xml, parsed here.

Deliberately NOT `inline_styles_of()`. That helper is what lied in findings 064
and 065 (blind to paragraph-level formatting), and every conclusion downstream
of it was wrong for a day. A question about a document is answered from the
document.

Usage:
  probe_inline_range_format.py [--profile e2-inline-range] [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402
from probe_a11y_gate0 import gate_mirror, wait_until  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
# ONE parser, in the runner, because a second copy is a second
# thing to be wrong on its own -- and on 2026-08-23 this one was
# wrong three times before it was right.
from run_e2_c_product_path import (  # noqa: E402
    FORMAT_PROPERTY, formatted_paragraphs, formatted_runs)

PROJECT = Path(__file__).resolve().parent.parent

def selected_count(session) -> dict:
    """How many characters the ENGINE says are selected.

    Through the product's own copy path, whose toast is written from the
    engine's answer (`copySelection()`), not from any DOM selection -- a canvas
    has none.
    """
    evaluate(session, pp.CLEAR_TOAST)
    ran = evaluate(session, pp.COPY)
    deadline = time.monotonic() + 20
    toast = ""
    while time.monotonic() < deadline:
        toast = evaluate(session, pp.READ_TOAST) or ""
        if toast:
            break
        time.sleep(0.3)
    # THE TOAST LISTS CODE POINTS, not a count.  The runner's comment says
    # `已複製 N 字` and that is out of date for this build -- measured
    # 2026-08-23: `已複製 U+0031,U+002D,U+004C,... 字`.  Counting the entries is
    # the same number and is checkable, which quoting a stale comment is not.
    points = re.findall(r"U\+([0-9A-Fa-f]{4,6})", toast)
    count = re.search(r"已複製\s*(\d+)\s*字", toast)
    return {"handlerRan": (ran or {}).get("handlerRan"),
            "toast": toast,
            "codePoints": len(points),
            "codePointsSeen": [chr(int(p, 16)) for p in points],
            "characters": (int(count.group(1)) if count
                           else (len(points) or None))}


def arm(session, label: str, x1, y1, x2, y2, action: str,
        save_index: int) -> dict:
    record: dict = {"label": label, "action": action,
                    "drag": {"from": [x1, y1], "to": [x2, y2]}}
    evaluate(session, pp.DRAG.replace("ARG_X1", x1).replace("ARG_Y1", y1)
             .replace("ARG_X2", x2).replace("ARG_Y2", y2))
    time.sleep(1.5)
    record["selection"] = selected_count(session)

    label_text = evaluate(session, pp.BUTTON_LABEL.replace("ARG_ACTION", action))
    record["buttonLabel"] = label_text
    record["buttonOffered"] = evaluate(
        session,
        "(() => { const b = document.querySelector('#toolbar "
        f"button[data-action=\"{action}\"]'); "
        "return b ? !b.disabled : null; })()")
    evaluate(session, pp.CLEAR_TOAST)
    evaluate(session, pp.CLEAR_LATENCY)
    evaluate(session, pp.PRESS.replace("ARG_ACTION", action))
    settled = pp.wait_for(
        session,
        lambda st, want=label_text: bool(want)
        and want in (st.get("latency") or ""), 30)
    record["latency"] = (settled or {}).get("latency")
    record["toast"] = evaluate(session, pp.READ_TOAST) or ""
    # A refusal is a RESULT here, not an error: it is what the shipped manifest
    # produces and what the operator hit.
    record["refused"] = "GESTURE_UNSUPPORTED" in record["toast"]

    saved = pp.capture_save(session, save_index)
    record["savedIsOdt"] = pp.is_an_odt(saved)
    content = saved.get("content") or ""
    record["formattedRuns"] = formatted_runs(content, action)
    record["formattedCharacters"] = sum(r["length"] for r in record["formattedRuns"])
    # Both, always. "No bold span" and "the whole paragraph went bold" are
    # different answers and only one of them is "not applied".
    record["formattedParagraphs"] = formatted_paragraphs(content, action)
    record["formattedParagraphCharacters"] = sum(
        r["length"] for r in record["formattedParagraphs"])
    # COMPARE THE TEXT, NOT THE COUNT.
    #
    # Counting was wrong twice in one hour. The engine's selection text carries
    # things that are not document text: a 5-character LIST PREFIX on the first
    # paragraph when the selection crosses paragraphs (and not when it does
    # not -- measured 2026-08-23), and a `\n` where one paragraph ends and the
    # next begins. Against `E1-LC-NUMBER-TWO`, whose fixture text has no
    # leading spaces at all, the copy path returned five of them.
    #
    # So a count-based oracle reported 24 bold characters against 30 selected
    # and read as "range-cross under-applies by a quarter". Nothing was
    # under-applied: 30 - 5 prefix - 1 separator = 24, exactly.
    #
    # The bold TEXT compared to the selected TEXT cannot be fooled that way:
    # both are strings, and the separators are named rather than counted.
    selected = "".join(record["selection"].get("codePointsSeen") or [])
    bold_text = "".join(r["text"] for r in record["formattedRuns"]) + "".join(
        r["text"] for r in record["formattedParagraphs"])
    def squeeze(value: str) -> str:
        return re.sub(r"\s+", "", value)
    record["selectedText"] = selected
    record["formattedText"] = bold_text
    record["appliedToExactlyTheSelection"] = bool(
        bold_text and squeeze(bold_text) == squeeze(selected))
    record["boldTextIsInsideTheSelection"] = bool(
        bold_text and squeeze(bold_text) in squeeze(selected))
    record["appliedToWholeParagraphs"] = bool(record["formattedParagraphs"])
    record["why"] = (
        "the bold TEXT is compared to the selected TEXT, whitespace squeezed, "
        "because the engine's selection string carries a list prefix and a "
        "paragraph separator that are not document text and a count cannot "
        "tell them from characters that are. A fully selected paragraph comes "
        "back as paragraph-level bold rather than a span, which is why both "
        "are concatenated")
    return record


# WHAT THE NORMALISATION CAN AND CANNOT HIDE.
#
# The oracle squeezes whitespace before comparing, and that is an INSTRUMENT
# ACCOMMODATION of a quirk nobody has explained: the engine's selection string
# carries a 5-character list prefix when the selection crosses paragraphs, plus
# a `\n` separator, and neither is document text.  An accommodation that can
# mask the defect class it accommodates is how this same oracle produced two
# wrong conclusions in one afternoon, so it gets a table rather than a promise.
#
# The result, run by `--self-test`: squeezing hides ONLY differences that are
# purely whitespace.  A dropped word, a dropped character and an extra
# character all still fail.
#
# THE NAMED LIMIT: a format that covered two words but not the space between
# them would be called equal here.  Nothing has measured whether that shape can
# occur, and this oracle would not see it.
NORMALISATION_CASES = [
    ("applied in full", "1-LC-NUMBER-TWOE1-LC-END", True),
    ("second paragraph dropped", "1-LC-NUMBER-TWO", False),
    ("first paragraph dropped", "E1-LC-END", False),
    ("one character dropped", "1-LC-NUMBER-TWE1-LC-END", False),
    ("one character too many", "1-LC-NUMBER-TWOXE1-LC-END", False),
    ("differs only in whitespace", "1-LC-NUMBER-TWO E1-LC-END", True),
]
NORMALISATION_SELECTION = "     1-LC-NUMBER-TWO\nE1-LC-END"


def self_test() -> int:
    squeeze = lambda v: re.sub(r"\s+", "", v)     # noqa: E731
    failures = 0
    print("can the whitespace normalisation hide a real miss?")
    for label, got, expected in NORMALISATION_CASES:
        equal = squeeze(got) == squeeze(NORMALISATION_SELECTION)
        ok = equal == expected
        failures += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'} {label}: judged "
              f"{'equal' if equal else 'different'}")
    print("  NAMED LIMIT: a difference that is only whitespace is invisible "
          "to this oracle, deliberately, and nothing has measured whether a "
          "format can miss a space between two words it covered")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="e2-inline-range")
    ap.add_argument("--action", default="set-bold")
    ap.add_argument("--out", default=None)
    ap.add_argument("--self-test", action="store_true",
                    help="check what the oracle's whitespace normalisation can "
                         "and cannot hide, and run nothing else")
    args = ap.parse_args()

    if args.self_test:
        failures = self_test()
        print("self-test", "ok" if not failures else "FAILED")
        return 1 if failures else 0

    record: dict = {
        "schemaVersion": 1,
        "release": "inline-range-format-characterisation",
        "finding": "078",
        "profile": args.profile,
        "question": "does an inline format applied to a SELECTION land on "
                    "exactly that selection?",
        "arms": [],
    }
    scratch = Path(tempfile.mkdtemp(prefix="inline-range-"))
    record["mirror"] = gate_mirror(scratch, args.profile)
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", record["mirror"]["root"]],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session = ChromeSession("cold")
    try:
        # Before navigating, so the page never sees a denied clipboard.  The
        # selection count comes through the copy path, and without both the
        # permission AND focus emulation the write is refused for a reason that
        # has nothing to do with what is selected -- the toast then says
        # CLIPBOARD_DENIED and carries no number.
        call = getattr(session, "call", None)
        if call is not None:
            try:
                call("Browser.grantPermissions",
                     {"origin": f"http://127.0.0.1:{port}",
                      "permissions": ["clipboardReadWrite",
                                      "clipboardSanitizedWrite"]})
                call("Emulation.setFocusEmulationEnabled", {"enabled": True})
                record["clipboardPermission"] = {"granted": True,
                                                 "focusEmulated": True}
            except Exception as error:      # noqa: BLE001 -- reported, not raised
                record["clipboardPermission"] = {
                    "granted": False, "why": f"{type(error).__name__}: {error}"}
        else:
            record["clipboardPermission"] = {"granted": False,
                                             "why": "no CDP on this session"}
        navigate(session, base)
        state = wait_until(session, lambda s: s.get("state") == "ready", 180)
        if state.get("state") != "ready":
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = "the page never reached ready"
            return finish(record, args)
        # THE SAVE SHIM, without which `capture_save` reports nothing and the
        # document side of every arm silently reads as "no bold".  The first run
        # of this probe did exactly that: `savedIsOdt: False` on both arms and
        # zero bold runs, which looks like "the format did not apply" and was
        # really "nobody was capturing the download".
        record["shimInstalled"] = evaluate(session, pp.INSTALL)
        record["shims"] = ["URL.createObjectURL", "HTMLAnchorElement.click"]
        time.sleep(1.5)

        # THE BEFORE-PICTURE, and its absence made the first run unreadable.
        #
        # Both diagnostic arms reported 37 characters of PARAGRAPH-level bold
        # while the shipped control reported none -- which reads as "the press
        # also emboldened two unrelated list paragraphs". It cannot be read that
        # way: the shipped control refused both presses, so its save is the
        # pristine fixture, and nothing had ever measured what this fixture
        # carries before anything is pressed. Two runs, one difference, and the
        # difference was doing two jobs.
        #
        # A save with nothing pressed answers it inside one run.
        baseline = pp.capture_save(session, 0)
        record["baseline"] = {
            "savedIsOdt": pp.is_an_odt(baseline),
            "formattedRuns": formatted_runs(baseline.get("content") or "", args.action),
            "formattedParagraphs": formatted_paragraphs(baseline.get("content") or "", args.action),
        }
        record["baseline"]["formattedCharacters"] = sum(
            r["length"] for r in record["baseline"]["formattedRuns"])
        record["baseline"]["formattedParagraphCharacters"] = sum(
            r["length"] for r in record["baseline"]["formattedParagraphs"])

        # RANGE-SINGLE: inside one line.
        record["arms"].append(arm(session, "range-single",
                                  "0.14", "0.28", "0.30", "0.28",
                                  args.action, 1))
        # RANGE-CROSS: from one line into the next.
        record["arms"].append(arm(session, "range-cross",
                                  "0.14", "0.28", "0.30", "0.34",
                                  args.action, 2))
        record["outcome"] = "SEE_ARMS"
    finally:
        try:
            session.close()
        finally:
            server.terminate()
    return finish(record, args)


def finish(record: dict, args) -> int:
    text = json.dumps(record, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
