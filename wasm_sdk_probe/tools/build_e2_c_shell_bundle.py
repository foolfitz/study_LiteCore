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
#   v9 -- findings 053 and 054: the product prescribed a recovery whose button
#         it did not show, and read a reload flag nobody ever wrote.
#   v10, v11 -- pinning the product page at the v3 artifact.  Two generations
#         because pointing a page at an artifact turned out to be two separate
#         statements (the worker URL and the pin), and the guard caught the
#         first attempt with only one of them changed.
#   v12 -- the second v3 link (artifact d538ce0b): the worker projects the
#         engine's new caretParagraph/formatStale fields.  The generation the
#         finding 056 measurement is bound to.
#   v13 -- the product can open a document the USER chose, not only the samples
#         in its own dropdown (web/e2-editor.html + web/e2-editor-app.js).  A
#         shell-only change: `session.open({bytes, name})` was already the one
#         door in, so there is no engine side and it needed no link.
#   v14 -- finding 046's residual: bulleting a blank line no longer demands a
#         rollback.  `recovery` gains a fourth value, `review` (SPEC E2-C 2.6b,
#         written in the same generation).  Also shell-only, and also no link --
#         the disposition was always decided host-side from fields the frozen
#         worker already projects.
#   v15 -- finding 058: the page draws the caret and the selection.  Both were
#         delivered all along (editorState.caret, selection.rectangles) and the
#         page's only drawing call pasted the tile, so a user clicked and saw
#         nothing move.  Plus finding 045's product half: the page stopped
#         sending `enabled: true` unconditionally.
#   v16 -- the typing path: Backspace and Delete (beforeinput's two delete
#         types, which the input adapter drops as `ignored-input-type` without
#         preventing them), the left/right arrows, Ctrl+Z, Ctrl+S and cut.
#         Correcting a typo used to require the mouse and a toolbar button.
#   v17 -- finding 059's disposition half.  LOK_COMMAND_FAILED now reports
#         `dispatched-unverified` rather than falling through to
#         `unknown-rollback`, because that code is emitted only from the UNO
#         command RESULT handler, after the payload is matched to the command
#         that was sent -- core answered, so dispatch is established rather than
#         guessed.  Measured on both sides the same day: core APPLIES the
#         parameterised inline format on the shipped artifact and reports
#         success:false, so the old disposition asked the user to discard work
#         in order to undo a change that had succeeded
#         (findings/evidence/059/wasm/).  Shell-only; no link.  The engine fix
#         still needs one and still blocks it.
FROZEN_MANIFESTS = (Path("e2/editor-shell-v2-bundle-v1.json"),
                    Path("e2/editor-shell-v2-bundle-v2.json"),
                    Path("e2/editor-shell-v2-bundle-v3.json"),
                    Path("e2/editor-shell-v2-bundle-v4.json"),
                    Path("e2/editor-shell-v2-bundle-v5.json"),
                    Path("e2/editor-shell-v2-bundle-v6.json"),
                    Path("e2/editor-shell-v2-bundle-v7.json"),
                    Path("e2/editor-shell-v2-bundle-v8.json"),
                    Path("e2/editor-shell-v2-bundle-v9.json"),
                    Path("e2/editor-shell-v2-bundle-v10.json"),
                    Path("e2/editor-shell-v2-bundle-v11.json"),
                    Path("e2/editor-shell-v2-bundle-v12.json"),
                    Path("e2/editor-shell-v2-bundle-v13.json"),
                    Path("e2/editor-shell-v2-bundle-v14.json"),
                    Path("e2/editor-shell-v2-bundle-v15.json"),
                    Path("e2/editor-shell-v2-bundle-v16.json"),
                    Path("e2/editor-shell-v2-bundle-v17.json"),
                    Path("e2/editor-shell-v2-bundle-v18.json"),
                    Path("e2/editor-shell-v2-bundle-v19.json"),
                    Path("e2/editor-shell-v2-bundle-v20.json"),
                    Path("e2/editor-shell-v2-bundle-v21.json"),
                    Path("e2/editor-shell-v2-bundle-v22.json"),
                    Path("e2/editor-shell-v2-bundle-v23.json"),
                    Path("e2/editor-shell-v2-bundle-v24.json"),
                    Path("e2/editor-shell-v2-bundle-v25.json"),
                    Path("e2/editor-shell-v2-bundle-v26.json"),
                    Path("e2/editor-shell-v2-bundle-v27.json"),
                    Path("e2/editor-shell-v2-bundle-v28.json"),
                    Path("e2/editor-shell-v2-bundle-v29.json"),
                    Path("e2/editor-shell-v2-bundle-v30.json"),
                    Path("e2/editor-shell-v2-bundle-v31.json"),
                    Path("e2/editor-shell-v2-bundle-v32.json"))
