#!/usr/bin/env python3
"""Derive findings/evidence/host-0.2.44/prepare-release.py from host-0.2.43's (SPEC-M3-v28-last-line-fallback 7.4).
Each replacement must match its stated count; the 0.2.43 file is not edited.
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[2]
SRC, DST = EV / 'host-0.2.43/prepare-release.py', EV / 'host-0.2.44/prepare-release.py'

DOC_OLD_START = '"""Package an isolated 0.2.43 host'
DOC_NEW = '''"""Package an isolated 0.2.44 host (Writer on profile e2-editor-v28, shell generation 82) from current verified dist, preserving the live predecessor.

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

'''

REPS = [
 ("APP = SDK / 'build/host-0.2.43/litecore'", "APP = SDK / 'build/host-0.2.44/litecore'", 1),
 ("PARENT = '93b1ebc4018335785974b9ef450323696c53dfbb'", "PARENT = 'ae8240d372525497c1a1067ce10f4286758fc5d1'", 1),
 ("OLD = SDK / 'build/archive/host-0.2.42-engine-01e6c3fb62626d16'", "OLD = SDK / 'build/archive/host-0.2.43-engine-741afd80a36e673b'", 1),
 ("PROFILE = 'e2-editor-v27'\nOLD_PROFILE = 'e2-editor-v26'", "PROFILE = 'e2-editor-v28'\nOLD_PROFILE = 'e2-editor-v27'", 1),
 ("DECLARED_CHANGED = ['e2-editor-app.js']", "DECLARED_CHANGED = ['e2-editor-app.js', 'editor-shell-v2/paragraph-editor-client.js']", 1),
 ("F3_81_BASIS = ('F3-81: the bulleting cell and recoveryPairing retired by design (spec v27 8), S3 is its successor')",
  "F3_81_BASIS = ('F3-81: the bulleting cell and recoveryPairing retired by design (spec v27 8), S3 is its successor')\n"
  "# SPEC-M3-v28-last-line-fallback 7.3 F3-82: reading 1 exactly F3-81's (no declared move, spec v28 8 item 1).\n"
  "F3_82_READ01_PROBLEMS = F3_81_READ01_PROBLEMS\n"
  "F3_82_BASIS = 'F3-82: every cell equal to F3-81 (no declared move, spec v28 8); S4 measures the last line'\n"
  "U2_NAMED = 'U2 wiring: the handler takes Ctrl+A before `if (accel) return;`, with a label, on profile v26'\n"
  "S4_MUTATIONS = ('press-list-none', 'cosmetic-review', 'wrong-button-b-number', 'wrong-button-b-none',\n"
  "                'wrong-button-b-heading', 'wrong-button-b-body')\n"
  "# press-list-none's first report has one NE run (page not ready) and does not count; its re-run does (s4/README.md).\n"
  "S4_MUTATION_DIRS = {'press-list-none': 'mutation-press-list-none-run-02'}", 1),
 ("from v81_four_arms_identity import identity", "from v82_four_arms_identity import identity", 1),
 ("raise ValueError('live predecessor differs from clean 93b1ebc (0.2.42)')", "raise ValueError('live predecessor differs from clean ae8240d (0.2.43)')", 1),
 ("'<version>0.2.43</version>'", "'<version>0.2.44</version>'", 1),
 ("""    if want['profile'] != PROFILE or want['shell'].get('generation') != 81:
        raise ValueError('identity module does not name e2-editor-v27 / generation 81: '""",
  """    if want['profile'] != PROFILE or want['shell'].get('generation') != 82:
        raise ValueError('identity module does not name e2-editor-v28 / generation 82: '""", 1),
 ("""        raise ValueError('spec v27 verdicts do not hold: ' + json.dumps({'gates': gates27, 'nodeCounts': node_counts27}))
""", """        raise ValueError('spec v27 verdicts do not hold: ' + json.dumps({'gates': gates27, 'nodeCounts': node_counts27}))
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
""", 1),
 ("raise ValueError('pages of the 0.2.42 package on e2-editor-v26 are not exactly the editor: '",
  "raise ValueError('pages of the 0.2.43 package on e2-editor-v27 are not exactly the editor: '", 1),
 ("raise ValueError('editor is not the verified generation-81 page')", "raise ValueError('editor is not the verified generation-82 page')", 1),
 ("""        raise ValueError('delta against 0.2.42 is not exactly the page, the four v27 profile files'
                         ' added and the four v26 profile files removed: '""",
  """        raise ValueError('delta against 0.2.43 is not exactly the page and the client, the four v28 profile files'
                         ' added and the four v27 profile files removed: '""", 1),
 ("successor = {n: {'v26': old['files'][f'profiles/{OLD_PROFILE}/{n}']['sha256'], 'v27': files[f'profiles/{PROFILE}/{n}']['sha256']}",
  "successor = {n: {'v27': old['files'][f'profiles/{OLD_PROFILE}/{n}']['sha256'], 'v28': files[f'profiles/{PROFILE}/{n}']['sha256']}", 1),
 ("raise ValueError('unreachable: SAME_BYTES is empty for v27 (a relink)')", "raise ValueError('unreachable: SAME_BYTES is empty for v28 (a relink)')", 1),
 ("""    if any(successor[n]['v26'] == successor[n]['v27'] for n in SUCCESSOR_FILES):
        raise ValueError('a v27 profile file equals the removed v26 one (a relink changes all four; probe.wasm equal = no new engine): ' + json.dumps(successor))""",
  """    if any(successor[n]['v27'] == successor[n]['v28'] for n in SUCCESSOR_FILES):
        raise ValueError('a v28 profile file equals the removed v27 one (a relink changes all four; probe.wasm equal = no new engine): ' + json.dumps(successor))""", 1),
 ("archive = SDK / 'build/archive' / ('host-0.2.43-engine-' + manifest['buildId'])", "archive = SDK / 'build/archive' / ('host-0.2.44-engine-' + manifest['buildId'])", 1),
 ("""    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.43 engine package\\n\\n'
        f'Host commit {candidate}, predecessor {PARENT} (0.2.42, exact 0.2.42 engine). Writer on profile e2-editor-v27 (owner-linked 2026-10-30, wasm c089dfd6) / frozen shell generation 81: finding 176 (the collapsed route judges a two-paragraph readback by its first block; the status strip says 待確認 on review); viewer v3, Calc v2 and 0.2.38 dark-theme HTML retained. v24 feature counts carried over (spec v25 section 14); v25 F1-F4, the section 9 reader, spec v79, spec v26 ({F3_80_BASIS}) and spec v27 PL-1/pre-link/P-v27/S3/S2prime/F3-81/F4-81/V0prime/E1-C hold ({F3_81_BASIS}); full K has not run. MANIFEST.json binds every raw/gzip/zstd member.\\n')""",
  """    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.44 engine package\\n\\n'
        f'Host commit {candidate}, predecessor {PARENT} (0.2.43, exact 0.2.43 engine). Writer on profile e2-editor-v28 (linked 2026-10-30 at the owner request, wasm 13f674e4) / frozen shell generation 82: the 083 path on a multi-paragraph last line (after a NONE SelectText read the engine selects one position back and judges the readback last block; a refused fallback gets its own sentence); viewer v3, Calc v2 and 0.2.38 dark-theme HTML retained. v24 feature counts carried over (spec v25 section 14); v25 F1-F4, the section 9 reader, spec v79, spec v26 ({F3_80_BASIS}), spec v27 ({F3_81_BASIS}) and spec v28 U-v28/pre-link/PL-1/P-v28/S4/F3-82/F4-82/V0prime/E1-C hold ({F3_82_BASIS}); full K has not run. MANIFEST.json binds every raw/gzip/zstd member.\\n')""", 1),
 ("release = {'version': '0.2.43', 'hostParent': PARENT, 'hostCommit': candidate, 'branch': 'host-0.2.43',",
  "release = {'version': '0.2.44', 'hostParent': PARENT, 'hostCommit': candidate, 'branch': 'host-0.2.44',", 1),
 ("'nominalShippedHost': '0.2.26', 'shellGeneration': 81, 'v25Gates': gates, 'v79Gates': gates79,",
  "'nominalShippedHost': '0.2.26', 'shellGeneration': 82, 'v25Gates': gates, 'v79Gates': gates79,", 1),
 ("'v26Gates': gates26, 'v26NodeCounts': node_counts, 'v27Gates': gates27, 'v27NodeCounts': node_counts27,",
  "'v26Gates': gates26, 'v26NodeCounts': node_counts, 'v27Gates': gates27, 'v27NodeCounts': node_counts27,\n"
  "               'v28Gates': gates28, 'v28NodeCounts': node_counts28,", 1),
 ("spec v27 PL-1/pre-link/P-v27/S3/S2prime/F3-81/F4-81/V0prime/E1-C; ' + F3_81_BASIS,",
  "spec v27 PL-1/pre-link/P-v27/S3/S2prime/F3-81/F4-81/V0prime/E1-C; ' + F3_81_BASIS + '; spec v28 U-v28/pre-link/PL-1/P-v28/S4/F3-82/F4-82/V0prime/E1-C; ' + F3_82_BASIS,", 1),
 ("""               'f3_81Verdicts': {'read01': v27json('f3-81/read-01.json'), 'equal01': v27json('f3-81/equal-01.json')},""",
  """               'f3_81Verdicts': {'read01': v27json('f3-81/read-01.json'), 'equal01': v27json('f3-81/equal-01.json')},
               'f3_82Verdicts': {'read01': v28json('f3-82/read-01.json'), 'equal01': v28json('f3-82/equal-01.json')},""", 1),
]

text = SRC.read_text(encoding='utf-8')
for old, new, count in REPS:
    got = text.count(old)
    if got != count:
        raise SystemExit(f'{old[:90]!r} occurs {got} times, expected {count}')
    text = text.replace(old, new)
start = text.index(DOC_OLD_START)
text = text[:start] + DOC_NEW + text[start + 3:]
DST.write_text(text, encoding='utf-8')
print('prepare-release.py written')
