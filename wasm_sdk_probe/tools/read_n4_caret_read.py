#!/usr/bin/env python3
"""SPEC-P-demo-batch-4 N4's reader.  For each arm: the post read against the saved ODT (the arm's truth), the pre read against the
fixture, and the saved document against the arm that never read (a read that moved anything would show).  Counts, then the misses.

  read_n4_caret_read.py DIR [PART ...]
"""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
STYLE = '{urn:oasis:names:tc:opendocument:xmlns:style:1.0}'
FO = '{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}'
ROOT = Path(sys.argv[1])
PARTS = sys.argv[2:] or ['blank', 'range', 'table', 'widen', 'caret']
EXPECT = {'bullet-on': ('list', 'ul'), 'number-on': ('list', 'ol'), 'remove': ('list', ''), 'h1': ('block', 'h1'), 'h2': ('block', 'h2'), 'h3': ('block', 'h3'),
          'h4': ('block', 'h4'), 'body': ('block', 'p'), 'left': ('align', 'left'), 'center': ('align', 'center'), 'right': ('align', 'right'), 'justify': ('align', 'justify')}


def document(url):
    """Every paragraph: text, block tag or heading level, list kind, alignment, as the saved file says."""
    with zipfile.ZipFile(url[len('file://'):]) as z:
        root = ET.fromstring(z.read('content.xml'))
        styles_root = ET.fromstring(z.read('styles.xml'))
    parents = {c: p for p in root.iter() for c in p}
    styles, kinds = {}, {}
    for tree in (styles_root, root):
        for s in tree.iter(STYLE + 'style'):
            props = s.find(STYLE + 'paragraph-properties')
            styles[s.get(STYLE + 'name')] = (props.get(FO + 'text-align') if props is not None else None, s.get(STYLE + 'parent-style-name'))
        for ls in tree.iter(TEXT + 'list-style'):
            for level in ls:
                kinds[(ls.get(STYLE + 'name'), int(level.get(TEXT + 'level') or 1))] = 'ul' if level.tag.endswith('bullet') else 'ol'
    out = []
    for p in root.iter():
        if p.tag not in (TEXT + 'p', TEXT + 'h'):
            continue
        walk, list_kind, named, depth = p, '', None, 0
        while walk in parents:
            walk = parents[walk]
            if walk.tag == TEXT + 'list':
                depth += 1
                # A nested list carries no style name; the outermost one names the style, the depth names the level.
                named = walk.get(TEXT + 'style-name') or named
        if named:
            list_kind = kinds.get((named, depth), kinds.get((named, 1), 'ol'))
        name, align = p.get(TEXT + 'style-name'), None
        seen = set()
        while name in styles and name not in seen:
            seen.add(name)
            align = align or styles[name][0]
            name = styles[name][1]
        level = p.get(TEXT + 'outline-level') if p.tag == TEXT + 'h' else None
        out.append({'text': ''.join(p.itertext()), 'block': f'h{level}' if level else 'p', 'list': list_kind, 'align': align or ''})
    return out


def rows(part):
    return [json.loads(line) for line in (ROOT / part / 'observations.jsonl').read_text().splitlines()]


def target(saved, needle):
    """The paragraph the arm acted on: it holds the X (a caret arm) or the needle (a range arm), else the only paragraph."""
    hits = [p for p in saved if 'X' in p['text'].replace('EX', '')] or [p for p in saved if needle and needle in p['text']]
    return hits[0] if hits else (saved[0] if len(saved) == 1 else None)


def covered(saved, rows_read):
    """The saved paragraphs a read's rows describe, in order.  A caret arm inserted X, so an empty row is the paragraph that is now X."""
    out, at = [], 0
    for row in rows_read:
        want = row['text']
        # One X at most, and only where the arm put it: FOXTROT has one of its own.
        while at < len(saved) and not (want in saved[at]['text'] if want else not saved[at]['text']) \
                and not (want in saved[at]['text'].replace('X', '', 1) if want else saved[at]['text'] == 'X') \
                and not any(want == saved[at]['text'][:i] + saved[at]['text'][i + 1:] for i, c in enumerate(saved[at]['text']) if c == 'X'):
            at += 1
        if at == len(saved):
            return None
        out.append(saved[at])
        at += 1
    return out


def agrees(row, para):
    align = {'start': 'left', 'end': 'right'}.get(para['align'], para['align'])
    return row['list'] == para['list'] and row['block'] == para['block'] and (row['align'] == align or (row['align'] in ('', 'left') and align in ('', 'left')))


tally = {}
for part in PARTS:
    data = rows(part)
    truth = {(r['place'], r['command']): document(r['saved']) for r in data if r['route'] == 'truth'}
    for r in data:
        if r['route'] == 'truth':
            continue
        saved = document(r['saved'])
        t = tally.setdefault(part, {'arms': 0, 'readOk': 0, 'postMatchesFile': 0, 'postMeetsCommand': 0, 'textKept': 0, 'sameAsNoRead': 0, 'selectionKept': 0, 'maxUs': 0, 'misses': []})
        t['arms'] += 1
        post, pre = r['post'], r['pre']
        t['readOk'] += post['ok'] == 1
        t['maxUs'] = max(t['maxUs'], post['us'], pre['us'])
        field, want = EXPECT[r['command']]
        paras = covered(saved, post['rows']) if post['ok'] else None
        # An empty paragraph the arm left empty is indistinguishable from any other: a row reads the first one, so take the one holding X.
        if paras is not None and len(post['rows']) == 1 and not post['rows'][0]['text']:
            paras = [p for p in saved if p['text'] == 'X'] or paras
        ok = paras is not None and all(agrees(a, b) for a, b in zip(post['rows'], paras))
        t['postMatchesFile'] += ok
        meets = post['ok'] == 1 and all(row[field] == want for row in post['rows'])
        t['postMeetsCommand'] += meets
        kept = [x['text'] for x in pre['rows']] == [x['text'] for x in post['rows']]
        t['textKept'] += kept
        same = (r['place'], r['command']) not in truth or saved == truth[(r['place'], r['command'])]
        t['sameAsNoRead'] += same
        t['selectionKept'] += r['typeBefore'] == r['typeAfter']
        if not (ok and meets and same and kept and post['ok'] == 1):
            t['misses'].append({'place': r['place'], 'cmd': r['command'], 'types': [r['typeBefore'], r['typeAfter']], 'pre': [(x['list'], x['block'], x['style'], x['text'][:14]) for x in pre['rows']][:5], 'post': [(x['list'], x['block'], x['align'], x['text'][:14]) for x in post['rows']][:5], 'reason': post['reason'], 'matches': ok, 'meets': meets, 'kept': kept, 'same': same})
for part, t in tally.items():
    misses = t.pop('misses')
    print(part, t)
    for m in misses[:60]:
        print('  ', json.dumps(m, ensure_ascii=False)[:420])
