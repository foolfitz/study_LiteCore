#!/usr/bin/env python3
"""Finding 037: is the stuck engine thread spinning, or is it blocked?

The call does not return.  That is all the evidence says so far, and the two
ways it can be true need different fixes and different next steps:

  spinning   the thread is executing, in a loop that never ends.  A CPU
             profile has samples for it, and with a build that keeps function
             names those samples name the loop.
  blocked    the thread is parked on a lock, a futex or a wait.  A CPU profile
             has no samples for it at all, and no amount of profiling will
             ever say more -- the question becomes what it is waiting for.

Chrome's CPU profiler distinguishes these two without any rebuild, which is why
this runs before asking for one.  The engine runs on an Emscripten pthread,
which is a Worker, so each candidate thread is its own CDP target; this
attaches at the browser level and profiles every worker target at once.

The shipped engine cannot reproduce the hang any more -- the finding 037 guard
is exactly the code that stops it -- so this drives the archived pre-guard
artifact through a repackaged profile.  Same bytes as the engine the hang was
measured on (ee185b3d), no rebuild involved.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from websockets.sync.client import connect as websocket_connect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent


class BrowserSession:
    """A second CDP connection, at the browser target rather than the page.

    Worker targets are only reachable from here, and messages to them carry a
    sessionId that ChromeSession.call() would discard.
    """

    def __init__(self, base_url: str):
        version = json.loads(
            urllib.request.urlopen(f"{base_url}/json/version").read())
        self.socket = websocket_connect(version["webSocketDebuggerUrl"],
                                        origin="http://127.0.0.1",
                                        max_size=64 * 1024 * 1024)
        self.next_id = 0
        # Events, kept rather than dropped.  Worker sessions are announced by
        # Target.attachedToTarget and nothing else; a reader that only matched
        # response ids threw them away, and the workers were then unreachable --
        # Target.attachToTarget on an id from Target.getTargets answers "no
        # target with given id found", because a page's workers are attached
        # through their parent, not by id from the browser.
        self.events: list[dict] = []

    def call(self, method, params=None, session=None, timeout=120):
        self.next_id += 1
        message_id = self.next_id
        payload = {"id": message_id, "method": method, "params": params or {}}
        if session:
            payload["sessionId"] = session
        self.socket.send(json.dumps(payload))
        while True:
            message = json.loads(self.socket.recv(timeout=timeout))
            if "id" not in message:
                self.events.append(message)
                continue
            if message["id"] != message_id:
                continue
            if "error" in message:
                raise RuntimeError(f"CDP {method}: {message['error']}")
            return message.get("result", {})

    def drain(self, seconds: float = 1.0) -> None:
        """Collect events that arrive on their own, with no request pending."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                message = json.loads(self.socket.recv(timeout=0.3))
            except Exception:
                continue
            if "id" not in message:
                self.events.append(message)

    def attached_sessions(self) -> list[dict]:
        seen = {}
        for event in self.events:
            if event.get("method") != "Target.attachedToTarget":
                continue
            params = event["params"]
            seen[params["sessionId"]] = params["targetInfo"]
        return [{"sessionId": sid, "target": info} for sid, info in seen.items()]

    def close(self):
        try:
            self.socket.close()
        except Exception:
            pass


def wait_for_the_hang(session, timeout: float) -> dict:
    """Return once the callback stream has been silent for a few seconds.

    The signal is the trace going quiet while the action is still outstanding,
    which is what the hang looks like from the page: no callback of any kind
    arrives again.  Waiting a fixed number of seconds instead would sometimes
    profile the run before it wedged.
    """
    deadline = time.monotonic() + timeout
    last_length, last_change = -1, time.monotonic()
    while time.monotonic() < deadline:
        metrics = evaluate(session, "globalThis.__e2_discovery || null") or {}
        trace = metrics.get("engineTrace") or []
        if len(trace) != last_length:
            last_length, last_change = len(trace), time.monotonic()
        elif last_length > 0 and time.monotonic() - last_change > 4:
            return {
                "traceEntries": last_length,
                "lastCallback": trace[-1] if trace else None,
                "quietSeconds": round(time.monotonic() - last_change, 1),
                "phase": metrics.get("phase"),
            }
        time.sleep(0.25)
    return {"traceEntries": last_length, "timedOutWaitingForQuiet": True}


