#!/usr/bin/env python3
"""Validate browser-produced ODT files structurally and with desktop LibreOffice."""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import uno


def file_url(path: Path) -> str:
    return uno.systemPathToFileUrl(str(path.resolve()))


def inspect_odt(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        content = archive.read("content.xml")
        root = ET.fromstring(content)
        names = archive.namelist()

    text = "".join(root.itertext())

    def count(local_name: str) -> int:
        return sum(element.tag.endswith("}" + local_name) for element in root.iter())

    return {
        "zip_ok": bad_member is None,
        "content_xml_ok": True,
        "text": text,
        "insert_character_count": text.count("測"),
        "tables": count("table"),
        "images": count("image"),
        "annotations": count("annotation"),
        "headings": count("h"),
        "picture_entries": len([name for name in names if name.startswith("Pictures/")]),
    }


def desktop_open_check(soffice: str, path: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="wasm-sdk-probe-roundtrip-") as temp:
        temp_path = Path(temp)
        profile = temp_path / "profile"
        output = temp_path / "pdf"
        profile.mkdir()
        output.mkdir()
        process = subprocess.run(
            [
                soffice,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--norestore",
                f"-env:UserInstallation={file_url(profile)}",
                "--convert-to", "pdf",
                "--outdir", str(output),
                str(path.resolve()),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        pdf = output / f"{path.stem}.pdf"
        return {
            "pass": process.returncode == 0 and pdf.is_file() and pdf.stat().st_size > 0,
            "returncode": process.returncode,
            "stdout": process.stdout.strip(),
            "stderr": process.stderr.strip(),
            "pdf_bytes": pdf.stat().st_size if pdf.is_file() else 0,
        }


def original_for_output(name: str, test_docs: Path) -> Path:
    for stem in ("t1-plain-zh", "t2-styled", "t3-long"):
        if stem in name:
            return test_docs / f"{stem}.odt"
    raise ValueError(f"cannot map browser output to an input document: {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser.add_argument(
        "--raw-dir", type=Path,
        default=workspace / "findings" / "evidence" / "probe-r1" / "browser-raw",
    )
    parser.add_argument("--test-docs", type=Path, default=project / "test-docs")
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "findings" / "evidence" / "probe-r1" / "roundtrip.json",
    )
    parser.add_argument("--soffice", default=shutil.which("soffice") or "soffice")
    args = parser.parse_args()

    desktop_version = subprocess.run(
        [args.soffice, "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    documents: dict[str, dict[str, Any]] = {}

    for output_path in sorted(args.raw_dir.glob("*-out.odt")):
        original_path = original_for_output(output_path.name, args.test_docs)
        key = original_path.stem
        original = inspect_odt(original_path)
        output = inspect_odt(output_path)
        text_similarity = difflib.SequenceMatcher(
            None, original["text"], output["text"], autojunk=False
        ).ratio()
        structure_ok = True
        if key == "t2-styled":
            for field in ("tables", "images", "annotations", "headings", "picture_entries"):
                structure_ok = structure_ok and output[field] >= original[field]

        desktop = desktop_open_check(args.soffice, output_path)
        passed = (
            output["zip_ok"]
            and output["content_xml_ok"]
            and output["insert_character_count"] >= original["insert_character_count"] + 1
            and text_similarity >= 0.95
            and structure_ok
            and desktop["pass"]
        )
        sample = {
            "path": str(output_path),
            "pass": passed,
            "inserted_character_delta": (
                output["insert_character_count"] - original["insert_character_count"]
            ),
            "text_similarity": text_similarity,
            "structure_ok": structure_ok,
            "output_structure": {
                key: output[key] for key in (
                    "tables", "images", "annotations", "headings", "picture_entries"
                )
            },
            "desktop_open": desktop,
        }
        document = documents.setdefault(key, {
            "doc": original_path.name,
            "desktop_version": desktop_version,
            "pass": True,
            "notes": "",
            "samples": [],
        })
        document["samples"].append(sample)
        document["pass"] = document["pass"] and passed

    if not documents:
        raise SystemExit(f"no browser output files found under {args.raw_dir}")
    for document in documents.values():
        document["notes"] = (
            f"{len(document['samples'])} browser outputs checked: ZIP/XML, inserted character "
            "delta, text preservation, desktop PDF export"
        )

    result = {
        "date": dt.date.today().isoformat(),
        "desktop_version": desktop_version,
        "documents": list(documents.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)


if __name__ == "__main__":
    main()
