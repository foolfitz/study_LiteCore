#!/usr/bin/env python3
"""SPEC-M3-link-batch-v25 section 9/14: v25 preprocesses like v24's link except inside OXSDK_E2_V25_FORMAT_PROOF.

The owner carried the v24 counts over to v25 (section 14, 「沿用」) on the condition that v25's preprocessed output
differs from v24's only in the segments section 4.1 declares; section 14 owed a tool-closed reader for it.

WHY NOT READ `ships.stdout.txt` ALONE.  `what_the_link_ships.py` puts only the old `.cpp` in its scratch dir
(`source_at`), so the old side's `#include "ordered_format.inc"` resolves through `-Isrc` to the LIVE file: both
sides read the same new `.inc`/`.h`, and a change inside one is invisible.  Its v25 report
(`findings/evidence/link-batch-v25/pre-link/ships.stdout.txt`) has two probe_engine hunks, both in the .cpp; the
stage (ordered_format.inc) and witness (ordered_engine_reply.inc) changes are not in it.  This reader therefore
re-derives the difference itself, with every input resolved at its own commit, and reports the hunks the ships
report could not see.

For each of the four product sources, with the Makefile's own compile lines (`make -n -B`, joined; v0_preprocess.py's
method):

  A  CONFINED.  The v25 line, and the same line without -DOXSDK_E2_V25_FORMAT_PROOF, preprocessed (-E, line markers
     kept) on --src.  Every output line that differs, on either side, is mapped through the line markers to
     file:line and must lie in a conditional branch whose own condition, or an enclosing one's, names
     OXSDK_E2_V25_FORMAT_PROOF (`#if`/`#ifdef`/`#ifndef`/`#elif` text; a branch counts from the first condition in
     its group that names it).  A macro DERIVED inside such a branch and used outside it is a difference outside,
     and is red.
  B  SAME AS V24's LINK.  The v24 line (build/e2/editor-v24) preprocessed (-E -P; nonblank, right-stripped) on
     --src and on `git archive <--since> wasm_sdk_probe/src` (headers resolve beside each source) must be equal.
  C  SAME LINE.  The v24 line equals the v25 line without the V25 define, except the object path.

A and C give: v25 differs from (v25 minus V25) only inside V25 branches, and (v25 minus V25) is v24's line; B gives
that v24's line on --src is v24's link.  Non-vacuity: A must find at least one differing line over the four units,
and the ships report must list at least one changed hunk -- "zero found" is red, not green.

Red cases: --src (a scratch src/), --ships (a scratch report).  Exit 0 iff CONFINED_V25_HOLDS.
em++ -E only, pinned to one core (`taskset -c 0`); nothing is compiled to an object.
"""
from __future__ import annotations

import argparse
import difflib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
DEFINE = "-DOXSDK_E2_V25_FORMAT_PROOF"
MACRO = "OXSDK_E2_V25_FORMAT_PROOF"
SOURCES = ["sdk_api", "probe_engine", "unoembind_stub", "editor_api"]
DIRECTIVE = re.compile(r"^\s*#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)$")
MARKER = re.compile(r'^# (\d+) "([^"]*)"')


def compile_line(obj: str) -> list[str]:
    text = subprocess.run(["make", "-n", "-B", obj], cwd=PROJECT, capture_output=True, text=True, check=True).stdout
    lines = [l for l in text.replace("\\\n", " ").splitlines() if "em++" in l and " -c " in l and obj in l]
    if len(lines) != 1:
        raise SystemExit(f"expected one compile line for {obj}, found {len(lines)}")
    return shlex.split(lines[0])


def without_output(argv: list[str], src_dir: Path) -> list[str]:
    out, skip = [], False
    for token in argv:
        if skip:
            skip = False
            continue
        if token == "-c":
            continue
        if token == "-o":
            skip = True
            continue
        if token.startswith("src/") and token.endswith(".cpp"):
            token = str(src_dir / token[len("src/"):])
        out.append(token)
    return out