def wait_for_checkpoint(session, name: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        metrics = evaluate(session, "globalThis.__e2_discovery || null") or {}
        if any(c.get("name") == name for c in metrics.get("checkpoints") or []):
            return True
        time.sleep(0.2)
    return False


def profile_workers(browser, seconds: float) -> list[dict]:
    samples = []
    for attached in browser.attached_sessions():
        target = attached["target"]
        if target["type"] not in ("worker", "shared_worker", "service_worker"):
            continue
        sid = attached["sessionId"]
        try:
            browser.call("Profiler.enable", session=sid, timeout=20)
            browser.call("Profiler.setSamplingInterval", {"interval": 200},
                         session=sid, timeout=20)
            browser.call("Profiler.start", session=sid, timeout=20)
            time.sleep(seconds)
            profile = browser.call("Profiler.stop", session=sid,
                                   timeout=60)["profile"]
        except Exception as error:  # a worker can die mid-attach
            samples.append({"url": target["url"][-70:], "error": str(error)[:120]})
            continue

        hits: dict[str, int] = {}
        for node in profile.get("nodes", []):
            if not node.get("hitCount"):
                continue
            frame = node["callFrame"]
            name = frame.get("functionName") or "(anonymous)"
            url = frame.get("url", "")
            hits[f"{name} @ {url[-40:]}" if url else name] = (
                hits.get(f"{name} @ {url[-40:]}" if url else name, 0)
                + node["hitCount"])
        # V8 reports idle time as samples in a pseudo-frame.  Counting those as
        # work reported every parked thread as "spinning" -- a verdict that came
        # out the same whichever answer was true, which is not a verdict.
        idle = sum(count for name, count in hits.items()
                   if name in ("(idle)", "(program)", "(root)",
                               "(garbage collector)"))
        working = sum(hits.values()) - idle
        samples.append({
            "url": target["url"][-70:],
            "workingSamples": working,
            "idleSamples": idle,
            "verdict": "executing" if working > idle else "parked",
            "top": sorted(hits.items(), key=lambda kv: -kv[1])[:8],
        })
    return samples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="paragraph-content")
    parser.add_argument("--cases", default="pc-plain,pc-image")
    parser.add_argument("--profile", default="e2-preguard-diagnostic")
    parser.add_argument("--profile-seconds", type=float, default=6.0)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument(
        "--output", type=Path,
        default=PROJECT.parent / "findings" / "evidence" / "sdk-e2" / "discovery"
        / "wedge-thread-state" / "chrome" / "result.json")
    args = parser.parse_args()

    server_port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(server_port)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = browser = None
    result: dict = {"schemaVersion": 1, "release": "finding-037-thread-state"}
    try:
        base = f"http://127.0.0.1:{server_port}/e2-format-discovery.html"
        wait_page(base)
        session = ChromeSession("cold")
        session.navigate(
            f"{base}?fixture={args.fixture}&mode=wedge-trace"
            f"&cases={args.cases}&profileOverride={args.profile}")

        # Attach BEFORE the hang, so the same worker set can be profiled
        # twice: once while the engine is alive and working normally, and once
        # while it is stuck.  The first is the control, and it has to come from
        # the same run -- a separate control run finished its case and tore its
        # workers down before the profiler could reach them.
        browser = BrowserSession(session.base_url)
        targets = browser.call("Target.getTargets")["targetInfos"]
        result["targets"] = [
            {"type": t["type"], "url": t["url"][-70:]} for t in targets]
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
                try:
                    browser.call("Target.setAutoAttach", auto_attach,
                                 session=attached["sessionId"], timeout=10)
                except Exception:
                    pass
            browser.drain(1.5)
        result["attachedSessions"] = [
            {"type": a["target"]["type"], "url": a["target"]["url"][-70:]}
            for a in browser.attached_sessions()]

        result["controlReached"] = wait_for_checkpoint(
            session, "readback-caret-only", args.timeout)
        result["controlProfiles"] = profile_workers(browser, 3.0)

        result["hang"] = wait_for_the_hang(session, args.timeout)
        result["profileRequested"] = args.profile
        result["hangProfiles"] = profile_workers(browser, args.profile_seconds)
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
        "hang": result.get("hang"),
        "control": [
            {k: v for k, v in s.items()
             if k in ("workingSamples", "idleSamples", "verdict", "error")}
            for s in result.get("controlProfiles", [])],
        "hang": [
            {k: v for k, v in s.items()
             if k in ("workingSamples", "idleSamples", "verdict", "error")}
            for s in result.get("hangProfiles", [])],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
