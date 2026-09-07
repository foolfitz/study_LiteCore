#!/usr/bin/env python3
"""Finding 093, phase 3: which candidate fix shapes satisfy O-FIX.

REGISTERED FIRST, MEASURED SECOND.  The oracle this probe evaluates is written
in `findings/evidence/093/ORACLE-fix-shape.md` and committed before this file
existed (`8edd7cf8`).  Nothing here may widen it.

WHY A SECOND PROBE RATHER THAN AN EXTENSION OF PHASE 2's.
`probe_093_a11y_region_position.py` answers four pre-registered questions about
where a node sits and what scrolling it costs.  It measures a SCROLL FRACTION,
and phase 2's own positive control is the demonstration that the fraction is a
proxy: `top: 0; left: 0` collapses it to 0.0000, which is a perfect score for a
page showing paragraph 1 while paragraph 8 is being read.  Widening that probe
to answer a different question would leave the tree with one instrument whose
name no longer says what it measures.  This one is named for the oracle.

O-FIX, so the code and the claim sit next to each other:

    after a screen reader arrives at paragraph N, the band in which the engine
    RENDERS paragraph N overlaps `.desk`'s visible band by at least half a line

The band for paragraph N is the caret rectangle at paragraph N, read as
`#sink.offsetTop` / `#sink.offsetHeight` -- the values `moveSinkToCaret()`
writes from `editorState.caret` (`web/e2-editor-app.js:722-735`).  The page's
own computation, read as a DOM observable; no new geometry is invented here.

WHAT THIS PROBE DOES NOT MEASURE, repeated from the oracle document because a
limitation stated once at the top of a file is a limitation nobody reads: it
does not run a screen reader.  The link from "Orca moves its browse cursor onto
the projected node" to "the browser scrolls that node into view" is finding
069's precedent and the owner's two walks.  Every verdict below is conditional
on it.

THE SHAPES, applied to a scratch mirror of `dist/` and never to the tree:

  S0        the page as it ships.  THE CONTROL.  It must fail.
  S1        `.a11y-only { top: 0; left: 0 }` -- phase 2's positive control,
            promoted to a candidate.  HTML override.
  S2        S1's CSS plus two lines in `moveSinkToCaret()` that give
            `#a11y-doc` the same left/top as the sink.  HTML + JS override.
  S3prime   each projected node positioned at its own paragraph's y, from a
            map this probe measured by walking the caret.  A runtime DOM
            mutation, NOT product code, because the product has no source for
            that map -- which is the finding, not a shortcut.

TWO ARMS FOR EVERY SHAPE, not just for S2, so the grid is comparable:

  browse    the caret stays at the first stop while node N is browsed.  A
            screen reader's browse cursor moves without moving the caret.
  focus     the caret is walked to paragraph N before node N is browsed.  The
            arrow-key flow, through the page's own keydown handler.

For S0, S1 and S3prime the node's position does not depend on the caret, so the
two arms are expected to agree; they are run anyway because "expected to agree"
is not a measurement.

Usage:
  probe_093_fix_shape_oracle.py [--profile P]... [--shape S]... [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))

from r7_support import evaluate, wait_page                      # noqa: E402
from run_browser_probe import ChromeSession, free_port          # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate            # noqa: E402
from run_e2_c_product_path import build_mirror, repointed_page  # noqa: E402


# ------------------------------------------------------------------ the edits

A11Y_ONLY_RULE = """  .a11y-only {
    position: absolute; width: 1px; height: 1px;"""

A11Y_ONLY_FIXED = """  .a11y-only {
    position: absolute; top: 0; left: 0; width: 1px; height: 1px;"""

SINK_TAIL = """  el.sink.style.height = `${Math.max(1, Math.round(caret.height * scaleY))}px`;
}"""

SINK_TAIL_S2 = """  el.sink.style.height = `${Math.max(1, Math.round(caret.height * scaleY))}px`;
  el.a11yDoc.style.left = el.sink.style.left;
  el.a11yDoc.style.top = el.sink.style.top;
}"""

# S2b.  ONE MORE LINE THAN S2, AND IT WAS FORCED BY A MEASUREMENT.
#
# S2 as first written copies left and top and leaves `.a11y-only`'s
# `height: 1px`.  Measured on a 133-paragraph document: the focus arm scrolled
# to the right paragraph every time and O-FIX still failed 0/3, because
# `scrollIntoView({block: "nearest"})` stops as soon as the target's BOTTOM
# edge reaches the viewport's bottom edge -- and for a 1px target that puts the
# text line the caret is on entirely BELOW the fold (overlap 0px, band top
# exactly 864 in an 864px viewport, three times).
#
# `#sink` does not have this problem because `moveSinkToCaret` already gives it
# the caret's height, and the comment there says why it does
# (`web/e2-editor-app.js:730-734`: an IME places its candidate window against
# the focused element's box).  The same line, for a different reason: an
# element the height of the line is an element the browser can bring fully into
# view.
SINK_TAIL_S2B = """  el.sink.style.height = `${Math.max(1, Math.round(caret.height * scaleY))}px`;
  el.a11yDoc.style.left = el.sink.style.left;
  el.a11yDoc.style.top = el.sink.style.top;
  el.a11yDoc.style.height = el.sink.style.height;
}"""


def shape_overrides(shape: str, page_js: str, page_html: str
                    ) -> tuple[dict[str, bytes], dict]:
    """The files a shape rewrites, and what the rewrite costs in lines."""
    files: dict[str, bytes] = {"e2-editor-app.js": page_js.encode("utf-8")}
    cost = {"cssDeclarations": 0, "jsLines": 0, "runtimeOnly": False}
    if shape in ("S1", "S2", "S2b", "S3prime"):
        if page_html.count(A11Y_ONLY_RULE) != 1:
            raise SystemExit(
                "the `.a11y-only` rule is not where this probe expects it; the "
                "tree moved under the instrument. Fix the pattern rather than "
                "patching blindly.")
        files["e2-editor.html"] = page_html.replace(
            A11Y_ONLY_RULE, A11Y_ONLY_FIXED, 1).encode("utf-8")
        cost["cssDeclarations"] = 2
    if shape in ("S2", "S2b"):
        if page_js.count(SINK_TAIL) != 1:
            raise SystemExit(
                "moveSinkToCaret's tail is not where this probe expects it")
        tail = SINK_TAIL_S2 if shape == "S2" else SINK_TAIL_S2B
        files["e2-editor-app.js"] = page_js.replace(
            SINK_TAIL, tail, 1).encode("utf-8")
        cost["jsLines"] = 2 if shape == "S2" else 3
    if shape == "S3prime":
        cost["runtimeOnly"] = True
    return files, cost


# ------------------------------------------------------------------ page reads

SWITCH_FIXTURE = """(() => {
const picker = document.querySelector('#fixture');
if (!picker) return { available: false };
const wanted = 'ARG_FIXTURE';
if (![...picker.options].some((o) => o.value === wanted))
  return { available: false, options: [...picker.options].map((o) => o.value) };
picker.value = wanted;
picker.dispatchEvent(new Event('change', { bubbles: true }));
return { available: true, to: wanted };
})()"""


# The caret rectangle AND the frame it has to be judged in, in ONE evaluate.
# Separate round trips let a repaint land between them, and then the anchor and
# the viewport describe two different layouts -- which matters here: the status
# bar wraps when `#s-latency` grows, and `.desk` loses ~50px when it does.
READ_FRAME = """(() => {
const sink = document.querySelector('#sink');
const desk = document.querySelector('#desk');
const paper = document.querySelector('#paper');
const canvas = document.querySelector('#canvas');
const structure = document.querySelector('#a11y-structure');
const doc = document.querySelector('#a11y-doc');
if (!sink || !desk || !paper) return null;
const focused = structure ? structure.querySelector('[data-focused="1"]') : null;
return {
  sinkTop: sink.offsetTop, sinkLeft: sink.offsetLeft,
  sinkHeight: sink.offsetHeight,
  focusedId: focused ? focused.id : null,
  activeDescendant: sink.getAttribute('aria-activedescendant'),
  deskScrollTop: desk.scrollTop,
  deskClientHeight: desk.clientHeight,
  deskScrollHeight: desk.scrollHeight,
  paperTopInDesk: Math.round(
    paper.getBoundingClientRect().top - desk.getBoundingClientRect().top),
  canvasHeight: canvas ? canvas.offsetHeight : null,
  a11yDocOffsetTop: doc ? doc.offsetTop : null,
  structureState: structure ? (structure.dataset.state ?? null) : null,
  structureParagraphs: structure ? (structure.dataset.paragraphs ?? null) : null,
  structureTruncated: structure ? (structure.dataset.truncated ?? null) : null,
  projectedNodes: document.querySelectorAll('[id^="a11y-node-"]').length,
  latency: document.querySelector('#s-latency').textContent,
  toast: document.querySelector('#toast').textContent,
};
})()"""


CLICK_AT = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const x = box.left + box.width * ARG_X;
const y = box.top + box.height * ARG_Y;
canvas.dispatchEvent(new PointerEvent('pointerdown', {
  clientX: x, clientY: y, button: 0, buttons: 1, pointerId: 1, bubbles: true }));
canvas.dispatchEvent(new PointerEvent('pointerup', {
  clientX: x, clientY: y, button: 0, buttons: 0, pointerId: 1, bubbles: true }));
return true;
})()"""

