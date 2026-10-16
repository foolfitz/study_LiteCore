#!/usr/bin/env python3
"""Recompute the finding-142 native table from the raw JSONL / saved fodt files.

Usage: python3 -I read_results.py OUT_DIR FIXTURES_DIR [--runs 3]

Reads OUT_DIR/arms.json (written by run_arms.py) and, for every arm, the files
OUT_DIR/<arm>/r<N>.jsonl (and r<N>.fodt.gz for arms that save). Prints one
Markdown table row per measured press, then the checks.

Exit status 1 (red) when any of these fails:
  * completeness: arms.json is empty, a run file is missing, a run has a
    `fatal` record, lacks `done`, or has a different number of measured presses
    than its script asks for;
  * agreement: the runs of an arm do not produce the same signature (callback
    types in order excluding STATE_CHANGED, whether STATE_CHANGED came, caret
    rectangle and selection after, Undo changed / Undo top, K1 reads, locator,
    saved-document text);
  * consistency: in the -n1/-n2/-n3 families, the caret after press k of the
    longer arm differs from the caret at the end of the -nk arm;
  * positive controls: plain Home / plain Down did not move the caret with an
    INVALIDATE_VISIBLE_CURSOR; plain Backspace did NOT change the saved text;
    K1 (either direction) from mid-text selected nothing.
Finding-level expectations (arm 8: the document stays unchanged) are printed as
results, not as instrument checks.
"""
import argparse
import difflib
import gzip
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

T = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
O = '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
STATE = 'STATE_CHANGED'


def doc_text(xml_bytes):
    """Paragraph texts of the body (document order, table cells included) and of
    the master pages (headers/footers)."""
    root = ET.fromstring(xml_bytes)
    out = []
    for part, tag in ((O + 'master-styles', 'M'), (O + 'body', 'B')):
        node = root.find(part)
        if node is None:
            continue
        for el in node.iter():
            if el.tag in (T + 'p', T + 'h'):
                out.append(f'{tag}:' + ''.join(el.itertext()))
    return out


ST = '{urn:oasis:names:tc:opendocument:xmlns:style:1.0}'
FO = '{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}'


def para_shapes(xml_bytes):
    """Per body paragraph: list membership (list-item / list-header / none) and the
    fo:text-indent of its automatic paragraph style (none if unset). Writer's own
    Backspace at an L-C position changes these, not the text."""
    root = ET.fromstring(xml_bytes)
    body = root.find(O + 'body')
    parent = {c: p for p in body.iter() for c in p}
    indents = {}
    for auto in root.iter(O + 'automatic-styles'):
        for st in auto.findall(ST + 'style'):
            pp = st.find(ST + 'paragraph-properties')
            if pp is not None and pp.get(FO + 'text-indent') is not None:
                indents[st.get(ST + 'name')] = pp.get(FO + 'text-indent')
    out = []
    for el in body.iter():
        if el.tag not in (T + 'p', T + 'h'):
            continue
        lst, node = 'none', el
        while node in parent:
            node = parent[node]
            if node.tag in (T + 'list-item', T + 'list-header'):
                lst = node.tag[len(T):]
                break
        out.append(f'{lst}, text-indent {indents.get(el.get(T + "style-name"), "none")}')
    return out


def shape_diff(base, got):
    if base == got:
        return 'shape: as fixture'
    if len(base) != len(got):
        return f'shape: {len(base)} -> {len(got)} paragraphs'
    return 'shape: ' + '; '.join(f'P{i + 1} {a} -> {b}' for i, (a, b) in enumerate(zip(base, got)) if a != b)


def short(s, n=60):
    return s if len(s) <= n else s[:n] + '…'


def compare(base, got):
    if base == got:
        return 'same'
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=base, b=got).get_opcodes():
        if op == 'equal':
            continue
        a = ' / '.join(repr(x[2:]) for x in base[i1:i2])
        b = ' / '.join(repr(x[2:]) for x in got[j1:j2])
        if op == 'insert':
            where = f'after {base[i1 - 1][2:]!r}' if i1 > 0 else 'at the start'
            return f'DIFFERS: paragraph {short(b, 50)} inserted {where}'
        if op == 'delete':
            return f'DIFFERS: paragraph {short(a, 50)} deleted'
        return f'DIFFERS: {short(a, 50)} -> {short(b, 50)}'
    return 'DIFFERS'


