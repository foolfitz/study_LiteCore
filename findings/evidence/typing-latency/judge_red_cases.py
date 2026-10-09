#!/usr/bin/env python3
"""Red cases for judge.py (spec §15.8; fable's fourth ruling, condition 2), each run once, output recorded.

Each case swaps ONE report slot for a real or mutated report (mutated copies go to a temp directory; the
committed reports are not touched) and records judge.py's full output and exit code.  Writes
judge-red-cases.txt beside this file.

R1   v58-chrome-owner-gap80-fixed-instrument.json in chrome:owner-gap80            ruled: FAIL (a) and (b)
R2   firefox candidate gap 80, +80 ms on every revisionMs                          ruled: FAIL (b) only
R2'  chrome candidate gap 80, +80 ms on every revisionMs                           (b) only (max 54.8+80 < 160)
R2'' firefox candidate gap 80, +15 ms on every revisionMs                          (b) only (median 65.3+15 >= 80)
R3   firefox candidate gap 80, one row (the slowest) set to 160                    ruled: FAIL (a) only
R4   diagnostic lazy-shim report in firefox:owner-gap80                            ruled: REFUSED
base the six candidate reports unchanged                                          PASS
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGE = HERE / "judge.py"


def mutated(tmp: Path, name: str, source: str, change) -> Path:
    report = json.loads((HERE / source).read_text())
    change(report["rows"])
    out = tmp / name
    out.write_text(json.dumps(report))
    return out


def add(ms):
    def change(rows):
        for row in rows:
            row["revisionMs"] = round(row["revisionMs"] + ms, 1)
    return change


def slowest_to(value):
    def change(rows):
        max(rows, key=lambda row: row["revisionMs"])["revisionMs"] = value
    return change


def main() -> int:
    log = []
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        cases = [
            ("R1 v58 chrome gap 80 (ruled: FAIL (a) and (b))",
             ["chrome:owner-gap80=" + str(HERE / "v58-chrome-owner-gap80-fixed-instrument.json")]),
            ("R2 firefox candidate gap 80, +80 on every key (ruled: FAIL (b) only)",
             ["firefox:owner-gap80=" + str(mutated(tmp, "r2.json", "v59-candidate2-firefox-owner-gap80.json", add(80)))]),
            ("R2' chrome candidate gap 80, +80 on every key ((b) only)",
             ["chrome:owner-gap80=" + str(mutated(tmp, "r2p.json", "v59-candidate2-chrome-owner-gap80.json", add(80)))]),
            ("R2'' firefox candidate gap 80, +15 on every key ((b) only)",
             ["firefox:owner-gap80=" + str(mutated(tmp, "r2pp.json", "v59-candidate2-firefox-owner-gap80.json", add(15)))]),
            ("R3 firefox candidate gap 80, slowest key set to 160 (ruled: FAIL (a) only)",
             ["firefox:owner-gap80=" + str(mutated(tmp, "r3.json", "v59-candidate2-firefox-owner-gap80.json", slowest_to(160.0)))]),
            ("R4 diagnostic lazy-shim report as firefox gap 80 (ruled: REFUSED)",
             ["firefox:owner-gap80=" + str(HERE / "diagnostic-shim-overhead" / "lazy-candidate2-firefox-owner-gap80.json")]),
            ("base: the six candidate reports unchanged (PASS)", []),
        ]
        for title, overrides in cases:
            args = [sys.executable, str(JUDGE)] + [f"--report={o}" for o in overrides]
            done = subprocess.run(args, capture_output=True, text=True)
            out = done.stdout.replace(str(tmp), "<tmp>").replace(str(HERE), "<here>")
            log.append(f"=== {title}\n{out}exit {done.returncode}\n")
    text = "".join(log)
    (HERE / "judge-red-cases.txt").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
