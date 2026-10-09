#!/usr/bin/env python3
"""DIAGNOSTIC ONLY -- not the 122-B instrument.  Runs tools/probe_typing_latency.py (dbad93c0...) unchanged
except for its paint shim, patched in memory: the two per-call `root.dataset.* = JSON.stringify(...)` writes
(one per stale putImageData, one per fresh one) are coalesced into one write per task (setTimeout 0).  The
recorded times are taken exactly as before; only the instrument's own per-call work moves out of the burst.
Question it answers: how much of the banded page's slower commit is the probe's overhead, which scales with
the number of putImageData calls (1 per re-blit on v58; 22 on A+B)?  Usage: same arguments as the probe.
The report's `runner` is rewritten to say what ran."""
import hashlib, json, sys
from pathlib import Path

TOOLS = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
sys.path.insert(0, str(TOOLS))
import probe_typing_latency as ptl  # noqa: E402

BASE = hashlib.sha256((TOOLS / "probe_typing_latency.py").read_bytes()).hexdigest()
assert BASE.startswith("dbad93c0dcf27fbf"), BASE
s = ptl.PAINT_SHIM
pairs = [
    ("  const stale = [], blits = [];\n",
     "  const stale = [], blits = [];\n  let flushPending = false;\n"
     "  const flush = () => { flushPending = false; root.dataset.blits = JSON.stringify(blits.slice(-600));\n"
     "                        root.dataset.paints = JSON.stringify(stale.slice(-400)); };\n"
     "  const later = () => { if (!flushPending) { flushPending = true; setTimeout(flush, 0); } };\n"),
    ("      root.dataset.blits = JSON.stringify(blits.slice(-600));\n", "      later();\n"),
    ("      root.dataset.paints = JSON.stringify(stale.slice(-400));\n", "      later();\n"),
]
for old, new in pairs:
    assert s.count(old) == 1, old
    s = s.replace(old, new)
ptl.PAINT_SHIM = s

code = ptl.main()
out = Path(sys.argv[sys.argv.index("--out") + 1])
report = json.loads(out.read_text())
report["runner"] = (f"DIAGNOSTIC lazy_shim_probe.py {hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]}"
                    f" over probe {BASE[:16]} (paint shim's dataset writes coalesced)")
out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
sys.exit(code)
