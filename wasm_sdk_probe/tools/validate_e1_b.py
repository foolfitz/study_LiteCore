#!/usr/bin/env python3
"""Validate E1-B product profile, browser evidence and ODT round-trip."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from build_e1_b_profile import EDITOR_ACTIONS
from e1_support import inspect_odt, sha256, write_json
from r7_support import desktop_pdf_roundtrip


ESSENTIAL_OPERATIONS = {
    "unsupported-redo",
    "move-character-left",
    "move-character-right",
    "extend-selection-left",
    "typed-selection-state",
    "delete-backward",
    "delete-backward-text",
    "undo-delete-backward",
    "delete-forward",
    "delete-forward-text",
    "undo-delete-forward",
    "insert-text",
    "insert-text-search",
    "insert-paragraph-break",
    "paragraph-text",
    "paragraph-search",
    "insert-line-break",
    "line-text",
    "line-search",
    "insert-undo-marker",
    "public-undo",
    "undo-text-postcondition",
    "save",
}
FORMAT_OPERATIONS = {"set-bold-on", "set-bold-off", "set-italic-on", "set-italic-off"}
PRESERVED_ANCHORS = [
    "E1-PLAIN-START",
    "臺灣中文游標測試",
    "emoji 😀 grapheme",
    "combining é boundary",
    "E1-PLAIN-END",
]


def latest_evidence_directory(base: Path) -> Path:
    attempts = sorted(path for path in base.glob("attempt-*") if path.is_dir())
    return attempts[-1] if attempts else base


def operation_pass(result: dict[str, Any], names: set[str]) -> bool:
    operations = {item.get("name"): item for item in result.get("operations", [])}
    return all(operations.get(name, {}).get("status") == "passed" for name in names)


def decide(
    browser_results: list[dict[str, Any]],
    profile_safe: bool,
    roundtrip_safe: bool,
    regression_safe: bool,
) -> dict[str, Any]:
    browsers_complete = {item.get("browserName") for item in browser_results} == {"chrome", "firefox"}
    essentials = browsers_complete and all(operation_pass(item, ESSENTIAL_OPERATIONS) for item in browser_results)
    formats = browsers_complete and all(operation_pass(item, FORMAT_OPERATIONS) for item in browser_results)
    sessions_safe = browsers_complete and all(
        all(state.get("state") not in {"restart-required", "recoverable-error"}
            for state in item.get("states", []))
        for item in browser_results
    )
    safety = profile_safe and roundtrip_safe and regression_safe and sessions_safe
    if essentials and formats and safety:
        decision = "GO_TO_E1_C"
    elif essentials and safety:
        decision = "PARTIAL_GO_TO_E1_C"
    else:
        decision = "STOP_OR_RESCOPE"
    return {
        "properties": {
            "browsersComplete": browsers_complete,
            "essentialOperations": essentials,
            "boldItalic": formats,
            "profileFailClosed": profile_safe,
            "roundtrip": roundtrip_safe,
            "regression": regression_safe,
            "sessionsSafe": sessions_safe,
        },
        "decision": decision,
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "editor-contract",
    )
    parser.add_argument("--skip-desktop", action="store_true")
    args = parser.parse_args()
    root = args.evidence_root.resolve()

    profile_dir = project / "dist" / "profiles" / "e1-editor-v1"
    manifest_path = profile_dir / "sdk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    exports_path = project / "build" / "e1" / "editor-v1" / "exports.txt"
    exports = exports_path.read_text(encoding="utf-8").splitlines() if exports_path.is_file() else []
    contract = manifest.get("editorContract") or {}
    profile_safe = (
        manifest.get("profile") == "e1-editor-v1"
        and "narrow-editor-v1" in manifest.get("capabilities", [])
        and "editor-discovery-closed-actions" not in manifest.get("capabilities", [])
        and "diagnostic" not in manifest
        and contract.get("version") == 1
        and contract.get("actions") == EDITOR_ACTIONS
        and contract.get("automaticRetry") is False
        and contract.get("rawCallbackExposed") is False
        and contract.get("arbitraryKeyCodeAccepted") is False
        and contract.get("arbitraryUnoCommandAccepted") is False
        and "_oxsdk_editor_action" in exports
        and "_oxsdk_editor_get_state" in exports
        and not any("editor_discovery" in item for item in exports)
    )
    profile_result = {
        "manifest": str(manifest_path),
        "exports": str(exports_path),
        "loaderSha256": sha256(profile_dir / "probe.js") if (profile_dir / "probe.js").is_file() else None,
        "wasmSha256": sha256(profile_dir / "probe.wasm") if (profile_dir / "probe.wasm").is_file() else None,
        "workerSha256": sha256(profile_dir / "sdk-worker.js") if (profile_dir / "sdk-worker.js").is_file() else None,
        "actions": contract.get("actions"),
        "pass": profile_safe,
    }
    write_json(root / "profile" / "summary.json", profile_result)

    browser_results = []
    documents = []
    for browser in ("chrome", "firefox"):
        directory = latest_evidence_directory(root / "browser" / browser)
        result_path = directory / "result.json"
        if result_path.is_file():
            browser_results.append(json.loads(result_path.read_text(encoding="utf-8")))
        output = directory / "output.odt"
        inspected = inspect_odt(output)
        anchors = [{"text": text, "found": text in inspected.get("text", "")} for text in PRESERVED_ANCHORS]
        added = [
            {"text": text, "found": text in inspected.get("text", "")}
            for text in ("E1B-文字😀", "E1B-PARAGRAPH", "E1B-LINE")
        ]
        desktop = (
            {"pass": True, "skipped": True}
            if args.skip_desktop
            else desktop_pdf_roundtrip(output, directory / "desktop.pdf")
        ) if output.is_file() else {"pass": False, "error": "missing output"}
        passed = (
            inspected.get("exists") is True
            and inspected.get("zip") is True
            and inspected.get("crc") is True
            and inspected.get("xml") is True
            and all(item["found"] for item in anchors + added)
            and desktop.get("pass") is True
        )
        documents.append({
            "browser": browser,
            "path": str(output),
            "bytes": output.stat().st_size if output.is_file() else None,
            "sha256": sha256(output) if output.is_file() else None,
            "anchors": anchors,
            "added": added,
            "desktop": desktop,
            "pass": passed,
        })
    roundtrip = {"schemaVersion": 1, "documents": documents, "pass": all(item["pass"] for item in documents)}
    write_json(root / "roundtrip" / "summary.json", roundtrip)

    regression_path = root / "regression" / "summary.json"
    regression = json.loads(regression_path.read_text(encoding="utf-8")) if regression_path.is_file() else {"pass": False}
    decision = decide(browser_results, profile_safe, roundtrip["pass"], regression.get("pass") is True)
    result = {
        "schemaVersion": 1,
        "release": "E1-B-narrow-editor",
        "browserResults": len(browser_results),
        "profile": profile_result,
        "roundtrip": roundtrip,
        "regression": regression,
        **decision,
        "complete": len(browser_results) == 2,
    }
    write_json(root / "summary.json", result)
    print(json.dumps({
        "output": str(root / "summary.json"),
        "complete": result["complete"],
        "decision": result["decision"],
    }))
    if not result["complete"] or result["decision"] == "STOP_OR_RESCOPE":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
