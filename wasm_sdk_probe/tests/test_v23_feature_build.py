"""Read actual make recipes only; no compile/link target is executed."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
SDK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SDK/'tools'))
import check_v23_feature_contract as checker

class Build(unittest.TestCase):
    def test_actual_target_and_causal_log_mutants(self):
        result=subprocess.run(['make','-n','ALLOW_FROZEN_RELINK=1','dist/profiles/e2-editor-v23/sdk-manifest.json'],cwd=SDK,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        log=result.stdout
        self.assertEqual(checker.feature_log_problems(log),[])
        for before,after in [('-DOXSDK_E2_V23_FEATURE_ABI6',''),
                             ('-DOXSDK_E2_V23_FEATURE_ABI6','-DOXSDK_E2_V23_FEATURE_ABI6 -DOXSDK_E2_V23_DIAGNOSTIC'),
                             ('-sSTACK_SIZE=131072','-sSTACK_OVERFLOW_CHECK=2 -sSTACK_SIZE=131072'),
                             ('-DOXSDK_MAINLOOP_ENGINE',''),
                             ('-c src/editor_api.cpp','-c src/probe_engine.cpp'),
                             ('-DOXSDK_E2_V23_FEATURE_ABI6','-DOXSDK_E2_V23_FEATURE_ABI6 -DOXSDK_FINDING_016_SCHEDULER_PROBE')]:
            with self.subTest(mutation=after):
                self.assertIn(before,log)
                self.assertTrue(checker.feature_log_problems(log.replace(before,after)))
        self.assertTrue(checker.feature_log_problems(''))
        self.assertIn('cp sdk/v23-feature-worker.js build/e2/editor-v23/sdk-worker.js',log)
        self.assertIn('cp build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/exports.txt build/e2/editor-v23/exports.txt',log)
        self.assertIn('--profile e2-editor-v23 --inline-range-gestures all',log)
        self.assertIn('--page-rectangles --paste-markdown',log.replace('\\\n',' '))
        preflight=log.index('python3 tools/check_v23_feature_contract.py --check-worker-base')
        first_compile=log.index(' -c src/')
        self.assertLess(preflight,first_compile)
        # Resolve the actual recipe arguments: source existence alone did not catch the old wrong-worker pin.
        logical=log.replace('\\\n',' ')
        base=re.search(r'--base-worker (\S+) --base-worker-sha256 (\S+)',logical)
        self.assertIsNotNone(base)
        checker.check_base(SDK/base[1],base[2])
        with self.assertRaises(ValueError):checker.check_base(SDK/'sdk/sdk-worker.js',base[2])

    def test_legacy_preprocessed_api_tokens_equal_protocol_boundary(self):
        # Header/comments/source differ, but every old selector sees identical C API tokens.
        variants=[[],['OXSDK_E2_V21_LINK_BATCH'],
                  ['OXSDK_E2_V21_LINK_BATCH','OXSDK_E2_V23_LINK_BATCH','OXSDK_E2_V23_DIAGNOSTIC']]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'emscripten').mkdir();(p/'emscripten/emscripten.h').write_text('#define EMSCRIPTEN_KEEPALIVE\n')
            old=p/'old';old.mkdir()
            for name in ('editor_api.cpp','editor_api.h'):
                content=subprocess.check_output(['git','show','561db7f6:wasm_sdk_probe/src/'+name],cwd=SDK)
                (old/name).write_bytes(content)
            for defs in variants:
                command=['g++','-std=c++17','-E','-P','-I'+tmp,'-I'+str(SDK/'src'),'-DOXSDK_E2_FORMAT_BARRIER']+['-D'+d for d in defs]
                before=subprocess.check_output(command+[str(old/'editor_api.cpp')])
                after=subprocess.check_output(command+[str(SDK/'src/editor_api.cpp')])
                self.assertEqual(before,after,defs)

if __name__=='__main__':unittest.main()
