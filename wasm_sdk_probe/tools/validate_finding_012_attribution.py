#!/usr/bin/env python3
"""Validate native LOK and diagnostic WASM evidence for finding 012."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ORIGINAL = "t2-original"
UNWRAPPED = "t2-image-unwrapped"
ENTER = "document-destroy-enter"
RETURN = "document-destroy-return"


def _records(results: dict[str, list[dict[str, Any]]], fixture: str) -> list[dict[str, Any]]:
    return list(results.get(fixture) or [])


def _all_close(records: list[dict[str, Any]]) -> bool:
    return bool(records) and all(
        item.get("outcome") == "close-pass"
        and ENTER in item.get("stages", [])
        and RETURN in item.get("stages", [])
        for item in records
    )


def _all_blocked(records: list[dict[str, Any]]) -> bool:
    return bool(records) and all(
        item.get("outcome") == "timeout"
        and ENTER in item.get("stages", [])
        and RETURN not in item.get("stages", [])
        for item in records
    )


def classify_native(results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    original = _records(results, ORIGINAL)
    unwrapped = _records(results, UNWRAPPED)
    if _all_blocked(original) and _all_close(unwrapped):
        decision = "NATIVE_LOK_REPRODUCED"
        passed = True
    elif _all_close(original) and _all_close(unwrapped):
        decision = "NOT_REPRODUCED_SYSTEM_NATIVE"
        passed = True
    else:
        decision = "INCONCLUSIVE_NATIVE"
        passed = False
    return {
        "decision": decision,
        "observed": "native LibreOfficeKit document destroy entry/return stages",
        "notValidated": ["version", "same-commit native LibreOfficeKit"],
        "runs": {ORIGINAL: len(original), UNWRAPPED: len(unwrapped)},
        "pass": passed,
    }


def classify_wasm(results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    original = _records(results, ORIGINAL)
    unwrapped = _records(results, UNWRAPPED)
    if _all_blocked(original) and _all_close(unwrapped):
        decision = "WASM_DOCUMENT_DESTROY_BLOCKED"
        passed = True
    elif _all_close(original) and _all_close(unwrapped):
        decision = "NOT_REPRODUCED_DIAGNOSTIC_WASM"
        passed = False
    else:
        decision = "INCONCLUSIVE_WASM"
        passed = False
    return {
        "decision": decision,
        "observed": "diagnostic stage events around LibreOfficeKitDocument::destroy",
        "notValidated": ["causality inside LibreOfficeKitDocument::destroy"],
        "runs": {ORIGINAL: len(original), UNWRAPPED: len(unwrapped)},
        "pass": passed,
    }


def combine_attribution(
    native: dict[str, Any], browsers: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    wasm_confirmed = set(browsers) == {"chrome", "firefox"} and all(
        item.get("decision") == "WASM_DOCUMENT_DESTROY_BLOCKED" and item.get("pass") is True
        for item in browsers.values()
    )
    if not wasm_confirmed:
        return {
            "decision": "INCONCLUSIVE",
            "candidateLayer": None,
            "fixed": False,
            "r7Pass": False,
            "notValidated": ["same-commit native LibreOfficeKit"],
            "pass": False,
        }

    native_decision = native.get("decision")
    if native_decision == "NATIVE_LOK_REPRODUCED":
        candidate = "libreofficekit-document-destroy-cross-runtime"
    elif native_decision == "NOT_REPRODUCED_SYSTEM_NATIVE":
        candidate = "wasm-build-or-version-specific-document-destroy"
    else:
        candidate = "wasm-document-destroy"
    return {
        "decision": "DOCUMENT_DESTROY_BOUNDARY_CONFIRMED",
        "candidateLayer": candidate,
        "fixed": False,
        "r7Pass": False,
        "notValidated": [
            "same-commit native LibreOfficeKit",
            "causality inside LibreOfficeKitDocument::destroy",
        ],
        "pass": True,
    }


def load_results(root: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(root.glob("**/result.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        fixture = record.get("fixture")
        fixture_id = fixture.get("id") if isinstance(fixture, dict) else fixture
        if fixture_id:
            grouped.setdefault(str(fixture_id), []).append(record)
    return grouped


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()

    native = classify_native(load_results(args.evidence_root / "native"))
    browsers = {
        browser: classify_wasm(load_results(args.evidence_root / "wasm" / browser))
        for browser in ("chrome", "firefox")
    }
    combined = combine_attribution(native, browsers)
    summary = {
        "schemaVersion": 1,
        "release": "finding-012-r7-attribution",
        "verifiedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "native": native,
        "wasm": browsers,
        **combined,
    }
    write_json(args.evidence_root / "summary.json", summary)
    if not summary["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
