#!/usr/bin/env python3
"""Closed R8-A release inventory and manifest validation helpers."""

from __future__ import annotations

import copy
import hashlib
import json
import posixpath
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit


SCHEMA_VERSION = 1
PROFILE = "writer-review"
ENTRY = "r7-reference.html"
RELEASE_ID_PATTERN = re.compile(r"^writer-review-[0-9a-f]{16}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
HASHED_FILENAME_PATTERN = re.compile(r"\.([0-9a-f]{12,64})\.[^.]+$")

ARTIFACT_FIELDS = {
    "role",
    "url",
    "sha256",
    "rawBytes",
    "mediaType",
    "contentEncoding",
    "required",
    "cachePolicy",
}
MANIFEST_FIELDS = {
    "schemaVersion",
    "releaseId",
    "createdAt",
    "sdkVersion",
    "profile",
    "coreCommit",
    "entry",
    "capabilities",
    "artifacts",
}

# The order is part of the R8-A discovery fixture.  It is intentionally closed:
# adding an application dependency must update this inventory and its tests.
ROLE_ORDER = (
    "entry-html",
    "stylesheet",
    "app-module",
    "document-sdk",
    "input-adapter",
    "clipboard-adapter",
    "page-navigation",
    "sdk-worker",
    "sdk-manifest",
    "wasm-loader",
    "wasm-binary",
    "base-data",
    "base-metadata",
    "cjk-data",
    "cjk-metadata",
    "fallback-data",
    "fallback-metadata",
)

STATIC_SPECS: dict[str, tuple[str, str, bool, str]] = {
    "entry-html": ("r7-reference.html", "text/html; charset=utf-8", True, "entry"),
    "stylesheet": ("r7.css", "text/css; charset=utf-8", True, "entry"),
    "app-module": ("r7-reference-app.js", "text/javascript; charset=utf-8", True, "entry"),
    "document-sdk": ("document-sdk.js", "text/javascript; charset=utf-8", True, "entry"),
    "input-adapter": ("input/input-adapter.js", "text/javascript; charset=utf-8", True, "entry"),
    "clipboard-adapter": ("input/clipboard-adapter.js", "text/javascript; charset=utf-8", True, "entry"),
    "page-navigation": ("r7/page-navigation.js", "text/javascript; charset=utf-8", True, "entry"),
    "sdk-worker": (
        "profiles/writer-review-r6/sdk-worker.js",
        "text/javascript; charset=utf-8",
        True,
        "entry",
    ),
    "sdk-manifest": (
        "profiles/writer-review-r6/sdk-manifest.json",
        "application/json; charset=utf-8",
        True,
        "entry",
    ),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def manifest_identity_seed(manifest: dict[str, Any]) -> dict[str, Any]:
    seed = copy.deepcopy(manifest)
    seed.pop("releaseId", None)
    return seed


def expected_release_id(manifest: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical_json_bytes(manifest_identity_seed(manifest))).hexdigest()
    return f"writer-review-{digest[:16]}"


def safe_relative_url(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 512 or "\\" in value:
        return False
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or value.startswith("/"):
        return False
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", value):
        return False
    parts = PurePosixPath(value).parts
    return bool(parts) and all(part not in {"", ".", ".."} for part in parts)


def _dynamic_specs(profile_manifest: dict[str, Any]) -> dict[str, tuple[str, str, bool, str]]:
    artifact_files = profile_manifest["artifactFiles"]
    packs = {pack["id"]: pack for pack in profile_manifest["resourcePacks"]}
    cjk = packs["cjk-r5"]
    fallback = packs["fallback-fonts-r5"]

    def profile_path(relative: str) -> str:
        normalized = posixpath.normpath(f"profiles/writer-review-r6/{relative}")
        if normalized.startswith("../") or normalized.startswith("/"):
            raise RuntimeError(f"profile artifact escapes dist: {relative}")
        return normalized

    return {
        "wasm-loader": (
            profile_path(artifact_files["probe.js"]),
            "text/javascript; charset=utf-8",
            True,
            "immutable",
        ),
        "wasm-binary": (
            profile_path(artifact_files["probe.wasm"]),
            "application/wasm",
            True,
            "immutable",
        ),
        "base-data": (
            profile_path(artifact_files["soffice.data"]),
            "application/octet-stream",
            True,
            "immutable",
        ),
        "base-metadata": (
            profile_path(artifact_files["soffice.data.js.metadata"]),
            "application/json; charset=utf-8",
            True,
            "immutable",
        ),
        "cjk-data": (
            profile_path(cjk["data"]),
            "application/octet-stream",
            True,
            "immutable",
        ),
        "cjk-metadata": (
            profile_path(cjk["metadata"]),
            "application/json; charset=utf-8",
            True,
            "immutable",
        ),
        "fallback-data": (
            profile_path(fallback["data"]),
            "application/octet-stream",
            False,
            "optional-pack",
        ),
        "fallback-metadata": (
            profile_path(fallback["metadata"]),
            "application/json; charset=utf-8",
            False,
            "optional-pack",
        ),
    }


def artifact_specs(profile_manifest: dict[str, Any]) -> dict[str, tuple[str, str, bool, str]]:
    specs = {**STATIC_SPECS, **_dynamic_specs(profile_manifest)}
    if set(specs) != set(ROLE_ORDER):
        raise RuntimeError("R8 release role inventory does not match ROLE_ORDER")
    return specs


def build_release_manifest(project: Path, created_at: str) -> dict[str, Any]:
    project = project.resolve()
    dist = project / "dist"
    profile_manifest_path = dist / "profiles" / "writer-review-r6" / "sdk-manifest.json"
    profile_manifest = load_json(profile_manifest_path)
    specs = artifact_specs(profile_manifest)

    artifacts: list[dict[str, Any]] = []
    for role in ROLE_ORDER:
        relative, media_type, required, cache_policy = specs[role]
        path = dist / relative
        if not path.is_file():
            raise FileNotFoundError(f"R8 release artifact is missing: {path}")
        artifacts.append({
            "role": role,
            "url": relative,
            "sha256": sha256_file(path),
            "rawBytes": path.stat().st_size,
            "mediaType": media_type,
            "contentEncoding": "identity",
            "required": required,
            "cachePolicy": cache_policy,
        })

    manifest: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "releaseId": "",
        "createdAt": created_at,
        "sdkVersion": profile_manifest["sdkVersion"],
        "profile": PROFILE,
        "coreCommit": profile_manifest["coreCommit"],
        "entry": ENTRY,
        "capabilities": sorted(profile_manifest["capabilities"]),
        "artifacts": artifacts,
    }
    manifest["releaseId"] = expected_release_id(manifest)
    return manifest


def _valid_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def validate_release_manifest(manifest: Any, dist_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    dist_root = dist_root.resolve()
    if not isinstance(manifest, dict):
        return {"schemaVersion": SCHEMA_VERSION, "errors": ["manifest must be an object"], "pass": False}

    try:
        expected_specs = artifact_specs(load_json(
            dist_root / "profiles" / "writer-review-r6" / "sdk-manifest.json"
        ))
    except Exception as error:  # noqa: BLE001 - validation reports source drift
        expected_specs = STATIC_SPECS
        errors.append(f"cannot load the frozen writer-review source manifest: {error}")

    if set(manifest) != MANIFEST_FIELDS:
        errors.append(
            f"manifest fields differ: missing={sorted(MANIFEST_FIELDS - set(manifest))} "
            f"extra={sorted(set(manifest) - MANIFEST_FIELDS)}"
        )
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("schemaVersion must be 1")
    if manifest.get("profile") != PROFILE:
        errors.append("profile must be writer-review")
    if manifest.get("entry") != ENTRY:
        errors.append(f"entry must be {ENTRY}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("coreCommit", ""))):
        errors.append("coreCommit must be a 40-character lowercase hex commit")
    if not _valid_datetime(manifest.get("createdAt")):
        errors.append("createdAt must be an offset-aware ISO-8601 date-time")
    if not isinstance(manifest.get("sdkVersion"), str) or not manifest.get("sdkVersion"):
        errors.append("sdkVersion must be a non-empty string")

    capabilities = manifest.get("capabilities")
    if (
        not isinstance(capabilities, list)
        or not capabilities
        or any(not isinstance(item, str) or not item for item in capabilities)
        or capabilities != sorted(set(capabilities))
    ):
        errors.append("capabilities must be a non-empty sorted unique string list")

    artifacts = manifest.get("artifacts")
    role_counts: dict[str, int] = {}
    checked_artifacts: list[dict[str, Any]] = []
    if not isinstance(artifacts, list):
        errors.append("artifacts must be an array")
        artifacts = []

    for index, artifact in enumerate(artifacts):
        prefix = f"artifact[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if set(artifact) != ARTIFACT_FIELDS:
            errors.append(f"{prefix} fields differ from the closed schema")
        role = artifact.get("role")
        if role not in ROLE_ORDER:
            errors.append(f"{prefix} has unknown role {role!r}")
            continue
        role_counts[role] = role_counts.get(role, 0) + 1
        url = artifact.get("url")
        if not safe_relative_url(url):
            errors.append(f"{prefix} has an unsafe relative URL")
            continue
        expected_spec = expected_specs.get(role)
        path = (dist_root / str(url)).resolve()
        if not path.is_relative_to(dist_root):
            errors.append(f"{prefix} escapes the dist root")
            continue
        exists = path.is_file()
        actual_hash = sha256_file(path) if exists else ""
        actual_size = path.stat().st_size if exists else 0
        if not exists:
            errors.append(f"{prefix} is missing: {url}")
        if not SHA256_PATTERN.fullmatch(str(artifact.get("sha256", ""))):
            errors.append(f"{prefix} has an invalid SHA-256")
        elif exists and artifact["sha256"] != actual_hash:
            errors.append(f"{prefix} SHA-256 does not match {url}")
        if not isinstance(artifact.get("rawBytes"), int) or artifact.get("rawBytes", 0) <= 0:
            errors.append(f"{prefix} has invalid rawBytes")
        elif exists and artifact["rawBytes"] != actual_size:
            errors.append(f"{prefix} rawBytes does not match {url}")
        if artifact.get("contentEncoding") != "identity":
            errors.append(f"{prefix} contentEncoding must be identity in R8-A")
        if artifact.get("cachePolicy") not in {"entry", "immutable", "optional-pack"}:
            errors.append(f"{prefix} has an invalid cachePolicy")
        if not isinstance(artifact.get("required"), bool):
            errors.append(f"{prefix} required must be boolean")

        match = HASHED_FILENAME_PATTERN.search(str(url))
        if artifact.get("cachePolicy") in {"immutable", "optional-pack"}:
            if not match or (actual_hash and not actual_hash.startswith(match.group(1))):
                errors.append(f"{prefix} content-hashed filename does not match its bytes")
        if expected_spec:
            expected_url, expected_media, expected_required, expected_cache = expected_spec
            if (url, artifact.get("mediaType"), artifact.get("required"), artifact.get("cachePolicy")) != (
                expected_url,
                expected_media,
                expected_required,
                expected_cache,
            ):
                errors.append(f"{prefix} differs from the frozen role contract")
        checked_artifacts.append({
            "role": role,
            "url": url,
            "exists": exists,
            "actualBytes": actual_size,
            "actualSha256": actual_hash,
        })

    if set(role_counts) != set(ROLE_ORDER) or any(count != 1 for count in role_counts.values()):
        missing = sorted(set(ROLE_ORDER) - set(role_counts))
        duplicate = sorted(role for role, count in role_counts.items() if count != 1)
        errors.append(f"artifact roles must occur exactly once: missing={missing} duplicate={duplicate}")
    elif [artifact.get("role") for artifact in artifacts] != list(ROLE_ORDER):
        errors.append("artifact roles must use the frozen deterministic order")

    release_id = str(manifest.get("releaseId", ""))
    if not RELEASE_ID_PATTERN.fullmatch(release_id):
        errors.append("releaseId has an invalid format")
    else:
        computed = expected_release_id(manifest)
        if release_id != computed:
            errors.append(f"releaseId does not match canonical manifest identity ({computed})")

    return {
        "schemaVersion": SCHEMA_VERSION,
        "releaseId": manifest.get("releaseId"),
        "manifestSha256": hashlib.sha256(canonical_json_bytes(manifest)).hexdigest(),
        "roles": list(role_counts),
        "artifacts": checked_artifacts,
        "errors": errors,
        "pass": not errors,
    }
