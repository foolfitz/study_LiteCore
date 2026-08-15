#!/usr/bin/env python3
"""Assemble the E2-B narrow editor v2 product profile.

A separate entry point from build_e1_b_profile.py, and separate on purpose
(SPEC E2-B 5.8): a builder that can turn a v1 profile into a v2 one with a flag
is a builder that can mislabel a v1 profile as v2.  The version of an allowlist
is an identity, not a setting, and "one path, two identities" is how E1-C
extended v1 in place while the freeze test kept pinning eight of ten actions.

It refuses to write a manifest at all when the artifact it was handed is not a
product one.  That check is not new -- validate_e1_b.py:126-128 already reads
the export inventory and rejects anything containing `editor_discovery` -- it is
just moved earlier.  Catching it here rather than in the validator matters
because by validator time the evidence may already have been produced against
the wrong artifact.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e1_support import sha256, write_json  # noqa: E402

# SPEC E2-B 5.7: the action map, not a list of names.
#
# `gestures` is what the engine enforces, through
# oxsdk_editor_set_action_gestures; `limits` is the machine-readable form of the
# narrowings, which is how a partial GO gets expressed as a field rather than as
# UI prose.
COLLAPSED = "collapsed"
RANGE_SINGLE = "range-single"
RANGE_CROSS = "range-cross"
ALL_GESTURES = [COLLAPSED, RANGE_SINGLE, RANGE_CROSS]

# Bit values, and they must agree with OXSDK_EDITOR_GESTURE_* in editor_api.h.
# The C++ side static_asserts its two spellings against each other; this is the
# third spelling and it is checked at runtime by the negative matrix (N11).
GESTURE_BITS = {COLLAPSED: 1, RANGE_SINGLE: 2, RANGE_CROSS: 4}

V1_ACTIONS = [
    "move-character-left",
    "move-character-right",
    "delete-backward",
    "delete-forward",
    "insert-paragraph-break",
    "insert-line-break",
    "set-bold",
    "set-italic",
    "set-underline",
    "set-strikethrough",
]

V2_PARAGRAPH_ACTIONS = {
    "set-list-none": {"id": 11, "limits": []},
    "set-list-unordered": {"id": 12, "limits": []},
    "set-list-ordered": {"id": 13, "limits": []},
    "set-paragraph-heading": {"id": 14,
                              "limits": ["heading-level-1-only",
                                         "no-precondition-state"]},
    "set-paragraph-body": {"id": 15, "limits": ["no-precondition-state"]},
}


def action_map(cross_paragraph: bool) -> dict[str, dict]:
    """The manifest's action map.

    `cross_paragraph` is the A-versus-B' disposition, and it is a manifest
    choice rather than a build choice: the binary carries both, the mask
    withholds one.  False produces disposition A (cross-paragraph ranges are
    refused before dispatch); True produces B' (they are dispatched and every
    block is verified).
    """
    gestures = list(ALL_GESTURES) if cross_paragraph else [COLLAPSED, RANGE_SINGLE]
    actions: dict[str, dict] = {}
    for index, name in enumerate(V1_ACTIONS, start=1):
        # v1 actions keep their wire ids and are caret-only in this contract:
        # range dispatch was characterised for the paragraph actions, not for
        # delete or insert, and declaring a gesture nobody measured would be
        # the manifest claiming coverage the evidence does not have.
        actions[name] = {"id": index, "gestures": [COLLAPSED], "limits": []}
    for name, spec in V2_PARAGRAPH_ACTIONS.items():
        actions[name] = {"id": spec["id"], "gestures": list(gestures),
                         "limits": list(spec["limits"])}
    return actions


def refuse_non_product(exports: Path) -> list[str]:
    """Reasons this artifact may not be built into a product profile."""
    problems: list[str] = []
    if not exports.is_file():
        return [f"no export inventory at {exports}: cannot prove this artifact "
                "does not export the diagnostic ABI"]
    symbols = exports.read_text(encoding="utf-8").splitlines()
    leaked = [s for s in symbols if "editor_discovery" in s]
    if leaked:
        problems.append(f"exports the diagnostic ABI: {leaked}")
    for required in ("_oxsdk_editor_action", "_oxsdk_editor_get_state",
                     "_oxsdk_editor_select_range", "_oxsdk_editor_abi_version",
                     "_oxsdk_editor_set_action_gestures"):
        if required not in symbols:
            problems.append(f"missing product symbol {required}")
    return problems


def build_profile(source_manifest: Path, loader: Path, wasm: Path, worker: Path,
                  output: Path, exports: Path, cross_paragraph: bool) -> dict:
    problems = refuse_non_product(exports)
    if problems:
        raise SystemExit("refusing to build a v2 product profile:\n  "
                         + "\n  ".join(problems))

    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(loader, output / "probe.js")
    shutil.copy2(wasm, output / "probe.wasm")
    shutil.copy2(worker, output / "sdk-worker.js")

    manifest["profile"] = "e2-editor-v2"
    manifest["sdkVersion"] = f'{manifest["sdkVersion"]}+e2-editor-v2'
    manifest["artifactFiles"] = {
        **manifest["artifactFiles"],
        "probe.js": "./probe.js",
        "probe.wasm": "./probe.wasm",
    }
    capabilities = list(manifest.get("capabilities", []))
    # narrow-editor-v1 is deliberately NOT declared.  A v1 client reaching a v2
    # profile is refused at the capability gate, which is honest: letting it
    # through would hand it raw diagnostic state, because the worker's product
    # projection keys on the operation name (SPEC E2-B 5.5).
    capabilities.extend(["narrow-editor-v2", "verified-selection-delete"])
    manifest["capabilities"] = capabilities
    manifest.pop("diagnostic", None)
    manifest["editorContract"] = {
        "version": 2,
        "abiVersion": 2,
        "actions": action_map(cross_paragraph),
        "gestureBits": GESTURE_BITS,
        "textCommit": "document-sdk-insert-text",
        "undo": "document-sdk-undo",
        "state": "typed-editor-state-v1",
        "selectionBarrier": "verified-single-writer-unit-v1",
        "formatBarrier": "verified-format-readback-v2",
        # SPEC E2-B 5.13: a dispatched-but-unverified failure is not recovered
        # by asking the user to undo -- undo goes through the same queue that
        # the failure blocks.  The host rolls back to its checkpoint instead.
        "postDispatchFailureDisposition": "rollback-to-checkpoint",
        "crossParagraphDisposition": "verify-every-block" if cross_paragraph
                                     else "refuse-before-dispatch",
        "boundaryRejectionRequiresFreshWorker": True,
        "automaticRetry": False,
        "rawCallbackExposed": False,
        "arbitraryKeyCodeAccepted": False,
        "arbitraryUnoCommandAccepted": False,
        "diagnosticOperationsExposed": False,
        "loaderSha256": sha256(output / "probe.js"),
        "wasmSha256": sha256(output / "probe.wasm"),
        "workerSha256": sha256(output / "sdk-worker.js"),
    }
    write_json(output / "sdk-manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--exports", type=Path, required=True,
                        help="export inventory of the artifact being packaged")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cross-paragraph", action="store_true",
                        help="disposition B': dispatch cross-paragraph ranges "
                             "and verify every block. Without it, disposition "
                             "A: refuse them before dispatch.")
    args = parser.parse_args()
    manifest = build_profile(args.source_manifest, args.loader, args.wasm,
                             args.worker, args.output, args.exports,
                             args.cross_paragraph)
    print(json.dumps({
        "profile": manifest["profile"],
        "wasmSha256": manifest["editorContract"]["wasmSha256"][:16],
        "crossParagraphDisposition":
            manifest["editorContract"]["crossParagraphDisposition"],
        "actions": len(manifest["editorContract"]["actions"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
