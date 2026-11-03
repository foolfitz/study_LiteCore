#!/usr/bin/env python3
"""Assemble the Calc undo successor (SPEC-P-calc-undo 4.2) without overwriting a frozen profile.  Derived from build_calc_style_profile.py.

Closed list of differences: the base is ods-editor-v3 and the profile ods-editor-v4; the two undo exports are required; the manifest
gains the `undo` capability (redo rides on it in the worker), bit 8 (OXSDK_CAPABILITY_UNDO) in expectedCapabilityBits, and an
undoContract; this docstring."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parents[1]
BASE = HERE / "dist/profiles/ods-editor-v3"
PROFILE = "ods-editor-v4"
REQUIRED = {"_oxsdk_document_cell", "_oxsdk_document_save", "_oxsdk_document_open",
            "_oxsdk_document_paint", "_oxsdk_document_set_part", "_oxsdk_document_part_info",
            "_oxsdk_document_undo", "_oxsdk_document_redo"}
CAPABILITY_UNDO = 1 << 8  # src/sdk_api.h OXSDK_CAPABILITY_UNDO


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("loader", "wasm", "worker", "exports", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.development and not output.is_relative_to((HERE / "build").resolve()):
        raise SystemExit("development assembly must stay under build; frozen profiles are immutable")
    if (output / "sdk-manifest.json").exists() and not args.development:
        raise SystemExit("profile already exists; a frozen profile is not overwritten")
    if output == BASE.resolve():
        raise SystemExit("the predecessor profile must never be overwritten")
    exports = set(args.exports.read_text().split())
    if not REQUIRED <= exports or any(name.startswith("_oxsdk_editor") for name in exports):
        raise SystemExit(f"invalid Calc exports: missing {sorted(REQUIRED - exports)} or Writer API present")
    manifest = json.loads((BASE / "sdk-manifest.json").read_text())
    if "undo" in manifest["capabilities"] or manifest["expectedCapabilityBits"] & CAPABILITY_UNDO:
        raise SystemExit("the base already claims undo")
    output.mkdir(parents=True, exist_ok=True)
    for name, source in (("probe.js", args.loader), ("probe.wasm", args.wasm), ("sdk-worker.js", args.worker)):
        shutil.copyfile(source, output / name)
    for key in ("soffice.data", "soffice.data.js.metadata"):
        name = manifest["artifactFiles"][key].removeprefix("./")
        shutil.copyfile(BASE / name, output / name)
    manifest["profile"] = PROFILE
    manifest["sdkVersion"] = "0.6.0-r6-worker+" + PROFILE
    manifest["capabilities"].append("undo")
    manifest["expectedCapabilityBits"] |= CAPABILITY_UNDO
    manifest["undoContract"] = {
        "version": 1, "operations": ["undo", "redo"],
        "emptyStack": "NOTHING_TO_UNDO / NOTHING_TO_REDO before dispatch",
        "proof": "the undo and redo lists move by exactly one, else MUTATION_OUTCOME_UNKNOWN",
        "reply": ["revision", "undoCount", "redoCount", "cursor {part, column, row, moved} or null"],
        "singleCellBoldItalic": "one undo action (one setPropertyValues)",
    }
    (output / "sdk-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"profile": PROFILE, "development": args.development,
        "capabilityBits": manifest["expectedCapabilityBits"],
        "sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                   for name in ("probe.js", "probe.wasm", "sdk-worker.js", "sdk-manifest.json")}}, indent=2))


if __name__ == "__main__":
    main()