def run_e(argv: list[str], keep_markers: bool) -> tuple[str | None, str, float]:
    started = time.monotonic()
    run = subprocess.run(["taskset", "-c", "0", *argv, "-E", *([] if keep_markers else ["-P"])],
                         cwd=PROJECT, capture_output=True, text=True)
    return (None if run.returncode else run.stdout), run.stderr[-2000:], round(time.monotonic() - started, 2)


def located(text: str) -> list[tuple[str, int, str]]:
    """(file, line, text) for every nonblank, non-marker output line."""
    out, name, line = [], "", 0
    for raw in text.splitlines():
        marker = MARKER.match(raw)
        if marker:
            line, name = int(marker.group(1)), marker.group(2)
            continue
        if raw.startswith("#pragma") or raw.startswith("# "):
            line += 1
            continue
        if raw.strip():
            out.append((name, line, raw.rstrip()))
        line += 1
    return out


def v25_lines(path: Path) -> set[int]:
    """1-based line numbers of `path` that lie in a branch governed by MACRO (see the module docstring)."""
    inside, stack, physical = set(), [], path.read_text(errors="replace").split("\n")
    i = 0
    while i < len(physical):
        start, logical = i, physical[i]
        while logical.endswith("\\") and i + 1 < len(physical):
            i += 1
            logical = logical[:-1] + physical[i]
        directive = DIRECTIVE.match(logical)
        if directive:
            kind, rest = directive.group(1), directive.group(2)
            names = re.search(rf"\b{MACRO}\b", rest) is not None
            if kind in ("if", "ifdef", "ifndef"):
                stack.append(names)
            elif kind == "elif" and stack:
                stack[-1] = stack[-1] or names
            elif kind == "endif" and stack:
                stack.pop()
        if any(stack):
            inside.update(range(start + 1, i + 2))
        i += 1
    return inside


