#!/usr/bin/env python3
"""Drive the R6 reader and collaboration reference application."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from run_browser_probe import (
    ChromeSession,
    FirefoxSession,
    browser_state,
    free_port,
)


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


def wait_reader_ready(session, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state = browser_state(session)
        metrics = state.get("metrics") or {}
        if state.get("status") == "ready" and metrics.get("firstTileMs") is not None:
            return state
        if metrics.get("error"):
            raise RuntimeError(f"reader initialization failed: {metrics['error']}")
        time.sleep(0.25)
    raise RuntimeError(f"reader did not become ready: {state}")


def wait_reader_complete(session, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state = browser_state(session)
        metrics = state.get("metrics") or {}
        if metrics.get("complete"):
            return state
        time.sleep(0.25)
    raise RuntimeError(f"reader flow timed out: {state}")


def run_reader(args, project: Path) -> None:
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
    session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
    summary: dict[str, Any] = {
        "schemaVersion": 1,
        "release": "R6-A",
        "browser": args.browser,
        "samples": [],
        "pass": False,
    }
    try:
        url = f"http://127.0.0.1:{port}/r6-reader.html"
        wait_page(url)
        for sample_index in range(1, args.samples + 1):
            session = session_class("cold")
            try:
                session.navigate(f"{url}?sample={sample_index}")
                wait_reader_ready(session, args.timeout)
                session.click("#run-all")
                state = wait_reader_complete(session, args.timeout)
                metrics = state["metrics"]
                prefix = f"reader-{args.browser}-{sample_index}"
                (args.evidence_dir / f"{prefix}.json").write_text(
                    json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                (args.evidence_dir / f"{prefix}.log.txt").write_text(
                    state.get("log", ""), encoding="utf-8",
                )
                (args.evidence_dir / f"{prefix}.png").write_bytes(session.screenshot())
                summary["browserVersion"] = session.version
                summary["samples"].append({
                    "sample": sample_index,
                    "pass": metrics.get("pass") is True,
                    "firstTileMs": metrics.get("firstTileMs"),
                    "scrollTileY": metrics.get("scrollTileY"),
                    "reloadedVersion": metrics.get("reloadedVersion"),
                    "crashCode": metrics.get("crashCode"),
                    "scheduler": metrics.get("scheduler"),
                    "error": metrics.get("error"),
                })
                print(json.dumps(summary["samples"][-1], ensure_ascii=False))
                if not metrics.get("pass"):
                    raise RuntimeError(f"R6-A browser invariants failed: {metrics.get('error')}")
            finally:
                session.close()
        summary["pass"] = len(summary["samples"]) == args.samples \
            and all(sample["pass"] for sample in summary["samples"])
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
        output = args.evidence_dir / f"reader-{args.browser}-summary.json"
        output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(output)
    if not summary["pass"]:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="phase", required=True)
    reader = subparsers.add_parser("reader")
    reader.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    reader.add_argument("--samples", type=int, default=3)
    reader.add_argument("--timeout", type=float, default=600)
    reader.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    project = Path(__file__).resolve().parent.parent
    if args.phase == "reader":
        run_reader(args, project)


if __name__ == "__main__":
    main()
