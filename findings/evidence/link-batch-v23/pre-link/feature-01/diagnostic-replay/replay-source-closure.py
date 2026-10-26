#!/usr/bin/env python3
"""Compare accepted diagnostic source SHA maps with one immutable Git commit."""
import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
R2 = ROOT / 'findings/evidence/link-batch-v23/post-link/r2-attempt-01'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def literal_assignment(commit, source, name):
    cmd = ['git', 'show', f'{commit}:{source}']
    proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode:
        raise ValueError(f'cannot read source-owned case set: {cmd}: {proc.stderr.decode("utf-8", "replace")}')
    tree = ast.parse(proc.stdout.decode('utf-8'))
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            if not isinstance(node.value, ast.Dict):
                raise ValueError(f'{source}:{name} is not a literal dict')
            keys = [ast.literal_eval(key) for key in node.value.keys]
            if not all(isinstance(key, str) for key in keys):
                raise ValueError(f'{source}:{name} contains nonliteral case keys')
            return sorted(keys)
    raise ValueError(f'{source} has no top-level literal {name}')


def validate_members(cohort, expected, actual, directory_exists):
    problems = []
    if not directory_exists:
        problems.append({'cohort': cohort, 'problem': 'missing-directory'})
    elif not actual:
        problems.append({'cohort': cohort, 'problem': 'empty-member-list'})
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing:
        problems.append({'cohort': cohort, 'problem': 'missing-members', 'members': missing})
    if extra:
        problems.append({'cohort': cohort, 'problem': 'unexpected-members', 'members': extra})
    return problems


def accepted_reports(commit):
    expected_040 = literal_assignment(commit, 'wasm_sdk_probe/tools/v23_remaining_cases.py', 'CASES_040')
    expected_wd = literal_assignment(commit, 'wasm_sdk_probe/tools/v23_wd_cases.py', 'PLANS')
    result = []
    membership = []
    for cohort, relpath in [
        ('bounded', 'bounded-counted-01/report.json'),
        ('S-init', 's-init-counted-01/report.json'),
        ('timing-largest', 'timing-counted-01/largest/report.json'),
        ('timing-workload', 'timing-counted-01/workload/report.json'),
    ]:
        path = R2 / relpath
        result.append((cohort, path))
        if not path.is_file():
            membership.append({'cohort': cohort, 'report': str(path.relative_to(ROOT)), 'problem': 'accepted report missing'})
    for cohort, dirname, expected in [('040', '040-counted-02', expected_040), ('W-D', 'wd-counted-01', expected_wd)]:
        directory = R2 / dirname
        actual_paths = sorted(directory.glob('*/report.json')) if directory.is_dir() else []
        actual = [p.parent.name for p in actual_paths]
        membership.extend(validate_members(cohort, expected, actual, directory.is_dir()))
        result.extend((f'{cohort}-{p.parent.name}', p) for p in actual_paths)
    return result, membership, {'040': expected_040, 'W-D': expected_wd}


def selftest_members():
    expected = ['case-a', 'case-b']
    vectors = [
        ('missing-directory', expected, [], False, 'missing-directory'),
        ('empty-list', expected, [], True, 'empty-member-list'),
    ]
    rows = []
    for name, members, actual, exists, expected_problem in vectors:
        found = validate_members(name, members, actual, exists)
        detected = any(p['problem'] == expected_problem for p in found)
        rows.append({'case': name, 'expectedRed': True, 'problems': found, 'detected': detected})
    return {'cases': rows, 'allDetected': all(row['detected'] for row in rows)}


def report_maps(report):
    maps = []
    for field in ('instrument', 'wdInstrumentSha256'):
        value = report.get(field)
        if isinstance(value, dict):
            maps.append((field, value, 'sdk'))
    config = report.get('config')
    if isinstance(config, dict):
        value = config.get('instrumentSha256')
        if isinstance(value, dict):
            maps.append(('config.instrumentSha256', value, 'sdk'))
    for field in ('mirrorInstrument',):
        value = report.get(field)
        if isinstance(value, dict):
            maps.append((field, value, 'served'))
    if isinstance(config, dict) and isinstance(config.get('servedSources'), dict):
        maps.append(('config.servedSources', config['servedSources'], 'served'))
    if isinstance(report.get('wdMirrorSha256'), str):
        maps.append(('wdMirrorSha256', {'v23-diagnostic-wd.js': report['wdMirrorSha256']}, 'served'))
    return maps


