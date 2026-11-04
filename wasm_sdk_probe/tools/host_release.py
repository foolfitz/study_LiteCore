#!/usr/bin/env python3
"""One host-release tool for every version (CLAUDE.md, the section on cadence, item 2, 2026-11-04).

Reads DIR/release-inputs.json (DIR = findings/evidence/host-X) and writes its records next to it.  It replaces the per-release
copies that host-0.2.4x..0.2.55 derived from each other by replacement lists (prepare-release.py, check-delta.py,
offline-package-check.py, install-X.py, capture-after.py, rollback-package.sh); their refusals are kept, in the same order.
Every record it writes carries this tool's sha256 and argv.  Run with host-stack/bin first on PATH.

  host_release.py candidate DIR   clone the host repo's release branch into build/host-X/litecore (refuses if it exists)
  host_release.py gate      DIR   read every gate report named in the inputs and print them; nothing is packaged
  host_release.py package   DIR   the gate, then package the candidate: release.json, archive.sha256, build/archive/host-X-engine-ID
  host_release.py delta     DIR   the archived package against the predecessor's, from the two MANIFEST.json files, with red cases
  host_release.py offline   DIR   the package reader (check_m3_assets) and its red cases
  host_release.py install   DIR [--offline-only | --preflight-only]
  host_release.py capture   DIR INSTALL_DIR WORKFLOW_DIR   the installed identity after the Files workflow run (read-only)
  host_release.py rollback  DIR   the predecessor's exact engine bytes back; the host label stays

release-inputs.json:
  version, branch            "0.2.56", "host-0.2.56"
  predecessor                the folder under findings/evidence whose release.json is the live predecessor ("host-0.2.55")
  hostSourceDelta            exactly `git diff --name-only parent candidate` in the host repo
  served.changed             served files whose bytes change (sorted)
  served.profileMoves        {page: [old profile, new profile]}; every file of the old profile goes, every file of the new comes
  pages                      {page: {profile, wasmSha256, moduleSha256}} for each moved page, and for each page whose module
                             changed in place (0.2.57: the Writer page, profile unchanged); every other page keeps its record
  writerIdentity             optional {module, profile, generation}: the generation's identity module, as prepare-release read it;
                             module "four_arms_identity" reads e2/generations/generation-N.json (generation 90 on)
  gate                       [{id, path, read, want}]; path is from the repo root; read is "verdict", "all_pass", "key:a.b.c",
                             "values:a.b:field" (distinct values of field over a dict/list) or "failed" ({failed ids, fatal})
  attribution                one paragraph for the archive's ATTRIBUTION.md
"""
import argparse
import copy
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import posixpath
import shutil
import subprocess
import sys
import time
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / 'wasm_sdk_probe'
HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
sys.path.insert(0, str(SDK / 'tools'))
TOOL_SHA = None


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def command(argv, cwd=HOST):
    return subprocess.check_output(argv, cwd=cwd, text=True, stderr=subprocess.STDOUT, timeout=300).strip()


def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in Path(path).rglob('*') if p.is_file() and p.name != 'ATTRIBUTION.md'}


def stamp(record):
    return {**record, 'tool': {'path': 'wasm_sdk_probe/tools/host_release.py', 'sha256': TOOL_SHA, 'argv': sys.argv[1:]}}


class Release:
    def __init__(self, folder):
        self.dir = Path(folder).resolve()
        self.inputs = load(self.dir / 'release-inputs.json')
        self.version = self.inputs['version']
        self.app = SDK / 'build' / f'host-{self.version}' / 'litecore'
        self.pred = load(ROOT / 'findings/evidence' / self.inputs['predecessor'] / 'release.json')

    def record(self):
        return load(self.dir / 'release.json')


# ------------------------------------------------------------------ the gate

