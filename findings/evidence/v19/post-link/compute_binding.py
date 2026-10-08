"""Compute run_merge_wasm_shakedown.bound_values for a profile, the way main() does, without a browser."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tools"))
import run_merge_wasm_shakedown as r
pp = r.pp
profile = sys.argv[1]
root = r.HERE / "dist"
source = pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8")
lagging = pp.shell_lagging_source(root)
manifest = root / "profiles" / profile / "sdk-manifest.json"
page, pin_before, wasm = pp.repointed_page(source, profile, manifest)
html = (root / "e2-editor.html").read_text(encoding="utf-8")
bound = r.bound_values(root, profile, page, source, html)
print(json.dumps({"profile": profile, "lagging": lagging, "pinBefore": pin_before, "pinAfter": wasm[:16],
                  "shellManifest": str(pp.SHELL_BUNDLE_V2), "bound": bound}, indent=1))
