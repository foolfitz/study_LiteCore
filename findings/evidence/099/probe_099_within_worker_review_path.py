#!/usr/bin/env python3
"""Finding 099, the WITHIN-Worker mode, at browser level on the real engine.

WHAT 099 CLAIMS (the within-Worker half).  A format action that comes back
"dispatched, unverified" (`recoveryFor` -> "review") is counted by the session
as a mutation -- the drain bumps the content stamp -- but the engine does not
advance the revision on that path (`failFormatBarrier` never calls
`advanceRevision`, `src/probe_engine.cpp`).  Before the fix, half C's price
control skipped a checkpoint whenever `_checkpointRevision === document.revision`,
so the arrow key after such an action banked nothing, and a death after it went
back to the OLDER checkpoint under a notice saying 「回到檢查點」.

Until this probe that was measured at unit level only, against the test file's
FIXTURE engine.  The two premises it rests on -- the review path is reachable
from the product's buttons, and the real engine leaves the revision where it was
on that path -- were read from source, not measured.  This probe measures both,
and then the consequence.

THE REVIEW-PATH INDUCER is finding 046's residual, the cell
`bulleting-a-blank-line-does-not-demand-a-rollback` already drives: on the
shipping core `.uno:SelectText` on an EMPTY paragraph overshoots into the
paragraph below, the barrier declines to say which paragraph it read, and the
disposition is "review".  The empty paragraph is made here the way that cell
makes it -- click past a line's end, `insert-paragraph-break` -- on
`multi-paragraph.odt`, whose paragraphs are one line each, so the new empty
paragraph always has a paragraph below it.

THE DEATH INDUCER is `induce_worker_failure` (a real uncaught error inside the
document worker, `Target.setAutoAttach`), the one check 42 uses on v14.  Not a
boundary press: the pressed key must be an ordinary mid-document move, so that
what differs between arms is the guard and nothing else.

STEPS (all through the product's own controls; keys are real CDP key events):
  1. open `multi-paragraph.odt`; click past the end of the SECOND line;
  2. type SENTINEL through the insert control            -> revision r1
  3. `insert-paragraph-break`: caret on a new empty paragraph -> r2
  4. ArrowLeft  (to the end of paragraph 2): half C banks  -> 有（r2）  [all arms]
  5. ArrowRight (back onto the empty paragraph): banks nothing        [all arms]
  6. 「• 項目符號」: the review toast; the revision is READ here (premise 2)
  7. ArrowLeft -- THE PRESS UNDER TEST.  Stamp moved, revision did not.
  8. induce a worker failure; press the product's notice; save through the
     product's save button; read content.xml.

ARMS (the served session file differs only in exact-text pairs; nothing else):
  * `prefix`  -- both halves reverted: the v51 guard, moves still mutations.
  * `a-only`  -- 098's half only (moves are not mutations), the REVISION guard
                 kept.  This is the arm that isolates 099's fix: the only
                 difference from `landed` is the one comparison.
  * `landed`  -- the tree's file, byte-identical (`servesLandedBytes`).

CRITERIA, written before the first run (per attempt):
  * VOID unless: boot, open, typing and break each advanced the revision; the
    step-4 label is exactly 有（r2） and step 5 left it there; the step-6 toast
    carries the review promise 「不是你要的就按「復原」」 and not 「請回到檢查點」;
    the worker failure fired and the session died; the notice offered
    `rescue: checkpoint`; the notice's button returned a ready session; the
    save is an ODT; the SENTINEL paragraph is in it; and the paragraph after it
    is EMPTY -- that last pair is the POSITIVE CONTROL that the checkpoint
    restored is the r2 one (typing and break both present), not the authority
    bytes and not r1.
  * `revisionUnchangedByReview`: revision after step 6 == revision before it.
    Recorded, NOT a void condition -- if it is false the within-Worker premise
    is false on the real engine and every arm should keep the bullet; that is
    a result, and it would retract half of 099's claim.
  * outcome KEPT_THE_BULLET: the empty paragraph after the SENTINEL is inside
    a `text:list-item`.  LOST_THE_BULLET: it is not.
  * PREDICTION: prefix LOST 3/3, a-only LOST 3/3, landed KEPT 3/3.

WHAT THE CROSS-ARM DESIGN BUYS AND WHAT IT DOES NOT.  LOST in `prefix` or
`a-only` alone could mean "the bullet never reached the document".  KEPT in
`landed`, on the same recipe and the same engine, is what rules that out: the
arms differ only in session code that runs AFTER the bullet was dispatched.  No
arm checks the bullet is applied in the live session before the death (the
barrier could not verify it, which is the whole review path, and the page
renders no list state).

The page pins `e2-editor-v8`.  The profile that will ship with half C is v14;
the guard is profile-independent session code, and v14's core takes the review
path by a different sentence (finding 083, 「取不到任何內容」) which this probe
accepts, but it has only been run where stated in its report.

Usage:
  probe_099_within_worker_review_path.py [--attempts 3] [--arm ARM ...] [--out FILE]
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
from xml.etree import ElementTree

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
sys.path.insert(0, str(PROJECT / "tools"))

from r7_support import evaluate, wait_page                          # noqa: E402
from run_browser_probe import ChromeSession, free_port              # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate                # noqa: E402
from run_e2_c_product_path import (                                 # noqa: E402
    CLEAR_TOAST, CLICK_NOTICE, INSTALL, LINE_INK, OPEN_FILE, POINT_AT, PRESS,
    READ_NOTICE, READ_TOAST, SAVE_COUNT, SET_TEXT, build_mirror,
    capture_save, caret_click_fractions, dead_session, induce_worker_failure,
    is_an_odt, repointed_page, stable_bands,
)

SESSION_JS = "editor-shell-v2/narrow-editor-v2-session.js"

# (unfixed, fixed) exact-text pairs, the same two the 098 probe carries.  Exact
# text: a pattern that silently matched nothing would give two arms the same
# bytes and report agreement between identical mirrors.
PAIR_098 = ("      { mutation: true },\n    )",
            "      { mutation: !BOUNDARY_CAPABLE_MOVES.has(action) },\n    )")
PAIR_099 = ("        && this._checkpointRevision === document.revision) {",
            "        && this._checkpointStamp === this._currentContentStamp) {")
ARMS = {
    "prefix": {PAIR_098: False, PAIR_099: False},
    "a-only": {PAIR_098: True, PAIR_099: False},
    "landed": {PAIR_098: True, PAIR_099: True},
}
PREDICTION = {"prefix": "LOST_THE_BULLET", "a-only": "LOST_THE_BULLET",
              "landed": "KEPT_THE_BULLET"}

FIXTURE_URL = "./e1-fixtures/multi-paragraph.odt"
SENTINEL = "F099REVIEWMARK"
LINE_INDEX = 1            # the second of five one-line paragraphs
REVIEW_PROMISE = "不是你要的就按「復原」"
ROLLBACK_PRESCRIPTION = "請回到檢查點"

NS_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
NS_OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"

SINK_AT = """(() => {
const sink = document.querySelector('#sink');
return sink ? { top: sink.offsetTop, left: sink.offsetLeft } : null;
})()"""

KEYS = {"ArrowLeft": 37, "ArrowRight": 39}


def served_session(source: str, arm: str) -> str:
    """The session source this arm serves; refuses to guess."""
    text = source
    for pair, fixed in ARMS[arm].items():
        want, other = (pair[1], pair[0]) if fixed else pair
        if text.count(want) == 1 and other not in text:
            continue
        if text.count(other) != 1:
            raise SystemExit(
                f"arm {arm}: a fix pair matched neither side exactly once -- "
                "the tree moved under the probe; fix the pair, do not patch "
                "blindly")
        text = text.replace(other, want, 1)
    return text


def wait_state(session, predicate, timeout: float, poll: float = 0.3):
    deadline = time.monotonic() + timeout
    state = None
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if state and predicate(state):
            return state
        time.sleep(poll)
    return state


def press_key(session, key: str) -> dict:
    """One real key at the renderer; waits for the caret, then for `ready`."""
    before = evaluate(session, SINK_AT) or {}
    started = time.monotonic()
    code = KEYS[key]
    for kind in ("rawKeyDown", "keyUp"):
        session.call("Input.dispatchKeyEvent",
                     {"type": kind, "key": key, "code": key,
                      "windowsVirtualKeyCode": code, "nativeVirtualKeyCode": code})
    moved = False
    after = before
    watch = time.monotonic() + 4.0
    while time.monotonic() < watch:
        time.sleep(0.15)
        after = evaluate(session, SINK_AT) or after
        if after != before:
            moved = True
            break
    settled = wait_state(session, lambda s: dead_session(s)
                         or s.get("state") == "ready", 60) or {}
    return {"key": key, "moved": moved,
            "seconds": round(time.monotonic() - started, 2),
            "state": settled.get("state"), "revision": settled.get("revision"),
            "checkpoint": settled.get("checkpoint")}


def press_and_wait_revision(session, action: str, timeout: float = 120) -> dict:
    before = evaluate(session, READ_STATE) or {}
    evaluate(session, PRESS.replace("ARG_ACTION", action))
    after = wait_state(session, lambda s: dead_session(s)
                       or ((s.get("revision") or "") != (before.get("revision") or "")
                           and s.get("state") == "ready"), timeout) or {}
    return {"action": action, "revisionBefore": before.get("revision"),
            "revisionAfter": after.get("revision"), "state": after.get("state"),
            "checkpoint": after.get("checkpoint")}


def paragraphs(content_xml: str) -> list[dict]:
    """Every text:p / text:h in the body, in document order, with list context."""
    root = ElementTree.fromstring(content_xml)
    body = root.find(f"{{{NS_OFFICE}}}body/{{{NS_OFFICE}}}text")
    out: list[dict] = []

    def walk(node, in_list: bool) -> None:
        for child in node:
            tag = child.tag
            if tag in (f"{{{NS_TEXT}}}p", f"{{{NS_TEXT}}}h"):
                out.append({"tag": tag.split("}")[1],
                            "text": "".join(child.itertext()),
                            "inListItem": in_list})
                continue
            walk(child, in_list or tag == f"{{{NS_TEXT}}}list-item")

    if body is not None:
        walk(body, False)
    return out


def classify(saved: dict) -> dict:
    """What came back, read off the saved content.xml."""
    if not (saved and is_an_odt(saved)):
        return {"readable": False}
    paras = paragraphs(saved["content"])
    hits = [i for i, p in enumerate(paras) if SENTINEL in p["text"]]
    out: dict = {"readable": True, "paragraphs": paras,
                 "sentinelParagraphs": hits}
    if len(hits) != 1:
        out["sentinelCameBack"] = bool(hits)
        return out
    out["sentinelCameBack"] = True
    after = paras[hits[0] + 1] if hits[0] + 1 < len(paras) else None
    out["paragraphAfterSentinel"] = after
    out["breakCameBack"] = bool(after) and after["text"] == ""
    out["bulletCameBack"] = bool(after) and after["text"] == "" \
        and after["inListItem"]
    return out


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
    record["boot"] = (booted or {}).get("state")
    if record["boot"] != "ready":
        return void(f"the page booted to {record['boot']!r}")

    name = f"f099-{arm}-{index}.odt"
    evaluate(session, OPEN_FILE.replace("ARG_URL", FIXTURE_URL)
             .replace("ARG_NAME", name))
    opened = wait_state(session, lambda s: (s.get("doc") or "") == name
                        and s.get("state") == "ready", 180)
    record["opened"] = (opened or {}).get("state")
    if record["opened"] != "ready":
        return void(f"the fixture did not open: {record['opened']!r}")
    record["revisionAtOpen"] = (opened or {}).get("revision")
    record["checkpointAtOpen"] = (opened or {}).get("checkpoint")

    # 1. Past the end of the second line, from the ink.
    scan, bands = stable_bands(session)
    record["bands"] = len(bands)
    if len(bands) != 5:
        return void(f"{len(bands)} text bands, expected the fixture's five")
    y = f"{bands[LINE_INDEX]['centreFraction']:.5f}"
    fractions = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", y)) or {})
    record["click"] = {"x": fractions["past"], "y": y,
                       "derived": fractions.get("derived")}
    evaluate(session, POINT_AT.replace("ARG_X", fractions["past"])
             .replace("ARG_Y", y))
    placed = wait_state(session, lambda s: "定位游標" in (s.get("latency") or ""), 90)
    record["placed"] = (placed or {}).get("latency")
    if "定位游標" not in (record["placed"] or "") or "失敗" in (record["placed"] or ""):
        return void(f"the caret could not be placed: {record['placed']!r}")

    # 2. Work worth losing.
    evaluate(session, SET_TEXT.replace("ARG_TEXT", SENTINEL))
    record["typing"] = press_and_wait_revision(session, "insert-text")
    if record["typing"]["revisionAfter"] == record["typing"]["revisionBefore"]:
        return void("the insert never reached the document")

    # 3. The empty paragraph.
    record["break"] = press_and_wait_revision(session, "insert-paragraph-break")
    if record["break"]["revisionAfter"] == record["break"]["revisionBefore"] \
            or record["break"]["state"] != "ready":
        return void("the paragraph break did not advance the revision")
    r2 = record["break"]["revisionAfter"]

    # 4-5. Bank the checkpoint at r2, and come back onto the empty paragraph.
    record["bankPress"] = press_key(session, "ArrowLeft")
    record["returnPress"] = press_key(session, "ArrowRight")
    if record["bankPress"]["checkpoint"] != f"有（r{r2}）" \
            or record["returnPress"]["checkpoint"] != f"有（r{r2}）" \
            or not (record["bankPress"]["moved"] and record["returnPress"]["moved"]):
        return void("the checkpoint was not banked at the break's revision by "
                    "the first move, or the second move changed it, or a move "
                    "did not move the caret: "
                    f"{record['bankPress']['checkpoint']!r} then "
                    f"{record['returnPress']['checkpoint']!r}")

    # 6. The review path.  Premise 2 is READ here.
    evaluate(session, CLEAR_TOAST)
    before = evaluate(session, READ_STATE) or {}
    evaluate(session, PRESS.replace("ARG_ACTION", "set-list-unordered"))
    reviewed = wait_state(session, lambda s: dead_session(s)
                          or ((s.get("toast") or "").strip()
                              and s.get("state") == "ready"), 60) or {}
    # The toast is written with the disposition; give the drain a moment to
    # settle the state after it, then read once more.
    time.sleep(1.0)
    reviewed = wait_state(session, lambda s: dead_session(s)
                          or s.get("state") == "ready", 30) or reviewed
    toast = evaluate(session, READ_TOAST) or ""
    record["review"] = {"revisionBefore": before.get("revision"),
                        "revisionAfter": reviewed.get("revision"),
                        "state": reviewed.get("state"),
                        "checkpoint": reviewed.get("checkpoint"),
                        "toast": toast}
    record["revisionUnchangedByReview"] = (
        reviewed.get("revision") == before.get("revision"))
    if dead_session(reviewed) or reviewed.get("state") != "ready":
        return void(f"the bullet left the session {reviewed.get('state')!r}")
    if REVIEW_PROMISE not in toast or ROLLBACK_PRESCRIPTION in toast:
        return void("the bullet did not take the review path "
                    f"(toast {toast!r}); nothing here is 099's cell")

    # 7. THE PRESS UNDER TEST.
    record["testedPress"] = press_key(session, "ArrowLeft")
    if not record["testedPress"]["moved"] or dead_session(record["testedPress"]):
        return void("the tested press did not move the caret or killed the session")

    # 8. Kill it, recover through the product, save through the product.
    record["inducer"] = induce_worker_failure(session)
    if not record["inducer"].get("fired"):
        return void(f"the worker failure never fired: {record['inducer'].get('why')}")
    died = wait_state(session, dead_session, 90) or {}
    record["stateAfterInducer"] = died.get("state")
    if not dead_session(died):
        return void(f"the worker failure left the session {died.get('state')!r}")
    record["checkpointOnOffer"] = died.get("checkpoint")
    notice = evaluate(session, READ_NOTICE) or {}
    record["notice"] = notice
    if notice.get("rescue") != "checkpoint":
        return void(f"the notice offered rescue {notice.get('rescue')!r}")
    record["pressedTheNotice"] = evaluate(session, CLICK_NOTICE)
    recovered = wait_state(session, lambda s: s.get("state") == "ready", 240) or {}
    record["stateAfterRecovery"] = recovered.get("state")
    if recovered.get("state") != "ready":
        return void("the notice's button did not return a ready session")
    evaluate(session, CLEAR_TOAST)
    saved = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
    record["savedBytes"] = saved.get("bytes")
    got = classify(saved)
    record["cameBack"] = {k: v for k, v in got.items() if k != "paragraphs"}
    record["savedParagraphs"] = got.get("paragraphs")
    if not got.get("readable"):
        return void("the save was not a readable ODT")
    if not got.get("sentinelCameBack") or not got.get("breakCameBack"):
        return void("the POSITIVE CONTROL failed: what came back is not the r2 "
                    "checkpoint (typing and break both present), so which "
                    "checkpoint was restored is unknown")
    record["outcome"] = ("KEPT_THE_BULLET" if got["bulletCameBack"]
                         else "LOST_THE_BULLET")
    record["completedAt"] = datetime.now(timezone.utc).isoformat()
    return record


def run_arm(arm: str, source: str, attempts: int, report: dict,
            profile: str | None = None) -> None:
    served = served_session(source, arm)
    scratch = Path(tempfile.mkdtemp(prefix=f"f099-{arm}-"))
    mirror = scratch / "root"
    overrides = {SESSION_JS: served.encode("utf-8")}
    if profile:
        # The same transformation `--profile` / `--candidate-profile` and
        # `tools/build_cutover_page.py` use, so "the page measured" is the page
        # a cutover to this profile would serve, not a hand-edited one.
        page_text, _, _ = repointed_page(
            (PROJECT / "dist" / "e2-editor-app.js").read_text(encoding="utf-8"),
            profile, PROJECT / "dist" / "profiles" / profile / "sdk-manifest.json")
        overrides["e2-editor-app.js"] = page_text.encode("utf-8")
    build_mirror(PROJECT / "dist", mirror, overrides)
    on_disk = (mirror / SESSION_JS).read_bytes()
    landed = (PROJECT / SESSION_JS).read_bytes()
    if arm == "landed" and on_disk != landed:
        raise SystemExit("the landed arm would not serve the source tree's "
                         "session file; run `make e2-c-assets`")
    page = (mirror / "e2-editor-app.js").read_bytes()
    entry = {"arm": arm,
             "fixed": {"098": ARMS[arm][PAIR_098], "099": ARMS[arm][PAIR_099]},
             "servedSessionSha256": hashlib.sha256(on_disk).hexdigest(),
             "landedSessionSha256": hashlib.sha256(landed).hexdigest(),
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
            # A FRESH BROWSER PER ATTEMPT.  `induce_worker_failure` leaves
            # `Target.setAutoAttach` on; in the first run of this probe
            # (within-worker-v8-2026-09-28.json) every second and third attempt
            # in one Chrome session -- a navigation later -- came back
            # "auto-attach delivered no session for a document worker", 6 of 6.
            # The mechanism was not isolated; a new browser sidesteps it.
            session = ChromeSession("cold")
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
                  f"review-rev {(got.get('review') or {}).get('revisionBefore')}"
                  f"->{(got.get('review') or {}).get('revisionAfter')} "
                  f"tested={((got.get('testedPress') or {}).get('seconds'))}s "
                  f"why={got.get('why')!r}",
                  file=sys.stderr, flush=True)
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
    parser.add_argument("--profile", help="repoint the page at this profile "
                        "(diagnostic; the default is the page as dist/ pins it)")
    args = parser.parse_args()
    arms = args.arm or list(ARMS)
    source = (PROJECT / "dist" / SESSION_JS).read_text(encoding="utf-8")
    # The three arms must be three different files, or the run compares a file
    # with itself.
    variants = {arm: served_session(source, arm) for arm in ARMS}
    if len(set(variants.values())) != len(ARMS):
        print("two arms would serve identical bytes", file=sys.stderr)
        return 2
    report = {
        "schemaVersion": 1, "finding": "099", "mode": "within-Worker",
        "evidenceClass": "red-case",
        "profile": (f"{args.profile} (page repointed with repointed_page; "
                    "diagnostic)" if args.profile
                    else "e2-editor-v8 (the page as dist/ pins it)"),
        "fixture": FIXTURE_URL, "sentinel": SENTINEL,
        "prediction": PREDICTION,
        "startedAt": datetime.now(timezone.utc).isoformat(), "arms": []}
    for arm in arms:
        run_arm(arm, source, args.attempts, report, args.profile)
        if args.out:
            Path(args.out).write_text(json.dumps(report, ensure_ascii=False,
                                                 indent=1) + "\n", encoding="utf-8")
    report["completedAt"] = datetime.now(timezone.utc).isoformat()
    by_arm = {e["arm"]: e["attempts"] for e in report["arms"]}
    verdict: dict = {}
    for arm, attempts in by_arm.items():
        outcomes = [a.get("outcome") for a in attempts]
        verdict[arm] = {
            "outcomes": outcomes,
            "asPredictedEvery": bool(outcomes) and all(
                o == PREDICTION[arm] for o in outcomes),
            "revisionUnchangedByReview": [a.get("revisionUnchangedByReview")
                                          for a in attempts],
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
