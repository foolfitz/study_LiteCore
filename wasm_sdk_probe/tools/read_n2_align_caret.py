#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 N2's reader: on each caret place, does a route leave the caret where the dispatch alone leaves it?  The saved
document says: X was inserted after the route.  read_n2_align_caret.py DIR"""
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
ROOT = Path(sys.argv[1])


def paragraphs(url):
    with zipfile.ZipFile(url[len('file://'):]) as z:
        root = ET.fromstring(z.read('content.xml'))
    return [''.join(p.itertext()) for p in root.iter() if p.tag in (TEXT + 'p', TEXT + 'h')]


rows = [json.loads(line) for line in (ROOT / 'observations.jsonl').read_text().splitlines()]
truth = {(r['place'], r['command']): paragraphs(r['saved']) for r in rows if r['route'] == 'truth'}
summary = {}
for r in rows:
    if r['route'] == 'truth':
        continue
    equal = paragraphs(r['saved']) == truth[(r['place'], r['command'])]
    aligns = re.findall(r'<(?:p|h\d)\b[^>]*?align="(\w+)"', r['html'])
    summary.setdefault(r['route'], []).append(equal)
    r['equal'] = equal
    print(r['route'].ljust(12), r['command'][5:].ljust(11), r['place'].ljust(15), 'SAME' if equal else 'MOVED', r['how'], r['typeAtRead'], r['typeAfter'], aligns,
          '' if equal else [p[:30] for p, q in zip(paragraphs(r['saved']), truth[(r['place'], r['command'])]) if p != q])
print({k: f'{sum(v)}/{len(v)}' for k, v in summary.items()})
