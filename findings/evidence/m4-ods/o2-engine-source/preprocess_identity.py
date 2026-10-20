#!/usr/bin/env python3
"""One-shot measurement (SPEC-M4-ods-in-nextcloud O2): does the viewer's engine source move any
object of any rule that exists in the Makefile?

Not a check in a chain: it reuses `wasm_sdk_probe/tools/check_merge_key_undo_scope.py`'s machinery
(the Makefile's own compile command per object, from `make -n -B`, a dry run; preprocessed `-E -P`
from a scratch tree holding `src/` at BASE and one holding `src/` as it is now) and reports, per
object: same tokens, different tokens, or unbuildable on both sides.  It cannot be the tool itself:
that one requires carriers of the merge define and checks that define's compile guards.

  python3 -I preprocess_identity.py --base REF [--json OUT]
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[4] / "wasm_sdk_probe"
sys.path.insert(0, str(PROJECT / "tools"))
import check_merge_key_undo_scope as scope  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    rules = [m.group(1) for line in (PROJECT / "Makefile").read_text().splitlines()
             if (m := scope.RULE.match(line))]
    with tempfile.TemporaryDirectory() as tmp:
        base, cur = Path(tmp, "base"), Path(tmp, "cur")
        base.mkdir()
        archive = subprocess.run(["git", "archive", a.base, "src"], cwd=PROJECT,
                                 capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(base)], input=archive, check=True)
        shutil.copytree(PROJECT / "src", cur / "src")
        jobs = [(rule, obj, scope.preprocess_args(scope.compile_command(obj), []))
                for rule in rules for obj in scope.objects(rule)]

        def both(job):
            rule, obj, args = job
            return rule, obj, scope.run(args, base), scope.run(args, cur)

        rows = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            for rule, obj, rb, rc in pool.map(both, jobs):
                rows.append({"rule": rule, "object": obj, "baseExit": rb[0], "curExit": rc[0],
                             "same": rb[0] == 0 and rc[0] == 0 and rb[1] == rc[1],
                             "unbuildableBothSides": rb[0] != 0 and rc[0] != 0,
                             "baseError": rb[2][-200:] if rb[0] else "",
                             "curError": rc[2][-200:] if rc[0] else ""})
    different = [r for r in rows if not r["same"] and not r["unbuildableBothSides"]]
    summary = {"base": a.base, "rules": len(rules), "objects": len(rows),
               "same": sum(r["same"] for r in rows),
               "unbuildableBothSides": sum(r["unbuildableBothSides"] for r in rows),
               "different": [f"{r['rule']} {r['object']} (base exit {r['baseExit']}, now {r['curExit']})"
                             for r in different]}
    if a.json:
        Path(a.json).write_text(json.dumps({"summary": summary, "rows": rows}, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    if not rows or len(rules) < 20:
        print("FAIL the population is empty or too small")
        return 2
    return 1 if different else 0


if __name__ == "__main__":
    sys.exit(main())
