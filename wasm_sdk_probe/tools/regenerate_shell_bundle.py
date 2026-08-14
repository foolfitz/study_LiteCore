#!/usr/bin/env python3
"""Recompute the E1-C shell bundle manifest, and say what would change.

Why this exists (task #43).  The shell bundle hash is pinned in three places:

    e1/editor-shell-bundle-v1.json   per-file hashes and the aggregate
    e1/validation-matrix-v2.json     baseline.shellBundleSha256
    tests/test_e1_c.py               a literal, so the manifest cannot drift
                                     without a test saying so

A legitimate shell change therefore needs three hand edits, all of which have
to agree.  When that is annoying enough, the cheap way out is to loosen the
check -- which is exactly the coverage that let task #33 ship a contradiction
with every automated gate green.  So this tool exists to make the honest path
the easy one, and it is deliberately built so that the dishonest path does not
get easier at the same time:

  * it ALWAYS prints the diff, including under --write;
  * a byte change inside an already-included module is one flag (--write);
  * a change to the SET of modules is not -- that needs --allow-set-change,
    and every newly excluded file needs a reason spelled out on the command
    line, because "this file is not covered" is a claim someone has to make;
  * it REFUSES to write when source and dist disagree, so a manifest can never
    be frozen against files the server is not actually serving (serve.py
    serves dist/, and forgetting `make ... -assets` is a standing trap).

Check mode (the default) exits 1 when something differs, so it can be run as a
question rather than as an action.  The enforcing gate is still
tests/test_e1_c.py -- this tool tells you what to write, it does not replace
the test that notices you did not.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_e1_c import (  # noqa: E402
    SHELL_BUNDLE_MANIFEST, loaded_shell_modules, sha256, shell_bundle_digest,
)

PROJECT = Path(__file__).resolve().parent.parent
MATRIX = Path("e1/validation-matrix-v2.json")
TEST_FILE = Path("tests/test_e1_c.py")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compute(project: Path) -> dict[str, Any]:
    """What the manifest WOULD say if regenerated from the tree right now."""
    manifest_path = project / SHELL_BUNDLE_MANIFEST
    manifest = read_json(manifest_path)
    loaded = loaded_shell_modules(project)
    available = sorted(
        path.relative_to(project).as_posix()
        for directory in (project / "editor-shell", project / "input")
        for path in directory.glob("*.js")
    )
    source = {p: sha256(project / p) for p in loaded}
    # dist is checked for every AVAILABLE module, not just the loaded ones:
    # a stale dist copy of an excluded file is still a stale server.
    dist = {
        p: (sha256(project / "dist" / p) if (project / "dist" / p).is_file() else None)
        for p in available
    }
    return {
        "manifestPath": manifest_path,
        "manifest": manifest,
        "loaded": loaded,
        "available": available,
        "sourceHashes": source,
        "distHashes": dist,
        "bundleSha256": shell_bundle_digest(source),
        "excludedNow": sorted(set(available) - set(loaded)),
    }


def plan(project: Path) -> dict[str, Any]:
    state = compute(project)
    manifest = state["manifest"]
    included_before = {
        str(item["path"]): item["sha256"] for item in manifest.get("included") or []
    }
    excluded_before = {
        str(item["path"]): item.get("reason", "")
        for item in manifest.get("excluded") or []
    }

    added = [p for p in state["loaded"] if p not in included_before]
    removed = [p for p in included_before if p not in state["loaded"]]
    changed = [
        {"path": p, "was": included_before[p], "now": state["sourceHashes"][p]}
        for p in state["loaded"]
        if p in included_before and included_before[p] != state["sourceHashes"][p]
    ]
    newly_excluded = [p for p in state["excludedNow"] if p not in excluded_before]
    unexcluded = [p for p in excluded_before if p not in state["excludedNow"]]

    # Source vs dist.  Only a mismatch matters; a file absent from dist is a
    # mismatch too, and a loud one -- it means the page cannot even load it.
    stale_dist = [
        {"path": p, "source": state["sourceHashes"].get(p) or sha256(project / p),
         "dist": state["distHashes"].get(p)}
        for p in state["available"]
        if state["distHashes"].get(p) != (
            state["sourceHashes"].get(p) or sha256(project / p))
    ]

    matrix = read_json(project / MATRIX)
    matrix_hash = matrix.get("baseline", {}).get("shellBundleSha256")
    test_text = (project / TEST_FILE).read_text(encoding="utf-8")
    old_bundle = manifest.get("bundleSha256")
    test_occurrences = test_text.count(str(old_bundle))

    set_changed = bool(added or removed or newly_excluded or unexcluded)
    return {
        **state,
        "includedBefore": included_before,
        "excludedBefore": excluded_before,
        "added": added,
        "removed": removed,
        "changed": changed,
        "newlyExcluded": newly_excluded,
        "unexcluded": unexcluded,
        "staleDist": stale_dist,
        "oldBundleSha256": old_bundle,
        "matrixSha256": matrix_hash,
        "matrixAgrees": matrix_hash == old_bundle,
        "testOccurrences": test_occurrences,
        "setChanged": set_changed,
        "bundleChanged": state["bundleSha256"] != old_bundle,
        "clean": (
            not set_changed
            and not changed
            and state["bundleSha256"] == old_bundle
            and matrix_hash == old_bundle
            and test_occurrences == 1
            and not stale_dist
        ),
    }


def render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"manifest : {report['manifestPath']}")
    lines.append(f"bundle   : {report['oldBundleSha256']}  (pinned)")
    lines.append(f"           {report['bundleSha256']}  (computed)")
    lines.append("")

    if report["clean"]:
        lines.append("no change: the tree, the manifest, the matrix and the test agree.")
        return "\n".join(lines)

    for path in report["added"]:
        lines.append(f"  + included   {path}   {report['sourceHashes'][path]}")
    for path in report["removed"]:
        lines.append(f"  - included   {path}   (no longer imported)")
    for item in report["changed"]:
        lines.append(f"  ~ changed    {item['path']}")
        lines.append(f"                 was {item['was']}")
        lines.append(f"                 now {item['now']}")
    for path in report["newlyExcluded"]:
        lines.append(f"  + excluded   {path}   NEEDS --exclude-reason")
    for path in report["unexcluded"]:
        lines.append(f"  - excluded   {path}   (now imported, or deleted)")
    for item in report["staleDist"]:
        lines.append(f"  ! dist stale {item['path']}")
        lines.append(f"                 source {item['source']}")
        lines.append(f"                 dist   {item['dist']}")
    if not report["matrixAgrees"]:
        lines.append(f"  ! matrix     {MATRIX} pins {report['matrixSha256']}, "
                     f"manifest says {report['oldBundleSha256']}")
    if report["testOccurrences"] != 1:
        lines.append(f"  ! test       {TEST_FILE} mentions the pinned hash "
                     f"{report['testOccurrences']} times, expected exactly 1")
    return "\n".join(lines)


def blockers(report: dict[str, Any], allow_set_change: bool,
             reasons: dict[str, str]) -> list[str]:
    out: list[str] = []
    if report["staleDist"]:
        out.append(
            "source and dist disagree -- run the asset target first. Freezing a "
            "manifest against files the server does not serve would pin a state "
            "no browser has ever loaded.")
    if report["setChanged"] and not allow_set_change:
        out.append(
            "the SET of shell modules changed, not just their bytes. That is a "
            "coverage decision, so it needs --allow-set-change.")
    missing = [p for p in report["newlyExcluded"] if p not in reasons]
    if missing:
        out.append(
            "newly excluded with no reason given: " + ", ".join(missing)
            + ". Every exclusion is a claim that browser evidence does not cover "
              "that file; write it down with --exclude-reason path=reason.")
    if report["testOccurrences"] != 1:
        out.append(
            f"{TEST_FILE} mentions the pinned hash {report['testOccurrences']} "
            "times; expected exactly 1, so the rewrite target is ambiguous.")
    return out


def apply(project: Path, report: dict[str, Any], reasons: dict[str, str],
          frozen_date: str) -> list[str]:
    manifest = dict(report["manifest"])
    manifest["included"] = [
        {"path": path, "sha256": report["sourceHashes"][path]}
        for path in report["loaded"]
    ]
    kept = dict(report["excludedBefore"])
    manifest["excluded"] = [
        {"path": path, "reason": reasons.get(path) or kept.get(path, "")}
        for path in report["excludedNow"]
    ]
    manifest["bundleSha256"] = report["bundleSha256"]
    manifest["frozenDate"] = frozen_date
    (project / SHELL_BUNDLE_MANIFEST).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    matrix_path = project / MATRIX
    matrix = read_json(matrix_path)
    matrix.setdefault("baseline", {})["shellBundleSha256"] = report["bundleSha256"]
    matrix_path.write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    test_path = project / TEST_FILE
    text = test_path.read_text(encoding="utf-8")
    test_path.write_text(
        text.replace(str(report["oldBundleSha256"]), report["bundleSha256"]),
        encoding="utf-8")
    return [str(SHELL_BUNDLE_MANIFEST), str(MATRIX), str(TEST_FILE)]


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def _copy_project(destination: Path) -> Path:
    project = destination / "wasm_sdk_probe"
    project.mkdir(parents=True)
    for name in ("editor-shell", "input", "e1", "tests", "tools", "web", "sdk"):
        source = PROJECT / name
        if source.is_dir():
            shutil.copytree(source, project / name,
                            ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("editor-shell", "input", "web"):
        source = PROJECT / "dist" / name
        if source.is_dir():
            shutil.copytree(source, project / "dist" / name)
    return project


def self_test() -> int:
    failures: list[str] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)

        # 1. an untouched copy has to come back clean, or every other case
        #    below is measuring the copy rather than the mutation.
        project = _copy_project(root / "clean")
        report = plan(project)
        check("untouched copy reports clean", report["clean"], render(report))

        # 2. one byte inside an included module: detected, and one flag fixes it
        project = _copy_project(root / "byte")
        target = project / "editor-shell/state-machine.js"
        target.write_text(target.read_text(encoding="utf-8") + "\n// probe\n",
                          encoding="utf-8")
        report = plan(project)
        check("byte change is detected", not report["clean"])
        check("byte change alone is not a set change", not report["setChanged"])
        check("byte change with stale dist is blocked",
              any("source and dist disagree" in b
                  for b in blockers(report, False, {})))
        shutil.copy(target, project / "dist/editor-shell/state-machine.js")
        report = plan(project)
        check("after the asset copy, nothing blocks the write",
              not blockers(report, False, {}), str(blockers(report, False, {})))
        apply(project, report, {}, "2026-01-01")
        after = plan(project)
        check("write makes all three agree", after["clean"], render(after))

        # 3. a NEW module in the import graph must not be one flag
        project = _copy_project(root / "set")
        new_module = project / "editor-shell/probe-module.js"
        new_module.write_text("export const probe = 1;\n", encoding="utf-8")
        (project / "dist/editor-shell/probe-module.js").write_text(
            "export const probe = 1;\n", encoding="utf-8")
        entry = project / "web/e1-editor-validation-app.js"
        # The entry's own specifiers resolve from the project root, not from
        # web/ -- it is copied to dist/ root at build time.  Getting this wrong
        # in the fixture made the new module look UNIMPORTED, which is a
        # different case entirely; the first version of this self-test failed
        # for exactly that reason.
        entry.write_text(
            'import { probe } from "./editor-shell/probe-module.js";\n'
            + entry.read_text(encoding="utf-8"), encoding="utf-8")
        report = plan(project)
        check("a new imported module is a set change", report["setChanged"])
        check("--write alone refuses a set change",
              any("--allow-set-change" in b for b in blockers(report, False, {})))
        check("--allow-set-change lets it through",
              not blockers(report, True, {}), str(blockers(report, True, {})))

        # 4. a new UNimported module is an exclusion, and exclusions need reasons
        project = _copy_project(root / "excluded")
        orphan = project / "editor-shell/orphan-module.js"
        orphan.write_text("export const orphan = 1;\n", encoding="utf-8")
        (project / "dist/editor-shell/orphan-module.js").write_text(
            "export const orphan = 1;\n", encoding="utf-8")
        report = plan(project)
        check("an unimported module shows up as newly excluded",
              report["newlyExcluded"] == ["editor-shell/orphan-module.js"],
              str(report["newlyExcluded"]))
        check("exclusion without a reason is blocked",
              any("no reason given" in b for b in blockers(report, True, {})))
        reasons = {"editor-shell/orphan-module.js": "self-test fixture"}
        check("exclusion with a reason is allowed",
              not blockers(report, True, reasons),
              str(blockers(report, True, reasons)))
        apply(project, report, reasons, "2026-01-01")
        rewritten = read_json(project / SHELL_BUNDLE_MANIFEST)
        check("the reason is written into the manifest",
              any(item["path"] == "editor-shell/orphan-module.js"
                  and item["reason"] == "self-test fixture"
                  for item in rewritten["excluded"]))
        check("an exclusion does not move the bundle hash",
              rewritten["bundleSha256"] == report["oldBundleSha256"])

        # 5. the guard that matters most: after a write, the REAL gate must be
        #    no worse off.  A regenerate tool that satisfies itself but leaves
        #    tests/test_e1_c.py red would be worse than no tool.
        #
        #    Compared against a CLEAN copy rather than against "zero failures",
        #    because this sandbox has no dist/profiles or build tree, so some
        #    unrelated cases cannot run here at all.  Demanding zero would make
        #    the check fail for reasons that have nothing to do with the write
        #    -- and it did, the first time this ran.
        baseline_project = _copy_project(root / "gate-clean")
        before_failures = _failing_shell_tests(baseline_project)
        project = _copy_project(root / "gate")
        target = project / "editor-shell/state-machine.js"
        target.write_text(target.read_text(encoding="utf-8") + "\n// probe\n",
                          encoding="utf-8")
        shutil.copy(target, project / "dist/editor-shell/state-machine.js")
        apply(project, plan(project), {}, "2026-01-01")
        after_failures = _failing_shell_tests(project)
        introduced = sorted(set(after_failures) - set(before_failures))
        ran = _shell_test_count(baseline_project)
        check("a write introduces no new shell-bundle test failure",
              not introduced, ", ".join(introduced))
        check("the sandbox can run at least one shell-bundle test", ran > 0,
              "no shell-bundle test ran, so the check above proves nothing")
        # Say out loud how much of the gate this sandbox can actually reach.
        # Two cases need dist/profiles and a real workspace, so they fail on a
        # clean copy too; the check above is a subset comparison, not "green".
        print(f"        ({ran} shell-bundle cases ran in the sandbox; "
              f"{len(before_failures)} already fail on a clean copy and are "
              f"excluded by comparison, not by being green: "
              f"{', '.join(before_failures) or 'none'})")

    print()
    if failures:
        print(f"self-test FAILED: {len(failures)} case(s): {', '.join(failures)}")
        return 1
    print("self-test passed")
    return 0


def _run_shell_tests(project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "tests.test_e1_c"],
        cwd=project, capture_output=True, text=True)


def _failing_shell_tests(project: Path) -> list[str]:
    """Names of shell-bundle cases that FAIL or ERROR in this project copy."""
    completed = _run_shell_tests(project)
    return sorted({
        line.split(" ")[0]
        for line in completed.stderr.splitlines()
        if line.startswith(("FAIL: ", "ERROR: "))
        or (" ... " in line and line.split(" ... ")[-1].strip()
            in {"FAIL", "ERROR"})
        for line in [line.removeprefix("FAIL: ").removeprefix("ERROR: ")]
        if "shell_bundle" in line
    })


def _shell_test_count(project: Path) -> int:
    completed = _run_shell_tests(project)
    return sum(1 for line in completed.stderr.splitlines()
               if "shell_bundle" in line and " ... " in line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true",
                        help="apply the change to all three pinned locations")
    parser.add_argument("--allow-set-change", action="store_true",
                        help="required when the set of modules changed, not "
                             "just their bytes")
    parser.add_argument("--exclude-reason", action="append", default=[],
                        metavar="PATH=REASON",
                        help="reason a newly unimported module is excluded")
    parser.add_argument("--frozen-date", default=None,
                        help="frozenDate to stamp (default: today)")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--project", type=Path, default=PROJECT)
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    reasons: dict[str, str] = {}
    for item in args.exclude_reason:
        path, _, reason = item.partition("=")
        if not reason.strip():
            parser.error(f"--exclude-reason needs PATH=REASON, got: {item}")
        reasons[path] = reason.strip()

    report = plan(args.project)
    print(render(report))

    if report["clean"]:
        return 0

    problems = blockers(report, args.allow_set_change, reasons)
    if not args.write:
        print("\n(check mode -- nothing written. Re-run with --write to apply.)")
        for problem in problems:
            print(f"\nblocked: {problem}")
        return 1

    if problems:
        for problem in problems:
            print(f"\nblocked: {problem}")
        return 2

    from datetime import date
    written = apply(args.project, report, reasons,
                    args.frozen_date or date.today().isoformat())
    print("\nwritten:")
    for path in written:
        print(f"  {path}")
    print("\nNow re-run the gate that actually enforces this:"
          "\n  python3 -m unittest tests.test_e1_c")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
