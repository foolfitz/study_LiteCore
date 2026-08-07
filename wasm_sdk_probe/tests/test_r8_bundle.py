from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from r8_bundle import (  # noqa: E402
    LOCATE_FILE_CLOSED_MARKER,
    POLICIES,
    build_bundles,
    build_policy_bundle,
    validate_bundle,
    validate_bundle_index,
)
from build_r8_c_release_set import build_release_set  # noqa: E402
from r8_release import ROLE_ORDER, expected_release_id  # noqa: E402


class R8BundleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="r8-bundle-test-")
        self.project = Path(self.temporary.name)
        self.dist = self.project / "dist"
        (self.dist / "r8").mkdir(parents=True)
        sdk_manifest = {
            "abiVersion": 65537,
            "artifactFiles": {
                "probe.js": "../writer-review/probe.000000000000.js",
                "probe.wasm": "../writer-review/probe.000000000000.wasm",
                "soffice.data": "../resources/base.000000000000.data",
                "soffice.data.js.metadata": "../resources/base.000000000000.metadata",
            },
            "capabilities": ["open-odt", "save-odt"],
            "coreCommit": "1" * 40,
            "expectedCapabilityBits": 1,
            "profile": "writer-review",
            "protocolVersion": 1,
            "resourcePacks": [
                {"id": "cjk-r5", "loadAtStartup": True, "data": "cjk.data",
                 "metadata": "cjk.metadata", "bytes": 4, "sha256": "2" * 64},
                {"id": "fallback-fonts-r5", "loadAtStartup": False, "data": "fallback.data",
                 "metadata": "fallback.metadata", "bytes": 4, "sha256": "3" * 64},
            ],
            "sdkVersion": "test",
        }
        urls = {
            "entry-html": "r7-reference.html",
            "stylesheet": "r7.css",
            "app-module": "r7-reference-app.js",
            "document-sdk": "document-sdk.js",
            "input-adapter": "input/input-adapter.js",
            "clipboard-adapter": "input/clipboard-adapter.js",
            "page-navigation": "r7/page-navigation.js",
            "sdk-worker": "profiles/writer-review-r6/sdk-worker.js",
            "sdk-manifest": "profiles/writer-review-r6/sdk-manifest.json",
            "wasm-loader": "profiles/writer-review/probe.000000000000.js",
            "wasm-binary": "profiles/writer-review/probe.000000000000.wasm",
            "base-data": "profiles/resources/base.000000000000.data",
            "base-metadata": "profiles/resources/base.000000000000.metadata",
            "cjk-data": "profiles/resources/cjk.000000000000.data",
            "cjk-metadata": "profiles/resources/cjk.000000000000.metadata",
            "fallback-data": "profiles/resources/fallback.000000000000.data",
            "fallback-metadata": "profiles/resources/fallback.000000000000.metadata",
        }
        media = {
            "entry-html": "text/html; charset=utf-8", "stylesheet": "text/css; charset=utf-8",
            "app-module": "text/javascript; charset=utf-8", "document-sdk": "text/javascript; charset=utf-8",
            "input-adapter": "text/javascript; charset=utf-8", "clipboard-adapter": "text/javascript; charset=utf-8",
            "page-navigation": "text/javascript; charset=utf-8", "sdk-worker": "text/javascript; charset=utf-8",
            "sdk-manifest": "application/json; charset=utf-8", "wasm-loader": "text/javascript; charset=utf-8",
            "wasm-binary": "application/wasm", "base-data": "application/octet-stream",
            "base-metadata": "application/json; charset=utf-8", "cjk-data": "application/octet-stream",
            "cjk-metadata": "application/json; charset=utf-8", "fallback-data": "application/octet-stream",
            "fallback-metadata": "application/json; charset=utf-8",
        }
        artifacts = []
        for role in ROLE_ORDER:
            path = self.dist / urls[role]
            path.parent.mkdir(parents=True, exist_ok=True)
            if role == "sdk-manifest":
                path.write_text(json.dumps(sdk_manifest), encoding="utf-8")
            elif role == "sdk-worker":
                path.write_text(
                    "const artifactFiles = {};\n"
                    "const options = { locateFile: (path) => new URL(artifactFiles[path] || path, self.location.href).href, };\n",
                    encoding="utf-8",
                )
            else:
                path.write_bytes(f"fixture-{role}\n".encode())
            artifacts.append({
                "role": role, "url": urls[role], "sha256": "0" * 64,
                "rawBytes": path.stat().st_size, "mediaType": media[role],
                "contentEncoding": "identity", "required": not role.startswith("fallback-"),
                "cachePolicy": "optional-pack" if role.startswith("fallback-")
                else ("entry" if role in set(ROLE_ORDER[:9]) else "immutable"),
            })
        manifest = {
            "schemaVersion": 1, "releaseId": "", "createdAt": "2026-08-04T00:00:00+08:00",
            "sdkVersion": "test", "profile": "writer-review", "coreCommit": "1" * 40,
            "entry": "r7-reference.html", "capabilities": ["open-odt", "save-odt"],
            "artifacts": artifacts,
        }
        manifest["releaseId"] = expected_release_id(manifest)
        (self.dist / "r8" / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.releases = self.dist / "releases"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_builds_distinct_valid_standard_and_full_fidelity_releases(self) -> None:
        index = build_bundles(self.project, self.releases)
        self.assertEqual([item["policy"] for item in index["releases"]], list(POLICIES))
        self.assertEqual(len({item["releaseId"] for item in index["releases"]}), 2)
        self.assertTrue(validate_bundle_index(self.releases)["pass"])
        for item in index["releases"]:
            manifest = json.loads((self.releases / item["releaseId"] / "release-manifest.json").read_text())
            worker_url = next(artifact["url"] for artifact in manifest["artifacts"]
                              if artifact["role"] == "sdk-worker")
            self.assertIn(
                LOCATE_FILE_CLOSED_MARKER,
                (self.releases / item["releaseId"] / worker_url).read_text(encoding="utf-8"),
            )

    def test_full_fidelity_requires_and_mounts_fallback_pair(self) -> None:
        index = build_bundles(self.project, self.releases)
        releases = {item["policy"]: item for item in index["releases"]}
        standard_root = self.releases / releases["standard"]["releaseId"]
        full_root = self.releases / releases["full-fidelity"]["releaseId"]
        standard = json.loads((standard_root / "release-manifest.json").read_text())
        full = json.loads((full_root / "release-manifest.json").read_text())
        self.assertFalse(next(item for item in standard["artifacts"] if item["role"] == "fallback-data")["required"])
        self.assertTrue(next(item for item in full["artifacts"] if item["role"] == "fallback-data")["required"])
        sdk = json.loads((full_root / "profiles/writer-review-r6/sdk-manifest.json").read_text())
        fallback = next(item for item in sdk["resourcePacks"] if item["id"] == "fallback-fonts-r5")
        self.assertTrue(fallback["loadAtStartup"])

    def test_rebuild_is_deterministic_and_reuses_identical_release(self) -> None:
        first = build_bundles(self.project, self.releases)
        second = build_bundles(self.project, self.releases)
        self.assertEqual(first, second)

    def test_tampered_gzip_representation_is_rejected(self) -> None:
        index = build_bundles(self.project, self.releases)
        item = index["releases"][0]
        root = self.releases / item["releaseId"]
        (root / "document-sdk.js.gz").write_bytes(b"not-gzip")
        result = validate_bundle(root, "standard")
        self.assertFalse(result["pass"])
        self.assertTrue(any("gzip" in error for error in result["errors"]))

    def test_r8_c_release_set_keeps_canonical_a_and_builds_distinct_b(self) -> None:
        canonical = build_policy_bundle(self.project, self.releases, "standard")
        output = self.dist / "r8c"
        release_set = build_release_set(self.project, output)
        by_slot = {item["slot"]: item for item in release_set["releases"]}
        self.assertEqual(by_slot["A"]["releaseId"], canonical["releaseId"])
        self.assertNotEqual(by_slot["A"]["releaseId"], by_slot["B"]["releaseId"])
        self.assertNotEqual(by_slot["B"]["releaseId"], by_slot["C"]["releaseId"])
        self.assertEqual(len({item["releaseId"] for item in by_slot.values()}), 3)
        self.assertTrue(release_set["pass"])
        candidate_root = output / "releases" / by_slot["B"]["releaseId"]
        candidate_manifest = json.loads(
            (candidate_root / "release-manifest.json").read_text(encoding="utf-8")
        )
        app_url = next(
            item["url"] for item in candidate_manifest["artifacts"]
            if item["role"] == "app-module"
        )
        self.assertIn(
            "OXSDK_R8_RELEASE_VARIANT:r8c-candidate-v1",
            (candidate_root / app_url).read_text(encoding="utf-8"),
        )

    def test_release_variant_marker_is_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_policy_bundle(
                self.project, self.releases, "standard", variant_marker="../unsafe",
            )


if __name__ == "__main__":
    unittest.main()
