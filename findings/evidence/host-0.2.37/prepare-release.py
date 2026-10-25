#!/usr/bin/env python3
"""Package an isolated host worktree and archive exact reviewed bytes."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
PROBE=ROOT/'wasm_sdk_probe'
OUT=Path(__file__).resolve().parent
APP=PROBE/'build/host-0.2.37/litecore'
OLD=PROBE/'build/archive/host-0.2.36-engine-2b17a0e790b24eb3'
sys.path.insert(0,str(PROBE/'tools'))
from package_m3_engine import package

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    assert not (OUT/'release.json').exists(),'a prepared release record is not overwritten'
    frozen=json.loads((OUT/'freeze-v2.json').read_text())
    accepted=json.loads((ROOT/'findings/evidence/calc-range-autosave/range-browser-03/mirror-sources.json').read_text())['sha256']
    for name in ['ods-editor.html','ods-editor-app.js','spreadsheet-shell/calc-document-sdk.js',
                 'spreadsheet-shell/calc-editor-session.js','spreadsheet-shell/calc-autosave.js']:
        assert sha(PROBE/'dist'/name)==accepted[name],'staged source differs from accepted mirror: '+name
    assert '<version>0.2.37</version>' in (APP/'appinfo/info.xml').read_text()
    m=package(APP)
    old=json.loads((OLD/'MANIFEST.json').read_text())
    archive=PROBE/'build/archive'/('host-0.2.37-engine-'+m['buildId'])
    assert not archive.exists(),'immutable package archive already exists'
    shutil.copytree(APP/'engine',archive)
    same=[p for p,e in m['files'].items() if old['files'].get(p)==e]
    changed=[p for p,e in m['files'].items() if p in old['files'] and old['files'][p]!=e]
    added=sorted(set(m['files'])-set(old['files']));removed=sorted(set(old['files'])-set(m['files']))
    commit=subprocess.check_output(['git','-C',str(APP),'rev-parse','HEAD'],text=True).strip()
    r={'version':'0.2.37','hostParent':'702bad6d72be5a70d9e3aaca3290b99f0d9fc1d5',
       'hostCommit':commit,'branch':'host-0.2.37','buildId':m['buildId'],'oldBuildId':old['buildId'],
       'archive':str(archive),'oldArchive':str(OLD),'manifestSha256':sha(archive/'MANIFEST.json'),
       'totals':m['totals'],'pages':m['source']['pages'],'changed':changed,'added':added,'removed':removed,
       'unchangedFiles':len(same),'calcProfile':'ods-editor-v2','calcSha256':frozen['sha256'],
       'rangeCohort':'range-browser-03','autosaveCohort':'auto-v2-02','installed':False,
       'K':'DEFERRED; nominal shipped host 0.2.26','section34_4':{'added':[0,0],'cumulative':[47,27]}}
    (archive/'ATTRIBUTION.md').write_text('# Exact host 0.2.37 engine package\n\n'
        f'Build ID {m["buildId"]}, host commit {commit}. This immutable archive matches the isolated host engine byte-for-byte, excluding this attribution file. Calc ods-editor-v2 uses owner-built wasm 5bc53490 and worker 0bed22bd. Writer e2-editor-v22 and readonly ods-viewer-v3 retain their frozen identities. Full file/coding identities are in MANIFEST.json and the external archive.sha256.\n')
    files=sorted(p for p in archive.rglob('*') if p.is_file())
    (OUT/'archive.sha256').write_text(''.join(sha(p)+'  '+str(p.relative_to(archive))+'\n' for p in files))
    r['archiveFilesVerified']=len(files)
    (OUT/'release.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'version':r['version'],'buildId':r['buildId'],'totals':r['totals'],
        'unchangedFiles':len(same),'changed':changed,'added':added,'removed':removed},indent=2))

if __name__=='__main__':main()
