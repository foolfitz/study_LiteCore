#!/usr/bin/env python3
"""Compile the finding 168 native route harness from captured source bytes; no core build.

A single-file g++ build of a small harness: the agent may run it after checking `uptime` and
`pgrep -a make` (owner decision 2026-10-28, AGENTS.md).  Same receipt form as
build_v23_native_s5_type_owner.py, whose bytes stay unchanged because frozen runs bind them."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_v23_native_s5_owner import ROOT,TOOLS,sha
COMPILED=('f168_native_table_type_routes.cpp','link_native_extend_signatures.cpp')
BINARY='f168-native-table-type-routes'
# The archived signature setup the S5 native runs used (type-build-02 receipt).
SIGNATURE_SOURCE_SHA256='1e29f73bfa0a0b73a5ced6d5f5a91fbaac48bfdfa1fb1c1799514aa0913eef17'
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',action='store_true',required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    if out.exists():p.error('build output must be fresh')
    if sha(TOOLS/COMPILED[1])!=SIGNATURE_SOURCE_SHA256:p.error('retained signature source changed')
    compiler=shutil.which('g++')
    if not compiler:p.error('g++ unavailable')
    include=ROOT/'libreoffice-26-8/include'
    headers={str(p.relative_to(ROOT)):sha(p) for p in sorted((include/'LibreOfficeKit').glob('*.h*')) if p.is_file()}
    if not headers:p.error('LibreOfficeKit headers missing')
    sources={str((TOOLS/n).relative_to(ROOT)):sha(TOOLS/n) for n in COMPILED}
    out.mkdir(parents=True);snap=out/'source';snap.mkdir()
    for name in COMPILED:shutil.copyfile(TOOLS/name,snap/name)
    binary=out/BINARY
    command=[compiler,'-std=c++17','-O2','-I'+str(include),str(snap/COMPILED[0]),'-ldl','-lpthread','-o',str(binary)]
    receipt={'schema':1,'sources':sources,'headers':headers,'argv':command,
             'compiler':{'path':compiler,'sha256':sha(Path(compiler)),'version':subprocess.check_output([compiler,'--version'],text=True)}}
    (out/'build-inputs.json').write_text(json.dumps(receipt,indent=2)+'\n')
    with (out/'build.stdout').open('x') as stdout,(out/'build.stderr').open('x') as stderr:
        result=subprocess.run(command,stdout=stdout,stderr=stderr)
    receipt['exitCode']=result.returncode
    receipt['protectedInputsUnchanged']=all(sha(ROOT/p)==v for p,v in {**sources,**headers}.items())
    receipt['snapshotsMatch']=all(sha(snap/n)==sources[str((TOOLS/n).relative_to(ROOT))] for n in COMPILED)
    receipt['binary']={'path':str(binary),'sha256':sha(binary)} if binary.is_file() else None
    (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
    return result.returncode or int(not receipt['protectedInputsUnchanged'] or not receipt['snapshotsMatch'])
if __name__=='__main__':raise SystemExit(main())
