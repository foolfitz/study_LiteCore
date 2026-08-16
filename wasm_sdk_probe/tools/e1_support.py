#!/usr/bin/env python3
"""Shared deterministic helpers for E1 corpus and evidence validation."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


SHELL_BUNDLE_DIVERGENCE = Path("e1/editor-shell-bundle-v1-divergence.json")


def declared_divergences(project: Path) -> dict[str, dict[str, Any]]:
    """What deliberate changes to E1-C's bound shell files have been declared.

    One rule, one place.  `check_e1_c_bundle_intact.py` had this inline first;
    it lives here now because three other callers need the SAME answer, and a
    second copy of "is this change declared" is a second place for the answer
    to drift.  The file itself is the record: path, the hash the verdict bound,
    the hash it now has, why it moved, and what that costs.
    """
    path = project / SHELL_BUNDLE_DIVERGENCE
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    # A RESOLVED declaration relaxes nothing.  On 2026-08-16 the binding was
    # repaired by rebinding (e1/editor-shell-bundle-v2.json), so the four
    # entries below stopped being differences and became history -- and a
    # declaration that keeps tolerating its paths after the thing it described
    # is over is an exemption, which is the failure mode the file was written
    # to avoid.  The file itself is kept: SPEC E1-C 11.8's argument turns on
    # the difference between an expired binding and a misplaced one.
    if data.get("resolved"):
        return {}
    return {str(item["path"]): item for item in data.get("diverged", [])}


def classify_divergence(path: str, actual: str | None, expected: str,
                        declared: dict[str, dict[str, Any]]) -> str:
    """`match` | `declared` | `drifted` | `undeclared`.

    `drifted` is the case a naive "is it in the file" check would wave through:
    a declared file that has moved AGAIN now has a declaration describing a
    version that no longer exists either, so it is exactly as unaccounted for
    as an undeclared change.  It is a separate word because the fix differs --
    update the declaration, versus write one.
    """
    if actual == expected:
        return "match"
    note = declared.get(path)
    if note is None:
        return "undeclared"
    return "declared" if actual == note.get("nowSha256") else "drifted"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def inspect_odt(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "zip": False,
        "crc": False,
        "xml": False,
        "text": "",
        "paragraphs": 0,
        "headings": 0,
        "lists": 0,
        "tables": 0,
    }
    if not path.is_file() or not zipfile.is_zipfile(path):
        return result
    result["zip"] = True
    try:
        with zipfile.ZipFile(path) as archive:
            result["crc"] = archive.testzip() is None
            roots: dict[str, ElementTree.Element] = {}
            for name in archive.namelist():
                if name.endswith(".xml"):
                    roots[name] = ElementTree.fromstring(archive.read(name))
            result["xml"] = True
            content = roots["content.xml"]
        result["text"] = "".join(content.itertext())
        result["paragraphs"] = sum(node.tag.endswith("}p") for node in content.iter())
        result["headings"] = sum(node.tag.endswith("}h") for node in content.iter())
        result["lists"] = sum(node.tag.endswith("}list") for node in content.iter())
        result["tables"] = sum(node.tag.endswith("}table") for node in content.iter())
    except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as error:
        result["error"] = {"name": type(error).__name__, "message": str(error)}
    return result

