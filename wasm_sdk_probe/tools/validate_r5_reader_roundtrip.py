#!/usr/bin/env python3
"""Validate R5 reader outputs without allowing unsupported mutations."""

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
    return {
        "zipOk": bad_member is None,
        "contentXmlOk": True,
        "latinPresent": "LibreOfficeKit" in text,
        "cjkPresent": "臺灣軟體工程" in text,
        "blockedReplaceAbsent": "must-not-apply" not in text,
        "text": text,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r5" / "browser-raw" / "reader",
    )
    parser.add_argument("--input", type=Path, default=project / "test-docs" / "t1-plain-zh.odt")
    parser.add_argument(
        "--output",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r5" / "reader-roundtrip.json",
    )
    parser.add_argument("--soffice", default=shutil.which("soffice") or "soffice")
    args = parser.parse_args()

    desktop_version = subprocess.run(
        [args.soffice, "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    original = inspect(args.input)
    samples: list[dict[str, Any]] = []
    for output_path in sorted(args.raw_dir.glob("*-out.odt")):
        structure = inspect(output_path)
        text_unchanged = structure["text"] == original["text"]
        public_checks = {key: value for key, value in structure.items() if key != "text"}
        desktop = desktop_open_check(args.soffice, output_path)
        passed = all(public_checks.values()) and text_unchanged and desktop["pass"]
        samples.append({
            "path": str(output_path),
            "pass": passed,
            "structure": public_checks,
            "textUnchanged": text_unchanged,
            "desktopOpen": desktop,
        })

    if not samples:
        raise SystemExit(f"no browser output files found under {args.raw_dir}")
    result = {
        "date": dt.date.today().isoformat(),
        "desktopVersion": desktop_version,
        "sampleCount": len(samples),
        "pass": all(sample["pass"] for sample in samples),
        "samples": samples,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)
    if not result["pass"]:
        raise SystemExit("R5 reader round-trip validation failed")


if __name__ == "__main__":
    main()
