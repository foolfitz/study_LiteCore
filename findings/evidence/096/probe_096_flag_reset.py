#!/usr/bin/env python3
"""Finding 096: is the boundary's silence M1 (closed gate) or M2 (the
flush-time dedup of an unchanged INVALIDATE_VISIBLE_CURSOR payload)?

REGISTERED FIRST, MEASURED SECOND.  The protocol this probe executes is
`handoff/tasks/TASK-2026-09-10-096-why-the-core-is-silent-at-a-boundary.md`.
Three sections exist in that file, written in order (`## 1`-`## 6`, then
"Supersession 1", then "Supersession 2"); **Supersession 2 is operative**
where it disagrees with anything earlier.  Nothing here may widen its arms
or its verdict rule.

THIS PROBE MAY NOT NAME A CAUSE beyond what Supersession 2's verdict rule
licenses.  P''s second Home being silent while its first is answered is the
whole of the argument for M2; nothing else may be read into it.

THE USER'S PATH, NOT THE HARNESS'S.  Keys go through CDP
`Input.dispatchKeyEvent` (rawKeyDown/keyUp, a real virtual key code); the
caret is placed by a canvas `pointerdown`; the fixture is handed to the
product's own `#file` input as a real file on disk -- the same rules
`probe_096_boundary_arrow.py` and `probe_095_click_after_boundary.py` state
and follow.

ASK THE ENGINE, NOT THE PAGE.  The instrument named by Supersession 2 is the
RAW `lok` stream captured inside the live document worker's own realm --
NOT `sourceSequence` (withdrawn: it does not move on `LOK_CALLBACK_STATE_
CHANGED` and is unreadable from the page without injecting a new probe,
which Supersession 2 and this task both forbid).  Every raw
`{"type":"lok","id":N,"payload":...}` line `onLokCallback`
(`src/probe_engine.cpp:2372-2381`) emits for EVERY LOK callback -- before the
type switch, outside every `#ifdef` -- is what "answered"/"silent" is read
from here, exactly as `probe_096_engine_side.py` (imported below, not
copied) already captures it.

REUSE, NOT COPY.  This file writes only what neither import already gives:
the four arms' click targets and key sequences, and the per-press bookkeeping
that ties `probe_096_engine_side.py`'s worker-realm instrumentation to
`probe_096_boundary_arrow.py`'s caret-placement-by-ink-band machinery
(imported directly) and `probe_095_click_after_boundary.py`'s full-canvas
band finder and `lastLineEvidence` (imported directly, per the T9 lesson:
ink finds the last PAINTED line, not the document boundary, and the fixture's
last element must be checked, not assumed).

  * from `probe_096_boundary_arrow.py`: `BufferingSession` (RAW CDP buffer +
    worker-console attach), `READ_FRAME`, `WATCH_STATE`/`WATCH_ERRORS`/
    `READ_TRANSITIONS`, `CLEAR_LATENCY`, `INK_ROWS`, `press`, `dead`,
    `finish`, `worker_liveness`.
  * from `probe_096_engine_side.py`: `live_worker` (asks every attached
    worker session which one is the live engine, rather than assuming),
    `mark`, `worker_eval`, `INSTALL_WORKER`, `COLLECT`, `_lok_ids`, `_types`,
    `_completions`.
  * from `probe_095_click_after_boundary.py`: `find_bands` (every contiguous
    ink band, not just the first/last `text_row` answers) and
    `last_line_evidence` (band count, whether anything lies below the last
    painted band).
  * from `run_e2_c_product_path.py`: `DEAD_STATES`, `LINE_INK`, `POINT_AT`,
    `caret_click_fractions`, `build_mirror`, `repointed_page`, `INSTALL`.

ONE THING IS WRITTEN FRESH: `mid_click_fraction()`.  P' and G click MID-LINE,
inside the line's ink rather than at the margin `caret_click_fractions`'s
`near` targets (`near` = `inkLeft + 0.12 * span`); this adds the protocol's
own "+0.3 of ink width" on top of that same anchor, in the same pixel units,
before dividing by the canvas width -- so both fractions are readable off the
same ink measurement.

THE FIXTURE'S PARAGRAPH ORDER, read from content.xml (2026-09-10) rather
than assumed: heading1, plain, heading2, plain, bullet-1, bullet-2, PLAIN
(P' target, band index 6), NUMBERED-1 (G target, band index 7), NUMBERED-2,
PLAIN (last line, C/N target, band index 9).  Ten paragraphs, no nesting, no
wrapping expected at 1920x1080 -- and the probe CHECKS that at runtime
(`bandScan.bandCount == 10`, VOID otherwise) rather than trusting it.

Usage:
  probe_096_flag_reset.py --arm P [--attempts 3] [--out FILE] [--label run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
EVIDENCE_096 = Path("/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/096")
EVIDENCE_095 = Path("/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/095")
sys.path.insert(0, str(PROJECT / "tools"))
sys.path.insert(0, str(EVIDENCE_096))
sys.path.insert(0, str(EVIDENCE_095))

from r7_support import evaluate, wait_page                          # noqa: E402
from run_browser_probe import free_port                             # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate                # noqa: E402
from run_e2_c_product_path import (                                 # noqa: E402
    DEAD_STATES, INSTALL, LINE_INK, POINT_AT,
    build_mirror, caret_click_fractions, repointed_page,
)
from probe_096_boundary_arrow import (                              # noqa: E402
    BufferingSession, CLEAR_LATENCY, INK_ROWS, READ_FRAME,
    READ_TRANSITIONS, WATCH_ERRORS, WATCH_STATE, dead, finish, press,
    worker_liveness,
)
import probe_096_engine_side as ENGINE                               # noqa: E402
from probe_095_click_after_boundary import (                        # noqa: E402
    find_bands, last_line_evidence,
)

FIXTURE = PROJECT / "test-docs" / "e1" / "a11y-audible.odt"

# The fixture's ten paragraphs, in document order (content.xml, read
# 2026-09-10).  `bandIndex` is 0-based, top to bottom of a full-canvas scan.
ARMS = {
    "P": {
        "description": "P' -- plain line, same-position Home (M2 isolation)",
        "bandIndex": 6,
        "paragraphText": "夾在中間的這一行不是清單 只是普通內文",
        "clickKind": "mid",
        "keys": [("Home", 36), ("Home", 36)],
    },
    "G": {
        "description": "G -- numbered item, three Homes (flag-reset control)",
        "bandIndex": 7,
        "paragraphText": "編號的部分開始 這裡應該被唸成編號清單的第一項",
        "clickKind": "mid",
        "keys": [("Home", 36), ("Home", 36), ("Home", 36)],
    },
    "C": {
        "description": "C -- control, `past` on the last line",
        "bandIndex": None,
        "paragraphText": "最後一行到了 整份文件到這裡結束",
        "clickKind": "past",
        "keys": [("ArrowDown", 40)],
    },
    "N": {
        "description": "N -- tdf#150457, `near` on the last line",
        "bandIndex": None,
        "paragraphText": "最後一行到了 整份文件到這裡結束",
        "clickKind": "near",
        "keys": [("ArrowDown", 40), ("ArrowDown", 40)],
    },
}

# Not the instrument (that is the raw lok stream) -- a bonus corroboration,
# read from a DOM element the product already exposes for accessibility, of
# which paragraph the click actually landed the caret in.  Recorded, and
# never load-bearing: on a profile that does not offer caret paragraph text
# this is just `{"offers": "0", "text": null, ...}` and the band-order
# assumption (checked separately, see `bandScan`) carries the claim alone.
READ_A11Y = """(() => {
const para = document.querySelector('#a11y-para');
const doc = document.querySelector('#a11y-doc');
return { text: para ? para.textContent : null,
        reason: para ? para.dataset.reason : null,
        deferredToStructure: para ? para.dataset.deferredToStructure : null,
        offers: doc ? doc.dataset.offers : null };
})()"""


def mid_click_fraction(ink: dict) -> dict:
    """The mid-line click point P'/G use: `near` + 0.3 * the line's own ink span.

    `caret_click_fractions` (imported) anchors `near` at
    `inkLeft + 0.12 * span` -- just inside the text, not the margin.  The
    protocol wants P'/G clicking further in, so this adds another
    `0.3 * span` on the same anchor, in the same pixel units, before dividing
    by the canvas width -- so both fractions are read off one measurement of
    the SAME line, not two independent guesses.
    """
    if not ink.get("available"):
        return {"derived": False, "mid": "0.30",
                "why": "no line ink found; falling back to a viewport fraction"}
    left, right = ink["inkLeft"], ink["inkRight"]
    width, span = ink["width"], right - left
    mid = left + 0.42 * span
    return {"derived": True, "mid": f"{mid / width:.6f}",
            "inkLeft": left, "inkRight": right, "canvasWidth": width}


def press_verdict(lok_ids, resolution: str) -> str:
    """Read Supersession 2's answered/silent rule back; do not compose a new one.

    answered = a raw lok id 1 or 2 in the window AND the pill returned to
    ready.  silent = no id 1/2 in the window AND the session reached a dead
    state.  The other two combinations are the "third thing" 096's own
    protocol already named (a callback that arrived but did not save the
    press, or a press that resolved with no raw callback at all) -- banked
    under their own label, not folded into either verdict.
    """
    ids = set(lok_ids or [])
    has_12 = bool(ids & {1, 2})
    if has_12 and resolution == "ready":
        return "answered"
    if not has_12 and resolution == "dead":
        return "silent"
    if has_12 and resolution == "dead":
        return "callback-but-wedged"
    if not has_12 and resolution == "ready":
        return "resolved-without-raw-callback"
    return "ambiguous-timeout"


def fixture_content_xml_tail(path: Path, length: int = 700) -> str:
    with zipfile.ZipFile(path) as zf:
        data = zf.read("content.xml").decode("utf-8")
    return data[-length:]


# ------------------------------------------------------------------ one attempt

def attempt(session, base: str, arm: str, index: int, args, content_tail: str) -> dict:
    cfg = ARMS[arm]
    record: dict = {"attempt": index, "arm": arm, "armDescription": cfg["description"],
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
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        booted = evaluate(session, READ_STATE) or {}
        if booted.get("state") in ("ready", "stopped", "expired"):
            break
        time.sleep(0.4)
    record["boot"] = booted
    if (booted or {}).get("state") != "ready":
        record["outcome"] = "VOID"
        record["why"] = f"page booted to {(booted or {}).get('state')!r}"
        return finish(session, record)

    session.set_file("#file", FIXTURE)
    opened = None
    stem6 = FIXTURE.stem[:6]
    deadline = time.monotonic() + args.timeout
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
        record["why"] = f"the document did not open: {(opened or {}).get('state')!r}"
        return finish(session, record)
    time.sleep(4.0)
    record["workersAfterOpen"] = session.sync_workers()
    record["fixtureContentXmlTail"] = content_tail

    # THE LIVE WORKER, asked rather than assumed (2026-09-09 lesson, sessions
    # from an earlier attempt linger in the map and answer stale).
    found = ENGINE.live_worker(session)
    record["workerIdentity"] = found
    sid = found.get("chosen")
    if not sid:
        record["outcome"] = "VOID"
        record["why"] = "no attached worker realm carried __probe_on_event"
        return finish(session, record)
    record["workerSessionId"] = sid
    record["install"] = ENGINE.worker_eval(session, sid, ENGINE.INSTALL_WORKER, timeout=20.0)
    if not record["install"].get("returned") \
            or (record["install"].get("value") or {}).get("installed") != "yes":
        record["outcome"] = "VOID"
        record["why"] = "the worker-realm instrumentation did not install"
        return finish(session, record)

    # T9 lesson: record what is actually painted before clicking anything.
    record["lastLineEvidence"] = last_line_evidence(session)

    scan = evaluate(session, INK_ROWS.replace("ARG_ROWS", "100000")
                                     .replace("ARG_FROM_END", "false"))
    bands = find_bands(scan or {})
    record["bandScan"] = {"bandCount": len(bands),
                          "fractions": [round(b["fraction"], 6) for b in bands]}
    if len(bands) != 10:
        record["outcome"] = "VOID"
        record["why"] = (f"expected 10 unwrapped paragraphs (fixture content.xml "
                         f"has 10 text:h/text:p elements), found {len(bands)} ink "
                         f"bands; the click-target assumption does not hold")
        return finish(session, record)

    band_index = cfg["bandIndex"] if cfg["bandIndex"] is not None else len(bands) - 1
    target_band = bands[band_index]
    record["targetBand"] = {"index": band_index, **target_band}

    y = f"{target_band['fraction']:.6f}"
    ink = evaluate(session, LINE_INK.replace("ARG_Y", y)) or {}
    record["lineInk"] = ink
    if cfg["clickKind"] == "mid":
        fractions = mid_click_fraction(ink)
        x = fractions["mid"]
    else:
        fractions = caret_click_fractions(ink)
        x = fractions[cfg["clickKind"]]
    record["clickFractions"] = dict(fractions, y=y, kind=cfg["clickKind"])

    evaluate(session, CLEAR_LATENCY)
    ENGINE.mark(session, sid, "before-caret-click")
    evaluate(session, POINT_AT.replace("ARG_X", x).replace("ARG_Y", y))
    placed = None
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        placed = evaluate(session, READ_STATE) or {}
        if "定位游標" in (placed.get("latency") or ""):
            break
        time.sleep(0.3)
    record["placement"] = placed
    latency = (placed or {}).get("latency") or ""
    if "定位游標" not in latency or "失敗" in latency:
        record["outcome"] = "VOID"
        record["why"] = f"the caret could not be placed: {latency!r}"
        record["worker"] = ENGINE.worker_eval(session, sid, ENGINE.COLLECT, timeout=30.0)
        return finish(session, record)
    ENGINE.mark(session, sid, "after-caret-click")
    time.sleep(1.0)
    record["a11yAfterPlacement"] = evaluate(session, READ_A11Y)

    trace: list[dict] = []
    for step, (key, code) in enumerate(cfg["keys"], start=1):
        is_final = step == len(cfg["keys"])
        prior = evaluate(session, READ_FRAME) or {}
        evaluate(session, CLEAR_LATENCY)
        marked_before = ENGINE.mark(session, sid, f"press-{step}-before")
        press(session, key, code)
        # NOT PRE-JUDGED: every press, predicted-answered or predicted-silent
        # alike, gets the same watch loop up to the same generous timeout, so
        # an unpredicted wedge on an "answered" press is caught rather than
        # cut off, and the final press gets the protocol's 60s+ tail for free
        # (65s here; wedges resolve at 29-31s with margin to spare).
        watch_timeout = 65.0 if is_final else 35.0
        started = time.monotonic()
        after = prior
        resolution = "timeout"
        while time.monotonic() - started < watch_timeout:
            time.sleep(0.2)
            after = evaluate(session, READ_FRAME) or after
            if dead(after):
                resolution = "dead"
                break
            if after.get("state") == "ready" and (after.get("latency") or "").strip():
                resolution = "ready"
                break
        seconds = round(time.monotonic() - started, 3)
        marked_after = ENGINE.mark(session, sid, f"press-{step}-after")
        trace.append({
            "press": step, "key": key, "code": code, "final": is_final,
            "watchTimeoutSeconds": watch_timeout,
            "resolution": resolution, "secondsToResolution": seconds,
            "sinkLeftBefore": prior.get("sinkLeft"), "sinkTopBefore": prior.get("sinkTop"),
            "sinkLeftAfter": after.get("sinkLeft"), "sinkTopAfter": after.get("sinkTop"),
            "stateAfter": after.get("state"), "latencyAfter": after.get("latency"),
            "pendingAfter": after.get("pending"), "revisionAfter": after.get("revision"),
            "deadStateAfter": dead(after),
            "engineIndexBefore": (marked_before.get("value") or {}).get("engineIndex"),
            "engineIndexAfter": (marked_after.get("value") or {}).get("engineIndex"),
        })
        if resolution == "dead":
            # Further keys would land on a dead session; stop rather than
            # dispatch presses the protocol did not ask this arm to survive.
            break
    record["pressesPlanned"] = len(cfg["keys"])
    record["pressesDispatched"] = len(trace)

    # THE PROTOCOL'S 60s WATCH AFTER THE LAST PRESS.  The final press's own
    # loop above already ran up to 65s and stopped as soon as it resolved;
    # this only adds time when it resolved fast, topping the total up to 60s
    # so a delayed death after an apparently-answered final press is not
    # missed.
    frame = evaluate(session, READ_FRAME) or {}
    spent = trace[-1]["secondsToResolution"] if trace else 0.0
    tail_budget = max(0.0, 60.0 - spent)
    waited = 0.0
    while waited < tail_budget and not dead(frame):
        session.pump(0.5)
        waited += 0.5
        frame = evaluate(session, READ_FRAME) or frame
    record["frameAfterTailWait"] = frame
    record["tailWaitedSeconds"] = round(waited, 1)

    record["workerLiveness"] = worker_liveness(session)
    record["worker"] = ENGINE.worker_eval(session, sid, ENGINE.COLLECT, timeout=60.0)

    state_name = dead(frame)
    record["died"] = bool(state_name)
    record["deadState"] = state_name
    if state_name:
        record["noticeRescue"] = frame.get("noticeRescue")
        record["noticeText"] = frame.get("noticeText")

    # ---- per-press raw windows and lokIds, sliced from the ONE buffer fetch ----
    worker_value = (record["worker"].get("value") or {})
    events = worker_value.get("engine") or []
    record["engineEventsTotal"] = len(events)
    record["engineEventsDropped"] = worker_value.get("engineDropped")
    for entry in trace:
        start, end = entry.get("engineIndexBefore"), entry.get("engineIndexAfter")
        if start is None or end is None or end < start:
            entry["window"] = None
            entry["lokIds"] = None
            entry["types"] = None
            entry["completions"] = None
            entry["pressVerdict"] = "no-window"
            continue
        window = events[start:end]
        entry["window"] = window
        entry["lokIds"] = ENGINE._lok_ids(window)
        entry["types"] = ENGINE._types(window)
        entry["completions"] = ENGINE._completions(window)
        entry["pressVerdict"] = press_verdict(entry["lokIds"], entry["resolution"])
    record["pressTrace"] = trace
    record["outcome"] = "DIED" if record["died"] else "ALIVE"
    return finish(session, record)


# --------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="e2-editor-v8")
    parser.add_argument("--arm", required=True, choices=tuple(ARMS))
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--viewport", default="1920x1080")
    parser.add_argument("--out")
    parser.add_argument("--label", default="run")
    args = parser.parse_args()

    root = PROJECT / "dist"
    manifest = root / "profiles" / args.profile / "sdk-manifest.json"
    source = (PROJECT / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
    page, pin_before, wasm = repointed_page(source, args.profile, manifest)
    page_sha = hashlib.sha256(page.encode("utf-8")).hexdigest()
    fixture_sha = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    content_tail = fixture_content_xml_tail(FIXTURE)
    cfg = ARMS[args.arm]

    report = {
        "schemaVersion": 1,
        "finding": "096",
        "evidenceClass": "diagnostic",
        "label": args.label,
        "protocol": "handoff/tasks/TASK-2026-09-10-096-why-the-core-is-silent-at-"
                    "a-boundary.md, Supersession 2, registered before this probe "
                    "was written",
        "instrument": "the raw lok stream inside the live document worker's own "
                      "realm (probe_096_engine_side.py); NOT sourceSequence",
        "mayNotWidenTheArmsOrVerdict": True,
        "arm": args.arm,
        "armDescription": cfg["description"],
        "armParagraphText": cfg["paragraphText"],
        "profile": args.profile,
        "pageSha256": page_sha,
        "pagePinBefore": pin_before,
        "wasmSha256": wasm,
        "fixture": str(FIXTURE),
        "fixtureSha256": fixture_sha,
        "fixtureContentXmlTail": content_tail,
        "viewport": args.viewport,
        "attempts": args.attempts,
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "runs": [],
    }

    scratch = Path(tempfile.mkdtemp(prefix=f"f096flag-{args.arm}-"))
    mirror = scratch / "root"
    build_mirror(root, mirror, {"e2-editor-app.js": page.encode("utf-8")})
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
            entry = attempt(session, base, args.arm, index, args, content_tail)
            report["runs"].append(entry)
            trace = entry.get("pressTrace") or []
            verdicts = [t.get("pressVerdict") for t in trace]
            print(f"[{args.arm}] #{index}: outcome={entry.get('outcome')} "
                  f"pressVerdicts={verdicts}", file=sys.stderr, flush=True)
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
        for t in (entry.get("pressTrace") or []):
            key = f"press{t['press']}:{t.get('pressVerdict')}"
            counts[key] = counts.get(key, 0) + 1
        counts[f"outcome:{entry.get('outcome')}"] = \
            counts.get(f"outcome:{entry.get('outcome')}", 0) + 1
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
