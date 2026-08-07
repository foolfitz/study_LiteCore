#!/usr/bin/env python3
"""Build and validate deterministic R8-B standard/full-fidelity bundles."""

from __future__ import annotations

import copy
import gzip
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from r8_release import (
    ARTIFACT_FIELDS,
    MANIFEST_FIELDS,
    ROLE_ORDER,
    canonical_json_bytes,
    expected_release_id,
    load_json,
    safe_relative_url,
    sha256_file,
    write_json,
)


POLICIES = ("standard", "full-fidelity")
FALLBACK_ROLES = {"fallback-data", "fallback-metadata"}
CREATED_AT = "2026-08-04T00:00:00+08:00"
RELEASE_HANDSHAKE_MARKER = "__r8_release_id"
LOCATE_FILE_CLOSED_MARKER = "R8_UNKNOWN_LOGICAL_ARTIFACT"
LOCATE_FILE_SOURCE = (
    'locateFile: (path) => new URL(artifactFiles[path] || path, self.location.href).href,'
)
LOCATE_FILE_REPLACEMENT = '''locateFile: (path) => {
        const mapped = artifactFiles[path];
        if (typeof mapped !== "string" || !mapped)
          throw new Error(`R8_UNKNOWN_LOGICAL_ARTIFACT: ${path}`);
        return new URL(mapped, self.location.href).href;
      },'''
WORKER_PRELUDE = '''"use strict";
const __r8_release_id = (() => {
  const match = self.location.pathname.match(/\\/releases\\/(writer-review-[0-9a-f]{16})\\//);
  return match ? match[1] : "unversioned-r8-worker";
})();
const __r8_artifact_origin = (() => {
  const value = new URL(self.location.href).searchParams.get("artifactOrigin");
  if (!value)
    return self.location.origin;
  const parsed = new URL(value);
  if (!/^https?:$/.test(parsed.protocol) || parsed.username || parsed.password
      || parsed.pathname !== "/" || parsed.search || parsed.hash)
    return "invalid-r8-artifact-origin";
  return parsed.origin;
})();
const __r8_original_fetch = self.fetch.bind(self);
self.fetch = async (input, init) => {
  const url = new URL(input instanceof Request ? input.url : input, self.location.href);
  const response = await __r8_original_fetch(input, init);
  if (!url.pathname.endsWith("/sdk-manifest.json")
      || __r8_artifact_origin === self.location.origin)
    return response;
  if (!response.ok)
    return response;
  const manifest = await response.json();
  const toArtifactOrigin = (value) => {
    const resolved = new URL(value, self.location.href);
    return `${__r8_artifact_origin}${resolved.pathname}`;
  };
  for (const key of ["probe.wasm", "soffice.data", "soffice.data.js.metadata"])
    manifest.artifactFiles[key] = toArtifactOrigin(manifest.artifactFiles[key]);
  for (const pack of manifest.resourcePacks || []) {
    pack.data = toArtifactOrigin(pack.data);
    pack.metadata = toArtifactOrigin(pack.metadata);
  }
  const headers = new Headers(response.headers);
  headers.set("Content-Type", "application/json; charset=utf-8");
  headers.delete("Content-Length");
  headers.delete("Content-Encoding");
  return new Response(JSON.stringify(manifest), {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
};
const __r8_original_post_message = self.postMessage.bind(self);
self.postMessage = (message, transfer = []) => {
  const isHandshake = message?.kind === "response" && message?.ok === true
    && typeof message?.result?.sdkVersion === "string"
    && typeof message?.result?.profile === "string"
    && Number.isInteger(message?.result?.abiVersion);
  const output = isHandshake
    ? { ...message, result: { ...message.result, releaseId: __r8_release_id } }
    : message;
  return __r8_original_post_message(output, transfer);
};
'''.encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def gzip_bytes(value: bytes) -> bytes:
    return gzip.compress(value, compresslevel=9, mtime=0)


