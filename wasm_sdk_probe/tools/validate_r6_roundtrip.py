#!/usr/bin/env python3
"""Validate R6-C browser matrix, ODT integrity and desktop PDF conversion."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any


REQUIRED_TEXT = (
    "R1 純文字中英混排測試",
    "臺灣軟體工程",
    "ODT round-trip 完整性檢查",
)
REPLACEMENT = "R4 Provider：LibreOfficeKit"
FORBIDDEN_TEXT = (
    "BOB-FORBIDDEN-STALE-R6",
    "forbidden-missing",
    "forbidden-ambiguous",
    "R6-S7-saved-local",
    "R6-S7-unsaved-local",
    ".uno:",
)


def file_url(path: Path) -> str:
    return path.resolve().as_uri()


def xml_and_text(archive: zipfile.ZipFile, name: str) -> tuple[ET.Element, str]:
    root = ET.fromstring(archive.read(name))
    return root, "".join(root.itertext())


def style_names(root: ET.Element) -> set[str]:
    names: set[str] = set()
    for element in root.iter():
        for key, value in element.attrib.items():
            if key.endswith("}style-name") or key.endswith("}name"):
                names.add(value)
    return names


def inspect_odt(path: Path, original_styles: set[str]) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        content_root, text = xml_and_text(archive, "content.xml")
        styles_root, _ = xml_and_text(archive, "styles.xml")
        xml_members = [
            name for name in archive.namelist()
            if name.endswith(".xml") or name.endswith(".rdf")
        ]
        parsed_members = []
        for name in xml_members:
            ET.fromstring(archive.read(name))
            parsed_members.append(name)
    styles = style_names(content_root) | style_names(styles_root)
    checks = {
        "zipCrcOk": bad_member is None,
        "allXmlWellFormed": len(parsed_members) == len(xml_members),
        "requiredTextPresent": all(value in text for value in REQUIRED_TEXT),
        "replacementCount": text.count(REPLACEMENT),
        "forbiddenTextAbsent": all(value not in text for value in FORBIDDEN_TEXT),
        "originalStylesRetained": original_styles.issubset(styles),
    }
    checks["pass"] = (
        checks["zipCrcOk"]
        and checks["allXmlWellFormed"]
        and checks["requiredTextPresent"]
        and checks["replacementCount"] == 1
        and checks["forbiddenTextAbsent"]
        and checks["originalStylesRetained"]
    )
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "xmlMembers": parsed_members,
        "styleCount": len(styles),
        "checks": checks,
    }


def convert_pdf(soffice: str, odt: Path, pdf_directory: Path) -> dict[str, Any]:
    pdf_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="r6-desktop-profile-") as temporary:
        profile = Path(temporary) / "profile"
        profile.mkdir()
        process = subprocess.run(
            [
                soffice,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--norestore",
                f"-env:UserInstallation={file_url(profile)}",
                "--convert-to", "pdf",
                "--outdir", str(pdf_directory.resolve()),
                str(odt.resolve()),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    pdf = pdf_directory / f"{odt.stem}.pdf"
    return {
        "pass": process.returncode == 0 and pdf.is_file() and pdf.stat().st_size > 0,
        "returncode": process.returncode,
        "stdout": process.stdout.strip(),
        "stderr": process.stderr.strip(),
        "pdf": str(pdf),
        "pdfBytes": pdf.stat().st_size if pdf.is_file() else 0,
        "pdfSha256": hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.is_file() else None,
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--browser-dir", type=Path,
        default=workspace / "findings/evidence/sdk-r6/browser/r6-c",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=workspace / "findings/evidence/sdk-r6/roundtrip",
    )
    parser.add_argument("--soffice", default=shutil.which("libreoffice") or "libreoffice")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pdf_directory = args.output_dir / "pdf"

    summaries = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(args.browser_dir.glob("reference-*-summary.json"))
    ]
    expected = {
        ("chrome", "chrome"): (3, {"s1", "s2", "s3", "s4", "s5", "s6", "s7"}),
        ("firefox", "firefox"): (3, {"s1", "s2", "s3", "s4", "s5", "s6", "s7"}),
        ("chrome", "firefox"): (1, {"s1", "s2", "s3", "s5"}),
    }
    matrix_checks = []
    for key, (samples, scenarios) in expected.items():
        match = next((item for item in summaries
                      if (item["aliceBrowser"], item["bobBrowser"]) == key), None)
        passed = bool(
            match and match.get("pass")
            and match.get("requestedSamples") == samples
            and scenarios.issubset(set(match.get("scenarios", [])))
        )
        matrix_checks.append({
            "aliceBrowser": key[0], "bobBrowser": key[1],
            "requiredSamples": samples, "requiredScenarios": sorted(scenarios),
            "pass": passed,
        })
    matrix_summary = {
        "schemaVersion": 1,
        "release": "R6-C",
        "checks": matrix_checks,
        "pass": all(item["pass"] for item in matrix_checks),
    }
    (args.output_dir / "browser-matrix-summary.json").write_text(
        json.dumps(matrix_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with zipfile.ZipFile(project / "test-docs/t1-plain-zh.odt") as archive:
        original_content, _ = xml_and_text(archive, "content.xml")
        original_styles_root, _ = xml_and_text(archive, "styles.xml")
    original_styles = style_names(original_content) | style_names(original_styles_root)
    desktop_version = subprocess.run(
        [args.soffice, "--version"], check=True, capture_output=True, text=True,
    ).stdout.strip()
    samples = []
    for odt in sorted(args.browser_dir.glob("reference-*-s2-v2.odt")):
        structure = inspect_odt(odt, original_styles)
        desktop = convert_pdf(args.soffice, odt, pdf_directory)
        samples.append({
            **structure,
            "desktop": desktop,
            "pass": structure["checks"]["pass"] and desktop["pass"],
        })
    if len(samples) != 7:
        raise SystemExit(f"expected 7 S2 v2 ODT samples, found {len(samples)}")
    result = {
        "schemaVersion": 1,
        "release": "R6-C",
        "desktopVersion": desktop_version,
        "originalV1Sha256": hashlib.sha256(
            (project / "test-docs/t1-plain-zh.odt").read_bytes()
        ).hexdigest(),
        "matrix": matrix_summary,
        "samples": samples,
        "pass": matrix_summary["pass"] and all(item["pass"] for item in samples),
    }
    output = args.output_dir / "summary.json"
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(output)
    if not result["pass"]:
        raise SystemExit("R6 round-trip validation failed")


if __name__ == "__main__":
    main()
