#!/usr/bin/env python3
"""Read existing M4 cell artifacts; no browser, build, service or count run.

Chrome admin and readonly are separate completed arms (03 and 05); those
reports' unrelated unfinished arms remain failures, not relabeled clean.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from run_calc_cell_native import cells_from_xml, NAMES

ROOT=Path(__file__).resolve().parents[2]

def load(root):
    cell=root/'findings/evidence/m4-cell-editing';host=root/'findings/evidence/host-0.2.34'
    read=lambda p:json.loads(p.read_text())
    return {'native':read(cell/'native/run-03-final/report.json'),
            'browser':read(cell/'browser-edit-03-download/report.json'),
            'host':{browser:{'admin':read(host/f'{admin}/report.json'),
                            'readonly':read(host/f'{readonly}/report.json')}
                for browser,admin,readonly in [('chrome','host-write-03','host-readonly-05'),
                                               ('firefox','host-firefox-07','host-firefox-07')]}}

def judge(model,root):
    problems=[];summary={}
    def require(ok,message):
        if not ok: problems.append(message)
    native=model['native']['checks']
    require(bool(native) and all(c['pass'] is True for c in native),'native checks empty/red')
    summary['nativeChecks']=len(native)
    runs=model['browser']['runs'];summary['browserChecks']=sum(len(r['checks']) for r in runs)
    require(sorted((r['browser'],r['repeat']) for r in runs)==[(b,n) for b in ('chrome','firefox') for n in (1,2,3)],'W-edit requires both browsers N=3')
    for run in runs:
        prefix=f"{run['browser']}-r{run['repeat']}"
        require(not run.get('error') and bool(run['checks']) and all(c['pass'] is True for c in run['checks']),prefix+' checks empty/red')
        saved=root/f'findings/evidence/m4-cell-editing/browser-edit-03-download/{prefix}-saved.ods'
        downloaded=root/f'findings/evidence/m4-cell-editing/browser-edit-03-download/downloads-{prefix}/cell-editing.ods'
        require(saved.read_bytes()==downloaded.read_bytes(),prefix+' disk download differs')
    summary['host']={}
    for browser,arms in model['host'].items():
        summary['host'][browser]={}
        for kind,completion in [('admin','writer-still-opens-saves'),('readonly','readonly-no-lock')]:
            checks=[c for c in arms[kind]['checks'] if c['id'].startswith(browser+'/')
                and (('/readonly-' in c['id']) == (kind=='readonly'))]
            require(bool(checks) and all(c['ok'] is True for c in checks),browser+'/'+kind+' empty/red')
            require(any(c['id']==browser+'/'+completion for c in checks),browser+'/'+kind+' never reached its final check')
            summary['host'][browser][kind]=len(checks)
        admin=next(r for r in arms['admin']['runs'] if r['browser']==browser and r.get('kind')!='readonly')
        puts=[r for r in admin['requests'] if r['method']=='PUT']
        require(len(puts)==1 and puts[0]['contentType']=='application/vnd.oasis.opendocument.spreadsheet'
            and bool(puts[0]['ifMatch']) and puts[0]['withToken'] and puts[0]['status'] in (200,201,204),browser+' raw conditional ODS PUT')
        require(admin['savedHost']['saves'][0]['outcome']=='saved' and admin['conflictHost']['saves'][0]['outcome']=='copy',browser+' host outcomes')
        ro=next(r for r in arms['readonly']['runs'] if r['browser']==browser and r.get('kind')=='readonly')
        require('/ods-viewer.html?' in ro['entry']['landed'],browser+' readonly route')
        directory='host-write-03' if browser=='chrome' else 'host-firefox-07'
        path=root/f'findings/evidence/host-0.2.34/{directory}/{browser}-server-saved.ods'
        content,cells=cells_from_xml(path)
        require(''.join(cells[(0,0,0)].itertext())=='Host inline '+browser+' 中文',browser+' saved XML text')
        require(cells[(0,2,0)].get('{'+NAMES['o']+'}value')=='85',browser+' saved XML result')
        style=cells[(0,1,1)].get('{'+NAMES['t']+'}style-name')
        attributes=content.find(f".//s:style[@s:name='{style}']/s:text-properties",NAMES)
        require(attributes is not None and attributes.get('{'+NAMES['f']+'}font-weight')=='bold'
            and attributes.get('{'+NAMES['f']+'}font-style')=='italic'
            and attributes.get('{'+NAMES['s']+'}text-underline-style')=='solid',browser+' saved XML formats')
        finalcopy=path.with_name(browser+'-conflict-copy.ods');_,copied=cells_from_xml(finalcopy)
        require(''.join(copied[(0,0,0)].itertext())=='After conflict '+browser,browser+' continuing copy XML')
        fixture=path.parent/'fixture/cell-editing.ods';expected=hashlib.sha256(fixture.read_bytes()).hexdigest()
        original=next(c for c in arms['admin']['checks'] if c['id']==browser+'/conflict-preserves-original')['raw']
        require(original['status']==200 and original['sha256']==expected,browser+' conflict original hash')
    return problems,summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--red-cases',action='store_true');args=parser.parse_args()
    model=load(ROOT);problems,summary=judge(model,ROOT)
    if args.red_cases:
        controls=[]
        for label,mutate in [
            ('empty native',lambda m:m['native'].update(checks=[])),
            ('missing Firefox W-edit',lambda m:m['browser'].update(runs=[r for r in m['browser']['runs'] if r['browser']=='chrome'])),
            ('real host conflict red',lambda m:next(c for c in m['host']['chrome']['admin']['checks'] if c['id']=='chrome/copy-success-clears-dirty').update(ok=False)),
        ]:
            broken=copy.deepcopy(model);mutate(broken);bad,_=judge(broken,ROOT);controls.append({'case':label,'red':bool(bad)})
        summary['redCases']=controls
        problems.extend(c['case']+' stayed green' for c in controls if not c['red'])
    print(json.dumps({'problems':problems,**summary},indent=2));raise SystemExit(bool(problems))