def undo_top(undo_json):
    try:
        acts = json.loads(undo_json).get('actions')
    except Exception:
        return '<unparsable>'
    if not acts:
        return ''
    return acts[0].get('comment', '?')


def ctype(t):
    return t[len('LOK_CALLBACK_'):] if t.startswith('LOK_CALLBACK_') else t


def collapse(types):
    out = []
    for t in types:
        if not out or out[-1] != t:
            out.append(t)
    return out


def measured_steps(script):
    return [s for s in script.split(',') if s and s[0] in 'MBKJQ']


def parse_run(path):
    recs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return recs


def press_sig(p):
    types = [ctype(c['type']) for c in p['callbacks']]
    sig = {
        'label': p['label'],
        'kind': p['kind'],
        'types': collapse([t for t in types if t != STATE]),
        'state': STATE in types,
        'moved': p['before']['cursor'] != p['after']['cursor'],
        'cursorAfter': p['after']['cursor'],
        'selAfter': p['after']['selText'],
        'undoChanged': p['undoChanged'],
        'undoTop': undo_top(p['after']['undo']),
    }
    if p['kind'] == 'K1':
        sig['sel250'] = p['sel250']['text']
        sig['sel2250'] = p['sel2250']['text']
    return sig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('fixtures')
    ap.add_argument('--runs', type=int, default=3)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    fixtures = pathlib.Path(a.fixtures)
    problems = []
    arms = json.loads((out / 'arms.json').read_text())
    if not arms:
        print('RED: arms.json lists no arms')
        return 1
    base_text = {}
    data = {}  # arm -> list of per-run dicts
    for arm in arms:
        name = arm['name']
        fx = arm['fixture']
        if fx not in base_text:
            raw = (fixtures / f'{fx}.fodt').read_bytes()
            base_text[fx] = (doc_text(raw), para_shapes(raw))
        runs = []
        for r in range(1, a.runs + 1):
            path = out / name / f'r{r}.jsonl'
            if not path.exists():
                problems.append(f'{name} r{r}: missing {path.name}')
                continue
            recs = parse_run(path)
            kinds = [x['rec'] for x in recs]
            if 'fatal' in kinds or 'done' not in kinds:
                problems.append(f'{name} r{r}: fatal or no done record')
                continue
            presses = [x for x in recs if x['rec'] == 'press']
            if len(presses) != len(measured_steps(arm['script'])):
                problems.append(f'{name} r{r}: {len(presses)} measured presses, script asks for '
                                f'{len(measured_steps(arm["script"]))}')
                continue
            for x in presses:
                if x['capped'] or x['preQuietMs'] < 1500:
                    problems.append(f'{name} r{r} {x["label"]}: window capped or pre-quiet < 1500 ms')
            loc = next((x for x in recs if x['rec'] == 'locate'), None)
            setups = [x for x in recs if x['rec'] in ('setup', 'load')]
            run = {
                'presses': presses,
                'sigs': [press_sig(p) for p in presses],
                'locate': (loc['prefix'], loc['suffix'], loc['selBefore']) if loc else None,
                'placedCursor': setups[-1]['cursor'] if setups else '',
                'doc': None,
            }
            if arm['saves']:
                saved = next((x for x in recs if x['rec'] == 'saved'), None)
                gz = out / name / f'r{r}.fodt.gz'
                if not saved or not saved['ok'] or not gz.exists():
                    problems.append(f'{name} r{r}: save missing')
                    continue
                raw = gzip.decompress(gz.read_bytes())
                run['doc'] = (compare(base_text[fx][0], doc_text(raw)) + '; '
                              + shape_diff(base_text[fx][1], para_shapes(raw)))
            runs.append(run)
        data[name] = runs

    # (fixture, caret rect) -> locator text, learned from every run whose locator
    # describes a collapsed caret at a known rect
    where = {}
    for arm in arms:
        for run in data[arm['name']]:
            if not run['locate'] or run['locate'][2] != '':
                continue
            rect = run['presses'][-1]['after']['cursor'] if run['presses'] else run['placedCursor']
            if run['presses'] and run['presses'][-1]['after']['selText'] != '':
                continue
            pre, suf, _ = run['locate']
            label = '(empty paragraph)' if pre == '' and suf == '' else f'{pre}|{suf}'
            where.setdefault((arm['fixture'], rect), set()).add(label)
    for key, labels in where.items():
        if len(labels) > 1:
            problems.append(f'locator disagreement at {key}: {sorted(labels)}')

    def at(fx, rect):
        labels = where.get((fx, rect))
        return '«' + next(iter(labels)) + '»' if labels else '?'

    # agreement
    agree = {}
    for arm in arms:
        runs = data[arm['name']]
        if len(runs) != a.runs:
            agree[arm['name']] = f'{len(runs)}/{a.runs} complete'
            continue
        keys = [json.dumps([run['sigs'], run['locate'], run['doc']], sort_keys=True) for run in runs]
        same = max(keys.count(k) for k in keys)
        agree[arm['name']] = f'{same}/{a.runs}'
        if same != a.runs:
            problems.append(f'{arm["name"]}: runs disagree ({same}/{a.runs})')

    # consistency inside -nN families
    names = {arm['name'] for arm in arms}
    for arm in arms:
        m = re.match(r'(.*)-n(\d)$', arm['name'])
        if not m or not data[arm['name']]:
            continue
        stem, n = m.group(1), int(m.group(2))
        for k in range(1, n):
            sib = f'{stem}-n{k}'
            if sib not in names or not data[sib]:
                continue
            mine = {run['presses'][k - 1]['after']['cursor'] for run in data[arm['name']]}
            theirs = {run['presses'][-1]['after']['cursor'] for run in data[sib]}
            if mine != theirs:
                problems.append(f'{arm["name"]} press {k} caret {sorted(mine)} != {sib} final {sorted(theirs)}')

    # positive controls
    def all_runs(name, pred, what):
        runs = data.get(name, [])
        ok = bool(runs) and all(pred(run) for run in runs)
        print(f'- positive control `{name}`: {what}: {"OK" if ok else "FAILED"}')
        if not ok:
            problems.append(f'positive control {name} failed: {what}')

    # table
    print('| arm | runs agree | placed at | press | callbacks after the post (STATE_CHANGED omitted; +S = some came) '
          '| first cb ms (min-max) | last cb ms (max) | caret moved | caret after | lands at | selection after | Undo changed / top | saved text |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for arm in arms:
        if arm['group'] == 'P':
            continue
        runs = data[arm['name']]
        if not runs:
            print(f'| {arm["name"]} | {agree[arm["name"]]} | | | | | | | | | | | |')
            continue
        r0 = runs[0]
        placed = at(arm['fixture'], r0['presses'][0]['before']['cursor']) if r0['presses'] else ''
        if r0['presses'] and r0['presses'][0]['before']['selText']:
            placed = f'range {r0["presses"][0]["before"]["selText"]!r}'
        for i, sig in enumerate(r0['sigs']):
            firsts = [run['presses'][i]['firstCbMs'] for run in runs]
            firsts = [f for f in firsts if f >= 0]
            fcol = f'{min(firsts):.1f}-{max(firsts):.1f}' if firsts else 'none'
            lasts = [run['presses'][i]['lastCbMs'] for run in runs]
            lcol = f'{max(lasts):.0f}' if max(lasts) >= 0 else 'none'
            types = ', '.join(sig['types']) if sig['types'] else '(none)'
            if sig['state']:
                types += ' +S'
            if not sig['types'] and not sig['state']:
                quiet = min(run['presses'][i]['windowMs'] for run in runs)
                types = f'**none** (silent >= {quiet:.0f} ms)'
            sel = repr(sig['selAfter']) if sig['selAfter'] else '-'
            if sig['kind'] == 'K1':
                sel = f'+250: {sig["sel250"]!r}; +2250: {sig["sel2250"]!r}'
            landing = at(arm['fixture'], sig['cursorAfter']) if not sig['selAfter'] else '(range)'
            undo = f'{"yes" if sig["undoChanged"] else "no"}' + (f' / {sig["undoTop"]}' if sig['undoTop'] else '')
            doc = r0['doc'] if (arm['saves'] and i == len(r0['sigs']) - 1) else ''
            cells = [arm['name'] if i == 0 else '', agree[arm['name']] if i == 0 else '',
                     placed if i == 0 else '', f'{sig["label"]} ({"+".join(map(str, r0["presses"][i]["codes"]))})',
                     types, fcol, lcol, 'yes' if sig['moved'] else 'no', sig['cursorAfter'], landing,
                     sel, undo, doc]
            print('| ' + ' | '.join(str(c).replace('|', '\\|') for c in cells) + ' |')

    print()
    print('Placement checks (group P): caret after placement, and the locator there')
    print()
    for arm in arms:
        if arm['group'] != 'P':
            continue
        runs = data[arm['name']]
        locs = sorted({f'{run["locate"][0]}|{run["locate"][1]}' for run in runs if run['locate']})
        rects = sorted({run['placedCursor'] for run in runs})
        print(f'- `{arm["name"]}` ({agree[arm["name"]]}): caret {rects}, locator {locs}')

    print()
    print('Checks')
    print()
    all_runs('ctl-home', lambda r: r['sigs'][0]['moved'] and 'INVALIDATE_VISIBLE_CURSOR' in r['sigs'][0]['types'],
             'plain Home moved the caret with INVALIDATE_VISIBLE_CURSOR')
    all_runs('ctl-down', lambda r: r['sigs'][0]['moved'] and 'INVALIDATE_VISIBLE_CURSOR' in r['sigs'][0]['types'],
             'plain Down moved the caret with INVALIDATE_VISIBLE_CURSOR')
    all_runs('ctl-bksp', lambda r: (r['doc'] or '').startswith('DIFFERS'),
             'plain Backspace from mid-text changed the saved text (the comparison can go red)')
    all_runs('ctl-k1', lambda r: r['sigs'][0]['sel2250'] != '', 'K1 Shift+Left from mid-text selected something')
    all_runs('ctl-k1r', lambda r: r['sigs'][0]['sel2250'] != '', 'K1 Shift+Right from mid-text selected something')
    all_runs('ctl-bksp-at-num', lambda r: 'P2 list-item' in (r['doc'] or ''),
             'Writer\'s own Backspace at the start of the numbered P2 changed P2 (the discriminator can tell)')
    for name in ('red-home-bksp', 'red-end-del', 'b2b-home-bksp', 'b2b-end-del'):
        docs = sorted({str(run['doc']) for run in data.get(name, [])})
        print(f'- result `{name}`: saved text vs fixture: {docs}')
    for name in ('b2b-home-bksp-at-num',):
        docs = sorted({str(run['doc']) for run in data.get(name, [])})
        print(f'- result `{name}`: saved text vs fixture: {docs}')
    for name in ('q-home-bksp', 'q-end-del', 'q-ctl-home-bksp', 'q-home-bksp-at-num'):
        docs = sorted({str(run['doc']) for run in data.get(name, [])})
        fired = sorted({run['presses'][-1].get('fired') for run in data.get(name, [])})
        print(f'- result `{name}`: pair posted from inside the callback: {fired}; saved text vs fixture: {docs}')
    for name in ('red-home-k1', 'red-end-k1r'):
        sels = sorted({(run['sigs'][-1]['sel250'], run['sigs'][-1]['sel2250']) for run in data.get(name, [])})
        print(f'- result `{name}`: K1 selection at +250 / +2250 ms: {sels}')
    print()
    if problems:
        print('RED:')
        for p in problems:
            print(f'- {p}')
        return 1
    print(f'GREEN: {len(arms)} arms x {a.runs} runs complete, every arm {a.runs}/{a.runs}, no window capped, '
          'every press preceded by >= 1500 ms of quiet, n-families consistent, positive controls met')
    return 0


if __name__ == '__main__':
    sys.exit(main())
