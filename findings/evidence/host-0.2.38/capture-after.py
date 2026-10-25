#!/usr/bin/env python3
"""Read installed package identity and preserve the current owner's resources."""
from pathlib import Path
import base64
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
from check_m3_skeleton_open import Instance, DEFAULT_DDEV


def main():
    instance = Instance(DEFAULT_DDEV)
    before = json.loads((OUT / 'protected-documents-before.json').read_text())
    after = []
    for item in before:
        status, body = instance.dav('GET', item['path'])
        after.append(dict(fileId=item['fileId'], path=item['path'], status=status,
                          bytes=len(body), sha256=hashlib.sha256(body).hexdigest()))
    (OUT / 'protected-documents-after.json').write_text(json.dumps(after, indent=2, ensure_ascii=False) + '\n')
    assert after == before, 'protected document bytes changed'
    locks = subprocess.check_output(['ddev', 'mysql', '-N', '-e',
        'SELECT file_id FROM oc_files_lock ORDER BY file_id;'], cwd=DEFAULT_DDEV, text=True)
    (OUT / 'locks-after.txt').write_text(locks)
    assert locks.split() == (OUT / 'locks-before.txt').read_text().split(), 'unrelated locks changed'
    states = json.loads(subprocess.check_output(['ddev', 'list', '-j'], text=True))
    (OUT / 'ddev-after.json').write_text(json.dumps(states, indent=2) + '\n')
    state_map = lambda d: {p['name']: p['status'] for p in d['raw']}
    assert state_map(states) == state_map(json.loads((OUT / 'ddev-before.json').read_text())), 'service states changed'
    release = json.loads((OUT / 'release.json').read_text())
    installed = json.loads((DEFAULT_DDEV / 'engine/MANIFEST.json').read_text())
    head = subprocess.check_output(['git', '-C', str(DEFAULT_DDEV), 'rev-parse', 'HEAD'], text=True).strip()
    clean = not subprocess.check_output(['git', '-C', str(DEFAULT_DDEV), 'status', '--short'], text=True).strip()
    version = instance._run(['ddev', 'occ', 'config:app:get', 'litecore', 'installed_version']).strip()
    assert installed['buildId'] == release['buildId'] and head == release['hostCommit'] and clean and version == '0.2.38'
    compared = subprocess.run(['diff', '-rq', str(DEFAULT_DDEV / 'engine'), release['archive']], text=True, capture_output=True)
    assert compared.returncode == 1 and compared.stdout.strip() == 'Only in ' + release['archive'] + ': ATTRIBUTION.md'
    report = json.loads((ROOT / 'findings/evidence/calc-dark-mode/installed-01/report.json').read_text())
    assert report['ok'] and len(report['runs']) == 2
    assert all('previewSourceSha256' not in run for run in report['runs']), 'preview injection in installed run'
    for run in report['runs']:
        assert release['buildId'] in run['entry']['landed'], 'different package served'
        assert {s['mode'] for s in run['samples']} == {'light', 'dark'}
        assert all(s['contrast'] >= 4.5 and s['caret'] == s['color'] == s['textFill'] and s['colorScheme'] == 'light'
                   for s in run['samples'])
    try:
        folder_status = instance.dav('PROPFIND', report['ownedFolder'], headers={'Depth': '0'})[0]
    except urllib.error.HTTPError as exc:
        folder_status = exc.code
    assert folder_status == 404, 'owned fixture folder remains'
    assert not report['cleanup']['ownedUnlocks'], 'installed run needed fallback unlock'
    user_url = instance.base + '/ocs/v2.php/cloud/users/' + urllib.parse.quote(report['temporaryUser']) + '?format=json'
    request = urllib.request.Request(user_url, headers={'OCS-APIRequest': 'true',
        'Authorization': 'Basic ' + base64.b64encode(('admin:' + instance.password).encode()).decode()})
    try:
        with urllib.request.urlopen(request, context=instance.tls, timeout=45) as response:
            user_status, user_body = response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        user_status, user_body = exc.code, json.load(exc)
    user_absent = user_status == 404 or user_body['ocs']['meta'].get('statuscode') == 404
    assert user_absent, 'owned temporary user remains'
    record = dict(hostCommit=head, hostClean=clean, installedVersion=version,
        buildId=installed['buildId'], protectedFileIds=[item['fileId'] for item in after],
        protectedDocumentsPreserved=True, lockFileIds=locks.split(),
        globalLockTableWrites=False, serviceStatesPreserved=True,
        ownedFolderStatus=folder_status, temporaryUserAbsent=user_absent, engineEqualsArchive=True,
        installedStyleChecks=len(report['checks']))
    (OUT / 'post-test-identity.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
