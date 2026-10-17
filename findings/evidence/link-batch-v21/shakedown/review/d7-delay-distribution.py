#!/usr/bin/env python3
"""Descriptive only (not a judge): D7 ask delay = ask7.tPosted - response.t per press, per D1 report.
Usage: python3 -I d7-delay-distribution.py <report.json>..."""
import json, sys, statistics as st
from collections import defaultdict
for path in sys.argv[1:]:
    r = json.load(open(path))
    rounds = r['results']['d1']['rounds']
    print('==', path.split('/')[-1], r.get('browser'), r.get('browserVersion'), 'rounds', len(rounds))
    if rounds:
        print('   round keys', list(rounds[0].keys())[:30])
        p0 = (rounds[0].get('presses') or [{}])[0]
        print('   press keys', list(p0.keys()))
    ds = []; byfam = defaultdict(list); late = []
    for rec in rounds:
        for i, p in enumerate(rec.get('presses') or []):
            a = p.get('ask7') or {}; s = p.get('response') or {}
            if a.get('tPosted') is None or s.get('t') is None: continue
            d = a['tPosted'] - s['t']
            ds.append(d)
            fam = rec['arm'].split('-')[0]
            byfam[fam].append(d)
            if d > 520: late.append((rec['arm'], rec.get('round'), i, round(d,1), s.get('completion')))
    ds.sort()
    print('   n', len(ds), 'min', ds[0], 'p50', st.median(ds), 'p90', ds[int(.9*len(ds))], 'max', ds[-1])
    bins = defaultdict(int)
    for d in ds: bins[int((d-500)//5)*5] += 1
    print('   bins (ms past 500):', dict(sorted(bins.items())))
    for f, v in sorted(byfam.items()):
        v.sort(); print(f'   {f:5} n={len(v):3} min={v[0]:.1f} p50={st.median(v):.1f} max={v[-1]:.1f} >505:{sum(x>505 for x in v)}')
    for l in late: print('   late', l)
