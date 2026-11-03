#!/usr/bin/env python3
"""Generation 88's freeze argv = generation 87's (../../demo-batch-4/freeze-87/argv.json) with the manifest name changed.  No new source: the
change is web/e2-editor-app.js, which the bundle already covers (SPEC-P-demo-batch-5).
  python3 -I freeze.py dry|write          (run from wasm_sdk_probe/)
"""
import json, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent
argv = json.loads((E.parent.parent / "demo-batch-4/freeze-87/argv.json").read_text())
assert argv.count("e2/editor-shell-v2-bundle-v87.json") == 1
argv = [a.replace("e2/editor-shell-v2-bundle-v87.json", "e2/editor-shell-v2-bundle-v88.json") for a in argv]
mode = sys.argv[1]
run = [a for a in argv if a != "--write"] if mode == "dry" else argv
p = subprocess.run([sys.executable] + run, capture_output=True, text=True)
(E / f"{mode}.stdout.txt").write_text(p.stdout); (E / f"{mode}.stderr.txt").write_text(p.stderr)
(E / f"{mode}.exit.txt").write_text(f"exit={p.returncode}\n")
if mode == "write":
    (E / "argv.json").write_text(json.dumps(argv, indent=1, ensure_ascii=False) + "\n")
print(mode, "exit", p.returncode); print(p.stdout[-500:]); print(p.stderr[-300:])
