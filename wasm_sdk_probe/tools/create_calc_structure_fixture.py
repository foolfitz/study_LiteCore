#!/usr/bin/env python3
"""The fixture of specs/SPEC-P-calc-structure.md section 6: calc-headers.ods's three sheets (create_calc_headers_fixture.py, not
edited) and two more -- 邊界測試 (text at A1048576 and XFD1: nothing can be inserted) and 陣列測試 (one array formula over B2:C3,
=E2:F3*2, with 1..4 in E2:F3).

  create_calc_structure_fixture.py OUTPUT_DIR      writes calc-structure.ods and manifest.json
"""
import argparse
import json
import zipfile
from pathlib import Path

from create_calc_edit_fixture import NS
from create_calc_headers_fixture import FIRST_SHEET, OTHER_SHEETS, STYLES

EDGE_SHEET = '''<table:table table:name="邊界測試"><table:table-column table:number-columns-repeated="16384"/>
<table:table-row><table:table-cell office:value-type="string"><text:p>邊界</text:p></table:table-cell><table:table-cell table:number-columns-repeated="16382"/><table:table-cell office:value-type="string"><text:p>最後一欄</text:p></table:table-cell></table:table-row>
<table:table-row table:number-rows-repeated="1048574"><table:table-cell table:number-columns-repeated="16384"/></table:table-row>
<table:table-row><table:table-cell office:value-type="string"><text:p>最後一列</text:p></table:table-cell></table:table-row>
</table:table>'''

FLOAT = '<table:table-cell office:value-type="float" office:value="{0}"><text:p>{0}</text:p></table:table-cell>'
ARRAY_SHEET = ('<table:table table:name="陣列測試"><table:table-column table:number-columns-repeated="6"/>'
               '<table:table-row><table:table-cell office:value-type="string"><text:p>陣列</text:p></table:table-cell></table:table-row>'
               '<table:table-row><table:table-cell/><table:table-cell table:number-matrix-columns-spanned="2" '
               'table:number-matrix-rows-spanned="2" table:formula="of:=[.E2:.F3]*2" office:value-type="float" office:value="2">'
               '<text:p>2</text:p></table:table-cell>' + FLOAT.format(4) + '<table:table-cell/>' + FLOAT.format(1) + FLOAT.format(2)
               + '</table:table-row><table:table-row><table:table-cell/>' + FLOAT.format(6) + FLOAT.format(8) + '<table:table-cell/>'
               + FLOAT.format(3) + FLOAT.format(4) + '</table:table-row></table:table>')


def create(output):
    output.mkdir(parents=True, exist_ok=True)
    content = (f'<?xml version="1.0" encoding="UTF-8"?>\n<office:document-content {NS} office:version="1.3">\n{STYLES}'
               f'<office:body><office:spreadsheet>\n{FIRST_SHEET}\n{OTHER_SHEETS}\n{EDGE_SHEET}\n{ARRAY_SHEET}\n'
               '</office:spreadsheet></office:body></office:document-content>')
    manifest_xml = ('<?xml version="1.0"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
                    'manifest:version="1.3"><manifest:file-entry manifest:full-path="/" '
                    'manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/><manifest:file-entry '
                    'manifest:full-path="content.xml" manifest:media-type="text/xml"/></manifest:manifest>')
    path = output / 'calc-structure.ods'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo('mimetype', (2026, 11, 5, 0, 0, 0)), b'application/vnd.oasis.opendocument.spreadsheet')
        for name, body in (('content.xml', content), ('META-INF/manifest.xml', manifest_xml)):
            info = zipfile.ZipInfo(name, (2026, 11, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, body.encode())
    metadata = {'file': path.name, 'sheets': ['編輯測試', '另一張表', '保護測試', '邊界測試', '陣列測試'],
                'expected': {'protectedPart': 2, 'edgePart': 3, 'arrayPart': 4,
                             'edgeCells': [{'column': 0, 'row': 1048575, 'text': '最後一列'},
                                           {'column': 16383, 'row': 0, 'text': '最後一欄'}],
                             'array': {'column': 1, 'row': 1, 'endColumn': 2, 'endRow': 2, 'values': [[2, 4], [6, 8]]}}}
    (output / 'manifest.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', type=Path)
    print(create(parser.parse_args().output))
