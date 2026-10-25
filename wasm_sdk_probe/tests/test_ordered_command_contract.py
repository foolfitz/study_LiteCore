"""Run the v23 pure contracts and require compilable mutations to turn red.

No LibreOffice build/link or live host is involved. These tests do not certify
engine integration, callback routing, RESET restoration or WASM behavior.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SDK = Path(__file__).resolve().parents[1]
ROOT = SDK.parent


class OrderedCommandContract(unittest.TestCase):
    def exercise(self, header_name, test_name, mutations):
        self.assertIsNotNone(shutil.which('g++'), 'g++ is required for the host unit tests')
        source = (SDK / 'src' / header_name).read_text()
        variants = [('original', source)]
        for label, before, after in mutations:
            self.assertEqual(source.count(before), 1, f'mutation drift: {label}')
            variants.append((label, source.replace(before, after)))
        with tempfile.TemporaryDirectory(prefix='v23-contract-') as work:
            for label, text in variants:
                with self.subTest(variant=label):
                    directory = Path(work) / label
                    directory.mkdir()
                    (directory / header_name).write_text(text)
                    binary = directory / 'test'
                    compile_result = subprocess.run([
                        'g++', '-std=c++17', '-O0', '-Wall', '-Wextra',
                        '-DLOK_USE_UNSTABLE_API',
                        '-I' + str(directory), '-I' + str(SDK / 'src'),
                        '-I' + str(ROOT / 'libreoffice-26-8/include'),
                        str(SDK / 'tests' / test_name), '-o', str(binary),
                    ], capture_output=True, text=True, timeout=30)
                    # A compiler error is an invalid mutation, not a red case.
                    self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
                    result = subprocess.run([str(binary)], capture_output=True,
                                            text=True, timeout=10)
                    if label == 'original':
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    else:
                        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                        self.assertIn('FAIL ', result.stdout)

    def test_post_flush_reply_and_typed_refusal(self):
        self.exercise('ordered_command_proof.hpp', 'ordered_command_proof_test.cpp', [
            ('proof-absent-as-success',
             'return proofPresent ? Verdict::Available : Verdict::MutationUnknown;',
             'return Verdict::Available;'),
            ('dispatch-failure-as-success',
             '    return Verdict::DispatchFailed;', '    return Verdict::Available;'),
            ('wrong-unknown-code', '    return "MUTATION_OUTCOME_UNKNOWN";',
             '    return "LOK_COMMAND_FAILED";'),
        ])

    def test_k1_selection_oracle_routes_and_bounds(self):
        self.exercise('ordered_delete_route.hpp', 'ordered_delete_route_test.cpp', [
            ('none-refused', '    return Route::BoundaryNoop;',
             '    return Route::Unsupported;'),
            ('separator-deleted-as-unit', '    return Route::RestoreForMerge;',
             '    return Route::DeleteUnit;'),
            ('unit-cap-removed', 'byteCount <= 128', 'byteCount <= 4096'),
            ('merge-cap-removed', 'byteCount > 4096 || ', ''),
            ('invalid-utf8-accepted', '!utf8Valid || ', ''),
            ('unsupported-type-accepted', 'selectionType != LOK_SELTYPE_TEXT || ', ''),
        ])


if __name__ == '__main__':
    unittest.main()
