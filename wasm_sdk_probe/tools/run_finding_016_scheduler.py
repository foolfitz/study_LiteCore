#!/usr/bin/env python3
"""Run the isolated Finding 016 scheduler-drain experiment."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from e1_support import sha256, write_json
from r7_support import evaluate, wait_page
from run_browser_probe import ChromeSession, FirefoxSession, free_port


def command_output(arguments: list[str], cwd: Path) -> str:
    return subprocess.run(
        arguments,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ).stdout


def next_evidence_directory(base: Path) -> Path:
    if not (base / "result.json").exists():
        return base
    attempt = 2
    while (base / f"attempt-{attempt:02d}").exists():
        attempt += 1
    return base / f"attempt-{attempt:02d}"


def artifact_record(project: Path, core: Path) -> dict[str, Any]:
    profile = project / "dist" / "profiles" / "finding-016-scheduler"
    manifest = json.loads((profile / "sdk-manifest.json").read_text(encoding="utf-8"))
    return {
        "schemaVersion": 1,
        "finding": "016",
        "experiment": "scheduler-drain",
        "coreHead": command_output(["git", "rev-parse", "HEAD"], core).strip(),
        "profile": manifest["profile"],
        "sdkVersion": manifest["sdkVersion"],
        "diagnostic": manifest["diagnostic"],
        "files": {
            name: {
                "bytes": (profile / name).stat().st_size,
                "sha256": sha256(profile / name),
            }
            for name in ("probe.js", "probe.wasm", "sdk-worker.js", "sdk-manifest.json")
        },
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    core = workspace / "libreoffice-26-8"
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--timeout", type=float, default=240)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "016" / "scheduler-wasm",
    )
    args = parser.parse_args()
    evidence_root = args.evidence_root.resolve()
    baseline = evidence_root / "baseline"
    baseline.mkdir(parents=True, exist_ok=True)
    before_path = baseline / "core-status-before.txt"
    if not before_path.exists():
        before_path.write_text(
            command_output(["git", "status", "--short"], core), encoding="utf-8"
        )
    write_json(evidence_root / "artifact.json", artifact_record(project, core))

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
    evidence = next_evidence_directory(evidence_root / "browser" / args.browser)
    evidence.mkdir(parents=True, exist_ok=True)
    metrics: dict[str, Any] = {}
    try:
        url = f"http://127.0.0.1:{server_port}/finding-016-scheduler.html"
        wait_page(url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(url)
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__finding_016_scheduler || null") or {}
            if metrics.get("complete"):
                break
            time.sleep(0.25)
        if not metrics.get("complete"):
            metrics = {
                **metrics,
                "schemaVersion": 1,
                "release": "E1-Finding-016-scheduler-drain",
                "complete": False,
                "pass": False,
                "decision": "RUNNER_TIMEOUT",
                "error": {
                    "code": "RUNNER_TIMEOUT",
                    "message": f"page timed out after {args.timeout}s",
                },
            }
        (evidence / "page.png").write_bytes(session.screenshot())
        log_text = str(evaluate(session, "document.querySelector('#log')?.textContent || ''"))
        (evidence / "page.log.txt").write_text(log_text, encoding="utf-8")
        encoded = str(evaluate(
            session,
            "globalThis.__finding_016_scheduler_get_output_base64?.() || ''",
        ))
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
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
        (baseline / "core-status-after.txt").write_text(
            command_output(["git", "status", "--short"], core), encoding="utf-8"
        )

    result = {
        **metrics,
        "browser": args.browser,
        "browserVersion": session.version if session is not None else "unavailable",
        "evidenceDirectory": str(evidence),
    }
    write_json(evidence / "result.json", result)
    write_json(evidence_root / "browser" / args.browser / "latest.json", result)

    result_paths = sorted((evidence_root / "browser").glob("*/latest.json"))
    results = [json.loads(path.read_text(encoding="utf-8")) for path in result_paths]
    summary = {
        "schemaVersion": 1,
        "finding": "016",
        "experiment": "scheduler-drain",
        "runs": [
            {
                "browser": item.get("browser"),
                "browserVersion": item.get("browserVersion"),
                "decision": item.get("decision"),
                "pass": item.get("pass") is True,
                "path": str(path),
            }
            for path, item in zip(result_paths, results)
        ],
        "pass": len(results) == 2 and all(item.get("pass") is True for item in results),
    }
    write_json(evidence_root / "summary.json", summary)
    print(json.dumps({
        "result": str(evidence / "result.json"),
        "decision": result.get("decision"),
        "pass": result.get("pass") is True,
    }, ensure_ascii=False))
    if result.get("pass") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
