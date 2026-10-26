"""Native S5 type run 02 (fable ruling 3): finite set, order-witness reds, runner-to-reader boundary."""
import contextlib
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
SDK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SDK/'tools'))
import run_v23_native_s5_type as runner
import read_v23_native_s5_type as reader
from read_v23_native_s5 import expected_posts
from build_v23_native_s5_type_owner import COMPILED
RUN01=runner.ROOT/'findings/evidence/link-batch-v23/feature-protocol/s5-native/run-01/native.jsonl'

def record(table,rows,rounds,cell_id):
    """A witnessed record built from the archived rounds' own states for the source arm."""
    item=next(r for r in rows if r['id']==cell_id);setup=next(r for r in table['cases'] if r['id']==item['sourceArm'])
    states=reader.round_states(rounds,item['sourceArm'])
    before=dict(states[0]['before']);between=dict(states[0]['after']);after={'getTextSelection':'','INVALIDATE_VISIBLE_CURSOR':'1,2,0,276'}
    times=[0.0,0.01,815.0,815.01]
    posts=[dict(p,atMs=t,returnMs=t+.005) for p,t in zip(expected_posts(item),times)]
    row={'id':item['id'],'shape':setup['shape'],'key':setup['key'],'family':'type','sequence':item['sequence'],
         'mode':'default-native-queued','expectedSelection':setup['setup']['expectedSelection'],
         'expectedCursorPoint':setup['setup']['expectedMovingPointName'],'expectedCursorRect':before['INVALIDATE_VISIBLE_CURSOR'],
         'before':before,'beforePost':before,'between':between,'after':after,
         'beforeSelectionType':1 if setup['setup']['expectRange'] else 0,
         'betweenSelectionType':0 if between['getTextSelection']=='' else 1,'afterSelectionType':0,
         'openedSettleMs':800,'setupSettleMs':800,'shiftSettleMs':812.0,'finalSettleMs':800,
         'betweenReadStartMs':812.5,'betweenReadEndMs':812.9,
         'savedBefore':True,'savedAfter':True,'beforeFile':'before.odt','afterFile':'after.odt','posts':posts}
    return item,setup,states,row

