#!/usr/bin/env python3
"""Per-thread /proc sampler for TASK-2026-09-07-089-cpu-or-wait.md, section 3.1.

Samples EVERY thread of EVERY process in the Chrome tree rooted at a given
probe (or browser) pid, every `--interval` seconds, for the life of the
browser. Deliberately does not select a thread: section 2.3 of the protocol
requires the central verdict to be answerable without having identified
anything, so every tid seen is recorded.

Also implements the R-D red case (section 7): a sampler pointed at a pid with
no Chrome descendant must report status "no-tree" and exit non-zero -- not a
clean file of zeros. See `main()` below.

This file is imported by `run_one.py` and `idle_control.py` (same code, same
instrument, so a control and a measurement run share one implementation) and
is also runnable stand-alone for the red case.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Process discovery (section 2.2, C1/C2)
# ---------------------------------------------------------------------------

def _pgrep_x(name: str) -> list[int]:
    try:
        out = subprocess.run(["pgrep", "-x", name], capture_output=True,
                              text=True, timeout=5)
    except Exception:
        return []
    if out.returncode not in (0, 1):
        return []
    return [int(x) for x in out.stdout.split() if x.strip()]


def read_proc_stat_field4_ppid(pid: int) -> Optional[int]:
    """ppid from /proc/<pid>/stat, field 4. `comm` can hold ')' or spaces, so
    split after the LAST ')', matching the protocol's parser for task/stat."""
    try:
        raw = open(f"/proc/{pid}/stat", "rb").read().decode("utf-8", "replace")
        rest = raw[raw.rindex(")") + 2:].split()
        return int(rest[1])  # field 4 overall = rest[1] after the split at ')'
    except Exception:
        return None


def read_cmdline(pid: int) -> Optional[str]:
    try:
        raw = open(f"/proc/{pid}/cmdline", "rb").read()
        return raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()
    except Exception:
        return None


def classify(pid: int) -> str:
    cmd = read_cmdline(pid) or ""
    for token in cmd.split(" "):
        if token.startswith("--type="):
            return token[len("--type="):]
    return "browser"


def find_chrome_pids() -> list[int]:
    pids = set(_pgrep_x("chrome")) | set(_pgrep_x("google-chrome"))
    return sorted(pids)


def closure_from(seed_pids: set[int], chrome_pids: list[int]) -> set[int]:
    """ppid closure over `chrome_pids`, seeded at `seed_pids` (C1's browser
    pid plus, for robustness, itself). Renderers are forked from a zygote
    whose parent is the browser, so this needs to iterate to a fixpoint, not
    stop at one hop."""
    tree = set(seed_pids)
    changed = True
    while changed:
        changed = False
        for p in chrome_pids:
            if p in tree:
                continue
            ppid = read_proc_stat_field4_ppid(p)
            if ppid is not None and ppid in tree:
                tree.add(p)
                changed = True
    return tree


def discover_tree(probe_pid: int) -> dict[str, Any]:
    """C1 (primary, exact) + the ppid closure. Returns a dict with either
    status 'ok' (browserPid, route, treePids) or status 'no-tree'."""
    chrome_pids = find_chrome_pids()
    if not chrome_pids:
        return {"status": "no-tree", "reason": "no chrome/google-chrome pids"}
    direct = [p for p in chrome_pids if read_proc_stat_field4_ppid(p) == probe_pid]
    if direct:
        browser_pid = direct[0]
        route = "C1-direct-ppid"
    else:
        grand = [p for p in chrome_pids
                 if (gp := read_proc_stat_field4_ppid(p)) is not None
                 and read_proc_stat_field4_ppid(gp) == probe_pid]
        if grand:
            browser_pid = grand[0]
            route = "C1-grandparent-no-exec"
        else:
            return {"status": "no-tree",
                    "reason": "chrome pids exist but none are descendants "
                              "of the probe pid (direct or grandparent)"}
    tree = closure_from({browser_pid}, chrome_pids)
    return {"status": "ok", "browserPid": browser_pid, "route": route,
            "treePids": sorted(tree)}


def tree_from_known_browser_pid(browser_pid: int) -> dict[str, Any]:
    """For callers (idle_control.py) that already hold the exact browser pid
    from their own subprocess.Popen and do not need to search for it."""
    chrome_pids = find_chrome_pids()
    if browser_pid not in chrome_pids:
        return {"status": "no-tree",
                "reason": f"known browser pid {browser_pid} not found among "
                          f"chrome/google-chrome pids {chrome_pids}"}
    tree = closure_from({browser_pid}, chrome_pids)
    return {"status": "ok", "browserPid": browser_pid, "route": "known-pid",
            "treePids": sorted(tree)}


