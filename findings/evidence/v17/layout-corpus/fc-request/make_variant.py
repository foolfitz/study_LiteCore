#!/usr/bin/env python3
"""Variant D of test-docs/e1/paragraph-content.odt for the fc-request discriminator (PREDICTION.md).

D: the `Preformatted_20_Text` paragraph gets an automatic style (parent: that style) whose ONLY added property is
`style:font-name` (the WESTERN slot) = Liberation Mono (in the base pack, so present in both arms).  The fixture's
style sets that slot to the generic name `monospace` (`fo:font-family`); D replaces it with a named face.  Nothing
else in the document changes.  Same construction as ../mono-discriminator/make_variants.py, which only ever varied
the Asian slot.  Writes to wasm_sdk_probe/build/fc-request/ and refuses to overwrite; prints the output's sha256.
"""
import hashlib
import sys
import zipfile
from pathlib import Path

PROBE = Path(__file__).resolve().parents[5] / "wasm_sdk_probe"
SRC = PROBE / "test-docs/e1/paragraph-content.odt"
OUT = PROBE / "build/fc-request"
FAMILY = "Liberation Mono"


def variant(name: str) -> Path:
    src = zipfile.ZipFile(SRC)
    content = src.read("content.xml").decode("utf-8")
    anchor_p = '<text:p text:style-name="Preformatted_20_Text">'
    if content.count(anchor_p) != 1 or content.count("<office:automatic-styles>") != 1 \
            or "<office:font-face-decls" in content:
        sys.exit("the fixture is not shaped as this script expects")
    content = content.replace(anchor_p, '<text:p text:style-name="PREX">')
    content = content.replace(
        "<office:automatic-styles>",
        f'<office:font-face-decls><style:font-face style:name="PREXF" svg:font-family="&apos;{FAMILY}&apos;"/>'
        "</office:font-face-decls><office:automatic-styles>"
        '<style:style style:name="PREX" style:family="paragraph" style:parent-style-name="Preformatted_20_Text">'
        '<style:text-properties style:font-name="PREXF"/></style:style>')
    out = OUT / f"{name}.odt"
    with zipfile.ZipFile(out, "w") as z:
        for info in src.infolist():
            data = content.encode("utf-8") if info.filename == "content.xml" else src.read(info.filename)
            z.writestr(info, data, compress_type=zipfile.ZIP_STORED if info.filename == "mimetype"
                       else zipfile.ZIP_DEFLATED)
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=False)
    path = variant("D-western-liberation-mono")
    print(hashlib.sha256(SRC.read_bytes()).hexdigest(), SRC.relative_to(PROBE))
    print(hashlib.sha256(path.read_bytes()).hexdigest(), path.relative_to(PROBE))
