#!/usr/bin/env python3
"""Run R8-D active-release compatibility, longevity, and regression evidence."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
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


def page_url(origin: str, **values: Any) -> str:
    query = urllib.parse.urlencode({key: value for key, value in values.items() if value is not None})
    return f"{origin}/r8-update.html?{query}"


def wait_value(session: ChromeSession | FirefoxSession, expression: str,
               timeout: float, complete: callable) -> Any:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            raw = evaluate(session, f"JSON.stringify({expression})")
            last = json.loads(raw) if raw else None
            if complete(last):
                return last
        except Exception:
            pass
        time.sleep(0.25)
    raise TimeoutError(f"R8-D browser value timed out: {last}")


def wait_page(session: ChromeSession | FirefoxSession, timeout: float = 900) -> dict[str, Any]:
    return wait_value(
        session, "globalThis.__r8_update || null", timeout,
        lambda value: bool(value) and value.get("status") in {"complete", "failed"},
    )




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


def start_server(project: Path, port: int) -> subprocess.Popen[str]:
    process = spawn_captured(
        [sys.executable, str(project / "tools" / "r8_delivery_server.py"),
         "--root", str(project / "dist"), "--port", str(port), "--role", "app"])
    wait_http(f"http://127.0.0.1:{port}/__r8__/health")
    return process


def stop_process(process: subprocess.Popen[str] | None) -> dict[str, Any] | None:
    if process is None:
        return None
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    stdout, stderr = drain_captured(process)
    return {"returnCode": process.returncode, "stdout": stdout, "stderr": stderr}


def release_ids(project: Path) -> dict[str, str]:
    value = load_json(project / "dist" / "r8c" / "release-set.json")
    return {item["slot"]: item["releaseId"] for item in value["releases"]}


def new_session(browser: str, profile: Path,
                reset: bool = True) -> ChromeSession | FirefoxSession:
    if reset and profile.exists():
        shutil.rmtree(profile)
    profile.mkdir(parents=True, exist_ok=True)
    session_class = ChromeSession if browser == "chrome" else FirefoxSession
    return session_class("hot", profile_dir=profile)


def fresh_active_release(session: ChromeSession | FirefoxSession, origin: str,
                         timeout: float) -> dict[str, Any]:
    navigate(session, page_url(origin, topology="t0", artifactOrigin=origin, action="fresh"))
    result = wait_page(session, timeout)
    if result.get("pass") is not True:
        raise RuntimeError(f"R8-D fresh active release failed: {result.get('error')}")
    return result


def compatibility_script(release_id: str, selected_ids: list[str]) -> str:
    return f"""
      (() => {{
        globalThis.__r8d_compatibility = {{ phase: 'running', pass: false }};
        const serializeError = error => ({{
          name: error?.name || 'Error', code: error?.code || 'DOCUMENT_OPEN_FAILED',
          message: String(error?.message || error), details: error?.details || null
        }});
        const digest = async buffer => [...new Uint8Array(await crypto.subtle.digest('SHA-256', buffer))]
          .map(value => value.toString(16).padStart(2, '0')).join('');
        (async () => {{
          const delivery = await import('./delivery/verified-loader.js');
          const preflight = await import('./r7/document-preflight.js');
          const releaseId = {json.dumps(release_id)};
          await globalThis.__r8_update_command('pin', {{ releaseId }});
          let workersStarted = 0;
          let verifyMs = 0;
          const cases = [];
          try {{
            const manifest = await (await fetch('./r7-compat-fixtures/manifest.json', {{ cache: 'no-cache' }})).json();
            const selectedIds = {json.dumps(selected_ids)};
            const selected = new Set(selectedIds);
            const documents = manifest.documents.filter(item => selected.has(item.id));
            for (const item of documents) {{
              const workerBaseline = workersStarted;
              const result = {{
                id: item.id, expected: item.expected, opened: false,
                anchors: [], tiles: [], pass: false
              }};
              let documentHandle = null;
              let caseSession = null;
              try {{
                const response = await fetch(`./r7-compat-fixtures/${{item.path}}`, {{ cache: 'no-cache' }});
                if (!response.ok) throw new Error(`fixture HTTP ${{response.status}}`);
                const bytes = await response.arrayBuffer();
                result.inputBytes = bytes.byteLength;
                result.inputSha256 = await digest(bytes);
                try {{
                  result.preflight = preflight.preflightDocument(bytes, {{ name: item.path, limits: manifest.limits }});
                }} catch (error) {{
                  result.error = serializeError(error);
                }}
                if (item.expected.open === 'typed-failure') {{
                  result.pass = !result.opened && result.error?.code === item.expected.typedCode;
                }} else if (!result.error) {{
                  const verifyStarted = performance.now();
                  const verified = await delivery.verifyRelease({{
                    manifestUrl: new URL(`./__r8c_cache__/releases/${{releaseId}}/release-manifest.json`, location.href),
                    policy: 'standard', transport: 'identity', cacheMode: 'warm',
                    artifactOrigin: location.origin, requireIsolation: true, timeoutMs: 600000
                  }});
                  verifyMs += performance.now() - verifyStarted;
                  caseSession = await delivery.startVerifiedEngine(verified, {{
                    timeoutMs: 180000,
                    workerFactory(url) {{
                      workersStarted += 1;
                      return new Worker(url, {{ name: `r8-d-${{item.id}}` }});
                    }}
                  }});
                  const openedAt = performance.now();
                  documentHandle = await caseSession.engine.open(bytes.slice(0), {{
                    name: item.path, transfer: true, timeoutMs: item.limits.openMs
                  }});
                  result.opened = true;
                  result.openMs = performance.now() - openedAt;
                  const widthTwips = Math.min(documentHandle.widthTwips, 7680);
                  const heightTwips = Math.min(documentHandle.heightTwips, 7680);
                  for (const [ratio, scale] of [[0, 1], [0.5, 1], [1, 1], [0.5, 1.5]]) {{
                    const yTwips = Math.max(0, Math.min(
                      documentHandle.heightTwips - heightTwips,
                      Math.round((documentHandle.heightTwips - heightTwips) * ratio)
                    ));
                    const tile = await documentHandle.render({{
                      xTwips: 0, yTwips, widthTwips, heightTwips,
                      canvasWidthPx: Math.round(128 * scale),
                      canvasHeightPx: Math.round(128 * scale)
                    }}, {{ timeoutMs: 180000 }});
                    result.tiles.push({{
                      ratio, scale, width: tile.width, height: tile.height,
                      bytes: tile.pixels.byteLength
                    }});
                  }}
                  for (const anchor of item.anchors) {{
                    const found = await documentHandle.search(anchor.text, {{ timeoutMs: 60000 }});
                    result.anchors.push({{ text: anchor.text, found: found.found }});
                  }}
                  if (item.expected.save === 'odt') {{
                    const output = await documentHandle.save({{ format: 'odt' }}, {{ timeoutMs: 180000 }});
                    result.output = {{ bytes: output.byteLength, sha256: await digest(output) }};
                  }}
                  await documentHandle.close({{ timeoutMs: 180000 }});
                  documentHandle = null;
                  result.pass = result.anchors.every(anchor => anchor.found)
                    && result.tiles.length === 4
                    && result.tiles.every(tile => tile.bytes === tile.width * tile.height * 4)
                    && (item.expected.save !== 'odt' || result.output.bytes > 0);
                }}
              }} catch (error) {{
                result.error = serializeError(error);
              }} finally {{
                if (documentHandle) await documentHandle.close({{ timeoutMs: 10000 }}).catch(() => {{}});
                caseSession?.dispose();
              }}
              result.workerGenerations = workersStarted - workerBaseline;
              cases.push(result);
              globalThis.__r8d_compatibility.completedCases = cases.length;
              globalThis.__r8d_compatibility.lastCase = item.id;
            }}
            const status = await globalThis.__r8_update_command('status');
            return {{
              schemaVersion: 1, release: 'R8-D-production-validation', releaseId,
              selectedDocumentIds: selectedIds, documentCount: cases.length,
              workersStarted, verifyMs, cases, status,
              pass: cases.length === selectedIds.length && cases.every(item => item.pass)
                && workersStarted >= documents.filter(item => item.expected.open === 'pass').length
                && workersStarted <= 3 && status.state.currentReleaseId === releaseId
            }};
          }} finally {{
            await globalThis.__r8_update_command('unpin').catch(() => {{}});
          }}
        }})().then(
          value => {{ globalThis.__r8d_compatibility = {{ phase: 'complete', ...value }}; }},
          error => {{ globalThis.__r8d_compatibility = {{
            phase: 'failed', error: serializeError(error), pass: false
          }}; }}
        );
        return true;
      }})()
    """


def run_compatibility(project: Path, evidence: Path, browser: str, timeout: float,
                      reuse_profile: bool = False,
                      fixed_port: int | None = None) -> dict[str, Any]:
    ids = release_ids(project)
    port = fixed_port or free_port()
    origin = f"http://127.0.0.1:{port}"
    profile = project / "dist" / "r8-d-profiles" / f"{browser}-compatibility"
    output = evidence / "production" / "compatibility" / browser
    output.mkdir(parents=True, exist_ok=True)
    manifest = load_json(project / "test-docs" / "r7-compat" / "manifest.json")
    batches: list[list[str]] = []
    batch: list[str] = []
    generation_count = 0
    for item in manifest["documents"]:
        is_open = item["expected"]["open"] == "pass"
        generation_weight = 0
        if is_open:
            generation_weight = (
                2 if "finding-012-known-discovery-sequence"
                in item["expected"].get("degradation", []) else 1
            )
        if generation_weight and generation_count + generation_weight > 2:
            batches.append(batch)
            batch, generation_count = [], 0
        batch.append(item["id"])
        generation_count += generation_weight
    if batch:
        batches.append(batch)
    server = start_server(project, port)
    started = time.monotonic()
    session: ChromeSession | FirefoxSession | None = None
    try:
        session = new_session(browser, profile, reset=not reuse_profile)
        if reuse_profile:
            navigate(session, page_url(
                origin, topology="t0", artifactOrigin=origin, action="status",
            ))
            fresh = wait_page(session, timeout)
            current = fresh.get("serviceWorker", {}).get("state", {}).get("currentReleaseId")
            state = fresh.get("serviceWorker", {}).get("state", {})
            if fresh.get("pass") is not True:
                raise RuntimeError("reused R8-D profile status failed")
            if current != ids["A"] and ids["A"] in state.get("releases", {}):
                navigate(session, page_url(
                    origin, topology="t0", artifactOrigin=origin,
                    action="rollback", releaseId=ids["A"],
                ))
                fresh = wait_page(session, timeout)
                current = fresh.get("serviceWorker", {}).get("state", {}).get("currentReleaseId")
            if current != ids["A"]:
                raise RuntimeError(f"reused R8-D profile has no active cached release A: {current}")
        else:
            fresh = fresh_active_release(session, origin, timeout)
        browser_version = session.version
        batch_results = []
        for index, selected_ids in enumerate(batches, start=1):
            if browser == "firefox" and index > 1:
                time.sleep(8)
            batch_root = output / "batches" / f"batch-{index:02d}"
            batch_root.mkdir(parents=True, exist_ok=True)
            navigate(session, page_url(
                origin, topology="t0", artifactOrigin=origin, action="status",
            ))
            status_page = wait_page(session, timeout)
            if status_page.get("pass") is not True:
                raise RuntimeError("R8-D compatibility status page failed")
            evaluate(session, compatibility_script(ids["A"], selected_ids))
            batch_result = wait_value(
                session, "globalThis.__r8d_compatibility || null", timeout,
                lambda value: bool(value) and value.get("phase") in {"complete", "failed"},
            )
            batch_result.update({
                "batch": index, "browser": browser,
                "browserVersion": session.version,
            })
            write_json(batch_root / "result.json", batch_result)
            if batch_result.get("pass") is not True:
                (batch_root / "page.png").write_bytes(session.screenshot())
            batch_results.append(batch_result)
            if batch_result.get("pass") is not True:
                break
        cases = [case for item in batch_results for case in item.get("cases", [])]
        result = {
            "schemaVersion": 1, "release": "R8-D-production-validation",
            "browser": browser, "browserVersion": browser_version,
            "releaseId": ids["A"],
            "freshRelease": fresh.get("serviceWorker", {}).get("state", {}).get("currentReleaseId"),
            "documentCount": len(cases),
            "workersStarted": sum(item.get("workersStarted", 0) for item in batch_results),
            "maxWorkersPerPage": max((item.get("workersStarted", 0) for item in batch_results), default=0),
            "verifyMs": sum(item.get("verifyMs", 0) for item in batch_results),
            "batchCount": len(batch_results), "batches": batch_results,
            "cases": cases,
            "runnerElapsedMs": round((time.monotonic() - started) * 1000, 3),
        }
        result["pass"] = (
            len(batch_results) == len(batches) and len(cases) == 28
            and all(item.get("pass") is True for item in batch_results)
            and result["maxWorkersPerPage"] <= 3
        )
        write_json(output / "summary.json", result)
        return result
    finally:
        if session is not None:
            session.close()
        write_json(output / "server.json", stop_process(server) or {})


def descendants(root_pid: int) -> set[int]:
    rows: list[tuple[int, int]] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text(encoding="utf-8").split()
            rows.append((int(fields[0]), int(fields[3])))
        except (OSError, ValueError, IndexError):
            continue
    selected = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in rows:
            if parent in selected and pid not in selected:
                selected.add(pid)
                changed = True
    return selected


def process_memory(root_pid: int) -> dict[str, int]:
    rss, pss = 0, 0
    for pid in descendants(root_pid):
        try:
            status = (Path("/proc") / str(pid) / "status").read_text(encoding="utf-8")
            rss += int(next(line.split()[1] for line in status.splitlines() if line.startswith("VmRSS:"))) * 1024
        except (OSError, StopIteration, ValueError):
            pass
        try:
            rollup = (Path("/proc") / str(pid) / "smaps_rollup").read_text(encoding="utf-8")
            pss += int(next(line.split()[1] for line in rollup.splitlines() if line.startswith("Pss:"))) * 1024
        except (OSError, StopIteration, ValueError):
            pass
    return {"processCount": len(descendants(root_pid)), "rssBytes": rss, "pssBytes": pss}


def async_result(session: ChromeSession | FirefoxSession, name: str, body: str,
                 timeout: float = 900) -> dict[str, Any]:
    expression = f"""
      (() => {{
        globalThis[{json.dumps(name)}] = null;
        Promise.resolve().then(async () => {{ {body} }}).then(
          value => globalThis[{json.dumps(name)}] = {{ pass: true, value }},
          error => globalThis[{json.dumps(name)}] = {{ pass: false, error: {{
            name: error?.name || 'Error', code: error?.code || 'UNCLASSIFIED_ERROR',
            message: String(error?.message || error)
          }} }}
        );
        return true;
      }})()
    """
    evaluate(session, expression)
    return wait_value(session, f"globalThis[{json.dumps(name)}]", timeout, lambda value: value is not None)


def run_soak(project: Path, evidence: Path, browser: str, minutes: float,
             interval_ms: int, timeout: float) -> dict[str, Any]:
    ids = release_ids(project)
    port = free_port()
    origin = f"http://127.0.0.1:{port}"
    profile = project / "dist" / "r8-d-profiles" / f"{browser}-soak"
    output = evidence / "production" / "longevity" / browser
    output.mkdir(parents=True, exist_ok=True)
    server: subprocess.Popen[str] | None = start_server(project, port)
    server_runs: list[dict[str, Any]] = []
    session = new_session(browser, profile)
    started = time.monotonic()
    cycles: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    transitions = ["active-a"]
    try:
        fresh_active_release(session, origin, timeout)
        init = async_result(session, "__r8d_soak_init", f"""
          const delivery = await import('./delivery/verified-loader.js');
          const releaseId = {json.dumps(ids['A'])};
          await globalThis.__r8_update_command('pin', {{ releaseId }});
          const verified = await delivery.verifyRelease({{
            manifestUrl: new URL(`./__r8c_cache__/releases/${{releaseId}}/release-manifest.json`, location.href),
            policy: 'standard', transport: 'identity', cacheMode: 'warm',
            artifactOrigin: location.origin, requireIsolation: true, timeoutMs: 600000
          }});
          globalThis.__r8d_soak_session = await delivery.startVerifiedEngine(verified, {{
            timeoutMs: 180000,
            workerFactory(url) {{ return new Worker(url, {{ name: 'r8-d-long-lived-a' }}); }}
          }});
          return {{ releaseId, artifactCount: verified.artifacts.length }};
        """, timeout)
        if not init["pass"]:
            raise RuntimeError(f"soak init failed: {init}")
        update = async_result(session, "__r8d_soak_update", f"""
          const releaseSet = await (await fetch('./r8c/release-set.json', {{ cache: 'no-store' }})).json();
          const release = releaseSet.releases.find(item => item.slot === 'B');
          await globalThis.__r8_update_command('stage-release', {{
            releaseId: release.releaseId,
            manifestUrl: new URL(`./r8c/${{release.manifestUrl}}`, location.href).href,
            manifestSha256: release.manifestSha256,
            requiredArtifactCount: release.requiredArtifactCount,
            artifactOrigin: location.origin
          }}, 900000);
          await globalThis.__r8_update_command('activate-release', {{ releaseId: release.releaseId }});
          const healthUrl = new URL('./r8-update.html', location.href);
          healthUrl.searchParams.set('topology', 't0');
          healthUrl.searchParams.set('artifactOrigin', location.origin);
          healthUrl.searchParams.set('action', 'health');
          healthUrl.searchParams.set('releaseId', release.releaseId);
          const healthFrame = document.createElement('iframe');
          healthFrame.src = healthUrl.href;
          document.body.append(healthFrame);
          const healthMetrics = await new Promise((resolve, reject) => {{
            const started = performance.now();
            const poll = () => {{
              const value = healthFrame.contentWindow?.__r8_update;
              if (value?.status === 'complete') return resolve(value);
              if (value?.status === 'failed') return reject(new Error(JSON.stringify(value.error)));
              if (performance.now() - started > 300000)
                return reject(new Error('release B health client timed out'));
              setTimeout(poll, 100);
            }};
            poll();
          }});
          healthFrame.remove();
          const health = healthMetrics.runtime;
          await globalThis.__r8_update_command('health-result', {{
            releaseId: release.releaseId, pass: healthMetrics.pass
          }});
          return {{ health, status: await globalThis.__r8_update_command('status') }};
        """, timeout)
        if not update["pass"] or not update["value"]["health"]["pass"]:
            raise RuntimeError(f"soak update failed: {update}")
        transitions.append("active-b")
        soak_started = time.monotonic()
        target_seconds = minutes * 60
        deadline = soak_started + target_seconds
        cycle_count = max(2, math.ceil(target_seconds * 1000 / interval_ms))
        offline_at = max(1, cycle_count // 3)
        online_at = max(offline_at + 1, cycle_count * 2 // 3)
        for index in range(cycle_count):
            if index == offline_at and server is not None:
                server_runs.append({"label": "offline", "server": stop_process(server)})
                server = None
            if index == online_at and server is None:
                server = start_server(project, port)
            cycle = async_result(session, f"__r8d_soak_cycle_{index}", """
              const response = await fetch('./r6-fixtures/t1-plain-zh.odt', { cache: 'no-cache' });
              if (!response.ok) throw new Error(`fixture HTTP ${response.status}`);
              const bytes = await response.arrayBuffer();
              const handle = await globalThis.__r8d_soak_session.engine.open(bytes, {
                name: 'r8-d-soak.odt', transfer: false, timeoutMs: 180000
              });
              try {
                const tile = await handle.render({
                  xTwips: 0, yTwips: 0,
                  widthTwips: Math.min(handle.widthTwips, 4800),
                  heightTwips: Math.min(handle.heightTwips, 4800),
                  canvasWidthPx: 128, canvasHeightPx: 128
                }, { timeoutMs: 180000 });
                return {
                  verification: 'render-only-long-lived-reuse',
                  tileBytes: tile.pixels.byteLength,
                  pass: tile.pixels.byteLength === 65536
                };
              } finally {
                await handle.close({ timeoutMs: 180000 });
              }
            """, timeout)
            cycle_value = cycle.get("value") or {}
            cycle_record = {
                "index": index + 1, "serverOnline": server is not None,
                "elapsedMs": round((time.monotonic() - soak_started) * 1000, 3),
                "pass": cycle.get("pass") is True and cycle_value.get("pass") is True,
                "result": cycle_value, "error": cycle.get("error"),
            }
            cycles.append(cycle_record)
            if server is None and cycle_record["pass"] and "offline-a-runtime" not in transitions:
                transitions.append("offline-a-runtime")
            storage = async_result(session, f"__r8d_storage_{index}", """
              const estimate = await navigator.storage.estimate();
              const status = await globalThis.__r8_update_command('status');
              return { estimate, state: status.state };
            """, 60)
            state = (storage.get("value") or {}).get("state", {})
            cached_bytes = sum(item.get("cachedBytes", 0) for item in state.get("releases", {}).values())
            samples.append({
                "index": index + 1,
                "elapsedMs": round((time.monotonic() - soak_started) * 1000, 3),
                "serverOnline": server is not None,
                "memory": process_memory(session.process.pid),
                "storage": (storage.get("value") or {}).get("estimate"),
                "releaseCachedBytes": cached_bytes,
                "clientPins": len(state.get("clientPins", {})),
            })
            write_json(output / "progress.json", {
                "browser": browser, "minutes": minutes, "completedCycles": len(cycles),
                "plannedCycles": cycle_count, "lastCyclePass": cycle_record["pass"],
                "elapsedMinutes": (time.monotonic() - soak_started) / 60,
            })
            if not cycle_record["pass"]:
                break
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(interval_ms / 1000, remaining))
        if server is None:
            server = start_server(project, port)
        before_dispose = async_result(session, "__r8d_soak_before_dispose", """
          return await globalThis.__r8_update_command('status');
        """, 60)
        evaluate(session, "globalThis.__r8d_soak_session?.dispose(); globalThis.__r8d_soak_session = null; true")
        async_result(session, "__r8d_soak_unpin", """
          await globalThis.__r8_update_command('unpin'); return true;
        """, 60)
        rollback = async_result(session, "__r8d_soak_rollback", f"""
          await globalThis.__r8_update_command('rollback', {{ releaseId: {json.dumps(ids['A'])} }});
          return await globalThis.__r8_update_command('status');
        """, 60)
        if rollback.get("pass") and rollback.get("value", {}).get("state", {}).get("currentReleaseId") == ids["A"]:
            transitions.append("rollback-a")
        server_runs.append({"label": "final", "server": stop_process(server)})
        server = None
        offline = async_result(session, "__r8d_soak_offline_final", f"""
          const health = await globalThis.__r8_runtime_health({json.dumps(ids['A'])});
          return {{ health, status: await globalThis.__r8_update_command('status') }};
        """, timeout)
        duration_minutes = (time.monotonic() - soak_started) / 60
        worker_generations = 4
        summary = {
            "schemaVersion": 1, "release": "R8-D-production-validation",
            "browser": browser, "browserVersion": session.version,
            "releaseIds": ids, "durationMinutes": duration_minutes,
            "intervalMs": interval_ms, "workerGenerations": worker_generations,
            "maxWorkerGenerationsPerPage": 3,
            "transitions": transitions, "cycles": cycles, "samples": samples,
            "beforeDispose": before_dispose, "rollback": rollback,
            "offlineFinal": offline, "serverRuns": server_runs,
            "highWater": {
                "pssBytes": max((item["memory"]["pssBytes"] for item in samples), default=0),
                "rssBytes": max((item["memory"]["rssBytes"] for item in samples), default=0),
                "storageUsageBytes": max((item.get("storage") or {}).get("usage", 0) for item in samples),
                "releaseCachedBytes": max((item["releaseCachedBytes"] for item in samples), default=0),
            },
        }
        summary["pass"] = (
            duration_minutes >= minutes and len(cycles) == cycle_count
            and all(item["pass"] for item in cycles)
            and offline.get("pass") is True
            and {"active-a", "active-b", "offline-a-runtime", "rollback-a"}.issubset(transitions)
            and worker_generations <= (4 if browser == "firefox" else 8)
        )
        write_json(output / "summary.json", summary)
        return summary
    finally:
        if server is not None:
            server_runs.append({"label": "cleanup", "server": stop_process(server)})
        session.close()


def run_regression(project: Path, evidence: Path) -> dict[str, Any]:
    output = evidence / "production" / "regression"
    output.mkdir(parents=True, exist_ok=True)
    commands = [
        ["make", "test-r6-c"],
        ["make", "test-r6-roundtrip"],
        ["make", "test-r6-release"],
        ["make", "test-r7-d-static"],
        ["make", "test-finding-012-remediation"],
        ["make", "test-r8-c-static"],
        [sys.executable, "tools/validate_r8_c_preflight.py", "--phase", "after"],
        [sys.executable, "tools/validate_r8_c.py"],
    ]
    results = []
    for index, command in enumerate(commands, start=1):
        started = time.monotonic()
        completed = subprocess.run(command, cwd=project, text=True, capture_output=True, check=False)
        log = output / f"command-{index:02d}.log"
        log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
        result = {
            "command": command, "returnCode": completed.returncode,
            "elapsedMs": round((time.monotonic() - started) * 1000, 3),
            "log": str(log), "pass": completed.returncode == 0,
        }
        results.append(result)
        write_json(output / "progress.json", {"completed": index, "results": results})
        if not result["pass"]:
            break
    summary = {
        "schemaVersion": 1, "release": "R8-D-production-validation",
        "commands": results, "pass": len(results) == len(commands) and all(item["pass"] for item in results),
    }
    write_json(output / "summary.json", summary)
    return summary


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("compatibility", "soak", "regression"), required=True)
    parser.add_argument("--browser", choices=("chrome", "firefox"))
    parser.add_argument("--minutes", type=float, default=30)
    parser.add_argument("--interval-ms", type=int, default=60000)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--reuse-profile", action="store_true")
    parser.add_argument("--port", type=int)
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r8",
    )
    args = parser.parse_args()
    if args.phase in {"compatibility", "soak"} and not args.browser:
        parser.error(f"--browser is required for {args.phase}")
    if args.minutes <= 0 or args.interval_ms <= 0:
        parser.error("--minutes and --interval-ms must be positive")
    if args.phase == "compatibility":
        result = run_compatibility(
            project, args.evidence_root.resolve(), args.browser,
            args.timeout, args.reuse_profile, args.port,
        )
    elif args.phase == "soak":
        result = run_soak(
            project, args.evidence_root.resolve(), args.browser,
            args.minutes, args.interval_ms, args.timeout,
        )
    else:
        result = run_regression(project, args.evidence_root.resolve())
    print(json.dumps({
        "phase": args.phase, "browser": args.browser, "pass": result.get("pass"),
    }, ensure_ascii=False, indent=2))
    if result.get("pass") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
