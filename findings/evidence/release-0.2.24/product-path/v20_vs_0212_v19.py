#!/usr/bin/env python3
"""Descriptive, not judged (../../release-0.2.23/product-path/PREDICTION.md, carried by this release's PREDICTION.md):
each cell of this release's plain arm (v20, page 901dd6a6...) against 0.2.12's plain arm (v19, page 8909564e..., the
last complete net before the batch), per browser, 3 rounds each.  Prints the cells whose outcome counts differ and the
cells where 0.2.12's v19 passed every round and this v20 did not (predicted: none).  The shape of
../../release-0.2.12/product-path/old-vs-new-v19.txt.  Reads only the 12 reports; writes nothing.
Run: python3 -I v20_vs_0212_v19.py [NEW_DIR [OLD_DIR]]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEW = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE
OLD = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parents[1] / "release-0.2.12" / "product-path"


def cells(d: Path, profile: str, browser: str) -> tuple[list[str], dict[str, list[str]], list[str]]:
    out: dict[str, list[str]] = {}
    ids: list[str] = []
    pages = []
    for n in (1, 2, 3):
        f = d / f"e2-editor-{profile}-{browser}-r{n}.json"
        r = json.loads(f.read_text())
        pages.append(r["servedShell"]["entrypointSha256"][:16])
        for c in r["checks"]:
            if c["id"] not in out:
                ids.append(c["id"])
            out.setdefault(c["id"], []).append(c["outcome"])
    return ids, out, pages


def fmt(outcomes: list[str]) -> str:
    c = Counter("NE" if o == "NOT_ESTABLISHED" else o for o in outcomes)
    return ", ".join(f"{c[k]} {k}" for k in ("PASS", "FAIL", "NE") if c[k])


def main() -> int:
    total_worse = 0
    print(f"Descriptive: old = v19 reports in {OLD}, new = v20 reports in {NEW}; 3 rounds per arm")
    for b in ("chrome", "firefox"):
        old_ids, old, old_pages = cells(OLD, "v19", b)
        new_ids, new, new_pages = cells(NEW, "v20", b)
        print(f"\n{b}: old entrypoints {sorted(set(old_pages))}, new entrypoints {sorted(set(new_pages))}")
        if old_ids != new_ids:
            print(f"  check ids differ: only old {sorted(set(old_ids) - set(new_ids))}, only new {sorted(set(new_ids) - set(old_ids))}")
        common = [i for i in new_ids if i in old]
        differ = [i for i in common if Counter(old[i]) != Counter(new[i])]
        worse = [i for i in common if all(o == "PASS" for o in old[i]) and not all(o == "PASS" for o in new[i])]
        total_worse += len(worse)
        print(f"  {len(common)} cells, {len(differ)} differ, {len(worse)} where the old page passed every round and the new did not")
        for i in differ:
            print(f"    DIFF {i}: old v19 {fmt(old[i])} | new v20 {fmt(new[i])}")
        for i in worse:
            print(f"    WORSE {i}: old v19 {fmt(old[i])} | new v20 {fmt(new[i])}")
    print(f"\ncells where old passed every round and new did not: {total_worse}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
