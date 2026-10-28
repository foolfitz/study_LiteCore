"""Fresh remainder orchestration controls; never a browser or counted observation."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import unittest

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK / 'tools'))
import v24_remaining_counts as r

OUT = SDK.parent / 'findings/evidence/link-batch-v24/remaining-preparation/controls-01'


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True, exist_ok=False)
        cls.frozen = r.freeze(OUT / 'scratch-cohort')
        cls.cohort = OUT / 'scratch-cohort/cohort.json'
        cls.original = cls.cohort.read_bytes()

    def test_code_and_namespace(self):
        self.assertIs(r.REMAINING_VERIFY.__code__, r.BASE_VERIFY.__code__)
        changed = sorted(k for k in set(r.VERIFY_GLOBALS) | set(vars(r.base))
                         if r.VERIFY_GLOBALS.get(k, KeyError) is not vars(r.base).get(k, KeyError))
        self.assertEqual(changed, ['KINDS', 'stage_spec'])
        self.assertIs(r.READ_REMAINING.__code__, r.original_reader.read.__code__)
        changed = sorted(k for k in set(r.READ_GLOBALS) | set(vars(r.original_reader))
                         if r.READ_GLOBALS.get(k, KeyError) is not vars(r.original_reader).get(k, KeyError))
        self.assertEqual(changed, ['verify'])
        self.assertIs(r.original_reader.verify, r.BASE_VERIFY)
        self.assertEqual(r.base.KINDS, ('s5', 'r1', 'selection'))

    def test_frozen_populations_and_original(self):
        old = r.BASE_VERIFY(r.SOURCE)
        frozen = r.verify(self.cohort)
        self.assertEqual(old['configSha256'], frozen['configSha256'])
        self.assertEqual(old['instrumentSources'], frozen['instrumentSources'])
        self.assertEqual([s['expectedCells'] for s in frozen['stages']], [144, 234])
        self.assertEqual([s['population'] for s in frozen['stages']], ['r1', 'selection'])
        self.assertTrue(set(old['instrumentSources']) <= set(frozen['orchestrationSources']))
        for name in r.STARTS:
            self.assertIn('tools/' + name, frozen['orchestrationSources'])

    def test_receipt_and_population_mutations(self):
        mutations = {
            'missing case': lambda f: f['stages'][0]['caseIds'].pop(),
            'missing browser': lambda f: f['stages'][0]['browsers'].pop(),
            'source receipt': lambda f: f['retainedS5'].update(completionSha256='0' * 64),
            'source omitted': lambda f: f.pop('retainedS5'),
            'orchestration hash': lambda f: f['orchestrationSources'].update({'tools/v24_remaining_counts.py': '0' * 64}),
            'override': lambda f: f['namespaceOverrides'].update(KINDS=['s5', 'r1', 'selection']),
        }
        records = []
        for name, change in mutations.items():
            with self.subTest(name=name):
                frozen = json.loads(self.original); change(frozen); self.cohort.write_bytes(r.encoded(frozen))
                try:
                    with self.assertRaises((ValueError, KeyError)) as caught:
                        r.verify(self.cohort)
                    records.append({'case': name, 'refused': str(caught.exception)})
                finally:
                    self.cohort.write_bytes(self.original)
        (OUT / 'mutations.json').write_bytes(r.encoded(records))

    def test_archive_member_red(self):
        p = self.cohort.with_name('orchestration-sources.tar.gz'); raw = p.read_bytes()
        with tarfile.open(p, 'r:gz') as archive:
            blobs = [(m, archive.extractfile(m).read()) for m in archive.getmembers()]
        try:
            with tarfile.open(p, 'w:gz') as archive:
                for m, blob in blobs[:-1]:
                    archive.addfile(m, io.BytesIO(blob))
            changed = json.loads(self.original); changed['prerequisites'][str(p.relative_to(r.ROOT))] = r.sha(p)
            self.cohort.write_bytes(r.encoded(changed))
            with self.assertRaisesRegex(ValueError, 'orchestration archive membership differs'):
                r.verify(self.cohort)
        finally:
            p.write_bytes(raw); self.cohort.write_bytes(self.original)

    def test_missing_empty_status_and_admission(self):
        status = self.cohort.with_name('status.json')
        with self.assertRaises(FileNotFoundError):
            r.READ_REMAINING(self.cohort)
        status.write_bytes(r.encoded({'cohortSha256': r.sha(self.cohort), 'state': 'STOPPED_EXCEPTION', 'stages': []}))
        self.assertEqual(r.READ_REMAINING(self.cohort)['verdict'], 'NOT_ESTABLISHED')
        # Receipt control uses an existing real V0 result, but creates no run or browser cell.
        p = OUT / 'scratch-cohort/v0-proof.json'
        p.write_bytes(r.SOURCE.parent.joinpath('v0-r1/report.json').read_bytes())
        record = {'cohortSha256': r.sha(self.cohort), 'pid': os.getppid(), 'state': 'RUNNING_R1',
                  'stages': [{'population': 'r1', 'v0': {'path': p.name, 'sha256': r.sha(p)}}]}
        try:
            status.write_bytes(r.encoded(record))
            output = r.ROOT / self.frozen['stages'][0]['output']
            r.base.verify_stage_admission(self.cohort, self.frozen, 'r1', output)
            record['stages'][0]['v0']['sha256'] = '0' * 64; status.write_bytes(r.encoded(record))
            with self.assertRaisesRegex(ValueError, 'V0 preflight'):
                r.base.verify_stage_admission(self.cohort, self.frozen, 'r1', output)
        finally:
            status.unlink()

    def test_cli_dry_run_and_reused_status(self):
        argv = [sys.executable, '-I', 'tools/run_v24_remaining_cohort.py', '--cohort', str(self.cohort)]
        good = subprocess.run(argv + ['--dry-run'], cwd=SDK, capture_output=True, text=True)
        (OUT / 'dry-run.stdout.txt').write_text(good.stdout); (OUT / 'dry-run.stderr.txt').write_text(good.stderr)
        self.assertEqual(good.returncode, 0, good.stderr)
        status = self.cohort.with_name('status.json'); status.write_text('{}')
        try:
            red = subprocess.run(argv, cwd=SDK, capture_output=True, text=True)
            (OUT / 'reused-status.stderr.txt').write_text(red.stderr)
            self.assertNotEqual(red.returncode, 0); self.assertIn('FileExistsError', red.stderr)
            self.assertFalse(list(self.cohort.parent.glob('v0-*'))[1:])
        finally:
            status.unlink()


if __name__ == '__main__':
    unittest.main()
