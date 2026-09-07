#!/usr/bin/env python3
"""Section 3.4b's known-idle control: the same sampler, on the same page,
settled -- proving a near-zero reading is a measurement, not the sampler's
constant output.

Serves a read-only, symlink-only scratch mirror of the probe page (never
`wasm_sdk_probe/web/`, `dist/` or the profile themselves), opens the ODT
control only, waits for `window.__odsProbe.done`, then keeps sampling for
180 s with the page settled.

One necessary addition to the protocol's literal four-symlink recipe, recorded
here rather than silently: `ods-decisive-probe-app.js` imports
`./sdk/document-sdk.js` relative to itself, so a fifth symlink,
`sdk -> wasm_sdk_probe/dist/sdk` (the whole directory, read-only), is required
for the page to load at all -- without it the module import 404s before
anything can be measured. This mirrors exactly what `build_mirror()` (used by
the real measurement runs) already does implicitly for any dist path an
override does not touch, so it does not change what code the page runs; it
only supplies what the protocol's four-item list omitted. Nothing under
`web/`, `dist/` or the profile is copied, written, or modified -- the fifth
entry is a symlink like the other four.
"""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sample_threads  # noqa: E402
import analyse  # noqa: E402

PROJECT = HERE.parent.parent.parent.parent
WASM_SDK_PROBE = PROJECT / "wasm_sdk_probe"
sys.path.insert(0, str(WASM_SDK_PROBE / "tools"))
from run_browser_probe import ChromeSession, free_port, wait_http  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402
from r7_support import evaluate  # noqa: E402

import run_one  # noqa: E402  (clock_ok, git_status_porcelain, cleanup_tmp)


def build_scratch_root(scratch_dir: Path, profile: str) -> Path:
    root = scratch_dir / "root"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    (root / "ods-decisive-probe.html").symlink_to(
        (WASM_SDK_PROBE / "web" / "ods-decisive-probe.html").resolve())
    (root / "ods-decisive-probe-app.js").symlink_to(
        (WASM_SDK_PROBE / "web" / "ods-decisive-probe-app.js").resolve())
    (root / "profiles").mkdir()
    (root / "profiles" / profile).symlink_to(
        (WASM_SDK_PROBE / "dist" / "profiles" / profile).resolve())
    (root / "ods-cases").mkdir()
    (root / "ods-cases" / "d1-anchors.odt").symlink_to(
        (WASM_SDK_PROBE / "dist" / "e2-fixtures" / "d1-anchors.odt").resolve())
    # The fifth symlink -- see module docstring.
    (root / "sdk").symlink_to((WASM_SDK_PROBE / "dist" / "sdk").resolve())
    return root


