#!/usr/bin/env python3
"""Read whatever `engine-side-*.json` files are present and print every attempt.

Form 2 by AGENTS.md §1: the rows are generated from the artifacts, so an
attempt that is added, or one that fails, appears here without anybody editing
a list.  Nothing is filtered out -- VOID and NOT_REPRODUCED attempts print too.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    files = sorted(HERE.glob("engine-side-*.json"))
    if not files:
        print("no engine-side-*.json in", HERE)
        return 1
    overall: Counter = Counter()
    uncounted: Counter = Counter()
    for path in files:
        report = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n=== {path.name} ===")
        print(f"label={report.get('label')} profile={report.get('profile')} "
              f"page={report.get('pageSha256', '')[:16]} "
              f"wasm={report.get('wasmSha256', '')[:16]}")
        print(f"{'dir':5} {'#':>2} {'outcome':16} {'engineCell':22} "
              f"{'ab':16} {'C':18} {'P':8} {'lok@boundary':14} "
              f"{'lok@moving':22} seq")
        for entry in report.get("attempts", []):
            cell = entry.get("cell") or {}
            moving = cell.get("movingPresses") or []
            moving_ids = ";".join(
                f"{m['press']}:{m['lokIds']}" for m in moving) or "-"
            key = (f"{entry.get('outcome')}/{cell.get('engineCell')}"
                   f"/{cell.get('abCell')}")
            # A shakedown is not a counted attempt, and merging the two would
            # hide that its cell was produced by the pre-change classifier.
            if report.get("label") == "matrix":
                overall[key] += 1
            else:
                uncounted[f"{report.get('label')}: {key}"] += 1
            print(f"{entry.get('direction', ''):5} {entry.get('attempt', 0):>2} "
                  f"{str(entry.get('outcome')):16} "
                  f"{str(cell.get('engineCell')):22} "
                  f"{str(cell.get('abCell')):16} "
                  f"{str(cell.get('controlCode')):18} "
                  f"{str(cell.get('actionCode')):8} "
                  f"{str(cell.get('lokIdsInWindow')):14} "
                  f"{moving_ids:22} "
                  f"{cell.get('sourceSequenceAfterVerdict')}")
        print("counts:", json.dumps(report.get("counts", {}), ensure_ascii=False))
    print("\n=== counted attempts (label 'matrix') ===")
    for key, count in sorted(overall.items()):
        print(f"{count:3}  {key}")
    print(f"{sum(overall.values()):3}  TOTAL COUNTED")
    if uncounted:
        print("\n=== uncounted (shakedown), reported because every attempt is ===")
        for key, count in sorted(uncounted.items()):
            print(f"{count:3}  {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
