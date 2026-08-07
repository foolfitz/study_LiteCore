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

