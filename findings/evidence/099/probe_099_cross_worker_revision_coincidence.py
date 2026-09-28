#!/usr/bin/env python3
"""Finding 099, the CROSS-Worker mode, at browser level on the real engine.

WHAT 099 CLAIMS (the cross-Worker half).  Revisions restart at zero with every
Worker (`src/probe_engine.cpp`, `gState.revision = 0` on open), while the
checkpoint survives the rollback -- that is what it is for.  Before the fix,
half C's price control skipped whenever `_checkpointRevision ===
document.revision`, so after one rollback it compared two unrelated counters;
when they coincided, the next boundary-capable press banked nothing, and a
second death went back to the OLDER checkpoint under 「回到檢查點」.

The finding's own trigger conditions say that on v8 "the skipped press may
itself be the boundary press, i.e. it causes the second death".  This probe is
that sentence, driven through the product.

TWO INDUCERS, AND WHY.  Death one is `induce_worker_failure` (an uncaught error
inside the document worker).  It works once per browser -- the within-Worker
probe's first run, 6 of 6 VOID on the second call -- so death two cannot be a
second call.  Death two is the boundary press itself: on `e2-editor-v8` (no
half A, no move-path deadline) an ArrowUp on the first line of the document
wedges for the SDK's 30 s and the session dies (finding 096; check 42 exercises
exactly this on v8).  So this probe runs on v8 only, by construction: on v14
half A answers the press and there is no second death.

STEPS (the product's controls; keys are real CDP key events; fixture
`multi-paragraph.odt`):
  1. click near the start of the FIRST line; type MARK1                 -> r1
  2. ArrowLeft (mid-line): half C banks                              -> 有（r1）
  3. death one: worker failure -> the notice -> 「回到檢查點」: a new Worker
     opens the r1 checkpoint; the revision label is READ here (premise:
     it restarts at 0)
  4. click near the start of the first line again (placeCaret, which banks
     nothing); type MARK2 -> revision 1 in the new Worker, equal to the old
     checkpoint's r1 -- the coincidence, engineered
  5. ArrowUp until a press does not move the caret -- check 42's loop.  The
     first ArrowUp on the first line moves the caret to the start of the
     document and is answered (measured in this probe's shakedown: one press
     left the session `ready`); the next one has nowhere to go and wedges.
     EVERY one of them asks half C's guard first, and every one of them sees
     the same revision 1 and the same stamp, so THE FIRST ArrowUp is the press
     under test: the pre-fix guard sees revision 1 == checkpoint revision 1 and
     skips it and every press after it; the landed guard sees a new stamp,
     banks MARK2 on the first press, and then skips (stamp unchanged).
  6. the notice -> 「回到檢查點」 -> save through the product -> content.xml

ARMS: the same three as the within-Worker probe (`prefix`, `a-only`, `landed`),
served the same way and asserted the same way.

CRITERIA, written before the first run (per attempt):
  * VOID unless: every step reached its state; the step-2 label is exactly
    有（r1）; death one happened and offered `rescue: checkpoint`; the session
    came back ready; MARK2's typing advanced the revision to exactly 1 (else
    there is no coincidence and nothing here is 099's cell); the ArrowUp was
    taken by the page and the session then died; the notice offered
    `rescue: checkpoint`; recovery returned a ready session; the save is an
    ODT; and MARK1 is in it (POSITIVE CONTROL: a checkpoint was restored, not
    the authority bytes).
  * `revisionAfterFirstRecovery`: recorded, not a void condition.  Predicted
    "0"; anything else and the premise is false on the real engine.
  * outcome KEPT_MARK2 if MARK2 is in the saved document, LOST_MARK2 if not.
  * PREDICTION: prefix LOST 3/3, a-only LOST 3/3, landed KEPT 3/3.

Usage:
  probe_099_cross_worker_revision_coincidence.py [--attempts 3] [--arm ARM ...] [--out FILE]
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from probe_099_within_worker_review_path import (                   # noqa: E402
    ARMS, PROJECT, SESSION_JS, SINK_AT, paragraphs, press_and_wait_revision,
    press_key, served_session, wait_state,
)
from r7_support import evaluate, wait_page                          # noqa: E402
from run_browser_probe import ChromeSession, free_port              # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate                # noqa: E402
from run_e2_c_product_path import (                                 # noqa: E402
    CLEAR_TOAST, CLICK_NOTICE, INSTALL, INSTALL_KEY_TAKEN, LINE_INK, OPEN_FILE,
    POINT_AT, READ_KEY_TAKEN, READ_NOTICE, SAVE_COUNT, SET_TEXT, build_mirror,
    capture_save, caret_click_fractions, dead_session, induce_worker_failure,
    is_an_odt, stable_bands,
)

PREDICTION = {"prefix": "LOST_MARK2", "a-only": "LOST_MARK2",
              "landed": "KEPT_MARK2"}
FIXTURE_URL = "./e1-fixtures/multi-paragraph.odt"
MARK1 = "F099GENONE"
MARK2 = "F099GENTWO"


def place_on_first_line(session, record: dict, key: str) -> bool:
    scan, bands = stable_bands(session)
    if not bands:
        record[key] = {"bands": 0}
        return False
    y = f"{bands[0]['centreFraction']:.5f}"
    fractions = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", y)) or {})
    evaluate(session, POINT_AT.replace("ARG_X", fractions["near"])
             .replace("ARG_Y", y))
    placed = wait_state(session, lambda s: "定位游標" in (s.get("latency") or ""), 90)
    latency = (placed or {}).get("latency") or ""
    record[key] = {"bands": len(bands), "x": fractions["near"], "y": y,
                   "latency": latency, "checkpoint": (placed or {}).get("checkpoint")}
    return "定位游標" in latency and "失敗" not in latency


def recover(session, record: dict, key: str) -> bool:
    notice = evaluate(session, READ_NOTICE) or {}
    record[key] = {"notice": notice}
    if notice.get("rescue") != "checkpoint":
        return False
    record[key]["pressed"] = evaluate(session, CLICK_NOTICE)
    back = wait_state(session, lambda s: s.get("state") == "ready", 240) or {}
    record[key].update(state=back.get("state"), revision=back.get("revision"),
                       checkpoint=back.get("checkpoint"))
    return back.get("state") == "ready"


def attempt(session, base: str, arm: str, index: int) -> dict:
    record: dict = {"arm": arm, "attempt": index,
                    "startedAt": datetime.now(timezone.utc).isoformat()}

    def void(why: str) -> dict:
        record.update(outcome="VOID", why=why,
                      completedAt=datetime.now(timezone.utc).isoformat())
        return record

    navigate(session, base)
    evaluate(session, INSTALL)
    booted = wait_state(session, lambda s: s.get("state") in ("ready", "stopped",
                                                             "expired"), 180)
    if (booted or {}).get("state") != "ready":
        return void(f"the page booted to {(booted or {}).get('state')!r}")
    name = f"f099x-{arm}-{index}.odt"
    evaluate(session, OPEN_FILE.replace("ARG_URL", FIXTURE_URL)
             .replace("ARG_NAME", name))
    opened = wait_state(session, lambda s: (s.get("doc") or "") == name
                        and s.get("state") == "ready", 180)
    if (opened or {}).get("state") != "ready":
        return void("the fixture did not open")

    # 1-2. Generation one: work, and a checkpoint of it.
    if not place_on_first_line(session, record, "firstClick"):
        return void("the caret could not be placed on the first line")
    evaluate(session, SET_TEXT.replace("ARG_TEXT", MARK1))
    record["typing1"] = press_and_wait_revision(session, "insert-text")
    if record["typing1"]["revisionAfter"] != "1":
        return void(f"MARK1 left revision {record['typing1']['revisionAfter']!r}")
    record["bankPress"] = press_key(session, "ArrowLeft")
    if record["bankPress"]["checkpoint"] != "有（r1）" or not record["bankPress"]["moved"]:
        return void(f"the first checkpoint is {record['bankPress']['checkpoint']!r}")

    # 3. Death one, from outside; back into a new Worker.
    record["inducer"] = induce_worker_failure(session)
    if not record["inducer"].get("fired"):
        return void(f"the worker failure never fired: {record['inducer'].get('why')}")
    died = wait_state(session, dead_session, 90) or {}
    record["stateAfterDeathOne"] = died.get("state")
    if not dead_session(died):
        return void(f"death one did not happen: {died.get('state')!r}")
    if not recover(session, record, "recoveryOne"):
        return void(f"recovery one failed: {record.get('recoveryOne')}")
    record["revisionAfterFirstRecovery"] = record["recoveryOne"]["revision"]

    # 4. Generation two: work, until the new revision equals the old checkpoint's.
    if not place_on_first_line(session, record, "secondClick"):
        return void("the caret could not be placed after recovery")
    if record["secondClick"]["checkpoint"] != "有（r1）":
        return void("the click after recovery changed the checkpoint label: "
                    f"{record['secondClick']['checkpoint']!r}")
    evaluate(session, SET_TEXT.replace("ARG_TEXT", MARK2))
    record["typing2"] = press_and_wait_revision(session, "insert-text")
    if record["typing2"]["revisionAfter"] != "1":
        return void("MARK2 did not land on revision 1 in the new Worker "
                    f"({record['typing2']['revisionAfter']!r}), so there is no "
                    "coincidence and this is not 099's cell")

    # 5. THE PRESS UNDER TEST (the first ArrowUp), and death two on v8.
    started = time.monotonic()
    presses = []
    for step in range(1, 5):
        was = evaluate(session, SINK_AT) or {}
        evaluate(session, INSTALL_KEY_TAKEN)
        pressed_at = time.monotonic()
        for kind in ("rawKeyDown", "keyUp"):
            session.call("Input.dispatchKeyEvent",
                         {"type": kind, "key": "ArrowUp", "code": "ArrowUp",
                          "windowsVirtualKeyCode": 38, "nativeVirtualKeyCode": 38})
        moved = False
        watch = time.monotonic() + 4.0
        while time.monotonic() < watch:
            time.sleep(0.15)
            if dead_session(evaluate(session, READ_STATE)):
                break
            if (evaluate(session, SINK_AT) or was) != was:
                moved = True
                break
        state = evaluate(session, READ_STATE) or {}
        presses.append({
            "press": step, "moved": moved,
            "seconds": round(time.monotonic() - pressed_at, 2),
            "checkpoint": state.get("checkpoint"), "state": state.get("state"),
            "takenByThePage": [k.get("defaultPrevented") for k in
                               (evaluate(session, READ_KEY_TAKEN) or [])
                               if k.get("key") == "ArrowUp"]})
        if not moved:
            break
    record["upPresses"] = presses
    taken = presses[-1]["takenByThePage"]
    if not (taken and all(taken)):
        return void(f"the page did not take the last ArrowUp: {taken!r}")
    died = wait_state(session, lambda s: dead_session(s)
                      or s.get("state") == "ready", 90) or {}
    record["deathTwo"] = {"state": died.get("state"),
                          "seconds": round(time.monotonic() - started, 2),
                          "checkpoint": died.get("checkpoint")}
    if not dead_session(died):
        return void(f"the boundary press did not kill the session: "
                    f"{died.get('state')!r} -- is this a profile with half A?")

    # 6. Back, and what came back.
    if not recover(session, record, "recoveryTwo"):
        return void(f"recovery two failed: {record.get('recoveryTwo')}")
    evaluate(session, CLEAR_TOAST)
    saved = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
    if not (saved and is_an_odt(saved)):
        return void("the save was not a readable ODT")
    texts = [p["text"] for p in paragraphs(saved["content"])]
    record["savedParagraphs"] = texts
    joined = "\n".join(texts)
    # MARK1 IS LOOKED FOR WITH MARK2 TAKEN OUT, and that is a correction, not
    # a loosening (AGENTS.md: a criterion changed after a run says why).  The
    # first full run (cross-worker-v8-2026-09-28-run1-mark1-split-by-mark2.json)
    # voided the landed arm 3/3 on this control: the click after recovery is
    # derived from the line's ink, which MARK1 had lengthened, so it landed
    # INSIDE MARK1 and MARK2 was typed there -- the saved line read
    # `E1-FF099GENTWO099GENONEMULTI-START alpha`.  Every character of MARK1
    # came back, in order, split by the work this probe is about.  Removing
    # MARK2 cannot create MARK1 where it is absent, so the control still fails
    # when no checkpoint was restored.
    record["mark2CameBack"] = MARK2 in joined
    record["mark1CameBack"] = MARK1 in joined.replace(MARK2, "")
    if not record["mark1CameBack"]:
        return void("the POSITIVE CONTROL failed: MARK1 is not in what came "
                    "back, so no checkpoint was restored")
    record["outcome"] = "KEPT_MARK2" if record["mark2CameBack"] else "LOST_MARK2"
    record["completedAt"] = datetime.now(timezone.utc).isoformat()
    return record


def run_arm(arm: str, source: str, attempts: int, report: dict) -> None:
    served = served_session(source, arm)
    scratch = Path(tempfile.mkdtemp(prefix=f"f099x-{arm}-"))
    mirror = scratch / "root"
    build_mirror(PROJECT / "dist", mirror, {SESSION_JS: served.encode("utf-8")})
    on_disk = (mirror / SESSION_JS).read_bytes()
    landed = (PROJECT / SESSION_JS).read_bytes()
    if arm == "landed" and on_disk != landed:
        raise SystemExit("the landed arm would not serve the source tree's "
                         "session file; run `make e2-c-assets`")
    page = (mirror / "e2-editor-app.js").read_bytes()
    entry = {"arm": arm,
             "servedSessionSha256": hashlib.sha256(on_disk).hexdigest(),
             "servesLandedBytes": on_disk == landed,
             "servedPageSha256": hashlib.sha256(page).hexdigest(),
             "servedPin": (page.decode("utf-8").split('PINNED_WASM_SHA256 = "', 1)[1]
                           .split('"', 1)[0]),
             "servedMatchesArm": on_disk.decode("utf-8") == served,
             "prediction": PREDICTION[arm], "attempts": []}
    report["arms"].append(entry)
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(mirror)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        for index in range(1, attempts + 1):
            session = ChromeSession("cold")      # one inducer call per browser
            try:
                report.setdefault("browser", session.version)
                session.call("Emulation.setDeviceMetricsOverride",
                             {"width": 1920, "height": 1080,
                              "deviceScaleFactor": 1, "mobile": False})
                got = attempt(session, base, arm, index)
            except Exception as error:          # noqa: BLE001 -- recorded
                got = {"arm": arm, "attempt": index, "outcome": "VOID",
                       "why": f"the probe raised: {error!r}"}
            finally:
                session.close()
            entry["attempts"].append(got)
            print(f"[{arm}] #{index}: {got.get('outcome')} "
                  f"rev-after-recovery={got.get('revisionAfterFirstRecovery')!r} "
                  f"up={[(p['moved'], p['seconds']) for p in got.get('upPresses') or []]} "
                  f"why={got.get('why')!r}", file=sys.stderr, flush=True)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--arm", action="append", choices=tuple(ARMS), default=None)
    parser.add_argument("--out")
    args = parser.parse_args()
    source = (PROJECT / "dist" / SESSION_JS).read_text(encoding="utf-8")
    if len({served_session(source, arm) for arm in ARMS}) != len(ARMS):
        print("two arms would serve identical bytes", file=sys.stderr)
        return 2
    report = {"schemaVersion": 1, "finding": "099", "mode": "cross-Worker",
              "evidenceClass": "red-case",
              "profile": "e2-editor-v8 (the page as dist/ pins it)",
              "fixture": FIXTURE_URL, "marks": [MARK1, MARK2],
              "prediction": PREDICTION,
              "startedAt": datetime.now(timezone.utc).isoformat(), "arms": []}
    for arm in args.arm or list(ARMS):
        run_arm(arm, source, args.attempts, report)
        if args.out:
            Path(args.out).write_text(json.dumps(report, ensure_ascii=False,
                                                 indent=1) + "\n", encoding="utf-8")
    report["completedAt"] = datetime.now(timezone.utc).isoformat()
    verdict: dict = {}
    for entry in report["arms"]:
        outcomes = [a.get("outcome") for a in entry["attempts"]]
        verdict[entry["arm"]] = {
            "outcomes": outcomes,
            "asPredictedEvery": bool(outcomes) and all(
                o == PREDICTION[entry["arm"]] for o in outcomes),
            "revisionAfterFirstRecovery": [a.get("revisionAfterFirstRecovery")
                                           for a in entry["attempts"]],
        }
    verdict["armsDisagreeAsPredicted"] = all(
        verdict.get(arm, {}).get("asPredictedEvery") for arm in ARMS)
    report["verdict"] = verdict
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    print(json.dumps(verdict, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
