#!/usr/bin/env python3
"""ST2 and ST3 of SPEC-M3-own-stack, read from the recorded reports: every cell against the ddev shakedown, every difference
named.  Read-only; it does not reach the host.

  read_st2.py            write reading.json next to this file, exit 0 iff ST2_ST3_HOLD
  read_st2.py --self-test     every mutation must turn the reading red

A cell is the runner's own `pass/runs` plus its own failure text.  What may differ is a closed table below, each row with the
reason; a difference outside it is `unexplained` and the reading is red.

The runners pin the page against the TREE, and the tree moved to v29 before the cutover while the host stayed on 0.2.44.  So one
top-level problem is expected everywhere, `page {...}`, and it is only accepted when the report's own host files equal the
baseline's: the host did not move.  `assets` derives more from the tree (the closure, the dist hashes); there the tree half is
transplanted from the baseline and the runner's own score() decides.
"""
import argparse
import copy
import importlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[4]
EV = ROOT / 'findings/evidence'
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))

FIRST = EV / 'k-0.2.44/first-contact'
PAIRS = {
    'host_entry': ('m3-host-entry/shakedown/2026-11-01T112919Z.json', 'm3-host-entry/shakedown/2026-10-31T152248Z.json'),
    'page_honesty': ('m3-page-honesty/shakedown/2026-11-01T113134+0000.json', 'm3-page-honesty/shakedown/2026-10-31T055630+0000.json'),
    'locks': ('m3-locks/shakedown/2026-11-01T115308+0000.json', 'm3-locks/shakedown/2026-10-31T061758+0000.json'),
    'versions': ('m3-versions/shakedown/2026-11-01T122850+0000.json', 'm3-versions/shakedown/2026-10-31T065336+0000.json'),
    'same_second': ('m3-same-second/shakedown/2026-11-01T123017+0000.json', 'm3-same-second/shakedown/2026-10-31T152501+0000.json'),
    'new_document': ('new-document/shakedown/2026-11-01T131532Z.json', 'new-document/shakedown/2026-10-31T152855Z.json'),
    'production_ui': ('own-stack/st2/production-ui.json', 'k-0.2.44/first-contact/production-ui.json'),
}
ASSETS = ('m3-assets/shakedown/2026-11-01T112717+0000.json', 'm3-assets/shakedown/2026-10-31T152043+0000.json')

# (runner, cell): why the cell may differ.  Closed; filled from the reading, each row checked against the evidence it names.
EXPLAINED = {
    # Accepted only while check_foreign_phase() below finds what this says.
    ('same_second', 'chrome:same-second-foreign'):
        "the instrument, not the stack: the baseline pressed at phase .05, on v28 X crossed S1's second (`premise`). 3d78bd5c6, "
        'after the baseline, set FOREIGN_PHASE to 0.60 (SPEC-M3-K-0.2.44 append 2), not re-run until here',
    ('same_second', 'firefox:same-second-foreign'): 'as chrome:same-second-foreign',
    # Accepted only while check_p_arm() below finds what this says.
    ('production_ui', 'P/chrome'):
        "the instrument, not the stack: the baseline's one failure is A3-1 on button[paste-markdown], and 4c4e7b639 (after the "
        'baseline) added paste-markdown to KEEP_ACTIONS (SPEC-M3-K-0.2.44 append 3)',
    ('production_ui', 'P/firefox'): 'as P/chrome',
}


def report(name):
    return json.loads((EV / name).read_text())


def cells_of(runner, doc):
    """{cell: [pass, runs, failures]}, by the runner's own recorded score."""
    score = doc.get('score') or {}
    if runner == 'host_entry':
        return {'browsers': score.get('browsers'), 'lands': score.get('lands')}
    if runner == 'new_document':
        return {'runs': score.get('runs'), 'works': score.get('works')}
    table = score.get('tally') or score.get('cells') or {}
    return {k: [v.get('pass'), v.get('runs'), v.get('problems', v.get('failures'))] for k, v in table.items()}


def autosave_cells(text):
    rows = re.findall(r'^(as\S+/\S+)\s+(\S+)\s+pass (\d+)/(\d+)', text, flags=re.M)
    return {cell: [word, int(p), int(r)] for cell, word, p, r in rows}


def check_foreign_phase(new, old):
    """The same_second rows of EXPLAINED: the press really moved, and the baseline's red really is the premise."""
    def phases(doc):
        return [round(r['pressedAt'] % 1, 1) for r in doc['runs'] if r.get('arm') == 'same-second-foreign']
    tally = (old.get('score') or {}).get('tally') or {}
    premise = all(tally[c]['problems'] and tally[c]['problems'][0][0].startswith('premise:') for c in ('chrome:same-second-foreign', 'firefox:same-second-foreign'))
    near = lambda rows, want: bool(rows) and all(abs(p - want) <= 0.1 for p in rows)  # noqa: E731
    return premise and near(phases(old), 0.05) and near(phases(new), 0.6) and new.get('runnerSha256') != old.get('runnerSha256')