CLEAR_LATENCY = """(() => {
document.querySelector('#s-latency').textContent = '';
return true;
})()"""

RESET_SCROLL = """(() => {
const desk = document.querySelector('#desk');
desk.scrollTop = 0;
return desk.scrollTop;
})()"""


# The arrival.  `block: "nearest"` for the reason phase 2 records: it models
# what a browser does when it brings an AT target into view, and the aggressive
# default would measure the instrument's choice instead.
SCROLL_TO = """(() => {
const desk = document.querySelector('#desk');
const target = document.querySelector('ARG_SELECTOR');
if (!desk || !target) return { found: false };
const before = desk.scrollTop;
target.scrollIntoView({ block: "nearest" });
return { found: true, before, after: desk.scrollTop,
         room: desk.scrollHeight - desk.clientHeight };
})()"""


# S3prime.  The container stops clipping and spans the paper; each node carries
# the clip itself and sits at its own paragraph's y.  A RUNTIME mutation, and
# labelled one: the product has no source for `ARG_MAP`.
APPLY_S3PRIME = """(() => {
const doc = document.querySelector('#a11y-doc');
const canvas = document.querySelector('#canvas');
if (!doc || !canvas) return { applied: false };
const map = ARG_MAP;
doc.style.top = '0px'; doc.style.left = '0px';
doc.style.width = '1px'; doc.style.height = canvas.offsetHeight + 'px';
doc.style.overflow = 'visible'; doc.style.clip = 'auto';
doc.style.clipPath = 'none'; doc.style.margin = '0';
let placed = 0;
for (const [index, band] of Object.entries(map)) {
  const node = document.getElementById('a11y-node-' + index);
  if (!node) continue;
  node.style.position = 'absolute';
  node.style.top = band.top + 'px';
  node.style.left = '0px';
  node.style.width = '1px';
  node.style.height = Math.max(1, band.height) + 'px';
  node.style.overflow = 'hidden';
  node.style.clipPath = 'inset(50%)';
  node.style.whiteSpace = 'nowrap';
  placed += 1;
}
return { applied: true, placed, docHeight: doc.offsetHeight };
})()"""


