#!/usr/bin/env python3
"""Assemble ods-editor-v1 using the frozen viewer-v3 filesystem and shared packs.

The new engine owns its editing/save exports; no frozen viewer artifact is
modified. Development output stays under build/ until browser acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parents[1]
BASE = HERE / "dist/profiles/ods-viewer-v3"
PROFILE = "ods-editor-v1"
REQUIRED = {"_oxsdk_document_cell", "_oxsdk_document_save", "_oxsdk_document_open",
            "_oxsdk_document_paint", "_oxsdk_document_set_part", "_oxsdk_document_part_info"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("loader", "wasm", "worker", "exports", "output"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--development", action="store_true")
    a = ap.parse_args()
    if (a.output / "sdk-manifest.json").exists() and not a.development:
        raise SystemExit("profile already exists; a frozen profile is not overwritten")
    exports = set(a.exports.read_text().split())
    if not REQUIRED <= exports or any(name.startswith("_oxsdk_editor") for name in exports):
        raise SystemExit(f"invalid Calc exports: missing {sorted(REQUIRED - exports)} or Writer API present")
    manifest = json.loads((BASE / "sdk-manifest.json").read_text())
    a.output.mkdir(parents=True, exist_ok=True)
    for name, source in (("probe.js", a.loader), ("probe.wasm", a.wasm), ("sdk-worker.js", a.worker)):
        shutil.copyfile(source, a.output / name)
    for key in ("soffice.data", "soffice.data.js.metadata"):
        name = manifest["artifactFiles"][key].removeprefix("./")
        shutil.copyfile(BASE / name, a.output / name)
    manifest["profile"] = PROFILE
    manifest["sdkVersion"] = "0.6.0-r6-worker+" + PROFILE
    manifest["capabilities"] += ["cell-editing", "save-ods"]
    manifest["expectedCapabilityBits"] |= (1 << 16) | (1 << 17)
    manifest["cellEditingContract"] = {"version": 1, "inputLimitUtf16": 32767,
        "formats": ["bold", "italic", "underline"], "geometryTwipsPerCssPixel": 15}
    (a.output / "sdk-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"profile": PROFILE, "development": a.development,
        "capabilityBits": manifest["expectedCapabilityBits"],
        "sha256": {name: hashlib.sha256((a.output / name).read_bytes()).hexdigest()
                   for name in ("probe.js", "probe.wasm", "sdk-worker.js", "sdk-manifest.json")}}, indent=2))


if __name__ == "__main__":
    main()
