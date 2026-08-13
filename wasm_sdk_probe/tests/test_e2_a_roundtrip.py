#!/usr/bin/env python3
"""Checks for A7's round-trip slice (tools/validate_e2_a_roundtrip.py).

The tool gates part of a spec verdict, so the question these tests ask is not
"does it pass a good document" but "does it fail a bad one".  Each check gets a
document that violates exactly it, and a near-identical document that does not.

The tool also ships a `--self-test` that mutates a real evidence document.  That
one guards the checks against the corpus; these guard them against each other,
and they caught a real hole: the first mutation renamed a style in a document
that declared none, so `unresolved-style` reported clean without ever running.
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from validate_e2_a_roundtrip import (  # noqa: E402
    break_document,
    check_package,
    check_structure,
    choose_sample,
    collect,
    expressiveness,
)

CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0">
 <office:automatic-styles>
  <style:style style:name="P1" style:family="paragraph"/>
  <text:list-style style:name="L1"/>
 </office:automatic-styles>
 <office:body><office:text>
  <text:h text:outline-level="1" text:style-name="P1">E1-STYLED-END heading</text:h>
  <text:list text:style-name="L1"><text:list-item><text:p
    text:style-name="P1">item</text:p></text:list-item></text:list>
 </office:text></office:body>
</office:document-content>
"""
STYLES = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0">
 <office:styles><style:style style:name="Standard" style:family="paragraph"/>
 </office:styles>
