#!/usr/bin/env python3
"""Re-sweep A3/A4/A5 after an engine change and rebind the verdicts.

Every verdict E2-A carries is bound to one artifact (finding 027), and the wasm
hash is not a function of the source (finding 036), so a rebuild does not
"probably" invalidate the evidence -- it invalidates all of it, and
validate_e2_a.py will say so by reporting every cell as superseded.  This runs
the sweep that puts the coverage back.

Three things here are deliberate, and each is a lesson rather than a
preference:

  * The artifact hash is checked before EVERY run, not once at the start.  A
    single session has had two artifacts swapped in and out of dist/ for a
    control, and a sweep that checked once would have attributed whatever ran
    after the swap to the wrong engine.

  * Verdicts are read from the evidence tree by validate_e2_a.py, never parsed
    out of this script's stdout.  The previous sweep's stdout extractor died on
    a quoting bug and left a log whose verdict columns were all empty -- which
    looked like a sweep that had run.

  * A failed run is recorded and the sweep continues.  Stopping on the first
    failure produces a tree where "not covered" and "covered and failing" are
    indistinguishable, and those need different responses.

The runner's exit code is NOT the verdict and is not treated as one here.  It
follows the page's `metrics.pass`, which requires a2.trackedCaret -- the format
state tracking the caret, measured false since finding 021 and false on every
a3/a4/a5 run ever recorded, including runs the validator judges as passing.  So
a3/a4/a5 runs exit 1 when everything worked.  What this script checks instead is
whether the run left evidence behind: the count of result.json files under that
cell has to grow, or the run produced nothing and the sweep should say so.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

A3_FIXTURES = ("styled-list", "multi-paragraph", "plain-grapheme")
A5_FIXTURES = A3_FIXTURES + ("table-boundary",)
BROWSERS = ("chrome", "firefox")

EVIDENCE_ROOT = (PROJECT.parent / "findings" / "evidence" / "sdk-e2" / "discovery")
MODE_TREE = {"a3": "browser", "a4": "repeat", "a5": "negative"}


def evidence_count(mode: str, browser: str, fixture: str) -> int:
    """How many runs this cell has on disk, of any artifact."""
    cell = EVIDENCE_ROOT / MODE_TREE[mode] / browser / fixture
    if not cell.is_dir():
        return 0
    return len(list(cell.glob("**/result.json")))


def artifact_hash() -> str:
    wasm = PROJECT / "dist" / "profiles" / "e2-format-discovery" / "probe.wasm"
    digest = hashlib.sha256()
    with wasm.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def planned_runs(repetitions: int) -> list[tuple[str, str, str]]:
    runs = []
    for browser in BROWSERS:
        for fixture in A3_FIXTURES:
            for _ in range(repetitions):
                runs.append(("a3", browser, fixture))
        for fixture in A3_FIXTURES:
            for _ in range(repetitions):
                runs.append(("a4", browser, fixture))
        for fixture in A5_FIXTURES:
            runs.append(("a5", browser, fixture))
    return runs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--expect-wasm", required=True,
        help="sha256 the shipped profile must carry for every run in this sweep")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--log", type=Path,
        default=PROJECT / "build" / "sweep-e2-a.jsonl")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="print the plan and check the artifact, run nothing")
    args = parser.parse_args()

    expected = args.expect_wasm.lower()
    current = artifact_hash()
    if current != expected:
        raise SystemExit(
            f"shipped profile is {current}, sweep was asked for {expected}")

    runs = planned_runs(args.repetitions)
    print(f"artifact {current}")
    print(f"{len(runs)} runs planned")
    if args.dry_run:
        for mode, browser, fixture in runs:
            print(f"  {mode:<3} {browser:<8} {fixture}")
        return

    args.log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with args.log.open("w", encoding="utf-8") as log:
        for index, (mode, browser, fixture) in enumerate(runs, start=1):
            # Before every run, not once: see the module docstring.
            now = artifact_hash()
            if now != expected:
                raise SystemExit(
                    f"artifact changed mid-sweep at run {index}: {now}")
            command = [
                sys.executable, str(PROJECT / "tools" / "run_e2_discovery.py"),
                "--browser", browser, "--fixture", fixture, "--mode", mode,
            ]
            before = evidence_count(mode, browser, fixture)
            run_started = time.monotonic()
            completed = subprocess.run(
                command, cwd=PROJECT, capture_output=True, text=True)
            elapsed = round(time.monotonic() - run_started, 1)
            after = evidence_count(mode, browser, fixture)
            record = {
                "index": index,
                "mode": mode,
                "browser": browser,
                "fixture": fixture,
                # Recorded, not interpreted: see the module docstring on why
                # exit 1 is the normal outcome of a working a3/a4/a5 run.
                "runnerExit": completed.returncode,
                "evidenceBefore": before,
                "evidenceAfter": after,
                "leftEvidence": after > before,
                "elapsedSeconds": elapsed,
                "artifact": now,
            }
            log.write(json.dumps(record) + "\n")
            log.flush()
            status = "evidence" if after > before else "NO EVIDENCE"
            print(f"[{index:>2}/{len(runs)}] {mode} {browser} {fixture} "
                  f"{status} exit={completed.returncode} {elapsed}s", flush=True)
            if after == before:
                # Kept in the log, not raised: a run that produced nothing is a
                # measurement too, and stopping here would leave the rest of the
                # sweep unmeasured rather than measured-and-failing.
                print(completed.stdout[-2000:], flush=True)

    print(f"sweep finished in {round((time.monotonic() - started) / 60, 1)} min")
    print("verdicts come from validate_e2_a.py against the evidence tree, "
          "not from this output")


if __name__ == "__main__":
    main()
