#!/usr/bin/env python3
"""Deterministic inputs for the v21 shakedown, item 2 (paste as Markdown).

Arms: findings/evidence/link-batch-v21/shakedown/ARMS-item2.md (I-10, DM-13, DM-17 A).

  size_corpus(n)      M3's size corpus: "中" * floor(n/3) + "a" * (n - 3*floor(n/3)), exactly n UTF-8
                      bytes. The shape of sdk/tests/paste-markdown.test.mjs:43-47 (`corpus()`).
  m6_corpus(limit)    M6's corpus (DM-13 A, shared with item 1's D6): round 1's BLOCK sections
                      (findings/evidence/link-batch-v21/native/markdown-paste/tool/make_corpus.py) while the
                      total stays <= limit - 16 bytes, then one ASCII paragraph "Tail ttt...\n" to exactly
                      `limit` bytes.
  m10_selectables()   M10b/c's fixture (DM-17 A): an ODT with a 2 cm square PNG anchored as a character,
                      alone in the first paragraph; body text; a page-anchored 6 cm x 3 cm text frame with a
                      border and 0.5 cm padding at (3 cm, 10 cm) on page 1; a tail paragraph. A4, 2 cm margins.

Every output's sha256 is pinned in PINNED and checked by tests/test_v21_item2_fixtures.py. A generator change
that moves a sha256 is a new input: update PINNED in the same commit and say so.

  v21_item2_fixtures.py --out DIR     write every output into DIR (refuses to overwrite) and print the sums
  v21_item2_fixtures.py --check       recompute every output and compare it with PINNED (exit 1 on a difference)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import struct
import sys
import zipfile
import zlib
from pathlib import Path

sys.dont_write_bytecode = True      # never write a __pycache__ into the committed native round's tool/

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
ROUND1_MAKE_CORPUS = REPO / "findings/evidence/link-batch-v21/native/markdown-paste/tool/make_corpus.py"

SIZE_UNIT = "中"                     # U+4E2D, three UTF-8 bytes
SIZE_TAIL = "a"

# sha256 of every output this module can produce, as written into ARMS-item2.md (I-10, M6) before any run.
PINNED = {
    "size-65536.md": "9ecdb239209da768f29a61418a5488f8878ead671ee967a705f80b3fe46d0460",
    "size-65537.md": "19bb9725c72fcd84ac9910ae0b8bb56937421cb9a0ace15d4f02eeea5cfc4af0",
    "size-16384.md": "2840901a77a8eb2298d3307f72420390ad644c80412543c4d225a47a48d403e5",
    "size-16385.md": "6f0b9f72b5aa5dc8b288142b9be1bb4bc2b6f7514a3988ce744b471600e6d6fd",
    "m6-65536.md": "78d342b089140c7aeec6bbffa8cc738fef9530c11758ab616e9640144b26ae22",
    "m6-16384.md": "7189c657fedffb4561b4ba1fa01ac204d84d550cfc9e52e9f303686c38c784c7",
    # Not in the arms file (the fixture did not exist when it was written); pinned here at its creation.
    "m10-selectables.odt": "c0628cc94189228fa36e5a24ca017930cd6a4d081ca7437c95153b46e395ea2e",
}


def size_corpus(n: int) -> bytes:
    """Exactly n UTF-8 bytes: three-byte CJK characters and an ASCII tail of n mod 3 bytes."""
    if n < 0:
        raise ValueError("negative size")
    cjk = n // 3
    data = (SIZE_UNIT * cjk + SIZE_TAIL * (n - 3 * cjk)).encode("utf-8")
    if len(data) != n:
        raise AssertionError(f"size corpus is {len(data)} bytes, wanted {n}")
    return data


def _round1_block() -> str:
    spec = importlib.util.spec_from_file_location("v21_round1_make_corpus", ROUND1_MAKE_CORPUS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BLOCK


def m6_corpus(limit: int) -> tuple[bytes, int]:
    """(bytes, sections): round 1's BLOCK sections up to limit - 16 bytes, then an ASCII tail to `limit`."""
    block = _round1_block()
    out, sections = b"", 0
    while True:
        nxt = block.format(n=sections + 1).encode("utf-8")
        if len(out) + len(nxt) > limit - 16:
            break
        out += nxt
        sections += 1
    pad = limit - len(out) - len(b"Tail \n")
    if pad < 1:
        raise AssertionError("no room for the tail paragraph")
    data = out + b"Tail " + b"t" * pad + b"\n"
    if len(data) != limit:
        raise AssertionError(f"M6 corpus is {len(data)} bytes, wanted {limit}")
    return data, sections


def _png(width: int, height: int, rgb=(30, 90, 200)) -> bytes:
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
      'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
      'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
      'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
      'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
      'xmlns:xlink="http://www.w3.org/1999/xlink"')

M10_PICTURE = "Pictures/m10-square.png"

