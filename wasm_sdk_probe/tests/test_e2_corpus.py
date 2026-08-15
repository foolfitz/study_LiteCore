"""SPEC E2-C D3: the E2 fixture is what the L7 cell needs it to be.

The content-axis inventory can say the corpus has lists and how many items
those lists hold in total.  It cannot say whether any SINGLE list has an
interior item -- two lists of two items and one list of four both count four.
L7 ("leave the list from an interior item") needs one list with three, so that
property is pinned here rather than inferred from a total.
"""

from __future__ import annotations

import json
import re
import unittest
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
CORPUS = PROJECT / "test-docs" / "e2"


def content_of(name: str) -> str:
    with zipfile.ZipFile(CORPUS / name) as archive:
        return archive.read("content.xml").decode("utf-8")


def items_per_list(content: str) -> list[int]:
    """How many <text:list-item> each <text:list> holds, in document order."""
    counts = []
    for block in re.findall(r"<text:list\b.*?</text:list>", content, re.S):
        counts.append(len(re.findall(r"<text:list-item\b", block)))
    return counts


class TestE2Corpus(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(
            (CORPUS / "manifest.json").read_text(encoding="utf-8"))
        self.fixtures = {entry["id"]: entry for entry in self.manifest["fixtures"]}

    def test_manifest_matches_the_bytes_on_disk(self) -> None:
        import hashlib
        for entry in self.manifest["fixtures"]:
            path = CORPUS / entry["path"]
            data = path.read_bytes()
            self.assertEqual(len(data), entry["bytes"], entry["id"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"],
                             entry["id"])

    def test_every_list_has_an_interior_item(self) -> None:
        counts = items_per_list(content_of("list-split.odt"))
        self.assertEqual(counts, [3, 3],
                         "L7 needs a list with a first, a middle and a last")

    def test_the_interior_anchor_is_the_middle_item(self) -> None:
        content = content_of("list-split.odt")
        block = re.search(r"<text:list\b.*?</text:list>", content, re.S).group(0)
        items = re.findall(r"<text:list-item>(.*?)</text:list-item>", block, re.S)
        self.assertEqual(len(items), 3)
        self.assertIn("E2-LS-MID", items[1])
        # And not in the others -- an anchor that appears three times cannot
        # tell the runner which item it selected.
        self.assertNotIn("E2-LS-MID", items[0])
        self.assertNotIn("E2-LS-MID", items[2])

    def test_the_anchors_the_manifest_claims_are_really_there(self) -> None:
        content = content_of("list-split.odt")
        for anchor in self.fixtures["list-split"]["anchors"]:
            self.assertIn(anchor, content, anchor)

    def test_the_item_count_check_can_fail(self) -> None:
        # Without this the structural assertion could be matching nothing at
        # all: a regex that never fires reports [] and [] == [] would pass if
        # the expectation were ever written that way.
        two_item = ('<text:list><text:list-item><text:p>a</text:p></text:list-item>'
                    '<text:list-item><text:p>b</text:p></text:list-item></text:list>')
        self.assertEqual(items_per_list(two_item), [2])
        self.assertEqual(items_per_list("<text:p>no lists here</text:p>"), [])

    def test_this_corpus_does_not_shadow_an_e1_fixture(self) -> None:
        # The suites file names fixtures by BASENAME across corpora, so an E2
        # file called list-contexts.odt would silently replace E1's in the
        # roll-up and nothing would say which one was measured.
        e1 = {path.name for path in (PROJECT / "test-docs" / "e1").glob("*.odt")}
        e2 = {path.name for path in CORPUS.glob("*.odt")}
        self.assertEqual(e1 & e2, set())


if __name__ == "__main__":
    unittest.main()
