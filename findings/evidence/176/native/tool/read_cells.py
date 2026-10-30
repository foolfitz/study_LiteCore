#!/usr/bin/env python3
"""Judge finding 176's native cells (engine item C) against ../PREDICTION.md, from the records only.

Usage:
  python3 -I read_cells.py OUT_DIR                 verdict + the per-cell table (JSON on stdout)
  python3 -I read_cells.py --self-test OUT_DIR     the red cases, built from OUT_DIR's own summaries

Per round (extract): clean or not, and why; the op's callbacks split by index into during-the-call, before the
first poll (on time) and late; the `.uno:DefaultBullet` items on time and late; the readback's block count and
whether its first block is in a <ul>; the selection types; the undo stack before and after; the saved target
paragraph (in a list or not, the list style's kind, heading or not).  Then judge() applies P0-P2 and the verdict
rules exactly as registered.  Nothing is written.
"""
import argparse
import copy
import gzip
import json
import pathlib
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

NS = {'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
      'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
      'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0'}
T = '{%s}' % NS['text']
ROUNDS = 5
BULLET = '.uno:DefaultBullet='
STATE = 'LOK_CALLBACK_STATE_CHANGED'


def saved_target(fodt_gz, index):
    root = ET.fromstring(gzip.decompress(fodt_gz.read_bytes()))
    kinds = {}
    for ls in root.iter(T + 'list-style'):
        name = ls.get('{%s}name' % NS['style'])
        first = next(iter(ls), None)
        kinds[name] = ('bullet' if first is not None and first.tag == T + 'list-level-style-bullet'
                       else 'number' if first is not None and first.tag == T + 'list-level-style-number' else '?')
    body = root.find('office:body/office:text', NS)
    paragraphs = []

    def walk(node, lists):
        for child in node:
            if child.tag in (T + 'p', T + 'h'):
                paragraphs.append((child, list(lists)))
            elif child.tag == T + 'list':
                walk(child, lists + [child])
            elif child.tag in (T + 'list-item', T + 'list-header', T + 'section'):
                walk(child, lists)
    walk(body, [])
    if index >= len(paragraphs):
        return {'found': False, 'paragraphs': len(paragraphs)}
    node, lists = paragraphs[index]
    style = next((x.get(T + 'style-name') for x in lists if x.get(T + 'style-name')), None)
    return {'found': True, 'paragraphs': len(paragraphs), 'text': ''.join(node.itertext()),
            'inList': bool(lists), 'listStyle': style, 'listKind': kinds.get(style) if style else None,
            'heading': node.tag == T + 'h'}


def undo_actions(payload):
    try:
        actions = json.loads(payload).get('actions')
    except (ValueError, AttributeError):
        return None
    return [a.get('comment') for a in actions] if isinstance(actions, list) else []


STRUCTURAL = ('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li')


def readback(html):
    body = html.split('<body', 1)[1] if '<body' in html else ''
    blocks = [m.start() for m in re.finditer(r'<(p|h[1-6])[\s>]', body)]
    ul = body.find('<ul')
    # RECORDED, not pre-registered: the two fields the engine's parseFormatReadback derives from the FIRST
    # structural tags (listTag = the first one if it is ul/ol; blockTag = the first block tag), which
    # formatBarrierReadbackSatisfied reads -- i.e. what the existing predicate says about the first block.
    tags = [t.lower() for t in re.findall(r'<([A-Za-z0-9]+)', body.split('>', 1)[1] if '>' in body else '')
            if t.lower() in STRUCTURAL]
    return {'blocks': len(blocks), 'firstBlockInUl': bool(blocks) and ul != -1 and ul < blocks[0],
            'parserListTag': (tags[0] if tags and tags[0] in ('ul', 'ol') else 'none') if tags else None,
            'parserBlockTag': next((t for t in tags if t == 'p' or t[0] == 'h'), None)}


