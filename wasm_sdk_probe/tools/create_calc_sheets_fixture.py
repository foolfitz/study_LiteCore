#!/usr/bin/env python3
"""The fixture of specs/SPEC-P-calc-sheets.md section 6: calc-structure.ods's five sheets (create_calc_structure_fixture.py, not
edited) and four more whose names need quoting in a reference, or do not -- 有 空白 (a space), 2026 (starts with a digit),
O'Neil (an apostrophe) and Sheet_3 (ASCII, no quoting) -- each with its own name in A1 and 10 in B1.

  create_calc_sheets_fixture.py OUTPUT_DIR      writes calc-sheets.ods and manifest.json
"""
import argparse
from html import escape
import json
import zipfile
from pathlib import Path

from create_calc_edit_fixture import NS
from create_calc_headers_fixture import FIRST_SHEET, OTHER_SHEETS, STYLES
from create_calc_structure_fixture import ARRAY_SHEET, EDGE_SHEET

NAMED = ['有 空白', '2026', "O'Neil", 'Sheet_3']


def named_sheet(name):
    quoted = escape(name, quote=True)
    return (f'<table:table table:name="{quoted}"><table:table-row><table:table-cell office:value-type="string">'
            f'<text:p>{escape(name)}</text:p></table:table-cell><table:table-cell office:value-type="float" office:value="10">'
            '<text:p>10</text:p></table:table-cell></table:table-row></table:table>')


def create(output):
    output.mkdir(parents=True, exist_ok=True)
    named = '\n'.join(named_sheet(name) for name in NAMED)
    content = (f'<?xml version="1.0" encoding="UTF-8"?>\n<office:document-content {NS} office:version="1.3">\n{STYLES}'
               f'<office:body><office:spreadsheet>\n{FIRST_SHEET}\n{OTHER_SHEETS}\n{EDGE_SHEET}\n{ARRAY_SHEET}\n{named}\n'
               '</office:spreadsheet></office:body></office:document-content>')
    manifest_xml = ('<?xml version="1.0"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
                    'manifest:version="1.3"><manifest:file-entry manifest:full-path="/" '
                    'manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/><manifest:file-entry '
                    'manifest:full-path="content.xml" manifest:media-type="text/xml"/></manifest:manifest>')
    path = output / 'calc-sheets.ods'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo('mimetype', (2026, 11, 6, 0, 0, 0)), b'application/vnd.oasis.opendocument.spreadsheet')
        for name, body in (('content.xml', content), ('META-INF/manifest.xml', manifest_xml)):
            info = zipfile.ZipInfo(name, (2026, 11, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, body.encode())
    metadata = {'file': path.name, 'sheets': ['編輯測試', '另一張表', '保護測試', '邊界測試', '陣列測試', *NAMED],
                'expected': {'protectedPart': 2, 'namedParts': {name: 5 + i for i, name in enumerate(NAMED)}}}
    (output / 'manifest.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', type=Path)
    print(create(parser.parse_args().output))
