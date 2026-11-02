#!/usr/bin/env python3
"""Generation 87's freeze argv = generation 86's (../../demo-batch-3/freeze-86/argv.json) with the manifest name changed, the frozen date and one
exclusion added: the v32 worker source, on the same terms as every earlier feature worker.
  python3 -I freeze.py dry|write          (run from wasm_sdk_probe/)
"""
import json, subprocess, sys
from pathlib import Path
E = Path(__file__).resolve().parent
argv = json.loads((E.parent.parent / "demo-batch-3/freeze-86/argv.json").read_text())
assert argv.count("e2/editor-shell-v2-bundle-v86.json") == 1
argv = [a.replace("e2/editor-shell-v2-bundle-v86.json", "e2/editor-shell-v2-bundle-v87.json") for a in argv]
assert argv.count("2026-11-02") == 1
argv = [a.replace("2026-11-02", "2026-11-03") for a in argv]
argv += ["--exclude", "sdk/v32-paragraph-read-worker.js=Source of the ABI6 e2-editor-v32 profile worker, separately bound by the profile manifest workerSha256 (c394302c...) and copied into dist/profiles/e2-editor-v32; the product page creates its worker from the profile, never from this path (SPEC-P-demo-batch-4 section 5)."]
mode = sys.argv[1]
run = [a for a in argv if a != "--write"] if mode == "dry" else argv
p = subprocess.run([sys.executable] + run, capture_output=True, text=True)
(E / f"{mode}.stdout.txt").write_text(p.stdout); (E / f"{mode}.stderr.txt").write_text(p.stderr)
(E / f"{mode}.exit.txt").write_text(f"exit={p.returncode}\n")
if mode == "write":
    (E / "argv.json").write_text(json.dumps(argv, indent=1, ensure_ascii=False) + "\n")
print(mode, "exit", p.returncode); print(p.stdout[-900:]); print(p.stderr[-500:])