def serve(root: Path):
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, str(WASM_SDK_PROBE / "web" / "serve.py"),
         "--port", str(port), "--root", str(root)],
        cwd=WASM_SDK_PROBE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # wait_http (imported for parity with the other tools) expects a JSON
    # response; this page is HTML, so poll for a plain 200 instead.
    deadline = time.monotonic() + 30
    import urllib.request
    last_error = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/ods-decisive-probe.html",
                    timeout=2) as resp:
                if resp.status == 200:
                    return port, proc
        except Exception as error:
            last_error = error
        time.sleep(0.2)
    raise RuntimeError(f"page server did not come up: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--profile", default="e2-editor-v12")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--scratch-dir", type=Path, required=True)
    parser.add_argument("--settle-seconds", type=float, default=180.0)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--clk-tck", type=int, required=True)
    args = parser.parse_args()

    ok, reason = run_one.clock_ok()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    if not ok:
        meta = {"status": "refused", "reason": reason}
        (out_dir / f"idle-{args.run_id}-meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8")
        print(f"REFUSED (clock window): {reason}")
        return 3

    status_before = run_one.git_status_porcelain()
    window_start_wall = time.time()
    started_utc = datetime.now(timezone.utc)

    scratch_dir = args.scratch_dir
    scratch_dir.mkdir(parents=True, exist_ok=True)
    root = build_scratch_root(scratch_dir, args.profile)

    port, server_proc = serve(root)
    session = None
    browser_pid = None
    samples_plain = out_dir / f"idle-{args.run_id}-samples.jsonl"
    samples_plain.touch()
    error_info = None
    summary: dict[str, Any] = {"status": "void", "reason": "not run"}
    try:
        session = ChromeSession("cold")
        browser_pid = session.process.pid
        inline_cases = json.dumps([
            {"name": "d1-anchors.odt", "file": "./ods-cases/d1-anchors.odt",
             "kind": "control-odt", "paint": True}])
        import urllib.parse
        query = ("?profile=" + args.profile + "&openTimeoutMs=180000&cases="
                 + urllib.parse.quote(inline_cases))
        url = f"http://127.0.0.1:{port}/ods-decisive-probe.html{query}"
        navigate(session, url)

        deadline = time.monotonic() + 60
        done = False
        while time.monotonic() < deadline:
            value = evaluate(session,
                             "(window.__odsProbe && window.__odsProbe.done) || false")
            if value:
                done = True
                break
            time.sleep(1.0)
        if not done:
            error_info = "page did not report done within 60s"

        # Now sample for the settle window with the page idle.
        summary = sample_threads.run_loop(
            probe_pid=None, known_browser_pid=browser_pid, out_path=samples_plain,
            interval=args.interval, duration=args.settle_seconds)
    except Exception as error:
        error_info = f"{error_info or ''} exception: {error}".strip()
        summary = {"status": "void", "reason": str(error)}
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass
        try:
            server_proc.terminate()
            server_proc.wait(timeout=10)
        except Exception:
            pass

    completed_utc = datetime.now(timezone.utc)
    window_end_wall = time.time()
    status_after = run_one.git_status_porcelain()

    samples_gz = out_dir / f"idle-{args.run_id}-samples.jsonl.gz"
    with open(samples_plain, "rb") as fin, gzip.open(samples_gz, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    samples_plain.unlink()

    removed_tmp = run_one.cleanup_tmp(window_start_wall, window_end_wall)

    meta = {
        "runId": args.run_id, "port": port, "browserPid": browser_pid,
        "startedAtUtc": started_utc.isoformat(),
        "completedAtUtc": completed_utc.isoformat(),
        "startedAtCst": started_utc.astimezone().isoformat(),
        "completedAtCst": completed_utc.astimezone().isoformat(),
        "gitStatusBefore": status_before, "gitStatusAfter": status_after,
        "sampler": summary, "pageDoneError": error_info,
        "removedTmpPaths": removed_tmp, "clkTck": args.clk_tck,
        "scratchRoot": str(root),
        "symlinks": {
            "ods-decisive-probe.html": str((WASM_SDK_PROBE / "web" / "ods-decisive-probe.html").resolve()),
            "ods-decisive-probe-app.js": str((WASM_SDK_PROBE / "web" / "ods-decisive-probe-app.js").resolve()),
            f"profiles/{args.profile}": str((WASM_SDK_PROBE / "dist" / "profiles" / args.profile).resolve()),
            "ods-cases/d1-anchors.odt": str((WASM_SDK_PROBE / "dist" / "e2-fixtures" / "d1-anchors.odt").resolve()),
            "sdk (added, see module docstring)": str((WASM_SDK_PROBE / "dist" / "sdk").resolve()),
        },
    }
    (out_dir / f"idle-{args.run_id}-meta.json").write_text(
        json.dumps(meta, indent=2, default=str), encoding="utf-8")

    verdict = compute_idle_verdict(samples_gz, args.clk_tck, error_info)
    (out_dir / f"idle-{args.run_id}-verdict.json").write_text(
        json.dumps(verdict, indent=2, default=str) + "\n", encoding="utf-8")

    print(json.dumps(verdict, indent=2, default=str))
    return 0


def compute_idle_verdict(samples_path: Path, clk_tck: int, page_done_error) -> dict[str, Any]:
    rows = analyse.load_samples(samples_path)
    timelines, ok_ticks, empty_ticks, tick_count = analyse.build_timelines(rows)
    result: dict[str, Any] = {"tickCount": tick_count, "okTickCount": len(ok_ticks),
                              "emptyTickCount": len(empty_ticks),
                              "pageDoneError": page_done_error}
    if page_done_error:
        result["status"] = "void"
        result["reason"] = f"page did not settle: {page_done_error}"
        return result
    if not ok_ticks:
        result["status"] = "void"
        result["reason"] = "no ok ticks (no-tree throughout)"
        return result
    t_min, t_max = min(ok_ticks), max(ok_ticks)
    result["window"] = [t_min, t_max]
    renderer_tls = analyse.find_renderer_timelines(timelines)
    per_thread = []
    for (pid, tid), tl in renderer_tls.items():
        r = analyse.rate(tl, t_min, t_max, clk_tck)
        per_thread.append({"pid": pid, "tid": tid, "comm": tl.comm, "rate": r})
    per_thread.sort(key=lambda p: -p["rate"])
    result["rendererThreadRates"] = per_thread
    max_renderer_rate = max((p["rate"] for p in per_thread), default=0.0)

    all_rates = []
    for (pid, tid), tl in timelines.items():
        all_rates.append({"pid": pid, "tid": tid, "comm": tl.comm, "type": tl.proc_type,
                          "rate": analyse.rate(tl, t_min, t_max, clk_tck)})
    all_rates.sort(key=lambda r: -r["rate"])
    result["maxRateAllThreads"] = all_rates[0]["rate"] if all_rates else 0.0
    result["allThreadRatesTopTen"] = all_rates[:10]

    quiet_bar_held = all(p["rate"] < analyse.QUIET_BAR for p in per_thread)
    noise_bar_held = result["maxRateAllThreads"] < analyse.NOISE_BAR
    result["quietBarHeld"] = quiet_bar_held
    result["noiseBarHeld"] = noise_bar_held
    result["status"] = "ok" if (quiet_bar_held and noise_bar_held) else "void"
    if result["status"] == "void":
        result["reason"] = ("idle control failed: quietBarHeld="
                            f"{quiet_bar_held}, noiseBarHeld={noise_bar_held}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
