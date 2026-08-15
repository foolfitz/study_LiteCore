#!/usr/bin/env python3
"""SPEC E2-B 5.10: build the negative-matrix profile variants.

Each variant is the baseline v2 profile with EXACTLY ONE thing changed.  That
is rule 1 of 5.10 and it is not a style preference: change two things and "it
refused" cannot be attributed to either.  Task #49's arm G was struck for
exactly this shape, so the rule is enforced here by construction -- every
variant is produced by a single named mutation applied to a fresh copy of the
baseline, and the tool reports what it changed.

The artifact files are hard-linked, not copied: a variant must differ from the
baseline in its MANIFEST only.  Copying the wasm would work too, but a
hard-link makes "same artifact" a property of the filesystem rather than of my
having remembered to copy the right file.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e1_support import write_json  # noqa: E402

ARTIFACT_FILES = ("probe.js", "probe.wasm", "sdk-worker.js")


def drop_action(manifest: dict, action: str) -> str:
    del manifest["editorContract"]["actions"][action]
    return f"editorContract.actions no longer lists {action}"


def drop_capability(manifest: dict, capability: str) -> str:
    manifest["capabilities"] = [c for c in manifest["capabilities"]
                                if c != capability]
    return f"capabilities no longer includes {capability}"


def set_contract_version(manifest: dict, version: int) -> str:
    manifest["editorContract"]["version"] = version
    return f"editorContract.version is {version}"


def set_abi_version(manifest: dict, version: int) -> str:
    manifest["editorContract"]["abiVersion"] = version
    return f"editorContract.abiVersion is {version} (the binary reports 2)"


def restrict_gestures(manifest: dict, action: str, gestures: list[str]) -> str:
    manifest["editorContract"]["actions"][action]["gestures"] = list(gestures)
    return f"{action} is restricted to {gestures}"


# The rows that are produced by mutating a manifest.  The rest of the matrix --
# unknown action names, wrong option flags, stale revisions, forbidden fields --
# are payload mutations and belong to the harness, not here: they need no
# variant profile, and giving them one would mean two things differed.
VARIANTS = {
    "n1-action-withheld": lambda m: drop_action(m, "set-list-ordered"),
    "n2-capability-withheld": lambda m: drop_capability(m, "narrow-editor-v2"),
    "n3-contract-version-1": lambda m: set_contract_version(m, 1),
    "n4-abi-version-mismatch": lambda m: set_abi_version(m, 3),
    "n11-gesture-withheld": lambda m: restrict_gestures(
        m, "set-list-unordered", ["collapsed", "range-single"]),
}


def build(baseline: Path, output_root: Path, name: str) -> dict:
    manifest = json.loads((baseline / "sdk-manifest.json").read_text(encoding="utf-8"))
    target = output_root / f"{baseline.name}-{name}"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for filename in ARTIFACT_FILES:
        source = baseline / filename
        try:
            os.link(source, target / filename)
        except OSError:
            shutil.copy2(source, target / filename)

    changed = VARIANTS[name](manifest)
    manifest["profile"] = f'{manifest["profile"]}-{name}'
    # The recorded artifact hashes are NOT touched: the variant runs the same
    # binary, and a row that changed the manifest's idea of the artifact as
    # well would be two mutations.  n4 is the exception and it is the point of
    # that row -- it changes abiVersion and nothing else.
    write_json(target / "sdk-manifest.json", manifest)
    return {"variant": name, "profile": manifest["profile"],
            "path": str(target), "changed": changed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path,
                        default=Path("dist/profiles/e2-editor-v2"))
    parser.add_argument("--output-root", type=Path, default=Path("dist/profiles"))
    args = parser.parse_args()
    built = [build(args.baseline, args.output_root, name) for name in VARIANTS]
    print(json.dumps({"baseline": str(args.baseline), "variants": built},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