FROZEN_MANIFEST = FROZEN_MANIFESTS[0]
# v33, 2026-08-22: redo and cut, prepared ahead of the ABI 4 link.
# 重做 joins the toolbar HIDDEN, plus Ctrl+Shift+Z and Ctrl+Y, all three gated on
# `offersRedo()` -- a separate accessor from `offers()` because redo is not an
# action: it has no wire id and no gesture, and the action map would answer
# "absent" for it on every profile including the ones that carry it.  Hidden
# rather than disabled: a disabled control promises a later moment that never
# arrives on a profile without redo.  Cut now prefers `delete-selection` when
# the profile offers it and otherwise falls back to today's behaviour rather
# than to an untested path.
#
# v32, 2026-08-22: the arrow keys, bound ahead of the ABI 4 link.
# The page now lists all six (Left/Right/Up/Down/Home/End) and gates each on
# `offers()`, a new client method that separates "this profile does not carry
# the action" from "this manifest has no gesture map at all" -- `gesturesFor`
# answers null for both, and treating them alike binds a key the engine refuses
# on every press.  On v3 the four new ones fall through untouched, measured; on
# v4 they light up because the manifest says the action exists.
#
# v31, 2026-08-22: finding 069's fix.  `#sink` had `position: absolute` with no
# `top`/`left`, so it sat at its static position -- after a canvas the height of
# the whole document -- and every IME composition scrolled the desk to the
# bottom.  It now rides the caret from `paint()`, in CSS pixels rather than
# backing pixels, sized to the caret so an IME candidate window has a line to
# open against, and with `pointer-events: none` so a 1px target over the canvas
# cannot swallow the pointerdown that places the caret.  Two files, and one of
# them is the HTML, which is the first time this bundle has moved for a
# stylesheet.
#
# v30, 2026-08-22: finding 068's fix, the session half.
# `editor-shell-v2/narrow-editor-v2-session.js` overrides `_handleEngineEvent`
# to take the caret from the engine's own `editor-state` announcement instead of
# waiting for the next queued operation to read it.
#
# AN OVERRIDE, not an edit to the base class, and the tree said so rather than
# me: the natural home was `EditorSession._handleEngineEvent`, and
# `check_e1_c_bundle_intact.py` refused it -- `editor-shell/editor-session.js`
# is bound to E1-C's verdict (shell bundle `187706b2…`), so editing it would
# unbind a verdict that has nothing to do with this defect.
#
# The other half is in the worker, which is NOT in this bundle: it is one of the
# profile's five bound identities, so it ships with the v4 link.  Verified in a
# mirror before either shipped: 5/5 with both halves, 0/4 with the worker half
# alone, 2/7 with neither.
#
# v29, 2026-08-22: the ABI 4 relink's client half.
# `editor-shell-v2/narrow-editor-v2-client.js` learned the five appended actions
# -- four movements by line and delete-selection -- with the movements sharing
# the character moves' postcondition (same route through the engine: a posted
# key event, `mutation = false`) and delete-selection filed with the UNO
# mutations rather than the barrier deletes, because it completes as
# `uno-command-result` and never produces `verified-selection-delete`.
#
# TWO GENERATIONS IN ONE DAY, and the second one is the honest cost of freezing
# the first too early: v28 was minted mid-work, before the client change was
# written. No round ran on v28, so rewriting it would have been harmless in
# fact -- which is exactly the argument this file's guard exists to refuse. A
# generation number is cheap; a generation that says one thing and holds another
# is what cost a day in 2026-08-17.
#
# v28, 2026-08-22: the ABI 4 relink's shell half.  `sdk/document-sdk.js` gained
# `redo()`, the sibling of `undo()` -- a document-level operation with no wire
# id, because an action id would drag the gesture mask and the option-flag
# validation along with it and none of the three means anything for walking the
# undo stack.  One file, and it is NOT the entrypoint this time, which is the
# point: the bundle covers the SDK the shell loads, so a change there moves the
# generation exactly as an entrypoint change does.
#
# v27, 2026-08-22: finding 067's fix.  `web/e2-editor-app.js` binds the Enter
# key in its own keydown handler -- paragraph break, or line break with Shift --
# instead of letting it reach the frozen input adapter, which turned it into a
# newline paste the engine accepted and ignored.  One file, and it is the
# entrypoint again.
#
# v26, 2026-08-22: finding 066's fix.  `web/e2-editor-app.js` gained a
# `mousedown` listener on the toolbar so a style button no longer takes the
# keyboard away from the document.  One file changed, and it is the entrypoint,
# so the bundle digest moves and the generation is a new identity -- which is
# what the version number is for (E2-B's first structural lesson: 版本是身分).
MANIFEST = Path("e2/editor-shell-v2-bundle-v33.json")
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
    # A path in BOTH lists is a manifest that contradicts itself, and the
    # exclusion's stated reason is by then describing a file that is imported
    # after all.  It happened on 2026-08-19: the page started importing
    # recovery-notice.js, the builder correctly moved it into `included`, and
    # the inherited exclusion -- "the product page never imports it" -- came
    # along for the ride.  The digest was right; the document was lying.
    both = sorted(set(state["included"]) & {
        str(item.get("path")) for item in (manifest or {}).get("excluded", [])})
    if both:
        out.append(f"included AND excluded, so one of the two is wrong: {both}")
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
    parser.add_argument("--force", action="store_true",
                        help="rewrite an existing manifest whose digest would "
                             "change -- discards the record of what a round ran "
                             "on, so it is never the routine answer")
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
    # Refuse to change a generation that already exists.
    #
    # 2026-08-17: bumping MANIFEST to v15 was done with a string replace that did
    # not match, so MANIFEST was still v14 and `--write` regenerated it in place
    # with a DIFFERENT digest -- the generation `e2/validation-matrix-v2.json`
    # and finding 046's evidence both name.  It was restored from git and no
    # measurement had been taken against the rewritten copy, so the damage was
    # nil, but only by luck: nothing complained.
    #
    # A generation is the record of what some round ran on (the comment at the
    # top of this file has said so since v1).  Adding it to FROZEN_MANIFESTS is
    # a manual step, so "not yet listed there" cannot be what protects it.  What
    # protects it is this: an existing manifest may be rewritten only when the
    # bytes it describes are unchanged.
    rewrites_existing = (manifest is not None
                         and manifest.get("bundleSha256") != state["digest"])
    if rewrites_existing and not args.force:
        # `.append`, not `found = found + [...]`: `report["problems"]` already
        # holds a reference to this list, and rebinding would leave the refusal
        # out of the report -- a guard that stops the write and says nothing,
        # which is the failure mode it was written for.
        found.append(
            f"refusing to rewrite {args.manifest} -- it exists with digest "
            f"{manifest.get('bundleSha256', '')[:16]}... and the tree now hashes "
            f"{state['digest'][:16]}.... A changed shell needs a NEW generation: "
            f"bump MANIFEST and add this one to FROZEN_MANIFESTS. --force only if "
            f"you mean to discard the record of what a round actually ran on.")
    if args.write and not rewrites_existing and not [p for p in found if "dist copy" in p]:
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