def all_pass(report):
    return bool(report['runs']) and all(not r.get('error') and not r.get('fatal') and r['checks']
                                        and all(c['pass'] for c in r['checks']) for r in report['runs']
                                        if not r.get('arm', '').startswith('cost'))


def read_gate(entry):
    data = load(ROOT / entry['path'])
    how = entry['read']
    if how == 'verdict':
        return data.get('verdict')
    if how == 'all_pass':
        return all_pass(data)
    if how == 'failed':  # the ids that failed in any run, and whether any run was fatal
        return {'failed': sorted({c['id'] for r in data['runs'] for c in r['checks'] if not c['pass']}),
                'fatal': any(r.get('fatal') for r in data['runs'])}
    if how.startswith('values:'):  # values:a.b:field -> the distinct values of `field` over the dict or list at a.b
        where, field = how[7:].rsplit(':', 1)
        for part in where.split('.'):
            data = data[int(part)] if isinstance(data, list) else data[part]
        return sorted({row[field] for row in (data.values() if isinstance(data, dict) else data)})
    if how.startswith('key:'):
        for part in how[4:].split('.'):
            data = data[int(part)] if isinstance(data, list) else data[part]
        return data
    raise ValueError('unknown gate read: ' + how)


def gate(rel):
    got, wrong = {}, {}
    for entry in rel.inputs['gate']:
        try:
            value = read_gate(entry)
        except (OSError, KeyError, IndexError, ValueError) as error:  # a missing file is a refusal, with its reason
            value = f'unreadable: {type(error).__name__}: {error}'
        got[entry['id']] = value
        if json.loads(json.dumps(value)) != entry['want']:
            wrong[entry['id']] = {'got': value, 'want': entry['want'], 'path': entry['path']}
    if wrong:
        raise ValueError('gate does not hold: ' + json.dumps(wrong, ensure_ascii=False))
    return got


# ------------------------------------------------------------------ the served delta (one judge for package and delta)

def expected_delta(rel, old, new):
    moves = rel.inputs['served']['profileMoves']
    gone = sorted(n for n in old['files'] for a, _ in moves.values() if n.startswith(f'profiles/{a}/'))
    came = sorted(n for n in new['files'] for _, b in moves.values() if n.startswith(f'profiles/{b}/'))
    return sorted(rel.inputs['served']['changed']), came, gone


def judge(rel, old, new):
    of, nf = old['files'], new['files']
    d = {'changed': sorted(n for n in nf if n in of and of[n] != nf[n]),
         'added': sorted(set(nf) - set(of)), 'removed': sorted(set(of) - set(nf)),
         'same': sum(1 for n in nf if of.get(n) == nf[n])}
    changed, came, gone = expected_delta(rel, old, new)
    problems = []
    if d['changed'] != changed:
        problems.append(f"changed {d['changed']}")
    if d['added'] != came or d['removed'] != gone:
        problems.append(f"added {d['added']} removed {d['removed']}")
    moves = rel.inputs['served']['profileMoves']
    for a, b in moves.values():
        names = lambda files, p: sorted(n.split('/', 2)[2] for n in files if n.startswith(f'profiles/{p}/'))  # noqa: E731
        if not names(nf, b) or names(of, a) != names(nf, b):
            problems.append(f'{a} -> {b} does not move the same files')
    for page, record in old['source']['pages'].items():
        now = new['source']['pages'].get(page, {})
        want = rel.inputs['pages'].get(page)
        if page in moves or want is not None:  # moved, or verified in place (its module changed, its profile did not)
            if {k: now.get(k) for k in ('profile', 'wasmSha256', 'moduleSha256')} != want:
                problems.append(f'{page} is not the verified page')
        elif now != record:
            problems.append(f'{page} changed')
    return d, problems


