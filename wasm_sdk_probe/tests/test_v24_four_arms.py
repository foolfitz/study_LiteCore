"""Frozen-77/v24 identity positives and reds; no synthetic row gets product credit."""
import copy
import json
from pathlib import Path
import sys
import unittest

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK / 'tools'))
import judge_v24_product_four_arms as reader
import v24_feature_selection_cases as cases

EVIDENCE = SDK.parent / 'findings/evidence/link-batch-v24/count-preparation'


class IdentityControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = json.loads((EVIDENCE / 'a4-green-01/wrapper.json').read_bytes())['identity']
        i = cls.identity
        a = reader.j23.arms
        cls.page_identity = {'profile': cases.PROFILE, 'served': {
            **i['shell']['served'], a.HTML: i['servedHtmlSha256'],
            a.OBSERVER_ENTRY: i['observerEntrySha256'], a.OBSERVER_CORE: i['observerCoreSha256'],
            **{f"profiles/{i['profile']}/{n}": h for n, h in i['profileArtifacts'].items()}}}

    def check_identity(self, identity):
        record = object.__new__(reader.Record)
        record.identity = identity
        record.page = {'identity': self.page_identity}
        record._identity(SDK)

    def test_good_identity(self):
        self.check_identity(self.identity)

    def test_identity_reds(self):
        for field, value, reason in (('profile', 'e2-editor-v23', 'v24 ABI6'),
                                     ('abiVersion', 7, 'v24 ABI6'),
                                     ('profileArtifacts', {}, 'frozen v24')):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.identity); changed[field] = value
                with self.assertRaisesRegex(ValueError, reason):
                    self.check_identity(changed)
        for field in ('bundle', 'bundleFileSha256'):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.identity); changed['shell'][field] = 'wrong'
                with self.assertRaisesRegex(ValueError, 'not frozen 77'):
                    self.check_identity(changed)

    def test_old_runs_have_explicit_generation_reason(self):
        result = json.loads((EVIDENCE / 'a4-old-runs-01.json').read_bytes())
        self.assertEqual(result['rows'], 24)
        self.assertTrue(all(v['outcome'] == 'NOT_ESTABLISHED' for v in result['arms'].values()))
        for run in result['runs']:
            for row in run['rows']:
                self.assertIn('shell generation is not frozen 77', row['why'])

    def test_code_objects_unchanged(self):
        self.assertIs(reader.aggregate.__code__, reader.j23.aggregate.__code__)
        self.assertIs(reader.judge_run.__code__, reader.j23.judge_run.__code__)
        self.assertIs(reader.G['_judge_run'].__code__, reader.j23._judge_run.__code__)


if __name__ == '__main__':
    unittest.main()
