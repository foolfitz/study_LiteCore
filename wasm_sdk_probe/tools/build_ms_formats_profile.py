#!/usr/bin/env python3
"""Assemble the Microsoft-formats successors (specs/SPEC-P-ms-formats.md 5.1) without overwriting a frozen profile.  Derived from
build_calc_undo_profile.py.

Closed list of differences from the frozen base manifest:

  writer  base dist/profiles/e2-editor-v32  -> e2-editor-v33: capabilities + open-docx, save-docx; bits 20, 21
  calc    base dist/profiles/ods-editor-v4  -> ods-editor-v5: capabilities + open-xlsx, save-xlsx; bits 22, 23
  calc-headers  base dist/profiles/ods-editor-v5 -> ods-editor-v6: capabilities + cell-headers; bit 24; a `headersContract`
          (SPEC-P-calc-headers 3.3, 2026-11-05: an entry in this table, not a new tool; writer and calc build as before)

plus `profile`, `sdkVersion`, a `documentFormatContract` naming the table (src/document_format.hpp), and -- Writer only -- the
editorContract's loaderSha256 / wasmSha256 / workerSha256 recomputed from the copied artifacts (they named v32's; Codex review
2026-11-03 item 1).  No other field of either base manifest names an engine artifact (the resource packs' sha256 do not move).  The export list must equal
the base's (no new export), and the base must not already claim either capability.  --development assembles under build/ only;
without it the output must not already hold a manifest (a frozen profile is never overwritten).
  build_ms_formats_profile.py --profile writer|calc --loader F --wasm F --worker F --exports F --base-exports F --output DIR [--development]
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parents[1]
PROFILES = {
    "writer": {"base": HERE / "dist/profiles/e2-editor-v32", "profile": "e2-editor-v33", "ms": "docx",
               "bits": (1 << 20) | (1 << 21),  # src/sdk_api.h OXSDK_CAPABILITY_OPEN_DOCX, SAVE_DOCX
               "open": [".odt", ".docx"], "save": ["odt", "docx"]},
    "calc": {"base": HERE / "dist/profiles/ods-editor-v4", "profile": "ods-editor-v5", "ms": "xlsx",
             "bits": (1 << 22) | (1 << 23),  # OXSDK_CAPABILITY_OPEN_XLSX, SAVE_XLSX
             "open": [".odt", ".ods", ".xlsx"], "save": ["ods", "xlsx"]},
    "calc-headers": {"base": HERE / "dist/profiles/ods-editor-v5", "profile": "ods-editor-v6",
                     "capabilities": ["cell-headers"], "bits": 1 << 24,  # src/sdk_api.h OXSDK_CAPABILITY_CELL_HEADERS
                     "contract": ("headersContract", {
                         "version": 1, "spec": "specs/SPEC-P-calc-headers.md",
                         "operation": "cellHeaders: cell operation 13, read-only, no cell selected",
                         "rectangle": "twips {x, y, width, height}, non-negative integers, width and height not both 0, each at most 245760",
                         "reply": "{maxColumns, maxRows, columns, rows}; entries {index, label, startPx, endPx, hidden}; 1 CSS px = 15 twips",
                         "wholeRanges": "a whole column (rows 0..maxRows-1), whole row (columns 0..maxColumns-1) or the sheet "
                                        "passes the 65536-cell limit and the merge boundary; protection and read-only still refuse"})},
}
for _spec in PROFILES.values():  # the Microsoft-formats entries, in the general form
    if "ms" in _spec:
        _spec["capabilities"] = [f"open-{_spec['ms']}", f"save-{_spec['ms']}"]
        _spec["contract"] = ("documentFormatContract", {
            "version": 1, "table": "src/document_format.hpp", "open": _spec["open"], "save": _spec["save"],
            "openReply": "format: the accepted suffix's format", "refused": "INVALID_ARGUMENT before the queue"})


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    for name in ("loader", "wasm", "worker", "exports", "base-exports", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    spec = PROFILES[args.profile]
    base = spec["base"]
    output = args.output.resolve()
    if args.development and not output.is_relative_to((HERE / "build").resolve()):
        raise SystemExit("development assembly must stay under build; frozen profiles are immutable")
    if (output / "sdk-manifest.json").exists() and not args.development:
        raise SystemExit("profile already exists; a frozen profile is not overwritten")
    if output == base.resolve():
        raise SystemExit("the predecessor profile must never be overwritten")
    exports, base_exports = set(args.exports.read_text().split()), set(args.base_exports.read_text().split())
    if exports != base_exports:
        raise SystemExit(f"the export list moved: added {sorted(exports - base_exports)}, removed {sorted(base_exports - exports)}")
    manifest = json.loads((base / "sdk-manifest.json").read_text())
    if set(spec["capabilities"]) & set(manifest["capabilities"]) or manifest["expectedCapabilityBits"] & spec["bits"]:
        raise SystemExit(f"the base already claims {spec['capabilities']}")
    output.mkdir(parents=True, exist_ok=True)
    for name, source in (("probe.js", args.loader), ("probe.wasm", args.wasm), ("sdk-worker.js", args.worker)):
        shutil.copyfile(source, output / name)
    for key in ("soffice.data", "soffice.data.js.metadata"):
        relative = manifest["artifactFiles"][key]
        if relative.startswith("./"):  # Calc carries its image beside the engine; Writer's lives in ../resources
            shutil.copyfile(base / relative[2:], output / relative[2:])
    sha = lambda name: hashlib.sha256((output / name).read_bytes()).hexdigest()
    contract = manifest.get("editorContract")
    if contract is not None:
        for key, name in (("loaderSha256", "probe.js"), ("wasmSha256", "probe.wasm"), ("workerSha256", "sdk-worker.js")):
            if key not in contract:
                raise SystemExit(f"editorContract lacks {key}: the base manifest changed shape")
            contract[key] = sha(name)
    manifest["profile"] = spec["profile"]
    manifest["sdkVersion"] = "0.6.0-r6-worker+" + spec["profile"]
    manifest["capabilities"] += spec["capabilities"]
    manifest["expectedCapabilityBits"] |= spec["bits"]
    key, value = spec["contract"]
    manifest[key] = value
    (output / "sdk-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"profile": spec["profile"], "development": args.development,
                      "capabilityBits": manifest["expectedCapabilityBits"],
                      "sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                                 for name in ("probe.js", "probe.wasm", "sdk-worker.js", "sdk-manifest.json")}}, indent=2))


if __name__ == "__main__":
    main()
