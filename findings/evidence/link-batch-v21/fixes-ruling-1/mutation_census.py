"""Hits of every MUTATIONS entry of tools/run_e2_c_product_path.py whose path is the page, the
markup or the v2 session, counted on the TREE files (a hit count other than 1 makes `apply_mutation`
exit).  Usage: python3 mutation_census.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "wasm_sdk_probe" / "tools"))
import run_e2_c_product_path as r
P = r.PROJECT
tree = {"e2-editor-app.js": "web/e2-editor-app.js", "e2-editor.html": "web/e2-editor.html",
        "editor-shell-v2/narrow-editor-v2-session.js": "editor-shell-v2/narrow-editor-v2-session.js"}
for name, spec in r.MUTATIONS.items():
    p = spec["path"]
    if p in tree:
        text = (P / tree[p]).read_text(encoding="utf-8")
        print(f"{text.count(spec['find'])}  {tree[p]}  {name}")
