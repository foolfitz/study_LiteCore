#!/usr/bin/env python3
"""Validate E1 browser outputs as ODT and reopen/export them in desktop LibreOffice."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from e1_support import inspect_odt, sha256, write_json
from r7_support import desktop_pdf_roundtrip


def latest_evidence_directory(base: Path) -> Path:
    attempts = sorted(path for path in base.glob("attempt-*") if path.is_dir())
    return attempts[-1] if attempts else base


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--browser-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "discovery" / "browser",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "discovery" / "roundtrip" / "summary.json",
    )
    args = parser.parse_args()
    manifest = json.loads((project / "test-docs" / "e1" / "manifest.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest["fixtures"]}
    documents = []
    for browser in ("chrome", "firefox"):
        for fixture_id, fixture in by_id.items():
            directory = latest_evidence_directory(
                args.browser_root / browser / fixture_id
            )
            path = directory / "output.odt"
            inspected = inspect_odt(path)
            anchors = [
                {"text": anchor, "found": anchor in inspected["text"]}
                for anchor in fixture["anchors"]
            ]
            minimum = fixture["minimum"]
            structure = {
                key: {"actual": inspected.get(key, 0), "minimum": value,
                      "pass": inspected.get(key, 0) >= value}
                for key, value in minimum.items()
            }
            desktop = desktop_pdf_roundtrip(path, directory / "desktop.pdf") if path.is_file() else {"pass": False, "error": "missing output"}
            passed = (
                inspected["exists"] and inspected["zip"] and inspected["crc"] and inspected["xml"]
                and all(item["found"] for item in anchors)
                and all(item["pass"] for item in structure.values())
                and desktop["pass"]
            )
            documents.append({
                "browser": browser,
                "fixture": fixture_id,
                "path": str(path),
                "bytes": path.stat().st_size if path.is_file() else None,
                "sha256": sha256(path) if path.is_file() else None,
                "anchors": anchors,
                "structure": structure,
                "desktop": desktop,
                "pass": passed,
            })
    result = {
        "schemaVersion": 1,
        "release": "E1-A-editing-discovery",
        "documents": documents,
        "pass": len(documents) == 10 and all(item["pass"] for item in documents),
    }
    write_json(args.output.resolve(), result)
    print(json.dumps({"output": str(args.output.resolve()), "pass": result["pass"]}))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
