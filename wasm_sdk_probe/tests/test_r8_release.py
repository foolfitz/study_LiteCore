from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from build_r8_release_manifest import DEFAULT_CREATED_AT  # noqa: E402
from r8_release import (  # noqa: E402
    ROLE_ORDER,
    build_release_manifest,
    expected_release_id,
    validate_release_manifest,
)


class R8ReleaseManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = Path(__file__).resolve().parent.parent
        cls.dist = cls.project / "dist"
        cls.manifest = build_release_manifest(cls.project, DEFAULT_CREATED_AT)

    def changed(self, mutate) -> dict:
        manifest = copy.deepcopy(self.manifest)
        mutate(manifest)
        manifest["releaseId"] = expected_release_id(manifest)
        return manifest

    def test_frozen_writer_review_graph_passes(self) -> None:
        report = validate_release_manifest(self.manifest, self.dist)
        self.assertTrue(report["pass"], report["errors"])
        self.assertEqual([item["role"] for item in self.manifest["artifacts"]], list(ROLE_ORDER))
        self.assertEqual(sum(item["required"] for item in self.manifest["artifacts"]), 15)
        self.assertEqual(len(self.manifest["artifacts"]), 17)

    def test_json_schema_role_enum_matches_closed_inventory(self) -> None:
        schema = json.loads(
            (self.project / "r8" / "release-schema-v1.json").read_text(encoding="utf-8")
        )
        roles = schema["$defs"]["artifact"]["properties"]["role"]["enum"]
        self.assertEqual(roles, list(ROLE_ORDER))

    def test_release_identity_changes_when_release_metadata_changes(self) -> None:
        changed = self.changed(lambda value: value.__setitem__(
            "createdAt", "2026-08-04T00:00:01+08:00"
        ))
        self.assertNotEqual(changed["releaseId"], self.manifest["releaseId"])
        self.assertTrue(validate_release_manifest(changed, self.dist)["pass"])

    def test_traversal_url_is_rejected_before_file_access(self) -> None:
        changed = self.changed(lambda value: value["artifacts"][0].__setitem__(
            "url", "../outside.html"
        ))
        report = validate_release_manifest(changed, self.dist)
        self.assertFalse(report["pass"])
        self.assertTrue(any("unsafe relative URL" in item for item in report["errors"]))

    def test_hash_mismatch_is_rejected(self) -> None:
        changed = self.changed(lambda value: value["artifacts"][0].__setitem__(
            "sha256", "0" * 64
        ))
        report = validate_release_manifest(changed, self.dist)
        self.assertFalse(report["pass"])
        self.assertTrue(any("SHA-256 does not match" in item for item in report["errors"]))

    def test_duplicate_and_missing_role_are_rejected(self) -> None:
        def mutate(value: dict) -> None:
            value["artifacts"][-1]["role"] = "fallback-data"

        report = validate_release_manifest(self.changed(mutate), self.dist)
        self.assertFalse(report["pass"])
        self.assertTrue(any("exactly once" in item for item in report["errors"]))

    def test_unknown_top_level_field_is_rejected(self) -> None:
        changed = self.changed(lambda value: value.__setitem__("command", ".uno:Save"))
        report = validate_release_manifest(changed, self.dist)
        self.assertFalse(report["pass"])
        self.assertTrue(any("manifest fields differ" in item for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
