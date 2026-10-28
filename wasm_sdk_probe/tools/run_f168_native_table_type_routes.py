#!/usr/bin/env python3
"""Finding 168 native route comparison; never compiles. One run into a fresh directory, no retry.

Runs the owner-built f168 harness on the bound S5 fixture (native run-03's copy) with run-03's
environment (svp, SAL_LOK_OPTIONS and OC_A11Y removed, nice 10).  --lc-all reruns the same arms
with LC_ALL/LANG set, the locale perturbation for the later cell's suffix."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_v23_native_s5_owner import ROOT,TOOLS,sha
from build_f168_native_owner import COMPILED
FIXTURE=ROOT/'findings/evidence/link-batch-v23/feature-protocol/s5-native/run-03/fixture.fodt'
FIXTURE_SHA256='ede9cb038b8edabfb8dc6c05fb46b15deacfc6f529756ca816096bfd2c18b7bc'
SOURCES=[TOOLS/n for n in (*COMPILED,'build_f168_native_owner.py','run_f168_native_table_type_routes.py',
    'read_f168_native_table_type_routes.py','odt_paragraphs.py')]

def validate_build_receipt(binary,build_receipt):
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
    receipt_binding=validate_build_receipt(binary,build_receipt)
    libraries=sorted(set(p.resolve() for p in [*install.glob('*.so'),*install.glob('*.so.*')] if p.is_file()))
    if not libraries:raise ValueError('native install has no shared libraries')
    return {'buildReceipt':receipt_binding,'binary':{'path':str(binary),'sha256':sha(binary)},
            'sources':{str(p.relative_to(ROOT)):sha(p) for p in SOURCES},
            'libraries':{str(p):sha(p) for p in libraries},
            'fixture':{'path':str(FIXTURE.relative_to(ROOT)),'sha256':sha(FIXTURE)}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','install','out','build-receipt'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--rounds',type=int,default=3);p.add_argument('--lc-all')
    a=p.parse_args();a.binary=a.binary.resolve();a.install=a.install.resolve();a.out=a.out.resolve()
    if a.out.exists():p.error('output must be fresh; failed runs are preserved')
    if sha(FIXTURE)!=FIXTURE_SHA256:p.error('bound fixture changed')
    identity=pins(a.binary,a.install,a.build_receipt)
    inventory=subprocess.check_output([str(a.binary),'--inventory'],text=True)
    paragraphs=subprocess.check_output([str(a.binary),'--paragraphs'],text=True).splitlines()
    from odt_paragraphs import paragraph_texts_from_xml
    if paragraphs!=paragraph_texts_from_xml(FIXTURE.read_bytes()):raise ValueError('compiled fixture text mismatch')
    a.out.mkdir(parents=True);(a.out/'profile').mkdir();(a.out/'saves').mkdir()
    shutil.copyfile(FIXTURE,a.out/'fixture.fodt')
    (a.out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    (a.out/'inventory.jsonl').write_text(inventory)
    env=dict(os.environ,SAL_USE_VCLPLUGIN='svp');env.pop('SAL_LOK_OPTIONS',None);env.pop('OC_A11Y',None)
    if a.lc_all is not None:env['LC_ALL']=a.lc_all;env['LANG']=a.lc_all
    cmd=['nice','-n','10',str(a.binary),str(a.install),(a.out/'profile').as_uri(),
         (a.out/'fixture.fodt').as_uri(),str(a.out/'saves'),str(a.rounds)]
    (a.out/'command.json').write_text(json.dumps({'argv':cmd,'rounds':a.rounds,
        'interMemberSettle':{'after':'each Shift key','quietMs':800,'capMs':8000},
        'environment':{'SAL_USE_VCLPLUGIN':'svp','SAL_LOK_OPTIONS':None,'OC_A11Y':None,
                       'LC_ALL':env.get('LC_ALL'),'LANG':env.get('LANG')}},indent=2)+'\n')
    with (a.out/'native.jsonl').open('x') as stdout,(a.out/'native.stderr').open('x') as stderr:
        result=subprocess.run(cmd,stdout=stdout,stderr=stderr,env=env)
    try:after=pins(a.binary,a.install,a.build_receipt)
    except (OSError,ValueError,KeyError) as error:after={'captureError':str(error)}
    (a.out/'completion.json').write_text(json.dumps({'exitCode':result.returncode,
        'protectedInputsUnchanged':after==identity,'afterIdentity':after,
        'artifacts':{str(f.relative_to(a.out)):sha(f) for f in sorted(list((a.out/'saves').glob('*.odt'))+[a.out/n for n in ('native.jsonl','native.stderr','identity.json','inventory.jsonl','command.json','fixture.fodt')])}},indent=2)+'\n')
    return result.returncode or (0 if after==identity else 1)
if __name__=='__main__':raise SystemExit(main())
