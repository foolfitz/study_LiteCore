#!/usr/bin/env python3
"""Collect native LOK and diagnostic WASM close-boundary evidence."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
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


FIXTURE_IDS = ("t2-original", "t2-image-unwrapped")
ENTER = "document-destroy-enter"
RETURN = "document-destroy-return"


def parse_stages(output: str) -> list[str]:
    stages: list[str] = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("stage"), str):
            stages.append(value["stage"])
    return stages


def stop_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return process.communicate(timeout=5)


def run_native_case(
    binary: Path,
    install_path: Path,
    fixture: dict[str, Any],
    run_number: int,
    timeout_ms: int,
    root: Path,
    version: str,
    runtime: dict[str, Any],
    probe: dict[str, Any],
) -> dict[str, Any]:
    case_root = root / fixture["id"] / f"run-{run_number}"
    case_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    timed_out = False
    with tempfile.TemporaryDirectory(prefix="finding-012-native-profile-") as temporary:
        profile_url = (Path(temporary) / "profile").resolve().as_uri()
        command = [
            str(binary), str(install_path), profile_url,
            (Path(fixture["absolutePath"])).resolve().as_uri(),
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_ms / 1000)
        except subprocess.TimeoutExpired:
            timed_out = True
            stdout, stderr = stop_process(process)
    elapsed_ms = (time.monotonic() - started) * 1000
    stages = parse_stages(stdout)
    if timed_out:
        outcome = "timeout"
    elif process.returncode == 0 and RETURN in stages:
        outcome = "close-pass"
    else:
        outcome = "error"
    (case_root / "stdout.log.txt").write_text(stdout, encoding="utf-8")
    (case_root / "stderr.log.txt").write_text(stderr, encoding="utf-8")
    result = {
        "schemaVersion": 1,
        "release": "finding-012-r7-attribution",
        "layer": "native-lok",
        "nativeVersion": version,
        "runtime": runtime,
        "probe": probe,
        "fixture": {key: value for key, value in fixture.items() if key != "absolutePath"},
        "run": run_number,
        "timeoutMs": timeout_ms,
        "elapsedMs": elapsed_ms,
        "returnCode": process.returncode,
        "timedOut": timed_out,
        "stages": stages,
        "outcome": outcome,
        "pass": outcome in {"close-pass", "timeout"} and ENTER in stages,
    }
    write_json(case_root / "result.json", result)
    return result


def native_layer(
    project: Path,
    evidence_root: Path,
    timeout_ms: int,
    confirm_ms: int,
    install_path: Path,
    source_path: Path | None,
) -> None:
    manifest = load_json(project / "test-docs" / "r7-finding-012" / "manifest.json")
    variants = {item["id"]: item for item in manifest["variants"]}
    fixtures = {}
    for identifier in FIXTURE_IDS:
        fixture = dict(variants[identifier])
        path = project / "test-docs" / "r7-finding-012" / fixture["path"]
        fixture["absolutePath"] = str(path)
        fixtures[identifier] = fixture
    binary = project / "build" / "finding-012" / "native-lok-probe"
    install_path = install_path.resolve()
    if not (install_path / "libmergedlo.so").is_file():
        raise SystemExit(f"native install has no libmergedlo.so: {install_path}")
    soffice = install_path / "soffice"
    version_command = [str(soffice), "--version"] if os.access(soffice, os.X_OK) \
        else ["libreoffice", "--version"]
    version_run = subprocess.run(
        version_command, capture_output=True, text=True, check=False,
    )
    version = (version_run.stdout or version_run.stderr).strip()
    header_commit_run = subprocess.run(
        ["git", "-C", str(project.parent / "libreoffice-26-8"), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    probe = {
        "sha256": sha256(binary),
        "headerCoreCommit": header_commit_run.stdout.strip(),
        "runtimeInstallPath": str(install_path),
    }
    runtime_source: dict[str, Any] = {
        "path": None,
        "coreCommit": None,
        "clean": None,
    }
    if source_path is not None:
        source_path = source_path.resolve()
        source_commit_run = subprocess.run(
            ["git", "-C", str(source_path), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
        )
        source_status_run = subprocess.run(
            ["git", "-C", str(source_path), "status", "--short"],
            capture_output=True, text=True, check=False,
        )
        runtime_source = {
            "path": str(source_path),
            "coreCommit": source_commit_run.stdout.strip(),
            "clean": source_status_run.returncode == 0 and not source_status_run.stdout.strip(),
        }
    runtime = {
        "installPath": str(install_path),
        "version": version,
        "source": runtime_source,
    }
    root = evidence_root / "native"
    results = [
        run_native_case(
            binary, install_path, fixtures[identifier], 1, timeout_ms, root,
            version, runtime, probe,
        )
        for identifier in FIXTURE_IDS
    ]
    first = {item["fixture"]["id"]: item for item in results}
    if first["t2-original"]["outcome"] == "timeout" \
            and first["t2-image-unwrapped"]["outcome"] == "close-pass":
        results.append(run_native_case(
            binary, install_path, fixtures["t2-original"], 2, confirm_ms, root,
            version, runtime, probe,
        ))
        for run_number in (2, 3):
            results.append(run_native_case(
                binary, install_path, fixtures["t2-image-unwrapped"], run_number,
                timeout_ms, root, version, runtime, probe,
            ))
    elif all(item["outcome"] == "close-pass" for item in results):
        for identifier in FIXTURE_IDS:
            for run_number in (2, 3):
                results.append(run_native_case(
                    binary, install_path, fixtures[identifier], run_number,
                    timeout_ms, root, version, runtime, probe,
                ))
    summary = {
        "schemaVersion": 1,
        "release": "finding-012-r7-attribution",
        "layer": "native-lok",
        "nativeVersion": version,
        "probe": probe,
        "runtimeSource": runtime_source,
        "runtimeInstallPath": str(install_path),
        "runs": [
            {"fixture": item["fixture"]["id"], "run": item["run"],
             "timeoutMs": item["timeoutMs"], "outcome": item["outcome"],
             "stages": item["stages"], "pass": item["pass"]}
            for item in results
        ],
        "pass": all(item["pass"] for item in results),
    }
    write_json(root / "summary.json", summary)
    if not summary["pass"]:
        raise SystemExit(1)


def wasm_stages(metrics: dict[str, Any]) -> list[str]:
    stages = []
    for event in metrics.get("sdkEvents", []):
        detail = event.get("detail") if event.get("level") == "stage" else None
        if event.get("event") == "diagnostic" and isinstance(detail, dict):
            name = detail.get("name")
            if isinstance(name, str):
                stages.append(name)
    return stages


def wasm_outcome(metrics: dict[str, Any]) -> str:
    close = metrics.get("close") or {}
    if close.get("status") == "passed":
        return "close-pass"
    if close.get("error", {}).get("code") == "TIMEOUT":
        return "timeout"
    return "error"


def run_wasm_case(
    session_class: type[ChromeSession] | type[FirefoxSession],
    browser: str,
    base_url: str,
    fixture: dict[str, Any],
    run_number: int,
    timeout_ms: int,
    root: Path,
    artifact_hashes: dict[str, str],
) -> dict[str, Any]:
    case_root = root / fixture["id"] / f"run-{run_number}"
    case_root.mkdir(parents=True, exist_ok=True)
    session = session_class("cold")
    metrics: dict[str, Any] | None = None
    samples = []
    last_sample = 0.0
    try:
        session.navigate(
            f"{base_url}?fixture={fixture['id']}&timeoutMs={timeout_ms}&artifact=diagnostic"
        )
        deadline = time.monotonic() + timeout_ms / 1000 + 240
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__finding_012 || null")
            now = time.monotonic()
            if now - last_sample >= 1:
                samples.append(process_snapshot(session.process.pid, {
                    "checkpoint": metrics.get("stage") if metrics else None,
                    "cycle": run_number,
                    "activeWorkers": metrics.get("workers", {}).get("active") if metrics else None,
                    "activeHandles": metrics.get("handles", {}).get("active") if metrics else None,
                }))
                last_sample = now
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.2)
        if not metrics or not metrics.get("complete"):
            raise RuntimeError(f"fixture {fixture['id']} did not complete")
        stages = wasm_stages(metrics)
        outcome = wasm_outcome(metrics)
        result = {
            "schemaVersion": 1,
            "release": "finding-012-r7-attribution",
            "layer": "diagnostic-wasm",
            "browser": browser,
            "browserVersion": session.version,
            "fixture": fixture,
            "run": run_number,
            "timeoutMs": timeout_ms,
            "stages": stages,
            "outcome": outcome,
            "metrics": metrics,
            "processSamples": samples,
            "artifactHashes": artifact_hashes,
            "pass": outcome in {"close-pass", "timeout"} and ENTER in stages,
        }
        (case_root / "page.png").write_bytes(session.screenshot())
        (case_root / "browser.log.txt").write_text(
            str(evaluate(session, "document.querySelector('#log').textContent")),
            encoding="utf-8",
        )
    except Exception as error:  # noqa: BLE001 - preserve terminal evidence
        result = {
            "schemaVersion": 1,
            "release": "finding-012-r7-attribution",
            "layer": "diagnostic-wasm",
            "browser": browser,
            "fixture": fixture,
            "run": run_number,
            "timeoutMs": timeout_ms,
            "stages": wasm_stages(metrics or {}),
            "error": {"name": type(error).__name__, "message": str(error)},
            "lastMetrics": metrics,
            "processSamples": samples,
            "outcome": "runner-error",
            "pass": False,
        }
    finally:
        session.close()
    write_json(case_root / "result.json", result)
    return result


def wasm_layer(
    project: Path,
    evidence_root: Path,
    browser: str,
    timeout_ms: int,
    confirm_ms: int,
) -> None:
    manifest = load_json(project / "test-docs" / "r7-finding-012" / "manifest.json")
    fixtures = {item["id"]: item for item in manifest["variants"]}
    diagnostic = project / "dist" / "profiles" / "finding-012-diagnostic"
    hashes = {
        "loader": sha256(diagnostic / "probe.js"),
        "wasm": sha256(diagnostic / "probe.wasm"),
        "manifest": sha256(diagnostic / "sdk-manifest.json"),
        "productionLoader": sha256(project / "dist" / "profiles" / "writer-review" / "probe.35d96f5fdcb9ed0c.js"),
        "productionWasm": sha256(project / "dist" / "profiles" / "writer-review" / "probe.ba257beb038b6a2d.wasm"),
    }
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(port)],
        cwd=project, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    root = evidence_root / "wasm" / browser
    results: list[dict[str, Any]] = []
    try:
        base_url = f"http://127.0.0.1:{port}/r7-close-minimizer.html"
        wait_page(base_url)
        session_class = ChromeSession if browser == "chrome" else FirefoxSession
        for identifier in FIXTURE_IDS:
            results.append(run_wasm_case(
                session_class, browser, base_url, fixtures[identifier], 1,
                timeout_ms, root, hashes,
            ))
        first = {item["fixture"]["id"]: item for item in results}
        if first["t2-original"]["outcome"] == "timeout" \
                and first["t2-image-unwrapped"]["outcome"] == "close-pass":
            results.append(run_wasm_case(
                session_class, browser, base_url, fixtures["t2-original"], 2,
                confirm_ms, root, hashes,
            ))
            for run_number in (2, 3):
                results.append(run_wasm_case(
                    session_class, browser, base_url, fixtures["t2-image-unwrapped"],
                    run_number, timeout_ms, root, hashes,
                ))
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
    summary = {
        "schemaVersion": 1,
        "release": "finding-012-r7-attribution",
        "layer": "diagnostic-wasm",
        "browser": browser,
        "runs": [
            {"fixture": item["fixture"]["id"], "run": item["run"],
             "timeoutMs": item["timeoutMs"], "outcome": item["outcome"],
             "stages": item["stages"], "pass": item["pass"]}
            for item in results
        ],
        "artifactHashes": hashes,
        "pass": bool(results) and all(item["pass"] for item in results),
    }
    write_json(root / "summary.json", summary)
    if not summary["pass"]:
        raise SystemExit(1)


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer", choices=("native", "wasm"), required=True)
    parser.add_argument("--browser", choices=("chrome", "firefox"))
    parser.add_argument("--timeout-ms", type=int, default=10000)
    parser.add_argument("--confirm-timeout-ms", type=int, default=180000)
    parser.add_argument(
        "--native-install-path", type=Path,
        default=Path("/usr/lib/libreoffice/program"),
    )
    parser.add_argument("--native-source", type=Path)
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "012" / "r7-attribution",
    )
    args = parser.parse_args()
    if not 1000 <= args.timeout_ms <= 30000:
        raise SystemExit("classification timeout must be between 1000 and 30000 ms")
    if not args.timeout_ms <= args.confirm_timeout_ms <= 180000:
        raise SystemExit("confirmation timeout must be between classification and 180000 ms")
    if args.layer == "native":
        native_layer(
            project, args.evidence_root, args.timeout_ms, args.confirm_timeout_ms,
            args.native_install_path, args.native_source,
        )
    else:
        if not args.browser:
            raise SystemExit("--browser is required for the wasm layer")
        wasm_layer(
            project, args.evidence_root, args.browser,
            args.timeout_ms, args.confirm_timeout_ms,
        )


if __name__ == "__main__":
    main()
