#!/usr/bin/env python3
"""Finding 098: does moving the caret on an untouched document bank a checkpoint?

THE RED CASE, run the way 096's half-C probe ran: the SAME steps on two mirrors
of `dist/` that differ only in the fix, and the two arms are required to
disagree.

  * arm `unfixed` -- the v2 session as it was before the fix.  Predicted: the
                     first ArrowRight leaves `#s-checkpoint` at 無, the second
                     turns it into 有（r0） -- a checkpoint of bytes identical to
                     what was opened, on a document nobody typed into.
  * arm `fixed`   -- the fix applied.  Predicted: 無 after every press.

A POSITIVE CONTROL IN BOTH ARMS (AGENTS.md section 6, and the memory "every
'X did not happen' arm needs a positive control"): after the clean presses, the
probe types through the product's own insert control and presses ArrowRight
once more.  Both arms must then show 有（rN） with N the revision the typing
produced.  Without it, 無 in the fixed arm could mean "half C never runs" rather
than "half C correctly had nothing to do".

WHY ArrowRight IN THE MIDDLE OF A LINE.  The page pins `e2-editor-v8`, which has
no move-path deadline, so a press at a document BOUNDARY wedges for 30 s and
kills the session (finding 096).  098 does not need a boundary: every one of the
six key-path moves goes through `_checkpointBeforeBoundaryMove`, wherever the
caret is.  A mid-line ArrowRight is answered in ~50 ms and keeps the session
alive, so what is measured is 098 and nothing else.

WHAT THIS CANNOT SEE.  Finding 099 (a checkpoint skipped after a rollback,
because the guard compared revisions from two Worker generations) needs two
induced deaths and a revision coincidence; it is measured at unit level only
(editor-shell-v2/tests/narrow-editor-v2-session.test.mjs).  The page does not
render `dirty`, so this probe reads what the user can see: the checkpoint label
and the revision label.  CONSEQUENCE, named by the second review: a fix that
only guarded the checkpoint (leaving a move a mutation and `dirty` lying) would
give the SAME labels.  What this run shows is "no checkpoint of a clean
document"; "a move is not a mutation" is pinned by the unit tests only.

Usage:
  probe_098_a_caret_move_banks_a_checkpoint.py [--attempts 3] [--out FILE]
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
    DEAD_STATES, INSTALL, LINE_INK, OPEN_FILE, POINT_AT, PRESS, SET_TEXT,
    build_mirror, caret_click_fractions, stable_bands,
)

SESSION_JS = "editor-shell-v2/narrow-editor-v2-session.js"

# The fix, as (unfixed, fixed) source-text pairs.  Exact text rather than a
# regular expression: a pattern that silently matched nothing would give both
# arms the same bytes and report agreement between two identical mirrors.
# Filled in from the landed fix; each arm asserts every pair resolved.
FIX_PAIRS: list[tuple[str, str]] = [
    # 098 -- a move is not a mutation.
    ("      { mutation: true },\n    )",
     "      { mutation: !BOUNDARY_CAPABLE_MOVES.has(action) },\n    )"),
    # 099 -- the price control compares content stamps, not revisions.  Carried
    # in the same pair list because the landed fix is both; this probe cannot
    # SEE 099 (see the docstring), so the unfixed arm reverting it too only
    # makes that arm's session code-identical to the pre-fix shell.
    ("        && this._checkpointRevision === document.revision) {",
     "        && this._checkpointStamp === this._currentContentStamp) {"),
]

FIXTURE_URL = "./e1-fixtures/list-contexts.odt"
SENTINEL = "F098MOVEMARK"
CLEAN_PRESSES = 5

SINK_AT = """(() => {
const sink = document.querySelector('#sink');
return sink ? { top: sink.offsetTop, left: sink.offsetLeft } : null;
})()"""


def served_session(source: str, arm: str) -> str:
    """The session source this arm serves; refuses to guess."""
    text = source
    for unfixed, fixed in FIX_PAIRS:
        want, other = (fixed, unfixed) if arm == "fixed" else (unfixed, fixed)
        if text.count(want) == 1 and other not in text:
            continue
        if text.count(other) != 1:
            raise SystemExit(
                f"arm {arm}: a fix pair matched neither side exactly once -- "
                "the tree moved under the probe; fix the pair, do not patch "
                "blindly")
        text = text.replace(other, want, 1)
    return text


def dead(state) -> str | None:
    name = (state or {}).get("state")
    return name if name in DEAD_STATES else None


def wait_state(session, predicate, timeout: float):
    deadline = time.monotonic() + timeout
    state = None
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if state and predicate(state):
            return state
        time.sleep(0.3)
    return state


def press_right(session) -> dict:
    """One real ArrowRight at the renderer; waits for the caret to move."""
    before = evaluate(session, SINK_AT) or {}
    started = time.monotonic()
    for kind in ("rawKeyDown", "keyUp"):
        session.call("Input.dispatchKeyEvent",
                     {"type": kind, "key": "ArrowRight", "code": "ArrowRight",
                      "windowsVirtualKeyCode": 39, "nativeVirtualKeyCode": 39})
    moved = False
    after = before
    watch = time.monotonic() + 4.0
    while time.monotonic() < watch:
        time.sleep(0.15)
        after = evaluate(session, SINK_AT) or after
        if after != before:
            moved = True
            break
    # The drain settles after the caret announcement; read the labels once it
    # is back to ready so a checkpoint save in flight is not missed.
    settled = wait_state(session, lambda s: dead(s) or s.get("state") == "ready",
                         30) or {}
    return {"moved": moved, "seconds": round(time.monotonic() - started, 2),
            "state": settled.get("state"), "revision": settled.get("revision"),
            "checkpoint": settled.get("checkpoint")}


def attempt(session, base: str, arm: str, index: int) -> dict:
    record: dict = {"arm": arm, "attempt": index,
                    "startedAt": datetime.now(timezone.utc).isoformat()}
    navigate(session, base)
    evaluate(session, INSTALL)
    booted = wait_state(session, lambda s: s.get("state") in ("ready", "stopped",
                                                             "expired"), 180)
    record["boot"] = (booted or {}).get("state")
    if record["boot"] != "ready":
        record.update(outcome="VOID", why=f"the page booted to {record['boot']!r}")
        return record

    name = f"f098-{arm}-{index}.odt"
    evaluate(session, OPEN_FILE.replace("ARG_URL", FIXTURE_URL)
             .replace("ARG_NAME", name))
    opened = wait_state(session, lambda s: (s.get("doc") or "") == name
                        and s.get("state") == "ready", 180)
    record["opened"] = (opened or {}).get("state")
    if record["opened"] != "ready":
        record.update(outcome="VOID", why=f"the fixture did not open: {record['opened']!r}")
        return record
    record["checkpointAtOpen"] = (opened or {}).get("checkpoint")
    record["revisionAtOpen"] = (opened or {}).get("revision")

    # A MIDDLE LINE, from the ink.  Near the start of it, so ArrowRight has
    # somewhere to go for every press and no press is a boundary press.
    scan, bands = stable_bands(session)
    record["bands"] = len(bands)
    if len(bands) < 3:
        record.update(outcome="VOID", why="fewer than three text bands; no middle line")
        return record
    line = bands[len(bands) // 2]
    y = f"{line['centreFraction']:.5f}"
    fractions = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", y)) or {})
    record["click"] = {"x": fractions["near"], "y": y}
    evaluate(session, POINT_AT.replace("ARG_X", fractions["near"])
             .replace("ARG_Y", y))
    placed = wait_state(session, lambda s: "定位游標" in (s.get("latency") or ""), 90)
    record["placed"] = (placed or {}).get("latency")
    if "定位游標" not in (record["placed"] or "") or "失敗" in (record["placed"] or ""):
        record.update(outcome="VOID", why=f"the caret could not be placed: {record['placed']!r}")
        return record
    record["checkpointAfterClick"] = (placed or {}).get("checkpoint")

    # THE MEASUREMENT: clean presses, labels read after each.
    record["cleanPresses"] = [press_right(session) for _ in range(CLEAN_PRESSES)]
    if any(dead(p) for p in record["cleanPresses"]) \
            or not all(p["moved"] for p in record["cleanPresses"]):
        record.update(outcome="VOID", why="a clean press did not move the caret "
                      "or the session died; this attempt measured something else")
        return record

    # THE POSITIVE CONTROL: real work, then one more press.
    before = evaluate(session, READ_STATE) or {}
    evaluate(session, SET_TEXT.replace("ARG_TEXT", SENTINEL))
    evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
    typed = wait_state(session, lambda s: (s.get("revision") or "")
                       != (before.get("revision") or ""), 120) or {}
    record["revisionAfterTyping"] = typed.get("revision")
    record["checkpointAfterTyping"] = typed.get("checkpoint")
    record["controlPress"] = press_right(session)

    clean_labels = [p["checkpoint"] for p in record["cleanPresses"]]
    record["cleanLabels"] = clean_labels
    record["cleanRevisions"] = [p["revision"] for p in record["cleanPresses"]]
    banked_clean = any((label or "").startswith("有") for label in clean_labels)
    # "Untouched" is EXACTLY 無 on every press -- not "anything but 有".  A
    # failed checkpoint save renders 寫入失敗 and a missing label renders None;
    # neither is a clean document left alone (second review, 2026-09-28).
    untouched = all(label == "無" for label in clean_labels)
    control_ok = (record["controlPress"]["checkpoint"] or "") \
        == f"有（r{record['revisionAfterTyping']}）"
    record["controlBanked"] = control_ok
    if not control_ok:
        record["outcome"] = "CONTROL_FAILED"
    elif banked_clean:
        record["outcome"] = "BANKED_ON_A_CLEAN_DOCUMENT"
    elif untouched:
        record["outcome"] = "CLEAN_DOCUMENT_UNTOUCHED"
    else:
        record["outcome"] = "NEITHER"
    record["completedAt"] = datetime.now(timezone.utc).isoformat()
    return record


def run_arm(arm: str, source: str, attempts: int, report: dict,
            require_landed: bool = False) -> None:
    served = served_session(source, arm)
    scratch = Path(tempfile.mkdtemp(prefix=f"f098-{arm}-"))
    mirror = scratch / "root"
    build_mirror(PROJECT / "dist", mirror, {SESSION_JS: served.encode("utf-8")})
    on_disk = (mirror / SESSION_JS).read_bytes()
    landed = (PROJECT / SESSION_JS).read_bytes()
    if arm == "fixed" and require_landed and on_disk != landed:
        raise SystemExit("--require-landed: the fixed arm would not serve the "
                         "source tree's session file; run `make e2-c-assets`")
    page = (mirror / "e2-editor-app.js").read_bytes()
    entry = {"arm": arm,
             "servedSessionSha256": hashlib.sha256(on_disk).hexdigest(),
             # What dist/ held when the run started, and what the SOURCE tree
             # holds.  After `make e2-c-assets` the two are equal and the fixed
             # arm serves the landed bytes; before it they are not.
             "distSessionSha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
             "landedSessionSha256": hashlib.sha256(landed).hexdigest(),
             "servesLandedBytes": on_disk == landed,
             "servedPageSha256": hashlib.sha256(page).hexdigest(),
             "servedPin": (page.decode("utf-8").split('PINNED_WASM_SHA256 = "', 1)[1]
                           .split('"', 1)[0]),
             "servedMatchesArm": on_disk.decode("utf-8") == served,
             "servedFrom": str(mirror), "attempts": []}
    report["arms"].append(entry)
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
        report.setdefault("browser", session.version)
        session.call("Emulation.setDeviceMetricsOverride",
                     {"width": 1920, "height": 1080,
                      "deviceScaleFactor": 1, "mobile": False})
        for index in range(1, attempts + 1):
            got = attempt(session, base, arm, index)
            entry["attempts"].append(got)
            print(f"[{arm}] #{index}: {got.get('outcome')} "
                  f"clean={got.get('cleanLabels')} "
                  f"control={(got.get('controlPress') or {}).get('checkpoint')!r}",
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
    parser.add_argument("--arm", action="append", choices=("unfixed", "fixed"),
                        default=None)
    parser.add_argument("--out")
    parser.add_argument("--require-landed", action="store_true",
                        help="refuse unless the fixed arm serves exactly the "
                             "source tree's session file")
    args = parser.parse_args()
    if not FIX_PAIRS:
        print("FIX_PAIRS is empty: the two arms would serve identical bytes",
              file=sys.stderr)
        return 2
    arms = args.arm or ["unfixed", "fixed"]
    source = (PROJECT / "dist" / SESSION_JS).read_text(encoding="utf-8")
    report = {
        "schemaVersion": 1, "finding": "098", "evidenceClass": "red-case",
        "profile": "e2-editor-v8 (the page as dist/ pins it)",
        "fixture": FIXTURE_URL, "cleanPresses": CLEAN_PRESSES,
        "prediction": {
            "unfixed": "cleanLabels: 無 after press 1, 有（r0） from press 2 on; "
                       "control 有（rN）",
            "fixed": "cleanLabels: 無 on every press; control 有（rN）"},
        "startedAt": datetime.now(timezone.utc).isoformat(), "arms": []}
    for arm in arms:
        run_arm(arm, source, args.attempts, report, args.require_landed)
        if args.out:
            Path(args.out).write_text(json.dumps(report, ensure_ascii=False,
                                                 indent=1) + "\n", encoding="utf-8")
    report["completedAt"] = datetime.now(timezone.utc).isoformat()
    by_arm = {e["arm"]: e["attempts"] for e in report["arms"]}
    unfixed = by_arm.get("unfixed", [])
    fixed = by_arm.get("fixed", [])
    report["verdict"] = {
        "unfixedBankedEvery": bool(unfixed) and all(
            g.get("outcome") == "BANKED_ON_A_CLEAN_DOCUMENT" for g in unfixed),
        "fixedUntouchedEvery": bool(fixed) and all(
            g.get("outcome") == "CLEAN_DOCUMENT_UNTOUCHED" for g in fixed),
    }
    report["verdict"]["armsDisagree"] = (report["verdict"]["unfixedBankedEvery"]
                                         and report["verdict"]["fixedUntouchedEvery"])
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    print(json.dumps(report["verdict"], ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
