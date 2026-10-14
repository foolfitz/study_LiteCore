#!/usr/bin/env python3
"""Recompute the stored `phases` block of every raw report from its events,
with the probe's current `phases()` (the extraction was corrected twice while
the runs were being made; the events are the record, the block is derived)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "wasm_sdk_probe" / "tools"))
from probe_paste_latency import phases  # noqa: E402


def main() -> int:
    for path in sorted((HERE / "raw").glob("*.json")):
        report = json.loads(path.read_text())
        changed = 0
        for run in report.get("runs") or []:
            fresh = phases(run)
            if run.get("phases") != fresh:
                run["phases"] = fresh
                changed += 1
        if changed:
            path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
        print(f"{path.name}: {changed} run(s) refreshed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
