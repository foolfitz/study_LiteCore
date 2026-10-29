#!/usr/bin/env python3
"""Package an isolated 0.2.42 host (Writer on profile e2-editor-v26, shell generation 80) from current verified dist, preserving the live predecessor.

Derived from findings/evidence/host-0.2.41/prepare-release.py (not edited).  Closed list of differences:
- the live predecessor is host 2bb5718 (0.2.41) with the exact 0.2.41 engine, so OLD is the 0.2.41 archive
  (host-0.2.41-engine-829a988e199ebc43) and PARENT is 2bb5718; the isolated candidate is build/host-0.2.42
  and its info.xml must say 0.2.42;
- the editor page is generation 80's (tools/v80_four_arms_identity.py); the identity it returns must name
  profile e2-editor-v26 and shell generation 80; the packaged editor page must name profile e2-editor-v26
  and its artifacts are looked up under profiles/e2-editor-v26/;
- before packaging, the old (0.2.41) package's page table is read: exactly one page (e2-editor.html) names
  profile e2-editor-v25, so removing that profile's four files takes it from no other page (spec 5.9);
- the evidence gate keeps 0.2.41's unchanged (carried-over v24 counts; v25 F1-F4 and the section 9 reader;
  spec v79's U1/U2/shell tests/B1/F3-79 both readings/F4-79/V0'/E1-C) and adds SPEC-M3-select-all-v26's,
  all under findings/evidence/select-all-v26/: P1 (dist profile P1_HOLDS, red cases RED_CASES_HOLD); U1-U4
  (red-before's last `ℹ fail K` line has K > 0, green-after's has K = 0 and its last `ℹ pass N` has N > 0);
  the whole shell suite after finding 175 (`suite-after-175.txt`, same green reading); S2 run-02 S2_HOLDS
  (run-01 does not count, spec append 1); S1 run-01 S1_HOLDS with self-test ALL_RED; F3-80 under spec v26
  append 2 (see the next item); F4-80 24/24 (the same expression as F4-79's); V0' V0_PRIME_HOLDS;
  E1-C intact after the V0' put-back.  Every v26 evidence file is checked for existence first and the
  missing ones are named in the refusal;
- F3-80 (spec v26 append 2, fable ruling B modified, findings/evidence/select-all-v26/f3/RULING-fable-2026-10-30.md;
  edited by the main session after the scripts were derived and before any run): the two original readings are
  required to be exactly the recorded move -- read-01 (F3_RED, exactly the three Chrome problems) and equal-01
  (F3_80_MOVED, exactly the three moved records, chrome 46/43 and firefox 46/46 equal) -- and the append-2
  reader (tools/read_v80_f3_append2.py) must say F3_80_HOLDS_UNDER_APPEND_2 with its self-test ALL_RED; both
  of its files are in the existence check.  Any other F3-80 result is a refusal.  countBasis and ATTRIBUTION
  say "F3-80 under spec v26 append 2: three Chrome cells count-only (L-175-blinds-three-F3-cells)"; the release
  record carries the three verdict strings (f3_80Verdicts);
- the delta against 0.2.41 must be exactly: three changed records (e2-editor-app.js and the two
  editor-shell-v2 narrow-editor-v2 files), the four profiles/e2-editor-v26/ files added, the four
  profiles/e2-editor-v25/ files removed; the added probe.wasm and probe.js equal the removed ones (sha256
  and byte count) and the added sdk-manifest.json and sdk-worker.js differ from the removed ones (spec 5.9);
- names (0.2.42, archive host-0.2.42-engine-<buildId>, attribution, release fields: shellGeneration 80,
  v26Gates, v26NodeCounts (the fail/pass counts the U1-U4 and suite gates read), profileSuccessor (v25 and
  v26 sha256 of the four profile files), countBasis).
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
APP = SDK / 'build/host-0.2.42/litecore'
HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
PARENT = '2bb5718b05442a9c4fa4b3a0e8240aea4f9f4941'
OLD = SDK / 'build/archive/host-0.2.41-engine-829a988e199ebc43'
PROFILE = 'e2-editor-v26'
OLD_PROFILE = 'e2-editor-v25'
PROFILE_FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
SAME_BYTES = ('probe.js', 'probe.wasm')
SUCCESSOR_FILES = ('sdk-manifest.json', 'sdk-worker.js')
DECLARED_CHANGED = ['e2-editor-app.js', 'editor-shell-v2/narrow-editor-v2-client.js',
                    'editor-shell-v2/narrow-editor-v2-session.js']
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
sys.path.insert(0, str(SDK / 'tools'))
from package_m3_engine import package, validate_manifest
from probe_m3_assets import closure
from v80_four_arms_identity import identity
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
        raise ValueError('live predecessor differs from clean 2bb5718 (0.2.41)')
    if '<version>0.2.42</version>' not in (APP / 'appinfo/info.xml').read_text():
        raise ValueError('isolated version differs')
    candidate = git(APP, 'rev-parse', 'HEAD')
    if git(APP, 'diff', '--name-only', PARENT, candidate).splitlines() != ['appinfo/info.xml']:
        raise ValueError('candidate host source delta is not only its version')
    want = identity()
    if want['profile'] != PROFILE or want['shell'].get('generation') != 80:
        raise ValueError('identity module does not name e2-editor-v26 / generation 80: '
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
    old = json.loads((OLD / 'MANIFEST.json').read_bytes())
    # Spec 5.9: no other page of the old package uses the profile whose four files this package removes.
    on_old_profile = sorted(h for h, p in old['source']['pages'].items() if p['profile'] == OLD_PROFILE)
    if on_old_profile != ['e2-editor.html']:
        raise ValueError('pages of the 0.2.41 package on e2-editor-v25 are not exactly the editor: ' + json.dumps(on_old_profile))
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
        raise ValueError('editor is not the verified generation-80 page')
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
        raise ValueError('delta against 0.2.41 is not exactly the three declared shell files, the four v26 profile files'
                         ' added and the four v25 profile files removed: '
                         + json.dumps({'changed': changed, 'added': added, 'removed': removed}))
    raw_identity = lambda e: (e['sha256'], e['bytes'])  # noqa: E731
    successor = {n: {'v25': old['files'][f'profiles/{OLD_PROFILE}/{n}']['sha256'], 'v26': files[f'profiles/{PROFILE}/{n}']['sha256']}
                 for n in PROFILE_FILES}
    if any(raw_identity(old['files'][f'profiles/{OLD_PROFILE}/{n}']) != raw_identity(files[f'profiles/{PROFILE}/{n}']) for n in SAME_BYTES):
        raise ValueError('v26 probe.wasm/probe.js are not the removed v25 bytes: ' + json.dumps(successor))
    if any(successor[n]['v25'] == successor[n]['v26'] for n in SUCCESSOR_FILES):
        raise ValueError('v26 sdk-manifest.json/sdk-worker.js do not differ from v25: ' + json.dumps(successor))
    archive = SDK / 'build/archive' / ('host-0.2.42-engine-' + manifest['buildId'])
    if archive.exists():
        raise ValueError('archive already exists')
    shutil.copytree(APP / 'engine', archive)
    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.42 engine package\n\n'
        f'Host commit {candidate}, predecessor {PARENT} (0.2.41, exact 0.2.41 engine). Writer on profile e2-editor-v26 (manifest successor of v25; wasm and loader are v25\'s bytes) / frozen shell generation 80: Ctrl+A select-all, findings 174 and 175; viewer v3, Calc v2 and 0.2.38 dark-theme HTML retained. v24 feature counts carried over (spec v25 section 14); v25 F1-F4, the section 9 reader, spec v79 U1/U2/B1/F3-79/F4-79/V0prime/E1-C and spec v26 P1/U1-U4/S1/S2/F3-80/F4-80/V0prime/E1-C hold ({F3_80_BASIS}); full K has not run. MANIFEST.json binds every raw/gzip/zstd member.\n')
    members = sorted(p for p in archive.rglob('*') if p.is_file())
    (OUT / 'archive.sha256').write_text(''.join(sha(p) + '  ' + p.relative_to(archive).as_posix() + '\n' for p in members))
    release = {'version': '0.2.42', 'hostParent': PARENT, 'hostCommit': candidate, 'branch': 'host-0.2.42',
               'buildId': manifest['buildId'], 'oldBuildId': old['buildId'], 'archive': str(archive),
               'oldArchive': str(OLD), 'manifestSha256': sha(archive / 'MANIFEST.json'),
               'totals': manifest['totals'], 'pages': pages, 'unchangedFiles': len(same),
               'unchanged': sorted(same), 'changed': changed, 'added': added, 'removed': removed,
               'profileSuccessor': successor,
               'archiveFilesVerified': len(members), 'installed': False, 'K': 'NOT_RUN',
               'nominalShippedHost': '0.2.26', 'shellGeneration': 80, 'v25Gates': gates, 'v79Gates': gates79,
               'v26Gates': gates26, 'v26NodeCounts': node_counts,
               'countBasis': 'v24 counts carried over (owner, spec v25 section 14); v25 F1-F4 and section 9 reader; spec v79 U1/U2/B1/F3-79/F4-79/V0prime/E1-C; spec v26 P1/U1-U4/S1/S2 run-02/F3-80/F4-80/V0prime/E1-C; ' + F3_80_BASIS,
               'f3_80Verdicts': {'read01': verdict('f3/read-01.json'), 'equal01': verdict('f3/equal-01.json'),
                                 'append2': verdict('f3/append2-read-01.json')},
               'shellBundleFileSha256': want['shell']['bundleFileSha256']}
    release['canonicalPackageReusedAfterWrapperError'] = args.reuse_existing
    (OUT / 'release.json').write_text(json.dumps(release, indent=1) + '\n')
    print(json.dumps(release, indent=1), flush=True)


if __name__ == '__main__':
    main()
