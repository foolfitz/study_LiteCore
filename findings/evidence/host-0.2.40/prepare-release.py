#!/usr/bin/env python3
"""Package an isolated 0.2.40 host (Writer v25) from current verified dist, preserving the live predecessor.

Derived from findings/evidence/host-0.2.39/prepare-release.py (not edited).  Closed list of differences:
- the live predecessor is host 4a8b3cd (label 0.2.39) running the EXACT 0.2.38 engine after the
  2026-10-29 rollback, so OLD is the 0.2.38 archive and PARENT is 4a8b3cd;
- the editor is v25 / frozen shell 78 (tools/v25_four_arms_identity.py), not v24 / 77;
- the evidence gate reads the carried-over v24 counts (spec v25 section 14) AND v25's own 6.3 checks
  F1/F2/F3/F4 and the section 9 reader, each by its recorded verdict;
- names (0.2.40, archive, attribution, release fields).
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
APP = SDK / 'build/host-0.2.40/litecore'
HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
PARENT = '4a8b3cd23a746fa6645823be7819bab91cdbbefe'
OLD = SDK / 'build/archive/host-0.2.38-engine-5ad1f70a8c5f7d2f'
sys.path.insert(0, str(SDK / 'tools'))
from package_m3_engine import package, validate_manifest
from probe_m3_assets import closure
from v25_four_arms_identity import identity
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
        raise ValueError('live predecessor differs from clean 4a8b3cd (label 0.2.39)')
    if '<version>0.2.40</version>' not in (APP / 'appinfo/info.xml').read_text():
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
        raise ValueError('editor is not the verified v25 page')
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
    archive = SDK / 'build/archive' / ('host-0.2.40-engine-' + manifest['buildId'])
    if archive.exists():
        raise ValueError('archive already exists')
    shutil.copytree(APP / 'engine', archive)
    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.40 engine package\n\n'
        f'Host commit {candidate}, predecessor {PARENT} (label 0.2.39, live engine exact 0.2.38). Writer v25 / frozen shell 78; viewer v3, Calc v2 and 0.2.38 dark-theme HTML retained. v24 feature counts carried over (spec v25 section 14); v25 F1-F4 and the section 9 reader hold; full K has not run. MANIFEST.json binds every raw/gzip/zstd member.\n')
    members = sorted(p for p in archive.rglob('*') if p.is_file())
    (OUT / 'archive.sha256').write_text(''.join(sha(p) + '  ' + p.relative_to(archive).as_posix() + '\n' for p in members))
    release = {'version': '0.2.40', 'hostParent': PARENT, 'hostCommit': candidate, 'branch': 'host-0.2.40',
               'buildId': manifest['buildId'], 'oldBuildId': old['buildId'], 'archive': str(archive),
               'oldArchive': str(OLD), 'manifestSha256': sha(archive / 'MANIFEST.json'),
               'totals': manifest['totals'], 'pages': pages, 'unchangedFiles': len(same),
               'unchanged': sorted(same), 'changed': changed, 'added': added, 'removed': removed,
               'archiveFilesVerified': len(members), 'installed': False, 'K': 'NOT_RUN',
               'nominalShippedHost': '0.2.26', 'shellGeneration': 78, 'v25Gates': gates,
               'countBasis': 'v24 counts carried over (owner, spec v25 section 14); v25 F1-F4 and section 9 reader',
               'shellBundleFileSha256': want['shell']['bundleFileSha256']}
    release['canonicalPackageReusedAfterWrapperError'] = args.reuse_existing
    (OUT / 'release.json').write_text(json.dumps(release, indent=1) + '\n')
    print(json.dumps(release, indent=1), flush=True)


if __name__ == '__main__':
    main()
