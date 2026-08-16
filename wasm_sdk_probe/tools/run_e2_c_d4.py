#!/usr/bin/env python3
"""Drive SPEC E2-C phase D4 in one browser and sample its process tree.

Separate from `run_e2_c_d0.py` for one reason: D4 needs samples taken WHILE the
page runs, and every other E2-C phase only needs what the page ends up holding.
The sampling contract is R7-D's -- the page bumps `sampleState.token`, the
runner snapshots the browser's whole process tree and labels the sample with
whatever the page published beside the token.

No verdict here.  `tools/analyze_e2_c_d4.py` applies the thresholds
`e2/validation-matrix-v1.json` froze, offline, so they can be recomputed from
the files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1_support import sha256, write_json  # noqa: E402
from r7_support import evaluate, process_snapshot, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent


def artifact_hashes(profile: str) -> dict[str, str]:
    directory = PROJECT / "dist" / "profiles" / profile
    return {
        "profile": profile,
        "wasmSha256": sha256(directory / "probe.wasm"),
        "loaderSha256": sha256(directory / "probe.js"),
        "workerSha256": sha256(directory / "sdk-worker.js"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--profile", default="e2-editor-v2")
    parser.add_argument("--cycles", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=2400)
    parser.add_argument("--poll", type=float, default=0.25)
    parser.add_argument("--page", default="e2-c-d4.html")
    parser.add_argument("--namespace", default="__e2c_d4")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--output", type=Path,
                        default=PROJECT.parent / "findings" / "evidence" / "sdk-e2"
                        / "e2-c-validation" / "d4")
    args = parser.parse_args()

    artifact = artifact_hashes(args.profile)
    evidence = (args.output / f"{args.profile}-{artifact['wasmSha256'][:8]}"
                / args.browser)
    # A round is a record.  Same guard as the D0 runner, and for the same
    # reason: an --output pointing at a finished round once destroyed the round
    # a finding had been written from.
    if (evidence / "result.json").is_file() and not args.overwrite:
        raise SystemExit(
            f"{evidence} already holds a completed run.\n"
            f"Point --output somewhere new, or pass --overwrite to discard it.")

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    metrics = None
    samples: list[dict] = []
    log_text = ""
    try:
        base = f"http://127.0.0.1:{port}/{args.page}"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(f"{base}?profile={args.profile}&cycles={args.cycles}")
        deadline = time.monotonic() + args.timeout
        last_token = None
        while time.monotonic() < deadline:
            metrics = evaluate(session, f"globalThis.{args.namespace} || null")
            state = (metrics or {}).get("sampleState") or {}
            token = state.get("token")
            if token is not None and token != last_token:
                # One snapshot per checkpoint the page marks -- quiescence and
                # three seconds later -- so the analyzer can take the smaller of
                # each pair without the runner deciding anything.
                samples.append(process_snapshot(session.process.pid, state))
                last_token = token
            if metrics and metrics.get("complete"):
                break
            time.sleep(args.poll)
        if not metrics or not metrics.get("complete"):
            metrics = {"schemaVersion": 1, "release": "spec-e2c-d4",
                       "complete": False,
                       "error": {"code": "RUNNER_TIMEOUT",
                                 "message": "page never completed"}}
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

    reported = {key: (metrics.get("inventory") or {}).get(key)
                for key in ("wasmSha256", "loaderSha256", "workerSha256")}
    metrics["artifact"] = artifact
    metrics["attribution"] = {
        "runnerProfile": args.profile,
        "pageReported": reported,
        "consistent": all(reported.get(key) == artifact[key] for key in reported),
    }
    metrics["browserName"] = args.browser
    metrics["samples"] = samples

    evidence.mkdir(parents=True, exist_ok=True)
    write_json(evidence / "result.json", metrics)
    (evidence / "page.log").write_text(log_text, encoding="utf-8")
    print(json.dumps({
        "evidence": str(evidence),
        "complete": metrics.get("complete"),
        "cycles": len(metrics.get("cycles") or []),
        "samples": len(samples),
        "attributionConsistent": metrics["attribution"]["consistent"],
        "error": metrics.get("error"),
    }, indent=2, ensure_ascii=False))
    return 0 if metrics.get("complete") and not metrics.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
