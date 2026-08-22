#!/usr/bin/env python3
"""Drive web/e2-c-block-identity.html and keep what it measured.

The two engine changes that rode the 2026-08-17 link -- a click that ANSWERS,
and a barrier that stops verifying the wrong paragraph -- against the four
predictions registered before the link, in
research/DESIGN-2026-08-16-caret-by-block-and-offset.md.

This runner does not judge.  tools/analyze_block_identity_link.py does, offline,
so the run and the criteria stay separable -- and so that a criterion cannot be
edited into agreement with what came back.

Usage:
  run_block_identity_link.py --browser firefox [--profile e2-editor-v4] --out FILE
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

READ = "(() => globalThis.__e2c_bi || null)()"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="firefox")
    parser.add_argument("--profile", default="e2-editor-v4")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(PROJECT / "dist")],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        url = (f"http://127.0.0.1:{port}/e2-c-block-identity.html"
               f"?profile={args.profile}")
        wait_page(f"http://127.0.0.1:{port}/e2-c-block-identity.html")
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(url)
        deadline = time.monotonic() + args.timeout
        metrics = None
        while time.monotonic() < deadline:
            metrics = evaluate(session, READ)
            if metrics and metrics.get("complete"):
                break
            time.sleep(1.0)
        if not metrics:
            raise SystemExit("the page never published its metrics")
        metrics["browser"] = args.browser
        text = json.dumps(metrics, indent=2, ensure_ascii=False)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0 if metrics.get("complete") and not metrics.get("error") else 1
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    sys.exit(main())