# ---------------------------------------------------------------------------
# Per-thread reads (section 3.1)
# ---------------------------------------------------------------------------

def read_task_stat(pid: int, tid: int) -> Optional[dict[str, Any]]:
    try:
        raw = open(f"/proc/{pid}/task/{tid}/stat", "rb").read().decode(
            "utf-8", "replace")
    except (FileNotFoundError, ProcessLookupError):
        return None
    except Exception as error:
        return {"readError": str(error)}
    try:
        comm = raw[raw.index("(") + 1:raw.rindex(")")]
        rest = raw[raw.rindex(")") + 2:].split()   # rindex, not index
        state = rest[0]        # field  3   R running, S sleep, D uninterruptible
        utime = int(rest[11])  # field 14   clock ticks
        stime = int(rest[12])  # field 15   clock ticks
        processor = int(rest[36])  # field 39
        return {"comm": comm, "state": state, "utime": utime, "stime": stime,
                "processor": processor, "rawStat": raw.rstrip("\n")}
    except Exception as error:
        return {"parseError": str(error), "rawStat": raw.rstrip("\n")}


def read_task_status_ctxt(pid: int, tid: int) -> dict[str, Any]:
    out = {"voluntary_ctxt_switches": None, "nonvoluntary_ctxt_switches": None}
    try:
        with open(f"/proc/{pid}/task/{tid}/status", "r") as fh:
            for line in fh:
                if line.startswith("voluntary_ctxt_switches:"):
                    out["voluntary_ctxt_switches"] = int(line.split(":")[1].strip())
                elif line.startswith("nonvoluntary_ctxt_switches:"):
                    out["nonvoluntary_ctxt_switches"] = int(line.split(":")[1].strip())
    except (FileNotFoundError, ProcessLookupError):
        return {"voluntary_ctxt_switches": "gone",
                "nonvoluntary_ctxt_switches": "gone"}
    except Exception as error:
        return {"readError": str(error)}
    return out


def read_wchan(pid: int, tid: int) -> Any:
    try:
        v = open(f"/proc/{pid}/task/{tid}/wchan", "r").read()
        return v if v else "0"
    except Exception as error:
        return {"readError": str(error)}


def read_syscall(pid: int, tid: int) -> Any:
    try:
        return open(f"/proc/{pid}/task/{tid}/syscall", "r").read().strip()
    except Exception as error:
        return {"readError": str(error)}


def read_vmrss(pid: int) -> Optional[int]:
    try:
        with open(f"/proc/{pid}/status", "r") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])  # kB
    except Exception:
        return None
    return None


def list_tasks(pid: int) -> list[int]:
    try:
        return [int(x) for x in __import__("os").listdir(f"/proc/{pid}/task")]
    except (FileNotFoundError, ProcessLookupError):
        return []
    except Exception:
        return []


def sample_tick(t: float, tree_pids: list[int]) -> dict[str, Any]:
    """One tick over the whole tree. Returns a row for run-<N>-samples.jsonl."""
    procs = []
    for pid in sorted(tree_pids):
        proc_row: dict[str, Any] = {
            "pid": pid,
            "cmdline": read_cmdline(pid),
            "type": classify(pid),
            "vmRssKb": read_vmrss(pid),
            "threads": [],
        }
        for tid in sorted(list_tasks(pid)):
            st = read_task_stat(pid, tid)
            if st is None:
                proc_row["threads"].append({"tid": tid, "gone": True})
                continue
            ctxt = read_task_status_ctxt(pid, tid)
            proc_row["threads"].append({
                "tid": tid,
                **st,
                **ctxt,
                "wchan": read_wchan(pid, tid),
                "syscall": read_syscall(pid, tid),
            })
        procs.append(proc_row)
    return {"t": t, "procs": procs}


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------

