#!/usr/bin/env python3
"""Run the R7-D lifecycle scenarios with process-tree memory sampling."""

from __future__ import annotations

import argparse
import base64
import copy
import json
import math
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from r7_longevity_analysis import analyse_memory
from r7_support import (
    ChromeSession,
    FirefoxSession,
    desktop_pdf_roundtrip,
    evaluate,
    load_json,
    process_snapshot,
    sha256,
    wait_page,
    write_json,
)
from run_browser_probe import free_port


FORMAL_PLANS = [
    ("s1", 1), ("s1", 2), ("s1", 3),
    ("s2-reuse", 1), ("s2-fresh", 1), ("s3", 1),
    ("s4", 1), ("s5-normal", 1), ("s5-known", 1),
]


def scenario_plans(args: argparse.Namespace) -> list[tuple[str, int]]:
    if args.scenario:
        return [(args.scenario, args.run)]
    if args.plan_prefix is not None:
        return FORMAL_PLANS[:args.plan_prefix]
    return FORMAL_PLANS


def collect_browser_summary(browser: str, browser_root: Path, threshold: dict) -> dict:
    runs = []
    for scenario, run_number in FORMAL_PLANS:
        path = browser_root / scenario / f"run-{run_number}" / "result.json"
        value = load_json(path) if path.is_file() else {"pass": False}
        runs.append({
            "scenario": scenario, "run": run_number,
            "result": str(path), "pass": value.get("pass") is True,
            "knownDegradation": value.get("metrics", {}).get("knownDegradation"),
        })
    return {
        "schemaVersion": 1, "release": "R7-D", "browser": browser,
        "threshold": threshold, "runs": runs,
        "pass": all(item["pass"] for item in runs),
    }


def safe_odt(path: Path) -> dict:
    result = {
        "path": str(path), "bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256(path) if path.is_file() else None,
        "zip": False, "crc": False, "pass": False,
    }
    if path.is_file() and zipfile.is_zipfile(path):
        result["zip"] = True
        with zipfile.ZipFile(path) as archive:
            result["crc"] = archive.testzip() is None
        result["pass"] = result["crc"]
    return result


def offset_cycle_state(state: dict, offset: int) -> dict:
    adjusted = dict(state)
    cycle = adjusted.get("cycle")
    if isinstance(cycle, int) and cycle > 0:
        adjusted["cycle"] = cycle + offset
        adjusted["block"] = math.ceil(adjusted["cycle"] / 10)
    return adjusted


def merge_fresh_metrics(batches: list[dict], target_cycles: int) -> dict:
    if not batches:
        return {
            "scenario": "s2-fresh", "complete": True, "pass": False,
            "phase": "error", "lifecycle": [],
            "error": {"code": "NO_BATCH_EVIDENCE", "message": "no batch completed"},
        }
    merged = copy.deepcopy(batches[0]["metrics"])
    lifecycle = []
    workers = {"created": 0, "terminated": 0, "crashes": 0, "active": 0}
    handles = {"opened": 0, "closed": 0, "active": 0}
    batch_evidence = []
    offset = 0
    for item in batches:
        metrics = item["metrics"]
        for cycle in metrics.get("lifecycle", []):
            adjusted = copy.deepcopy(cycle)
            adjusted["cycle"] = int(adjusted["cycle"]) + offset
            lifecycle.append(adjusted)
        for name in workers:
            if name == "active":
                workers[name] = int(metrics.get("workers", {}).get(name, 0))
            else:
                workers[name] += int(metrics.get("workers", {}).get(name, 0))
        for name in handles:
            if name == "active":
                handles[name] = int(metrics.get("handles", {}).get(name, 0))
            else:
                handles[name] += int(metrics.get("handles", {}).get(name, 0))
        count = len(metrics.get("lifecycle", []))
        batch_evidence.append({
            "batch": item["batch"], "cycleStart": offset + 1,
            "cycleEnd": offset + count, "pass": metrics.get("pass") is True,
            "result": item["result"],
        })
        offset += count
    merged.update({
        "lifecycle": lifecycle,
        "workers": workers,
        "handles": handles,
        "sampleState": offset_cycle_state(
            batches[-1]["metrics"].get("sampleState", {}),
            offset - len(batches[-1]["metrics"].get("lifecycle", [])),
        ),
        "batches": batch_evidence,
        "phase": "complete",
        "complete": True,
        "error": None,
    })
    merged["pass"] = (
        len(lifecycle) == target_cycles
        and all(item.get("pass") is True for item in lifecycle)
        and all(item["pass"] for item in batch_evidence)
        and workers["active"] == 0
        and handles["active"] == 0
    )
    return merged


