#!/usr/bin/env python3
"""SPEC-M4-ods-in-nextcloud §7, step 1: the viewer page on `e2-editor-v14` with a
1 MiB pthread stack -- no link, no ddev.  DIAGNOSTIC, never gate evidence.

What it does: mirrors `dist/` with symlinks (`build_mirror`), writes the viewer
page into the MIRROR only, with two rewrites made in the mirror's copies and
nowhere else:
  * the page's one worker literal points at `e2-editor-v14` instead of the
    not-yet-linked `ods-viewer-v1` (`retarget_page`, anchor exactly once);
  * v14's `probe.js` gets the default pthread stack 1,048,576 instead of 65,536
    and an echo of every pthread's stack size (`patch_pthread_stack`, finding
    089's arm, both anchors exactly once).
Then it serves the mirror, opens the page with `?diagnostics=1`, and hands four
files to the page's own file input, one after the other:
  three-sheets-distinct.ods, numeric-100k.ods, tdf149752.ods (089), password.ods.

What it cannot measure: the reader object set on this core (only the link can),
and anything of W7 -- the name is still spoofed and `documentType` unknown.

Machine preconditions: the KDE wallet, other Chrome processes and the load are
RECORDED, not refused: this run measures no time (the owner, 2026-10-20: the
desk gate is for timing cells only).  The wallet was refused until the launcher
got --password-store=basic (SPEC-M3-production-ui 17.27).

  run_ods_viewer_step1.py --selftest        the judge against synthetic red cases
  run_ods_viewer_step1.py [--out DIR]
Report: findings/evidence/m4-ods/step1-mirror-v14-1mib/report-<UTC>.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))
from run_ods_viewer_draft_smoke import PAGE_FILES, preconditions, retarget_page  # noqa: E402

PROFILE = "e2-editor-v14"
STACK_BYTES = 1_048_576
CORPUS = PROJECT / "test-docs" / "ods"
FIXTURES = [
    CORPUS / "ladder" / "three-sheets-distinct.ods",
    CORPUS / "ladder" / "numeric-100k.ods",
    CORPUS / "upstream" / "tdf149752.ods",
    CORPUS / "upstream" / "password.ods",
]
DEFAULT_OUT = PROJECT.parent / "findings" / "evidence" / "m4-ods" / "step1-mirror-v14-1mib"
STACK_ECHO = "[engine-stack] "
# W5 (findings/evidence/m4-ods/RESULT-W5-the-memory-ladder.md): numeric-100k's
# sbrk at the last open stage on v12, 64 KB stacks.  The spec's prediction adds
# the stack difference of the 7-thread pool: 7 x (1 MiB - 64 KiB).
W5_NUMERIC_100K_SBRK = 314_814_464
STACK_POOL_DELTA = 7 * (STACK_BYTES - 65_536)
KILL_LINE = 939_524_096

RUN_EXPR = """(() => {
  const r = window.__odsViewer && window.__odsViewer.runs[INDEX];
  if (!r) return null;
  return JSON.stringify({ settled: r.settled, file: r.file, inputBytes: r.inputBytes ?? null,
    inputSha256: r.inputSha256 ?? null, opened: r.opened, refused: r.refused, error: r.error,
    tileDraws: r.tileDraws, engineEvents: r.engineEvents, firstTile: r.firstTile,
    finalState: r.finalState ?? null, engineCreated: r.engineCreated,
    viewReadyAtMs: r.viewReadyAtMs, stages: r.stages, messages: r.messages,
    messagesDropped: r.messagesDropped, fit: r.fit ?? null, refits: r.refits ?? 0 });
})()"""


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


# ---------------------------------------------------------------- the judge --
def expectation(identifier: str, ok: bool, detail) -> dict:
    return {"id": identifier, "ok": bool(ok), "detail": detail}


def stack_sizes(run: dict) -> dict:
    sizes = {}
    for row in run.get("messages") or []:
        message = str(row.get("message", ""))
        if message.startswith(STACK_ECHO):
            sizes[message[len(STACK_ECHO):]] = row.get("count", 1)
    return sizes


def sbrk_summary(run: dict) -> dict:
    stages = [s for s in run.get("stages") or [] if isinstance(s.get("sbrk"), int)]
    opens = [s for s in stages if str(s.get("name", "")).startswith("open.")]
    begin = next((s["sbrk"] for s in opens if s.get("name") == "open.begin"), None)
    last_open = opens[-1]["sbrk"] if opens else None
    return {
        "stageCount": len(stages),
        "openBegin": begin,
        "lastOpenStage": opens[-1].get("name") if opens else None,
        "lastOpenSbrk": last_open,
        "documentCost": (last_open - begin) if begin is not None and last_open is not None else None,
        "maxOverStages": max((s["sbrk"] for s in stages), default=None),
        "destroyStagesSeen": [s.get("name") for s in stages
                              if str(s.get("name", "")).startswith("document-destroy")],
    }


def judge(report: dict) -> list[dict]:
    """The spec's predictions (§7), as a pure function of the report so it can be
    shown red without a browser.  RECORDED: a miss is registered, the spec's
    criteria do not move."""
    runs = {r.get("file"): r for r in report.get("runs") or []}
    wanted = [f.name for f in FIXTURES]
    missing = [name for name in wanted if name not in runs]
    out = [expectation("every-fixture-was-run", not missing,
                       {"missing": missing, "seen": list(runs)})]
    if missing:
        return out

    def opened(name, parts):
        run = runs[name]
        got = (run.get("opened") or {}).get("parts")
        return expectation(f"{name}-opens-with-{parts}-parts",
                           bool(run.get("opened")) and not run.get("error")
                           and not run.get("refused") and got == parts and not run.get("timedOut"),
                           {"parts": got, "error": run.get("error"), "refused": run.get("refused"),
                            "timedOut": run.get("timedOut"), "viewReadyAtMs": run.get("viewReadyAtMs")})

    out.append(opened("three-sheets-distinct.ods", 3))
    out.append(opened("numeric-100k.ods", 1))
    out.append(opened("tdf149752.ods", 2))

    password = runs["password.ods"]
    refusal = password.get("refused") or {}
    out.append(expectation(
        "password.ods-refused-encrypted-before-any-engine",
        refusal.get("code") == "ENCRYPTED_DOCUMENT" and password.get("engineCreated") is False
        and not password.get("stages") and not password.get("engineEvents")
        and ((password.get("finalState") or {}).get("packageProbe") or {}).get("encrypted") is True,
        {"refused": refusal.get("code"), "engineCreated": password.get("engineCreated"),
         "stages": len(password.get("stages") or []),
         "engineEvents": password.get("engineEvents")}))

    engines = [r for r in runs.values() if r.get("engineCreated")]
    out.append(expectation(
        "every-engine-run-echoed-the-1-mib-stack",
        bool(engines) and all(str(STACK_BYTES) in stack_sizes(r) for r in engines),
        {r.get("file"): stack_sizes(r) for r in engines}))

    numeric = sbrk_summary(runs["numeric-100k.ods"])
    low, high = W5_NUMERIC_100K_SBRK, W5_NUMERIC_100K_SBRK + STACK_POOL_DELTA
    out.append(expectation(
        "numeric-100k-last-open-sbrk-within-w5-plus-stack-delta",
        numeric["lastOpenSbrk"] is not None and low <= numeric["lastOpenSbrk"] <= high,
        {**numeric, "predictedRange": [low, high]}))

    out.append(expectation(
        "every-engine-run-stays-under-the-kill-line",
        bool(engines) and all((sbrk_summary(r)["maxOverStages"] or KILL_LINE) < KILL_LINE
                              for r in engines),
        {r.get("file"): sbrk_summary(r)["maxOverStages"] for r in engines}))
    return out


def selftest() -> int:
    def run(file, parts=None, *, refused=None, engine=True, stack=True, stages=None):
        record = {"file": file, "settled": True, "timedOut": False, "error": None,
                  "refused": refused, "opened": {"parts": parts} if parts else None,
                  "engineCreated": engine, "engineEvents": ["view-ready"] if engine else [],
                  "stages": stages if stages is not None else (
                      [{"name": "open.begin", "sbrk": 296_000_000},
                       {"name": "open.query-metadata", "sbrk": 296_100_000}] if engine else []),
                  "messages": [{"message": f"{STACK_ECHO}{STACK_BYTES}", "count": 8}] if stack and engine else [],
                  "finalState": {"packageProbe": {"encrypted": not engine}}}
        return record

    base = {"runs": [
        run("three-sheets-distinct.ods", 3),
        run("numeric-100k.ods", 1, stages=[{"name": "open.begin", "sbrk": 296_000_000},
                                           {"name": "open.query-metadata", "sbrk": 320_000_000}]),
        run("tdf149752.ods", 2),
        run("password.ods", refused={"code": "ENCRYPTED_DOCUMENT"}, engine=False),
    ]}

    def find(report, name):
        return next(r for r in report["runs"] if r["file"] == name)

    cases = [
        ("no runs at all", ["every-fixture-was-run"], lambda b: b.update(runs=[])),
        ("tdf149752 was not run", ["every-fixture-was-run"],
         lambda b: b["runs"].pop(2)),
        ("three sheets read as 2 parts", ["three-sheets-distinct.ods-opens-with-3-parts"],
         lambda b: find(b, "three-sheets-distinct.ods").update(opened={"parts": 2})),
        ("tdf149752 timed out (089 not cured)", ["tdf149752.ods-opens-with-2-parts"],
         lambda b: find(b, "tdf149752.ods").update(timedOut=True)),
        ("numeric-100k open errored", ["numeric-100k.ods-opens-with-1-parts"],
         lambda b: find(b, "numeric-100k.ods").update(error={"code": "LOK_ERROR"})),
        ("password reached an engine", ["password.ods-refused-encrypted-before-any-engine"],
         lambda b: find(b, "password.ods").update(engineCreated=True)),
        ("password refused with the generic code", ["password.ods-refused-encrypted-before-any-engine"],
         lambda b: find(b, "password.ods").update(refused={"code": "LOK_ERROR"})),
        ("the stack patch did not take on one run", ["every-engine-run-echoed-the-1-mib-stack"],
         lambda b: find(b, "tdf149752.ods").update(messages=[{"message": f"{STACK_ECHO}65536"}])),
        ("numeric-100k far above W5", ["numeric-100k-last-open-sbrk-within-w5-plus-stack-delta"],
         lambda b: find(b, "numeric-100k.ods")["stages"][1].update(sbrk=400_000_000)),
        ("no stage lines for numeric-100k", ["numeric-100k-last-open-sbrk-within-w5-plus-stack-delta"],
         lambda b: find(b, "numeric-100k.ods").update(stages=[])),
        ("a run over the kill line", ["every-engine-run-stays-under-the-kill-line"],
         lambda b: find(b, "three-sheets-distinct.ods")["stages"].append(
             {"name": "document-destroy-enter", "sbrk": KILL_LINE})),
    ]
    control = judge(base)
    results = [("control (every prediction met)", all(e["ok"] for e in control),
                [e["id"] for e in control if not e["ok"]])]
    for label, flips, edit in cases:
        broken = copy.deepcopy(base)
        edit(broken)
        red = sorted(e["id"] for e in judge(broken) if not e["ok"])
        results.append((label, all(f in red for f in flips), red))
    for label, ok, red in results:
        print(("PASS " if ok else "FAIL ") + label + (f"  red={red}" if red else ""))
    passed = sum(ok for _, ok, _ in results)
    print(f"selftest: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


# ------------------------------------------------------------- the browser --
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--per-file-timeout", type=float, default=300)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()

    gate = preconditions()

    from probe_ods_on_profile import patch_pthread_stack           # noqa: E402
    from r7_support import evaluate, wait_page                      # noqa: E402
    from run_browser_probe import ChromeSession, free_port          # noqa: E402
    from run_e2_c_page_smoke import navigate                        # noqa: E402
    from run_e2_c_product_path import build_mirror                  # noqa: E402

    dist_probe_js = PROJECT / "dist" / "profiles" / PROFILE / "probe.js"
    dist_probe_js_before = sha256_of(dist_probe_js.read_bytes())
    for fixture in FIXTURES:
        if not fixture.is_file():
            raise SystemExit(f"missing fixture {fixture}")

    overrides = {path: source.read_bytes() for path, source in PAGE_FILES.items()}
    page_source_sha256 = sha256_of(overrides["ods-viewer-app.js"])
    overrides["ods-viewer-app.js"] = retarget_page(overrides["ods-viewer-app.js"], PROFILE)
    stack = patch_pthread_stack(PROFILE, STACK_BYTES, overrides)

    scratch = Path(tempfile.mkdtemp(prefix="ods-viewer-step1-"))
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root, overrides)
    # build_mirror materialises an override only where it meets that path in
    # dist/, so the page's own files (not in dist/) are written afterwards.
    for relative, payload in overrides.items():
        target = root / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    for relative, payload in overrides.items():
        target = root / relative
        if target.is_symlink() or target.read_bytes() != payload:
            raise SystemExit(f"mirror does not serve the override for {relative} as a real file")

    record: dict = {
        "schemaVersion": 1,
        "release": "m4-ods-step1-mirror-v14-1mib",
        "spec": "specs/SPEC-M4-ods-in-nextcloud.md §7",
        "evidenceClass": "diagnostic",
        "why": "the viewer page on the a11y+calc core it will be linked on, with the 1 MiB stack, "
               "through its own file input; W7 does not exist, so the name is spoofed and the "
               "reader object set on this core is not measured",
        "startedAt": utc_now(),
        "profile": PROFILE,
        "probeWasmSha256": sha256_of((PROJECT / "dist" / "profiles" / PROFILE / "probe.wasm").read_bytes()),
        "engineStack": stack,
        "preconditions": gate,
        "pageSourceSha256": {"ods-viewer-app.js": page_source_sha256, "retargetedTo": PROFILE},
        "pageFiles": {path: sha256_of(payload) for path, payload in overrides.items()},
        "fixtures": [{"file": f.name, "path": str(f.relative_to(PROJECT)), "sha256": sha256_of(f.read_bytes())}
                     for f in FIXTURES],
        "runs": [],
    }
    session = None
    server = None
    started = time.monotonic()
    try:
        port = free_port()
        server = subprocess.Popen(
            [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port), "--root", str(root)],
            cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_page(f"http://127.0.0.1:{port}/ods-viewer.html")
        session = ChromeSession("cold")
        record["chrome"] = session.version
        navigate(session, f"http://127.0.0.1:{port}/ods-viewer.html?diagnostics=1&openTimeoutMs=180000")
        record["pageWorkerUrl"] = evaluate(session, "window.__odsViewer && window.__odsViewer.workerUrl")
        for index, fixture in enumerate(FIXTURES):
            begun = time.monotonic()
            session.set_file("#file-input", fixture)
            deadline = begun + args.per_file_timeout
            run = None
            while time.monotonic() < deadline:
                text = evaluate(session, RUN_EXPR.replace("INDEX", str(index)))
                run = json.loads(text) if text else None
                if run and run.get("settled"):
                    break
                time.sleep(1.0)
            if not run:
                record["runs"].append({"file": fixture.name, "fatal": "the page never started a run"})
                break
            run["timedOut"] = not run.get("settled")
            run["runnerSeconds"] = round(time.monotonic() - begun, 1)
            record["runs"].append(run)
        # The last document's close is where its destroy stage lines come from;
        # every earlier one was closed by the next file's open.
        evaluate(session, "(() => { window.__odsViewer.close(); return true; })()")
        time.sleep(5)
        for index in range(len(record["runs"])):
            text = evaluate(session, RUN_EXPR.replace("INDEX", str(index)))
            if text:
                late = json.loads(text)
                record["runs"][index]["stages"] = late.get("stages")
                record["runs"][index]["messages"] = late.get("messages")
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                pass
        if server is not None:
            server.terminate()
        shutil.rmtree(scratch, ignore_errors=True)

    record["distProbeJsUnchanged"] = sha256_of(dist_probe_js.read_bytes()) == dist_probe_js_before
    record["sbrk"] = {r.get("file"): sbrk_summary(r) for r in record["runs"]}
    record["stackSizes"] = {r.get("file"): stack_sizes(r) for r in record["runs"]}
    record["predictions"] = judge(record)
    missed = [e["id"] for e in record["predictions"] if not e["ok"]]
    record["verdict"] = ("STEP 1 (diagnostic): every prediction met" if not missed
                         else f"STEP 1 (diagnostic): predictions missed {missed}")
    record["elapsedSeconds"] = round(time.monotonic() - started, 1)
    record["completedAt"] = utc_now()
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f"report-{record['startedAt']}.json"
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)
    print(record["verdict"])
    print(json.dumps({"sbrk": record["sbrk"], "stackSizes": record["stackSizes"],
                      "distProbeJsUnchanged": record["distProbeJsUnchanged"]}, indent=1))
    return 0 if record["distProbeJsUnchanged"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
