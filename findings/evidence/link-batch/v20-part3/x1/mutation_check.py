#!/usr/bin/env python3
"""Mutates the declared-delta logic of tools/check_profile_identity.py one expression at a time (in memory; the
file is never written) and runs tests.test_profile_identity.DeclaredDeltas against each mutant.  A mutation that
leaves the suite green is a check nobody pins.  Run from wasm_sdk_probe/ :
    python3 ../findings/evidence/link-batch/v20-part3/x1/mutation_check.py
"""
import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, ".")
SRC = Path("tools/check_profile_identity.py").read_text()
MUTATIONS = [
    ("worker must differ from the reference's", "and worker != their_worker", ""),
    ("worker must equal the declared one", "all(worker == w.lower() for w in declared_workers)", "True"),
    ("manifest worker leaf must be the worker", "and mine.get(WORKER_LEAF) == worker)\n    else", ")\n    else"),
    ("declared leaf must be absent from the reference", "path not in theirs and path in mine", "path in mine"),
    ("declared leaf must be present in the candidate", "path not in theirs and path in mine", "path not in theirs"),
    ("declared leaf is compared type-strictly", "same_leaf(mine[path], value)", "mine[path] == value"),
    ("declared leaves are licensed to move", "*(path for path, _ in declared_leaves))", ")"),
    ("the worker leaf is licensed only when a worker is declared",
     "*([WORKER_LEAF] if declared_workers else [])", "WORKER_LEAF"),
    ("declared export must not already be in the reference", "and not any(s in already for s in declared_exports)", ""),
    ("declared exports are appended with a newline each", 'f"{s}\\n".encode()', 's.encode()'),
]
import tests.test_profile_identity as t  # noqa: E402

survivors = 0
for name, old, new in MUTATIONS:
    assert SRC.count(old) >= 1, (name, old)
    spec = importlib.util.spec_from_loader("check_profile_identity", loader=None)
    mod = importlib.util.module_from_spec(spec)
    exec(compile(SRC.replace(old, new, 1), "check_profile_identity(mutant)", "exec"), mod.__dict__)
    t.x = mod
    result = unittest.TextTestRunner(stream=open("/dev/null", "w")).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(t.DeclaredDeltas))
    red = sorted(str(f[0]).split()[0] for f in result.failures + result.errors)
    survivors += not red
    print(f"{'SURVIVED' if not red else 'killed  '} [{name}] by {len(red)} test(s): {', '.join(red[:3])}{' ...' if len(red) > 3 else ''}")
print(f"survivors: {survivors}")
sys.exit(1 if survivors else 0)