def parse_firefox_prefs(items: list[str]) -> dict[str, object]:
    """Parse repeated NAME=VALUE pref arguments; JSON values where possible."""
    prefs: dict[str, object] = {}
    for item in items:
        name, _, raw = item.partition("=")
        if not name or not _:
            raise SystemExit(f"--firefox-pref expects NAME=VALUE, got {item!r}")
        try:
            prefs[name] = json.loads(raw)
        except json.JSONDecodeError:
            prefs[name] = raw
    return prefs


def open_session(
    session_class: type[ChromeSession] | type[FirefoxSession],
    args: argparse.Namespace,
) -> ChromeSession | FirefoxSession:
    """Open a cold session, applying --firefox-pref when the browser is firefox.

    Prefs are the only handle we have on a *browser* budget, so this is what
    turns "50 generations passed" into an attribution: shrink the budget and
    watch whether the wall moves with it (finding 024's method).
    """
    prefs = parse_firefox_prefs(args.firefox_pref)
    if prefs and session_class is FirefoxSession:
        return session_class("cold", extra_prefs=prefs)
    return session_class("cold")


def run_one(
    session_class: type[ChromeSession] | type[FirefoxSession],
    base_url: str,
    browser: str,
    browser_root: Path,
    scenario: str,
    run_number: int,
    threshold: dict,
    args: argparse.Namespace,
    artifact_hashes: dict,
) -> dict:
    root = browser_root / scenario / f"run-{run_number}"
    root.mkdir(parents=True, exist_ok=True)
    session = open_session(session_class, args)
    samples = []
    metrics = None
    last_token = None
    last_sample = 0.0
    try:
        query = {
            "scenario": scenario,
            "sampleDwellMs": args.sample_dwell_ms,
            "closeTimeoutMs": args.close_timeout_ms or threshold["closeTimeoutMs"],
        }
        if scenario == "s5-normal":
            query["s5Variant"] = args.s5_variant
        if scenario.startswith("s2"):
            query["cycles"] = args.lifecycle_cycles
        if scenario == "s3":
            query["cycles"] = args.crash_cycles
        if scenario == "s4":
            query["soakMinutes"] = args.soak_minutes
            query["soakIntervalMs"] = args.soak_interval_ms
        encoded = "&".join(f"{key}={value}" for key, value in query.items())
        session.navigate(f"{base_url}?{encoded}")
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__r7_longevity || null")
            now = time.monotonic()
            state = metrics.get("sampleState", {}) if metrics else {}
            token = state.get("token")
            if token != last_token or now - last_sample >= threshold["sampleIntervalMs"] / 1000:
                samples.append(process_snapshot(session.process.pid, state))
                last_token = token
                last_sample = now
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.2)
        if not metrics or not metrics.get("complete"):
            raise RuntimeError(f"R7-D {scenario} timed out at {metrics and metrics.get('phase')}")
        # Idle tail: keep sampling the SAME page, doing no work, after the last
        # generation is disposed.  The post-close block medians rise
        # monotonically across a run, but "residue that accumulates per
        # generation" and "reclamation that simply lags the workload" produce
        # exactly the same rising curve while work is ongoing.  They differ only
        # once the work stops: residue stays, lag drains.  Tagged with its own
        # checkpoint so analyse_memory()'s post-close gate never sees these.
        if args.idle_tail_seconds > 0:
            tail_deadline = time.monotonic() + args.idle_tail_seconds
            tail_index = 0
            while time.monotonic() < tail_deadline:
                samples.append(process_snapshot(session.process.pid, {
                    "checkpoint": "idle-tail",
                    "cycle": (metrics.get("sampleState") or {}).get("cycle"),
                    "block": tail_index,
                }))
                tail_index += 1
                time.sleep(threshold["sampleIntervalMs"] / 1000)
        (root / "page.png").write_bytes(session.screenshot())
        (root / "browser.log.txt").write_text(
            str(evaluate(session, "document.querySelector('#log').textContent")), encoding="utf-8"
        )
        output = None
        encoded_output = evaluate(session, "globalThis.__r7_longevity_get_output_base64()")
        if encoded_output:
            output_path = root / "output.odt"
            output_path.write_bytes(base64.b64decode(str(encoded_output)))
            odt = safe_odt(output_path)
            desktop = desktop_pdf_roundtrip(output_path, root / "output.pdf")
            output = {"odt": odt, "desktopRoundtrip": desktop, "pass": odt["pass"] and desktop["pass"]}
        memory = analyse_memory(samples, threshold) if scenario.startswith("s2") else {
            "status": "samples-recorded-not-a-50-cycle-gate",
            "sampleCount": len(samples),
            "pass": True,
        }
        result = {
            "schemaVersion": 1,
            "release": "R7-D",
            "browser": browser,
            "browserVersion": session.version,
            "sessionType": "headless-automatic",
            "scenario": scenario,
            "run": run_number,
            "browserRootPid": session.process.pid,
            "firefoxPrefs": parse_firefox_prefs(args.firefox_pref) or None,
            "artifactHashes": artifact_hashes,
            "threshold": threshold,
            "metrics": metrics,
            "processSamples": samples,
            "memoryAnalysis": memory,
            "output": output,
            "pass": metrics.get("pass") is True
            and memory.get("pass") is True
            and (output is None or output["pass"]),
        }
        write_json(root / "result.json", result)
        return {
            "scenario": scenario, "run": run_number,
            "result": str(root / "result.json"), "pass": result["pass"],
            "knownDegradation": metrics.get("knownDegradation"),
        }
    except Exception as error:
        failure = {
            "schemaVersion": 1, "release": "R7-D", "browser": browser,
            "scenario": scenario, "run": run_number,
            "firefoxPrefs": parse_firefox_prefs(args.firefox_pref) or None,
            "error": {"name": type(error).__name__, "message": str(error)},
            "lastMetrics": metrics, "processSamples": samples, "pass": False,
        }
        write_json(root / "result.json", failure)
        return {"scenario": scenario, "run": run_number, "result": str(root / "result.json"), "pass": False}
    finally:
        session.close()


