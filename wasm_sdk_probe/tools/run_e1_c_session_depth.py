#!/usr/bin/env python3
"""Attribution probe: does E1-C's lifecycle failure depend on session depth?

E1-C runs all four phases inside ONE browser session (run_e1_c.py builds
session_class("cold") once).  On 2026-08-06 and again on 2026-08-07 the run died
with `init timed out after 120000 ms` at chrome cycle-06 and firefox warmup-08 --
the same two cases both times.  Counted in session order those are chrome's 30th
navigation and firefox's 22nd, and the matrix note that "a clean re-run of the
lifecycle phase passed every cycle" is consistent with that: lifecycle alone is
only 20 navigations, under both numbers.  The recorded attribution (host load)
does not survive the same two cases failing twice.

This probe repeats ONE identical cheap case in one session and reports the
elapsed time of every iteration.  It is built to print a number that can move:
if the hypothesis is right the failure lands near the same depth even though
nothing about the case changes, and any creep in the elapsed time before that is
visible rather than hidden behind a pass/fail.  If it runs clean to --iterations
then session depth is NOT the trigger and the cause lies in what the earlier
phases do, not in how many of them there were.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

from e1_support import write_json
from r7_support import evaluate, process_snapshot, wait_page
from run_browser_probe import (
    ChromeSession,
    FirefoxSession,
    free_port,
    wait_http,
    websocket_connect,
)


def tree_bytes(sample: dict) -> int:
    return sum(
        item.get("pssBytes") or item.get("rssBytes") or 0
        for item in sample.get("processes", [])
    )


# Mutable one-element box so the RUNGS query builders can see --generations
# without rewriting every builder's signature.
GENERATIONS = [16]

RUNGS = {
    # rung -> (page, query builder).  The full rung is the real harness; the
    # others strip the stack down so a reproduction can be attributed.
    "full": ("e1-editor-validation.html", lambda index, mib: {
        "scenario": "lifecycle", "fixture": "plain-grapheme",
        "repetition": 100 + index,
    }),
    # Not a ladder rung: ONE page load that drives N crash-recovery generations
    # inside it, on the shipped e1-editor-v1 artifact.  Every E1-C case
    # navigates once per generation, so the per-page cap has never been
    # exercised at any value -- including the 3 it is set to.  Use with
    # --iterations 1 --generations N.
    "generations": ("e1-editor-validation.html", lambda index, mib: {
        "scenario": "generations", "fixture": "plain-grapheme",
        "generations": GENERATIONS[0], "maxGenerations": GENERATIONS[0],
    }),
    "inert": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "inert", "n": index,
    }),
    "worker": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "worker", "n": index,
    }),
    "buffer": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "buffer", "bufferMib": mib, "n": index,
    }),
    # The engine's resource shape without the engine: -sPTHREAD_POOL_SIZE=7 plus
    # the SDK worker itself is 8 workers sharing -sTOTAL_MEMORY=1GB.  The single
    # worker / 256 MiB rungs do not cover that, so on their own they cannot rule
    # out "too many workers" or "too much shared memory" as the trigger.
    "pool": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "pool", "bufferMib": mib, "poolWorkers": 8, "n": index,
    }),
    # The one allocation the buffer/pool rungs cannot stand in for: the engine's
    # pthread runtime allocates its 1 GiB as a *shared WebAssembly.Memory*
    # (-sTOTAL_MEMORY=1GB, initial == maximum), not as a SharedArrayBuffer.
    # Wasm memories are reserved with guard regions in the wasm engine's own
    # per-process accounting; plain SharedArrayBuffers are not.  If this rung
    # wedges at the same depth as `full`, the budget being exhausted is the
    # browser's wasm-memory accounting and LibreOffice is not involved at all.
    "wasmmem": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "wasmmem", "bufferMib": mib, "n": index,
    }),
    # Fetch and compile the real shipped engine wasm (115 MB) in the control
    # worker, without instantiating it.  Splits "compiled code accumulates per
    # navigation" from "the engine runs".  wasmmem passed 60/60 on both
    # browsers, so memory accounting alone is excluded; this is the next
    # cheapest layer that needs no build.
    "compile": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "compile", "n": index,
    }),
    # The engine's exact load path (classic worker + importScripts + emscripten
    # instantiation with the 1 GiB shared memory and 7-thread pool) without any
    # LibreOffice code: a tiny module linked with link_r5_product's flags.
    # Needs `make e1-c-session-depth-minimal-assets` once.
    "minimal": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "minimal", "n": index,
    }),
    # The same load path against the real shipped probe.js/probe.wasm, stopping
    # after instantiation + oxsdk_abi_version: everything the full rung does
    # except oxsdk_engine_start and the startup resource packs.
    "realinstant": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "realinstant", "n": index,
    }),
    # The real SDK init chain (sdk-worker.js + manifest + module + startup
    # resource packs + oxsdk_engine_start) with no document ever opened: the
    # last layer between `realinstant` and `full`.
    "enginestart": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "enginestart", "n": index,
    }),
    # keepAlive variants: identical allocations, but nothing is terminated
    # explicitly -- navigation tears the workers down, exactly as it does for
    # the engine worker in the real harness.  If wasmmem-keep wedges where
    # wasmmem ran clean, the leak is in the browsers' navigation teardown of
    # shared wasm memories and no LibreOffice code is involved.
    "wasmmem-keep": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "wasmmem", "bufferMib": mib, "keepAlive": 1, "n": index,
    }),
    "pool-keep": ("e1-c-session-depth-control.html", lambda index, mib: {
        "mode": "pool", "bufferMib": mib, "poolWorkers": 8, "keepAlive": 1,
        "n": index,
    }),
}


def tree_extras(root_pid: int) -> dict:
    """Threads and virtual address space across the browser's process tree.

    finding 023 next-step 3: processCount and RSS/PSS are flat, so a leak
    would live in threads or in *reserved* address space -- wasm memories carry
    guard-region reservations that never show up in RSS.  maxVmsBytes is the
    single fattest process (the renderer under test), which is where a
    per-process reservation budget would fill up.
    """
    try:
        import psutil

        root = psutil.Process(root_pid)
        threads = 0
        vms = []
        fds = []
        for process in (root, *root.children(recursive=True)):
            threads += process.num_threads()
            vms.append(process.memory_info().vms)
            try:
                fds.append(process.num_fds())
            except psutil.Error:
                pass
        return {
            "threads": threads,
            "vmsBytes": sum(vms),
            "maxVmsBytes": max(vms, default=0),
            "fdCount": sum(fds),
            "maxProcessFdCount": max(fds, default=0),
        }
    except Exception:  # noqa: BLE001 - a missing sample must not kill the series
        return {
            "threads": None,
            "vmsBytes": None,
            "maxVmsBytes": None,
            "fdCount": None,
            "maxProcessFdCount": None,
        }


def rotate_to_fresh_tab(session) -> None:
    """Open a new tab, close the old one, continue in the new one.

    Handoff step 4: if the wedge does not follow us into fresh tabs, the
    exhausted budget is tab-scoped (navigation history of one tab); if it still
    lands at the same depth, it is renderer-process-scoped.

    FirefoxSession speaks WebDriver; ChromeSession is a CDP websocket bound to
    one page target, so a fresh tab there means a new target plus a new
    websocket, with Page/Runtime/Network re-enabled to match __init__.
    """
    if isinstance(session, ChromeSession):
        old_pages = [
            target for target in wait_http(f"{session.base_url}/json/list")
            if target["type"] == "page"
        ]
        created = session.call("Target.createTarget", {"url": "about:blank"})["targetId"]
        page = next(
            target for target in wait_http(f"{session.base_url}/json/list")
            if target.get("id") == created
        )
        old_websocket = session.websocket
        session.websocket = websocket_connect(
            page["webSocketDebuggerUrl"], origin="http://127.0.0.1"
        )
        session.next_id = 0
        session.call("Page.enable")
        session.call("Runtime.enable")
        session.call("Network.enable")
        session.call("Network.setCacheDisabled", {"cacheDisabled": True})
        for target in old_pages:
            session.call("Target.closeTarget", {"targetId": target["id"]})
        try:
            old_websocket.close()
        except Exception:  # noqa: BLE001 - the socket may already be gone
            pass
    else:
        new_handle = session.command("POST", "/window/new", {"type": "tab"})["handle"]
        session.command("DELETE", "/window", None)
        session.command("POST", "/window", {"handle": new_handle})


def one_navigation(
    session, base_url: str, index: int, timeout: float, rung: str, buffer_mib: int,
) -> dict:
    """One page load at the requested rung of the ladder, timed."""
    query = urlencode(RUNGS[rung][1](index, buffer_mib))
    before = process_snapshot(session.process.pid, {"checkpoint": f"before-{index:03d}"})
    started = time.monotonic()
    metrics = None
    # The wedge can surface below the page too: chrome's first observed failure
    # was the driver's own navigate() giving up, not an SDK timeout.  Recording
    # that as raw evidence matters more than propagating it -- a probe that dies
    # without writing its series destroys the measurement it exists to take.
    navigation_error = None
    try:
        session.navigate(f"{base_url}?{query}")
        deadline = started + timeout
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__e1_c || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.2)
    except Exception as error:  # noqa: BLE001 - raw failure evidence is required
        navigation_error = {"name": type(error).__name__, "message": str(error)}
    elapsed = time.monotonic() - started
    after = process_snapshot(session.process.pid, {"checkpoint": f"after-{index:03d}"})
    extras = tree_extras(session.process.pid)
    completed = bool(metrics and metrics.get("complete"))
    return {
        "index": index,
        "elapsedSeconds": round(elapsed, 3),
        "completed": completed,
        "pass": navigation_error is None and completed
        and (metrics or {}).get("pass") is True,
        "error": (metrics or {}).get("error"),
        "navigationError": navigation_error,
        "crossOriginIsolated": (metrics or {}).get("crossOriginIsolated"),
        "workers": (metrics or {}).get("workers"),
        "operations": len((metrics or {}).get("operations") or []),
        # A control rung that cannot show it did the thing is not a control.
        # Keep the last operation's payload so `buffer` can be seen to have
        # actually allocated, rather than silently degrading into `worker`.
        "lastOperation": ((metrics or {}).get("operations") or [None])[-1],
        "generationLimitProbe": (metrics or {}).get("generationLimitProbe"),
        "treeBytesBefore": tree_bytes(before),
        "treeBytesAfter": tree_bytes(after),
        "processCount": len(after.get("processes", [])),
        **{
            "treeThreads": extras["threads"],
            "treeVmsBytes": extras["vmsBytes"],
            "maxProcessVmsBytes": extras["maxVmsBytes"],
            "treeFdCount": extras["fdCount"],
            "maxProcessFdCount": extras["maxProcessFdCount"],
        },
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--rung", choices=tuple(RUNGS), default="full")
    parser.add_argument("--buffer-mib", type=int, default=256)
    parser.add_argument("--iterations", type=int, default=40)
    parser.add_argument(
        "--generations", type=int, default=16,
        help="for --rung generations: how many crash-recovery generations to "
        "drive inside ONE page, and what to set the session's own limit to.  "
        "The probe then asserts the (N+1)-th recovery is still refused with "
        "WORKER_GENERATION_LIMIT, so raising a cap cannot silently remove it",
    )
    parser.add_argument("--timeout-per-iteration", type=float, default=180)
    parser.add_argument(
        "--firefox-pref", action="append", default=[], metavar="NAME=VALUE",
        help="extra about:config pref for the firefox session (repeatable); "
        "values are parsed as JSON when possible, else kept as strings.  Used "
        "to move a suspected browser budget (e.g. dom.workers.maxPerDomain) "
        "and watch whether the wall moves with it.  Evidence lands under "
        "<rung>-pref/ so it never overwrites the stock series",
    )
    parser.add_argument(
        "--fresh-tab", action="store_true",
        help="open a new tab (and close the old one) before every navigation; "
        "evidence lands under <rung>-freshtab/ so it never overwrites the "
        "same-tab series",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "editor-validation"
        / "session-depth",
    )
    args = parser.parse_args()
    GENERATIONS[0] = args.generations
    rung_label = f"{args.rung}-freshtab" if args.fresh_tab else args.rung
    extra_prefs = {}
    for item in args.firefox_pref:
        name, _, raw = item.partition("=")
        try:
            extra_prefs[name] = json.loads(raw)
        except json.JSONDecodeError:
            extra_prefs[name] = raw
    if extra_prefs:
        rung_label = f"{rung_label}-pref"
    output = (args.evidence_root / rung_label / args.browser).resolve()
    # Never overwrite an earlier series: later runs land in attempt-NN, the
    # same convention run_e1_c.py uses.
    if (output / "result.json").exists():
        attempt = 2
        while (output / f"attempt-{attempt:02d}" / "result.json").exists():
            attempt += 1
        output = output / f"attempt-{attempt:02d}"
    output.mkdir(parents=True, exist_ok=True)

    port = free_port()
    # Server output goes to a real file, never a pipe.  This probe's own walls
    # (full 26/34, realinstant 54, minimal 55/62) were the request log filling
    # the unread 64 KiB stderr pipe: the handler thread then blocked inside
    # log_message() before sending the response body, every later fetch hung,
    # and init timed out at a deterministic depth.  Caught live on 2026-08-07:
    # serve.py handler threads in wchan=anon_pipe_write while chrome idled
    # (evidence/.../session-depth/pipe-forensics/).  The log doubles as the
    # per-navigation request-count evidence.
    serve_log_path = output / "serve.log"
    serve_log = open(serve_log_path, "w", buffering=1)
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(port)],
        cwd=project, stdout=serve_log, stderr=subprocess.STDOUT, text=True,
    )
    session = None
    iterations: list[dict] = []
    try:
        base_url = f"http://127.0.0.1:{port}/{RUNGS[args.rung][0]}"
        wait_page(base_url)
        if args.browser == "chrome":
            session = ChromeSession("cold")
        else:
            session = FirefoxSession("cold", extra_prefs=extra_prefs or None)
        for index in range(1, args.iterations + 1):
            if args.fresh_tab and index > 1:
                rotate_to_fresh_tab(session)
            entry = one_navigation(
                session, base_url, index, args.timeout_per_iteration,
                args.rung, args.buffer_mib,
            )
            entry["serveLogBytesAfter"] = serve_log_path.stat().st_size
            iterations.append(entry)
            print(json.dumps(entry, ensure_ascii=False), flush=True)
            if not entry["pass"]:
                break
    finally:
        if session is not None:
            session.close()
        server.terminate()
        server.wait(timeout=30)
        serve_log.close()

    failed = next((item for item in iterations if not item["pass"]), None)
    result = {
        "schemaVersion": 1,
        "release": "E1-C-session-depth-attribution",
        "browser": args.browser,
        "rung": rung_label,
        "browserVersion": getattr(session, "version", None),
        # A run that moved a pref must say so, or its wall would be quoted as
        # the stock browser's.
        "firefoxPrefs": extra_prefs or None,
        "freshTab": args.fresh_tab,
        "requestedIterations": args.iterations,
        "completedIterations": len(iterations),
        "firstFailureIndex": failed["index"] if failed else None,
        "firstFailureError": (
            failed.get("error") or failed.get("navigationError") if failed else None
        ),
        "elapsedSecondsSeries": [item["elapsedSeconds"] for item in iterations],
        "treeBytesAfterSeries": [item["treeBytesAfter"] for item in iterations],
        "treeThreadsSeries": [item["treeThreads"] for item in iterations],
        "maxProcessVmsBytesSeries": [
            item["maxProcessVmsBytes"] for item in iterations
        ],
        "maxProcessFdCountSeries": [
            item["maxProcessFdCount"] for item in iterations
        ],
        "serveLogBytesAfterSeries": [
            item.get("serveLogBytesAfter") for item in iterations
        ],
        "iterations": iterations,
        # Deliberately NOT a pass/fail gate.  This probe attributes; it does not
        # decide anything.  A clean run and a run that dies at 22 are both useful
        # results and neither is "the probe failing".
        "observation": (
            f"first failure at navigation {failed['index']}" if failed
            else f"no failure in {len(iterations)} navigations"
        ),
    }
    write_json(output / "result.json", result)
    print(json.dumps({
        "output": str(output / "result.json"),
        "browser": args.browser,
        "firstFailureIndex": result["firstFailureIndex"],
        "completedIterations": result["completedIterations"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
