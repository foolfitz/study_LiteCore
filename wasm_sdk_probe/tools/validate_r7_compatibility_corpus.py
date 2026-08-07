#!/usr/bin/env python3
"""Validate the frozen R7-C corpus and its typed ODT-first policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree


ZIP_MEDIA = {
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
TYPED_CODES = {
    "UNSUPPORTED_FORMAT", "CORRUPT_DOCUMENT", "DOCUMENT_TOO_LARGE",
    "DOCUMENT_OPEN_FAILED", "DOCUMENT_OPEN_TIMEOUT",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_archive(path: Path, kind: str, limits: dict[str, int]) -> dict[str, Any]:
    result: dict[str, Any] = {"isZip": zipfile.is_zipfile(path)}
    if not result["isZip"]:
        return result
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            uncompressed = sum(item.file_size for item in infos)
            compressed = sum(max(1, item.compress_size) for item in infos)
            ratio = uncompressed / max(1, compressed)
            xml_errors = []
            external = []
            for item in infos:
                if item.filename.lower().endswith((".xml", ".rels")):
                    try:
                        root = ElementTree.fromstring(archive.read(item))
                        if item.filename.lower().endswith(".rels"):
                            external.extend(
                                child.attrib.get("Target", "") for child in root
                                if child.attrib.get("TargetMode") == "External"
                            )
                    except (ElementTree.ParseError, KeyError) as error:
                        xml_errors.append({"entry": item.filename, "error": str(error)})
            structure = (
                "mimetype" in names and "content.xml" in names
                if kind == "odt"
                else "[Content_Types].xml" in names and "word/document.xml" in names
            )
            result.update({
                "entryCount": len(infos),
                "uncompressedBytes": uncompressed,
                "compressionRatio": ratio,
                "crcErrorEntry": archive.testzip(),
                "xmlErrors": xml_errors,
                "externalRelationships": external,
                "structurePass": structure,
                "limitsPass": len(infos) <= limits["maxZipEntries"]
                and uncompressed <= limits["maxUncompressedBytes"]
                and ratio <= limits["maxCompressionRatio"],
                "macroEntries": [name for name in names if name.lower().endswith(("vbaProject.bin".lower(), ".docm"))],
            })
    except zipfile.BadZipFile as error:
        result["badZip"] = str(error)
    return result


def validate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    limits = manifest.get("limits", {})
    schema_errors = []
    if manifest.get("schemaVersion") != 2 or manifest.get("release") != "R7-C":
        schema_errors.append("manifest must be R7-C schemaVersion 2")
    if manifest.get("generator", {}).get("rawUnoUsed") is not False:
        schema_errors.append("generator must record rawUnoUsed=false")
    required_limits = {
        "maxFileBytes", "maxZipEntries", "maxUncompressedBytes", "maxCompressionRatio"
    }
    if not required_limits.issubset(limits):
        schema_errors.append("limits are incomplete")
    documents = manifest.get("documents", [])
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    results = []
    for item in documents:
        errors = []
        identifier = item.get("id")
        relative = item.get("path", "")
        path_value = PurePosixPath(relative)
        if not identifier or identifier in seen_ids:
            errors.append("id must be unique")
        if not relative or path_value.is_absolute() or relative != path_value.name or relative in seen_paths:
            errors.append("path must be a unique safe basename")
        seen_ids.add(identifier)
        seen_paths.add(relative)
        if item.get("tier") not in {"L0", "L1", "L2", "L3", "L4"}:
            errors.append("tier is invalid")
        source = item.get("source", {})
        if not source.get("kind") or not source.get("path") or source.get("license") != "MPL-2.0":
            errors.append("source provenance is incomplete")
        if source.get("kind") == "libreoffice-qa" and not source.get("coreCommit"):
            errors.append("LibreOffice QA source requires coreCommit")
        expected = item.get("expected", {})
        if expected.get("open") not in {"pass", "typed-failure"}:
            errors.append("expected.open is invalid")
        if expected.get("open") == "typed-failure" and expected.get("typedCode") not in TYPED_CODES:
            errors.append("typed failure requires a supported typedCode")
        if item.get("mediaType") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            if expected.get("open") != "typed-failure" or expected.get("typedCode") != "UNSUPPORTED_FORMAT":
                errors.append("DOCX must stay typed unsupported under finding 013")
        anchors = item.get("anchors")
        if not isinstance(anchors, list):
            errors.append("anchors must be an array")
        else:
            for anchor in anchors:
                if not anchor.get("text") or not isinstance(anchor.get("count"), int) or anchor["count"] < 1:
                    errors.append("anchor text/count is invalid")
        path = manifest_path.parent / relative
        exists = path.is_file()
        actual_bytes = path.stat().st_size if exists else None
        actual_hash = sha256(path) if exists else None
        if not exists:
            errors.append("file is missing")
        elif actual_bytes != item.get("bytes") or actual_hash != item.get("sha256"):
            errors.append("exact bytes or SHA-256 mismatch")
        parent = item.get("parent")
        if parent:
            parent_path = manifest_path.parent / parent.get("path", "")
            if not item.get("derivation"):
                errors.append("derived item requires a recipe")
            if not parent_path.is_file() or sha256(parent_path) != parent.get("sha256"):
                errors.append("derived parent hash mismatch")
        media_type = item.get("mediaType")
        archive = inspect_archive(path, ZIP_MEDIA[media_type], limits) if exists and media_type in ZIP_MEDIA else {"isZip": False}
        if expected.get("open") == "pass":
            if actual_bytes and actual_bytes > limits["maxFileBytes"]:
                errors.append("positive fixture exceeds compressed limit")
            if media_type not in ZIP_MEDIA or not archive.get("isZip"):
                errors.append("positive Office fixture is not a ZIP")
            elif not all((
                archive.get("crcErrorEntry") is None,
                not archive.get("xmlErrors"),
                archive.get("structurePass") is True,
                archive.get("limitsPass") is True,
                not archive.get("macroEntries"),
                not archive.get("externalRelationships"),
            )):
                errors.append("positive Office fixture failed package safety")
        results.append({
            "id": identifier,
            "tier": item.get("tier"),
            "path": relative,
            "exists": exists,
            "bytes": actual_bytes,
            "sha256": actual_hash,
            "expected": expected,
            "archive": archive,
            "errors": errors,
            "pass": not errors,
        })

    by_tier = {tier: sum(item.get("tier") == tier for item in documents) for tier in ("L0", "L1", "L2", "L3", "L4")}
    features = {feature for item in documents for feature in item.get("features", [])}
    requirements = {
        "tierCoverage": all(by_tier[tier] > 0 for tier in by_tier),
        "l0Count": by_tier["L0"] == 3,
        "l1Pairs": all(
            any(item.get("path") == f"l1-{stem}.odt" for item in documents)
            and any(item.get("path") == f"l1-{stem}.docx" for item in documents)
            for stem in ("plain", "layout-table-image", "review", "hyperlink-font")
        ),
        "qaAllowlist": by_tier["L2"] == 6,
        "negativeCoverage": by_tier["L3"] >= 10,
        "stress100": any(
            item.get("tier") == "L4" and item.get("expected", {}).get("pageCount") == 100
            for item in documents
        ),
        "featureCoverage": {"table", "image", "comments", "tracked-changes", "hyperlink", "missing-font"}.issubset(features),
    }
    return {
        "schemaVersion": 1,
        "release": "R7-C-corpus-validation",
        "manifest": str(manifest_path.resolve()),
        "manifestSha256": sha256(manifest_path),
        "schemaErrors": schema_errors,
        "tierCounts": by_tier,
        "requirements": requirements,
        "documents": results,
        "pass": not schema_errors and bool(results)
        and all(requirements.values()) and all(item["pass"] for item in results),
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=project / "test-docs" / "r7-compat" / "manifest.json")
    parser.add_argument(
        "--output", type=Path,
        default=project.parent / "findings" / "evidence" / "sdk-r7" / "corpus" / "compatibility-manifest-validation.json",
    )
    args = parser.parse_args()
    result = validate_manifest(args.manifest.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "documents": len(result["documents"]), "pass": result["pass"]}, ensure_ascii=False))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

