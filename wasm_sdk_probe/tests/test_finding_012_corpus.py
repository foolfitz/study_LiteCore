from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path

from tools.create_finding_012_corpus import FEATURES, create_corpus
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from tools import validate_finding_012


class Finding012CorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = Path(__file__).resolve().parent.parent
        cls.temporary = tempfile.TemporaryDirectory(prefix="finding-012-test-")
        cls.output = Path(cls.temporary.name)
        cls.manifest = create_corpus(
            cls.project / "test-docs" / "t2-styled.odt",
            cls.output,
            validate_desktop=False,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_all_feature_combinations_are_valid_packages(self) -> None:
        self.assertEqual(len(self.manifest["variants"]), 16)
        self.assertTrue(self.manifest["pass"])
        combinations = {tuple(item["retainedFeatures"]) for item in self.manifest["variants"]}
        self.assertEqual(len(combinations), 16)
        self.assertTrue(all(item["packageValidation"]["pass"] for item in self.manifest["variants"]))

    def test_original_is_byte_identical_and_empty_variant_removes_all_features(self) -> None:
        by_id = {item["id"]: item for item in self.manifest["variants"]}
        self.assertEqual(by_id["t2-original"]["sha256"], self.manifest["source"]["sha256"])
        empty = by_id["t2-keep-none"]
        self.assertEqual(empty["retainedFeatures"], [])
        self.assertEqual(set(empty["removedFeatures"]), set(FEATURES))
        self.assertEqual(empty["packageValidation"]["features"], {
            "table": False, "image": False, "annotation": False, "page-break": False,
        })

    def test_generator_does_not_import_uno(self) -> None:
        source = (self.project / "tools" / "create_finding_012_corpus.py").read_text(encoding="utf-8")
        self.assertNotIn("import uno", source)

    def test_image_axis_corpus_preserves_image_and_changes_one_declared_axis(self) -> None:
        output = self.output / "image-axis"
        try:
            manifest = create_corpus(
                self.project / "test-docs" / "t2-styled.odt",
                output,
                validate_desktop=False,
                axis="image",
            )
        except TypeError as error:
            self.fail(f"image-axis corpus API is missing: {error}")

        by_id = {item["id"]: item for item in manifest["variants"]}
        self.assertEqual(manifest["release"], "finding-012-r7-image-axis")
        self.assertEqual(set(by_id), {
            "t2-original",
            "t2-image-no-mime",
            "t2-image-no-style-ref",
            "t2-image-no-name-zindex",
            "t2-image-no-clip",
            "t2-image-no-graphic-properties",
            "t2-image-unwrapped",
            "t2-image-l4-geometry",
            "t2-image-l4-like-frame",
        })
        self.assertEqual(by_id["t2-original"]["sha256"], manifest["source"]["sha256"])
        self.assertEqual(by_id["t2-original"]["changedAxes"], [])
        self.assertEqual(
            by_id["t2-image-no-clip"]["changedAxes"],
            ["graphic-style.clip"],
        )
        self.assertEqual(
            by_id["t2-image-l4-like-frame"]["changedAxes"],
            [
                "image.mime-type",
                "frame.style-ref",
                "frame.identity",
                "frame.wrapper",
                "frame.geometry",
            ],
        )
        self.assertTrue(manifest["pass"])
        self.assertTrue(all(item["packageValidation"]["pass"] for item in by_id.values()))
        self.assertEqual(
            {item["packageValidation"]["embeddedImageSha256"] for item in by_id.values()},
            {manifest["embeddedImage"]["sha256"]},
        )

    def test_image_axis_selector_prefers_single_axis_passing_boundary(self) -> None:
        try:
            selector = validate_finding_012.select_image_axis_boundaries
        except AttributeError as error:
            self.fail(f"image-axis boundary selector is missing: {error}")
        manifest = {
            "variants": [
                {"id": "t2-original", "changedAxes": []},
                {"id": "t2-image-no-clip", "changedAxes": ["graphic-style.clip"]},
                {
                    "id": "t2-image-l4-like-frame",
                    "changedAxes": ["frame.style-ref", "frame.wrapper"],
                },
            ]
        }
        selected = selector(manifest, {
            "t2-original": "timeout",
            "t2-image-no-clip": "close-pass",
            "t2-image-l4-like-frame": "close-pass",
        })
        self.assertEqual(selected, [
            {
                "id": "t2-image-no-clip",
                "expectedOutcome": "close-pass",
                "runs": 3,
                "reason": "smallest passing image-object change: graphic-style.clip",
            },
            {
                "id": "t2-original",
                "expectedOutcome": "timeout",
                "runs": 1,
                "reason": "byte-identical failing control",
            },
        ])

    def test_image_axis_selector_keeps_smallest_interaction_when_no_single_axis_passes(self) -> None:
        selector = getattr(validate_finding_012, "select_image_axis_boundaries", None)
        if selector is None:
            self.fail("image-axis boundary selector is missing")
        manifest = {
            "variants": [
                {"id": "t2-original", "changedAxes": []},
                {"id": "t2-image-no-clip", "changedAxes": ["graphic-style.clip"]},
                {
                    "id": "t2-image-l4-like-frame",
                    "changedAxes": ["frame.style-ref", "frame.wrapper"],
                },
            ]
        }
        selected = selector(manifest, {
            "t2-original": "timeout",
            "t2-image-no-clip": "timeout",
            "t2-image-l4-like-frame": "close-pass",
        })
        self.assertEqual(selected[0]["id"], "t2-image-l4-like-frame")
        self.assertEqual(selected[0]["runs"], 3)
        self.assertIn("interaction", selected[0]["reason"])
        self.assertEqual(selected[1]["id"], "t2-original")


if __name__ == "__main__":
    unittest.main()
