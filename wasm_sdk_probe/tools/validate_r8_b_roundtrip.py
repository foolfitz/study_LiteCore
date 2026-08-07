#!/usr/bin/env python3
"""Validate R8-B saved ODT outputs as ZIP/XML/text and desktop PDF round-trips."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from r7_support import desktop_pdf_roundtrip, odt_text, sha256, write_json


def load_previous_pass(path: Path) -> bool | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("pass")
    except (OSError, json.JSONDecodeError):
        return None


def page_count(result: dict[str, Any]) -> int | None:
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.get("pdfinfo") or "", re.MULTILINE)
    return int(match.group(1)) if match else None


def validate_odt(path: Path) -> dict[str, Any]:
    result = {"path": str(path), "bytes": path.stat().st_size if path.is_file() else 0,
              "sha256": sha256(path) if path.is_file() else None,
              "zip": False, "crc": False, "xml": False, "pass": False}
    if not path.is_file() or not zipfile.is_zipfile(path):
        return result
    result["zip"] = True
    try:
        with zipfile.ZipFile(path) as archive:
            result["crc"] = archive.testzip() is None
            for name in archive.namelist():
                if name.endswith(".xml"):
                    ElementTree.fromstring(archive.read(name))
            result["xml"] = True
    except (zipfile.BadZipFile, ElementTree.ParseError, KeyError) as error:
        result["error"] = {"name": type(error).__name__, "message": str(error)}
    result["pass"] = result["zip"] and result["crc"] and result["xml"]
    return result


def validate_case(project: Path, case_root: Path) -> dict[str, Any]:
    browser_result = json.loads((case_root / "result.json").read_text(encoding="utf-8"))
    output = case_root / "output.odt"
    document = browser_result.get("document") or {}
    relative = str(document.get("path") or "").removeprefix("./")
    source = project / "dist" / relative
    package = validate_odt(output)
    text_equal = False
    text_error = None
    try:
        text_equal = source.is_file() and odt_text(source) == odt_text(output)
    except Exception as error:  # noqa: BLE001
        text_error = {"name": type(error).__name__, "message": str(error)}
    desktop_root = case_root / "desktop"
    source_pdf = desktop_pdf_roundtrip(source, desktop_root / "source.pdf")
    output_pdf = desktop_pdf_roundtrip(output, desktop_root / "output.pdf")
    source_pages, output_pages = page_count(source_pdf), page_count(output_pdf)
    result = {
        "case": str(case_root), "browserPass": browser_result.get("pass") is True,
        "source": str(source), "package": package, "textEqual": text_equal,
        "textError": text_error, "sourceDesktop": source_pdf, "outputDesktop": output_pdf,
        "sourcePages": source_pages, "outputPages": output_pages,
        "pageCountEqual": source_pages is not None and source_pages == output_pages,
    }
    result["pass"] = (result["browserPass"] and package["pass"] and text_equal
                      and source_pdf["pass"] and output_pdf["pass"]
                      and result["pageCountEqual"])
    return result


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=project)
    parser.add_argument("--evidence-root", type=Path,
                        default=workspace / "findings" / "evidence" / "sdk-r8" / "delivery")
    args = parser.parse_args()
    root = args.evidence_root.resolve()
    formal_cases = {
        "r6-reader-smoke", "r7-t1-roundtrip", "r7-t2-roundtrip", "font-full-fidelity",
    }
    case_roots = sorted({
        path.parent for path in (root / "browser").glob("*/*/*/output.odt")
        if path.parent.name in formal_cases
    })
    results = [validate_case(args.project.resolve(), path) for path in case_roots]
    summary = {"schemaVersion": 1, "release": "R8-B-versioned-artifact-delivery",
               "cases": results, "caseCount": len(results),
               "pass": len(results) >= 8 and all(item["pass"] for item in results)}
    output = root / "roundtrip" / "summary.json"
    if output.is_file() and load_previous_pass(output) is not True:
        attempt = 1
        while output.with_name(f"summary-attempt-{attempt}.json").exists():
            attempt += 1
        output.replace(output.with_name(f"summary-attempt-{attempt}.json"))
    write_json(output, summary)
    print(json.dumps({"output": str(output), "cases": len(results),
                      "pass": summary["pass"]}, ensure_ascii=False, indent=2))
    if not summary["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