class NativeS5Type(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table,cls.rows=runner.cases();cls.rounds=reader.source.read_rounds()

    def test_population_is_the_56_native_capable_type_cells(self):
        self.assertEqual(len(self.rows),56)
        self.assertEqual({r['family'] for r in self.rows},{'type'})
        self.assertEqual(sum(r['referencePolicy']=='native' for r in self.rows),28)
        good='\n'.join(json.dumps({'id':r['id'],'sequence':r['sequence']}) for r in self.rows)
        runner.read_inventory(good,self.rows)
        with self.assertRaises(ValueError):runner.read_inventory(good+'\n'+json.dumps({'id':'shift-Right@caret-mid/delete','sequence':['Shift+Right','Delete']}),self.rows)

    def test_strong_witness_and_the_three_ruling_reds(self):
        item,setup,states,row=record(self.table,self.rows,self.rounds,'shift-Right@caret-mid/type')
        self.assertEqual(setup['nativeAfterSelectionText'],['T']*3)
        self.assertEqual(reader.order_witness(row,setup,states),('selection-before-x',[]))
        # Red 1: swap the between-read and x timestamps.
        bad=copy.deepcopy(row);x=bad['posts'][2]
        bad['betweenReadEndMs'],x['atMs']=x['atMs'],bad['betweenReadEndMs']
        witness,why=reader.order_witness(bad,setup,states)
        self.assertIsNone(witness);self.assertIn('between-read does not complete before the x post',why)
        # Equal timestamps (run-02's six-digit output) cannot witness "precedes".
        bad=copy.deepcopy(row);bad['betweenReadEndMs']=bad['posts'][2]['atMs']
        self.assertIn('between-read does not complete before the x post',reader.order_witness(bad,setup,states)[1])
        # Red 2: the between-read text replaced by the post-x selection.
        bad=copy.deepcopy(row);bad['between']['getTextSelection']=bad['after']['getTextSelection']
        witness,why=reader.order_witness(bad,setup,states)
        self.assertIsNone(witness);self.assertIn('between-read selection differs from the three native rounds',why)
        # Red 3: the actual run-01 record of this cell has no between-read.
        old=next(json.loads(l) for l in RUN01.read_text().splitlines() if l.strip() and json.loads(l).get('id')==item['id'])
        witness,why=reader.order_witness(old,setup,states)
        self.assertIsNone(witness);self.assertIn('missing between-read',why)

    def test_every_run01_type_record_reads_ne(self):
        old={(r:=json.loads(l)).get('id'):r for l in RUN01.read_text().splitlines() if l.strip()}
        setups={r['id']:r for r in self.table['cases']}
        for item in self.rows:
            witness,why=reader.order_witness(old[item['id']],setups[item['sourceArm']],reader.round_states(self.rounds,item['sourceArm']))
            self.assertIsNone(witness,item['id']);self.assertIn('missing between-read',why)

    def test_cap_and_silent_member_witness(self):
        _,setup,states,row=record(self.table,self.rows,self.rounds,'shift-Right@caret-mid/type')
        for mutate,reason in [(lambda r:r.update(shiftSettleMs=-8025.0),'Shift settle reached its cap'),
                              (lambda r:r.pop('shiftSettleMs'),'missing Shift settle'),
                              (lambda r:r.pop('between'),'missing between-read'),
                              (lambda r:r.update(betweenReadStartMs=0.001),'between-read does not follow the Shift posts')]:
            bad=copy.deepcopy(row);mutate(bad)
            witness,why=reader.order_witness(bad,setup,states)
            self.assertIsNone(witness);self.assertIn(reason,why)
        # Silent member whose caret moves: range-one, Shift+Left collapses the one-character range.
        _,setup,states,row=record(self.table,self.rows,self.rounds,'shift-Left@range-one/type')
        self.assertEqual(setup['nativeAfterSelectionText'],['']*3)
        self.assertEqual(reader.order_witness(row,setup,states),('settle-only',[]))
        # Its named limit: the text alone cannot tell the post-x state, the caret can.
        bad=copy.deepcopy(row);bad['between']['getTextSelection']=bad['after']['getTextSelection']
        self.assertEqual(reader.order_witness(bad,setup,states),('settle-only',[]))
        bad['between']=copy.deepcopy(bad['after'])
        witness,why=reader.order_witness(bad,setup,states)
        self.assertIsNone(witness);self.assertIn('silent member caret not at the moving point',why)
        bad=copy.deepcopy(row);bad['between']=dict(bad['before'])
        self.assertIsNone(reader.order_witness(bad,setup,states)[0])
        bad=copy.deepcopy(row);bad['betweenSelectionType']=1
        self.assertIn('silent member not collapsed at the between-read',reader.order_witness(bad,setup,states)[1])
        bad=copy.deepcopy(row);bad['beforePost']=dict(bad['beforePost'],INVALIDATE_VISIBLE_CURSOR='9,9,0,276')
        self.assertIn('native round caret not comparable with this run',reader.order_witness(bad,setup,states)[1])

    def test_harness_settles_and_reads_only_between_the_two_members(self):
        text=(SDK/'tools/v23_native_s5_type.cpp').read_text()
        self.assertEqual(runner.sha(SDK/'tools/link_native_extend_signatures.cpp'),runner.base.source.PINS['tool-source-as-run.cpp'])
        dispatch=text.split('v23s5::dispatch({member},',1)[1].split('        });',1)[0]
        self.assertEqual(dispatch.count('s.d->pClass->'),1)
        for forbidden in ('settle(','drain(','snap(','paste(','saveAs('):self.assertNotIn(forbidden,dispatch)
        between=text.split('post(seq[0]);',1)[1].split('post(seq[1]);',1)[0]
        calls=[line.strip() for line in between.splitlines() if '(' in line and not line.strip().startswith('//')]
        self.assertEqual(calls,['const auto shiftSettled=settle(s,800,8000);','const auto readStart=nowMs()-start;',
            'const auto between=snap(s);','const int betweenType=s.d->pClass->getSelectionType(s.d);','const auto readEnd=nowMs()-start;'])
        self.assertEqual(text.count('post(seq['),2)
        # Timestamps are printed with enough digits to order microsecond-apart events past 1000 ms.
        main=text.split('int main(',1)[1]
        self.assertIn('std::cout.precision(15);',main)
        self.assertLess(main.index('std::cout.precision(15);'),main.index('measured(kit'))
        # run-01's harness and builder are untouched; run-01 keeps reading through them.
        self.assertNotIn('v23_native_s5_type',(SDK/'tools/v23_native_s5.cpp').read_text())

    def test_runner_to_reader_boundary_with_fallback_cell(self):
        cells=['shift-Right@caret-mid/type','shift-Left@range-one/type']
        fixture=(runner.ROOT/self.table['fixture']['path']).read_bytes()
        xml=fixture.replace(b'<office:document ',b'<office:document-content ').replace(b'</office:document>',b'</office:document-content>')
        built={c:record(self.table,self.rows,self.rounds,c) for c in cells}
        for mutation in ('none','cap','source'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp,contextlib.ExitStack() as stack:
                p=Path(tmp);tools=p/'tools';tools.mkdir();install=p/'install';install.mkdir()
                (install/'libstandin.so').write_bytes(b'standin library')
                sources=[]
                for name in COMPILED:
                    f=tools/name;f.write_text('standin '+name);sources.append(f)
                header=p/'header.h';header.write_text('standin header')
                binary=p/'binary';binary.write_bytes(b'standin binary; execution mocked')
                fx=p/'fixture.fodt';fx.write_bytes(fixture)
                receipt=p/'build-receipt.json'
                receipt.write_text(json.dumps({'exitCode':0,'protectedInputsUnchanged':True,'snapshotsMatch':True,
                    'binary':{'path':str(binary),'sha256':runner.sha(binary)},
                    'sources':{str(f.relative_to(p)):runner.sha(f) for f in sources},'headers':{'header.h':runner.sha(header)}}))
                table=copy.deepcopy(self.table);table['fixture']={'path':'fixture.fodt','sha256':runner.sha(fx)}
                table['inputPins']={'fixture.fodt':runner.sha(fx)}
                expected=[built[c][0] for c in cells]
                for module in (runner,reader):
                    for key,value in [('ROOT',p),('TOOLS',tools),('SOURCES',sources)]:stack.enter_context(patch.object(module,key,value))
                    stack.enter_context(patch.object(module,'cases',return_value=(table,expected)))
                out=p/'out'
                stack.enter_context(patch.object(sys,'argv',['runner','--binary',str(binary),'--install',str(install),'--build-receipt',str(receipt),'--out',str(out)]))
                def check_output(command,**kw):
                    if command[-1]=='--inventory':return ''.join(json.dumps({'id':e['id'],'sequence':e['sequence']})+'\n' for e in expected)
                    self.assertEqual(command[-1],'--paragraphs')
                    return '\n'.join(reader.paragraph_texts_from_xml(fixture))+'\n'
                stack.enter_context(patch.object(runner.subprocess,'check_output',side_effect=check_output))
                def execute(command,stdout,stderr,env):
                    self.assertEqual(command[3],str(binary));self.assertNotIn('SAL_LOK_OPTIONS',env)
                    steps=[]
                    for i,c in enumerate(cells):
                        row=copy.deepcopy(built[c][3]);stem=c.replace('/','_')
                        row.update(beforeFile=stem+'-before.odt',afterFile=stem+'-after.odt')
                        if mutation=='cap' and i==0:row['shiftSettleMs']=-8025.0
                        for label in ('before','after'):
                            with zipfile.ZipFile(out/'saves'/row[label+'File'],'w') as z:z.writestr('content.xml',xml)
                        steps.append({'name':row['expectedCursorPoint'],'rect':row['expectedCursorRect']})
                        built[c]=built[c][:3]+(row,)
                    stdout.write(json.dumps({'arm':'discover-stub','steps':steps})+'\n'+''.join(json.dumps(built[c][3])+'\n' for c in cells))
                    if mutation=='source':sources[0].write_text('changed source')
                    return type('Result',(),{'returncode':0})()
                stack.enter_context(patch.object(runner.subprocess,'run',side_effect=execute))
                self.assertEqual(runner.main(),1 if mutation=='source' else 0)
                result=reader.read(out)
                self.assertEqual(result['verdict']=='NATIVE_S5_TYPE_SAVES_READ',mutation!='source',result['problems'])
                if mutation=='source':continue
                status={r['id']:(r['status'],r['orderWitness']) for r in result['cells']}
                self.assertEqual(status[cells[1]],('NATIVE_SAVE_AVAILABLE','settle-only'))
                self.assertEqual(status[cells[0]],('NOT_ESTABLISHED',None) if mutation=='cap' else ('NATIVE_SAVE_AVAILABLE','selection-before-x'))
                self.assertEqual(result['counts']['fallbackSettledWasm'],int(mutation=='cap'))

if __name__=='__main__':unittest.main()
