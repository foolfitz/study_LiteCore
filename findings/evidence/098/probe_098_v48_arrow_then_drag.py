#!/usr/bin/env python3
"""Finding 098 on the SHIPPED shell (generation v48): does an arrow key make the
next drag bank a checkpoint of an untouched document?

WHY.  098's "scope" section says v48 carries `mutation: true` for moves but has
no half C, so the arrow key alone banks nothing there, and then INFERS -- "not
measured on v48" -- that a clean document, an arrow key, then a drag, banks a
checkpoint of clean bytes through the base class's `_checkpointBeforeSelection`
(`if (!dirty || contentStamp === this._checkpointStamp) return;`).  v48 is what
users are served until a cutover, so the inference is worth one measurement
(AGENTS.md section 7: what can be looked at is not inferred).

THE SHELL UNDER TEST IS REBUILT FROM GIT, NOT GUESSED.  Every file in
`e2/editor-shell-v2-bundle-v48.json`'s `included` list is taken from commit
`2d319677` (the commit that froze v48) and laid over a mirror of `dist/`; the
probe then recomputes the bundle digest over the SERVED files the way the
product-path runner does and refuses to run unless it equals v48's declared
`bundleSha256`.  `web/e2-editor.html` sits outside the hash net (finding 094),
so it is taken from the same commit and its hash recorded.  The v8 profile
(engine, worker) is untouched and shared by every arm.

The same three scenarios run on the CURRENT `dist/` (shell v52) as the
comparison, where 098's fix predicts the arrow key changes nothing.

SCENARIOS (all through the product: its file input, a canvas click on a middle
line, a real CDP ArrowRight, the canvas drag, the insert control):
  * `drag-only`       open, click, drag.  CONTROL: a drag on an untouched
                      document banks nothing on either shell.
  * `arrow-then-drag` open, click, ArrowRight once, drag.  THE MEASUREMENT.
  * `typed-then-drag` open, click, type, drag.  POSITIVE CONTROL: the drag
                      banks at all -- without it, 無 could mean "the drag never
                      reached `_checkpointBeforeSelection`".

CRITERIA, written before the first run (per attempt, `#s-checkpoint` after the
drag settles):
  * v48: drag-only 無; arrow-then-drag 有（r0）; typed-then-drag 有（r1）.
  * v52: drag-only 無; arrow-then-drag 無;       typed-then-drag 有（r1）.
  * VOID if the page did not boot or open, the click did not place the caret,
    the arrow did not move the caret, the typing did not advance the revision,
    or the revision label is not what the scenario implies before the drag.
  * If v48 arrow-then-drag reads 無, the inference in 098 was WRONG and the
    section is corrected, not the criterion.

WHAT THIS CANNOT SEE.  `dirty` itself (the page does not render it).  What is
read is the consequence a user can see: the checkpoint label, and the latency
of the drag (a checkpoint save shows in it).

Usage:
  probe_098_v48_arrow_then_drag.py [--attempts 3] [--shell v48|v52 ...] [--out FILE]
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
REPO = PROJECT.parent
sys.path.insert(0, str(PROJECT / "tools"))

from r7_support import evaluate, wait_page                          # noqa: E402
from run_browser_probe import ChromeSession, free_port              # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate                # noqa: E402
from run_e2_c_product_path import (                                 # noqa: E402
    DRAG, INSTALL, LINE_INK, OPEN_FILE, POINT_AT, PRESS, SET_TEXT,
    build_mirror, caret_click_fractions, dead_session, served_in_dist,
    stable_bands,
)
from validate_e1_c import shell_bundle_digest                       # noqa: E402

V48_MANIFEST = PROJECT / "e2" / "editor-shell-v2-bundle-v48.json"
V48_COMMIT = "2d319677"
V52_MANIFEST = PROJECT / "e2" / "editor-shell-v2-bundle-v52.json"
PAGE_HTML = "web/e2-editor.html"

FIXTURE_URL = "./e1-fixtures/multi-paragraph.odt"
SENTINEL = "F098V48MARK"
SCENARIOS = ("drag-only", "arrow-then-drag", "typed-then-drag")
PREDICTION = {
    "v48": {"drag-only": "無", "arrow-then-drag": "有（r0）",
            "typed-then-drag": "有（r1）"},
    "v52": {"drag-only": "無", "arrow-then-drag": "無",
            "typed-then-drag": "有（r1）"},
}

SINK_AT = """(() => {
const sink = document.querySelector('#sink');
return sink ? { top: sink.offsetTop, left: sink.offsetLeft } : null;
})()"""


def git_bytes(commit: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:wasm_sdk_probe/{relative}"],
        cwd=REPO, check=True, capture_output=True).stdout


def served_identity(root: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes: dict[str, str | None] = {}
    for entry in manifest["included"]:
        served = root / served_in_dist(entry["path"])
        hashes[entry["path"]] = (hashlib.sha256(served.read_bytes()).hexdigest()
                                 if served.is_file() else None)
    digest = shell_bundle_digest(hashes)
    return {"manifest": manifest_path.relative_to(REPO).as_posix(),
            "declaredSha256": manifest["bundleSha256"],
            "servedSha256": digest,
            "servesDeclared": digest == manifest["bundleSha256"]}


def build_shell(shell: str) -> tuple[Path, dict]:
    scratch = Path(tempfile.mkdtemp(prefix=f"f098-{shell}-"))
    mirror = scratch / "root"
    overrides: dict[str, bytes] = {}
    if shell == "v48":
        manifest = json.loads(V48_MANIFEST.read_text(encoding="utf-8"))
        for entry in manifest["included"]:
            overrides[served_in_dist(entry["path"])] = git_bytes(
                V48_COMMIT, entry["path"])
        overrides[served_in_dist(PAGE_HTML)] = git_bytes(V48_COMMIT, PAGE_HTML)
    build_mirror(PROJECT / "dist", mirror, overrides)
    identity = served_identity(mirror, V48_MANIFEST if shell == "v48"
                               else V52_MANIFEST)
    page = (mirror / "e2-editor-app.js").read_text(encoding="utf-8")
    identity.update(
        shell=shell, servedFrom=str(mirror),
        servedHtmlSha256=hashlib.sha256(
            (mirror / served_in_dist(PAGE_HTML)).read_bytes()).hexdigest(),
        servedPin=page.split('PINNED_WASM_SHA256 = "', 1)[1].split('"', 1)[0])
    if not identity["servesDeclared"]:
        raise SystemExit(f"{shell}: the mirror does not serve the declared "
                         f"bundle ({identity['servedSha256']} != "
                         f"{identity['declaredSha256']}); refusing to measure "
                         "a shell nobody declared")
    return mirror, identity


def wait_state(session, predicate, timeout: float, poll: float = 0.3):
    deadline = time.monotonic() + timeout
    state = None
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if state and predicate(state):
            return state
        time.sleep(poll)
    return state


def attempt(session, base: str, shell: str, scenario: str, index: int) -> dict:
    record: dict = {"shell": shell, "scenario": scenario, "attempt": index,
                    "startedAt": datetime.now(timezone.utc).isoformat()}

    def void(why: str) -> dict:
        record.update(outcome="VOID", why=why)
        return record

    navigate(session, base)
    evaluate(session, INSTALL)
    booted = wait_state(session, lambda s: s.get("state") in ("ready", "stopped",
                                                             "expired"), 180)
    if (booted or {}).get("state") != "ready":
        return void(f"the page booted to {(booted or {}).get('state')!r}")
    name = f"f098-{shell}-{scenario}-{index}.odt"
    evaluate(session, OPEN_FILE.replace("ARG_URL", FIXTURE_URL)
             .replace("ARG_NAME", name))
    opened = wait_state(session, lambda s: (s.get("doc") or "") == name
                        and s.get("state") == "ready", 180)
    if (opened or {}).get("state") != "ready":
        return void("the fixture did not open")
    record["checkpointAtOpen"] = opened.get("checkpoint")

    scan, bands = stable_bands(session)
    if len(bands) < 3:
        return void(f"{len(bands)} text bands; no middle line")
    y = f"{bands[len(bands) // 2]['centreFraction']:.5f}"
    fractions = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", y)) or {})
    evaluate(session, POINT_AT.replace("ARG_X", fractions["near"])
             .replace("ARG_Y", y))
    placed = wait_state(session, lambda s: "定位游標" in (s.get("latency") or ""), 90)
    record["placed"] = (placed or {}).get("latency")
    if "定位游標" not in (record["placed"] or "") or "失敗" in (record["placed"] or ""):
        return void(f"the caret could not be placed: {record['placed']!r}")

    expected_revision = "0"
    if scenario == "arrow-then-drag":
        before = evaluate(session, SINK_AT) or {}
        for kind in ("rawKeyDown", "keyUp"):
            session.call("Input.dispatchKeyEvent",
                         {"type": kind, "key": "ArrowRight", "code": "ArrowRight",
                          "windowsVirtualKeyCode": 39, "nativeVirtualKeyCode": 39})
        moved = False
        watch = time.monotonic() + 4.0
        while time.monotonic() < watch:
            time.sleep(0.15)
            if (evaluate(session, SINK_AT) or before) != before:
                moved = True
                break
        record["arrowMoved"] = moved
        if not moved:
            return void("the arrow key did not move the caret")
    elif scenario == "typed-then-drag":
        evaluate(session, SET_TEXT.replace("ARG_TEXT", SENTINEL))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
        typed = wait_state(session, lambda s: (s.get("revision") or "") != "0"
                           and s.get("state") == "ready", 120) or {}
        expected_revision = "1"
        record["revisionAfterTyping"] = typed.get("revision")

    ready = wait_state(session, lambda s: dead_session(s)
                       or s.get("state") == "ready", 30) or {}
    record["beforeDrag"] = {"revision": ready.get("revision"),
                            "checkpoint": ready.get("checkpoint")}
    if ready.get("revision") != expected_revision \
            or ready.get("checkpoint") != "無":
        return void(f"before the drag: revision {ready.get('revision')!r} "
                    f"(expected {expected_revision}), checkpoint "
                    f"{ready.get('checkpoint')!r} (expected 無)")

    x1 = fractions["near"]
    x2 = f"{min(float(fractions['near']) + 0.25, 0.9):.5f}"
    started = time.monotonic()
    evaluate(session, DRAG.replace("ARG_X1", x1).replace("ARG_Y1", y)
             .replace("ARG_X2", x2).replace("ARG_Y2", y))
    # A checkpoint save lands in well under a second on this fixture; wait for
    # the label to change or three seconds, then for the queue to settle.
    wait_state(session, lambda s: (s.get("checkpoint") or "") != "無", 3.0)
    settled = wait_state(session, lambda s: dead_session(s)
                         or (s.get("state") == "ready"
                             and (s.get("pending") or "0") == "0"), 30) or {}
    record["afterDrag"] = {"revision": settled.get("revision"),
                           "checkpoint": settled.get("checkpoint"),
                           "state": settled.get("state"),
                           "latency": settled.get("latency"),
                           "seconds": round(time.monotonic() - started, 2)}
    record["outcome"] = settled.get("checkpoint")
    record["asPredicted"] = settled.get("checkpoint") == PREDICTION[shell][scenario]
    record["completedAt"] = datetime.now(timezone.utc).isoformat()
    return record


def run_shell(shell: str, attempts: int, report: dict) -> None:
    mirror, identity = build_shell(shell)
    entry = {"identity": identity, "attempts": []}
    report["shells"].append(entry)
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
        # Interleaved, so a drift in the browser over the run cannot line up
        # with one scenario.
        for index in range(1, attempts + 1):
            for scenario in SCENARIOS:
                try:
                    got = attempt(session, base, shell, scenario, index)
                except Exception as error:      # noqa: BLE001 -- recorded
                    got = {"shell": shell, "scenario": scenario,
                           "attempt": index, "outcome": "VOID",
                           "why": f"the probe raised: {error!r}"}
                entry["attempts"].append(got)
                print(f"[{shell}] {scenario} #{index}: {got.get('outcome')} "
                      f"predicted={PREDICTION[shell][scenario]} "
                      f"drag={(got.get('afterDrag') or {}).get('seconds')}s "
                      f"why={got.get('why')!r}", file=sys.stderr, flush=True)
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
    parser.add_argument("--shell", action="append", choices=("v48", "v52"),
                        default=None)
    parser.add_argument("--out")
    args = parser.parse_args()
    report = {"schemaVersion": 1, "finding": "098",
              "question": "v48: does an arrow key make the next drag bank a "
                          "checkpoint of an untouched document?",
              "fixture": FIXTURE_URL, "prediction": PREDICTION,
              "startedAt": datetime.now(timezone.utc).isoformat(), "shells": []}
    for shell in args.shell or ["v48", "v52"]:
        run_shell(shell, args.attempts, report)
        if args.out:
            Path(args.out).write_text(json.dumps(report, ensure_ascii=False,
                                                 indent=1) + "\n", encoding="utf-8")
    report["completedAt"] = datetime.now(timezone.utc).isoformat()
    verdict: dict = {}
    for entry in report["shells"]:
        shell = entry["identity"]["shell"]
        for scenario in SCENARIOS:
            got = [a for a in entry["attempts"] if a["scenario"] == scenario]
            verdict[f"{shell}/{scenario}"] = {
                "outcomes": [a.get("outcome") for a in got],
                "asPredictedEvery": bool(got) and all(a.get("asPredicted")
                                                      for a in got)}
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
