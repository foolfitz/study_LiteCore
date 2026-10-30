#!/usr/bin/env python3
"""Judge the 083 path's native cells (ruling 3 Q5.2) against ../PREDICTION.md, from the records only.

Usage:
  python3 -I read_q52.py OUT_DIR                 the verdicts + the per-cell table (JSON on stdout)
  python3 -I read_q52.py --self-test OUT_DIR     the red cases, built from OUT_DIR's own summaries

extract() keeps each round's RAW inputs (the fallback's type and full markup, the restore read, the locator, the
saved file's last paragraph); judge() derives everything else from them -- the port of parseFormatReadback, rules
ONE / LAST / FIRST, P0, P3 -- so a self-test mutation of a raw input goes through the same parser and rules.

The sham cells dispatch set-list-unordered's command with On:false: the engine's expectation is the bullet's
(list `ul`), and "the saved paragraph matches the action" means "is a bullet", which a sham must not be.
Nothing is written.
"""
import argparse
import copy
import gzip
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

NS = {'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
      'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
      'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0'}
T = '{%s}' % NS['text']
ROUNDS = 5
NONE, TEXT = 0, 1
# ordered_format.inc:160-202 -- (expected list tag, expected block tag); the sham is the bullet's command
EXPECTED = {'bullet': ('ul', None), 'sham': ('ul', None), 'number': ('ol', None), 'none': ('none', None),
            'heading': (None, 'h1'), 'body': (None, 'p')}


# ---- the port of parseFormatReadback (wasm_sdk_probe/src/probe_engine.cpp:753-893), plus the LAST-block fields --

STRUCTURAL = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'blockquote', 'ul', 'ol', 'li'}
BLOCK = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'blockquote'}


def parse(html):
    r = {'parsed': False, 'unknownTag': False, 'unknownTagName': '', 'malformedNesting': False,
         'footnoteApparatus': False, 'listTag': '', 'blockTag': '', 'blockCount': 0, 'itemCount': 0,
         'multiBlock': False, 'lastListTag': None, 'lastBlockTag': None}
    body = html.find('<body')
    if body == -1:
        return r
    i = html.find('>', body)
    if i == -1:
        return r
    depth, first, stack = 0, True, []
    i += 1
    while i < len(html):
        if html[i] != '<':
            i += 1
            continue
        start = i + 1
        if start >= len(html):
            break
        closing = html[start] == '/'
        if closing:
            start += 1
        end = start
        while end < len(html) and html[end].isascii() and html[end].isalnum():
            end += 1
        if end == start:          # a comment or a declaration: never a refusal
            i += 1
            continue
        tag = html[start:end].lower()
        bracket = html.find('>', end)
        attributes = '' if bracket == -1 else html[end:bracket]
        self_closing = attributes.endswith('/')
        i = end if bracket == -1 else bracket
        if tag in STRUCTURAL:
            r['parsed'] = True
            if closing:
                if depth == 0:
                    r['malformedNesting'] = True
                    break
                depth -= 1
                stack.pop()
                continue
            if first:
                first = False
                if tag in ('ul', 'ol'):
                    r['listTag'] = tag
            if tag in BLOCK:
                r['blockCount'] += 1
                if not r['blockTag']:
                    r['blockTag'] = tag
                # LAST-block fields (PREDICTION.md): the innermost open list when the last block opens
                r['lastBlockTag'] = tag
                r['lastListTag'] = next((t for t in reversed(stack) if t in ('ul', 'ol')), 'none')
            elif tag == 'li':
                r['itemCount'] += 1
            if not self_closing:
                depth += 1
                stack.append(tag)
            continue
        if depth > 0 or closing:
            continue
        if tag == 'div' and ('id="sdfootnote' in attributes or 'id="sdendnote' in attributes):
            r['footnoteApparatus'] = True
            break
        r['unknownTag'], r['unknownTagName'] = True, tag
        break
    r['multiBlock'] = r['blockCount'] > 1 or r['itemCount'] > 1
    return r


