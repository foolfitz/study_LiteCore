#!/usr/bin/env python3
"""Package an isolated 0.2.43 host (Writer on profile e2-editor-v27, shell generation 81) from current verified dist, preserving the live predecessor.

Derived from findings/evidence/host-0.2.42/prepare-release.py (not edited).  Closed list of differences
(SPEC-M3-v27-finding-176 7.4):
- the live predecessor is host 93b1ebc (0.2.42) with the exact 0.2.42 engine, so OLD is the 0.2.42 archive
  (host-0.2.42-engine-01e6c3fb62626d16) and PARENT is 93b1ebc; the isolated candidate is build/host-0.2.43 and its
  info.xml must say 0.2.43;
- the editor page is generation 81's (tools/v81_four_arms_identity.py); the identity must name profile
  e2-editor-v27 and shell generation 81; the packaged editor page must name e2-editor-v27, whose artifacts are
  looked up under profiles/e2-editor-v27/;
- the old (0.2.42) package's page table: exactly one page (e2-editor.html) names e2-editor-v26, so removing that
  profile's four files takes it from no other page;
- the delta against 0.2.42 must be exactly: ONE changed record (e2-editor-app.js), the four profiles/e2-editor-v27/
  files added, the four profiles/e2-editor-v26/ files removed; this time ALL FOUR added files differ from the
  removed ones (v27 is a relink: new wasm, loader, worker and manifest), and v27's probe.wasm equal to v26's is a
  refusal (= no new engine; spec 7.4's red case);
- the evidence gate keeps 0.2.42's unchanged (carried-over v24 counts; v25 F1-F4 and the section 9 reader; spec
  v79's; spec v26's, F3-80 under append 2 included) and adds SPEC-M3-v27-finding-176's, all under
  findings/evidence/v27-176/, every file checked for existence first: U1 red then green and the whole shell suite;
  pre-link E1-E4 (receipts end OK), V0-v27 V0_V27_HOLDS with its positive control V0_V27_DIFFERS, S S_V27_HOLDS,
  W1/W2 and the static target (exit 0), M1-1 (red exit 1, green exit 0), L (CONFINED_V27_HOLDS), PIN (allAgree);
  PL-1 PL1_WOULD_VERIFY with self-test ALL_RED; P-v27 (both contract checks "v27 preconditions hold", I1
  VERDICT PASS, frozen set exit 0); S3 S3_HOLDS, its self-test ALL_RED and its three mutations
  S3_MUTATION_CAUGHT; S2' S2P_HOLDS with self-test ALL_RED; F3-81 reading 2 F3_81_DECLARED_ONLY with self-test
  ALL_RED, and reading 1 EXACTLY F3_RED with the four declared problems (spec 8 item 5, written out here, not
  imported from the reader); F4-81 24/24; V0'-81 V0_PRIME_HOLDS; E1-C intact.  From v27 on no reading here
  requires recoveryPairing.held true (spec 8 item 3);
- names (0.2.43, archive host-0.2.43-engine-<buildId>, attribution, release fields: shellGeneration 81,
  v27Gates, profileSuccessor (v26 and v27 sha256 of the four profile files), countBasis, f3_81Verdicts).
"""
import argparse
import gzip
import hashlib
import json
import posixpath
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SDK = ROOT / 'wasm_sdk_probe'
OUT = Path(__file__).resolve().parent
APP = SDK / 'build/host-0.2.43/litecore'
HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
PARENT = '93b1ebc4018335785974b9ef450323696c53dfbb'
OLD = SDK / 'build/archive/host-0.2.42-engine-01e6c3fb62626d16'
PROFILE = 'e2-editor-v27'
OLD_PROFILE = 'e2-editor-v26'
PROFILE_FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
SAME_BYTES = ()
SUCCESSOR_FILES = PROFILE_FILES
DECLARED_CHANGED = ['e2-editor-app.js']
DECLARED_ADDED = sorted(f'profiles/{PROFILE}/{n}' for n in PROFILE_FILES)
DECLARED_REMOVED = sorted(f'profiles/{OLD_PROFILE}/{n}' for n in PROFILE_FILES)
# Spec v26 append 2: the recorded F3-80 move, exactly.
F3_80_CELLS = ('an-aborted-gesture-stops-selecting', 'an-inline-format-reaches-a-selection',
               'the-page-agrees-with-the-engine-about-the-selection')
