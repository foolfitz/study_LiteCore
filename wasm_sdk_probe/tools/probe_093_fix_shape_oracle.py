#!/usr/bin/env python3
"""Finding 093, phase 3: which candidate fix shapes satisfy O-FIX.

REGISTERED FIRST, MEASURED SECOND.  The oracle this probe evaluates is written
in `findings/evidence/093/ORACLE-fix-shape.md` and committed before this file
existed.  Nothing here may widen it.

WHY A SECOND PROBE RATHER THAN AN EXTENSION OF PHASE 2's.
`probe_093_a11y_region_position.py` answers four pre-registered questions about
where a node sits and what scrolling it costs.  It measures a SCROLL FRACTION,
and phase 2's own positive control is the demonstration that the fraction is a
proxy: `top: 0; left: 0` collapses it to 0.0000, which is a perfect score for a
page showing paragraph 1 while paragraph 8 is being read.  Widening that probe
to answer a different question would leave the tree with one instrument whose
name no longer says what it measures.  This one is named for the oracle.

O-FIX, restated so the code and the claim sit next to each other:

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
            Two arms: S2-focus (caret in paragraph N) and S2-browse (caret
            left in paragraph 0 while node N is browsed).
  S3prime   each projected node positioned at its own paragraph's y, from a
            map this probe measured by walking the caret.  Applied as a runtime
            DOM mutation, NOT as product code, because the product has no
            source for that map -- which is the finding, not a shortcut.

Usage:
  probe_093_fix_shape_oracle.py [--profile P]... [--shape S]... [--out FILE]
"""
from __future__ import annotations

import argparse
import json
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
#
# Both are made to a MIRROR of dist/ built with symlinks (`build_mirror`), so
# the shape's real cost in lines is visible and nothing under web/ or dist/ is
# written.  `e2-editor.html` is hashed by nothing (finding 094); that is the
# reason for the mirror, not permission to skip it.

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


def shape_overrides(shape: str, page_js: str, page_html: str
                    ) -> tuple[dict[str, bytes], dict]:
    """The files a shape rewrites, and the cost of the rewrite in lines."""
    files: dict[str, bytes] = {"e2-editor-app.js": page_js.encode("utf-8")}
    cost = {"cssDeclarations": 0, "jsLines": 0, "runtimeOnly": False}
    if shape in ("S1", "S2", "S3prime"):
        if page_html.count(A11Y_ONLY_RULE) != 1:
            raise SystemExit(
                "the `.a11y-only` rule is not where this probe expects it; the "
                "tree moved under the instrument. Fix the pattern rather than "
                "patching blindly.")
        html = page_html.replace(A11Y_ONLY_RULE, A11Y_ONLY_FIXED, 1)
        files["e2-editor.html"] = html.encode("utf-8")
        cost["cssDeclarations"] = 2
    if shape == "S2":
        if page_js.count(SINK_TAIL) != 1:
            raise SystemExit(
                "moveSinkToCaret's tail is not where this probe expects it")
        files["e2-editor-app.js"] = page_js.replace(
            SINK_TAIL, SINK_TAIL_S2, 1).encode("utf-8")
        cost["jsLines"] = 2
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


