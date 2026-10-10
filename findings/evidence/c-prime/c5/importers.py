#!/usr/bin/env python3
"""C5 (i)'s importer list (SPEC-M3-production-ui §17.9 (g) S5): which counted runners import a ported module.

Computed, not listed by hand.  The changed modules are the files under wasm_sdk_probe/tools/ that differ between
BASE and the working tree (`git diff --name-only BASE`).  The import graph is read with `ast` from every
tools/*.py (`import X` and `from X import ...` whose X is a tools/ module).  The counted runners are read from a
release's chain script: `SIX="..."` expanded as check_m3_<name>.py, plus every `$T/<name>.py` it runs.

Prints, for each counted runner, whether it reaches a changed module (directly or through other tools modules)
and by which path.  Every runner that does must be in C5 (i)'s zero-difference set: its own pin cannot see a
helper's change (§34.5).

Exit 0: printed, at least one counted runner reaches a changed module.  3: printed, NONE does -- said with
the resolved base, because the plausible cause is a wrong base (codex review 2026-10-11: `--base HEAD~1` one
commit late printed all eight runners clear and exited 0).  2: REFUSED -- no changed module (nothing was
ported against BASE), or no counted runner found in the chain script (the parse found nothing, which must not
read as "no importers").
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TOOLS = ROOT / "wasm_sdk_probe" / "tools"


def graph() -> dict[str, set[str]]:
    local = {p.stem for p in TOOLS.glob("*.py")}
    edges: dict[str, set[str]] = {}
    for p in TOOLS.glob("*.py"):
        found: set[str] = set()
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"), str(p))):
            if isinstance(node, ast.Import):
                found |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                found.add(node.module.split(".")[0])
        edges[p.stem] = found & local - {p.stem}
    return edges


def counted(chain: Path) -> list[str]:
    text = chain.read_text(encoding="utf-8")
    names: list[str] = []
    six = re.search(r'^SIX="([^"]+)"', text, re.M)
    if six:
        names += [f"check_m3_{n}" for n in six.group(1).split()]
    names += re.findall(r"\$T/([A-Za-z0-9_]+)\.py", text)
    return sorted({n for n in names if (TOOLS / f"{n}.py").exists()})


def path_to(edges: dict[str, set[str]], start: str, targets: set[str]) -> list[str] | None:
    seen, queue = {start}, [[start]]
    while queue:
        trail = queue.pop(0)
        if trail[-1] in targets:
            return trail
        for nxt in sorted(edges.get(trail[-1], ())):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(trail + [nxt])
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="git revision before the port")
    parser.add_argument("--chain", required=True, type=Path, help="the release's chain script")
    args = parser.parse_args()
    diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", args.base, "--", "wasm_sdk_probe/tools/"],
                          capture_output=True, text=True, check=True).stdout.split()
    changed = {Path(f).stem for f in diff if f.endswith(".py")}
    runners = counted(args.chain)
    resolved = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h %s", args.base],
                              capture_output=True, text=True, check=True).stdout.strip()
    print(f"base {args.base} = {resolved[:90]}")
    print(f"changed {sorted(changed)}")
    print(f"counted runners from {args.chain.name}: {runners}")
    if not changed:
        print("REFUSED: no tools/ module differs from the base")
        return 2
    if not runners:
        print("REFUSED: the chain script names no counted runner")
        return 2
    edges = graph()
    reach = {r: path_to(edges, r, changed) for r in runners}
    for r in runners:
        print(f"{'IMPORTS ' if reach[r] else 'clear   '} {r}" + (f"  via {' -> '.join(reach[r])}" if reach[r] else ""))
    reached = sum(1 for v in reach.values() if v)
    print(f"SUMMARY {reached} of {len(runners)} counted runners reach a changed module")
    if not reached:
        print(f"NOTE: none does -- is {args.base} really the commit before the change?")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
