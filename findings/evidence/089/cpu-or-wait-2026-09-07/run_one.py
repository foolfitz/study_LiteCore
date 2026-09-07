#!/usr/bin/env python3
"""One run of TASK-2026-09-07-089-cpu-or-wait.md section 3.6.

Launches the probe (`probe_ods_on_profile.py`) as its own subprocess so its
pid is known exactly, samples every thread of the whole Chrome process tree
from before the browser exists until the probe exits (+2s), runs a best-effort
CDP cross-check in a background thread, writes the meta/verdict files, and
runs `analyse.py`'s pipeline over the result.

This script does not decide anything about section 6's clock windows beyond
checking them (see `clock_ok`) -- if the window is closed it refuses to start
and exits non-zero without touching the filesystem beyond a note.
"""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sample_threads  # noqa: E402
import analyse  # noqa: E402

PROJECT = HERE.parent.parent.parent.parent  # .../study_LiteCore
WASM_SDK_PROBE = PROJECT / "wasm_sdk_probe"
sys.path.insert(0, str(WASM_SDK_PROBE / "tools"))
from run_browser_probe import http_json, wait_http  # noqa: E402
from websockets.sync.client import connect as websocket_connect  # noqa: E402


# ---------------------------------------------------------------------------
# Section 6: clock windows
# ---------------------------------------------------------------------------

BLOCKED_WINDOWS = [((8, 10), (8, 45)), ((15, 40), (16, 15))]


def _in_any_window(dt: datetime) -> bool:
    m = dt.hour * 60 + dt.minute
    for (s, e) in BLOCKED_WINDOWS:
        if s[0] * 60 + s[1] <= m <= e[0] * 60 + e[1]:
            return True
    return False


def clock_ok(now: Optional[datetime] = None) -> tuple[bool, str]:
    now = now or datetime.now()
    later = now + timedelta(minutes=20)
    if _in_any_window(now) or _in_any_window(later):
        return False, (f"now={now.strftime('%H:%M')} or now+20min="
                       f"{later.strftime('%H:%M')} CST falls inside a "
                       f"blocked window")
    return True, "clear"


def git_status_porcelain() -> str:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT,
                         capture_output=True, text=True)
    return out.stdout


def count_other_chrome() -> int:
    return len(sample_threads.find_chrome_pids())


# ---------------------------------------------------------------------------
# CDP cross-check thread (C3, C4, and the phase-stamp poll)
# ---------------------------------------------------------------------------

