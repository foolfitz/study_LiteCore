#!/usr/bin/env python3
"""Assemble the isolated E1-B narrow editor v1 product profile."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from e1_support import sha256, write_json


EDITOR_ACTIONS = [
    "move-character-left",
    "move-character-right",
    "delete-backward",
    "delete-forward",
    "insert-paragraph-break",
    "insert-line-break",
    "set-bold",
    "set-italic",
    "set-underline",
    "set-strikethrough",
]


def build_profile(
    source_manifest: Path,
    loader: Path,
    wasm: Path,
    worker: Path,
    output: Path,
) -> dict[str, object]:
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(loader, output / "probe.js")
    shutil.copy2(wasm, output / "probe.wasm")
    shutil.copy2(worker, output / "sdk-worker.js")
    manifest["profile"] = "e1-editor-v1"
    manifest["sdkVersion"] = f'{manifest["sdkVersion"]}+e1-editor-v1'
    manifest["artifactFiles"] = {
        **manifest["artifactFiles"],
        "probe.js": "./probe.js",
        "probe.wasm": "./probe.wasm",
    }
    capabilities = list(manifest.get("capabilities", []))
    capabilities.extend(["narrow-editor-v1", "verified-selection-delete"])
    manifest["capabilities"] = capabilities
    manifest.pop("diagnostic", None)
    manifest["editorContract"] = {
        "version": 1,
        "abiVersion": 1,
        "actions": EDITOR_ACTIONS,
        "textCommit": "document-sdk-insert-text",
        "undo": "document-sdk-undo",
        "state": "typed-editor-state-v1",
        "selectionBarrier": "verified-single-writer-unit-v1",
        "boundaryRejectionRequiresFreshWorker": True,
        "automaticRetry": False,
        "rawCallbackExposed": False,
        "arbitraryKeyCodeAccepted": False,
        "arbitraryUnoCommandAccepted": False,
        "diagnosticOperationsExposed": False,
        "loaderSha256": sha256(output / "probe.js"),
        "wasmSha256": sha256(output / "probe.wasm"),
        "workerSha256": sha256(output / "sdk-worker.js"),
    }
    write_json(output / "sdk-manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_profile(args.source_manifest, args.loader, args.wasm, args.worker, args.output)


if __name__ == "__main__":
    main()