def check_p_arm(new, old):
    """The P rows of EXPLAINED: the runner did change between the two reports, and the baseline's only failure is that entry."""
    cells = (old.get('score') or {}).get('cells') or {}
    only = all(len(cells[c]['failures']) == 1 and len(cells[c]['failures'][0]) == 1 and 'button[paste-markdown]' in cells[c]['failures'][0][0]
               and cells[c]['failures'][0][0].startswith('A3-1:') for c in ('P/chrome', 'P/firefox'))
    return only and new.get('runnerSha256') != old.get('runnerSha256')


def as5_shape(text):
    """AS-5's red is the same product behaviour when the same number of letters survives; which ones is a matter of timing."""
    held = re.findall(r"AS-5: 20 letters typed during the save, the server holds '([a-z]*)'", text)
    return sorted(len(h) for h in held)


def page_problem_only(doc, base):
    """The one accepted top-level problem: the tree's page, on a host that did not move."""
    problems = list((doc.get('score') or {}).get('problems') or [])
    moved = [p for p in problems if not p.startswith("page {'dist': '022d0cd0")]
    same_host = doc.get('hostFiles') == base.get('hostFiles') and doc.get('hostRepo') == base.get('hostRepo')
    return moved, same_host


def read_assets(new, old):
    """The runner's score() on the report with the tree half replaced by the baseline's; a control that must stay red."""
    m = importlib.import_module('check_m3_' + 'assets')
    c = copy.deepcopy(new)
    c['static']['page'] = old['static']['page']
    for key in ('derived', 'pageFiles', 'noCacheFetches'):
        c['package'][key] = old['package'][key]
    for path, seen in c['package']['files'].items():
        seen['distSha256'] = old['package']['files'][path]['distSha256']
    host_half = {k: [new['package']['files'][p][k] == old['package']['files'][p][k] for p in old['package']['files']]
                 for k in ('decodedSha256', 'gzSha256', 'zstSha256')}
    scored = m.score(c, strict=False)
    control = copy.deepcopy(c)
    control['package']['files'][next(iter(control['package']['files']))]['decodedSha256'] = '0' * 64
    return {'verdict': scored['verdict'], 'tally': scored['tally'], 'problems': scored.get('problems'),
            'hostHalfEqualsBaseline': all(all(v) for v in host_half.values()), 'manifestEqual': new['package']['manifest'] == old['package']['manifest'],
            'wireAddressEqual': new['wire']['address'] == old['wire']['address'],
            'controlStaysRed': m.score(control, strict=False)['verdict'] != 'clean'}


def collect():
    return {'pairs': {r: (report(n), report(o)) for r, (n, o) in PAIRS.items()},
            'autosave': ((HERE / 'autosave.stdout.txt').read_text(), (FIRST / 'autosave.stdout.txt').read_text()),
            'files': (json.loads((HERE / 'files-workflow/report.json').read_text()),
                      json.loads((EV / 'host-0.2.44/files-workflow-01/report.json').read_text())),
            'assets': read_assets(report(ASSETS[0]), report(ASSETS[1]))}


