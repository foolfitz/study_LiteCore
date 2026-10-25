#!/usr/bin/env python3
"""Read live identities and preservation facts after owned fixture cleanup."""
from pathlib import Path
import hashlib
import json
import base64
import subprocess
import sys
import urllib.request
import urllib.error
import urllib.parse
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'wasm_sdk_probe/tools'))
from check_m3_skeleton_open import Instance,DEFAULT_DDEV
from check_m3_host_entry import LOCK_PROPS

def main():
    instance=Instance(DEFAULT_DDEV)
    name='LiteCore 手動驗收 2026-10-25/Markdown 焦點測試.odt'
    status,body=instance.dav('GET',name)
    _,props=instance.dav('PROPFIND',name,LOCK_PROPS,{'Depth':'0','Content-Type':'application/xml'})
    fileid=ET.fromstring(props).findtext('.//{http://owncloud.org/ns}fileid')
    owner={'fileId':int(fileid),'path':name,'status':status,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
    (OUT/'owner-document-after.json').write_text(json.dumps(owner,indent=2,ensure_ascii=False)+'\n')
    locks=subprocess.check_output(['ddev','mysql','-N','-e','SELECT file_id FROM oc_files_lock ORDER BY file_id;'],cwd=DEFAULT_DDEV,text=True)
    (OUT/'locks-after.txt').write_text(locks)
    states=json.loads(subprocess.check_output(['ddev','list','-j'],text=True))
    (OUT/'ddev-after.json').write_text(json.dumps(states,indent=2)+'\n')
    before=json.loads((OUT/'owner-document-before.json').read_text())
    assert owner==before,'owner document changed'
    assert locks.split()==(OUT/'locks-before.txt').read_text().split(),'unrelated locks changed'
    to_map=lambda d:{p['name']:p['status'] for p in d['raw']}
    assert to_map(states)==to_map(json.loads((OUT/'ddev-before.json').read_text())),'shared service state changed'
    release=json.loads((OUT/'release.json').read_text())
    installed=json.loads((DEFAULT_DDEV/'engine/MANIFEST.json').read_text())
    head=subprocess.check_output(['git','-C',str(DEFAULT_DDEV),'rev-parse','HEAD'],text=True).strip()
    clean=not subprocess.check_output(['git','-C',str(DEFAULT_DDEV),'status','--short'],text=True).strip()
    version=instance._run(['ddev','occ','config:app:get','litecore','installed_version']).strip()
    assert installed['buildId']==release['buildId'] and head==release['hostCommit'] and clean and version=='0.2.37'
    report=json.loads((OUT/'range-autosave-host-01/report.json').read_text())
    try:folder_status=instance.dav('PROPFIND',report['ownedFolder'],LOCK_PROPS,{'Depth':'0'})[0]
    except urllib.error.HTTPError as e:folder_status=e.code
    url=instance.base+'/ocs/v2.php/cloud/users/'+urllib.parse.quote(report['temporaryUser'])+'?format=json'
    request=urllib.request.Request(url,headers={'OCS-APIRequest':'true',
        'Authorization':'Basic '+base64.b64encode(('admin:'+instance.password).encode()).decode()})
    try:
        with urllib.request.urlopen(request,context=instance.tls,timeout=45) as response:
            user_status=response.status;user_body=json.load(response)
    except urllib.error.HTTPError as e:user_status=e.code;user_body=json.load(e)
    user_absent=user_status==404 or user_body['ocs']['meta'].get('statuscode')==404
    assert folder_status==404 and user_absent,'owned resources remain'
    record={'hostCommit':head,'hostClean':clean,'installedVersion':version,'buildId':installed['buildId'],
        'ownerFileId24920Preserved':True,'lockFileIdsBefore':locks.split(),'lockFileIdsAfter':locks.split(),
        'globalLockTableWrites':False,'serviceStatesPreserved':True,
        'ownedFolderStatus':folder_status,'temporaryUserAbsent':user_absent}
    (OUT/'post-test-identity.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
