#!/usr/bin/env python3
"""What shape does the PAGE think the selection is, and when does it think it?

FINDING 079.  The page keeps `lastSelectionShape` in a module variable and the
toolbar decides `button.disabled` from it.  The finding was raised INDIRECTLY:
a mutation that returned early when the shape was not `collapsed` never fired,
on two runs, which is consistent with the shape being stale at press time --
and equally consistent with the mutation not being installed, with the press
taking another path, or with the drag never producing a selection at all.  All
four look the same from outside, and the finding says so.

This probe replaces that inference with an observation, and it observes BOTH
sides inside one arm:

  * what the PAGE believes -- read out of the toolbar, which is the only place
    `lastSelectionShape` is legible from outside.  `updateGestureAffordance()`
    writes `manifest 沒有為「SHAPE」宣告這個動作` into the title of every button
    it disables, so a disabled caret-only button NAMES the shape the page
    holds, and an enabled one says the page holds `collapsed`;
  * what the ENGINE believes -- through the product's own copy path, whose
    toast is written from `copySelection()` and therefore from the engine.  A
    canvas has no DOM selection, so nothing else in the page could answer.

Recording both in the same arm is the rule this tree keeps re-learning: on
2026-08-23 five conclusions were signed with a measurement of something else,
and the two that were caught were caught by putting both sides in one record.

WHAT THE FINDING PREDICTED, AND WHY THIS PROBE DOES NOT TEST IT
--------------------------------------------------------------
079 predicted the visible cost would land on `delete-selection`: offered for
ranges only, so a stale `collapsed` would show it DISABLED when it is
available.  That prediction is unreachable, and reading the page says so
without a browser: `lastSelectionShape` is read in exactly ONE place
(`updateGestureAffordance`), which only touches `#toolbar button[data-action]`,
and there IS no delete-selection button.  Its only dispatch site is the cut
handler, which asks `session.offers("delete-selection")` -- the manifest, not
the shape.

The cost lands on the OTHER side of the same gate.  Six buttons are offered for
`collapsed` only (the two character moves, the two deletes, the two breaks), so
a stale `collapsed` leaves all six ENABLED while a range is selected, and the
engine's mask refuses them.  Same defect, inverted, on buttons that exist.

THE TIMING IS THE POINT
-----------------------
"Never updated", "updated too late" and "updated then reset" produce the same
still photograph.  The sampler runs INSIDE the page, from the moment the
pointer goes down, and records a row whenever the toolbar changes -- so a shape
that arrives at 900 ms is distinguishable from one that never arrives, without
paying a CDP round trip per sample (finding 048 measured those at 22-28 ms,
which is the resolution the question needs).

POSITIVE CONTROL
----------------
`--positive-control` serves a mirror whose only difference is the INITIAL value
of `lastSelectionShape`, set to `range-single`.  If the toolbar read cannot
show a range shape there, then a run reporting `collapsed` everywhere is
reporting about the instrument.  Every "X did not happen" arm in this tree owes
one of these; three were missed in a single day for want of it.

Usage:
  probe_079_selection_shape.py [--out FILE] [--positive-control]
                               [--window-ms 8000]
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
from probe_a11y_gate0 import wait_until  # noqa: E402
from probe_inline_range_format import selected_count  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

# The title `updateGestureAffordance()` writes on a button it greys out.  Read
# rather than assumed: this probe's whole page-side reading rests on it, so the
# regex is checked against the page's source before the browser starts.
TITLE_PATTERN = re.compile(r"沒有為「(.+?)」宣告")
TITLE_SOURCE = re.compile(r"manifest 沒有為「\$\{lastSelectionShape\}」宣告")

# Offered for `collapsed` only on every profile from v1 to v7.  Enabled while a
# range is selected means the page believes the selection is collapsed.
CARET_ONLY = ["move-character-left", "move-character-right",
              "delete-backward", "delete-forward",
              "insert-paragraph-break", "insert-line-break"]

# One evaluate call: start sampling, then dispatch the drag.  t0 is taken
# immediately before `pointerdown`, so every row's `t` is measured from the
# gesture and not from when Python got around to asking.
#
# A row is kept only when the toolbar CHANGES (plus the first and the last), so
# an eight-second window is a transition log rather than 160 copies of one
# answer.
DRAG_AND_SAMPLE = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const at = (fx, fy) => ({ x: box.left + box.width * fx, y: box.top + box.height * fy });
const a = at(ARG_X1, ARG_Y1);
const b = at(ARG_X2, ARG_Y2);
const read = () => [...document.querySelectorAll('#toolbar button[data-action]')]
  .map((el) => ({ action: el.dataset.action, disabled: el.disabled, title: el.title }));
const key = (bs) => bs.map((x) => x.action + (x.disabled ? '!' : '.') + x.title).join('|');
const store = { t0: performance.now(), rows: [], lastKey: null, done: false };
globalThis.__f079 = store;
const tick = (why) => {
  const buttons = read();
  const k = key(buttons);
  if (k === store.lastKey && why === 'poll') return;
  store.lastKey = k;
  store.rows.push({
    t: Math.round(performance.now() - store.t0), why, buttons,
    latency: document.querySelector('#s-latency').textContent,
    pending: document.querySelector('#s-pending').textContent,
    state: document.querySelector('#state-pill').dataset.state,
  });
};
const send = (type, point, buttons) => canvas.dispatchEvent(new PointerEvent(type, {
  clientX: point.x, clientY: point.y, button: 0, buttons, pointerId: 1, bubbles: true }));
tick('before');
send('pointerdown', a, 1);
tick('after-pointerdown');
send('pointermove', { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, 1);
send('pointermove', b, 1);
send('pointerup', b, 0);
tick('after-pointerup');
const timer = setInterval(() => tick('poll'), 50);
setTimeout(() => { clearInterval(timer); tick('last'); store.done = true; }, ARG_MS);
return { started: true, rows: store.rows.length };
})()"""

