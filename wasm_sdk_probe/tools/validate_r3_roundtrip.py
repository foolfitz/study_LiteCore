#!/usr/bin/env python3
"""Validate R3 review-operation ODT outputs and desktop readability."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from validate_roundtrip import desktop_open_check


def inspect(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        root = ET.fromstring(archive.read("content.xml"))
    text = "".join(root.itertext())

    def count(local_name: str) -> int:
        return sum(element.tag.endswith("}" + local_name) for element in root.iter())

    return {
        "zip_ok": bad_member is None,
        "content_xml_ok": True,
        "replacement_present": "English terms" in text,
        "stale_text_absent": "SHOULD-NOT-APPEAR" not in text,
        "comment_text_present": "R3 review note" in text,
        "annotations": count("annotation"),
        "changed_regions": count("changed-region"),
        "insertions": count("insertion"),
        "deletions": count("deletion"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser.add_argument(
        "--raw-dir", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r3" / "browser-raw",
    )
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r3" / "roundtrip.json",
    )
    parser.add_argument("--soffice", default=shutil.which("soffice") or "soffice")
    args = parser.parse_args()

    desktop_version = subprocess.run(
        [args.soffice, "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    samples: list[dict[str, Any]] = []
    for output_path in sorted(args.raw_dir.glob("*-out.odt")):
        structure = inspect(output_path)
        desktop = desktop_open_check(args.soffice, output_path)
        passed = (
            all(structure[key] for key in (
                "zip_ok", "content_xml_ok", "replacement_present",
                "stale_text_absent", "comment_text_present",
            ))
            and structure["annotations"] >= 1
            and structure["changed_regions"] >= 1
            and structure["insertions"] >= 1
            and structure["deletions"] >= 1
            and desktop["pass"]
        )
        samples.append({
            "path": str(output_path),
            "pass": passed,
            "structure": structure,
            "desktop_open": desktop,
        })

    if not samples:
        raise SystemExit(f"no browser output files found under {args.raw_dir}")
    result = {
        "date": dt.date.today().isoformat(),
        "desktop_version": desktop_version,
        "pass": all(sample["pass"] for sample in samples),
        "samples": samples,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)
    if not result["pass"]:
        raise SystemExit("R3 round-trip validation failed")


if __name__ == "__main__":
    main()