def run_firefox_fresh_batched(
    session_class: type[FirefoxSession],
    base_url: str,
    browser_root: Path,
    threshold: dict,
    args: argparse.Namespace,
    artifact_hashes: dict,
) -> dict:
    """Run all 50 fresh-engine cycles in one Firefox process and fresh pages."""
    scenario = "s2-fresh"
    run_number = 1
    root = browser_root / scenario / f"run-{run_number}"
    root.mkdir(parents=True, exist_ok=True)
    session = None
    samples = []
    batches = []
    browser_versions = []
    browser_root_pids = []
    batch_size = 5
    try:
        for batch_number, offset in enumerate(
            range(0, args.lifecycle_cycles, batch_size), 1
        ):
            count = min(batch_size, args.lifecycle_cycles - offset)
            batch_root = root / "batches" / f"batch-{batch_number}"
            batch_root.mkdir(parents=True, exist_ok=True)
            session = open_session(session_class, args)
            browser_versions.append(session.version)
            browser_root_pids.append(session.process.pid)
            query = {
                "scenario": scenario,
                "cycles": count,
                "sampleDwellMs": args.sample_dwell_ms,
                "closeTimeoutMs": args.close_timeout_ms or threshold["closeTimeoutMs"],
            }
            encoded = "&".join(f"{key}={value}" for key, value in query.items())
            session.navigate(f"{base_url}?{encoded}")
            deadline = time.monotonic() + args.timeout
            metrics = None
            last_token = None
            last_sample = 0.0
            while time.monotonic() < deadline:
                metrics = evaluate(session, "globalThis.__r7_longevity || null")
                now = time.monotonic()
                state = metrics.get("sampleState", {}) if metrics else {}
                token = state.get("token")
                if token != last_token or now - last_sample >= threshold["sampleIntervalMs"] / 1000:
                    samples.append(process_snapshot(
                        session.process.pid, offset_cycle_state(state, offset)
                    ))
                    last_token = token
                    last_sample = now
                if metrics and metrics.get("complete"):
                    break
                time.sleep(0.2)
            if not metrics or not metrics.get("complete"):
                raise RuntimeError(
                    f"R7-D {scenario} batch {batch_number} timed out"
                )
            (batch_root / "page.png").write_bytes(session.screenshot())
            (batch_root / "browser.log.txt").write_text(
                str(evaluate(session, "document.querySelector('#log').textContent")),
                encoding="utf-8",
            )
            batch_result = {
                "schemaVersion": 1, "release": "R7-D", "browser": "firefox",
                "browserVersion": session.version, "scenario": scenario,
                "run": run_number, "batch": batch_number,
                "cycleStart": offset + 1, "cycleEnd": offset + count,
                "metrics": metrics, "pass": metrics.get("pass") is True,
            }
            batch_path = batch_root / "result.json"
            write_json(batch_path, batch_result)
            batches.append({
                "batch": batch_number, "metrics": metrics,
                "result": str(batch_path),
            })
            session.close()
            session = None
            if not batch_result["pass"]:
                break
            if offset + count < args.lifecycle_cycles:
                time.sleep(12)

        metrics = merge_fresh_metrics(batches, args.lifecycle_cycles)
        memory = analyse_memory(samples, threshold)
        result = {
            "schemaVersion": 1, "release": "R7-D", "browser": "firefox",
            "browserVersion": browser_versions[0] if browser_versions else "unknown",
            "browserVersions": browser_versions,
            "sessionType": "headless-automatic-batched-browser-processes",
            "scenario": scenario, "run": run_number,
            "browserRootPids": browser_root_pids,
            "artifactHashes": artifact_hashes, "threshold": threshold,
            "metrics": metrics, "processSamples": samples,
            "memoryAnalysis": memory, "output": None,
            "pass": metrics.get("pass") is True and memory.get("pass") is True,
        }
        write_json(root / "result.json", result)
        return {
            "scenario": scenario, "run": run_number,
            "result": str(root / "result.json"), "pass": result["pass"],
            "knownDegradation": metrics.get("knownDegradation"),
        }
    except Exception as error:
        failure = {
            "schemaVersion": 1, "release": "R7-D", "browser": "firefox",
            "scenario": scenario, "run": run_number,
            "error": {"name": type(error).__name__, "message": str(error)},
            "processSamples": samples, "pass": False,
        }
        write_json(root / "result.json", failure)
        return {
            "scenario": scenario, "run": run_number,
            "result": str(root / "result.json"), "pass": False,
        }
    finally:
        if session is not None:
            session.close()


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument(
        "--scenario",
        choices=("s1", "s2-reuse", "s2-fresh", "s3", "s4", "s5-normal", "s5-known"),
    )
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--lifecycle-cycles", type=int, default=50)
    parser.add_argument(
        "--firefox-single-session", action="store_true",
        help="run firefox s2-fresh in one browser process and ONE page instead "
        "of 5-cycle batches; measures how many engine generations a single page "
        "actually sustains (the E1 specs cap it at 3, citing finding 014)",
    )
    parser.add_argument(
        "--idle-tail-seconds", type=float, default=0.0, metavar="SECONDS",
        help="after the page reports complete, keep sampling the same idle page "
        "for SECONDS.  Separates per-generation residue (stays) from reclaim "
        "latency (drains) -- while work is ongoing the two look identical "
        "(finding 014 待驗證 10).  Samples are tagged checkpoint=idle-tail and "
        "are excluded from the formal post-close gate",
    )
    parser.add_argument(
        "--plan-prefix", type=int, metavar="N",
        help="with --all, run only the first N entries of the formal plan.  "
        "Exists so the byte prefix that a later scenario inherits on a shared "
        "serve.py log can be measured on the real code path (finding 014's "
        "待驗證 9) instead of a re-implementation that might issue a different "
        "request sequence.  Needs its own --evidence-root",
    )
    parser.add_argument(
        "--firefox-pref", action="append", default=[], metavar="NAME=VALUE",
        help="extra about:config pref for the firefox session (repeatable); "
        "values are parsed as JSON when possible, else kept as strings.  Used "
        "to shrink a suspected browser budget (e.g. dom.workers.maxPerDomain) "
        "and watch whether a wall moves with it.  Requires an explicit "
        "--evidence-root so a pref run can never overwrite the formal series",
    )
    parser.add_argument("--crash-cycles", type=int, default=20)
    parser.add_argument("--soak-minutes", type=int, default=30)
    parser.add_argument("--soak-interval-ms", type=int, default=60000)
    parser.add_argument("--sample-dwell-ms", type=int, default=1100)
    parser.add_argument("--close-timeout-ms", type=int)
    parser.add_argument(
        "--s5-variant", choices=("open", "render", "search", "reader", "comments", "semantic"),
        default="reader",
    )
    parser.add_argument("--timeout", type=float, default=7200)
    default_evidence_root = workspace / "findings" / "evidence" / "sdk-r7" / "longevity"
    parser.add_argument("--evidence-root", type=Path, default=default_evidence_root)
    args = parser.parse_args()
    if not args.all and not args.scenario and not args.summarize_only:
        parser.error("use --all or --scenario")
    if args.firefox_pref and args.evidence_root == default_evidence_root:
        parser.error("--firefox-pref needs its own --evidence-root: a run with a "
                     "moved browser budget is not the formal series and must not "
                     "overwrite it")
    if args.idle_tail_seconds > 0 and args.evidence_root == default_evidence_root:
        parser.error("--idle-tail-seconds needs its own --evidence-root: it adds "
                     "samples the formal series does not have")
    if args.plan_prefix is not None:
        if not args.all:
            parser.error("--plan-prefix only applies to --all")
        if args.evidence_root == default_evidence_root:
            parser.error("--plan-prefix needs its own --evidence-root: a truncated "
                         "plan is not the formal series and must not overwrite it")
    thresholds = load_json(workspace / "findings" / "evidence" / "sdk-r7" / "discovery" / "memory" / "thresholds.json")
    threshold = next(item for item in thresholds["thresholds"] if item["browser"] == args.browser)
    if args.lifecycle_cycles != threshold["cycleCount"] and args.all:
        raise SystemExit("formal --all must use the preregistered lifecycle cycle count")
    if args.all and args.close_timeout_ms is not None:
        raise SystemExit("formal --all must use the preregistered close timeout")
    browser_root = args.evidence_root / args.browser
    if args.summarize_only:
        summary = collect_browser_summary(args.browser, browser_root, threshold)
        write_json(browser_root / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if not summary["pass"]:
            raise SystemExit(1)
        return
    port = free_port()
    # OXSDK_SERVER_LOG_DIR opts into keeping serve.py's request log so its
    # BYTE VOLUME can be measured -- that volume is what filled the 64 KiB pipe
    # in finding 023, and finding 014's byte ledger needs it per workload.  A
    # real file, never a pipe, so enabling it cannot reintroduce 023.
    server_log_dir = os.environ.get("OXSDK_SERVER_LOG_DIR")
    server_log_path = Path(server_log_dir) / "serve.log" if server_log_dir else None
    server_log = None
    if server_log_path:
        server_log_path.parent.mkdir(parents=True, exist_ok=True)
        server_log = open(server_log_path, "w", buffering=1)
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(port)],
        # DEVNULL, not PIPE: nothing ever read these pipes, and the request
        # log fills 64 KiB after a workload-dependent number of navigations --
        # the handler thread then blocks before sending the response body and
        # every later fetch hangs (finding 023).
        cwd=project, stdout=server_log or subprocess.DEVNULL,
        stderr=subprocess.STDOUT if server_log else subprocess.DEVNULL,
        text=True,
    )

    def server_log_bytes() -> int | None:
        return server_log_path.stat().st_size if server_log_path else None
    summaries = []
    try:
        base_url = f"http://127.0.0.1:{port}/r7-longevity.html"
        wait_page(base_url)
        # Sampled BEFORE the first scenario so wait_page()'s own polling is
        # attributed to startup and not to scenario 1.
        server_log_ledger = [{"after": "wait_page", "bytes": server_log_bytes(),
                              "monotonic": time.monotonic()}]
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        artifact_hashes = {
            "manifest": sha256(project / "dist" / "profiles" / "writer-review-r6" / "sdk-manifest.json"),
            "loader": sha256(project / "dist" / "profiles" / "writer-review" / "probe.35d96f5fdcb9ed0c.js"),
            "wasm": sha256(project / "dist" / "profiles" / "writer-review" / "probe.ba257beb038b6a2d.wasm"),
            "corpusManifest": sha256(project / "dist" / "r7-compat-fixtures" / "manifest.json"),
        }
        for scenario, run_number in scenario_plans(args):
            # The Firefox-only batching below (a fresh browser process every 5
            # cycles) exists because of finding 014's "worker generation
            # exhaustion".  finding 014's cause turned out to be our own unread
            # serve.py pipe (finding 023), so the batching may be unnecessary --
            # and while it is in place, one page never runs more than 5 engine
            # generations, which is exactly the claim the E1 specs' "max 3
            # generations per page" limit rests on.  --firefox-single-session
            # runs all 50 cycles in ONE page so that can be measured; default
            # behaviour is unchanged.
            if (args.browser == "firefox" and scenario == "s2-fresh"
                    and not args.firefox_single_session):
                item = run_firefox_fresh_batched(
                    session_class, base_url, browser_root,
                    threshold, args, artifact_hashes,
                )
            else:
                item = run_one(
                    session_class, base_url, args.browser, browser_root,
                    scenario, run_number, threshold, args, artifact_hashes,
                )
            summaries.append(item)
            server_log_ledger.append({
                "after": f"{scenario} run-{run_number}",
                "bytes": server_log_bytes(), "monotonic": time.monotonic(),
            })
            print(json.dumps(item, ensure_ascii=False), flush=True)
            if not item["pass"]:
                break
        summary = {
            "schemaVersion": 1, "release": "R7-D", "browser": args.browser,
            "threshold": threshold, "runs": summaries,
            "serverLogLedger": server_log_ledger if server_log_path else None,
            "serverLogPath": str(server_log_path) if server_log_path else None,
            "pass": len(summaries) == len(scenario_plans(args)) and all(item["pass"] for item in summaries),
        }
        write_json(browser_root / "summary.json", summary)
        if not summary["pass"]:
            raise SystemExit(1)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
        if server_log is not None:
            server_log.close()


if __name__ == "__main__":
    main()
