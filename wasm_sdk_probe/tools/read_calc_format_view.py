#!/usr/bin/env python3
"""Re-read finding 165's existing native-model/DOM-vs-engine snapshots."""
import argparse
import json
from pathlib import Path

def score(root,repeats):
    report=json.loads((root/'report.json').read_text());problems=[];tiles=0;views=0
    expected={(b,n) for b in ('chrome','firefox') for n in range(1,repeats+1)}
    if {(r['browser'],r['repeat']) for r in report['runs']}!=expected:problems.append('missing browser round')
    for run in report['runs']:
        if run.get('error') or not run['checks'] or not all(c['pass'] is True for c in run['checks']):problems.append(f"{run['browser']} r{run['repeat']} red/incomplete")
        for fmt in ('bold','italic','underline'):
            for mode in ('inline','cell'):
                path=root/f"{run['browser']}-r{run['repeat']}-{fmt}-{mode}.json"
                if not path.exists():problems.append(str(path)+' absent');continue
                snapshot=json.loads(path.read_text());views+=1;tiles+=len(snapshot['tiles'])
                if snapshot['revision']!=snapshot['context']['revision'] or snapshot['visibleTiles']<=0 or not snapshot['tiles'] or not all(t['matched'] is True for t in snapshot['tiles']) or snapshot['state']['tileErrors']!=0:problems.append(path.name+' stale/empty/error')
    return {'problems':problems,'views':views,'tilesCompared':tiles,'checks':sum(len(r['checks']) for r in report['runs'])}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--repeats',type=int,default=3);args=p.parse_args()
    result=score(args.root,args.repeats);print(json.dumps(result,indent=2));raise SystemExit(bool(result['problems']))
