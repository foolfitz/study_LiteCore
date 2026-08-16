"""SPEC E2-C section 6: the shell binding, and proof it can say no.

A binding that cannot fail is not a binding.  Each of the three ways the shell
can drift out from under a verdict gets a case here -- a covered file changing,
a new file appearing beside the covered ones, and the served dist copy falling
behind the source -- plus one live check that the tree is currently clean.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

import build_e2_c_shell_bundle as bundle  # noqa: E402


def state(included, hashes, available=None, dist=None):
    available = available if available is not None else list(included)
    dist = dist if dist is not None else dict(hashes)
    return {"included": list(included), "hashes": dict(hashes),
            "available": list(available), "distHashes": dict(dist),
            "digest": bundle.shell_bundle_digest(hashes)}


def manifest_for(current):
    return {"included": [{"path": p, "sha256": h}
                         for p, h in sorted(current["hashes"].items())],
            "excluded": [],
            "bundleSha256": current["digest"]}


class TestShellBundle(unittest.TestCase):
    def setUp(self) -> None:
        self.clean = state(["a.js", "b.js"], {"a.js": "1" * 64, "b.js": "2" * 64})
        self.manifest = manifest_for(self.clean)

    def test_a_clean_tree_reports_nothing(self) -> None:
        self.assertEqual(bundle.problems(PROJECT, self.clean, self.manifest), [])

    def test_a_covered_file_changing_is_caught(self) -> None:
        changed = state(["a.js", "b.js"], {"a.js": "9" * 64, "b.js": "2" * 64})
        found = bundle.problems(PROJECT, changed, self.manifest)
        self.assertTrue(any("out of date" in item and "a.js" in item
                            for item in found), found)

    def test_a_new_file_beside_the_covered_ones_is_caught(self) -> None:
        # The rule E1-C's bundle already has, and the reason adding a file to
        # editor-shell/ unbinds E1_GO_ODT_EDITOR: coverage has to be a
        # statement about the directory, not only about a list.
        grown = state(["a.js", "b.js"], {"a.js": "1" * 64, "b.js": "2" * 64},
                      available=["a.js", "b.js", "sneaked-in.js"])
        found = bundle.problems(PROJECT, grown, self.manifest)
        self.assertTrue(any("neither included nor excluded" in item
                            and "sneaked-in.js" in item for item in found), found)

    def test_an_excluded_file_satisfies_the_coverage_rule(self) -> None:
        grown = state(["a.js", "b.js"], {"a.js": "1" * 64, "b.js": "2" * 64},
                      available=["a.js", "b.js", "known.js"])
        manifest = dict(self.manifest,
                        excluded=[{"path": "known.js", "reason": "stated"}])
        self.assertEqual(bundle.problems(PROJECT, grown, manifest), [])

    def test_a_stale_dist_copy_is_caught(self) -> None:
        # serve.py serves dist/.  A manifest frozen against source bytes the
        # server is not serving binds the wrong thing, and forgetting
        # `make e2-c-assets` is a standing trap in this tree.
        stale = state(["a.js", "b.js"], {"a.js": "1" * 64, "b.js": "2" * 64},
                      dist={"a.js": "1" * 64, "b.js": "0" * 64})
        found = bundle.problems(PROJECT, stale, self.manifest)
        self.assertTrue(any("dist copy differs" in item and "b.js" in item
                            for item in found), found)

    def test_a_missing_dist_copy_is_caught(self) -> None:
        stale = state(["a.js", "b.js"], {"a.js": "1" * 64, "b.js": "2" * 64},
                      dist={"a.js": "1" * 64, "b.js": None})
        found = bundle.problems(PROJECT, stale, self.manifest)
        self.assertTrue(any("dist copy differs" in item for item in found), found)

    def test_the_digest_depends_on_the_path_not_only_the_bytes(self) -> None:
        # Renaming a module with identical bytes must change the digest;
        # otherwise the binding cannot tell one module from another.
        first = bundle.shell_bundle_digest({"a.js": "1" * 64})
        second = bundle.shell_bundle_digest({"b.js": "1" * 64})
        self.assertNotEqual(first, second)

    def test_every_frozen_generation_stays_put(self) -> None:
        # Each frozen manifest is the shell some round ran on.  Regenerating one
        # in place would leave that round's evidence present but unverifiable --
        # finding 027's shape applied to the shell -- so the only legal move is
        # a NEW generation.  This asserts each frozen digest still differs from
        # the tree, which is what makes it a record rather than a duplicate of
        # the current manifest.
        current = bundle.compute(PROJECT)["digest"]
        for path in bundle.FROZEN_MANIFESTS:
            frozen = json.loads((PROJECT / path).read_text(encoding="utf-8"))
            self.assertNotEqual(
                frozen["bundleSha256"], current,
                f"{path} equals the current tree, so it is not recording "
                f"anything -- either the generation was pointless or the tree "
                f"was reverted")

    def test_round_ones_manifest_is_frozen(self) -> None:
        # Round one's bundle is a historical record: e2/validation-matrix-v1.json
        # names its digest, and round one's evidence can only be revalidated
        # against the shell it actually ran on.  A legitimate shell change
        # writes a NEW manifest; regenerating this one in place would leave the
        # old evidence present but unverifiable, which is finding 027's shape
        # applied to the shell.
        frozen = json.loads(
            (PROJECT / bundle.FROZEN_MANIFEST).read_text(encoding="utf-8"))
        matrix = json.loads(
            (PROJECT / "e2" / "validation-matrix-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(frozen["bundleSha256"],
                         matrix["baseline"]["shellBundleSha256"],
                         "round one's matrix and its bundle have come apart")
        self.assertNotEqual(frozen["bundleSha256"],
                            bundle.compute(PROJECT)["digest"],
                            "if these are equal the shell has not changed and "
                            "this test is not testing anything -- delete it "
                            "rather than leaving a check that cannot fail")

    def test_the_real_manifest_matches_the_real_tree(self) -> None:
        manifest_path = PROJECT / bundle.MANIFEST
        self.assertTrue(manifest_path.is_file(), "the bundle has not been written")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        current = bundle.compute(PROJECT)
        self.assertEqual(bundle.problems(PROJECT, current, manifest), [])
        self.assertEqual(manifest["bundleSha256"], current["digest"])
        # Every exclusion carries a reason.  "Not covered" is a claim somebody
        # has to make, and an empty string is not making it.
        for item in manifest["excluded"]:
            self.assertTrue(item.get("reason", "").strip(), item)

    def test_the_product_modules_are_actually_in_it(self) -> None:
        # Named rather than counted: the point of this bundle is those three
        # files, and a graph walk that quietly missed one would still produce a
        # perfectly consistent manifest.
        manifest = json.loads(
            (PROJECT / bundle.MANIFEST).read_text(encoding="utf-8"))
        paths = {item["path"] for item in manifest["included"]}
        for required in ("editor-shell-v2/narrow-editor-v2-client.js",
                         "editor-shell-v2/narrow-editor-v2-session.js",
                         "web/e2-editor-app.js",
                         "editor-shell/editor-session.js"):
            self.assertIn(required, paths)

    def test_make_owns_the_dist_copy_of_every_bound_module(self) -> None:
        # `make e2-c-assets` must rebuild every module the bundle binds,
        # because serve.py serves dist/ and the product page therefore runs the
        # dist copy.  This gap has bitten twice: input/input-adapter.js on
        # 2026-08-16 (finding 050's fix could not be served) and the three
        # editor-shell modules the same day (finding 051's fix could not be
        # served), each discovered only because something downstream refused.
        #
        # `test_a_stale_dist_copy_is_caught` covers the symptom after the fact;
        # this covers the cause, in the build graph, before anybody runs a
        # browser.
        manifest = json.loads(
            (PROJECT / bundle.MANIFEST).read_text(encoding="utf-8"))
        makefile = (PROJECT / "Makefile").read_text(encoding="utf-8")
        start = makefile.index("\ne2-c-assets:")
        block = makefile[start:]
        block = block[:block.index("\n\n")]
        prerequisites = set(block.replace("\\\n", " ").split())
        missing = []
        for item in manifest["included"]:
            path = item["path"]
            # The page itself is copied under its own name in dist's root.
            expected = ("dist/" + path[len("web/"):] if path.startswith("web/")
                        else "dist/" + path)
            if expected not in prerequisites:
                missing.append(expected)
        self.assertEqual(missing, [], f"e2-c-assets does not own {missing}")


if __name__ == "__main__":
    unittest.main()