def rule(name, action, fb_type, html):
    """ONE, LAST or FIRST (PREDICTION.md, Derivations): 'refused', 'satisfied' or 'not-satisfied'."""
    if fb_type != TEXT:
        return 'refused'
    pr = parse(html)
    if not pr['parsed'] or pr['unknownTag'] or pr['malformedNesting'] or pr['footnoteApparatus']:
        return 'refused'
    if name == 'ONE' and pr['multiBlock']:
        return 'refused'
    want_list, want_block = EXPECTED[action]
    if name == 'LAST':
        if pr['lastBlockTag'] is None:
            return 'refused'
        got_list, got_block = pr['lastListTag'], pr['lastBlockTag']
    else:
        got_list, got_block = pr['listTag'] or 'none', pr['blockTag']
    ok = (want_list is None or got_list == want_list) and (want_block is None or got_block == want_block)
    return 'satisfied' if ok else 'not-satisfied'


# ---- ground truth: the saved FODT's LAST text:p / text:h in document order -------------------------------------

def saved_last(fodt_gz):
    root = ET.fromstring(gzip.decompress(fodt_gz.read_bytes()))
    kinds = {}
    for ls in root.iter(T + 'list-style'):
        first = next(iter(ls), None)
        kinds[ls.get('{%s}name' % NS['style'])] = (
            'bullet' if first is not None and first.tag == T + 'list-level-style-bullet'
            else 'number' if first is not None and first.tag == T + 'list-level-style-number' else '?')
    body = root.find('office:body/office:text', NS)
    paragraphs = []

    def walk(node, lists):
        for child in node:
            if child.tag in (T + 'p', T + 'h'):
                paragraphs.append((child, list(lists)))
            walk(child, lists + [child] if child.tag == T + 'list' else lists)
    walk(body, [])
    if not paragraphs:
        return {'found': False, 'paragraphs': 0}
    node, lists = paragraphs[-1]
    style = next((x.get(T + 'style-name') for x in lists if x.get(T + 'style-name')), None)
    return {'found': True, 'paragraphs': len(paragraphs), 'text': ''.join(node.itertext()), 'inList': bool(lists),
            'listStyle': style, 'listKind': kinds.get(style) if style else None, 'heading': node.tag == T + 'h'}


def matches(action, saved):
    if action in ('bullet', 'sham'):
        return bool(saved.get('inList')) and saved.get('listKind') == 'bullet'
    if action == 'number':
        return bool(saved.get('inList')) and saved.get('listKind') == 'number'
    if action == 'none':
        return not saved.get('inList')
    if action == 'heading':
        return bool(saved.get('heading'))
    return not saved.get('heading')            # body


def undo_actions(payload):
    try:
        actions = json.loads(payload).get('actions')
    except (ValueError, AttributeError):
        return None
    return [a.get('comment') for a in actions] if isinstance(actions, list) else []


# ---- per round: the raw inputs ----------------------------------------------------------------------------------

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
    if not (by.get('saved') or [{}])[0].get('ok'):
        why.append('not saved')
    locate = (by.get('locate') or [None])[0]
    if not locate:
        why.append('no locate record')
    measured = (by.get('measured') or [None])[0]
    if not measured:
        return {'round': r, 'clean': False, 'why': why + ['no measured record']}
    if measured.get('capped'):
        why.append('capped settle')
    op = (measured.get('ops') or [None])[0]
    if not op or op['op'][:1] != 'H' or 'fallback' not in (op.get('format') or {}):
        return {'round': r, 'clean': False, 'why': why + ['no H op with a fallback record']}
    fmt, fb = op['format'], op['format']['fallback']
    if fb['htmlBytes'] != len(fb['html'].encode('utf-8')):
        why.append('fallback markup truncated')
    gz = out / cell['name'] / f'r{r}.fodt.gz'
    saved = saved_last(gz) if gz.exists() else {'found': False}
    if not saved.get('found'):
        why.append('no paragraph in the saved file')
    results = [json.loads(c['payload']) for c in measured['callbacks'] + (op.get('lateCallbacks') or [])
               if c['type'] == 'LOK_CALLBACK_UNO_COMMAND_RESULT' and fb['command'] in c['payload']]
    return {'round': r, 'clean': not why, 'why': why,
            # raw inputs of the derivations
            'selectedType': fmt['selectedType'], 'fallbackRan': fb['ran'], 'fbType': fb['type'],
            'fbHtml': fb['html'], 'restoredType': fmt['restoredType'],
            'locate': {k: locate.get(k) for k in ('selBefore', 'suffix', 'prefix')} if locate else None,
            'saved': saved,
            # recorded only
            'fbText': fb['text'], 'fbTextBytes': fb['textBytes'], 'fbHtmlBytes': fb['htmlBytes'],
            'fbPostMs': fb['postMs'], 'fbHtmlMs': fb['htmlMs'],
            'fbCommandResult': [x.get('success') for x in results],
            'undoBefore': undo_actions(fmt.get('undoAtStart', '')), 'undoAfter': undo_actions(op['atReturn']['undo'])}


