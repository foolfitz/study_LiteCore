#!/usr/bin/env python3
"""SPEC-M3-v27-finding-176 4.4 / 5: the successor's identity delta, before any link.

The contract checker accepts exactly v26 under the v27 name (every leaf -- select-all's
three gestures and limits, typedInsert -- equal; ABI 6; no new export) and names every
other change; the builder refuses another identity and a worker that is not the v27
worker; the build-log reader requires the v27 define on all four units.  The real v27
manifest is judged after the link; these are its reds in advance.  (The shape of
test_v25_feature_profile.py.)  One addition: the builder run end to end on the v26
archive's own wasm and loader with the v27 worker must give v26's manifest with exactly
profile, sdkVersion and workerSha256 changed -- the select-all leaf comes from the
archive, and v25's construction path is what reproduces every other leaf.
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
import build_e2_v27_first_block_profile as builder  # noqa: E402
import check_v27_first_block_contract as contract  # noqa: E402

REFERENCE = json.loads((contract.ARCHIVE / 'sdk-manifest.json').read_text())


def candidate():
    manifest = copy.deepcopy(REFERENCE)
    manifest['profile'] = contract.PROFILE
    manifest['sdkVersion'] = REFERENCE['sdkVersion'].replace('+e2-editor-v26', '+e2-editor-v27')
    return manifest


def changes(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        return [c for k in sorted(set(a) | set(b)) for c in changes(a.get(k), b.get(k), f'{path}/{k}')]
    return [] if a == b else [path]


class ContractDelta(unittest.TestCase):
    def test_exact_successor_holds(self):
        self.assertEqual(REFERENCE['profile'], 'e2-editor-v26')
        self.assertEqual(REFERENCE['editorContract']['abiVersion'], 6)
        self.assertEqual(REFERENCE['editorContract']['typedInsert'], 'document-sdk-insert-typed-text')
        self.assertEqual(REFERENCE['editorContract']['actions']['select-all']['gestures'],
                         ['collapsed', 'range-single', 'range-cross'])
        self.assertEqual(contract.contract_problems(candidate(), REFERENCE), [])

    def test_every_other_change_is_named(self):
        def changed(edit):
            manifest = candidate()
            edit(manifest)
            return contract.contract_problems(manifest, REFERENCE)
        cases = {
            'abi 7': lambda m: m['editorContract'].__setitem__('abiVersion', 7),
            'typedInsert absent': lambda m: m['editorContract'].pop('typedInsert'),
            'a new leaf': lambda m: m['editorContract'].__setitem__('firstBlock', 'v27'),
            'formatBarrier leaf bumped': lambda m: m['editorContract'].__setitem__('formatBarrier', 'verified-format-readback-v3'),
            'select-all withheld again': lambda m: m['editorContract']['actions']['select-all'].__setitem__('gestures', []),
            'a gesture': lambda m: m['editorContract']['actions']['move-line-up'].__setitem__('gestures', ['collapsed']),
            'profile name': lambda m: m.__setitem__('profile', 'e2-editor-v26'),
            'a top-level leaf': lambda m: m.__setitem__('abiVersion', 65538),
        }
        for label, edit in cases.items():
            with self.subTest(label):
                self.assertNotEqual(changed(edit), [])

    def test_export_list_is_v26s(self):
        names = contract.expected_exports()
        self.assertEqual(names, (contract.ARCHIVE / 'exports.txt').read_text().splitlines())
        self.assertEqual(names[-1], '_oxsdk_document_insert_typed_text')
        self.assertEqual(len(names), 37)


class BuilderIsTold(unittest.TestCase):
    def argv(self, worker, output):
        return ['build_e2_v27_first_block_profile.py', '--source-manifest', str(ROOT / 'sdk/v18-writer-review-manifest.json'),
                '--profile', 'e2-editor-v27',
                '--loader', str(contract.ARCHIVE / 'probe.js'), '--wasm', str(contract.ARCHIVE / 'probe.wasm'),
                '--worker', str(worker), '--exports', str(contract.ARCHIVE / 'exports.txt'),
                '--inline-range-gestures', 'all', '--page-rectangles', '--paste-markdown', '--output', str(output)]

    def test_v26_worker_is_refused(self):
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch) / 'out'
            with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(io.StringIO()):
                builder.main(self.argv(ROOT / 'sdk/v26-select-all-worker.js', out))
            self.assertIn('worker differs from sdk/v27-first-block-worker.js', str(raised.exception))
            self.assertFalse(out.exists())

    def test_wrong_identity_is_refused(self):
        with self.assertRaises(SystemExit) as raised:
            builder.main(['b', '--profile', 'e2-editor-v26', '--loader', 'x', '--wasm', 'x', '--worker', 'x',
                          '--exports', 'x', '--output', 'x'])
        self.assertIn('requires exactly e2-editor-v27', str(raised.exception))

    def test_dry_run_on_v26_binaries_is_v26_plus_three_values(self):
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch) / 'out'
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                self.assertEqual(builder.main(self.argv(contract.WORKER, out)), 0)
            built = json.loads((out / 'sdk-manifest.json').read_text())
            self.assertEqual(changes(REFERENCE, built), ['/editorContract/workerSha256', '/profile', '/sdkVersion'])
            self.assertEqual(built['editorContract']['workerSha256'], contract.sha(contract.WORKER))
            self.assertEqual(json.loads(printed.getvalue())['withheld'], [])


class FeatureLog(unittest.TestCase):
    def test_v27_log_needs_the_define_and_four_units(self):
        line = ('em++ -DOXSDK_E2_V23_LINK_BATCH -DOXSDK_E2_V21_LINK_BATCH -DOXSDK_E2_V20_LINK_BATCH '
                '-DOXSDK_MAINLOOP_ENGINE -DOXSDK_E2_V23_FEATURE_ABI6 -DOXSDK_E2_V24_TYPED_INSERT '
                '-DOXSDK_E2_V25_FORMAT_PROOF -DOXSDK_E2_V27_FIRST_BLOCK -c src/{0}.cpp -o build/e2/editor-v27/{0}.o')
        units = ['probe_engine', 'sdk_api', 'editor_api', 'unoembind_stub']
        link = 'em++ a.o -sDEFAULT_PTHREAD_STACK_SIZE=1048576 -o build/e2/editor-v27/probe.js'
        good = '\n'.join(line.format(u) for u in units) + '\n' + link + '\n'
        missing = good.replace(' -DOXSDK_E2_V27_FIRST_BLOCK', '', 1)
        three = '\n'.join(line.format(u) for u in units[:3]) + '\n' + link + '\n'
        self.assertFalse(any('lacks' in p or 'exactly once' in p for p in contract.feature_log_problems(good)))
        self.assertIn('v27 object lacks -DOXSDK_E2_V27_FIRST_BLOCK', contract.feature_log_problems(missing))
        self.assertIn('v27 record must compile each of the four source units exactly once',
                      contract.feature_log_problems(three))


if __name__ == '__main__':
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
