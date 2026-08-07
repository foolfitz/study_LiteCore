#!/usr/bin/env python3
"""Drive finding 012 close classification and full boundary confirmation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from r7_support import (
    ChromeSession,
    FirefoxSession,
    evaluate,
    load_json,
    process_snapshot,
    sha256,
    wait_page,
    write_json,
)
from run_browser_probe import free_port


def outcome(metrics: dict[str, Any]) -> str:
    close = metrics.get("close") or {}
    if close.get("status") == "passed":
        return "close-pass"
    if close.get("error", {}).get("code") == "TIMEOUT":
        return "timeout"
    return "error"


def run_case(
    session_class: type[ChromeSession] | type[FirefoxSession],
    base_url: str,
    browser: str,
    root: Path,
    fixture: dict[str, Any],
    run_number: int,
    timeout_ms: int,
    expected: str | None,
    artifact_hashes: dict[str, str],
    release: str,
) -> dict[str, Any]:
    case_root = root / browser / fixture["id"] / f"run-{run_number}"
    case_root.mkdir(parents=True, exist_ok=True)
    session = session_class("cold")
    metrics = None
    samples = []
    last_sample = 0.0
    try:
        session.navigate(
            f"{base_url}?fixture={fixture['id']}&timeoutMs={timeout_ms}"
        )
        deadline = time.monotonic() + timeout_ms / 1000 + 240
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__finding_012 || null")
            now = time.monotonic()
            if now - last_sample >= 1:
                state = {
                    "checkpoint": metrics.get("stage") if metrics else None,
                    "cycle": run_number,
                    "activeWorkers": metrics.get("workers", {}).get("active") if metrics else None,
                    "activeHandles": metrics.get("handles", {}).get("active") if metrics else None,
                    "workersAfterClose": (
                        metrics.get("workers", {}).get("active") if metrics and metrics.get("complete") else None
                    ),
                    "tileCacheBytes": 0,
                    "documentVersion": fixture["sha256"],
                    "revision": metrics.get("open", {}).get("revision") if metrics else None,
                }
                samples.append(process_snapshot(session.process.pid, state))
                last_sample = now
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.2)
        if not metrics or not metrics.get("complete"):
            raise RuntimeError(f"fixture {fixture['id']} did not complete")
        observed = outcome(metrics)
        observation_pass = observed in {"close-pass", "timeout"}
        expected_pass = expected is None or observed == expected
        (case_root / "page.png").write_bytes(session.screenshot())
        (case_root / "browser.log.txt").write_text(
            str(evaluate(session, "document.querySelector('#log').textContent")), encoding="utf-8"
        )
        result = {
            "schemaVersion": 1,
            "release": release,
            "browser": browser,
            "browserVersion": session.version,
            "sessionType": "headless-automatic",
            "fixture": fixture,
            "run": run_number,
            "timeoutMs": timeout_ms,
            "expectedOutcome": expected,
            "outcome": observed,
            "metrics": metrics,
            "processSamples": samples,
            "artifactHashes": artifact_hashes,
            "observationPass": observation_pass,
            "expectedPass": expected_pass,
            "pass": observation_pass and expected_pass,
        }
    except Exception as error:  # noqa: BLE001 - preserve runner failure as evidence
        result = {
            "schemaVersion": 1,
            "release": release,
            "browser": browser,
            "fixture": fixture,
            "run": run_number,
            "timeoutMs": timeout_ms,
            "expectedOutcome": expected,
            "error": {"name": type(error).__name__, "message": str(error)},
            "lastMetrics": metrics,
            "processSamples": samples,
            "pass": False,
        }
    finally:
        session.close()
    write_json(case_root / "result.json", result)
    return {
        "id": fixture["id"], "run": run_number,
        "outcome": result.get("outcome", "runner-error"),
        "result": str(case_root / "result.json"), "pass": result["pass"],
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--classify", action="store_true")
    modes.add_argument("--confirm-boundaries", action="store_true")
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "012" / "r7-minimization",
    )
    parser.add_argument("--timeout-ms", type=int)
    args = parser.parse_args()
    manifest = load_json(project / "test-docs" / "r7-finding-012" / "manifest.json")
    release = manifest.get("release", "finding-012-r7-minimization")
    fixtures = {item["id"]: item for item in manifest["variants"]}
    mode = "classify" if args.classify else "confirm"
    timeout_ms = args.timeout_ms or (10000 if args.classify else 180000)
    if not 1000 <= timeout_ms <= 180000:
        raise SystemExit("timeout must be between 1000 and 180000 ms")
    plans: list[tuple[dict[str, Any], int, str | None]] = []
    if args.classify:
        plans = [(item, 1, None) for item in manifest["variants"]]
    else:
        selection = load_json(args.evidence_root / "selection.json")
        for item in selection["selected"]:
            fixture = fixtures[item["id"]]
            plans.extend((fixture, run, item["expectedOutcome"])
                         for run in range(1, item["runs"] + 1))

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(port)],
        # DEVNULL, not PIPE: nothing ever read these pipes, and the request
        # log fills 64 KiB after a workload-dependent number of navigations --
        # the handler thread then blocks before sending the response body and
        # every later fetch hangs (finding 023).
        cwd=project, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        text=True,
    )
    results = []
    try:
        base_url = f"http://127.0.0.1:{port}/r7-close-minimizer.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        artifact_hashes = {
            "loader": sha256(project / "dist" / "profiles" / "writer-review" / "probe.35d96f5fdcb9ed0c.js"),
            "wasm": sha256(project / "dist" / "profiles" / "writer-review" / "probe.ba257beb038b6a2d.wasm"),
            "manifest": sha256(project / "dist" / "profiles" / "writer-review-r6" / "sdk-manifest.json"),
            "corpusManifest": sha256(project / "dist" / "r7-finding-012" / "manifest.json"),
        }
        root = args.evidence_root / mode
        for fixture, run_number, expected in plans:
            item = run_case(
                session_class, base_url, args.browser, root,
                fixture, run_number, timeout_ms, expected, artifact_hashes, release,
            )
            results.append(item)
            print(json.dumps(item, ensure_ascii=False), flush=True)
        summary = {
            "schemaVersion": 1,
            "release": release,
            "mode": mode,
            "browser": args.browser,
            "timeoutMs": timeout_ms,
            "runs": results,
            "outcomes": {
                identifier: [item["outcome"] for item in results if item["id"] == identifier]
                for identifier in sorted({item["id"] for item in results})
            },
            "pass": len(results) == len(plans) and all(item["pass"] for item in results),
        }
        write_json(root / args.browser / "summary.json", summary)
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
