#!/usr/bin/env python3
"""Run deterministic R8-C Service Worker install/update/offline/recovery scenarios."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Any

from r7_support import evaluate, load_json, run_in_page, write_json
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
            raw = evaluate(session, "JSON.stringify(globalThis.__r8_update || null)")
            last = json.loads(raw) if raw else None
            if last and last.get("status") in {"complete", "failed"}:
                return last
        except Exception:
            pass
        time.sleep(0.25)
    raise TimeoutError(f"R8-C page timed out; last={last}")




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


def server_command(project: Path, port: int, role: str,
                   allow_origin: str | None = None) -> list[str]:
    command = [
        sys.executable, str(project / "tools" / "r8_delivery_server.py"),
        "--root", str(project / "dist"), "--port", str(port), "--role", role,
    ]
    if allow_origin:
        command.extend(["--allow-origin", allow_origin])
    return command


def page_url(app_origin: str, values: dict[str, Any]) -> str:
    query = urllib.parse.urlencode({
        key: value for key, value in values.items() if value is not None
    })
    return f"{app_origin}/r8-update.html?{query}"


def run_page(
    session_class: type[ChromeSession] | type[FirefoxSession],
    profile: Path,
    url: str,
    output: Path,
    timeout: float,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    session = session_class("hot", profile_dir=profile)
    started = time.monotonic()
    try:
        navigate(session, url)
        result = wait_result(session, timeout)
        result["browserVersion"] = session.version
        result["runnerElapsedMs"] = round((time.monotonic() - started) * 1000, 3)
        try:
            (output / "browser.log.txt").write_text(
                str(evaluate(session, "document.querySelector('#log')?.textContent || ''")),
                encoding="utf-8",
            )
        except Exception:
            pass
        if result.get("pass") is not True:
            (output / "page.png").write_bytes(session.screenshot())
        write_json(output / "result.json", result)
        return result
    except Exception as error:  # noqa: BLE001 - terminal evidence is intentional
        result = {
            "url": url,
            "browserVersion": getattr(session, "version", "unknown"),
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


def state_from(result: dict[str, Any]) -> dict[str, Any]:
    service_worker = result.get("serviceWorker") or {}
    return service_worker.get("state") or {}


def case_pass(result: dict[str, Any], current: str | None = None,
              known_good: str | None = None) -> bool:
    if result.get("pass") is not True:
        return False
    state = state_from(result)
    return ((current is None or state.get("currentReleaseId") == current)
            and (known_good is None or state.get("lastKnownGoodReleaseId") == known_good))


def run_multi_client(
    session_class: type[ChromeSession] | type[FirefoxSession],
    profile: Path,
    app_origin: str,
    artifact_origin: str,
    topology: str,
    release_a: dict[str, Any],
    release_b: dict[str, Any],
    output: Path,
    timeout: float,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    session = session_class("hot", profile_dir=profile)
    started = time.monotonic()
    try:
        # The Firefox-only branch below was written to get around a hang in the
        # injected-script path.  finding 025 shows that hang was our own bug
        # (evaluate() built `return \n <script>`, ASI made it dead code), so the
        # branch may now be retirable -- two browsers on two code paths is exactly
        # what makes them incomparable.  This env var forces Firefox down the
        # shared path so that can be measured; default behaviour is unchanged.
        force_injected = os.environ.get("OXSDK_R8C_FORCE_INJECTED_MULTICLIENT") == "1"
        if isinstance(session, FirefoxSession) and not force_injected:
            parent_handle = session.command("GET", "/window")
            navigate(session, page_url(app_origin, {
                "topology": topology, "artifactOrigin": artifact_origin, "action": "status",
            }))
            initial = wait_result(session, timeout)
            if initial.get("pass") is not True:
                raise RuntimeError("multi-client parent status page failed")

            old_handle = session.command("POST", "/window/new", {"type": "tab"})["handle"]
            session.command("POST", "/window", {"handle": old_handle})
            navigate(session, page_url(app_origin, {
                "topology": topology, "artifactOrigin": artifact_origin,
                "action": "pin-only", "releaseId": release_a["releaseId"],
            }))
            old_metrics = wait_result(session, timeout)

            session.command("POST", "/window", {"handle": parent_handle})
            navigate(session, page_url(app_origin, {
                "topology": topology, "artifactOrigin": artifact_origin,
                "action": "stage", "slot": "B",
            }))
            staged = wait_result(session, timeout)
            navigate(session, page_url(app_origin, {
                "topology": topology, "artifactOrigin": artifact_origin,
                "action": "activate", "slot": "B",
            }))
            activated = wait_result(session, timeout)

            new_handle = session.command("POST", "/window/new", {"type": "tab"})["handle"]
            session.command("POST", "/window", {"handle": new_handle})
            navigate(session, page_url(app_origin, {
                "topology": topology, "artifactOrigin": artifact_origin,
                "action": "pin-only", "releaseId": release_b["releaseId"],
            }))
            new_metrics = wait_result(session, timeout)
            session.command("POST", "/window", {"handle": parent_handle})
            navigate(session, page_url(app_origin, {
                "topology": topology, "artifactOrigin": artifact_origin, "action": "status",
            }))
            status_metrics = wait_result(session, timeout)
            status = status_metrics.get("serviceWorker") or {}
            pin_values = list((status.get("state") or {}).get("clientPins", {}).values())
            value = {
                "oldClientReleaseId": release_a["releaseId"],
                "newClientReleaseId": release_b["releaseId"],
                "oldClientPass": old_metrics.get("pass") is True,
                "newClientPass": new_metrics.get("pass") is True,
                "stagedPass": staged.get("pass") is True,
                "health": activated.get("runtime"),
                "status": status,
                "pinValues": pin_values,
            }
            value["pass"] = (
                value["oldClientPass"] and value["newClientPass"] and value["stagedPass"]
                and activated.get("pass") is True
                and (status.get("state") or {}).get("currentReleaseId") == release_b["releaseId"]
                and (status.get("state") or {}).get("lastKnownGoodReleaseId") == release_b["releaseId"]
                and release_a["releaseId"] in pin_values
                and release_b["releaseId"] in pin_values
            )
            result = {
                "schemaVersion": 1, "release": "R8-C-service-worker",
                "browser": session.version, "topology": topology,
                "action": "multi-client-update", "strategy": "webdriver-tabs",
                "multiClient": value, "serviceWorker": status,
                "runnerElapsedMs": round((time.monotonic() - started) * 1000, 3),
                "pass": value["pass"],
            }
            write_json(output / "result.json", result)
            return result

        navigate(session, page_url(app_origin, {
            "topology": topology, "artifactOrigin": artifact_origin, "action": "status",
        }))
        initial = wait_result(session, timeout)
        if initial.get("pass") is not True:
            raise RuntimeError("multi-client parent status page failed")
        old_client_url = page_url(app_origin, {
            "topology": topology,
            "artifactOrigin": artifact_origin,
            "action": "pin-only",
            "releaseId": release_a["releaseId"],
        })
        new_client_url = page_url(app_origin, {
            "topology": topology,
            "artifactOrigin": artifact_origin,
            "action": "pin-only",
            "releaseId": release_b["releaseId"],
        })
        stage_payload = {
            "releaseId": release_b["releaseId"],
            "manifestUrl": f"{app_origin}/r8c/{release_b['manifestUrl']}",
            "manifestSha256": release_b["manifestSha256"],
            "requiredArtifactCount": release_b.get("requiredArtifactCount", 15),
            "artifactOrigin": artifact_origin,
        }
        expression = f"""
          (() => {{
            window.__r8_multi_result = null;
            const waitFrame = (frame) => new Promise((resolve, reject) => {{
              const started = performance.now();
              const poll = () => {{
                try {{
                  const value = frame.contentWindow.__r8_update;
                  if (value?.status === 'complete') return resolve(value);
                  if (value?.status === 'failed') return reject(new Error(JSON.stringify(value.error)));
                }} catch (error) {{}}
                if (performance.now() - started > 120000)
                  return reject(new Error('pinned client iframe timed out'));
                setTimeout(poll, 100);
              }};
              poll();
            }});
            (async () => {{
              const oldFrame = document.createElement('iframe');
              oldFrame.id = 'old-release-client';
              oldFrame.src = {json.dumps(old_client_url)};
              document.body.append(oldFrame);
              const oldMetrics = await waitFrame(oldFrame);
              const staged = await globalThis.__r8_update_command(
                'stage-release', {json.dumps(stage_payload)}, 900000
              );
              await globalThis.__r8_update_command('activate-release', {{
                releaseId: {json.dumps(release_b['releaseId'])}
              }});
              const health = await globalThis.__r8_runtime_health(
                {json.dumps(release_b['releaseId'])}
              );
              await globalThis.__r8_update_command('health-result', {{
                releaseId: {json.dumps(release_b['releaseId'])}, pass: health.pass
              }});
              const newFrame = document.createElement('iframe');
              newFrame.id = 'new-release-client';
              newFrame.src = {json.dumps(new_client_url)};
              document.body.append(newFrame);
              const newMetrics = await waitFrame(newFrame);
              const status = await globalThis.__r8_update_command('status');
              const pinValues = Object.values(status.state.clientPins);
              return {{
                oldClientReleaseId: {json.dumps(release_a['releaseId'])},
                newClientReleaseId: {json.dumps(release_b['releaseId'])},
                oldClientPass: oldMetrics.pass,
                newClientPass: newMetrics.pass,
                stagedArtifacts: staged.cachedArtifacts,
                health,
                status,
                pinValues,
                pass: oldMetrics.pass === true && newMetrics.pass === true
                  && health.pass === true
                  && status.state.currentReleaseId === {json.dumps(release_b['releaseId'])}
                  && status.state.lastKnownGoodReleaseId === {json.dumps(release_b['releaseId'])}
                  && pinValues.includes({json.dumps(release_a['releaseId'])})
                  && pinValues.includes({json.dumps(release_b['releaseId'])})
              }};
            }})().then(
              value => {{ window.__r8_multi_result = value; }},
              error => {{ window.__r8_multi_result = {{
                pass: false,
                error: {{ name: error?.name || 'Error', message: String(error?.message || error) }}
              }}; }}
            );
            return true;
          }})()
        """
        run_in_page(session, expression)
        deadline = time.monotonic() + timeout
        value = None
        while time.monotonic() < deadline:
            raw = evaluate(session, "JSON.stringify(globalThis.__r8_multi_result || null)")
            value = json.loads(raw) if raw else None
            if value is not None:
                break
            time.sleep(0.25)
        if value is None:
            raise TimeoutError("R8-C multi-client update timed out")
        result = {
            "schemaVersion": 1,
            "release": "R8-C-service-worker",
            "browser": session.version,
            "topology": topology,
            "action": "multi-client-update",
            "multiClient": value,
            "serviceWorker": value.get("status"),
            "runnerElapsedMs": round((time.monotonic() - started) * 1000, 3),
            "pass": value.get("pass") is True,
        }
        if not result["pass"]:
            (output / "page.png").write_bytes(session.screenshot())
        write_json(output / "result.json", result)
        return result
    except Exception as error:  # noqa: BLE001
        result = {
            "schemaVersion": 1,
            "release": "R8-C-service-worker",
            "topology": topology,
            "action": "multi-client-update",
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


def run_topology(project: Path, evidence_root: Path, browser: str, topology: str,
                 suite: str, timeout: float, release_set: dict[str, Any]) -> dict[str, Any]:
    app_port = free_port()
    artifact_port = free_port()
    app_origin = f"http://127.0.0.1:{app_port}"
    artifact_origin = app_origin if topology == "t0" else f"http://127.0.0.1:{artifact_port}"
    session_class = ChromeSession if browser == "chrome" else FirefoxSession
    root = evidence_root / "browser" / browser / topology
    root.mkdir(parents=True, exist_ok=True)
    profile = project / "dist" / "r8-c-profiles" / f"{browser}-{topology}-main"
    if profile.exists():
        shutil.rmtree(profile)
    profile.mkdir(parents=True)
    releases = {item["slot"]: item for item in release_set["releases"]}
    release_a = releases["A"]["releaseId"]
    release_b = releases["B"]["releaseId"]
    release_c = releases["C"]["releaseId"]
    processes: list[subprocess.Popen[str]] = []
    server_runs: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    def start_servers() -> None:
        nonlocal processes
        if processes:
            raise RuntimeError("R8-C servers are already running")
        processes = [spawn_captured(server_command(project, app_port, "app"))]
        wait_http(f"{app_origin}/__r8__/health")
        if topology == "t1":
            processes.append(spawn_captured(
                server_command(project, artifact_port, "artifact", app_origin)))
            wait_http(f"{artifact_origin}/__r8__/health")

    def stop_servers(label: str) -> None:
        nonlocal processes
        server_runs.append({
            "label": label,
            "servers": [stop_process(process) for process in reversed(processes)],
        })
        processes = []

    def execute(identifier: str, values: dict[str, Any], expected_current: str | None = None,
                expected_known_good: str | None = None,
                target_profile: Path | None = None) -> dict[str, Any]:
        case_root = root / identifier
        result = run_page(
            session_class,
            target_profile or profile,
            page_url(app_origin, {
                "topology": topology,
                "artifactOrigin": artifact_origin,
                **values,
            }),
            case_root,
            timeout,
        )
        result["caseId"] = identifier
        result["gatePass"] = case_pass(result, expected_current, expected_known_good)
        write_json(case_root / "result.json", result)
        results.append(result)
        return result

    try:
        start_servers()
        execute("fresh-1", {"action": "fresh"}, release_a, release_a)
        execute("warm-1", {"action": "health"}, release_a, release_a)

        if suite == "smoke":
            execute("stage-b", {"action": "stage", "slot": "B"}, release_a, release_a)
            execute("activate-b", {"action": "activate", "slot": "B"}, release_b, release_b)
            execute("rollback-a", {
                "action": "rollback", "releaseId": release_a,
            }, release_a, release_a)
            stop_servers("before-offline")
            execute("offline-known-good", {"action": "offline"}, release_a, release_a)
            start_servers()
            execute("online-recovery", {"action": "status"}, release_a, release_a)
        elif suite == "multi-client":
            multi = run_multi_client(
                session_class, profile, app_origin, artifact_origin, topology,
                releases["A"], releases["B"], root / "update-multi-client-1", timeout,
            )
            multi["caseId"] = "update-multi-client-1"
            multi["gatePass"] = multi.get("pass") is True
            write_json(root / "update-multi-client-1" / "result.json", multi)
            results.append(multi)
            execute("update-rollback-a-1", {
                "action": "rollback", "releaseId": release_a,
            }, release_a, release_a)
        else:
            repeat_count = 3 if topology == "t0" else 1
            for repetition in range(2, repeat_count + 1):
                extra_profile = (
                    project / "dist" / "r8-c-profiles"
                    / f"{browser}-{topology}-fresh-{repetition}"
                )
                if extra_profile.exists():
                    shutil.rmtree(extra_profile)
                extra_profile.mkdir(parents=True)
                execute(f"fresh-{repetition}", {"action": "fresh"}, release_a, release_a,
                        target_profile=extra_profile)
                shutil.rmtree(extra_profile, ignore_errors=True)
            for repetition in range(2, 4):
                execute(f"warm-{repetition}", {"action": "health"}, release_a, release_a)

            cold_profile = (
                project / "dist" / "r8-c-profiles" / f"{browser}-{topology}-offline-cold"
            )
            if cold_profile.exists():
                shutil.rmtree(cold_profile)
            cold_profile.mkdir(parents=True)
            execute("offline-cold-shell-prime", {"action": "prepare-shell"},
                    target_profile=cold_profile)
            stop_servers("before-offline-repetitions")
            for repetition in range(1, 4 if topology == "t0" else 2):
                execute(f"offline-ready-{repetition}", {"action": "offline"}, release_a, release_a)
            execute("offline-cold-no-release", {
                "action": "offline", "expect": "OFFLINE_RELEASE_UNAVAILABLE",
            }, target_profile=cold_profile)
            execute("offline-delete-entry", {
                "action": "delete-entry", "releaseId": release_a, "role": "app-module",
            }, release_a, release_a)
            execute("offline-entry-missing", {
                "action": "offline", "expect": "CACHED_ARTIFACT_INVALID",
            }, release_a, release_a)
            start_servers()
            execute("online-repair-a", {
                "action": "repair", "releaseId": release_a,
            }, release_a, release_a)
            execute("online-repair-health", {"action": "health"}, release_a, release_a)
            shutil.rmtree(cold_profile, ignore_errors=True)

            for repetition in range(1, 4 if topology == "t0" else 2):
                if topology == "t0" and repetition == 1:
                    multi = run_multi_client(
                        session_class, profile, app_origin, artifact_origin, topology,
                        releases["A"], releases["B"], root / "update-multi-client-1", timeout,
                    )
                    multi["caseId"] = "update-multi-client-1"
                    multi["gatePass"] = multi.get("pass") is True
                    write_json(root / "update-multi-client-1" / "result.json", multi)
                    results.append(multi)
                else:
                    execute(f"update-stage-b-{repetition}", {
                        "action": "stage", "slot": "B",
                    }, release_a, release_a)
                    execute(f"update-activate-b-{repetition}", {
                        "action": "activate", "slot": "B",
                    }, release_b, release_b)
                execute(f"update-rollback-a-{repetition}", {
                    "action": "rollback", "releaseId": release_a,
                }, release_a, release_a)

            for barrier, role in [
                ("manifest-verified", None),
                ("artifact-cached", "app-module"),
                ("metadata-before-ready", None),
            ]:
                execute(f"interrupt-{barrier}", {
                    "action": "stage", "slot": "B", "interruptAt": barrier,
                    "interruptRole": role, "expect": "R8_BARRIER_REACHED",
                }, release_a, release_a)
                execute(f"recover-{barrier}", {"action": "recover"}, release_a, release_a)

            execute("stage-b-activation-interrupt", {
                "action": "stage", "slot": "B",
            }, release_a, release_a)
            execute("interrupt-activation-prepared", {
                "action": "activate", "slot": "B", "interruptAt": "activation-prepared",
                "expect": "R8_BARRIER_REACHED",
            }, release_a, release_a)
            execute("recover-activation-prepared", {
                "action": "recover",
            }, release_a, release_a)

            execute("storage-write-failure", {
                "action": "stage", "slot": "B", "writeFailureRole": "app-module",
                "expect": "CACHE_WRITE_FAILED",
            }, release_a, release_a)
            metadata_recovery = execute(
                "metadata-corrupt", {"action": "corrupt-metadata"}, release_a, release_a,
            )
            metadata_recovery["gatePass"] = (
                metadata_recovery["gatePass"]
                and metadata_recovery.get("serviceWorker", {}).get("metadataRecovery")
                == "restored-valid-backup"
            )
            write_json(root / "metadata-corrupt" / "result.json", metadata_recovery)

            execute("stage-b-health-failure", {
                "action": "stage", "slot": "B",
            }, release_a, release_a)
            execute("activate-b-health-failure", {
                "action": "activate", "slot": "B", "health": "fail",
            }, release_a, release_a)

            execute("stage-b-integrity", {"action": "stage", "slot": "B"}, release_a, release_a)
            execute("corrupt-b-app", {
                "action": "corrupt-entry", "releaseId": release_b, "role": "app-module",
            }, release_a, release_a)
            execute("verify-corrupt-b", {
                "action": "verify-cache", "releaseId": release_b,
                "expect": "CACHED_ARTIFACT_INVALID",
            }, release_a, release_a)

            execute("restage-b", {"action": "stage", "slot": "B"}, release_a, release_a)
            execute("activate-b-for-retention", {
                "action": "activate", "slot": "B",
            }, release_b, release_b)
            execute("stage-c", {"action": "stage", "slot": "C"}, release_b, release_b)
            execute("activate-c", {"action": "activate", "slot": "C"}, release_c, release_c)
            execute("evict-bounded", {"action": "evict"}, release_c, release_c)
            execute("rollback-b", {
                "action": "rollback", "releaseId": release_b,
            }, release_b, release_b)
            stop_servers("before-rollback-offline")
            execute("rollback-offline", {"action": "offline"}, release_b, release_b)
            start_servers()

        summary = {
            "schemaVersion": 1,
            "release": "R8-C-service-worker",
            "browser": browser,
            "topology": topology,
            "suite": suite,
            "releaseIds": {"A": release_a, "B": release_b, "C": release_c},
            "cases": [{
                "caseId": item["caseId"],
                "result": str(root / item["caseId"] / "result.json"),
                "pass": item.get("pass") is True,
                "gatePass": item.get("gatePass") is True,
            } for item in results],
            "pass": bool(results) and all(item.get("gatePass") is True for item in results),
        }
        write_json(root / "summary.json", summary)
        write_json(root / "server-runs.json", server_runs)
        return summary
    finally:
        if processes:
            stop_servers("final-cleanup")


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--topology", choices=("all", "t0", "t1"), default="all")
    parser.add_argument("--suite", choices=("smoke", "multi-client", "full"), default="full")
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r8" / "service-worker",
    )
    args = parser.parse_args()
    release_set = load_json(project / "dist" / "r8c" / "release-set.json")
    output = args.evidence_root.resolve() / "browser" / args.browser / "summary.json"
    topologies = ("t0", "t1") if args.topology == "all" else (args.topology,)
    summaries = [
        run_topology(
            project, args.evidence_root.resolve(), args.browser, topology,
            args.suite, args.timeout, release_set,
        )
        for topology in topologies
    ]
    if args.topology != "all" and output.exists():
        previous = load_json(output)
        if (previous.get("browser") == args.browser
                and previous.get("suite") == args.suite):
            by_topology = {
                item["topology"]: item
                for item in previous.get("topologies", [])
                if item.get("topology") in {"t0", "t1"}
            }
            by_topology.update({item["topology"]: item for item in summaries})
            summaries = [by_topology[name] for name in ("t0", "t1") if name in by_topology]
    result = {
        "schemaVersion": 1,
        "release": "R8-C-service-worker",
        "browser": args.browser,
        "suite": args.suite,
        "topologies": summaries,
        "pass": all(item["pass"] for item in summaries),
    }
    write_json(output, result)
    print(json.dumps({
        "output": str(output),
        "browser": args.browser,
        "topologies": {item["topology"]: item["pass"] for item in summaries},
        "pass": result["pass"],
    }, ensure_ascii=False, indent=2))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
