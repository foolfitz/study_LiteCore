#!/usr/bin/env python3
"""Finding 177 diagnosis: the same typing probe with the main-loop pacing changed in the mirror's copy of probe.js only.
Nothing in dist/ or the tree changes.  argv: PATCH-NAME BROWSER DOCUMENT GAP CHARS OUT"""
import sys
from pathlib import Path
TOOLS = Path(__file__).resolve().parents[5] / "wasm_sdk_probe/tools"
sys.path.insert(0, str(TOOLS))
import probe_typing_latency as p
PATCHES = {"none": "", "immediate": "mode=2;value=0;", "timeout0": "mode=0;value=0;"}
name, browser, document, gap, chars, out = sys.argv[1:7]
RELATIVE = "profiles/e2-editor-v28/probe.js"
MARKER = "var _emscripten_set_main_loop_timing=(mode,value)=>{"
source = (p.DIST / RELATIVE).read_text(encoding="utf-8")
assert source.count(MARKER) == 1
patched = source.replace(MARKER, MARKER + PATCHES[name]).encode("utf-8")
build = p.pp.build_mirror
p.pp.build_mirror = lambda src, mirror, overrides: build(src, mirror, {**overrides, RELATIVE: patched})
sys.argv = ["probe_typing_latency.py", "--browser", browser, "--document", document, "--gap", gap, "--chars", chars, "--out", out]
raise SystemExit(p.main())
