#!/usr/bin/env python3
"""Opus seat, review 1, A12/A13 (copies only).
A12: out/ with d7iii's unipoll round 4 missing (an honest crash leaves no jsonl/fodt) -> verdict, exit.
A13: out/ with every D7 arm dropped from arms.json -> verdict, exit (the arm list is read from the run).
Usage: python3 -I a12_d7_missing.py <ordered-commands dir> <work dir>"""
import json, pathlib, shutil, subprocess, sys
oc, work = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
def fresh(name):
    d = work / name
    if d.exists(): shutil.rmtree(d)
    shutil.copytree(oc / 'out', d); return d
def run(out):
    p = subprocess.run([sys.executable, '-I', str(oc / 'tool' / 'read_results.py'), str(out)], capture_output=True, text=True)
    return p.returncode, [l for l in p.stdout.splitlines() if l.startswith(('d7', 'D8', 'VERDICT'))]
a = fresh('A12')
for ext in ('jsonl', 'stderr', 'fodt.gz'):
    (a / 'd7iii' / f'unipoll-r4.{ext}').unlink()
print('A12', *run(a), sep='\n  ')
b = fresh('A13')
arms = [x for x in json.loads((b / 'arms.json').read_text()) if not x['name'].startswith('d7')]
(b / 'arms.json').write_text(json.dumps(arms))
print('A13', *run(b), sep='\n  ')
