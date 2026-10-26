"""Full-contract deltas and transactional wrapper faults; no product build."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
SDK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SDK/'tools'))
import build_e2_v23_feature_profile as builder
import check_v23_feature_contract as checker

def uleb(value):
    out=bytearray()
    while True:
        byte=value&127;value>>=7
        out.append(byte|(128 if value else 0))
        if not value:return bytes(out)

def wasm_string(value):
    raw=value.encode();return uleb(len(raw))+raw

def synthetic_public_pair(names=None):
    if names is None:
        names=[n for n in (checker.ARCHIVE/'exports.txt').read_text().splitlines() if n.startswith(('_oxsdk_','_probe_'))]
    rows=[(n,'f'+str(i)) for i,n in enumerate(names)]
    loader=';'.join(f'Module["{n}"]={n}=wasmExports["{symbol}"]' for n,symbol in rows)
    exports=uleb(len(rows))+b''.join(wasm_string(symbol)+b'\0\0' for _,symbol in rows)
    def section(kind,data):return bytes([kind])+uleb(len(data))+data
    wasm=(b'\0asm\1\0\0\0'+section(0,wasm_string('core-built-without-accessibility'))+
          section(1,b'\1\x60\0\0')+section(3,b'\1\0')+section(7,exports)+section(10,b'\1\2\0\x0b'))
    return loader.encode(),wasm

class Profile(unittest.TestCase):
    def setUp(self):
        self.reference=json.loads((checker.ARCHIVE/'sdk-manifest.json').read_text())
        self.candidate=copy.deepcopy(self.reference)
        self.candidate['profile']=checker.PROFILE
        self.candidate['sdkVersion']=self.reference['sdkVersion'].removesuffix('+e2-editor-v22')+'+'+checker.PROFILE
        self.candidate['editorContract']=checker.expected_contract(self.reference)

    def test_every_action_field_is_bound(self):
        self.assertEqual(checker.contract_problems(self.candidate,self.reference),[])
        actions=self.candidate['editorContract']['actions']
        self.assertEqual(len(actions),23)
        for name,action in actions.items():
            for field in action:
                with self.subTest(action=name,field=field):
                    bad=copy.deepcopy(self.candidate)
                    del bad['editorContract']['actions'][name][field]
                    self.assertTrue(checker.contract_problems(bad,self.reference))
        for change in ('new-action','capability','abi','profile','withheld'):
            bad=copy.deepcopy(self.candidate)
            if change=='new-action':bad['editorContract']['actions']['invented']={'id':24,'gestures':[]}
            elif change=='capability':bad['capabilities'].append('invented')
            elif change=='abi':bad['editorContract']['abiVersion']=5
            elif change=='profile':bad['profile']='e2-editor-v23-diag-r2'
            else:bad['editorContract']['actions']['select-all']['gestures']=['collapsed']
            self.assertTrue(checker.contract_problems(bad,self.reference))

    def test_every_top_level_public_field_is_bound(self):
        for key in self.candidate:
            if key=='editorContract':continue
            for mutation in ('delete','replace'):
                with self.subTest(key=key,mutation=mutation):
                    bad=copy.deepcopy(self.candidate)
                    if mutation=='delete':del bad[key]
                    else:bad[key]={'unexpected':'value'}
                    self.assertTrue(checker.contract_problems(bad,self.reference))
        for key in ('diagnosticOnly','inventedPublicGrant'):
            bad=copy.deepcopy(self.candidate);bad[key]=True
            self.assertTrue(checker.contract_problems(bad,self.reference))
        bad=copy.deepcopy(self.candidate);bad['expectedCapabilityBits']^=1
        self.assertTrue(checker.contract_problems(bad,self.reference))

    def test_actual_binary_bindings_and_frozen_controls(self):
        self.assertEqual(checker.actual_export_problems(checker.ARCHIVE/'probe.js',checker.ARCHIVE/'probe.wasm'),[])
        # An actual retained diagnostic binary has a public entrance absent from v22.
        r2=SDK/'dist/profiles/e2-editor-v23-diag-r2'
        self.assertTrue(checker.actual_export_problems(r2/'probe.js',r2/'probe.wasm'))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);loader,wasm=synthetic_public_pair()
            (p/'probe.js').write_bytes(loader);(p/'probe.wasm').write_bytes(wasm)
            self.assertEqual(checker.actual_export_problems(p/'probe.js',p/'probe.wasm'),[])
            names=[n for n in (checker.ARCHIVE/'exports.txt').read_text().splitlines() if n.startswith('_oxsdk_')]
            for variant in (names[:-1],names+['_oxsdk_v23_diagnostic'],names+['_oxsdk_invented']):
                l,w=synthetic_public_pair(variant);(p/'probe.js').write_bytes(l);(p/'probe.wasm').write_bytes(w)
                self.assertTrue(checker.actual_export_problems(p/'probe.js',p/'probe.wasm'))
            (p/'probe.js').write_bytes(loader)
            for bad in (b'\0asm\1\0\0\0',wasm[:-1],wasm.replace(b'f0',b'z0',1)):
                (p/'probe.wasm').write_bytes(bad)
                self.assertTrue(checker.actual_export_problems(p/'probe.js',p/'probe.wasm'))

    def test_exact_archived_base_and_inputs(self):
        checker.check_base()
        with self.assertRaises(ValueError):checker.check_base(SDK/'sdk/sdk-worker.js')
        with self.assertRaises(ValueError):checker.check_base(pin='0'*64)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);w=p/'worker';e=p/'exports';a=p/'wasm'
            w.write_bytes(checker.WORKER.read_bytes());e.write_bytes((checker.ARCHIVE/'exports.txt').read_bytes())
            a.write_bytes(b'\0asm\1\0\0\0core-built-without-accessibility')
            self.assertEqual(checker.input_problems(w,e,a),[])
            w.write_bytes((SDK/'sdk/sdk-worker.js').read_bytes())
            self.assertTrue(checker.input_problems(w,e,a))
            w.write_bytes(checker.WORKER.read_bytes());e.write_text(e.read_text()+'_oxsdk_v23_diagnostic\n')
            self.assertTrue(checker.input_problems(w,e,a))
            e.write_bytes((checker.ARCHIVE/'exports.txt').read_bytes());a.write_bytes(b'not wasm')
            self.assertTrue(checker.input_problems(w,e,a))

    def test_actual_inherited_builder_chain_on_standin_bytes(self):
        # No compiler/linker or frozen output: real v5/v4/c/b packing in a temporary directory.
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);output=p/'profile'
            loader,wasm=synthetic_public_pair()
            (p/'probe.js').write_bytes(loader)
            (p/'probe.wasm').write_bytes(wasm)
            (p/'sdk-worker.js').write_bytes(checker.WORKER.read_bytes())
            (p/'exports.txt').write_bytes((checker.ARCHIVE/'exports.txt').read_bytes())
            args=['builder','--source-manifest',str(SDK/'sdk/v18-writer-review-manifest.json'),
                  '--profile',checker.PROFILE,'--loader',str(p/'probe.js'),'--wasm',str(p/'probe.wasm'),
                  '--worker',str(p/'sdk-worker.js'),'--exports',str(p/'exports.txt'),'--output',str(output),
                  '--inline-range-gestures','all','--page-rectangles','--paste-markdown']
            originals=(builder.v5.ABI_VERSION,builder.v5.action_map,builder.v5.v4.ABI_VERSION,builder.v5.v4.action_map)
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                self.assertEqual(builder.main(args),0)
            manifest=json.loads((output/'sdk-manifest.json').read_text())
            self.assertEqual(checker.contract_problems(manifest,self.reference),[])
            self.assertEqual(checker.binding_problems(manifest,output),[])
            self.assertEqual(json.loads(printed.getvalue())['withheld'],['select-all'])
            self.assertEqual(originals,(builder.v5.ABI_VERSION,builder.v5.action_map,builder.v5.v4.ABI_VERSION,builder.v5.v4.action_map))

    def test_transactional_wrapper_faults(self):
        original=(builder.v5.ABI_VERSION,builder.v5.action_map)
        for fault in ('none','exception','nonzero','manifest-parse','contract','binding','summary'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as tmp:
                output=Path(tmp)/'profile'
                def underlying(argv):
                    self.assertEqual(builder.v5.ABI_VERSION,6)
                    self.assertEqual(builder.v5.action_map()['move-line-end']['gestures'],['collapsed','range-single','range-cross'])
                    output.mkdir();candidate=copy.deepcopy(self.candidate)
                    for key,name in checker.BINDINGS.items():
                        (output/name).write_bytes(name.encode());candidate['editorContract'][key]=checker.sha(output/name)
                    if fault=='contract':candidate['editorContract']['abiVersion']=5
                    if fault=='binding':candidate['editorContract']['workerSha256']='0'*64
                    (output/'sdk-manifest.json').write_text('invalid' if fault=='manifest-parse' else json.dumps(candidate))
                    print('CAPTURED FAILURE' if fault in ('summary','exception','nonzero') else '{}')
                    if fault=='exception':raise RuntimeError('postwrite failure')
                    return 7 if fault=='nonzero' else 0
                args=['builder','--profile',checker.PROFILE,'--loader','unused','--worker','unused','--wasm','unused','--exports','unused','--output',str(output)]
                err=io.StringIO()
                with patch.object(checker,'input_problems',return_value=[]),patch.object(checker,'actual_export_problems',return_value=[]),patch.object(builder.v5,'main',side_effect=underlying),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(err):
                    if fault in ('exception','manifest-parse','contract','binding','summary'):
                        with self.assertRaises((RuntimeError,ValueError,SystemExit)):builder.main(args)
                    else:self.assertEqual(builder.main(args),7 if fault=='nonzero' else 0)
                self.assertEqual((builder.v5.ABI_VERSION,builder.v5.action_map),original)
                self.assertEqual((output/'sdk-manifest.json').exists(),fault=='none')
                failed=list(output.glob('sdk-manifest.failed-*.json'))
                self.assertEqual(len(failed),int(fault!='none'))
                if fault in ('summary','exception','nonzero'):self.assertIn('CAPTURED FAILURE',err.getvalue())
                # Every partial/successful output is preserved on a repeated invocation.
                before={p.name:p.read_bytes() for p in output.iterdir()}
                with self.assertRaises(SystemExit):builder.main(args)
                self.assertEqual(before,{p.name:p.read_bytes() for p in output.iterdir()})

if __name__=='__main__':unittest.main()