def derive(cell, s):
    """Everything judged, from the raw inputs only."""
    if not s.get('clean'):
        return s
    d = dict(s)
    d['P0'] = s['selectedType'] == NONE and bool(s['fallbackRan'])
    loc = s['locate'] or {}
    d['P3'] = s['restoredType'] == NONE and loc.get('suffix') == '' and loc.get('prefix') == ''
    d['parse'] = parse(s['fbHtml']) if s['fbType'] == TEXT else None
    for name in ('ONE', 'LAST', 'FIRST'):
        d[name] = rule(name, cell['action'], s['fbType'], s['fbHtml'])
    d['matches'] = matches(cell['action'], s['saved'])
    return d


# ---- verdicts ---------------------------------------------------------------------------------------------------

def deciding(cells, rounds, names):
    """Per cell: NE reason or None, and its clean derived rounds."""
    res = {}
    for n in names:
        clean = [s for s in rounds[n] if s.get('clean')]
        if len(clean) < ROUNDS:
            res[n] = (f'{len(clean)}/{ROUNDS} clean', clean)
        elif not all(s['P0'] for s in clean):
            res[n] = ('P0 fails (not the 083 path)', clean)
        else:
            res[n] = (None, clean)
    return res


def unsafe(cells, rounds, rule_name, prefix=''):
    return [f"{c['name']} r{s['round']}" for c in cells if c['name'].startswith(prefix)
            for s in rounds[c['name']] if s.get('clean') and s[rule_name] == 'satisfied' and not s['matches']]


def classify(cell, clean):
    """V2/V3 (PREDICTION.md): COVERED / REFUSED / PARTIAL for A cells, SAFE / PARTIAL for N cells."""
    if cell['class'] == 'N':
        ok = all(s['LAST'] != 'satisfied' and not s['saved'].get('inList') for s in clean)
        return 'SAFE' if ok else 'PARTIAL'
    if all(s['LAST'] == 'satisfied' and s['P3'] for s in clean):
        return 'COVERED'
    if all(s['LAST'] == 'refused' for s in clean):
        return 'REFUSED'
    return 'PARTIAL'


