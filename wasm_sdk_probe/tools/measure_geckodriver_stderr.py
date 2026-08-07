#!/usr/bin/env python3
"""How many bytes does geckodriver actually write to stderr per unit of work?

finding 014's 2026-08-04 evidence was taken while `run_browser_probe.py` spawned
geckodriver with `Popen(stderr=PIPE)` and nothing ever read it.  geckodriver
forwards the browser's own chatter onto that pipe, so the third unread pipe of
finding 023 was live for the whole R7/R8 campaign -- and a 64 KiB pipe that
nobody drains blocks its writer, which is exactly how 023 wedges a run at a
deterministic depth.  Whether that pipe could have *reached* 64 KiB during those
runs is an arithmetic question nobody has answered, so 014's Firefox-only walls
still carry an unexcluded alternative explanation.

This probe answers it by measurement rather than by argument: drive the real
R7-D `s2-fresh` page through a geckodriver whose stderr goes to a real file, and
count the bytes.  It reports bytes per batch and per lifecycle cycle, and the
cycle depth at which an unread 64 KiB pipe would have blocked.

Two log levels are measured because `--log error` was added by the same
2026-08-07 change that switched to DEVNULL; the 2026-08-04 runs may have been at
geckodriver's default level, which is far chattier.  Quoting only the quiet
number would understate the confound it exists to bound.

The probe is built to print a number that can move: if the answer were
structurally zero (nothing is ever written) the byte counts would be flat at 0
across both levels, which is itself a reportable result rather than a silent
pass.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from e1_support import write_json
from r7_support import wait_page
from run_browser_probe import free_port, http_json, wait_http

PIPE_CAPACITY_BYTES = 65536


class InstrumentedFirefox:
    """A minimal FirefoxSession whose geckodriver stderr lands in a file.

    Deliberately not a subclass: FirefoxSession hard-codes DEVNULL (that is the
    finding 023 fix and must stay), and the point here is to measure what that
    fix throws away.
    """

    def __init__(self, log_path: Path, log_level: str | None):
        geckodriver = shutil.which("geckodriver") or "/snap/bin/geckodriver"
        if not Path(geckodriver).exists():
            raise RuntimeError("geckodriver is unavailable")
        self.port = free_port()
        command = [geckodriver, "--port", str(self.port)]
        if log_level:
            command.extend(["--log", log_level])
        self.log_path = log_path
        self.log_file = open(log_path, "wb")
        self.process = subprocess.Popen(
            command, stdout=self.log_file, stderr=subprocess.STDOUT,
        )
        self.base_url = f"http://127.0.0.1:{self.port}"
        wait_http(f"{self.base_url}/status")
        response = http_json("POST", f"{self.base_url}/session", {
            "capabilities": {
                "alwaysMatch": {
                    "browserName": "firefox",
                    "moz:firefoxOptions": {
                        "args": ["-headless"],
                        # The same cold-cache prefs run_browser_probe.py uses for
                        # session_class("cold"); cache state changes how many
                        # requests -- and therefore how much chatter -- a
                        # navigation produces.
                        "prefs": {
                            "browser.shell.checkDefaultBrowser": False,
                            "browser.startup.page": 0,
                            "browser.cache.disk.enable": False,
                            "browser.cache.memory.enable": False,
                            "network.http.use-cache": False,
                        },
                    },
                }
            }
        }, timeout=180)["value"]
        self.session_id = response["sessionId"]
        self.version = response["capabilities"].get("browserVersion", "unknown")

    def bytes_written(self) -> int:
        return self.log_path.stat().st_size

    def command(self, method: str, suffix: str, payload: object | None = None):
        return http_json(
            method, f"{self.base_url}/session/{self.session_id}{suffix}",
            payload, timeout=180,
        )["value"]

    def navigate(self, url: str) -> None:
        self.command("POST", "/url", {"url": url})

    def evaluate(self, script: str):
        return self.command("POST", "/execute/sync", {"script": script, "args": []})

    def close(self) -> None:
        try:
            http_json("DELETE", f"{self.base_url}/session/{self.session_id}")
        except Exception:  # noqa: BLE001 - teardown must not lose the measurement
            pass
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=10)
        self.log_file.close()


def run_batch(session: InstrumentedFirefox, base_url: str, cycles: int,
              timeout: float) -> dict:
    """One R7-D s2-fresh batch: `cycles` fresh engines, each opened and closed."""
    query = f"scenario=s2-fresh&cycles={cycles}&sampleDwellMs=1100"
    before = session.bytes_written()
    started = time.monotonic()
    session.navigate(f"{base_url}?{query}")
    metrics = None
    deadline = started + timeout
    while time.monotonic() < deadline:
        metrics = session.evaluate("return globalThis.__r7_longevity || null;")
        if metrics and metrics.get("complete"):
            break
        time.sleep(0.5)
    after = session.bytes_written()
    return {
        "cycles": cycles,
        "elapsedSeconds": round(time.monotonic() - started, 3),
        "complete": bool(metrics and metrics.get("complete")),
        "pagePass": (metrics or {}).get("pass"),
        "workers": (metrics or {}).get("workers"),
        "lifecycleCycles": len((metrics or {}).get("lifecycle") or []),
        "stderrBytesBefore": before,
        "stderrBytesAfter": after,
        "stderrBytesDelta": after - before,
    }


def measure(level: str | None, base_url: str, batches: int, cycles: int,
            timeout: float, output: Path) -> dict:
    log_path = output / f"geckodriver-{level or 'default'}.log"
    session = InstrumentedFirefox(log_path, level)
    entries = []
    try:
        startup_bytes = session.bytes_written()
        for _ in range(batches):
            entry = run_batch(session, base_url, cycles, timeout)
            entries.append(entry)
            print(json.dumps({"level": level or "default", **entry},
                             ensure_ascii=False), flush=True)
    finally:
        session.close()
    work_bytes = sum(item["stderrBytesDelta"] for item in entries)
    done_cycles = sum(item["lifecycleCycles"] for item in entries)
    per_cycle = work_bytes / done_cycles if done_cycles else None
    # The 2026-08-04 s2-fresh runs died at cumulative cycle 36 (5-cycle batches)
    # and 38 (10-cycle batches).  A pipe explanation has to put 64 KiB inside
    # that many cycles, counting the one-off startup chatter once per browser
    # process (the batched runner starts a fresh one per batch).
    return {
        "logLevel": level or "default",
        "browserVersion": session.version,
        "startupBytes": startup_bytes,
        "workBytes": work_bytes,
        "cyclesMeasured": done_cycles,
        "bytesPerCycle": round(per_cycle, 1) if per_cycle else None,
        "cyclesToFill64KiB": (
            round((PIPE_CAPACITY_BYTES - startup_bytes) / per_cycle, 1)
            if per_cycle else None
        ),
        "batches": entries,
        "logPath": str(log_path),
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", type=int, default=2)
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument(
        "--log-level", action="append", default=None,
        help="geckodriver --log level to measure (repeatable); 'default' means "
        "pass no --log flag at all.  Defaults to both 'default' and 'error'.",
    )
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r7"
        / "geckodriver-stderr-volume",
    )
    args = parser.parse_args()
    levels = args.log_level or ["default", "error"]
    output = args.output.resolve()
    if (output / "result.json").exists():
        attempt = 2
        while (output / f"attempt-{attempt:02d}" / "result.json").exists():
            attempt += 1
        output = output / f"attempt-{attempt:02d}"
    output.mkdir(parents=True, exist_ok=True)

    port = free_port()
    # This probe exists because of an unread pipe; it does not get to have one.
    serve_log_path = output / "serve.log"
    serve_log = open(serve_log_path, "w", buffering=1)
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(port)],
        cwd=project, stdout=serve_log, stderr=subprocess.STDOUT, text=True,
    )
    measurements = []
    try:
        base_url = f"http://127.0.0.1:{port}/r7-longevity.html"
        wait_page(base_url)
        for level in levels:
            measurements.append(measure(
                None if level == "default" else level,
                base_url, args.batches, args.cycles, args.timeout, output,
            ))
    finally:
        server.terminate()
        server.wait(timeout=30)
        serve_log.close()

    result = {
        "schemaVersion": 1,
        "release": "finding-014-geckodriver-stderr-volume",
        "pipeCapacityBytes": PIPE_CAPACITY_BYTES,
        "workload": "R7-D s2-fresh page, fresh engine per cycle",
        "measurements": measurements,
        # No pass/fail: this probe bounds a confound, it does not decide
        # anything.  Both "far too little to matter" and "easily enough" are
        # useful answers.
        "observation": "; ".join(
            f"{item['logLevel']}: {item['bytesPerCycle']} B/cycle, "
            f"64 KiB after {item['cyclesToFill64KiB']} cycles"
            for item in measurements
        ),
    }
    write_json(output / "result.json", result)
    print(json.dumps({"output": str(output / "result.json"),
                      "observation": result["observation"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
