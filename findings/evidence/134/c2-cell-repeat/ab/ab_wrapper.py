#!/usr/bin/env python3
"""DIAGNOSTIC (ruling-2 condition 1): the counted C2 cell through `probe_typing_latency_view.py`, unchanged,
with the probe's own mirror carrying the page bytes given here as `e2-editor-app.js`.  dist/ is never
written: `pp.build_mirror` is wrapped to add one override, and the wrapper checks that the mirror holds a
real file with those bytes (not a symlink back into dist/).  The report's `page` becomes the sha256 of the
bytes served; `runner` says DIAGNOSTIC.  Both arms of the A/B go through this, the 0.2.16 arm included.

  ab_wrapper.py --page-bytes PATH <the view wrapper's own arguments>
"""
import hashlib
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
TOOLS = ROOT / "wasm_sdk_probe" / "tools"
VIEW = TOOLS / "probe_typing_latency_view.py"
sys.path.insert(0, str(TOOLS))
import run_e2_c_product_path as pp  # noqa: E402  -- the same module object the probe uses

i = sys.argv.index("--page-bytes")
page_bytes = Path(sys.argv[i + 1]).read_bytes()
del sys.argv[i:i + 2]
page_sha = hashlib.sha256(page_bytes).hexdigest()
served: dict = {}
native_build_mirror = pp.build_mirror


def build_mirror(source, target, overrides):
    native_build_mirror(source, target, {**overrides, "e2-editor-app.js": page_bytes})
    path = Path(target) / "e2-editor-app.js"
    served.update(isSymlink=path.is_symlink(), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    if served["isSymlink"] or served["sha256"] != page_sha:
        raise SystemExit(f"the mirror does not serve the given page: {served}")


pp.build_mirror = build_mirror
out = Path(sys.argv[sys.argv.index("--out") + 1])
sys.argv = [str(VIEW)] + sys.argv[1:]
code = 0
try:
    runpy.run_path(str(VIEW), run_name="__main__")
except SystemExit as exit_:
    code = exit_.code if isinstance(exit_.code, int) else (0 if exit_.code is None else 1)
if not served:
    sys.exit("the probe never built its mirror; nothing was served from the given bytes")
report = json.loads(out.read_text())
report["pageInDist"] = report.get("page")
report["page"] = page_sha
report["servedFromMirror"] = served
report["runner"] = (f"DIAGNOSTIC ab_wrapper.py {hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]}"
                    f" over {report.get('runner')}")
out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
sys.exit(code)