def first_block_agrees(s):
    """Recorded: does the parser's first-block state equal the saved dispatch paragraph's state?"""
    saved = s['saved']
    want_list = {'bullet': 'ul', 'number': 'ol'}.get(saved.get('listKind'), 'none') if saved.get('inList') else 'none'
    want_block = 'h1' if saved.get('heading') else 'p'
    return s.get('parserListTag') == want_list and s.get('parserBlockTag') == want_block


def extract(out, cell, r, run_log):
    why = []
    path = out / cell['name'] / f'r{r}.jsonl'
    if not path.exists():
        return {'round': r, 'clean': False, 'why': ['no record']}
    recs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    by = {}
    for rec in recs:
        by.setdefault(rec['rec'], []).append(rec)
    log = run_log.get((cell['name'], r))
    if not log or log.get('exit') != 0:
        why.append(f"exit {log and log.get('exit')}")
    if 'done' not in by:
        why.append('no done record')
    if 'fatal' in by:
        why.append('fatal: ' + by['fatal'][0].get('what', ''))
    env = (by.get('env') or [{}])[0]
    if env.get('SAL_LOK_OPTIONS') != 'unipoll' or env.get('mode') != 'uni1ai':
        why.append(f"env {env.get('mode')} {env.get('SAL_LOK_OPTIONS')}")
    if not (by.get('init') or [{}])[0].get('anyInputRegistered'):
        why.append('anyInput not registered')
    measured = (by.get('measured') or [None])[0]
    if not measured:
        return {'round': r, 'clean': False, 'why': why + ['no measured record']}
    if measured.get('capped'):
        why.append('capped settle')
    if not (by.get('saved') or [{}])[0].get('ok'):
        why.append('not saved')
    op = (measured.get('ops') or [None])[0]
    if not op:
        return {'round': r, 'clean': False, 'why': why + ['no op record']}
    fmt = op.get('format')
    if op['op'][0] in 'FG' and not fmt:
        why.append('format record missing')
    # the op's window, by index: on time = [cbIndexAtStart, cbIndexAtFirstPoll), aligned in the measured list at
    # its first callback at or after the op's start, then checked against the index-based late list
    n_on = op['cbIndexAtFirstPoll'] - op['cbIndexAtStart']
    n_during = op['cbIndexAtReturn'] - op['cbIndexAtStart']
    cbs = measured['callbacks']
    j = next((i for i, c in enumerate(cbs) if c['t'] >= op['startMs']), len(cbs))
    on_time, late = cbs[j:j + n_on], op.get('lateCallbacks') or []
    # (no clock check: `returnedMs` is taken before the op's own reads at return, the first poll after them)
    if len(on_time) != n_on:
        why.append('on-time window does not align')
    if late and (j + n_on >= len(cbs) or (cbs[j + n_on]['type'], cbs[j + n_on]['payload'])
                 != (late[0]['type'], late[0]['payload'])):
        why.append('late list does not continue the on-time window')
    bullets_on = [c['payload'][len(BULLET):] for c in on_time if c['type'] == STATE and c['payload'].startswith(BULLET)]
    bullets_late = [c['payload'][len(BULLET):] for c in late if c['type'] == STATE and c['payload'].startswith(BULLET)]
    keys_on = sorted({c['payload'].split('=', 1)[0] for c in on_time if c['type'] == STATE})
    keys_late = sorted({c['payload'].split('=', 1)[0] for c in late if c['type'] == STATE})
    gz = out / cell['name'] / f'r{r}.fodt.gz'
    target = saved_target(gz, cell['target']) if gz.exists() else {'found': False}
    if not target.get('found'):
        why.append('target paragraph not found in the saved file')
    summary = {'round': r, 'clean': not why, 'why': why, 'nDuring': n_during, 'nOnTime': n_on,
               'bulletOnTime': bullets_on, 'bulletLate': bullets_late, 'stateKeysOnTime': keys_on,
               'stateKeysLate': keys_late, 'saved': target,
               'undoAfter': undo_actions(op['atReturn']['undo'])}
    if fmt:
        summary.update({'selectedType': fmt['selectedType'], 'restoredType': fmt['restoredType'],
                        'selectedText': fmt['selectedText'], **readback(fmt['html']),
                        'undoBefore': undo_actions(fmt.get('undoAtStart', ''))})
    return summary


