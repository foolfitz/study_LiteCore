#!/usr/bin/env python3
"""What would a product relink actually ship, measured instead of read.

A link mints a new identity and unbinds every verdict that named the old one, so
"what changed" is the question the decision turns on -- and the two cheap ways to
answer it are both wrong:

  * READING COMMIT MESSAGES answers about the repository, not about the build.
    Since `e2-editor-v4` was linked, `src/probe_engine.cpp` gained 153 lines
    across five commits, four of them accessibility work for a different core.
  * READING THE #ifdefs is closer and still missed a hunk on 2026-08-24. The
    `refreshCaretParagraph()` honesty fix is gated on a RUNTIME flag, on purpose
    ("this also covers the runtime cases"), so it is not behind any
    `OXSDK_A11Y_*` and it does reach the product build.

The preprocessor knows. This compiles nothing and links nothing: it runs `-E` on
the product's own translation units, with the product's own defines, at a base
commit and at the working tree, and diffs the two. What comes out is exactly
what the link would compile differently.

Deliberately NOT an object-file comparison. Finding 032: comparing object files
is a coin flip, not an isolation check.

Usage:
  what_the_link_ships.py --since <commit> [--profile v4] [--json]

`--since` is the commit the SHIPPED artifact was linked from. There is no
default: guessing it would produce a confident answer about the wrong baseline,
and the runbook that calls this names it.

THE ARTIFACT IS NOT ONLY C++. The profile builder hashes whichever
`sdk/sdk-worker.js` is in the tree, so a link ships every accumulated worker
change as well. This tool answered as if the engine were the whole story until a
dry packaging run showed `workerSha256` moving under it -- which is the same
failure it exists to prevent, one level in. It now compares the tree's worker
against the one the shipped profile carries.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent

# The product profile's own compile line, kept as data rather than re-derived.
# `make -pn` is the source of truth and the check below asserts these still
# match it, so a Makefile edit cannot silently leave this tool measuring a
# configuration nobody builds.
PRODUCT_DEFINES = [
    "-DOXSDK_EDITOR_DISCOVERY",
    "-DOXSDK_FINDING_016_SELECTION_BARRIER",
    "-DOXSDK_E2_FORMAT_BARRIER",
]
# The four translation units the product artifact is linked from.  a11y_tree_probe
# is NOT among them -- it has a rule under the v4 build directory but is not in
# E2_V4_OBJECTS, which is the sort of thing only an expansion tells you.
PRODUCT_UNITS = ["sdk_api", "probe_engine", "unoembind_stub", "editor_api"]


def make_var(name: str) -> str:
    out = subprocess.run(["make", "-pn"], cwd=PROJECT, capture_output=True,
                         text=True).stdout
    for line in out.splitlines():
        if line.startswith(f"{name} :=") or line.startswith(f"{name} ="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"cannot resolve {name} from the Makefile")


def source_at(commit: str, unit: str, into: Path) -> bool:
    """One translation unit as of `commit`, or False if it did not exist."""
    result = subprocess.run(
        ["git", "show", f"{commit}:wasm_sdk_probe/src/{unit}.cpp"],
        cwd=REPO, capture_output=True)
    if result.returncode != 0:
        return False
    (into / f"{unit}.cpp").write_bytes(result.stdout)
    return True


def preprocess(cxx: str, flags: list[str], src: Path, out: Path) -> str | None:
    result = subprocess.run([cxx, *flags, "-E", "-P", str(src), "-o", str(out)],
                            capture_output=True, text=True)
    return None if result.returncode == 0 else (result.stderr or "")[-400:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True,
                    help="the commit the SHIPPED artifact was linked from")
    ap.add_argument("--shipped-profile", default="dist/profiles/e2-editor-v8",
                    help="the profile directory the product currently ships, "
                         "whose packaged worker is compared against the tree's")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cxx = make_var("CXX")
    flags = (make_var("E1_CPPFLAGS").split() + make_var("R5_CXXFLAGS").split()
             + PRODUCT_DEFINES + ["-Isrc"])

    # THE PRODUCT'S OWN LISTS, asserted rather than assumed.  If the Makefile
    # stops building these four units, or starts defining a fourth symbol, this
    # tool would go on measuring the old configuration and answer confidently
    # about a build nobody links.
    objects = make_var("E2_V4_OBJECTS").split()
    units_in_make = sorted(Path(o).stem for o in objects)
    drift = []
    if units_in_make != sorted(PRODUCT_UNITS):
        drift.append(f"E2_V4_OBJECTS is {units_in_make}, this tool has "
                     f"{sorted(PRODUCT_UNITS)}")
    recipe = subprocess.run(["make", "-pn"], cwd=PROJECT, capture_output=True,
                            text=True).stdout
    for define in PRODUCT_DEFINES:
        if define not in recipe:
            drift.append(f"{define} no longer appears in any recipe")

    report: dict = {
        "schemaVersion": 1,
        "release": "what-the-link-ships",
        "since": args.since,
        "units": PRODUCT_UNITS,
        "defines": PRODUCT_DEFINES,
        "configurationDrift": drift,
        "changed": {},
        "identical": [],
        "errors": {},
    }

    scratch = Path(tempfile.mkdtemp(prefix="link-ships-"))
    try:
        old, new = scratch / "old", scratch / "new"
        old.mkdir(); new.mkdir()
        for unit in PRODUCT_UNITS:
            if not source_at(args.since, unit, old):
                report["errors"][unit] = f"absent at {args.since}"
                continue
            shutil.copyfile(PROJECT / "src" / f"{unit}.cpp", new / f"{unit}.cpp")
            for where in (old, new):
                failure = preprocess(cxx, flags, where / f"{unit}.cpp",
                                     where / f"{unit}.i")
                if failure:
                    report["errors"][unit] = failure
                    break
            else:
                # Split on `;` so the diff is statement-shaped: the preprocessor
                # emits enormous single lines and a line diff of those is
                # unreadable, which is the same as not having one.
                a = (old / f"{unit}.i").read_text(errors="replace").split(";")
                b = (new / f"{unit}.i").read_text(errors="replace").split(";")
                if a == b:
                    report["identical"].append(unit)
                    continue
                import difflib
                hunks = [line for line in difflib.unified_diff(
                    a, b, fromfile=f"{unit}@{args.since}", tofile=f"{unit}@tree",
                    n=1, lineterm="") if line.startswith(("+", "-", "@@"))]
                report["changed"][unit] = hunks
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    # THE ARTIFACT IS NOT ONLY C++, and this tool answered as if it were until
    # 2026-08-24, when a dry packaging run showed the workerSha256 moving.
    #
    # `build_e2_editor_v4_profile.py` hashes WHICHEVER WORKER IS IN THE TREE.
    # The v4 runbook already knew -- finding 068's worker half "rides this link
    # for free" -- so a link ships every accumulated worker change too, and a
    # C++-only answer to "what does this link ship" is a confident answer to
    # half the question. That is this file's own failure mode, one level in.
    shipped = PROJECT / args.shipped_profile
    tree_worker = PROJECT / "sdk" / "sdk-worker.js"
    packed_worker = shipped / "sdk-worker.js"
    worker: dict = {"shippedProfile": args.shipped_profile}
    if not packed_worker.is_file():
        worker["error"] = f"{packed_worker} does not exist"
        report["errors"]["sdk-worker.js"] = worker["error"]
    else:
        import hashlib
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: E731
        worker["shipped"] = digest(packed_worker)[:16]
        worker["tree"] = digest(tree_worker)[:16]
        worker["identical"] = worker["shipped"] == worker["tree"]
        if not worker["identical"]:
            import difflib
            a_lines = packed_worker.read_text(errors="replace").splitlines()
            b_lines = tree_worker.read_text(errors="replace").splitlines()
            added = [l[1:].strip() for l in difflib.unified_diff(
                a_lines, b_lines, n=0, lineterm="")
                if l.startswith("+") and not l.startswith("+++")]
            removed = [l[1:].strip() for l in difflib.unified_diff(
                a_lines, b_lines, n=0, lineterm="")
                if l.startswith("-") and not l.startswith("---")]
            worker["addedLines"] = len(added)
            worker["removedLines"] = len(removed)
            # Code, not comments: a hundred lines of rationale and four lines of
            # forwarding are very different things to put into an artifact, and
            # a line count alone cannot tell them apart.
            code = lambda ls: [l for l in ls if l and not l.startswith(("//", "*", "/*"))]  # noqa: E731
            worker["addedCodeLines"] = code(added)
            worker["removedCodeLines"] = code(removed)
    report["worker"] = worker

    report["ok"] = not report["errors"] and not report["configurationDrift"]
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if drift:
            print("CONFIGURATION DRIFT -- this tool is measuring a build the "
                  "Makefile no longer describes:", file=sys.stderr)
            for item in drift:
                print(f"  {item}", file=sys.stderr)
        print(f"since {args.since}: "
              f"{len(report['identical'])} unit(s) preprocess identically, "
              f"{len(report['changed'])} changed")
        for unit in report["identical"]:
            print(f"  same     {unit}")
        for unit, hunks in report["changed"].items():
            print(f"  CHANGED  {unit}")
            for line in hunks:
                text = line.strip()
                if text and not text.startswith("@@"):
                    print(f"      {text[:150]}")
        for unit, why in report["errors"].items():
            print(f"  ERROR    {unit}: {why}")
        w = report.get("worker") or {}
        if w.get("identical"):
            print(f"  same     sdk-worker.js ({w['tree']})")
        elif "tree" in w:
            print(f"  CHANGED  sdk-worker.js {w['shipped']} -> {w['tree']} "
                  f"(+{w['addedLines']}/-{w['removedLines']} lines, "
                  f"{len(w['addedCodeLines'])} of them code)")
            for line in w["addedCodeLines"]:
                print(f"      + {line[:140]}")
            for line in w["removedCodeLines"]:
                print(f"      - {line[:140]}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
