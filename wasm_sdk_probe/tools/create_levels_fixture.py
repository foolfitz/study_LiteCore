#!/usr/bin/env python3
"""SPEC-P-demo-batch-4: a small ODT for the heading and list arms.  Body, H1 to H4, a two-item bullet list, a numbered item, a mid
empty paragraph and an empty last paragraph, every paragraph with a text anchor.  Deterministic bytes.
create_levels_fixture.py OUT.odt"""
from pathlib import Path
import sys
import zipfile

NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
      'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"')
CONTENT = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content {NS} office:version="1.3"><office:automatic-styles>
<text:list-style style:name="L1"><text:list-level-style-bullet text:level="1" text:bullet-char="&#8226;"/></text:list-style>
<text:list-style style:name="L2"><text:list-level-style-number text:level="1" style:num-format="1" style:num-suffix="."/></text:list-style>
</office:automatic-styles><office:body><office:text>
<text:p text:style-name="Text_20_body">ALPHA plain paragraph one</text:p>
<text:p text:style-name="Text_20_body">BRAVO plain paragraph two</text:p>
<text:h text:style-name="Heading_20_1" text:outline-level="1">CHARLIE heading one</text:h>
<text:h text:style-name="Heading_20_2" text:outline-level="2">DELTA heading two</text:h>
<text:h text:style-name="Heading_20_3" text:outline-level="3">ECHO heading three</text:h>
<text:h text:style-name="Heading_20_4" text:outline-level="4">FOXTROT heading four</text:h>
<text:list text:style-name="L1"><text:list-item><text:p text:style-name="Standard">GOLF bullet item</text:p></text:list-item><text:list-item><text:p text:style-name="Standard">HOTEL bullet item</text:p></text:list-item></text:list>
<text:list text:style-name="L2"><text:list-item><text:p text:style-name="Standard">INDIA numbered item</text:p></text:list-item></text:list>
<text:p text:style-name="Text_20_body">JULIET plain paragraph</text:p>
<text:p text:style-name="Text_20_body"/>
<text:p text:style-name="Text_20_body">KILO last with text</text:p>
<text:p text:style-name="Text_20_body"/>
</office:text></office:body></office:document-content>'''


def heading(level, size):
    return (f'<style:style style:name="Heading_20_{level}" style:display-name="Heading {level}" style:family="paragraph" '
            f'style:parent-style-name="Standard" style:default-outline-level="{level}"><style:text-properties fo:font-size="{size}pt" '
            'fo:font-weight="bold"/></style:style>')


STYLES = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles {NS} office:version="1.3"><office:styles>
<style:style style:name="Standard" style:family="paragraph" style:class="text"/>
<style:style style:name="Text_20_body" style:display-name="Text body" style:family="paragraph" style:parent-style-name="Standard"/>
{heading(1, 20)}{heading(2, 17)}{heading(3, 15)}{heading(4, 13)}
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
            info = zipfile.ZipInfo(name, (2026, 11, 3, 0, 0, 0))
            info.compress_type = method
            z.writestr(info, data)
        add("mimetype", "application/vnd.oasis.opendocument.text", zipfile.ZIP_STORED)
        add("content.xml", CONTENT, zipfile.ZIP_DEFLATED)
        add("styles.xml", STYLES, zipfile.ZIP_DEFLATED)
        add("META-INF/manifest.xml", MANIFEST, zipfile.ZIP_DEFLATED)


if __name__ == "__main__":
    main()
