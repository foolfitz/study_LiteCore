#!/usr/bin/env python3
"""Variants of test-docs/e1/paragraph-content.odt for the H-mono discriminator (PREDICTION.md).

A: the fixture as is.  B: the `Preformatted_20_Text` paragraph gets an automatic style (parent: that style) whose
ONLY added property is `style:font-name-asian` = Noto Sans CJK TC (present in both packs).  C: the same with
Liberation Mono (in the base pack, so present in both).  Nothing else in the document changes.
Writes to wasm_sdk_probe/build/mono-discriminator/ (inside the probe tree, because the corpus tool keys documents
by their path relative to it); prints each output's sha256.
"""
import hashlib
import sys
import zipfile
from pathlib import Path

PROBE = Path(__file__).resolve().parents[5] / "wasm_sdk_probe"
SRC = PROBE / "test-docs/e1/paragraph-content.odt"
OUT = PROBE / "build/mono-discriminator"


def variant(name: str, family: str | None) -> Path:
    src = zipfile.ZipFile(SRC)
    content = src.read("content.xml").decode("utf-8")
    if family is not None:
        anchor_p = '<text:p text:style-name="Preformatted_20_Text">'
        if content.count(anchor_p) != 1 or content.count("<office:automatic-styles>") != 1 \
                or "<office:font-face-decls" in content:
            sys.exit("the fixture is not shaped as this script expects")
        content = content.replace(anchor_p, '<text:p text:style-name="PREX">')
        content = content.replace(
            "<office:automatic-styles>",
            f'<office:font-face-decls><style:font-face style:name="PREXF" svg:font-family="&apos;{family}&apos;"/>'
            "</office:font-face-decls><office:automatic-styles>"
            '<style:style style:name="PREX" style:family="paragraph" style:parent-style-name="Preformatted_20_Text">'
            '<style:text-properties style:font-name-asian="PREXF"/></style:style>')
    out = OUT / f"{name}.odt"
    with zipfile.ZipFile(out, "w") as z:
        for info in src.infolist():
            data = content.encode("utf-8") if info.filename == "content.xml" else src.read(info.filename)
            z.writestr(info, data, compress_type=zipfile.ZIP_STORED if info.filename == "mimetype"
                       else zipfile.ZIP_DEFLATED)
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=False)
    for name, family in (("A-as-is", None), ("B-asian-noto-sans-cjk-tc", "Noto Sans CJK TC"),
                         ("C-asian-liberation-mono", "Liberation Mono")):
        path = variant(name, family)
        print(hashlib.sha256(path.read_bytes()).hexdigest(), path.relative_to(PROBE))
