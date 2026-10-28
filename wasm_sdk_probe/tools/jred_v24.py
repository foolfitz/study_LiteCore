#!/usr/bin/env python3
"""SPEC-M3-link-batch-v24 6.1 J-red: the v24 S5 reader's red cases, before it judges any v24 page,
and red case (v) for both guards it names (T2 here, T3 in tests/v24-typed-insert-sdk.test.mjs).

Inputs are v23 counted-02 pages (s5-counted-02/*.json.gz, each checked against that run's
report.json), read through the v24 plan.  No browser.  Cases:

  (ii-a)  a passing v23 type cell rewritten to the v24 wire shape (route on every insertText, typed
          replies with completion), then the s5cand `x` reply replaced by the engine's proof-absent
          error (MUTATION_OUTCOME_UNKNOWN, proof-absent-at-poll:UNO_COMMAND_RESULT)   -> FAIL, proof
  (ii-b)  the same, the `x` reply ok with method uno-insert-text but no completion  -> FAIL, proof
  (ii-c)  the same rewrite with every reply proper (the control)                  -> T2 holds
  (iii)   counted-02's chrome shift-Right@cell-end/type page as it is             -> FAIL naming the route
  (iii')  that page with `completion` added to every insertText reply, route and method left as they
          are: only the route is wrong                                            -> FAIL, route only

(v) guard removal: the reader is copied to a scratch module with the lines tagged `# T2-route`
(resp. `# T2-proof`) deleted, and every case is read again.  A guard counts as tested only if a red
case that names it stops naming it when (and only when) that guard is removed.

T3 (v): the T3 test is copied to a scratch root with its set-equality line deleted and run on
(a) the real input/, (b) red case (iv)'s scratch input (pre-link/t3-red/fake.diff applied),
(c) an empty directory; the real test runs on (b) too.  The equality guard is tested if the real
test is red on (b) and the guardless copy is green on (b), while the copy stays red on (c)
(non-vacuity is a different clause) and green on (a).

Usage: python3 tools/jred_v24.py --out <new dir>
"""
import argparse
import copy
import os
import shutil
import subprocess
import gzip
import importlib.util
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_v24_feature_selection as j24
from v24_feature_selection_cases import ROOT, config, digest

COUNTED = ROOT / 'findings/evidence/link-batch-v23/feature-protocol/s5-counted-02'
BASE = 'chrome-shift-Down@caret-mid__type.json'
ROUTE_RED = 'chrome-shift-Right@cell-end__type.json'
PROOF_ABSENT = {'code': 'MUTATION_OUTCOME_UNKNOWN', 'failureShape': 'proof-absent-at-poll:UNO_COMMAND_RESULT',
                'message': 'synthetic (J-red ii-a): no UNO_COMMAND_RESULT at the first poll'}


def counted_cell(name):
    runs = {r['path']: r['sha256'] for r in json.loads((COUNTED / 'report.json').read_text())['runs']}
    raw = gzip.decompress((COUNTED / (name + '.gz')).read_bytes())
    if runs.get(name) != digest(raw):
        raise SystemExit('counted-02 cell bytes differ from its report: ' + name)
    return json.loads(raw), {'path': str((COUNTED / (name + '.gz')).relative_to(ROOT)), 'sha256': digest(raw)}


def insert_pairs(page):
    keys = {(r['generation'], r['message']['requestId']): r for r in page['requests'] if r['message'].get('operation') == 'insertText'}
    return [(request, next(x for x in page['responses'] if (x['generation'], x['message'].get('requestId')) == key))
            for key, request in keys.items()]


def v24_shape(page):
    """Every insertText request routed and every reply a typed one, the way a v24 page would carry them."""
    page = copy.deepcopy(page)
    for request, reply in insert_pairs(page):
        request['message']['payload']['route'] = 'uno-insert-text'
        result = reply['message']['result']
        result.update(method='uno-insert-text', completion='uno-command-result',
                      resultPayload='{ "commandName": ".uno:InsertText", "synthetic": "J-red" }')
    return page


