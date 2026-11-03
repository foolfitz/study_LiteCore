#!/usr/bin/env python3
"""SPEC-P-calc-undo, before the link (Codex review 1): every `_oxsdk_*` name the ods-editor-v4 exports rule lists has a function body in
the v4 objects' sources after preprocessing with v4's defines.  An export without a definition fails the link, and -fsyntax-only cannot
see it.

Tool-closed: the names are read from the Makefile's `$(ODS_EDITOR_V4_BUILD)/exports.txt` rule, not listed here.  em++ -E only (nothing
produced, no make), taskset -c 0, refuses while a make runs.  Red case: --red-source runs the same check on another copy of sdk_api.cpp
(the one before the fix, `git show bacfd8c84:wasm_sdk_probe/src/sdk_api.cpp`) and must find undo and redo missing.
  check_calc_undo_ships.py --out DIR [--red-source FILE]
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

import check_calc_undo_syntax as syntax

SDK = syntax.SDK
V4 = syntax.ENGINE_V3 + ["-DOXSDK_ODS_UNDO"]


def exported_names():
    text = (SDK / "Makefile").read_text()
    start = text.index("$(ODS_EDITOR_V4_BUILD)/exports.txt:")
    rule = text[start:text.index("\n\n", start)]
    return sorted({n.lstrip("_") for n in re.findall(r"\b_oxsdk_[a-z_]+", rule)})


def defined(sources, defines):
    found = set()
    for source in sources:
        done = subprocess.run(["taskset", "-c", "0", str(syntax.EMXX), "-E", "-P", *syntax.CPPFLAGS, f"-I{SDK / 'src'}", *defines,
                               str(source)], capture_output=True, text=True, cwd=SDK)
        if done.returncode:
            raise SystemExit(f"em++ -E failed on {source}: {done.stderr[-400:]}")
        found |= set(re.findall(r"\b(oxsdk_[a-z_]+)\s*\([^;{}]*\)\s*\{", done.stdout))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--red-source", type=Path)
    args = parser.parse_args()
    if subprocess.run(["pgrep", "-a", "make"], capture_output=True).returncode == 0:
        raise SystemExit("a make is running; ask the owner first")
    names = exported_names()
    sources = [SDK / "src/sdk_api.cpp", SDK / "src/probe_engine.cpp"]
    if args.red_source:
        sources[0] = args.red_source.resolve()
    found = defined(sources, V4)
    missing = [n for n in names if n not in found]
    report = {"uptime": subprocess.check_output(["uptime"], text=True).strip(), "sources": [str(s) for s in sources],
              "defines": V4, "exported": names, "missing": missing, "verdict": "SHIPS" if names and not missing else "MISSING"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"verdict": report["verdict"], "exported": len(names), "missing": missing}))
    return 0 if report["verdict"] == "SHIPS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
