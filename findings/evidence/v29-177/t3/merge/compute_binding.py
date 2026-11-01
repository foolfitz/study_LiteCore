#!/usr/bin/env python3
"""The merge binding for v29 on generation 83: run_merge_wasm_shakedown.bound_values for the profile, the way main() does,
without a browser (findings/evidence/v19/post-link/compute_binding.py), with the shell manifest rebound to generation 83
first, as the wrapper does.  Run from wasm_sdk_probe/.  Writes binding.json beside this file; prints the diff to v28's."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / "tools"))
import build_e2_c_shell_bundle as bundle
bundle.MANIFEST = Path("e2/editor-shell-v2-bundle-v83.json")
import run_merge_wasm_shakedown as r
pp = r.pp
PROFILE = "e2-editor-v29"
root = r.HERE / "dist"
source = pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8")
lagging = pp.shell_lagging_source(root)
page, pin_before, wasm = pp.repointed_page(source, PROFILE, root / "profiles" / PROFILE / "sdk-manifest.json")
bound = r.bound_values(root, PROFILE, page, source, (root / "e2-editor.html").read_text(encoding="utf-8"))
if set(bound) != set(r.BOUND_KEYS):
    raise SystemExit(f"bound keys differ: {sorted(bound)}")
out = {"profile": PROFILE, "lagging": lagging, "pinBefore": pin_before, "pinAfter": wasm[:16],
       "shellManifest": bundle.MANIFEST.as_posix(), "proposedMergeBinding": bound}
Path(__file__).with_name("binding.json").write_text(json.dumps(out, indent=1) + "\n")
v28 = json.loads(Path("../findings/evidence/k-0.2.44/k-binding-inventory.json").read_bytes())["proposedMergeBinding"]
print("lagging", lagging)
for k in r.BOUND_KEYS:
    print(f"{'MOVED' if bound[k] != v28[k] else 'same '} {k} {v28[k][:16]} -> {bound[k][:16]}")
