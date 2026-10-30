#!/usr/bin/env python3
"""Judge amendment 2's cells (../PREDICTION.md, V4 with correction 1) from the records only.

Usage:
  python3 -I read_q52_actions.py OUT_DIR               V4 per action + the per-cell table (JSON on stdout)
  python3 -I read_q52_actions.py --self-test OUT_DIR   the red cases, built from OUT_DIR's own summaries

Imports read_q52.py (unedited) for extract(), derive() -- the parseFormatReadback port, rule LAST, the saved file's
last paragraph, P0 and P3 -- and table().  Each cell's `action` is the action it is JUDGED AS (the expectation
and the target state); an N cell's dispatch is a different command that should leave that state absent.
Nothing is written.
"""
import argparse
import copy
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('read_q52', HERE / 'read_q52.py')
rq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rq)
ROUNDS, NONE, TEXT = rq.ROUNDS, rq.NONE, rq.TEXT
PAIRS = {'number': ('cl-num-empty-last', 'cl-nnum-after-number'),
         'none': ('cl-none-bulleted-last', 'cl-nnone-noop-bulleted-last'),
         'heading': ('cl-head-empty-last', 'cl-nhead-after-heading'),
         'body': ('cl-body-heading-last', 'cl-nbody-sham-heading-last')}


def judge(cells, rounds):
    bad = [f"{c['name']} r{s['round']}" for c in cells for s in rounds[c['name']]
           if s.get('clean') and s['LAST'] == 'satisfied' and not s['matches']]
    if bad:
        return {'verdict': 'LAST-UNSAFE', 'rounds': bad}
    actions = {}
    for action, (a, n) in PAIRS.items():
        dec = rq.deciding(cells, rounds, [a, n])
        ne = {k: v for k, (v, _) in dec.items() if v}
        if ne:
            actions[action] = {'status': 'NOT-ESTABLISHED', 'why': ne}
            continue
        a_ok = all(s['LAST'] == 'satisfied' and s['matches'] and s['P3'] for s in dec[a][1])
        n_ok = all(s['LAST'] != 'satisfied' and not s['matches'] and s['P3'] for s in dec[n][1])
        actions[action] = {'status': 'IN-SCOPE' if a_ok and n_ok else 'OUT-OF-SCOPE', 'applied': a_ok,
                           'negative': n_ok}
    return {'verdict': 'PER-ACTION', 'actions': actions}


def load(out):
    cells = json.loads((out / 'cells.json').read_text())
    run_log = {}
    for line in (out / 'run-log.jsonl').read_text().splitlines():
        rec = json.loads(line)
        run_log[(rec['cell'], rec['round'])] = rec
    return cells, {c['name']: [rq.derive(c, rq.extract(out, c, r, run_log)) for r in range(1, ROUNDS + 1)]
                   for c in cells}


