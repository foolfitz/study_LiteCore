#!/usr/bin/env python3
"""M1-1 (SPEC-M3-paragraph-merge 4.1 as amended in 10.2): option B reaches only
the v15 objects.

Population, taken from the Makefile, not listed: every rule of the form
`$(NAME_BUILD)/%.o: src/%.cpp`, every object in `$(NAME_OBJECTS)`.  For each
object the compile command is the Makefile's own expansion (`make -n -B
EXTRA_DEFINES= <object>`, a dry run: nothing is compiled), turned into a
preprocessing run (`-E -P`).  Each run happens twice, from two scratch trees
holding `src/` at BASE (a git ref before B's engine code) and `src/` as it is
in the working tree, with the same relative paths, so `__FILE__` and the
include chain are identical.  Every object of every rule must preprocess to
the same bytes, except the rule named by --v15, whose objects must differ
somewhere (otherwise B is not in it).

Also, for the v15 rule's probe_engine object (3.1 item 10): adding
-DOXSDK_MAINLOOP_ENGINE, or removing -DOXSDK_FINDING_016_SELECTION_BARRIER,
must make preprocessing fail.

Non-vacuity: the rules for v8 (E2_V8), v14 (E2_V14) and v15 must all be found,
and at least 20 rules in all; a rule without objects is an error.

Red case (--inject RULE=FLAG, test only): adds FLAG to that rule's commands;
with B's code present, injecting -DOXSDK_MERGE_KEY_UNDO into E2_V8 must turn
it red.

Usage: check_merge_key_undo_scope.py --base REF [--v15 NAME] [--inject RULE=FLAG] [--json OUT]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RULE = re.compile(r"^\$\(([A-Z0-9_]+)_BUILD\)/%\.o: src/%\.cpp")
REQUIRED = ("E2_V8", "E2_V14")


def make(*args: str) -> str:
    return subprocess.run(["make", "-s", "--no-print-directory", "EXTRA_DEFINES=", *args],
                          cwd=HERE, capture_output=True, text=True, check=True).stdout


def objects(rule: str) -> list[str]:
    out = make("--eval", "print-var-%: ; @echo $($*)", f"print-var-{rule}_OBJECTS")
    return out.split()


def compile_command(obj: str) -> list[str]:
    out = make("-n", "-B", obj).replace("\\\n", " ")  # recipes continue lines with a backslash
    for line in out.splitlines():
        if not re.search(r"\s-c\s+src/", line) or obj not in line:
            continue
        args = shlex.split(line)
        if "-c" in args and "-o" in args and args[args.index("-o") + 1] == obj:
            return args
    raise SystemExit(f"no compile command for {obj} in:\n{out}")


def preprocess_args(args: list[str], inject: list[str]) -> list[str]:
    out = []
    skip = False
    for i, arg in enumerate(args):
        if skip:
            skip = False
            continue
        if i == 0:
            out.append(str((HERE / arg).resolve()) if "/" in arg else arg)
        elif arg == "-o":
            skip = True
        elif arg == "-c":
            continue
        elif arg.startswith("-I") and not arg.startswith("-I/"):
            out.append("-I" + str((HERE / arg[2:]).resolve()))
        else:
            out.append(arg)
    return out[:1] + inject + ["-E", "-P"] + out[1:]


def run(args: list[str], tree: Path) -> tuple[int, str, str]:
    p = subprocess.run(args, cwd=tree, capture_output=True)
    return p.returncode, hashlib.sha256(p.stdout).hexdigest(), p.stderr.decode(errors="replace")[-400:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--v15", default="E2_V15")
    ap.add_argument("--inject", action="append", default=[])
    ap.add_argument("--json")
    a = ap.parse_args()
    inject: dict[str, list[str]] = {}
    for item in a.inject:
        rule, flag = item.split("=", 1)
        inject.setdefault(rule, []).append(flag)

    rules = [m.group(1) for line in (HERE / "Makefile").read_text().splitlines()
             if (m := RULE.match(line))]
    failures = []
    for need in (*REQUIRED, a.v15):
        if need not in rules:
            failures.append(f"rule {need} not found in the Makefile")
    if len(rules) < 20:
        failures.append(f"only {len(rules)} rules found")

    with tempfile.TemporaryDirectory() as tmp:
        base, cur = Path(tmp, "base"), Path(tmp, "cur")
        base.mkdir()
        archive = subprocess.run(["git", "archive", a.base, "src"], cwd=HERE,
                                 capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(base)], input=archive, check=True)
        shutil.copytree(HERE / "src", cur / "src")

        jobs = []
        for rule in rules:
            objs = objects(rule)
            if not objs:
                failures.append(f"{rule}: no objects")
            for obj in objs:
                jobs.append((rule, obj, preprocess_args(compile_command(obj), inject.get(rule, []))))

        def both(job):
            rule, obj, args = job
            return rule, obj, run(args, base), run(args, cur)

        rows = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            for rule, obj, rb, rc in pool.map(both, jobs):
                # A rule whose flags cannot preprocess today's source (an old
                # diagnostic rule) fails the same way at BASE and now: B cannot
                # have changed it.  Failing on one side only is a difference.
                unbuildable = rb[0] != 0 and rc[0] != 0 and rb[2] == rc[2]
                row = {"rule": rule, "object": obj, "baseExit": rb[0], "curExit": rc[0],
                       "unbuildable": unbuildable,
                       "same": unbuildable or (rb[0] == 0 and rc[0] == 0 and rb[1] == rc[1])}
                rows.append(row)
                if (rb[0] or rc[0]) and not unbuildable:
                    failures.append(f"{rule} {obj}: preprocessing failed on one side: {(rb[2] or rc[2]).strip()}")
                elif rule != a.v15 and not row["same"]:
                    failures.append(f"{rule} {obj}: preprocessed output differs from {a.base}")
        if a.v15 in rules and any(r["unbuildable"] for r in rows if r["rule"] == a.v15):
            failures.append(f"{a.v15}: an object does not preprocess")
        if a.v15 in rules and not any(not r["same"] for r in rows if r["rule"] == a.v15):
            failures.append(f"{a.v15}: no object differs from {a.base} (B is not in it)")

        # 3.1 item 10: the compile guard.
        guards = []
        engine = [j for j in jobs if j[0] == a.v15 and j[1].endswith("/probe_engine.o")]
        for rule, obj, args in engine:
            with_mainloop = args[:1] + ["-DOXSDK_MAINLOOP_ENGINE"] + args[1:]
            without_barrier = [x for x in args if x != "-DOXSDK_FINDING_016_SELECTION_BARRIER"]
            for name, variant in (("with OXSDK_MAINLOOP_ENGINE", with_mainloop),
                                  ("without OXSDK_FINDING_016_SELECTION_BARRIER", without_barrier)):
                code = run(variant, cur)[0]
                guards.append({"variant": name, "exit": code})
                if code == 0:
                    failures.append(f"{rule}: preprocessing {name} did not fail")
        if a.v15 in rules and not engine:
            failures.append(f"{a.v15}: no probe_engine object")

    summary = {"rules": len(rules), "objects": len(rows),
               "different": sum(1 for r in rows if not r["same"]),
               "unbuildable": sorted({f"{r['rule']} {r['object']}" for r in rows if r["unbuildable"]}),
               "guards": guards}
    if a.json:
        Path(a.json).write_text(json.dumps({"summary": summary, "rows": rows,
                                            "failures": failures}, indent=1) + "\n")
    print(json.dumps(summary))
    for f in failures:
        print("FAIL " + f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
