from pathlib import Path
import copy
import contextlib
import hashlib
import io
import re
import subprocess
import sys
import unittest
from unittest import mock
SDK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SDK/'tools'))
import build_e2_v23_diagnostic_profile as builder
import check_v23_diagnostic_build as check
from check_merge_key_undo_scope import compile_command,preprocess_args
from ordered_format_scope import function_bodies
from v23_diagnostic_packaging_test import PackagingFailures
R2='e2-editor-v23-diag-r2'

class R2Packaging(PackagingFailures):
    def setUp(self):
        super().setUp()
        self.candidate['profile']=R2
        self.argv[self.argv.index('--profile')+1]=R2
        worker=builder.checked_base_worker()+(SDK/'sdk/v23-diagnostic-r2-worker-tail.js').read_bytes()
        (self.work/'worker.js').write_bytes(worker);(self.work/'sdk-worker.js').write_bytes(worker)
        self.candidate['editorContract']['workerSha256']=hashlib.sha256(worker).hexdigest()
    def invoke(self, packer):
        with mock.patch.object(builder.v5,'main',side_effect=packer),contextlib.redirect_stdout(self.stdout),contextlib.redirect_stderr(self.stderr):
            return builder.main(self.argv,expected_profile=R2)
    def test_bad_reference_is_read_before_packer_and_invalidates_stale_manifest(self):
        original=builder.main
        with mock.patch.object(builder,'main',side_effect=lambda argv:original(argv,expected_profile=R2)):
            super().test_bad_reference_is_read_before_packer_and_invalidates_stale_manifest()
    def test_original_entry_rejects_successor(self):
        with self.assertRaises(SystemExit):builder.main(self.argv)
    def test_successor_rejects_original_tail(self):
        (self.work/'worker.js').write_bytes(builder.checked_base_worker()+(SDK/'sdk/v23-diagnostic-worker-tail.js').read_bytes())
        with self.assertRaisesRegex(SystemExit,'base worker plus diagnostic tail'):self.invoke(lambda argv:0)

class R2Scope(unittest.TestCase):
    def test_exact_build_rules_and_causal_mutations(self):
        make=(SDK/'Makefile').read_text()
        self.assertEqual(check.read_makefile(make),[])
        self.assertEqual(check.read_makefile(make,True),[])
        base=re.search(r'^E2_V23D_R2_BASE_WORKER := (.+)$',make,re.M)[1]
        pin=re.search(r'^E2_V23D_R2_WORKER_SHA256 := (.+)$',make,re.M)[1]
        builder.checked_base_worker(SDK/base,pin)
        original=check.GOOD_LOG
        successor=original.replace(check.BUILD_DIR,check.R2_BUILD_DIR)
        self.assertEqual(check.read_build_log(successor,True),[])
        self.assertTrue(check.read_build_log(original,True))
        self.assertTrue(check.read_build_log(successor))
        self.assertTrue(check.read_build_log(successor.replace(check.FLAG,''),True))
        changed=make.replace('$(call link_product_stack_1m,','$(call link_v23_diagnostic,',1)
        self.assertTrue(check.read_makefile(changed,True))
        changed=make.replace('$(E2_V23D_R2_BUILD)/%.o:', '$(WRONG_BUILD)/%.o:')
        self.assertTrue(check.read_makefile(changed,True))
        self.assertTrue(builder.contract_problems({'profile':R2}, {}, 'invented-profile'))
    def test_actual_diagnostic_dispatch_and_public_guard(self):
        r=subprocess.run(preprocess_args(compile_command('build/e2/editor-v23-diag-r2/probe_engine.o'),[]),cwd=SDK,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        source=r.stdout[r.stdout.index('enum class CommandType'):]
        def problems(text):
            b=function_bodies(text)
            private=''.join(b.get('oxsdk_v23_diagnostic',[]))
            dispatch=''.join(b.get('dispatch',[]))
            handler=''.join(b.get('handleOrderedDiagnostic',[]))
            route=''.join(b.get('routeFormatBarrier',[]))
            return (not all(x in private for x in ('kind > 9','kind == 9 ? CommandType::DiagnosticHtml','submit(std::move(command))'))
                    or 'case CommandType::DiagnosticHtml:' not in dispatch
                    or 'startOrderedHtmlRead(command)' not in handler
                    or handler.find('requireDocument')>handler.find('startOrderedHtmlRead')
                    or 'selection.type != LOK_SELTYPE_TEXT' not in route)
        self.assertFalse(problems(source))
        for before,after in [('kind > 9','kind > 10'),('case CommandType::DiagnosticHtml:',''),
                             ('startOrderedHtmlRead(command)','handleGetSelection(command)'),
                             ('selection.type != LOK_SELTYPE_TEXT','false')]:
            self.assertIn(before,source)
            self.assertTrue(problems(source.replace(before,after)))
        plain=subprocess.run(preprocess_args([arg for arg in compile_command('build/e2/editor-v23-diag-r2/probe_engine.o') if arg!='-DOXSDK_E2_V23_DIAGNOSTIC'],[]),cwd=SDK,capture_output=True,text=True)
        self.assertEqual(plain.returncode,0,plain.stderr)
        self.assertNotIn('startOrderedHtmlRead',plain.stdout)
        self.assertNotIn('oxsdk_v23_diagnostic',plain.stdout)
if __name__=='__main__':unittest.main()
