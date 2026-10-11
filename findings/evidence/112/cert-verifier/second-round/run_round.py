#!/usr/bin/env python3
"""The second round's schedule (PREDICTION.md): the arms, their counts and flags, run one launch at a time in
round-robin order so that a drift over the ~22 minutes (network latency, machine load) spreads over every arm instead
of landing on one.  Appends one line per launch to runs.log.

  run_round.py --netlog-dir DIR [--dry-run] [--only e5-03,e6-01]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

# arm -> (count, extra flags, idle seconds, window seconds)
ARMS: dict[str, tuple[int, list[str], float, float]] = {
    "e1": (20, [], 0, 16),                                                      # the runners' flags
    "e2": (8, ["--disable-component-update"], 0, 16),                           # first round's flag
    "e3": (12, [], 5, 21),                                                      # no request until 5 s after launch
    "e5": (12, ["--disable-features=CertVerificationNetworkTime"], 0, 16),     # no network-time push to the verifier
    "e6": (12, ["--disable-background-networking"], 0, 16),                    # the usual automation flag
}
ORDER = ["e1", "e2", "e3", "e5", "e6"]


def schedule() -> list[str]:
    labels: list[str] = []
    for i in range(max(c for c, *_ in ARMS.values())):
        for arm in ORDER:
            if i < ARMS[arm][0]:
                labels.append(f"{arm}-{i + 1:02d}")
    return labels


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--netlog-dir", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated labels to (re)run instead of the whole schedule")
    args = ap.parse_args()
    labels = [x for x in args.only.split(",") if x] or schedule()
    log = HERE / "runs.log"
    if args.dry_run:
        print("\n".join(labels))
        return 0
    for label in labels:
        arm = label.split("-")[0]
        count, flags, idle, seconds = ARMS[arm]
        cmd = [sys.executable, "-I", str(HERE / "probe_early_reset.py"), "--label", label, "--arm", arm,
               "--seconds", str(seconds), "--idle-seconds", str(idle), "--netlog-dir", str(args.netlog_dir),
               "--out", str(HERE / f"{label}.json")]
        for f in flags:
            cmd += [f"--extra-flag={f}"]    # the value starts with "--": argparse takes it only in this form
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        res = subprocess.run(cmd, capture_output=True, text=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(f"{started} {label} start\n")
            fh.write((res.stdout or "").rstrip() + "\n")
            if res.stderr.strip():
                fh.write("STDERR " + res.stderr.strip().replace("\n", " | ")[-2000:] + "\n")
            fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {label} exit {res.returncode}\n")
        print(label, "exit", res.returncode, flush=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} DONE\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
