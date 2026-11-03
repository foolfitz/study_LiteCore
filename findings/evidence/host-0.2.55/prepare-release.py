#!/usr/bin/env python3
"""Package an isolated 0.2.55 host (Calc document undo, SPEC-P-calc-undo) from current verified dist, preserving the live predecessor.

Derived from findings/evidence/host-0.2.54/prepare-release.py (not edited).  Closed list of differences: this paragraph; the predecessor is host
8c95b50 (0.2.54) with the exact 0.2.54 engine, and the candidate is build/host-0.2.55; the host source delta is info.xml alone again, so
0.2.54's blank-ods and G1/G3 re-run go (G1 to G3 stay in the gate); the served delta is the Calc page's four files and the Calc profile move
to ods-editor-v4, judged as 0.2.51 judged its move (the page's profile, wasm and module), and the buildId may no longer equal the
predecessor's; the gate adds Calc undo: CU on the frozen v4, its red on v3, the field-guard mutation, C on v4, the cell, range,
autosave and P2 arms on v4, NU-3, the pre-link syntax and export checks, the v4 manifest's capability bits; the names.

0.2.54's docstring follows.

Package an isolated 0.2.54 host (New spreadsheet, LibreOffice's document icons, SPEC-P-demo-batch-6) from current verified dist,
preserving the live predecessor.

Derived from findings/evidence/host-0.2.53/prepare-release.py (not edited).  Closed list of differences: this paragraph; the predecessor is host
6b1660c (0.2.53) with the exact 0.2.53 engine, and the candidate is build/host-0.2.54; the host source delta is the declared list (SOURCE_DECLARED
and blank-ods/ with its manifest's 30 files), not only info.xml; the served delta is empty and the buildId must be 0.2.53's; the gate adds G1 to
G3 and their red cases from static/, and G1 and G3 are run again on the candidate before packaging, their output kept in release.json; the names.

0.2.53's docstring follows.

Package an isolated 0.2.53 host (Enter over a selection, the empty-copy sentence, SPEC-P-demo-batch-5) from current verified dist,
preserving the live predecessor.

Derived from findings/evidence/host-0.2.52/prepare-release.py (not edited).  Closed list of differences: this paragraph; the predecessor is host
c657aba (0.2.52) with the exact 0.2.52 engine, and the candidate is build/host-0.2.53; Writer stays e2-editor-v32, generation 88; the delta is
e2-editor-app.js alone; the evidence gate reads generation 88 and P5 with its red case, P4's red cases from batch 4; the names.

0.2.52's docstring follows.

Package an isolated 0.2.52 host (the heading menu, list toggles, findings 180, 181, 182, SPEC-P-demo-batch-4) from current verified dist,
preserving the live predecessor.

Derived from findings/evidence/host-0.2.51/prepare-release.py (not edited).  Closed list of differences: this paragraph; the predecessor is host
1b8c667 (0.2.51) with the exact 0.2.51 engine, and the candidate is build/host-0.2.52; Writer is e2-editor-v32, generation 87, Calc and the viewer
stay; the delta is the five Writer page and shell files and one profile move; the evidence gate reads generation 87, P4 and its red cases, P1 and
C on this generation, F3 from its own run, whose runner now waits on the toast, and Calc's P2 and regression from batch 3, whose engine and page
these bytes are; the names.

0.2.51's docstring follows.

Package an isolated 0.2.51 host (alignment on both apps, Calc text colour and cell fill, SPEC-P-demo-batch-3 section 3) from current
verified dist, preserving the live predecessor.

Derived from findings/evidence/host-0.2.50/prepare-release.py (not edited).  Closed list of differences: this paragraph; the
predecessor is host 350cc4c (0.2.50) with the exact 0.2.50 engine, and the candidate is build/host-0.2.51; Writer is e2-editor-v31,
generation 86, Calc is ods-editor-v3, the viewer stays; the delta is the nine page and shell files and the two profile moves; the
evidence gate reads generation 86, P1, P2 and the Calc regression, C on this generation, and F3 through the clear-wait read (finding
178's append); the names.

0.2.50's docstring follows.

Derived from findings/evidence/host-0.2.49/prepare-release.py (not edited).  Closed list of differences: this paragraph; the
predecessor is host 7782714 (0.2.49) with the exact 0.2.49 engine, and the candidate is build/host-0.2.50; the profile is
e2-editor-v30, generation 85; the delta is `e2-editor-app.js` and the profile's four files moving; the evidence gate reads
demo-batch-3; the Calc module is compared with the predecessor's package and not with web/, which already holds the next batch's
Calc page, unshipped; the names.

0.2.49's docstring follows.

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
APP = SDK / 'build/host-0.2.55/litecore'
HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
PARENT = '8c95b50'
OLD = SDK / 'build/archive/host-0.2.54-engine-89860962782b3a21'
DECLARED_CHANGED = ['ods-editor-app.js', 'ods-editor.html', 'spreadsheet-shell/calc-document-sdk.js', 'spreadsheet-shell/calc-editor-session.js']
SOURCE_DECLARED = ['LICENSES/MPL-2.0.txt', 'appinfo/info.xml', 'img/README.md', 'img/oasis-spreadsheet.svg', 'img/oasis-text.svg', 'l10n/zh_TW.js',
                   'l10n/zh_TW.json', 'lib/Listener/FileCreatedFromTemplateListener.php', 'lib/Listener/RegisterTemplateCreatorListener.php',
                   'lib/Template/BlankDocument.php']
STATIC = OUT.parent / 'host-0.2.54/static'  # batch 6's static criteria, read where they were run
PROFILE = 'e2-editor-v32'
FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
OLD_CALC, CALC = 'ods-editor-v3', 'ods-editor-v4'
PACKS = ('base-viewer-v3-no35.21bec6461a48d3ec.data', 'base-viewer-v3-no35.43da6a24481dc483.metadata')
ADDED = sorted(f'profiles/{CALC}/{n}' for n in FILES + PACKS)
REMOVED = sorted(f'profiles/{OLD_CALC}/{n}' for n in FILES + PACKS)
CALC_WASM = '9f37ed5a447bfc23db058b24e7a129087eab1c303e3c833e0de8e01bffd33b00'
BATCH = ROOT / 'findings/evidence/demo-batch-1'
BATCH2 = ROOT / 'findings/evidence/demo-batch-2'
BATCH3 = ROOT / 'findings/evidence/demo-batch-3'
BATCH4 = ROOT / 'findings/evidence/demo-batch-4'
BATCH5 = ROOT / 'findings/evidence/demo-batch-5'
UNDO = ROOT / 'findings/evidence/calc-undo'
MUTATIONS = ('no-side-follow', 'no-centre', 'no-flex-none', 'stretched')
sys.path.insert(0, str(SDK / 'tools'))
from package_m3_engine import package, validate_manifest  # noqa: E402
from probe_m3_assets import closure  # noqa: E402
from v88_four_arms_identity import identity  # noqa: E402
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
    calc = load(BATCH5 / 'calc-sheet-view/run-88/report.json')
    z10_red = load(ROOT / 'findings/evidence/host-0.2.46/z10-red-on-0246/report.json')
    layout_red = load(BATCH2 / 'red-on-0247/report.json')
    calc_red = load(BATCH / 'calc-sheet-view/red-before/report.json')
    zoom = load(BATCH5 / 'writer-zoom/run-88/report.json')
    f4 = load(BATCH5 / 'f4-88/aggregate-judge.json')
    equal = json.loads((BATCH5 / 'f3-88/equal.stdout.txt').read_bytes())
    self_test = json.loads((BATCH5 / 'f3-88/equal-self-test.stdout.txt').read_bytes())
    v0 = load(BATCH5 / 'v0-88/v0-prime.json')
    e1c = [load(BATCH5 / 'freeze-88/e1-c.json').get('intact'), load(BATCH5 / 'v0-88/e1-c-after-put-back.json').get('intact')]
    shift_red = load(BATCH3 / 'shift-lines/red-on-v29/report.json')
    shift = load(BATCH5 / 'shift-lines/live-page-88/report.json')
    p1 = load(BATCH5 / 'p1/final-88/report.json')
    p4 = load(BATCH5 / 'p4/final-88/report.json')
    p5 = load(BATCH5 / 'p5/final-88/report.json')
    p5_red = load(BATCH5 / 'p5/red-on-generation-87/report.json')
    p4_reds = [load(BATCH4 / f'p4/{n}/report.json').get('verdict') for n in ('red-swap-levels-02', 'red-no-undo', 'red-no-second-press')]
    p1_reds = [load(BATCH3 / f'p1/{n}/report.json').get('verdict') for n in ('red-no-undo', 'red-swap-worker')]
    p2 = load(BATCH3 / 'p2/final-dist/report.json')
    p2_reds = [load(BATCH3 / f'p2/{n}/report.json') for n in ('red-wrong-fill', 'red-engine-v2')]
    regression = [load(BATCH3 / f'calc-regression/{n}/report.json') for n in ('cell-v3-01', 'range-v3-01', 'auto-v3-01')]
    g1, g1_red = load(STATIC / 'g1-check.stdout.txt'), load(STATIC / 'g1-red-one-byte.stdout.txt')
    g2, g3 = load(STATIC / 'g2-validate.stdout.txt'), load(STATIC / 'g3-choose.stdout.txt')
    g3_red = (STATIC / 'g3-red-manifest-missing-one.stdout.txt').read_text()
    cu = load(UNDO / 'after-freeze/cu/report.json')
    cu_red = load(UNDO / 'cu/red-on-v3-03/report.json')
    cu_mutation = load(UNDO / 'cu/mutation-field-guard/report.json')
    c_v4 = load(UNDO / 'after-freeze/calc-sheet-view-v4/report.json')
    arms_v4 = [load(UNDO / p) for p in ('after-freeze/cell-v4-dist/report.json', 'cu8-dev/range-v4/report.json',
                                                    'cu8-dev/auto/report.json', 'cu8-dev/p2-v4/report.json')]
    nu3 = [load(UNDO / f'nu3-{v}/report.json')['table'] for v in ('undo', 'control')]
    syntax = load(UNDO / 'pre-link-syntax-03/report.json')['verdict']
    ships, ships_red = load(UNDO / 'pre-link-ships/green.json'), load(UNDO / 'pre-link-ships/red-before-fix.json')
    v4_manifest = load(SDK / 'dist/profiles/ods-editor-v4/sdk-manifest.json')
    cu12 = ['CU-1/input', 'CU-1/cell-bold', 'CU-1/range-fill', 'CU-2/ctrl-z-input', 'CU-2/ctrl-y-input', 'CU-2/ctrl-z-bold', 'CU-2/ctrl-shift-z-bold']

    def all_pass(report):
        return bool(report['runs']) and all(not r.get('error') and not r.get('fatal') and r['checks']
                                            and all(c['pass'] for c in r['checks']) for r in report['runs']
                                            if not r.get('arm', '').startswith('cost'))
    red_editor = [c['id'] for r in calc_red['runs'] if r['page'] == 'editor' for c in r['checks'] if not c['pass']]
    gates = {
        'K-0.2.45': (k.get('verdict'), 'K_HOLDS'),
        'S1-red-on-v29': (shift_red.get('verdict'), 'S1_RED'),
        'S1': (shift.get('verdict'), 'S1_HOLDS'),
        'P1': (p1.get('verdict'), 'P1_HOLDS'),
        'P1-red-cases': (p1_reds, ['P1_RED', 'P1_RED']),
        'P4': (p4.get('verdict'), 'P4_HOLDS'),
        'P4-red-cases': (p4_reds, ['P4_RED', 'P4_RED', 'P4_RED']),
        'P5': (p5.get('verdict'), 'P5_HOLDS'),
        'P5-red-on-generation-87': (sorted({c['id'].split('/')[0] for r in p5_red['runs'] for c in r['checks'] if not c['pass']}), ['E1', 'E6', 'E7']),
        'P2': (all_pass(p2), True),
        'P2-red-cases': ([all_pass(r) for r in p2_reds], [False, False]),
        'Calc-regression-on-v3': ([all_pass(r) for r in regression], [True, True, True]),
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
        'F3-88': (equal.get('verdict'), 'F3_83_EQUAL'),
        'F3-88-self-test': (self_test.get('selfTest'), 'ALL_RED'),
        'F3-88-no-cell-moved': (equal['reading2']['moved'], []),
        'F4-88': ('PASS' if not f4['problems'] and f4['rows'] == 24
                  and all(x['outcome'] == 'PASS' for x in f4['arms'].values()) else 'NOT', 'PASS'),
        'V0prime-88': (v0.get('verdict'), 'V0_PRIME_HOLDS'),
        'E1-C': (e1c, [True, True]),
        'G1': (g1.get('identical'), True),
        'G1-red-one-byte': (g1_red.get('identical'), False),
        'G2': ([g2.get('validated'), g2.get('passed'), g2.get('failed'), g2.get('hashesMatch')], [30, 30, [], True]),
        'G3': (g3.get('verdict'), 'G3_HOLDS'),
        'G3-red-manifest-missing-one': ('is not in MANIFEST.json' in g3_red, True),
        'CU-v4': (cu.get('verdict'), 'CU_HOLDS'),
        'CU-v4-browsers': (sorted(r['browser'] for r in cu['runs']), ['chrome', 'firefox']),
        'CU-red-on-v3': ([all(i in {c['id'] for c in r['checks'] if not c['pass']} for i in cu12) and not r['fatal'] for r in cu_red['runs']],
                         [True, True]),
        'CU-field-guard-mutation': ([sorted(c['id'] for c in r['checks'] if not c['pass']) for r in cu_mutation['runs']],
                                    [['CU-3/field-keeps-its-undo'], ['CU-3/field-keeps-its-undo']]),
        'C-v4': (all_pass(c_v4), True),
        'Calc-arms-on-v4': ([all_pass(r) for r in arms_v4], [True, True, True, True]),
        'NU-3': ([{k: t[k] for k in ('cell-bold', 'cell-italic', 'draft-then-bold')} for t in nu3],
                 [{'cell-bold': 1, 'cell-italic': 1, 'draft-then-bold': 2}, {'cell-bold': 3, 'cell-italic': 3, 'draft-then-bold': 4}]),
        'pre-link-syntax': (all(syntax.values()) and len(syntax) == 4, True),
        'pre-link-ships': ([ships.get('verdict'), ships_red.get('missing')], ['SHIPS', ['oxsdk_document_redo', 'oxsdk_document_undo']]),
        'v4-manifest': ([v4_manifest.get('profile'), v4_manifest.get('expectedCapabilityBits'), 'undo' in v4_manifest.get('capabilities', [])],
                        ['ods-editor-v4', 1046835, True]),
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
        raise ValueError('live predecessor differs from clean 8c95b50 (0.2.54)')
    if '<version>0.2.55</version>' not in (APP / 'appinfo/info.xml').read_text():
        raise ValueError('isolated version differs')
    candidate = git(APP, 'rev-parse', 'HEAD')
    source_delta = git(APP, 'diff', '--name-only', parent, candidate).splitlines()
    if source_delta != ['appinfo/info.xml']:
        raise ValueError('candidate host source delta is not only its version: ' + json.dumps(source_delta))
    want = identity()
    if want['profile'] != PROFILE or want['shell'].get('generation') != 88:
        raise ValueError('identity module does not name e2-editor-v32 / generation 88')
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
    if pages['ods-viewer.html'] != old['source']['pages']['ods-viewer.html'] or files['ods-viewer.html'] != old['files']['ods-viewer.html']:
        raise ValueError('viewer identity changed')
    sheet = pages['ods-editor.html']
    if sheet['profile'] != CALC or sheet['wasmSha256'] != CALC_WASM or sheet['moduleSha256'] != sha(SDK / 'web/ods-editor-app.js'):
        raise ValueError('Calc page is not the verified ods-editor-v4 page')
    editor = pages['e2-editor.html']
    if editor['profile'] != PROFILE or editor['moduleSha256'] != want['pageSha256']:
        raise ValueError('editor is not the verified generation-88 page')
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
    if changed != DECLARED_CHANGED or added != ADDED or removed != REMOVED:
        raise ValueError('delta against 0.2.54 is not the Calc page and the v4 move: '
                         + json.dumps({'changed': changed, 'added': added, 'removed': removed}))
    archive = SDK / 'build/archive' / ('host-0.2.55-engine-' + manifest['buildId'])
    if archive.exists():
        raise ValueError('archive already exists')
    shutil.copytree(APP / 'engine', archive)
    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.55 engine package\n\n'
        f'Host commit {candidate}, predecessor {parent} (0.2.54, exact 0.2.54 engine). Writer on profile e2-editor-v32, shell '
        'generation 88, Calc on ods-editor-v4: Calc document undo (SPEC-P-calc-undo). Uncounted candidate.\n')
    members = sorted(p for p in archive.rglob('*') if p.is_file())
    (OUT / 'archive.sha256').write_text(''.join(sha(p) + '  ' + p.relative_to(archive).as_posix() + '\n' for p in members))
    release = {'version': '0.2.55', 'hostParent': parent, 'hostCommit': candidate, 'branch': 'host-0.2.55',
               'buildId': manifest['buildId'], 'oldBuildId': old['buildId'], 'archive': str(archive),
               'oldArchive': str(OLD), 'manifestSha256': sha(archive / 'MANIFEST.json'),
               'totals': manifest['totals'], 'pages': pages, 'unchangedFiles': len(same),
               'changed': changed, 'added': added, 'removed': removed,
               'archiveFilesVerified': len(members), 'installed': False, 'K': 'NOT_RUN',
               'nominalShippedHost': '0.2.45', 'shellGeneration': 88, 'gates': gates,
               'countBasis': 'K holds on 0.2.45 (release-0.2.45/k-verdict.json); this release moves Calc to ods-editor-v4 with its page, Writer and the viewer unchanged, and is read by its own gates, not counted',
               'shellBundleFileSha256': want['shell']['bundleFileSha256'], 'hostSourceDelta': source_delta}
    release['canonicalPackageReusedAfterWrapperError'] = args.reuse_existing
    (OUT / 'release.json').write_text(json.dumps(release, indent=1) + '\n')
    print(json.dumps({k: release[k] for k in ('version', 'hostCommit', 'buildId', 'changed', 'unchangedFiles', 'archiveFilesVerified')}, indent=1), flush=True)


if __name__ == '__main__':
    main()
