#!/usr/bin/env python3
"""SPEC E2-C section 6: bind the E2 verdict to the shell, not just the artifact.

Half of what E2-C proves lives in JavaScript -- the fifteen-action client, the
product session, the page that drives them.  A verdict bound to wasm, loader
and worker alone permits all three to change afterwards while
`E2_GO_PARAGRAPH_FORMAT` stays green.  E1-C learned this the expensive way and
now binds a fourth hash; this is E2's.

Two deliberate choices carried over from E1-C's bundle:

  * the digest is over PATH + HASH pairs, so renaming a module is a change even
    if its bytes are identical;
  * `available - included - excluded` must be empty, so ADDING a file beside
    the covered ones is a change too.  Without that rule the binding says
    nothing about a module somebody drops in tomorrow.

And one addition E1-C's does not have, because E2-C's page is served rather
than imported by a test: every included path is compared against its copy under
`dist/`.  serve.py serves dist/, so a manifest frozen against source bytes the
server is not actually serving would bind the wrong thing.  Forgetting
`make e2-c-assets` is a standing trap in this tree.

Default mode is a question, not an action: it prints the difference and exits 1.
`--write` is the answer, and it always prints the diff as well.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_e1_c import sha256, shell_bundle_digest  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
# v1 is ROUND ONE's record and is frozen: `e2/validation-matrix-v1.json` names
# its digest, and round one's evidence can only be revalidated against the shell
# it actually ran on.  A legitimate shell change therefore writes a NEW manifest
# rather than regenerating that one -- the same rule the artifacts follow.
# Each generation is the record of the shell some round actually ran on, so a
# legitimate shell change writes a NEW manifest instead of regenerating one.
#   v1 -- round one's shell; `e2/validation-matrix-v1.json` names its digest.
#   v2 -- the shell the pre-relink D2/D3 defect sweeps ran on, including every
#         arm of finding 048.  Frozen from 2026-08-16, when the fix landed.
#   v3 -- the shell with finding 048's fix in EditorSession.placeCaret.  Frozen
#         from 2026-08-16: D3's corpus round, D4, D5's machine half and both
#         operator rounds ran on it, and so did the 046 and 048 rounds.
#   v4 -- the shell with finding 049's fix in web/e2-editor-app.js: the save
#         button had been writing 15 bytes of "[object Object]".  A new
#         manifest rather than a rewrite of v3, for the same reason as every
#         generation before it -- v3 is the record of what those rounds ran on.
#   v5 -- the shell with finding 050's fix in input/input-adapter.js: every IME
#         commit after the first was being rejected as a buffer mismatch,
#         because nothing cleared the host sink.
#   v6 -- the shell that wires Ctrl+C to session.copySelection() and surfaces
#         the input/clipboard traces, so a silently rejected commit is visible.
#   v7 -- finding 051: caretIsOnLine accepts the whole line box.  Under v1-v6
#         every click landing in the BOTTOM HALF of the line it hit waited 30 s
#         and was then refused, so about half of the product's clicks failed.
#   v8 -- finding 052: a click OUTSIDE every line box (below the last line, say)
#         is confirmed when the engine moves the caret, instead of waiting out
#         the 30 s timeout and being refused.
FROZEN_MANIFESTS = (Path("e2/editor-shell-v2-bundle-v1.json"),
                    Path("e2/editor-shell-v2-bundle-v2.json"),
                    Path("e2/editor-shell-v2-bundle-v3.json"),
                    Path("e2/editor-shell-v2-bundle-v4.json"),
                    Path("e2/editor-shell-v2-bundle-v5.json"),
                    Path("e2/editor-shell-v2-bundle-v6.json"),
                    Path("e2/editor-shell-v2-bundle-v7.json"),
                    Path("e2/editor-shell-v2-bundle-v8.json"))
FROZEN_MANIFEST = FROZEN_MANIFESTS[0]
MANIFEST = Path("e2/editor-shell-v2-bundle-v9.json")
ENTRYPOINT = Path("web/e2-editor-app.js")

# The directories whose *.js files must all be accounted for.  `editor-shell`
# is in the list even though E2 does not own it: the v2 session extends the v1
# session, so v1's bytes are part of what E2-C measures, and a change there must
# break E2's binding as well as E1's.  `reader-shell` is in it because the
# session's tile scheduler lives there -- a directory that contributes a module
# to the graph has to be scanned, or a file dropped in beside that module is
# invisible to this check.
SCOPE = ("editor-shell-v2", "editor-shell", "input", "sdk",
         "reader-shell")

IMPORT_PATTERN = re.compile(
    r"""(?:import|export)[^"']*?from\s*["']([^"']+)["']|import\s*\(\s*["']([^"']+)["']\s*\)""")


