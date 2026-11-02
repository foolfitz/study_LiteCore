#!/usr/bin/env python3
"""SPEC-P-demo-batch-4 N3's reader.  caret, table, blank: does a route leave the caret where the dispatch alone leaves it (X was
inserted after the route, so the saved document says)?  undo: one Undo equals the fixture's paragraphs.  range: selection kept, text
kept, every paragraph reached.  Structure per paragraph comes from the saved ODT.  read_n3_toggle.py DIR [PART ...]"""
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
ROOT = Path(sys.argv[1])
PARTS = sys.argv[2:] or ['styles', 'undo', 'blank', 'table', 'range', 'caret']


def paragraphs(url):
    with zipfile.ZipFile(url[len('file://'):]) as z:
        root = ET.fromstring(z.read('content.xml'))
    parents = {c: p for p in root.iter() for c in p}
    out = []
    for p in root.iter():
        if p.tag not in (TEXT + 'p', TEXT + 'h'):
            continue
        walk, in_list = p, False
        while walk in parents:
            walk = parents[walk]
            if walk.tag == TEXT + 'list':
                in_list = True
                break
        out.append((''.join(p.itertext()), p.tag.split('}')[1], p.get(TEXT + 'outline-level'), in_list))
    return out


def rows(part):
    return [json.loads(line) for line in (ROOT / part / 'observations.jsonl').read_text().splitlines()]


def blocks(html):
    return re.findall(r'<(ul|ol|li|p|h[1-6]|table|td|div)\b', html or '')


def caret(part):
    data = rows(part)
    truth = {(r['place'], r['command']): paragraphs(r['saved']) for r in data if r['route'] == 'truth'}
    tally = {}
    for r in data:
        if r['route'] == 'truth':
            continue
        same = paragraphs(r['saved']) == truth[(r['place'], r['command'])]
        tally.setdefault(r['route'], []).append(same)
        note = (r.get('postHow'), r.get('postType'), r.get('postAfter'), r.get('preHow'), r.get('preAfter'))
        if not same or part != 'caret':
            print(part, r['route'].ljust(9), r['command'].ljust(10), r['place'].ljust(20), 'SAME' if same else 'MOVED', note, blocks(r.get('postHtml'))[:12],
                  '' if same else [a[0][:34] for a, b in zip(paragraphs(r['saved']), truth[(r['place'], r['command'])]) if a != b])
    print(part, {k: f'{sum(v)}/{len(v)}' for k, v in tally.items()})


def undo():
    data = rows('undo')
    base = None
    for r in data:
        undone = paragraphs(r['undone'])
        changed = paragraphs(r['saved'])
        print('undo', r['route'].ljust(9), r['command'].ljust(10), 'changed' if changed != undone else 'NOT-CHANGED', blocks(r.get('postHtml'))[:8], undone[1][:2], changed[1][:3])
        base = base or undone
        if undone != base:
            print('  UNDO DIFFERS', [a for a, b in zip(undone, base) if a != b][:2])


def styles():
    for r in rows('styles'):
        print('styles', r['command'], paragraphs(r['saved'])[1], blocks(r['postHtml']))


def blank():
    for r in rows('blank'):
        print('blank', r['route'].ljust(9), r['command'].ljust(10), r.get('preHow'), r.get('preType'), r.get('postHow'), r.get('postType'), paragraphs(r['saved']))


def ranges():
    fixture = None
    for r in rows('range'):
        text_before = re.sub(r'<[^>]+>', '', r['preHtml']).split()
        text_after = re.sub(r'<[^>]+>', '', r['postHtml']).split()
        saved = paragraphs(r['saved'])
        undone = paragraphs(r['undone'])
        fixture = fixture or undone
        print('range', r['place'].ljust(18), r['command'].ljust(10), 'type', r['preType'], '->', r['postType'], 'textSame' if text_before == text_after else 'TEXT-DIFF',
              'undo1' if undone == fixture else 'UNDO-DIFF', blocks(r['preHtml'])[:9], '=>', blocks(r['postHtml'])[:12])


for part in PARTS:
    if part in ('caret', 'table'):
        caret(part)
    elif part == 'undo':
        undo()
    elif part == 'styles':
        styles()
    elif part == 'blank':
        blank()
    elif part == 'range':
        ranges()
