#!/usr/bin/env python3
"""Native S5 type-family references, run 02 (fable ruling 3); never compiles. One run, no retry.

Only the 56 native-capable type cells.  run_v23_native_s5.py stays unchanged because run-01's
identity binds its bytes; this module reuses its pure helpers."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_v23_native_s5 as base
from run_v23_native_s5 import ROOT,TOOLS,sha,read_inventory
SOURCES=[TOOLS/name for name in ('v23_native_s5_type.cpp','v23_native_s5_sequence.hpp',
    'link_native_extend_signatures.cpp','run_v23_native_s5_type.py','read_v23_native_s5_type.py',
    'run_v23_native_s5.py','read_v23_native_s5.py','v23_feature_s_cases.py','run_merge_wasm_shakedown.py',
    'odt_paragraphs.py','build_v23_native_s5_owner.py','build_v23_native_s5_type_owner.py')]

def cases():
    table,rows=base.cases()
    return table,[row for row in rows if row['family']=='type']

def validate_build_receipt(binary,build_receipt):
    from build_v23_native_s5_type_owner import COMPILED
    receipt=json.loads(build_receipt.read_text())
    if receipt.get('exitCode')!=0 or receipt.get('protectedInputsUnchanged') is not True or receipt.get('snapshotsMatch') is not True:
        raise ValueError('owner build receipt is not successful')
    if receipt.get('binary')!={'path':str(binary),'sha256':sha(binary)}:
        raise ValueError('binary differs from actual owner build receipt')
    required={str((TOOLS/n).relative_to(ROOT)):sha(TOOLS/n) for n in COMPILED}
    if receipt.get('sources')!=required:raise ValueError('compiled sources differ from owner build receipt')
    if not receipt.get('headers'):raise ValueError('owner build receipt has no headers')
    for name,value in receipt['headers'].items():
        if sha(ROOT/name)!=value:raise ValueError('compiled header changed: '+name)
    return {'path':str(build_receipt.resolve()),'sha256':sha(build_receipt)}

def pins(binary,install,build_receipt):
    receipt_binding=validate_build_receipt(binary.resolve(),build_receipt)
    libraries=sorted(install.glob('*.so'))+sorted(install.glob('*.so.*'))
    libraries=sorted(set(p.resolve() for p in libraries if p.is_file()))
    if not libraries:raise ValueError('native install has no shared libraries')
    return {'buildReceipt':receipt_binding,'binary':{'path':str(binary.resolve()),'sha256':sha(binary)},
            'sources':{str(p.relative_to(ROOT)):sha(p) for p in SOURCES},
            'libraries':{str(p):sha(p) for p in libraries},
            'inputPins':{str(ROOT/p):value for p,value in cases()[0]['inputPins'].items()}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','install','out','build-receipt'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.binary=a.binary.resolve();a.install=a.install.resolve();a.out=a.out.resolve()
    if a.out.exists():p.error('output must be fresh; failed runs are preserved')
    table,rows=cases();identity=pins(a.binary,a.install,a.build_receipt)
    inventory=subprocess.check_output([str(a.binary),'--inventory'],text=True)
    read_inventory(inventory,rows)
    paragraphs=subprocess.check_output([str(a.binary),'--paragraphs'],text=True).splitlines()
    from odt_paragraphs import paragraph_texts_from_xml
    fixture=ROOT/table['fixture']['path']
    if paragraphs!=paragraph_texts_from_xml(fixture.read_bytes()):raise ValueError('compiled fixture text mismatch')
    a.out.mkdir(parents=True);(a.out/'profile').mkdir();(a.out/'saves').mkdir()
    shutil.copyfile(fixture,a.out/'fixture.fodt')
    (a.out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    (a.out/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
    (a.out/'inventory.jsonl').write_text(inventory)
    env=dict(os.environ,SAL_USE_VCLPLUGIN='svp');env.pop('SAL_LOK_OPTIONS',None);env.pop('OC_A11Y',None)
    cmd=['nice','-n','10',str(a.binary),str(a.install),(a.out/'profile').as_uri(),
         (a.out/'fixture.fodt').as_uri(),str(a.out/'saves')]
    (a.out/'command.json').write_text(json.dumps({'argv':cmd,'mode':'default-native-queued',
        'interMemberSettle':{'after':'Shift member','quietMs':800,'capMs':8000,'authority':'fable ruling 3'},
        'environment':{'SAL_USE_VCLPLUGIN':'svp','SAL_LOK_OPTIONS':None,'OC_A11Y':None},
        'executionsPerCell':1,'homeEndConditional':True},indent=2)+'\n')
    with (a.out/'native.jsonl').open('x') as stdout,(a.out/'native.stderr').open('x') as stderr:
        result=subprocess.run(cmd,stdout=stdout,stderr=stderr,env=env)
    try:after=pins(a.binary,a.install,a.build_receipt)
    except (OSError,ValueError,KeyError) as error:after={'captureError':str(error)}
    (a.out/'completion.json').write_text(json.dumps({'exitCode':result.returncode,
        'protectedInputsUnchanged':after==identity,'afterIdentity':after,
        'artifacts':{str(f.relative_to(a.out)):sha(f) for f in sorted(list((a.out/'saves').glob('*.odt'))+[a.out/n for n in ('native.jsonl','native.stderr','identity.json','cases.json','inventory.jsonl','command.json','fixture.fodt')])}},indent=2)+'\n')
    return result.returncode or (0 if after==identity else 1)
if __name__=='__main__':raise SystemExit(main())
