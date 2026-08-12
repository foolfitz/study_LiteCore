#!/usr/bin/env python3
"""Read emscripten's own pthread trace across a wedge (findings 037/038/032).

The stuck thread is parked, not spinning, so profiling is exhausted and the
question is what it is waiting for.  Emscripten already traces exactly that --
futex waits, mailbox activity and calls proxied to the main thread -- under
-sPTHREADS_DEBUG, which is a link-time setting.  The e2-wait-diagnostic profile
is the shipped engine's sources linked with it; the shipped artifact is not
touched and needs no re-sweep.

The trace goes to each worker's console, so this attaches to every worker
target and collects Runtime.consoleAPICalled.  What matters is the tail: the
last thing each thread said before it stopped saying anything.

Note on which wedge: the diagnostic build carries the finding 037 guard, so the
html-read hang cannot be reached on it.  Finding 038's wedge -- an as-char frame
inside a footnote body, hit by a plain drag-select -- is not covered by that
guard and reproduces here, which is why frame-contexts is the default fixture.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_wedge_thread_state import BrowserSession  # noqa: E402
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent


def console_lines(browser: BrowserSession) -> list[dict]:
    lines = []
    for event in browser.events:
        if event.get("method") != "Runtime.consoleAPICalled":
            continue
        params = event["params"]
        text = " ".join(
            str(arg.get("value", arg.get("description", "")))
            for arg in params.get("args", []))
        lines.append({
            "session": event.get("sessionId", "")[-6:],
            "type": params.get("type"),
            "timestamp": params.get("timestamp"),
            "text": text[:300],
        })
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="frame-contexts")
    parser.add_argument("--mode", default="wedge-split")
    parser.add_argument("--cases", default="")
    parser.add_argument("--profile", default="e2-wait-diagnostic")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--quiet-seconds", type=float, default=6.0)
    parser.add_argument(
        "--output", type=Path,
        default=PROJECT.parent / "findings" / "evidence" / "sdk-e2" / "discovery"
        / "pthread-trace" / "chrome" / "result.json")
    args = parser.parse_args()

    server_port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(server_port)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = browser = None
    result: dict = {"schemaVersion": 1, "release": "finding-032-pthread-trace",
                    "fixture": args.fixture, "profile": args.profile}
    try:
        base = f"http://127.0.0.1:{server_port}/e2-format-discovery.html"
        wait_page(base)
        session = ChromeSession("cold")
        query = f"?fixture={args.fixture}&mode={args.mode}&profileOverride={args.profile}"
        if args.cases:
            query += f"&cases={args.cases}"
        session.navigate(base + query)

        browser = BrowserSession(session.base_url)
        targets = browser.call("Target.getTargets")["targetInfos"]
        page = next(t for t in targets if t["type"] == "page")
        page_session = browser.call(
            "Target.attachToTarget",
            {"targetId": page["targetId"], "flatten": True})["sessionId"]
        auto_attach = {"autoAttach": True, "waitForDebuggerOnStart": False,
                       "flatten": True}
        browser.call("Target.setAutoAttach", auto_attach, session=page_session)
        browser.drain(2.0)
        for _ in range(2):
            for attached in browser.attached_sessions():
                sid = attached["sessionId"]
                for method in ("Target.setAutoAttach", "Runtime.enable"):
                    try:
                        browser.call(
                            method,
                            auto_attach if method.startswith("Target") else None,
                            session=sid, timeout=10)
                    except Exception:
                        pass
            browser.drain(1.5)
        result["workers"] = [
            {"type": a["target"]["type"], "url": a["target"]["url"][-60:]}
            for a in browser.attached_sessions()]

        # Let the run reach the wedge, pumping the socket so console output is
        # collected as it arrives rather than only at the end.
        deadline = time.monotonic() + args.timeout
        last_count, last_change = -1, time.monotonic()
        while time.monotonic() < deadline:
            browser.drain(0.5)
            metrics = evaluate(session, "globalThis.__e2_discovery || null") or {}
            trace = metrics.get("engineTrace") or []
            if len(trace) != last_count:
                last_count, last_change = len(trace), time.monotonic()
            elif last_count > 0 and time.monotonic() - last_change > args.quiet_seconds:
                result["wedge"] = {
                    "engineTraceEntries": last_count,
                    "lastLokCallback": trace[-1] if trace else None,
                    "phase": metrics.get("phase"),
                }
                break
        browser.drain(3.0)

        lines = console_lines(browser)
        result["consoleLines"] = len(lines)
        result["tail"] = lines[-120:]
        interesting = [
            line for line in lines
            if any(word in line["text"] for word in
                   ("futex", "proxy", "mailbox", "main thread", "block",
                    "wait", "join", "spawn"))]
        result["waitRelated"] = interesting[-80:]
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

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "wedge": result.get("wedge"),
        "consoleLines": result.get("consoleLines"),
        "waitRelated": len(result.get("waitRelated") or []),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
