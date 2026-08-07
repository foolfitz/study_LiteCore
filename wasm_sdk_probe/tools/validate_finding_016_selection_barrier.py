#!/usr/bin/env python3
"""Validate Finding 016 verified-selection barrier browser evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from e1_support import sha256, write_json
from r7_support import desktop_pdf_roundtrip

EXPECTED_POSITIVE_CASES = {
    "ascii-forward",
    "ascii-backward",
    "zh-forward",
    "zh-backward",
    "emoji-forward",
    "emoji-backward",
    "combining-forward",
    "combining-backward",
}
EXPECTED_BOUNDARY_CASES = {
    "document-start-backward",
    "paragraph-end-forward",
    "table-cell-start-backward",
    "table-cell-end-forward",
}
EXPECTED_OUTPUT_NAMES = {
    "plain-positive-final.odt",
    "boundary-document-start.odt",
    "boundary-paragraph-end.odt",
    "boundary-table-start.odt",
    "boundary-table-end.odt",
}


def evaluate_result(result: dict[str, Any]) -> dict[str, Any]:
    positives = result.get("positiveCases") or []
    boundaries = result.get("boundaryCases") or []
    positive_ids = {item.get("id") for item in positives}
    boundary_ids = {item.get("id") for item in boundaries}
    positive_pass = positive_ids == EXPECTED_POSITIVE_CASES and all(
        len(item.get("repetitions") or []) == 3
        and all(
            repetition.get("status") == "passed"
            and repetition.get("completion") == "verified-selection-delete"
            and repetition.get("changed") is True
            and repetition.get("revisionDelta") == 1
            and repetition.get("selectedTextMatches") is True
            and repetition.get("exactMutation") is True
            and repetition.get("undoRestored") is True
            for repetition in item.get("repetitions") or []
        )
        for item in positives
    )
    boundary_pass = boundary_ids == EXPECTED_BOUNDARY_CASES and all(
        item.get("status") == "rejected"
        and item.get("code") == "EDITOR_BOUNDARY_UNSUPPORTED"
        and item.get("revisionDelta") == 0
        and item.get("contentUnchanged") is True
        for item in boundaries
    )
    outputs = result.get("outputs") or []
    output_pass = len(outputs) == 5 and all(
        item.get("zip") is True
        and item.get("crc") is True
        and item.get("xml") is True
        and item.get("anchorsPreserved") is True
        for item in outputs
    )
    invariant_pass = (
        result.get("complete") is True
        and result.get("rawCallbackExposed") is False
        and result.get("manifest", {}).get("profile")
        == "finding-016-selection-barrier"
        and result.get("manifest", {})
        .get("diagnostic", {})
        .get("stateWordCountUsedForCompletion")
        is False
        and result.get("manifest", {})
        .get("diagnostic", {})
        .get("boundaryRejectionRequiresFreshWorker")
        is True
        and result.get("automaticRetry") is False
    )
    passed = positive_pass and boundary_pass and output_pass and invariant_pass
    return {
        "browser": result.get("browser"),
        "browserVersion": result.get("browserVersion"),
        "positivePass": positive_pass,
        "boundaryPass": boundary_pass,
        "outputPass": output_pass,
        "invariantPass": invariant_pass,
        "pass": passed,
    }


def decide(results: list[dict[str, Any]]) -> dict[str, Any]:
    browsers = [evaluate_result(item) for item in results]
    complete = {item.get("browser") for item in browsers} == {"chrome", "firefox"}
    passed = complete and all(item["pass"] for item in browsers)
    return {
        "schemaVersion": 1,
        "finding": "016",
        "experiment": "selection-barrier",
        "browsers": browsers,
        "complete": complete,
        "pass": passed,
        "decision": (
            "SELECTION_BARRIER_SUPPORTED_WITH_BOUNDARY_RESTART"
            if passed
            else "STOP_OR_RESCOPE"
        ),
    }


def evaluate_desktop_roundtrip(
    results: list[dict[str, Any]],
    output_root: Path,
    converter=desktop_pdf_roundtrip,
) -> dict[str, Any]:
    """Reopen every browser output in desktop LibreOffice and export it to PDF."""
    documents: list[dict[str, Any]] = []
    for result in sorted(results, key=lambda item: str(item.get("browser"))):
        browser = result.get("browser")
        outputs = {
            item.get("name"): item
            for item in result.get("outputs") or []
            if isinstance(item, dict)
        }
        for name in sorted(EXPECTED_OUTPUT_NAMES):
            item = outputs.get(name) or {}
            source = Path(item.get("path") or "")
            source_exists = source.is_file()
            actual_sha256 = sha256(source) if source_exists else None
            source_matches = (
                source_exists
                and item.get("sha256") == actual_sha256
                and item.get("zip") is True
                and item.get("crc") is True
                and item.get("xml") is True
                and item.get("anchorsPreserved") is True
            )
            pdf = (
                output_root
                / str(browser)
                / f"{Path(name).stem}.{(actual_sha256 or 'missing')[:12]}.pdf"
            )
            desktop = (
                converter(source, pdf)
                if source_matches
                else {"pass": False, "error": "source evidence is missing or changed"}
            )
            documents.append({
                "browser": browser,
                "browserVersion": result.get("browserVersion"),
                "name": name,
                "source": str(source),
                "sourceBytes": source.stat().st_size if source_exists else None,
                "sourceSha256": actual_sha256,
                "sourceMatchesBrowserEvidence": source_matches,
                "desktop": desktop,
                "pass": source_matches and desktop.get("pass") is True,
            })
    browsers = {item.get("browser") for item in results}
    passed = (
        browsers == {"chrome", "firefox"}
        and len(documents) == 10
        and all(item["pass"] for item in documents)
    )
    return {
        "schemaVersion": 1,
        "finding": "016",
        "experiment": "selection-barrier-desktop-roundtrip",
        "documents": documents,
        "complete": len(documents) == 10,
        "pass": passed,
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--browser-root",
        type=Path,
        default=(
            workspace
            / "findings"
            / "evidence"
            / "016"
            / "selection-barrier-wasm"
            / "browser"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            workspace
            / "findings"
            / "evidence"
            / "016"
            / "selection-barrier-wasm"
            / "summary.json"
        ),
    )
    parser.add_argument(
        "--desktop-roundtrip",
        action="store_true",
        help="also reopen all ten saved ODT files in desktop LibreOffice",
    )
    parser.add_argument(
        "--roundtrip-output",
        type=Path,
        default=(
            workspace
            / "findings"
            / "evidence"
            / "016"
            / "selection-barrier-wasm"
            / "roundtrip"
            / "summary.json"
        ),
    )
    args = parser.parse_args()
    paths = sorted(args.browser_root.resolve().glob("*/latest.json"))
    results = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    summary = decide(results)
    summary["sources"] = [str(path) for path in paths]
    if args.desktop_roundtrip:
        roundtrip = evaluate_desktop_roundtrip(
            results, args.roundtrip_output.resolve().parent
        )
        write_json(args.roundtrip_output.resolve(), roundtrip)
        summary["desktopRoundtrip"] = {
            "source": str(args.roundtrip_output.resolve()),
            "complete": roundtrip["complete"],
            "pass": roundtrip["pass"],
        }
        summary["pass"] = summary["pass"] and roundtrip["pass"]
        if not summary["pass"]:
            summary["decision"] = "STOP_OR_RESCOPE"
    write_json(args.output.resolve(), summary)
    print(json.dumps({"output": str(args.output.resolve()), **summary}))
    if not summary["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
