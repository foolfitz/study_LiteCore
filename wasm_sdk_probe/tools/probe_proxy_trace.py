#!/usr/bin/env python3
"""Finding 037: distinguish a stuck main-thread proxy from an intra-WASM wait.

This drives pc-plain and pc-image in one browser session against the JS-only
e2-proxy-trace profile.  The primary readout comes from the still-responsive
SDK runtime worker; pthread-side proxy issue records were forwarded there
before a synchronous proxy could block.  Worker Debugger.pause is a secondary,
best-effort readout and can never prevent the primary trace from being saved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import uuid
from collections import Counter
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_wedge_thread_state import (  # noqa: E402
    BrowserSession,
    wait_for_checkpoint,
    wait_for_the_hang,
)
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402


PROJECT = Path(__file__).resolve().parent.parent
EXPECTED_WASM_SHA256 = (
    "ee185b3d5972cac761acbcbc19cbafe916962788822e7cbae87bfe771d62a566"
)
DEFAULT_OUTPUT = (
    PROJECT.parent / "findings" / "evidence" / "sdk-e2" / "discovery"
    / "proxy-trace" / "chrome" / "result.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def worker_sessions(browser: BrowserSession) -> list[dict]:
    return [
        attached for attached in browser.attached_sessions()
        if attached["target"].get("type") in (
            "worker", "shared_worker", "service_worker"
        )
    ]


def read_proxy_trace(browser: BrowserSession) -> dict:
    """Read the combined trace through the SDK worker's snapshot export."""
    attempts = []
    for attached in worker_sessions(browser):
        target = attached["target"]
        url = target.get("url", "")
        if not url.endswith("/sdk-worker.js"):
            continue
        sid = attached["sessionId"]
        try:
            response = browser.call(
                "Runtime.evaluate",
                {
                    "expression": (
                        "typeof self.__sdkProxyTraceSnapshot === 'function'"
                        " ? self.__sdkProxyTraceSnapshot()"
                        " : ({error:'snapshot-export-missing'})"
                    ),
                    "returnByValue": True,
                    "awaitPromise": True,
                },
                session=sid,
                timeout=30,
            )
            if response.get("exceptionDetails"):
                raise RuntimeError(str(response["exceptionDetails"]))
            value = (response.get("result") or {}).get("value")
            if not isinstance(value, dict):
                raise RuntimeError(f"snapshot returned {type(value).__name__}")
            if value.get("error"):
                raise RuntimeError(str(value["error"]))
            value["sourceWorkerUrl"] = url
            value["sourceSessionId"] = sid
            return value
        except Exception as error:
            attempts.append({"url": url[-100:], "error": str(error)[:300]})
    raise RuntimeError(f"no readable SDK proxy trace worker: {attempts}")


def trace_tail(snapshot: dict, limit: int) -> dict:
    entries = snapshot.get("entries") or []
    tail = entries[-limit:]
    return {
        "capturedAtMs": snapshot.get("capturedAt"),
        "timeOriginMs": snapshot.get("timeOrigin"),
        "sourceWorkerUrl": snapshot.get("sourceWorkerUrl"),
        "traceLimit": snapshot.get("limit"),
        "dropped": snapshot.get("dropped", 0),
        "totalRetainedEntries": len(entries),
        "capturedEntries": len(tail),
        "omittedBeforeTail": max(0, len(entries) - len(tail)),
        "phaseCountsRetained": dict(Counter(
            str(entry.get("phase")) for entry in entries
        )),
        "entries": tail,
    }


def absolute_time(entry: dict) -> float | None:
    origin = entry.get("timeOrigin")
    stamp = entry.get("t")
    if isinstance(origin, (int, float)) and isinstance(stamp, (int, float)):
        return float(origin) + float(stamp)
    return None


def find_matching_exit(entries: list[dict], enter: dict, exit_phase: str) -> dict | None:
    for candidate in entries:
        if candidate.get("phase") != exit_phase:
            continue
        if candidate.get("context") != enter.get("context"):
            continue
        if candidate.get("thread") != enter.get("thread"):
            continue
        if candidate.get("callId") != enter.get("callId"):
            continue
        enter_time = absolute_time(enter)
        exit_time = absolute_time(candidate)
        if enter_time is None or exit_time is None or exit_time >= enter_time:
            return candidate
    return None


