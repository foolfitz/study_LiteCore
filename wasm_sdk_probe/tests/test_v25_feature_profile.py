#!/usr/bin/env python3
"""SPEC-M3-link-batch-v25 4.5 / 6.2: the successor's identity delta, before any link.

The contract checker accepts exactly v24 under the v25 name (every leaf, typedInsert
included, equal; ABI 6; no new export) and names every other change; the builder
refuses another identity and a worker that is not the v25 worker; the build-log
reader requires the v25 define on all four units.  The real v25 manifest is judged
after the link; these are its reds in advance.  (The shape of test_v24_feature_profile.py.)
"""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import build_e2_v25_feature_profile as builder  # noqa: E402
import check_v25_feature_contract as contract  # noqa: E402

REFERENCE = json.loads((contract.ARCHIVE / 'sdk-manifest.json').read_text())


def candidate():
    manifest = copy.deepcopy(REFERENCE)
    manifest['profile'] = contract.PROFILE
    manifest['sdkVersion'] = REFERENCE['sdkVersion'].replace('+e2-editor-v24', '+e2-editor-v25')
    return manifest


class ContractDelta(unittest.TestCase):
    def test_exact_successor_holds(self):
        self.assertEqual(REFERENCE['profile'], 'e2-editor-v24')
        self.assertEqual(REFERENCE['editorContract']['abiVersion'], 6)
        self.assertEqual(REFERENCE['editorContract']['typedInsert'], 'document-sdk-insert-typed-text')
        self.assertEqual(contract.contract_problems(candidate(), REFERENCE), [])

    def test_every_other_change_is_named(self):
        def changed(edit):
            manifest = candidate()
            edit(manifest)
            return contract.contract_problems(manifest, REFERENCE)
        cases = {
            'abi 7': lambda m: m['editorContract'].__setitem__('abiVersion', 7),
            'typedInsert absent': lambda m: m['editorContract'].pop('typedInsert'),
            'typedInsert value': lambda m: m['editorContract'].__setitem__('typedInsert', 'document-sdk-insert-text'),
            'a new leaf': lambda m: m['editorContract'].__setitem__('formatProof', 'v25'),
            'a gesture': lambda m: m['editorContract']['actions']['move-line-up'].__setitem__('gestures', ['collapsed']),
            'pasteMarkdown dropped': lambda m: m['editorContract'].pop('pasteMarkdown'),
            'profile name': lambda m: m.__setitem__('profile', 'e2-editor-v24'),
            'a top-level leaf': lambda m: m.__setitem__('abiVersion', 65538),
        }
        for label, edit in cases.items():
            with self.subTest(label):
                self.assertNotEqual(changed(edit), [])

    def test_export_list_is_v24s(self):
        names = contract.expected_exports()
        self.assertEqual(names, (contract.ARCHIVE / 'exports.txt').read_text().splitlines())
        self.assertEqual(names[-1], '_oxsdk_document_insert_typed_text')
        self.assertEqual(len(names), 37)


class BuilderIsTold(unittest.TestCase):
    def test_v24_worker_is_refused(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            argv = ['build_e2_v25_feature_profile.py', '--profile', 'e2-editor-v25',
                    '--loader', str(contract.ARCHIVE / 'probe.js'), '--wasm', str(contract.ARCHIVE / 'probe.wasm'),
                    '--worker', str(ROOT / 'sdk/v24-feature-worker.js'),
                    '--exports', str(contract.ARCHIVE / 'exports.txt'), '--output', str(scratch / 'out')]
            with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(io.StringIO()):
                builder.main(argv)
            self.assertIn('worker differs from sdk/v25-feature-worker.js', str(raised.exception))
            self.assertFalse((scratch / 'out').exists())

    def test_wrong_identity_is_refused(self):
        with self.assertRaises(SystemExit) as raised:
            builder.main(['b', '--profile', 'e2-editor-v24', '--loader', 'x', '--wasm', 'x', '--worker', 'x',
                          '--exports', 'x', '--output', 'x'])
        self.assertIn('requires exactly e2-editor-v25', str(raised.exception))


class FeatureLog(unittest.TestCase):
    def test_v25_log_needs_the_define_and_four_units(self):
        line = ('em++ -DOXSDK_E2_V23_LINK_BATCH -DOXSDK_E2_V21_LINK_BATCH -DOXSDK_E2_V20_LINK_BATCH '
                '-DOXSDK_MAINLOOP_ENGINE -DOXSDK_E2_V23_FEATURE_ABI6 -DOXSDK_E2_V24_TYPED_INSERT '
                '-DOXSDK_E2_V25_FORMAT_PROOF -c src/{0}.cpp -o build/e2/editor-v25/{0}.o')
        units = ['probe_engine', 'sdk_api', 'editor_api', 'unoembind_stub']
        link = 'em++ a.o -sDEFAULT_PTHREAD_STACK_SIZE=1048576 -o build/e2/editor-v25/probe.js'
        good = '\n'.join(line.format(u) for u in units) + '\n' + link + '\n'
        missing = good.replace(' -DOXSDK_E2_V25_FORMAT_PROOF', '', 1)
        three = '\n'.join(line.format(u) for u in units[:3]) + '\n' + link + '\n'
        self.assertFalse(any('lacks' in p or 'exactly once' in p for p in contract.feature_log_problems(good)))
        self.assertIn('v25 object lacks -DOXSDK_E2_V25_FORMAT_PROOF', contract.feature_log_problems(missing))
        self.assertIn('v25 record must compile each of the four source units exactly once',
                      contract.feature_log_problems(three))


if __name__ == '__main__':
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
