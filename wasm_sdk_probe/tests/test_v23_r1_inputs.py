#!/usr/bin/env python3
"""Reject broken native input provenance before an R1 protocol uses it."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'collect_v23_r1_inputs', ROOT / 'wasm_sdk_probe/tools/collect_v23_r1_inputs.py')
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class NativeR1InputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for _, directory in collector.SOURCES:
            source = ROOT / collector.NATIVE / directory
            target = self.root / collector.NATIVE / directory
            target.mkdir(parents=True)
            for pattern in ('inputs.sha256', 'tool-source-as-run.cpp', 'arms-r*.jsonl', 'arms-r*.exit'):
                for path in source.glob(pattern):
                    shutil.copyfile(path, target / path.name)
        fixtures = Path('wasm_sdk_probe/test-docs/f129')
        (self.root / fixtures).mkdir(parents=True)
        for path in (ROOT / fixtures).glob('arrow-selection*.fodt'):
            shutil.copyfile(path, self.root / fixtures / path.name)
        self.folder = self.root / collector.NATIVE / collector.SOURCES[0][1]
        self.raw = self.folder / 'arms-r1.jsonl'

    def tearDown(self):
        self.temp.cleanup()

    def rows(self):
        return [json.loads(line) for line in self.raw.read_text().splitlines()]

    def write(self, rows):
        self.raw.write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def test_actual_population_and_old_workaround_red_controls(self):
        result = collector.collect(self.root)
        self.assertEqual({'main': 42, 'wrap-keys': 18, 'wrap-drag': 12}, result['groups'])
        self.assertEqual(216, result['nativeObservationCount'])
        self.assertEqual({'wrap-keys/m1e/Down', 'wrap-drag/m1d/Down', 'wrap-drag/s1d/Down'},
                         {row['id'] for row in result['wrongOldClickControls']})
        self.assertEqual('NOT_ESTABLISHED', result['wasmVerdict'])

    def test_missing_directory_cannot_pass_vacuously(self):
        shutil.rmtree(self.folder)
        with self.assertRaises(FileNotFoundError):
            collector.collect(self.root)

    def test_missing_reference_is_rejected(self):
        rows = self.rows()
        self.write([row for row in rows if row.get('arm') != 'ref-p2-forward-Left'])
        with self.assertRaisesRegex(ValueError, 'incomplete repetitions'):
            collector.collect(self.root)

    def test_duplicate_reference_is_rejected(self):
        rows = self.rows()
        self.write(rows + [next(row for row in rows if row.get('kind') == 'ref')])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            collector.collect(self.root)

    def test_changed_native_reference_cannot_hide_in_other_rounds(self):
        rows = self.rows()
        next(row for row in rows if row.get('kind') == 'ref')['text'] += 'wrong'
        self.write(rows)
        with self.assertRaisesRegex(ValueError, 'unstable native reference'):
            collector.collect(self.root)

    def test_fixture_drift_is_rejected(self):
        (self.root / 'wasm_sdk_probe/test-docs/f129/arrow-selection.fodt').write_text('wrong')
        with self.assertRaisesRegex(ValueError, 'fixture binding'):
            collector.collect(self.root)

    def test_as_run_source_drift_is_rejected(self):
        (self.folder / 'tool-source-as-run.cpp').write_text('wrong')
        with self.assertRaisesRegex(ValueError, 'as-run source binding'):
            collector.collect(self.root)

    def test_failed_native_process_is_rejected(self):
        (self.folder / 'arms-r1.exit').write_text('exit 1\n')
        with self.assertRaisesRegex(ValueError, 'native exit'):
            collector.collect(self.root)


if __name__ == '__main__':
    unittest.main()
