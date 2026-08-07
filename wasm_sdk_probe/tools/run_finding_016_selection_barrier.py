#!/usr/bin/env python3
"""Run the isolated Finding 016 verified-selection barrier experiment."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from e1_support import inspect_odt, sha256, write_json
from r7_support import evaluate, wait_page
from run_browser_probe import ChromeSession, FirefoxSession, free_port
from validate_finding_016_selection_barrier import decide, evaluate_result


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
    profile = project / "dist" / "profiles" / "finding-016-selection-barrier"
    manifest = json.loads((profile / "sdk-manifest.json").read_text(encoding="utf-8"))
    return {
        "schemaVersion": 1,
        "finding": "016",
        "experiment": "selection-barrier",
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


def inspect_output(path: Path, anchors: list[str]) -> dict[str, Any]:
    inspected = inspect_odt(path)
    return {
        "name": path.name,
        "path": str(path),
        "bytes": path.stat().st_size if path.is_file() else 0,
        "sha256": sha256(path) if path.is_file() else None,
        "zip": inspected["zip"],
        "crc": inspected["crc"],
        "xml": inspected["xml"],
        "anchors": [
            {"text": anchor, "found": anchor in inspected["text"]}
            for anchor in anchors
        ],
        "anchorsPreserved": all(anchor in inspected["text"] for anchor in anchors),
        "paragraphs": inspected["paragraphs"],
        "tables": inspected["tables"],
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    core = workspace / "libreoffice-26-8"
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--boundary-smoke", action="store_true")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=(
            workspace
            / "findings"
            / "evidence"
            / "016"
            / "selection-barrier-wasm"
        ),
    )
    args = parser.parse_args()
    if args.smoke and args.boundary_smoke:
        parser.error("--smoke and --boundary-smoke are mutually exclusive")
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
    if args.boundary_smoke:
        evidence_base = evidence_root / "smoke" / "boundary" / args.browser
    elif args.smoke:
        evidence_base = evidence_root / "smoke" / args.browser
    else:
        evidence_base = evidence_root / "browser" / args.browser
    evidence = next_evidence_directory(evidence_base)
    evidence.mkdir(parents=True, exist_ok=True)
    metrics: dict[str, Any] = {}
    browser_version = "unavailable"
    browser_process = None
    try:
        query = (
            "?boundarySmoke=1" if args.boundary_smoke
            else ("?smoke=1" if args.smoke else "")
        )
        url = (
            f"http://127.0.0.1:{server_port}/"
            f"finding-016-selection-barrier.html{query}"
        )
        wait_page(url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        browser_process = session.process
        browser_version = session.version
        session.navigate(url)
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            metrics = evaluate(
                session, "globalThis.__finding_016_selection_barrier || null"
            ) or {}
            if metrics.get("complete"):
                break
            time.sleep(0.25)
        if not metrics.get("complete"):
            metrics = {
                **metrics,
                "schemaVersion": 1,
                "release": "E1-Finding-016-selection-barrier",
                "complete": False,
                "pass": False,
                "decision": "STOP_OR_RESCOPE",
                "error": {
                    "code": "RUNNER_TIMEOUT",
                    "message": f"page timed out after {args.timeout}s",
                },
            }
        (evidence / "page.png").write_bytes(session.screenshot())
        log_text = str(
            evaluate(session, "document.querySelector('#log')?.textContent || ''")
        )
        (evidence / "page.log.txt").write_text(log_text, encoding="utf-8")
        encoded_outputs = evaluate(
            session,
            "globalThis.__finding_016_selection_barrier_get_outputs?.() || {}",
        ) or {}
        declared = {
            item.get("name"): item for item in metrics.get("outputs") or []
        }
        inspected_outputs = []
        for name, encoded in encoded_outputs.items():
            output_path = evidence / name
            output_path.write_bytes(base64.b64decode(encoded))
            inspected_outputs.append(
                inspect_output(output_path, declared.get(name, {}).get("anchors") or [])
            )
        metrics["outputs"] = inspected_outputs
    finally:
        if session is not None:
            session.close()
        if browser_process is not None:
            stdout = browser_process.stdout.read() if browser_process.stdout else ""
            stderr = browser_process.stderr.read() if browser_process.stderr else ""
            (evidence / "browser.stdout.txt").write_text(stdout, encoding="utf-8")
            (evidence / "browser.stderr.txt").write_text(stderr, encoding="utf-8")
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
        "browserVersion": browser_version,
        "evidenceDirectory": str(evidence),
    }
    write_json(evidence / "result.json", result)
    write_json(evidence_base / "latest.json", result)

    if args.smoke or args.boundary_smoke:
        output_pass = len(result.get("outputs") or []) == 1 and all(
            item.get("zip") is True
            and item.get("crc") is True
            and item.get("xml") is True
            and item.get("anchorsPreserved") is True
            for item in result.get("outputs") or []
        )
        current = {"pass": result.get("pass") is True and output_pass}
        decision = result.get("decision")
    else:
        paths = sorted((evidence_root / "browser").glob("*/latest.json"))
        results = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        summary = decide(results)
        summary["sources"] = [str(path) for path in paths]
        write_json(evidence_root / "summary.json", summary)
        current = evaluate_result(result)
        decision = summary["decision"]
    print(json.dumps({
        "result": str(evidence / "result.json"),
        "browser": args.browser,
        "mode": (
            "boundary-smoke" if args.boundary_smoke
            else ("smoke" if args.smoke else "full")
        ),
        "pass": current["pass"],
        "decision": decision,
    }, ensure_ascii=False))
    if not current["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
