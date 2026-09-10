#!/usr/bin/env python3
"""Finding 095: is the click's silence the pre-death window of finding 096?

REGISTERED FIRST, MEASURED SECOND.  The protocol this probe executes is
`handoff/tasks/TASK-2026-09-10-095-is-it-096s-window.md`, committed before
this file existed.  Nothing here may widen it.

THIS PROBE MAY NOT NAME A CAUSE.  It tests one prediction about *when*
095's symptom (a canvas click that places no caret) sits relative to 096's
known death (a boundary arrow press that wedges for 30 s and then kills the
session).  Why the core does not answer a boundary move is out of scope --
096's own standing limit, unchanged here.

THE USER'S PATH, NOT THE HARNESS'S.  Keys go through CDP
`Input.dispatchKeyEvent` (rawKeyDown/keyUp, a real virtual key code); the
caret is placed by a canvas `pointerdown`; the fixture is handed to the
product's own `#file` input as a real file on disk -- the same three rules
`findings/evidence/096/probe_096_boundary_arrow.py` states and follows.

REUSE, NOT COPY.  This file imports its machinery rather than
re-implementing it, per the task's instruction:

  * from `probe_096_boundary_arrow.py` (`findings/evidence/096/`, reached by
    inserting that directory onto `sys.path`): `BufferingSession` (the RAW
    CDP event buffer and worker-console attachment), `READ_FRAME`,
    `WATCH_STATE` / `WATCH_ERRORS` / `READ_TRANSITIONS` / `READ_ERRORS`,
    `CLEAR_LATENCY`, `INK_ROWS`, `text_row`, `press`, `dead`, `finish`,
    `worker_liveness` -- the "ask the engine, not the page" instrumentation
    and the state-pill transition trace this probe reuses unchanged.
  * from `probe_093_fix_shape_oracle.py` (`wasm_sdk_probe/tools/`):
    `click_to_top`, called with the exact `ys=("0.09",)` that produced
    095's original observation (093's own `postWalkClick` call), not the
    function's four-value default -- so this arm measures what 095
    measured, only for longer.
  * from `run_e2_c_product_path.py`: `DEAD_STATES`, `LINE_INK`, `POINT_AT`,
    `caret_click_fractions`, `build_mirror`, `repointed_page`.

ONE FUNCTION IS WRITTEN FRESH: `find_bands()`.  No existing function
returns the *count* of ink bands on the canvas -- `text_row()` (imported)
answers only "where is the first/last text row" and stops there.  This task
additionally needs the count, to answer "was the line the boundary press
landed on really the document's last line, or just the last one painted" --
the exact question 095 leaves open for the long fixture.  `find_bands()`
reuses `text_row()`'s own thresholds (dark-pixel floor 20, page-frame limit
half the canvas width), named rather than re-derived, because a threshold
measured once by 093's shakedown and re-measured here would be two numbers
that can drift apart.

THE FILE, NOT THE FIXTURE-SELECTOR.  `probe_093_fix_shape_oracle.py` opens
documents through a fixture-selector dropdown (`SWITCH_FIXTURE`), because
its subject is a11y projection across many small fixtures.  This probe
opens every arm's document -- including the long one -- through the
product's own `#file` input, matching S8/S14 and matching what 096's own
probe does.  This is a deliberate divergence from 093's UI path, not from
its file bytes: L8 hands `wasm_sdk_probe/dist/a11y-long.odt` to `#file`
byte for byte, the same 133-paragraph document 093 installed into a
fixture manifest for a different reason (a11y projection, not #file
coverage).

Usage:
  probe_095_click_after_boundary.py --profile e2-editor-v8
      --fixture wasm_sdk_probe/test-docs/e1/a11y-audible.odt
      --attempts 3 --label S8 --out findings/evidence/095/s8-e2-editor-v8.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
EVIDENCE_096 = Path("/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/096")
sys.path.insert(0, str(PROJECT / "tools"))
sys.path.insert(0, str(EVIDENCE_096))

from r7_support import evaluate, wait_page                          # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate                # noqa: E402
from run_e2_c_product_path import (                                 # noqa: E402
    DEAD_STATES, INSTALL, LINE_INK, POINT_AT,
    build_mirror, caret_click_fractions, repointed_page,
)
from probe_096_boundary_arrow import (                              # noqa: E402
    BufferingSession, CLEAR_LATENCY, INK_ROWS, READ_ERRORS, READ_FRAME,
    READ_TRANSITIONS, WATCH_ERRORS, WATCH_STATE, dead, finish, press,
    text_row, worker_liveness,
)
from probe_093_fix_shape_oracle import click_to_top                 # noqa: E402

PROTOCOL = ("handoff/tasks/TASK-2026-09-10-095-is-it-096s-window.md, "
            "registered before this probe was written")

# Same floor/limit `text_row()` (imported) uses -- forced by 093's shakedown
# 1 (the paper's own borders put a handful of dark pixels in every row).
BAND_FLOOR = 20

PRESS_PAGE_MS = ("(() => (window.__f096 ? Math.round("
                  "performance.now() - window.__f096.t0) : null))()")


# --------------------------------------------------------------- last line

def find_bands(scan: dict) -> list[dict]:
    """Every contiguous run of text ink in a full-canvas scan.

    `text_row()` stops at the first-or-last band; this returns all of them,
    because this task needs to know how many there are, not merely where one
    end is.
    """
    if not scan.get("available"):
        return []
    width = scan["width"]
    limit = 0.5 * width
    bands: list[list[int]] = []
    current: list[int] = []
    for i, n in enumerate(scan["dark"]):
        if BAND_FLOOR <= n < limit:
            current.append(i)
        else:
            if current:
                bands.append(current)
                current = []
    if current:
        bands.append(current)
    out = []
    for band in bands:
        mid = sum(band) // len(band)
        y = scan["y0"] + mid
        out.append({"localStart": band[0], "localEnd": band[-1],
                    "y": y, "fraction": y / scan["height"], "rows": len(band)})
    return out


def last_line_evidence(session) -> dict:
    """The last painted band, band count, and whether anything lies below it.

    A scan across the WHOLE canvas (`ARG_FROM_END=false`, `ARG_ROWS` larger
    than any canvas this page draws), not the bottom-anchored window
    `probe_096_boundary_arrow.py` uses for its own boundary walk -- that
    window answers "where is the last row in THIS strip"; this needs "is
    there a band the scan did not even look at", which only a full scan can
    rule out.
    """
    scan = evaluate(session, INK_ROWS.replace("ARG_ROWS", "100000")
                                     .replace("ARG_FROM_END", "false"))
    if not (scan or {}).get("available"):
        return {"found": False, "why": "no canvas", "scan": scan}
    covered_full = (scan["y0"] == 0 and scan["y0"] + scan["rows"] == scan["height"])
    bands = find_bands(scan)
    if not bands:
        return {"found": False, "why": "no ink band in the full-canvas scan",
                "scanCoveredFullCanvas": covered_full, "bandCount": 0,
                "maxDark": max(scan["dark"]) if scan["dark"] else None}
    last = bands[-1]
    below_start = last["localEnd"] + 1
    rows_below = sum(1 for i in range(below_start, len(scan["dark"]))
                      if BAND_FLOOR <= scan["dark"][i] < limit_of(scan))
    return {"found": True, "bandIndex": len(bands) - 1, "bandCount": len(bands),
            "y": last["y"], "fraction": last["fraction"], "rows": last["rows"],
            "scanCoveredFullCanvas": covered_full, "rowsBelowCount": rows_below,
            "floor": BAND_FLOOR, "borderLimit": limit_of(scan),
            "canvasHeight": scan["height"], "canvasWidth": scan["width"]}


def limit_of(scan: dict) -> float:
    return 0.5 * scan["width"]


# ------------------------------------------------------------------ watches

def move_watch(session, prior_frame: dict, window_seconds: float) -> dict:
    """Poll `#sink`'s position for a FIXED window after the press.

    Does not break early on movement: the click that follows is scheduled at
    a fixed delay (the protocol's "+2 s"), not at "as soon as something
    happens", so this window must always run to its end.  `moved` is 096's
    own before/after `sinkTop`/`sinkLeft` criterion.
    """
    trace = []
    moved = False
    moved_after_seconds = None
    start = time.monotonic()
    while time.monotonic() - start < window_seconds:
        time.sleep(0.15)
        after = evaluate(session, READ_FRAME) or {}
        elapsed = round(time.monotonic() - start, 3)
        trace.append({"elapsedSeconds": elapsed, "sinkTop": after.get("sinkTop"),
                      "sinkLeft": after.get("sinkLeft"), "state": after.get("state"),
                      "latency": after.get("latency")})
        if not moved and (after.get("sinkTop") != prior_frame.get("sinkTop")
                          or after.get("sinkLeft") != prior_frame.get("sinkLeft")):
            moved = True
            moved_after_seconds = elapsed
    final = trace[-1] if trace else {}
    return {"windowSeconds": window_seconds, "moved": moved,
            "movedAfterSeconds": moved_after_seconds, "trace": trace,
            "latencyAtEnd": final.get("latency"), "stateAtEnd": final.get("state")}


def top_line_click(session, timeout: float) -> dict:
    """The exact click that produced 095: one attempt, y=0.09, no retry list."""
    evaluate(session, CLEAR_LATENCY)
    started = time.monotonic()
    result = click_to_top(session, timeout=timeout, ys=("0.09",))
    elapsed = round(time.monotonic() - started, 3)
    return {"timeoutSeconds": timeout, "elapsedSeconds": elapsed,
            "ok": bool(result.get("ok")), "y": result.get("y"),
            "attempts": result.get("attempts"), "frame": result.get("frame")}


def time_to_dead_seconds(transitions, press_page_ms, dead_state: str):
    if press_page_ms is None or not transitions:
        return None
    for entry in transitions:
        if entry.get("state") == dead_state:
            return round((entry["ms"] - press_page_ms) / 1000.0, 3)
    return None


# ------------------------------------------------------------------ one attempt

def attempt(session, base: str, profile: str, fixture_path: Path, index: int,
            timeout: float, click_delay: float, click_timeout: float,
            watch_total: float) -> dict:
    record: dict = {"attempt": index, "profile": profile,
                    "fixture": str(fixture_path),
                    "startedAt": datetime.now(timezone.utc).isoformat()}
    session.events = []
    session.dropped = 0
    session._t0 = time.monotonic()

    navigate(session, base)
    evaluate(session, WATCH_STATE)
    evaluate(session, WATCH_ERRORS)
    evaluate(session, INSTALL)
    record["workers"] = session.attach_workers()

    booted = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        booted = evaluate(session, READ_STATE) or {}
        if booted.get("state") in ("ready", "stopped", "expired"):
            break
        time.sleep(0.4)
    record["boot"] = booted
    if (booted or {}).get("state") != "ready":
        record["outcome"] = "VOID"
        record["why"] = f"page booted to {(booted or {}).get('state')!r}, not ready"
        return finish(session, record)

    session.set_file("#file", fixture_path)
    opened = None
    stem6 = fixture_path.stem[:6]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        opened = evaluate(session, READ_STATE) or {}
        if opened.get("state") == "ready" and stem6 in (opened.get("doc") or ""):
            break
        if opened.get("state") in DEAD_STATES:
            break
        time.sleep(0.4)
    record["opened"] = opened
    if (opened or {}).get("state") != "ready":
        record["outcome"] = "VOID"
        record["why"] = f"the document did not open: state {(opened or {}).get('state')!r}"
        return finish(session, record)
    time.sleep(4.0)
    record["workersAfterOpen"] = session.sync_workers()

    evidence = last_line_evidence(session)
    record["lastLineEvidence"] = evidence
    if not evidence.get("found"):
        record["outcome"] = "VOID"
        record["why"] = evidence.get("why")
        return finish(session, record)

    y = f"{evidence['fraction']:.6f}"
    ink = evaluate(session, LINE_INK.replace("ARG_Y", y)) or {}
    fractions = caret_click_fractions(ink)
    record["placementClickFractions"] = dict(fractions, y=y)
    evaluate(session, CLEAR_LATENCY)
    evaluate(session, POINT_AT.replace("ARG_X", fractions["past"]).replace("ARG_Y", y))
    placed = None
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        placed = evaluate(session, READ_STATE) or {}
        if "定位游標" in (placed.get("latency") or ""):
            break
        time.sleep(0.3)
    record["placementOnLastLine"] = placed
    ok = "定位游標" in ((placed or {}).get("latency") or "") \
        and "失敗" not in ((placed or {}).get("latency") or "")
    if not ok:
        record["outcome"] = "VOID"
        record["why"] = ("the caret could not be placed on the last line: "
                         f"latency {(placed or {}).get('latency')!r}")
        return finish(session, record)
    time.sleep(1.0)

    # PLACEMENT LANDS AT THE END OF THE LINE ON PURPOSE.  `fractions["past"]`
    # (not `["near"]`) clicks just past the last glyph's ink, which is where
    # `caret_click_fractions` is documented to snap the caret to the LAST
    # character.  FORCED BY THE SHAKEDOWN (see the protocol's Execution
    # record): a click at `["near"]` -- just inside the START of the last
    # line -- followed by a single ArrowDown resolves in 40 ms to the END of
    # that SAME line (a real, answered move, not the wedge 096 measured),
    # because there was still somewhere within the line to go.  A prior
    # attempt tried reaching the boundary with an extra walk of repeated
    # ArrowDown presses instead of moving the click; that walk enqueues
    # `mutation: true` actions and marks the document dirty before the
    # measured press, so half C's checkpoint fires and the death no longer
    # matches this arm's pinned `noticeRescue == "none"` -- a criterion this
    # task may not launder away by choosing a gesture that happens to dodge
    # it. Landing the initial click at the line's own end reaches the SDK's
    # boundary in the ONE press this task measures, with nothing dirtying
    # the document first.
    prior = evaluate(session, READ_FRAME) or {}
    record["revisionBeforePress"] = prior.get("revision")
    record["checkpointBeforePress"] = prior.get("checkpoint")
    record["frameBeforePress"] = prior

    evaluate(session, CLEAR_LATENCY)
    press_started = time.monotonic()
    press(session, "ArrowDown", 40)
    press_page_ms = evaluate(session, PRESS_PAGE_MS)
    record["pressedAt"] = datetime.now(timezone.utc).isoformat()
    record["pressPageMs"] = press_page_ms
    record["key"] = {"key": "ArrowDown", "windowsVirtualKeyCode": 40,
                     "delivery": "CDP Input.dispatchKeyEvent rawKeyDown/keyUp"}

    watch = move_watch(session, prior, click_delay)
    record["moveWatch"] = watch
    record["caretMovedAfterPress"] = bool(watch["moved"])
    record["latencyAfterPress"] = watch["latencyAtEnd"]

    click = top_line_click(session, click_timeout)
    record["clickAt"] = click
    record["clickPlacedCaret"] = bool(click["ok"])
    record["clickLatencyText"] = ((click.get("attempts") or [{}])[-1] or {}).get("latency")

    frame = evaluate(session, READ_FRAME) or {}
    while (time.monotonic() - press_started) < watch_total and not dead(frame):
        session.pump(0.5)
        frame = evaluate(session, READ_FRAME) or frame
    record["watchedSeconds"] = round(time.monotonic() - press_started, 1)
    record["frameAfterWatch"] = frame
    record["revisionAfterWatch"] = frame.get("revision")
    record["checkpointAfterWatch"] = frame.get("checkpoint")

    record["workerLiveness"] = worker_liveness(session)

    state_name = dead(frame)
    record["died"] = bool(state_name)
    record["deadState"] = state_name
    if state_name:
        transitions = evaluate(session, READ_TRANSITIONS) or []
        record["statePillTrace"] = transitions
        record["timeToDeadStateSeconds"] = time_to_dead_seconds(
            transitions, press_page_ms, state_name)
        record["noticeShow"] = frame.get("noticeShow")
        record["noticeRescue"] = frame.get("noticeRescue")
        record["noticeText"] = frame.get("noticeText")
        record["outcome"] = ("REPRODUCED_NO_CHECKPOINT"
                              if frame.get("noticeShow") == "1"
                                  and frame.get("noticeRescue") == "none"
                              else "DIED_WITH_CHECKPOINT")
    else:
        record["statePillTrace"] = evaluate(session, READ_TRANSITIONS)
        record["timeToDeadStateSeconds"] = None
        record["outcome"] = "NOT_REPRODUCED"
    return finish(session, record)


# --------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="e2-editor-v8")
    parser.add_argument("--fixture", required=True,
                        help="path to the .odt fixture handed to #file")
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--click-delay", type=float, default=2.0)
    parser.add_argument("--click-timeout", type=float, default=25.0)
    parser.add_argument("--watch-total", type=float, default=65.0,
                        help="seconds after the press to watch for a dead "
                             "state before concluding NOT_REPRODUCED; must "
                             "be >= 60 per the protocol")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--viewport", default="1920x1080")
    parser.add_argument("--out")
    parser.add_argument("--label", default="run")
    args = parser.parse_args()
    if args.watch_total < 60.0:
        print("error: --watch-total must be >= 60 (protocol §1)", file=sys.stderr)
        return 2

    fixture_path = Path(args.fixture).resolve()
    if not fixture_path.is_file():
        print(f"error: fixture not found: {fixture_path}", file=sys.stderr)
        return 2

    root = PROJECT / "dist"
    manifest = root / "profiles" / args.profile / "sdk-manifest.json"
    page_source_path = PROJECT / "web" / "e2-editor-app.js"
    source = page_source_path.read_text(encoding="utf-8")
    page, pin_before, wasm = repointed_page(source, args.profile, manifest)
    page_sha = hashlib.sha256(page.encode("utf-8")).hexdigest()
    document_sha = hashlib.sha256(fixture_path.read_bytes()).hexdigest()

    report = {
        "schemaVersion": 1,
        "finding": "095",
        "evidenceClass": "diagnostic",
        "label": args.label,
        "protocol": PROTOCOL,
        "mayNotNameACause": True,
        "profile": args.profile,
        "pageSource": str(page_source_path),
        "pageSha256": page_sha,
        "pagePinBefore": pin_before,
        "wasmSha256": wasm,
        "fixture": str(fixture_path),
        "fixtureSha256": document_sha,
        "viewport": args.viewport,
        "attempts": args.attempts,
        "clickDelaySeconds": args.click_delay,
        "clickTimeoutSeconds": args.click_timeout,
        "watchTotalSeconds": args.watch_total,
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "runs": [],
    }

    scratch = Path(tempfile.mkdtemp(prefix=f"f095-{args.profile}-"))
    mirror = scratch / "root"
    build_mirror(root, mirror, {"e2-editor-app.js": page.encode("utf-8")})
    from run_browser_probe import free_port  # local import: only main() needs it
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(mirror)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report["servedFrom"] = str(mirror)
    report["port"] = port
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session = BufferingSession("cold")
        report["browser"] = session.version
        width, _, height = args.viewport.partition("x")
        session.call("Emulation.setDeviceMetricsOverride",
                     {"width": int(width), "height": int(height),
                      "deviceScaleFactor": 1, "mobile": False})
        session.call("Log.enable")
        for index in range(1, args.attempts + 1):
            entry = attempt(session, base, args.profile, fixture_path, index,
                            args.timeout, args.click_delay, args.click_timeout,
                            args.watch_total)
            report["runs"].append(entry)
            print(f"[{args.label}] #{index}: outcome={entry.get('outcome')} "
                  f"moved={entry.get('caretMovedAfterPress')} "
                  f"clickPlaced={entry.get('clickPlacedCaret')} "
                  f"deadIn={entry.get('timeToDeadStateSeconds')}",
                  file=sys.stderr, flush=True)
            if args.out:        # incremental: a long matrix must not be lost
                Path(args.out).write_text(
                    json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    finally:
        if session is not None:
            session.close()
        server.terminate()
        server.wait(timeout=10)

    report["completedAt"] = datetime.now(timezone.utc).isoformat()
    counts: dict = {}
    for entry in report["runs"]:
        key = entry.get("outcome")
        counts[key] = counts.get(key, 0) + 1
    report["counts"] = counts
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    print(json.dumps(counts, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