def s5cand_x(page):
    window = page['s5cand']['sequence']
    found = [(q, r) for q, r in insert_pairs(page) if q['generation'] == window['generation']
             and q in page['requests'][window['requestStart']:window['requestEnd']]]
    if len(found) != 1:
        raise SystemExit('base page: the s5cand x insert is not unique')
    return found[0]


def cases():
    base, base_receipt = counted_cell(BASE)
    red, red_receipt = counted_cell(ROUTE_RED)
    out = {}
    a = v24_shape(base['page']); _, reply = s5cand_x(a)
    reply['message'] = {k: v for k, v in reply['message'].items() if k != 'result'} | {'ok': False, 'error': PROOF_ABSENT}
    out['ii-a'] = a
    b = v24_shape(base['page']); _, reply = s5cand_x(b); reply['message']['result'].pop('completion')
    out['ii-b'] = b
    out['ii-c'] = v24_shape(base['page'])
    out['iii'] = copy.deepcopy(red['page'])
    c = copy.deepcopy(red['page'])
    for _, reply in insert_pairs(c):
        reply['message']['result']['completion'] = 'uno-command-result'
    out["iii'"] = c
    return out, {'base': base_receipt, 'routeRed': red_receipt}


def names(problems, guard):
    if guard == 'route':
        return any(' route ' in p or 'method' in p for p in problems)
    return any('completion' in p or 'refused' in p for p in problems)


EXPECT = {  # case -> (expected T2-FAIL guards with the real reader)
    'ii-a': {'proof'}, 'ii-b': {'proof'}, 'ii-c': set(), 'iii': {'route', 'proof'}, "iii'": {'route'}}


def mutant(tag, where):
    source = Path(j24.__file__).read_text().splitlines(keepends=True)
    kept = [line for line in source if not line.rstrip().endswith('# ' + tag)]
    removed = len(source) - len(kept)
    if removed == 0:
        raise SystemExit('no line tagged ' + tag)
    path = where / f'judge_v24_mutant_{tag.replace("-", "_")}.py'
    path.write_text(''.join(kept))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module, removed, digest(path.read_bytes())


def read(module, page, plan):
    problems = module.t2(page, plan)
    value = module.inspect(page, plan, 'chrome')
    return {'verdict': value['verdict'], 'reason': value.get('reason'), 't2': problems,
            'guards': sorted(g for g in ('route', 'proof') if problems and names(problems, g))}


T3_TEST = Path(__file__).resolve().parent.parent / 'tests/v24-typed-insert-sdk.test.mjs'
T3_EQUALITY = '  assert.deepEqual([...literals].sort(), [...INSERT_ROUTE_BY_SOURCE.keys()].sort());\n'
FAKE_DIFF = ROOT / 'findings/evidence/link-batch-v24/pre-link/t3-red/fake.diff'


