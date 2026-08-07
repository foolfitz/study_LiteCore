#!/usr/bin/env python3
"""Aggregate R7-C corpus, browser, fidelity and desktop evidence."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from r7_support import desktop_pdf_roundtrip, load_json, write_json


def archive_text(path: Path) -> str:
    if not zipfile.is_zipfile(path):
        return ""
    chunks = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith(".xml"):
                continue
            try:
                chunks.append("".join(ElementTree.fromstring(archive.read(name)).itertext()))
            except (ElementTree.ParseError, KeyError):
                continue
    return "\n".join(chunks)


def desktop_baseline(item: dict[str, Any], source: Path, output_root: Path) -> dict[str, Any]:
    pdf = output_root / f"{item['id']}.pdf"
    converted = desktop_pdf_roundtrip(source, pdf)
    extracted = output_root / f"{item['id']}.txt"
    text_result = subprocess.run(
        ["pdftotext", str(pdf), str(extracted)],
        check=False, capture_output=True, text=True, timeout=60,
    ) if converted["pass"] else None
    pdf_text = extracted.read_text(encoding="utf-8", errors="replace") if extracted.is_file() else ""
    package_text = archive_text(source)
    anchor_results = []
    for anchor in item["anchors"]:
        package_count = package_text.count(anchor["text"])
        pdf_count = pdf_text.count(anchor["text"])
        anchor_results.append({
            **anchor,
            "packageCount": package_count,
            "pdfCount": pdf_count,
            "packagePass": package_count >= anchor["count"],
        })
    match = re.search(r"^Pages:\s+(\d+)$", converted.get("pdfinfo") or "", re.MULTILINE)
    pages = int(match.group(1)) if match else None
    expected_pages = item["expected"].get("pageCount")
    return {
        "id": item["id"],
        "source": str(source),
        "converted": converted,
        "pdftotextReturnCode": text_result.returncode if text_result else None,
        "pages": pages,
        "expectedPages": expected_pages,
        "anchors": anchor_results,
        "pass": converted["pass"]
        and text_result is not None and text_result.returncode == 0
        and all(anchor["packagePass"] for anchor in anchor_results)
        and (expected_pages is None or pages == expected_pages),
    }


def all_cases(evidence_root: Path, browser: str) -> list[dict[str, Any]]:
    cases = []
    root = evidence_root / "browser" / "compatibility" / browser
    for group, runs in (("repeat", range(1, 4)), ("full", range(1, 2))):
        for run in runs:
            path = root / group / f"run-{run}" / "result.json"
            if path.is_file():
                value = load_json(path)
                cases.extend(value.get("metrics", {}).get("cases", []))
    return cases


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r7",
    )
    args = parser.parse_args()
    manifest = load_json(project / "test-docs" / "r7-compat" / "manifest.json")
    corpus_validation = load_json(
        args.evidence_root / "corpus" / "compatibility-manifest-validation.json"
    )
    browser_summaries = {}
    for browser in ("chrome", "firefox"):
        path = args.evidence_root / "browser" / "compatibility" / browser / "summary.json"
        browser_summaries[browser] = load_json(path) if path.is_file() else {
            "path": str(path), "pass": False
        }

    baseline_root = args.evidence_root / "roundtrip" / "source-baseline"
    baselines = []
    for item in manifest["documents"]:
        is_supported_positive = item["expected"]["open"] == "pass"
        is_docx_baseline = item["mediaType"].endswith("wordprocessingml.document") and item["tier"] in {"L1", "L2"}
        if is_supported_positive or is_docx_baseline:
            baselines.append(desktop_baseline(
                item, project / "test-docs" / "r7-compat" / item["path"], baseline_root
            ))
    write_json(args.evidence_root / "roundtrip" / "desktop-source-baseline.json", {
        "schemaVersion": 1, "release": "R7-C", "documents": baselines,
        "pass": bool(baselines) and all(item["pass"] for item in baselines),
    })

    fidelity = []
    for item in manifest["documents"]:
        occurrences = {
            browser: [case for case in all_cases(args.evidence_root, browser) if case["id"] == item["id"]]
            for browser in ("chrome", "firefox")
        }
        required_runs = 3 if item["tier"] == "L0" or any(
            item["id"].startswith(prefix)
            for prefix in ("l1-plain", "l1-layout-table-image", "l1-review")
        ) else 1
        browser_pass = all(
            len(occurrences[browser]) >= required_runs
            and all(case["pass"] for case in occurrences[browser])
            for browser in occurrences
        )
        if item["expected"]["open"] == "typed-failure":
            content = "not-opened-typed"
            structure = "preflight-rejected"
            layout = "not-applicable"
        else:
            content = "exact-anchors" if browser_pass else "failed"
            structure = "package-and-semantic-pass" if browser_pass else "failed"
            layout = "landmark-tiles-and-desktop-pages" if browser_pass else "failed"
        font = "degraded-known" if "missing-font" in item["features"] else "not-observable"
        fidelity.append({
            "id": item["id"],
            "requiredRunsPerBrowser": required_runs,
            "observedRuns": {browser: len(values) for browser, values in occurrences.items()},
            "content": content,
            "structure": structure,
            "layout": layout,
            "font": font,
            "degradations": item["expected"].get("degradation", []),
            "pass": browser_pass,
        })

    checks = {
        "corpus": corpus_validation.get("pass") is True,
        "chrome": browser_summaries["chrome"].get("pass") is True,
        "firefox": browser_summaries["firefox"].get("pass") is True,
        "desktopBaselines": bool(baselines) and all(item["pass"] for item in baselines),
        "fidelityMatrix": bool(fidelity) and all(item["pass"] for item in fidelity),
        "docxTypedUnsupported": all(
            item["expected"]["typedCode"] == "UNSUPPORTED_FORMAT"
            for item in manifest["documents"]
            if item["mediaType"].endswith("wordprocessingml.document")
        ),
    }
    automatic_pass = all(checks.values())
    result = {
        "schemaVersion": 1,
        "release": "R7-C",
        "decision": "PARTIAL_GO_ODT_FIRST" if automatic_pass else "STOP",
        "checks": checks,
        "browsers": browser_summaries,
        "desktopBaselines": baselines,
        "fidelity": fidelity,
        "docxCapability": "unsupported-finding-013",
        "pass": automatic_pass,
    }
    output = args.evidence_root / "compatibility-summary.json"
    write_json(output, result)
    print(json.dumps({"output": str(output), "decision": result["decision"], "checks": checks}, ensure_ascii=False, indent=2))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
