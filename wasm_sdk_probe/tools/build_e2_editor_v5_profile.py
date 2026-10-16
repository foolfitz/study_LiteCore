#!/usr/bin/env python3
"""Assemble an editor-ABI-5 product profile: the link batch v21 (e2-editor-v21).

SPEC-M3-link-batch-v21 4.1, 4.2 and 9.10.  Named for the ABI it packages, as
`build_e2_editor_v4_profile.py` is: ABI 5 is the successor identity of ABI 4.

THE MECHANISM (spec 9.10, opus S9), and why it is this one
-----------------------------------------------------------

The v4 builder is not edited by one byte.  It is a prerequisite of the v8-v20
manifest rules, and editing it would make make(1) treat those frozen targets
as out of date (finding 042).  So this module

  1. patches `v4.ABI_VERSION` (4 -> 5) and `v4.action_map` (ids 1-21 -> 1-23),
  2. strips its own flags from argv and calls `v4.main()` -- every other flag,
     every guard and every packaging step is v4's, unchanged,
  3. adds its own leaves to the manifest v4 wrote, rewrites it, and reprints
     v4's digest with the final manifest's hash.

The patch is undone before this returns, whatever happens, so a process that
imports both builders (the tests) sees v4 as v4.

WHAT MOVES
----------

  * `editorContract.abiVersion` 4 -> 5.  The worker's handshake is an EXACT
    match against `oxsdk_editor_abi_version()`, which the v21 engine reports
    as 5 (editor_api.h under OXSDK_E2_V21_LINK_BATCH).
  * two actions appended, ids 22 and 23 (finding 142, Ctrl+Home / Ctrl+End).
    Ids 1-21 are inherited verbatim -- checked below, not asserted.
  * `editorContract.pasteMarkdown = "document-sdk-paste-markdown"`, ONLY with
    `--paste-markdown`, and refused unless the export list carries
    `_oxsdk_document_paste_markdown` -- the same TOLD-not-guessed rule as
    v4's `--page-rectangles`: a declaration the artifact cannot honour is the
    2026-08-22 defect.  It is a document-level export, not an action: no wire
    id, no gesture (spec 4.2).

WHAT DOES NOT
-------------

  * C's declaration (`boundaryNoop`) is not here: the owner withdrew it from
    v21 (spec 9.13, OD3=A).  No `--boundary-noop` flag exists.
  * Everything v4 decides: the inherited gestures, `--inline-range-gestures`,
    `--page-rectangles`, the packs.  This module does not see them.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_e2_b_profile as v2  # noqa: E402
import build_e2_editor_v4_profile as v4  # noqa: E402
from e1_support import write_json  # noqa: E402

ABI_VERSION = 5

# The two caret moves: `collapsed` only, `no-extend-selection` (spec 4.1).  On
# a range, natively, the empty TEXT_SELECTION arrives before the caret, and
# completing on it would serialise the caret from before the move -- the
# defect that keeps the six other moves collapsed-only too.  The page reaches
# a range through moveFromPoint instead (spec 4.1, D4).
NEW_ACTIONS: dict[str, dict] = {
    "move-document-start": {"id": 22, "gestures": [v2.COLLAPSED],
                            "limits": ["no-extend-selection"]},
    "move-document-end": {"id": 23, "gestures": [v2.COLLAPSED],
                          "limits": ["no-extend-selection"]},
}

PASTE_MARKDOWN_DECLARATION = "document-sdk-paste-markdown"
PASTE_MARKDOWN_EXPORT = "_oxsdk_document_paste_markdown"
OWN_FLAGS = ("--paste-markdown",)

# Captured at import, while it is still v4's own: once patched, `v4.action_map`
# IS this module's action_map, and calling it from here would recurse.
_V4_ACTION_MAP = v4.action_map


def action_map() -> dict:
    actions = _V4_ACTION_MAP()
    inherited = {name: spec["id"] for name, spec in actions.items()}
    for name, spec in NEW_ACTIONS.items():
        if name in actions:
            raise SystemExit(f"v5 redefines inherited action {name}")
        actions[name] = {"id": spec["id"], "gestures": list(spec["gestures"]),
                         "limits": list(spec["limits"])}
    # The claim, checked: the 21 inherited actions keep their wire ids, and the
    # two new ones are exactly 22 and 23.
    for name, wire in inherited.items():
        if actions[name]["id"] != wire:
            raise SystemExit(f"v5 renumbered inherited action {name}: "
                             f"{wire} -> {actions[name]['id']}")
    ids = sorted(spec["id"] for spec in actions.values())
    if ids != list(range(1, 24)):
        raise SystemExit(f"v5 action ids are not 1..23 exactly: {ids}")
    return actions


def paste_markdown_problems(exports: Path | None) -> list[str]:
    """Why --paste-markdown may not be declared for this artifact."""
    if exports is None or not exports.is_file():
        return [f"no export inventory at {exports}"]
    if PASTE_MARKDOWN_EXPORT not in exports.read_text(encoding="utf-8").splitlines():
        return [f"--paste-markdown needs {PASTE_MARKDOWN_EXPORT} in {exports}"]
    return []


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    own = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    own.add_argument("--paste-markdown", action="store_true")
    own.add_argument("--exports", type=Path)
    own.add_argument("--output", type=Path)
    own.add_argument("--profile")
    known, _ = own.parse_known_args(argv[1:])

    # v4 defaults --profile to its own frozen name.  An ABI-5 manifest stamped
    # `e2-editor-v4` would make two artifacts answer to one name.
    if not known.profile:
        raise SystemExit("--profile is required: this builder has no default "
                         "identity, and v4's default is a frozen ABI-4 name")
    if known.profile == v4.PROFILE:
        raise SystemExit(f"refusing to stamp an ABI-{ABI_VERSION} manifest "
                         f"with the frozen name {v4.PROFILE}")
    # Before anything is built, like v4's --page-rectangles refusal.
    if known.paste_markdown:
        problems = paste_markdown_problems(known.exports)
        if problems:
            raise SystemExit("refusing to declare pasteMarkdown:\n  "
                             + "\n  ".join(problems))

    v4_argv = [argv[0]] + [arg for arg in argv[1:] if arg not in OWN_FLAGS]
    saved = (v4.ABI_VERSION, v4.action_map, sys.argv)
    v4.ABI_VERSION = ABI_VERSION
    v4.action_map = action_map
    sys.argv = v4_argv
    printed = io.StringIO()
    try:
        with contextlib.redirect_stdout(printed):
            code = v4.main()
    finally:
        v4.ABI_VERSION, v4.action_map, sys.argv = saved
    if code:
        return code

    manifest_path = known.output / "sdk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = manifest["editorContract"]
    # A patch that did not take effect must not ship as if it had.
    if contract.get("abiVersion") != ABI_VERSION or sorted(
            spec["id"] for spec in contract["actions"].values()) != list(range(1, 24)):
        raise SystemExit("v4.main() did not write the patched ABI and actions")
    if known.paste_markdown:
        contract["pasteMarkdown"] = PASTE_MARKDOWN_DECLARATION
    manifest["editorContract"] = contract
    write_json(manifest_path, manifest)

    summary = json.loads(printed.getvalue())
    summary["abiVersion"] = ABI_VERSION
    summary["manifestSha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    summary["pasteMarkdown"] = contract.get("pasteMarkdown")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
