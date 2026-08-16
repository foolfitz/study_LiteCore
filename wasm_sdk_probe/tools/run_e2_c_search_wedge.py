#!/usr/bin/env python3
"""Run the search-wedge arms and write one result.json per arm and browser.

Criteria: findings/evidence/sdk-e2/e2-c-validation/search-wedge/PREDICTION.md
(written before the page existed).

Each arm gets its own page load and its own engine, so one wedged arm cannot
affect the next -- which matters here more than usual, because a wedge is
exactly what is being looked for.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1_support import write_json  # noqa: E402
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
ARMS = ("two-searches-one-open", "search-close-open-search",
        "full-cycle-then-search", "no-search-then-search")


def run_arm(browser: str, arm: str, profile: str, timeout: float) -> dict:
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-c-search-wedge.html"
        wait_page(base)
        session = (ChromeSession if browser == "chrome" else FirefoxSession)("cold")
        session.navigate(f"{base}?profile={profile}&arm={arm}")
        deadline = time.monotonic() + timeout
        metrics = None
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__search_wedge || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.5)
        else:
            # Not an exception: a page that never completes IS a result here,
            # and throwing it away would hide the strongest possible outcome.
            metrics = (metrics or {}) | {"complete": False,
                                         "runnerTimedOut": True}
        metrics["browserName"] = browser
        return metrics
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
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--profile", default="e2-editor-v2")
    parser.add_argument("--arm", choices=ARMS + ("all",), default="all")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--output", type=Path,
                        default=PROJECT.parent / "findings" / "evidence" / "sdk-e2"
                        / "e2-c-validation" / "search-wedge")
    args = parser.parse_args()

    arms = ARMS if args.arm == "all" else (args.arm,)
    summary = []
    for arm in arms:
        metrics = run_arm(args.browser, arm, args.profile, args.timeout)
        directory = args.output / args.browser / arm
        directory.mkdir(parents=True, exist_ok=True)
        write_json(directory / "result.json", metrics)
        verdict = metrics.get("verdict") or {}
        summary.append({
            "arm": arm, "browser": args.browser,
            "complete": metrics.get("complete"),
            "searches": verdict.get("searches"),
            "lastSearchOutcome": verdict.get("lastSearchOutcome"),
            "lastSearchTookMs": verdict.get("lastSearchTookMs"),
            "lastSearchWedged": verdict.get("lastSearchWedged"),
            "error": metrics.get("error"),
        })
        print(json.dumps(summary[-1], indent=2, ensure_ascii=False), flush=True)
    write_json(args.output / args.browser / "summary.json",
               {"schemaVersion": 1, "release": "e2-c-search-wedge",
                "browser": args.browser, "arms": summary})
    return 0


if __name__ == "__main__":
    sys.exit(main())
