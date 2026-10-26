"""Native S5 instruments: finite source set, FIFO stub and real saved-content reds."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
SDK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SDK/'tools'))
import run_v23_native_s5 as runner
import read_v23_native_s5 as reader

XML='''<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><office:text><text:p>{}</text:p></office:text></office:body></office:document-content>'''
def odt(path,text):
    with zipfile.ZipFile(path,'w') as z:z.writestr('content.xml',XML.format(text))

class NativeS5(unittest.TestCase):
    def test_source_derived_inventory_and_missing_extra_reds(self):
        table,rows=runner.cases()
        self.assertEqual(len(rows),392)
        self.assertEqual(sum(r['referencePolicy']=='native' for r in rows),196)
        good=[{'id':r['id'],'sequence':r['sequence']} for r in rows]
        encode=lambda rows:'\n'.join(json.dumps(r) for r in rows)
        runner.read_inventory(encode(good),rows)
        for bad in ([],good[:-1],good+[good[0]],good+[{'id':'invented','sequence':[]} ]):
            with self.assertRaises(ValueError):runner.read_inventory(encode(bad),rows)
        bad=copy.deepcopy(good);bad[0]['sequence'].reverse()
        with self.assertRaises(ValueError):runner.read_inventory(encode(bad),rows)

    def test_exact_sequence_dispatch_with_standalone_recording_stub(self):
        # This only compiles a tiny test of the pure header, never the LOK harness/core.
        harness=r'''#include "v23_native_s5_sequence.hpp"
#include <iostream>
int main(){for(const auto* family:v23s5::families){
std::cout<<family;
v23s5::dispatch(v23s5::sequence(family,1027,"Right"),[](int type,int ch,int key){std::cout<<" "<<type<<","<<ch<<","<<key;});
std::cout<<"\n";}}
'''
        header=(SDK/'tools/v23_native_s5_sequence.hpp').read_text()
        variants=[('actual',header),('discard-prefix',header.replace('return {back,shift,back}','return {shift,back}')),
                  ('wrong-direction',header.replace('1283','1286')),
                  ('type-as-key',header.replace('text{120,0','text{0,120')),
                  ('omit-keyup',header.replace('send(1,post.character,post.key);',';'))]
        expected={r['family']:reader.expected_posts(r) for r in runner.cases()[1] if r['sourceArm']=='shift-Right@caret-mid'}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'test.cpp').write_text(harness)
            for name,text in variants:
                (p/'v23_native_s5_sequence.hpp').write_text(text)
                subprocess.run(['g++','-std=c++17','-I'+tmp,str(p/'test.cpp'),'-o',str(p/'test')],check=True,capture_output=True)
                lines=subprocess.check_output([str(p/'test')],text=True).splitlines()
                actual={}
                for line in lines:
                    family,*posts=line.split();actual[family]=[dict(zip(('type','character','key'),map(int,item.split(',')))) for item in posts]
                self.assertEqual(actual==expected,name=='actual',name)

    def test_actual_saves_and_cell_refusals(self):
        table,rows=runner.cases();expected=next(r for r in rows if r['id']=='shift-Right@caret-mid/backspace')
        setup=next(r for r in table['cases'] if r['id']==expected['sourceArm'])
        selection=setup['setup']['expectedSelection']
        row={'id':expected['id'],'shape':setup['shape'],'key':setup['key'],'family':expected['family'],
             'sequence':expected['sequence'],'mode':'default-native-queued','expectedSelection':selection,
             'before':{'getTextSelection':selection,'INVALIDATE_VISIBLE_CURSOR':'10,20,0,30'},
             'beforePost':{'getTextSelection':selection,'INVALIDATE_VISIBLE_CURSOR':'10,20,0,30'},
             'expectedCursorPoint':setup['setup']['expectedMovingPointName'],'expectedCursorRect':'10,20,0,30',
             'beforeSelectionType':0,'afterSelectionType':0,'after':{'getTextSelection':''},
             'openedSettleMs':800,'setupSettleMs':800,'finalSettleMs':800,
             'savedBefore':True,'savedAfter':True,'beforeFile':'before.odt','afterFile':'after.odt',
             'posts':[dict(p,atMs=i,returnMs=i+.1) for i,p in enumerate(reader.expected_posts(expected))]}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);odt(p/'before.odt','abcd');odt(p/'after.odt','abd')
            artifacts={'saves/'+f.name:runner.sha(f) for f in p.iterdir()}
            self.assertEqual(reader.validate_cell(row,expected,setup,p,artifacts)[0],[])
            mutations=[lambda r:r['posts'].pop(),lambda r:r['posts'][0].update(character=120),
                       lambda r:r.update(finalSettleMs=-8000),lambda r:r.update(savedAfter=False),
                       lambda r:r['beforePost'].update(getTextSelection='wrong'),lambda r:r.update(beforeSelectionType=1),lambda r:r['beforePost'].update(INVALIDATE_VISIBLE_CURSOR='99,99,0,30'),
                       lambda r:r.update(sequence=list(reversed(r['sequence']))),lambda r:r.update(afterFile='../outside.odt')]
            for mutate in mutations:
                bad=copy.deepcopy(row);mutate(bad)
                self.assertTrue(reader.validate_cell(bad,expected,setup,p,artifacts)[0])
            odt(p/'candidate.odt','abd')
            self.assertTrue(reader.compare_saved(p/'after.odt',p/'candidate.odt','backspace'))
            odt(p/'candidate.odt','ab')
            self.assertFalse(reader.compare_saved(p/'after.odt',p/'candidate.odt','backspace'))
            odt(p/'candidate.odt','ab<text:span>d</text:span>')
            self.assertTrue(reader.compare_saved(p/'after.odt',p/'candidate.odt','type'))
            self.assertFalse(reader.compare_saved(p/'after.odt',p/'candidate.odt','backspace'))
            odt(p/'after.odt','changed')
            self.assertTrue(reader.validate_cell(row,expected,setup,p,artifacts)[0])

    def test_harness_reuses_pinned_setup_and_has_no_between_post_lok_seam(self):
        self.assertEqual(runner.sha(SDK/'tools/link_native_extend_signatures.cpp'),runner.source.PINS['tool-source-as-run.cpp'])
        text=(SDK/'tools/v23_native_s5.cpp').read_text()
        dispatch=text.split('v23s5::dispatch(seq,',1)[1].split('    });',1)[0]
        self.assertEqual(dispatch.count('s.d->pClass->'),1)
        self.assertIn('s.d->pClass->postKeyEvent(s.d,type,character,code)',dispatch)
        for forbidden in ('settle(', 'drain(', 'snap(', 'paste(', 'saveAs('):self.assertNotIn(forbidden,dispatch)

if __name__=='__main__':unittest.main()
