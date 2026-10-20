#!/usr/bin/env python3
"""M1-1 (SPEC-M3-paragraph-merge 4.1 as amended in 10.2; 31.3): option B
reaches only the objects of the rules that carry it -- v15 and, since spec 31.3,
v19 (v18 with finding 117's fix, the same defines over the tree's engine).

Population, taken from the Makefile, not listed: every rule of the form
`$(NAME_BUILD)/%.o: src/%.cpp`, every object in `$(NAME_OBJECTS)`.  For each
object the compile command is the Makefile's own expansion (`make -n -B
EXTRA_DEFINES= <object>`, a dry run: nothing is compiled), turned into a
preprocessing run (`-E -P`).  Each run happens twice, from two scratch trees
holding `src/` at BASE (a git ref before B's engine code) and `src/` as it is
in the working tree, with the same relative paths, so `__FILE__` and the
include chain are identical.  Every object of every rule must preprocess to
the same bytes, except the declared objects of each rule named by --carrier
(default E2_V15 and E2_V19, declared object: probe_engine), which must differ
(otherwise B is not in it); a carrier's other objects must be the same as well
(since the review of 2026-10-08: before, one differing object let any number of
others pass).  Before 2026-10-08 there was one such rule (--v15); with one
carrier named, the other carrier's objects differ from BASE and the run is red
-- the red case below that shows the checker sees v19.

Per-carrier object sets (2026-10-14, ruling 6 condition 50 as amended): `--carrier
RULE=obj,obj,...` declares which objects of RULE differ (object names without
`.o`; no `=` means `probe_engine`, as before).  E2_V20 carries the v20 define
into probe_engine, sdk_api and editor_api (the last by two declarations only:
v20-part3/m1-1-witness/editor_api-define-diff.txt), so its set is
`E2_V20=probe_engine,sdk_api,editor_api`.  The declared set is an exception list
over a tool-closed population (every object of every rule): an undeclared object
that differs is red, and a declared object that does not differ is red.

Also, for each carrier's probe_engine object (3.1 item 10): adding
-DOXSDK_MAINLOOP_ENGINE, or removing -DOXSDK_FINDING_016_SELECTION_BARRIER,
must make preprocessing fail.

Non-vacuity: the rules for v8 (E2_V8), v14 (E2_V14) and every carrier must be
found, and at least 20 rules in all; a rule without objects is an error.

Red cases (test only): --inject RULE=FLAG adds FLAG to that rule's commands
(injecting -DOXSDK_MERGE_KEY_UNDO into E2_V8 must turn it red); --carrier
E2_V15 alone must be red (v19 carries B unlisted); naming E2_V8 as a carrier
must be red (it carries no B); a carrier's declared set one object short, or
one object over (declared, did not move), must be red.

Usage: check_merge_key_undo_scope.py --base REF [--carrier RULE[=obj,...] ...] [--inject RULE=FLAG] [--json OUT]
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
CARRIERS = ("E2_V15", "E2_V19")
ENGINE = "probe_engine"


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
    # `-E -P` pads skipped #if blocks with blank lines (first run: one blank
    # line was the whole difference in five a11y rules).  Blank lines carry no
    # tokens, so they are dropped before hashing; anything else counts.
    tokens = b"\n".join(line.rstrip() for line in p.stdout.splitlines() if line.strip())
    return p.returncode, hashlib.sha256(tokens).hexdigest(), p.stderr.decode(errors="replace")[-400:]


def carrier_map(carriers) -> dict[str, tuple[str, ...]]:
    """RULE -> the names of its objects that must differ from BASE.  A plain sequence of rule names (the shape
    before 2026-10-14) means probe_engine only."""
    if isinstance(carriers, dict):
        return {rule: tuple(objs) for rule, objs in carriers.items()}
    return {rule: (ENGINE,) for rule in carriers}


def parse_carrier(item: str) -> tuple[str, tuple[str, ...]]:
    rule, sep, objs = item.partition("=")
    names = tuple(objs.split(",")) if sep else (ENGINE,)
    if not rule or any(not n or n.endswith(".o") or "/" in n for n in names):
        raise SystemExit(f"--carrier {item!r}: expected RULE or RULE=obj,obj,... (object names without .o)")
    return rule, names


def guard_variants(args: list[str]) -> list[tuple[str, list[str]]]:
    """3.1 item 10, per carrier's probe_engine object: the preprocessing runs that must FAIL.

    A carrier of B (its compile command defines OXSDK_MERGE_KEY_UNDO): adding OXSDK_MAINLOOP_ENGINE, or
    removing OXSDK_FINDING_016_SELECTION_BARRIER.  A carrier WITHOUT B -- since 2026-10-20 ODS_VIEWER_V1,
    whose objects differ from BASE for its own define (SPEC-M4-ods-in-nextcloud addendum 3) -- gets the
    guard that means something for it: adding OXSDK_MERGE_KEY_UNDO must fail, i.e. B cannot be compiled
    into it.  Before, both B guards were applied to every carrier, so a carrier without B was red on the
    second one whatever its objects were.  Witness: findings/evidence/m4-ods/o3-pre-link/
    test-e2-c-static-red-viewer-not-declared.txt (the viewer's rule undeclared) and the run declaring it.
    A B carrier that lost its define now falls in the second branch and is red there: B compiles into it.
    """
    if "-DOXSDK_MERGE_KEY_UNDO" in args:
        return [("with OXSDK_MAINLOOP_ENGINE", args[:1] + ["-DOXSDK_MAINLOOP_ENGINE"] + args[1:]),
                ("without OXSDK_FINDING_016_SELECTION_BARRIER",
                 [x for x in args if x != "-DOXSDK_FINDING_016_SELECTION_BARRIER"])]
    return [("with OXSDK_MERGE_KEY_UNDO", args[:1] + ["-DOXSDK_MERGE_KEY_UNDO"] + args[1:])]


def object_name(row: dict) -> str:
    return row["object"].rsplit("/", 1)[-1].removesuffix(".o")


def judge_rows(rows: list[dict], carriers, rules: list[str], base: str) -> list[str]:
    """Per object: only a carrier's declared objects may differ from BASE, and each must.  Before the review of
    2026-10-08 (codex B7, opus S3) a carrier passed with ANY one differing object and any number of others;
    before 2026-10-14 the declared object was always probe_engine."""
    declared = carrier_map(carriers)
    failures = []
    for row in rows:
        expected = object_name(row) in declared.get(row["rule"], ())
        if not row["same"] and not expected:
            failures.append(f"{row['rule']} {row['object']}: preprocessed output differs from {base}")
    for carrier, names in declared.items():
        if carrier not in rules:
            continue
        mine = [r for r in rows if r["rule"] == carrier]
        if any(r["unbuildable"] for r in mine):
            failures.append(f"{carrier}: an object does not preprocess")
        for name in names:
            if not any(not r["same"] for r in mine if object_name(r) == name):
                tail = "B is not in it" if name == ENGINE else "declared to differ, did not move"
                failures.append(f"{carrier}: its {name} object does not differ from {base} ({tail})")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--carrier", action="append", default=None, metavar="RULE[=obj,...]",
                    help="a rule that must carry B (repeatable), with the objects that must differ from BASE "
                         "(names without .o; default probe_engine); default carriers E2_V15 and E2_V19")
    ap.add_argument("--inject", action="append", default=[])
    ap.add_argument("--json")
    a = ap.parse_args()
    carriers: dict[str, tuple[str, ...]] = {}
    for item in a.carrier or CARRIERS:
        rule, names = parse_carrier(item)
        if rule in carriers:
            raise SystemExit(f"--carrier {rule} named twice")
        carriers[rule] = names
    inject: dict[str, list[str]] = {}
    for item in a.inject:
        rule, flag = item.split("=", 1)
        inject.setdefault(rule, []).append(flag)

    rules = [m.group(1) for line in (HERE / "Makefile").read_text().splitlines()
             if (m := RULE.match(line))]
    failures = []
    for need in (*REQUIRED, *carriers):
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
                # (Not compared by message: an insertion above the failing
                # #include shifts the line number in it.)
                unbuildable = rb[0] != 0 and rc[0] != 0
                row = {"rule": rule, "object": obj, "baseExit": rb[0], "curExit": rc[0],
                       "unbuildable": unbuildable,
                       "same": unbuildable or (rb[0] == 0 and rc[0] == 0 and rb[1] == rc[1])}
                rows.append(row)
                if (rb[0] or rc[0]) and not unbuildable:
                    failures.append(f"{rule} {obj}: preprocessing failed on one side: {(rb[2] or rc[2]).strip()}")
        failures += judge_rows(rows, carriers, rules, a.base)

        # 3.1 item 10: the compile guard.
        guards = []
        engine = [j for j in jobs if j[0] in carriers and j[1].endswith("/probe_engine.o")]
        for rule, obj, args in engine:
            for name, variant in guard_variants(args):
                code = run(variant, cur)[0]
                guards.append({"rule": rule, "variant": name, "exit": code})
                if code == 0:
                    failures.append(f"{rule}: preprocessing {name} did not fail")
        for carrier in carriers:
            if carrier in rules and not any(j[0] == carrier for j in engine):
                failures.append(f"{carrier}: no probe_engine object")

    summary = {"carriers": list(carriers), "rules": len(rules), "objects": len(rows),
               "different": sum(1 for r in rows if not r["same"]),
               "unbuildable": sorted({f"{r['rule']} {r['object']}" for r in rows if r["unbuildable"]}),
               "guards": guards}
    if any(names != (ENGINE,) for names in carriers.values()):
        # Printed only when a carrier declares more than the default, so a default run's line is unchanged.
        summary = {"carriers": summary["carriers"], "declared": {r: list(n) for r, n in carriers.items()},
                   **{k: v for k, v in summary.items() if k != "carriers"}}
    if a.json:
        Path(a.json).write_text(json.dumps({"summary": summary, "rows": rows,
                                            "failures": failures}, indent=1) + "\n")
    print(json.dumps(summary))
    for f in failures:
        print("FAIL " + f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
