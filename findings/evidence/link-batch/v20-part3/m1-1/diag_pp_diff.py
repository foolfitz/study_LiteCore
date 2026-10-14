#!/usr/bin/env python3
"""Diagnostic for green-2 (not part of the checker): for one object, preprocess it the way
tools/check_merge_key_undo_scope.py does (its own functions, its own compile command, blank lines dropped) from
`git archive BASE src` and from the working tree, and print a unified diff of the two token streams.
Run from wasm_sdk_probe/:  python3 ../findings/evidence/link-batch/v20-part3/m1-1/diag_pp_diff.py OBJECT BASE
"""
import difflib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "tools")
import check_merge_key_undo_scope as c  # noqa: E402

obj, base = sys.argv[1], sys.argv[2]
with tempfile.TemporaryDirectory() as tmp:
    old, cur = Path(tmp, "base"), Path(tmp, "cur")
    old.mkdir()
    archive = subprocess.run(["git", "archive", base, "src"], cwd=c.HERE, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(old)], input=archive, check=True)
    shutil.copytree(c.HERE / "src", cur / "src")
    args = c.preprocess_args(c.compile_command(obj), [])
    sides = []
    for tree in (old, cur):
        p = subprocess.run(args, cwd=tree, capture_output=True)
        sides.append((p.returncode, [l.rstrip() for l in p.stdout.decode().splitlines() if l.strip()]))
print(f"object {obj}; base {base}; exit base {sides[0][0]} cur {sides[1][0]}; lines base {len(sides[0][1])} cur {len(sides[1][1])}")
for line in difflib.unified_diff(sides[0][1], sides[1][1], f"{base}", "working tree", n=2, lineterm=""):
    print(line)
