#!/usr/bin/env python3
"""Validate the frozen R7 corpus without accepting or rewriting hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree


ZIP_MEDIA_TYPES = {
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
FORBIDDEN_SUFFIXES = (".bin", ".vba", ".xlsm", ".docm", ".pptm")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return not path.is_absolute() and value == path.name and ".." not in path.parts


def inspect_zip(path: Path, kind: str, limits: dict[str, int]) -> dict[str, Any]:
    result: dict[str, Any] = {"isZip": zipfile.is_zipfile(path)}
    if not result["isZip"]:
        return result
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        uncompressed = sum(info.file_size for info in infos)
        compressed = sum(max(info.compress_size, 1) for info in infos)
        ratio = uncompressed / compressed if compressed else float("inf")
        crc_error = archive.testzip()
        forbidden = [name for name in names if name.lower().endswith(FORBIDDEN_SUFFIXES)]
        external_relationships: list[str] = []
        xml_errors: list[dict[str, str]] = []
        for info in infos:
            lower = info.filename.lower()
            if lower.endswith((".xml", ".rels")):
                try:
                    root = ElementTree.fromstring(archive.read(info))
                    if lower.endswith(".rels"):
                        for relationship in root:
                            if relationship.attrib.get("TargetMode") == "External":
                                external_relationships.append(
                                    relationship.attrib.get("Target", "")
                                )
                except (ElementTree.ParseError, KeyError) as error:
                    xml_errors.append({"entry": info.filename, "error": str(error)})
        format_ok = True
        if kind == "odt":
            format_ok = "mimetype" in names and archive.read("mimetype") == b"application/vnd.oasis.opendocument.text"
        elif kind == "docx":
            format_ok = "[Content_Types].xml" in names and "word/document.xml" in names
        result.update(
            {
                "entryCount": len(infos),
                "uncompressedBytes": uncompressed,
                "compressionRatio": ratio,
                "crcErrorEntry": crc_error,
                "xmlErrors": xml_errors,
                "formatStructurePass": format_ok,
                "forbiddenEntries": forbidden,
                "externalRelationships": external_relationships,
                "limitsPass": len(infos) <= limits["maxZipEntries"]
                and uncompressed <= limits["maxUncompressedBytes"]
                and ratio <= limits["maxCompressionRatio"],
            }
        )
    return result


def validate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    limits = manifest.get("limits", {})
    required_limits = {
        "maxFileBytes", "maxZipEntries", "maxUncompressedBytes", "maxCompressionRatio"
    }
    schema_errors: list[str] = []
    if manifest.get("schemaVersion") != 1:
        schema_errors.append("schemaVersion must equal 1")
    if not required_limits.issubset(limits):
        schema_errors.append("limits are incomplete")
    documents = manifest.get("documents")
    if not isinstance(documents, list) or not documents:
        schema_errors.append("documents must be a non-empty array")
        documents = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    items: list[dict[str, Any]] = []
    expected_results = {"pass", "discover", "typed-failure"}
    for entry in documents:
        errors: list[str] = []
        identifier = entry.get("id")
        relative = entry.get("path", "")
        if not identifier or identifier in seen_ids:
            errors.append("id must be non-empty and unique")
        if not safe_relative_path(relative) or relative in seen_paths:
            errors.append("path must be a unique basename")
        seen_ids.add(identifier)
        seen_paths.add(relative)
        if entry.get("expectedOpen") not in expected_results:
            errors.append("expectedOpen is invalid")
        source = entry.get("source", {})
        if not source.get("path") or not source.get("license"):
            errors.append("source path and license are required")
        if entry.get("mutationPolicy") != "discovery-copy-only":
            errors.append("mutationPolicy must be discovery-copy-only")
        if not entry.get("pageClass"):
            errors.append("pageClass is required")
        path = manifest_path.parent / relative
        exists = path.is_file()
        actual_bytes = path.stat().st_size if exists else None
        actual_hash = sha256(path) if exists else None
        if not exists:
            errors.append("file is missing")
        elif actual_bytes != entry.get("bytes") or actual_hash != entry.get("sha256"):
            errors.append("exact bytes or SHA-256 mismatch")
        if exists and actual_bytes is not None and actual_bytes > limits.get("maxFileBytes", 0):
            errors.append("file exceeds maxFileBytes")

        parent = entry.get("parent")
        if parent:
            parent_path = manifest_path.parent / parent.get("path", "")
            if not entry.get("derivation"):
                errors.append("derived negative must provide a derivation recipe")
            if not parent_path.is_file() or sha256(parent_path) != parent.get("sha256"):
                errors.append("derived negative parent hash mismatch")

        media_type = entry.get("mediaType")
        archive = inspect_zip(path, ZIP_MEDIA_TYPES[media_type], limits) if exists and media_type in ZIP_MEDIA_TYPES else {"isZip": False}
        if entry.get("expectedOpen") in {"pass", "discover"} and media_type in ZIP_MEDIA_TYPES:
            if not archive.get("isZip"):
                errors.append("positive Office fixture is not a ZIP")
            else:
                if archive.get("crcErrorEntry"):
                    errors.append("ZIP CRC failed")
                if archive.get("xmlErrors"):
                    errors.append("XML parse failed")
                if not archive.get("formatStructurePass"):
                    errors.append("format-specific structure failed")
                if not archive.get("limitsPass"):
                    errors.append("ZIP limits failed")
                if archive.get("forbiddenEntries"):
                    errors.append("macro or forbidden binary entry found")
                if archive.get("externalRelationships"):
                    errors.append("external relationship found")
        items.append(
            {
                "id": identifier,
                "path": relative,
                "expectedOpen": entry.get("expectedOpen"),
                "exists": exists,
                "bytes": actual_bytes,
                "sha256": actual_hash,
                "archive": archive,
                "errors": errors,
                "pass": not errors,
            }
        )

    return {
        "schemaVersion": 1,
        "manifest": str(manifest_path.resolve()),
        "manifestSha256": sha256(manifest_path),
        "schemaErrors": schema_errors,
        "documents": items,
        "pass": not schema_errors and bool(items) and all(item["pass"] for item in items),
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=project / "test-docs" / "r7" / "manifest.json")
    parser.add_argument("--output", type=Path, default=project.parent / "findings" / "evidence" / "sdk-r7" / "corpus" / "manifest-validation.json")
    args = parser.parse_args()

    result = validate_manifest(args.manifest.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "pass": result["pass"]}, ensure_ascii=False))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
