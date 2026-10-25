from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK/'tools'))
import resume_v23_diagnostic_packaging as resume

class Resume(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_boundary = SDK.parent/'findings/evidence/link-batch-v23/pre-link/ordered-engine-01'
        cls.old_make = subprocess.check_output(['git','show',json.loads((cls.real_boundary/'source-inputs.json').read_text())['commit']+':wasm_sdk_probe/Makefile'],cwd=SDK,text=True)
        # The successful resume fixture is the historical packaging-only fix.
        # Later successor source/Makefile changes must not authorize its reuse.
        cls.current_make = subprocess.check_output(['git','show','45e9eb15:wasm_sdk_probe/Makefile'],cwd=SDK,text=True)
        cls.log = (SDK/'build/link-v23-diagnostic-01.log').read_text()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=SDK/'build',prefix='resume-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sdk = self.root/'wasm_sdk_probe'
        self.sdk.mkdir()
        self.boundary = self.root/'boundary'; self.boundary.mkdir()
        def write(name,data):
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);return p
        def row(p):return {'path':str(p.relative_to(self.root)),'bytes':p.stat().st_size,'sha256':resume.digest(p)}
        artifacts=[]
        for name in sorted(resume.EXPECTED):
            data=b'\0asm\x01\0\0\0core-built-without-accessibility' if name.endswith('.wasm') else b'preserved'
            artifacts.append(row(write(name,data)))
        self.logfile=write('wasm_sdk_probe/build/link-v23-diagnostic-01.log',self.log.encode())
        self.plan=write('plan.txt',self.log.encode())
        self.audit={'build_artifacts':artifacts,'link_log':row(self.logfile)}
        engine=write('wasm_sdk_probe/src/probe_engine.cpp',b'engine unchanged')
        core=write('core.a',b'core unchanged')
        (self.boundary/'source-inputs.json').write_text(json.dumps({'commit':'fixture','files':[row(engine)]}))
        (self.boundary/'core-inputs.json').write_text(json.dumps({'files':[row(core)]}))
        write('wasm_sdk_probe/Makefile',self.current_make.encode())

    def validate(self):
        with mock.patch.object(resume.subprocess,'check_output',return_value=self.old_make) as run:
            result=resume.validate(self.audit,self.boundary,self.logfile,self.plan,self.root)
            self.assertEqual(run.call_args.args[0][:2],['git','show'])
            return result

    def test_valid_preserved_link(self):
        self.assertEqual(len(self.validate()),8)

    def test_each_linked_artifact_and_log_mutation_refused(self):
        for row in self.audit['build_artifacts']+[self.audit['link_log']]:
            with self.subTest(path=row['path']):
                p=self.root/row['path']; original=p.read_bytes();p.write_bytes(original+b'changed')
                with self.assertRaisesRegex(ValueError,'preserved input changed'):self.validate()
                p.write_bytes(original)

    def test_changed_engine_or_core_refused(self):
        for name in ('wasm_sdk_probe/src/probe_engine.cpp','core.a'):
            p=self.root/name;original=p.read_bytes();p.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'preserved input changed'):self.validate()
            p.write_bytes(original)

    def test_incomplete_duplicate_and_different_planned_commands_refused(self):
        lines=self.log.splitlines()
        compile_line=next(x for x in lines if ' -c ' in x and ' -o build/e2/editor-v23-diag/' in x)
        for text in (self.log.replace(compile_line,''),self.log+'\n'+compile_line,
                     self.log.replace('-sSTACK_SIZE=131072','-sSTACK_SIZE=65536')):
            self.plan.write_text(text)
            with self.assertRaises(ValueError):self.validate()

    def test_stale_plan_cannot_hide_current_flag_edit(self):
        p=self.sdk/'Makefile';p.write_text(self.current_make.replace('-sSTACK_OVERFLOW_CHECK=2','-sSTACK_OVERFLOW_CHECK=2 -sSAFE_HEAP=1'))
        with self.assertRaisesRegex(ValueError,'link macro changed'):self.validate()

    def test_stale_plan_cannot_hide_header_flag_variable_edit(self):
        p=self.sdk/'Makefile';p.write_text(self.current_make.replace('E1_CPPFLAGS := $(CPPFLAGS)', 'E1_CPPFLAGS := $(CPPFLAGS) -DUNREVIEWED'))
        with self.assertRaisesRegex(ValueError,'outside the reviewed packaging-only delta'):self.validate()

    def test_partial_profile_is_refused_without_overwrite(self):
        output=self.sdk/'dist/profiles/e2-editor-v23-diag';output.mkdir(parents=True)
        old=output/'probe.wasm';old.write_bytes(b'previous failed attempt')
        with mock.patch.object(resume,'ROOT',self.root),mock.patch.object(resume,'SDK',self.sdk), \
             mock.patch.object(resume.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'existing worker/manifest/failed bytes'):resume.package()
            run.assert_not_called()
        self.assertEqual(old.read_bytes(),b'previous failed attempt')

    def test_postpackage_input_change_quarantines_whole_profile(self):
        output=self.sdk/'dist/profiles/e2-editor-v23-diag'
        tail=self.sdk/'sdk/v23-diagnostic-worker-tail.js';tail.parent.mkdir();tail.write_bytes(b'tail')
        def change_protected(argv):
            output.mkdir(parents=True)
            for name in ('sdk-manifest.json','probe.js','probe.wasm','sdk-worker.js'):
                (output/name).write_bytes(b'new candidate')
            (self.root/self.audit['build_artifacts'][0]['path']).write_bytes(b'changed during packing')
            return 0
        with mock.patch.object(resume,'ROOT',self.root),mock.patch.object(resume,'SDK',self.sdk), \
             mock.patch.object(resume.packer,'checked_base_worker',return_value=b'base'), \
             mock.patch.object(resume.packer,'main',side_effect=change_protected), \
             mock.patch.object(resume.subprocess,'run'):
            with self.assertRaisesRegex(ValueError,'preserved input changed'):
                resume.package(self.audit['build_artifacts'])
        self.assertFalse(output.exists())
        failed=output.with_name(output.name+'.failed')
        self.assertEqual(len(list(failed.iterdir())),4)
        self.assertFalse((self.root/resume.BUILD/'sdk-worker.js').exists())

    def test_quarantine_error_keeps_primary_error_and_continues(self):
        output=self.sdk/'dist/profiles/e2-editor-v23-diag';output.mkdir(parents=True)
        tail=self.sdk/'sdk/v23-diagnostic-worker-tail.js';tail.parent.mkdir();tail.write_bytes(b'tail')
        def fail(argv):
            (output/'probe.js').write_bytes(b'partial loader')
            raise ValueError('original packing failure')
        original_rename=resume.os.rename
        def rename(source,target):
            if source==output:raise PermissionError('injected quarantine denial')
            return original_rename(source,target)
        with mock.patch.object(resume,'ROOT',self.root),mock.patch.object(resume,'SDK',self.sdk), \
             mock.patch.object(resume.packer,'checked_base_worker',return_value=b'base'), \
             mock.patch.object(resume.packer,'main',side_effect=fail), \
             mock.patch.object(resume.subprocess,'run'),mock.patch.object(resume.os,'rename',side_effect=rename):
            with self.assertRaisesRegex(ValueError,'original packing failure') as raised:resume.package()
        self.assertIn('quarantine denial',raised.exception.__notes__[0])
        self.assertTrue((self.root/resume.BUILD/'sdk-worker.failed.js').exists())

    def test_pack_failure_preserves_bytes_without_success_target(self):
        output=self.sdk/'dist/profiles/e2-editor-v23-diag';output.mkdir(parents=True)
        tail=self.sdk/'sdk/v23-diagnostic-worker-tail.js';tail.parent.mkdir();tail.write_bytes(b'tail')
        def fail(argv):
            (output/'sdk-manifest.json').write_bytes(b'partial manifest')
            raise ValueError('injected postwrite failure')
        with mock.patch.object(resume,'ROOT',self.root),mock.patch.object(resume,'SDK',self.sdk), \
             mock.patch.object(resume.packer,'checked_base_worker',return_value=b'base'), \
             mock.patch.object(resume.packer,'main',side_effect=fail), \
             mock.patch.object(resume.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'postwrite'):resume.package()
            self.assertEqual(len(run.call_args_list),2)
            for call in run.call_args_list:
                self.assertEqual(call.args[0][0],sys.executable)
                self.assertEqual(call.args[0][-1],'--check')
        worker=self.root/resume.BUILD/'sdk-worker.js'
        self.assertFalse(worker.exists());self.assertFalse((output/'sdk-manifest.json').exists())
        self.assertEqual(worker.with_name('sdk-worker.failed.js').read_bytes(),b'basetail')
        self.assertEqual((output.with_name(output.name+'.failed')/'sdk-manifest.json').read_bytes(),b'partial manifest')
        for row in self.audit['build_artifacts']+[self.audit['link_log']]:
            resume.verify_rows([row],self.root)

if __name__=='__main__':unittest.main()
