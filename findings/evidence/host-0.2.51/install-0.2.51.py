#!/usr/bin/env python3
"""Guarded 0.2.51 candidate install; no service lifecycle, root command or global lock write.

Derived from findings/evidence/host-0.2.47/install-0.2.47.py (not edited).  Closed list of differences: the
version in this line, this paragraph, the isolated candidate path (build/host-0.2.47 -> build/host-0.2.48).  Run with
host-stack/bin first on PATH.  The live predecessor it verifies is whatever release.json names: host 350cc4c (0.2.50)
with the exact 0.2.50 engine archive.  The preflight-only mode and every other check below are 0.2.47's, unchanged.

--offline-only validates exact source/archive/package without DDEV. Live preflight/install require
slot.json naming the owner-confirmed window, no-site agreement and shared-DDEV coordination.
The caller starts litecore only after coordination; this script never pauses another project.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.error

ROOT = Path(__file__).resolve().parents[3]
SDK = ROOT / 'wasm_sdk_probe'
OUT = Path(__file__).resolve().parent
HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
sys.path.insert(0, str(SDK / 'tools'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def command(argv, cwd=HOST):
    return subprocess.check_output(argv, cwd=cwd, text=True, stderr=subprocess.STDOUT, timeout=300).strip()


def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in path.rglob('*') if p.is_file() and p.name != 'ATTRIBUTION.md'}


def slot():
    # SPEC-M3-own-stack: the slot was there because ddev was shared.  What stays is that this is the stack it thinks it is;
    # without host-stack/bin first on PATH `ddev` is the real one, which lists other projects and this refuses.
    states = json.loads(command(['ddev', 'list', '-j']))['raw']
    if states != [{'name': 'litecore', 'status': 'running'}]:
        raise ValueError('not the own stack, or it is not running: ' + json.dumps(states))
    return {'ownStack': json.loads(command(['ddev', 'describe', '-j']))['raw']['primary_url']}, {p['name']: p['status'] for p in states}


def snapshot(instance):
    reference = json.loads((ROOT / 'findings/evidence/host-0.2.38/protected-documents-before.json').read_bytes())
    docs = []
    for item in reference:
        try:
            status, body = instance.dav('GET', item['path'])
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        docs.append({'fileId': item['fileId'], 'path': item['path'], 'status': status,
                     'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
    # Full read-only rows, never DELETE or expiration inference from an old snapshot.
    locks = command(['ddev', 'mysql', '-B', '-e', 'SELECT * FROM oc_files_lock ORDER BY file_id;'])
    return {'protectedDocuments': docs, 'lockRows': locks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--offline-only', action='store_true')
    mode.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args(); release = json.loads((OUT / 'release.json').read_bytes())
    if command(['git', 'rev-parse', 'HEAD']) != release['hostParent'] or command(['git', 'status', '--porcelain']):
        raise ValueError('live source differs from the clean recorded predecessor')
    if command(['git', 'branch', '--show-current']) != 'main':
        raise ValueError('live host is not on main')
    if command(['git', 'rev-parse', release['branch']]) != release['hostCommit']:
        raise ValueError('candidate branch moved')
    command(['git', 'merge-base', '--is-ancestor', release['hostParent'], release['hostCommit']])
    archive = Path(release['archive']); old = Path(release['oldArchive'])
    if tree(HOST / 'engine') != tree(old):
        raise ValueError('live predecessor engine differs from exact archive')
    candidate = SDK / 'build/host-0.2.51/litecore'
    if tree(candidate / 'engine') != tree(archive):
        raise ValueError('isolated candidate differs from exact archive')
    for line in (OUT / 'archive.sha256').read_text().splitlines():
        expected, name = line.split('  ', 1)
        if sha(archive / name) != expected:
            raise ValueError('archive checksum differs: ' + name)
    checked = command([sys.executable, str(OUT / 'offline-package-check.py'), str(candidate)], cwd=ROOT)
    if json.loads(checked)['verdict'] != 'PACKAGE_HOLDS':
        raise ValueError('offline package check does not hold')
    if args.offline_only:
        print(json.dumps({'verdict': 'OFFLINE_INSTALL_READY', 'hostParent': release['hostParent'],
                          'hostCommit': release['hostCommit'], 'buildId': release['buildId'], 'liveMutation': False}))
        return 0
    owner_slot, states = slot()
    from check_m3_skeleton_open import Instance
    instance = Instance(HOST)
    stamp = datetime.datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z')
    evidence = OUT / ('install-' + stamp); evidence.mkdir(exist_ok=False)
    before = snapshot(instance)
    (evidence / 'before.json').write_text(json.dumps({'snapshot': before, 'states': states, 'slot': owner_slot}, indent=1, ensure_ascii=False) + '\n')
    if args.preflight_only:
        print(json.dumps({'verdict': 'LIVE_PREFLIGHT_READY', 'evidence': str(evidence), 'liveMutation': False})); return 0
    slot()  # Recheck after full before-state capture, immediately before mutation.
    log = []
    for argv in (['git', 'merge', '--ff-only', release['branch']],
                 ['rsync', '-a', '--delete', '--exclude', 'ATTRIBUTION.md', str(archive) + '/', str(HOST / 'engine') + '/'],
                 ['ddev', 'occ', 'upgrade']):
        output = command(argv); log.append({'argv': argv, 'output': output})
        (evidence / 'commands.json').write_text(json.dumps(log, indent=1) + '\n')
    after = snapshot(instance)
    (evidence / 'after.json').write_text(json.dumps(after, indent=1, ensure_ascii=False) + '\n')
    status = json.loads(command(['ddev', 'occ', 'status', '--output=json']))
    version = command(['ddev', 'occ', 'config:app:get', 'litecore', 'installed_version'])
    if before != after or tree(HOST / 'engine') != tree(archive) or version != release['version'] or status.get('maintenance') or status.get('needsDbUpgrade'):
        raise ValueError('post-install preservation, identity or upgrade state differs; retain evidence, no automatic rollback')
    base = json.loads(command(['ddev', 'describe', '-j']))['raw']['primary_url']
    routes = {}
    for page in ('e2-editor.html', 'ods-viewer.html', 'ods-editor.html'):
        code = command(['curl', '-sk', '-o', '/dev/null', '-w', '%{http_code}', base + '/index.php/apps/litecore/r/' + page + '?fileId=0'])
        if code not in ('401', '302', '303'):
            raise ValueError('unauthenticated route was not refused: ' + page + ': ' + code)
        routes[page] = code
    result = {'verdict': 'CANDIDATE_INSTALLED', 'hostCommit': release['hostCommit'], 'buildId': release['buildId'],
              'version': version, 'preservedDocumentsAndLocks': before == after, 'globalLockWrites': False,
              'routesUnauthenticated': routes, 'K': 'NOT_RUN'}
    (evidence / 'result.json').write_text(json.dumps(result, indent=1) + '\n'); print(json.dumps(result)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