# A CLICK, not a drag -- the control that proves the instrument can read
# `collapsed` and that the toolbar is being updated at all.  Same sampler.
CLICK_AND_SAMPLE = DRAG_AND_SAMPLE  # same script; the caller passes x2 == x1.

READ_SAMPLES = "(() => globalThis.__f079 || null)()"

# THE PAGE'S OWN INPUT, put into the record.
#
# `pumpDrag` computes the shape from two fields of whatever `session
# .selectRange()` resolves to.  Reading the source says which fields; only the
# browser says whether the resolved object HAS them, and the difference decides
# whether 079 is a staleness (a value that fails to refresh) or an absence (a
# value computed from `undefined`, which is `collapsed` by construction).  Two
# findings were retracted in this tree on 2026-08-23 for judging a parser
# without recording what it read.
#
# `--capture-result` mirrors the served page with ONE added line.  Nothing else
# differs, and everything this mode reports is stamped diagnostic.
CAPTURE_BEFORE = """    const result = await session.selectRange(drag.start, end);"""
CAPTURE_AFTER = """    const result = await session.selectRange(drag.start, end);
    try {
      globalThis.__f079result = {
        keys: result === null || result === undefined ? null : Object.keys(result),
        typeName: Object.prototype.toString.call(result),
        collapsed: result?.collapsed, collapsedType: typeof result?.collapsed,
        rectanglesType: typeof result?.rectangles,
        rectangleCount: Array.isArray(result?.rectangles) ? result.rectangles.length : null,
        json: JSON.parse(JSON.stringify(result ?? null)),
      };
    } catch (error) { globalThis.__f079result = { error: String(error) }; }"""
READ_RESULT = "(() => globalThis.__f079result || null)()"


def shape_of(buttons: list[dict]) -> dict:
    """What the page believes, derived from the toolbar it drew.

    Two independent readings, reported side by side rather than collapsed into
    one answer, because they can disagree and a disagreement is information:

      * `named` -- the shape spelled out in the title of any button the page
        disabled.  Only available when SOMETHING is disabled.
      * `implied` -- `collapsed` when every caret-only button is enabled.

    The raw buttons travel with them.  A derivation whose input is not in the
    record is a derivation nobody downstream can check, and this tree retracted
    two findings in one day for exactly that.
    """
    by_action = {b["action"]: b for b in buttons}
    named = sorted({m.group(1) for b in buttons
                    if (m := TITLE_PATTERN.search(b.get("title") or ""))})
    present = [a for a in CARET_ONLY if a in by_action]
    enabled = [a for a in present if not by_action[a]["disabled"]]
    disabled = [a for a in present if by_action[a]["disabled"]]
    implied = None
    if present and not disabled:
        implied = "collapsed"
    elif present and not enabled:
        implied = "a-range"        # which one is only knowable from `named`
    return {
        "namedInTitles": named,
        "impliedByCaretOnlyButtons": implied,
        "caretOnlyPresent": present,
        "caretOnlyEnabled": enabled,
        "caretOnlyDisabled": disabled,
    }