def imports_of(text: str) -> list[str]:
    return [a or b for a, b in IMPORT_PATTERN.findall(text)]


def reachable(project: Path, entry_relative: Path) -> list[str]:
    """Local modules reachable from the entry point, project-relative."""
    entry = project / entry_relative
    pending = [entry]
    visited: set[Path] = set()
    found: set[str] = set()
    while pending:
        path = pending.pop()
        resolved = path.resolve()
        if resolved in visited or not path.is_file():
            continue
        visited.add(resolved)
        text = path.read_text(encoding="utf-8")
        # The entry point lives under web/ but is served from the dist ROOT, so
        # its relative specifiers resolve from the project root.  Everything it
        # pulls in keeps its own directory.
        base = project if path == entry else path.parent
        for specifier in imports_of(text):
            if not specifier.startswith("."):
                continue
            dependency = (base / specifier).resolve()
            try:
                relative = dependency.relative_to(project.resolve())
            except ValueError:
                continue
            pending.append(dependency)
            if relative.suffix == ".js":
                found.add(relative.as_posix())
    return sorted(found)


def available(project: Path) -> list[str]:
    return sorted(path.relative_to(project).as_posix()
                  for directory in SCOPE
                  for path in (project / directory).glob("*.js"))


def compute(project: Path) -> dict[str, Any]:
    entry = ENTRYPOINT.as_posix()
    included = sorted({entry, *reachable(project, ENTRYPOINT)})
    hashes = {path: sha256(project / path) for path in included}
    # The dist copy of every included module, and of every available one: a
    # stale copy of a module this bundle excludes is still a stale server.
    dist_root = project / "dist"
    dist_name = {path: ("e2-editor-app.js" if path == entry else path)
                 for path in set(included) | set(available(project))}
    dist_hashes = {
        path: (sha256(dist_root / name) if (dist_root / name).is_file() else None)
        for path, name in dist_name.items()
    }
    return {
        "included": included,
        "hashes": hashes,
        "available": available(project),
        "distHashes": dist_hashes,
        "digest": shell_bundle_digest(hashes),
    }


def manifest_body(state: dict[str, Any], excluded: list[dict[str, str]],
                  frozen_date: str) -> dict:
    return {
        "schemaVersion": 1,
        "release": "E2-C-editor-shell-v2-bundle",
        # A generation's own date, not the first generation's.  It was hard
        # coded, so v4 came out claiming it was frozen on the day v1 was --
        # a manifest whose own record of when it was written is wrong is a poor
        # thing to bind a verdict to.
        "frozenDate": frozen_date,
        "entrypoint": ENTRYPOINT.as_posix(),
        "scope": "JavaScript modules reached by the E2-C product page's import "
                 "graph, plus every *.js in " + ", ".join(SCOPE),
        "algorithm": "SHA-256 of UTF-8 path + NUL + lowercase file SHA-256 + LF "
                     "for each included path in lexicographic order",
        "included": [{"path": path, "sha256": state["hashes"][path]}
                     for path in state["included"]],
        "excluded": excluded,
        "bundleSha256": state["digest"],
    }


