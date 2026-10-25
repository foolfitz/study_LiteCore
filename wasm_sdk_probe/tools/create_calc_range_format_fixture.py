#!/usr/bin/env python3
"""Finite range-format population shared by native and browser probes."""
import json
from create_calc_edit_fixture import create as base_create

FORMATS = {"bold": 7, "italic": 8, "underline": 9}
CASES = [
    {"id": "ordinary", "part": 0, "bounds": [0, 0, 2, 1], "code": ""},
    {"id": "whole-merge", "part": 0, "bounds": [0, 2, 2, 2], "code": ""},
    {"id": "hidden-included", "part": 0, "bounds": [2, 0, 4, 4], "code": ""},
    {"id": "merge-boundary", "part": 0, "bounds": [1, 1, 2, 4], "code": "RANGE_MERGE_BOUNDARY"},
    {"id": "protected-mixed", "part": 2, "bounds": [0, 0, 1, 0], "code": "READ_ONLY"},
    {"id": "protected-unlocked", "part": 2, "bounds": [1, 0, 1, 0], "code": ""},
]


def create(output):
    path = base_create(output)
    manifest = json.loads((output / "manifest.json").read_text())
    manifest["rangeFormats"] = FORMATS
    manifest["rangeCases"] = CASES
    manifest["rangeCellLimit"] = 65536
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return path