def self_test(cells, raw):
    by = {c['name']: c for c in cells}
    cases = []
    UL = '<html><body><p></p><ul><li><p></p></li></ul></body></html>'
    OL = '<html><body><p></p><ol><li><p></p></li></ol></body></html>'
    OL_P = '<html><body><ol><li><p>Numbered before</p></li></ol><p></p></body></html>'
    H1_P = '<html><body><h1>Heading before</h1><p></p></body></html>'
    P_H1 = '<html><body><p></p><h1></h1></body></html>'
    P_P = '<html><body><p></p><p></p></body></html>'
    BASE = {  # cell -> (markup, saved overrides): every action IN-SCOPE
        'cl-num-empty-last': (OL, {'inList': True, 'listKind': 'number'}),
        'cl-nnum-after-number': (OL_P, {}),
        'cl-none-bulleted-last': (P_P, {}),
        'cl-nnone-noop-bulleted-last': (UL, {'inList': True, 'listKind': 'bullet'}),
        'cl-head-empty-last': (P_H1, {'heading': True}),
        'cl-nhead-after-heading': (P_P, {}),
        'cl-body-heading-last': (P_P, {}),
        'cl-nbody-sham-heading-last': (P_H1, {'heading': True})}

    def force(r, cell, html, **saved):
        for s in r[cell]:
            s.update(clean=True, why=[], selectedType=NONE, fallbackRan=True, fbType=TEXT, fbHtml=html,
                     restoredType=NONE, locate={'selBefore': '', 'suffix': '', 'prefix': ''},
                     saved={'found': True, 'paragraphs': 2, 'text': '', 'inList': False, 'listStyle': None,
                            'listKind': None, 'heading': False, **saved})

    def base(r):
        for cell, (html, saved) in BASE.items():
            force(r, cell, html, **saved)

    def run(name, mutate, check):
        r = copy.deepcopy(raw)
        mutate(r)
        r = {n: [rq.derive(by[n], s) for s in rs] for n, rs in r.items()}
        got = judge(cells, r)
        cases.append({'case': name, 'ok': check(got), 'got': got})

    def status(got, action):
        return got.get('actions', {}).get(action, {}).get('status')

    run('every action IN-SCOPE from the forced baseline', base,
        lambda g: g['verdict'] == 'PER-ACTION' and all(v['status'] == 'IN-SCOPE' for v in g['actions'].values()))
    run('the number trap read as ol last (FIRST-style) -> LAST-UNSAFE',
        lambda r: (base(r), r['cl-nnum-after-number'][0].update(fbHtml=OL)), lambda g: g['verdict'] == 'LAST-UNSAFE')
    run('the heading trap read as h1 last -> LAST-UNSAFE',
        lambda r: (base(r), r['cl-nhead-after-heading'][2].update(fbHtml=P_H1)),
        lambda g: g['verdict'] == 'LAST-UNSAFE')
    run('an applied heading saved as text:p while read as h1 -> LAST-UNSAFE (A cell)',
        lambda r: (base(r), r['cl-head-empty-last'][1]['saved'].update(heading=False)),
        lambda g: g['verdict'] == 'LAST-UNSAFE')
    run('correction 1: the none negative APPLIED (saved out of a list, read as p) -> none OUT-OF-SCOPE, not UNSAFE',
        lambda r: (base(r), force(r, 'cl-nnone-noop-bulleted-last', P_P)),
        lambda g: g['verdict'] == 'PER-ACTION' and status(g, 'none') == 'OUT-OF-SCOPE')
    run('the body A cell refused in one round -> body OUT-OF-SCOPE',
        lambda r: (base(r), r['cl-body-heading-last'][3].update(fbType=NONE)),
        lambda g: status(g, 'body') == 'OUT-OF-SCOPE' and status(g, 'number') == 'IN-SCOPE')
    run('the number A cell restore not NONE -> number OUT-OF-SCOPE',
        lambda r: (base(r), r['cl-num-empty-last'][4].update(restoredType=TEXT)),
        lambda g: status(g, 'number') == 'OUT-OF-SCOPE')
    run('the heading negative with one unclean round -> heading NOT-ESTABLISHED',
        lambda r: (base(r), r['cl-nhead-after-heading'][0].update(clean=False, why=['mutated'])),
        lambda g: status(g, 'heading') == 'NOT-ESTABLISHED')
    run('the none A cell SelectText read TEXT (not the 083 path) -> none NOT-ESTABLISHED',
        lambda r: (base(r), r['cl-none-bulleted-last'][1].update(selectedType=TEXT)),
        lambda g: status(g, 'none') == 'NOT-ESTABLISHED')
    cases.append({'case': 'non-vacuous: 8 cells x 5 rounds, the four pairs present',
                  'ok': len(cells) == 8 and all(len(rs) == ROUNDS for rs in raw.values())
                  and all(n in raw for pair in PAIRS.values() for n in pair)})
    for c in cases:
        if c['ok']:
            c.pop('got', None)
    return {'cases': cases, 'result': 'ALL_AS_EXPECTED' if all(c['ok'] for c in cases) else 'UNEXPECTED'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    cells, rounds = load(a.out)
    if a.self_test:
        raw = {n: [{k: v for k, v in s.items() if k not in ('P0', 'P3', 'parse', 'ONE', 'LAST', 'FIRST', 'matches')}
                   for s in rs] for n, rs in rounds.items()}
        result = self_test(cells, raw)
    else:
        result = {'V4': judge(cells, rounds), 'cells': rq.table(cells, rounds)}
    json.dump(result, sys.stdout, indent=1, ensure_ascii=False)
    print()
    return 0 if not a.self_test or result['result'] == 'ALL_AS_EXPECTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
