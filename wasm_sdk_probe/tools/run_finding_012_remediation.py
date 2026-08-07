#!/usr/bin/env python3
"""Verify the bounded Document Worker recovery for finding 012."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from r7_support import ChromeSession, FirefoxSession, load_json, sha256, wait_page, write_json
from run_browser_probe import free_port
from run_finding_012 import run_case


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout-ms", type=int, default=3000)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "012" / "r7-remediation",
    )
    args = parser.parse_args()
    if not 1 <= args.runs <= 10:
        raise SystemExit("runs must be between 1 and 10")
    if not 1000 <= args.timeout_ms <= 30000:
        raise SystemExit("timeout must be between 1000 and 30000 ms")

    manifest = load_json(project / "test-docs" / "r7-finding-012" / "manifest.json")
    fixture = next(item for item in manifest["variants"] if item["id"] == "t2-original")
    artifact_hashes = {
        "loader": sha256(project / "dist" / "profiles" / "writer-review" / "probe.35d96f5fdcb9ed0c.js"),
        "wasm": sha256(project / "dist" / "profiles" / "writer-review" / "probe.ba257beb038b6a2d.wasm"),
        "documentSdk": sha256(project / "dist" / "document-sdk.js"),
        "worker": sha256(project / "dist" / "profiles" / "writer-review-r6" / "sdk-worker.js"),
        "manifest": sha256(project / "dist" / "profiles" / "writer-review-r6" / "sdk-manifest.json"),
        "corpusManifest": sha256(project / "dist" / "r7-finding-012" / "manifest.json"),
    }
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
    results = []
    try:
        base_url = f"http://127.0.0.1:{port}/r7-close-minimizer.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        for run_number in range(1, args.runs + 1):
            result = run_case(
                session_class,
                base_url,
                args.browser,
                args.evidence_root,
                fixture,
                run_number,
                args.timeout_ms,
                "close-pass",
                artifact_hashes,
                "finding-012-r7-remediation",
            )
            results.append(result)
            print(json.dumps({
                "browser": args.browser,
                "run": run_number,
                "outcome": result["outcome"],
                "pass": result["pass"],
            }, ensure_ascii=False), flush=True)
        summary = {
            "schemaVersion": 1,
            "release": "finding-012-r7-remediation",
            "browser": args.browser,
            "fixture": fixture["id"],
            "timeoutMs": args.timeout_ms,
            "artifactHashes": artifact_hashes,
            "runs": results,
            "pass": len(results) == args.runs and all(item["pass"] for item in results),
        }
        write_json(args.evidence_root / args.browser / "summary.json", summary)
        if not summary["pass"]:
            raise SystemExit(1)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