def p0(cell, s):
    name = cell['name']
    if name.startswith('a1'):
        return s.get('selectedType') == 1 and s.get('blocks') == 1
    if name.startswith(('a2', 'a3')):
        return s.get('selectedType') == 1 and s.get('blocks', 0) >= 2
    if name.startswith(('a4', 'a5')):
        return s.get('selectedType') == 0
    return True


def p1(s):
    return (s['saved'].get('inList') and s['saved'].get('listKind') == 'bullet'
            and bool(s['bulletOnTime']) and s['bulletOnTime'][-1] == 'true')


def p2(s):
    return not s['saved'].get('inList') and 'true' not in s['bulletOnTime']


def judge(cells, summaries):
    problems, ne, p1_fail = [], [], []
    for cell in cells:
        if cell['class'] not in ('A', 'N'):
            continue
        rounds = summaries[cell['name']]
        clean = [s for s in rounds if s['clean']]
        if len(clean) < ROUNDS:
            ne.append(f"{cell['name']}: {len(clean)}/{ROUNDS} clean")
            continue
        if not all(p0(cell, s) for s in clean):
            ne.append(f"{cell['name']}: P0 fails (not the browser's cell)")
            continue
        if cell['class'] == 'A':
            bad = [s['round'] for s in clean if not p1(s)]
            if bad:
                p1_fail.append(cell['name'])
                problems.append(f"{cell['name']}: P1 fails in rounds {bad}")
        else:
            bad = [s['round'] for s in clean if not p2(s)]
            if bad:
                problems.append(f"{cell['name']}: P2 FAILS in rounds {bad}")
    if any('P2 FAILS' in p for p in problems) or any(c.startswith(('a1', 'a2', 'a3')) for c in p1_fail):
        verdict = 'WITNESS-FAILS'
    elif ne:
        verdict = 'NOT-ESTABLISHED'
    elif p1_fail:
        verdict = 'WITNESS-HOLDS-MID-ONLY'
    else:
        verdict = 'WITNESS-HOLDS'
    return verdict, problems + ne


def table(cells, summaries):
    rows = []
    for cell in cells:
        rounds = summaries[cell['name']]

        def distinct(key):
            return sorted({json.dumps(s.get(key), ensure_ascii=False) for s in rounds if s['clean']})
        rows.append({'cell': cell['name'], 'class': cell['class'],
                     'clean': sum(s['clean'] for s in rounds), 'why': sorted({w for s in rounds for w in s['why']}),
                     'saved': distinct('saved'), 'bulletOnTime': distinct('bulletOnTime'),
                     'bulletLate': distinct('bulletLate'), 'nDuring': distinct('nDuring'),
                     'selectedType': distinct('selectedType'), 'blocks': distinct('blocks'),
                     'firstBlockInUl': distinct('firstBlockInUl'), 'restoredType': distinct('restoredType'),
                     'undoBefore': distinct('undoBefore'), 'undoAfter': distinct('undoAfter'),
                     'stateKeysOnTime': distinct('stateKeysOnTime'),
                     'parserFirstBlock': distinct('parserListTag') + distinct('parserBlockTag'),
                     'firstBlockAgreesWithSaved': sorted({first_block_agrees(s) for s in rounds
                                                          if s['clean'] and s.get('parserBlockTag')})})
    return rows


def load(out):
    cells = json.loads((out / 'cells.json').read_text())
    run_log = {}
    for line in (out / 'run-log.jsonl').read_text().splitlines():
        rec = json.loads(line)
        run_log[(rec['cell'], rec['round'])] = rec
    summaries = {c['name']: [extract(out, c, r, run_log) for r in range(1, ROUNDS + 1)] for c in cells}
    return cells, summaries


