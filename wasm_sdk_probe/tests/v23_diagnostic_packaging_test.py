#!/usr/bin/env python3
"""Contract controls use the complete actual v22 contract as their population."""
import copy
import json
import hashlib
import contextlib
import io
import tempfile
from unittest import mock
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from build_e2_v23_diagnostic_profile import contract_problems, PROFILE
import build_e2_v23_diagnostic_profile as builder


class DiagnosticContract(unittest.TestCase):
    def setUp(self):
        self.reference = json.loads((ROOT / 'dist/profiles/e2-editor-v22/sdk-manifest.json').read_text())
        self.candidate = copy.deepcopy(self.reference)
        self.candidate['profile'] = PROFILE

    def test_frozen_worker_identity_rejects_current_sdk_and_bad_pin(self):
        self.assertEqual(hashlib.sha256(builder.checked_base_worker()).hexdigest(), builder.BASE_WORKER_SHA256)
        with self.assertRaises(ValueError):
            builder.checked_base_worker(ROOT / 'sdk/sdk-worker.js')
        with self.assertRaises(ValueError):
            builder.checked_base_worker(expected='0' * 64)
        with mock.patch.object(Path, 'read_bytes', return_value=b'corrupt frozen archive'):
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                builder.checked_base_worker()

    def test_makefile_base_resolves_to_checked_bytes(self):
        import re
        text = (ROOT / 'Makefile').read_text()
        base = re.search(r'^E2_V23D_BASE_WORKER := (.+)$', text, re.M)[1]
        pin = re.search(r'^E2_V23D_WORKER_SHA256 := (.+)$', text, re.M)[1]
        builder.checked_base_worker(ROOT / base, pin)
        self.assertIn('| $(E2_V23D_BUILD) v23-diagnostic-worker-preflight', text)
        self.assertIn('--base-worker $(E2_V23D_BASE_WORKER)', text)

    def test_inherited_contract(self):
        self.assertEqual([], contract_problems(self.candidate, self.reference))

    def test_v22_cannot_masquerade_as_diagnostic(self):
        self.assertTrue(contract_problems(self.reference, self.reference))

    def test_abi6_is_feature_only(self):
        self.candidate['editorContract']['abiVersion'] = 6
        self.assertTrue(contract_problems(self.candidate, self.reference))

    def test_every_action_is_inherited_verbatim(self):
        for name in self.reference['editorContract']['actions']:
            with self.subTest(action=name):
                changed = copy.deepcopy(self.candidate)
                del changed['editorContract']['actions'][name]
                self.assertTrue(contract_problems(changed, self.reference))

    def test_new_action_is_refused(self):
        self.candidate['editorContract']['actions']['invented-shift'] = {'id': 999, 'gestures': []}
        self.assertTrue(contract_problems(self.candidate, self.reference))

    def test_diagnostic_capability_is_not_public(self):
        self.candidate['capabilities'].append('v23-diagnostic')
        self.assertTrue(contract_problems(self.candidate, self.reference))

    def test_new_artifact_bindings_do_not_change_public_contract(self):
        for key in ('loaderSha256', 'wasmSha256', 'workerSha256'):
            self.candidate['editorContract'][key] = '1' * 64
        self.assertEqual([], contract_problems(self.candidate, self.reference))

    def test_reference_identity(self):
        self.reference['profile'] = PROFILE
        self.assertTrue(contract_problems(self.candidate, self.reference))


