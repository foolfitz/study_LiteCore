#!/usr/bin/env python3
"""Descriptive, not criteria: paragraph text of the kept documents across browsers and against v17's run, and
key-to-response latency.  Run from the repository root:
    python3 -I findings/evidence/v18/merge/descriptive.py > findings/evidence/v18/merge/descriptive-output.txt
Reads kept documents with the runner's own `odt_parts`; prints file names and counts, no text.  Writes nothing.
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "wasm_sdk_probe/tools"))
from run_merge_wasm_shakedown import odt_parts  # noqa: E402

E = ROOT / "findings/evidence"


def texts(d):
    return {f.name: odt_parts(f.read_bytes())["paragraphs"] for f in sorted(d.glob("*.odt"))}


for side in ("shakedown", "control"):
    c, f = texts(E / f"v18/merge/{side}-chrome.docs"), texts(E / f"v18/merge/{side}-firefox.docs")
    both = sorted(set(c) & set(f))
    print(f"v18 {side}: Chrome {len(c)} docs, Firefox {len(f)}, both {len(both)}; "
          f"paragraph text differs in {[n for n in both if c[n] != f[n]] or 'none'}")
for b in ("chrome", "firefox"):
    for side in ("shakedown", "control"):
        a, o = texts(E / f"v18/merge/{side}-{b}.docs"), texts(E / f"v17/merge/{side}-{b}.docs")
        both = sorted(set(a) & set(o))
        print(f"v18 vs v17 {side}-{b}: {len(a)} vs {len(o)} docs, both {len(both)}; "
              f"paragraph text differs in {[n for n in both if a[n] != o[n]] or 'none'}")
for b in ("chrome", "firefox"):
    ms = [c["keyToResponseMs"] for c in json.loads((E / f"v18/merge/shakedown-{b}.json").read_text())["cases"]
          if c.get("keyToResponseMs") is not None]
    print(f"keyToResponseMs {b} (listed, not judged): n {len(ms)} min {min(ms)} "
          f"median {round(statistics.median(ms), 2)} max {max(ms)}")
