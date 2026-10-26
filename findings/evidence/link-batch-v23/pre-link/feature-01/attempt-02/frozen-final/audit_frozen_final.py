#!/usr/bin/env python3
"""Read-only final inventory audit for the ABI6 pre-link boundary."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
BASE = ROOT / 'findings/evidence/link-batch-v23/pre-link/feature-01'
ATTEMPT = BASE / 'attempt-02'
FROZEN = BASE / 'frozen-before.json'
BUILD_SNAPSHOT = ATTEMPT / 'build-inputs.json'
SDK = ROOT / 'wasm_sdk_probe'
SHARED_WORKER = SDK / 'sdk/sdk-worker.js'
EXPECTED_SHARED_WORKER = '0bed22bdb979138f1f0c23bd41bc05896e14f69e29fba10d4e42ccbcda5e1de9'
INVENTORY_ROOTS = ('wasm_sdk_probe/dist/profiles', 'wasm_sdk_probe/build/archive')


def hash_file(path):
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
            size += len(block)
    return size, h.hexdigest()


def inventory():
    rows = []
    for root in INVENTORY_ROOTS:
        directory = ROOT / root
        if not directory.is_dir():
            raise FileNotFoundError(f'missing inventory root: {root}')
        rows.extend(p.relative_to(ROOT).as_posix() for p in directory.rglob('*') if p.is_file())
    return sorted(rows)


def snapshot_rows():
    snap = json.loads(BUILD_SNAPSHOT.read_text(encoding='utf-8'))
    rows = {}
    for group in ('allSourceFilesUnderSrc', 'explicitFeatureAndBaseInputs', 'localPackagingPython'):
        for row in snap['groups'][group]['files']:
            rows[row['path']] = {'bytes': row['bytes'], 'sha256': row['sha256']}
    for row in (snap['collector'], snap['groups']['localPackagingPython']['collector']):
        rows[row['path']] = {'bytes': row['bytes'], 'sha256': row['sha256']}
    return snap, rows


def main():
    before_paths = inventory()
    frozen = json.loads(FROZEN.read_text(encoding='utf-8'))
    expected = {row['path']: {'bytes': row['bytes'], 'sha256': row['sha256']} for row in frozen['files']}
    problems = []
    if len(expected) != 2337 or len(expected) != len(frozen['files']):
        problems.append({'problem': 'frozen baseline population or uniqueness differs',
                         'expectedRows': 2337, 'baselineRows': len(frozen['files']),
                         'uniquePaths': len(expected)})
    current_set = set(before_paths)
    expected_set = set(expected)
    additions = sorted(current_set - expected_set)
    deletions = sorted(expected_set - current_set)
    first_rows = {}
    mismatches = []
    for i, rel in enumerate(before_paths, 1):
        size, digest = hash_file(ROOT / rel)
        first_rows[rel] = {'bytes': size, 'sha256': digest}
        baseline = expected.get(rel)
        if baseline is not None and first_rows[rel] != baseline:
            mismatches.append({'path': rel, 'expected': baseline, 'actual': first_rows[rel]})
        if i % 250 == 0:
            print(f'inventory first pass: {i}/{len(before_paths)}', file=sys.stderr, flush=True)

    build_snapshot, pin_expected = snapshot_rows()
    pin_first = {}
    source_pin_mismatches = []
    for rel, baseline in sorted(pin_expected.items()):
        path = ROOT / rel
        if not path.is_file():
            source_pin_mismatches.append({'path': rel, 'problem': 'missing compiled-source pin'})
            continue
        size, digest = hash_file(path)
        actual = {'bytes': size, 'sha256': digest}
        pin_first[rel] = actual
        if actual != baseline:
            source_pin_mismatches.append({'path': rel, 'expected': baseline, 'actual': actual})
    shared_size, shared_sha = hash_file(SHARED_WORKER)

    e1_argv = ['python3', '-I', 'tools/check_e1_c_bundle_intact.py']
    e1 = subprocess.run(e1_argv, cwd=SDK, capture_output=True, text=True)

    after_paths = inventory()
    after_set = set(after_paths)
    membership_changed = sorted(current_set ^ after_set)
    second_rows = {}
    reread_changes = []
    for i, rel in enumerate(after_paths, 1):
        size, digest = hash_file(ROOT / rel)
        second_rows[rel] = {'bytes': size, 'sha256': digest}
        if first_rows.get(rel) != second_rows[rel]:
            reread_changes.append({'path': rel, 'first': first_rows.get(rel), 'second': second_rows[rel]})
        if i % 250 == 0:
            print(f'inventory reread: {i}/{len(after_paths)}', file=sys.stderr, flush=True)

    pin_second = {}
    pin_reread_changes = []
    for rel in sorted(pin_first):
        size, digest = hash_file(ROOT / rel)
        pin_second[rel] = {'bytes': size, 'sha256': digest}
        if pin_second[rel] != pin_first[rel]:
            pin_reread_changes.append({'path': rel, 'first': pin_first[rel], 'second': pin_second[rel]})

    root_counts = {root: sum(path.startswith(root + '/') for path in before_paths) for root in INVENTORY_ROOTS}
    result = {
        'schema': 'v23-feature-final-frozen-audit-v1',
        'capturedUtc': datetime.now(timezone.utc).isoformat(),
        'gitHead': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True,
                                  text=True, check=True).stdout.strip(),
        'baseline': {'path': FROZEN.relative_to(ROOT).as_posix(), 'capturedHead': frozen.get('gitHead'),
                     'rowCount': len(frozen['files']), 'uniquePathCount': len(expected)},
        'inventory': {'roots': list(INVENTORY_ROOTS), 'rootCounts': root_counts,
                      'expectedCount': len(expected), 'actualCount': len(before_paths),
                      'actualPaths': before_paths, 'additions': additions, 'deletions': deletions,
                      'byteOrShaMismatches': mismatches,
                      'reread': {'count': len(after_paths), 'membershipChanges': membership_changed,
                                 'contentChanges': reread_changes}},
        'sharedSdkWorker': {'path': SHARED_WORKER.relative_to(ROOT).as_posix(), 'bytes': shared_size,
                            'expectedSha256': EXPECTED_SHARED_WORKER, 'actualSha256': shared_sha,
                            'matches': shared_sha == EXPECTED_SHARED_WORKER},
        'compiledSourcePins': {'snapshotPath': BUILD_SNAPSHOT.relative_to(ROOT).as_posix(),
                               'snapshotHead': build_snapshot.get('gitHead'), 'expectedCount': len(pin_expected),
                               'matchedInitial': len(pin_expected) - len(source_pin_mismatches),
                               'mismatches': source_pin_mismatches,
                               'rereadChanges': pin_reread_changes},
        'e1cGuard': {'argv': e1_argv, 'cwd': 'wasm_sdk_probe', 'exitCode': e1.returncode,
                     'stdout': e1.stdout, 'stderr': e1.stderr},
        'problems': problems,
    }
    result['status'] = 'PASS' if not (problems or additions or deletions or mismatches or membership_changed
                                      or reread_changes or source_pin_mismatches or pin_reread_changes
                                      or shared_sha != EXPECTED_SHARED_WORKER or e1.returncode) else 'FAIL'
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
