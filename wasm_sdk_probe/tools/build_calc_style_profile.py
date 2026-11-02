#!/usr/bin/env python3
"""Assemble the Calc style successor (SPEC-P-demo-batch-3 3.1) without overwriting a frozen profile.  Derived from build_calc_range_profile.py."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parents[1]
BASE = HERE / "dist/profiles/ods-editor-v2"
PROFILE = "ods-editor-v3"
REQUIRED = {"_oxsdk_document_cell", "_oxsdk_document_save", "_oxsdk_document_open",
            "_oxsdk_document_paint", "_oxsdk_document_set_part", "_oxsdk_document_part_info"}


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
    output.mkdir(parents=True, exist_ok=True)
    for name, source in (("probe.js", args.loader), ("probe.wasm", args.wasm), ("sdk-worker.js", args.worker)):
        shutil.copyfile(source, output / name)
    for key in ("soffice.data", "soffice.data.js.metadata"):
        name = manifest["artifactFiles"][key].removeprefix("./")
        shutil.copyfile(BASE / name, output / name)
    manifest["profile"] = PROFILE
    manifest["sdkVersion"] = "0.6.0-r6-worker+" + PROFILE
    manifest["capabilities"].append("cell-range-styling")
    manifest["expectedCapabilityBits"] |= 1 << 19
    manifest["rangeStylingContract"] = {
        "version": 1, "maxLogicalCells": 65536, "styles": ["textColor", "backColor", "horizontalAlign"],
        "colors": "lower-case #rrggbb, auto for text, none for background",
        "horizontalAligns": ["standard", "left", "center", "right", "block"],
        "mergeBoundary": "refuse", "hiddenCells": "included", "mutation": "single-native-pattern",
        "unknownOutcome": "retain-document-and-refuse-further-writes",
    }
    (output / "sdk-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"profile": PROFILE, "development": args.development,
        "capabilityBits": manifest["expectedCapabilityBits"],
        "sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                   for name in ("probe.js", "probe.wasm", "sdk-worker.js", "sdk-manifest.json")}}, indent=2))


if __name__ == "__main__":
    main()