def judge(cells, rounds):
    by = {c['name']: c for c in cells}
    out = {}
    # V1
    bad = unsafe(cells, rounds, 'ONE')
    dec = deciding(cells, rounds, ['sa-a5-blank-one', 'sa-n5-sham-blank-one'])
    if bad:
        v1 = {'verdict': 'ONE-BLOCK-UNSAFE', 'rounds': bad}
    elif any(ne for ne, _ in dec.values()):
        v1 = {'verdict': 'NOT-ESTABLISHED', 'why': {n: ne for n, (ne, _) in dec.items() if ne}}
    else:
        problems = []
        for s in dec['sa-a5-blank-one'][1]:
            if not (s['fbType'] == TEXT and s['parse'] and s['parse']['blockCount'] == 1 and s['ONE'] == 'satisfied'
                    and s['matches'] and s['P3']):
                problems.append(f"sa-a5 r{s['round']}: fbType {s['fbType']}, ONE {s['ONE']}, matches "
                                f"{s['matches']}, P3 {s['P3']}")
        for s in dec['sa-n5-sham-blank-one'][1]:
            if not (s['ONE'] != 'satisfied' and not s['saved'].get('inList') and s['P3']):
                problems.append(f"sa-n5 r{s['round']}: ONE {s['ONE']}, inList {s['saved'].get('inList')}, P3 {s['P3']}")
        v1 = {'verdict': 'ONE-BLOCK-DOES-NOT-VERIFY', 'problems': problems} if problems else {'verdict': 'ONE-BLOCK-HOLDS'}
    out['V1'] = v1
    # action scope (SA-5)
    scope = {}
    for c in cells:
        if c['group'] not in ('SA-5',) and c['name'] != 'sa-a5-blank-one':
            continue
        ne, clean = deciding(cells, rounds, [c['name']])[c['name']]
        if ne:
            scope[c['action']] = {'cell': c['name'], 'status': 'NOT-ESTABLISHED', 'why': ne}
        else:
            ok = all(s['ONE'] == 'satisfied' and s['matches'] and s['P3'] for s in clean)
            scope[c['action']] = {'cell': c['name'], 'status': 'IN-SCOPE' if ok else 'OUT-OF-SCOPE',
                                  'ONE': [s['ONE'] for s in clean]}
    out['scope'] = {'read': v1['verdict'] == 'ONE-BLOCK-HOLDS', 'actions': scope}
    # V2 and V3
    for key, group, prefix in (('V2', 'SA-M', 'sa-'), ('V3', 'CL', 'cl-')):
        names = [c['name'] for c in cells if c['group'] == group]
        bad = unsafe(cells, rounds, 'LAST', prefix)
        dec = deciding(cells, rounds, names)
        if bad:
            out[key] = {'verdict': 'LAST-UNSAFE', 'rounds': bad}
            continue
        if any(ne for ne, _ in dec.values()):
            out[key] = {'verdict': 'NOT-ESTABLISHED', 'why': {n: ne for n, (ne, _) in dec.items() if ne}}
            continue
        cls = {n: classify(by[n], clean) for n, (_, clean) in dec.items()}
        p3 = [f"{n} r{s['round']}" for n, (_, clean) in dec.items() for s in clean if not s['P3']]
        holds = (not p3 and all(v == 'SAFE' for n, v in cls.items() if by[n]['class'] == 'N')
                 and all(v in ('COVERED', 'REFUSED') for n, v in cls.items() if by[n]['class'] == 'A'))
        out[key] = {'verdict': 'LAST-HOLDS' if holds else 'LAST-PARTIAL', 'cells': cls, 'p3Fails': p3,
                    'covered': sorted(n for n, v in cls.items() if v == 'COVERED')}
    return out


def table(cells, rounds):
    rows = {}
    for c in cells:
        rs = []
        for s in rounds[c['name']]:
            if not s.get('clean'):
                rs.append({'round': s['round'], 'clean': False, 'why': s['why']})
                continue
            pr = s['parse'] or {}
            rs.append({'round': s['round'], 'clean': True, 'P0': s['P0'], 'P3': s['P3'], 'fbType': s['fbType'],
                       'ONE': s['ONE'], 'LAST': s['LAST'], 'FIRST': s['FIRST'], 'matches': s['matches'],
                       'blocks': pr.get('blockCount'), 'items': pr.get('itemCount'),
                       'first': [pr.get('listTag') or 'none', pr.get('blockTag')] if pr else None,
                       'last': [pr.get('lastListTag'), pr.get('lastBlockTag')] if pr else None,
                       'unknownTag': pr.get('unknownTagName') or None, 'fbText': s['fbText'][:60],
                       'fbHtmlBytes': s['fbHtmlBytes'], 'fbHtmlMs': round(s['fbHtmlMs'], 1),
                       'fbPostMs': round(s['fbPostMs'], 1), 'fbCommandResult': s['fbCommandResult'],
                       'saved': {k: s['saved'].get(k) for k in ('paragraphs', 'inList', 'listKind', 'heading')},
                       'undoTopAfter': (s['undoAfter'] or [None])[0], 'undoChanged': s['undoAfter'] != s['undoBefore']})
        rows[c['name']] = {'class': c['class'], 'group': c['group'], 'action': c['action'], 'rounds': rs}
    return rows


