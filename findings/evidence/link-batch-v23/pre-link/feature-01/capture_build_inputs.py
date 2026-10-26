#!/usr/bin/env python3
"""Read-only ABI6 feature input inventory; final capture is explicitly opt-in.

Run from the repository root with --capture only when the coordinator schedules
the final pre-link snapshot. The command emits JSON to stdout and writes no files.
"""
import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SDK = ROOT / 'wasm_sdk_probe'
EVIDENCE = ROOT / 'findings/evidence/link-batch-v23/pre-link/feature-01'
R2 = ROOT / 'findings/evidence/link-batch-v23/pre-link/diagnostic-r2-01'
CORE_MANIFEST = R2 / 'core-inputs.json'
TOOLING_COLLECTOR = EVIDENCE / 'capture_tooling_inputs.py'
FEATURE_WORKER = SDK / 'sdk/v23-feature-worker.js'
V22_ARCHIVE = SDK / 'build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa'
CORE_LINKDEPS = ROOT / 'wasm-lite/build-headless-probe/instdir/program/soffice.js.linkdeps'


class InputError(RuntimeError):
    pass


def row(path):
    path = Path(path)
    raw_hash = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            raw_hash.update(block)
            size += len(block)
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': size, 'sha256': raw_hash.hexdigest()}


def source_paths(src_root):
    if not src_root.is_dir():
        raise InputError(f'missing source directory: {src_root}')
    found = sorted(p for p in src_root.rglob('*') if p.is_file())
    if not found:
        raise InputError(f'empty source file population: {src_root}')
    return found


def require_files(paths, label):
    missing = [str(path) for path in paths if not Path(path).is_file()]
    if missing:
        raise InputError(f'{label} required inputs missing: ' + ', '.join(missing))
    if not paths:
        raise InputError(f'{label} required input population is empty')
    return [Path(path) for path in paths]


def current_rows(paths):
    return [row(path) for path in sorted(set(Path(p) for p in paths))]


def row_identity(rows):
    return {entry['path']: (entry['bytes'], entry['sha256']) for entry in rows}


def validate_nonempty(rows, label):
    if not rows:
        raise InputError(f'{label} input population is empty')


def git_head():
    proc = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise InputError(f'git rev-parse HEAD failed: {proc.stderr.strip()}')
    return proc.stdout.strip()


def read_tooling_graph():
    argv = ['python3', '-I', str(TOOLING_COLLECTOR.relative_to(ROOT))]
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise InputError('adjacent tooling collector failed: ' + proc.stderr.strip())
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise InputError(f'adjacent tooling collector emitted invalid JSON: {exc}') from exc
    validate_nonempty(data.get('files', []), 'local packaging Python')
    return {'argv': argv, 'exitCode': proc.returncode, 'stderr': proc.stderr, 'data': data}


