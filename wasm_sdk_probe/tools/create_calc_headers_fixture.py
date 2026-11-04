#!/usr/bin/env python3
"""The fixture of specs/SPEC-P-calc-headers.md section 6: cell-editing.ods's three sheets (create_calc_edit_fixture.py, not
edited) with two cells added on the first sheet -- AA1 (a column label past Z, from the engine) and A1000 (row 1000, far below
the view) -- and the column definitions extended to AA.

  create_calc_headers_fixture.py OUTPUT_DIR      writes calc-headers.ods and manifest.json
"""
import argparse
import json
import zipfile
from pathlib import Path

from create_calc_edit_fixture import NS

FIRST_SHEET = '''<table:table table:name="編輯測試">
<table:table-column table:style-name="wide"/><table:table-column table:style-name="narrow"/>
<table:table-column table:style-name="wide"/><table:table-column table:visibility="collapse"/><table:table-column table:style-name="wide"/>
<table:table-column table:number-columns-repeated="22"/>
<table:table-row table:style-name="short"><table:table-cell office:value-type="string"><text:p>原始中文 Alpha</text:p></table:table-cell><table:table-cell office:value-type="float" office:value="42"><text:p>42</text:p></table:table-cell><table:table-cell table:formula="of:=[.B1]*2" office:value-type="float" office:value="84"><text:p>84</text:p></table:table-cell><table:table-cell/><table:table-cell office:value-type="string"><text:p>隱藏欄之後</text:p></table:table-cell><table:table-cell table:number-columns-repeated="21"/><table:table-cell office:value-type="string"><text:p>AA 欄</text:p></table:table-cell></table:table-row>
<table:table-row table:style-name="tall"><table:table-cell office:value-type="string"><text:p>鄰格必須保留</text:p></table:table-cell><table:table-cell office:value-type="string"><text:p>格式測試</text:p></table:table-cell><table:table-cell office:value-type="string"><text:p>待清除</text:p></table:table-cell></table:table-row>
<table:table-row table:style-name="short"><table:table-cell table:number-columns-spanned="2" office:value-type="string"><text:p>合併格</text:p></table:table-cell><table:covered-table-cell/><table:table-cell office:value-type="string"><text:p>合併格右邊</text:p></table:table-cell></table:table-row>
<table:table-row table:visibility="collapse"><table:table-cell office:value-type="string"><text:p>隱藏列</text:p></table:table-cell></table:table-row>
<table:table-row><table:table-cell office:value-type="string"><text:p>隱藏列之後</text:p></table:table-cell></table:table-row>
<table:table-row table:number-rows-repeated="994"><table:table-cell/></table:table-row>
<table:table-row><table:table-cell office:value-type="string"><text:p>第 1000 列</text:p></table:table-cell></table:table-row>
</table:table>'''

STYLES = '''<office:automatic-styles>
<style:style style:name="wide" style:family="table-column"><style:table-column-properties style:column-width="3cm"/></style:style>
<style:style style:name="narrow" style:family="table-column"><style:table-column-properties style:column-width="1.8cm"/></style:style>
<style:style style:name="tall" style:family="table-row"><style:table-row-properties style:row-height="1cm"/></style:style>
<style:style style:name="short" style:family="table-row"><style:table-row-properties style:row-height="0.5cm"/></style:style>
<style:style style:name="unlocked" style:family="table-cell"><style:table-cell-properties style:cell-protect="none"/></style:style>
</office:automatic-styles>'''

OTHER_SHEETS = '''<table:table table:name="另一張表"><table:table-column table:style-name="wide"/><table:table-row><table:table-cell office:value-type="string"><text:p>第二表不應改動</text:p></table:table-cell></table:table-row></table:table>
<table:table table:name="保護測試" table:protected="true"><table:table-row><table:table-cell office:value-type="string"><text:p>鎖定內容</text:p></table:table-cell><table:table-cell table:style-name="unlocked" office:value-type="string"><text:p>可編輯</text:p></table:table-cell></table:table-row></table:table>'''


def create(output):
    output.mkdir(parents=True, exist_ok=True)
    content = (f'<?xml version="1.0" encoding="UTF-8"?>\n<office:document-content {NS} office:version="1.3">\n{STYLES}'
               f'<office:body><office:spreadsheet>\n{FIRST_SHEET}\n{OTHER_SHEETS}\n</office:spreadsheet></office:body></office:document-content>')
    manifest_xml = ('<?xml version="1.0"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
                    'manifest:version="1.3"><manifest:file-entry manifest:full-path="/" '
                    'manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/><manifest:file-entry '
                    'manifest:full-path="content.xml" manifest:media-type="text/xml"/></manifest:manifest>')
    path = output / 'calc-headers.ods'
    with zipfile.ZipFile(path, 'w') as z:
        for name, body in (('mimetype', 'application/vnd.oasis.opendocument.spreadsheet'),
                           ('content.xml', content), ('META-INF/manifest.xml', manifest_xml)):
            z.writestr(zipfile.ZipInfo(name, (2026, 11, 5, 0, 0, 0)), body.encode())
    metadata = {'file': path.name, 'sheets': ['編輯測試', '另一張表', '保護測試'],
                'expected': {'hiddenColumns': [3], 'hiddenRows': [3], 'merged': {'column': 0, 'row': 2, 'endColumn': 1, 'endRow': 2},
                             'cells': [{'column': 26, 'row': 0, 'text': 'AA 欄'}, {'column': 0, 'row': 999, 'text': '第 1000 列'},
                                       {'column': 4, 'row': 0, 'text': '隱藏欄之後'}, {'column': 0, 'row': 4, 'text': '隱藏列之後'}],
                             'protectedPart': 2}}
    (output / 'manifest.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', type=Path)
    print(create(parser.parse_args().output))
