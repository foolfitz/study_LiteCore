#!/usr/bin/env python3
"""Drive the R7-A browser discovery and record browser process-tree memory."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import psutil

from run_browser_probe import ChromeSession, FirefoxSession, free_port


def evaluate(session, script: str) -> Any:
    if isinstance(session, ChromeSession):
        return session.evaluate(script)
    return session.execute(f"return {script};")


def wait_page(url: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as caught:
            error = caught
        time.sleep(0.2)
    raise RuntimeError(f"timed out waiting for {url}: {error}")


def process_snapshot(root_pid: int, page_phase: str | None) -> dict[str, Any]:
    sample: dict[str, Any] = {
        "monotonicSeconds": time.monotonic(),
        "pagePhase": page_phase,
        "rootPid": root_pid,
        "processes": [],
    }
    try:
        root = psutil.Process(root_pid)
        processes = [root, *root.children(recursive=True)]
    except (psutil.Error, ProcessLookupError) as error:
        sample["error"] = str(error)
        return sample
    for process in processes:
        try:
            memory = process.memory_info()
            try:
                pss = process.memory_full_info().pss
            except (AttributeError, psutil.Error, PermissionError):
                pss = None
            sample["processes"].append({
                "pid": process.pid,
                "ppid": process.ppid(),
                "name": process.name(),
                "rssBytes": memory.rss,
                "pssBytes": pss,
                "status": process.status(),
            })
        except (psutil.Error, ProcessLookupError):
            continue
    sample["processCount"] = len(sample["processes"])
    sample["rssBytes"] = sum(item["rssBytes"] for item in sample["processes"])
    values = [item["pssBytes"] for item in sample["processes"] if item["pssBytes"] is not None]
    sample["pssBytes"] = sum(values) if values else None
    sample["workerLikeCount"] = sum(
        1 for item in sample["processes"]
        if item["name"].lower() in {"chrome", "firefox", "firefox-bin"}
    )
    return sample


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--lifecycle-cycles", type=int, default=10)
    parser.add_argument("--crash-cycles", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=1200)
    parser.add_argument("--evidence-root", type=Path, default=workspace / "findings" / "evidence" / "sdk-r7" / "discovery")
    args = parser.parse_args()
    if args.lifecycle_cycles < 1 or args.crash_cycles < 1:
        raise SystemExit("cycle counts must be positive")

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
    samples: list[dict[str, Any]] = []
    metrics: dict[str, Any] | None = None
    log_text = ""
    try:
        base_url = f"http://127.0.0.1:{server_port}/r7-discovery.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        url = f"{base_url}?lifecycleCycles={args.lifecycle_cycles}&crashCycles={args.crash_cycles}"
        session.navigate(url)
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__r7_discovery || null")
            phase = metrics.get("phase") if metrics else None
            samples.append(process_snapshot(session.process.pid, phase))
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.5)
        if not metrics or not metrics.get("complete"):
            raise RuntimeError(f"R7 discovery timed out at {metrics and metrics.get('phase')}")
        log_text = str(evaluate(session, "document.querySelector('#log').textContent"))
        screenshot = session.screenshot()
        output = base64.b64decode(str(evaluate(session, "globalThis.__r7_discovery_get_output_base64()")))
        evidence = args.evidence_root
        paths = {
            "input": evidence / "input" / f"{args.browser}.json",
            "clipboard": evidence / "clipboard" / f"{args.browser}.json",
            "formats": evidence / "formats" / f"{args.browser}.json",
            "memory": evidence / "memory" / f"{args.browser}.json",
        }
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        common = {
            "schemaVersion": 1,
            "release": "R7-A",
            "browser": args.browser,
            "browserVersion": session.version,
            "userAgent": metrics["userAgent"],
        }
        paths["input"].write_text(json.dumps({**common, "input": metrics["input"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths["clipboard"].write_text(json.dumps({**common, "clipboard": metrics["clipboard"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths["formats"].write_text(json.dumps({**common, "formats": metrics["formats"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths["memory"].write_text(json.dumps({
            **common,
            "browserMemory": metrics["browserMemory"],
            "workers": metrics["workers"],
            "lifecycle": metrics["lifecycle"],
            "processSamples": samples,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (evidence / "input" / f"{args.browser}-unicode-out.odt").write_bytes(output)
        (evidence / "input" / f"{args.browser}.log.txt").write_text(log_text, encoding="utf-8")
        (evidence / "input" / f"{args.browser}.png").write_bytes(screenshot)
        summary = {
            **common,
            "manifest": metrics["manifest"],
            "crossOriginIsolated": metrics["crossOriginIsolated"],
            "decisionCandidate": metrics["decisionCandidate"],
            "pass": metrics["pass"],
            "error": metrics["error"],
            "outputBytes": len(output),
            "evidence": {key: str(path) for key, path in paths.items()},
        }
        summary_path = evidence / f"{args.browser}-summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"summary": str(summary_path), "pass": metrics["pass"], "decisionCandidate": metrics["decisionCandidate"]}, ensure_ascii=False))
        if not metrics["pass"]:
            raise SystemExit(1)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
