#!/usr/bin/env python3
"""Package an isolated 0.2.45 host (Writer on profile e2-editor-v29, shell generation 83, the icon toolbar HTML) from current verified dist, preserving the live predecessor.

Derived from findings/evidence/host-0.2.44/prepare-release.py (not edited).  Closed list of differences
(SPEC-M3-v29-tick-pacing append 6):
- the live predecessor is host a97724f (0.2.44) with the exact 0.2.44 engine, so OLD is the 0.2.44 archive
  (host-0.2.44-engine-dacdfa20fd4ff1ea) and PARENT is a97724f; the isolated candidate is build/host-0.2.45 and its
  info.xml must say 0.2.45;
- the editor page is generation 83's (tools/v83_four_arms_identity.py); the identity must name profile
  e2-editor-v29 and shell generation 83; the packaged editor page must name e2-editor-v29, and the packaged
  e2-editor.html must be the identity's originalHtmlSha256 (the icon HTML is outside the shell bundle);
- the old (0.2.44) package's page table: exactly one page (e2-editor.html) names e2-editor-v28;
- the delta against 0.2.44 must be exactly: TWO changed records (e2-editor-app.js and e2-editor.html), the four
  profiles/e2-editor-v29/ files added, the four profiles/e2-editor-v28/ files removed;
- SAME_BYTES is sdk-worker.js and SUCCESSOR_FILES the other three: v29's worker is v28's by bytes (spec v29 2), so
  the worker differing is a refusal, and probe.wasm equal is a refusal (= no new engine);
- the evidence gate keeps 0.2.44's unchanged and adds SPEC-M3-v29-tick-pacing's, all under
  findings/evidence/v29-177/, every file checked for existence first: U (four mutations red), S (exit 0, three
  controls exit 1), M (the named reds), the contract and the archive (receipt in this directory), T1 (C2 three
  times PASS; judge_p2 PASS once and twice exactly the one line spec v29 6 leaves to the owner), T2 (recomputed
  here, eight cases and the red arm), F3-83 single-press F3_83_EQUAL with reading 1 exactly F3-82's four and the
  pinned runner's F3_83_MOVED (finding 178), F4-83 final page 24/24, S4 and six mutations, merge, gap order, T4 x3,
  V0'-83, E1-C, the toolbar on both browsers; and SPEC-M3-own-stack's ST1, ST2/ST3 and ST4 readings;
- names (0.2.45, archive host-0.2.45-engine-<buildId>, attribution, release fields: shellGeneration 83, v29Gates,
  profileSuccessor (v28 and v29), countBasis, f3_83Verdicts).

The 0.2.44 derivation note follows, unchanged.

Package an isolated 0.2.44 host (Writer on profile e2-editor-v28, shell generation 82) from current verified dist, preserving the live predecessor.

Derived from findings/evidence/host-0.2.43/prepare-release.py (not edited).  Closed list of differences
(SPEC-M3-v28-last-line-fallback 7.4):
- the live predecessor is host ae8240d (0.2.43) with the exact 0.2.43 engine, so OLD is the 0.2.43 archive
  (host-0.2.43-engine-741afd80a36e673b) and PARENT is ae8240d; the isolated candidate is build/host-0.2.44 and its
  info.xml must say 0.2.44;
- the editor page is generation 82's (tools/v82_four_arms_identity.py); the identity must name profile
  e2-editor-v28 and shell generation 82; the packaged editor page must name e2-editor-v28;
- the old (0.2.43) package's page table: exactly one page (e2-editor.html) names e2-editor-v27;
- the delta against 0.2.43 must be exactly: TWO changed records (e2-editor-app.js and
  editor-shell-v2/paragraph-editor-client.js; spec 7.4, review item 20), the four profiles/e2-editor-v28/ files
  added, the four profiles/e2-editor-v27/ files removed, all four added files different from the removed ones
  (v28 is a relink; probe.wasm equal is a refusal);
- the evidence gate keeps 0.2.43's unchanged (v24 counts carried over; v25; spec v79; spec v26; spec v27) and adds
  SPEC-M3-v28-last-line-fallback's, all under findings/evidence/v28-083/, every file checked for existence first:
  U-v28 (red first, the three page tests red first, the shell suite with exactly one failing test, the named
  L-select-all-u2-pins-v26-profile), E1 red first and E1/E2 green, E3's green receipts, E4, V0-v28 with its positive
  control, S, W1 green and its red case, W2, the static target, M1-1 red and green, L, PIN, the v27 archive check;
  PL-1-v28 and its self-test; P-v28 (the link's three contract lines, the frozen-set delta); the cutover's E1-C;
  S4 S4_HOLDS with its self-test and six mutations caught; the freeze's E1-C; F3-82 reading 2 F3_82_EQUAL with
  its self-test and reading 1 EXACTLY F3-81's F3_RED with the four problems (written out here); F4-82 24/24;
  V0'-82; E1-C;
- names (0.2.44, archive host-0.2.44-engine-<buildId>, attribution, release fields: shellGeneration 82,
  v28Gates, profileSuccessor (v27 and v28), countBasis, f3_82Verdicts).

The 0.2.43 derivation note follows, unchanged.

Package an isolated 0.2.43 host (Writer on profile e2-editor-v27, shell generation 81) from current verified dist, preserving the live predecessor.

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
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SDK = ROOT / 'wasm_sdk_probe'
OUT = Path(__file__).resolve().parent
APP = SDK / 'build/host-0.2.45/litecore'
HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
PARENT = 'a97724f302ddc7eb7180a4d3fd6d4863bfd6952d'
OLD = SDK / 'build/archive/host-0.2.44-engine-dacdfa20fd4ff1ea'
PROFILE = 'e2-editor-v29'
OLD_PROFILE = 'e2-editor-v28'
PROFILE_FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
SAME_BYTES = ('sdk-worker.js',)
SUCCESSOR_FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json')
DECLARED_CHANGED = ['e2-editor-app.js', 'e2-editor.html']
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
# SPEC-M3-v28-last-line-fallback 7.3 F3-82: reading 1 exactly F3-81's (no declared move, spec v28 8 item 1).
F3_82_READ01_PROBLEMS = F3_81_READ01_PROBLEMS
F3_82_BASIS = 'F3-82: every cell equal to F3-81 (no declared move, spec v28 8); S4 measures the last line'
U2_NAMED = 'U2 wiring: the handler takes Ctrl+A before `if (accel) return;`, with a label, on profile v26'
S4_MUTATIONS = ('press-list-none', 'cosmetic-review', 'wrong-button-b-number', 'wrong-button-b-none',
                'wrong-button-b-heading', 'wrong-button-b-body')
# press-list-none's first report has one NE run (page not ready) and does not count; its re-run does (s4/README.md).
S4_MUTATION_DIRS = {'press-list-none': 'mutation-press-list-none-run-02'}
# SPEC-M3-v29-tick-pacing append 2: reading 1 exactly F3-82's; no declared move.
F3_83_READ01_PROBLEMS = F3_82_READ01_PROBLEMS
F3_83_BASIS = 'F3-83 single-press (finding 178): every cell equal to F3-82, no declared move'
S4_MUTATIONS_V29 = S4_MUTATIONS  # on v29 press-list-none's first report counts (s4/README.md)
V29_ARCHIVE = SDK / 'build/archive/e2-editor-v29-e61e5890-worker-a5df83db'
T1_PASS = 'PASS: both browsers, every cell'
T1_P2_NAMED = 'FAIL: chrome boundaries-gap200 commit median'
T1_P2_WORDS = ['chrome', 'boundaries-gap200', 'commit', 'median:']
sys.path.insert(0, str(SDK / 'tools'))
from package_m3_engine import package, validate_manifest
from probe_m3_assets import closure
from v83_four_arms_identity import identity
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
        raise ValueError('live predecessor differs from clean a97724f (0.2.44)')
    if '<version>0.2.45</version>' not in (APP / 'appinfo/info.xml').read_text():
        raise ValueError('isolated version differs')
    candidate = git(APP, 'rev-parse', 'HEAD')
    if git(APP, 'diff', '--name-only', PARENT, candidate).splitlines() != ['appinfo/info.xml']:
        raise ValueError('candidate host source delta is not only its version')
    want = identity()
    if want['profile'] != PROFILE or want['shell'].get('generation') != 83:
        raise ValueError('identity module does not name e2-editor-v29 / generation 83: '
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
    # SPEC-M3-v28-last-line-fallback (7.1-7.3): every recorded result, refused when absent or wrong.
    v28 = ROOT / 'findings/evidence/v28-083'
    needed28 = (['u-v28/red-before.txt', 'u-v28/page-tests-red-before.txt', 'u-v28/shell-tests-after.txt',
                 'u-v28/e1-c-before.txt', 'u-v28/e1-c-after.txt',
                 'pre-link/e1-red-before-inc-edit.txt', 'pre-link/e1-e2-green.txt', 'pre-link/e4-v28.txt',
                 'pre-link/v0-v28.json', 'pre-link/v0-v28-positive-control.json', 'pre-link/s-v28.json',
                 'pre-link/w1-green.txt', 'pre-link/w1-red-extra-line.txt', 'pre-link/w2.txt',
                 'pre-link/test-v28-last-block-static.txt', 'pre-link/m1-1-red-without-v28-carrier.exit.txt',
                 'pre-link/m1-1-green-with-v28-carrier.exit.txt', 'pre-link/l-confined.json', 'pre-link/source-pin.json',
                 'pre-link/v27-archive-sha256sums-check.txt',
                 'pl1/run-01/report.json', 'pl1/run-01-self-test.json',
                 'post-link/link-owner-run.stdout.txt', 'post-link/frozen-set-delta.json',
                 'cutover/e1-c-after-cutover.txt', 's4/run-01/report.json', 's4/self-test-01.json',
                 'freeze-82/e1-c.txt', 'f3-82/equal-01.json', 'f3-82/equal-01-self-test.json', 'f3-82/read-01.json',
                 'f4-82/aggregate-judge.json', 'v0/v0-prime.json', 'v0/e1-c-after-put-back.json']
                + [f'pre-link/e3-{n}.txt' for n in ('make-test-v27-first-block-static', 'test_ordered_format',
                                                     'test_ordered_format_v25', 'test_ordered_format_v27',
                                                     'test_format_readback_v27', 'test_ordered_format_scope')]
                + [f's4/{S4_MUTATION_DIRS.get(m, "mutation-" + m)}/report.json' for m in S4_MUTATIONS])
    missing28 = [n for n in needed28 if not (v28 / n).is_file()]
    if missing28:
        raise ValueError('spec v28 evidence missing: ' + json.dumps(missing28))

    def v28json(name, key='verdict'):
        return json.loads((v28 / name).read_bytes()).get(key)

    def v28last(name):
        return (v28 / name).read_text().rstrip().splitlines()[-1]

    def v28intact(name):
        # check_e1_c_bundle_intact.py's JSON; U-v28's two receipts end in an `exit N` line, which must be `exit 0`.
        lines = (v28 / name).read_text().rstrip().splitlines()
        if lines and lines[-1].startswith('exit '):
            if lines[-1] != 'exit 0':
                return False
            lines = lines[:-1]
        return json.loads('\n'.join(lines)).get('intact')

    def v28count(name, word):
        node_counts28[name + ':' + word] = node_last(v28 / name, word)
        return node_counts28[name + ':' + word]
    node_counts28 = {}
    f4_82 = json.loads((v28 / 'f4-82/aggregate-judge.json').read_bytes())
    shell_after = (v28 / 'u-v28/shell-tests-after.txt').read_text()
    contract = (v28 / 'post-link/link-owner-run.stdout.txt').read_text().splitlines()
    gates28 = {
        'U-v28': ([v28last('u-v28/red-before.txt'), v28last('u-v28/page-tests-red-before.txt')], ['exit 1', 'exit 1']),
        # The one failing test is the named L-select-all-u2-pins-v26-profile (red since the v27 cut-over).
        'shellSuite': ([v28count('u-v28/shell-tests-after.txt', 'fail'), (v28count('u-v28/shell-tests-after.txt', 'pass') or 0) > 0,
                        sum(1 for line in shell_after.splitlines() if line.startswith('✖ U2 wiring')) == 2 and U2_NAMED in shell_after],
                       [1, True, True]),
        'E1-red-first': ('FAIL' in (v28 / 'pre-link/e1-red-before-inc-edit.txt').read_text(), True),
        'E1-E2': (v28last('pre-link/e1-e2-green.txt'), 'exit 0'),
        'E3': ([v28last(f'pre-link/e3-{n}.txt') for n in ('make-test-v27-first-block-static', 'test_ordered_format',
                                                          'test_ordered_format_v25', 'test_ordered_format_v27',
                                                          'test_format_readback_v27', 'test_ordered_format_scope')], ['exit 0'] * 6),
        'E4': (v28last('pre-link/e4-v28.txt'), 'exit 0'),
        'V0-v28': ([v28json('pre-link/v0-v28.json'), v28json('pre-link/v0-v28-positive-control.json')], ['V0_V28_HOLDS', 'V0_V28_DIFFERS']),
        'S': (v28json('pre-link/s-v28.json'), 'S_V28_HOLDS'),
        'W1': ([v28last('pre-link/w1-green.txt'), v28last('pre-link/w1-red-extra-line.txt')], ['exit 0', 'exit 1']),
        'W2': (v28last('pre-link/w2.txt'), 'exit 0'),
        'static': (v28last('pre-link/test-v28-last-block-static.txt'), 'exit 0'),
        'M1-1': ([v28last('pre-link/m1-1-red-without-v28-carrier.exit.txt'), v28last('pre-link/m1-1-green-with-v28-carrier.exit.txt')],
                 ['exit 1', 'exit 0']),
        'L': (v28json('pre-link/l-confined.json'), 'CONFINED_V28_HOLDS'),
        'PIN': ([v28json('pre-link/source-pin.json', 'allAgree'), v28last('pre-link/v27-archive-sha256sums-check.txt')], [True, 'exit 0']),
        'PL-1': ([v28json('pl1/run-01/report.json'), v28json('pl1/run-01-self-test.json', 'selfTest')], ['PL1_V28_HOLDS', 'ALL_AS_EXPECTED']),
        'P-v28': ([sum(1 for line in contract if line.strip() == 'v28 preconditions hold'), v28json('post-link/frozen-set-delta.json', 'holds')],
                  [3, True]),
        'S4': ([v28json('s4/run-01/report.json'), v28json('s4/self-test-01.json', 'selfTest')], ['S4_HOLDS', 'ALL_RED']),
        'S4-mutations': ([v28json(f's4/{S4_MUTATION_DIRS.get(m, "mutation-" + m)}/report.json') for m in S4_MUTATIONS],
                         ['S4_MUTATION_CAUGHT'] * len(S4_MUTATIONS)),
        'F3-82-reading2': ([v28json('f3-82/equal-01.json'), v28json('f3-82/equal-01-self-test.json', 'selfTest')], ['F3_82_EQUAL', 'ALL_RED']),
        # Written out here, not imported from the reader: exactly F3_RED and F3-81's four.
        'F3-82-reading1': ([v28json('f3-82/read-01.json'), v28json('f3-82/read-01.json', 'problems')], ['F3_RED', F3_82_READ01_PROBLEMS]),
        'F4-82': ('PASS' if not f4_82['problems'] and f4_82['rows'] == 24 and all(x['outcome'] == 'PASS' for x in f4_82['arms'].values()) else 'NOT', 'PASS'),
        'V0prime-82': (v28json('v0/v0-prime.json'), 'V0_PRIME_HOLDS'),
        'E1-C': ([v28intact(n) for n in ('u-v28/e1-c-before.txt', 'u-v28/e1-c-after.txt', 'cutover/e1-c-after-cutover.txt',
                                                  'freeze-82/e1-c.txt', 'v0/e1-c-after-put-back.json')], [True] * 5),
    }
    if any(got != want_ for got, want_ in gates28.values()):
        raise ValueError('spec v28 verdicts do not hold: ' + json.dumps({'gates': gates28, 'nodeCounts': node_counts28}))
    # SPEC-M3-v29-tick-pacing (5, 6, appends 2-5) and SPEC-M3-own-stack 6: every recorded result, refused when absent or wrong.
    v29 = ROOT / 'findings/evidence/v29-177'
    own = ROOT / 'findings/evidence/own-stack'
    t2_cases = [(b, d, s) for b in ('chrome', 'firefox') for d in ('boundaries', 'owner') for s in ('opened', 'typed')]
    needed29 = (['pre-link/pacing-mutations.txt', 'pre-link/syntax-v29.exit.txt', 'pre-link/static-reds-after-v29.txt',
                 'cutover/e1-c-after-cutover.txt', 'freeze-83/e1-c.txt',
                 'f3-83/equal-02.stdout.txt', 'f3-83/diag-single-press/equal.json', 'f3-83/diag-single-press/equal-self-test.json',
                 'f4-83/final-page/aggregate-judge.json', 's4/run-01/report.json', 's4/self-test-01.stdout.txt',
                 't3/merge/reading-01.json', 't3/merge/self-test-01.json', 't3/typing-gap/reading-01.json',
                 't3/typing-gap/self-test-01.json', 't4/self-test-01.json', 'v0/v0-prime.json', 'v0/e1-c-after-put-back.json',
                 '../toolbar-icons/check-02/chrome.json', '../toolbar-icons/check-02/firefox.json',
                 '../own-stack/cutover/before.json', '../own-stack/cutover/after.json',
                 '../own-stack/st2/reading.json', '../own-stack/st4/reading.json', '../host-0.2.45/p-contract.txt']
                + [f'pre-link/syntax-control-{n}.exit.txt' for n in ('no-v28-define', 'call', 'switch')]
                + [f't1/judge-{j}-r{r}.txt' for j in ('c2', 'p2') for r in (1, 2, 3)]
                + [f't4/reading-run-0{r}.json' for r in (1, 2, 3)]
                + [f's4/mutation-{m}/report.json' for m in S4_MUTATIONS_V29]
                + [f'post-link/idle-{v}-{b}-{d}-r{r}.json' for v in ('v28', 'v29') for b, d, _ in t2_cases[::2] for r in (1, 2, 3)]
                + [f'post-link/idle-spin-{n}-r1.json' for n in ('chrome-owner', 'firefox-boundaries')])
    missing29 = [n for n in needed29 if not (v29 / n).is_file()]
    if missing29:
        raise ValueError('spec v29 evidence missing: ' + json.dumps(missing29))

    def v29json(name, key='verdict'):
        return json.loads((v29 / name).read_bytes()).get(key)

    def v29last(name):
        return (v29 / name).read_text().rstrip().splitlines()[-1]

    def idle(variant, browser, document, state):
        return statistics.median(json.loads((v29 / f'post-link/idle-{variant}-{browser}-{document}-r{r}.json').read_bytes())[state]['cpuSeconds']
                                 for r in (1, 2, 3))

    def t1_fail_lines(r):
        return [line.split() for line in (v29 / f't1/judge-p2-r{r}.txt').read_text().splitlines() if line.startswith('  FAIL')]
    t2 = {f'{b}/{d}/{s}': {'v28': idle('v28', b, d, s), 'v29': idle('v29', b, d, s)} for b, d, s in t2_cases}
    t2_red = [json.loads((v29 / f'post-link/idle-spin-{b}-{d}-r1.json').read_bytes())[s]['cpuSeconds'] > idle('v28', b, d, s) * 1.5 + 0.5
              for b, d in (('chrome', 'owner'), ('firefox', 'boundaries')) for s in ('opened', 'typed')]
    mutations = (v29 / 'pre-link/pacing-mutations.txt').read_text()
    f3_equal = json.loads((v29 / 'f3-83/diag-single-press/equal.json').read_bytes())
    f4_83 = json.loads((v29 / 'f4-83/final-page/aggregate-judge.json').read_bytes())
    gap = json.loads((v29 / 't3/typing-gap/reading-01.json').read_bytes())
    gates29 = {
        'U': (mutations.count(' exit 1'), 4),
        'S': ([(v29 / f'pre-link/{n}.exit.txt').read_text().strip() for n in ('syntax-v29', 'syntax-control-no-v28-define', 'syntax-control-call', 'syntax-control-switch')],
              ['0', '1', '1', '1']),
        'M': ((v29 / 'pre-link/static-reds-after-v29.txt').read_text() == (ROOT / 'findings/evidence/k-0.2.44/p6-named-reds.txt').read_text(), True),
        'P-contract': ((OUT / 'p-contract.txt').read_text().splitlines()[0], 'v29 preconditions hold'),
        'P-archive': ([sha(SDK / 'dist' / 'profiles' / PROFILE / n) == sha(V29_ARCHIVE / n) for n in PROFILE_FILES], [True] * 4),
        # Spec v29 6: a boundaries commit over the line is not a v29 failure, the gate is the owner's before the next K spec.
        'T1-C2': ([v29last(f't1/judge-c2-r{r}.txt') for r in (1, 2, 3)], [T1_PASS] * 3),
        'T1-P2': ([v29last('t1/judge-p2-r1.txt'), v29last('t1/judge-p2-r2.txt'), v29last('t1/judge-p2-r3.txt')], [T1_PASS, T1_P2_NAMED, T1_P2_NAMED]),
        'T1-P2-one-line': ([[line[1:5] for line in t1_fail_lines(r)] for r in (1, 2, 3)],
                           [[], [T1_P2_WORDS], [T1_P2_WORDS]]),
        'T2': (all(c['v29'] <= c['v28'] * 1.5 + 0.5 for c in t2.values()), True),
        'T2-red': (t2_red, [True] * 4),
        'F3-83-reading2': ([f3_equal['verdict'], v29json('f3-83/diag-single-press/equal-self-test.json', 'selfTest'), f3_equal['reading2']['moved']],
                           ['F3_83_EQUAL', 'ALL_RED', []]),
        'F3-83-reading1': ([f3_equal['reading1']['verdict'], f3_equal['reading1']['problems']], ['F3_RED', F3_83_READ01_PROBLEMS]),
        # Finding 178: the pinned runner on the same bytes, the red case of the single-press reading.
        'F3-83-pinned-runner': (v29json('f3-83/equal-02.stdout.txt'), 'F3_83_MOVED'),
        'F4-83': ('PASS' if not f4_83['problems'] and f4_83['rows'] == 24 and all(x['outcome'] == 'PASS' for x in f4_83['arms'].values()) else 'NOT', 'PASS'),
        'S4': ([v29json('s4/run-01/report.json'), v29json('s4/self-test-01.stdout.txt', 'selfTest')], ['S4_HOLDS', 'ALL_RED']),
        'S4-mutations': ([v29json(f's4/mutation-{m}/report.json') for m in S4_MUTATIONS_V29], ['S4_MUTATION_CAUGHT'] * len(S4_MUTATIONS_V29)),
        'merge': ([v29json('t3/merge/reading-01.json'), v29json('t3/merge/self-test-01.json', 'selfTest')], ['MERGE_T3_HOLDS', 'ALL_RED']),
        'gap-order': ([gap['verdict'], gap['runs'], gap['held'], v29json('t3/typing-gap/self-test-01.json', 'selfTest')], ['GAP_ORDER_HOLDS', 24, 24, 'ALL_RED']),
        'T4': ([v29json(f't4/reading-run-0{r}.json') for r in (1, 2, 3)] + [v29json('t4/self-test-01.json', 'selfTest')], ['T4_HOLDS'] * 3 + ['ALL_RED']),
        'V0prime-83': (v29json('v0/v0-prime.json'), 'V0_PRIME_HOLDS'),
        'E1-C': ([json.loads((v29 / n).read_text().rstrip().removesuffix('exit 0')).get('intact')
                  for n in ('cutover/e1-c-after-cutover.txt', 'freeze-83/e1-c.txt', 'v0/e1-c-after-put-back.json')], [True] * 3),
        'toolbar': ([json.loads((v29 / f'../toolbar-icons/check-02/{b}.json').read_bytes())['holds'] for b in ('chrome', 'firefox')], [True, True]),
        'ST1': (json.loads((own / 'cutover/before.json').read_bytes()) == json.loads((own / 'cutover/after.json').read_bytes()), True),
        'ST2-ST3': (json.loads((own / 'st2/reading.json').read_bytes())['verdict'], 'ST2_ST3_HOLD'),
        'ST4': (json.loads((own / 'st4/reading.json').read_bytes())['verdict'], 'ST4_HOLDS'),
    }
    if any(got != want_ for got, want_ in gates29.values()):
        raise ValueError('spec v29 verdicts do not hold: ' + json.dumps({k: g for k, g in gates29.items() if g[0] != g[1]}))
    old = json.loads((OLD / 'MANIFEST.json').read_bytes())
    # Spec 5.9: no other page of the old package uses the profile whose four files this package removes.
    on_old_profile = sorted(h for h, p in old['source']['pages'].items() if p['profile'] == OLD_PROFILE)
    if on_old_profile != ['e2-editor.html']:
        raise ValueError('pages of the 0.2.44 package on e2-editor-v28 are not exactly the editor: ' + json.dumps(on_old_profile))
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
        raise ValueError('editor is not the verified generation-83 page')
    if files['e2-editor.html']['sha256'] != want['originalHtmlSha256']:
        raise ValueError('editor HTML is not the verified icon page')
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
        raise ValueError('delta against 0.2.44 is not exactly the page and its HTML, the four v29 profile files'
                         ' added and the four v28 profile files removed: '
                         + json.dumps({'changed': changed, 'added': added, 'removed': removed}))
    raw_identity = lambda e: (e['sha256'], e['bytes'])  # noqa: E731
    successor = {n: {'v28': old['files'][f'profiles/{OLD_PROFILE}/{n}']['sha256'], 'v29': files[f'profiles/{PROFILE}/{n}']['sha256']}
                 for n in PROFILE_FILES}
    if any(raw_identity(old['files'][f'profiles/{OLD_PROFILE}/{n}']) != raw_identity(files[f'profiles/{PROFILE}/{n}']) for n in SAME_BYTES):
        raise ValueError('the v29 worker is not the removed v28 bytes (spec v29 2): ' + json.dumps(successor))
    if any(successor[n]['v28'] == successor[n]['v29'] for n in SUCCESSOR_FILES):
        raise ValueError('a v29 profile file equals the removed v28 one (the relink changes three; probe.wasm equal = no new engine): ' + json.dumps(successor))
    archive = SDK / 'build/archive' / ('host-0.2.45-engine-' + manifest['buildId'])
    if archive.exists():
        raise ValueError('archive already exists')
    shutil.copytree(APP / 'engine', archive)
    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.45 engine package\n\n'
        f'Host commit {candidate}, predecessor {PARENT} (0.2.44, exact 0.2.44 engine). Writer on profile e2-editor-v29 (linked 2026-11-01 at the owner request, wasm e61e5890, worker bytes of v28) / frozen shell generation 83 / icon toolbar HTML ca58f40f: finding 177, no main-loop pacing while there is work; viewer v3 and Calc v2 retained. v24 feature counts carried over (spec v25 section 14); v25 F1-F4, the section 9 reader, spec v79, spec v26 ({F3_80_BASIS}), spec v27 ({F3_81_BASIS}), spec v28 ({F3_82_BASIS}) and spec v29 U/S/M/P/T1/T2/F3-83/F4-83/S4/merge/gap-order/T4/V0prime/E1-C/toolbar with ST1-ST4 hold ({F3_83_BASIS}); T1 records Chrome boundaries commit over the v20 gate, the owner decides it before the next K spec; full K has not run. MANIFEST.json binds every raw/gzip/zstd member.\n')
    members = sorted(p for p in archive.rglob('*') if p.is_file())
    (OUT / 'archive.sha256').write_text(''.join(sha(p) + '  ' + p.relative_to(archive).as_posix() + '\n' for p in members))
    release = {'version': '0.2.45', 'hostParent': PARENT, 'hostCommit': candidate, 'branch': 'host-0.2.45',
               'buildId': manifest['buildId'], 'oldBuildId': old['buildId'], 'archive': str(archive),
               'oldArchive': str(OLD), 'manifestSha256': sha(archive / 'MANIFEST.json'),
               'totals': manifest['totals'], 'pages': pages, 'unchangedFiles': len(same),
               'unchanged': sorted(same), 'changed': changed, 'added': added, 'removed': removed,
               'profileSuccessor': successor,
               'archiveFilesVerified': len(members), 'installed': False, 'K': 'NOT_RUN',
               'nominalShippedHost': '0.2.26', 'shellGeneration': 83, 'v25Gates': gates, 'v79Gates': gates79,
               'v26Gates': gates26, 'v26NodeCounts': node_counts, 'v27Gates': gates27, 'v27NodeCounts': node_counts27,
               'v28Gates': gates28, 'v28NodeCounts': node_counts28, 'v29Gates': gates29, 't2Medians': t2,
               'countBasis': 'v24 counts carried over (owner, spec v25 section 14); v25 F1-F4 and section 9 reader; spec v79 U1/U2/B1/F3-79/F4-79/V0prime/E1-C; spec v26 P1/U1-U4/S1/S2 run-02/F3-80/F4-80/V0prime/E1-C; ' + F3_80_BASIS + '; spec v27 PL-1/pre-link/P-v27/S3/S2prime/F3-81/F4-81/V0prime/E1-C; ' + F3_81_BASIS + '; spec v28 U-v28/pre-link/PL-1/P-v28/S4/F3-82/F4-82/V0prime/E1-C; ' + F3_82_BASIS + '; spec v29 U/S/M/P/T1/T2/F3-83/F4-83/S4/merge/gap-order/T4/V0prime/E1-C/toolbar, own-stack ST1-ST4; ' + F3_83_BASIS,
               'f3_80Verdicts': {'read01': verdict('f3/read-01.json'), 'equal01': verdict('f3/equal-01.json'),
                                 'append2': verdict('f3/append2-read-01.json')},
               'f3_81Verdicts': {'read01': v27json('f3-81/read-01.json'), 'equal01': v27json('f3-81/equal-01.json')},
               'f3_82Verdicts': {'read01': v28json('f3-82/read-01.json'), 'equal01': v28json('f3-82/equal-01.json')},
               'f3_83Verdicts': {'singlePress': f3_equal['verdict'], 'pinnedRunner': v29json('f3-83/equal-02.stdout.txt')},
               'shellBundleFileSha256': want['shell']['bundleFileSha256']}
    release['canonicalPackageReusedAfterWrapperError'] = args.reuse_existing
    (OUT / 'release.json').write_text(json.dumps(release, indent=1) + '\n')
    print(json.dumps(release, indent=1), flush=True)


if __name__ == '__main__':
    main()
