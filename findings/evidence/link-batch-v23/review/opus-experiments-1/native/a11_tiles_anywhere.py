#!/usr/bin/env python3
"""Opus seat, review 1, A11: count INVALIDATE_TILES records in every committed native output (out, out-n1,
smoke, smoke-n1), per mode.  Usage: python3 -I a11_tiles_anywhere.py <ordered-commands dir>"""
import collections, json, pathlib, sys
oc = pathlib.Path(sys.argv[1])
for d in ('out', 'out-n1', 'smoke', 'smoke-n1'):
    n = collections.Counter(); files = collections.Counter()
    for f in (oc / d).glob('*/*.jsonl'):
        mode = f.name.split('-r')[0]
        files[mode] += 1
        for x in f.read_text().splitlines():
            if 'INVALIDATE_TILES' in x:
                n[mode] += x.count('LOK_CALLBACK_INVALIDATE_TILES')
    print(f'{d:9} files per mode {dict(files)}; INVALIDATE_TILES occurrences per mode {dict(n)}')
