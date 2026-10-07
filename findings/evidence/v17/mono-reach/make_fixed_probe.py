#!/usr/bin/env python3
"""M2's probe document (PREDICTION.md): six one-line paragraphs, each with its own automatic style.

Every paragraph: Western language en-US, Asian language zh-TW, text `<label> ABC abc 123 中文字測試`.  Fonts are
declared the way LibreOffice records them (`style:font-family-generic`, `style:font-pitch`).  Deterministic: fixed
zip timestamps, mimetype first and stored.  Writes wasm_sdk_probe/build/mono-reach-probe/fixed-pitch-probe.odt
(refuses an existing directory) and prints its sha256.
"""
import hashlib
import zipfile
from pathlib import Path

PROBE = Path(__file__).resolve().parents[4] / "wasm_sdk_probe"
OUT = PROBE / "build/mono-reach-probe"
NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
      'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
      'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
      'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"')
# name, svg:font-family, generic, pitch
FACES = [("細明體", "細明體", "modern", "fixed"),
         ("MingLiU", "MingLiU", "modern", "fixed"),
         ("Liberation Serif", "&apos;Liberation Serif&apos;", "roman", "variable"),
         ("新細明體", "新細明體", "roman", "variable"),
         ("Courier New", "&apos;Courier New&apos;", "modern", "fixed")]
LANGS = 'fo:language="en" fo:country="US" style:language-asian="zh" style:country-asian="TW"'
# label, Western (font-face name, or None), Asian (font-face name, or None), extra text properties
LINES = [("F1", "細明體", "細明體", ""),
         ("F2", "MingLiU", "MingLiU", ""),
         ("F3", "Liberation Serif", "細明體", ""),
         ("N1", "新細明體", "新細明體", ""),
         ("N2", "Courier New", None, ""),
         ("PC", None, None, 'fo:font-family="monospace"')]


def content() -> bytes:
    faces = "".join(f'<style:font-face style:name="{n}" svg:font-family="{f}" style:font-family-generic="{g}" '
                    f'style:font-pitch="{p}"/>' for n, f, g, p in FACES)
    styles, body = "", ""
    for label, western, asian, extra in LINES:
        props = " ".join(x for x in (f'style:font-name="{western}"' if western else "",
                                      f'style:font-name-asian="{asian}"' if asian else "", extra, LANGS) if x)
        styles += (f'<style:style style:name="{label}" style:family="paragraph">'
                   f'<style:text-properties {props}/></style:style>')
        body += f'<text:p text:style-name="{label}">{label} ABC abc 123 中文字測試</text:p>'
    return (f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {NS} office:version="1.3">'
            f'<office:font-face-decls>{faces}</office:font-face-decls>'
            f'<office:automatic-styles>{styles}</office:automatic-styles>'
            f'<office:body><office:text>{body}</office:text></office:body></office:document-content>'
            ).encode("utf-8")


MANIFEST = ('<?xml version="1.0" encoding="UTF-8"?><manifest:manifest '
            'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">'
            '<manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>'
            '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
            '</manifest:manifest>').encode("utf-8")

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=False)
    path = OUT / "fixed-pitch-probe.odt"
    with zipfile.ZipFile(path, "w") as z:
        for name, data, method in (("mimetype", b"application/vnd.oasis.opendocument.text", zipfile.ZIP_STORED),
                                   ("content.xml", content(), zipfile.ZIP_DEFLATED),
                                   ("META-INF/manifest.xml", MANIFEST, zipfile.ZIP_DEFLATED)):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 8, 0, 0, 0))
            info.compress_type = method
            z.writestr(info, data)
    print(hashlib.sha256(path.read_bytes()).hexdigest(), path.relative_to(PROBE))