def self_test(out):
    cells, base = load(out)
    got, _ = judge(cells, base)
    results = {'as-recorded': got}
    a_cells = [c['name'] for c in cells if c['class'] == 'A']

    def all_on_time(s):
        for name in a_cells:
            for x in s[name]:
                x['bulletOnTime'], x['bulletLate'] = x['bulletOnTime'] + x['bulletLate'], []

    cases = {
        # every A cell's late items moved on time: the run as it would look if the candidate worked
        'holds-if-on-time': (all_on_time, 'WITNESS-HOLDS'),
        'n2-says-true': (lambda s: (all_on_time(s), s['n2-sham-empty-before-list'][0]['bulletOnTime'].append('true')),
                         'WITNESS-FAILS'),
        'a4-says-false': (lambda s: (all_on_time(s), s['a4-empty-last'][2]['bulletOnTime'].append('false')),
                          'WITNESS-HOLDS-MID-ONLY'),
        'a2-not-saved-in-list': (lambda s: (all_on_time(s), s['a2-empty-mid'][1]['saved'].update(inList=False)),
                                 'WITNESS-FAILS'),
        'a2-one-round-unclean': (lambda s: (all_on_time(s), s['a2-empty-mid'][4].update(clean=False)),
                                 'NOT-ESTABLISHED'),
        'a3-not-the-browser-cell': (lambda s: (all_on_time(s), s['a3-enter-mid'][0].update(blocks=1)),
                                    'NOT-ESTABLISHED'),
        'n1-saved-in-list': (lambda s: (all_on_time(s), s['n1-sham-empty-mid'][3]['saved'].update(inList=True)),
                             'WITNESS-FAILS'),
    }
    red = True
    for name, (mutate, expected) in cases.items():
        mutated = copy.deepcopy(base)
        mutate(mutated)
        verdict, _ = judge(cells, mutated)
        results[name] = {'verdict': verdict, 'expected': expected, 'ok': verdict == expected}
        red = red and verdict == expected
    # the recorded first-block comparison must be able to say "disagrees"
    for name, field, value in (('n2-sham-empty-before-list', 'parserListTag', 'ul'),
                               ('a2-empty-mid', 'parserListTag', 'none'),
                               ('r5-heading-empty-mid', 'parserBlockTag', 'p')):
        x = copy.deepcopy(base[name][0])
        x[field] = value
        ok = first_block_agrees(base[name][0]) and not first_block_agrees(x)
        results[f'first-block-{name}-{field}={value}'] = {'ok': ok}
        red = red and ok
    # extraction-level red case: a record whose window does not align is not clean
    probe = copy.deepcopy(cells[0])
    rec_path = out / probe['name'] / 'r1.jsonl'
    recs = [json.loads(line) for line in rec_path.read_text().splitlines() if line.strip()]
    m = next(x for x in recs if x['rec'] == 'measured')
    m['ops'][0]['cbIndexAtFirstPoll'] += 1000
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='f176-self-test-'))
    (tmp / probe['name']).mkdir(parents=True, exist_ok=True)
    (tmp / probe['name'] / 'r1.jsonl').write_text('\n'.join(json.dumps(x) for x in recs) + '\n')
    (tmp / probe['name'] / 'r1.fodt.gz').write_bytes((out / probe['name'] / 'r1.fodt.gz').read_bytes())
    log = {(probe['name'], 1): {'exit': 0}}
    s = extract(tmp, probe, 1, log)
    results['misaligned-window-is-unclean'] = {'clean': s['clean'], 'why': s['why'], 'ok': not s['clean']}
    red = red and not s['clean']
    print(json.dumps({'selfTest': 'ALL_AS_EXPECTED' if red else 'SOME_CASE_WRONG', 'cases': results}, indent=1))
    return 0 if red else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test(a.out)
    cells, summaries = load(a.out)
    verdict, problems = judge(cells, summaries)
    print(json.dumps({'verdict': verdict, 'problems': problems, 'cells': table(cells, summaries)},
                     indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
