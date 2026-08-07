#!/usr/bin/env python3
"""Build reproducible R5 profile manifests and split Emscripten resource packs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zlib
from pathlib import Path
from typing import Any, Iterable


FONT_PREFIX = "/instdir/share/fonts/truetype/"
CJK_FONT = "NotoSansCJK-Regular.ttc"
BASE_FONTS = {
    f"Liberation{family}-{style}.ttf"
    for family in ("Mono", "Sans", "Serif")
    for style in ("Regular", "Bold", "Italic", "BoldItalic")
}
FULL_CAPABILITIES = [
    "open-odt",
    "rgba-tile",
    "insert-text",
    "save-odt",
    "cancel-queued",
    "search",
    "selection-text",
    "replace-selection",
    "undo",
    "comments",
    "tracked-changes",
]
READER_CAPABILITIES = [
    "open-odt",
    "rgba-tile",
    "save-odt",
    "cancel-queued",
    "search",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gzip_size(path: Path) -> int:
    compressor = zlib.compressobj(level=9, wbits=31)
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(compressor.compress(block))
    return size + len(compressor.flush())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def hashed_copy(source: Path, destination: Path, stem: str, suffix: str) -> tuple[str, str]:
    digest = sha256_file(source)
    filename = f"{stem}.{digest[:16]}{suffix}"
    target = destination / filename
    if not target.exists():
        shutil.copyfile(source, target)
    elif sha256_file(target) != digest:
        raise RuntimeError(f"existing hashed artifact has wrong contents: {target}")
    return filename, digest


def classify(files: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {
        "base": [],
        "cjk": [],
        "fallback-fonts": [],
    }
    found_base_fonts: set[str] = set()
    found_cjk = False
    seen_paths: set[str] = set()
    previous_end = 0
    for entry in files:
        filename = entry.get("filename")
        start = entry.get("start")
        end = entry.get("end")
        if (
            not isinstance(filename, str)
            or filename in seen_paths
            or not isinstance(start, int)
            or not isinstance(end, int)
            or start != previous_end
            or end <= start
        ):
            raise RuntimeError(f"invalid or non-contiguous source metadata entry: {entry}")
        seen_paths.add(filename)
        previous_end = end
        if not filename.startswith(FONT_PREFIX):
            group = "base"
        else:
            basename = Path(filename).name
            if basename in BASE_FONTS:
                group = "base"
                found_base_fonts.add(basename)
            elif basename == CJK_FONT:
                group = "cjk"
                found_cjk = True
            else:
                group = "fallback-fonts"
        groups[group].append(entry)
    if found_base_fonts != BASE_FONTS:
        missing = sorted(BASE_FONTS - found_base_fonts)
        raise RuntimeError(f"full metadata is missing required base fonts: {missing}")
    if not found_cjk:
        raise RuntimeError(f"full metadata is missing required CJK font: {CJK_FONT}")
    return groups


def create_pack(
    source_data: Path,
    entries: Iterable[dict[str, Any]],
    output_dir: Path,
    stem: str,
) -> dict[str, Any]:
    temporary_data = output_dir / f".{stem}.building.data"
    packed_entries: list[dict[str, Any]] = []
    offset = 0
    with source_data.open("rb") as source, temporary_data.open("wb") as target:
        for entry in entries:
            size = entry["end"] - entry["start"]
            source.seek(entry["start"])
            payload = source.read(size)
            if len(payload) != size:
                raise RuntimeError(f"short read for {entry['filename']}")
            target.write(payload)
            packed_entries.append({
                "filename": entry["filename"],
                "start": offset,
                "end": offset + size,
            })
            offset += size

    data_hash = sha256_file(temporary_data)
    data_name = f"{stem}.{data_hash[:16]}.data"
    data_path = output_dir / data_name
    if data_path.exists():
        if sha256_file(data_path) != data_hash:
            raise RuntimeError(f"existing hashed resource has wrong contents: {data_path}")
        temporary_data.unlink()
    else:
        temporary_data.replace(data_path)

    metadata = {
        "files": packed_entries,
        "remote_package_size": offset,
        "sha256": data_hash,
    }
    temporary_metadata = output_dir / f".{stem}.building.metadata"
    write_json(temporary_metadata, metadata)
    metadata_hash = sha256_file(temporary_metadata)
    metadata_name = f"{stem}.{metadata_hash[:16]}.metadata"
    metadata_path = output_dir / metadata_name
    if metadata_path.exists():
        if sha256_file(metadata_path) != metadata_hash:
            raise RuntimeError(f"existing hashed metadata has wrong contents: {metadata_path}")
        temporary_metadata.unlink()
    else:
        temporary_metadata.replace(metadata_path)

    return {
        "id": stem,
        "data": data_name,
        "metadata": metadata_name,
        "bytes": offset,
        "files": len(packed_entries),
        "sha256": data_hash,
        "metadataSha256": metadata_hash,
        "dataPath": data_path,
        "metadataPath": metadata_path,
    }


def artifact_metrics(path: Path) -> dict[str, Any]:
    return {
        "file": path.name,
        "rawBytes": path.stat().st_size,
        "gzip9Bytes": gzip_size(path),
        "sha256": sha256_file(path),
    }


def prune_generated(directory: Path, pattern: re.Pattern[str], keep: set[str]) -> None:
    """Remove only stale content-hashed files produced by this script."""
    for path in directory.iterdir():
        if path.is_file() and pattern.fullmatch(path.name) and path.name not in keep:
            path.unlink()


def relative_resource(pack: dict[str, Any], *, startup: bool, purpose: str) -> dict[str, Any]:
    return {
        "id": pack["id"],
        "data": f"../resources/{pack['data']}",
        "metadata": f"../resources/{pack['metadata']}",
        "bytes": pack["bytes"],
        "sha256": pack["sha256"],
        "loadAtStartup": startup,
        "purpose": purpose,
    }


def build_profile(
    *,
    profile_root: Path,
    resources_root: Path,
    name: str,
    loader: Path,
    wasm: Path,
    worker: Path,
    base_pack: dict[str, Any],
    capabilities: list[str],
    capability_bits: int,
    core_commit: str,
    resource_packs: list[dict[str, Any]],
) -> dict[str, Any]:
    target = profile_root / name
    target.mkdir(parents=True, exist_ok=True)
    loader_name, loader_hash = hashed_copy(loader, target, "probe", ".js")
    wasm_name, wasm_hash = hashed_copy(wasm, target, "probe", ".wasm")
    shutil.copyfile(worker, target / "sdk-worker.js")
    manifest = {
        "sdkVersion": "0.5.0-r5",
        "protocolVersion": 1,
        "abiVersion": 65537,
        "abiVersionText": "1.1",
        "providerContractVersion": "1.0",
        "coreCommit": core_commit,
        "profile": name,
        "capabilities": capabilities,
        "expectedCapabilityBits": capability_bits,
        "artifactFiles": {
            "probe.js": loader_name,
            "probe.wasm": wasm_name,
            "soffice.data": f"../resources/{base_pack['data']}",
            "soffice.data.js.metadata": f"../resources/{base_pack['metadata']}",
        },
        "resourcePacks": resource_packs,
    }
    write_json(target / "sdk-manifest.json", manifest)
    startup_resource_bytes = base_pack["bytes"] + sum(
        pack["bytes"] for pack in resource_packs if pack["loadAtStartup"]
    )
    return {
        "profile": name,
        "capabilityBits": capability_bits,
        "capabilities": capabilities,
        "loader": artifact_metrics(target / loader_name),
        "wasm": artifact_metrics(target / wasm_name),
        "startupResourceBytes": startup_resource_bytes,
        "optionalResourceBytes": sum(
            pack["bytes"] for pack in resource_packs if not pack["loadAtStartup"]
        ),
        "loaderSha256": loader_hash,
        "wasmSha256": wasm_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-loader", type=Path, required=True)
    parser.add_argument("--full-wasm", type=Path, required=True)
    parser.add_argument("--review-loader", type=Path, required=True)
    parser.add_argument("--review-wasm", type=Path, required=True)
    parser.add_argument("--reader-loader", type=Path, required=True)
    parser.add_argument("--reader-wasm", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--core-commit", required=True)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    resources_root = args.output / "resources"
    resources_root.mkdir(parents=True, exist_ok=True)
    source_metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    files = source_metadata.get("files")
    if not isinstance(files, list) or source_metadata.get("remote_package_size") != args.data.stat().st_size:
        raise RuntimeError("source data and metadata size do not match")
    groups = classify(files)
    if sum(len(entries) for entries in groups.values()) != len(files):
        raise RuntimeError("resource groups do not cover the source metadata")
    paths = [entry["filename"] for entries in groups.values() for entry in entries]
    if len(paths) != len(set(paths)):
        raise RuntimeError("resource groups overlap")

    packs = {
        name: create_pack(args.data, entries, resources_root, f"{name}-r5")
        for name, entries in groups.items()
    }
    if sum(pack["bytes"] for pack in packs.values()) != args.data.stat().st_size:
        raise RuntimeError("resource pack byte totals do not equal the full source")

    full_data_name, full_data_hash = hashed_copy(
        args.data, resources_root, "full-qa-r5", ".data"
    )
    full_metadata_name, full_metadata_hash = hashed_copy(
        args.metadata, resources_root, "full-qa-r5", ".metadata"
    )
    full_pack = {
        "id": "full-qa-r5",
        "data": full_data_name,
        "metadata": full_metadata_name,
        "bytes": args.data.stat().st_size,
        "files": len(files),
        "sha256": full_data_hash,
        "metadataSha256": full_metadata_hash,
        "dataPath": resources_root / full_data_name,
        "metadataPath": resources_root / full_metadata_name,
    }

    provider_capabilities = [
        "provider-contract-1.0",
        "provider-worker",
        "validated-provider-operation",
    ]
    profiles = [
        build_profile(
            profile_root=args.output,
            resources_root=resources_root,
            name="full-qa",
            loader=args.full_loader,
            wasm=args.full_wasm,
            worker=args.worker,
            base_pack=full_pack,
            capabilities=FULL_CAPABILITIES + provider_capabilities,
            capability_bits=2047,
            core_commit=args.core_commit,
            resource_packs=[],
        ),
        build_profile(
            profile_root=args.output,
            resources_root=resources_root,
            name="writer-review",
            loader=args.review_loader,
            wasm=args.review_wasm,
            worker=args.worker,
            base_pack=packs["base"],
            capabilities=FULL_CAPABILITIES + provider_capabilities,
            capability_bits=2047,
            core_commit=args.core_commit,
            resource_packs=[
                relative_resource(packs["cjk"], startup=True, purpose="CJK corpus"),
                relative_resource(
                    packs["fallback-fonts"], startup=False,
                    purpose="optional complex-script and fidelity fallback",
                ),
            ],
        ),
        build_profile(
            profile_root=args.output,
            resources_root=resources_root,
            name="writer-reader",
            loader=args.reader_loader,
            wasm=args.reader_wasm,
            worker=args.worker,
            base_pack=packs["base"],
            capabilities=READER_CAPABILITIES,
            capability_bits=59,
            core_commit=args.core_commit,
            resource_packs=[
                relative_resource(packs["cjk"], startup=True, purpose="CJK corpus"),
                relative_resource(
                    packs["fallback-fonts"], startup=False,
                    purpose="optional complex-script and fidelity fallback",
                ),
            ],
        ),
    ]

    for profile in profiles:
        prune_generated(
            args.output / profile["profile"],
            re.compile(r"probe\.[0-9a-f]{16}\.(?:js|wasm)"),
            {profile["loader"]["file"], profile["wasm"]["file"]},
        )
    all_packs = [full_pack, *packs.values()]
    prune_generated(
        resources_root,
        re.compile(
            r"(?:full-qa-r5|base-r5|cjk-r5|fallback-fonts-r5)"
            r"\.[0-9a-f]{16}\.(?:data|metadata)"
        ),
        {filename for pack in all_packs for filename in (pack["data"], pack["metadata"])},
    )

    pack_inventory = {}
    for name, pack in {"full-qa": full_pack, **packs}.items():
        pack_inventory[name] = {
            "files": pack["files"],
            "data": artifact_metrics(pack["dataPath"]),
            "metadata": artifact_metrics(pack["metadataPath"]),
        }
    report = {
        "schemaVersion": 1,
        "sdkVersion": "0.5.0-r5",
        "coreCommit": args.core_commit,
        "source": {
            "files": len(files),
            "bytes": args.data.stat().st_size,
            "sha256": sha256_file(args.data),
        },
        "proof": {
            "groupsDisjoint": len(paths) == len(set(paths)),
            "groupsCoverSource": len(paths) == len(files),
            "packBytesEqualSource": sum(pack["bytes"] for pack in packs.values())
            == args.data.stat().st_size,
        },
        "packs": pack_inventory,
        "profiles": profiles,
        "writer-automation": {
            "status": "not-shippable",
            "reason": "controlled automation operations and permission contract are undefined",
            "binaryProduced": False,
        },
    }
    write_json(args.output / "r5-inventory.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