def delta(rel):
    release = rel.record()
    old = load(Path(release['oldArchive']) / 'MANIFEST.json')
    new = load(Path(release['archive']) / 'MANIFEST.json')
    d, problems = judge(rel, old, new)
    moves = rel.inputs['served']['profileMoves']
    moved_pages = sorted(rel.inputs['pages'])  # the pages the inputs verify: moved ones, or ones changed in place
    still = sorted(p for p in new['source']['pages'] if p not in rel.inputs['pages'])
    other = next(n for n in new['files'] if n not in d['changed'] and not n.startswith('profiles/'))
    kept_profile = next((n for n in new['files'] if n.startswith('profiles/') and n not in d['added']), None)

    def more(o, m): m['files'][other] = {**m['files'][other], 'sha256': '0' * 64}
    def fewer(o, m): m['files'][d['changed'][0]] = copy.deepcopy(o['files'][d['changed'][0]])
    def added(o, m): m['files']['profiles/e2-editor-v99/probe.wasm'] = {'sha256': '2' * 64}
    def removed(o, m): del m['files'][other]
    def kept_profile_changed(o, m): m['files'][kept_profile] = {**m['files'][kept_profile], 'sha256': '3' * 64}
    def moved_page_still_old(o, m): m['source']['pages'][moved_pages[0]] = copy.deepcopy(o['source']['pages'][moved_pages[0]])
    def kept_page_wasm(o, m): m['source']['pages'][still[0]]['wasmSha256'] = '5' * 64

    cases = [more, fewer, added, removed, moved_page_still_old] + ([kept_page_wasm] if still else []) \
        + ([kept_profile_changed] if kept_profile else [])
    reds = {}
    for fn in cases:
        mo, mn = copy.deepcopy(old), copy.deepcopy(new)
        fn(mo, mn)
        reds[fn.__name__] = bool(judge(rel, mo, mn)[1])
    holds = not problems and all(reds.values())
    out = stamp({'verdict': 'DELTA_HOLDS' if holds else 'DELTA_RED', 'oldBuildId': old['buildId'], 'buildId': new['buildId'],
                 'delta': d, 'problems': problems, 'redCases': reds})
    print(json.dumps(out, indent=1))
    return 0 if holds else 1


# ------------------------------------------------------------------ candidate and package

def candidate(rel):
    if rel.app.exists():
        raise ValueError(f'{rel.app} exists')
    rel.app.parent.mkdir(parents=True, exist_ok=False)
    subprocess.check_call(['git', 'clone', '-q', '--branch', rel.inputs['branch'], str(HOST), str(rel.app)])
    print(json.dumps(stamp({'candidate': str(rel.app), 'commit': git(rel.app, 'rev-parse', 'HEAD')})))
    return 0


