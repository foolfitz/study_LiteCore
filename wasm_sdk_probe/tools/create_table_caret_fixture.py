#!/usr/bin/env python3
"""SPEC-P-demo-batch-4 N3: a paragraph, a two-by-two table, a paragraph.  Where does a one-character read go at a cell's edge?
Deterministic bytes.  create_table_caret_fixture.py OUT.odt"""
from pathlib import Path
import sys
import zipfile

NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
      'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
      'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"')


def cell(text):
    return f'<table:table-cell office:value-type="string"><text:p text:style-name="Standard">{text}</text:p></table:table-cell>'


CONTENT = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content {NS} office:version="1.3"><office:body><office:text>
<text:p text:style-name="Standard">BEFORE the table</text:p>
<table:table table:name="T1"><table:table-column table:number-columns-repeated="2"/>
<table:table-row>{cell("CELLA first")}{cell("CELLB second")}</table:table-row>
<table:table-row>{cell("CELLC third")}{cell("CELLD fourth")}</table:table-row>
</table:table>
<text:p text:style-name="Standard">AFTER the table</text:p>
</office:text></office:body></office:document-content>'''
STYLES = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles {NS} office:version="1.3"><office:styles>
<style:style style:name="Standard" style:family="paragraph" style:class="text"/>
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
