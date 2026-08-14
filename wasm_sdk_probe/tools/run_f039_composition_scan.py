#!/usr/bin/env python3
"""Task #47, P2: does finding 039's arm 8 survive in the combination E2-B ships?

Run it twice, and the second run is the one that makes the first mean anything:

    --profile e2-format-discovery   the archived control.  Arm 8 must still
                                    time out here, or this tool cannot detect
                                    the defect it claims to have measured away.
    --profile e2-combination        the artifact under test.

Within a single run the control is intrinsic as well: the combination exports
both select entry points, so arm 8 is issued through each, on the same document
and the same format action.  The discovery one is expected to STILL time out --
the ruling keeps that path unbuffered on purpose -- and a product-path pass only
means something beside that failure.

Judged by the reported selection, never by the fact that a call returned.
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
        / "039-combination" / "p2-composition-scan")
    parser.add_argument("--rounds", type=int, default=3)
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
        base = f"http://127.0.0.1:{port}/f039-composition-scan.html"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(
            f"{base}?autorun=1&profile={args.profile}&fixture={args.fixture}"
            f"&rounds={args.rounds}")
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__f039_composition || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.25)
        if not metrics or not metrics.get("complete"):
            metrics = {
                "schemaVersion": 1,
                "release": "task-047-P2-composition-scan",
                "complete": False,
                "judgement": None,
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
    evidence = args.output / args.profile / args.browser
    evidence.mkdir(parents=True, exist_ok=True)
    write_json(evidence / "result.json", metrics)
    (evidence / "page.log").write_text(log_text, encoding="utf-8")

    judgement = metrics.get("judgement") or {}
    print(json.dumps({
        "output": str(evidence / "result.json"),
        "wasmSha256": artifact["wasmSha256"][:16] + "…",
        "productAbiAvailable": metrics.get("productAbiAvailable"),
        "judgement": judgement,
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
    # This runner does not judge; it exits non-zero unless the page produced a
    # judgement at all, so "it ran" can never be mistaken for "it passed".
    return 0 if metrics.get("complete") and judgement else 1


if __name__ == "__main__":
    raise SystemExit(main())
