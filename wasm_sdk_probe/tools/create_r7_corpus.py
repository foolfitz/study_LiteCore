#!/usr/bin/env python3
"""Create and freeze the minimal self-generated R7 discovery corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_manifest_is_frozen(manifest_path: Path) -> bool:
    if not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("documents", []):
        path = manifest_path.parent / item["path"]
        if not path.is_file():
            raise RuntimeError(f"frozen corpus file is missing: {path}")
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"frozen corpus hash mismatch; use --force intentionally: {path}")
    return True


def convert_docx(soffice: str, source: Path, output: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="r7-corpus-") as temporary:
        temporary_path = Path(temporary)
        profile = temporary_path / "profile"
        input_path = temporary_path / "r7-plain.odt"
        shutil.copyfile(source, input_path)
        completed = subprocess.run(
            [
                soffice,
                "--headless",
                "--nologo",
                "--nodefault",
                "--nofirststartwizard",
                "--norestore",
                f"-env:UserInstallation={profile.resolve().as_uri()}",
                "--convert-to",
                "docx:Office Open XML Text",
                "--outdir",
                str(output),
                str(input_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        if completed.returncode != 0 or not (output / "r7-plain.docx").is_file():
            raise RuntimeError(
                "DOCX conversion failed: " + completed.stdout + "\n" + completed.stderr
            )
        return (completed.stdout + completed.stderr).strip()


def document_entry(
    identifier: str,
    path: Path,
    media_type: str,
    expected_open: str,
    *,
    anchors: list[str] | None = None,
    parent: dict[str, str] | None = None,
    derivation: str | None = None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "id": identifier,
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "mediaType": media_type,
        "source": {
            "kind": "project-generated",
            "path": "wasm_sdk_probe/test-docs/t1-plain-zh.odt",
            "license": "MPL-2.0",
        },
        "expectedOpen": expected_open,
        "mutationPolicy": "discovery-copy-only",
        "pageClass": "short",
        "anchors": anchors or [],
    }
    if parent:
        entry["parent"] = parent
    if derivation:
        entry["derivation"] = derivation
    return entry


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=project / "test-docs" / "r7")
    parser.add_argument("--soffice", default=shutil.which("soffice") or "soffice")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    manifest_path = output / "manifest.json"
    if not args.force and current_manifest_is_frozen(manifest_path):
        print(json.dumps({"manifest": str(manifest_path), "status": "frozen-valid"}))
        return
    output.mkdir(parents=True, exist_ok=True)

    source = project / "test-docs" / "t1-plain-zh.odt"
    odt = output / "r7-plain.odt"
    docx = output / "r7-plain.docx"
    shutil.copyfile(source, odt)
    conversion_log = convert_docx(args.soffice, source, output)

    corrupt_odt = output / "r7-corrupt-truncated.odt"
    corrupt_docx = output / "r7-corrupt-truncated.docx"
    odt_bytes = odt.read_bytes()
    docx_bytes = docx.read_bytes()
    corrupt_odt.write_bytes(odt_bytes[:-257])
    corrupt_docx.write_bytes(docx_bytes[:-257])
    unknown = output / "r7-unknown.bin"
    unknown.write_bytes(b"R7 deterministic unsupported-format fixture\n\x00\x01\x02\xff")

    odt_parent = {"path": odt.name, "sha256": sha256(odt)}
    docx_parent = {"path": docx.name, "sha256": sha256(docx)}
    anchor = ["Final line：ODT round-trip 完整性檢查。"]
    documents = [
        document_entry("r7-plain-odt", odt, "application/vnd.oasis.opendocument.text", "pass", anchors=anchor),
        document_entry("r7-plain-docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "discover", anchors=anchor),
        document_entry(
            "r7-corrupt-truncated-odt",
            corrupt_odt,
            "application/vnd.oasis.opendocument.text",
            "typed-failure",
            parent=odt_parent,
            derivation="remove the final 257 bytes from the parent, with no other transformation",
        ),
        document_entry(
            "r7-corrupt-truncated-docx",
            corrupt_docx,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "typed-failure",
            parent=docx_parent,
            derivation="remove the final 257 bytes from the parent, with no other transformation",
        ),
        document_entry(
            "r7-unknown-bin",
            unknown,
            "application/octet-stream",
            "typed-failure",
            derivation="literal bytes: R7 deterministic unsupported-format fixture plus LF 00 01 02 FF",
        ),
    ]
    manifest = {
        "schemaVersion": 1,
        "release": "R7-A",
        "frozenDate": "2026-08-02",
        "limits": {
            "maxFileBytes": 5 * 1024 * 1024,
            "maxZipEntries": 2048,
            "maxUncompressedBytes": 64 * 1024 * 1024,
            "maxCompressionRatio": 200,
        },
        "generator": {
            "sourceSha256": sha256(source),
            "soffice": subprocess.run(
                [args.soffice, "--version"], check=True, capture_output=True, text=True
            ).stdout.strip(),
            "conversionLog": conversion_log,
        },
        "documents": documents,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "documents": len(documents)}))


if __name__ == "__main__":
    main()