def canonical_sdk_manifest(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sdk_manifest_for_policy(source: bytes, policy: str) -> bytes:
    if policy not in POLICIES:
        raise ValueError(f"unknown R8 fidelity policy: {policy}")
    if policy == "standard":
        return source
    manifest = json.loads(source)
    packs = manifest.get("resourcePacks")
    if not isinstance(packs, list):
        raise RuntimeError("SDK manifest has no resourcePacks array")
    fallback = [item for item in packs if item.get("id") == "fallback-fonts-r5"]
    if len(fallback) != 1:
        raise RuntimeError("SDK manifest must contain exactly one fallback-fonts-r5 pack")
    fallback[0]["loadAtStartup"] = True
    return canonical_sdk_manifest(manifest)


def worker_for_release(source: bytes) -> bytes:
    if RELEASE_HANDSHAKE_MARKER.encode() in source:
        raise RuntimeError("source worker already contains the R8 release handshake prelude")
    source_text = source.decode("utf-8")
    if source_text.count(LOCATE_FILE_SOURCE) != 1:
        raise RuntimeError("source worker locateFile shape differs from the closed R8-B transform")
    closed_worker = source_text.replace(LOCATE_FILE_SOURCE, LOCATE_FILE_REPLACEMENT)
    return WORKER_PRELUDE + closed_worker.encode("utf-8")


def source_bytes(project: Path, artifact: dict[str, Any], policy: str,
                 variant_marker: str | None = None) -> bytes:
    path = project / "dist" / artifact["url"]
    value = path.read_bytes()
    if artifact["role"] == "sdk-worker":
        return worker_for_release(value)
    if artifact["role"] == "sdk-manifest":
        return sdk_manifest_for_policy(value, policy)
    if artifact["role"] == "app-module" and variant_marker is not None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", variant_marker):
            raise ValueError(f"unsafe R8 release variant marker: {variant_marker}")
        return value + f"\n/* OXSDK_R8_RELEASE_VARIANT:{variant_marker} */\n".encode("ascii")
    return value


def bundle_manifest(project: Path, policy: str, values: dict[str, bytes]) -> dict[str, Any]:
    source = load_json(project / "dist" / "r8" / "release-manifest.json")
    manifest = copy.deepcopy(source)
    manifest["createdAt"] = CREATED_AT
    artifacts = []
    for artifact in source["artifacts"]:
        item = copy.deepcopy(artifact)
        value = values[item["role"]]
        item["rawBytes"] = len(value)
        item["sha256"] = sha256_bytes(value)
        if policy == "full-fidelity" and item["role"] in FALLBACK_ROLES:
            item["required"] = True
            item["cachePolicy"] = "immutable"
        artifacts.append(item)
    manifest["artifacts"] = artifacts
    manifest["releaseId"] = expected_release_id(manifest)
    return manifest


def expected_bundle_files(manifest: dict[str, Any]) -> set[str]:
    files = {"release-manifest.json", "compression-index.json"}
    for artifact in manifest["artifacts"]:
        files.add(artifact["url"])
        files.add(f"{artifact['url']}.gz")
    return files


def write_bundle(staging: Path, manifest: dict[str, Any], policy: str,
                 values: dict[str, bytes]) -> dict[str, Any]:
    representations = []
    for artifact in manifest["artifacts"]:
        value = values[artifact["role"]]
        path = staging / artifact["url"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        encoded = gzip_bytes(value)
        gzip_path = Path(f"{path}.gz")
        gzip_path.write_bytes(encoded)
        representations.append({
            "role": artifact["role"],
            "url": artifact["url"],
            "decodedBytes": len(value),
            "decodedSha256": sha256_bytes(value),
            "identity": {"encodedBytes": len(value), "encodedSha256": sha256_bytes(value)},
            "gzip": {
                "storagePath": f"{artifact['url']}.gz",
                "encodedBytes": len(encoded),
                "encodedSha256": sha256_bytes(encoded),
            },
        })
    compression = {
        "schemaVersion": 1,
        "releaseId": manifest["releaseId"],
        "policy": policy,
        "hashBoundary": "decoded-artifact-bytes",
        "gzip": {"implementation": "python-gzip", "compresslevel": 9, "mtime": 0},
        "artifacts": representations,
    }
    write_json(staging / "release-manifest.json", manifest)
    write_json(staging / "compression-index.json", compression)
    return compression


def tree_identity(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256_file(path)
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def install_staging(staging: Path, target: Path) -> None:
    if target.exists():
        if tree_identity(staging) != tree_identity(target):
            raise RuntimeError(f"refusing to overwrite non-identical release directory: {target}")
        shutil.rmtree(staging)
        return
    staging.rename(target)


def build_policy_bundle(project: Path, releases_root: Path, policy: str,
                        variant_marker: str | None = None) -> dict[str, Any]:
    if policy not in POLICIES:
        raise ValueError(f"unknown R8 fidelity policy: {policy}")
    source = load_json(project / "dist" / "r8" / "release-manifest.json")
    values = {
        item["role"]: source_bytes(project, item, policy, variant_marker)
        for item in source["artifacts"]
    }
    manifest = bundle_manifest(project, policy, values)
    releases_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".r8-{policy}-", dir=releases_root))
    try:
        compression = write_bundle(staging, manifest, policy, values)
        target = releases_root / manifest["releaseId"]
        install_staging(staging, target)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    result = validate_bundle(releases_root / manifest["releaseId"], policy)
    if not result["pass"]:
        raise RuntimeError(f"generated R8 bundle failed validation: {result['errors']}")
    return {
        "policy": policy,
        "releaseId": manifest["releaseId"],
        "manifestUrl": f"releases/{manifest['releaseId']}/release-manifest.json",
        "manifestSha256": sha256_file(releases_root / manifest["releaseId"] / "release-manifest.json"),
        "requiredRawBytes": sum(item["rawBytes"] for item in manifest["artifacts"] if item["required"]),
        "gzipEncodedBytes": sum(item["gzip"]["encodedBytes"] for item in compression["artifacts"]),
        "pass": True,
    }


def build_bundles(project: Path, releases_root: Path) -> dict[str, Any]:
    previous_ids: set[str] = set()
    previous_index = releases_root / "index.json"
    if previous_index.is_file():
        try:
            previous_ids = {
                str(item["releaseId"]) for item in load_json(previous_index).get("releases", [])
                if isinstance(item, dict)
            }
        except Exception:
            previous_ids = set()
    releases = [build_policy_bundle(project, releases_root, policy) for policy in POLICIES]
    index = {
        "schemaVersion": 1,
        "release": "R8-B-versioned-artifact-delivery",
        "createdAt": CREATED_AT,
        "releases": releases,
        "pass": all(item["pass"] for item in releases),
    }
    write_json(releases_root / "index.json", index)
    current_ids = {item["releaseId"] for item in releases}
    for release_id in sorted(previous_ids - current_ids):
        target = releases_root / release_id
        if (target.parent == releases_root and target.is_dir()
                and release_id.startswith("writer-review-") and len(release_id) == 30):
            shutil.rmtree(target)
    return index


def validate_sdk_policy(path: Path, policy: str, errors: list[str]) -> None:
    try:
        manifest = load_json(path)
        fallback = [item for item in manifest["resourcePacks"] if item.get("id") == "fallback-fonts-r5"]
        if len(fallback) != 1:
            errors.append("SDK manifest fallback pack count differs from one")
        elif fallback[0].get("loadAtStartup") is not (policy == "full-fidelity"):
            errors.append("SDK manifest fallback loadAtStartup differs from policy")
    except Exception as error:  # noqa: BLE001 - validation reports all drift
        errors.append(f"SDK manifest validation failed: {error}")


def validate_bundle(root: Path, policy: str) -> dict[str, Any]:
    errors: list[str] = []
    try:
        manifest = load_json(root / "release-manifest.json")
        compression = load_json(root / "compression-index.json")
    except Exception as error:  # noqa: BLE001
        return {"policy": policy, "errors": [f"bundle metadata load failed: {error}"], "pass": False}
    if set(manifest) != MANIFEST_FIELDS:
        errors.append("release manifest fields differ from the closed schema")
    if manifest.get("releaseId") != expected_release_id(manifest):
        errors.append("release ID does not match canonical manifest identity")
    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), list) else []
    if [item.get("role") for item in artifacts] != list(ROLE_ORDER):
        errors.append("artifact roles or order differ from the frozen graph")
    seen: set[str] = set()
    by_role: dict[str, dict[str, Any]] = {}
    for item in artifacts:
        role = item.get("role")
        if set(item) != ARTIFACT_FIELDS:
            errors.append(f"{role}: fields differ")
            continue
        if role in seen:
            errors.append(f"{role}: duplicate role")
        seen.add(role)
        by_role[str(role)] = item
        if not safe_relative_url(item.get("url")):
            errors.append(f"{role}: unsafe URL")
            continue
        path = root / item["url"]
        if not path.is_file():
            errors.append(f"{role}: artifact is missing")
            continue
        if item.get("rawBytes") != path.stat().st_size:
            errors.append(f"{role}: decoded size mismatch")
        if item.get("sha256") != sha256_file(path):
            errors.append(f"{role}: decoded hash mismatch")
        expected_required = role not in FALLBACK_ROLES or policy == "full-fidelity"
        if item.get("required") is not expected_required:
            errors.append(f"{role}: required differs from fidelity policy")
    worker = root / by_role.get("sdk-worker", {}).get("url", "missing")
    if not worker.is_file() or RELEASE_HANDSHAKE_MARKER.encode() not in worker.read_bytes()[:4096]:
        errors.append("SDK Worker lacks the release handshake prelude")
    if not worker.is_file() or LOCATE_FILE_CLOSED_MARKER.encode() not in worker.read_bytes():
        errors.append("SDK Worker locateFile does not reject unknown logical artifacts")
    sdk_manifest = root / by_role.get("sdk-manifest", {}).get("url", "missing")
    validate_sdk_policy(sdk_manifest, policy, errors)

    representations = compression.get("artifacts", [])
    by_compression = {item.get("role"): item for item in representations}
    if set(by_compression) != set(ROLE_ORDER):
        errors.append("compression index roles differ from the frozen graph")
    for role, artifact in by_role.items():
        entry = by_compression.get(role, {})
        path = root / artifact.get("url", "missing")
        gzip_path = root / entry.get("gzip", {}).get("storagePath", "missing")
        if not gzip_path.is_file():
            errors.append(f"{role}: gzip representation is missing")
            continue
        encoded = gzip_path.read_bytes()
        try:
            decoded = gzip.decompress(encoded)
        except Exception as error:  # noqa: BLE001
            errors.append(f"{role}: gzip decode failed: {error}")
            continue
        if path.is_file() and decoded != path.read_bytes():
            errors.append(f"{role}: gzip decoded bytes differ from identity")
        if entry.get("gzip", {}).get("encodedBytes") != len(encoded):
            errors.append(f"{role}: gzip encoded size mismatch")
        if entry.get("gzip", {}).get("encodedSha256") != sha256_bytes(encoded):
            errors.append(f"{role}: gzip encoded hash mismatch")
    actual_files = {
        str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()
    }
    expected_files = expected_bundle_files(manifest)
    if actual_files != expected_files:
        errors.append(
            f"bundle files differ: missing={sorted(expected_files - actual_files)} "
            f"extra={sorted(actual_files - expected_files)}"
        )
    return {
        "schemaVersion": 1,
        "policy": policy,
        "releaseId": manifest.get("releaseId"),
        "artifactCount": len(artifacts),
        "requiredArtifactCount": sum(item.get("required") is True for item in artifacts),
        "errors": errors,
        "pass": not errors,
    }


def validate_bundle_index(root: Path) -> dict[str, Any]:
    index = load_json(root / "index.json")
    errors: list[str] = []
    releases = index.get("releases", [])
    if [item.get("policy") for item in releases] != list(POLICIES):
        errors.append("bundle index policy order differs")
    release_ids = [item.get("releaseId") for item in releases]
    if len(set(release_ids)) != len(POLICIES):
        errors.append("fidelity policies must have distinct release IDs")
    results = []
    for item in releases:
        policy = item.get("policy")
        result = validate_bundle(root / str(item.get("releaseId")), str(policy))
        results.append(result)
        if not result["pass"]:
            errors.extend(f"{policy}: {error}" for error in result["errors"])
    return {"schemaVersion": 1, "releases": results, "errors": errors, "pass": not errors}