def summarise_call(entry: dict | None, matching_exit: dict | None = None) -> dict | None:
    if entry is None:
        return None
    summary = {
        key: entry.get(key) for key in (
            "t", "timeOrigin", "phase", "index", "argCount", "sync",
            "callId", "context", "thread", "callingThread", "emAsmAddr",
        ) if key in entry
    }
    summary["absoluteTimestampMs"] = absolute_time(entry)
    if matching_exit is not None:
        summary["matchingExitFollowed"] = True
        summary["matchingExitTimestampMs"] = absolute_time(matching_exit)
        summary["matchingExitCompleted"] = matching_exit.get("completed")
    else:
        summary["matchingExitFollowed"] = False
    return summary


def pause_workers(browser: BrowserSession, label: str) -> dict:
    """Best-effort Debugger.pause with an unconditional resume per worker."""
    result = {"label": label, "workers": [], "pausedEventArrived": False}
    for attached in worker_sessions(browser):
        sid = attached["sessionId"]
        target = attached["target"]
        record = {
            "type": target.get("type"),
            "url": target.get("url", "")[-100:],
            "sessionId": sid,
            "pauseRequested": False,
            "pausedEventArrived": False,
            "callFrames": [],
        }
        event_start = len(browser.events)
        try:
            browser.call("Debugger.enable", session=sid, timeout=10)
            record["pauseRequested"] = True
            browser.call("Debugger.pause", session=sid, timeout=10)
            browser.drain(0.4)
            paused = [
                event for event in browser.events[event_start:]
                if event.get("sessionId") == sid
                and event.get("method") == "Debugger.paused"
            ]
            if paused:
                event = paused[-1]
                record["pausedEventArrived"] = True
                record["reason"] = (event.get("params") or {}).get("reason")
                for frame in (event.get("params") or {}).get("callFrames", []):
                    location = frame.get("location") or {}
                    record["callFrames"].append({
                        "callFrameId": frame.get("callFrameId"),
                        "functionName": frame.get("functionName"),
                        "url": frame.get("url"),
                        "scriptId": location.get("scriptId"),
                        "lineNumber": location.get("lineNumber"),
                        "columnNumber": location.get("columnNumber"),
                    })
        except Exception as error:
            record["error"] = str(error)[:500]
        finally:
            try:
                browser.call("Debugger.resume", session=sid, timeout=10)
                record["resumeRequested"] = True
            except Exception as error:
                record["resumeRequested"] = False
                record["resumeError"] = str(error)[:500]
        result["workers"].append(record)
    result["pausedEventArrived"] = any(
        worker["pausedEventArrived"] for worker in result["workers"]
    )
    return result


