#!/usr/bin/env python3
"""Assemble the Microsoft-formats successors (specs/SPEC-P-ms-formats.md 5.1) without overwriting a frozen profile.  Derived from
build_calc_undo_profile.py.

Closed list of differences from the frozen base manifest:

  writer  base dist/profiles/e2-editor-v32  -> e2-editor-v33: capabilities + open-docx, save-docx; bits 20, 21
  calc    base dist/profiles/ods-editor-v4  -> ods-editor-v5: capabilities + open-xlsx, save-xlsx; bits 22, 23
  calc-headers  base dist/profiles/ods-editor-v5 -> ods-editor-v6: capabilities + cell-headers, cell-structure; bits 24, 25;
          a `headersContract` and a `structureContract` (SPEC-P-calc-headers 3.3, 2026-11-05: an entry in this table, not a new
          tool; SPEC-P-calc-structure 3.2 adds the second capability to the same, unreleased profile)
  calc-copy  base dist/profiles/ods-editor-v6 -> ods-editor-v7: capabilities + cell-copy; bit 26; a `copyContract`
          (SPEC-P-calc-copy 3.1-3.2)
  calc-html-zoom  base dist/profiles/ods-editor-v7 -> ods-editor-v8: capabilities + cell-copy-html, cell-zoom; bits 27, 28;
          a `copyHtmlContract` and a `zoomContract` (SPEC-P-calc-copy 9.1, SPEC-P-calc-zoom 3.1-3.2)

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
                     "capabilities": ["cell-headers", "cell-structure"],
                     "bits": (1 << 24) | (1 << 25),  # src/sdk_api.h OXSDK_CAPABILITY_CELL_HEADERS, CELL_STRUCTURE
                     "contracts": [("structureContract", {
                         "version": 1, "spec": "specs/SPEC-P-calc-structure.md",
                         "operation": "cellStructure: cell operation 14, a mutation",
                         "change": "{axis: rows|columns, action: insert|delete, index, count}; count >= 1, index + count <= max",
                         "reply": "{axis, action, index, count, maxColumns, maxRows, changed: true}",
                         "refused": "READ_ONLY (read-only or protected sheet), STRUCTURE_REFUSED (the core refused; nothing changed)"})],
                     "contract": ("headersContract", {
                         "version": 1, "spec": "specs/SPEC-P-calc-headers.md",
                         "operation": "cellHeaders: cell operation 13, read-only, no cell selected",
                         "rectangle": "twips {x, y, width, height}, non-negative integers, width and height not both 0, each at most 245760",
                         "reply": "{maxColumns, maxRows, columns, rows}; entries {index, label, startPx, endPx, hidden}; 1 CSS px = 15 twips",
                         "wholeRanges": "a whole column (rows 0..maxRows-1), whole row (columns 0..maxColumns-1) or the sheet "
                                        "passes the 65536-cell limit and the merge boundary; protection and read-only still refuse"})},
    "calc-copy": {"base": HERE / "dist/profiles/ods-editor-v6", "profile": "ods-editor-v7",
                  "capabilities": ["cell-copy"],
                  "bits": 1 << 26,  # src/sdk_api.h OXSDK_CAPABILITY_CELL_COPY
                  "contract": ("copyContract", {
                      "version": 1, "spec": "specs/SPEC-P-calc-copy.md",
                      "operation": "cellCopy: cell operation 15, read-only, the selection is restored",
                      "range": "{column, row, endColumn, endRow}; at most 65536 cells unless a whole column, row or the sheet",
                      "reply": "{plainText, markedColumn, markedRow, markedEndColumn, markedEndRow, changed: false}; plainText is "
                               "the core's own copy text (getTextSelection text/plain;charset=utf-8)",
                      "refused": "COPY_UNAVAILABLE (no text: an empty range), RANGE_TOO_LARGE, COPY_REFUSED (the range was not "
                                 "selected)"})},
    "calc-html-zoom": {"base": HERE / "dist/profiles/ods-editor-v7", "profile": "ods-editor-v8",
                       "capabilities": ["cell-copy-html", "cell-zoom"],
                       "bits": (1 << 27) | (1 << 28),  # src/sdk_api.h OXSDK_CAPABILITY_CELL_COPY_HTML, _CELL_ZOOM
                       "contract": ("copyHtmlContract", {
                           "version": 1, "spec": "specs/SPEC-P-calc-copy.md 9",
                           "reply": "cellCopy's reply also carries htmlText, the core's text/html for the same selection "
                                    "(getTextSelection text/html), kept as it came; absent when the core gives none"}),
                       "contracts": [("zoomContract", {
                           "version": 1, "spec": "specs/SPEC-P-calc-zoom.md",
                           "operation": "cellZoom: cell operation 16, read-only for the document; every later operation and "
                                        "the page's tiles use 256 px per tileTwips",
                           "tileTwips": [7680, 5120, 3840, 3072, 2560, 1920],
                           "reply": "{tileTwips, percent: 384000 / tileTwips, widthTwips, heightTwips (getDocumentSize at that "
                                    "zoom), changed: false}",
                           "refused": "INVALID_ARGUMENT (tileTwips outside the list)"})]},
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
    for key, value in [spec["contract"], *spec.get("contracts", [])]:
        manifest[key] = value
    (output / "sdk-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"profile": spec["profile"], "development": args.development,
                      "capabilityBits": manifest["expectedCapabilityBits"],
                      "sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                                 for name in ("probe.js", "probe.wasm", "sdk-worker.js", "sdk-manifest.json")}}, indent=2))


if __name__ == "__main__":
    main()