def problems(project: Path, state: dict[str, Any],
             manifest: dict[str, Any] | None) -> list[str]:
    out: list[str] = []
    covered = set(state["included"]) | {
        str(item.get("path")) for item in (manifest or {}).get("excluded", [])}
    uncovered = sorted(set(state["available"]) - covered)
    if uncovered:
        out.append(f"in scope but neither included nor excluded: {uncovered}")
    for path in state["included"]:
        if state["distHashes"].get(path) != state["hashes"][path]:
            out.append(f"dist copy differs from source: {path} "
                       f"(run `make e2-c-assets`)")
    for path in state["available"]:
        if path in state["included"]:
            continue
        source = project / path
        # A path with no source file has nothing to be stale against.  Reading
        # it unconditionally made this function crash instead of reporting,
        # which the unit test found before the tree ever produced the case.
        if not source.is_file():
            continue
        if state["distHashes"].get(path) not in (None, sha256(source)):
            out.append(f"dist copy of an excluded module is stale: {path}")
    if manifest is not None:
        recorded = {item["path"]: item["sha256"]
                    for item in manifest.get("included", [])}
        if recorded != state["hashes"]:
            added = sorted(set(state["hashes"]) - set(recorded))
            removed = sorted(set(recorded) - set(state["hashes"]))
            changed = sorted(p for p in set(recorded) & set(state["hashes"])
                             if recorded[p] != state["hashes"][p])
            out.append(f"manifest is out of date: added={added} "
                       f"removed={removed} changed={changed}")
        elif manifest.get("bundleSha256") != state["digest"]:
            out.append("manifest records a digest that does not match its own "
                       "file list")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST,
                        help="which bundle manifest to check or write; the "
                             "default is round two's, and round one's is frozen")
    parser.add_argument("--write", action="store_true",
                        help="write the manifest; the diff is printed either way")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="PATH=REASON",
                        help="exclude a module from the bundle, with a reason; "
                             "'this file is not covered' is a claim somebody has "
                             "to make, so it does not get a default")
    parser.add_argument("--frozen-date", default=None,
                        help="the date THIS generation was frozen; defaults to "
                             "the existing manifest's, and a new generation "
                             "should be given one explicitly")
    args = parser.parse_args()

    state = compute(PROJECT)
    manifest_path = PROJECT / args.manifest
    manifest = (json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_path.is_file() else None)

    excluded = [{"path": item.split("=", 1)[0], "reason": item.split("=", 1)[1]}
                for item in args.exclude if "=" in item]
    if manifest and not excluded:
        excluded = manifest.get("excluded", [])
    if not manifest and not excluded:
        # Starting a NEW generation used to silently produce an empty exclusion
        # list, and an empty one breaks the rule this bundle is built on:
        # `available - included - excluded` must be empty, so that dropping a
        # file beside the covered ones is a change.  A v4 that inherits nothing
        # binds LESS than the v3 it replaces, while looking like progress.
        # Measured on 2026-08-16 while freezing v4 for finding 049.
        for candidate in reversed(FROZEN_MANIFESTS):
            path = PROJECT / candidate
            if not path.is_file():
                continue
            inherited = json.loads(path.read_text(encoding="utf-8")).get("excluded")
            if inherited:
                excluded = inherited
                report_inherited = str(candidate)
                break
        else:
            report_inherited = None
    else:
        report_inherited = None

    found = problems(PROJECT, state, manifest if not args.write else None)
    report = {
        "manifest": str(args.manifest),
        "included": state["included"],
        "excluded": [item["path"] for item in excluded],
        "bundleSha256": state["digest"],
        "problems": found,
        # Said out loud: a new generation that inherited its exclusions did not
        # decide them, and the reader should know which manifest did.
        "exclusionsInheritedFrom": report_inherited,
    }
    if args.write and not [p for p in found if "dist copy" in p]:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        body = manifest_body(state, excluded, args.frozen_date
                             or (manifest or {}).get("frozenDate")
                             or "unrecorded")
        manifest_path.write_text(
            json.dumps(body, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        report["written"] = True
        # Re-checked against what was just written.  `found` above was computed
        # with no manifest (a new generation has none yet), so it reports every
        # exclusion as unaccounted for -- a report that reads like four problems
        # when the file on disk has none.  A tool that prints stale problems
        # trains its reader to ignore the field.
        found = problems(PROJECT, state,
                         json.loads(manifest_path.read_text(encoding="utf-8")))
        report["problems"] = found
        report["problemsRecheckedAfterWrite"] = True
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not found else 1


if __name__ == "__main__":
    sys.exit(main())
