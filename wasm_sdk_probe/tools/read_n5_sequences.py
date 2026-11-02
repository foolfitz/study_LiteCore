#!/usr/bin/env python3
"""SPEC-P-demo-batch-4 N5's reader: every press verified or refused as designed, each saved file agrees with what the read said, and a refused
press left the file as the press before it did.  read_n5_sequences.py DIR"""
import json
from pathlib import Path
import sys

source = (Path(__file__).parent / 'read_n4_caret_read.py').read_text().split('def rows(part):')[0]
n4 = {}
exec(compile(source, 'read_n4_caret_read.py', 'exec'), n4)
document = n4['document']
ROOT = Path(sys.argv[1])
rows = [json.loads(line) for line in (ROOT / 'observations.jsonl').read_text().splitlines()]
counts, misses = {}, []
previous = None
for r in rows:
    counts[r['outcome']] = counts.get(r['outcome'], 0) + 1
    saved = document(r['saved'])
    if r['outcome'].startswith('refused'):
        if previous and previous[0] == r['sequence'] and saved != previous[1]:
            misses.append((r['sequence'], r['step'], 'a refusal changed the file'))
    else:
        for row in r['after']:
            hit = [p for p in saved if p['text'].startswith(row['text']) and p['block'] == row['block'] and (p['list'] == row['list'] or (row['list'] and p['list']))]
            if not hit:
                misses.append((r['sequence'], r['step'], row, [p for p in saved if p['text'].startswith(row['text'])][:2]))
    previous = (r['sequence'], saved)
print({'presses': len(rows), 'outcomes': counts, 'fileDisagrees': len(misses)})
for m in misses[:20]:
    print(m)
