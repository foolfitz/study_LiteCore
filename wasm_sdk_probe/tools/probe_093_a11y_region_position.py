#!/usr/bin/env python3
"""Finding 093's phase 2: where `#a11y-doc` sits, and what it costs the viewport.

WHAT THIS ANSWERS, and it is exactly the four measurements pre-registered in
`findings/093-...md` before any number existed.  Nothing here may be traded for
a nearby measurement: the pre-registration names the four, and an instrument
that cannot produce one of them must say so rather than substitute.

  1. `#a11y-doc.offsetTop` against `#canvas.offsetHeight`, on BOTH profiles.
  2. The FRACTION of `.desk`'s scrollable room consumed by scrolling the
     region's content into view.  A fraction, not a pixel count, and finding
     069 is why: its first criterion demanded "< 50px", measured 125, and
     called the fix a failure -- because pixels cannot separate "scrolled to
     the caret" from "scrolled past it to the end of the document".
  3. Whether the shipping profile really leaves `#a11y-structure` at
     `unavailable`, and how many browsable stops each profile puts in the
     region.
  4. THE POSITIVE CONTROL: give `.a11y-only` the `top: 0; left: 0` that
     `#sink` got in 069's fix, and the fraction must collapse.  If it does not,
     the mechanism reading in 093 is wrong and must be withdrawn rather than
     patched (AGENTS.md section 4).

WHY THE CONTROL IS A RUNTIME STYLE MUTATION AND NOT AN EDIT TO THE TREE.
`e2-editor.html` is hashed by nothing (finding 094), so an edit to it would not
turn a single check red -- which is precisely the reason not to make one.  The
mutation is applied to the live DOM, which is the same shape 069's own probe
used in the opposite direction (`PARK_SINK_AT_THE_BOTTOM` sets
`sink.style.top = 'auto'`).  Nothing under web/ or dist/ is written.

WHY BOTH PROFILES RUN THE SAME PAGE FUNCTION.  The v8 arm builds its page with
`repointed_page(source, "e2-editor-v8", ...)`, which for the shipping profile
is a no-op -- the arm therefore runs the shipped bytes, and the two arms differ
by the two lines the cutover changes and nothing else.

Usage:
  probe_093_a11y_region_position.py [--profile P]... [--fixture a11y-audible]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))

from r7_support import evaluate, wait_page                      # noqa: E402
from run_browser_probe import ChromeSession, free_port          # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate            # noqa: E402
from run_e2_c_product_path import build_mirror, repointed_page  # noqa: E402


# MEASUREMENT 1 and 3 in one read.  One evaluate rather than five, so every
# number in a row describes the same layout: reading `offsetTop` and the desk's
# scroll height in separate round trips lets a repaint land between them.
READ_GEOMETRY = """(() => {
const doc = document.querySelector('#a11y-doc');
const para = document.querySelector('#a11y-para');
const structure = document.querySelector('#a11y-structure');
const canvas = document.querySelector('#canvas');
const sink = document.querySelector('#sink');
const paper = document.querySelector('#paper');
const desk = document.querySelector('#desk');
if (!doc || !canvas || !desk || !paper) return null;
// A BROWSABLE STOP is a node a screen reader's caret can land on: inside the
// region, not aria-hidden, carrying text.  Counted rather than assumed,
// because "v8 has one and v12 has one per paragraph" is the prediction under
// test and not an input to it.
const hidden = (node) => {
  for (let n = node; n && n !== doc.parentNode; n = n.parentElement)
    if (n.getAttribute && n.getAttribute('aria-hidden') === 'true') return true;
  return false;
};
const stops = [...doc.querySelectorAll('*')].filter(
  (n) => !hidden(n) && (n.textContent || '').trim() !== '');
return {
  a11yDocOffsetTop: doc.offsetTop,
  a11yDocOffsetParent: doc.offsetParent ? doc.offsetParent.id : null,
  a11yDocComputedTop: getComputedStyle(doc).top,
  a11yDocComputedLeft: getComputedStyle(doc).left,
  a11yDocComputedPosition: getComputedStyle(doc).position,
  canvasHeight: canvas.offsetHeight,
  canvasOffsetTop: canvas.offsetTop,
  paperHeight: paper.offsetHeight,
  sinkOffsetTop: sink ? sink.offsetTop : null,
  sinkComputedTop: sink ? getComputedStyle(sink).top : null,
  deskScrollTop: desk.scrollTop,
  deskScrollHeight: desk.scrollHeight,
  deskClientHeight: desk.clientHeight,
  structureState: structure ? (structure.dataset.state ?? null) : null,
  structureAriaHidden: structure ? structure.getAttribute('aria-hidden') : null,
  structureChildren: structure ? structure.children.length : null,
  structureParagraphs: structure ? (structure.dataset.paragraphs ?? null) : null,
  structureTruncated: structure ? (structure.dataset.truncated ?? null) : null,
  a11yDocOffers: doc.dataset.offers ?? null,
  a11yParaReason: para ? (para.dataset.reason ?? null) : null,
  a11yParaText: para ? (para.textContent || '').slice(0, 80) : null,
  a11yParaDeferred: para ? (para.dataset.deferredToStructure ?? null) : null,
  sinkAriaOwns: sink ? sink.getAttribute('aria-owns') : null,
  sinkActiveDescendant: sink ? sink.getAttribute('aria-activedescendant') : null,
  browsableStops: stops.length,
  browsableStopSample: stops.slice(0, 4).map(
    (n) => ({ tag: n.tagName, role: n.getAttribute('role'),
              top: n.offsetTop, text: (n.textContent || '').trim().slice(0, 24) })),
};
})()"""


# MEASUREMENT 2.  `block: "nearest"` models what a browser actually does when
# it brings a caret or a browse target into view; the aggressive default would
# measure the instrument's choice rather than the reported symptom.  Finding
# 069's probe made the same call for the same reason.
SCROLL_INTO_VIEW = """(() => {
const desk = document.querySelector('#desk');
const target = document.querySelector('ARG_SELECTOR');
if (!desk || !target) return null;
desk.scrollTop = 0;
const before = desk.scrollTop;
target.scrollIntoView({ block: "nearest" });
const room = desk.scrollHeight - desk.clientHeight;
return { before, after: desk.scrollTop, room,
         fraction: room > 0 ? desk.scrollTop / room : null,
         targetOffsetTop: target.offsetTop };
})()"""


# MEASUREMENT 4.  069's fix, applied to the element that never got it.  Written
# on the live DOM: `e2-editor.html` is bound by nothing (finding 094), so an
# edit to the tree would be both unnecessary and un-guarded.
APPLY_069_FIX = """(() => {
const doc = document.querySelector('#a11y-doc');
if (!doc) return null;
doc.style.top = '0px';
doc.style.left = '0px';
return { offsetTop: doc.offsetTop,
         computedTop: getComputedStyle(doc).top };
})()"""

REVERT_069_FIX = """(() => {
const doc = document.querySelector('#a11y-doc');
if (!doc) return null;
doc.style.top = '';
doc.style.left = '';
return doc.offsetTop;
})()"""


SWITCH_FIXTURE = """(() => {
const picker = document.querySelector('#fixture');
if (!picker) return { available: false };
const wanted = 'ARG_FIXTURE';
if (![...picker.options].some((o) => o.value === wanted))
  return { available: false, options: [...picker.options].map((o) => o.value) };
const from = picker.value;
picker.value = wanted;
picker.dispatchEvent(new Event('change', { bubbles: true }));
return { available: true, from, to: wanted };
})()"""


def wait_for(session, predicate, timeout):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = evaluate(session, READ_STATE) or {}
        if predicate(last):
            return last
        time.sleep(0.25)
    return None


def measure(session, base, fixture, timeout) -> dict:
    """One profile's four measurements, on one page load."""
    record: dict = {}
    navigate(session, base)
    booted = wait_for(session, lambda s: s.get("state") in
                      ("ready", "stopped", "expired"), timeout)
    record["boot"] = booted
    if not booted or booted.get("state") != "ready":
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the page did not reach ready; state="
                         f"{(booted or {}).get('state')}")
        return record

    # The walk the owner made was on `a11y-audible` (its name is in the Orca
    # log at 00:10:43.828). Measuring a different document would answer a
    # different question.
    record["fixture"] = evaluate(
        session, SWITCH_FIXTURE.replace("ARG_FIXTURE", fixture))
    if not (record["fixture"] or {}).get("available"):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = f"fixture {fixture!r} is not offered by this page"
        return record
    settled = wait_for(session, lambda s: s.get("state") == "ready", timeout)
    if not settled:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not return to ready after the fixture"
        return record
    # A SETTLE TRACE, NOT A WAIT-UNTIL-GREEN.  The first run of this probe read
    # `projected` from v12 at Chrome's default viewport and `unavailable` at
    # 1920x1080, on the same bytes -- so a single reading of measurement 3 is a
    # coin toss, not a profile fact.  `projectStructure` itself documents the
    # transient (`e2-editor-app.js:267-270`: two readings on 2026-08-23 came
    # back with no tree at all).
    #
    # The sampling is a FIXED COUNT with no early exit, and that is deliberate:
    # a loop that stopped as soon as it saw `projected` would give v12 as long
    # as it needed and v8 the full wait every time, and the difference between
    # the two profiles is exactly what this measurement is for. Both arms get
    # the same 16 samples over the same 8 seconds.
    trace = []
    for _ in range(16):
        time.sleep(0.5)
        sample = evaluate(session, READ_GEOMETRY) or {}
        trace.append({"structureState": sample.get("structureState"),
                      "structureChildren": sample.get("structureChildren"),
                      "browsableStops": sample.get("browsableStops"),
                      "a11yDocOffsetTop": sample.get("a11yDocOffsetTop")})
    record["settleTrace"] = trace
    record["settleStates"] = sorted({str(s["structureState"]) for s in trace})

    geometry = evaluate(session, READ_GEOMETRY)
    record["geometry"] = geometry
    if not geometry or not geometry.get("canvasHeight"):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page reported no canvas, so nothing can be sited"
        return record

    # 069's own guard, and it is not a formality: with nowhere to scroll, every
    # fraction below is 0 and the arm is green for the wrong reason.
    room = geometry["deskScrollHeight"] - geometry["deskClientHeight"]
    record["scrollableRoom"] = room
    if room < 50:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = (f"the desk has {room}px of scroll room, so a drag "
                         "could not be detected either way")
        return record

    # MEASUREMENT 2, on three targets rather than one.  The region itself, the
    # live region inside it, and -- where it exists -- a projected paragraph
    # node, which is what a screen reader's caret actually lands on.
    targets = {"a11y-doc": "#a11y-doc", "a11y-para": "#a11y-para"}
    if (geometry.get("structureChildren") or 0) > 0:
        targets["first-projected-node"] = "#a11y-structure > *"
        if geometry.get("sinkActiveDescendant"):
            targets["focused-node"] = "#" + geometry["sinkActiveDescendant"]
    record["scrollBeforeFix"] = {
        name: evaluate(session, SCROLL_INTO_VIEW.replace("ARG_SELECTOR", sel))
        for name, sel in targets.items()}

    # MEASUREMENT 4.
    record["fixApplied"] = evaluate(session, APPLY_069_FIX)
    time.sleep(0.3)
    record["geometryAfterFix"] = evaluate(session, READ_GEOMETRY)
    record["scrollAfterFix"] = {
        name: evaluate(session, SCROLL_INTO_VIEW.replace("ARG_SELECTOR", sel))
        for name, sel in targets.items()}
    record["reverted"] = evaluate(session, REVERT_069_FIX)
    record["outcome"] = "MEASURED"
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", action="append",
                        default=None, help="repeatable; default v8 then v12")
    parser.add_argument("--fixture", default="a11y-audible")
    # THE FRACTION MUST NOT BE A FUNCTION OF THE WINDOW, and this is how that
    # gets checked rather than asserted.  Headless Chrome's default leaves the
    # desk 139px tall -- the same figure finding 069's record carries, so the
    # numbers are comparable to it, but a viewport that small is nobody's
    # window.  Re-running at a real size is what separates "the region is at
    # the bottom of the document" from "the desk was too short to show it".
    parser.add_argument("--viewport", default=None,
                        help="WxH, e.g. 1920x1080; default is Chrome's own")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--out", help="write the report here")
    args = parser.parse_args()
    profiles = args.profile or ["e2-editor-v8", "e2-editor-v12"]

    root = PROJECT / "dist"
    source = (PROJECT / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
    report: dict = {
        "schemaVersion": 1,
        "finding": "093",
        "evidenceClass": "diagnostic",
        "phase": "phase-2",
        "preRegistration": "findings/093-the-accessibility-projection-sits-at-"
                           "the-bottom-of-the-paper-because-it-never-got-069s-"
                           "fix.md, section 'Phase 2 的預先登錄'",
        "fixture": args.fixture,
        "viewport": args.viewport or "chrome-default",
        "note": "Geometry and scroll only. This probe does NOT run a screen "
                "reader and makes no claim about what Orca does; it measures "
                "where the region sits and what scrolling its contents into "
                "view costs the desk.",
        "mutation": "positive control only: #a11y-doc.style.top/left = 0 on "
                    "the live DOM, reverted after the reading. Nothing under "
                    "web/ or dist/ is written.",
        "profiles": {},
    }

    import tempfile
    for profile in profiles:
        manifest = root / "profiles" / profile / "sdk-manifest.json"
        if not manifest.is_file():
            report["profiles"][profile] = {
                "outcome": "NOT_ESTABLISHED",
                "why": f"no manifest at {manifest}"}
            continue
        page, pin_before, wasm = repointed_page(source, profile, manifest)
        scratch = Path(tempfile.mkdtemp(prefix=f"f093-{profile}-"))
        mirror = scratch / "root"
        build_mirror(root, mirror, {"e2-editor-app.js": page.encode("utf-8")})

        port = free_port()
        server = subprocess.Popen(
            [sys.executable, str(PROJECT / "web" / "serve.py"),
             "--port", str(port), "--root", str(mirror)],
            cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        session = None
        try:
            base = f"http://127.0.0.1:{port}/e2-editor.html"
            wait_page(base)
            session = ChromeSession("cold")
            if args.viewport:
                width, _, height = args.viewport.partition("x")
                session.call("Emulation.setDeviceMetricsOverride",
                             {"width": int(width), "height": int(height),
                              "deviceScaleFactor": 1, "mobile": False})
            entry = measure(session, base, args.fixture, args.timeout)
        finally:
            if session is not None:
                session.close()
            server.terminate()
            server.wait(timeout=10)
        entry["pagePinBefore"] = pin_before
        entry["pagePinAfter"] = wasm[:16]
        entry["pageUnchangedFromShipping"] = (page == source)
        report["profiles"][profile] = entry
        print(f"{profile}: {entry.get('outcome')}", file=sys.stderr)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