</office:document-styles>
"""
MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest
 xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
 <manifest:file-entry manifest:full-path="/"
  manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""


def odt(content: str = CONTENT, styles: str = STYLES, manifest: str = MANIFEST,
        mimetype_first: bool = True, deflate_mimetype: bool = False,
        omit: tuple[str, ...] = ()) -> Path:
    handle = tempfile.NamedTemporaryFile(suffix=".odt", delete=False)
    buffer = io.BytesIO()
    mime = ("mimetype", b"application/vnd.oasis.opendocument.text",
            zipfile.ZIP_DEFLATED if deflate_mimetype else zipfile.ZIP_STORED)
    rest = [
        ("content.xml", content.encode("utf-8"), zipfile.ZIP_DEFLATED),
        ("styles.xml", styles.encode("utf-8"), zipfile.ZIP_DEFLATED),
        ("META-INF/manifest.xml", manifest.encode("utf-8"), zipfile.ZIP_DEFLATED),
    ]
    members = rest + [mime] if not mimetype_first else [mime] + rest
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data, method in members:
            if name in omit:
                continue
            archive.writestr(zipfile.ZipInfo(name), data, compress_type=method)
    handle.write(buffer.getvalue())
    handle.close()
    return Path(handle.name)


class PackageTest(unittest.TestCase):
    def test_a_well_formed_package_reports_nothing(self) -> None:
        self.assertEqual(check_package(odt()), [])
        self.assertEqual(check_structure(odt(), "E1-STYLED-END"), [])

    def test_mimetype_must_come_first(self) -> None:
        self.assertIn("mimetype-not-first", check_package(odt(mimetype_first=False)))

    def test_mimetype_must_be_stored(self) -> None:
        """Desktop LibreOffice sniffs the type from the first 30 bytes."""
        self.assertIn("mimetype-deflated", check_package(odt(deflate_mimetype=True)))

    def test_a_broken_crc_is_caught(self) -> None:
        path = odt()
        raw = bytearray(path.read_bytes())
        # Corrupt the deflated payload without touching the central directory,
        # which is exactly what a truncated or half-flushed write looks like.
        raw[len(raw) // 2] ^= 0xFF
        path.write_bytes(bytes(raw))
        self.assertTrue(any(problem.startswith(("crc-failed", "xml-malformed"))
                            for problem in check_package(path)))

    def test_malformed_content_is_caught(self) -> None:
        problems = check_package(odt(content=CONTENT.replace("</office:text>", "")))
        self.assertTrue(any(problem.startswith("xml-malformed:content.xml")
                            for problem in problems))

    def test_a_part_missing_from_the_manifest_is_caught(self) -> None:
        """A part in the zip but not the manifest survives the write, not the read."""
        thin = MANIFEST.replace(
            '<manifest:file-entry manifest:full-path="styles.xml"'
            ' manifest:media-type="text/xml"/>', "")
        self.assertIn("manifest-missing-entry:styles.xml", check_package(odt(manifest=thin)))

    def test_a_manifest_entry_with_no_part_is_caught(self) -> None:
        self.assertIn("manifest-lists-absent-part:styles.xml",
                      check_package(odt(omit=("styles.xml",))))


class StructureTest(unittest.TestCase):
    def test_a_reference_to_an_undeclared_style_is_caught(self) -> None:
        """The shape silent structure loss takes in the file."""
        broken = CONTENT.replace('style:name="P1"', 'style:name="P1-GONE"')
        self.assertIn("unresolved-style:P1", check_structure(odt(content=broken), None))

    def test_a_style_declared_only_in_styles_xml_still_resolves(self) -> None:
        """Named styles live in styles.xml; a content-only reader invents failures."""
        using = CONTENT.replace('text:style-name="P1">item', 'text:style-name="Standard">item')
        self.assertEqual(check_structure(odt(content=using), None), [])

    def test_an_orphan_list_item_is_caught(self) -> None:
        broken = CONTENT.replace("<text:list text:style-name=\"L1\">", "").replace(
            "</text:list>", "")
        self.assertIn("orphan-list-item", check_structure(odt(content=broken), None))

    def test_an_empty_list_is_caught(self) -> None:
        broken = CONTENT.replace(
            '<text:list-item><text:p\n    text:style-name="P1">item</text:p></text:list-item>',
            "")
        self.assertIn("empty-list", check_structure(odt(content=broken), None))

    def test_a_heading_without_an_outline_level_is_caught(self) -> None:
        broken = CONTENT.replace(' text:outline-level="1"', "")
        self.assertIn("heading-without-outline-level:None",
                      check_structure(odt(content=broken), None))

    def test_the_anchor_check_can_fail(self) -> None:
        self.assertEqual(check_structure(odt(), "E1-STYLED-END"), [])
        self.assertIn("anchor-missing:E1-MULTI-END",
                      check_structure(odt(), "E1-MULTI-END"))


class SampleChoiceTest(unittest.TestCase):
    """A mutation test on a document that cannot express the defect is no test."""

    def test_expressiveness_separates_a_list_document_from_a_bare_one(self) -> None:
        bare = CONTENT.replace(
            '<text:list text:style-name="L1"><text:list-item><text:p\n'
            '    text:style-name="P1">item</text:p></text:list-item></text:list>', "")
        self.assertEqual(expressiveness(odt(content=bare))["listItems"], 0)
        self.assertEqual(expressiveness(odt())["listItems"], 1)

    def test_choose_sample_prefers_a_document_that_can_be_broken(self) -> None:
        bare = odt(content=CONTENT.replace(
            '<text:list text:style-name="L1"><text:list-item><text:p\n'
            '    text:style-name="P1">item</text:p></text:list-item></text:list>', ""))
        rich = odt()
        self.assertEqual(choose_sample([bare, rich]), rich)
        self.assertEqual(choose_sample([rich, bare]), rich)

    def test_the_dangling_style_mutation_renames_a_style_that_is_used(self) -> None:
        """The bug this file was written after: it renamed an unused style."""
        with tempfile.TemporaryDirectory() as workspace:
            broken = Path(workspace) / "broken.odt"
            break_document(odt(), "dangling-style", broken)
            self.assertTrue(any(problem.startswith("unresolved-style:")
                                for problem in check_structure(broken, None)))


class ArtifactBindingTest(unittest.TestCase):
    """Finding 027: evidence from a superseded build is not coverage."""

    def make_run(self, root: Path, name: str, sha: str) -> None:
        run = root / "browser" / "chrome" / name
        run.mkdir(parents=True)
        (run / "result.json").write_text(
            '{"browser": "chrome", "fixture": "styled-list",'
            ' "manifest": {"diagnostic": {"wasmSha256": "%s"}}}' % sha,
            encoding="utf-8")
        (run / "after.odt").write_bytes(odt().read_bytes())

    def test_only_documents_from_the_current_artifact_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            self.make_run(root, "current", "aaaa")
            self.make_run(root, "superseded", "bbbb")
            documents, skipped = collect(root, "aaaa")
            self.assertEqual([entry["path"].parent.name for entry in documents],
                             ["current"])
            self.assertEqual(skipped, {"other-artifact:bbbb": 1})


if __name__ == "__main__":
    unittest.main()
