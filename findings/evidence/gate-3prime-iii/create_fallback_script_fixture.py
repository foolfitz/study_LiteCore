#!/usr/bin/env python3
"""Build the fixture B-2 criterion 3'-iii needs: text only the fallback pack can draw.

The families are chosen FROM THE FALLBACK PACK'S OWN METADATA, per the
criterion. `Amiri` is in the fallback slice and in neither the base nor the cjk
slice, so a profile without the fallback pack has no font for it -- and neither
Arabic nor Hebrew has any coverage in `Liberation*` + `NotoSansCJK`, which is
everything the base and cjk slices contain.

Four paragraphs, because two different questions are being asked:

  1  Latin, default family        -- the control. Must render identically
                                     everywhere, or the comparison measures the
                                     harness rather than the fonts.
  2  Arabic, family `Amiri`       -- a NAMED font that exists only in the
                                     fallback pack.
  3  Arabic, default family       -- the engine's own script fallback, which is
                                     what the pack is named for.
  4  Hebrew, default family       -- a second script, so a result cannot be an
                                     Arabic-shaping peculiarity.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

LATIN = "TP3-LATIN control ABCdef 123"
ARABIC = "TP3-ARABIC السلام عليكم"
HEBREW = "TP3-HEBREW שלום עולם"

STYLES = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 office:version="1.3">
 <office:font-face-decls>
  <style:font-face style:name="Amiri" svg:font-family="Amiri"
   xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"/>
 </office:font-face-decls>
 <office:styles/>
 <office:automatic-styles/>
 <office:master-styles/>
</office:document-styles>
"""

CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
 office:version="1.3">
 <office:font-face-decls>
  <style:font-face style:name="Amiri" svg:font-family="Amiri"/>
 </office:font-face-decls>
 <office:automatic-styles>
  <style:style style:name="TP3Amiri" style:family="paragraph">
   <style:text-properties style:font-name="Amiri" fo:font-size="20pt"
    style:font-name-complex="Amiri" style:font-size-complex="20pt"/>
  </style:style>
  <style:style style:name="TP3Big" style:family="paragraph">
   <style:text-properties fo:font-size="20pt" style:font-size-complex="20pt"/>
  </style:style>
 </office:automatic-styles>
 <office:body><office:text>
  <text:p text:style-name="TP3Big">{latin}</text:p>
  <text:p text:style-name="TP3Amiri">{arabic}</text:p>
  <text:p text:style-name="TP3Big">{arabic}</text:p>
  <text:p text:style-name="TP3Big">{hebrew}</text:p>
 </office:text></office:body>
</office:document-content>
""".format(latin=LATIN, arabic=ARABIC, hebrew=HEBREW)

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
 manifest:version="1.3">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.3"
  manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""


def main() -> int:
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w") as archive:
        # `mimetype` first and STORED, or it is not an ODT.
        archive.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/vnd.oasis.opendocument.text",
            compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/manifest.xml", MANIFEST)
        archive.writestr("content.xml", CONTENT)
        archive.writestr("styles.xml", STYLES)
    print(f"wrote {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
