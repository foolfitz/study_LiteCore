#!/usr/bin/env python3
"""Run the R6-A discovery checkpoint against an existing R5 artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from run_browser_probe import ChromeSession, FirefoxSession, free_port


def evaluate(session, script: str):
    if isinstance(session, ChromeSession):
        return session.evaluate(script)
    return session.execute(f"return {script};")


def wait_page(url: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as error:
            last_error = error
        time.sleep(0.2)
    raise RuntimeError(f"timed out waiting for {url}: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--fixture", choices=(
        "t1-plain-zh.odt", "t2-styled.odt", "t3-long.odt",
    ))
    args = parser.parse_args()

    project = Path(__file__).resolve().parent.parent
    root = project.parent
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(port)],
        cwd=project,
        # DEVNULL, not PIPE: nothing ever read these pipes, and the request
        # log fills 64 KiB after a workload-dependent number of navigations --
        # the handler thread then blocks before sending the response body and
        # every later fetch hangs (finding 023).
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    session = None
    try:
        wait_page(f"http://127.0.0.1:{port}/r6-discovery.html", timeout=30)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        suffix = f"?fixture={args.fixture}" if args.fixture else ""
        session.navigate(f"http://127.0.0.1:{port}/r6-discovery.html{suffix}")
        deadline = time.monotonic() + args.timeout
        metrics = None
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__r6_discovery_metrics || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.5)
        if not metrics or not metrics.get("complete"):
            raise RuntimeError("discovery timed out")
        screenshot = session.screenshot()
        fixture_suffix = f"-{Path(args.fixture).stem}" if args.fixture else ""
        prefix = f"{args.browser}{fixture_suffix}"
        (args.evidence_dir / f"{prefix}.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (args.evidence_dir / f"{prefix}.png").write_bytes(screenshot)
        (args.evidence_dir / f"{prefix}.log.txt").write_text(
            str(evaluate(session, "document.querySelector('#log').textContent")),
            encoding="utf-8",
        )
        print(json.dumps({
            "browser": args.browser,
            "version": session.version,
            "pass": metrics.get("pass"),
            "error": metrics.get("error"),
        }, ensure_ascii=False))
        if not metrics.get("pass"):
            raise SystemExit(1)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
