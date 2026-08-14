#!/usr/bin/env python3
"""Name the wait primitive the engine thread parks in (findings 037/032).

The pause readout on the pre-guard artifact (ee185b3d) caught the engine thread
parked at `memory.atomic.wait32`, six frames deep, reached through twenty-one
frames of application code.  That artifact has no name section, so those six
frames are `$func15470` and friends.

The trick this exploits: the idle pool threads sit at *the same six frames, at
byte-identical offsets* as the parked engine thread -- that was visible in the
control column of the same run.  So the wait primitive can be named without
reproducing any wedge at all: pause an idle thread on the diagnostic build,
which was linked with --profiling-funcs and does carry names.

What this does NOT do, and must not be read as doing: the two builds are
separate links, so **function indices do not correspond between them**.  This
names the shape of the wait, not the twenty-one application frames above it --
those stay index-only on ee185b3d, and naming them needs that build relinked
with --profiling-funcs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_wedge_thread_state import (  # noqa: E402
    BrowserSession, wait_for_checkpoint, wait_for_the_hang,
)
from r7_support import wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent


def pause_and_read(browser: BrowserSession, settle: float = 2.0) -> list[dict]:
    """Pause every worker target, read its frames, resume it."""
    out = []
    for attached in browser.attached_sessions():
        target = attached["target"]
        if target["type"] not in ("worker", "shared_worker", "service_worker"):
            continue
        sid = attached["sessionId"]
        record = {"url": target["url"][-60:], "sessionId": sid[:8],
                  "paused": False, "frames": [], "error": None}
        try:
            browser.call("Debugger.enable", session=sid, timeout=20)
            browser.call("Debugger.pause", session=sid, timeout=20)
            deadline = time.monotonic() + settle
            while time.monotonic() < deadline:
                browser.drain(0.3)
                event = next(
                    (e for e in reversed(browser.events)
                     if e.get("method") == "Debugger.paused"
                     and e.get("sessionId") == sid), None)
                if event is not None:
                    record["paused"] = True
                    record["frames"] = [
                        {"functionName": f.get("functionName") or "(anonymous)",
                         "offset": f.get("columnNumber")}
                        for f in event["params"].get("callFrames", [])]
                    break
        except Exception as error:
            record["error"] = str(error)[:160]
        finally:
            try:
                browser.call("Debugger.resume", session=sid, timeout=10)
            except Exception:
                pass
        out.append(record)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="e2-wait-diagnostic")
    parser.add_argument("--fixture", default="paragraph-content")
    parser.add_argument("--cases", default="pc-plain")
    parser.add_argument("--fixture-mode", default="wedge-trace")
    parser.add_argument("--timeout", type=float, default=240)
    parser.add_argument(
        "--wait-for-hang", action="store_true",
        help="pause while the engine is wedged rather than while it is alive")
    parser.add_argument("--pause-rounds", type=int, default=3)
    parser.add_argument("--pause-gap", type=float, default=8.0)
    parser.add_argument(
        "--output", type=Path,
        default=PROJECT.parent / "findings" / "evidence" / "sdk-e2" / "discovery"
        / "wait-primitive-names" / "chrome" / "result.json")
    args = parser.parse_args()

    profile_dir = PROJECT / "dist" / "profiles" / args.profile
    wasm = profile_dir / "probe.wasm"
    import hashlib
    digest = hashlib.sha256()
    with wasm.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = browser = None
    result = {"schemaVersion": 1, "release": "finding-032-wait-primitive-names",
              "profile": args.profile, "wasmSha256": digest.hexdigest()}
    try:
        base = f"http://127.0.0.1:{port}/e2-format-discovery.html"
        wait_page(base)
        session = ChromeSession("cold")
        session.navigate(
            f"{base}?fixture={args.fixture}&mode={args.fixture_mode}"
            + (f"&cases={args.cases}" if args.cases else "")
            + f"&profileOverride={args.profile}")
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
                try:
                    browser.call("Target.setAutoAttach", auto_attach,
                                 session=attached["sessionId"], timeout=10)
                except Exception:
                    pass
            browser.drain(1.5)

        if args.wait_for_hang:
            # The naming trick works on idle threads because they share the wait
            # site.  Finding 040's prediction is about the frame ABOVE that
            # shared prefix, which only exists while the engine is actually
            # wedged -- so this waits for the callback stream to go quiet
            # instead of for the engine to be healthy.
            result["hang"] = wait_for_the_hang(session, args.timeout)
            result["engineAlive"] = False
        else:
            result["engineAlive"] = wait_for_checkpoint(
                session, "readback-caret-only", args.timeout)
        # One pause cannot tell "parked" from "passing through": a thread caught
        # inside a call it completes a millisecond later looks identical to one
        # that never leaves.  Sample the same threads several times, spaced out,
        # and let the comparison say which it was.
        result["rounds"] = []
        for index in range(args.pause_rounds):
            if index:
                time.sleep(args.pause_gap)
            result["rounds"].append({
                "round": index,
                "atSeconds": round(index * args.pause_gap, 1),
                "workers": pause_and_read(browser),
            })
        result["workers"] = result["rounds"][0]["workers"]

        # A thread is "parked" here only if every round found it at the same
        # frames.  Anything else is a thread doing work.
        by_session: dict[str, list] = {}
        for entry in result["rounds"]:
            for worker in entry["workers"]:
                by_session.setdefault(worker["sessionId"], []).append(
                    [frame["functionName"] for frame in worker["frames"]]
                    if worker["paused"] else None)
        result["stability"] = {
            sid: {
                "roundsPaused": sum(1 for s in stacks if s is not None),
                "identicalAcrossRounds": (
                    len({json.dumps(s) for s in stacks if s is not None}) == 1
                    and sum(1 for s in stacks if s is not None) > 1),
                "depths": [None if s is None else len(s) for s in stacks],
                "top": next((s[0] for s in stacks if s), None),
                "bottomApplicationFrame": next(
                    (s[-3] for s in stacks if s and len(s) >= 3), None),
            }
            for sid, stacks in by_session.items()
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

    named = [w for w in result.get("workers", [])
             if any(f["functionName"].startswith("$func") is False
                    and f["functionName"] not in ("", "(anonymous)")
                    for f in w["frames"])]
    result["anyNamedFrames"] = bool(
        [w for w in result.get("workers", [])
         for f in w["frames"]
         if not f["functionName"].startswith("$func")
         and f["functionName"] not in ("(anonymous)",)])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "wasmSha256": result["wasmSha256"][:16] + "…",
        "engineAlive": result.get("engineAlive"),
        "workersPaused": sum(1 for w in result.get("workers", []) if w["paused"]),
        "stability": result.get("stability"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
