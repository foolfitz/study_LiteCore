"""Astra ruling: exact-sequence native settled references and historical semantic compatibility."""
import base64
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SDK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SDK/'tools'))
import v23_feature_selection_cases as cases
import judge_v23_feature_selection as judge
BASE=SDK.parent/'findings/evidence/link-batch-v23/feature-protocol'
IDS=('shift-Home@heading-mid/backspace-twice','shift-Home@list-mid/backspace-twice')


class SettledNativePages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.live=cases.config()

    def page(self,cid,browser='chrome',adopt=True):
        directory=BASE/'s5-order-prep-02'
        plan=json.loads((directory/'report.json').read_bytes())['config']
        cell=json.loads(gzip.decompress((directory/(browser+'-'+cid.replace('/','__')+'.json.gz')).read_bytes()))
        if adopt:
            plan['s5NativeReferenceSchema']=self.live.get('s5NativeReferenceSchema',1)
            plan['s5'][cid]=copy.deepcopy(self.live['s5'][cid])
        cell['page']['configSha256']=cases.digest(cases.encoded(plan))
        return cell,plan

    def test_own_sequence_settled_native_is_used_in_both_browsers(self):
        for browser in cases.BROWSERS:
            for cid in IDS:
                with self.subTest(browser=browser,case=cid):
                    cell,plan=self.page(cid,browser);value=judge.inspect(cell['page'],plan,browser)
                    self.assertEqual(value['verdict'],'PASS',value)
                    record=value['groups']['S5']
                    self.assertEqual(record['reference'],'native-every-member-settled')
                    self.assertIs(record['nativeOrderIndependent'],False)
                    self.assertIs(record['emptyMark'],False)
                    self.assertTrue(record['singleLineWitness'])

    def test_historical_pages_keep_their_exact_ne_inspections(self):
        for browser in cases.BROWSERS:
            for cid in IDS:
                with self.subTest(browser=browser,case=cid):
                    cell,plan=self.page(cid,browser,False)
                    self.assertEqual(judge.inspect(cell['page'],plan,browser),cell['inspection'])

    def test_existing_reference_partitions_keep_their_semantics_in_schema_2(self):
        for prep,cid,reference in (
            ('s5-prep-03','shift-Left@caret-mid/backspace','native'),
            ('s5-prep-03','shift-Down@caret-mid/delete','settled-wasm'),
            ('s5-prep-03','shift-Right@caret-mid/type','native'),
            ('s5-counted-01','shift-End@cell-end/backspace','settled-wasm')):
            with self.subTest(case=cid):
                directory=BASE/prep;plan=json.loads((directory/'report.json').read_bytes())['config']
                page=json.loads(gzip.decompress((directory/('chrome-'+cid.replace('/','__')+'.json.gz')).read_bytes()))['page']
                plan['s5NativeReferenceSchema']=2;plan['s5'][cid]=copy.deepcopy(self.live['s5'][cid])
                page['configSha256']=cases.digest(cases.encoded(plan));result=judge.inspect(page,plan,'chrome')
                self.assertEqual((result['verdict'],result['groups']['S5'].get('reference')),('PASS',reference),result)

    def test_home_end_still_require_the_browser_single_line_witness(self):
        cell,plan=self.page(IDS[0])
        with patch.object(judge,'single_line',return_value=False):
            value=judge.inspect(cell['page'],plan,'chrome')
        self.assertEqual((value['verdict'],value['groups']['S5']['reference']),('PASS','settled-wasm'))

    def test_unknown_schema_is_ne(self):
        cell,plan=self.page(IDS[0]);plan['s5NativeReferenceSchema']=3
        cell['page']['configSha256']=cases.digest(cases.encoded(plan))
        result=judge.inspect(cell['page'],plan,'chrome')
        self.assertEqual((result['verdict'],result['reason']),('NOT_ESTABLISHED','unknown S5 native reference schema'))

    def test_new_schema_never_falls_back_when_its_declaration_is_bad(self):
        for edit,reason in (
            (lambda p,r:p.update(s5NativeReferenceSchema=True),'unknown S5 native reference schema'),
            (lambda p,r:p.pop('s5NativeReferenceSchema'),'settled native declaration without schema'),
            (lambda p,r:r.pop('nativeEveryMemberSettled'),'settled native declaration absent'),
            (lambda p,r:r.update(nativeEveryMemberSettled=None),'native settled partition/reference differs'),
            (lambda p,r:r.update(referencePolicy='unknown'),'unknown S5 reference policy'),
            (lambda p,r:r.update(nativeOrderIndependent=None),'native witness classification absent')):
            with self.subTest(reason=reason):
                cell,plan=self.page(IDS[0]);edit(plan,plan['s5'][IDS[0]])
                cell['page']['configSha256']=cases.digest(cases.encoded(plan))
                value=judge.inspect(cell['page'],plan,'chrome')
                self.assertEqual((value['verdict'],value['reason']),('NOT_ESTABLISHED',reason))

    def test_empty_mark_refuses_both_native_routes(self):
        for settled in (False,True):
            with self.subTest(settled=settled),self.assertRaisesRegex(ValueError,'empty-mark row has no native oracle'):
                judge.native_reference({'emptyMark':True},b'',every_member_settled=settled)

    def test_plan_requires_the_sealed_report_and_matching_mark_classification(self):
        table=cases.derive(cases.read_rounds())
        marks={c['id']:c for c in json.loads((cases.NATIVE_S5/'empty-mark-reader-01.json').read_bytes())['cells']}
        with patch.object(cases,'NATIVE_S5_SETTLED_READER_SHA256','0'*64),self.assertRaisesRegex(ValueError,'reader output differs'):
            cases.settled_references(table,marks)
        wrong=copy.deepcopy(marks);wrong[IDS[0]]['orderIndependent']=True
        with self.assertRaisesRegex(ValueError,'classification disagrees with empty-mark witness'):
            cases.settled_references(table,wrong)

    def test_own_pair_and_browser_original_guards_are_independent(self):
        cell,plan=self.page(IDS[0]);row=plan['s5'][IDS[0]];page=cell['page']
        original=base64.b64decode(page['s5cand']['originalSave']['base64'])
        result=judge.native_reference(row,original,every_member_settled=True)
        self.assertTrue(result)
        with self.assertRaisesRegex(ValueError,'native reference not comparable'):
            judge.native_reference(row,result,every_member_settled=True)
        # Isolate the byte/before guards below the independently tested certificate boundary.
        with patch.object(judge,'settled_binding',lambda r:r['nativeEveryMemberSettled']):
            changed=copy.deepcopy(row);changed['nativeEveryMemberSettled']['saves']['before']['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'native reference bytes differ'):
                judge.native_reference(changed,original,every_member_settled=True)
            changed=copy.deepcopy(row);changed['native']['before']['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'queued native before bytes differ'):
                judge.native_reference(changed,original,every_member_settled=True)

    def test_aggregate_derives_and_reconciles_the_actual_route_identities(self):
        cells=[];plan=None
        for browser in cases.BROWSERS:
            for cid in IDS:
                cell,one=self.page(cid,browser)
                if plan is None:plan=one
                else:plan['s5'][cid]=one['s5'][cid]
                cells.append(cell)
        # A bounded aggregate model over exactly these real pages, not a qualifying S5 population.
        plan['s5']={cid:plan['s5'][cid] for cid in IDS}
        for cell in cells:cell['page']['configSha256']=cases.digest(cases.encoded(plan))
        result=judge.judge(cells,plan,'s5');g=result['groups']['S5']
        for browser in cases.BROWSERS:
            self.assertEqual(g['nativeSettledDerivedCells'][browser],sorted(IDS))
            self.assertEqual(g['nativeSettledEligibleCells'][browser],sorted(IDS))
            self.assertEqual(g['nativeSettledRoutedCells'][browser],sorted(IDS))
        # This routing-only model intentionally lacks empty-mark cells. A routing mismatch must
        # be diagnosed before the existing empty-mark non-vacuity check, without accepting this model.
        from unittest.mock import patch
        original_inspect=judge.inspect
        def missing_route(page,cfg,browser):
            value=original_inspect(page,cfg,browser)
            if page['caseId']==IDS[0]:value['groups']['S5']['reference']='native'
            return value
        with patch.object(judge,'inspect',side_effect=missing_route):
            value=judge.judge(cells,plan,'s5')
        self.assertEqual(value['groups']['S5']['reason'],'eligible native settled routing differs')

    @staticmethod
    def replace_final(page,raw):
        saved=page['s5cand']['finalSave'];saved.update(base64=base64.b64encode(raw).decode(),sha256=cases.digest(raw))
        call=next(c for c in page['calls'] if c['name']=='s5cand-final-save')
        call['result']['bytes'].update(data=saved['base64'],bytes=len(raw))
        requests=[r for r in page['requests'][call['requestStart']:call['requestEnd']] if r['message']['operation']=='save']
        request=requests[-1]
        reply=next(t for t in page['responses'] if t['generation']==request['generation'] and t['message']['requestId']==request['message']['requestId'])
        reply['message']['result']['buffer'].update(data=saved['base64'],bytes=len(raw))

    def test_queued_heading_and_structure_only_list_results_fail(self):
        for cid in IDS:
            with self.subTest(case=cid):
                cell,plan=self.page(cid);row=plan['s5'][cid]
                raw=(cases.ROOT/row['native']['after']['path']).read_bytes()
                self.replace_final(cell['page'],raw)
                value=judge.inspect(cell['page'],plan,'chrome')
                self.assertEqual(value['verdict'],'FAIL',value)
                record=value['groups']['S5']
                self.assertEqual(record['reference'],'native-every-member-settled')
                self.assertTrue(record['reducedDifference'])
                if 'list-mid' in cid:
                    self.assertIsNone(record['differingParagraph']['index'])
                    self.assertIn('list-header','\n'.join(record['reducedDifference']))


if __name__=='__main__':unittest.main()
