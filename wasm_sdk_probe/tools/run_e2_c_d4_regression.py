#!/usr/bin/env python3
"""Run D4's regression half and record what each target did.

The list is the one `e2/validation-matrix-v1.json` froze for `d4-regression`,
including the two exclusions it names: `test-e1-c-static` is NOT in it, and
`check_e1_c_bundle_intact` plus `test-e1-c-frozen-guard` stand in its place.

Every profile's `probe.wasm` is hashed before and after.  A regression sweep
that changes an artifact is not a regression sweep, whatever the target names
say -- and finding 041 is what that looks like when nobody checks.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1_support import sha256, write_json  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

TARGETS = (
    "test-r6-release",
    "test-r7-b-static",
    "test-r7-c-static",
    "test-r7-d-static",
    "test-r8-d-static",
    "test-e1-a-static",
    "test-e1-b-static",
    "test-e2-a-static",
    "test-e2-b-static",
    # In place of test-e1-c-static, which the matrix excludes by name.
    "test-e1-c-frozen-guard",
)
GUARD = ("python3", "tools/check_e1_c_bundle_intact.py")


def artifact_hashes() -> dict[str, str]:
    return {
        str(path.parent.relative_to(PROJECT / "dist" / "profiles")): sha256(path)
        for path in sorted((PROJECT / "dist" / "profiles").glob("*/probe.wasm"))
    }


def run(command: list[str], log: Path) -> dict:
    started = time.monotonic()
    completed = subprocess.run(command, cwd=PROJECT, capture_output=True, text=True)
    log.write_text((completed.stdout or "") + (completed.stderr or ""),
                   encoding="utf-8")
    return {
        "command": command,
        "returnCode": completed.returncode,
        "seconds": round(time.monotonic() - started, 1),
        "pass": completed.returncode == 0,
        "log": log.name,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=PROJECT.parent / "findings" / "evidence" / "sdk-e2"
                        / "e2-c-validation" / "d4" / "regression")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    before = artifact_hashes()
    results = [run(["make", target], args.output / f"{target}.log")
               for target in TARGETS]
    results.append(run(list(GUARD), args.output / "check_e1_c_bundle_intact.log"))
    after = artifact_hashes()

    moved = {name: [before.get(name), after.get(name)]
             for name in set(before) | set(after)
             if before.get(name) != after.get(name)}

    summary = {
        "schemaVersion": 1,
        "release": "spec-e2c-d4-regression",
        "excludedByMatrix": {
            "target": "test-e1-c-static",
            "why": "e2/validation-matrix-v1.json's d4-regression oracle names it "
                   "as NOT run; check_e1_c_bundle_intact and "
                   "test-e1-c-frozen-guard stand in its place.",
        },
        "targets": results,
        "artifactsBefore": before,
        "artifactsAfter": after,
        "artifactsUnchanged": not moved,
        "artifactsMoved": moved,
        "pass": all(item["pass"] for item in results) and not moved,
    }
    write_json(args.output / "summary.json", summary)
    print(json.dumps({
        "output": str(args.output),
        "targets": len(results),
        "failed": [item["command"][-1] for item in results if not item["pass"]],
        "artifactsUnchanged": summary["artifactsUnchanged"],
        "pass": summary["pass"],
    }, indent=2, ensure_ascii=False))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
