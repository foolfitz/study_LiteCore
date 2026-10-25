#!/usr/bin/env python3
"""Deterministic selection cases; the browser reader consumes this population."""
import json
from pathlib import Path
import zipfile

from create_calc_edit_fixture import create as base_create


def create(output):
    path = base_create(output)
    with zipfile.ZipFile(path) as z:
        entries = {n: z.read(n) for n in z.namelist()}
    text = entries["content.xml"].decode()
    text = text.replace('<table:table-column table:visibility="collapse"/>',
                        '<table:table-column table:visibility="collapse" table:number-columns-repeated="3"/>')
    text = text.replace('<table:table-row table:visibility="collapse">',
                        '<table:table-row table:visibility="collapse" table:number-rows-repeated="3">')
    entries["content.xml"] = text.encode()
    with zipfile.ZipFile(path, "w") as z:
        for name, data in entries.items():
            z.writestr(zipfile.ZipInfo(name, (2026, 10, 25, 0, 0, 0)), data)
    cases = [{"id": name, "from": start, "to": end} for name, start, end in [
        ("drag-SE", [0, 0], [2, 1]), ("drag-NW", [2, 1], [0, 0]),
        ("drag-NE", [0, 1], [2, 0]), ("drag-SW", [2, 0], [0, 1]),
        ("merged-endpoint", [2, 1], [1, 2]),
        ("interior-boundary-merge", [1, 1], [2, 6]),
        ("hidden-columns-rows", [2, 1], [6, 6]),
    ]]
    manifest = json.loads((output / "manifest.json").read_text())
    manifest["selectionCases"] = cases
    manifest["selectionPolicy"] = "endpoint-address-rectangle-without-recursive-merge-closure"
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return path
