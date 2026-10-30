#!/usr/bin/env python3
"""Judge amendment 4's cells (../PREDICTION.md: V6 number/none, V7 the long document and two empties at the end).

Usage:
  python3 -I read_q52_v6.py OUT_V6               V6 + V7 + the per-cell table (JSON on stdout)
  python3 -I read_q52_v6.py --self-test OUT_V6   the red cases, built from OUT_V6's own summaries

Imports read_q52.py (extract, derive, deciding, parse, table) and read_q52_headings.py (saved_at, for the saved
second-to-last paragraph), both unedited.  Nothing is written.
"""
import argparse
import copy
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rq, rh = _load('read_q52'), _load('read_q52_headings')
ROUNDS, NONE, TEXT = rq.ROUNDS, rq.NONE, rq.TEXT
V6_PAIRS = {'number': ('cl-num-empty-last', 'cl-nnum-after-number'),
            'none': ('cl-none-bulleted-last', 'cl-nnone-noop-bulleted-last')}


def load(out):
    cells = json.loads((out / 'cells.json').read_text())
    run_log = {}
    for line in (out / 'run-log.jsonl').read_text().splitlines():
        rec = json.loads(line)
        run_log[(rec['cell'], rec['round'])] = rec
    raw = {}
    for c in cells:
        rs = []
        for r in range(1, ROUNDS + 1):
            s = rq.extract(out, c, r, run_log)
            if s.get('clean'):
                s['savedPrev'] = rh.saved_at(out / c['name'] / f'r{r}.fodt.gz', -2)
            rs.append(s)
        raw[c['name']] = rs
    return cells, raw


def derive(cells, raw):
    by = {c['name']: c for c in cells}
    out = {}
    for n, rs in raw.items():
        d = []
        for s in rs:
            x = rq.derive(by[n], s)
            if x.get('clean'):
                x['blocks'] = rq.parse(x['fbHtml'])['blockCount'] if x['fbType'] == TEXT else None
            d.append(x)
        out[n] = d
    return out


def judge(cells, rounds):
    res = {}
    # V6
    names6 = [n for pair in V6_PAIRS.values() for n in pair]
    bad = [f"{n} r{s['round']}" for n in names6 for s in rounds[n]
           if s.get('clean') and s['LAST'] == 'satisfied' and not s['matches']]
    if bad:
        res['V6'] = {'verdict': 'LAST-UNSAFE', 'rounds': bad}
    else:
        actions = {}
        for action, (a, n) in V6_PAIRS.items():
            dec = rq.deciding(cells, rounds, [a, n])
            ne = {k: v for k, (v, _) in dec.items() if v}
            if ne:
                actions[action] = {'status': 'NOT-ESTABLISHED', 'why': ne}
                continue
            a_ok = all(s['LAST'] == 'satisfied' and s['matches'] and s['P3'] for s in dec[a][1])
            n_ok = all(s['LAST'] != 'satisfied' and not s['matches'] and s['P3'] for s in dec[n][1])
            actions[action] = {'status': 'IN-SCOPE' if a_ok and n_ok else 'OUT-OF-SCOPE', 'applied': a_ok,
                               'negative': n_ok}
        res['V6'] = {'verdict': 'PER-ACTION', 'actions': actions}
    # V7
    names7 = ['cl-long-300', 'cl-a6-end', 'cl-n6-end']
    bad = [f"{n} r{s['round']}" for n in names7 for s in rounds[n]
           if s.get('clean') and s['LAST'] == 'satisfied' and not s['matches']]
    dec = rq.deciding(cells, rounds, names7)
    if bad:
        res['V7'] = {'verdict': 'V7-UNSAFE', 'rounds': bad}
    elif any(v for v, _ in dec.values()):
        res['V7'] = {'verdict': 'NOT-ESTABLISHED', 'why': {k: v for k, (v, _) in dec.items() if v}}
    else:
        def covered(s, prev_out_of_list=False):
            return (s['fbType'] == TEXT and s['blocks'] == 2 and s['LAST'] == 'satisfied' and s['matches']
                    and (not prev_out_of_list or not s['savedPrev'].get('inList')))
        cls = {'cl-long-300': all(covered(s) and s['P3'] for s in dec['cl-long-300'][1]),
               'cl-a6-end': all(covered(s, True) and s['restoredType'] == NONE for s in dec['cl-a6-end'][1]),
               'cl-n6-end': all(s['LAST'] != 'satisfied' and not s['saved'].get('inList')
                                and not s['savedPrev'].get('inList') and s['restoredType'] == NONE
                                for s in dec['cl-n6-end'][1])}
        res['V7'] = {'verdict': 'V7-HOLDS' if all(cls.values()) else 'V7-PARTIAL', 'cells': cls,
                     'longFallbackBytes': sorted({s['fbHtmlBytes'] for s in dec['cl-long-300'][1]}),
                     'a6Locator': sorted({json.dumps(s['locate']) for s in dec['cl-a6-end'][1]})}
    return res


