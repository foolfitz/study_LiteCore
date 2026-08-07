#!/usr/bin/env python3
"""Run R6-C scenarios with two independent browser contexts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from run_browser_probe import ChromeSession, FirefoxSession, browser_state, free_port


def http_json(method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, method=method, data=data,
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def http_bytes(url: str) -> tuple[bytes, dict[str, str]]:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read(), {key.lower(): value for key, value in response.headers.items()}


def wait_service(url: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            http_json("GET", f"{url}/api/documents/r6-reference-document")
            return
        except Exception as caught:
            error = caught
            time.sleep(0.2)
    raise RuntimeError(f"reference service was not ready: {error}")


def session_class(browser: str):
    return ChromeSession if browser == "chrome" else FirefoxSession


def evaluate(session, expression: str) -> Any:
    if isinstance(session, ChromeSession):
        return session.evaluate(expression)
    return session.execute(f"return ({expression});")


def wait_ready(session, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state = browser_state(session)
        metrics = state.get("metrics") or {}
        if metrics.get("fatalError"):
            raise RuntimeError(f"reference app initialization failed: {metrics['fatalError']}")
        if metrics.get("ready") and metrics.get("firstTileMs") is not None:
            return state
        time.sleep(0.25)
    raise RuntimeError(f"reference app was not ready: {state}")


def command(session, name: str, arguments: dict[str, Any] | None = None,
            timeout: float = 300, expected_error: str | None = None) -> dict[str, Any]:
    expression = (
        f"globalThis.__r6_reference.startCommand({json.dumps(name)},"
        f"{json.dumps(arguments or {}, ensure_ascii=False)})"
    )
    command_id = evaluate(session, expression)
    deadline = time.monotonic() + timeout
    state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state = browser_state(session)
        records = (state.get("metrics") or {}).get("commands") or []
        record = next((item for item in records if item.get("id") == command_id), None)
        if record and record.get("status") in {"passed", "failed"}:
            if expected_error:
                if record.get("status") != "failed" or record.get("error", {}).get("code") != expected_error:
                    raise RuntimeError(
                        f"{name} expected {expected_error}, got {json.dumps(record, ensure_ascii=False)}"
                    )
            elif record.get("status") != "passed":
                raise RuntimeError(f"{name} failed: {json.dumps(record, ensure_ascii=False)}")
            return record
        time.sleep(0.2)
    raise RuntimeError(f"command {name}/{command_id} timed out: {state}")


class ScenarioRun:
    def __init__(self, base_url: str, alice, bob, timeout: float,
                 evidence_dir: Path, prefix: str):
        self.base_url = base_url
        self.alice = alice
        self.bob = bob
        self.timeout = timeout
        self.evidence_dir = evidence_dir
        self.prefix = prefix
        self.results: list[dict[str, Any]] = []

    def reset(self, fixture_name: str = "t1-plain-zh.odt", event_retention: int = 64) -> None:
        http_json("POST", f"{self.base_url}/__test/reset", {
            "fixtureName": fixture_name,
            "eventRetention": event_retention,
        })
        command(self.alice, "reloadAuthority", timeout=self.timeout)
        command(self.bob, "reloadAuthority", timeout=self.timeout)
        command(self.alice, "heartbeat", timeout=self.timeout)
        command(self.bob, "heartbeat", timeout=self.timeout)

    def server_state(self) -> dict[str, Any]:
        return http_json("GET", f"{self.base_url}/__test/state/r6-reference-document")

    def metadata(self) -> dict[str, Any]:
        return http_json("GET", f"{self.base_url}/api/documents/r6-reference-document")["data"]["current"]

    def collaboration(self) -> dict[str, Any]:
        return http_json("GET", f"{self.base_url}/api/documents/r6-reference-document/collaboration")

    def run_scenario(self, scenario_id: str, operation) -> None:
        started = time.monotonic()
        try:
            details = operation()
            self.results.append({
                "id": scenario_id,
                "pass": True,
                "durationMs": (time.monotonic() - started) * 1000,
                "details": details,
            })
        except Exception as error:
            self.results.append({
                "id": scenario_id,
                "pass": False,
                "durationMs": (time.monotonic() - started) * 1000,
                "error": str(error),
            })
            raise

    def s1(self) -> dict[str, Any]:
        self.reset()
        before = self.metadata()
        alice_snapshot = command(self.alice, "refresh", timeout=self.timeout)["result"]
        bob_snapshot = command(self.bob, "refresh", timeout=self.timeout)["result"]
        presence = self.collaboration()["data"]["presence"]
        if len(presence) != 2:
            raise RuntimeError("S1 expected Alice and Bob presence")
        comment = command(self.bob, "createComment", {"body": "Bob S1 comment"}, self.timeout)["result"]
        reply = command(self.alice, "createComment", {
            "body": "Alice S1 reply", "parentId": comment["id"],
        }, self.timeout)["result"]
        command(self.alice, "resolveComment", {"commentId": comment["id"]}, self.timeout)
        after_sidecar = self.metadata()
        expiry = command(self.alice, "advanceClock", {"milliseconds": 15001}, self.timeout)["result"]
        command(self.alice, "heartbeat", timeout=self.timeout)
        remaining = self.collaboration()["data"]["presence"]
        if before["blobSha256"] != after_sidecar["blobSha256"] or after_sidecar["version"] != "v1":
            raise RuntimeError("S1 sidecar changed Office blob")
        if len(remaining) != 1 or remaining[0]["actorId"] != "alice":
            raise RuntimeError("S1 Bob presence did not expire")
        return {
            "initialPresence": len(presence),
            "commentId": comment["id"],
            "replyId": reply["id"],
            "remainingPresence": [item["actorId"] for item in remaining],
            "expiry": expiry,
            "version": after_sidecar["version"],
            "blobSha256": after_sidecar["blobSha256"],
            "snapshots": [alice_snapshot, bob_snapshot],
        }

    def s2(self) -> dict[str, Any]:
        self.reset()
        v1 = self.metadata()
        v1_bytes, _ = http_bytes(
            f"{self.base_url}/api/documents/r6-reference-document/versions/v1/blob"
        )
        provider = command(self.bob, "providerSuggestion", timeout=self.timeout)["result"]
        if not provider["sidecarOnly"] or provider["sdkRevision"] != 0:
            raise RuntimeError("S2 Provider mutated Bob document")
        accepted = command(self.alice, "acceptSuggestion", {
            "suggestionId": provider["suggestionId"],
        }, self.timeout)["result"]
        manual_edit = command(self.alice, "localEditFromSearch", timeout=self.timeout)["result"]
        manual_undo = command(self.alice, "undoLocal", timeout=self.timeout)["result"]
        event = command(self.bob, "pollEvents", timeout=self.timeout)["result"]
        bob_before_reload = browser_state(self.bob)["metrics"]
        if bob_before_reload["readerStates"][-1]["state"] != "stale":
            raise RuntimeError("S2 Bob did not enter stale after document-updated")
        reload_result = command(self.bob, "reloadAuthority", timeout=self.timeout)["result"]
        replacement = command(self.bob, "search", {
            "query": provider["replacement"],
        }, self.timeout)["result"]
        state = self.server_state()
        v1_after, _ = http_bytes(
            f"{self.base_url}/api/documents/r6-reference-document/versions/v1/blob"
        )
        v2_bytes, _ = http_bytes(
            f"{self.base_url}/api/documents/r6-reference-document/versions/v2/blob"
        )
        output = self.evidence_dir / f"{self.prefix}-s2-v2.odt"
        output.write_bytes(v2_bytes)
        if v1_bytes != v1_after or hashlib.sha256(v1_after).hexdigest() != v1["blobSha256"]:
            raise RuntimeError("S2 immutable v1 changed")
        if state["versionCount"] != 2 or not replacement["found"]:
            raise RuntimeError("S2 v2/reload/replacement invariant failed")
        return {
            "provider": provider,
            "accepted": accepted,
            "manualEditAfterAccept": manual_edit,
            "manualUndo": manual_undo,
            "bobEvent": event,
            "bobReload": reload_result,
            "replacementFound": replacement["found"],
            "v1Immutable": True,
            "versionCount": state["versionCount"],
            "v2Evidence": output.name,
        }

    def s3(self) -> dict[str, Any]:
        self.reset()
        suggestion = command(self.alice, "createSuggestion", {
            "quote": "LibreOfficeKit", "replacement": "Alice-authoritative-R6-S3",
        }, self.timeout)["result"]
        lease = command(self.alice, "acquireLease", timeout=self.timeout)["result"]
        held = command(self.bob, "acquireLease", timeout=self.timeout, expected_error="LEASE_HELD")
        bob_local = command(self.bob, "localEditAndSave", {
            "replacement": "BOB-FORBIDDEN-STALE-R6",
        }, self.timeout)["result"]
        alice_commit = command(self.alice, "acceptSuggestion", {
            "suggestionId": suggestion["id"],
        }, self.timeout)["result"]
        stale = command(self.bob, "stalePut", timeout=self.timeout, expected_error="VERSION_CONFLICT")
        state = self.server_state()
        bob_metrics = browser_state(self.bob)["metrics"]
        if state["versionCount"] != 2 or not bob_metrics["localBytesAvailable"]:
            raise RuntimeError("S3 conflict changed authority or lost Bob local bytes")
        return {
            "aliceLease": {"leaseId": lease["leaseId"], "waitMs": lease["waitMs"]},
            "bobAcquireError": held["error"],
            "bobLocal": bob_local,
            "aliceCommit": alice_commit,
            "bobSubmitError": stale["error"],
            "bobConflict": bob_metrics["conflict"],
            "versionCount": state["versionCount"],
        }

    def s4(self) -> dict[str, Any]:
        self.reset("t3-long.odt")
        before = self.metadata()
        missing = command(self.alice, "createSuggestion", {
            "quote": "R6-ANCHOR-DOES-NOT-EXIST", "replacement": "forbidden-missing",
        }, self.timeout)["result"]
        missing_error = command(self.alice, "acceptSuggestion", {
            "suggestionId": missing["id"],
        }, self.timeout, expected_error="ANCHOR_NOT_FOUND")
        repeated = command(self.alice, "createSuggestion", {
            "quote": "English compatibility text", "replacement": "forbidden-ambiguous",
        }, self.timeout)["result"]
        ambiguous_error = command(self.alice, "acceptSuggestion", {
            "suggestionId": repeated["id"],
        }, self.timeout, expected_error="ANCHOR_AMBIGUOUS")
        after = self.metadata()
        snapshot = self.collaboration()["data"]
        if before["blobSha256"] != after["blobSha256"] or after["version"] != "v1":
            raise RuntimeError("S4 anchor failure changed the Office blob")
        statuses = {item["id"]: item["status"] for item in snapshot["suggestions"]}
        if statuses[missing["id"]] != "conflict" or statuses[repeated["id"]] != "conflict":
            raise RuntimeError("S4 suggestions were not recorded as conflict")
        return {
            "missing": missing_error["error"],
            "ambiguous": ambiguous_error["error"],
            "statuses": statuses,
            "version": after["version"],
            "blobUnchanged": True,
        }

    def s5(self) -> dict[str, Any]:
        self.reset()
        command(self.alice, "createComment", {"body": "S5 replay comment"}, self.timeout)
        suggestion = command(self.alice, "createSuggestion", {
            "quote": "LibreOfficeKit", "replacement": "R6-S5-replay-version",
        }, self.timeout)["result"]
        command(self.alice, "acceptSuggestion", {"suggestionId": suggestion["id"]}, self.timeout)
        replay = command(self.bob, "pollEvents", timeout=self.timeout)["result"]
        if replay["mode"] != "replay" or replay["version"] != "v2":
            raise RuntimeError("S5 retained gap did not replay")
        command(self.bob, "reloadAuthority", timeout=self.timeout)

        self.reset(event_retention=3)
        for index in range(4):
            command(self.alice, "createComment", {"body": f"S5 snapshot comment {index}"}, self.timeout)
        suggestion = command(self.alice, "createSuggestion", {
            "quote": "LibreOfficeKit", "replacement": "R6-S5-snapshot-version",
        }, self.timeout)["result"]
        command(self.alice, "acceptSuggestion", {"suggestionId": suggestion["id"]}, self.timeout)
        fallback = command(self.bob, "pollEvents", timeout=self.timeout)["result"]
        bob_before_reload = browser_state(self.bob)["metrics"]
        if fallback["mode"] != "snapshot" or fallback["version"] != "v2":
            raise RuntimeError("S5 evicted gap did not return snapshot")
        if bob_before_reload["version"] != "v1" or bob_before_reload["authorityVersion"] != "v2":
            raise RuntimeError("S5 mislabeled the v1 canvas as v2")
        reload_result = command(self.bob, "reloadAuthority", timeout=self.timeout)["result"]
        if reload_result["version"] != "v2":
            raise RuntimeError("S5 snapshot fallback did not converge after explicit reload")
        return {
            "replay": replay,
            "snapshot": fallback,
            "canvasBeforeReload": bob_before_reload["version"],
            "authorityBeforeReload": bob_before_reload["authorityVersion"],
            "reload": reload_result,
        }

    def s6(self) -> dict[str, Any]:
        self.reset()
        before = self.collaboration()["data"]
        result = command(self.bob, "providerBoundaryRegression", timeout=self.timeout)["result"]
        after = self.collaboration()["data"]
        if len(before["suggestions"]) != len(after["suggestions"]):
            raise RuntimeError("S6 rejected/cancelled/crashed Provider created a suggestion")
        return result

    def s7(self) -> dict[str, Any]:
        self.reset()
        saved = command(self.alice, "crashWithLocalEdit", {
            "save": True, "replacement": "R6-S7-saved-local",
        }, self.timeout)["result"]
        state_after_saved = self.server_state()
        if state_after_saved["versionCount"] != 1 or not saved["localBytesAvailable"]:
            raise RuntimeError("S7 saved crash path mutated authority or lost local bytes")
        self.reset()
        unsaved = command(self.alice, "crashWithLocalEdit", {
            "save": False, "replacement": "R6-S7-unsaved-local",
        }, self.timeout)["result"]
        state_after_unsaved = self.server_state()
        if state_after_unsaved["versionCount"] != 1 or unsaved["localBytesAvailable"]:
            raise RuntimeError("S7 unsaved crash recovery contract is wrong")
        command(self.alice, "reloadAuthority", timeout=self.timeout)
        return {
            "savedCrash": saved,
            "unsavedCrash": unsaved,
            "authorityVersionCount": state_after_unsaved["versionCount"],
            "automaticMutationReplay": False,
        }


def run_sample(base_url: str, alice_browser: str, bob_browser: str,
               sample: int, scenarios: list[str], timeout: float,
               evidence_dir: Path) -> dict[str, Any]:
    prefix = f"reference-{alice_browser}-{bob_browser}-{sample}"
    http_json("POST", f"{base_url}/__test/reset", {
        "fixtureName": "t1-plain-zh.odt", "eventRetention": 64,
    })
    alice = session_class(alice_browser)("cold")
    bob = session_class(bob_browser)("cold")
    result: dict[str, Any] = {
        "schemaVersion": 1,
        "release": "R6-C",
        "runId": prefix,
        "aliceBrowser": alice_browser,
        "bobBrowser": bob_browser,
        "aliceBrowserVersion": alice.version,
        "bobBrowserVersion": bob.version,
        "scenarios": [],
        "pass": False,
    }
    try:
        alice.navigate(f"{base_url}/r6-reference.html?role=alice&run={sample}")
        bob.navigate(f"{base_url}/r6-reference.html?role=bob&run={sample}")
        wait_ready(alice, timeout)
        wait_ready(bob, timeout)
        run = ScenarioRun(base_url, alice, bob, timeout, evidence_dir, prefix)
        for scenario in scenarios:
            run.run_scenario(scenario.upper(), getattr(run, scenario.lower()))
        result["scenarios"] = run.results
        result["alice"] = browser_state(alice)["metrics"]
        result["bob"] = browser_state(bob)["metrics"]
        result["finalServer"] = run.server_state()
        result["pass"] = all(item["pass"] for item in run.results) \
            and len(run.results) == len(scenarios)
        (evidence_dir / f"{prefix}-alice.png").write_bytes(alice.screenshot())
        (evidence_dir / f"{prefix}-bob.png").write_bytes(bob.screenshot())
        (evidence_dir / f"{prefix}-alice.log.txt").write_text(
            browser_state(alice).get("log", ""), encoding="utf-8",
        )
        (evidence_dir / f"{prefix}-bob.log.txt").write_text(
            browser_state(bob).get("log", ""), encoding="utf-8",
        )
    finally:
        (evidence_dir / f"{prefix}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        alice.close()
        bob.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alice-browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--bob-browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--scenarios", default="s1,s2,s3,s4,s5,s6,s7")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    project = Path(__file__).resolve().parent.parent
    port = free_port()
    service = subprocess.Popen(
        ["node", "tools/serve_r6_reference.mjs", "--port", str(port)],
        cwd=project,
        # DEVNULL, not PIPE: nothing ever read these pipes, and the request
        # log fills 64 KiB after a workload-dependent number of navigations --
        # the handler thread then blocks before sending the response body and
        # every later fetch hangs (finding 023).
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    scenarios = [item.strip().lower() for item in args.scenarios.split(",") if item.strip()]
    summaries: list[dict[str, Any]] = []
    try:
        wait_service(base_url)
        for sample in range(1, args.samples + 1):
            result = run_sample(
                base_url, args.alice_browser, args.bob_browser,
                sample, scenarios, args.timeout, args.evidence_dir,
            )
            sample_summary = {
                "runId": result["runId"],
                "pass": result["pass"],
                "scenarios": [{"id": item["id"], "pass": item["pass"]}
                              for item in result["scenarios"]],
            }
            summaries.append(sample_summary)
            print(json.dumps(sample_summary, ensure_ascii=False), flush=True)
    finally:
        service.terminate()
        try:
            service.wait(timeout=10)
        except subprocess.TimeoutExpired:
            service.kill()
            service.wait(timeout=10)
        stdout, stderr = service.communicate()
        (args.evidence_dir / f"service-{args.alice_browser}-{args.bob_browser}.log.txt").write_text(
            f"stdout:\n{stdout}\nstderr:\n{stderr}", encoding="utf-8",
        )
    summary = {
        "schemaVersion": 1,
        "release": "R6-C",
        "aliceBrowser": args.alice_browser,
        "bobBrowser": args.bob_browser,
        "requestedSamples": args.samples,
        "scenarios": scenarios,
        "samples": summaries,
        "pass": len(summaries) == args.samples and all(item["pass"] for item in summaries),
    }
    output = args.evidence_dir / f"reference-{args.alice_browser}-{args.bob_browser}-summary.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    if not summary["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
