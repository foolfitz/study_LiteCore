"""tools/four_arms_identity.py reads a generation as the per-generation copy did.

generation-89.json against tools/v89_four_arms_identity.py's constants (the last copy); a file that names another
generation is refused; every generation file carries the keys the tool reads.  The live behaviour (shell() and
identity() against the tree) is witnessed by V0' 90's v89 stage, which re-reads F4-89 byte for byte.

    python3 -m unittest tests.test_four_arms_identity
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import four_arms_identity as fai  # noqa: E402
import v89_four_arms_identity as v89  # noqa: E402


class Generation89(unittest.TestCase):
    def test_constants_equal_the_last_copy(self):
        g = fai.Generation(89)
        self.assertEqual(g.profile, v89.PROFILE)
        self.assertEqual(g.page_sha256, v89.PAGE_SHA256)
        self.assertEqual(g.shell_digest, v89.CANDIDATE_SHELL_DIGEST)
        self.assertEqual(g.bundle, v89.BUNDLE)
        self.assertEqual(g.bundle_file_sha256, v89.BUNDLE_FILE_SHA256)
        self.assertEqual(g.artifact_pins, v89.ARTIFACT_PINS)
        self.assertEqual(g.archived_profile, v89.ARCHIVED_PROFILE)
        self.assertEqual(fai.TYPED_INSERT, v89.TYPED_INSERT)

    def test_every_generation_file_is_complete(self):
        keys = {'generation', 'profile', 'pageSha256', 'shellDigest', 'bundle', 'bundleFileSha256', 'artifactPins',
                'archivedProfile'}
        files = sorted(fai.GENERATIONS.glob('generation-*.json'))
        self.assertTrue(files)
        for path in files:
            data = json.loads(path.read_text())
            self.assertLessEqual(keys, set(data), path.name)
            self.assertEqual(path.name, f"generation-{data['generation']}.json")
            self.assertEqual(set(data['artifactPins']), set(v89.ARTIFACT_PINS), path.name)


class Refusals(unittest.TestCase):
    def test_a_file_naming_another_generation_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = json.loads((fai.GENERATIONS / 'generation-89.json').read_text())
            data['generation'] = 88
            (Path(tmp) / 'generation-89.json').write_text(json.dumps(data))
            with mock.patch.object(fai, 'GENERATIONS', Path(tmp)):
                with self.assertRaisesRegex(ValueError, 'names generation 88'):
                    fai.Generation(89)

    def test_a_missing_generation_is_refused(self):
        with self.assertRaises(FileNotFoundError):
            fai.Generation(1)


if __name__ == '__main__':
    unittest.main()