def core_rows_and_linkdeps():
    baseline = json.loads(CORE_MANIFEST.read_text(encoding='utf-8'))
    frozen = baseline.get('files', [])
    if len(frozen) != 189:
        raise InputError(f'r2 core manifest population changed: expected 189, found {len(frozen)}')
    if len({entry.get('path') for entry in frozen}) != len(frozen):
        raise InputError('r2 core manifest contains duplicate paths')
    actual = []
    problems = []
    by_path = {entry['path']: entry for entry in frozen}
    for expected in frozen:
        path = ROOT / expected['path']
        if not path.is_file():
            actual.append({'path': expected['path'], 'missing': True})
            problems.append({'path': expected['path'], 'problem': 'missing core input'})
            continue
        got = row(path)
        got['expectedBytes'] = expected['bytes']
        got['expectedSha256'] = expected['sha256']
        got['matchesR2'] = got['bytes'] == expected['bytes'] and got['sha256'] == expected['sha256']
        actual.append(got)
        if not got['matchesR2']:
            problems.append({'path': expected['path'], 'problem': 'core input differs from r2 frozen row',
                             'expectedBytes': expected['bytes'], 'actualBytes': got['bytes'],
                             'expectedSha256': expected['sha256'], 'actualSha256': got['sha256']})

    link_rel = CORE_LINKDEPS.relative_to(ROOT).as_posix()
    if link_rel not in by_path:
        raise InputError('r2 core manifest does not contain the established linkdeps source')
    linkdeps_bytes = (ROOT / link_rel).read_bytes()
    tokens = shlex.split(linkdeps_bytes.decode('utf-8'))
    if not tokens:
        raise InputError('linkdeps token population is empty')
    token_bytes = json.dumps(tokens, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    core_paths = set(by_path)
    direct_archives = []
    for token in tokens:
        if not token.startswith('/') or not token.endswith('.a'):
            continue
        token_path = Path(token)
        try:
            rel = token_path.relative_to(ROOT).as_posix()
        except ValueError:
            rel = None
        direct_archives.append({'token': token, 'repoPath': rel,
                                'presentInR2CoreRows': rel in core_paths if rel else False})
        if not rel or rel not in core_paths:
            problems.append({'token': token, 'problem': 'direct linkdeps archive is outside or absent from the r2 core inventory'})
    return {
        'baselineManifest': {'path': CORE_MANIFEST.relative_to(ROOT).as_posix(), **row(CORE_MANIFEST),
                             'declaredSource': baseline.get('source')},
        'expectedCount': len(frozen), 'actualCount': len(actual), 'files': actual,
        'linkdeps': {'path': link_rel, 'bytes': len(linkdeps_bytes),
                     'sha256': hashlib.sha256(linkdeps_bytes).hexdigest(),
                     'tokenCount': len(tokens), 'tokensSha256': hashlib.sha256(token_bytes).hexdigest(),
                     'tokens': tokens, 'directArchiveReferences': direct_archives,
                     'directArchiveCount': len(direct_archives)},
        'problems': problems,
    }


def capture():
    makefile = SDK / 'Makefile'
    sources = source_paths(SDK / 'src')
    source_inputs = require_files([makefile, FEATURE_WORKER,
                                   V22_ARCHIVE / 'sdk-worker.js',
                                   V22_ARCHIVE / 'exports.txt',
                                   V22_ARCHIVE / 'sdk-manifest.json',
                                   SDK / 'sdk/v18-writer-review-manifest.json'],
                                  'feature source/base/export/manifest')
    declared_make = makefile.read_text(encoding='utf-8')
    base_match = re.search(r'^E2_V23_BASE_WORKER\s*:=\s*(\S+)\s*$', declared_make, re.M)
    pin_match = re.search(r'^E2_V23_WORKER_SHA256\s*:=\s*([0-9a-f]{64})\s*$', declared_make, re.M)
    if not base_match or not pin_match:
        raise InputError('Makefile feature worker base path or SHA256 declaration is absent')
    if (SDK / base_match.group(1)).resolve() != (V22_ARCHIVE / 'sdk-worker.js').resolve():
        raise InputError('Makefile feature worker base path differs from the frozen v22 archive')

    source_rows = current_rows(sources)
    explicit_rows = current_rows(source_inputs)
    core = core_rows_and_linkdeps()
    tooling = read_tooling_graph()
    tooling_rows = tooling['data']['files']
    collector_path = Path(__file__).resolve()
    collector_row = row(collector_path)
    core_problems = core['problems']
    make_row = next(item for item in explicit_rows if item['path'] == 'wasm_sdk_probe/Makefile')
    tooling_make = tooling['data'].get('makefile', {})
    if (tooling_make.get('bytes'), tooling_make.get('sha256')) != (make_row['bytes'], make_row['sha256']):
        core_problems.append({'path': 'wasm_sdk_probe/Makefile',
                              'problem': 'Makefile identity differs between explicit and packaging-graph capture',
                              'explicit': make_row, 'toolingGraph': tooling_make})
    base_row = next(item for item in explicit_rows if item['path'].endswith('/sdk-worker.js'))
    base_matches_make_pin = base_row['sha256'] == pin_match.group(1)
    if not base_matches_make_pin:
        core_problems.append({'path': base_row['path'], 'problem': 'frozen v22 worker differs from Makefile identity pin',
                              'expectedSha256': pin_match.group(1), 'actualSha256': base_row['sha256']})

    # Compare the original per-group captures to one final full-content pass.
    captured_rows = {}
    for entry in source_rows + explicit_rows + core['files'] + tooling_rows:
        if entry.get('missing'):
            continue
        path = entry['path']
        normalized = {'path': path, 'bytes': entry['bytes'], 'sha256': entry['sha256']}
        prior = captured_rows.get(path)
        if prior is not None and prior != normalized:
            core_problems.append({'path': path, 'problem': 'source groups captured different bytes',
                                  'first': prior, 'later': normalized})
        captured_rows.setdefault(path, normalized)
    for entry in (core['baselineManifest'], tooling['data'].get('makefile'),
                  tooling['data'].get('collector'), collector_row):
        if entry and entry.get('path'):
            path = entry['path']
            normalized = {'path': path, 'bytes': entry['bytes'], 'sha256': entry['sha256']}
            prior = captured_rows.get(path)
            if prior is not None and prior != normalized:
                core_problems.append({'path': path, 'problem': 'metadata capture differs from source group',
                                      'first': prior, 'later': normalized})
            captured_rows.setdefault(path, normalized)
    all_paths = {ROOT / path for path in captured_rows}
    final_rows = {str(path.relative_to(ROOT)): row(path) for path in sorted(all_paths)}
    changed = [{'path': path, 'before': captured_rows[path], 'after': final_rows.get(path)}
               for path in captured_rows if final_rows.get(path) != captured_rows[path]]
    if changed:
        raise InputError('one or more inputs changed during final reread: ' + json.dumps(changed, sort_keys=True))
    core_by_path = {entry['path']: entry for entry in core['files'] if not entry.get('missing')}
    reread_core_mismatches = [path for path, expected in core_by_path.items()
                              if final_rows.get(path, {}).get('bytes') != expected['expectedBytes']
                              or final_rows.get(path, {}).get('sha256') != expected['expectedSha256']]
    if reread_core_mismatches:
        core_problems.append({'problem': 'core inputs differ on final reread', 'paths': reread_core_mismatches})

    result = {
        'schema': 'v23-feature-build-inputs-v1',
        'capturedUtc': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'gitHead': git_head(),
        'collector': collector_row,
        'groups': {
            'allSourceFilesUnderSrc': {'count': len(source_rows), 'files': source_rows},
            'explicitFeatureAndBaseInputs': {'count': len(explicit_rows), 'makefileBaseWorkerPath': base_match.group(1),
                                             'makefileBaseWorkerSha256': pin_match.group(1),
                                             'baseWorkerMatchesPin': base_matches_make_pin, 'files': explicit_rows},
            'localPackagingPython': {'argv': tooling['argv'], 'exitCode': tooling['exitCode'],
                                     'stderr': tooling['stderr'], **tooling['data']},
            'frozenR2CoreInputs': core,
            'reread': {'uniquePathCount': len(captured_rows), 'changedDuringCapture': changed,
                       'verification': 'Every selected path was hashed again after collection; core paths were compared again to all 189 frozen r2 rows.'},
        },
        'problems': core_problems,
        'status': 'PASS' if not core_problems and base_matches_make_pin else 'FAIL',
        'limits': [
            'The 189 core rows preserve the exact r2 resolved linkdeps/pre-js/toolchain file set and bytes; no broader build tree was inventoried.',
            'The linkdeps token sequence and direct absolute archive references are bound; -l token resolution is preserved by the frozen 189-row core set rather than recomputed with a linker.',
            'No compile, link, make, browser, profile write, service, or package operation is performed.',
        ],
    }
    return result


def selftest():
    rows = []
    with tempfile.TemporaryDirectory(prefix='v23-feature-input-selftest-') as temp:
        root = Path(temp)
        empty = root / 'empty-src'
        empty.mkdir()
        try:
            source_paths(empty)
        except InputError as exc:
            rows.append({'case': 'empty-source-population', 'detected': True, 'error': str(exc)})
        else:
            rows.append({'case': 'empty-source-population', 'detected': False})
        try:
            require_files([root / 'missing.cpp'], 'synthetic')
        except InputError as exc:
            rows.append({'case': 'missing-required-input', 'detected': True, 'error': str(exc)})
        else:
            rows.append({'case': 'missing-required-input', 'detected': False})
        try:
            validate_nonempty([], 'synthetic core')
        except InputError as exc:
            rows.append({'case': 'empty-core-population', 'detected': True, 'error': str(exc)})
        else:
            rows.append({'case': 'empty-core-population', 'detected': False})
    return {'cases': rows, 'allDetected': len(rows) == 3 and all(row['detected'] for row in rows),
            'realInputsReadOrModified': False}


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture', action='store_true', help='run the final read-only inventory and emit JSON to stdout')
    mode.add_argument('--selftest', action='store_true', help='exercise empty/missing input guards on temporary synthetic paths')
    args = parser.parse_args()
    try:
        result = capture() if args.capture else selftest()
    except Exception as exc:
        print(json.dumps({'status': 'FAIL', 'errorType': type(exc).__name__, 'error': str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if args.capture and result['status'] != 'PASS' else (0 if result.get('allDetected', True) else 1)


if __name__ == '__main__':
    raise SystemExit(main())
