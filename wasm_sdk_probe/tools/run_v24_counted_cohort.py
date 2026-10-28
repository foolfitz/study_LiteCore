#!/usr/bin/env python3
"""Run a frozen v24 cohort, V0'' before each population, stop at the first nonpass. Never retry.

--dry-run verifies every frozen binding and prints commands without starting V0 or a browser.
The owner chooses detached execution or owner-run before the real launch.
"""
import argparse
import datetime
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v24_counted_selection_cases import ROOT, PROJECT, config, encoded, digest, sha, population, KINDS, BROWSERS


def now():
    return datetime.datetime.now().astimezone().isoformat()


def verify(cohort):
    cohort = Path(cohort).resolve()
    frozen = json.loads(cohort.read_bytes())
    plan = config()
    if digest(encoded(plan)) != frozen['configSha256']:
        raise ValueError('frozen plan/input drift')
    if json.loads(gzip.decompress(cohort.with_name('frozen-config.json.gz').read_bytes())) != plan:
        raise ValueError('frozen config archive differs')
    for name, want in frozen['prerequisites'].items():
        if sha(ROOT / name) != want:
            raise ValueError('prerequisite changed: ' + name)
    if plan['instrumentSources'] != frozen['instrumentSources'] or plan['servedSources'] != frozen['servedSources']:
        raise ValueError('frozen source closure differs')
    with tarfile.open(cohort.with_name('frozen-sources.tar.gz'), 'r:gz') as archive:
        expected = {**{'instrument/' + n: h for n, h in plan['instrumentSources'].items()},
                    **{'served/' + n: h for n, h in plan['servedSources'].items()}}
        if len(archive.getmembers()) != len(expected) or set(archive.getnames()) != set(expected):
            raise ValueError('source archive membership differs')
        for member in archive.getmembers():
            if not member.isfile() or digest(archive.extractfile(member).read()) != expected[member.name]:
                raise ValueError('frozen source blob differs: ' + member.name)
    if [s['population'] for s in frozen['stages']] != list(KINDS):
        raise ValueError('stage population/order differs')
    for stage in frozen['stages']:
        wanted = population(plan, stage['population'])
        if stage['caseIds'] != wanted or stage['browsers'] != list(BROWSERS) or stage['expectedCells'] != len(wanted) * len(BROWSERS):
            raise ValueError('declared population differs')
        output = cohort.parent / stage['population']
        if stage != stage_spec(cohort, stage['population'], plan, frozen['preRed']['path']):
            raise ValueError('stage commands/output differ')
    return frozen


def stage_spec(cohort, kind, plan, pre_red):
    output = Path(cohort).resolve().parent / kind
    cases = population(plan, kind)
    return {'population': kind, 'output': str(output.relative_to(ROOT)), 'caseIds': cases,
            'browsers': list(BROWSERS), 'expectedCells': len(cases) * len(BROWSERS),
            'runnerArgv': [sys.executable, '-I', 'tools/run_v24_counted_selection.py', '--population', kind,
                           '--cohort', str(Path(cohort).resolve()), '--pre-red-report', pre_red, '--output', str(output)],
            'judgeArgv': [sys.executable, '-I', 'tools/judge_v24_counted_selection.py', str(output / 'report.json')]}


def verify_stage_admission(cohort, frozen, kind, output):
    cohort = Path(cohort).resolve()
    status = json.loads(cohort.with_name('status.json').read_bytes())
    entry = status['stages'][-1]
    if status['cohortSha256'] != sha(cohort) or status['pid'] != os.getppid() or status['state'] != 'RUNNING_' + kind.upper():
        raise ValueError('collection was not launched by this cohort')
    if entry['population'] != kind or Path(output).resolve() != ROOT / next(s for s in frozen['stages'] if s['population'] == kind)['output']:
        raise ValueError('collection stage/output differs')
    preflight = cohort.parent / entry['v0']['path']
    if sha(preflight) != entry['v0']['sha256'] or json.loads(preflight.read_bytes()).get('verdict') != 'V0PP_HOLDS':
        raise ValueError('V0 preflight absent/changed/nonpassing')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    args.cohort = args.cohort.resolve()
    frozen = verify(args.cohort)
    if args.dry_run:
        print(encoded({'verdict': 'FROZEN_COHORT_READY', 'stages': frozen['stages']}).decode(), end='')
        return 0
    status = args.cohort.with_name('status.json')
    record = {'schema': 1, 'startedAt': now(), 'pid': os.getpid(), 'cohortSha256': sha(args.cohort),
              'gitHead': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'state': 'STARTING', 'stages': []}
    # Exclusive creation is also the concurrency guard; a stale/failed run is never resumed.
    with status.open('x') as stream:
        stream.write(encoded(record).decode())
    def write():
        temporary = status.with_suffix('.json.tmp')
        temporary.write_bytes(encoded(record)); temporary.replace(status)
    def execute(name, argv):
        started = time.monotonic()
        log = args.cohort.parent / (name + '.txt')
        with log.open('x') as stream:
            result = subprocess.run(argv, cwd=PROJECT, stdout=stream, stderr=subprocess.STDOUT)
        return {'argv': argv, 'exit': result.returncode, 'seconds': round(time.monotonic() - started, 1),
                'log': log.name, 'logSha256': sha(log)}
    try:
        for stage in frozen['stages']:
            verify(args.cohort)
            kind = stage['population']
            if (ROOT / stage['output']).exists():
                raise ValueError('cohort output already exists')
            entry = {'population': kind, 'startedAt': now()}
            record['stages'].append(entry); record['state'] = 'PREFLIGHT_' + kind.upper(); write()
            v0dir = args.cohort.parent / ('v0-' + kind)
            entry['preflight'] = execute(kind + '.v0', [sys.executable, '-I', 'tools/run_v24_v0_double_prime.py', '--out', str(v0dir)])
            v0 = v0dir / 'report.json'
            if entry['preflight']['exit'] or not v0.is_file() or json.loads(v0.read_bytes()).get('verdict') != 'V0PP_HOLDS':
                raise ValueError('V0PP_HOLDS not established')
            entry['v0'] = {'path': str(v0.relative_to(args.cohort.parent)), 'sha256': sha(v0)}
            verify(args.cohort)
            record['state'] = 'RUNNING_' + kind.upper(); write()
            entry['runner'] = execute(kind + '.runner', stage['runnerArgv']); write()
            report = ROOT / stage['output'] / 'report.json'
            if report.is_file():
                entry['reportSha256'] = sha(report)
                entry['judge'] = execute(kind + '.judge', stage['judgeArgv'])
            verify(args.cohort); write()
            if entry['runner']['exit'] or entry.get('judge', {}).get('exit') != 0:
                record.update(state='STOPPED_FIRST_NONPASS', finishedAt=now()); write(); return 1
        record.update(state='ALL_COHORTS_PASS', finishedAt=now()); write(); return 0
    except BaseException as error:
        record.update(state='STOPPED_EXCEPTION', finishedAt=now(), error=repr(error)); write(); raise


if __name__ == '__main__':
    raise SystemExit(main())
