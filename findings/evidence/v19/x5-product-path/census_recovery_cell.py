#!/usr/bin/env python3
"""Census of the product-path cell `recovery-returns-what-the-product-promised` over committed reports.

Spec SPEC-M3-paragraph-merge §36 and fable-ruling-x5.md (this directory): the evidence that v8 abstains on this
cell, which is what places it under §23 row 1' instead of row 1.  It counts and lists; it judges nothing else.

Window: every git-tracked `findings/evidence/**/e2-editor-<profile>-<browser>-r<N>.json` whose record for this
check carries `observed.finding038Reproduced` (the two-inducer semantics, ba84ec81 2026-08-28; older reports are
outside the window and counted separately).  Arms: profile `v8`; every other profile is a candidate.
NOT `observed.fallbackInducer`, which fable-ruling-x5.md recommended: only a record whose first inducer did not
fire carries it, so that window holds the NE records alone and no FAIL or PASS can enter it.  This tool's first
version used it and its own red case (selftest.sh (2): a FAIL) stayed green; that output is kept.

Printed: per arm PASS / FAIL / NOT_ESTABLISHED, and the path of every report that is not PASS.  Flagged:
  - any FAIL;
  - a NOT_ESTABLISHED where an inducer fired (`finding038Reproduced` true, or `fallbackInducer.fired` true);
  - a PASS where neither fired.
Exit: 0 the window is non-empty and nothing is flagged; 1 something is flagged; 2 the window is empty.

    python3 -I census_recovery_cell.py [--browser firefox] [--dir DIR]
`--dir` reads DIR's reports by glob instead of the git index (the red cases, `selftest.sh`).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

CHECK = "recovery-returns-what-the-product-promised"
EVIDENCE = Path(__file__).resolve().parents[2]          # findings/evidence


def reports(browser: str, directory: Path | None) -> list[Path]:
    pattern = f"e2-editor-*-{browser}-r*.json"
    if directory is not None:
        return sorted(directory.rglob(pattern))
    listed = subprocess.run(["git", "-C", str(EVIDENCE), "ls-files", "-z", "--", f"**/{pattern}"],
                            capture_output=True, check=True).stdout.decode().split("\0")
    return sorted(EVIDENCE / name for name in listed if name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", default="firefox", choices=("chrome", "firefox"))
    ap.add_argument("--dir", type=Path, default=None)
    a = ap.parse_args()
    base = a.dir if a.dir is not None else EVIDENCE
    counts = {"v8": Counter(), "candidate": Counter()}
    outside, flagged, listed = Counter(), [], []
    for path in reports(a.browser, a.dir):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        record = next((c for c in report.get("checks") or [] if isinstance(c, dict) and c.get("id") == CHECK), None)
        if record is None:
            continue
        observed = record.get("observed") or {}
        name = path.relative_to(base).as_posix()
        if "finding038Reproduced" not in observed:
            outside[record.get("outcome")] += 1
            continue
        profile = path.name.split(f"-{a.browser}-")[0].removeprefix("e2-editor-")
        arm = "v8" if profile == "v8" else "candidate"
        outcome = record.get("outcome")
        counts[arm][outcome] += 1
        fired = observed.get("finding038Reproduced") is True or (observed.get("fallbackInducer") or {}).get("fired") is True
        if outcome != "PASS":
            listed.append(f"  {arm:9} {outcome:15} 038={observed.get('finding038Reproduced')} "
                          f"fallbackFired={(observed.get('fallbackInducer') or {}).get('fired')}  {name}")
        if outcome == "FAIL":
            flagged.append(f"FAIL: {name}")
        elif outcome == "NOT_ESTABLISHED" and fired:
            flagged.append(f"NE although an inducer fired: {name}")
        elif outcome == "PASS" and not fired:
            flagged.append(f"PASS although no inducer fired: {name}")
    total = sum(sum(c.values()) for c in counts.values())
    print(f"check {CHECK}, browser {a.browser}, window: reports carrying observed.finding038Reproduced "
          f"({'git index' if a.dir is None else a.dir})")
    for arm, c in counts.items():
        print(f"  {arm:9} runs {sum(c.values()):3}  " + "  ".join(f"{k} {c[k]}" for k in ("PASS", "FAIL", "NOT_ESTABLISHED")))
    print(f"  outside the window (no finding038Reproduced): {dict(outside) or 'none'}")
    print("not PASS:" if listed else "not PASS: none")
    print("\n".join(listed)) if listed else None
    for line in flagged:
        print("FLAG " + line)
    if total == 0:
        print("CENSUS EMPTY: no report in the window")
        return 2
    print("CENSUS " + ("FLAGGED" if flagged else "OK") + f": {total} reports")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
