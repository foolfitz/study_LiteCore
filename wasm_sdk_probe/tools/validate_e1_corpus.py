#!/usr/bin/env python3
"""Validate E1 fixture hashes, ODT structure, XML and required anchors."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from e1_support import inspect_odt, sha256, write_json

# The corpus E1-A froze.  Named rather than counted: this check used to be
# `len(results) == 5`, which stopped being true the moment a later release added
# a sixth fixture -- and since nothing ran this validator, that failure sat
# unnoticed through three more additions, taking a wrong `minimum` on
# paragraph-content with it.  A count says "the corpus is the size I remember";
# what E1-A actually needs is "the five files I froze are all still here and
# still pass", which is what this says now.  Later releases may add fixtures,
# and those have to pass too -- they just cannot displace these.
E1_A_FROZEN_FIXTURES = frozenset({
    "plain-grapheme", "multi-paragraph", "styled-list", "table-boundary",
    "r7-t2-styled",
})


def dangling_embedded_hrefs(path: Path) -> list[str]:
    """Package-relative hrefs marked xlink:show="embed" with no such member.

    LibreOffice does not degrade for these -- it refuses the whole document,
    in half a second, with "source file could not be loaded".  Measured
    2026-08-12 on a fixture whose one broken row took its other eight rows with
    it, and read at first as "the engine hangs opening this file".  A relative
    href says "the picture is in this package"; if it is not, the file is
    broken, and that is checkable here without needing LibreOffice at all.

    An absolute URL is a different thing entirely: a link to a picture that may
    or may not resolve at open time, which documents legitimately contain and
    which loads fine.
    """
    if not path.is_file():
        return []
    dangling = []
    with zipfile.ZipFile(path) as archive:
        members = set(archive.namelist())
        try:
            content = archive.read("content.xml").decode("utf-8")
        except KeyError:
            return []
    for element in re.findall(r"<draw:image\b[^>]*>", content):
        if 'xlink:show="embed"' not in element:
            continue
        href = re.search(r'xlink:href="([^"]*)"', element)
        if not href:
            continue
        target = href.group(1)
        if "://" in target or target.startswith("/"):
            continue
        if target not in members:
            dangling.append(target)
    return dangling


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
        dangling = dangling_embedded_hrefs(path)
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
            and not dangling
        )
        results.append({
            "id": fixture["id"],
            "path": str(path),
            "sha256": sha256(path) if path.is_file() else None,
            "anchors": anchors,
            "structure": structure,
            "danglingEmbeddedHrefs": dangling,
            "pass": passed,
        })
    present = {item["id"] for item in results}
    missing = sorted(E1_A_FROZEN_FIXTURES - present)
    schema_pass = (
        manifest.get("schemaVersion") == 1
        and manifest.get("release") == "E1-A-editing-discovery"
        and manifest.get("mutationPolicy") == "copy-only"
        and not missing
    )
    return {
        "schemaVersion": 1,
        "release": "E1-A-editing-discovery",
        "manifest": str(manifest_path),
        "manifestSha256": sha256(manifest_path),
        "schemaPass": schema_pass,
        "frozenFixturesMissing": missing,
        "addedSinceE1A": sorted(present - E1_A_FROZEN_FIXTURES),
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

