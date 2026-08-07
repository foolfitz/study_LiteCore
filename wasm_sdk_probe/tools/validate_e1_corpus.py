#!/usr/bin/env python3
"""Validate E1 fixture hashes, ODT structure, XML and required anchors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from e1_support import inspect_odt, sha256, write_json


def validate(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = []
    for fixture in manifest.get("fixtures", []):
        path = manifest_path.parent / fixture["path"]
        inspected = inspect_odt(path)
        anchors = [
            {"text": anchor, "found": anchor in inspected["text"]}
            for anchor in fixture.get("anchors", [])
        ]
        minimum = fixture.get("minimum", {})
        structure = {
            key: {"actual": inspected.get(key, 0), "minimum": value, "pass": inspected.get(key, 0) >= value}
            for key, value in minimum.items()
        }
        passed = (
            inspected["exists"] and inspected["zip"] and inspected["crc"] and inspected["xml"]
            and path.stat().st_size == fixture["bytes"]
            and sha256(path) == fixture["sha256"]
            and bool(anchors) and all(item["found"] for item in anchors)
            and all(item["pass"] for item in structure.values())
        )
        results.append({
            "id": fixture["id"],
            "path": str(path),
            "sha256": sha256(path) if path.is_file() else None,
            "anchors": anchors,
            "structure": structure,
            "pass": passed,
        })
    schema_pass = (
        manifest.get("schemaVersion") == 1
        and manifest.get("release") == "E1-A-editing-discovery"
        and manifest.get("mutationPolicy") == "copy-only"
        and len(results) == 5
    )
    return {
        "schemaVersion": 1,
        "release": "E1-A-editing-discovery",
        "manifest": str(manifest_path),
        "manifestSha256": sha256(manifest_path),
        "schemaPass": schema_pass,
        "fixtures": results,
        "pass": schema_pass and all(item["pass"] for item in results),
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=project / "test-docs" / "e1" / "manifest.json")
    parser.add_argument("--output", type=Path, default=project.parent / "findings" / "evidence" / "sdk-e1" / "baseline" / "corpus.json")
    args = parser.parse_args()
    result = validate(args.manifest.resolve())
    write_json(args.output.resolve(), result)
    print(json.dumps({"output": str(args.output.resolve()), "pass": result["pass"]}))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