class CdpCrossCheck:
    def __init__(self, probe_pid: int):
        self.probe_pid = probe_pid
        self.stop_event = threading.Event()
        self.phase_stamps: list[dict[str, Any]] = []
        self.c3_samples: list[dict[str, Any]] = []
        self.c4_samples: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.browser_pid: Optional[int] = None
        self.port: Optional[int] = None
        self.route: Optional[str] = None
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self, timeout: float = 15.0):
        self.stop_event.set()
        self.thread.join(timeout=timeout)

    def _find_browser(self, deadline: float) -> bool:
        while time.monotonic() < deadline and not self.stop_event.is_set():
            tree = sample_threads.discover_tree(self.probe_pid)
            if tree.get("status") == "ok":
                self.browser_pid = tree["browserPid"]
                self.route = tree["route"]
                cmdline = sample_threads.read_cmdline(self.browser_pid) or ""
                for token in cmdline.split(" "):
                    if token.startswith("--remote-debugging-port="):
                        self.port = int(token.split("=", 1)[1])
                return self.port is not None
            time.sleep(0.5)
        return False

    def _run(self):
        try:
            if not self._find_browser(deadline=time.monotonic() + 60):
                self.errors.append({"stage": "find-browser",
                                    "error": "browser/port not found within 60s"})
                return
            version = wait_http(f"http://127.0.0.1:{self.port}/json/version",
                                timeout=20)
            ws_url = version["webSocketDebuggerUrl"]
            ws = websocket_connect(ws_url, origin="http://127.0.0.1")
        except Exception as error:
            self.errors.append({"stage": "connect", "error": str(error)})
            return

        next_id = [0]

        def call(method: str, params: Optional[dict] = None,
                 session_id: Optional[str] = None, timeout: float = 10):
            next_id[0] += 1
            mid = next_id[0]
            msg = {"id": mid, "method": method, "params": params or {}}
            if session_id is not None:
                msg["sessionId"] = session_id
            ws.send(json.dumps(msg))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                raw = ws.recv(timeout=max(0.1, deadline - time.monotonic()))
                resp = json.loads(raw)
                if resp.get("id") == mid:
                    if "error" in resp:
                        raise RuntimeError(str(resp["error"]))
                    return resp.get("result", {})
            raise TimeoutError(f"{method} did not answer within {timeout}s")

        session_id = None
        try:
            targets = call("Target.getTargets")["targetInfos"]
            page = next(t for t in targets if t["type"] == "page")
            attach = call("Target.attachToTarget",
                          {"targetId": page["targetId"], "flatten": True})
            session_id = attach["sessionId"]
        except Exception as error:
            self.errors.append({"stage": "attach-page", "error": str(error)})

        last_c3c4 = 0.0
        last_phase = 0.0
        while not self.stop_event.is_set():
            now = time.monotonic()
            if session_id is not None and now - last_phase >= 2.0:
                last_phase = now
                try:
                    result = call(
                        "Runtime.evaluate",
                        {"expression": ("(() => { const r = window.__odsProbe; "
                                        "if (!r) return null; return {done: "
                                        "r.done, casesLength: (r.cases||[])."
                                        "length}; })()"),
                         "returnByValue": True}, session_id=session_id,
                        timeout=5)
                    value = (result.get("result") or {}).get("value")
                    self.phase_stamps.append({
                        "tMono": time.monotonic(), "tWall": time.time(),
                        "casesLength": (value or {}).get("casesLength"),
                        "done": (value or {}).get("done"),
                    })
                except Exception as error:
                    self.phase_stamps.append({
                        "tMono": time.monotonic(), "tWall": time.time(),
                        "casesLength": None, "done": None,
                        "error": str(error)})
            if now - last_c3c4 >= 10.0:
                last_c3c4 = now
                try:
                    info = call("SystemInfo.getProcessInfo", timeout=5)
                    self.c3_samples.append({"tMono": now, "result": info})
                except Exception as error:
                    self.c3_samples.append({"tMono": now, "error": str(error)})
                try:
                    targets = call("Target.getTargets", timeout=5)["targetInfos"]
                    worker_like = [t for t in targets if
                                  str(t.get("url", "")).endswith("sdk-worker.js")
                                  or str(t.get("url", "")).endswith("probe.js")]
                    self.c4_samples.append({
                        "tMono": now,
                        "targetCount": len(targets),
                        "workerLikeCount": len(worker_like),
                        "targets": [{"type": t.get("type"), "url": t.get("url"),
                                    "targetId": t.get("targetId")}
                                   for t in targets],
                    })
                except Exception as error:
                    self.c4_samples.append({"tMono": now, "error": str(error)})
            time.sleep(0.2)

        try:
            ws.close()
        except Exception:
            pass

    def as_dict(self) -> dict[str, Any]:
        return {
            "browserPid": self.browser_pid, "port": self.port, "route": self.route,
            "phaseStamps": self.phase_stamps, "c3Samples": self.c3_samples,
            "c4Samples": self.c4_samples, "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# /tmp cleanup (section 6)
# ---------------------------------------------------------------------------

def cleanup_tmp(window_start_wall: float, window_end_wall: float) -> list[str]:
    removed = []
    for pattern in ("/tmp/ods-decisive-*", "/tmp/wasm-sdk-probe-chrome-*"):
        for p in Path("/tmp").glob(Path(pattern).name):
            try:
                mtime = p.stat().st_mtime
            except FileNotFoundError:
                continue
            if window_start_wall - 5 <= mtime <= window_end_wall + 30:
                try:
                    if p.is_dir():
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        p.unlink()
                    removed.append(str(p))
                except Exception:
                    pass
    return removed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--profile", default="e2-editor-v12")
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, action="append", required=True)
    parser.add_argument("--open-timeout-ms", type=int, default=180000)
    parser.add_argument("--timeout", type=float, default=480)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--clk-tck", type=int, required=True)
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id

    ok, reason = clock_ok()
    if not ok:
        meta = {"status": "refused", "reason": reason,
               "checkedAtLocal": datetime.now().isoformat()}
        (out_dir / f"run-{run_id}-meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8")
        print(f"REFUSED (clock window): {reason}")
        return 3

    status_before = git_status_porcelain()
    other_chrome_before = count_other_chrome()
    window_start_wall = time.time()
    started_at_utc = datetime.now(timezone.utc)
    started_at_cst = datetime.now()

    probe_out = out_dir / f"run-{run_id}-probe.json"
    probe_log = out_dir / f"run-{run_id}-probe-stdout.log"
    samples_plain = out_dir / f"run-{run_id}-samples.jsonl"

    cmd = [sys.executable, "tools/probe_ods_on_profile.py",
          "--profile", args.profile,
          "--control", str(args.control)]
    for f in args.fixture:
        cmd += ["--fixture", str(f)]
    cmd += ["--open-timeout-ms", str(args.open_timeout_ms),
           "--timeout", str(args.timeout), "--out", str(probe_out)]

    with open(probe_log, "w") as logf:
        probe_proc = subprocess.Popen(cmd, cwd=WASM_SDK_PROBE, stdout=logf,
                                      stderr=subprocess.STDOUT)
    probe_pid = probe_proc.pid
    print(f"run {run_id}: probe pid {probe_pid}, cmd: {' '.join(cmd)}")

    cdp = CdpCrossCheck(probe_pid)
    cdp.start()

    exit_state = {"exit_t": None}

    def should_stop() -> bool:
        if probe_proc.poll() is not None:
            if exit_state["exit_t"] is None:
                exit_state["exit_t"] = time.monotonic()
            return time.monotonic() - exit_state["exit_t"] >= 2.0
        return False

    void_reason = None
    try:
        sampler_summary = sample_threads.run_loop(
            probe_pid=probe_pid, known_browser_pid=None, out_path=samples_plain,
            interval=args.interval, should_stop=should_stop,
            abort_if_no_tree_after=120.0)
    except sample_threads.NoBrowserError as error:
        void_reason = str(error)
        sampler_summary = {"status": "void-no-browser", "reason": void_reason}
        probe_proc.terminate()
        try:
            probe_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            probe_proc.kill()

    cdp.stop(timeout=15)

    try:
        probe_exit_code = probe_proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        probe_proc.kill()
        probe_exit_code = probe_proc.wait(timeout=10)

    completed_at_utc = datetime.now(timezone.utc)
    completed_at_cst = datetime.now()
    window_end_wall = time.time()
    status_after = git_status_porcelain()

    # gzip samples
    samples_gz = out_dir / f"run-{run_id}-samples.jsonl.gz"
    with open(samples_plain, "rb") as fin, gzip.open(samples_gz, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    samples_plain.unlink()

    removed_tmp = cleanup_tmp(window_start_wall, window_end_wall)

    meta = {
        "runId": run_id,
        "probePid": probe_pid,
        "probeExitCode": probe_exit_code,
        "probeCmd": cmd,
        "startedAtUtc": started_at_utc.isoformat(),
        "startedAtCst": started_at_cst.isoformat(),
        "completedAtUtc": completed_at_utc.isoformat(),
        "completedAtCst": completed_at_cst.isoformat(),
        "otherChromeProcessesAtStart": other_chrome_before,
        "gitStatusBefore": status_before,
        "gitStatusAfter": status_after,
        "sampler": sampler_summary,
        "voidReason": void_reason,
        "cdp": cdp.as_dict(),
        # Duplicated at the top level because analyse.py's
        # derive_case_boundaries() reads meta["phaseStamps"] directly (it is
        # meant to be usable standalone against a bare meta file, not coupled
        # to this script's own nesting choice for the rest of the CDP record).
        "phaseStamps": cdp.phase_stamps,
        "removedTmpPaths": removed_tmp,
        "clkTck": args.clk_tck,
        "interval": args.interval,
    }
    meta_path = out_dir / f"run-{run_id}-meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    # guard: only new files under our own directory, or the soak's own paths
    before_lines = set(l for l in status_before.splitlines() if l.strip())
    after_lines = set(l for l in status_after.splitlines() if l.strip())
    new_lines = after_lines - before_lines
    bad = []
    for line in new_lines:
        path_part = line[3:] if len(line) > 3 else line
        if (path_part.startswith("findings/evidence/089/cpu-or-wait-2026-09-07/")
                or path_part.startswith("findings/evidence/queue-v12-cutover-soak/")):
            continue
        bad.append(line)
    if bad:
        print("GUARD VIOLATION -- unexpected git status delta:")
        for line in bad:
            print("  ", line)
        meta["guardViolation"] = bad
        meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    probe_report = None
    if probe_out.exists():
        probe_report = json.loads(probe_out.read_text(encoding="utf-8"))

    if void_reason is not None:
        verdict = {"status": "void", "reason": void_reason}
    else:
        verdict = analyse.full_analysis(samples_gz, meta, probe_report,
                                        args.clk_tck)
    verdict_path = out_dir / f"run-{run_id}-verdict.json"
    verdict_path.write_text(json.dumps(verdict, indent=2, default=str) + "\n",
                            encoding="utf-8")

    print(f"run {run_id}: status={verdict.get('status')} "
         f"outcome={verdict.get('outcome')} reason={verdict.get('reason')}")
    return 0 if not bad else 4


if __name__ == "__main__":
    raise SystemExit(main())
