#!/usr/bin/env python3
"""Diagnostic (not an oracle run): native S5 deletion cells with every member settled.

Compiles v23_native_s5_settled.cpp from captured source bytes into OUT/build, runs the named
cells once each in a fresh document, then compares each after-save's paragraph text with
run-01's back-to-back after-save of the same cell.  Refuses an existing OUT."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from odt_paragraphs import paragraph_texts_from_xml
ROOT=Path(__file__).resolve().parents[2]
TOOLS=ROOT/'wasm_sdk_probe/tools'
COMPILED=('v23_native_s5_settled.cpp','v23_native_s5_sequence.hpp','link_native_extend_signatures.cpp')
FIXTURE=ROOT/'findings/evidence/link-batch/extend-signatures/run-20261013T095104Z/fixture-as-run.fodt'
RUN01=ROOT/'findings/evidence/link-batch-v23/feature-protocol/s5-native/run-01'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def paragraphs(path):
    with zipfile.ZipFile(path) as z:return paragraph_texts_from_xml(z.read('content.xml'))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--cells',type=Path,required=True)
    p.add_argument('--install',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    if out.exists():p.error('output must be fresh')
    cells=[l.strip() for l in a.cells.read_text().splitlines() if l.strip()]
    if not cells or len(set(cells))!=len(cells):p.error('empty or repeated cell list')
    out.mkdir(parents=True);build=out/'build';src=build/'source';src.mkdir(parents=True)
    for n in COMPILED:shutil.copyfile(TOOLS/n,src/n)
    include=ROOT/'libreoffice-26-8/include';binary=build/'v23-native-s5-settled'
    cmd=['g++','-std=c++17','-O2','-I'+str(include),str(src/COMPILED[0]),'-ldl','-lpthread','-o',str(binary)]
    b=subprocess.run(cmd,capture_output=True,text=True)
    receipt={'argv':cmd,'exitCode':b.returncode,'stdout':b.stdout,'stderr':b.stderr,
             'sources':{n:sha(TOOLS/n) for n in COMPILED},'snapshots':{n:sha(src/n) for n in COMPILED},
             'binary':sha(binary) if binary.is_file() else None}
    (build/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if b.returncode:return 3
    inventory={json.loads(l)['id'] for l in subprocess.check_output([str(binary),'--inventory'],text=True).splitlines() if l.strip()}
    if set(cells)-inventory:raise SystemExit('cells outside the native-capable inventory')
    (out/'cells.txt').write_text('\n'.join(cells)+'\n');(out/'profile').mkdir();(out/'saves').mkdir()
    shutil.copyfile(FIXTURE,out/'fixture.fodt')
    env=dict(os.environ,SAL_USE_VCLPLUGIN='svp');env.pop('SAL_LOK_OPTIONS',None);env.pop('OC_A11Y',None)
    run=['nice','-n','10',str(binary),str(a.install.resolve()),(out/'profile').as_uri(),(out/'fixture.fodt').as_uri(),str(out/'saves'),str(out/'cells.txt')]
    (out/'command.json').write_text(json.dumps({'argv':run,'mode':'default-native-queued','interMemberSettle':'every member, 800 ms quiet / 8000 ms cap',
        'environment':{'SAL_USE_VCLPLUGIN':'svp','SAL_LOK_OPTIONS':None,'OC_A11Y':None},'installSha256':{'libmergedlo.so':sha(a.install/'libmergedlo.so')}},indent=2)+'\n')
    with (out/'native.jsonl').open('x') as so,(out/'native.stderr').open('x') as se:
        r=subprocess.run(run,stdout=so,stderr=se,env=env)
    rows={x['id']:x for x in (json.loads(l) for l in (out/'native.jsonl').read_text().splitlines() if l.strip()) if 'id' in x}
    old={x['id']:x for x in (json.loads(l) for l in (RUN01/'native.jsonl').read_text().splitlines() if l.strip()) if 'id' in x}
    comparison=[]
    for c in cells:
        row=rows.get(c);prev=old[c]
        if row is None:comparison.append({'id':c,'status':'missing'});continue
        settled=paragraphs(out/'saves'/row['afterFile']);before=paragraphs(out/'saves'/row['beforeFile'])
        backtoback=paragraphs(RUN01/'saves'/prev['afterFile'])
        comparison.append({'id':c,'settledEqualsBackToBack':settled==backtoback,
            'removedSettled':sum(map(len,before))+len(before)-sum(map(len,settled))-len(settled),
            'removedBackToBack':sum(map(len,before))+len(before)-sum(map(len,backtoback))-len(backtoback),
            'settleCapped':any(s['settleMs']<0 for s in row['steps']),
            'stepSelections':[s['state']['getTextSelection'] for s in row['steps']]})
    summary={'exitCode':r.returncode,'cells':len(cells),'settledEqualsBackToBack':sum(1 for c in comparison if c.get('settledEqualsBackToBack')),
             'capped':sum(1 for c in comparison if c.get('settleCapped')),'comparison':comparison,
             'artifacts':{str(f.relative_to(out)):sha(f) for f in sorted(list((out/'saves').glob('*.odt'))+[out/n for n in ('native.jsonl','native.stderr','command.json','cells.txt','fixture.fodt','build/build-receipt.json')])}}
    (out/'comparison.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('comparison','artifacts')}))
    return r.returncode
if __name__=='__main__':raise SystemExit(main())