def load(out):
    cells = json.loads((out / 'cells.json').read_text())
    run_log = {}
    for line in (out / 'run-log.jsonl').read_text().splitlines():
        rec = json.loads(line)
        run_log[(rec['cell'], rec['round'])] = rec
    rounds = {c['name']: [derive(c, extract(out, c, r, run_log)) for r in range(1, ROUNDS + 1)] for c in cells}
    return cells, rounds


# ---- red cases --------------------------------------------------------------------------------------------------

ONE_UL = '<html><body dir="ltr"><ul><li><p></p></li></ul></body></html>'
ONE_P = '<html><body dir="ltr"><p></p></body></html>'


def self_test(cells, rounds):
    by = {c['name']: c for c in cells}
    cases = []

    def run(name, mutate, key, want):
        r = copy.deepcopy(rounds)
        mutate(r)
        r = {n: [derive(by[n], s) for s in rs] for n, rs in r.items()}
        got = judge(cells, r)[key]['verdict'] if key != 'scope' else judge(cells, r)['scope']
        ok = got == want if key != 'scope' else want(got['actions'])
        cases.append({'case': name, 'want': want if key != 'scope' else 'see case', 'got': got if key != 'scope'
                      else got['actions'], 'ok': ok})

    def each(r, cell, **kw):
        for s in r[cell]:
            s.update(kw)

    def force(r, cell, html, in_bullet, **saved_over):
        """A clean 083-path round whose fallback reads `html`, restored, saved in a bullet list or not."""
        saved = {'found': True, 'paragraphs': 2, 'text': '', 'inList': in_bullet,
                 'listStyle': 'L1' if in_bullet else None, 'listKind': 'bullet' if in_bullet else None,
                 'heading': False, **saved_over}
        each(r, cell, clean=True, why=[], selectedType=NONE, fallbackRan=True, fbType=TEXT, fbHtml=html,
             restoredType=NONE, locate={'selBefore': '', 'suffix': '', 'prefix': ''}, saved=saved)

    def blank_holds(r):  # the candidate as the ruling imagined it: SelectAll reads the one empty bullet
        force(r, 'sa-a5-blank-one', ONE_UL, True)
        force(r, 'sa-n5-sham-blank-one', ONE_P, False)

    TWO_UL = '<html><body><p>a</p><ul><li><p></p></li></ul></body></html>'
    TWO_P = '<html><body><ul><li><p>a</p></li></ul><p></p></body></html>'

    def group_holds(r, group):  # every A cell COVERED, every N cell SAFE
        for c in cells:
            if c['group'] == group:
                force(r, c['name'], TWO_UL if c['class'] == 'A' else TWO_P, c['class'] == 'A')

    # V1 reachability
    run('V1: sa-a5 reads one <ul> block, sa-n5 one <p> -> HOLDS', blank_holds, 'V1', 'ONE-BLOCK-HOLDS')
    run('V1: then sa-n5 r3 reads <ul> while saved out of a list -> UNSAFE',
        lambda r: (blank_holds(r), r['sa-n5-sham-blank-one'][2].update(fbHtml=ONE_UL)), 'V1', 'ONE-BLOCK-UNSAFE')
    run('V1: UNSAFE is checked in every cell: sa-r1 r1 satisfied while saved out of a list',
        lambda r: force(r, 'sa-r1-noop-bulleted-only', ONE_UL, False), 'V1', 'ONE-BLOCK-UNSAFE')
    run('V1: then one sa-a5 round unclean -> NOT-ESTABLISHED',
        lambda r: (blank_holds(r), r['sa-a5-blank-one'][1].update(clean=False, why=['mutated'])), 'V1',
        'NOT-ESTABLISHED')
    run('V1: then sa-a5 r2 SelectText read TEXT (not the 083 path) -> NOT-ESTABLISHED',
        lambda r: (blank_holds(r), r['sa-a5-blank-one'][1].update(selectedType=TEXT)), 'V1', 'NOT-ESTABLISHED')
    run('V1: then sa-a5 r4 restore read TEXT -> DOES-NOT-VERIFY',
        lambda r: (blank_holds(r), r['sa-a5-blank-one'][3].update(restoredType=TEXT)), 'V1',
        'ONE-BLOCK-DOES-NOT-VERIFY')
    run('V1: then sa-a5 r5 two blocks -> DOES-NOT-VERIFY (multi-block refused)',
        lambda r: (blank_holds(r), r['sa-a5-blank-one'][4].update(
            fbHtml='<html><body><ul><li><p></p></li></ul><p>x</p></body></html>')), 'V1', 'ONE-BLOCK-DOES-NOT-VERIFY')
    run('V1: then the sa-a5 markup has a body-level <table> -> DOES-NOT-VERIFY (unknown tag refused)',
        lambda r: (blank_holds(r), each(r, 'sa-a5-blank-one', fbHtml='<html><body><table></table>'
                                                                      '<ul><li><p></p></li></ul></body></html>')),
        'V1', 'ONE-BLOCK-DOES-NOT-VERIFY')
    # scope
    run('scope: V1 holds and sa-num reads one <ol> -> number IN-SCOPE',
        lambda r: (blank_holds(r), force(r, 'sa-num-blank-one', '<html><body><ol><li><p></p></li></ol></body></html>',
                                         True, listKind='number')),
        'scope', lambda g: g['number']['status'] == 'IN-SCOPE')
    run('scope: then saved as a bullet, not a number -> number OUT-OF-SCOPE',
        lambda r: (blank_holds(r), force(r, 'sa-num-blank-one', '<html><body><ol><li><p></p></li></ol></body></html>',
                                         True)),
        'scope', lambda g: g['number']['status'] == 'OUT-OF-SCOPE')
    run('scope: sa-head reads <p> -> heading OUT-OF-SCOPE',
        lambda r: (blank_holds(r), force(r, 'sa-head-blank-one', ONE_P, False, heading=True)),
        'scope', lambda g: g['heading']['status'] == 'OUT-OF-SCOPE')
    run('scope: sa-head reads <h1> saved as a heading -> heading IN-SCOPE',
        lambda r: (blank_holds(r), force(r, 'sa-head-blank-one', '<html><body><h1></h1></body></html>', False,
                                         heading=True)),
        'scope', lambda g: g['heading']['status'] == 'IN-SCOPE')
    # V2 / V3, each from a forced holding baseline so that every case moves exactly one verdict
    for key, group, n8, a4, t1 in (('V2', 'SA-M', 'sa-n8-sham-after-bullet', 'sa-a4-empty-last',
                                    'sa-t1-table-then-empty-last'),
                                   ('V3', 'CL', 'cl-n8-sham-after-bullet', 'cl-a4-empty-last',
                                    'cl-t1-table-then-empty-last')):
        g = lambda r, group=group: group_holds(r, group)
        run(f'{key}: every A cell COVERED, every N cell SAFE -> LAST-HOLDS', g, key, 'LAST-HOLDS')
        run(f'{key}: then {t1} refused in every round (body-level table) -> still LAST-HOLDS (fail closed)',
            lambda r, g=g, t1=t1: (g(r), each(r, t1, fbHtml='<html><body><table></table><ul><li><p></p></li></ul>'
                                                            '</body></html>')), key, 'LAST-HOLDS')
        run(f'{key}: then {t1} refused in one round only -> LAST-PARTIAL',
            lambda r, g=g, t1=t1: (g(r), r[t1][0].update(fbType=NONE)), key, 'LAST-PARTIAL')
        run(f'{key}: then {n8} r1 last block in a <ul> while saved out of a list -> LAST-UNSAFE',
            lambda r, g=g, n8=n8: (g(r), r[n8][0].update(fbHtml=TWO_UL)), key, 'LAST-UNSAFE')
        run(f'{key}: then {a4} r2 unclean -> NOT-ESTABLISHED',
            lambda r, g=g, a4=a4: (g(r), r[a4][1].update(clean=False, why=['mutated'])), key, 'NOT-ESTABLISHED')
        run(f'{key}: then {a4} r3 restore not NONE -> LAST-PARTIAL',
            lambda r, g=g, a4=a4: (g(r), r[a4][2].update(restoredType=TEXT)), key, 'LAST-PARTIAL')
        run(f'{key}: then {a4} r4 locator suffix not empty -> LAST-PARTIAL',
            lambda r, g=g, a4=a4: (g(r), r[a4][3].update(locate={'selBefore': '', 'suffix': 'Plain first',
                                                                 'prefix': ''})), key, 'LAST-PARTIAL')
        run(f'{key}: then {n8} saved in a list (the sham applied) -> LAST-PARTIAL',
            lambda r, g=g, n8=n8: (g(r), r[n8][4]['saved'].update(inList=True, listKind='bullet')), key,
            'LAST-PARTIAL')
    # the parser port, directly
    p = parse('<html><body><ul><li><p></p></li></ul><p>x</p></body></html>')
    cases.append({'case': 'parse: first ul/p, last none/p, two blocks', 'ok': (p['listTag'], p['blockTag'],
                  p['lastListTag'], p['lastBlockTag'], p['multiBlock']) == ('ul', 'p', 'none', 'p', True)})
    p = parse('<html><body><p>a</p><ul><li><p>b</p><ol><li><p></p></li></ol></li></ul></body></html>')
    cases.append({'case': 'parse: nested lists, the last block is in the inner ol', 'ok': p['lastListTag'] == 'ol'})
    p = parse('<html><body><p>a<sup>1</sup></p><div id="sdfootnote1"><p>n</p></div></body></html>')
    cases.append({'case': 'parse: footnote apparatus refused', 'ok': p['footnoteApparatus']
                  and rule('LAST', 'bullet', TEXT, '<html><body><p>a</p><div id="sdfootnote1"></div></body></html>')
                  == 'refused'})
    cases.append({'case': 'parse: a body-level closing tag is malformed nesting',
                  'ok': parse('<html><body></p><p></p></body></html>')['malformedNesting']})
    cases.append({'case': 'parse: a comment is skipped, not refused',
                  'ok': rule('ONE', 'bullet', TEXT, '<html><body><!-- c --><ul><li><p></p></li></ul></body></html>')
                  == 'satisfied'})
    cases.append({'case': 'rule FIRST is fooled where LAST is not (the trap)',
                  'ok': rule('FIRST', 'sham', TEXT, '<html><body><ul><li><p>B</p></li></ul><p></p></body></html>')
                  == 'satisfied' and rule('LAST', 'sham', TEXT,
                                          '<html><body><ul><li><p>B</p></li></ul><p></p></body></html>')
                  == 'not-satisfied'})
    cases.append({'case': 'not TEXT is refused by every rule',
                  'ok': {rule(n, 'bullet', NONE, ONE_UL) for n in ('ONE', 'LAST', 'FIRST')} == {'refused'}})
    # non-vacuity: the run has every cell, five rounds each
    cases.append({'case': 'non-vacuous: 27 cells x 5 rounds were read',
                  'ok': len(cells) == 27 and all(len(rs) == ROUNDS for rs in rounds.values())})
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
        result = {'verdicts': judge(cells, rounds), 'cells': table(cells, rounds)}
    json.dump(result, sys.stdout, indent=1, ensure_ascii=False)
    print()
    return 0 if not a.self_test or result['result'] == 'ALL_AS_EXPECTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
