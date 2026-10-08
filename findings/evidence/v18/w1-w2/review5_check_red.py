#!/usr/bin/env python3
"""End-to-end red case for build_cjk_subset_mono_pack.py --check's on-disk comparison (opus review item 5).

Copies the shipped cjk-sub-e5 data and v18's cjk-sub-e10 data and metadata into a fresh temporary directory, flips one
bit of the e10 data (offset 1000), points the tool's RESOURCES at that directory and runs its own main() with --check.
Expected: exit 1 with exactly one FAIL, naming the e10 data ("is not the bytes the tool builds").  Writes nothing in
the repository or in dist/.  Run from the repository root:
    python3 -I findings/evidence/v18/w1-w2/review5_check_red.py > findings/evidence/v18/w1-w2/review5-check-red.txt
"""
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROBE = ROOT / "wasm_sdk_probe"
RES = PROBE / "dist/profiles/resources"
TOOL = PROBE / "tools/build_cjk_subset_mono_pack.py"
E5 = [e["data"].split("/")[-1] for e in json.loads((PROBE / "sdk/v17-writer-review-manifest.json").read_text())
      ["resourcePacks"] if e["id"] == "cjk-sub-e5"][0]
E10 = ["cjk-sub-e10.06976180177c8bd2.data", "cjk-sub-e10.4144b2b2a44dd797.metadata"]

sys.path.insert(0, str(TOOL.parent))
spec = importlib.util.spec_from_file_location("mono_pack", TOOL)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
with tempfile.TemporaryDirectory() as tmp:
    res = Path(tmp)
    for name in [E5] + E10:
        shutil.copyfile(RES / name, res / name)
    data = bytearray((res / E10[0]).read_bytes())
    data[1000] ^= 1
    (res / E10[0]).write_bytes(bytes(data))
    tool.RESOURCES = res
    sys.argv = [str(TOOL), "--check"]
    rc = tool.main()
print(f"exit {rc}")
sys.exit(0 if rc == 1 else 1)