def t3_guard_removal(out):
    project = Path(__file__).resolve().parent.parent
    root = out / 't3-v'; (root / 'tests').mkdir(parents=True)
    (root / 'sdk').symlink_to(project / 'sdk', target_is_directory=True)
    source = T3_TEST.read_text()
    if source.count(T3_EQUALITY) != 1:
        raise SystemExit('the T3 equality line is not where J-red expects it')
    guardless = root / 'tests' / T3_TEST.name
    guardless.write_text(source.replace(T3_EQUALITY, '', 1))
    fake = root / 'input-fake'; fake.mkdir()
    for path in (project / 'input').glob('*.js'):
        shutil.copy(path, fake / path.name)
    lines = (fake / 'input-adapter.js').read_text().splitlines(keepends=True)
    lines[323:323] = ['  commitFakeText(text) {\n', '    return this.commitText(text, { source: "fake" });\n', '  }\n', '\n']
    (fake / 'input-adapter.js').write_text(''.join(lines))
    diff = subprocess.run(['diff', str(project / 'input/input-adapter.js'), str(fake / 'input-adapter.js')], capture_output=True, text=True).stdout
    if diff != FAKE_DIFF.read_text():
        raise SystemExit('the scratch fake input differs from red case (iv)')
    empty = root / 'input-empty'; empty.mkdir()
    runs = {}
    for name, test, directory in (('real-on-fake', T3_TEST, fake), ('guardless-on-real', guardless, project / 'input'),
                                  ('guardless-on-fake', guardless, fake), ('guardless-on-empty', guardless, empty)):
        done = subprocess.run(['node', '--test', '--test-name-pattern', '^T3', str(test)], capture_output=True, text=True,
                              env={**os.environ, 'V24_T3_INPUT_DIR': str(directory)}, cwd=project)
        (root / (name + '.stdout.txt')).write_text(done.stdout + done.stderr)
        runs[name] = done.returncode
        # A name pattern that matches nothing exits 0 too: every run must have run exactly the one T3 test.
        if 'ℹ tests 1\n' not in done.stdout or ('✔ T3:' if done.returncode == 0 else '✖ T3:') not in done.stdout:
            raise SystemExit('T3 run did not execute exactly the T3 test: ' + name)
    checks = [('T3 real test red on (iv)', runs['real-on-fake'] != 0), ('T3 guardless green on (iv): the equality clause is what made it red', runs['guardless-on-fake'] == 0),
              ('T3 guardless green on the real input', runs['guardless-on-real'] == 0), ('T3 guardless still red on an empty directory (non-vacuity)', runs['guardless-on-empty'] != 0)]
    return runs, {'guardlessSha256': digest(guardless.read_bytes()), 'testSha256': digest(T3_TEST.read_bytes())}, checks


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    plan = config(); pages, receipts = cases()
    readers = {'real': (j24, 0, digest(Path(j24.__file__).read_bytes()))}
    for tag in ('T2-route', 'T2-proof'):
        readers['without-' + tag] = mutant(tag, args.out)
    table = {name: {case: read(module, page, plan) for case, page in pages.items()} for name, (module, _, _) in readers.items()}
    checks = []
    def check(label, ok): checks.append({'check': label, 'ok': bool(ok)})
    for case, guards in EXPECT.items():
        got = table['real'][case]
        check(f'real reader, {case}: T2 names exactly {sorted(guards)}', set(got['guards']) == guards)
        check(f'real reader, {case}: verdict ' + ('FAIL' if guards else 'not FAIL by T2'),
              (got['verdict'] == 'FAIL') if guards else got['t2'] == [])
    for tag, guard in (('T2-route', 'route'), ('T2-proof', 'proof')):
        other = 'proof' if guard == 'route' else 'route'
        for case, guards in EXPECT.items():
            got = table['without-' + tag][case]
            check(f'without {tag}, {case}: {guard} no longer named', guard not in got['guards'])
            check(f'without {tag}, {case}: {other} still named iff it was', (other in got['guards']) == (other in guards))
        sole = [c for c, g in EXPECT.items() if g == {guard}]
        check(f'without {tag}: every {guard}-only red ({sole}) stops being FAIL',
              sole and all(table['without-' + tag][c]['verdict'] != 'FAIL' for c in sole))
    t3_runs, t3_receipt, t3_checks = t3_guard_removal(args.out)
    for label, ok in t3_checks: check(label, ok)
    report = {'schema': 1, 'argv': sys.argv, 'inputs': receipts, 't3': {'exits': t3_runs, **t3_receipt},
              'readers': {n: {'linesRemoved': r, 'sha256': s} for n, (_, r, s) in readers.items()},
              'planProfile': plan['profile']['profile'], 'table': table, 'checks': checks,
              'verdict': 'RED_CASES_HOLD' if all(c['ok'] for c in checks) else 'RED_CASES_DO_NOT_HOLD'}
    (args.out / 'j-red.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    for c in checks: print(('ok   ' if c['ok'] else 'FAIL ') + c['check'])
    print(report['verdict'])
    return 0 if report['verdict'] == 'RED_CASES_HOLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
