#!/usr/bin/env python3
"""Fable ruling 1 (v24 pre-count) section 1.4: red cases R-a..R-f for tools/read_v24_t4.py.

Each case copies run 01's chrome/ (and firefox/ for R-f) into --scratch, mutates the copy, runs the
reader on it and checks the declared outcome.  The committed run 01 files are only read.

  python3 -I findings/evidence/link-batch-v24/pre-count/t4/reader-red-01/reader_red.py --scratch <new dir>
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
T4 = HERE.parent
ROOT = T4.parents[4]
READER = ROOT / 'wasm_sdk_probe/tools/read_v24_t4.py'


def copy(scratch, name, browsers=('chrome',)):
    out = scratch / name
    for b in browsers:
        target = out / b; target.mkdir(parents=True)
        for f in ('report.json', 'steps.json', 'wire.json'):
            if (T4 / b / f).exists():
                shutil.copy(T4 / b / f, target / f)
    return out


def entry(report, cid):
    found = [e for e in report['checks'] if e['id'] == cid]
    assert len(found) == 1, cid
    return found[0]


def edit_report(directory, fn):
    path = directory / 'chrome/report.json'; report = json.loads(path.read_text()); fn(report)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')


def read(directory, browsers=('chrome',)):
    argv = [sys.executable, '-I', str(READER), '--chrome', str(directory / 'chrome'), '--out', str(directory / 'read.json')]
    if 'firefox' in browsers:
        argv += ['--firefox', str(directory / 'firefox')]
    done = subprocess.run(argv, capture_output=True, text=True)
    return done.returncode, json.loads((directory / 'read.json').read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=False)
    results, checks = {}, []

    def case(name, mutate=None, browsers=('chrome',)):
        directory = copy(args.scratch, name, browsers)
        if mutate: mutate(directory)
        code, out = read(directory, browsers)
        results[name] = {'exit': code, 'verdict': out['verdict'], 'rule2': out['rule2']['verdict'],
                         'red': out['rule2']['red'], 'rule1': out['rule1']['verdict']}
        return results[name]

    def ra(d):
        def f(r): e = entry(r, 'ctrl-v-reaches-the-document'); e['outcome'] = 'FAIL'; e['ok'] = False
        edit_report(d, f)
    r = case('R-a', ra)
    checks.append(('R-a: ctrl-v PASS->FAIL is a 2a FAIL naming it', r['rule2'] == 'FAIL' and [(x['check'], x['rule']) for x in r['red']] == [('ctrl-v-reaches-the-document', '2a')]))

    def rb(d):
        def f(r): e = entry(r, 'clear-format-removes-every-inline-format'); e['outcome'] = 'PASS'; e['ok'] = True
        edit_report(d, f)
    r = case('R-b', rb)
    checks.append(('R-b: clear-format NE->PASS is a 2b FAIL naming it', r['rule2'] == 'FAIL' and [(x['check'], x['rule']) for x in r['red']] == [('clear-format-removes-every-inline-format', '2b')]))

    def rc(d):
        def f(r):
            arm = entry(r, 'every-inline-format-reaches-the-document')['observed']['arms'][0]
            key = next(k for k, v in arm.items() if isinstance(v, bool))
            arm[key] = not arm[key]; results['R-c-leaf'] = key
        edit_report(d, f)
    r = case('R-c', rc)
    leaf = results.get('R-c-leaf')
    checks.append(('R-c: one non-volatile leaf changed is a 2b FAIL printing that leaf path', r['rule2'] == 'FAIL' and len(r['red']) == 1
                   and r['red'][0]['check'] == 'every-inline-format-reaches-the-document'
                   and [x.split(' | ')[0] for x in r['red'][0]['differingLeaves']] == [f'[0]/observed/arms[0]/{leaf}']))

    def rd(d):
        def f(r): entry(r, 'every-inline-format-reaches-the-document')['observed']['arms'][0]['formatPressWaitedMs'] = 999
        edit_report(d, f)
    r = case('R-d', rd)
    checks.append(('R-d: only formatPressWaitedMs changed: the member stays ok, rule 2 PASS', r['rule2'] == 'PASS' and not r['red']))

    def re_(d):
        path = d / 'chrome/wire.json'; wire = json.loads(path.read_text())
        drop = {(x['worker'], x['requestId']) for x in wire['records'] if x['kind'] == 'request' and (
            x['operation'] in ('replaceSelection', 'pasteMarkdown') or (x['operation'] == 'insertText' and x['route'] == 'paste'))}
        wire['records'] = [x for x in wire['records'] if (x['worker'], x['requestId']) not in drop]
        path.write_text(json.dumps(wire, indent=1) + '\n'); results['R-e-dropped'] = len(drop)
    r = case('R-e', re_)
    checks.append(('R-e: no paste-route request: T4 NE, not PASS', r['verdict'] == 'NOT_ESTABLISHED' and r['rule2'] == 'NOT_ESTABLISHED'))

    r = case('R-f', None, ('chrome', 'firefox'))
    checks.append(('R-f: run 01 unmodified under the corrected reader: rule 2 PASS (not T4\'s verdict)', r['rule2'] == 'PASS'))

    report = {'reader': str(READER.relative_to(ROOT)), 'results': results,
              'checks': [{'check': c, 'ok': bool(ok)} for c, ok in checks],
              'verdict': 'RED_CASES_HOLD' if all(ok for _, ok in checks) else 'RED_CASES_DO_NOT_HOLD'}
    (HERE / 'results.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    shutil.copy(args.scratch / 'R-f/read.json', T4 / 'read-01b.json')
    for c, ok in checks: print(('ok   ' if ok else 'FAIL ') + c)
    print(report['verdict'])
    return 0 if report['verdict'] == 'RED_CASES_HOLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
