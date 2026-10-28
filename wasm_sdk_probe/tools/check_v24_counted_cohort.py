#!/usr/bin/env python3
"""Offline cohort mutation controls. Creates scratch artifacts; never starts V0 or browsers."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v24_counted_selection_cases import ROOT, PROJECT, encoded, sha
from run_v24_counted_cohort import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    result = {'scope': 'Scratch instrument controls only; zero counted observations', 'commands': [], 'checks': []}
    def run(name, argv):
        start = time.monotonic()
        done = subprocess.run(argv, cwd=PROJECT, capture_output=True, text=True)
        (out / (name + '.stdout.txt')).write_text(done.stdout)
        (out / (name + '.stderr.txt')).write_text(done.stderr)
        result['commands'].append({'name': name, 'argv': argv, 'exit': done.returncode,
                                   'seconds': round(time.monotonic() - start, 3)})
        return done
    def check(name, value, **payload):
        result['checks'].append({'name': name, 'ok': bool(value), **payload})
    cohort = out / 'scratch-cohort/cohort.json'
    done = run('freeze', [sys.executable, '-I', 'tools/freeze_v24_counted_cohort.py', '--out', str(cohort.parent)])
    check('scratch-freeze', done.returncode == 0)
    if done.returncode:
        raise ValueError('scratch freeze failed: ' + done.stderr)
    original = cohort.read_bytes()
    frozen = verify(cohort)
    check('unmodified-verifies', bool(frozen))
    done = run('dry-run', [sys.executable, '-I', 'tools/run_v24_counted_cohort.py', '--cohort', str(cohort), '--dry-run'])
    check('dry-run-no-status', done.returncode == 0 and not cohort.with_name('status.json').exists())
    def mutant(name, change):
        altered = json.loads(original); change(altered); cohort.write_bytes(encoded(altered))
        try:
            verify(cohort)
        except Exception as error:
            check(name, True, reason=f'{type(error).__name__}: {error}')
        else:
            check(name, False, reason='mutation accepted')
        finally:
            cohort.write_bytes(original)
    mutant('config-drift', lambda f: f.update(configSha256='0' * 64))
    mutant('case-removed', lambda f: f['stages'][0]['caseIds'].pop())
    mutant('browser-removed', lambda f: f['stages'][0]['browsers'].pop())
    mutant('prerequisite-drift', lambda f: f['prerequisites'].update({next(iter(f['prerequisites'])): '0' * 64}))
    # Reach the membership guard even if a corrupt archive has been re-hashed into the receipt.
    archive_path = cohort.with_name('frozen-sources.tar.gz'); archive_raw = archive_path.read_bytes()
    with tarfile.open(archive_path, 'r:gz') as archive:
        blobs = [(m, archive.extractfile(m).read()) for m in archive.getmembers()]
    try:
        with tarfile.open(archive_path, 'w:gz') as archive:
            for member, raw in blobs[:-1]:
                archive.addfile(member, io.BytesIO(raw))
        altered = json.loads(original)
        altered['prerequisites'][str(archive_path.relative_to(ROOT))] = sha(archive_path)
        cohort.write_bytes(encoded(altered))
        try:
            verify(cohort)
        except ValueError as error:
            check('archive-member-removed', 'membership differs' in str(error), reason=str(error))
        else:
            check('archive-member-removed', False)
    finally:
        archive_path.write_bytes(archive_raw); cohort.write_bytes(original)
    done = run('missing-status-reader', [sys.executable, '-I', 'tools/read_v24_counted_cohort.py', '--cohort', str(cohort), '--out', str(out / 'missing-status.json')])
    check('missing-status-no-credit', done.returncode == 1 and json.loads((out / 'missing-status.json').read_bytes())['verdict'] == 'NOT_ESTABLISHED')
    status = cohort.with_name('status.json')
    status.write_bytes(encoded({'cohortSha256': sha(cohort), 'state': 'STOPPED_EXCEPTION', 'stages': []}))
    done = run('reused-status', [sys.executable, '-I', 'tools/run_v24_counted_cohort.py', '--cohort', str(cohort)])
    check('reused-status-no-launch', done.returncode != 0 and 'FileExistsError' in done.stderr and not list(cohort.parent.glob('v0-*')))
    done = run('empty-status-reader', [sys.executable, '-I', 'tools/read_v24_counted_cohort.py', '--cohort', str(cohort), '--out', str(out / 'empty-status.json')])
    check('empty-status-no-credit', done.returncode == 1 and json.loads((out / 'empty-status.json').read_bytes())['verdict'] == 'NOT_ESTABLISHED')
    done = run('filters-counted-refused', [sys.executable, '-I', 'tools/run_v24_counted_selection.py', '--population', 's5', '--browser', 'chrome', '--output', str(out / 'must-not-exist')])
    check('counted-filters-refused', done.returncode != 0 and 'filters require preparation-only' in done.stderr and not (out / 'must-not-exist').exists())
    done = run('no-cohort-refused', [sys.executable, '-I', 'tools/run_v24_counted_selection.py', '--population', 's5', '--output', str(out / 'must-not-exist')])
    check('counted-no-cohort-refused', done.returncode != 0 and 'requires a frozen cohort' in done.stderr and not (out / 'must-not-exist').exists())
    result['verdict'] = 'COHORT_CONTROLS_HOLD' if all(c['ok'] for c in result['checks']) else 'NOT_ESTABLISHED'
    (out / 'results.json').write_bytes(encoded(result))
    print(encoded({'verdict': result['verdict'], 'checks': result['checks']}).decode(), end='')
    return 0 if result['verdict'] == 'COHORT_CONTROLS_HOLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
