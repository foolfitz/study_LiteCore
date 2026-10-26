#!/usr/bin/env python3
"""Causal controls for the source-only S tables; no browser/native execution."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from v23_feature_s_cases import read_rounds, derive


class SourcePopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.rounds = read_rounds()

    def test_archive_and_missing_oracle_are_distinct(self):
        result = derive(self.rounds)
        self.assertEqual(result['contracts']['S2']['wireStateOperation'], 'editorGetStateV2')
        self.assertEqual(result['counts'], {'S1':84,'S2':108,'v19PreRed':16,'S3':10,'S4':9,'S5':588})
        self.assertEqual(len({r['id'] for r in result['S5']}), 588)
        self.assertEqual(sum(r['referencePolicy']=='native' for r in result['S5']), 196)
        self.assertEqual(sum(r['referencePolicy']=='settled-wasm' for r in result['S5']), 196)
        self.assertTrue(all(r['nativeContinuationOracle']['status'] in
                            ('NOT_ESTABLISHED_MISSING_EXECUTION', 'NOT_APPLICABLE') for r in result['S5']))
        self.assertTrue(all(r['settledWasmOracle']['status']=='NOT_ESTABLISHED_UNPERFORMED'
                            for r in result['S5'] if r['referencePolicy']=='settled-wasm'))
        self.assertTrue(all(len(r['nativeReferences']) == 3 for r in result['cases']))
        pre = {r['id'] for r in result['cases'] if 'v19-pre-red' in r['memberships']}
        self.assertTrue(pre.isdisjoint(result['preRedExcluded']))
        sequences = {r['family']:r['sequence'] for r in result['S5'] if r['sourceArm']=='shift-Left@caret-mid'}
        self.assertEqual(sequences['backspace-before-and-after'], ['Backspace','Shift+Left','Backspace'])
        self.assertEqual(sequences['type'], ['Shift+Left','text:x'])

    def test_empty_source(self):
        with self.assertRaises(ValueError): derive([[],[],[]])

    def test_missing_round_member(self):
        rounds = copy.deepcopy(self.rounds)
        rounds[1] = [r for r in rounds[1] if r.get('arm') != 'shift-Left@caret-mid']
        with self.assertRaisesRegex(ValueError, 'membership'): derive(rounds)

    def test_new_truth_source_member_cannot_silently_escape(self):
        rounds = copy.deepcopy(self.rounds)
        for rows in rounds:
            row = copy.deepcopy(next(r for r in rows if r.get('kind')=='shift'))
            row['arm'] = 'shift-Left@invented-shape'; row['shape'] = 'invented-shape'; rows.append(row)
        with self.assertRaisesRegex(ValueError, 'cardinality'): derive(rounds)

    def test_duplicate_member(self):
        rounds = copy.deepcopy(self.rounds)
        rounds[0].append(copy.deepcopy(next(r for r in rounds[0] if r.get('kind')=='shift')))
        with self.assertRaisesRegex(ValueError, 'duplicate'): derive(rounds)

    def test_invalid_setup_not_accepted_as_oracle(self):
        rounds = copy.deepcopy(self.rounds)
        next(r for r in rounds[1] if r.get('arm')=='shift-Right@caret-mid')['before']['getTextSelection']='wrong'
        with self.assertRaisesRegex(ValueError, 'setup mismatch'): derive(rounds)

    def test_callback_in_no_callback_cell(self):
        rounds = copy.deepcopy(self.rounds)
        next(r for r in rounds[1] if r.get('arm')=='shift-Left@doc-start')['callbacks'].append({'tMs':1})
        with self.assertRaisesRegex(ValueError, 'no-callback'): derive(rounds)

if __name__ == '__main__': unittest.main()
