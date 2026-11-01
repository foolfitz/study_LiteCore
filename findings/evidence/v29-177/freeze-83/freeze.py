#!/usr/bin/env python3
"""Generation 83's freeze argv = generation 82's (../../v28-083/freeze-82/argv.json) with the manifest name and the
frozen date changed. No exclusion is added: v29 reuses the v28 worker source byte for byte (spec section 2).
  python3 -I freeze.py dry|write          (run from wasm_sdk_probe/)
"""
import json, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent
argv = json.loads((E.parent.parent / "v28-083/freeze-82/argv.json").read_text())
assert argv.count("e2/editor-shell-v2-bundle-v82.json") == 1 and argv.count("2026-10-30") == 1
argv = [a.replace("e2/editor-shell-v2-bundle-v82.json", "e2/editor-shell-v2-bundle-v83.json") for a in argv]
argv[argv.index("2026-10-30")] = "2026-11-01"
mode = sys.argv[1]
run = [a for a in argv if a != "--write"] if mode == "dry" else argv
p = subprocess.run([sys.executable] + run, capture_output=True, text=True)
(E / f"{mode}.stdout.txt").write_text(p.stdout); (E / f"{mode}.stderr.txt").write_text(p.stderr)
(E / f"{mode}.exit.txt").write_text(f"exit={p.returncode}\n")
if mode == "write":
    (E / "argv.json").write_text(json.dumps(argv, indent=1, ensure_ascii=False) + "\n")
print(mode, "exit", p.returncode); print(p.stdout[-1800:]); print(p.stderr[-600:])
