#!/usr/bin/env python3
"""Freeze exact owner-built/accepted bytes once; no compile and no relink."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[3]
PROBE=ROOT/'wasm_sdk_probe'
OUT=Path(__file__).resolve().parent
EVIDENCE=ROOT/'findings/evidence/calc-range-autosave'
SOURCE=PROBE/'build/ods/editor-v2/profile'
TARGET=PROBE/'dist/profiles/ods-editor-v2'
ARCHIVE=PROBE/'build/archive/ods-editor-v2-5bc53490-worker-0bed22bd'

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    assert not TARGET.exists() and not ARCHIVE.exists(),'a frozen successor is never overwritten'
    owner=json.loads((EVIDENCE/'owner-build.json').read_text())
    for name,digest in owner['sha256'].items():assert sha(SOURCE/name)==digest,'owner build changed: '+name
    native=json.loads((EVIDENCE/'native-01/report.json').read_text())
    assert native['pass'] is True and len(native['checks'])==22 and all(c['pass'] for c in native['checks'])
    for tool,directory in [('read_calc_range_format.py','range-browser-03'),('read_calc_autosave.py','auto-v2-02')]:
        subprocess.run(['python3',str(PROBE/'tools'/tool),str(EVIDENCE/directory),'--red-cases'],check=True)
    hashes={p.name:sha(p) for p in SOURCE.iterdir() if p.is_file()}
    assert len(hashes)==6,'unexpected engine file population'
    shutil.copytree(SOURCE,TARGET)
    shutil.copytree(SOURCE,ARCHIVE)
    for destination in (TARGET,ARCHIVE):
        assert {p.name:sha(p) for p in destination.iterdir() if p.is_file()}==hashes
    (ARCHIVE/'ATTRIBUTION.md').write_text('# Exact Calc range successor\n\nOwner-built ods-editor-v2: wasm 5bc53490 / worker 0bed22bd. This archive and the new frozen profile were copied byte-for-byte from the accepted development profile after native, range and autosave acceptance. No existing profile was modified. See findings/evidence/host-0.2.37/freeze-v2.json for complete file hashes and accepted cohorts.\n')
    record={'profile':'ods-editor-v2','source':str(SOURCE),'frozen':str(TARGET),'archive':str(ARCHIVE),
        'sha256':hashes,'nativeCases':22,'rangeCohort':'range-browser-03','autosaveCohort':'auto-v2-02',
        'compileOrRelinkPerformedByAgent':False}
    (OUT/'freeze-v2.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'profile':record['profile'],'files':len(hashes),'frozen':str(TARGET)}))

if __name__=='__main__':main()