# The caret rectangle AND the frame it has to be judged in, in one evaluate.
# Separate round trips let a repaint land between them, and then the anchor and
# the viewport describe two different layouts.
READ_FRAME = """(() => {
const sink = document.querySelector('#sink');
const desk = document.querySelector('#desk');
const paper = document.querySelector('#paper');
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
  a11yDocOffsetTop: doc ? doc.offsetTop : null,
  structureState: structure ? (structure.dataset.state ?? null) : null,
  structureParagraphs: structure ? (structure.dataset.paragraphs ?? null) : null,
  projectedNodes: document.querySelectorAll('[id^="a11y-node-"]').length,
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
# labelled one: the product has no source for `ARG_MAP` -- see the feasibility
# section of the report.
APPLY_S3PRIME = """(() => {
const doc = document.querySelector('#a11y-doc');
const canvas = document.querySelector('#canvas');
if (!doc || !canvas) return { applied: false };
const map = ARG_MAP;
doc.style.top = '0px'; doc.style.left = '0px';
doc.style.width = '1px'; doc.style.height = canvas.offsetHeight + 'px';
doc.style.overflow = 'visible'; doc.style.clip = 'auto';
doc.style.clipPath = 'none'; doc.style.margin = '0';
const structure = document.querySelector('#a11y-structure');
if (structure) { structure.style.position = 'static'; }
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
    """One key, delivered as a real key, and waited for by OBSERVED CHANGE.

    A fixed sleep is what finding 084 was hiding behind: the caret sometimes
    skips a commit entirely on the accessibility core, and a fixed wait reports
    that as "the caret did not move" with no way to tell it from a key the page
    never took.  This waits for the sink to move OR for the focused projection
    node to change, and reports which -- and reports neither when neither
    happens, rather than reading the stale frame as an answer.
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
    """Which projected paragraph the engine says the caret is in, or None."""
    identifier = frame.get("focusedId") or frame.get("activeDescendant")
    if not identifier or not identifier.startswith("a11y-node-"):
        return None
    try:
        return int(identifier[len("a11y-node-"):])
    except ValueError:
        return None


def build_anchor_map(session, presses: int) -> dict:
    """paragraph index -> the caret band the engine draws that paragraph on.

    Walked with the DOWN ARROW through the page's own keydown handler
    (`web/e2-editor-app.js:1183-1192,1287`), which is the path the owner used
    when they saw the defect.  The first band recorded for an index wins: it is
    the paragraph's first line, which is where a reader arriving at it lands.
    """
    trace = []
    anchors: dict[int, dict] = {}
    order: list[int] = []
    frame = evaluate(session, READ_FRAME) or {}
    index = node_index(frame)
    if index is not None:
        anchors[index] = {"top": frame["sinkTop"], "height": frame["sinkHeight"],
                          "pressIndex": 0}
        order.append(index)
    trace.append({"press": 0, "index": index, "top": frame.get("sinkTop"),
                  "height": frame.get("sinkHeight"), "changed": None})
    for step in range(1, presses + 1):
        record = press(session, "ArrowDown", "ArrowDown", 40)
        frame = record["after"]
        index = node_index(frame)
        trace.append({"press": step, "index": index,
                      "top": frame.get("sinkTop"),
                      "height": frame.get("sinkHeight"),
                      "changed": record["changed"]})
        if index is None:
            continue
        if index not in anchors:
            anchors[index] = {"top": frame["sinkTop"],
                              "height": frame["sinkHeight"],
                              "pressIndex": step}
            order.append(index)
        if len(trace) > 4 and all(t["changed"] is False for t in trace[-3:]):
            break   # the caret stopped moving: the end of the document
    return {"anchors": {str(k): v for k, v in anchors.items()},
            "order": order, "trace": trace}


def overlap(frame: dict, band: dict) -> dict:
    """O-FIX, in the terms the oracle document defines it in."""
    top = frame["paperTopInDesk"] + band["top"]
    bottom = top + max(1, band["height"])
    visible = frame["deskClientHeight"]
    value = max(0, min(bottom, visible) - max(top, 0))
    threshold = 0.5 * max(1, band["height"])
    return {"bandTopInViewport": top, "bandBottomInViewport": bottom,
            "viewportHeight": visible, "overlapPx": value,
            "thresholdPx": threshold, "pass": value >= threshold,
            "deskScrollTop": frame["deskScrollTop"],
            "scrollFraction": (
                round(frame["deskScrollTop"]
                      / (frame["deskScrollHeight"] - frame["deskClientHeight"]), 4)
                if frame["deskScrollHeight"] > frame["deskClientHeight"] else None)}


def click_to_top(session, timeout) -> dict:
    """Put the caret near the start of the text and give the sink the keyboard.

    A canvas pointerdown is the ONLY thing in this page that moves the caret
    (`web/e2-editor-app.js:1051-1065`), and it focuses the sink on the way --
    so this is one gesture, not two, and it is the user's gesture.
    """
    for y in ("0.08", "0.10", "0.12", "0.06", "0.15"):
        evaluate(session, CLEAR_LATENCY)
        evaluate(session, CLICK_AT.replace("ARG_X", "0.2").replace("ARG_Y", y))
        settled = wait_state(session,
                             lambda s: "定位游標" in (s.get("latency") or ""),
                             timeout)
        time.sleep(0.6)
        frame = evaluate(session, READ_FRAME) or {}
        if settled and frame.get("sinkTop") is not None:
            return {"y": y, "frame": frame}
    return {"y": None, "frame": evaluate(session, READ_FRAME) or {}}


# ------------------------------------------------------------------- the arms

def run_arm(session, arm: str, targets: list[int], anchors: dict,
            timeout: float, s3_map: dict | None = None) -> dict:
    """One walk: arrive at each target in turn and judge O-FIX there."""
    results = []
    if arm == "S2-focus":
        start = click_to_top(session, timeout)
    else:
        start = click_to_top(session, timeout)
    evaluate(session, RESET_SCROLL)
    if s3_map is not None:
        applied = evaluate(session, APPLY_S3PRIME.replace(
            "ARG_MAP", json.dumps(s3_map)))
    else:
        applied = None
    walked = []
    for index in targets:
        band = anchors.get(str(index))
        if band is None:
            results.append({"paragraph": index, "outcome": "NOT_ESTABLISHED",
                            "why": "the caret walk never reached this paragraph, "
                                   "so it has no measured band"})
            continue
        if arm == "S2-focus":
            # Walk the caret FORWARD to paragraph N -- ascending, so the walk
            # is one pass, which is also what a reader does.
            guard = 0
            while guard < 40:
                frame = evaluate(session, READ_FRAME) or {}
                if node_index(frame) == index:
                    break
                record = press(session, "ArrowDown", "ArrowDown", 40)
                walked.append({"target": index, "changed": record["changed"],
                               "index": node_index(record["after"])})
                if not record["changed"]:
                    break
                guard += 1
        if s3_map is not None:
            evaluate(session, APPLY_S3PRIME.replace("ARG_MAP",
                                                    json.dumps(s3_map)))
        selector = f"#a11y-node-{index}"
        probe = evaluate(session, SCROLL_TO.replace("ARG_SELECTOR", selector))
        if not (probe or {}).get("found"):
            # No per-paragraph target on this profile: the only stop in the
            # region is the live region itself, which is what an AT would land
            # on.  Recorded as a different selector, not silently substituted.
            selector = "#a11y-para"
            probe = evaluate(session, SCROLL_TO.replace("ARG_SELECTOR",
                                                        selector))
        time.sleep(0.35)
        frame = evaluate(session, READ_FRAME) or {}
        verdict = overlap(frame, band)
        verdict.update({"paragraph": index, "outcome": "MEASURED",
                        "target": selector, "band": band,
                        "scroll": probe,
                        "caretIndexAtArrival": node_index(frame)})
        results.append(verdict)
    return {"arm": arm, "start": start, "applied": applied,
            "caretWalk": walked, "targets": results,
            "pass": all(r.get("pass") is True for r in results)
                    and all(r.get("outcome") == "MEASURED" for r in results)}


def measure_shape(session, base, fixture, shape, timeout, presses) -> dict:
    record: dict = {"shape": shape}
    navigate(session, base)
    booted = wait_state(session, lambda s: s.get("state") in
                        ("ready", "stopped", "expired"), timeout)
    if not booted or booted.get("state") != "ready":
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = f"page state {(booted or {}).get('state')!r}, not ready"
        return record
    record["fixture"] = evaluate(
        session, SWITCH_FIXTURE.replace("ARG_FIXTURE", fixture))
    if not (record["fixture"] or {}).get("available"):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = f"fixture {fixture!r} is not offered"
        return record
    if not wait_state(session, lambda s: s.get("state") == "ready", timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not return to ready after the fixture"
        return record
    # A FIXED settle, no early exit, for the reason phase 2 recorded: the
    # projection needs 1.0-1.5s and a loop that stops at the first `projected`
    # gives one profile as long as it needs and the other the whole wait.
    time.sleep(6.0)
    record["frameAfterSettle"] = evaluate(session, READ_FRAME)

    place = click_to_top(session, timeout)
    record["initialPlacement"] = place
    walk = build_anchor_map(session, presses)
    record["anchorWalk"] = {"order": walk["order"],
                            "anchors": walk["anchors"],
                            "trace": walk["trace"]}
    anchors = walk["anchors"]
    indices = sorted(int(k) for k in anchors)
    if not indices:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("no paragraph could be identified during the caret "
                         "walk: this profile projects no per-paragraph nodes, "
                         "so O-FIX has no target it can name")
        record["fallbackBand"] = {"top": place["frame"].get("sinkTop"),
                                  "height": place["frame"].get("sinkHeight")}
        return record
    targets = sorted({indices[0], indices[len(indices) // 2], indices[-1]})
    record["targets"] = targets

    arms = ["S2-focus", "S2-browse"] if shape == "S2" else ["default"]
    s3_map = ({k: v for k, v in anchors.items()}
              if shape == "S3prime" else None)
    record["arms"] = [run_arm(session, arm, targets, anchors, timeout, s3_map)
                      for arm in arms]
    record["outcome"] = "MEASURED"
    record["pass"] = all(a["pass"] for a in record["arms"])
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", action="append", default=None)
    parser.add_argument("--shape", action="append", default=None)
    parser.add_argument("--fixture", default="a11y-audible")
    parser.add_argument("--viewport", default="1920x1080")
    parser.add_argument("--presses", type=int, default=26)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--out")
    args = parser.parse_args()
    profiles = args.profile or ["e2-editor-v12"]
    shapes = args.shape or ["S0", "S1", "S2", "S3prime"]

    root = PROJECT / "dist"
    page_js_source = (PROJECT / "web" / "e2-editor-app.js").read_text("utf-8")
    page_html = (PROJECT / "web" / "e2-editor.html").read_text("utf-8")

    report = {
        "schemaVersion": 1,
        "finding": "093",
        "evidenceClass": "diagnostic",
        "phase": "phase-3",
        "oracle": "findings/evidence/093/ORACLE-fix-shape.md, registered and "
                  "committed before this probe was written",
        "oracleRestated": "after arriving at paragraph N, the band the engine "
                          "renders paragraph N in overlaps .desk's visible "
                          "band by at least half a line",
        "fixture": args.fixture,
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
        for shape in shapes:
            files, cost = shape_overrides(shape, page_js, page_html)
            scratch = Path(tempfile.mkdtemp(prefix=f"f093p3-{profile}-{shape}-"))
            mirror = scratch / "root"
            build_mirror(root, mirror, files)
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
                entry = measure_shape(session, base, args.fixture, shape,
                                      args.timeout, args.presses)
            finally:
                if session is not None:
                    session.close()
                server.terminate()
                server.wait(timeout=10)
            entry["profile"] = profile
            entry["cost"] = cost
            entry["filesRewritten"] = sorted(files)
            entry["pageUnchangedFromShipping"] = (
                files["e2-editor-app.js"].decode("utf-8") == page_js_source
                and "e2-editor.html" not in files)
            entry["pagePinBefore"] = pin_before
            entry["wasmSha256"] = wasm[:16]
            report["runs"].append(entry)
            print(f"{profile}/{shape}: {entry.get('outcome')} "
                  f"pass={entry.get('pass')}", file=sys.stderr)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
