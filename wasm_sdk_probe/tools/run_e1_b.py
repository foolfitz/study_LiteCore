#!/usr/bin/env python3
"""Run the E1-B narrow editor shell in Chrome or Firefox."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

from e1_support import sha256, write_json
from r7_support import evaluate, wait_page
from run_browser_probe import ChromeSession, FirefoxSession, free_port


def next_evidence_directory(base: Path) -> Path:
    if not (base / "result.json").exists():
        return base
    attempt = 2
    while (base / f"attempt-{attempt:02d}").exists():
        attempt += 1
    return base / f"attempt-{attempt:02d}"


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--fixture", default="plain-grapheme")
    parser.add_argument("--timeout", type=float, default=420)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "editor-contract" / "browser",
    )
    args = parser.parse_args()

    server_port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(server_port)],
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
    evidence = next_evidence_directory(args.evidence_root / args.browser)
    evidence.mkdir(parents=True, exist_ok=True)
    try:
        base_url = f"http://127.0.0.1:{server_port}/e1-editor.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        query = urlencode({"fixture": args.fixture, "autorun": "1"})
        session.navigate(f"{base_url}?{query}")
        deadline = time.monotonic() + args.timeout
        metrics = None
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__e1_b || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.25)
        if not metrics or not metrics.get("complete"):
            metrics = {
                "schemaVersion": 1,
                "release": "E1-B-narrow-editor",
                "fixture": args.fixture,
                "complete": False,
                "pass": False,
                "error": {
                    "code": "RUNNER_TIMEOUT",
                    "message": f"page timed out after {args.timeout}s",
                },
            }
        (evidence / "page.png").write_bytes(session.screenshot())
        log_text = str(evaluate(session, "document.querySelector('#log')?.textContent || ''"))
        (evidence / "page.log.txt").write_text(log_text, encoding="utf-8")
        encoded = str(evaluate(session, "globalThis.__e1_b_get_output_base64?.() || ''"))
        if encoded:
            output = base64.b64decode(encoded)
            output_path = evidence / "output.odt"
            output_path.write_bytes(output)
            metrics["output"] = {
                **(metrics.get("output") or {}),
                "path": str(output_path),
                "bytes": len(output),
                "sha256": sha256(output_path),
            }
        result = {
            **metrics,
            "browserName": args.browser,
            "browserVersion": session.version,
            "evidenceDirectory": str(evidence),
        }
        write_json(evidence / "result.json", result)
        print(json.dumps({
            "browser": args.browser,
            "result": str(evidence / "result.json"),
            "pass": result.get("pass") is True,
        }, ensure_ascii=False))
        if result.get("pass") is not True:
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
