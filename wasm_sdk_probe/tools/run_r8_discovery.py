#!/usr/bin/env python3
"""Run R8-A T0/T1 delivery discovery with persistent browser profiles."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from r8_release import load_json, write_json
from run_browser_probe import ChromeSession, FirefoxSession, free_port, wait_http


def evaluate(session: ChromeSession | FirefoxSession, expression: str) -> Any:
    if isinstance(session, ChromeSession):
        return session.evaluate(expression)
    return session.execute(f"return ({expression});")


def navigate(session: ChromeSession | FirefoxSession, url: str) -> None:
    if isinstance(session, ChromeSession):
        session.call("Page.navigate", {"url": url})
    else:
        session.navigate(url)


def wait_for_result(session: ChromeSession | FirefoxSession, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        try:
            raw = evaluate(session, "JSON.stringify(globalThis.__r8_discovery || null)")
            last = json.loads(raw) if raw else None
            if last and last.get("status") in {"complete", "failed"}:
                return last
        except Exception:
            pass
        time.sleep(0.25)
    raise TimeoutError(f"R8 discovery timed out; last={last}")


def head(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return {
                "url": url,
                "status": response.status,
                "headers": {key.lower(): value for key, value in response.headers.items()},
            }
    except urllib.error.HTTPError as error:
        try:
            return {
                "url": url,
                "status": error.code,
                "headers": {key.lower(): value for key, value in error.headers.items()},
            }
        finally:
            error.close()


def server_command(
    project: Path,
    port: int,
    role: str,
    allow_origin: str | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(project / "tools" / "r8_delivery_server.py"),
        "--root",
        str(project / "dist"),
        "--port",
        str(port),
        "--role",
        role,
    ]
    if allow_origin:
        command.extend(["--allow-origin", allow_origin])
    return command




def spawn_captured(command: list[str]) -> subprocess.Popen[str]:
    """Spawn with output captured to temp files, never to an unread pipe.

    finding 023: with stdout/stderr=PIPE and no reader, a chatty child fills
    the 64 KiB pipe and blocks mid-write; communicate() at stop time drains
    too late to prevent the wedge.  stop_process() reads the files back so
    the evidence shape is unchanged.
    """
    stdout = tempfile.NamedTemporaryFile(
        mode="w+", prefix="r8-server-", suffix=".out", delete=False)
    stderr = tempfile.NamedTemporaryFile(
        mode="w+", prefix="r8-server-", suffix=".err", delete=False)
    process = subprocess.Popen(command, stdout=stdout, stderr=stderr, text=True)
    process.capture_files = (stdout, stderr)  # type: ignore[attr-defined]
    return process


def drain_captured(process: subprocess.Popen[str]) -> tuple[str, str]:
    captured = getattr(process, "capture_files", None)
    if captured is None:
        stdout, stderr = process.communicate()
        return stdout or "", stderr or ""
    values = []
    for handle in captured:
        handle.flush()
        handle.seek(0)
        values.append(handle.read())
        handle.close()
        os.unlink(handle.name)
    return values[0], values[1]


def stop_process(process: subprocess.Popen[str]) -> dict[str, Any]:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    stdout, stderr = drain_captured(process)
    return {
        "returnCode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def fetch_json(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def profile_temp_parent(project: Path) -> Path:
    """Keep persistent profiles visible to strict-confined browser packages."""
    parent = project / "dist" / "r8"
    parent.mkdir(parents=True, exist_ok=True)
    return parent


def run_phase(
    session_class,
    profile: Path,
    url: str,
    output: Path,
    timeout: float,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    session = session_class("hot", profile_dir=profile)
    browser_version = session.version
    try:
        navigate(session, url)
        result = wait_for_result(session, timeout)
        result["browserVersion"] = browser_version
        write_json(output / "result.json", result)
        (output / "page.png").write_bytes(session.screenshot())
        (output / "page.log.txt").write_text(
            "\n".join(result.get("logs", [])) + "\n",
            encoding="utf-8",
        )
        return result
    except Exception as error:  # noqa: BLE001 - preserve terminal evidence
        result = {
            "browserVersion": browser_version,
            "error": {"name": type(error).__name__, "message": str(error)},
            "pass": False,
        }
        write_json(output / "result.json", result)
        try:
            (output / "page.png").write_bytes(session.screenshot())
        except Exception:
            pass
        return result
    finally:
        session.close()


def header_checks(
    app_origin: str,
    artifact_origin: str,
    manifest: dict[str, Any],
    topology: str,
) -> dict[str, Any]:
    by_role = {item["role"]: item for item in manifest["artifacts"]}
    app_entry = head(f"{app_origin}/r8-discovery.html")
    app_worker = head(f"{app_origin}/r8-discovery-sw.js")
    artifact_loader = head(f"{artifact_origin}/{by_role['wasm-loader']['url']}")
    artifact_wasm = head(f"{artifact_origin}/{by_role['wasm-binary']['url']}")
    app_headers = app_entry["headers"]
    loader_headers = artifact_loader["headers"]
    checks = {
        "entryOk": app_entry["status"] == 200,
        "workerNoCache": app_worker["headers"].get("cache-control") == "no-cache",
        "coop": app_headers.get("cross-origin-opener-policy") == "same-origin",
        "coep": app_headers.get("cross-origin-embedder-policy") == "require-corp",
        "nosniff": app_headers.get("x-content-type-options") == "nosniff",
        "loaderImmutable": "immutable" in loader_headers.get("cache-control", ""),
        "loaderType": loader_headers.get("content-type", "").startswith("text/javascript"),
        "wasmType": artifact_wasm["headers"].get("content-type") == "application/wasm",
    }
    if topology == "t1":
        checks.update({
            "artifactCors": loader_headers.get("access-control-allow-origin") == app_origin,
            "artifactCorp": loader_headers.get("cross-origin-resource-policy") == "cross-origin",
        })
    return {
        "entry": app_entry,
        "worker": app_worker,
        "loader": artifact_loader,
        "wasm": artifact_wasm,
        "checks": checks,
        "pass": all(checks.values()),
    }


def run_topology(
    project: Path,
    evidence_root: Path,
    browser: str,
    topology: str,
    timeout: float,
) -> dict[str, Any]:
    app_port = free_port()
    artifact_port = free_port() if topology == "t1" else app_port
    app_origin = f"http://127.0.0.1:{app_port}"
    artifact_origin = f"http://127.0.0.1:{artifact_port}"
    processes: list[subprocess.Popen[str]] = []
    output = evidence_root / "browser" / browser / topology
    output.mkdir(parents=True, exist_ok=True)
    server_logs: dict[str, Any] = {}
    try:
        app_process = spawn_captured(server_command(project, app_port, "app"))
        processes.append(app_process)
        wait_http(f"{app_origin}/__r8__/health")
        if topology == "t1":
            artifact_process = spawn_captured(
                server_command(project, artifact_port, "artifact", app_origin))
            processes.append(artifact_process)
            wait_http(f"{artifact_origin}/__r8__/health")

        query_base = {
            "topology": topology,
            "artifactOrigin": artifact_origin,
        }
        session_class = ChromeSession if browser == "chrome" else FirefoxSession
        with tempfile.TemporaryDirectory(
            prefix=f"r8-{browser}-{topology}-profile-",
            dir=profile_temp_parent(project),
        ) as temporary:
            profile = Path(temporary)
            initial_query = urllib.parse.urlencode({**query_base, "phase": "initial"})
            initial = run_phase(
                session_class,
                profile,
                f"{app_origin}/r8-discovery.html?{initial_query}",
                output / "initial",
                timeout,
            )
            restart_query = urllib.parse.urlencode({**query_base, "phase": "restart"})
            restart = run_phase(
                session_class,
                profile,
                f"{app_origin}/r8-discovery.html?{restart_query}",
                output / "restart",
                timeout,
            )

        manifest = load_json(project / "dist" / "r8" / "release-manifest.json")
        headers = header_checks(app_origin, artifact_origin, manifest, topology)
        write_json(output / "headers.json", headers)
        app_requests = fetch_json(f"{app_origin}/__r8__/requests")
        artifact_requests = (
            fetch_json(f"{artifact_origin}/__r8__/requests")
            if topology == "t1" else app_requests
        )
        write_json(output / "app-requests.json", app_requests)
        write_json(output / "artifact-requests.json", artifact_requests)
        result = {
            "browser": browser,
            "topology": topology,
            "appOrigin": app_origin,
            "artifactOrigin": artifact_origin,
            "initial": initial,
            "restart": restart,
            "headers": headers,
            "pass": initial.get("pass") is True
            and restart.get("pass") is True
            and headers["pass"],
        }
        write_json(output / "summary.json", result)
        return result
    finally:
        for index, process in enumerate(reversed(processes), start=1):
            server_logs[f"server{index}"] = stop_process(process)
        if server_logs:
            write_json(output / "server-processes.json", server_logs)


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--topology", choices=("all", "t0", "t1"), default="all")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r8" / "discovery",
    )
    args = parser.parse_args()

    manifest_path = project / "dist" / "r8" / "release-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"missing R8 release manifest: {manifest_path}")

    topologies = ("t0", "t1") if args.topology == "all" else (args.topology,)
    results = [
        run_topology(project, args.evidence_root.resolve(), args.browser, topology, args.timeout)
        for topology in topologies
    ]
    summary = {
        "schemaVersion": 1,
        "release": "R8-A-delivery-discovery",
        "browser": args.browser,
        "topologies": results,
        "pass": len(results) == len(topologies) and all(item["pass"] for item in results),
    }
    output = args.evidence_root.resolve() / "browser" / args.browser / "summary.json"
    write_json(output, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
