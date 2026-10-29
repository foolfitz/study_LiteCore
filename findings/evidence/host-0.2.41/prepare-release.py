#!/usr/bin/env python3
"""Package an isolated 0.2.41 host (Writer v25, shell generation 79) from current verified dist, preserving the live predecessor.

Derived from findings/evidence/host-0.2.40/prepare-release.py (not edited).  Closed list of differences:
- the live predecessor is host ae1f9db (0.2.40) with the exact 0.2.40 engine, so OLD is the 0.2.40 archive
  and PARENT is ae1f9db;
- the editor page is generation 79's (tools/v79_four_arms_identity.py; profile still e2-editor-v25);
- the evidence gate keeps 0.2.40's (carried-over v24 counts, v25 F1-F4, section 9 reader) and adds
  SPEC-M3-shell-v79-finding-173's: U1, U2, B1, F3-79 (both readings), F4-79, V0' and E1-C, each by its
  recorded result;
- the delta against 0.2.40 must be exactly the two declared shell files: no profile file changes, nothing
  added or removed (spec 5.7);
- names (0.2.41, archive, attribution, release fields).
"""
import argparse
import gzip
import hashlib
import json
import posixpath
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SDK = ROOT / 'wasm_sdk_probe'
OUT = Path(__file__).resolve().parent
APP = SDK / 'build/host-0.2.41/litecore'
HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
PARENT = 'ae1f9dbc2468afe3772fd142bfc75769f6669d29'
OLD = SDK / 'build/archive/host-0.2.40-engine-a08bc6ecb7241448'
sys.path.insert(0, str(SDK / 'tools'))
from package_m3_engine import package, validate_manifest
from probe_m3_assets import closure
from v79_four_arms_identity import identity
from compression import zstd


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-existing', action='store_true', help='revalidate the already-produced canonical package after a wrapper error')
    args = parser.parse_args()
    if (OUT / 'release.json').exists():
        raise ValueError('release record already exists')
    if git(HOST, 'rev-parse', 'HEAD') != PARENT or git(HOST, 'status', '--porcelain'):
        raise ValueError('live predecessor differs from clean ae1f9db (0.2.40)')
    if '<version>0.2.41</version>' not in (APP / 'appinfo/info.xml').read_text():
        raise ValueError('isolated version differs')
    candidate = git(APP, 'rev-parse', 'HEAD')
    if git(APP, 'diff', '--name-only', PARENT, candidate).splitlines() != ['appinfo/info.xml']:
        raise ValueError('candidate host source delta is not only its version')
    want = identity()
    combined = json.loads((ROOT / 'findings/evidence/link-batch-v24/remaining-counted-01/completion-read-01.json').read_bytes())
    a4 = json.loads((ROOT / 'findings/evidence/link-batch-v24/four-arms-counted-01/aggregate-judge.json').read_bytes())
    if combined['verdict'] != 'V24_SELECTION_COUNTS_HOLD' or a4['problems'] or not all(x['outcome'] == 'PASS' for x in a4['arms'].values()):
        raise ValueError('carried-over v24 feature counts do not hold')
    v25 = ROOT / 'findings/evidence/link-batch-v25'
    gates = {'F1': (json.loads((v25 / 'f1/read-01.json').read_bytes())['verdict'], 'F1_HOLDS'),
             'F2': (json.loads((v25 / 'f2/run-01/report.json').read_bytes())['verdict'], 'F2_HOLDS'),
             'F3': (json.loads((v25 / 'f3/read-02.json').read_bytes())['verdict'], 'F3_HOLDS'),
             'section9': (json.loads((v25 / 'section-9-reader/live.json').read_bytes())['verdict'], 'CONFINED_V25_HOLDS')}
    f4 = json.loads((v25 / 'f4/aggregate-judge.json').read_bytes())
    gates['F4'] = ('PASS' if not f4['problems'] and f4['rows'] == 24 and all(x['outcome'] == 'PASS' for x in f4['arms'].values()) else 'NOT', 'PASS')
    if any(got != want_ for got, want_ in gates.values()):
        raise ValueError('v25 section 6.3 / section 9 verdicts do not hold: ' + json.dumps(gates))
    v79 = ROOT / 'findings/evidence/shell-v79-173'

    def node_exit(path):
        return path.read_text().rstrip().splitlines()[-1]
    f4_79 = json.loads((v79 / 'f4/aggregate-judge.json').read_bytes())
    gates79 = {
        'U1': ((node_exit(v79 / 'u1/red-before.txt'), node_exit(v79 / 'u1/green-after.txt')), ('# exit 1', '# exit 0')),
        'U2': ((node_exit(v79 / 'u2/red-before.txt'), node_exit(v79 / 'u2/green-after.txt')), ('# exit 1', '# exit 0')),
        'shellTests': (node_exit(v79 / 'u1/all-shell-tests-after.txt'), '# exit 0'),
        'B1': (json.loads((v79 / 'b1/run-01/report.json').read_bytes())['verdict'], 'B1_HOLDS'),
        'F3-79-spec16': (json.loads((v79 / 'f3/read-01.json').read_bytes())['verdict'], 'F3_HOLDS'),
        'F3-79-equal': (json.loads((v79 / 'f3/equal-01.json').read_bytes())['verdict'], 'F3_79_EQUAL'),
        'F4-79': ('PASS' if not f4_79['problems'] and f4_79['rows'] == 24 and all(x['outcome'] == 'PASS' for x in f4_79['arms'].values()) else 'NOT', 'PASS'),
        'V0prime': (json.loads((v79 / 'v0/v0-prime.json').read_bytes())['verdict'], 'V0_PRIME_HOLDS'),
        'E1-C': (json.loads((v79 / 'v0/e1-c-after-put-back.json').read_bytes()).get('intact'), True),
    }
    gates79 = {k: (list(g) if isinstance(g, tuple) else g, list(w) if isinstance(w, tuple) else w) for k, (g, w) in gates79.items()}
    if any(got != want_ for got, want_ in gates79.values()):
        raise ValueError('spec v79 verdicts do not hold: ' + json.dumps(gates79))
    old = json.loads((OLD / 'MANIFEST.json').read_bytes())
    # The real live predecessor's ignored package must also be the archived one.
    old_files = [p.relative_to(OLD) for p in OLD.rglob('*') if p.is_file() and p.name != 'ATTRIBUTION.md']
    if any(sha(OLD / n) != sha(HOST / 'engine' / n) for n in old_files):
        raise ValueError('live predecessor engine differs from its archive')
    started = time.monotonic()
    manifest = json.loads((APP / 'engine/MANIFEST.json').read_bytes()) if args.reuse_existing else package(APP)
    if validate_manifest(manifest):
        raise ValueError('canonical manifest does not hold')
    derived = closure(SDK / 'dist')
    if {n: e['sha256'] for n, e in manifest['files'].items()} != {e['path']: e['sha256'] for e in derived['files']}:
        raise ValueError('existing package differs from the complete current closure')
    print('packaged', manifest['buildId'], round(time.monotonic() - started, 2), flush=True)
    files = manifest['files']
    # Preserve every predecessor viewer/Calc closure member except the intentionally shared SDK.
    pages = manifest['source']['pages']
    for html in ('ods-viewer.html', 'ods-editor.html'):
        if pages[html] != old['source']['pages'][html] or files[html] != old['files'][html]:
            raise ValueError('viewer/Calc identity or HTML changed: ' + html)
    editor = pages['e2-editor.html']
    if editor['profile'] != 'e2-editor-v25' or editor['moduleSha256'] != want['pageSha256']:
        raise ValueError('editor is not the verified generation-79 page')
    for name, expected in want['artifacts'].items():
        path = posixpath.normpath('profiles/e2-editor-v25/' + name)
        if path in editor['declaredNotLoaded']:
            if path in files:
                raise ValueError('declared-not-loaded file was packaged: ' + path)
            continue
        if files[path]['sha256'] != expected:
            raise ValueError('packaged Writer artifact differs: ' + name)
    # Decode both codings and bind every packaged raw byte to current dist.
    for name, entry in files.items():
        raw = (SDK / 'dist' / name).read_bytes()
        if sha(SDK / 'dist' / name) != entry['sha256']:
            raise ValueError('dist drift: ' + name)
        for suffix, decode in (('.gz', gzip.decompress), ('.zst', zstd.decompress)):
            if decode((APP / 'engine/files' / (name + suffix)).read_bytes()) != raw:
                raise ValueError('coding differs: ' + name + suffix)
    same = [n for n, entry in files.items() if old['files'].get(n) == entry]
    changed = [n for n, entry in files.items() if n in old['files'] and old['files'][n] != entry]
    added = sorted(set(files) - set(old['files'])); removed = sorted(set(old['files']) - set(files))
    if sorted(changed) != ['e2-editor-app.js', 'editor-shell-v2/paragraph-editor-client.js'] or added or removed:
        raise ValueError('delta against 0.2.40 is not exactly the two declared shell files: '
                         + json.dumps({'changed': changed, 'added': added, 'removed': removed}))
    archive = SDK / 'build/archive' / ('host-0.2.41-engine-' + manifest['buildId'])
    if archive.exists():
        raise ValueError('archive already exists')
    shutil.copytree(APP / 'engine', archive)
    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.41 engine package\n\n'
        f'Host commit {candidate}, predecessor {PARENT} (0.2.40, exact 0.2.40 engine). Writer v25 / frozen shell 79 (finding 173 page fix); viewer v3, Calc v2 and 0.2.38 dark-theme HTML retained. v24 feature counts carried over (spec v25 section 14); v25 F1-F4, the section 9 reader and spec v79 U1/U2/B1/F3-79/F4-79/V0prime/E1-C hold; full K has not run. MANIFEST.json binds every raw/gzip/zstd member.\n')
    members = sorted(p for p in archive.rglob('*') if p.is_file())
    (OUT / 'archive.sha256').write_text(''.join(sha(p) + '  ' + p.relative_to(archive).as_posix() + '\n' for p in members))
    release = {'version': '0.2.41', 'hostParent': PARENT, 'hostCommit': candidate, 'branch': 'host-0.2.41',
               'buildId': manifest['buildId'], 'oldBuildId': old['buildId'], 'archive': str(archive),
               'oldArchive': str(OLD), 'manifestSha256': sha(archive / 'MANIFEST.json'),
               'totals': manifest['totals'], 'pages': pages, 'unchangedFiles': len(same),
               'unchanged': sorted(same), 'changed': changed, 'added': added, 'removed': removed,
               'archiveFilesVerified': len(members), 'installed': False, 'K': 'NOT_RUN',
               'nominalShippedHost': '0.2.26', 'shellGeneration': 79, 'v25Gates': gates, 'v79Gates': gates79,
               'countBasis': 'v24 counts carried over (owner, spec v25 section 14); v25 F1-F4 and section 9 reader; spec v79 U1/U2/B1/F3-79/F4-79/V0prime/E1-C',
               'shellBundleFileSha256': want['shell']['bundleFileSha256']}
    release['canonicalPackageReusedAfterWrapperError'] = args.reuse_existing
    (OUT / 'release.json').write_text(json.dumps(release, indent=1) + '\n')
    print(json.dumps(release, indent=1), flush=True)


if __name__ == '__main__':
    main()