def self_test(cells, raw):
    cases = []
    TWO_UL = '<html><body><p><br/></p><ul><li><p></p></li></ul></body></html>'
    TWO_OL = '<html><body><p><br/></p><ol><li><p></p></li></ol></body></html>'
    TWO_P = '<html><body><p><br/></p><p></p></body></html>'
    OL_P = '<html><body><ol><li><p></p></li></ol><p></p></body></html>'

    def force(r, cell, html, in_list=False, kind=None, prev_in_list=False):
        for s in r[cell]:
            s.update(clean=True, why=[], selectedType=NONE, fallbackRan=True, fbType=TEXT, fbHtml=html,
                     restoredType=NONE, locate={'selBefore': '', 'suffix': '', 'prefix': ''},
                     saved={'found': True, 'paragraphs': 3, 'text': '', 'inList': in_list, 'listStyle': None,
                            'listKind': kind, 'heading': False},
                     savedPrev={'found': True, 'inList': prev_in_list, 'heading': False})

    def base(r):
        force(r, 'cl-num-empty-last', TWO_OL, True, 'number')
        force(r, 'cl-nnum-after-number', OL_P)
        force(r, 'cl-none-bulleted-last', TWO_P)
        force(r, 'cl-nnone-noop-bulleted-last', TWO_UL, True, 'bullet')
        force(r, 'cl-long-300', TWO_UL, True, 'bullet')
        force(r, 'cl-a6-end', TWO_UL, True, 'bullet')
        force(r, 'cl-n6-end', TWO_P)

    def run(name, mutate, check):
        r = copy.deepcopy(raw)
        mutate(r)
        got = judge(cells, derive(cells, r))
        cases.append({'case': name, 'ok': check(got), 'got': {k: v.get('verdict') for k, v in got.items()}})

    st = lambda g, a: g['V6'].get('actions', {}).get(a, {}).get('status')
    run('forced baseline: V6 both IN-SCOPE, V7 HOLDS', base,
        lambda g: st(g, 'number') == st(g, 'none') == 'IN-SCOPE' and g['V7']['verdict'] == 'V7-HOLDS')
    run('V6: the number trap read with ol last while saved out of a list -> LAST-UNSAFE',
        lambda r: (base(r), r['cl-nnum-after-number'][0].update(fbHtml=TWO_OL)),
        lambda g: g['V6']['verdict'] == 'LAST-UNSAFE' and g['V7']['verdict'] == 'V7-HOLDS')
    run('V6: the none negative applied (saved out of a list) -> none OUT-OF-SCOPE',
        lambda r: (base(r), force(r, 'cl-nnone-noop-bulleted-last', TWO_P)),
        lambda g: st(g, 'none') == 'OUT-OF-SCOPE' and st(g, 'number') == 'IN-SCOPE')
    run('V6: one unclean number round -> number NOT-ESTABLISHED',
        lambda r: (base(r), r['cl-num-empty-last'][2].update(clean=False, why=['mutated'])),
        lambda g: st(g, 'number') == 'NOT-ESTABLISHED')
    run('V7: the long document reads three blocks -> V7-PARTIAL (blockCount == 2 required)',
        lambda r: (base(r), r['cl-long-300'][1].update(
            fbHtml='<html><body><p>a</p><p><br/></p><ul><li><p></p></li></ul></body></html>')),
        lambda g: g['V7']['verdict'] == 'V7-PARTIAL')
    run('V7: the long document reads COMPLEX -> V7-PARTIAL',
        lambda r: (base(r), r['cl-long-300'][3].update(fbType=3)), lambda g: g['V7']['verdict'] == 'V7-PARTIAL')
    run('V7: a6 bullets the second-to-last paragraph too -> V7-PARTIAL',
        lambda r: (base(r), r['cl-a6-end'][4]['savedPrev'].update(inList=True)),
        lambda g: g['V7']['verdict'] == 'V7-PARTIAL')
    run('V7: the n6 sham read with ul last while saved out of a list -> V7-UNSAFE',
        lambda r: (base(r), r['cl-n6-end'][0].update(fbHtml=TWO_UL)), lambda g: g['V7']['verdict'] == 'V7-UNSAFE')
    run('V7: a6 restore not NONE -> V7-PARTIAL',
        lambda r: (base(r), r['cl-a6-end'][0].update(restoredType=TEXT)), lambda g: g['V7']['verdict'] == 'V7-PARTIAL')
    run('V7: a6 SelectText read TEXT (not the 083 path) -> NOT-ESTABLISHED',
        lambda r: (base(r), r['cl-a6-end'][2].update(selectedType=TEXT)),
        lambda g: g['V7']['verdict'] == 'NOT-ESTABLISHED')
    cases.append({'case': 'non-vacuous: 7 cells x 5 rounds', 'ok': len(cells) == 7
                  and all(len(rs) == ROUNDS for rs in raw.values())})
    for c in cases:
        if c['ok']:
            c.pop('got', None)
    return {'cases': cases, 'result': 'ALL_AS_EXPECTED' if all(c['ok'] for c in cases) else 'UNEXPECTED'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    cells, raw = load(a.out)
    if a.self_test:
        result = self_test(cells, raw)
    else:
        rounds = derive(cells, raw)
        result = {**judge(cells, rounds), 'cells': rq.table(cells, rounds)}
    json.dump(result, sys.stdout, indent=1, ensure_ascii=False)
    print()
    return 0 if not a.self_test or result['result'] == 'ALL_AS_EXPECTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
