#!/usr/bin/env python3
"""Run the R8-B direct-delivery success, fault, and round-trip browser matrix."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from r7_support import evaluate, write_json
from r8_release import load_json
from run_browser_probe import ChromeSession, FirefoxSession, free_port, wait_http


def navigate(session: ChromeSession | FirefoxSession, url: str) -> None:
    if isinstance(session, ChromeSession):
        session.call("Page.navigate", {"url": url})
    else:
        session.navigate(url)


def wait_result(session: ChromeSession | FirefoxSession, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        try:
            raw = evaluate(session, "JSON.stringify(globalThis.__r8_delivery || null)")
            last = json.loads(raw) if raw else None
            if last and last.get("status") in {"complete", "failed"}:
                return last
        except Exception:
            pass
        time.sleep(0.25)
    raise TimeoutError(f"R8-B page timed out; last={last}")




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
    return {"returnCode": process.returncode, "stdout": stdout, "stderr": stderr}


def fetch_json(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def server_command(project: Path, port: int, role: str,
                   allow_origin: str | None = None) -> list[str]:
    command = [
        sys.executable, str(project / "tools" / "r8_delivery_server.py"),
        "--root", str(project / "dist"), "--port", str(port), "--role", role,
    ]
    if allow_origin:
        command.extend(["--allow-origin", allow_origin])
    return command


def case_url(app_origin: str, values: dict[str, Any]) -> str:
    query = urllib.parse.urlencode({key: value for key, value in values.items() if value is not None})
    return f"{app_origin}/r8-delivery.html?{query}"


def run_case(
    session_class: type[ChromeSession] | type[FirefoxSession],
    profile: Path,
    url: str,
    output: Path,
    timeout: float,
    cache_mode: str,
    save_output: bool = False,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    session = session_class(cache_mode, profile_dir=profile)
    started = time.monotonic()
    try:
        navigate(session, url)
        result = wait_result(session, timeout)
        result["browserVersion"] = session.version
        result["runnerElapsedMs"] = round((time.monotonic() - started) * 1000, 3)
        if save_output and result.get("pass") is True:
            encoded = evaluate(session, "globalThis.__r8_delivery_output_base64()")
            raw = base64.b64decode(str(encoded), validate=True)
            output_path = output / "output.odt"
            output_path.write_bytes(raw)
            result["outputPath"] = str(output_path)
        write_json(output / "result.json", result)
        if result.get("pass") is not True or save_output:
            (output / "page.png").write_bytes(session.screenshot())
        return result
    except Exception as error:  # noqa: BLE001 - terminal evidence is intentional
        result = {
            "browserVersion": getattr(session, "version", "unknown"),
            "url": url,
            "error": {"name": type(error).__name__, "message": str(error)},
            "runnerElapsedMs": round((time.monotonic() - started) * 1000, 3),
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


def success_values(topology: str, artifact_origin: str, transport: str,
                   cache: str, **extra: Any) -> dict[str, Any]:
    return {
        "topology": topology,
        "artifactOrigin": artifact_origin,
        "policy": "standard",
        "transport": transport,
        "cache": cache,
        "scenario": "success",
        **extra,
    }


def negative_cases(topology: str, artifact_origin: str, redirect_origin: str,
                   stale_release_id: str) -> list[tuple[str, dict[str, Any]]]:
    base = {
        "topology": topology, "artifactOrigin": artifact_origin,
        "policy": "standard", "transport": "identity", "cache": "cold",
        "scenario": "negative",
    }
    cases: list[tuple[str, dict[str, Any]]] = []
    for fault in [
        "wrong-bytes", "manifest-bad-schema", "manifest-bad-release",
        "manifest-duplicate-role", "manifest-unknown-role", "manifest-path-traversal",
        "manifest-credential-url", "manifest-unknown-scheme", "manifest-missing-role",
    ]:
        cases.append((fault, {**base, "manifestFault": fault,
                              "expect": "RELEASE_MANIFEST_INVALID"}))
    cases.extend([
        ("js-404", {**base, "deliveryFault": "http-404", "faultRole": "app-module",
                    "expect": "ARTIFACT_HTTP_ERROR"}),
        ("worker-500", {**base, "deliveryFault": "http-500", "faultRole": "sdk-worker",
                        "expect": "ARTIFACT_HTTP_ERROR"}),
        ("wasm-404", {**base, "deliveryFault": "http-404", "faultRole": "wasm-binary",
                      "expect": "ARTIFACT_HTTP_ERROR"}),
        ("data-wrong-bytes", {**base, "deliveryFault": "wrong-bytes", "faultRole": "base-data",
                              "expect": "ARTIFACT_HASH_MISMATCH"}),
        ("metadata-wrong-type", {**base, "deliveryFault": "wrong-type", "faultRole": "base-metadata",
                                 "expect": "ARTIFACT_MEDIA_TYPE_MISMATCH"}),
        ("wrong-encoding", {**base, "deliveryFault": "wrong-encoding", "faultRole": "app-module",
                            "expect": "ARTIFACT_ENCODING_MISMATCH"}),
        ("partial-response", {**base, "deliveryFault": "truncated", "faultRole": "app-module",
                              "expect": "ARTIFACT_SIZE_MISMATCH"}),
        ("timeout-late-response", {**base, "deliveryFault": "delay", "faultRole": "app-module",
                                   "verifyTimeoutMs": 50, "expect": "DELIVERY_TIMEOUT"}),
        ("cancel", {**base, "scenario": "cancel", "deliveryFault": "delay",
                    "faultRole": "app-module", "cancelAfterMs": 25,
                    "expect": "DELIVERY_ABORTED"}),
        ("stale-release", {**base, "deliveryFault": "stale-release", "faultRole": "sdk-manifest",
                           "staleReleaseId": stale_release_id,
                           "expect": "ARTIFACT_SIZE_MISMATCH"}),
        ("redirect-cross-origin", {**base, "deliveryFault": "redirect-cross-origin",
                                   "faultRole": "app-module",
                                   "redirectTargetOrigin": redirect_origin,
                                   "expect": "ARTIFACT_HTTP_ERROR"}),
        ("no-coep", {**base, "serverFault": "no-coep",
                     "expect": "CROSS_ORIGIN_ISOLATION_REQUIRED"}),
    ])
    if topology == "t1":
        cases.extend([
            ("no-cors", {**base, "deliveryFault": "no-cors", "faultRole": "wasm-binary",
                         "expect": "ARTIFACT_HTTP_ERROR"}),
            ("no-corp", {**base, "deliveryFault": "no-corp", "faultRole": "wasm-binary",
                         "expect": "CROSS_ORIGIN_ISOLATION_REQUIRED"}),
        ])
    return cases


def run_topology(project: Path, evidence_root: Path, browser: str, topology: str,
                 suite: str, timeout: float, index: dict[str, Any]) -> dict[str, Any]:
    app_port, artifact_port, redirect_port = free_port(), free_port(), free_port()
    app_origin = f"http://127.0.0.1:{app_port}"
    artifact_origin = app_origin if topology == "t0" else f"http://127.0.0.1:{artifact_port}"
    redirect_origin = f"http://127.0.0.1:{redirect_port}"
    processes: list[subprocess.Popen[str]] = []
    root = evidence_root / "browser" / browser / topology
    root.mkdir(parents=True, exist_ok=True)
    session_class = ChromeSession if browser == "chrome" else FirefoxSession
    results: list[dict[str, Any]] = []
    profile_parent = project / "dist" / "r8-b-profiles"
    profile_parent.mkdir(parents=True, exist_ok=True)
    try:
        processes.append(spawn_captured(server_command(project, app_port, "app")))
        wait_http(f"{app_origin}/__r8__/health")
        if topology == "t1":
            processes.append(spawn_captured(
                server_command(project, artifact_port, "artifact", app_origin)))
            wait_http(f"{artifact_origin}/__r8__/health")
        processes.append(spawn_captured(
            server_command(project, redirect_port, "artifact", app_origin)))
        wait_http(f"{redirect_origin}/__r8__/health")

        def execute(identifier: str, values: dict[str, Any], cache_mode: str = "cold",
                    profile: Path | None = None, save_output: bool = False) -> dict[str, Any]:
            existing_path = root / identifier / "result.json"
            if existing_path.is_file():
                existing = load_json(existing_path)
                expected_release = next(item["releaseId"] for item in index["releases"]
                                        if item["policy"] == values.get("policy", "standard"))
                if (existing.get("pass") is True
                        and existing.get("candidateReleaseId") == expected_release
                        and (not save_output or (root / identifier / "output.odt").is_file())):
                    existing["caseId"] = identifier
                    existing["resumed"] = True
                    results.append(existing)
                    return existing
            if profile is not None:
                profile.mkdir(parents=True, exist_ok=True)
                result = run_case(session_class, profile, case_url(app_origin, values),
                                  root / identifier, timeout, cache_mode, save_output)
            else:
                with tempfile.TemporaryDirectory(
                    prefix=f"r8b-{browser}-{topology}-", dir=profile_parent,
                ) as temporary:
                    result = run_case(session_class, Path(temporary), case_url(app_origin, values),
                                      root / identifier, timeout, cache_mode, save_output)
            result["caseId"] = identifier
            results.append(result)
            return result

        execute("smoke-standard-identity", success_values(
            topology, artifact_origin, "identity", "cold"
        ), save_output=suite == "smoke")
        if suite == "smoke":
            return {"browser": browser, "topology": topology, "cases": results,
                    "pass": all(item.get("pass") is True for item in results)}

        for transport in ("identity", "gzip"):
            for repetition in range(1, 4):
                execute(f"{transport}-cold-{repetition}", success_values(
                    topology, artifact_origin, transport, "cold"
                ))
            with tempfile.TemporaryDirectory(
                prefix=f"r8b-{browser}-{topology}-{transport}-warm-", dir=profile_parent,
            ) as warm_temporary:
                warm_profile = Path(warm_temporary)
                execute(f"{transport}-warm-prime", success_values(
                    topology, artifact_origin, transport, "warm", scenario="verify-only"
                ), cache_mode="hot", profile=warm_profile)
                for repetition in range(1, 4):
                    execute(f"{transport}-warm-{repetition}", success_values(
                        topology, artifact_origin, transport, "warm"
                    ), cache_mode="hot", profile=warm_profile)

        full_id = next(item["releaseId"] for item in index["releases"]
                       if item["policy"] == "full-fidelity")
        standard_id = next(item["releaseId"] for item in index["releases"]
                           if item["policy"] == "standard")
        if topology == "t0":
            fixtures = [
                ("r6-reader-smoke", "./r6-fixtures/t1-plain-zh.odt",
                 "Final line：ODT round-trip 完整性檢查。", "standard"),
                ("r7-t1-roundtrip", "./r7-compat-fixtures/l0-t1-plain-zh.odt",
                 "Final line：ODT round-trip 完整性檢查。", "standard"),
                ("r7-t2-roundtrip", "./r7-compat-fixtures/l0-t2-styled.odt",
                 "文件結尾：請確認表格、圖片、註解與標題樣式均保留。", "standard"),
                ("font-full-fidelity", "./r7-compat-fixtures/l1-hyperlink-font.odt",
                 "Normal text", "full-fidelity"),
            ]
            for identifier, document, search, policy in fixtures:
                execute(identifier, success_values(
                    topology, artifact_origin, "gzip", "cold", policy=policy,
                    document=document, name=Path(document).name, search=search,
                ), save_output=True)
            execute("fidelity-restart", success_values(
                topology, artifact_origin, "identity", "cold",
                scenario="fidelity-restart",
            ))
            execute("handshake-mismatch", success_values(
                topology, artifact_origin, "identity", "cold",
                scenario="handshake-mismatch", expect="WORKER_HANDSHAKE_MISMATCH",
            ))
            execute("optional-pack-404", {
                **success_values(topology, artifact_origin, "identity", "cold",
                                 policy="full-fidelity"),
                "scenario": "negative", "deliveryFault": "http-404",
                "faultRole": "fallback-data", "expect": "ARTIFACT_HTTP_ERROR",
            })

        for identifier, values in negative_cases(
            topology, artifact_origin, redirect_origin, full_id if standard_id else full_id
        ):
            execute(f"negative-{identifier}", values)
        execute("known-good-recovery", success_values(
            topology, artifact_origin, "identity", "cold"
        ))

        app_requests = fetch_json(f"{app_origin}/__r8__/requests")
        artifact_requests = (fetch_json(f"{artifact_origin}/__r8__/requests")
                             if topology == "t1" else app_requests)
        write_json(root / "app-requests.json", app_requests)
        write_json(root / "artifact-requests.json", artifact_requests)
        return {"browser": browser, "topology": topology, "cases": results,
                "releaseIds": {"standard": standard_id, "fullFidelity": full_id},
                "pass": all(item.get("pass") is True for item in results)}
    finally:
        write_json(root / "server-processes.json", {
            f"server{number}": stop_process(process)
            for number, process in enumerate(reversed(processes), start=1)
        })


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--topology", choices=("all", "t0", "t1"), default="all")
    parser.add_argument("--suite", choices=("full", "smoke"), default="full")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--evidence-root", type=Path,
                        default=workspace / "findings" / "evidence" / "sdk-r8" / "delivery")
    args = parser.parse_args()
    index = load_json(project / "dist" / "releases" / "index.json")
    topologies = ("t0", "t1") if args.topology == "all" else (args.topology,)
    results = [run_topology(project, args.evidence_root.resolve(), args.browser,
                            topology, args.suite, args.timeout, index)
               for topology in topologies]
    summary = {
        "schemaVersion": 1, "release": "R8-B-versioned-artifact-delivery",
        "browser": args.browser, "suite": args.suite, "topologies": results,
        "pass": all(item["pass"] for item in results),
    }
    output = args.evidence_root.resolve() / "browser" / args.browser / "summary.json"
    write_json(output, summary)
    print(json.dumps({
        "output": str(output), "browser": args.browser, "suite": args.suite,
        "topologies": [{"topology": item["topology"], "cases": len(item["cases"]),
                         "pass": item["pass"]} for item in results],
        "pass": summary["pass"],
    }, ensure_ascii=False, indent=2))
    if not summary["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
