#!/usr/bin/env python3
"""Create the deterministic ODT-first E1 editing discovery corpus."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

from e1_support import sha256, write_json


MIMETYPE = "application/vnd.oasis.opendocument.text"
ZIP_TIME = (2026, 8, 4, 0, 0, 0)
NAMESPACES = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
    'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
    'office:version="1.3"'
)


def xml_document(body: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content {NAMESPACES}>
 <office:automatic-styles>
  <style:style style:name="E1Bold" style:family="text"><style:text-properties fo:font-weight="bold"/></style:style>
  <style:style style:name="E1Italic" style:family="text"><style:text-properties fo:font-style="italic"/></style:style>
 </office:automatic-styles>
 <office:body><office:text>{body}</office:text></office:body>
</office:document-content>
'''


STYLES_XML = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles {NAMESPACES}>
 <office:styles>
  <style:default-style style:family="paragraph"><style:paragraph-properties fo:margin-top="0cm" fo:margin-bottom="0.2cm"/></style:default-style>
  <style:style style:name="Heading_20_1" style:display-name="Heading 1" style:family="paragraph"><style:text-properties fo:font-size="18pt" fo:font-weight="bold"/></style:style>
 </office:styles>
</office:document-styles>
'''

MANIFEST_XML = f'''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="{MIMETYPE}" manifest:version="1.3"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
'''


FIXTURES = {
    "plain-grapheme": {
        "body": """
 <text:p>E1-PLAIN-START</text:p>
 <text:p>ASCII abc XYZ 0123456789</text:p>
 <text:p>臺灣中文游標測試</text:p>
 <text:p>emoji 😀 grapheme</text:p>
 <text:p>combining é boundary</text:p>
 <text:p>E1-PLAIN-END</text:p>
""",
        "anchors": ["E1-PLAIN-START", "臺灣中文游標測試", "emoji 😀 grapheme", "combining é boundary", "E1-PLAIN-END"],
        "minimum": {"paragraphs": 6, "headings": 0, "lists": 0, "tables": 0},
    },
    "multi-paragraph": {
        "body": """
 <text:p>E1-MULTI-START alpha</text:p>
 <text:p>第二段中文 beta</text:p>
 <text:p>第三段跨行 gamma</text:p>
 <text:p>第四段落 delta</text:p>
 <text:p>E1-MULTI-END omega</text:p>
""",
        "anchors": ["E1-MULTI-START alpha", "第二段中文 beta", "E1-MULTI-END omega"],
        "minimum": {"paragraphs": 5, "headings": 0, "lists": 0, "tables": 0},
    },
    "styled-list": {
        "body": """
 <text:h text:outline-level="1" text:style-name="Heading_20_1">E1-STYLED-HEADING</text:h>
 <text:p>Normal <text:span text:style-name="E1Bold">bold anchor</text:span> and <text:span text:style-name="E1Italic">italic anchor</text:span>.</text:p>
 <text:list><text:list-item><text:p>E1-LIST-ONE</text:p></text:list-item><text:list-item><text:p>E1-LIST-TWO</text:p></text:list-item></text:list>
 <text:p>E1-STYLED-END</text:p>
""",
        "anchors": ["E1-STYLED-HEADING", "bold anchor", "italic anchor", "E1-LIST-ONE", "E1-STYLED-END"],
        "minimum": {"paragraphs": 4, "headings": 1, "lists": 1, "tables": 0},
    },
    "table-boundary": {
        "body": """
 <text:p>E1-TABLE-BEFORE</text:p>
 <table:table table:name="E1Table">
  <table:table-column table:number-columns-repeated="2"/>
  <table:table-row><table:table-cell><text:p>E1-CELL-A1</text:p></table:table-cell><table:table-cell><text:p>E1-CELL-B1</text:p></table:table-cell></table:table-row>
  <table:table-row><table:table-cell><text:p>E1-CELL-A2</text:p></table:table-cell><table:table-cell><text:p>E1-CELL-B2</text:p></table:table-cell></table:table-row>
 </table:table>
 <text:p>E1-TABLE-AFTER</text:p>
""",
        "anchors": ["E1-TABLE-BEFORE", "E1-CELL-A1", "E1-CELL-B2", "E1-TABLE-AFTER"],
        "minimum": {"paragraphs": 6, "headings": 0, "lists": 0, "tables": 1},
    },
}


def write_member(archive: zipfile.ZipFile, name: str, data: bytes, compress: int) -> None:
    info = zipfile.ZipInfo(name, ZIP_TIME)
    info.compress_type = compress
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def create_odt(path: Path, body: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        write_member(archive, "mimetype", MIMETYPE.encode(), zipfile.ZIP_STORED)
        write_member(archive, "content.xml", xml_document(body).encode(), zipfile.ZIP_DEFLATED)
        write_member(archive, "styles.xml", STYLES_XML.encode(), zipfile.ZIP_DEFLATED)
        write_member(archive, "META-INF/manifest.xml", MANIFEST_XML.encode(), zipfile.ZIP_DEFLATED)


def frozen_valid(manifest_path: Path) -> bool:
    if not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for fixture in manifest.get("fixtures", []):
        path = manifest_path.parent / fixture["path"]
        if not path.is_file() or path.stat().st_size != fixture["bytes"] or sha256(path) != fixture["sha256"]:
            return False
    return bool(manifest.get("fixtures"))


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=project / "test-docs" / "e1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    manifest_path = output / "manifest.json"
    if not args.force and frozen_valid(manifest_path):
        print(json.dumps({"manifest": str(manifest_path), "status": "frozen-valid"}))
        return
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for identifier, definition in FIXTURES.items():
        path = output / f"{identifier}.odt"
        create_odt(path, definition["body"])
        entries.append({
            "id": identifier,
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "anchors": definition["anchors"],
            "minimum": definition["minimum"],
            "source": "project-generated deterministic ODT",
        })
    source = project / "test-docs" / "t2-styled.odt"
    copied = output / "r7-t2-styled.odt"
    shutil.copyfile(source, copied)
    entries.append({
        "id": "r7-t2-styled",
        "path": copied.name,
        "bytes": copied.stat().st_size,
        "sha256": sha256(copied),
        "anchors": ["R1 樣式文件", "文件結尾：請確認表格、圖片、註解與標題樣式均保留。"],
        "minimum": {"paragraphs": 1, "headings": 1, "lists": 0, "tables": 1},
        "source": "wasm_sdk_probe/test-docs/t2-styled.odt exact copy",
    })
    write_json(manifest_path, {
        "schemaVersion": 1,
        "release": "E1-A-editing-discovery",
        "frozenDate": "2026-08-04",
        "mutationPolicy": "copy-only",
        "fixtures": entries,
    })
    print(json.dumps({"manifest": str(manifest_path), "fixtures": len(entries)}))


if __name__ == "__main__":
    main()

