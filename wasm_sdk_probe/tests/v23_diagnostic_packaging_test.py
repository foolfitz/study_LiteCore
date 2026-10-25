#!/usr/bin/env python3
"""Contract controls use the complete actual v22 contract as their population."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from build_e2_v23_diagnostic_profile import contract_problems, PROFILE


class DiagnosticContract(unittest.TestCase):
    def setUp(self):
        self.reference = json.loads((ROOT / 'dist/profiles/e2-editor-v22/sdk-manifest.json').read_text())
        self.candidate = copy.deepcopy(self.reference)
        self.candidate['profile'] = PROFILE

    def test_inherited_contract(self):
        self.assertEqual([], contract_problems(self.candidate, self.reference))

    def test_v22_cannot_masquerade_as_diagnostic(self):
        self.assertTrue(contract_problems(self.reference, self.reference))

    def test_abi6_is_feature_only(self):
        self.candidate['editorContract']['abiVersion'] = 6
        self.assertTrue(contract_problems(self.candidate, self.reference))

    def test_every_action_is_inherited_verbatim(self):
        for name in self.reference['editorContract']['actions']:
            with self.subTest(action=name):
                changed = copy.deepcopy(self.candidate)
                del changed['editorContract']['actions'][name]
                self.assertTrue(contract_problems(changed, self.reference))

    def test_new_action_is_refused(self):
        self.candidate['editorContract']['actions']['invented-shift'] = {'id': 999, 'gestures': []}
        self.assertTrue(contract_problems(self.candidate, self.reference))

    def test_diagnostic_capability_is_not_public(self):
        self.candidate['capabilities'].append('v23-diagnostic')
        self.assertTrue(contract_problems(self.candidate, self.reference))

    def test_reference_identity(self):
        self.reference['profile'] = PROFILE
        self.assertTrue(contract_problems(self.candidate, self.reference))


if __name__ == '__main__':
    unittest.main()
