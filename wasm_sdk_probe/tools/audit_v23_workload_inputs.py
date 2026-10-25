#!/usr/bin/env python3
"""Verify the literal workload inputs recorded by existing timing reports.

This is an input-provenance proof only. It does not judge timing steps, browser
behavior, or cohort completion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_long_document import build

MARKDOWN_BYTES = 65_536
LONG_DOCUMENT_PAGES = 60
PACKAGE_MEMBERS = (
    "META-INF/manifest.xml",
    "content.xml",
    "mimetype",
    "styles.xml",
)


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _zip_members(path: Path) -> tuple[dict[str, bytes], list[str]]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        duplicates = sorted({name for name in names if names.count(name) > 1})
        return {name: archive.read(name) for name in names}, duplicates


def audit_page(page: dict, report_path: Path, run_index: int) -> dict:
    """Check literal paste and long60 package bytes for one recorded page."""
    problems = []
    page = _mapping(page)
    page_source = f"{report_path}#/runs/{run_index}/page"
    request_rows = [r for r in _list(page.get("requests"))
                    if _mapping(r).get("operation") == "pasteMarkdown"]
    markdown_result = {
        "source": page_source,
        "requestCount": len(request_rows),
        "expectedUtf8Bytes": MARKDOWN_BYTES,
    }
    if len(request_rows) != 1:
        problems.append({"code": "paste-request-count", "source": page_source,
                         "actual": len(request_rows)})
    elif isinstance(_mapping(request_rows[0].get("payload")).get("text"), str):
        payload = _mapping(request_rows[0].get("payload"))
        text = payload["text"]
        raw = text.encode("utf-8")
        recorded_bytes = payload.get("textUtf8Bytes")
        markdown = _mapping(page.get("markdown"))
        actual_hash = _sha256(raw)
        markdown_result.update({
            "actualUtf8Bytes": len(raw),
            "payloadTextUtf8Bytes": recorded_bytes,
            "actualSha256": actual_hash,
            "pageMarkdownBytes": markdown.get("bytes"),
            "pageMarkdownSha256": markdown.get("sha256"),
        })
        if len(raw) != MARKDOWN_BYTES:
            problems.append({"code": "paste-literal-size", "source": page_source,
                             "expected": MARKDOWN_BYTES, "actual": len(raw)})
        if recorded_bytes != len(raw):
            problems.append({"code": "paste-recorded-size", "source": page_source,
                             "actualPayloadUtf8Bytes": recorded_bytes,
                             "actualTextUtf8Bytes": len(raw)})
        if markdown.get("bytes") != len(raw) or markdown.get("sha256") != actual_hash:
            problems.append({"code": "paste-markdown-binding", "source": page_source,
                             "actualTextUtf8Bytes": len(raw), "actualTextSha256": actual_hash,
                             "pageMarkdownBytes": markdown.get("bytes"),
                             "pageMarkdownSha256": markdown.get("sha256")})
    else:
        problems.append({"code": "paste-literal-missing", "source": page_source,
                         "message": "the unique pasteMarkdown request lacks literal string payload.text"})

    mirror_path = report_path.parent / "mirror" / "long60.odt"
    long_result = {"source": str(mirror_path), "expectedPages": LONG_DOCUMENT_PAGES}
    try:
        actual_bytes = mirror_path.read_bytes()
        expected_bytes = build(LONG_DOCUMENT_PAGES)
        actual_members, actual_duplicates = _zip_members(mirror_path)
        # Decode the generated archive in memory; never write the expected bytes.
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(expected_bytes)) as archive:
            expected_members = {name: archive.read(name) for name in archive.namelist()}
        actual_names = sorted(actual_members)
        expected_name_set = set(PACKAGE_MEMBERS)
        extra = sorted(set(actual_names) - expected_name_set)
        missing = sorted(expected_name_set - set(actual_names))
        member_rows = []
        for name in PACKAGE_MEMBERS:
            actual_member = actual_members.get(name)
            expected_member = expected_members.get(name)
            row = {"name": name, "present": actual_member is not None,
                   "expectedSha256": _sha256(expected_member) if expected_member is not None else None,
                   "actualSha256": _sha256(actual_member) if actual_member is not None else None,
                   "matches": actual_member == expected_member}
            member_rows.append(row)
        fixture_hash = _sha256(actual_bytes)
        report = json.loads(report_path.read_text())
        recorded_fixture = _mapping(report.get("fixtures")).get("long60")
        page_fixture = _mapping(_mapping(page.get("fixtures")).get("long60"))
        long_result.update({"actualFileSha256": fixture_hash,
                            "reportFixtureSha256": recorded_fixture,
                            "pageFixture": page_fixture,
                            "actualMemberNames": actual_names,
                            "expectedMemberNames": sorted(expected_name_set),
                            "extraMembers": extra, "missingMembers": missing,
                            "duplicateMembers": actual_duplicates,
                            "members": member_rows})
        if recorded_fixture != fixture_hash:
            problems.append({"code": "long60-report-binding", "source": page_source,
                             "reportFixtureSha256": recorded_fixture,
                             "actualFileSha256": fixture_hash})
        if page_fixture.get("sha256") != fixture_hash or page_fixture.get("bytes") != len(actual_bytes):
            problems.append({"code": "long60-page-binding", "source": page_source,
                             "pageFixture": page_fixture, "actualFileSha256": fixture_hash,
                             "actualFileBytes": len(actual_bytes)})
        if extra or missing or actual_duplicates or any(not row["matches"] for row in member_rows):
            problems.append({"code": "long60-package-members", "source": page_source,
                             "extraMembers": extra, "missingMembers": missing,
                             "duplicateMembers": actual_duplicates,
                             "mismatchedMembers": [row["name"] for row in member_rows if not row["matches"]]})
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        problems.append({"code": "long60-unreadable", "source": page_source,
                         "path": str(mirror_path), "error": str(exc)})

    return {"source": page_source, "markdown": markdown_result,
            "long60": long_result, "problems": problems}


def audit_report(report_path: Path) -> dict:
    report_path = Path(report_path).resolve()
    try:
        report = json.loads(report_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        problem = {"code": "report-unreadable", "source": str(report_path), "error": str(exc)}
        return {"source": str(report_path), "pages": [], "problems": [problem]}
    problems = []
    if not isinstance(report, dict):
        problem = {"code": "report-schema", "source": str(report_path),
                   "message": "report root must be an object"}
        return {"source": str(report_path), "pages": [], "problems": [problem]}
    rows = _list(report.get("runs"))
    workload_rows = [(i, row) for i, row in enumerate(rows)
                     if _mapping(row).get("arm") == "workload"]
    if not workload_rows:
        problems.append({"code": "workload-pages-missing", "source": str(report_path),
                         "runCount": len(rows)})
    pages = []
    for index, row_value in workload_rows:
        row = _mapping(row_value)
        page = _mapping(row.get("page"))
        if not page:
            result = {"source": f"{report_path}#/runs/{index}/page", "problems": [
                {"code": "workload-page-missing", "runFatal": row.get("fatal")} ]}
        else:
            result = audit_page(page, report_path, index)
            result["browser"] = row.get("browser")
            result["round"] = row.get("round")
            if page.get("complete") is not True or row.get("fatal") is not None or page.get("fatal") is not None:
                result["problems"].append({"code": "workload-page-unclean",
                                           "source": result["source"],
                                           "complete": page.get("complete"),
                                           "runFatal": row.get("fatal"),
                                           "pageFatal": page.get("fatal")})
        pages.append(result)
        problems.extend(result.get("problems", []))
    return {"source": str(report_path), "pageCount": len(pages),
            "pages": pages, "problems": problems}


def audit_reports(report_paths) -> dict:
    reports = [audit_report(Path(path)) for path in report_paths]
    problems = [problem for report in reports for problem in report.get("problems", [])]
    if not any(report.get("pageCount", 0) for report in reports):
        problems.append({"code": "zero-workload-pages",
                         "message": "input set contains no workload pages"})
    return {"verdict": "PASS" if not problems else "FAIL",
            "scope": "literal workload input provenance only; not timing or cohort acceptance",
            "reportCount": len(reports),
            "pageCount": sum(report.get("pageCount", 0) for report in reports),
            "reports": reports, "problems": problems}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args(argv)
    result = audit_reports(args.reports)
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
