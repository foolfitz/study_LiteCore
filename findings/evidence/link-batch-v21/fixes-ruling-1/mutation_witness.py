#!/usr/bin/env python3
"""Fable ruling 1, Q2 condition 3 (§34.4): the counted mutation against the tree with fix 1.

Calls the product-path runner's own `apply_mutation` for `boundary-move-takes-no-checkpoint`
with the tree (wasm_sdk_probe/) as `base` and a fresh scratch directory: no browser, no runner run.

  - before the mutation's find/replace is updated, the expected outcome is the runner's
    "the tree moved under the mutation" SystemExit (0 hits);
  - after, exactly one hit, and the mirrored session file differs from the tree's by exactly the
    removed checkpoint lines.

Usage: python3 mutation_witness.py <scratch-dir>
"""
import difflib
import hashlib
import sys
import tempfile
from pathlib import Path

PROBE = Path(__file__).resolve().parents[4] / "wasm_sdk_probe"
sys.path.insert(0, str(PROBE / "tools"))
import run_e2_c_product_path as runner  # noqa: E402

NAME = "boundary-move-takes-no-checkpoint"


def main() -> int:
    scratch = Path(tempfile.mkdtemp(prefix="mutation-witness-", dir=sys.argv[1]))
    spec = runner.MUTATIONS[NAME]
    tree_file = PROBE / spec["path"]
    tree_text = tree_file.read_text(encoding="utf-8")
    print(f"mutation: {NAME}")
    print(f"check (must go red): {spec['check']}")
    print(f"path: {spec['path']}")
    print(f"tree file sha256: {hashlib.sha256(tree_file.read_bytes()).hexdigest()}")
    print(f"find: {spec['find']!r}")
    print(f"replace: {spec['replace']!r}")
    print(f"hits in the tree: {tree_text.count(spec['find'])}")
    print(f"scratch: {scratch}")
    try:
        root, info = runner.apply_mutation(NAME, scratch, PROBE)
    except SystemExit as stop:
        print(f"apply_mutation EXITED: {stop}")
        return 0
    mutated = root / spec["path"]
    print(f"apply_mutation applied: {info}")
    print(f"mirrored file is a real file, not a symlink: {mutated.is_file() and not mutated.is_symlink()}")
    print(f"mirrored file sha256: {hashlib.sha256(mutated.read_bytes()).hexdigest()}")
    print("diff tree -> mutated mirror:")
    sys.stdout.writelines(difflib.unified_diff(
        tree_text.splitlines(keepends=True), mutated.read_text(encoding="utf-8").splitlines(keepends=True),
        fromfile=f"tree/{spec['path']}", tofile=f"mirror/{spec['path']}", n=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
