#!/usr/bin/env python3
"""Measure the three variants on both profiles with the corpus tool's own `measure` (same page, same reads),
then print band tops per variant and arm.  Writes measure-<profile>.json and summary.txt beside this file."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE.parents[4] / "wasm_sdk_probe"
sys.path.insert(0, str(PROBE / "tools"))
import compare_layout_corpus as clc  # noqa: E402

docs = sorted((PROBE / "build/mono-discriminator").glob("*.odt"))
assert [d.name for d in docs] == ["A-as-is.odt", "B-asian-noto-sans-cjk-tc.odt", "C-asian-liberation-mono.odt"], docs
results = {}
for profile in ("e2-editor-v17", "e2-editor-v17-cjk-r5-ab"):
    results[profile] = clc.measure(profile, docs, 120)
    (HERE / f"measure-{profile}.json").write_text(json.dumps(results[profile], ensure_ascii=False))
lines = []
for d in docs:
    key = str(d.relative_to(PROBE))
    a, b = (results[p]["documents"][key] for p in results)
    ra, rb = a.get("runs") or [], b.get("runs") or []
    top = max((abs(x[0] - y[0]) for x, y in zip(ra, rb)), default=None) if len(ra) == len(rb) else None
    lines.append(f"{d.name}: v17 bands {len(ra)} unsettled {a.get('unsettled')}; r5-ab bands {len(rb)} "
                 f"unsettled {b.get('unsettled')}; maxTop {top}; band10 tops v17 {ra[10][0] if len(ra) > 10 else None} "
                 f"r5-ab {rb[10][0] if len(rb) > 10 else None}")
(HERE / "summary.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