def package_release(rel, reuse):
    from package_m3_engine import package, validate_manifest
    from probe_m3_assets import closure
    from compression import zstd
    gates = gate(rel)
    if (rel.dir / 'release.json').exists():
        raise ValueError('release record already exists')
    parent = git(HOST, 'rev-parse', 'HEAD')
    if parent != rel.pred['hostCommit'] or git(HOST, 'status', '--porcelain'):
        raise ValueError(f"live host differs from clean {rel.pred['hostCommit'][:7]} ({rel.pred['version']})")
    if f'<version>{rel.version}</version>' not in (rel.app / 'appinfo/info.xml').read_text():
        raise ValueError('isolated version differs')
    cand = git(rel.app, 'rev-parse', 'HEAD')
    if cand != git(HOST, 'rev-parse', rel.inputs['branch']):
        raise ValueError('candidate is not the release branch')
    source_delta = git(rel.app, 'diff', '--name-only', parent, cand).splitlines()
    if source_delta != sorted(rel.inputs['hostSourceDelta']):
        raise ValueError('host source delta differs: ' + json.dumps(source_delta))
    ident = rel.inputs.get('writerIdentity')
    want = None
    if ident:
        if ident['module'] == 'four_arms_identity':  # generation 90 on: one tool, the generation from e2/generations/
            from four_arms_identity import Generation
            want = Generation(ident['generation']).identity()
        else:
            want = __import__(ident['module']).identity()
        if want['profile'] != ident['profile'] or want['shell'].get('generation') != ident['generation']:
            raise ValueError(f"identity module does not name {ident['profile']} / generation {ident['generation']}")
    old_dir = Path(rel.pred['archive'])
    old = load(old_dir / 'MANIFEST.json')
    if tree(HOST / 'engine') != tree(old_dir):
        raise ValueError('live predecessor engine differs from its archive')
    started = time.monotonic()
    manifest = load(rel.app / 'engine/MANIFEST.json') if reuse else package(rel.app)
    if validate_manifest(manifest):
        raise ValueError('canonical manifest does not hold')
    derived = closure(SDK / 'dist')
    if {n: e['sha256'] for n, e in manifest['files'].items()} != {e['path']: e['sha256'] for e in derived['files']}:
        raise ValueError('package differs from the complete current closure')
    print('packaged', manifest['buildId'], round(time.monotonic() - started, 2), flush=True)
    files, pages = manifest['files'], manifest['source']['pages']
    if want:
        editor = pages['e2-editor.html']
        if editor['profile'] != ident['profile'] or editor['moduleSha256'] != want['pageSha256']:
            raise ValueError('editor is not the verified page')
        if files['e2-editor.html']['sha256'] != want['originalHtmlSha256']:
            raise ValueError('editor HTML is not the verified page')
        for name, expected in want['artifacts'].items():
            path = posixpath.normpath(f"profiles/{ident['profile']}/" + name)
            if path in editor['declaredNotLoaded']:
                if path in files:
                    raise ValueError('declared-not-loaded file was packaged: ' + path)
                continue
            if files[path]['sha256'] != expected:
                raise ValueError('packaged Writer artifact differs: ' + name)
    for name, entry in files.items():
        raw = (SDK / 'dist' / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('dist drift: ' + name)
        for suffix, decode in (('.gz', gzip.decompress), ('.zst', zstd.decompress)):
            if decode((rel.app / 'engine/files' / (name + suffix)).read_bytes()) != raw:
                raise ValueError('coding differs: ' + name + suffix)
    d, problems = judge(rel, old, manifest)
    if problems:
        raise ValueError(f"delta against {rel.pred['version']} does not hold: " + json.dumps(problems))
    archive = SDK / 'build/archive' / f"host-{rel.version}-engine-{manifest['buildId']}"
    if archive.exists():
        raise ValueError('archive already exists')
    shutil.copytree(rel.app / 'engine', archive)
    (archive / 'ATTRIBUTION.md').write_text(f'# Exact host {rel.version} engine package\n\nHost commit {cand}, predecessor {parent} '
                                            f"({rel.pred['version']}, exact {rel.pred['version']} engine). {rel.inputs['attribution']}\n")
    members = sorted(p for p in archive.rglob('*') if p.is_file())
    (rel.dir / 'archive.sha256').write_text(''.join(sha(p) + '  ' + p.relative_to(archive).as_posix() + '\n' for p in members))
    release = stamp({'version': rel.version, 'hostParent': parent, 'hostCommit': cand, 'branch': rel.inputs['branch'],
                     'buildId': manifest['buildId'], 'oldBuildId': old['buildId'], 'archive': str(archive), 'oldArchive': str(old_dir),
                     'candidateApp': str(rel.app), 'manifestSha256': sha(archive / 'MANIFEST.json'), 'totals': manifest['totals'],
                     'pages': pages, 'unchangedFiles': d['same'], 'changed': d['changed'], 'added': d['added'], 'removed': d['removed'],
                     'archiveFilesVerified': len(members), 'installed': False, 'K': 'NOT_RUN', 'gates': gates,
                     'inputsSha256': sha(rel.dir / 'release-inputs.json'), 'hostSourceDelta': source_delta,
                     'shellBundleFileSha256': want['shell']['bundleFileSha256'] if want else None,
                     'canonicalPackageReusedAfterWrapperError': reuse})
    (rel.dir / 'release.json').write_text(json.dumps(release, indent=1) + '\n')
    print(json.dumps({k: release[k] for k in ('version', 'hostCommit', 'buildId', 'changed', 'unchangedFiles', 'archiveFilesVerified')}, indent=1))
    return 0


# ------------------------------------------------------------------ offline package reader

def offline(rel, app=None):
    import check_m3_assets as assets
    release = rel.record()
    assets.BUILD_ID = release['buildId']
    package = assets.package_record(Path(app or release['candidateApp']))
    problems = assets.score_package(package, True)
    result = {'scope': 'Offline package only; no full K binding or credit', 'buildId': assets.BUILD_ID, 'problems': problems, 'redCases': []}
    if not problems:
        for clause, label, mutate in assets.PACKAGE_CASES:
            changed = copy.deepcopy(package)
            mutate(changed)
            result['redCases'].append({'clause': clause, 'label': label,
                                       'red': any(p.startswith(clause) for p in assets.score_package(changed, True))})
    result['verdict'] = 'PACKAGE_HOLDS' if not problems and result['redCases'] and all(c['red'] for c in result['redCases']) else 'NOT_ESTABLISHED'
    return stamp(result)


# ------------------------------------------------------------------ install, capture, rollback (host-0.2.47's install, unchanged in substance)

def slot():
    # The own stack (SPEC-M3-own-stack): without host-stack/bin first on PATH `ddev` is the real one, which lists other projects.
    states = json.loads(command(['ddev', 'list', '-j']))['raw']
    if states != [{'name': 'litecore', 'status': 'running'}]:
        raise ValueError('not the own stack, or it is not running: ' + json.dumps(states))
    return {'ownStack': json.loads(command(['ddev', 'describe', '-j']))['raw']['primary_url']}, {p['name']: p['status'] for p in states}


def snapshot(instance):
    reference = load(ROOT / 'findings/evidence/host-0.2.38/protected-documents-before.json')
    docs = []
    for item in reference:
        try:
            status, body = instance.dav('GET', item['path'])
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        docs.append({'fileId': item['fileId'], 'path': item['path'], 'status': status, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
    locks = command(['ddev', 'mysql', '-B', '-e', 'SELECT * FROM oc_files_lock ORDER BY file_id;'])  # full read-only rows
    return {'protectedDocuments': docs, 'lockRows': locks}


def install(rel, offline_only, preflight_only):
    release = rel.record()
    if command(['git', 'rev-parse', 'HEAD']) != release['hostParent'] or command(['git', 'status', '--porcelain']):
        raise ValueError('live source differs from the clean recorded predecessor')
    if command(['git', 'branch', '--show-current']) != 'main':
        raise ValueError('live host is not on main')
    if command(['git', 'rev-parse', release['branch']]) != release['hostCommit']:
        raise ValueError('candidate branch moved')
    command(['git', 'merge-base', '--is-ancestor', release['hostParent'], release['hostCommit']])
    archive, old = Path(release['archive']), Path(release['oldArchive'])
    if tree(HOST / 'engine') != tree(old):
        raise ValueError('live predecessor engine differs from exact archive')
    cand = Path(release['candidateApp'])
    if tree(cand / 'engine') != tree(archive):
        raise ValueError('isolated candidate differs from exact archive')
    for line in (rel.dir / 'archive.sha256').read_text().splitlines():
        expected, name = line.split('  ', 1)
        if sha(archive / name) != expected:
            raise ValueError('archive checksum differs: ' + name)
    if offline(rel, cand)['verdict'] != 'PACKAGE_HOLDS':
        raise ValueError('offline package check does not hold')
    if offline_only:
        print(json.dumps(stamp({'verdict': 'OFFLINE_INSTALL_READY', 'hostParent': release['hostParent'], 'hostCommit': release['hostCommit'],
                                'buildId': release['buildId'], 'liveMutation': False})))
        return 0
    owner_slot, states = slot()
    from check_m3_skeleton_open import Instance
    instance = Instance(HOST)
    evidence = rel.dir / ('install-' + datetime.datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z'))
    evidence.mkdir(exist_ok=False)
    before = snapshot(instance)
    (evidence / 'before.json').write_text(json.dumps({'snapshot': before, 'states': states, 'slot': owner_slot}, indent=1, ensure_ascii=False) + '\n')
    if preflight_only:
        print(json.dumps(stamp({'verdict': 'LIVE_PREFLIGHT_READY', 'evidence': str(evidence), 'liveMutation': False})))
        return 0
    slot()  # again, after the full before-state and immediately before the mutation
    log = []
    for argv in (['git', 'merge', '--ff-only', release['branch']],
                 ['rsync', '-a', '--delete', '--exclude', 'ATTRIBUTION.md', str(archive) + '/', str(HOST / 'engine') + '/'],
                 ['ddev', 'occ', 'upgrade']):
        log.append({'argv': argv, 'output': command(argv)})
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
    result = stamp({'verdict': 'CANDIDATE_INSTALLED', 'hostCommit': release['hostCommit'], 'buildId': release['buildId'], 'version': version,
                    'preservedDocumentsAndLocks': before == after, 'globalLockWrites': False, 'routesUnauthenticated': routes, 'K': 'NOT_RUN'})
    (evidence / 'result.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result))
    return 0


def capture(rel, install_dir, workflow_dir):
    """Read-only: the protected documents and full lock rows against the installer's after-state, the Files workflow report's
    cleanup, the installed source and engine identity.  Inherited limits (host-0.2.41, host-0.2.43 READMEs): `holds` gates on the
    workflow's summary `ok`, and files_lock deletes an expired row lazily when it reads that file."""
    import base64
    import urllib.parse
    import urllib.request
    from check_m3_skeleton_open import Instance, DEFAULT_DDEV
    instance = Instance(DEFAULT_DDEV)
    installed_after = load(Path(install_dir) / 'after.json')
    docs = []
    for item in installed_after['protectedDocuments']:
        try:
            status, body = instance.dav('GET', item['path'])
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        docs.append({'fileId': item['fileId'], 'path': item['path'], 'status': status, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
    locks = subprocess.check_output(['ddev', 'mysql', '-B', '-e', 'SELECT * FROM oc_files_lock ORDER BY file_id;'], cwd=DEFAULT_DDEV, text=True).strip()
    release = rel.record()
    head = git(DEFAULT_DDEV, 'rev-parse', 'HEAD')
    clean = not git(DEFAULT_DDEV, 'status', '--porcelain')
    version = instance._run(['ddev', 'occ', 'config:app:get', 'litecore', 'installed_version']).strip()
    manifest = load(DEFAULT_DDEV / 'engine/MANIFEST.json')
    report = load(Path(workflow_dir) / 'report.json')
    try:
        folder_status = instance.dav('PROPFIND', report['ownedFolder'], headers={'Depth': '0'})[0]
    except urllib.error.HTTPError as error:
        folder_status = error.code
    request = urllib.request.Request(instance.base + '/ocs/v2.php/cloud/users/' + urllib.parse.quote(report['temporaryUser']) + '?format=json',
                                     headers={'OCS-APIRequest': 'true',
                                              'Authorization': 'Basic ' + base64.b64encode(('admin:' + instance.password).encode()).decode()})
    try:
        with urllib.request.urlopen(request, context=instance.tls, timeout=45) as response:
            user_status, user_body = response.status, json.load(response)
    except urllib.error.HTTPError as error:
        user_status, user_body = error.code, json.load(error)
    user_absent = user_status == 404 or user_body['ocs']['meta'].get('statuscode') == 404
    admin_runs = [run for run in report['runs'] if run.get('kind') != 'readonly']
    record = {'hostCommit': head, 'hostClean': clean, 'installedVersion': version, 'buildId': manifest['buildId'],
              'engineEqualsArchive': tree(DEFAULT_DDEV / 'engine') == tree(Path(release['archive'])), 'protectedDocuments': docs,
              'protectedDocumentsEqualInstallAfter': docs == installed_after['protectedDocuments'],
              'lockRows': locks, 'lockRowsEqualInstallAfter': locks == installed_after['lockRows'],
              'workflow': {'ok': report['ok'], 'checks': len(report['checks']), 'failed': [c['id'] for c in report['checks'] if not c['ok']],
                           'browsers': [run['browser'] + ('/readonly' if run.get('kind') == 'readonly' else '') for run in report['runs']],
                           'buildIdInEveryEntry': bool(admin_runs) and all(
                               release['buildId'] in run.get('entry', {}).get('landed', '')
                               and release['buildId'] in run.get('writerEntry', {}).get('landed', '') for run in admin_runs),
                           'ownedUnlocks': report['cleanup'].get('ownedUnlocks'), 'cleanupErrors': report['cleanup'].get('errors', [])},
              'ownedFolderStatus': folder_status, 'temporaryUserAbsent': user_absent, 'globalLockTableWrites': False}
    record['holds'] = (head == release['hostCommit'] and clean and version == release['version'] and record['buildId'] == release['buildId']
                       and record['engineEqualsArchive'] and record['protectedDocumentsEqualInstallAfter'] and record['lockRowsEqualInstallAfter']
                       and report['ok'] and record['workflow']['buildIdInEveryEntry'] and not record['workflow']['ownedUnlocks']
                       and folder_status == 404 and user_absent)
    print(json.dumps(stamp(record), indent=1, ensure_ascii=False))
    return 0 if record['holds'] else 1


def rollback(rel):
    slot()
    release = rel.record()
    if command(['git', 'rev-parse', 'HEAD']) != release['hostCommit'] or command(['git', 'status', '--porcelain']):
        raise ValueError('the live host is not the clean installed candidate')
    if tree(HOST / 'engine') != tree(Path(release['archive'])):
        raise ValueError('the live engine is not the candidate archive')
    subprocess.run(['rsync', '-a', '--delete', '--exclude', 'ATTRIBUTION.md', release['oldArchive'] + '/', str(HOST / 'engine') + '/'], check=True)
    if tree(HOST / 'engine') != tree(Path(release['oldArchive'])):
        raise ValueError('rollback did not restore the predecessor engine')
    print(f"Exact {rel.pred['version']} engine restored; host label stays {release['version']}.")
    return 0


def main():
    global TOOL_SHA
    TOOL_SHA = sha(__file__)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=('candidate', 'gate', 'package', 'delta', 'offline', 'install', 'capture', 'rollback'))
    parser.add_argument('dir')
    parser.add_argument('extra', nargs='*')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--offline-only', action='store_true')
    mode.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--reuse-existing', action='store_true', help='package: revalidate the package already produced after a wrapper error')
    args = parser.parse_args()
    rel = Release(args.dir)
    if args.action == 'candidate':
        return candidate(rel)
    if args.action == 'gate':
        print(json.dumps(stamp({'gates': gate(rel)}), indent=1))
        return 0
    if args.action == 'package':
        return package_release(rel, args.reuse_existing)
    if args.action == 'delta':
        return delta(rel)
    if args.action == 'offline':
        result = offline(rel)
        print(json.dumps(result, indent=1))
        return 0 if result['verdict'] == 'PACKAGE_HOLDS' else 1
    if args.action == 'install':
        return install(rel, args.offline_only, args.preflight_only)
    if args.action == 'capture':
        return capture(rel, *args.extra)
    return rollback(rel)


if __name__ == '__main__':
    raise SystemExit(main())