def attach_workers(browser: BrowserSession) -> tuple[list[dict], list[dict]]:
    targets = browser.call("Target.getTargets")["targetInfos"]
    page = next(target for target in targets if target["type"] == "page")
    page_session = browser.call(
        "Target.attachToTarget",
        {"targetId": page["targetId"], "flatten": True},
    )["sessionId"]
    auto_attach = {
        "autoAttach": True,
        "waitForDebuggerOnStart": False,
        "flatten": True,
    }
    browser.call("Target.setAutoAttach", auto_attach, session=page_session)
    browser.drain(2.0)
    for _ in range(2):
        for attached in browser.attached_sessions():
            try:
                browser.call(
                    "Target.setAutoAttach", auto_attach,
                    session=attached["sessionId"], timeout=10,
                )
            except Exception:
                pass
        browser.drain(1.5)
    target_summary = [
        {"type": target["type"], "url": target["url"][-100:]}
        for target in targets
    ]
    attached_summary = [
        {
            "type": attached["target"].get("type"),
            "url": attached["target"].get("url", "")[-100:],
            "sessionId": attached["sessionId"],
        }
        for attached in browser.attached_sessions()
    ]
    return target_summary, attached_summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="paragraph-content")
    parser.add_argument("--cases", default="pc-plain,pc-image")
    parser.add_argument("--profile", default="e2-proxy-trace")
    parser.add_argument("--fixture-mode", default="wedge-trace")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--tail-limit", type=int, default=2000)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.tail_limit < 1:
        raise SystemExit("--tail-limit must be positive")

    profile = PROJECT / "dist" / "profiles" / args.profile
    wasm_hash = sha256(profile / "probe.wasm")
    manifest = json.loads(
        (profile / "sdk-manifest.json").read_text(encoding="utf-8")
    )
    manifest_hash = manifest.get("diagnostic", {}).get("wasmSha256")
    if wasm_hash != EXPECTED_WASM_SHA256 or manifest_hash != wasm_hash:
        raise SystemExit(
            f"refusing run: profile WASM identity mismatch "
            f"file={wasm_hash} manifest={manifest_hash}"
        )

    run_id = str(uuid.uuid4())
    result: dict = {
        "schemaVersion": 1,
        "release": "finding-037-proxy-trace",
        "runId": run_id,
        "sameBrowserSession": True,
        "requested": {
            "fixture": args.fixture,
            "mode": args.fixture_mode,
            "cases": args.cases,
            "profileOverride": args.profile,
        },
        "artifact": {
            "profile": args.profile,
            "probeWasmSha256": wasm_hash,
            "manifestWasmSha256": manifest_hash,
            "expectedWasmSha256": EXPECTED_WASM_SHA256,
            "wasmIdentityVerified": True,
            "loaderSha256": sha256(profile / "probe.js"),
            "manifestLoaderSha256": manifest["diagnostic"].get("loaderSha256"),
            "workerSha256": sha256(profile / "sdk-worker.js"),
            "manifestWorkerSha256": manifest["diagnostic"].get("workerSha256"),
        },
    }

    server_port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(server_port)],
        cwd=PROJECT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    session = browser = None
    control_snapshot: dict | None = None
    hang_snapshot: dict | None = None
    try:
        base = f"http://127.0.0.1:{server_port}/e2-format-discovery.html"
        wait_page(base)
        session = ChromeSession("cold")
        result["browserSessionBaseUrl"] = session.base_url
        session.navigate(
            f"{base}?fixture={args.fixture}&mode={args.fixture_mode}"
            f"&cases={args.cases}&profileOverride={args.profile}"
        )

        browser = BrowserSession(session.base_url)
        result["targets"], result["attachedSessions"] = attach_workers(browser)

        control_reached = wait_for_checkpoint(
            session, "readback-caret-only", args.timeout
        )
        result["controlReached"] = control_reached
        if not control_reached:
            raise RuntimeError("readback-caret-only control checkpoint not reached")
        control_snapshot = read_proxy_trace(browser)
        result["control"] = {
            "case": "pc-plain",
            "checkpoint": "readback-caret-only",
            "proxyTrace": trace_tail(control_snapshot, args.tail_limit),
        }
        # The pause control happens only after the primary control trace exists.
        try:
            result["pauseControl"] = pause_workers(browser, "engine-alive")
        except Exception as error:
            result["pauseControl"] = {"error": str(error)[:500]}

        hang_observation = wait_for_the_hang(session, args.timeout)
        page_clock = evaluate(session, "({now:performance.now(), origin:performance.timeOrigin})")
        last_callback = hang_observation.get("lastCallback")
        quiet_start_absolute = None
        if isinstance(last_callback, dict) and isinstance(last_callback.get("atMs"), (int, float)):
            quiet_start_absolute = (
                float(page_clock["origin"]) + float(last_callback["atMs"])
            )
        hang_snapshot = read_proxy_trace(browser)
        hang_tail = trace_tail(hang_snapshot, args.tail_limit)
        result["hang"] = {
            "case": "pc-image",
            "quietSeconds": hang_observation.get("quietSeconds"),
            "lastLokCallback": last_callback,
            "callbackTraceEntries": hang_observation.get("traceEntries"),
            "phase": hang_observation.get("phase"),
            "timedOutWaitingForQuiet": hang_observation.get(
                "timedOutWaitingForQuiet", False
            ),
            "quietWindowStartAbsoluteMs": quiet_start_absolute,
            "capturedPageNowMs": page_clock.get("now"),
            "capturedPageTimeOriginMs": page_clock.get("origin"),
            "proxyTrace": hang_tail,
        }

        entries = hang_snapshot.get("entries") or []
        receive_enters = [
            entry for entry in entries if entry.get("phase") == "receive-enter"
        ]
        proxy_enters = [
            entry for entry in entries if entry.get("phase") == "proxy-enter"
        ]
        if quiet_start_absolute is None:
            receives_during = []
            issues_during = []
            receives_before = receive_enters
        else:
            receives_during = [
                entry for entry in receive_enters
                if absolute_time(entry) is not None
                and absolute_time(entry) >= quiet_start_absolute
            ]
            issues_during = [
                entry for entry in proxy_enters
                if absolute_time(entry) is not None
                and absolute_time(entry) >= quiet_start_absolute
            ]
            receives_before = [
                entry for entry in receive_enters
                if absolute_time(entry) is not None
                and absolute_time(entry) < quiet_start_absolute
            ]

        last_receive = max(
            receives_before,
            key=lambda entry: absolute_time(entry) or float("-inf"),
            default=None,
        )
        last_receive_exit = (
            find_matching_exit(entries, last_receive, "receive-exit")
            if last_receive else None
        )
        result["lastProxiedCallBeforeHang"] = summarise_call(
            last_receive, last_receive_exit
        )
        result["proxiedCallsDuringHang"] = {
            "definition": "receive-enter in the LOK-callback quiet window",
            "count": len(receives_during),
            "entries": [summarise_call(entry) for entry in receives_during],
        }
        result["proxyIssuesDuringHang"] = {
            "definition": (
                "pthread proxy-enter forwarded before the synchronous proxy "
                "wait, in the LOK-callback quiet window"
            ),
            "count": len(issues_during),
            "entries": [summarise_call(entry) for entry in issues_during],
        }

        pending_proxy_issues = []
        for entry in proxy_enters:
            matching = find_matching_exit(entries, entry, "proxy-exit")
            if matching is None:
                pending_proxy_issues.append(summarise_call(entry))
        pending_receives = []
        for entry in receive_enters:
            matching = find_matching_exit(entries, entry, "receive-exit")
            if matching is None:
                pending_receives.append(summarise_call(entry))
        result["unmatchedProxyIssuesAtCapture"] = pending_proxy_issues
        result["unmatchedReceivesAtCapture"] = pending_receives

        # The pause readout is strictly opportunistic and follows the saved-in-
        # memory primary hang snapshot.
        try:
            result["pauseDuringHang"] = pause_workers(browser, "callback-quiet")
        except Exception as error:
            result["pauseDuringHang"] = {"error": str(error)[:500]}
    except Exception as error:
        result["fatalError"] = {
            "type": type(error).__name__,
            "message": str(error),
        }
    finally:
        if browser is not None:
            browser.close()
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    control_entries = (
        ((result.get("control") or {}).get("proxyTrace") or {}).get("entries")
        or []
    )
    result["hookFired"] = bool(control_entries)
    result["proxyHookFiredInControl"] = any(
        entry.get("phase") in ("proxy-enter", "receive-enter")
        for entry in control_entries
    )
    if not result["hookFired"]:
        named_outcome = "instrument-broken-control-empty"
    elif result.get("fatalError"):
        named_outcome = "instrument-run-failed-after-control"
    elif (result.get("proxyIssuesDuringHang") or {}).get("count", 0) > 0:
        named_outcome = "proxied-call-issued-during-hang"
    elif (result.get("proxiedCallsDuringHang") or {}).get("count", 0) > 0:
        named_outcome = "proxied-call-received-during-hang"
    elif not result["proxyHookFiredInControl"]:
        # The control column is non-empty, but everything in it is mailbox
        # activity, which fires whether or not the proxyToMainThread wrapper
        # took.  "No proxied call during the hang" would then be exactly what a
        # wrapper that never installed also produces -- one reading for two
        # different worlds, which is not a reading.  H1 stays open here.
        named_outcome = "proxy-hook-unproven-only-mailbox-in-control"
    else:
        named_outcome = "hook-fired-no-proxied-call-during-hang"
    result["namedOutcome"] = named_outcome
    result["outcomeDistinguishesEmptyHangFromBrokenHook"] = True
    result["outcomeSupportsRulingOutProxying"] = (
        named_outcome == "hook-fired-no-proxied-call-during-hang")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "runId": run_id,
        "wasmSha256": wasm_hash,
        "hookFired": result["hookFired"],
        "proxyHookFiredInControl": result["proxyHookFiredInControl"],
        "namedOutcome": named_outcome,
        "lastProxiedCallBeforeHang": result.get("lastProxiedCallBeforeHang"),
        "proxiedCallsDuringHang": result.get("proxiedCallsDuringHang"),
        "proxyIssuesDuringHang": result.get("proxyIssuesDuringHang"),
        "hang": {
            key: (result.get("hang") or {}).get(key)
            for key in ("quietSeconds", "lastLokCallback", "phase")
        },
        "pauseControlWorked": (result.get("pauseControl") or {}).get(
            "pausedEventArrived"
        ),
        "pauseDuringHangWorked": (result.get("pauseDuringHang") or {}).get(
            "pausedEventArrived"
        ),
        "fatalError": result.get("fatalError"),
    }, indent=2, ensure_ascii=False))
    if result.get("fatalError") or not result["hookFired"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