def confined(unit: str, with_v25: str, without_v25: str, src_dir: Path) -> dict:
    a, b = located(without_v25), located(with_v25)
    ta, tb = [x[2] for x in a], [x[2] for x in b]
    lo = 0
    while lo < min(len(ta), len(tb)) and ta[lo] == tb[lo]:
        lo += 1
    hi = 0
    while hi < min(len(ta), len(tb)) - lo and ta[-1 - hi] == tb[-1 - hi]:
        hi += 1
    changed = []
    matcher = difflib.SequenceMatcher(None, ta[lo:len(ta) - hi], tb[lo:len(tb) - hi], autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            continue
        changed += [("-",) + a[lo + k] for k in range(i1, i2)] + [("+",) + b[lo + k] for k in range(j1, j2)]
    cache: dict[str, set[int] | None] = {}
    rows = []
    for sign, name, line, text in changed:
        path = (PROJECT / name) if not Path(name).is_absolute() else Path(name)
        try:
            path.resolve().relative_to(src_dir.resolve())
            in_src = True
        except ValueError:
            in_src = False
        if name not in cache:
            cache[name] = v25_lines(path) if in_src and path.is_file() else None
        ok = cache[name] is not None and line in cache[name]
        rows.append({"side": sign, "file": str(path.resolve().relative_to(src_dir.resolve())) if in_src else name,
                     "line": line, "insideV25": ok, "text": text[:160]})
    return {"changedLines": len(rows), "outside": [r for r in rows if not r["insideV25"]], "lines": rows}


def normalized(text: str) -> list[str]:
    return [l.rstrip() for l in text.splitlines() if l.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", default="1f95a9fca", help="v24's link source (spec v25 13 item 2)")
    parser.add_argument("--src", type=Path, default=PROJECT / "src", help="the source tree to judge (red cases: a copy)")
    parser.add_argument("--ships", type=Path,
                        default=REPO / "findings/evidence/link-batch-v25/pre-link/ships.stdout.txt")
    args = parser.parse_args()
    src = args.src.resolve()
    problems: list[str] = []
    ships = json.loads(args.ships.read_text(encoding="utf-8"))
    ships_hunks = {u: sum(1 for h in hs if h.startswith("@@")) for u, hs in (ships.get("changed") or {}).items()}
    if not ships_hunks or not sum(ships_hunks.values()):
        problems.append("the ships report lists zero changed hunks")
    since = subprocess.run(["git", "rev-parse", args.since], cwd=REPO, capture_output=True, text=True,
                           check=True).stdout.strip()
    report: dict = {"tool": "check_v25_ships_confined", "argv": sys.argv, "since": since, "src": str(src),
                    "ships": {"path": str(args.ships), "hunks": ships_hunks}, "units": {}}
    with tempfile.TemporaryDirectory(prefix="v25-confined-") as scratch:
        tar = subprocess.run(["git", "archive", since, "wasm_sdk_probe/src"], cwd=REPO, capture_output=True,
                             check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as archive:
            archive.extractall(scratch, filter="data")
        base = Path(scratch) / "wasm_sdk_probe/src"
        for unit in SOURCES:
            v25 = compile_line(f"build/e2/editor-v25/{unit}.o")
            v24 = compile_line(f"build/e2/editor-v24/{unit}.o")
            row: dict = {}
            if v25.count(DEFINE) != 1:
                problems.append(f"{unit}: the v25 line carries {DEFINE} {v25.count(DEFINE)} times, not once")
            minus = [t for t in v25 if t != DEFINE]
            strip = lambda argv: [t for t in without_output(argv, src) if not t.startswith("build/")]  # noqa: E731
            row["C-sameLine"] = strip(v24) == strip(minus)
            if not row["C-sameLine"]:
                problems.append(f"{unit}: v24's line is not v25's without {DEFINE}: "
                                f"{sorted(set(strip(v24)) ^ set(strip(minus)))}")
            with_v25, e1, s1 = run_e(without_output(v25, src), True)
            without_v25, e2, s2 = run_e(without_output(minus, src), True)
            live24, e3, s3 = run_e(without_output(v24, src), False)
            link24, e4, s4 = run_e(without_output(v24, base), False)
            row["seconds"] = [s1, s2, s3, s4]
            errors = [e for out, e in ((with_v25, e1), (without_v25, e2), (live24, e3), (link24, e4)) if out is None]
            if errors:
                problems.append(f"{unit}: preprocessing failed: {errors[0][-300:]}")
                report["units"][unit] = row
                continue
            row["B-sameAsLink"] = normalized(live24) == normalized(link24)
            if not row["B-sameAsLink"]:
                problems.append(f"{unit}: v24's line on --src differs from {args.since}")
            result = confined(unit, with_v25, without_v25, src)
            row.update({"A-changedLines": result["changedLines"], "A-outside": result["outside"][:20],
                        "A-outsideCount": len(result["outside"]),
                        "A-byFile": {f: sum(1 for r in result["lines"] if r["file"] == f)
                                     for f in sorted({r["file"] for r in result["lines"]})},
                        "A-lines": result["lines"]})
            if result["outside"]:
                first = result["outside"][0]
                problems.append(f"{unit}: {len(result['outside'])} differing line(s) outside {MACRO}, first "
                                f"{first['file']}:{first['line']} ({first['side']}) {first['text'][:80]!r}")
            report["units"][unit] = row
    total = sum(u.get("A-changedLines", 0) for u in report["units"].values())
    if not total:
        problems.append("A found zero differing lines: nothing was judged")
    unseen = sorted({r["file"] for u in report["units"].values() for r in u.get("A-lines", [])
                     if not r["file"].endswith(".cpp")})
    report["notVisibleToShips"] = {"files": unseen, "lines": sum(1 for u in report["units"].values()
                                                                  for r in u.get("A-lines", [])
                                                                  if not r["file"].endswith(".cpp"))}
    report["problems"] = problems
    report["verdict"] = "CONFINED_V25_HOLDS" if not problems else "CONFINED_V25_RED"
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