# Geometry the arms read (twips; 1 cm = 566.93 twips). The LOK document space puts page 1 at (284, 284)
# (v20's P1 rectangles: "284, 284, 11906, 16838" [observed findings/evidence/link-batch/v20-shakedown/README.md]).
# These are DECLARED here and MEASURED natively in round 3 (DM-17 C); the WASM arm clicks where the native
# run found the object, never where this table predicts it.
M10_GEOMETRY = {
    "imageCm": [2.0, 2.0], "imageAnchor": "as-char, alone in paragraph 1",
    "frameCm": {"x": 3.0, "y": 10.0, "width": 6.0, "height": 3.0, "border": 0.06, "padding": 0.5},
    "pageOriginTwips": [284, 284], "marginsCm": 2.0,
}


def m10_selectables() -> bytes:
    # The page-anchored frame comes BEFORE the first paragraph: placed after the paragraphs, native Writer
    # dropped it on import (round 3's dry run, 2026-10-16: the saved before.fodt had no m10-frame); round
    # 2's frame-protected.fodt has it first, as here.
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-content {NS} office:version="1.3">
 <office:automatic-styles>
  <style:style style:name="frImage" style:family="graphic"><style:graphic-properties style:vertical-pos="top" style:vertical-rel="baseline"/></style:style>
  <style:style style:name="frText" style:family="graphic"><style:graphic-properties style:wrap="none" style:vertical-pos="from-top" style:vertical-rel="page" style:horizontal-pos="from-left" style:horizontal-rel="page" fo:border="0.06cm solid #000000" fo:padding="0.5cm"/></style:style>
 </office:automatic-styles>
 <office:body><office:text>
  <draw:frame draw:style-name="frText" draw:name="m10-frame" text:anchor-type="page" text:anchor-page-number="1" svg:x="3cm" svg:y="10cm" svg:width="6cm" svg:height="3cm" draw:z-index="1"><draw:text-box><text:p text:style-name="Standard">M10-FRAME text</text:p></draw:text-box></draw:frame>
  <text:p text:style-name="Standard"><draw:frame draw:style-name="frImage" draw:name="m10-image" text:anchor-type="as-char" svg:width="2cm" svg:height="2cm" draw:z-index="0"><draw:image xlink:href="{M10_PICTURE}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad" draw:mime-type="image/png"/></draw:frame></text:p>
  <text:p text:style-name="Standard">M10-BODY plain paragraph after the image</text:p>
  <text:p text:style-name="Standard">M10-TAIL last paragraph</text:p>
 </office:text></office:body>
</office:document-content>
"""
    styles = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles {NS} office:version="1.3">
 <office:styles>
  <style:style style:name="Standard" style:family="paragraph" style:class="text"/>
 </office:styles>
 <office:automatic-styles>
  <style:page-layout style:name="pm1"><style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" fo:margin-top="2cm" fo:margin-bottom="2cm" fo:margin-left="2cm" fo:margin-right="2cm"/></style:page-layout>
 </office:automatic-styles>
 <office:master-styles>
  <style:master-page style:name="Standard" style:page-layout-name="pm1"/>
 </office:master-styles>
</office:document-styles>
"""
    manifest = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.3" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="Pictures/m10-square.png" manifest:media-type="image/png"/>
</manifest:manifest>
"""
    members = [("mimetype", b"application/vnd.oasis.opendocument.text", zipfile.ZIP_STORED),
               ("content.xml", content.encode("utf-8"), zipfile.ZIP_DEFLATED),
               ("styles.xml", styles.encode("utf-8"), zipfile.ZIP_DEFLATED),
               (M10_PICTURE, _png(8, 8), zipfile.ZIP_STORED),
               ("META-INF/manifest.xml", manifest.encode("utf-8"), zipfile.ZIP_DEFLATED)]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data, method in members:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = method
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def outputs() -> dict[str, bytes]:
    return {
        "size-65536.md": size_corpus(65536), "size-65537.md": size_corpus(65537),
        "size-16384.md": size_corpus(16384), "size-16385.md": size_corpus(16385),
        "m6-65536.md": m6_corpus(65536)[0], "m6-16384.md": m6_corpus(16384)[0],
        "m10-selectables.odt": m10_selectables(),
    }


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(pinned: dict[str, str | None] | None = None) -> list[str]:
    """Problems found: an output whose sha256 differs from its pin, or a pin with no output."""
    pinned = PINNED if pinned is None else pinned
    produced = outputs()
    problems = []
    for name, data in produced.items():
        want = pinned.get(name)
        if want is None:
            problems.append(f"{name}: no pinned sha256 (got {sha256(data)})")
        elif sha256(data) != want:
            problems.append(f"{name}: sha256 {sha256(data)} != pinned {want}")
    problems += [f"{name}: pinned but not produced" for name in pinned if name not in produced]
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        problems = check()
        for line in problems:
            print("PROBLEM", line)
        print("ok" if not problems else f"{len(problems)} problem(s)")
        return 0 if not problems else 1
    if args.out is None:
        parser.error("--out DIR or --check")
    args.out.mkdir(parents=True, exist_ok=True)
    for name, data in outputs().items():
        target = args.out / name
        if target.exists():
            raise SystemExit(f"refusing to overwrite {target}")
        target.write_bytes(data)
        print(sha256(data), name, len(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