def source_path(key, kind, sdk_keys):
    if kind == 'sdk':
        return key if key.startswith('wasm_sdk_probe/') else 'wasm_sdk_probe/' + key
    if key == 'e2-editor.html':
        candidates = [p for p in sdk_keys if p.startswith('web/') and p.endswith('.html')]
        return 'wasm_sdk_probe/' + candidates[0] if len(candidates) == 1 else None
    if '/' in key:
        return 'wasm_sdk_probe/' + key
    candidates = [p for p in sdk_keys if p.startswith('web/') and p.endswith('/' + key)]
    return 'wasm_sdk_probe/' + candidates[0] if len(candidates) == 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit', default='1fdd165a')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        result = selftest_members()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result['allDetected'] else 1
    commit = subprocess.run(['git', 'rev-parse', args.commit], cwd=ROOT, capture_output=True, check=True, text=True).stdout.strip()
    checks = []
    errors = []
    source_hashes = {}
    reports, membership_problems, source_case_sets = accepted_reports(commit)
    errors.extend(membership_problems)
    for cohort, path in reports:
        if not path.is_file():
            errors.append({'cohort': cohort, 'report': str(path.relative_to(ROOT)), 'problem': 'accepted report missing'})
            continue
        report = json.loads(path.read_text(encoding='utf-8'))
        maps = report_maps(report)
        if not maps:
            errors.append({'cohort': cohort, 'report': str(path.relative_to(ROOT)), 'problem': 'no source SHA map'})
            continue
        for map_name, values, kind in maps:
            sdk_keys = set()
            for name, digest in values.items():
                if kind == 'sdk':
                    sdk_keys.add(name if name.startswith('wasm_sdk_probe/') else name)
            # A private HTML entry maps to the sole cohort HTML in the bound SDK graph.
            source_keys = set()
            for name in values:
                if name.startswith('wasm_sdk_probe/'):
                    source_keys.add(name.removeprefix('wasm_sdk_probe/'))
                elif kind == 'sdk':
                    source_keys.add(name)
            # Pull the associated full graph as source-path context for served aliases.
            for field in ('instrument', 'wdInstrumentSha256'):
                for name in report.get(field, {}):
                    source_keys.add(name.removeprefix('wasm_sdk_probe/'))
            config = report.get('config') if isinstance(report.get('config'), dict) else {}
            for name in config.get('instrumentSha256', {}):
                source_keys.add(name.removeprefix('wasm_sdk_probe/'))
            for name, expected in values.items():
                source = source_path(name, kind, source_keys)
                if not source:
                    checks.append({'cohort': cohort, 'report': str(path.relative_to(ROOT)), 'map': map_name,
                                   'recordedPath': name, 'recordedSha256': expected, 'status': 'UNMAPPED'})
                    errors.append({'cohort': cohort, 'map': map_name, 'recordedPath': name, 'problem': 'served path has no unique recorded source path'})
                    continue
                previous = source_hashes.get(source)
                if previous is not None and previous != expected:
                    errors.append({'sourcePath': source, 'problem': 'conflicting recorded source hashes', 'first': previous, 'later': expected})
                source_hashes.setdefault(source, expected)
                cmd = ['git', 'show', f'{commit}:{source}']
                proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                actual = sha(proc.stdout) if proc.returncode == 0 else None
                blob_cmd = ['git', 'rev-parse', f'{commit}:{source}']
                blob_proc = subprocess.run(blob_cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                status = 'MATCH' if proc.returncode == 0 and actual == expected else ('MISSING_GIT_PATH' if proc.returncode else 'SHA_MISMATCH')
                checks.append({'cohort': cohort, 'report': str(path.relative_to(ROOT)), 'map': map_name,
                               'recordedPath': name, 'sourcePath': source, 'recordedSha256': expected,
                               'gitBlob': {'argv': blob_cmd, 'exitCode': blob_proc.returncode,
                                           'oid': blob_proc.stdout.strip() if blob_proc.returncode == 0 else None,
                                           'stderr': blob_proc.stderr},
                               'gitShow': {'argv': cmd, 'exitCode': proc.returncode, 'stdoutBytes': len(proc.stdout),
                                           'stdoutSha256': actual, 'stderr': proc.stderr.decode('utf-8', 'replace')},
                               'status': status})
                if status != 'MATCH':
                    errors.append({'cohort': cohort, 'map': map_name, 'recordedPath': name,
                                   'sourcePath': source, 'status': status,
                                   'recordedSha256': expected, 'gitSha256': actual})

    # v23_wd_cases imports the native population generator from this evidence path.
    # It is outside the SDK instrument map, so verify Git availability but keep the
    # report-binding limitation explicit instead of treating it as a bound input.
    generator = 'findings/evidence/link-batch-v23/native/ordered-commands/tool/run_arms.py'
    generator_cmd = ['git', 'show', f'{commit}:{generator}']
    generator_proc = subprocess.run(generator_cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    generator_blob_cmd = ['git', 'rev-parse', f'{commit}:{generator}']
    generator_blob = subprocess.run(generator_blob_cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    generator_row = {'sourcePath': generator, 'gitShow': {'argv': generator_cmd,
                    'exitCode': generator_proc.returncode, 'stdoutBytes': len(generator_proc.stdout),
                    'stdoutSha256': sha(generator_proc.stdout) if generator_proc.returncode == 0 else None,
                    'stderr': generator_proc.stderr.decode('utf-8', 'replace')},
                    'gitBlob': {'argv': generator_blob_cmd, 'exitCode': generator_blob.returncode,
                                'oid': generator_blob.stdout.strip() if generator_blob.returncode == 0 else None,
                                'stderr': generator_blob.stderr},
                    'status': 'PRESENT_BUT_NOT_RECORDED_IN_INSTRUMENT_MAP' if generator_proc.returncode == 0 else 'MISSING_GIT_PATH'}

    result = {'commit': commit, 'cohortReports': len(reports), 'sourceOwnedMemberSets': source_case_sets,
              'membershipProblems': membership_problems, 'uniqueBoundSourcePaths': len(source_hashes),
              'mapRowsChecked': len(checks), 'matchedRows': sum(x.get('status') == 'MATCH' for x in checks),
              'unmappedRows': sum(x.get('status') == 'UNMAPPED' for x in checks),
              'mismatchedOrMissingRows': sum(x.get('status') not in ('MATCH', 'UNMAPPED') for x in checks),
              'checks': checks, 'externalGeneratorCheck': generator_row, 'problems': errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
