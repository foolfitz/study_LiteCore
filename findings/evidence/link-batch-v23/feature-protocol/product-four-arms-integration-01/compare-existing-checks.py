#!/usr/bin/env python3
"""Read the before/after product reports and compare every original check's outcome.

Population comes from the bound original runner source, not a handwritten list. New four-arm
outcomes are outside this comparison and must be read by their independent judge.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'wasm_sdk_probe/tools'))
from run_e2_c_product_path import declared_check_ids
from v23_product_four_arms import ARMS


def sha(raw):return hashlib.sha256(raw).hexdigest()


def compare(before,after,original,patched):
    """Missing/duplicate/unreached evidence is NE; an established changed outcome is CHANGED."""
    problems=[];changes=[]
    for label,report,ids in (('unpatched',before,original),('patched',after,patched)):
        if report.get('complete') is not True:problems.append(label+' runner incomplete')
        if [r.get('id') for r in report.get('checks',[])]!=ids:problems.append(label+' recorded check population/order differs')
        if any(not isinstance(r.get('outcome'),str) or type(r.get('ok')) is not bool for r in report.get('checks',[])):
            problems.append(label+' check outcome/accounting absent')
    if [cid for cid in patched if cid not in {a['check'] for a in ARMS}]!=original:
        problems.append('original source population/order changed')
    if set(patched)-set(original)!={a['check'] for a in ARMS}:
        problems.append('new source population differs from the four-arm table')
    if before.get('browser')!=after.get('browser'):problems.append('browser differs')
    if not problems:
        indexed={r['id']:r for r in after['checks']}
        for old in before['checks']:
            new=indexed[old['id']]
            if (old.get('outcome'),old.get('ok'))!=(new.get('outcome'),new.get('ok')):
                changes.append({'id':old['id'],'before':{'outcome':old.get('outcome'),'ok':old.get('ok')},
                                'after':{'outcome':new.get('outcome'),'ok':new.get('ok')}})
    return {'verdict':'NOT_ESTABLISHED' if problems else 'CHANGED' if changes else 'UNCHANGED',
            'originalChecks':len(original),'problems':problems,'changes':changes}


def main():
    directory=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else HERE
    pins=json.loads((directory/'unpatched-source.json').read_bytes())
    source=subprocess.check_output(['git','show',pins['gitHead']+':'+pins['source']],cwd=ROOT)
    if sha(source)!=pins['sourceSha256'] or declared_check_ids(source.decode())!=pins['declaredChecks']:
        raise ValueError('original source binding differs')
    patched_pins=json.loads((directory/'patched-r2-source.json').read_bytes())
    patched_raw=subprocess.check_output(['git','show',patched_pins['gitHead']+':'+patched_pins['source']],cwd=ROOT)
    if sha(patched_raw)!=patched_pins['sourceSha256'] or declared_check_ids(patched_raw.decode())!=patched_pins['declaredChecks']:
        raise ValueError('patched source binding differs')
    patched=patched_pins['declaredChecks']
    records=[]
    for browser in ('chrome','firefox'):
        inputs={};reports=[]
        for mode in ('unpatched','patched-r2'):
            path=directory/(mode+'-'+browser+'.json');raw=path.read_bytes()
            inputs[path.name]=sha(raw);reports.append(json.loads(raw))
        if any(report.get('browser')!=browser for report in reports):raise ValueError('report filed under the wrong browser: '+browser)
        records.append({'browser':browser,'inputs':inputs,**compare(*reports,pins['declaredChecks'],patched)})
    verdict='NOT_ESTABLISHED' if any(r['verdict']=='NOT_ESTABLISHED' for r in records) else 'CHANGED' if any(r['verdict']=='CHANGED' for r in records) else 'UNCHANGED'
    print(json.dumps({'schema':1,'verdict':verdict,'readerSha256':sha(Path(__file__).read_bytes()),
        'unpatchedSourceSha256':pins['sourceSha256'],'patchedSourceSha256':sha(patched_raw),'browsers':records},indent=2))
    return 0 if verdict=='UNCHANGED' else 1


if __name__=='__main__':raise SystemExit(main())
