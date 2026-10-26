"""Runner-to-reader receipt boundary, fake files/process only; never loads LOK."""
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
import run_v23_native_s5 as runner
import read_v23_native_s5 as reader
from build_v23_native_s5_owner import COMPILED

class Boundary(unittest.TestCase):
    def test_complete_receipt_binding_and_changed_inputs(self):
        original_table,allrows=runner.cases()
        expected=next(r for r in allrows if r['id']=='shift-Right@caret-mid/backspace')
        setup=next(r for r in original_table['cases'] if r['id']==expected['sourceArm'])
        fixture=(runner.ROOT/original_table['fixture']['path']).read_bytes()
        xml=fixture.replace(b'<office:document ',b'<office:document-content ').replace(b'</office:document>',b'</office:document-content>')
        for mutation in ('none','receipt','source','header'):
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
                build={'exitCode':0,'protectedInputsUnchanged':True,'snapshotsMatch':True,
                       'binary':{'path':str(binary),'sha256':runner.sha(binary)},
                       'sources':{str(f.relative_to(p)):runner.sha(f) for f in sources},
                       'headers':{'header.h':runner.sha(header)}}
                receipt.write_text(json.dumps(build))
                table=copy.deepcopy(original_table);table['fixture']={'path':'fixture.fodt','sha256':runner.sha(fx)}
                table['inputPins']={'fixture.fodt':runner.sha(fx)}
                for module in (runner,reader):
                    for key,value in [('ROOT',p),('TOOLS',tools),('SOURCES',sources)]:stack.enter_context(patch.object(module,key,value))
                    stack.enter_context(patch.object(module,'cases',return_value=(table,[expected])))
                out=p/'out'
                argv=['runner','--binary',str(binary),'--install',str(install),'--build-receipt',str(receipt),'--out',str(out)]
                stack.enter_context(patch.object(sys,'argv',argv))
                def check_output(command,**kw):
                    if command[-1]=='--inventory':return json.dumps({'id':expected['id'],'sequence':expected['sequence']})+'\n'
                    self.assertEqual(command[-1],'--paragraphs')
                    return '\n'.join(reader.paragraph_texts_from_xml(fixture))+'\n'
                stack.enter_context(patch.object(runner.subprocess,'check_output',side_effect=check_output))
                def execute(command,stdout,stderr,env):
                    self.assertEqual(command[3],str(binary))
                    self.assertNotIn('SAL_LOK_OPTIONS',env)
                    for label in ('before','after'):
                        with zipfile.ZipFile(out/'saves'/f'{label}.odt','w') as z:z.writestr('content.xml',xml)
                    sel=setup['setup']['expectedSelection'];point=setup['setup']['expectedMovingPointName'];rect='10,20,0,30'
                    state={'getTextSelection':sel,'INVALIDATE_VISIBLE_CURSOR':rect}
                    row={'id':expected['id'],'shape':setup['shape'],'key':setup['key'],'family':expected['family'],
                         'sequence':expected['sequence'],'mode':'default-native-queued','expectedSelection':sel,
                         'expectedCursorPoint':point,'expectedCursorRect':rect,'before':state,'beforePost':state,
                         'after':state,'beforeSelectionType':0,'afterSelectionType':0,
                         'openedSettleMs':800,'setupSettleMs':800,'finalSettleMs':800,
                         'savedBefore':True,'savedAfter':True,'beforeFile':'before.odt','afterFile':'after.odt',
                         'posts':[dict(x,atMs=i,returnMs=i+.1) for i,x in enumerate(reader.expected_posts(expected))]}
                    stdout.write(json.dumps({'arm':'discover-stub','steps':[{'name':point,'rect':rect}]})+'\n'+json.dumps(row)+'\n')
                    if mutation=='receipt':receipt.write_text(receipt.read_text()+'\n')
                    elif mutation=='source':sources[0].write_text('changed source')
                    elif mutation=='header':header.write_text('changed header')
                    return type('Result',(),{'returncode':0})()
                stack.enter_context(patch.object(runner.subprocess,'run',side_effect=execute))
                self.assertEqual(runner.main(),0 if mutation=='none' else 1)
                completion=json.loads((out/'completion.json').read_text())
                self.assertEqual(completion['protectedInputsUnchanged'],mutation=='none')
                if mutation=='none':
                    self.assertEqual(completion['afterIdentity'],json.loads((out/'identity.json').read_text()))
                    self.assertIn('buildReceipt',completion['afterIdentity'])
                result=reader.read(out)
                self.assertEqual(result['verdict']=='NATIVE_S5_SAVES_AVAILABLE',mutation=='none',result['problems'])

if __name__=='__main__':unittest.main()
