#!/usr/bin/env python3
"""SPEC E2-B 5.10: run the negative matrix and keep every saved ODT.

This runner does NOT judge.  It drives the page, writes the metrics and every
saved document to disk, and exits non-zero if the page did not complete.  The
verdict is produced separately by analyze_e2b_gate.py, reading only the files
this leaves behind, so it can be recomputed without a browser.

The prediction and all dispositions were committed before the page existed:
findings/evidence/sdk-e2/discovery/e2b-negative/PREDICTION.md
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1_support import sha256, write_json  # noqa: E402
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent


def main() -> int:
    workspace = PROJECT.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    # The baseline v2 profile.  It MUST match what the page drives: the runner
    # records the artifact hashes from this path, and a mismatch would file the
    # evidence under an artifact that never ran it (finding 027).
    parser.add_argument("--profile", default="e2-editor-v2")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=1800)
    # Fixture validation, not measurement: selects the spans, records the
    # rectangles, dispatches nothing and saves nothing.  Point --output
    # somewhere of its own; it must not land next to a verdict run.
    parser.add_argument("--geometry-only", action="store_true")
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e2" / "discovery"
        / "e2b-negative")
    args = parser.parse_args()

    profile_dir = PROJECT / "dist" / "profiles" / args.profile
    artifact = {
        "profile": args.profile,
        "loaderSha256": sha256(profile_dir / "probe.js"),
        "wasmSha256": sha256(profile_dir / "probe.wasm"),
        "workerSha256": sha256(profile_dir / "sdk-worker.js"),
    }

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    metrics: dict[str, Any] | None = None
    saves: list[dict[str, Any]] = []
    log_text = ""
    try:
        base = f"http://127.0.0.1:{port}/e2b-negative.html"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        query = f"?autorun=1&profile={args.profile}&rounds={args.rounds}"
        if args.geometry_only:
            query += "&geometryOnly=1"
        session.navigate(base + query)
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__e2b_negative || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.5)
        if not metrics or not metrics.get("complete"):
            metrics = {
                "schemaVersion": 1,
                "release": "spec-e2b-negative-matrix",
                "complete": False,
                "error": {"code": "RUNNER_TIMEOUT", "message": "page never completed"},
            }
        else:
            # Pulled one at a time: the whole set is a few hundred kB of base64
            # and a single evaluate carrying all of it is the kind of thing that
            # silently truncates.
            count = evaluate(session, "globalThis.__e2b_negative_save_count()") or 0
            for index in range(int(count)):
                saves.append(evaluate(
                    session, f"globalThis.__e2b_negative_save({index})"))
        log_text = str(evaluate(
            session, "document.querySelector('#log')?.textContent || ''"))
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    # Attribution, checked rather than assumed.  The runner hashes the files at
    # --profile and the page names the profile each row drove; if those two ever
    # disagree the evidence would be filed under an artifact that never ran it,
    # which is finding 027's failure mode.  Cheap to check, so it is checked.
    drove = {row.get("profile", "") for row in (metrics.get("rows") or [])}
    # A row may drive a different profile ON PURPOSE -- N5 aims at the v1
    # profile, because "a v1 build rejects a v2 action id" cannot be shown on a
    # v2 build.  Those rows say so, and only undeclared ones are flagged: a
    # check that cries wolf on a legitimate row is a check people learn to
    # ignore, and then a real misattribution walks through.
    declared = {row.get("profile", "") for row in (metrics.get("rows") or [])
                if row.get("crossProfile")}
    unexpected = sorted(p for p in drove
                        if p and not p.startswith(args.profile)
                        and p not in declared)
    metrics["artifact"] = artifact
    metrics["attribution"] = {
        "runnerProfile": args.profile,
        "profilesDriven": sorted(drove),
        "declaredCrossProfile": sorted(declared),
        "unexpectedProfiles": unexpected,
        "consistent": not unexpected,
    }
    evidence = args.output / f"{args.profile}-{artifact['wasmSha256'][:8]}" / args.browser
    (evidence / "saved").mkdir(parents=True, exist_ok=True)
    written = []
    for entry in saves:
        if not entry or not entry.get("b64"):
            continue
        name = f"{entry['row']}-round{entry['round']}-{entry['phase']}.odt"
        (evidence / "saved" / name).write_bytes(base64.b64decode(entry["b64"]))
        written.append({"row": entry["row"], "round": entry["round"],
                        "phase": entry["phase"], "file": f"saved/{name}"})
    metrics["savedDocuments"] = written
    write_json(evidence / "result.json", metrics)
    (evidence / "page.log").write_text(log_text, encoding="utf-8")

    print(json.dumps({
        "output": str(evidence / "result.json"),
        "wasmSha256": artifact["wasmSha256"][:16] + "…",
        "productAbiAvailable": metrics.get("productAbiAvailable"),
        "rows": len(metrics.get("rows") or []),
        "savedDocuments": len(written),
        "arms": [
            {"arm": arm.get("arm"),
             "skipped": arm.get("skipped"),
             "fatal": arm.get("fatal"),
             "rounds": [
                 {"round": r.get("round"),
                  "void": r.get("void"),
                  "selectStatus": r.get("selectStatus"),
                  "collapsedBefore": r.get("collapsedBeforeDispatch"),
                  "rectanglesBefore": r.get("rectanglesBeforeDispatch"),
                  "selectedText": (r.get("selectionBeforeDispatch") or {}).get("text"),
                  "actionStatus": r.get("actionStatus"),
                  "actionError": (r.get("actionError") or {}).get("code"),
                  "collapsedAfter": r.get("collapsedAfterDispatch")}
                 for r in arm.get("rounds") or []]}
            for arm in metrics.get("arms") or []
        ],
    }, indent=2, ensure_ascii=False))
    # "It ran" must never be mistaken for "it passed": this exits non-zero
    # unless the page completed AND produced saved documents to judge.
    return 0 if metrics.get("complete") and written else 1


if __name__ == "__main__":
    raise SystemExit(main())
