#!/usr/bin/env python3
"""Derive the cpu-or-wait verdict from a `sample_threads.py` stream.

TASK-2026-09-07-089-cpu-or-wait.md, sections 2-4 and 7. This file computes
GEN(5), B(5), H, the controls of section 3.4a, and the outcome of section 4 --
and implements the forced-thread/forced-tid modes used by the section 7 red
cases R-A, R-B, R-C (which re-derive over an EXISTING banked stream; they
never launch a browser).

Central design point (protocol section 2, 2.4): GEN(5) is identified without
naming any thread -- it is "every renderer thread not present when the
renderer was born, that is still present at the run's last sample". That
excludes the renderer's own persistent threads (main thread, compositor, IO
thread, ...) by construction, because those ARE present at the renderer's
first sample and GEN(5)'s threads are not. Cases 1-4's worker generations
also fail the "still present at the end" test, because they are disposed
before the run ends. No comm string is hardcoded to find GEN(5).

For the section 3.4a controls on cases 2/3/4 (which are not the hang, and
whose exact tid-level generation boundaries can be hard to pin down when two
cases are only ~1 s apart), this file uses TIME WINDOWS instead: case k's
"open window" is `[T_k, T_(k+1))`, where `T_k` comes from the CDP phase-stamp
poll (`window.__odsProbe.cases.length`, recorded every 2 s by run_one.py) --
and asks whether ANY renderer thread that is not one of the persistent
baseline threads accumulates CPU inside that time window. This does not
depend on cleanly clustering tids into "generation 2" versus "generation 3";
it only depends on the well-defined GEN(5)-style baseline exclusion, applied
per time window instead of per tid-cluster. This is recorded explicitly
below, and in RESULT.md, as the method -- not asserted as tid identity.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any, Optional

BUSY_BAR = 0.5
QUIET_BAR = 0.02
NOISE_BAR = 0.10
SUSTAINED_FRACTION = 0.90
SUB_WINDOW = 5.0


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_samples(path: Path) -> list[dict[str, Any]]:
    opener = gzip.open if str(path).endswith(".gz") else open
    rows = []
    with opener(path, "rt") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_json(path: Optional[Path]) -> Optional[dict[str, Any]]:
    if path is None or not Path(path).exists():
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Reshape: per (pid,tid) timelines, over "ok" ticks only
# ---------------------------------------------------------------------------

class ThreadTimeline:
    __slots__ = ("pid", "tid", "comm", "proc_type", "samples")

    def __init__(self, pid: int, tid: int):
        self.pid = pid
        self.tid = tid
        self.comm: Optional[str] = None
        self.proc_type: Optional[str] = None
        self.samples: list[tuple[float, dict[str, Any]]] = []  # (t, row)

    def first_seen(self) -> Optional[float]:
        return self.samples[0][0] if self.samples else None

    def last_seen(self) -> Optional[float]:
        return self.samples[-1][0] if self.samples else None


def build_timelines(rows: list[dict[str, Any]]):
    """Returns (timelines: dict[(pid,tid) -> ThreadTimeline], ok_ticks:
    list[float], empty_ticks: list[float], tick_count)."""
    timelines: dict[tuple[int, int], ThreadTimeline] = {}
    ok_ticks: list[float] = []
    empty_ticks: list[float] = []
    for row in rows:
        t = row["t"]
        if row.get("treeStatus") != "ok":
            empty_ticks.append(t)
            continue
        ok_ticks.append(t)
        for proc in row.get("procs", []):
            pid = proc["pid"]
            ptype = proc.get("type")
            for th in proc.get("threads", []):
                tid = th["tid"]
                key = (pid, tid)
                tl = timelines.get(key)
                if tl is None:
                    tl = ThreadTimeline(pid, tid)
                    timelines[key] = tl
                if tl.proc_type is None:
                    tl.proc_type = ptype
                if th.get("gone"):
                    continue  # a real read failure this tick; presence
                    # is still implied by list_tasks() having found it, but
                    # no CPU numbers exist for this tick -- skip the datum,
                    # not the tid.
                if tl.comm is None and th.get("comm"):
                    tl.comm = th["comm"]
                cpu_ticks = None
                if "utime" in th and "stime" in th:
                    cpu_ticks = th["utime"] + th["stime"]
                tl.samples.append((t, {
                    "cpu_ticks": cpu_ticks,
                    "state": th.get("state"),
                    "vol": th.get("voluntary_ctxt_switches"),
                    "nonvol": th.get("nonvoluntary_ctxt_switches"),
                    "processor": th.get("processor"),
                    # Best effort, section 3.1: recorded raw here so RESULT.md
                    # can show them under a heading that says they are not
                    # interpreted -- the verdict logic never reads these two.
                    "wchan": th.get("wchan"),
                    "syscall": th.get("syscall"),
                }))
    return timelines, ok_ticks, empty_ticks, len(rows)


# ---------------------------------------------------------------------------
# Rate / window helpers
# ---------------------------------------------------------------------------

def value_before_or_at(samples: list[tuple[float, dict]], t: float, field: str):
    """Last recorded value of `field` at or before time t. None if the tid
    had not yet appeared."""
    result = None
    for (st, row) in samples:
        if st <= t:
            if row.get(field) is not None:
                result = row[field]
        else:
            break
    return result


def cpu_delta(tl: ThreadTimeline, w_start: float, w_end: float) -> Optional[float]:
    """Delta CPU ticks accumulated in [w_start, w_end], or None if the tid
    has no data anywhere at/near this window (never existed there)."""
    v_end = value_before_or_at(tl.samples, w_end, "cpu_ticks")
    v_start = value_before_or_at(tl.samples, w_start, "cpu_ticks")
    if v_end is None:
        return None
    if v_start is None:
        v_start = 0  # born after w_start but before/at w_end: count from 0
    return max(0, v_end - v_start)


def rate(tl: ThreadTimeline, w_start: float, w_end: float, clk_tck: int) -> float:
    d = cpu_delta(tl, w_start, w_end)
    if d is None:
        return 0.0
    length = w_end - w_start
    if length <= 0:
        return 0.0
    return (d / clk_tck) / length


def alive_at(tl: ThreadTimeline, t: float, tolerance: float) -> bool:
    """True if some sample of this tid falls within `tolerance` of t."""
    for (st, _row) in tl.samples:
        if abs(st - t) <= tolerance:
            return True
    return False


def is_present_across(tl: ThreadTimeline, w_start: float, w_end: float) -> bool:
    return any(w_start <= st <= w_end for (st, _row) in tl.samples)


def state_histogram(tl: ThreadTimeline, w_start: float, w_end: float) -> dict[str, int]:
    hist: dict[str, int] = {}
    for (st, row) in tl.samples:
        if w_start <= st <= w_end:
            s = row.get("state") or "?"
            hist[s] = hist.get(s, 0) + 1
    return hist


def value_counts(tl: ThreadTimeline, w_start: float, w_end: float,
                 field: str) -> dict[str, int]:
    """Distinct values of `field` (wchan or syscall) over a window, with
    counts -- section 3.1: 'recorded raw... not interpreted in the verdict.'
    A dict of distinct values is the payload; picking 'the' value would be a
    summary."""
    counts: dict[str, int] = {}
    for (st, row) in tl.samples:
        if w_start <= st <= w_end:
            v = row.get(field)
            key = json.dumps(v) if not isinstance(v, str) else v
            counts[key] = counts.get(key, 0) + 1
    return counts


def ctxt_delta(tl: ThreadTimeline, w_start: float, w_end: float) -> dict[str, Any]:
    v_end = value_before_or_at(tl.samples, w_end, "vol")
    v_start = value_before_or_at(tl.samples, w_start, "vol")
    nv_end = value_before_or_at(tl.samples, w_end, "nonvol")
    nv_start = value_before_or_at(tl.samples, w_start, "nonvol")
    out = {}
    out["voluntary"] = (v_end - v_start) if (v_end is not None and v_start is not None) else None
    out["nonvoluntary"] = (nv_end - nv_start) if (nv_end is not None and nv_start is not None) else None
    return out


# ---------------------------------------------------------------------------
# Phase stamps -> T_k
# ---------------------------------------------------------------------------

def derive_case_boundaries(meta: Optional[dict[str, Any]], n_cases: int = 5):
    """T_k = earliest phase-stamp time where casesLength >= k. Returns a dict
    {1: T_1, ..., n_cases: T_n} with any unresolved k mapped to None, plus the
    raw phase-stamp list for the record."""
    # Accept either meta["phaseStamps"] (top level) or meta["cdp"]["phaseStamps"]
    # (run_one.py's own nesting under its CDP-cross-check record) -- this file
    # is meant to be usable standalone against a bare meta document, so it does
    # not assume which shape produced it.
    stamps = (meta or {}).get("phaseStamps") or (meta or {}).get("cdp", {}).get("phaseStamps") or []
    out: dict[int, Optional[float]] = {k: None for k in range(1, n_cases + 1)}
    for k in range(1, n_cases + 1):
        candidates = [s["tMono"] for s in stamps
                      if s.get("casesLength") is not None and s["casesLength"] >= k]
        out[k] = min(candidates) if candidates else None
    return out, stamps


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------

def find_renderer_timelines(timelines: dict[tuple[int, int], ThreadTimeline]):
    return {k: v for k, v in timelines.items() if v.proc_type == "renderer"}


def compute_gen5(renderer_tls: dict, t_max: float, tick_interval_guess: float):
    if not renderer_tls:
        return None, {}
    renderer_t0 = min(tl.first_seen() for tl in renderer_tls.values() if tl.samples)
    tol = max(tick_interval_guess * 1.5, 0.75)
    baseline = {k: tl for k, tl in renderer_tls.items()
                if alive_at(tl, renderer_t0, tol) and alive_at(tl, t_max, tol)}
    gen5 = {k: tl for k, tl in renderer_tls.items()
            if k not in baseline and alive_at(tl, t_max, tol)}
    info = {"renderer_t0": renderer_t0, "baseline_tid_count": len(baseline),
            "baseline_tids": [{"pid": p, "tid": t, "comm": tl.comm}
                               for (p, t), tl in baseline.items()]}
    return gen5, info


def guess_interval(ok_ticks: list[float]) -> float:
    if len(ok_ticks) < 2:
        return 0.5
    diffs = [b - a for a, b in zip(ok_ticks, ok_ticks[1:])]
    diffs.sort()
    return diffs[len(diffs) // 2] if diffs else 0.5


def max_gap_within(ok_ticks: list[float], empty_ticks: list[float],
                    w_start: float, w_end: float) -> tuple[float, int]:
    """Largest gap between consecutive OK ticks inside [w_start,w_end], and
    the count of empty-tree ticks that fall inside the window (both feed the
    'more than two consecutive samples missing inside H' void condition)."""
    inside = sorted(t for t in ok_ticks if w_start <= t <= w_end)
    gap = 0.0
    for a, b in zip(inside, inside[1:]):
        gap = max(gap, b - a)
    empties_inside = sum(1 for t in empty_ticks if w_start <= t <= w_end)
    return gap, empties_inside


def non_vacuous_probe_gate(probe: Optional[dict[str, Any]],
                           expected_sha: dict[str, str]) -> dict[str, Any]:
    """Section 4.5. Returns {'pass': bool, 'reasons': [...], 'case5Opened':
    bool|None}."""
    reasons = []
    if probe is None:
        return {"pass": False, "reasons": ["no probe report given"], "case5Opened": None}
    verdict = probe.get("verdict", {})
    if not verdict.get("controlOdtOpened"):
        reasons.append("verdict.controlOdtOpened is not true")
    sheets = verdict.get("spreadsheetsOpened", [])
    by_name = {s.get("name"): s for s in sheets}
    inputs_by_name = {i.get("path", "").rsplit("/", 1)[-1]: i for i in probe.get("inputs", [])}

    def sheet_for(fname: str):
        for s in sheets:
            if fname in (s.get("name") or ""):
                return s
        return None

    case2 = sheet_for("tdf149752-rows35.ods")
    case3 = sheet_for("tdf149752-index36-index235.ods")
    case4 = sheet_for("tdf161948_NaturalSortSaveLoad.ods")
    case5 = sheet_for("tdf149752-rows36.ods")
    for label, case in (("case2/rows35", case2), ("case3/index36-235", case3),
                        ("case4/tdf161948", case4)):
        if not case or not case.get("opened"):
            reasons.append(f"{label} did not open")

    case5_opened = bool(case5 and case5.get("opened"))
    if case5 is None:
        reasons.append("case5/rows36 not found in report")
    elif case5_opened:
        pass  # handled by caller: "the hang did not reproduce"
    else:
        err = case5.get("error") or {}
        if err.get("code") != "TIMEOUT":
            reasons.append(f"case5 error.code is {err.get('code')!r}, not TIMEOUT")
        msg = str(err.get("message") or "")
        if "180000" not in msg:
            reasons.append(f"case5 error message does not quote 180000: {msg!r}")

    if probe.get("openTimeoutMs") != 180000:
        reasons.append(f"openTimeoutMs is {probe.get('openTimeoutMs')!r}, not 180000")

    for entry in probe.get("inputs", []):
        fname = entry.get("path", "").rsplit("/", 1)[-1]
        exp = expected_sha.get(fname)
        if exp is not None and entry.get("sha256") != exp:
            reasons.append(f"inputs[].sha256 mismatch for {fname}: "
                           f"{entry.get('sha256')} != {exp}")

    return {"pass": len(reasons) == 0 or case5_opened, "reasons": reasons,
            "case5Opened": case5_opened}


EXPECTED_SHA_BY_FILENAME = {
    "tdf149752-rows35.ods": "a16ac9c5a1e450d6de1a5f586a1a18595dcabf72654dec4852d4aa2bf70524ee",
    "tdf149752-rows36.ods": "87b92dbeb653fefcfc9d3017ad646e25431fa51a6981f26220036881b7649a70",
    "tdf149752-index36-index235.ods": "ea10861849df43dbf4e54a1ac34a64434f262090a8b7ce74f835e1da39efc6e6",
    "tdf161948_NaturalSortSaveLoad.ods": "ef161c0600bace29e04e51b0e5f57204178a0a809686d7c947ea29648a3a02bc",
    "d1-anchors.odt": "f89f1e63dcf7c8956f3986257dd79a7ed02bb7825c844a63f73abc4a5c68d241",
}


def full_analysis(samples_path: Path, meta: Optional[dict], probe: Optional[dict],
                   clk_tck: int, force_tid: Optional[int] = None,
                   force_thread_comm: Optional[str] = None) -> dict[str, Any]:
    rows = load_samples(samples_path)
    timelines, ok_ticks, empty_ticks, tick_count = build_timelines(rows)
    result: dict[str, Any] = {
        "samplesFile": str(samples_path),
        "tickCount": tick_count,
        "okTickCount": len(ok_ticks),
        "emptyTickCount": len(empty_ticks),
    }
    if not ok_ticks:
        result["status"] = "void"
        result["reason"] = "no ok ticks in the sample stream (no-tree throughout)"
        return result

    t_min, t_max = min(ok_ticks), max(ok_ticks)
    result["tMin"] = t_min
    result["tMax"] = t_max
    interval_guess = guess_interval(ok_ticks)
    result["intervalGuess"] = interval_guess

    # ---- Red case R-A: a tid absent from every sample --------------------
    if force_tid is not None:
        present = any(tid == force_tid for (_pid, tid) in timelines)
        if not present:
            return {"status": "void",
                    "reason": f"tid {force_tid} is absent from every sample",
                    "forceTid": force_tid}
        # If it DID exist, fall through and treat it like a forced comm set
        # of exactly that tid, so R-A still exercises the busy-predicate path
        # if somehow given a real tid.
        forced = {k: v for k, v in timelines.items() if k[1] == force_tid}
    elif force_thread_comm is not None:
        forced = {k: v for k, v in timelines.items() if v.comm == force_thread_comm}
        if not forced:
            return {"status": "void",
                    "reason": f"no thread with comm={force_thread_comm!r} in "
                              f"any sample",
                    "forceThreadComm": force_thread_comm}
    else:
        forced = None

    # ---- §4.5 non-vacuity gate --------------------------------------------
    gate = non_vacuous_probe_gate(probe, EXPECTED_SHA_BY_FILENAME)
    result["probeGate"] = gate
    if gate.get("case5Opened"):
        result["status"] = "hang-did-not-reproduce"
        result["reason"] = ("case 5 (rows36) OPENED in this run; the hang did "
                            "not reproduce on this date. No CPU-vs-wait claim "
                            "is made.")
        return result
    if not gate["pass"]:
        result["status"] = "void"
        result["reason"] = "probe report failed the section 4.5 non-vacuity gate: " + "; ".join(gate["reasons"])
        return result

    # ---- Case boundaries from phase stamps --------------------------------
    t_k, phase_stamps = derive_case_boundaries(meta, n_cases=5)
    result["caseBoundaries"] = t_k
    result["phaseStampCount"] = len(phase_stamps)

    # ---- GEN(5) (unambiguous by construction) -----------------------------
    renderer_tls = find_renderer_timelines(timelines)
    result["rendererThreadCount"] = len(renderer_tls)
    gen5, gen5_info = compute_gen5(renderer_tls, t_max, interval_guess)
    result["gen5Info"] = gen5_info
    if not gen5:
        result["status"] = "void"
        result["reason"] = "GEN(5) cannot be formed: no renderer thread is " \
                            "both absent-at-renderer-birth and present-at-last-sample"
        return result

    gen5_first = min(tl.first_seen() for tl in gen5.values())
    result["gen5FirstAppearance"] = gen5_first
    result["gen5Tids"] = [{"pid": p, "tid": t, "comm": tl.comm,
                            "firstSeen": tl.first_seen(), "lastSeen": tl.last_seen()}
                           for (p, t), tl in gen5.items()]

    b5_start, b5_end = gen5_first, min(gen5_first + 10.0, t_max)
    result["B5"] = [b5_start, b5_end]

    h_start = gen5_first + 20.0
    h_end = t_max - 5.0
    result["H"] = [h_start, h_end]
    result["Hlength"] = h_end - h_start

    if h_end - h_start < 120.0:
        result["status"] = "void"
        result["reason"] = f"|H| = {h_end - h_start:.1f}s < 120s"
        return result

    max_gap, empties_in_h = max_gap_within(ok_ticks, empty_ticks, h_start, h_end)
    result["maxSampleGapInH"] = max_gap
    result["emptyTicksInH"] = empties_in_h
    # "more than two consecutive samples missing inside H": a gap of more
    # than 3 intervals means at least 2 samples were skipped in a row.
    if max_gap > interval_guess * 3.5 or empties_in_h > 2:
        result["status"] = "void"
        result["reason"] = (f"more than two consecutive samples missing inside H "
                            f"(max gap {max_gap:.2f}s, {empties_in_h} empty-tree "
                            f"ticks inside H)")
        return result

    # ---- All-tree maxRate(H) (identification-free half) --------------------
    all_rates = []
    for (pid, tid), tl in timelines.items():
        r = rate(tl, h_start, h_end, clk_tck)
        all_rates.append({"pid": pid, "tid": tid, "comm": tl.comm,
                          "type": tl.proc_type, "rate": r})
    all_rates.sort(key=lambda r: -r["rate"])
    result["maxRateAllThreads"] = all_rates[0]["rate"] if all_rates else 0.0
    result["allThreadRatesTopTen"] = all_rates[:10]

    # ---- GEN(5) per-tid rate(H), duty cycle, histogram, ctxt ---------------
    candidate_tls = forced if forced is not None else gen5
    per_tid = []
    for (pid, tid), tl in candidate_tls.items():
        per_tid.append({
            "pid": pid, "tid": tid, "comm": tl.comm,
            "rateH": rate(tl, h_start, h_end, clk_tck),
            "stateHistogramH": state_histogram(tl, h_start, h_end),
            "ctxtDeltaH": ctxt_delta(tl, h_start, h_end),
            "aliveAtLastSample": alive_at(tl, t_max, max(interval_guess * 1.5, 0.75)),
            # Recorded raw per section 3.1; NOT read anywhere in the outcome
            # logic below (that would be naming what is waited on, which this
            # protocol may not do).
            "wchanCountsH": value_counts(tl, h_start, h_end, "wchan"),
            "syscallCountsH": value_counts(tl, h_start, h_end, "syscall"),
        })
    result["gen5PerTidH" if forced is None else "forcedPerTidH"] = per_tid

    n_sub = int((h_end - h_start) // SUB_WINDOW)
    duty_hits = 0
    for i in range(n_sub):
        sw_start = h_start + i * SUB_WINDOW
        sw_end = sw_start + SUB_WINDOW
        sub_max = max((rate(tl, sw_start, sw_end, clk_tck) for tl in candidate_tls.values()),
                      default=0.0)
        if sub_max >= BUSY_BAR:
            duty_hits += 1
    duty_cycle = (duty_hits / n_sub) if n_sub else 0.0
    result["dutyCycle"] = duty_cycle
    result["dutySubWindows"] = n_sub

    # ---- NOISE_BAR on threads outside the candidate set --------------------
    outside = [r for r in all_rates if (r["pid"], r["tid"]) not in candidate_tls]
    max_outside = max((r["rate"] for r in outside), default=0.0)
    result["maxRateOutsideCandidate"] = max_outside
    result["noiseBarHeld"] = max_outside < NOISE_BAR

    # ---- Controls (section 3.4a) -------------------------------------------
    controls: dict[str, Any] = {}

    def window_activity(w_start: Optional[float], w_end: Optional[float]):
        """Total CPU (s) and max rate, over ALL non-baseline renderer
        threads active in [w_start, w_end)."""
        if w_start is None or w_end is None or w_end <= w_start:
            return None
        baseline_keys = {(tl.pid, tl.tid) for tl in
                         [t for t in renderer_tls.values()]
                         if alive_at(tl, gen5_info["renderer_t0"],
                                     max(interval_guess * 1.5, 0.75))
                         and alive_at(tl, t_max, max(interval_guess * 1.5, 0.75))}
        active = {k: tl for k, tl in renderer_tls.items() if k not in baseline_keys
                 and is_present_across(tl, w_start, w_end)}
        total_ticks = 0
        max_r = 0.0
        for tl in active.values():
            d = cpu_delta(tl, w_start, w_end) or 0
            total_ticks += d
            max_r = max(max_r, rate(tl, w_start, w_end, clk_tck))
        return {"window": [w_start, w_end], "activeThreadCount": len(active),
                "totalCpuSeconds": total_ticks / clk_tck, "maxRate": max_r,
                "busyBarCleared": max_r >= BUSY_BAR}

    case4_window = window_activity(t_k.get(4), t_k.get(5))
    case2_window = window_activity(t_k.get(2), t_k.get(3))
    case3_window = window_activity(t_k.get(3), t_k.get(4))
    controls["case4HeavyFinite"] = case4_window
    controls["case2CheapNear"] = case2_window
    controls["case3CheapNear"] = case3_window

    if forced is not None:
        # Section 7 R-B/R-C: evaluate the SAME busy predicate but restricted
        # to the forced thread(s), not the normally-derived candidates.
        forced_case4_max = max((rate(tl, t_k.get(4) or 0, t_k.get(5) or t_max, clk_tck)
                               for tl in forced.values()), default=0.0) if t_k.get(4) and t_k.get(5) else 0.0
        forced_b5_total = sum((cpu_delta(tl, b5_start, b5_end) or 0) for tl in forced.values()) / clk_tck
        controls["forcedCase4MaxRate"] = forced_case4_max
        controls["forcedB5TotalCpuSeconds"] = forced_b5_total
        b3_holds = forced_b5_total >= 0.3
        a1_holds = forced_case4_max >= BUSY_BAR
        a2_holds = False  # not evaluated for forced mode; a1 or a2 needed
        controls_behave = b3_holds and (a1_holds or a2_holds)
        controls["controlsBehave"] = controls_behave
        if not controls_behave:
            result["status"] = "void"
            result["reason"] = "controls did not behave on the selected thread"
            result["controls"] = controls
            return result
    else:
        b3_total = sum((cpu_delta(tl, b5_start, b5_end) or 0) for tl in gen5.values()) / clk_tck
        controls["b5InBandTotalCpuSeconds"] = b3_total
        b3_holds = b3_total >= 0.3
        a1_holds = bool(case4_window and case4_window["busyBarCleared"])
        a2_holds = bool(case2_window and case2_window["totalCpuSeconds"] >= 0.15
                       and case3_window and case3_window["totalCpuSeconds"] >= 0.15)
        controls_behave = b3_holds and (a1_holds or a2_holds)
        controls["controlsBehave"] = controls_behave
        controls["b3Holds"] = b3_holds
        controls["a1Holds"] = a1_holds
        controls["a2Holds"] = a2_holds
        if not a1_holds and a2_holds and b3_holds:
            result["note"] = ("case 4 (30s, successful open) showed no thread "
                              "clearing BUSY_BAR: recorded prominently per "
                              "section 3.4a, not interpreted.")
        if not controls_behave:
            result["status"] = "void"
            result["reason"] = "controls-behave predicate failed: " + json.dumps(controls)
            result["controls"] = controls
            return result

    result["controls"] = controls

    # ---- Outcome (section 4) -----------------------------------------------
    gen5_rates = [p["rateH"] for p in per_tid]
    max_gen5_rate = max(gen5_rates, default=0.0)

    def sustained_for(tl_key):
        tl = candidate_tls[tl_key]
        hits, total = 0, 0
        i = 0
        w = h_start
        while w < h_end:
            sw_end = min(w + SUB_WINDOW, h_end)
            total += 1
            if rate(tl, w, sw_end, clk_tck) >= BUSY_BAR:
                hits += 1
            w += SUB_WINDOW
        return (hits / total) if total else 0.0

    sustained_info = {f"{p}.{t}": sustained_for((p, t)) for (p, t) in candidate_tls}
    result["sustainedFractionPerTid"] = sustained_info

    # Section 4.1 requires BOTH clauses over H: the mean rate clears BUSY_BAR
    # (section 3.3's definition, evaluated over the whole of H) AND the
    # SUSTAINED fraction of 5s sub-windows clears 90%. Sustained alone does not
    # imply the mean does (a tid could clear 0.5 in exactly 90% of sub-windows
    # and sit at 0 in the rest, landing a mean of ~0.45) so both are checked.
    rate_h_by_tid = {(p["pid"], p["tid"]): p["rateH"] for p in per_tid}
    busy_and_sustained_tids = [
        k for k in candidate_tls
        if rate_h_by_tid.get(k, 0.0) >= BUSY_BAR
        and sustained_info[f"{k[0]}.{k[1]}"] >= SUSTAINED_FRACTION]
    r_dominated_tids = []
    for p in per_tid:
        hist = p["stateHistogramH"]
        total = sum(hist.values())
        r_frac = (hist.get("R", 0) / total) if total else 0.0
        p["rFraction"] = r_frac
        if r_frac > 0.5:
            r_dominated_tids.append((p["pid"], p["tid"]))

    every_quiet = all(p["rateH"] < QUIET_BAR for p in per_tid)
    every_alive = all(p["aliveAtLastSample"] for p in per_tid)

    def wait_state_fraction(p):
        hist = p["stateHistogramH"]
        total = sum(hist.values())
        if not total:
            return 0.0
        return (hist.get("S", 0) + hist.get("D", 0)) / total

    every_waiting_states = all(wait_state_fraction(p) >= 0.95 for p in per_tid)

    cpu_bound_tids = [k for k in busy_and_sustained_tids if k in
                      {(p["pid"], p["tid"]) for p in per_tid if p["rFraction"] > 0.5}]

    outcome = None
    if cpu_bound_tids:
        outcome = "CPU-bound"
    elif every_quiet and result["noiseBarHeld"] and every_alive and every_waiting_states:
        outcome = "Waiting"
    else:
        outcome = "Mixed"

    result["status"] = "ok"
    result["outcome"] = outcome
    result["cpuBoundTids"] = [{"pid": p, "tid": t} for (p, t) in cpu_bound_tids]
    result["threadIdentification"] = ("ambiguous" if len(candidate_tls) != 1
                                      else "single-candidate")
    result["maxGen5RateH"] = max_gen5_rate
    result["clkTck"] = clk_tck
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--meta", type=Path, default=None)
    parser.add_argument("--probe-report", type=Path, default=None)
    parser.add_argument("--clk-tck", type=int, default=100)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--force-tid", type=int, default=None)
    parser.add_argument("--force-thread", type=str, default=None,
                        help="comm=NAME")
    args = parser.parse_args()

    force_comm = None
    if args.force_thread:
        if not args.force_thread.startswith("comm="):
            parser.error("--force-thread must be comm=NAME")
        force_comm = args.force_thread[len("comm="):]

    meta = load_json(args.meta)
    probe = load_json(args.probe_report)

    result = full_analysis(args.samples, meta, probe, args.clk_tck,
                           force_tid=args.force_tid, force_thread_comm=force_comm)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k in ("status", "outcome", "reason", "H", "Hlength",
                               "dutyCycle", "maxRateAllThreads")}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
