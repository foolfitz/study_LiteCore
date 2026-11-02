#!/usr/bin/env python3
"""SPEC-P-demo-batch-1 section 2: a three-sheet ODS for the per-sheet view.

Sheet 1 is tall and wide, sheet 2 is tall, sheet 3 is three screens shorter than
either.  The short sheet is the point: a page that scrolls before it has grown
the surface back clamps the restored position, and only a sheet shorter than the
one being restored can show that.
"""
import argparse
import json
import zipfile
from pathlib import Path

NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
      'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"')
SHEETS = (("表一", 300, 30), ("表二", 200, 6), ("表三", 8, 4))


def cell(text):
    return ('<table:table-cell office:value-type="string"><text:p>'
            f"{text}</text:p></table:table-cell>")


def sheet(index, name, rows, columns):
    body = "".join(
        "<table:table-row>"
        + "".join(cell(f"S{index + 1}-R{row + 1}-C{column + 1}") for column in range(columns))
        + "</table:table-row>"
        for row in range(rows))
    return f'<table:table table:name="{name}">{body}</table:table>'


def create(output):
    output.mkdir(parents=True, exist_ok=True)
    tables = "".join(sheet(i, *spec) for i, spec in enumerate(SHEETS))
    content = (f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {NS} '
               f'office:version="1.3"><office:body><office:spreadsheet>{tables}'
               "</office:spreadsheet></office:body></office:document-content>")
    manifest = ('<?xml version="1.0"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:'
                'opendocument:xmlns:manifest:1.0" manifest:version="1.3">'
                '<manifest:file-entry manifest:full-path="/" manifest:media-type="application/'
                'vnd.oasis.opendocument.spreadsheet"/><manifest:file-entry manifest:full-path='
                '"content.xml" manifest:media-type="text/xml"/></manifest:manifest>')
    path = output / "sheet-view.ods"
    with zipfile.ZipFile(path, "w") as archive:
        for name, body in (("mimetype", "application/vnd.oasis.opendocument.spreadsheet"),
                           ("content.xml", content), ("META-INF/manifest.xml", manifest)):
            archive.writestr(zipfile.ZipInfo(name, (2026, 11, 2, 0, 0, 0)), body.encode())
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    print(json.dumps({"fixture": str(create(parser.parse_args().out))}))
