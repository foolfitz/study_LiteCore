#!/usr/bin/env python3
"""Package an isolated 0.2.49 host (the whole Calc page light under any theme, SPEC-P-demo-batch-2 append 2) from current verified dist,
preserving the live predecessor.

Derived from findings/evidence/host-0.2.47/prepare-release.py (not edited).  Closed list of differences: this paragraph; the
predecessor is host d6cbbd9 (0.2.47) with the exact 0.2.47 engine, and the candidate is build/host-0.2.48; the host source delta
adds templates/viewer.php; the delta is exactly `e2-editor.html` and `ods-editor.html`; the evidence gate reads the runs on these
two pages under demo-batch-2 and the layout red on 0.2.47, the zoom mutations and the Calc red stay demo-batch-1's; the Calc page's
HTML may move, the viewer's may not; the names.

0.2.47's docstring follows.

Derived from findings/evidence/host-0.2.46/prepare-release.py (not edited).  Closed list of differences: that paragraph; the
predecessor is host b9d33d7 (0.2.46) with the exact 0.2.46 engine, and the candidate is build/host-0.2.47; the delta is exactly
`e2-editor.html`; the evidence gate reads the runs on the final HTML (writer-zoom run-02 and mutation-02-*, f4-84-final,
f3-84-final, v0-02) and the Z10 red on 0.2.46; the viewer and Calc pages must now equal the predecessor's; the names.

0.2.46's docstring follows.

Written by hand (SPEC-P-demo-batch-1 section 4).  The packaging half is findings/evidence/host-0.2.45/prepare-release.py's: the
same refusals in the same order.  The evidence gate is not.  0.2.45's gate read every result since v24 because nothing had
been counted; 0.2.45 has now been counted, so this one reads that verdict and then this batch's results.  Closed list of
differences in the packaging half:
- the predecessor is host eeac22c (0.2.45) with the exact 0.2.45 engine, and the candidate is build/host-0.2.46;
- the delta is exactly the five page files of the batch, nothing added or removed: no profile moves;
- the viewer and Calc pages are now expected to change, so instead of "their identity did not change" each must keep its
  profile and wasm, and its module must be the source in this tree;
- the names and the release fields.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import posixpath
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SDK = ROOT / 'wasm_sdk_probe'
OUT = Path(__file__).resolve().parent
APP = SDK / 'build/host-0.2.49/litecore'
HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
PARENT = '0411329'
OLD = SDK / 'build/archive/host-0.2.48-engine-a632c4463e700493'
PROFILE = 'e2-editor-v29'
DECLARED_CHANGED = ['ods-editor.html']
BATCH = ROOT / 'findings/evidence/demo-batch-1'
BATCH2 = ROOT / 'findings/evidence/demo-batch-2'
MUTATIONS = ('no-side-follow', 'no-centre', 'no-flex-none', 'stretched')
sys.path.insert(0, str(SDK / 'tools'))
from package_m3_engine import package, validate_manifest  # noqa: E402
from probe_m3_assets import closure  # noqa: E402
from v84_four_arms_identity import identity  # noqa: E402
from compression import zstd  # noqa: E402


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def load(path):
    return json.loads(path.read_bytes())


def gate():
    """Every result, read from its file; a missing file is a refusal."""
    k = load(ROOT / 'findings/evidence/release-0.2.45/k-verdict.json')
    calc = load(BATCH2 / 'calc-sheet-view/run-02/report.json')
    z10_red = load(ROOT / 'findings/evidence/host-0.2.46/z10-red-on-0246/report.json')
    layout_red = load(BATCH2 / 'red-on-0247/report.json')
    calc_red = load(BATCH / 'calc-sheet-view/red-before/report.json')
    zoom = load(BATCH2 / 'writer-zoom/run-01/report.json')
    f4 = load(BATCH2 / 'f4-84/aggregate-judge.json')
    equal = json.loads((BATCH2 / 'f3-84/equal.stdout.txt').read_bytes())
    self_test = json.loads((BATCH2 / 'f3-84/equal-self-test.stdout.txt').read_bytes())
    v0 = load(BATCH2 / 'v0/v0-prime.json')
    e1c = [load(BATCH / 'freeze-84/e1-c.json').get('intact'), load(BATCH2 / 'v0/e1-c-after-put-back.json').get('intact')]

    def all_pass(report):
        return bool(report['runs']) and all(not r.get('error') and not r.get('fatal') and r['checks']
                                            and all(c['pass'] for c in r['checks']) for r in report['runs']
                                            if not r.get('arm', '').startswith('cost'))
    red_editor = [c['id'] for r in calc_red['runs'] if r['page'] == 'editor' for c in r['checks'] if not c['pass']]
    gates = {
        'K-0.2.45': (k.get('verdict'), 'K_HOLDS'),
        'T6-red-on-0.2.48': (load(BATCH2 / 't6-red-on-0248/report.json').get('verdict'), 'T6_RED'),
        'Layout-red-on-0.2.47': (all(i in {c['id'] for r in layout_red['runs'] for c in r['checks'] if not c['pass']}
                                     for i in ('T1/close-right-gap-equal', 'T2/save-is-first', 'T4/writer-contrast')), True),
        'Z10-red-on-0.2.46': (sorted(c['id'] for r in z10_red['runs'] for c in r['checks'] if not c['pass']),
                              ['Z10/fit-has-no-side-scroll', 'Z10/fit-returns-to-the-width-it-opened-at']),
        'C-green': (all_pass(calc), True),
        'C-browsers-pages': (sorted((r['browser'], r['page']) for r in calc['runs']),
                             [['chrome', 'editor'], ['chrome', 'viewer'], ['firefox', 'editor'], ['firefox', 'viewer']]),
        'C-red-before-shows-the-symptom': ('C1/first-visit-sheet2' in red_editor, True),
        'Z': (zoom.get('verdict'), 'Z_HOLDS'),
        'Z-mutations': ([load(BATCH / f'writer-zoom/mutation-02-{m}/report.json').get('verdict') for m in MUTATIONS],
                        ['MUTATION_CAUGHT'] * len(MUTATIONS)),
        'F3-84': (equal.get('verdict'), 'F3_83_EQUAL'),
        'F3-84-self-test': (self_test.get('selfTest'), 'ALL_RED'),
        'F4-84': ('PASS' if not f4['problems'] and f4['rows'] == 24
                  and all(x['outcome'] == 'PASS' for x in f4['arms'].values()) else 'NOT', 'PASS'),
        'V0prime-84': (v0.get('verdict'), 'V0_PRIME_HOLDS'),
        'E1-C': (e1c, [True, True]),
    }
    gates = {k_: (list(g) if isinstance(g, list) else g, w) for k_, (g, w) in gates.items()}
    wrong = {k_: v for k_, v in gates.items() if json.loads(json.dumps(v[0])) != json.loads(json.dumps(v[1]))}
    if wrong:
        raise ValueError('batch verdicts do not hold: ' + json.dumps(wrong, ensure_ascii=False))
    return gates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-existing', action='store_true', help='revalidate the already-produced canonical package after a wrapper error')
    parser.add_argument('--gate-only', action='store_true', help='read the evidence gate and stop; nothing is packaged')
    args = parser.parse_args()
    gates = gate()
    if args.gate_only:
        print(json.dumps({k: v[0] for k, v in gates.items()}, indent=1))
        return
    if (OUT / 'release.json').exists():
        raise ValueError('release record already exists')
    parent = git(HOST, 'rev-parse', 'HEAD')
    if not parent.startswith(PARENT) or git(HOST, 'status', '--porcelain'):
        raise ValueError('live predecessor differs from clean 0411329 (0.2.48)')
    if '<version>0.2.49</version>' not in (APP / 'appinfo/info.xml').read_text():
        raise ValueError('isolated version differs')
    candidate = git(APP, 'rev-parse', 'HEAD')
    if git(APP, 'diff', '--name-only', parent, candidate).splitlines() != ['appinfo/info.xml']:
        raise ValueError('candidate host source delta is not only its version')
    want = identity()
    if want['profile'] != PROFILE or want['shell'].get('generation') != 84:
        raise ValueError('identity module does not name e2-editor-v29 / generation 84')
    old = load(OLD / 'MANIFEST.json')
    old_files = [p.relative_to(OLD) for p in OLD.rglob('*') if p.is_file() and p.name != 'ATTRIBUTION.md']
    if any(sha(OLD / n) != sha(HOST / 'engine' / n) for n in old_files):
        raise ValueError('live predecessor engine differs from its archive')
    started = time.monotonic()
    manifest = load(APP / 'engine/MANIFEST.json') if args.reuse_existing else package(APP)
    if validate_manifest(manifest):
        raise ValueError('canonical manifest does not hold')
    derived = closure(SDK / 'dist')
    if {n: e['sha256'] for n, e in manifest['files'].items()} != {e['path']: e['sha256'] for e in derived['files']}:
        raise ValueError('existing package differs from the complete current closure')
    print('packaged', manifest['buildId'], round(time.monotonic() - started, 2), flush=True)
    files = manifest['files']
    pages = manifest['source']['pages']
    for html, module in (('ods-viewer.html', 'web/ods-viewer-app.js'), ('ods-editor.html', 'web/ods-editor-app.js')):
        if pages[html] != old['source']['pages'][html] or pages[html]['moduleSha256'] != sha(SDK / module) \
                or (html == 'ods-viewer.html' and files[html] != old['files'][html]):
            raise ValueError('viewer/Calc identity changed, or the viewer HTML moved: ' + html)
    editor = pages['e2-editor.html']
    if editor['profile'] != PROFILE or editor['moduleSha256'] != want['pageSha256']:
        raise ValueError('editor is not the verified generation-84 page')
    if files['e2-editor.html']['sha256'] != want['originalHtmlSha256']:
        raise ValueError('editor HTML is not the verified page')
    for name, expected in want['artifacts'].items():
        path = posixpath.normpath(f'profiles/{PROFILE}/' + name)
        if path in editor['declaredNotLoaded']:
            if path in files:
                raise ValueError('declared-not-loaded file was packaged: ' + path)
            continue
        if files[path]['sha256'] != expected:
            raise ValueError('packaged Writer artifact differs: ' + name)
    for name, entry in files.items():
        raw = (SDK / 'dist' / name).read_bytes()
        if sha(SDK / 'dist' / name) != entry['sha256']:
            raise ValueError('dist drift: ' + name)
        for suffix, decode in (('.gz', gzip.decompress), ('.zst', zstd.decompress)):
            if decode((APP / 'engine/files' / (name + suffix)).read_bytes()) != raw:
                raise ValueError('coding differs: ' + name + suffix)
    same = [n for n, entry in files.items() if old['files'].get(n) == entry]
    changed = sorted(n for n, entry in files.items() if n in old['files'] and old['files'][n] != entry)
    added = sorted(set(files) - set(old['files'])); removed = sorted(set(old['files']) - set(files))
    if changed != DECLARED_CHANGED or added or removed:
        raise ValueError('delta against 0.2.48 is not exactly ods-editor.html: '
                         + json.dumps({'changed': changed, 'added': added, 'removed': removed}))
    archive = SDK / 'build/archive' / ('host-0.2.49-engine-' + manifest['buildId'])
    if archive.exists():
        raise ValueError('archive already exists')
    shutil.copytree(APP / 'engine', archive)
    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.49 engine package\n\n'
        f'Host commit {candidate}, predecessor {parent} (0.2.48, exact 0.2.48 engine). Writer on profile e2-editor-v29, shell '
        'generation 84; the whole Calc page light under any theme (SPEC-P-demo-batch-2 append 2). Uncounted candidate.\n')
    members = sorted(p for p in archive.rglob('*') if p.is_file())
    (OUT / 'archive.sha256').write_text(''.join(sha(p) + '  ' + p.relative_to(archive).as_posix() + '\n' for p in members))
    release = {'version': '0.2.49', 'hostParent': parent, 'hostCommit': candidate, 'branch': 'host-0.2.49',
               'buildId': manifest['buildId'], 'oldBuildId': old['buildId'], 'archive': str(archive),
               'oldArchive': str(OLD), 'manifestSha256': sha(archive / 'MANIFEST.json'),
               'totals': manifest['totals'], 'pages': pages, 'unchangedFiles': len(same),
               'changed': changed, 'added': added, 'removed': removed,
               'archiveFilesVerified': len(members), 'installed': False, 'K': 'NOT_RUN',
               'nominalShippedHost': '0.2.45', 'shellGeneration': 84, 'gates': gates,
               'countBasis': 'K holds on 0.2.45 (release-0.2.45/k-verdict.json); this batch changes pages only and is read by its own gates',
               'shellBundleFileSha256': want['shell']['bundleFileSha256']}
    release['canonicalPackageReusedAfterWrapperError'] = args.reuse_existing
    (OUT / 'release.json').write_text(json.dumps(release, indent=1) + '\n')
    print(json.dumps({k: release[k] for k in ('version', 'hostCommit', 'buildId', 'changed', 'unchangedFiles', 'archiveFilesVerified')}, indent=1), flush=True)


if __name__ == '__main__':
    main()
