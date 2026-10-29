#!/usr/bin/env python3
"""Read the installed 0.2.42 identity after the owned-document Files workflow run.

Derived from findings/evidence/host-0.2.41/capture-after.py (not edited; itself a copy of 0.2.40's and 0.2.39's).
Closed list of differences: the version in the first line and this paragraph; the code is 0.2.41's byte for byte.

Inherited named limit (host-0.2.41/README.md, found by post-install-red/flipped-check-only-the-cell/; spec v26
5.9 keeps it): `holds` gates on the Files workflow runner's summary `report['ok']`; `workflow.failed` lists the
failed cells without gating on them.  A report whose cells and summary disagree is not one the runner writes
(run_calc_editor_host.py sets ok from every check, the error and the cleanup errors), so a real run is not
affected.  Kept, not redesigned.

Read-only: compares the current protected documents and full lock rows with the
installer's own after-state, reads the Files workflow report's cleanup, and the
installed source/engine identity. Never unlocks, restores or deletes anything.
"""
from pathlib import Path
import base64
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
from check_m3_skeleton_open import Instance, DEFAULT_DDEV


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in path.rglob('*') if p.is_file() and p.name != 'ATTRIBUTION.md'}


def main():
    install, workflow = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    instance = Instance(DEFAULT_DDEV)
    installed_after = json.loads((install / 'after.json').read_text())
    docs = []
    for item in installed_after['protectedDocuments']:
        try:
            status, body = instance.dav('GET', item['path'])
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        docs.append({'fileId': item['fileId'], 'path': item['path'], 'status': status,
                     'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
    locks = subprocess.check_output(['ddev', 'mysql', '-B', '-e', 'SELECT * FROM oc_files_lock ORDER BY file_id;'],
                                    cwd=DEFAULT_DDEV, text=True).strip()
    release = json.loads((OUT / 'release.json').read_text())
    head = subprocess.check_output(['git', '-C', str(DEFAULT_DDEV), 'rev-parse', 'HEAD'], text=True).strip()
    clean = not subprocess.check_output(['git', '-C', str(DEFAULT_DDEV), 'status', '--porcelain'], text=True).strip()
    version = instance._run(['ddev', 'occ', 'config:app:get', 'litecore', 'installed_version']).strip()
    manifest = json.loads((DEFAULT_DDEV / 'engine/MANIFEST.json').read_text())
    report = json.loads((workflow / 'report.json').read_text())
    try:
        folder_status = instance.dav('PROPFIND', report['ownedFolder'], headers={'Depth': '0'})[0]
    except urllib.error.HTTPError as error:
        folder_status = error.code
    user_url = instance.base + '/ocs/v2.php/cloud/users/' + urllib.parse.quote(report['temporaryUser']) + '?format=json'
    request = urllib.request.Request(user_url, headers={'OCS-APIRequest': 'true',
        'Authorization': 'Basic ' + base64.b64encode(('admin:' + instance.password).encode()).decode()})
    try:
        with urllib.request.urlopen(request, context=instance.tls, timeout=45) as response:
            user_status, user_body = response.status, json.load(response)
    except urllib.error.HTTPError as error:
        user_status, user_body = error.code, json.load(error)
    user_absent = user_status == 404 or user_body['ocs']['meta'].get('statuscode') == 404
    admin_runs = [run for run in report['runs'] if run.get('kind') != 'readonly']
    record = {
        'hostCommit': head, 'hostClean': clean, 'installedVersion': version, 'buildId': manifest['buildId'],
        'engineEqualsArchive': tree(DEFAULT_DDEV / 'engine') == tree(Path(release['archive'])),
        'protectedDocuments': docs,
        'protectedDocumentsEqualInstallAfter': docs == installed_after['protectedDocuments'],
        'lockRows': locks, 'lockRowsEqualInstallAfter': locks == installed_after['lockRows'],
        'workflow': {'ok': report['ok'], 'checks': len(report['checks']),
                     'failed': [c['id'] for c in report['checks'] if not c['ok']],
                     'browsers': [run['browser'] + ('/readonly' if run.get('kind') == 'readonly' else '') for run in report['runs']],
                     'buildIdInEveryEntry': bool(admin_runs) and all(
                         release['buildId'] in run.get('entry', {}).get('landed', '')
                         and release['buildId'] in run.get('writerEntry', {}).get('landed', '') for run in admin_runs),
                     'ownedUnlocks': report['cleanup'].get('ownedUnlocks'),
                     'cleanupErrors': report['cleanup'].get('errors', [])},
        'ownedFolderStatus': folder_status, 'temporaryUserAbsent': user_absent, 'globalLockTableWrites': False,
    }
    record['holds'] = (head == release['hostCommit'] and clean and version == release['version']
                       and record['buildId'] == release['buildId'] and record['engineEqualsArchive']
                       and record['protectedDocumentsEqualInstallAfter'] and record['lockRowsEqualInstallAfter']
                       and report['ok'] and record['workflow']['buildIdInEveryEntry']
                       and not record['workflow']['ownedUnlocks'] and folder_status == 404 and user_absent)
    print(json.dumps(record, indent=1, ensure_ascii=False))
    return 0 if record['holds'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