def read(inputs):
    problems, differences = [], []

    def compare(runner, new, old):
        if not new or not old:
            problems.append(f'{runner}: no cells (new {len(new)}, baseline {len(old)})')
        if set(new) != set(old):
            problems.append(f'{runner}: cell sets differ {sorted(set(new) ^ set(old))}')
        for cell in sorted(set(new) & set(old)):
            if new[cell] != old[cell]:
                row = {'runner': runner, 'cell': cell, 'new': new[cell], 'baseline': old[cell]}
                row['reason'] = EXPLAINED.get((runner, cell))
                differences.append(row)

    for runner, (new, old) in inputs['pairs'].items():
        compare(runner, cells_of(runner, new), cells_of(runner, old))
        if runner in ('locks', 'versions', 'same_second'):
            moved, same_host = page_problem_only(new, old)
            if moved or not same_host:
                problems.append(f'{runner}: problems beyond the tree page {moved}, host unchanged {same_host}')
    compare('autosave', *(autosave_cells(t) for t in inputs['autosave']))
    as5 = {'new': as5_shape(inputs['autosave'][0]), 'baseline': as5_shape(inputs['autosave'][1])}
    if not as5['new'] or as5['new'] != as5['baseline']:
        problems.append(f'autosave: AS-5 is not the same red {as5}')
    if not check_foreign_phase(*inputs['pairs']['same_second']):
        for row in differences:
            if row['runner'] == 'same_second':
                row['reason'] = None
    if not check_p_arm(*inputs['pairs']['production_ui']):
        for row in differences:
            if row['runner'] == 'production_ui' and row['cell'].startswith('P/'):
                row['reason'] = None
    new_files, old_files = inputs['files']
    ids = lambda r: sorted(c['id'] for c in r['checks'])  # noqa: E731
    files = {'ok': new_files.get('ok'), 'checks': len(new_files.get('checks', [])), 'failed': [c['id'] for c in new_files.get('checks', []) if not c['ok']],
             'sameCheckIds': ids(new_files) == ids(old_files)}
    if files != {'ok': True, 'checks': 52, 'failed': [], 'sameCheckIds': True}:
        problems.append(f'ST3: {files}')
    assets = inputs['assets']
    if assets['verdict'] != 'clean' or not (assets['hostHalfEqualsBaseline'] and assets['manifestEqual'] and assets['wireAddressEqual'] and assets['controlStaysRed']):
        problems.append(f'assets: {assets}')
    unexplained = [d for d in differences if not d['reason']]
    # A table row that no difference used is stale: it would excuse a cell that has not moved.
    used = {(d['runner'], d['cell']) for d in differences}
    stale = [list(k) for k in EXPLAINED if k not in used]
    verdict = 'ST2_ST3_HOLD' if not (problems or unexplained or stale) else 'ST2_ST3_DIFFERS'
    return {'verdict': verdict, 'problems': problems, 'unexplained': unexplained, 'staleExplanations': stale,
            'differences': differences, 'as5': as5, 'assets': {k: v for k, v in assets.items() if k != 'tally'}, 'st3': files,
            'runners': sorted(inputs['pairs']) + ['assets', 'autosave']}


def self_test(inputs):
    def flip(i):
        table = i['pairs']['locks'][0]['score']['tally']
        table[next(iter(table))]['pass'] = 0

    def extra_problem(i):
        i['pairs']['versions'][0]['score']['problems'].append('a new top-level problem')

    def host_moved(i):
        i['pairs']['versions'][0]['hostFiles'] = {'js/x.js': '0' * 64}

    def no_cells(i):
        i['pairs']['locks'][0]['score']['tally'] = {}
        i['pairs']['locks'][1]['score']['tally'] = {}

    def lost_cell(i):
        del i['pairs']['production_ui'][0]['score']['cells']['S/chrome']

    def autosave_moved(i):
        i['autosave'] = (i['autosave'][0].replace('PASS', 'FAIL', 1).replace('pass 1/1', 'pass 0/1', 1), i['autosave'][1])

    def files_failed(i):
        i['files'][0]['checks'][0]['ok'] = False

    def assets_red(i):
        i['assets']['verdict'] = 'red'

    def as5_other_shape(i):
        i['autosave'] = (i['autosave'][0].replace("holds 'abcdefghijklmoprstu'", "holds 'abc'"), i['autosave'][1])

    def as5_gone(i):
        i['autosave'] = (i['autosave'][0].replace('AS-5:', 'AS-X:'), i['autosave'][1])

    def phase_never_moved(i):
        for r in i['pairs']['same_second'][0]['runs']:
            if r.get('arm') == 'same-second-foreign':
                r['pressedAt'] = int(r['pressedAt']) + 0.05

    def p_same_runner(i):
        i['pairs']['production_ui'][0]['runnerSha256'] = i['pairs']['production_ui'][1]['runnerSha256']

    def p_other_failure(i):
        i['pairs']['production_ui'][1]['score']['cells']['P/chrome']['failures'] = [['A3-2: something else']]

    def stale_row(i):
        new, old = i['pairs']['same_second']
        old['score']['tally'] = copy.deepcopy(new['score']['tally'])

    results = {}
    for fn in (flip, extra_problem, host_moved, no_cells, lost_cell, autosave_moved, files_failed, assets_red, stale_row,
               as5_other_shape, as5_gone, p_same_runner, p_other_failure, phase_never_moved):
        mutated = copy.deepcopy(inputs)
        fn(mutated)
        results[fn.__name__] = read(mutated)['verdict'] != 'ST2_ST3_HOLD'
    return {'selfTest': 'ALL_RED' if all(results.values()) else 'SOME_HELD', 'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    inputs = collect()
    if args.self_test:
        result = self_test(inputs)
        print(json.dumps(result, indent=1))
        return 0 if result['selfTest'] == 'ALL_RED' else 1
    result = read(inputs)
    (HERE / 'reading.json').write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: result[k] for k in ('verdict', 'problems', 'unexplained', 'staleExplanations')}, indent=1, ensure_ascii=False)[:6000])
    return 0 if result['verdict'] == 'ST2_ST3_HOLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
