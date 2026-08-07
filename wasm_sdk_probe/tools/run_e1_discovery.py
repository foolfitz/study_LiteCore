#!/usr/bin/env python3
"""Run E1-A discovery in Chrome or Firefox and retain per-fixture evidence."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from e1_support import sha256, write_json
from r7_support import evaluate, wait_page
from run_browser_probe import ChromeSession, FirefoxSession, free_port


def next_evidence_directory(base: Path) -> Path:
    """Keep every browser attempt instead of overwriting failed evidence."""
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
    parser.add_argument(
        "--mode",
        choices=("full", "finding-016-remediation"),
        default="full",
    )
    parser.add_argument("--fixture", action="append")
    parser.add_argument("--timeout", type=float, default=420)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "discovery" / "browser",
    )
    args = parser.parse_args()
    corpus = json.loads((project / "test-docs" / "e1" / "manifest.json").read_text(encoding="utf-8"))
    known = [item["id"] for item in corpus["fixtures"]]
    fixtures = args.fixture or known
    unknown = sorted(set(fixtures) - set(known))
    if unknown:
        raise SystemExit(f"unknown E1 fixtures: {unknown}")

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
    fixture_results: list[dict[str, Any]] = []
    try:
        base_url = f"http://127.0.0.1:{server_port}/e1-discovery.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        for fixture in fixtures:
            query = urlencode({"fixture": fixture, "mode": args.mode})
            session.navigate(f"{base_url}?{query}")
            deadline = time.monotonic() + args.timeout
            metrics = None
            while time.monotonic() < deadline:
                metrics = evaluate(session, "globalThis.__e1_discovery || null")
                if metrics and metrics.get("complete"):
                    break
                time.sleep(0.25)
            if not metrics or not metrics.get("complete"):
                metrics = {
                    "schemaVersion": 1,
                    "release": "E1-A-editing-discovery",
                    "fixture": fixture,
                    "mode": args.mode,
                    "complete": False,
                    "pass": False,
                    "error": {"code": "RUNNER_TIMEOUT", "message": f"page timed out after {args.timeout}s"},
                }
            evidence = next_evidence_directory(
                args.evidence_root / args.browser / fixture
            )
            evidence.mkdir(parents=True, exist_ok=True)
            screenshot = session.screenshot()
            (evidence / "page.png").write_bytes(screenshot)
            log_text = str(evaluate(session, "document.querySelector('#log')?.textContent || ''"))
            (evidence / "page.log.txt").write_text(log_text, encoding="utf-8")
            encoded = str(evaluate(session, "globalThis.__e1_discovery_get_output_base64?.() || ''"))
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
                "browser": args.browser,
                "browserVersion": session.version,
                "evidenceDirectory": str(evidence),
            }
            write_json(evidence / "result.json", result)
            fixture_results.append({
                "fixture": fixture,
                "path": str(evidence / "result.json"),
                "pass": result.get("pass") is True,
                "error": result.get("error"),
            })
            print(json.dumps(fixture_results[-1], ensure_ascii=False), flush=True)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
    summary = {
        "schemaVersion": 1,
        "release": "E1-A-editing-discovery",
        "browser": args.browser,
        "mode": args.mode,
        "fixtures": fixture_results,
        "pass": len(fixture_results) == len(fixtures)
        and all(item["pass"] for item in fixture_results),
    }
    write_json(args.evidence_root / args.browser / "summary.json", summary)
    print(json.dumps({"summary": str(args.evidence_root / args.browser / "summary.json"), "pass": summary["pass"]}))
    if not summary["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
