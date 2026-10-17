#!/usr/bin/env python3
"""Ruling 3 Q3: every v21 page entry's htmlSourceSha256 in the item-1 reports beside the installed host's packaged
e2-editor.html.  Reads only.  Output: html-source-equality-0226.txt (run from the repo root with python3 -I)."""
import glob
import json

m = json.load(open('/home/jiajun/Projects/Nextcloud_Apps/litecore/engine/MANIFEST.json'))
pkg = m['files']['e2-editor.html']['sha256']
print(f"installed host 0.2.26 engine/MANIFEST.json buildId {m['buildId']}: e2-editor.html {pkg}")
bad = 0
for f in sorted(glob.glob('findings/evidence/link-batch-v21/shakedown/evidence/item1/report-*.json')):
    r = json.load(open(f))
    for k, p in sorted((r.get('pages') or {}).items()):
        if not k.startswith('v21'):
            continue
        h = p.get('htmlSourceSha256')
        bad += h != pkg
        print(f"{f.split('/')[-1]:<75} {k:<8} {h} {'==' if h == pkg else '!='}")
print("all equal" if not bad else f"{bad} differ")
