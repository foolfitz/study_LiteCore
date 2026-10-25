#!/usr/bin/env python3
"""Create the cell editor's deterministic two-sheet and protection fixture."""
import argparse
import json
import zipfile
from pathlib import Path

NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
      'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
      'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
      'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
      'xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2"')


def create(output):
    output.mkdir(parents=True, exist_ok=True)
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content {NS} office:version="1.3">
<office:automatic-styles>
<style:style style:name="wide" style:family="table-column"><style:table-column-properties style:column-width="3cm"/></style:style>
<style:style style:name="narrow" style:family="table-column"><style:table-column-properties style:column-width="1.8cm"/></style:style>
<style:style style:name="tall" style:family="table-row"><style:table-row-properties style:row-height="1cm"/></style:style>
<style:style style:name="short" style:family="table-row"><style:table-row-properties style:row-height="0.5cm"/></style:style>
<style:style style:name="unlocked" style:family="table-cell"><style:table-cell-properties style:cell-protect="none"/></style:style>
</office:automatic-styles><office:body><office:spreadsheet>
<table:table table:name="編輯測試">
<table:table-column table:style-name="wide"/><table:table-column table:style-name="narrow"/>
<table:table-column table:style-name="wide"/><table:table-column table:visibility="collapse"/><table:table-column table:style-name="wide"/>
<table:table-row table:style-name="short"><table:table-cell office:value-type="string"><text:p>原始中文 Alpha</text:p></table:table-cell><table:table-cell office:value-type="float" office:value="42"><text:p>42</text:p></table:table-cell><table:table-cell table:formula="of:=[.B1]*2" office:value-type="float" office:value="84"><text:p>84</text:p></table:table-cell><table:table-cell/><table:table-cell office:value-type="string"><text:p>隱藏欄之後</text:p></table:table-cell></table:table-row>
<table:table-row table:style-name="tall"><table:table-cell office:value-type="string"><text:p>鄰格必須保留</text:p></table:table-cell><table:table-cell office:value-type="string"><text:p>格式測試</text:p></table:table-cell><table:table-cell office:value-type="string"><text:p>待清除</text:p></table:table-cell></table:table-row>
<table:table-row table:style-name="short"><table:table-cell table:number-columns-spanned="2" office:value-type="string"><text:p>合併格</text:p></table:table-cell><table:covered-table-cell/><table:table-cell office:value-type="string"><text:p>合併格右邊</text:p></table:table-cell></table:table-row>
<table:table-row table:visibility="collapse"><table:table-cell office:value-type="string"><text:p>隱藏列</text:p></table:table-cell></table:table-row>
<table:table-row><table:table-cell office:value-type="string"><text:p>隱藏列之後</text:p></table:table-cell></table:table-row>
</table:table>
<table:table table:name="另一張表"><table:table-column table:style-name="wide"/><table:table-row><table:table-cell office:value-type="string"><text:p>第二表不應改動</text:p></table:table-cell></table:table-row></table:table>
<table:table table:name="保護測試" table:protected="true"><table:table-row><table:table-cell office:value-type="string"><text:p>鎖定內容</text:p></table:table-cell><table:table-cell table:style-name="unlocked" office:value-type="string"><text:p>可編輯</text:p></table:table-cell></table:table-row></table:table>
</office:spreadsheet></office:body></office:document-content>'''
    manifest_xml = '''<?xml version="1.0"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/></manifest:manifest>'''
    path = output / "cell-editing.ods"
    with zipfile.ZipFile(path, "w") as z:
        for name, body in (("mimetype", "application/vnd.oasis.opendocument.spreadsheet"),
                           ("content.xml", content), ("META-INF/manifest.xml", manifest_xml)):
            info = zipfile.ZipInfo(name, (2026, 10, 25, 0, 0, 0))
            z.writestr(info, body.encode())
    cases = [
        {"id": "text", "column": 0, "row": 0, "input": "編輯完成 Alpha"},
        {"id": "number", "column": 1, "row": 0, "input": "21"},
        {"id": "formula", "column": 2, "row": 0, "input": "=B1*3"},
        {"id": "clear", "column": 2, "row": 1, "input": ""},
        {"id": "multiline", "column": 4, "row": 1, "input": "第一行\n第二行 \"引號\""},
        {"id": "literal", "column": 5, "row": 1, "input": "'=B1*9"},
        {"id": "merged", "column": 1, "row": 2, "input": "合併格已修改"},
    ]
    metadata = {"file": path.name, "sheets": ["編輯測試", "另一張表", "保護測試"],
                "cases": cases, "formats": ["bold", "italic", "underline"],
                "preserved": [{"part": 0, "column": 0, "row": 1, "formula": "鄰格必須保留"},
                              {"part": 1, "column": 0, "row": 0, "formula": "第二表不應改動"}],
                "geometry": [{"column": c, "row": r} for c, r in
                             [(0, 0), (1, 0), (2, 0), (4, 0), (1, 1), (1, 2), (0, 4)]]}
    (output / "manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=Path)
    print(create(ap.parse_args().output))