class PackagingFailures(unittest.TestCase):
    """Execute the real wrapper; only the underlying packer/fault site is injected."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='v23-pack-test-', dir=ROOT / 'build')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.manifest = self.work / 'sdk-manifest.json'
        self.reference = ROOT / 'dist/profiles/e2-editor-v22/sdk-manifest.json'
        self.candidate = json.loads(self.reference.read_text())
        self.candidate['profile'] = PROFILE
        (self.work / 'probe.wasm').write_bytes(b'\x00asm\x01\x00\x00\x00core-built-without-accessibility')
        (self.work / 'exports.txt').write_text(builder.PRIVATE_EXPORT + '\n')
        (self.work / 'worker.js').write_bytes(builder.checked_base_worker()
            + (ROOT / 'sdk/v23-diagnostic-worker-tail.js').read_bytes())
        (self.work / 'probe.js').write_text('// synthetic loader for packaging-only tests\n')
        (self.work / 'sdk-worker.js').write_bytes((self.work / 'worker.js').read_bytes())
        for key, filename in builder.ARTIFACT_BINDINGS.items():
            self.candidate['editorContract'][key] = hashlib.sha256((self.work / filename).read_bytes()).hexdigest()
        self.argv = ['builder', '--profile', PROFILE, '--wasm', str(self.work / 'probe.wasm'),
                     '--exports', str(self.work / 'exports.txt'), '--worker', str(self.work / 'worker.js'),
                     '--output', str(self.work)]
        self.stdout, self.stderr = io.StringIO(), io.StringIO()

    def invoke(self, packer):
        with mock.patch.object(builder.v5, 'main', side_effect=packer), \
                contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr):
            return builder.main(self.argv)

    def write_candidate(self, text=None):
        self.manifest.write_text(json.dumps(self.candidate) if text is None else text)

    def test_success_keeps_validated_manifest(self):
        def packer(argv):
            self.write_candidate()
            print('{}')
            return 0
        self.assertEqual(self.invoke(packer), 0)
        self.assertTrue(self.manifest.exists())
        self.assertEqual(self.stderr.getvalue(), '')
        self.assertTrue(json.loads(self.stdout.getvalue())['diagnosticOnly'])

    def test_each_missing_stale_or_corrupted_artifact_binding_is_rejected(self):
        for key, filename in builder.ARTIFACT_BINDINGS.items():
            for fault in ('missing', 'stale', 'bytes'):
                with self.subTest(binding=key, fault=fault):
                    candidate = copy.deepcopy(self.candidate)
                    original = (self.work / filename).read_bytes()
                    if fault == 'missing':
                        del candidate['editorContract'][key]
                    elif fault == 'stale':
                        candidate['editorContract'][key] = '0' * 64
                    else:
                        (self.work / filename).write_bytes(original + b'changed')
                    try:
                        self.assertTrue(builder.binding_problems(candidate, self.work))
                    finally:
                        (self.work / filename).write_bytes(original)

    def test_postwrite_missing_artifact_removes_manifest_and_keeps_output(self):
        def packer(argv):
            self.write_candidate()
            (self.work / 'probe.js').unlink()
            print('{}')
            return 0
        with self.assertRaises(FileNotFoundError):
            self.invoke(packer)
        self.assertFalse(self.manifest.exists())
        self.assertEqual(self.stderr.getvalue(), '{}\n')

    def test_postwrite_candidate_parse_failure_removes_manifest_and_keeps_output(self):
        def packer(argv):
            self.write_candidate('{broken')
            print('{}')
            return 0
        with self.assertRaises(json.JSONDecodeError):
            self.invoke(packer)
        self.assertFalse(self.manifest.exists())
        self.assertEqual(self.stderr.getvalue(), '{}\n')

    def test_postwrite_reference_comparison_failure_removes_manifest(self):
        def packer(argv):
            self.candidate['editorContract']['abiVersion'] = 6
            self.write_candidate()
            print('{}')
            return 0
        with self.assertRaises(SystemExit):
            self.invoke(packer)
        self.assertFalse(self.manifest.exists())
        self.assertEqual(self.stderr.getvalue(), '{}\n')

    def test_postwrite_validator_exception_removes_manifest(self):
        def packer(argv):
            self.write_candidate()
            print('{}')
            return 0
        with mock.patch.object(builder, 'contract_problems', side_effect=OSError('reference validation failed')):
            with self.assertRaisesRegex(OSError, 'reference validation failed'):
                self.invoke(packer)
        self.assertFalse(self.manifest.exists())
        self.assertEqual(self.stderr.getvalue(), '{}\n')

    def test_postwrite_summary_failure_removes_manifest_and_preserves_exact_output(self):
        def packer(argv):
            self.write_candidate()
            print('packer diagnosis\nnot JSON')
            return 0
        with self.assertRaises(json.JSONDecodeError):
            self.invoke(packer)
        self.assertFalse(self.manifest.exists())
        self.assertEqual(self.stderr.getvalue(), 'packer diagnosis\nnot JSON\n')

    def test_v5_nonzero_and_exceptions_remove_manifest_and_keep_output(self):
        for outcome in (7, RuntimeError('packer failed'), SystemExit(9)):
            with self.subTest(outcome=repr(outcome)):
                self.stderr = io.StringIO()
                def packer(argv):
                    self.write_candidate()
                    print('underlying packer diagnosis')
                    if isinstance(outcome, BaseException):
                        raise outcome
                    return outcome
                if isinstance(outcome, BaseException):
                    with self.assertRaises(type(outcome)):
                        self.invoke(packer)
                else:
                    self.assertEqual(self.invoke(packer), outcome)
                self.assertFalse(self.manifest.exists())
                self.assertEqual(self.stderr.getvalue(), 'underlying packer diagnosis\n')

    def test_bad_reference_is_read_before_packer_and_invalidates_stale_manifest(self):
        original_read = Path.read_text
        for fault in (FileNotFoundError('reference missing'), '{broken'):
            with self.subTest(fault=repr(fault)):
                self.write_candidate()
                def read(path, *args, **kwargs):
                    if path == self.reference:
                        if isinstance(fault, BaseException):
                            raise fault
                        return fault
                    return original_read(path, *args, **kwargs)
                with mock.patch.object(Path, 'read_text', read), \
                        mock.patch.object(builder.v5, 'main') as packer:
                    with self.assertRaises((FileNotFoundError, json.JSONDecodeError)):
                        builder.main(self.argv)
                    packer.assert_not_called()
                self.assertFalse(self.manifest.exists())


if __name__ == '__main__':
    unittest.main()
