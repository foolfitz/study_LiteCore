#!/usr/bin/env python3
"""OWNER ONLY: compile the small S5 harness from captured source bytes; no core build."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
TOOLS=ROOT/'wasm_sdk_probe/tools'
COMPILED=('v23_native_s5.cpp','v23_native_s5_sequence.hpp','link_native_extend_signatures.cpp')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',action='store_true',required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    if out.exists():p.error('build output must be fresh')
    compiler=shutil.which('g++')
    if not compiler:p.error('g++ unavailable')
    include=ROOT/'libreoffice-26-8/include'
    headers={str(p.relative_to(ROOT)):sha(p) for p in sorted((include/'LibreOfficeKit').glob('*.h*')) if p.is_file()}
    if not headers:p.error('LibreOfficeKit headers missing')
    sources={str((TOOLS/n).relative_to(ROOT)):sha(TOOLS/n) for n in COMPILED}
    out.mkdir(parents=True);snap=out/'source';snap.mkdir()
    for name in COMPILED:shutil.copyfile(TOOLS/name,snap/name)
    binary=out/'v23-native-s5'
    command=[compiler,'-std=c++17','-O2','-I'+str(include),str(snap/'v23_native_s5.cpp'),'-ldl','-lpthread','-o',str(binary)]
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
