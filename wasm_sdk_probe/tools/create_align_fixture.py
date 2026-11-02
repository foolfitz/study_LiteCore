#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 N1/P1: a small ODT for the alignment arms: plain, heading, list, already centred, empty, and an empty last
paragraph.  Deterministic bytes.  create_align_fixture.py OUT.odt"""
from pathlib import Path
import sys
import zipfile

NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
      'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"')
CONTENT = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content {NS} office:version="1.3"><office:automatic-styles>
<style:style style:name="PC" style:family="paragraph" style:parent-style-name="Standard"><style:paragraph-properties fo:text-align="center" style:justify-single-word="false"/></style:style>
<text:list-style style:name="L1"><text:list-level-style-bullet text:level="1" text:bullet-char="&#8226;"/></text:list-style>
</office:automatic-styles><office:body><office:text>
<text:p text:style-name="Standard">ALPHA plain paragraph one</text:p>
<text:p text:style-name="Standard">BRAVO plain paragraph two</text:p>
<text:h text:style-name="Heading_20_1" text:outline-level="1">CHARLIE heading</text:h>
<text:list text:style-name="L1"><text:list-item><text:p text:style-name="Standard">DELTA list item</text:p></text:list-item></text:list>
<text:p text:style-name="PC">ECHO already centred</text:p>
<text:p text:style-name="Standard"/>
<text:p text:style-name="Standard">FOXTROT last with text</text:p>
<text:p text:style-name="Standard"/>
</office:text></office:body></office:document-content>'''
STYLES = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles {NS} office:version="1.3"><office:styles>
<style:style style:name="Standard" style:family="paragraph" style:class="text"/>
<style:style style:name="Heading_20_1" style:display-name="Heading 1" style:family="paragraph" style:parent-style-name="Standard" style:default-outline-level="1"><style:text-properties fo:font-size="16pt" fo:font-weight="bold"/></style:style>
</office:styles></office:document-styles>'''
MANIFEST = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
<manifest:file-entry manifest:full-path="/" manifest:version="1.3" manifest:media-type="application/vnd.oasis.opendocument.text"/>
<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
<manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>'''


def main():
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w") as z:
        def add(name, data, method):
            info = zipfile.ZipInfo(name, (2026, 11, 2, 0, 0, 0))
            info.compress_type = method
            z.writestr(info, data)
        add("mimetype", "application/vnd.oasis.opendocument.text", zipfile.ZIP_STORED)
        add("content.xml", CONTENT, zipfile.ZIP_DEFLATED)
        add("styles.xml", STYLES, zipfile.ZIP_DEFLATED)
        add("META-INF/manifest.xml", MANIFEST, zipfile.ZIP_DEFLATED)


if __name__ == "__main__":
    main()
