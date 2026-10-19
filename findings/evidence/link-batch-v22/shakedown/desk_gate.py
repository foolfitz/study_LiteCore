#!/usr/bin/env python3
"""The desk gate before each item-1 re-run step (SPEC-M3-link-batch-v22 §11.4.2; fable ruling 6 addendum 1 item 9).

Clean = all of: KWallet unlocked (the runner's own pre-run refusal); no Chrome process at all (the owner's desktop
Chrome's extension renderer voided timing cells four times); no zen, make, cc1plus or ninja; 1-minute load < 1.5;
the runner's 2 s foreign-CPU sample `ok`; none of our runners up; the S-9 lock free.  Starts no browser.

  desk_gate.py [--wait SECONDS]   re-check every 30 s until clean or SECONDS have passed (default 0: check once)

Prints one JSON line per check.  Exit 0 = clean; 1 = still dirty when the wait ran out.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "wasm_sdk_probe" / "tools"))
import v21_shakedown_common as common  # noqa: E402

LOAD_LIMIT = 1.5
NAMES = ("zen", "make", "cc1plus", "ninja")


def count(name: str) -> int:
    out = subprocess.run(["pgrep", "-c", "-x", name], capture_output=True, text=True).stdout.strip()
    return int(out or 0)


def check() -> tuple[list[str], dict]:
    pre = common.pre_run_checks()
    reasons = list(pre["refuse"])
    if pre["chromeProcesses"].strip() not in ("", "0"):
        reasons.append(f"chrome processes {pre['chromeProcesses'].strip()}")
    for name in NAMES:
        n = count(name)
        if n:
            reasons.append(f"{name} running ({n})")
    if float(pre["loadavg"][0]) >= LOAD_LIMIT:
        reasons.append(f"1-min load {pre['loadavg'][0]} >= {LOAD_LIMIT}")
    if pre["oursRunning"]:
        reasons.append(f"ours running: {pre['oursRunning']}")
    sample = common.foreign_cpu()
    if not sample["ok"]:
        reasons.append("foreign CPU over the limit: "
                       + json.dumps([(r["pid"], r["comm"], r["pct"], r["cmd"][:80]) for r in sample["overLimit"]]))
    try:
        with common.browser_lock("desk_gate.py"):
            pass
    except common.LockBusy as error:
        reasons.append(str(error))
    seen = {"at": pre["at"], "load": pre["loadavg"], "chrome": pre["chromeProcesses"].strip(),
            "firefox": pre["firefoxProcesses"].strip(), "kwallet": pre["kwalletLocked"].strip(),
            "foreignTop": [(r["pid"], r["comm"], r["pct"]) for r in sample.get("topForeign", [])[:3]]}
    return reasons, seen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=float, default=0.0)
    args = ap.parse_args()
    deadline = time.monotonic() + args.wait
    while True:
        reasons, seen = check()
        print(json.dumps({"gate": "clean" if not reasons else "dirty", "reasons": reasons, **seen}, ensure_ascii=False),
              flush=True)
        if not reasons:
            return 0
        if time.monotonic() >= deadline:
            return 1
        time.sleep(30)


if __name__ == "__main__":
    sys.exit(main())
