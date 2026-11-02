#!/usr/bin/env python3
"""Generation 86's freeze argv = generation 85's (../freeze-85/argv.json) with the manifest name changed and two exclusions added:
the v31 worker source and the Calc v3 worker source, on the same terms as every earlier feature worker.
  python3 -I freeze.py dry|write          (run from wasm_sdk_probe/)
"""
import json, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent
argv = json.loads((E.parent / "freeze-85/argv.json").read_text())
assert argv.count("e2/editor-shell-v2-bundle-v85.json") == 1
argv = [a.replace("e2/editor-shell-v2-bundle-v85.json", "e2/editor-shell-v2-bundle-v86.json") for a in argv]
argv += ["--exclude", "sdk/v31-alignment-worker.js=Source of the ABI6 e2-editor-v31 profile worker, separately bound by the profile manifest workerSha256 (54352fad...) and copied into dist/profiles/e2-editor-v31; the product page creates its worker from the profile, never from this path (SPEC-P-demo-batch-3 section 3.2)."]
argv += ["--exclude", "sdk/ods-editor-v3-worker.js=Source of the Calc ods-editor-v3 profile worker, copied into dist/profiles/ods-editor-v3 (6df70322...); not reached from the Writer page's import graph (SPEC-P-demo-batch-3 section 3.1)."]
mode = sys.argv[1]
run = [a for a in argv if a != "--write"] if mode == "dry" else argv
p = subprocess.run([sys.executable] + run, capture_output=True, text=True)
(E / f"{mode}.stdout.txt").write_text(p.stdout); (E / f"{mode}.stderr.txt").write_text(p.stderr)
(E / f"{mode}.exit.txt").write_text(f"exit={p.returncode}\n")
if mode == "write":
    (E / "argv.json").write_text(json.dumps(argv, indent=1, ensure_ascii=False) + "\n")
print(mode, "exit", p.returncode); print(p.stdout[-900:]); print(p.stderr[-500:])