F3_80_READ01_PROBLEMS = [f'chrome {F3_80_CELLS[0]} [no-regression]: v24 PASS -> v25 NOT_ESTABLISHED',
                         f'chrome {F3_80_CELLS[1]} [P]: v24 FAIL -> v25 FAIL',
                         f'chrome {F3_80_CELLS[2]} [no-regression]: v24 PASS -> v25 NOT_ESTABLISHED']
F3_80_EQUAL01_MOVED = [{'browser': 'chrome', 'check': F3_80_CELLS[0], 'f379': 'PASS', 'v80': 'NOT_ESTABLISHED'},
                       {'browser': 'chrome', 'check': F3_80_CELLS[1], 'f379': 'PASS', 'v80': 'FAIL'},
                       {'browser': 'chrome', 'check': F3_80_CELLS[2], 'f379': 'PASS', 'v80': 'NOT_ESTABLISHED'}]
F3_80_EQUAL01_COUNTS = {'chrome': {'cells': 46, 'equal': 43}, 'firefox': {'cells': 46, 'equal': 46}}
F3_80_BASIS = 'F3-80 under spec v26 append 2: three Chrome cells count-only (L-175-blinds-three-F3-cells)'
# SPEC-M3-v27-finding-176 8 item 5: F3-81's reading 1, exactly.
F3_81_BULLETING = 'bulleting-a-blank-line-does-not-demand-a-rollback'
F3_81_READ01_PROBLEMS = [f'chrome {F3_81_BULLETING} [P]: v24 FAIL -> v25 FAIL',
                         'chrome notice-action-recovers-the-session [recovery-pairing]: held False',
                         f'firefox {F3_81_BULLETING} [P]: v24 FAIL -> v25 FAIL',
                         'firefox notice-action-recovers-the-session [recovery-pairing]: held False']