# ---------------------------------------------------------------- the walking

def wait_state(session, predicate, timeout):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = evaluate(session, READ_STATE) or {}
        if predicate(last):
            return last
        time.sleep(0.25)
    return None


def press(session, key, code, vk, settle=2.5):
    """One key, delivered as a real key, waited for by OBSERVED CHANGE.

    A fixed sleep is what finding 084 hides behind: the caret sometimes skips a
    commit entirely on the accessibility core, and a fixed wait reports that as
    "the caret did not move" with no way to tell it from a key the page never
    took.  This waits for the sink to move OR for the focused projection node to
    change, and reports `changed: False` when neither happens rather than
    reading the stale frame as an answer.
    """
    before = evaluate(session, READ_FRAME) or {}
    for kind in ("rawKeyDown", "keyUp"):
        session.call("Input.dispatchKeyEvent",
                     {"type": kind, "key": key, "code": code,
                      "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk})
    deadline = time.monotonic() + settle
    after = before
    changed = False
    while time.monotonic() < deadline:
        time.sleep(0.12)
        after = evaluate(session, READ_FRAME) or after
        if (after.get("sinkTop") != before.get("sinkTop")
                or after.get("sinkLeft") != before.get("sinkLeft")
                or after.get("focusedId") != before.get("focusedId")):
            changed = True
            break
    return {"key": key, "changed": changed, "before": before, "after": after}


def node_index(frame: dict):
    identifier = frame.get("focusedId") or frame.get("activeDescendant")
    if not identifier or not identifier.startswith("a11y-node-"):
        return None
    try:
        return int(identifier[len("a11y-node-"):])
    except ValueError:
        return None


def click_to_top(session, timeout=25.0, ys=("0.09", "0.11", "0.13", "0.07")
                 ) -> dict:
    """Caret near the start of the text, and the keyboard on the sink.

    A canvas pointerdown is the ONLY thing that moves the caret in this page
    (`web/e2-editor-app.js:1051-1065`), and it focuses the sink on the way, so
    this is one gesture and it is the user's gesture.

    THE SUCCESS PREDICATE REJECTS FAILURE EXPLICITLY.  `run()` writes
    "定位游標 失敗" into `#s-latency` when a placement fails, and a predicate
    that only asks whether the text CONTAINS 定位游標 is satisfied by the
    failure -- measured on this probe's first run, where three arms silently
    started with the caret still at the last paragraph the walk had reached and
    the arms were then judging a caret position they had not set.

    THE TIMEOUT IS SHORT ON PURPOSE.  A placement that works answers in tens of
    milliseconds (measured: "定位游標 36 ms"); waiting three minutes for one
    that is not coming buys nothing and hides the failure in wall-clock.
    """
    attempts = []
    for y in ys:
        evaluate(session, CLEAR_LATENCY)
        evaluate(session, CLICK_AT.replace("ARG_X", "0.18").replace("ARG_Y", y))
        settled = wait_state(
            session,
            lambda s: "定位游標" in (s.get("latency") or ""), timeout)
        time.sleep(0.5)
        frame = evaluate(session, READ_FRAME) or {}
        latency = (settled or {}).get("latency") or ""
        ok = "定位游標" in latency and "失敗" not in latency
        attempts.append({"y": y, "latency": latency, "ok": ok,
                         "sinkTop": frame.get("sinkTop"),
                         "index": node_index(frame)})
        if ok:
            return {"y": y, "frame": frame, "attempts": attempts, "ok": True}
    return {"y": None, "frame": evaluate(session, READ_FRAME) or {},
            "attempts": attempts, "ok": False}


def build_stops(session, presses: int) -> dict:
    """The stops a reader can arrive at, each with the band the engine draws it.

    Walked with the DOWN ARROW through the page's own keydown handler
    (`web/e2-editor-app.js:1183-1192,1287`) -- the path the owner used when they
    saw the defect.  The first band recorded for a stop wins: it is the
    paragraph's first line, which is where a reader arriving at it lands.

    On a profile that projects paragraph nodes a stop is a PARAGRAPH.  On one
    that does not (the shipping profile projects none) a stop is a LINE, and it
    is labelled a line rather than quietly called a paragraph.
    """
    trace = []
    stops: list[dict] = []
    seen_index: set = set()
    seen_top: set = set()

    def record(step, frame):
        index = node_index(frame)
        top, height = frame.get("sinkTop"), frame.get("sinkHeight")
        trace.append({"press": step, "index": index, "top": top,
                      "height": height})
        if top is None:
            return
        if index is not None:
            if index in seen_index:
                return
            seen_index.add(index)
            stops.append({"kind": "paragraph", "label": f"paragraph {index}",
                          "index": index, "selector": f"#a11y-node-{index}",
                          "presses": step, "band": {"top": top,
                                                    "height": height}})
        else:
            if top in seen_top:
                return
            seen_top.add(top)
            stops.append({"kind": "line", "label": f"line at y={top}",
                          "index": None, "selector": "#a11y-para",
                          "presses": step, "band": {"top": top,
                                                    "height": height}})

    record(0, evaluate(session, READ_FRAME) or {})
    still = 0
    for step in range(1, presses + 1):
        result = press(session, "ArrowDown", "ArrowDown", 40)
        record(step, result["after"])
        still = still + 1 if not result["changed"] else 0
        if still >= 3:
            break   # the caret stopped moving: the end of the document
    return {"stops": stops, "trace": trace}


def overlap(frame: dict, band: dict) -> dict:
    """O-FIX, in the terms the oracle document defines it in."""
    top = frame["paperTopInDesk"] + band["top"]
    bottom = top + max(1, band["height"])
    visible = frame["deskClientHeight"]
    value = max(0, min(bottom, visible) - max(top, 0))
    threshold = 0.5 * max(1, band["height"])
    room = frame["deskScrollHeight"] - frame["deskClientHeight"]
    return {"bandTopInViewport": top, "bandBottomInViewport": bottom,
            "viewportHeight": visible, "overlapPx": value,
            "thresholdPx": threshold, "pass": value >= threshold,
            "deskScrollTop": frame["deskScrollTop"],
            "scrollFraction": (round(frame["deskScrollTop"] / room, 4)
                               if room > 0 else None)}


# ------------------------------------------------------------------- the arms

def run_arm(session, arm, stops, targets, start, s3_map=None) -> dict:
    """One ascending walk: arrive at each target in turn and judge O-FIX.

    `start` is a FRESH page whose caret has already been placed by
    `prepare()`.  Every arm gets its own page load, and the reason is a
    measurement rather than caution: after the down-arrow walk reaches the end
    of the document, EVERY subsequent canvas click comes back "定位游標 失敗"
    on this build (recorded as `postWalkClick`).  Re-clicking between arms
    therefore left the caret wherever the walk had ended, and an arm that
    cannot set the caret is not measuring the arm it is named for.
    """
    stepped = []
    guard = 0
    while guard < 14:
        frame = evaluate(session, READ_FRAME) or {}
        if frame.get("sinkTop") == stops[0]["band"]["top"]:
            break
        result = press(session, "ArrowUp", "ArrowUp", 38)
        stepped.append({"changed": result["changed"],
                        "top": result["after"].get("sinkTop")})
        if not result["changed"]:
            break
        guard += 1
    atFirstStop = (evaluate(session, READ_FRAME) or {}).get("sinkTop") \
        == stops[0]["band"]["top"]
    evaluate(session, RESET_SCROLL)
    if s3_map is not None:
        evaluate(session, APPLY_S3PRIME.replace("ARG_MAP",
                                                json.dumps(s3_map)))
    walked = []
    results = []
    for stop in targets:
        if arm == "focus":
            inner = 0
            while inner < 45:
                frame = evaluate(session, READ_FRAME) or {}
                here = (node_index(frame) if stop["kind"] == "paragraph"
                        else frame.get("sinkTop"))
                want = stop["index"] if stop["kind"] == "paragraph" \
                    else stop["band"]["top"]
                if here == want:
                    break
                result = press(session, "ArrowDown", "ArrowDown", 40)
                walked.append({"target": stop["label"],
                               "changed": result["changed"],
                               "top": result["after"].get("sinkTop")})
                if not result["changed"]:
                    break
                inner += 1
        if s3_map is not None:
            evaluate(session, APPLY_S3PRIME.replace("ARG_MAP",
                                                    json.dumps(s3_map)))
        probe = evaluate(session, SCROLL_TO.replace("ARG_SELECTOR",
                                                    stop["selector"]))
        time.sleep(0.35)
        frame = evaluate(session, READ_FRAME) or {}
        if not (probe or {}).get("found"):
            results.append({"stop": stop["label"], "outcome": "NOT_ESTABLISHED",
                            "why": f"no element matches {stop['selector']!r}"})
            continue
        verdict = overlap(frame, stop["band"])
        caretHere = (node_index(frame) if stop["kind"] == "paragraph"
                     else frame.get("sinkTop"))
        want = (stop["index"] if stop["kind"] == "paragraph"
                else stop["band"]["top"])
        verdict.update({"stop": stop["label"], "outcome": "MEASURED",
                        "target": stop["selector"], "band": stop["band"],
                        "scroll": probe,
                        "caretIndexAtArrival": node_index(frame),
                        "caretTopAtArrival": frame.get("sinkTop"),
                        # THE ARM'S OWN PRECONDITION, judged rather than
                        # assumed: `focus` claims the caret is in the target
                        # paragraph and `browse` claims it is not.
                        "caretIsAtTarget": caretHere == want})
        results.append(verdict)
    established = all(r.get("outcome") == "MEASURED" for r in results)
    armHeld = all(
        (r.get("caretIsAtTarget") is True) if arm == "focus"
        else True for r in results)
    return {"arm": arm, "start": start, "steppedUp": stepped,
            "startedAtFirstStop": atFirstStop, "caretWalk": walked,
            "targets": results, "armPreconditionHeld": armHeld,
            "pass": bool(results) and established
                    and all(r.get("pass") is True for r in results)}


def prepare(session, base, fixture, timeout) -> dict:
    """A fresh page with the document open and the caret placed.

    Called once per pass AND once per arm.  Reloading between arms is not
    tidiness: see `run_arm`'s docstring -- on this build a canvas click after a
    down-arrow walk fails, so an arm that reuses the page cannot set its own
    starting caret.
    """
    navigate(session, base)
    booted = wait_state(session, lambda s: s.get("state") in
                        ("ready", "stopped", "expired"), timeout)
    if not booted or booted.get("state") != "ready":
        return {"ok": False,
                "why": f"page state {(booted or {}).get('state')!r}, not ready"}
    fixture_result = evaluate(
        session, SWITCH_FIXTURE.replace("ARG_FIXTURE", fixture))
    if not (fixture_result or {}).get("available"):
        return {"ok": False, "why": f"fixture {fixture!r} is not offered",
                "fixture": fixture_result}
    if not wait_state(session, lambda s: s.get("state") == "ready", timeout):
        return {"ok": False,
                "why": "the page did not return to ready after the fixture"}
    # A FIXED settle, no early exit, for the reason phase 2 recorded: the
    # projection needs 1.0-1.5s and a loop that stops at the first `projected`
    # gives one profile as long as it needs and the other the whole wait.
    time.sleep(6.0)
    settled = evaluate(session, READ_FRAME)
    placed = click_to_top(session)
    return {"ok": bool(placed.get("ok")), "fixture": fixture_result,
            "frameAfterSettle": settled, "placement": placed}


def measure_shape(session, base, fixture, shape, timeout, presses) -> dict:
    record: dict = {"shape": shape, "fixtureId": fixture}
    first = prepare(session, base, fixture, timeout)
    record["pass0"] = first
    if not first.get("ok"):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = first.get("why", "the caret could not be placed")
        return record
    record["frameAfterSettle"] = first.get("frameAfterSettle")

    walk = build_stops(session, presses)
    record["stops"] = walk["stops"]
    record["walkTrace"] = walk["trace"]
    stops = walk["stops"]
    if not stops:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the caret walk produced no stop at all"
        return record
    record["stopKind"] = stops[0]["kind"]

    # RECORDED, NOT INVESTIGATED.  A single click after the walk, so the
    # behaviour that forced a page reload per arm is in the evidence rather
    # than only in this file's comments.
    record["postWalkClick"] = click_to_top(session, timeout=25.0,
                                           ys=("0.09",))

    targets = [stops[0], stops[len(stops) // 2], stops[-1]]
    seen, unique = set(), []
    for stop in targets:
        if stop["label"] not in seen:
            seen.add(stop["label"])
            unique.append(stop)
    record["targets"] = [s["label"] for s in unique]

    s3_map = ({str(s["index"]): s["band"] for s in stops
               if s["index"] is not None} if shape == "S3prime" else None)
    arms = []
    for arm in ("browse", "focus"):
        fresh = prepare(session, base, fixture, timeout)
        if not fresh.get("ok"):
            arms.append({"arm": arm, "pass": False, "outcome":
                         "NOT_ESTABLISHED", "why": fresh.get("why"),
                         "start": fresh})
            continue
        arms.append(run_arm(session, arm, stops, unique, fresh, s3_map))
    record["arms"] = arms
    record["outcome"] = "MEASURED"
    record["pass"] = all(a.get("pass") for a in arms)
    return record


def install_long_fixture(mirror: Path, source_odt: Path) -> dict:
    """Add a long document to the MIRROR's fixture list, never to the tree.

    S1 pins the viewport to the top of the paper, so it satisfies O-FIX exactly
    when the whole document fits on one screen.  Every fixture this page offers
    is ten paragraphs or fewer, so measuring S1 only on those would report a
    property of the fixture as a property of the shape.  The mirror is test
    data; `dist/` and `web/` are untouched.
    """
    manifest_path = mirror / "e1-fixtures" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = mirror / "e1-fixtures" / "a11y-long.odt"
    shutil.copyfile(source_odt, target)
    manifest["fixtures"].append({
        "id": "a11y-long", "path": "a11y-long.odt",
        "bytes": target.stat().st_size,
        "source": "dist/a11y-long.odt, added to the MIRROR only by "
                  "tools/probe_093_fix_shape_oracle.py"})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return {"installed": "a11y-long", "bytes": target.stat().st_size}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", action="append", default=None)
    parser.add_argument("--shape", action="append", default=None)
    parser.add_argument("--fixture", action="append", default=None)
    parser.add_argument("--viewport", default="1920x1080")
    parser.add_argument("--presses", type=int, default=24)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--out")
    args = parser.parse_args()
    profiles = args.profile or ["e2-editor-v12"]
    shapes = args.shape or ["S0", "S1", "S2", "S3prime"]
    fixtures = args.fixture or ["a11y-audible"]

    root = PROJECT / "dist"
    page_js_source = (PROJECT / "web" / "e2-editor-app.js").read_text("utf-8")
    page_html = (PROJECT / "web" / "e2-editor.html").read_text("utf-8")

    report = {
        "schemaVersion": 1,
        "finding": "093",
        "evidenceClass": "diagnostic",
        "phase": "phase-3",
        "oracle": "findings/evidence/093/ORACLE-fix-shape.md (commit 8edd7cf8), "
                  "registered before this probe was written",
        "oracleRestated": "after arriving at paragraph N, the band the engine "
                          "renders paragraph N in overlaps .desk's visible band "
                          "by at least half a line",
        "viewport": args.viewport,
        "limitation": "no screen reader is run. The link from an AT browse "
                      "cursor to scrollIntoView is finding 069's precedent and "
                      "the owner's walks, not measured here.",
        "mutation": "scratch mirror of dist/ only; nothing under web/ or dist/ "
                    "is written",
        "runs": [],
    }

    for profile in profiles:
        manifest = root / "profiles" / profile / "sdk-manifest.json"
        if not manifest.is_file():
            report["runs"].append({"profile": profile,
                                   "outcome": "NOT_ESTABLISHED",
                                   "why": f"no manifest at {manifest}"})
            continue
        page_js, pin_before, wasm = repointed_page(page_js_source, profile,
                                                   manifest)
        for fixture in fixtures:
            for shape in shapes:
                files, cost = shape_overrides(shape, page_js, page_html)
                scratch = Path(tempfile.mkdtemp(
                    prefix=f"f093p3-{profile}-{shape}-"))
                mirror = scratch / "root"
                extra = dict(files)
                if fixture == "a11y-long":
                    extra["e1-fixtures/manifest.json"] = (
                        root / "e1-fixtures" / "manifest.json").read_bytes()
                build_mirror(root, mirror, extra)
                installed = None
                if fixture == "a11y-long":
                    installed = install_long_fixture(
                        mirror, root / "a11y-long.odt")
                port = free_port()
                server = subprocess.Popen(
                    [sys.executable, str(PROJECT / "web" / "serve.py"),
                     "--port", str(port), "--root", str(mirror)],
                    cwd=PROJECT, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
                session = None
                try:
                    base = f"http://127.0.0.1:{port}/e2-editor.html"
                    wait_page(base)
                    session = ChromeSession("cold")
                    width, _, height = args.viewport.partition("x")
                    session.call("Emulation.setDeviceMetricsOverride",
                                 {"width": int(width), "height": int(height),
                                  "deviceScaleFactor": 1, "mobile": False})
                    entry = measure_shape(session, base, fixture, shape,
                                          args.timeout, args.presses)
                finally:
                    if session is not None:
                        session.close()
                    server.terminate()
                    server.wait(timeout=10)
                entry["profile"] = profile
                entry["cost"] = cost
                entry["filesRewritten"] = sorted(files)
                entry["longFixtureInstalled"] = installed
                entry["pageUnchangedFromShipping"] = (
                    files["e2-editor-app.js"].decode("utf-8") == page_js_source
                    and "e2-editor.html" not in files)
                entry["pagePinBefore"] = pin_before
                entry["wasmSha256"] = wasm[:16]
                report["runs"].append(entry)
                print(f"{profile}/{fixture}/{shape}: {entry.get('outcome')} "
                      f"pass={entry.get('pass')}", file=sys.stderr)
                if args.out:      # incremental, so a long matrix is not lost
                    Path(args.out).write_text(
                        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
