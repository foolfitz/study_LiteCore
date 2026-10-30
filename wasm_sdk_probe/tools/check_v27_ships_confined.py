#!/usr/bin/env python3
"""SPEC-M3-v27-finding-176 5 (L): v27 preprocesses like v25's link except inside OXSDK_E2_V27_FIRST_BLOCK, and its
source change is exactly the closed list of section 4.1 item 6.

Derived from tools/check_v25_ships_confined.py (v25's evidence binds it; not edited).  The differences are a closed
list: the names (V25 -> V27, v24 -> v25, the default --since 9d7fb9e7c = v25's link source, the default --ships = this
batch's report, the scratch prefix), and check D below, which v25's reader did not have.

WHY NOT READ `ships.stdout.txt` ALONE.  `what_the_link_ships.py` puts only the old `.cpp` in its scratch dir
(`source_at`), so the old side's `#include "ordered_format.inc"` resolves through `-Isrc` to the LIVE file: both
sides read the same new `.inc`/`.h`, and a change inside one is invisible (v25 section 15).  v27's report
(`findings/evidence/v27-176/pre-link/ships.stdout.txt`) has two probe_engine hunks, both in the .cpp; the four
ordered_format.inc hunks are not in it.  This reader re-derives the difference with every input at its own commit.

For each of the four product sources, with the Makefile's own compile lines (`make -n -B`, joined):

  A  CONFINED.  The v27 line, and the same line without -DOXSDK_E2_V27_FIRST_BLOCK, preprocessed (-E, line markers
     kept) on --src.  Every output line that differs, on either side, is mapped through the line markers to
     file:line and must lie in a conditional branch whose own condition, or an enclosing one's, names
     OXSDK_E2_V27_FIRST_BLOCK.
  B  SAME AS V25's LINK.  The v25 line (build/e2/editor-v25) preprocessed (-E -P; nonblank, right-stripped) on
     --src and on `git archive <--since> wasm_sdk_probe/src` must be equal.
  C  SAME LINE.  The v25 line equals the v27 line without the V27 define, except the object path.

And once over the whole of src/ (new here):

  D  THE CLOSED LIST, TEXTUALLY.  Every conditional group in --src whose opening condition names the macro is found
     (with a /* ... */ comment block that immediately precedes it and names the macro, as editor_api.h's guard has).
     (i) Each group matches exactly one entry of DECLARED (by an anchor in its v27 branch) and each entry exactly
     one group: section 4.1 item 6's seven hunks, no more, no fewer.  (ii) No group sits inside a branch that names
     OXSDK_E2_V25_FORMAT_PROOF (4.1 item 6: strip_v25's non-greedy pattern would fail).  (iii) Strip every group --
     keep its #else branch if it has one, drop it whole otherwise -- and every file of --src equals <--since>'s,
     byte for byte, with the same set of files: outside the declared groups nothing changed, comments included.

A and C give: v27 differs from (v27 minus V27) only inside V27 branches, and (v27 minus V27) is v25's line; B gives
that v25's line on --src is v25's link; D gives that the text outside the groups is v25's link source and that the
groups are exactly the declared ones.  Non-vacuity: A must find at least one differing line over the four units,
and the ships report must list at least one changed hunk -- "zero found" is red, not green.

Red cases: --src (a scratch src/), --ships (a scratch report).  Exit 0 iff CONFINED_V27_HOLDS.
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
DEFINE = "-DOXSDK_E2_V27_FIRST_BLOCK"
MACRO = "OXSDK_E2_V27_FIRST_BLOCK"
V25_MACRO = "OXSDK_E2_V25_FORMAT_PROOF"
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


def v27_lines(path: Path) -> set[int]:
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


def confined(unit: str, with_v27: str, without_v27: str, src_dir: Path) -> dict:
    a, b = located(without_v27), located(with_v27)
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
            cache[name] = v27_lines(path) if in_src and path.is_file() else None
        ok = cache[name] is not None and line in cache[name]
        rows.append({"side": sign, "file": str(path.resolve().relative_to(src_dir.resolve())) if in_src else name,
                     "line": line, "insideV27": ok, "text": text[:160]})
    return {"changedLines": len(rows), "outside": [r for r in rows if not r["insideV27"]], "lines": rows}


def normalized(text: str) -> list[str]:
    return [l.rstrip() for l in text.splitlines() if l.strip()]


SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".h", ".hpp", ".inc"}
# D: section 4.1 item 6, the closed list.  (file, name, anchor in the group's v27 branch)
DECLARED = [
    ("editor_api.h", "guard", '#error "the v27 first-block read requires the v25 format-proof engine"'),
    ("probe_engine.cpp", "undo-fields", "bool undoAttempted = false;"),
    ("probe_engine.cpp", "undo-serialised", r'json << ",\"undo\":{\"read\":"'),
    ("ordered_format.inc", "undo-read-before-post", "const bool undoBeforeRead = readMergeUndoPayload(undoBefore);"),
    ("ordered_format.inc", "collapsed-no-restore-before-select", "if (barrier.route != FormatBarrierRoute::Collapsed)"),
    ("ordered_format.inc", "multi-block-refused-off-collapsed", "if (readback.multiBlock &&"),
    ("ordered_format.inc", "undo-read-after-restore", "const bool undoAfterRead = readMergeUndoPayload(undoAfter);"),
]


def v27_groups(text: str) -> tuple[list[dict], list[str]]:
    """Every conditional group whose OPENING condition names MACRO: 0-based line spans (a preceding /* */ block that
    names MACRO included), its v27 branch text, its #else branch (or None), and the conditions enclosing it."""
    lines, groups, problems, stack = text.split("\n"), [], [], []
    for i, raw in enumerate(lines):
        directive = DIRECTIVE.match(raw)
        if not directive:
            continue
        kind, rest = directive.group(1), directive.group(2)
        if kind in ("if", "ifdef", "ifndef"):
            names = re.search(rf"\b{MACRO}\b", rest) is not None
            stack.append({"open": i, "names": names, "else": None, "cond": rest.strip(),
                          "enclosing": [g["cond"] for g in stack]})
        elif kind == "elif" and stack and (stack[-1]["names"] or re.search(rf"\b{MACRO}\b", rest)):
            problems.append(f"line {i + 1}: #elif in a group naming {MACRO} is not a supported shape")
        elif kind == "else" and stack:
            stack[-1]["else"] = i
        elif kind == "endif" and stack:
            g = stack.pop()
            if not g["names"]:
                continue
            first = g["open"]
            if first > 0 and lines[first - 1].strip() == "*/":
                j = first - 1
                while j >= 0 and not lines[j].lstrip().startswith("/*"):
                    j -= 1
                if j >= 0 and MACRO in "\n".join(lines[j:first]):
                    first = j
            body_end = g["else"] if g["else"] is not None else i
            groups.append({"start": first, "end": i, "cond": g["cond"], "enclosing": g["enclosing"],
                           "v27": "\n".join(lines[g["open"] + 1:body_end]),
                           "elseLines": None if g["else"] is None else lines[g["else"] + 1:i]})
    if stack:
        problems.append("unterminated conditional group")
    return groups, problems


