#!/usr/bin/env python3
"""Reuse the verified predecessor codings; only Calc HTML bytes change."""
from pathlib import Path
import copy,gzip,hashlib,json,shutil,subprocess,sys
from compression import zstd
ROOT=Path(__file__).resolve().parents[3];PROBE=ROOT/'wasm_sdk_probe';OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(PROBE/'tools'))
from package_m3_engine import build_id,validate_manifest,check_caps,zstd_frame,MAX_ZSTD_WINDOW,ZSTD_LEVEL,page_table
from probe_m3_assets import closure
from probe_m3_gate0_coep import utc_now
APP=PROBE/'build/host-0.2.38/litecore'
OLD=PROBE/'build/archive/host-0.2.37-engine-754ae8eafd15edda'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 assert not (OUT/'release.json').exists() and not (APP/'engine').exists()
 old=json.loads((OLD/'MANIFEST.json').read_text());m=copy.deepcopy(old);derived=closure(PROBE/'dist')
 assert {x['path'] for x in derived['files']}==set(old['files'])
 changed=[x['path'] for x in derived['files'] if old['files'][x['path']]['sha256']!=x['sha256']]
 assert changed==['ods-editor.html'],changed
 shutil.copytree(OLD,APP/'engine',ignore=shutil.ignore_patterns('ATTRIBUTION.md'))
 raw=(PROBE/'dist/ods-editor.html').read_bytes();packed=gzip.compress(raw,9,mtime=0);squeezed=zstd.compress(raw,level=ZSTD_LEVEL)
 check_caps('ods-editor.html',len(packed),len(squeezed));frame=zstd_frame(squeezed)
 assert frame['window']<=MAX_ZSTD_WINDOW and frame['trailingBytes']==0
 entry={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'gzBytes':len(packed),'gzSha256':hashlib.sha256(packed).hexdigest(),'zstBytes':len(squeezed),'zstSha256':hashlib.sha256(squeezed).hexdigest()}
 (APP/'engine/files/ods-editor.html.gz').write_bytes(packed);(APP/'engine/files/ods-editor.html.zst').write_bytes(squeezed)
 m['files']['ods-editor.html']=entry;m['buildId']=build_id(m['files']);m['source'].update(pages=page_table(derived,m['files']),tool=sha(Path(__file__)),packagedAt=utc_now(),incrementalFrom=old['buildId'])
 m['totals']={'files':len(m['files']),'bytes':sum(e['bytes'] for e in m['files'].values()),'gzBytes':sum(e['gzBytes'] for e in m['files'].values()),'zstBytes':sum(e['zstBytes'] for e in m['files'].values())}
 assert not validate_manifest(m)
 (APP/'engine/MANIFEST.json').write_text(json.dumps(m,indent=1)+'\n')
 archive=PROBE/'build/archive'/('host-0.2.38-engine-'+m['buildId']);assert not archive.exists();shutil.copytree(APP/'engine',archive)
 commit=subprocess.check_output(['git','-C',str(APP),'rev-parse','HEAD'],text=True).strip()
 (archive/'ATTRIBUTION.md').write_text('# Exact host 0.2.38 CSS correction\n\nOnly ods-editor.html differs from 0.2.37. All45 other complete raw/gzip/zstd records are identical. Engine profiles and JavaScript are unchanged. The shared white canvas/editor now pairs dark text and caret with light control rendering.\n')
 files=sorted(p for p in archive.rglob('*') if p.is_file());(OUT/'archive.sha256').write_text(''.join(sha(p)+'  '+str(p.relative_to(archive))+'\n' for p in files))
 r={'version':'0.2.38','hostParent':'2f7a1193e3c296ea1c51dabe470fd2b289d3279b','hostCommit':commit,'branch':'host-0.2.38','buildId':m['buildId'],'oldBuildId':old['buildId'],'archive':str(archive),'oldArchive':str(OLD),'manifestSha256':sha(archive/'MANIFEST.json'),'totals':m['totals'],'pages':m['source']['pages'],'changed':changed,'unchangedFiles':45,'archiveFilesVerified':len(files),'installed':False,'K':'DEFERRED; nominal shipped0.2.26','section34_4':{'added':[0,0],'cumulative':[47,27]}}
 (OUT/'release.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
