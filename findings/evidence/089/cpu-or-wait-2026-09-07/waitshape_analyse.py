#!/usr/bin/env python3
"""
Step 1 analysis for finding 089 phase 2 (2026-09-07): re-derive, from the
already-banked run-1/run-2 sample streams of
findings/evidence/089/cpu-or-wait-2026-09-07/, per-GEN(5)-tid and full-tree
CPU/state/wchan/syscall/context-switch data over B(5) and H. No browser is
run by this script; it only reads run-<N>-samples.jsonl.gz and run-<N>-verdict.json.

Writes JSON artifacts into the same evidence directory (not into web/, dist/,
any profile, or any judge). This script itself is also copied into that
directory for the record.
"""
import gzip
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

EVDIR = Path("/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/cpu-or-wait-2026-09-07")


def load_samples(run):
    path = EVDIR / f"run-{run}-samples.jsonl.gz"
    ticks = []
    with gzip.open(path, "rt") as f:
        for line in f:
            ticks.append(json.loads(line))
    return ticks


def iter_thread_samples(ticks):
    """Yield (t, pid, proc_type, cmdline, tid, thread_dict) for every ok tick."""
    for tick in ticks:
        if tick.get("treeStatus") != "ok":
            continue
        t = tick["t"]
        for proc in tick.get("procs", []):
            pid = proc["pid"]
            ptype = proc.get("type")
            cmdline = proc.get("cmdline", "")
            for th in proc.get("threads", []):
                if th.get("gone"):
                    continue
                yield t, pid, ptype, cmdline, th


def in_window(t, window):
    return window[0] <= t <= window[1]


def analyse_run(run, verdict):
    ticks = load_samples(run)
    clk = verdict["clkTck"]
    H = verdict["H"]
    B5 = verdict["B5"]
    gen5_tids = {(g["pid"], g["tid"]) for g in verdict["gen5Tids"]}
    gen5_meta = {(g["pid"], g["tid"]): g for g in verdict["gen5Tids"]}

    # per (pid,tid) -> list of (t, utime, stime, state, wchan, syscall, vol, nonvol, ptype, comm, cmdline)
    series = defaultdict(list)
    proc_cmdlines = {}
    for t, pid, ptype, cmdline, th in iter_thread_samples(ticks):
        key = (pid, th["tid"])
        series[key].append({
            "t": t,
            "utime": th["utime"],
            "stime": th["stime"],
            "state": th["state"],
            "wchan": th.get("wchan"),
            "syscall": th.get("syscall"),
            "vol": th.get("voluntary_ctxt_switches"),
            "nonvol": th.get("nonvoluntary_ctxt_switches"),
            "comm": th.get("comm"),
        })
        proc_cmdlines[pid] = (ptype, cmdline)

    def window_stats(key, window):
        samples = [s for s in series[key] if in_window(s["t"], window)]
        if len(samples) < 2:
            return {"nSamples": len(samples), "note": "fewer than 2 samples in window"}
        samples.sort(key=lambda s: s["t"])
        cpu_delta = (samples[-1]["utime"] - samples[0]["utime"]) + (samples[-1]["stime"] - samples[0]["stime"])
        dur = samples[-1]["t"] - samples[0]["t"]
        rate = (cpu_delta / clk) / dur if dur > 0 else None
        state_hist = Counter(s["state"] for s in samples)
        wchan_counts = Counter(s["wchan"] for s in samples if s["wchan"] is not None)
        syscall_counts = Counter(s["syscall"] for s in samples if s["syscall"] is not None)
        vol_delta = samples[-1]["vol"] - samples[0]["vol"] if samples[-1]["vol"] is not None and samples[0]["vol"] is not None else None
        nonvol_delta = samples[-1]["nonvol"] - samples[0]["nonvol"] if samples[-1]["nonvol"] is not None and samples[0]["nonvol"] is not None else None
        return {
            "nSamples": len(samples),
            "windowSpanCoveredS": dur,
            "cpuDeltaTicks": cpu_delta,
            "cpuDeltaSeconds": cpu_delta / clk,
            "rate": rate,
            "stateHistogram": dict(state_hist),
            "wchanCounts": dict(wchan_counts),
            "syscallCounts": dict(syscall_counts),
            "ctxtDelta": {"voluntary": vol_delta, "nonvoluntary": nonvol_delta},
        }

    # --- Part A: GEN(5) contrast, B5 vs H ---
    gen5_contrast = []
    for key in sorted(gen5_tids):
        pid, tid = key
        meta = gen5_meta[key]
        b5 = window_stats(key, B5)
        h = window_stats(key, H)
        gen5_contrast.append({
            "pid": pid, "tid": tid, "comm": meta["comm"],
            "firstSeen": meta["firstSeen"], "lastSeen": meta["lastSeen"],
            "B5": b5, "H": h,
        })

    # --- Part B: full per-thread table over H, whole process tree ---
    full_table = []
    for key, samples in series.items():
        pid, tid = key
        ptype, cmdline = proc_cmdlines.get(pid, (None, None))
        h = window_stats(key, H)
        if h.get("nSamples", 0) == 0:
            continue
        full_table.append({
            "pid": pid, "tid": tid, "type": ptype,
            "comm": samples[0]["comm"],
            "inGen5": key in gen5_tids,
            "H": h,
        })
    full_table.sort(key=lambda r: (-(r["H"].get("rate") or 0)))

    # --- Part C: per-process summary over H ---
    proc_summary = defaultdict(lambda: {"threadCount": 0, "totalCpuSeconds": 0.0, "maxThreadRate": 0.0, "type": None, "cmdlineTail": None})
    for row in full_table:
        pid = row["pid"]
        ps = proc_summary[pid]
        ps["type"] = row["type"]
        ps["threadCount"] += 1
        cpu_s = row["H"].get("cpuDeltaSeconds") or 0.0
        ps["totalCpuSeconds"] += cpu_s
        rate = row["H"].get("rate") or 0.0
        if rate > ps["maxThreadRate"]:
            ps["maxThreadRate"] = rate
    for pid, ps in proc_summary.items():
        _, cmdline = proc_cmdlines.get(pid, (None, ""))
        ps["cmdlineTail"] = cmdline[-90:] if cmdline else ""

    return {
        "run": run,
        "clkTck": clk,
        "H": H,
        "B5": B5,
        "gen5Contrast": gen5_contrast,
        "fullThreadTableH": full_table,
        "processSummaryH": {str(pid): ps for pid, ps in sorted(proc_summary.items())},
        "totalTidsInTreeOverH": len(full_table),
        "totalTidsAtOrAboveTinyRate": sum(1 for r in full_table if (r["H"].get("rate") or 0) > 0.0005),
    }


def main():
    for run in (1, 2):
        verdict = json.load(open(EVDIR / f"run-{run}-verdict.json"))
        result = analyse_run(run, verdict)
        outpath = EVDIR / f"waitshape-run-{run}.json"
        outpath.write_text(json.dumps(result, indent=2))
        print(f"wrote {outpath} ({outpath.stat().st_size} bytes)")
        print(f"  run {run}: {result['totalTidsInTreeOverH']} tids in tree over H, "
              f"{result['totalTidsAtOrAboveTinyRate']} above 0.0005 cores/thread mean rate")


if __name__ == "__main__":
    main()
