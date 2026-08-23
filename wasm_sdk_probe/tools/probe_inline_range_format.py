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

PROJECT = Path(__file__).resolve().parent.parent

BOLD_WEIGHTS = ("bold", "600", "700", "800", "900")


def _weights_by_style(content: str, family: str) -> tuple[dict, dict]:
    """`style:name` -> `fo:font-weight`, for one style family.

    SELF-CLOSING STYLES ARE THE WHOLE REASON THIS IS A FUNCTION, and the first
    version of it produced a false defect within the hour. `<style:style
    ... style:family="paragraph" .../>` has no `</style:style>`, so a pattern
    that scans for the closing tag runs PAST it, through the next styles, and
    attributes THEIR `fo:font-weight` to it. Measured 2026-08-23: two list
    paragraphs whose style is `<... style:list-style-name="E1LCBullet"/>` -- no
    text properties at all -- were reported bold, because the scan reached a
    later text style that was.

    That read as "applying bold to a selection also emboldens two unrelated
    paragraphs", which is a serious defect, and it was not happening. What
    caught it was putting the style's own markup into the record beside the
    verdict; what did NOT catch it was the unit test, because the synthetic
    document I wrote for it contained no self-closing style.

    So: match each element in BOTH forms, and never let one style's body be read
    as another's.
    """
    weights: dict[str, str] = {}
    sources: dict[str, str] = {}
    for match in re.finditer(
            r"<style:style\b([^>]*?)(?:/>|>(.*?)</style:style>)",
            content, re.S):
        attrs, body = match.group(1), match.group(2) or ""
        if f'style:family="{family}"' not in attrs:
            continue
        name = re.search(r'style:name="([^"]+)"', attrs)
        if not name:
            continue
        weight = re.search(r'fo:font-weight="([^"]+)"', body)
        if weight:
            weights[name.group(1)] = weight.group(1)
            sources[name.group(1)] = match.group(0)[:600]
    return weights, sources


def bold_runs(content: str) -> list[dict]:
    """Every text:span in the document whose style is bold, with its text.

    Read from the document, not from a marker lookup: the style name is
    resolved through the automatic styles the save itself wrote, so a run is
    called bold because its own style says so.

    Deliberately NOT `inline_styles_of()`, which is what lied in findings 064
    and 065 -- a question about a document is answered from the document.
    """
    weights, sources = _weights_by_style(content, "text")
    runs = []
    for match in re.finditer(
            r'<text:span[^>]*text:style-name="([^"]+)"[^>]*>(.*?)</text:span>',
            content, re.S):
        style, inner = match.group(1), match.group(2)
        if weights.get(style) not in BOLD_WEIGHTS:
            continue
        text = re.sub(r"<[^>]+>", "", inner)
        runs.append({"styleName": style, "weight": weights.get(style),
                     "text": text, "length": len(text),
                     "styleSource": sources.get(style)})
    return runs


def bold_paragraphs(content: str) -> list[dict]:
    """Paragraphs whose OWN style is bold, with their text.

    THE FALSE NEGATIVE THIS EXISTS TO PREVENT: if the engine applies the format
    to the whole PARAGRAPH instead of to the selection, no text:span carries
    bold, `bold_runs` returns [], and the reading is "not applied" -- when what
    happened is worse than not applied. Finding 065's shape exactly.
    """
    weights, sources = _weights_by_style(content, "paragraph")
    out = []
    for match in re.finditer(
            r'<text:p[^>]*text:style-name="([^"]+)"[^>]*>(.*?)</text:p>',
            content, re.S):
        style, inner = match.group(1), match.group(2)
        if weights.get(style) not in BOLD_WEIGHTS:
            continue
        text = re.sub(r"<[^>]+>", "", inner)
        out.append({"styleName": style, "weight": weights.get(style),
                    "text": text, "length": len(text),
                    "styleSource": sources.get(style)})
    return out


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
    record["boldRuns"] = bold_runs(content)
    record["boldCharacters"] = sum(r["length"] for r in record["boldRuns"])
    # Both, always. "No bold span" and "the whole paragraph went bold" are
    # different answers and only one of them is "not applied".
    record["boldParagraphs"] = bold_paragraphs(content)
    record["boldParagraphCharacters"] = sum(
        r["length"] for r in record["boldParagraphs"])
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
    bold_text = "".join(r["text"] for r in record["boldRuns"]) + "".join(
        r["text"] for r in record["boldParagraphs"])
    def squeeze(value: str) -> str:
        return re.sub(r"\s+", "", value)
    record["selectedText"] = selected
    record["boldText"] = bold_text
    record["appliedToExactlyTheSelection"] = bool(
        bold_text and squeeze(bold_text) == squeeze(selected))
    record["boldTextIsInsideTheSelection"] = bool(
        bold_text and squeeze(bold_text) in squeeze(selected))
    record["appliedToWholeParagraphs"] = bool(record["boldParagraphs"])
    record["why"] = (
        "the bold TEXT is compared to the selected TEXT, whitespace squeezed, "
        "because the engine's selection string carries a list prefix and a "
        "paragraph separator that are not document text and a count cannot "
        "tell them from characters that are. A fully selected paragraph comes "
        "back as paragraph-level bold rather than a span, which is why both "
        "are concatenated")
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="e2-inline-range")
    ap.add_argument("--action", default="set-bold")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

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
            "boldRuns": bold_runs(baseline.get("content") or ""),
            "boldParagraphs": bold_paragraphs(baseline.get("content") or ""),
        }
        record["baseline"]["boldCharacters"] = sum(
            r["length"] for r in record["baseline"]["boldRuns"])
        record["baseline"]["boldParagraphCharacters"] = sum(
            r["length"] for r in record["baseline"]["boldParagraphs"])

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
