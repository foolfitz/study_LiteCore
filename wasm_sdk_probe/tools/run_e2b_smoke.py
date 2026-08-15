#!/usr/bin/env python3
"""Drive the E2-B v2 smoke page and print what came back.

Not a measurement: it produces no verdict and writes no evidence.  It exists so
that the wiring between a freshly linked artifact, the new worker, the new
manifest and the new client fails in one short run rather than in the first
cell of a 90-run matrix.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--profile", default="e2-editor-v2")
    parser.add_argument("--fixture", default="list-contexts.odt")
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    metrics = None
    try:
        base = f"http://127.0.0.1:{port}/e2b-smoke.html"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(f"{base}?profile={args.profile}&fixture={args.fixture}")
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__e2b_smoke || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.5)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    if not metrics:
        print(json.dumps({"complete": False, "error": "page never reported"}))
        return 1
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    dispatched = [s for s in metrics.get("steps", []) if s.get("step") == "dispatched"]
    ok = metrics.get("complete") and not metrics.get("error") \
        and dispatched and all(s.get("ok") for s in dispatched)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
