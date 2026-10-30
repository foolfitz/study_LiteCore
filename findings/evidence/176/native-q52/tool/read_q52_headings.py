#!/usr/bin/env python3
"""Judge amendment 3's cells (../PREDICTION.md, V5) from the records only.

Usage:
  python3 -I read_q52_headings.py OUT_HEADINGS OUT_ACTIONS              V5 + the recorded v27-route cells (JSON)
  python3 -I read_q52_headings.py --self-test OUT_HEADINGS OUT_ACTIONS  the red cases

OUT_ACTIONS is amendment 2's output: heading's A cell is its cl-head-empty-last (the dispatch applied a real Heading
1 there).  Imports read_q52.py (unedited) for extract(), derive(), deciding(), parse() and rule().  The v27-route
cells (route "collapsed") are judged as v27 judges them: rule FIRST on the .uno:SelectText readback.
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
ROUTE_083 = ('cl-nhead-after-realheading', 'cl-body-realheading-last', 'cl-nbody-realheading-last')
PAIRS = {'heading': ('cl-head-empty-last', 'cl-nhead-after-realheading'),
         'body': ('cl-body-realheading-last', 'cl-nbody-realheading-last')}


def saved_at(fodt_gz, index):
    """The saved paragraph at `index` among all text:p/text:h in document order (the mid-document cells' target;
    read_q52.extract reads the LAST one, which is right for the 083 cells only)."""
    import gzip
    import xml.etree.ElementTree as ET
    T = rq.T
    root = ET.fromstring(gzip.decompress(fodt_gz.read_bytes()))
    paragraphs = []

    def walk(node, lists):
        for child in node:
            if child.tag in (T + 'p', T + 'h'):
                paragraphs.append((child, list(lists)))
            walk(child, lists + [child] if child.tag == T + 'list' else lists)
    walk(root.find('office:body/office:text', rq.NS), [])
    if index >= len(paragraphs):
        return {'found': False, 'paragraphs': len(paragraphs)}
    node, lists = paragraphs[index]
    return {'found': True, 'paragraphs': len(paragraphs), 'text': ''.join(node.itertext()), 'inList': bool(lists),
            'listStyle': None, 'listKind': None, 'heading': node.tag == T + 'h',
            'styleName': node.get(T + 'style-name')}


def load(out):
    cells = json.loads((out / 'cells.json').read_text())
    run_log = {}
    for line in (out / 'run-log.jsonl').read_text().splitlines():
        rec = json.loads(line)
        run_log[(rec['cell'], rec['round'])] = rec
    rounds = {}
    for c in cells:
        rs = []
        for r in range(1, ROUNDS + 1):
            s = rq.extract(out, c, r, run_log)
            if s.get('clean'):   # the SelectText readback, kept raw for the v27-route cells and the precondition
                for line in (out / c['name'] / f'r{r}.jsonl').read_text().splitlines():
                    rec = json.loads(line)
                    if rec['rec'] == 'measured':
                        fmt = rec['ops'][0]['format']
                        s['selHtml'] = fmt['html']
                        if fmt['htmlBytes'] != len(fmt['html'].encode('utf-8')):
                            s.update(clean=False, why=s['why'] + ['SelectText markup truncated'])
            if s.get('clean') and isinstance(c['target'], int):
                s['saved'] = saved_at(out / c['name'] / f'r{r}.fodt.gz', c['target'])
            rs.append(s)
        rounds[c['name']] = rs
    return cells, rounds


def derive_all(cells, raw):
    out = {}
    for c in cells:
        rs = []
        for s in raw[c['name']]:
            d = rq.derive(c, s)
            if d.get('clean') and 'selHtml' in d:
                d['FIRST_selecttext'] = rq.rule('FIRST', c['action'], d['selectedType'], d['selHtml'])
                d['selParse'] = rq.parse(d['selHtml']) if d['selectedType'] == TEXT else None
            rs.append(d)
        out[c['name']] = rs
    return out


def judge(cells, rounds, a2_cells, a2_rounds):
    allc = cells + [c for c in a2_cells if c['name'] == 'cl-head-empty-last']
    allr = {**rounds, 'cl-head-empty-last': a2_rounds['cl-head-empty-last']}
    pre = []
    for s in rounds['cl-nbody-realheading-last']:
        if s.get('clean') and (rq.parse(s['fbHtml'])['lastBlockTag'] if s['fbType'] == TEXT else None) != 'h1':
            pre.append(f"cl-nbody-realheading-last r{s['round']}: CL last block is not h1")
    for s in rounds['g-nbody-real-empty-heading-mid']:
        if s.get('clean') and ((s.get('selParse') or {}).get('blockTag')) != 'h1':
            pre.append(f"g-nbody-real-empty-heading-mid r{s['round']}: SelectText first block is not h1")
    recorded = {n: [{'round': s['round'], 'selectedType': s.get('selectedType'),
                     'FIRST': s.get('FIRST_selecttext'), 'matches': s.get('matches'),
                     'first': [(s.get('selParse') or {}).get('listTag') or 'none', (s.get('selParse') or {}).get('blockTag')],
                     'blocks': (s.get('selParse') or {}).get('blockCount'), 'restoredType': s.get('restoredType'),
                     'saved': {k: s['saved'].get(k) for k in ('text', 'inList', 'heading', 'styleName')}
                     if s.get('clean') else None}
                    for s in rounds[n]] for n in rounds if n.startswith('g-')}
    if pre:
        return {'verdict': 'NOT-ESTABLISHED', 'why': 'fixture precondition', 'problems': pre, 'recorded': recorded}
    bad = [f"{n} r{s['round']}" for n in ROUTE_083 for s in rounds[n]
           if s.get('clean') and s['LAST'] == 'satisfied' and not s['matches']]
    if bad:
        return {'verdict': 'LAST-UNSAFE', 'rounds': bad, 'recorded': recorded}
    actions = {}
    for action, (a, n) in PAIRS.items():
        dec = rq.deciding(allc, allr, [a, n])
        ne = {k: v for k, (v, _) in dec.items() if v}
        if ne:
            actions[action] = {'status': 'NOT-ESTABLISHED', 'why': ne}
            continue
        a_ok = all(s['LAST'] == 'satisfied' and s['matches'] and s['P3'] for s in dec[a][1])
        n_ok = all(s['LAST'] != 'satisfied' and not s['matches'] and s['P3'] for s in dec[n][1])
        actions[action] = {'status': 'IN-SCOPE' if a_ok and n_ok else 'OUT-OF-SCOPE', 'applied': a_ok,
                           'negative': n_ok}
    return {'verdict': 'PER-ACTION', 'actions': actions, 'recorded': recorded}


def self_test(cells, raw, a2_cells, a2_rounds):
    cases = []
    H1_LAST = '<html><body><p><br/></p><h1></h1></body></html>'
    P_LAST = '<html><body><p><br/></p><p></p></body></html>'
    H1_MID = '<html><body><h1></h1><p>E1-EMPTY-AFTER</p></body></html>'

    def force(r, cell, html, saved, sel_type=NONE, sel_html=''):
        for s in r[cell]:
            s.update(clean=True, why=[], selectedType=sel_type, selHtml=sel_html, fallbackRan=sel_type == NONE,
                     fbType=TEXT if sel_type == NONE else -1, fbHtml=html if sel_type == NONE else '',
                     restoredType=NONE, locate={'selBefore': '', 'suffix': '', 'prefix': ''},
                     saved={'found': True, 'paragraphs': 2, 'text': '', 'inList': False, 'listStyle': None,
                            'listKind': None, 'heading': saved})

    def base(r):
        force(r, 'cl-nhead-after-realheading', P_LAST, False)
        force(r, 'cl-body-realheading-last', P_LAST, False)
        force(r, 'cl-nbody-realheading-last', H1_LAST, True)
        force(r, 'g-nbody-real-empty-heading-mid', '', True, TEXT, H1_MID)

    def run(name, mutate, check):
        r = copy.deepcopy(raw)
        mutate(r)
        got = judge(cells, derive_all(cells, r), a2_cells, a2_rounds)
        cases.append({'case': name, 'ok': check(got), 'verdict': got['verdict']})

    st = lambda g, a: g.get('actions', {}).get(a, {}).get('status')
    run('forced baseline: heading and body IN-SCOPE', base,
        lambda g: g['verdict'] == 'PER-ACTION' and st(g, 'heading') == st(g, 'body') == 'IN-SCOPE')
    run('precondition: the CL readback of the untouched heading is <p> -> NOT-ESTABLISHED',
        lambda r: (base(r), r['cl-nbody-realheading-last'][1].update(fbHtml=P_LAST)),
        lambda g: g['verdict'] == 'NOT-ESTABLISHED')
    run('precondition: the SelectText first block of the mid heading is <p> -> NOT-ESTABLISHED',
        lambda r: (base(r), r['g-nbody-real-empty-heading-mid'][4].update(
            selHtml='<html><body><p></p><p>E1-EMPTY-AFTER</p></body></html>')),
        lambda g: g['verdict'] == 'NOT-ESTABLISHED')
    run('body applied but saved still a heading while read <p> -> LAST-UNSAFE',
        lambda r: (base(r), r['cl-body-realheading-last'][2]['saved'].update(heading=True)),
        lambda g: g['verdict'] == 'LAST-UNSAFE')
    run('the heading trap read as h1 last with saved not a heading -> LAST-UNSAFE',
        lambda r: (base(r), r['cl-nhead-after-realheading'][0].update(fbHtml=H1_LAST)),
        lambda g: g['verdict'] == 'LAST-UNSAFE')
    run('the body negative saved as text:p but read <h1> -> precondition still holds, body OUT-OF-SCOPE',
        lambda r: (base(r), [s['saved'].update(heading=False) for s in r['cl-nbody-realheading-last']]),
        lambda g: g['verdict'] == 'PER-ACTION' and st(g, 'body') == 'OUT-OF-SCOPE')
    run('the heading negative unclean in one round -> heading NOT-ESTABLISHED',
        lambda r: (base(r), r['cl-nhead-after-realheading'][3].update(clean=False, why=['mutated'])),
        lambda g: st(g, 'heading') == 'NOT-ESTABLISHED' and st(g, 'body') == 'IN-SCOPE')
    cases.append({'case': 'non-vacuous: 6 cells x 5 rounds; the amendment-2 heading A cell has 5 rounds',
                  'ok': len(cells) == 6 and all(len(rs) == ROUNDS for rs in raw.values())
                  and len(a2_rounds['cl-head-empty-last']) == ROUNDS})
    return {'cases': cases, 'result': 'ALL_AS_EXPECTED' if all(c['ok'] for c in cases) else 'UNEXPECTED'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('out_actions', type=pathlib.Path)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    cells, raw = load(a.out)
    a2_cells = json.loads((a.out_actions / 'cells.json').read_text())
    a2_log = {}
    for line in (a.out_actions / 'run-log.jsonl').read_text().splitlines():
        rec = json.loads(line)
        a2_log[(rec['cell'], rec['round'])] = rec
    head = next(c for c in a2_cells if c['name'] == 'cl-head-empty-last')
    a2_rounds = {'cl-head-empty-last': [rq.derive(head, rq.extract(a.out_actions, head, r, a2_log))
                                        for r in range(1, ROUNDS + 1)]}
    if a.self_test:
        result = self_test(cells, raw, a2_cells, a2_rounds)
    else:
        result = {'V5': judge(cells, derive_all(cells, raw), a2_cells, a2_rounds)}
    json.dump(result, sys.stdout, indent=1, ensure_ascii=False)
    print()
    return 0 if not a.self_test or result['result'] == 'ALL_AS_EXPECTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