def run_loop(
    *,
    probe_pid: Optional[int],
    known_browser_pid: Optional[int],
    out_path: Path,
    interval: float = 0.5,
    duration: Optional[float] = None,
    should_stop: Optional[Callable[[], bool]] = None,
    abort_if_no_tree_after: Optional[float] = None,
) -> dict[str, Any]:
    """Sample every `interval` seconds until `should_stop()` is true (checked
    each tick) or `duration` seconds have elapsed (whichever governs -- both
    may be given; the loop stops at the first satisfied condition).

    `abort_if_no_tree_after`: if given and no chrome tree has EVER been found
    by this many seconds since the loop started, raises `NoBrowserError`
    instead of continuing -- used by run_one.py's 120 s wait-for-browser rule.
    It is NOT the same thing as the end-of-run "no-tree" verdict below, which
    applies to a loop that ran to its own natural stopping condition and found
    nothing across the whole of it (the R-D red case).

    Writes one JSON object per line to `out_path` (plain jsonl; gzip is the
    caller's job). Returns a summary dict: status "ok" or "no-tree", tick
    counts, and (if ever found) the last known tree.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    next_t = start
    ticks = 0
    ticks_with_tree = 0
    last_tree: Optional[dict[str, Any]] = None
    lag_ms_max = 0.0
    with open(out_path, "w") as fh:
        while True:
            now = time.monotonic()
            if now < next_t:
                time.sleep(next_t - now)
            sample_time = time.monotonic()
            lag_ms = (sample_time - next_t) * 1000.0

            if probe_pid is not None:
                tree = discover_tree(probe_pid)
            else:
                tree = tree_from_known_browser_pid(known_browser_pid)  # type: ignore[arg-type]

            # `t` is an ABSOLUTE time.monotonic() value, not relative to this
            # loop's own start -- so it lines up directly against the CDP
            # cross-check thread's phase-stamp timestamps (run_one.py writes
            # those with the same clock), which is what analyse.py uses to
            # place case boundaries without hardcoding anything about timing.
            if tree.get("status") == "ok":
                ticks_with_tree += 1
                last_tree = tree
                row = sample_tick(sample_time, tree["treePids"])
                row["sampleLagMs"] = round(lag_ms, 3)
                row["treeStatus"] = "ok"
                row["route"] = tree.get("route")
            else:
                row = {"t": sample_time, "sampleLagMs": round(lag_ms, 3),
                       "treeStatus": "empty", "reason": tree.get("reason")}

            fh.write(json.dumps(row) + "\n")
            fh.flush()
            ticks += 1
            lag_ms_max = max(lag_ms_max, lag_ms)

            elapsed = sample_time - start
            if (abort_if_no_tree_after is not None and ticks_with_tree == 0
                    and elapsed >= abort_if_no_tree_after):
                raise NoBrowserError(
                    f"no chrome tree found after {elapsed:.1f}s "
                    f"(limit {abort_if_no_tree_after}s)")

            next_t += interval

            stop = False
            if duration is not None and elapsed >= duration:
                stop = True
            if should_stop is not None and should_stop():
                stop = True
            if stop:
                break

    status = "ok" if ticks_with_tree > 0 else "no-tree"
    return {"status": status, "ticks": ticks, "ticksWithTree": ticks_with_tree,
            "lastTree": last_tree, "maxSampleLagMs": round(lag_ms_max, 3)}


class NoBrowserError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# CLI (used directly for the R-D red case, and available for manual use)
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-pid", type=int, required=True,
                        help="find the Chrome tree as a descendant of this pid")
    parser.add_argument("--out", type=Path, required=True,
                        help="jsonl output path (plain text; gzip separately)")
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--duration", type=float, default=None,
                        help="stop after this many seconds")
    parser.add_argument("--until-pid-exits", type=int, default=None,
                        help="stop 2s after this pid no longer exists")
    args = parser.parse_args()

    if args.duration is None and args.until_pid_exits is None:
        parser.error("one of --duration or --until-pid-exits is required")

    should_stop = None
    if args.until_pid_exits is not None:
        watched = args.until_pid_exits
        grace_deadline = {"t": None}

        def _pid_alive(p: int) -> bool:
            try:
                open(f"/proc/{p}/stat", "rb").close()
                return True
            except Exception:
                return False

        def _should_stop() -> bool:
            if _pid_alive(watched):
                return False
            if grace_deadline["t"] is None:
                grace_deadline["t"] = time.monotonic() + 2.0
            return time.monotonic() >= grace_deadline["t"]

        should_stop = _should_stop

    summary = run_loop(probe_pid=args.probe_pid, known_browser_pid=None,
                       out_path=args.out, interval=args.interval,
                       duration=args.duration, should_stop=should_stop)
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
