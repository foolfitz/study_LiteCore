#!/usr/bin/env python3
"""Finding 096, half C: without the checkpoint the work is gone; with it it comes back.

THE RED CASE FOR THE SHELL HALF, and it is a red case rather than a
demonstration: AGENTS.md section 6 says a checker that only ever returns green
proves it can return green.  So this runs the SAME seven steps twice, on two
mirrors of `dist/` that differ in exactly two lines of
`editor-shell-v2/narrow-editor-v2-session.js`, and requires them to disagree.

  * arm `without`  -- the two lines removed.  This is the product as it shipped
                      this morning.  Expected: the notice says there is no
                      checkpoint, the button says 「重新開啟」, and the sentence
                      the owner quoted appears verbatim.  Pressing it must
                      bring back a document that does NOT contain what was
                      typed.
  * arm `with`     -- the tree as it is now.  Expected: the notice offers the
                      checkpoint, the button says 「回到檢查點」, and pressing
                      it must bring back a document that DOES contain it.

A CHECKPOINT NOBODY RESTORED FROM IS NOT A CHECKPOINT.  Both arms end by
pressing the product's own recovery button and then its own save button, and
the verdict is taken from `content.xml` of the bytes that came out -- not from
`hasCheckpoint`, not from the pill, not from the notice.  The notice is
recorded because the owner quoted it; it is not what is judged.

WHAT THIS CANNOT MEASURE, said here rather than left implied: the ENGINE half.
No artifact in this tree carries the move-path deadline, so in both arms the
boundary press still wedges and the session still dies after the SDK's 30 s.
That is measured and reported (`boundaryPressAnsweredSeconds` is null in every
attempt) and it is exactly what the owner's link will change.  A green run here
is evidence about the loss, never about the hang.

THE USER'S PATH.  Real arrow keys through `Input.dispatchKeyEvent`, the caret
placed by a canvas pointerdown, the text typed through the product's own insert
control, the document opened through the product's own file input, and the
recovery taken by clicking the product's own button.

Usage:
  probe_096_checkpoint_before_the_gesture.py [--attempts 3] [--out FILE]
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
sys.path.insert(0, str(PROJECT / "tools"))

from r7_support import evaluate, wait_page                          # noqa: E402
from run_browser_probe import ChromeSession, free_port              # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate                # noqa: E402
from run_e2_c_product_path import (                                 # noqa: E402
    CLEAR_TOAST, DEAD_STATES, INSTALL, LINE_INK, OPEN_FILE, POINT_AT,
    PRESS, READ_TOASTS, SAVE_COUNT, SET_TEXT, build_mirror,
    capture_save, caret_click_fractions, is_an_odt, stable_bands,
)

# The shell file the two arms differ in, and the two lines themselves.  Written
# as the exact source text rather than as a regular expression: a pattern that
# silently matches nothing would give the `without` arm the fixed product and
# report agreement between two identical mirrors.
SESSION_JS = "editor-shell-v2/narrow-editor-v2-session.js"
THE_FIX = ("        if (BOUNDARY_CAPABLE_MOVES.has(action))\n"
           "          await this._checkpointBeforeBoundaryMove(document);\n")

# Absent from every fixture in the tree, so finding it in a saved ODT is a
# statement about this run.
SENTINEL = "F096RESCUEMARK"

# The owner's sentence, quoted for comparison and NOT used as the predicate.
OWNER_NOTICE = "引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。"

FIXTURE_URL = "./e1-fixtures/list-contexts.odt"

READ_NOTICE = """(() => {
const q = (s) => document.querySelector(s);
const notice = q('#notice');
return {
  show: notice ? notice.dataset.show : null,
  rescue: notice ? (notice.dataset.rescue || null) : null,
  text: q('#notice-text') ? q('#notice-text').textContent : null,
  action: q('#notice-action') ? q('#notice-action').textContent : null,
  disabled: q('#notice-action') ? q('#notice-action').disabled : null,
  state: q('#state-pill') ? q('#state-pill').dataset.state : null,
  checkpoint: q('#s-checkpoint') ? q('#s-checkpoint').textContent : null,
  revision: q('#s-revision') ? q('#s-revision').textContent : null,
  pending: q('#s-pending') ? q('#s-pending').textContent : null,
  latency: q('#s-latency') ? q('#s-latency').textContent : null,
};
})()"""

CLICK_NOTICE = """(() => {
const notice = document.querySelector('#notice');
if (!notice || notice.dataset.show !== "1") return false;
const button = document.querySelector('#notice-action');
if (!button || button.disabled) return false;
button.click();
return true;
})()"""

SINK_AT = """(() => {
const sink = document.querySelector('#sink');
return sink ? { top: sink.offsetTop, left: sink.offsetLeft } : null;
})()"""


def dead(state) -> str | None:
    name = (state or {}).get("state")
    return name if name in DEAD_STATES else None


def press_key(session, key: str, code: int) -> None:
    for kind in ("rawKeyDown", "keyUp"):
        session.call("Input.dispatchKeyEvent",
                     {"type": kind, "key": key, "code": key,
                      "windowsVirtualKeyCode": code, "nativeVirtualKeyCode": code})


def wait_state(session, predicate, timeout: float):
    deadline = time.monotonic() + timeout
    state = None
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if state and predicate(state):
            return state
        time.sleep(0.3)
    return state


def attempt(session, base: str, arm: str, index: int) -> dict:
    record: dict = {"arm": arm, "attempt": index,
                    "startedAt": datetime.now(timezone.utc).isoformat()}
    navigate(session, base)
    evaluate(session, INSTALL)
    booted = wait_state(session, lambda s: s.get("state") in ("ready", "stopped",
                                                             "expired"), 180)
    record["boot"] = (booted or {}).get("state")
    if record["boot"] != "ready":
        record["outcome"] = "VOID"
        record["why"] = f"the page booted to {record['boot']!r}"
        return record

    name = f"f096-checkpoint-{arm}-{index}.odt"
    evaluate(session, OPEN_FILE.replace("ARG_URL", FIXTURE_URL)
             .replace("ARG_NAME", name))
    opened = wait_state(session, lambda s: (s.get("doc") or "") == name
                        and s.get("state") == "ready", 180)
    record["opened"] = (opened or {}).get("state")
    if record["opened"] != "ready":
        record["outcome"] = "VOID"
        record["why"] = f"the fixture did not open: {record['opened']!r}"
        return record

    # THE FIRST LINE OF THE DOCUMENT, found from the ink rather than guessed at
    # a fraction: ArrowUp is only a boundary press if the caret is on the top
    # line, and a click that lands one line lower measures an ordinary move.
    scan, bands = stable_bands(session)
    record["bands"] = len(bands)
    if not bands:
        record["outcome"] = "VOID"
        record["why"] = "no text bands on the canvas, so no first line to click"
        return record
    top = bands[0]
    y = f"{top['centreFraction']:.5f}"
    ink = evaluate(session, LINE_INK.replace("ARG_Y", y)) or {}
    fractions = caret_click_fractions(ink)
    record["click"] = {"x": fractions["near"], "y": y}
    evaluate(session, POINT_AT.replace("ARG_X", fractions["near"])
             .replace("ARG_Y", y))
    placed = wait_state(session, lambda s: "定位游標" in (s.get("latency") or ""), 90)
    record["placed"] = (placed or {}).get("latency")
    if "定位游標" not in (record["placed"] or "") or "失敗" in (record["placed"] or ""):
        record["outcome"] = "VOID"
        record["why"] = f"the caret could not be placed: {record['placed']!r}"
        return record

    # WORK WORTH LOSING, through the product's own insert control.
    before_typing = evaluate(session, READ_STATE) or {}
    evaluate(session, SET_TEXT.replace("ARG_TEXT", SENTINEL))
    evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
    typed = wait_state(session,
                       lambda s: (s.get("revision") or "")
                       != (before_typing.get("revision") or ""), 120)
    record["revisionBeforeTyping"] = before_typing.get("revision")
    record["revisionAfterTyping"] = (typed or {}).get("revision")
    if record["revisionBeforeTyping"] == record["revisionAfterTyping"]:
        record["outcome"] = "VOID"
        record["why"] = "the insert never reached the document, so there is nothing to lose"
        return record
    # THE CONTROL ON THE CHECKPOINT: it must not exist yet.  Without this, a
    # checkpoint some earlier gesture left behind would be read as one this
    # arrow key banked -- and the `with` arm would pass on the `without` shell.
    record["checkpointBeforeTheKey"] = (
        evaluate(session, READ_NOTICE) or {}).get("checkpoint")

    # THE BOUNDARY PRESS.  Up to four, because a click lands where it lands and
    # the first press may still have somewhere to go; the one that matters is
    # the press after which the caret stops moving.
    presses = []
    for step in range(1, 5):
        before = evaluate(session, SINK_AT) or {}
        started = time.monotonic()
        press_key(session, "ArrowUp", 38)
        moved = False
        after = before
        watch = time.monotonic() + 4.0
        while time.monotonic() < watch:
            time.sleep(0.15)
            state = evaluate(session, READ_STATE) or {}
            after = evaluate(session, SINK_AT) or after
            if dead(state):
                break
            if after != before:
                moved = True
                break
        presses.append({"press": step, "moved": moved,
                        "seconds": round(time.monotonic() - started, 2),
                        "sinkBefore": before, "sinkAfter": after})
        if not moved:
            break
    record["presses"] = presses
    record["boundaryPress"] = len(presses)

    # WHAT THE CHECKPOINT SAYS WHILE THE PRESS IS STILL IN FLIGHT.  Read here
    # rather than after the death, because the death rebuilds the snapshot.
    record["checkpointAfterTheKey"] = (
        evaluate(session, READ_NOTICE) or {}).get("checkpoint")

    # DID THE ENGINE ANSWER?  Null on every artifact in this tree, and that is
    # the half this probe cannot fix -- see the module docstring.
    settled = wait_state(session,
                         lambda s: dead(s) or s.get("state") == "ready", 75)
    record["stateAfterPress"] = (settled or {}).get("state")
    record["boundaryPressAnsweredSeconds"] = (
        None if dead(settled) else presses[-1]["seconds"])

    notice = evaluate(session, READ_NOTICE) or {}
    record["notice"] = notice
    record["noticeMatchesOwnerQuote"] = (notice.get("text") or "").strip() == OWNER_NOTICE
    if not dead(settled):
        # The engine answered.  Then there is no notice to press and no rescue
        # to test, and this attempt measures the OTHER world.  Recorded, not
        # judged as a failure: it is what the owner's link is expected to
        # produce, and this probe must be able to say so.
        record["outcome"] = "ENGINE_ANSWERED"
        record["why"] = ("the boundary press was answered and the session "
                         "stayed usable, so half C was never reached")
        return record

    record["pressedTheButton"] = evaluate(session, CLICK_NOTICE)
    recovered = wait_state(session, lambda s: s.get("state") == "ready", 240)
    record["stateAfterRecovery"] = (recovered or {}).get("state")
    if record["stateAfterRecovery"] != "ready":
        record["outcome"] = "VOID"
        record["why"] = "the product's own recovery button did not return a usable session"
        record["toasts"] = evaluate(session, READ_TOASTS)
        return record

    # THE ONLY THING JUDGED: what came back.
    evaluate(session, CLEAR_TOAST)
    saved = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
    record["savedBytes"] = saved.get("bytes")
    record["savedIsOdt"] = is_an_odt(saved)
    if not record["savedIsOdt"]:
        record["outcome"] = "VOID"
        record["why"] = "the save after the recovery produced no readable ODT"
        record["toasts"] = evaluate(session, READ_TOASTS)
        return record
    record["workCameBack"] = SENTINEL in (saved.get("content") or "")
    record["outcome"] = "RECOVERED" if record["workCameBack"] else "WORK_LOST"
    record["completedAt"] = datetime.now(timezone.utc).isoformat()
    return record


def run_arm(arm: str, source: str, attempts: int, report: dict) -> None:
    root = PROJECT / "dist"
    overrides: dict[str, bytes] = {}
    if arm == "without":
        broken = source.replace(THE_FIX, "")
        assert broken != source, (
            "the mutation matched nothing -- the `without` arm would have run "
            "the FIXED product and reported agreement between two identical "
            "mirrors")
        overrides[SESSION_JS] = broken.encode("utf-8")
    scratch = Path(tempfile.mkdtemp(prefix=f"f096-c-{arm}-"))
    mirror = scratch / "root"
    build_mirror(root, mirror, overrides)
    served = (mirror / SESSION_JS).read_bytes()
    entry = {
        "arm": arm,
        "servedSessionSha256": hashlib.sha256(served).hexdigest(),
        "servedCarriesTheFix": THE_FIX in served.decode("utf-8"),
        "servedFrom": str(mirror),
        "attempts": [],
    }
    report["arms"].append(entry)
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(mirror)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    entry["port"] = port
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session = ChromeSession("cold")
        report.setdefault("browser", session.version)
        session.call("Emulation.setDeviceMetricsOverride",
                     {"width": 1920, "height": 1080,
                      "deviceScaleFactor": 1, "mobile": False})
        for index in range(1, attempts + 1):
            got = attempt(session, base, arm, index)
            entry["attempts"].append(got)
            print(f"[{arm}] #{index}: {got.get('outcome')} "
                  f"rescue={((got.get('notice') or {}).get('rescue'))} "
                  f"checkpoint={got.get('checkpointAfterTheKey')!r} "
                  f"cameBack={got.get('workCameBack')}",
                  file=sys.stderr, flush=True)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--arm", action="append",
                        choices=("with", "without"), default=None)
    parser.add_argument("--out")
    args = parser.parse_args()
    arms = args.arm or ["without", "with"]

    source = (PROJECT / "dist" / SESSION_JS).read_text(encoding="utf-8")
    if THE_FIX not in source:
        print("the served shell does not carry the fix; run `make e2-c-assets`",
              file=sys.stderr)
        return 2

    report = {
        "schemaVersion": 1,
        "finding": "096",
        "half": "C -- the checkpoint before the gesture",
        "evidenceClass": "red-case",
        "profile": "e2-editor-v8 (the shipping bytes, as the page pins them)",
        "fixture": FIXTURE_URL,
        "sentinel": SENTINEL,
        "mayNotNameACause": True,
        "engineHalfIsUnmeasurable": (
            "no artifact in this tree carries the move-path deadline, so the "
            "boundary press is expected to wedge in BOTH arms"),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "arms": [],
    }
    for arm in arms:
        run_arm(arm, source, args.attempts, report)
        if args.out:
            Path(args.out).write_text(
                json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8")
    report["completedAt"] = datetime.now(timezone.utc).isoformat()

    counts: dict = {}
    for entry in report["arms"]:
        for got in entry["attempts"]:
            key = f"{entry['arm']}:{got.get('outcome')}"
            counts[key] = counts.get(key, 0) + 1
    report["counts"] = counts
    # THE COMPARISON IS THE RESULT.  Either arm alone proves nothing: an arm
    # that recovers could be recovering from an authority save nobody noticed,
    # and an arm that loses the work could be a probe that never typed.
    with_arm = [g for e in report["arms"] if e["arm"] == "with"
                for g in e["attempts"]]
    without_arm = [g for e in report["arms"] if e["arm"] == "without"
                   for g in e["attempts"]]
    report["verdict"] = {
        "withRecoveredEvery": bool(with_arm) and all(
            g.get("outcome") == "RECOVERED" for g in with_arm),
        "withoutLostEvery": bool(without_arm) and all(
            g.get("outcome") == "WORK_LOST" for g in without_arm),
        "armsDisagree": bool(with_arm) and bool(without_arm) and all(
            g.get("outcome") == "RECOVERED" for g in with_arm) and all(
            g.get("outcome") == "WORK_LOST" for g in without_arm),
    }
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    print(json.dumps(report["counts"], ensure_ascii=False), file=sys.stderr)
    print(json.dumps(report["verdict"], ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
