#!/usr/bin/env python3
"""Assemble an isolated diagnostic profile without replacing R5 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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

    manifest["profile"] = "finding-012-diagnostic"
    manifest["sdkVersion"] = f'{manifest["sdkVersion"]}+finding-012-diagnostic'
    manifest["artifactFiles"] = {
        **manifest["artifactFiles"],
        "probe.js": "./probe.js",
        "probe.wasm": "./probe.wasm",
    }
    manifest["diagnostic"] = {
        "scope": "finding-012-document-destroy-boundary",
        "closeStages": ["document-destroy-enter", "document-destroy-return"],
        "loaderSha256": sha256(output / "probe.js"),
        "wasmSha256": sha256(output / "probe.wasm"),
        "productionArtifactReplaced": False,
    }
    (output / "sdk-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_profile(
        args.source_manifest, args.loader, args.wasm, args.worker, args.output,
    )


if __name__ == "__main__":
    main()
