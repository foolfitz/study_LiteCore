"""Astra ruling: exact-sequence native settled references and historical semantic compatibility."""
import base64
import copy
import contextlib
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


class NativeSettledReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import read_v23_native_s5_settled_reference as reader
        cls.reader=reader;cls.table,cls.expected=reader.marks.population()
        cls.rows=[json.loads(line) for line in (reader.DEFAULT/'native.jsonl').read_bytes().splitlines() if line]
        cls.native={r['id']:r for r in cls.rows if 'id' in r};cls.cid=IDS[0]
        cls.report=reader.read(reader.DEFAULT)
        cls.base_result=reader.marks.read(reader.DEFAULT)
        cls.queued_result=reader.queued.read(reader.QUEUED)

    def test_complete_real_population_and_partition(self):
        refs=self.reader.references(self.report,self.table)
        expected={r['id'] for r in self.report['cells'] if r['emptyMark'] is False and r['orderIndependent'] is False}
        self.assertEqual(set(refs),expected);self.assertTrue(refs)
        self.assertEqual(len(self.report['cells']),len(self.expected))

    def test_invalid_upstream_readers_and_classification_refuse(self):
        for module,result,reason in ((self.reader.marks,self.base_result,'invalid native empty-mark witness'),
                                     (self.reader.queued,self.queued_result,'invalid queued native witness')):
            invalid={**result,'verdict':'NOT_ESTABLISHED','problems':['forced invalid predecessor']}
            with self.subTest(reason=reason),patch.object(module,'read',return_value=invalid),self.assertRaisesRegex(ValueError,reason):
                self.reader.read(self.reader.DEFAULT)
        invalid=copy.deepcopy(self.base_result)
        invalid['cells'][0]['orderIndependent']=not invalid['cells'][0]['orderIndependent']
        with patch.object(self.reader.marks,'read',return_value=invalid),self.assertRaisesRegex(ValueError,'classification differs'):
            self.reader.read(self.reader.DEFAULT)

    def bad_order(self,mutate,reason):
        row=copy.deepcopy(self.native[self.cid]);mutate(row)
        with self.assertRaisesRegex(ValueError,reason):self.reader.validate_order(row,self.expected[self.cid])

    def test_exact_sequence_policy_operations_and_posts(self):
        for edit,reason in (
            (lambda r:r['sequence'].reverse(),'native sequence differs'),
            (lambda r:r['interMemberSettle'].update(after='Shift only'),'inter-member policy differs'),
            (lambda r:r['steps'].pop(),'member operations/count differ'),
            (lambda r:r['steps'].__setitem__(0,'malformed'),'member operations/count differ'),
            (lambda r:r['steps'][0].update(operation='Backspace'),'member operations/count differ'),
            (lambda r:r['posts'].pop(),'key posts/count differ'),
            (lambda r:r['posts'].__setitem__(0,'malformed'),'key posts/count differ'),
            (lambda r:r['posts'][0].update(key=1283),'key posts/count differ'),
            (lambda r:r['posts'][0].update(type=False),'key posts/count differ')):
            with self.subTest(reason=reason):self.bad_order(edit,reason)

    def test_open_setup_and_member_caps(self):
        for field in ('openedSettleMs','setupSettleMs'):
            with self.subTest(field=field):self.bad_order(lambda r:r.update({field:-1}),'settle missing/capped')
        self.bad_order(lambda r:r['steps'][0].update(settleMs=-1),'member settle/read missing/capped')

    def test_finite_nonboolean_and_monotone_times(self):
        for value in (False,float('nan'),float('inf')):
            with self.subTest(value=value):self.bad_order(lambda r:r['posts'][0].update(atMs=value),'invalid native post time')
        self.bad_order(lambda r:r['posts'][1].update(atMs=-1),'invalid native post time')
        self.bad_order(lambda r:r['steps'][0].update(readStartMs=float('nan')),'member settle/read missing/capped')

    def test_member_reads_must_be_between_key_posts(self):
        self.bad_order(lambda r:r['steps'][0].update(readStartMs=0),'read not ordered between posts')
        self.bad_order(lambda r:r['steps'][0].update(readEndMs=r['posts'][2]['atMs']),'read not ordered between posts')
        self.bad_order(lambda r:r['steps'][0].update(readEndMs=r['steps'][0]['readStartMs']-1),'read not ordered between posts')

    def test_every_member_has_the_actual_state_read_payload(self):
        for edit in (lambda r:r['steps'][-1].pop('state'),
                     lambda r:r['steps'][-1]['state'].pop('getTextSelection'),
                     lambda r:r['steps'][-1].update(selectionType=False)):
            with self.subTest(edit=edit):self.bad_order(edit,'state payload missing/malformed')

    def test_population_is_complete_unique_and_not_empty(self):
        records=[self.native[cid] for cid in self.expected]
        for rows,wanted in ((records[:-1],self.expected),(records+[records[0]],self.expected),([],self.expected),
                            (records,{**self.expected,'new-generated-member':{}})):
            with self.subTest(count=len(rows)),self.assertRaisesRegex(ValueError,'missing/extra/duplicate'):
                self.reader.index_records(rows,wanted,'settled')

    def test_execution_binary_core_and_command_bindings(self):
        directory=self.reader.DEFAULT
        receipt=json.loads((directory/'build/build-receipt.json').read_bytes())
        command=json.loads((directory/'command.json').read_bytes())
        self.reader.validate_execution(directory,receipt,command)
        for target,edit,reason in (
            ('command',lambda r:r['argv'].__setitem__(2,'0'),'invocation differs'),
            ('receipt',lambda r:r.update(binary='0'*64),'binary differs'),
            ('command',lambda r:r.update(mode='unipoll'),'command policy differs'),
            ('command',lambda r:r['installSha256'].update({'libmergedlo.so':'0'*64}),'core differs')):
            a,b=copy.deepcopy(receipt),copy.deepcopy(command);edit(a if target=='receipt' else b)
            with self.subTest(reason=reason),self.assertRaisesRegex(ValueError,reason):self.reader.validate_execution(directory,a,b)

    def test_own_saves_are_present_and_hash_bound(self):
        directory=self.reader.DEFAULT;row=self.native[self.cid]
        artifacts=json.loads((directory/'comparison.json').read_bytes())['artifacts']
        self.reader.checked_save(directory,row,'before',artifacts)
        for update,reason in (({'savedBefore':False},'own save missing'),({'beforeFile':'../outside.odt'},'own save missing'),
                              ({'beforeFile':'absent.odt'},'own save missing/hash differs')):
            with self.subTest(update=update),self.assertRaisesRegex(ValueError,reason):
                self.reader.checked_save(directory,{**row,**update},'before',artifacts)
        wrong={**artifacts,'saves/'+row['beforeFile']:'0'*64}
        with self.assertRaisesRegex(ValueError,'hash differs'):self.reader.checked_save(directory,row,'before',wrong)

    def test_binding_membership_and_bytes_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'data';p.write_bytes(b'data');bindings={self.reader.name(p):self.reader.sha(p)}
            self.reader.verify_bindings(bindings,{p})
            with self.assertRaisesRegex(ValueError,'binding population differs'):self.reader.verify_bindings({}, {p})
            with self.assertRaisesRegex(ValueError,'binding population differs'):self.reader.verify_bindings(bindings,{p,p.parent/'new'})
            p.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'input changed'):self.reader.verify_bindings(bindings,{p})

    def test_dependency_census_rejects_a_consumer_plan_cycle(self):
        import ast
        original=self.reader.ast.parse
        def parse(text):return original(text+'\nimport v23_feature_selection_cases\n')
        with patch.object(self.reader.ast,'parse',side_effect=parse),self.assertRaisesRegex(ValueError,'depends on its consumer plan'):
            self.reader.python_sources()

    def test_report_schema_coverage_and_classification(self):
        for edit,reason in (
            (lambda r:r.update(schema=True),'report invalid'),
            (lambda r:r.update(verdict='NOT_ESTABLISHED'),'report invalid'),
            (lambda r:r['cells'].pop(),'missing/extra/duplicate'),
            (lambda r:r['cells'].append(r['cells'][0]),'missing/extra/duplicate'),
            (lambda r:r['cells'][0].update(emptyMark=0),'classification malformed'),
            (lambda r:next(c for c in r['cells'] if c['reference']) .update(reference=None),'partition/reference differs'),
            (lambda r:next(c for c in r['cells'] if c['reference'])['reference']['schedule'].update(after='Shift'),'reference identity differs')):
            report=copy.deepcopy(self.report);edit(report)
            with self.subTest(reason=reason),self.assertRaisesRegex(ValueError,reason):self.reader.references(report,self.table)
        table=copy.deepcopy(self.table);table['S5'].append({**next(iter(self.expected.values())),'id':'new-generated-member'})
        with self.assertRaisesRegex(ValueError,'missing/extra/duplicate'):self.reader.references(self.report,table)

    def test_pair_guards_keep_before_structure_and_noncollapse(self):
        from v23_s5_comparison import validate_settled_pair,odt_content
        ref=next(c['reference'] for c in self.report['cells'] if c['reference'])
        before=(cases.ROOT/ref['saves']['before']['path']).read_bytes();after=(cases.ROOT/ref['saves']['after']['path']).read_bytes()
        def edit(raw,fn):
            src=zipfile.ZipFile(io.BytesIO(raw));out=io.BytesIO()
            with zipfile.ZipFile(out,'w') as dst:
                for item in src.infolist():dst.writestr(item,fn(src.read(item.filename)) if item.filename=='content.xml' else src.read(item.filename))
            return out.getvalue()
        wrong=edit(before,lambda x:x.replace(b'Heading_20_1',b'Heading_20_2'))
        self.assertNotEqual(odt_content(wrong),odt_content(before))
        with self.assertRaisesRegex(ValueError,'before differs from queued native before'):validate_settled_pair(wrong,after,before)
        collapsed=edit(before,lambda x:x.replace(b'</text:p>',b'<text:soft-page-break/></text:p>',1))
        self.assertNotEqual(odt_content(collapsed),odt_content(before))
        with self.assertRaisesRegex(ValueError,'reduction collapses settled native edit'):validate_settled_pair(before,collapsed,before)

    def test_native_font_declaration_guards_remain_exact(self):
        import re
        from v23_s5_comparison import strip_ffd,odt_content
        ref=next(c['reference'] for c in self.report['cells'] if c['reference'])
        content=odt_content((cases.ROOT/ref['saves']['before']['path']).read_bytes())
        strip_ffd(content)
        for raw,reason in (
            (re.sub(rb'<office:font-face-decls>.*?</office:font-face-decls>',b'',content,flags=re.S),'not uniquely present'),
            (re.sub(rb'(<office:font-face-decls>).*?(</office:font-face-decls>)',rb'\1\2',content,flags=re.S),'font-face-decls empty'),
            (content.replace(b'<office:body>',b'<office:other>'),'office:body absent')):
            with self.subTest(reason=reason),self.assertRaisesRegex(ValueError,reason):strip_ffd(raw)

    @contextlib.contextmanager
    def certificate(self):
        cell=copy.deepcopy(next(c for c in self.report['cells'] if c['reference']))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'certificate.json'
            report={'schema':1,'verdict':self.reader.VERDICT,'problems':[],'cells':[cell]}
            ref=copy.deepcopy(cell['reference'])
            row={'id':cell['id'],'family':ref['family'],'sequence':copy.deepcopy(ref['sequence']),'referencePolicy':ref['referencePolicy'],
                 'emptyMark':False,'nativeOrderIndependent':False,'nativeEveryMemberSettled':ref}
            def seal():
                path.write_text(json.dumps(report));ref['readerReport']={'path':path.name,'sha256':self.reader.sha(path)}
            seal()
            with patch.object(self.reader,'ROOT',root):yield row,report,seal

    def test_sealed_certificate_positive_and_partition_guards(self):
        with self.certificate() as (row,report,seal):self.assertEqual(self.reader.binding(row),row['nativeEveryMemberSettled'])
        for changes,reason in (({'nativeEveryMemberSettled':None},'reference absent'),({'emptyMark':True},'invalid every-member-settled partition'),
                               ({'nativeOrderIndependent':True},'invalid every-member-settled partition'),({'family':'type'},'invalid every-member-settled partition')):
            with self.subTest(changes=changes),self.certificate() as (row,report,seal):
                row.update(changes)
                with self.assertRaisesRegex(ValueError,reason):self.reader.binding(row)

    def test_certificate_path_file_and_hash_guards(self):
        for path in ('','../outside','/absolute'):
            with self.subTest(path=path),self.certificate() as (row,report,seal):
                row['nativeEveryMemberSettled']['readerReport']['path']=path
                with self.assertRaisesRegex(ValueError,'certificate path invalid'):self.reader.binding(row)
        for edit in (lambda r:r['readerReport'].update(path='missing.json'),lambda r:r['readerReport'].update(sha256='0'*64)):
            with self.certificate() as (row,report,seal):
                edit(row['nativeEveryMemberSettled'])
                with self.assertRaisesRegex(ValueError,'certificate missing/hash differs'):self.reader.binding(row)

    def test_certificate_schema_population_and_exact_identity(self):
        for edit,reason in (
            (lambda row,r:r.update(schema=2),'certificate invalid'),
            (lambda row,r:r.update(verdict='NOT_ESTABLISHED'),'certificate invalid'),
            (lambda row,r:r['cells'].append(copy.deepcopy(r['cells'][0])),'certificate cell differs'),
            (lambda row,r:row['nativeEveryMemberSettled']['witness'].update(id='wrong'),'certificate cell differs'),
            (lambda row,r:row['sequence'].append('Backspace'),'certificate sequence/schedule differs')):
            with self.subTest(reason=reason),self.certificate() as (row,report,seal):
                edit(row,report);seal()
                with self.assertRaisesRegex(ValueError,reason):self.reader.binding(row)


if __name__=="__main__":unittest.main()
