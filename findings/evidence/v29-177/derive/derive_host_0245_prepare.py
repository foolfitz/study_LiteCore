#!/usr/bin/env python3
"""Derive findings/evidence/host-0.2.45/prepare-release.py from host-0.2.44's (SPEC-M3-v29-tick-pacing append 6).
Each replacement must match its stated count; the 0.2.44 file is not edited.
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[2]
SRC, DST = EV / 'host-0.2.44/prepare-release.py', EV / 'host-0.2.45/prepare-release.py'

DOC_OLD_START = '"""Package an isolated 0.2.44 host'
DOC_NEW = '''"""Package an isolated 0.2.45 host (Writer on profile e2-editor-v29, shell generation 83, the icon toolbar HTML) from current verified dist, preserving the live predecessor.

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

'''

GATE = r"""    # SPEC-M3-v29-tick-pacing (5, 6, appends 2-5) and SPEC-M3-own-stack 6: every recorded result, refused when absent or wrong.
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
"""

REPS = [
 ("import shutil\n", "import shutil\nimport statistics\n", 1),
 ("APP = SDK / 'build/host-0.2.44/litecore'", "APP = SDK / 'build/host-0.2.45/litecore'", 1),
 ("PARENT = 'ae8240d372525497c1a1067ce10f4286758fc5d1'", "PARENT = 'a97724f302ddc7eb7180a4d3fd6d4863bfd6952d'", 1),
 ("OLD = SDK / 'build/archive/host-0.2.43-engine-741afd80a36e673b'", "OLD = SDK / 'build/archive/host-0.2.44-engine-dacdfa20fd4ff1ea'", 1),
 ("PROFILE = 'e2-editor-v28'\nOLD_PROFILE = 'e2-editor-v27'", "PROFILE = 'e2-editor-v29'\nOLD_PROFILE = 'e2-editor-v28'", 1),
 ("SAME_BYTES = ()\nSUCCESSOR_FILES = PROFILE_FILES",
  "SAME_BYTES = ('sdk-worker.js',)\nSUCCESSOR_FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json')", 1),
 ("DECLARED_CHANGED = ['e2-editor-app.js', 'editor-shell-v2/paragraph-editor-client.js']",
  "DECLARED_CHANGED = ['e2-editor-app.js', 'e2-editor.html']", 1),
 ("S4_MUTATION_DIRS = {'press-list-none': 'mutation-press-list-none-run-02'}\n",
  "S4_MUTATION_DIRS = {'press-list-none': 'mutation-press-list-none-run-02'}\n"
  "# SPEC-M3-v29-tick-pacing append 2: reading 1 exactly F3-82's; no declared move.\n"
  "F3_83_READ01_PROBLEMS = F3_82_READ01_PROBLEMS\n"
  "F3_83_BASIS = 'F3-83 single-press (finding 178): every cell equal to F3-82, no declared move'\n"
  "S4_MUTATIONS_V29 = S4_MUTATIONS  # on v29 press-list-none's first report counts (s4/README.md)\n"
  "V29_ARCHIVE = SDK / 'build/archive/e2-editor-v29-e61e5890-worker-a5df83db'\n"
  "T1_PASS = 'PASS: both browsers, every cell'\n"
  "T1_P2_NAMED = 'FAIL: chrome boundaries-gap200 commit median'\n"
  "T1_P2_WORDS = ['chrome', 'boundaries-gap200', 'commit', 'median:']\n", 1),
 ("from v82_four_arms_identity import identity", "from v83_four_arms_identity import identity", 1),
 ("raise ValueError('live predecessor differs from clean ae8240d (0.2.43)')", "raise ValueError('live predecessor differs from clean a97724f (0.2.44)')", 1),
 ("'<version>0.2.44</version>'", "'<version>0.2.45</version>'", 1),
 ("""    if want['profile'] != PROFILE or want['shell'].get('generation') != 82:
        raise ValueError('identity module does not name e2-editor-v28 / generation 82: '""",
  """    if want['profile'] != PROFILE or want['shell'].get('generation') != 83:
        raise ValueError('identity module does not name e2-editor-v29 / generation 83: '""", 1),
 ("""        raise ValueError('spec v28 verdicts do not hold: ' + json.dumps({'gates': gates28, 'nodeCounts': node_counts28}))
""", """        raise ValueError('spec v28 verdicts do not hold: ' + json.dumps({'gates': gates28, 'nodeCounts': node_counts28}))
""" + GATE, 1),
 ("raise ValueError('pages of the 0.2.43 package on e2-editor-v27 are not exactly the editor: '",
  "raise ValueError('pages of the 0.2.44 package on e2-editor-v28 are not exactly the editor: '", 1),
 ("""        raise ValueError('editor is not the verified generation-82 page')
""", """        raise ValueError('editor is not the verified generation-83 page')
    if files['e2-editor.html']['sha256'] != want['originalHtmlSha256']:
        raise ValueError('editor HTML is not the verified icon page')
""", 1),
 ("""        raise ValueError('delta against 0.2.43 is not exactly the page and the client, the four v28 profile files'
                         ' added and the four v27 profile files removed: '""",
  """        raise ValueError('delta against 0.2.44 is not exactly the page and its HTML, the four v29 profile files'
                         ' added and the four v28 profile files removed: '""", 1),
 ("successor = {n: {'v27': old['files'][f'profiles/{OLD_PROFILE}/{n}']['sha256'], 'v28': files[f'profiles/{PROFILE}/{n}']['sha256']}",
  "successor = {n: {'v28': old['files'][f'profiles/{OLD_PROFILE}/{n}']['sha256'], 'v29': files[f'profiles/{PROFILE}/{n}']['sha256']}", 1),
 ("raise ValueError('unreachable: SAME_BYTES is empty for v28 (a relink)')", "raise ValueError('the v29 worker is not the removed v28 bytes (spec v29 2): ' + json.dumps(successor))", 1),
 ("""    if any(successor[n]['v27'] == successor[n]['v28'] for n in SUCCESSOR_FILES):
        raise ValueError('a v28 profile file equals the removed v27 one (a relink changes all four; probe.wasm equal = no new engine): ' + json.dumps(successor))""",
  """    if any(successor[n]['v28'] == successor[n]['v29'] for n in SUCCESSOR_FILES):
        raise ValueError('a v29 profile file equals the removed v28 one (the relink changes three; probe.wasm equal = no new engine): ' + json.dumps(successor))""", 1),
 ("archive = SDK / 'build/archive' / ('host-0.2.44-engine-' + manifest['buildId'])", "archive = SDK / 'build/archive' / ('host-0.2.45-engine-' + manifest['buildId'])", 1),
 ("""    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.44 engine package\\n\\n'
        f'Host commit {candidate}, predecessor {PARENT} (0.2.43, exact 0.2.43 engine). Writer on profile e2-editor-v28 (linked 2026-10-30 at the owner request, wasm 13f674e4) / frozen shell generation 82: the 083 path on a multi-paragraph last line (after a NONE SelectText read the engine selects one position back and judges the readback last block; a refused fallback gets its own sentence); viewer v3, Calc v2 and 0.2.38 dark-theme HTML retained. v24 feature counts carried over (spec v25 section 14); v25 F1-F4, the section 9 reader, spec v79, spec v26 ({F3_80_BASIS}), spec v27 ({F3_81_BASIS}) and spec v28 U-v28/pre-link/PL-1/P-v28/S4/F3-82/F4-82/V0prime/E1-C hold ({F3_82_BASIS}); full K has not run. MANIFEST.json binds every raw/gzip/zstd member.\\n')""",
  """    (archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.45 engine package\\n\\n'
        f'Host commit {candidate}, predecessor {PARENT} (0.2.44, exact 0.2.44 engine). Writer on profile e2-editor-v29 (linked 2026-11-01 at the owner request, wasm e61e5890, worker bytes of v28) / frozen shell generation 83 / icon toolbar HTML ca58f40f: finding 177, no main-loop pacing while there is work; viewer v3 and Calc v2 retained. v24 feature counts carried over (spec v25 section 14); v25 F1-F4, the section 9 reader, spec v79, spec v26 ({F3_80_BASIS}), spec v27 ({F3_81_BASIS}), spec v28 ({F3_82_BASIS}) and spec v29 U/S/M/P/T1/T2/F3-83/F4-83/S4/merge/gap-order/T4/V0prime/E1-C/toolbar with ST1-ST4 hold ({F3_83_BASIS}); T1 records Chrome boundaries commit over the v20 gate, the owner decides it before the next K spec; full K has not run. MANIFEST.json binds every raw/gzip/zstd member.\\n')""", 1),
 ("release = {'version': '0.2.44', 'hostParent': PARENT, 'hostCommit': candidate, 'branch': 'host-0.2.44',",
  "release = {'version': '0.2.45', 'hostParent': PARENT, 'hostCommit': candidate, 'branch': 'host-0.2.45',", 1),
 ("'nominalShippedHost': '0.2.26', 'shellGeneration': 82, 'v25Gates': gates, 'v79Gates': gates79,",
  "'nominalShippedHost': '0.2.26', 'shellGeneration': 83, 'v25Gates': gates, 'v79Gates': gates79,", 1),
 ("'v28Gates': gates28, 'v28NodeCounts': node_counts28,",
  "'v28Gates': gates28, 'v28NodeCounts': node_counts28, 'v29Gates': gates29, 't2Medians': t2,", 1),
 ("spec v28 U-v28/pre-link/PL-1/P-v28/S4/F3-82/F4-82/V0prime/E1-C; ' + F3_82_BASIS,",
  "spec v28 U-v28/pre-link/PL-1/P-v28/S4/F3-82/F4-82/V0prime/E1-C; ' + F3_82_BASIS + '; spec v29 U/S/M/P/T1/T2/F3-83/F4-83/S4/merge/gap-order/T4/V0prime/E1-C/toolbar, own-stack ST1-ST4; ' + F3_83_BASIS,", 1),
 ("""               'f3_82Verdicts': {'read01': v28json('f3-82/read-01.json'), 'equal01': v28json('f3-82/equal-01.json')},""",
  """               'f3_82Verdicts': {'read01': v28json('f3-82/read-01.json'), 'equal01': v28json('f3-82/equal-01.json')},
               'f3_83Verdicts': {'singlePress': f3_equal['verdict'], 'pinnedRunner': v29json('f3-83/equal-02.stdout.txt')},""", 1),
]

text = SRC.read_text(encoding='utf-8')
for old, new, count in REPS:
    got = text.count(old)
    if got != count:
        raise SystemExit(f'{old[:90]!r} occurs {got} times, expected {count}')
    text = text.replace(old, new)
start = text.index(DOC_OLD_START)
text = text[:start] + DOC_NEW + text[start + 3:]
compile(text, str(DST), 'exec')
DST.write_text(text, encoding='utf-8')
print('prepare-release.py written')