def strip_v27(text: str, groups: list[dict]) -> str:
    lines, out, i = text.split("\n"), [], 0
    for g in sorted(groups, key=lambda g: g["start"]):
        out += lines[i:g["start"]] + (g["elseLines"] or [])
        i = g["end"] + 1
    return "\n".join(out + lines[i:])


def closed_list(src: Path, base: Path) -> dict:
    problems, found = [], []
    # Source files only: the live src/ also holds untracked object files (ignored, listed in the report).
    names = sorted(p.name for p in src.iterdir() if p.is_file() and p.suffix in SOURCE_SUFFIXES)
    base_names = sorted(p.name for p in base.iterdir() if p.is_file() and p.suffix in SOURCE_SUFFIXES)
    ignored = sorted(p.name for p in src.iterdir() if p.is_file() and p.suffix not in SOURCE_SUFFIXES)
    if names != base_names:
        problems.append(f"the files of --src differ from the base: {sorted(set(names) ^ set(base_names))}")
    differing = []
    for name in names:
        text = (src / name).read_text(errors="replace")
        groups, shape = v27_groups(text)
        problems += [f"{name}: {p}" for p in shape]
        for g in groups:
            hits = [d[1] for d in DECLARED if d[0] == name and d[2] in g["v27"]]
            found.append({"file": name, "lines": [g["start"] + 1, g["end"] + 1], "condition": g["cond"],
                          "hasElse": g["elseLines"] is not None, "declared": hits,
                          "enclosingNamesV25": any(V25_MACRO in c for c in g["enclosing"])})
        if (base / name).is_file() and strip_v27(text, groups) != (base / name).read_text(errors="replace"):
            differing.append(name)
    for name in differing:
        problems.append(f"{name}: with every {MACRO} group stripped it is not the base file byte for byte")
    for g in found:
        if len(g["declared"]) != 1:
            problems.append(f"{g['file']}:{g['lines'][0]}: a {MACRO} group matching {len(g['declared'])} declared "
                            f"hunks ({g['declared']}), not exactly one")
        if g["enclosingNamesV25"]:
            problems.append(f"{g['file']}:{g['lines'][0]}: a {MACRO} group nested in a {V25_MACRO} branch")
    for file, name, _ in DECLARED:
        count = sum(1 for g in found if g["file"] == file and name in g["declared"])
        if count != 1:
            problems.append(f"declared hunk {file}/{name} found in {count} groups, not exactly one")
    return {"groups": found, "declared": len(DECLARED), "strippedDiffer": differing, "files": len(names),
            "ignoredNonSource": ignored, "problems": problems}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", default="9d7fb9e7c", help="v25's link source (spec v27 5)")
    parser.add_argument("--src", type=Path, default=PROJECT / "src", help="the source tree to judge (red cases: a copy)")
    parser.add_argument("--ships", type=Path,
                        default=REPO / "findings/evidence/v27-176/pre-link/ships.stdout.txt")
    args = parser.parse_args()
    src = args.src.resolve()
    problems: list[str] = []
    ships = json.loads(args.ships.read_text(encoding="utf-8"))
    ships_hunks = {u: sum(1 for h in hs if h.startswith("@@")) for u, hs in (ships.get("changed") or {}).items()}
    if not ships_hunks or not sum(ships_hunks.values()):
        problems.append("the ships report lists zero changed hunks")
    since = subprocess.run(["git", "rev-parse", args.since], cwd=REPO, capture_output=True, text=True,
                           check=True).stdout.strip()
    report: dict = {"tool": "check_v27_ships_confined", "argv": sys.argv, "since": since, "src": str(src),
                    "ships": {"path": str(args.ships), "hunks": ships_hunks}, "units": {}}
    with tempfile.TemporaryDirectory(prefix="v27-confined-") as scratch:
        tar = subprocess.run(["git", "archive", since, "wasm_sdk_probe/src"], cwd=REPO, capture_output=True,
                             check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as archive:
            archive.extractall(scratch, filter="data")
        base = Path(scratch) / "wasm_sdk_probe/src"
        for unit in SOURCES:
            v27 = compile_line(f"build/e2/editor-v27/{unit}.o")
            v25 = compile_line(f"build/e2/editor-v25/{unit}.o")
            row: dict = {}
            if v27.count(DEFINE) != 1:
                problems.append(f"{unit}: the v27 line carries {DEFINE} {v27.count(DEFINE)} times, not once")
            minus = [t for t in v27 if t != DEFINE]
            strip = lambda argv: [t for t in without_output(argv, src) if not t.startswith("build/")]  # noqa: E731
            row["C-sameLine"] = strip(v25) == strip(minus)
            if not row["C-sameLine"]:
                problems.append(f"{unit}: v25's line is not v27's without {DEFINE}: "
                                f"{sorted(set(strip(v25)) ^ set(strip(minus)))}")
            with_v27, e1, s1 = run_e(without_output(v27, src), True)
            without_v27, e2, s2 = run_e(without_output(minus, src), True)
            live25, e3, s3 = run_e(without_output(v25, src), False)
            link25, e4, s4 = run_e(without_output(v25, base), False)
            row["seconds"] = [s1, s2, s3, s4]
            errors = [e for out, e in ((with_v27, e1), (without_v27, e2), (live25, e3), (link25, e4)) if out is None]
            if errors:
                problems.append(f"{unit}: preprocessing failed: {errors[0][-300:]}")
                report["units"][unit] = row
                continue
            row["B-sameAsLink"] = normalized(live25) == normalized(link25)
            if not row["B-sameAsLink"]:
                problems.append(f"{unit}: v25's line on --src differs from {args.since}")
            result = confined(unit, with_v27, without_v27, src)
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
        report["D-closedList"] = closed_list(src, base)
        problems += ["D: " + p for p in report["D-closedList"]["problems"]]
    total = sum(u.get("A-changedLines", 0) for u in report["units"].values())
    if not total:
        problems.append("A found zero differing lines: nothing was judged")
    unseen = sorted({r["file"] for u in report["units"].values() for r in u.get("A-lines", [])
                     if not r["file"].endswith(".cpp")})
    report["notVisibleToShips"] = {"files": unseen, "lines": sum(1 for u in report["units"].values()
                                                                  for r in u.get("A-lines", [])
                                                                  if not r["file"].endswith(".cpp"))}
    report["problems"] = problems
    report["verdict"] = "CONFINED_V27_HOLDS" if not problems else "CONFINED_V27_RED"
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