def arm(session, label: str, x1, y1, x2, y2, window_ms: int) -> dict:
    record: dict = {"label": label,
                    "drag": {"from": [x1, y1], "to": [x2, y2]}}
    script = (DRAG_AND_SAMPLE.replace("ARG_X1", x1).replace("ARG_Y1", y1)
              .replace("ARG_X2", x2).replace("ARG_Y2", y2)
              .replace("ARG_MS", str(window_ms)))
    record["started"] = evaluate(session, script)
    # Wait out the page's own window, then read it in one call.
    deadline = time.monotonic() + (window_ms / 1000.0) + 15
    store = None
    while time.monotonic() < deadline:
        store = evaluate(session, READ_SAMPLES)
        if store and store.get("done"):
            break
        time.sleep(0.4)
    record["sampleWindowClosed"] = bool((store or {}).get("done"))
    rows = (store or {}).get("rows") or []
    record["rows"] = [{**row, "shape": shape_of(row["buttons"])} for row in rows]
    record["transitions"] = len(rows)
    # THE PAGE'S ANSWER AT THE END OF THE WINDOW, which is what a user pressing
    # a button a second after letting go of the mouse would meet.
    record["pageShapeAtEnd"] = (record["rows"][-1]["shape"]
                                if record["rows"] else None)
    # `before` is excluded: the arms share one page, so that row still carries
    # the PREVIOUS arm's shape and counting it reported "0 ms" for a belief that
    # predates the gesture being measured.
    record["firstNonCollapsedAtMs"] = next(
        (row["t"] for row in record["rows"]
         if row["why"] != "before"
         and row["shape"]["impliedByCaretOnlyButtons"] not in (None, "collapsed")),
        None)
    record["shapeCarriedInFromThePreviousArm"] = bool(
        record["rows"]
        and record["rows"][0]["why"] == "before"
        and record["rows"][0]["shape"]["impliedByCaretOnlyButtons"] != "collapsed")
    # THE ENGINE'S ANSWER, in the same arm.  Taken after the window so the copy
    # dispatch cannot be what moved the toolbar mid-sample.
    record["engineSelection"] = selected_count(session)
    engine_chars = record["engineSelection"].get("codePoints") or 0
    record["engineHasARange"] = engine_chars > 0
    page_says_collapsed = (
        (record["pageShapeAtEnd"] or {}).get("impliedByCaretOnlyButtons")
        == "collapsed")
    record["pageSaysCollapsed"] = page_says_collapsed
    # THE FINDING'S CLAIM, as a single boolean, stated so it can be false.
    record["staleShape"] = bool(record["engineHasARange"] and page_says_collapsed)
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--window-ms", type=int, default=8000)
    ap.add_argument("--capture-result", action="store_true",
                    help="mirror the page with one added line that records "
                         "what session.selectRange() actually resolves to, and "
                         "report its keys. Answers whether the shape is stale "
                         "or computed from fields that are not there")
    ap.add_argument("--positive-control", action="store_true",
                    help="serve a mirror whose lastSelectionShape STARTS as "
                         "range-single, to prove the toolbar read can show a "
                         "range shape at all")
    args = ap.parse_args()

    record: dict = {
        "schemaVersion": 1,
        "release": "f079-selection-shape",
        "finding": "079",
        "question": "after a real drag through the page's own pointer "
                    "handlers, what shape does the page believe it has, when "
                    "does it believe it, and does the engine agree?",
        "positiveControl": bool(args.positive_control),
        "arms": [],
    }

    root = PROJECT / "dist"
    page_rel = "e2-editor-app.js"
    page_source = (root / page_rel).read_text(encoding="utf-8")
    # The title format this probe reads out of the DOM, checked against the
    # source that writes it.  If the page stops writing the shape into the
    # title, `namedInTitles` goes quietly empty and every arm still reports --
    # about nothing.
    record["titleFormatFoundInPage"] = bool(TITLE_SOURCE.search(page_source))
    record["profile"] = pp.product_profile(root)

    scratch = Path(tempfile.mkdtemp(prefix="f079-"))
    if args.capture_result:
        if page_source.count(CAPTURE_BEFORE) != 1:
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = ("the selectRange call in pumpDrag is not where "
                             "this capture expected it, so the mirror would "
                             "differ from the shipped page in a way this run "
                             "cannot name")
            return finish(record, args)
        mirror = scratch / "capture-root"
        pp.build_mirror(root, mirror,
                        {page_rel: page_source.replace(
                            CAPTURE_BEFORE, CAPTURE_AFTER, 1).encode("utf-8")})
        root = mirror
        record["captureDiagnostic"] = {
            "evidenceClass": "diagnostic",
            "note": "This run did NOT use the shipped page. One statement was "
                    "added after the selectRange await to record its resolved "
                    "value. It reads; it changes nothing the page decides.",
        }
    elif args.positive_control:
        before = 'let lastSelectionShape = "collapsed";'
        if before not in page_source:
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = ("the initial value of lastSelectionShape is not "
                             "where this control expected it, so the mirror "
                             "would differ from the shipped page in some way "
                             "this run cannot name")
            return finish(record, args)
        mirror = scratch / "control-root"
        pp.build_mirror(root, mirror,
                        {page_rel: page_source.replace(
                            before, 'let lastSelectionShape = "range-single";',
                            1).encode("utf-8")})
        root = mirror
        record["controlDiagnostic"] = {
            "evidenceClass": "diagnostic",
            "note": "This run did NOT use the shipped page. One line differs: "
                    "lastSelectionShape starts as range-single. Nothing here "
                    "is a statement about the product.",
        }

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session = ChromeSession("cold")
    try:
        call = getattr(session, "call", None)
        if call is not None:
            try:
                call("Browser.grantPermissions",
                     {"origin": f"http://127.0.0.1:{port}",
                      "permissions": ["clipboardReadWrite",
                                      "clipboardSanitizedWrite"]})
                call("Emulation.setFocusEmulationEnabled", {"enabled": True})
                record["clipboardPermission"] = {"granted": True}
            except Exception as error:      # noqa: BLE001 -- reported, not raised
                record["clipboardPermission"] = {
                    "granted": False, "why": f"{type(error).__name__}: {error}"}
        navigate(session, base)
        state = wait_until(session, lambda s: s.get("state") == "ready", 180)
        if state.get("state") != "ready":
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = "the page never reached ready"
            return finish(record, args)

        if args.capture_result:
            scan, bands = pp.stable_bands(session)
            wide = [b for b in bands if (b["last"] - b["first"]) > 60]
            if not wide:
                record["outcome"] = "NOT_ESTABLISHED"
                record["why"] = "no band wide enough to drag inside of"
                return finish(record, args)
            band = wide[len(wide) // 2]
            other = wide[(len(wide) // 2) + 1] if len(wide) > 1 else None
            left = band["first"] / scan["width"]
            right = band["last"] / scan["width"]
            y = f"{band['centreFraction']:.5f}"
            x1 = f"{left + (right - left) * 0.15:.5f}"
            x2 = f"{left + (right - left) * 0.70:.5f}"
            drags = [("within-one-line", x1, y, x2, y)]
            if other is not None:
                # BOTH SHAPES, because the branch that reads `rectangles` is a
                # different read from the one that reads `collapsed`, and a
                # within-line drag exercises only the second.
                drags.append(("across-two-lines", x1, y,
                              f"{(other['first'] / scan['width']) + 0.10:.5f}",
                              f"{other['centreFraction']:.5f}"))
            for label, ax, ay, bx, by in drags:
                evaluate(session, "(() => { globalThis.__f079result = null; "
                                  "return true; })()")
                evaluate(session, pp.DRAG.replace("ARG_X1", ax)
                         .replace("ARG_Y1", ay).replace("ARG_X2", bx)
                         .replace("ARG_Y2", by))
                deadline = time.monotonic() + 30
                resolved = None
                while time.monotonic() < deadline:
                    resolved = evaluate(session, READ_RESULT)
                    if resolved:
                        break
                    time.sleep(0.5)
                nested = ((resolved or {}).get("json") or {}).get("state", {})
                nested = (nested or {}).get("selection") or {}
                record["arms"].append({
                    "label": f"what-selectRange-resolves-to--{label}",
                    "drag": {"from": [ax, ay], "to": [bx, by]},
                    "resolved": resolved,
                    "engineSelection": selected_count(session),
                    # The page's two reads, evaluated here on the recorded
                    # object rather than described in prose.
                    "pageWouldSee": None if not resolved else {
                        "rectanglesLengthOrZero": resolved.get("rectangleCount") or 0,
                        "collapsedIsExactlyFalse": resolved.get("collapsed") is False,
                        "thereforeShape":
                            "range-cross" if (resolved.get("rectangleCount") or 0) > 1
                            else ("range-single" if resolved.get("collapsed") is False
                                  else "collapsed"),
                    },
                    # WHERE THE FIELDS ACTUALLY ARE.
                    "nestedSelection": {
                        "present": bool(nested),
                        "collapsed": nested.get("collapsed"),
                        "rectangleCount": (len(nested["rectangles"])
                                           if isinstance(nested.get("rectangles"), list)
                                           else None),
                        "observed": nested.get("observed"),
                    },
                    "shapeIfReadFromTheRightPlace":
                        None if not nested or not isinstance(nested.get("collapsed"), bool)
                        else ("collapsed" if nested["collapsed"]
                              else ("range-cross"
                                    if len(nested.get("rectangles") or []) > 1
                                    else "range-single")),
                })
            return finish(record, args)

        if args.positive_control:
            # AT LOAD, before any pointer event: pointerdown resets the shape
            # to collapsed, so the control has to be read before one happens.
            buttons = evaluate(
                session,
                "(() => [...document.querySelectorAll('#toolbar "
                "button[data-action]')].map((el) => ({ action: el.dataset.action, "
                "disabled: el.disabled, title: el.title })))()") or []
            shape = shape_of(buttons)
            record["arms"].append({
                "label": "positive-control-at-load",
                "buttons": buttons, "shape": shape,
                "instrumentCanShowARange":
                    shape["impliedByCaretOnlyButtons"] == "a-range"
                    and shape["namedInTitles"] == ["range-single"],
            })
            return finish(record, args)

        scan, bands = pp.stable_bands(session)
        record["bands"] = {"count": len(bands), "width": scan.get("width")}
        wide = [b for b in bands if (b["last"] - b["first"]) > 60]
        if len(wide) < 2:
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = (f"needs two wide bands to drag inside of and "
                             f"across; found {len(wide)}")
            return finish(record, args)

        band = wide[len(wide) // 2]
        left = band["first"] / scan["width"]
        right = band["last"] / scan["width"]
        y = f"{band['centreFraction']:.5f}"
        x1 = f"{left + (right - left) * 0.15:.5f}"
        x2 = f"{left + (right - left) * 0.70:.5f}"

        # THE CONTROL FIRST, and it is a click rather than a drag: it
        # establishes that the toolbar reads `collapsed` when the selection
        # really is collapsed.  Without it, a run where everything reads
        # `collapsed` cannot tell a stale page from an instrument that only
        # knows one word.
        record["arms"].append(
            arm(session, "control-click-no-drag", x1, y, x1, y, args.window_ms))
        record["arms"].append(
            arm(session, "drag-within-one-line", x1, y, x2, y, args.window_ms))

        other = wide[(len(wide) // 2) + 1]
        y2 = f"{other['centreFraction']:.5f}"
        record["arms"].append(
            arm(session, "drag-across-two-lines", x1, y,
                f"{(other['first'] / scan['width']) + 0.10:.5f}", y2,
                args.window_ms))
        return finish(record, args)
    finally:
        try:
            session.close()
        except Exception:       # noqa: BLE001 -- teardown
            pass
        server.terminate()


def finish(record: dict, args) -> int:
    stale = [a["label"] for a in record["arms"] if a.get("staleShape")]
    fresh = [a["label"] for a in record["arms"]
             if a.get("engineHasARange") and not a.get("staleShape")]
    record["summary"] = {
        "armsWhereTheEngineHadARange": [
            a["label"] for a in record["arms"] if a.get("engineHasARange")],
        "armsWhereThePageStillSaidCollapsed": stale,
        "armsWhereThePageAgreed": fresh,
    }
    text = json.dumps(record, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    for a in record["arms"]:
        if "staleShape" not in a:
            continue
        print(f"[arm] {a['label']:26s} engineChars="
              f"{(a.get('engineSelection') or {}).get('codePoints')} "
              f"pageShape={(a.get('pageShapeAtEnd') or {}).get('impliedByCaretOnlyButtons')} "
              f"named={(a.get('pageShapeAtEnd') or {}).get('namedInTitles')} "
              f"stale={a.get('staleShape')} transitions={a.get('transitions')}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
