#!/usr/bin/env python3
"""Task #47, P1: does the shipped bounded-readback completion actually fire?

Option C rests on the claim that the mechanism finding 039 needs already ships,
and that only the discovery entry point declines to arm it.  That claim is so
far pure source reading (editor_api.cpp:123 vs editor_discovery_api.cpp:58,
with probe_engine.hpp:69-72 saying the omission is on purpose).  This runs the
measurement on the FROZEN e1-editor-v1 -- nothing is rebuilt, and the artifact
hash is recorded next to the result so the binding is checkable.

The prediction and all four dispositions were written down first:
findings/evidence/sdk-e2/discovery/039-combination/PREDICTION.md

This runner judges nothing.  The page classifies itself into A/B/C/D by the
completion NAME, and D ("nothing measured") is a real outcome, not a failure to
report -- so a run that reaches D must not be re-read as anything else.
"""

from __future__ import annotations

import argparse
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
    parser.add_argument(
        "--profile", default="e1-editor-v1",
        help="the frozen shipped artifact; overriding this changes what P1 means")
    parser.add_argument("--fixture", default="plain-grapheme.odt")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e2" / "discovery"
        / "039-combination" / "p1-product-readback")
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
    try:
        base = f"http://127.0.0.1:{port}/f039-product-readback.html"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(
            f"{base}?autorun=1&profile={args.profile}&fixture={args.fixture}")
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__f039_product || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.25)
        if not metrics or not metrics.get("complete"):
            metrics = {
                "schemaVersion": 1,
                "release": "task-047-P1-product-readback",
                "complete": False,
                "outcome": {"code": "D", "label": "nothing measured",
                            "detail": f"runner timeout after {args.timeout}s"},
                "error": {"code": "RUNNER_TIMEOUT", "message": "page never completed"},
            }
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

    metrics["artifact"] = artifact
    evidence = args.output / args.browser
    evidence.mkdir(parents=True, exist_ok=True)
    write_json(evidence / "result.json", metrics)
    (evidence / "page.log").write_text(log_text, encoding="utf-8")

    outcome = metrics.get("outcome") or {}
    print(json.dumps({
        "output": str(evidence / "result.json"),
        "wasmSha256": artifact["wasmSha256"][:16] + "…",
        "outcome": outcome,
        "arms": [
            {"arm": arm.get("arm"),
             "steps": [{"step": s.get("step"), "status": s.get("status"),
                        "completion": s.get("completion"),
                        "elapsedMs": s.get("elapsedMs")}
                       for s in arm.get("steps") or []],
             "fatal": arm.get("fatal")}
            for arm in metrics.get("arms") or []
        ],
    }, indent=2, ensure_ascii=False))
    # D and C are outcomes, not crashes: exit non-zero so a caller cannot treat
    # "the page ran" as "the premise held".
    return 0 if outcome.get("code") in ("A", "B") else 1


if __name__ == "__main__":
    raise SystemExit(main())