F3_81_BASIS = ('F3-81: the bulleting cell and recoveryPairing retired by design (spec v27 8), S3 is its successor')
sys.path.insert(0, str(SDK / 'tools'))
from package_m3_engine import package, validate_manifest
from probe_m3_assets import closure
from v81_four_arms_identity import identity
from compression import zstd


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def node_last(path, word):
    """The count on the LAST `ℹ <word> K` line of a `node --test` transcript; None if there is none."""
    counts = [int(m.group(1)) for line in path.read_text().splitlines()
              if (m := re.fullmatch('ℹ ' + word + r' (\d+)', line.strip()))]
    return counts[-1] if counts else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-existing', action='store_true', help='revalidate the already-produced canonical package after a wrapper error')
    args = parser.parse_args()
    if (OUT / 'release.json').exists():
        raise ValueError('release record already exists')
    if git(HOST, 'rev-parse', 'HEAD') != PARENT or git(HOST, 'status', '--porcelain'):
        raise ValueError('live predecessor differs from clean 93b1ebc (0.2.42)')
    if '<version>0.2.43</version>' not in (APP / 'appinfo/info.xml').read_text():
        raise ValueError('isolated version differs')
    candidate = git(APP, 'rev-parse', 'HEAD')
    if git(APP, 'diff', '--name-only', PARENT, candidate).splitlines() != ['appinfo/info.xml']:
        raise ValueError('candidate host source delta is not only its version')
    want = identity()
    if want['profile'] != PROFILE or want['shell'].get('generation') != 81:
        raise ValueError('identity module does not name e2-editor-v27 / generation 81: '
                         + json.dumps({'profile': want['profile'], 'generation': want['shell'].get('generation')}))
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
    # SPEC-M3-select-all-v26 (5.1-5.7 and append 1): every recorded result, refused when absent or wrong.
    v26 = ROOT / 'findings/evidence/select-all-v26'
    units = ('u1', 'u2', 'u3', 'u4')
    needed = (['p1/dist-profile.json', 'p1/red/red-cases.json', 'suite-after-175.txt', 's2/run-02/report.json',
               's1/run-01/report.json', 's1/self-test.json', 's2/self-test-02.json', 'f3/read-01.json', 'f3/equal-01.json',
               'f3/append2-read-01.json', 'f3/append2-self-test.json', 'f4/aggregate-judge.json', 'v0/v0-prime.json', 'v0/e1-c-after-put-back.json']
              + [f'{u}/{n}' for u in units for n in ('red-before.txt', 'green-after.txt')])
    missing = [n for n in needed if not (v26 / n).is_file()]
    if missing:
        raise ValueError('spec v26 evidence missing: ' + json.dumps(missing))

    def verdict(name, key='verdict'):
        return json.loads((v26 / name).read_bytes()).get(key)
    node_counts = {}

    def green(name):
        fail, passed = node_last(v26 / name, 'fail'), node_last(v26 / name, 'pass')
        node_counts[name] = {'fail': fail, 'pass': passed}
        return fail == 0 and passed is not None and passed > 0

    def red_then_green(unit):
        red = node_last(v26 / unit / 'red-before.txt', 'fail')
        node_counts[unit + '/red-before.txt'] = {'fail': red}
        return [red is not None and red > 0, green(unit + '/green-after.txt')], [True, True]
    f4_80 = json.loads((v26 / 'f4/aggregate-judge.json').read_bytes())
    gates26 = {
        'P1': (verdict('p1/dist-profile.json'), 'P1_HOLDS'),
        'P1-red': (verdict('p1/red/red-cases.json'), 'RED_CASES_HOLD'),
        **{unit.upper(): red_then_green(unit) for unit in units},
        'shellSuiteAfter175': (green('suite-after-175.txt'), True),
        'S2': (verdict('s2/run-02/report.json'), 'S2_HOLDS'),
        'S1': (verdict('s1/run-01/report.json'), 'S1_HOLDS'),
        'S1-selfTest': (verdict('s1/self-test.json', 'selfTest'), 'ALL_RED'),
        # Added by the main session after review: S2 was rerun (run-02) on the final bytes; its own self-test.
        'S2-selfTest': (verdict('s2/self-test-02.json', 'selfTest'), 'ALL_RED'),
        # Spec v26 append 2: the two original readings must be exactly the recorded move, and the append-2
        # reader decides it.  The closed lists are written out here, not imported from the reader.
        'F3-80-spec16': ([verdict('f3/read-01.json'), verdict('f3/read-01.json', 'problems')], ['F3_RED', F3_80_READ01_PROBLEMS]),
        'F3-80-equal': ([verdict('f3/equal-01.json'), verdict('f3/equal-01.json', 'moved'), verdict('f3/equal-01.json', 'counts')],
                        ['F3_80_MOVED', F3_80_EQUAL01_MOVED, F3_80_EQUAL01_COUNTS]),
        'F3-80-append2': (verdict('f3/append2-read-01.json'), 'F3_80_HOLDS_UNDER_APPEND_2'),
        'F3-80-append2-selfTest': (verdict('f3/append2-self-test.json', 'selfTest'), 'ALL_RED'),
        'F4-80': ('PASS' if not f4_80['problems'] and f4_80['rows'] == 24 and all(x['outcome'] == 'PASS' for x in f4_80['arms'].values()) else 'NOT', 'PASS'),
        'V0prime': (verdict('v0/v0-prime.json'), 'V0_PRIME_HOLDS'),
        'E1-C': (verdict('v0/e1-c-after-put-back.json', 'intact'), True),
    }
    if any(got != want_ for got, want_ in gates26.values()):
        raise ValueError('spec v26 verdicts do not hold: ' + json.dumps({'gates': gates26, 'nodeCounts': node_counts}))
    # SPEC-M3-v27-finding-176 (7.1-7.3): every recorded result, refused when absent or wrong.
    v27 = ROOT / 'findings/evidence/v27-176'
    needed27 = ['u1/red-before.txt', 'u1/green-after.txt', 'u1/suite-after.txt',
                'pre-link/e1-e3-native-tests.txt', 'pre-link/e4-unittest.txt', 'pre-link/v0-v27.json',
                'pre-link/v0-v27-positive-control.json', 'pre-link/s-v27.json', 'pre-link/static-tests.exit.txt',
                'pre-link/m1-1-red-without-v27-carrier.exit.txt', 'pre-link/m1-1-green-with-v27-carrier.exit.txt',
                'pre-link/l-confined.json', 'pre-link/source-pin.json', 'pl1/read-01.json', 'pl1/read-01-self-test.json',
                'post-link/build-log-check.txt', 'post-link/manifest-check.txt', 'post-link/i1/x1.txt',
                'post-link/frozen-set-check.exit.txt', 's3/run-01/report.json', 's3/self-test-01.json',
                's3/mutation-press-list-none/report.json', 's3/mutation-hide-review-toast/report.json',
                's3/mutation-cosmetic-review/report.json', 's2p/run-01/report.json', 's2p/self-test-01.json',
                'f3-81/equal-01.json', 'f3-81/equal-01-self-test.json', 'f3-81/read-01.json',
                'f4-81/aggregate-judge.json', 'v0/v0-prime.json', 'v0/e1-c-after-put-back.json']
    missing27 = [n for n in needed27 if not (v27 / n).is_file()]
    if missing27:
        raise ValueError('spec v27 evidence missing: ' + json.dumps(missing27))

    def v27json(name, key='verdict'):
        return json.loads((v27 / name).read_bytes()).get(key)

    def v27text(name):
        return (v27 / name).read_text()

    def v27count(name, word):
        node_counts27[name + ':' + word] = node_last(v27 / name, word)
        return node_counts27[name + ':' + word]
    node_counts27 = {}
    f4_81 = json.loads((v27 / 'f4-81/aggregate-judge.json').read_bytes())
    gates27 = {
        'U1': ([(v27count('u1/red-before.txt', 'fail') or 0) > 0, v27count('u1/green-after.txt', 'fail') == 0
                and (v27count('u1/green-after.txt', 'pass') or 0) > 0], [True, True]),
        'shellSuite': (v27count('u1/suite-after.txt', 'fail') == 0 and (v27count('u1/suite-after.txt', 'pass') or 0) > 0, True),
        'E1-E3': (v27text('pre-link/e1-e3-native-tests.txt').rstrip().endswith('OK'), True),
        'E4': (v27text('pre-link/e4-unittest.txt').rstrip().endswith('OK'), True),
        'V0-v27': ([v27json('pre-link/v0-v27.json'), v27json('pre-link/v0-v27-positive-control.json')],
                   ['V0_V27_HOLDS', 'V0_V27_DIFFERS']),
        'S': (v27json('pre-link/s-v27.json'), 'S_V27_HOLDS'),
        'static': (v27text('pre-link/static-tests.exit.txt').strip(), 'exit=0'),
        'M1-1': ([v27text('pre-link/m1-1-red-without-v27-carrier.exit.txt').split()[0],
                  v27text('pre-link/m1-1-green-with-v27-carrier.exit.txt').split()[0]], ['exit=1', 'exit=0']),
        'L': (v27json('pre-link/l-confined.json'), 'CONFINED_V27_HOLDS'),
        'PIN': (v27json('pre-link/source-pin.json', 'allAgree'), True),
        'PL-1': ([v27json('pl1/read-01.json'), v27json('pl1/read-01-self-test.json', 'selfTest')],
                 ['PL1_WOULD_VERIFY', 'ALL_RED']),
        'P-v27': ([v27text('post-link/build-log-check.txt').splitlines()[0], v27text('post-link/manifest-check.txt').splitlines()[0],
                   v27text('post-link/i1/x1.txt').rstrip().splitlines()[-1], v27text('post-link/frozen-set-check.exit.txt').strip()],
                  ['v27 preconditions hold', 'v27 preconditions hold', 'VERDICT PASS', 'exit=0']),
        'S3': ([v27json('s3/run-01/report.json'), v27json('s3/self-test-01.json', 'selfTest')], ['S3_HOLDS', 'ALL_RED']),
        'S3-mutations': ([v27json(f's3/mutation-{m}/report.json') for m in ('press-list-none', 'hide-review-toast', 'cosmetic-review')],
                         ['S3_MUTATION_CAUGHT'] * 3),
        'S2prime': ([v27json('s2p/run-01/report.json'), v27json('s2p/self-test-01.json', 'selfTest')], ['S2P_HOLDS', 'ALL_RED']),
        'F3-81-reading2': ([v27json('f3-81/equal-01.json'), v27json('f3-81/equal-01-self-test.json', 'selfTest')],
                           ['F3_81_DECLARED_ONLY', 'ALL_RED']),
        # Written out here, not imported from the reader (spec 8 item 5): exactly F3_RED and these four.
        'F3-81-reading1': ([v27json('f3-81/read-01.json'), v27json('f3-81/read-01.json', 'problems')],
                           ['F3_RED', F3_81_READ01_PROBLEMS]),
        'F4-81': ('PASS' if not f4_81['problems'] and f4_81['rows'] == 24 and all(x['outcome'] == 'PASS' for x in f4_81['arms'].values()) else 'NOT', 'PASS'),
        'V0prime-81': (v27json('v0/v0-prime.json'), 'V0_PRIME_HOLDS'),
        'E1-C': (v27json('v0/e1-c-after-put-back.json', 'intact'), True),
    }
    if any(got != want_ for got, want_ in gates27.values()):
        raise ValueError('spec v27 verdicts do not hold: ' + json.dumps({'gates': gates27, 'nodeCounts': node_counts27}))
    old = json.loads((OLD / 'MANIFEST.json').read_bytes())
    # Spec 5.9: no other page of the old package uses the profile whose four files this package removes.
    on_old_profile = sorted(h for h, p in old['source']['pages'].items() if p['profile'] == OLD_PROFILE)
    if on_old_profile != ['e2-editor.html']:
        raise ValueError('pages of the 0.2.42 package on e2-editor-v26 are not exactly the editor: ' + json.dumps(on_old_profile))
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
    if editor['profile'] != PROFILE or editor['moduleSha256'] != want['pageSha256']:
        raise ValueError('editor is not the verified generation-81 page')
    for name, expected in want['artifacts'].items():
        path = posixpath.normpath(f'profiles/{PROFILE}/' + name)
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
    if sorted(changed) != DECLARED_CHANGED or added != DECLARED_ADDED or removed != DECLARED_REMOVED:
        raise ValueError('delta against 0.2.42 is not exactly the page, the four v27 profile files'
                         ' added and the four v26 profile files removed: '
                         + json.dumps({'changed': changed, 'added': added, 'removed': removed}))
    raw_identity = lambda e: (e['sha256'], e['bytes'])  # noqa: E731
    successor = {n: {'v26': old['files'][f'profiles/{OLD_PROFILE}/{n}']['sha256'], 'v27': files[f'profiles/{PROFILE}/{n}']['sha256']}
                 for n in PROFILE_FILES}
    if any(raw_identity(old['files'][f'profiles/{OLD_PROFILE}/{n}']) != raw_identity(files[f'profiles/{PROFILE}/{n}']) for n in SAME_BYTES):
        raise ValueError('unreachable: SAME_BYTES is empty for v27 (a relink)')
    if any(successor[n]['v26'] == successor[n]['v27'] for n in SUCCESSOR_FILES):
        raise ValueError('a v27 profile file equals the removed v26 one (a relink changes all four; probe.wasm equal = no new engine): ' + json.dumps(successor))
    archive = SDK / 'build/archive' / ('host-0.2.43-engine-' + manifest['buildId'])
    if archive.exists():
        raise ValueError('archive already exists')
    shutil.copytree(APP / 'engine', archive)
    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.43 engine package\n\n'
        f'Host commit {candidate}, predecessor {PARENT} (0.2.42, exact 0.2.42 engine). Writer on profile e2-editor-v27 (owner-linked 2026-10-30, wasm c089dfd6) / frozen shell generation 81: finding 176 (the collapsed route judges a two-paragraph readback by its first block; the status strip says 待確認 on review); viewer v3, Calc v2 and 0.2.38 dark-theme HTML retained. v24 feature counts carried over (spec v25 section 14); v25 F1-F4, the section 9 reader, spec v79, spec v26 ({F3_80_BASIS}) and spec v27 PL-1/pre-link/P-v27/S3/S2prime/F3-81/F4-81/V0prime/E1-C hold ({F3_81_BASIS}); full K has not run. MANIFEST.json binds every raw/gzip/zstd member.\n')
    members = sorted(p for p in archive.rglob('*') if p.is_file())
    (OUT / 'archive.sha256').write_text(''.join(sha(p) + '  ' + p.relative_to(archive).as_posix() + '\n' for p in members))
    release = {'version': '0.2.43', 'hostParent': PARENT, 'hostCommit': candidate, 'branch': 'host-0.2.43',
               'buildId': manifest['buildId'], 'oldBuildId': old['buildId'], 'archive': str(archive),
               'oldArchive': str(OLD), 'manifestSha256': sha(archive / 'MANIFEST.json'),
               'totals': manifest['totals'], 'pages': pages, 'unchangedFiles': len(same),
               'unchanged': sorted(same), 'changed': changed, 'added': added, 'removed': removed,
               'profileSuccessor': successor,
               'archiveFilesVerified': len(members), 'installed': False, 'K': 'NOT_RUN',
               'nominalShippedHost': '0.2.26', 'shellGeneration': 81, 'v25Gates': gates, 'v79Gates': gates79,
               'v26Gates': gates26, 'v26NodeCounts': node_counts, 'v27Gates': gates27, 'v27NodeCounts': node_counts27,
               'countBasis': 'v24 counts carried over (owner, spec v25 section 14); v25 F1-F4 and section 9 reader; spec v79 U1/U2/B1/F3-79/F4-79/V0prime/E1-C; spec v26 P1/U1-U4/S1/S2 run-02/F3-80/F4-80/V0prime/E1-C; ' + F3_80_BASIS + '; spec v27 PL-1/pre-link/P-v27/S3/S2prime/F3-81/F4-81/V0prime/E1-C; ' + F3_81_BASIS,
               'f3_80Verdicts': {'read01': verdict('f3/read-01.json'), 'equal01': verdict('f3/equal-01.json'),
                                 'append2': verdict('f3/append2-read-01.json')},
               'f3_81Verdicts': {'read01': v27json('f3-81/read-01.json'), 'equal01': v27json('f3-81/equal-01.json')},
               'shellBundleFileSha256': want['shell']['bundleFileSha256']}
    release['canonicalPackageReusedAfterWrapperError'] = args.reuse_existing
    (OUT / 'release.json').write_text(json.dumps(release, indent=1) + '\n')
    print(json.dumps(release, indent=1), flush=True)


if __name__ == '__main__':
    main()
