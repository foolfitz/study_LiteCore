#!/usr/bin/env python3
"""Read final I-entry/R-select artifacts; no engine, browser or service calls."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path

from run_calc_cell_native import cells_from_xml

PROJECT=Path(__file__).resolve().parents[1]
TOOL=PROJECT/'tools/probe_calc_input_range_full.py'


def required(manifest):
    # Literal checks come from executable call sites, dynamic populations from
    # the fixture used by that same runner. No second hand-maintained check list.
    names={'opened-cell'}
    for n in ast.walk(ast.parse(TOOL.read_text())):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str):
            if n.func.id=='check':names.add(n.args[0].value)
            if n.func.id=='view':names.add(n.args[0].value+'/tiles')
    for c in manifest['selectionCases']:
        names.update(('range/'+c['id'],'bounded/'+c['id']))
    names.update('pending/'+c for c in manifest['pendingCases'])
    names.update('range/'+k for k in manifest['shiftKeys'])
    for f in manifest['formats']:names.update(('range/toolbar-disabled/'+f,'range/refuses/'+f))
    names.update('save/reopen/'+a for a,_ in manifest['reopenCases'])
    return names


def score(root,report):
    bad=[]
    manifest=json.loads((root/'fixture/manifest.json').read_text())
    if not manifest.get('selectionCases') or not manifest.get('pendingCases'):return ['empty fixture population']
    wanted=required(manifest)
    runs=report.get('runs',[])
    if len(runs)!=6 or {(r['browser'],r['repeat']) for r in runs}!={(b,n) for b in ('chrome','firefox') for n in (1,2,3)}:bad.append('need both browsers N=3')
    hashes=json.loads((root/'mirror-sources.json').read_text())['sha256']
    for name,source in [('ods-editor-app.js','web/ods-editor-app.js'),('ods-editor.html','web/ods-editor.html'),('spreadsheet-shell/calc-editor-session.js','spreadsheet-shell/calc-editor-session.js')]:
        if hashes.get(name)!=hashlib.sha256((PROJECT/source).read_bytes()).hexdigest():bad.append('candidate source mismatch: '+name)
    for run in runs:
        label=f"{run['browser']}-r{run['repeat']}"
        checks=run.get('checks',[]);ids=[c['id'] for c in checks]
        if len(ids)!=len(set(ids)) or set(ids)!=wanted:bad.append(label+' missing/extra/duplicate checks: '+str(sorted(wanted-set(ids))))
        if run.get('error') or any(c.get('pass') is not True for c in checks):bad.append(label+' failed check/error')
        if run.get('toolSha256')!=hashlib.sha256(TOOL.read_bytes()).hexdigest():bad.append(label+' tool identity mismatch')
        if run.get('selectionCases')!=[c['id'] for c in manifest['selectionCases']] or run.get('pendingCases')!=manifest['pendingCases']:bad.append(label+' case population mismatch')
        for check in checks:
            snapfile=check.get('actual',{}).get('snapshot') if isinstance(check.get('actual'),dict) else None
            if snapfile:
                snap=json.loads((root/snapfile).read_text())
                if not snap['tiles'] or snap['visibleTiles']<=0 or any(t.get('matched') is not True for t in snap['tiles']) or snap['revision']!=snap['context']['revision']:bad.append(label+' invalid tile evidence')
        saved=root/(label+'-saved.ods')
        if not saved.exists():bad.append(label+' missing download');continue
        _,cells=cells_from_xml(saved)
        text=lambda p,c,r:''.join(cells[(p,c,r)].itertext())
        expected={(0,0,0):'active replacement',(0,1,1):'replacement 中文',(0,2,0):'=B1*9',(0,6,1):'組字完成',(0,0,1):'鄰格必須保留',(1,0,0):'第二表不應改動',(0,2,1):run.get('pendingSavedInput')}
        if any(text(*key)!=value for key,value in expected.items()):bad.append(label+' XML mismatch')
    return bad


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--red-cases',action='store_true');a=p.parse_args()
    report=json.loads((a.root/'report.json').read_text());bad=score(a.root,report)
    print(json.dumps({'runs':len(report.get('runs',[])),'checks':sum(len(r.get('checks',[])) for r in report.get('runs',[])),'problems':bad}))
    if bad:return 1
    if a.red_cases:
        mutations={
            'empty runs':lambda r:r.update(runs=[]),
            'missing browser':lambda r:r.update(runs=r['runs'][:3]),
            'empty checks':lambda r:r['runs'][0].update(checks=[]),
            'missing check':lambda r:r['runs'][0]['checks'].pop(),
            'false check':lambda r:r['runs'][0]['checks'][0].update({'pass':False}),
            'wrong tool':lambda r:r['runs'][0].update(toolSha256='0'*64),
        }
        for name,mutate in mutations.items():
            broken=copy.deepcopy(report);mutate(broken)
            assert score(a.root,broken),name+' incorrectly green'
            print('RED '+name)
    return 0


if __name__=='__main__':raise SystemExit(main())
