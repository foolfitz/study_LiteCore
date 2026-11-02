#!/usr/bin/env python3
"""Derive host-0.2.51's scripts from host-0.2.50's (SPEC-P-demo-batch-3 section 3): each replacement must match its stated count; the
0.2.50 files are not edited.  0.2.51 moves Writer from e2-editor-v30 to e2-editor-v31 and Calc from ods-editor-v2 to ods-editor-v3,
both real links, so every profile file is new except the two Calc packs, which keep their bytes under the new path.
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[1]
OLD, NEW = EV / 'host-0.2.50', EV / 'host-0.2.51'
A49, A50 = 'host-0.2.49-engine-dd6159b571d9b966', 'host-0.2.50-engine-7e3edb640c50d628'
DECLARED = ['e2-editor-app.js', 'e2-editor.html', 'editor-shell-v2/narrow-editor-v2-client.js', 'editor-shell-v2/narrow-editor-v2-session.js',
            'editor-shell-v2/paragraph-editor-client.js', 'ods-editor-app.js', 'ods-editor.html', 'spreadsheet-shell/calc-document-sdk.js',
            'spreadsheet-shell/calc-editor-session.js']
CONSTANTS = f"""DECLARED = {DECLARED!r}
OLD_PROFILE, PROFILE = 'e2-editor-v30', 'e2-editor-v31'
OLD_CALC, CALC = 'ods-editor-v2', 'ods-editor-v3'
FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
PACKS = ('base-viewer-v3-no35.21bec6461a48d3ec.data', 'base-viewer-v3-no35.43da6a24481dc483.metadata')
ADDED = sorted([f'profiles/{{PROFILE}}/{{n}}' for n in FILES] + [f'profiles/{{CALC}}/{{n}}' for n in FILES + PACKS])
REMOVED = sorted([f'profiles/{{OLD_PROFILE}}/{{n}}' for n in FILES] + [f'profiles/{{OLD_CALC}}/{{n}}' for n in FILES + PACKS])
"""
PLAN = {
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('only BUILD_ID rebound for candidate 0.2.50.', 'only BUILD_ID rebound for candidate 0.2.51.', 1),
  ('this docstring (0.2.49 -> 0.2.50 in its first line, and', 'this docstring (0.2.50 -> 0.2.51 in its first line, and', 1),
  ('rebinding; the 0.2.50 delta is judged', 'rebinding; the 0.2.51 delta is judged', 1)],
 ('capture-after.py', 'capture-after.py'): [('"""Read the installed 0.2.50 identity', '"""Read the installed 0.2.51 identity', 1)],
 ('install-0.2.50.py', 'install-0.2.51.py'): [
  ('"""Guarded 0.2.50 candidate install;', '"""Guarded 0.2.51 candidate install;', 1),
  ('names: host 7782714 (0.2.49)\nwith the exact 0.2.49 engine archive.', 'names: host 350cc4c (0.2.50)\nwith the exact 0.2.50 engine archive.', 1),
  ("candidate = SDK / 'build/host-0.2.50/litecore'", "candidate = SDK / 'build/host-0.2.51/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('# Functional engine rollback to exact 0.2.49 bytes, preserving host label 0.2.50', '# Functional engine rollback to exact 0.2.50 bytes, preserving host label 0.2.51', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.50', 'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.51', 1),
  ("spec_from_file_location('host050_install',out/'install-0.2.50.py')", "spec_from_file_location('host051_install',out/'install-0.2.51.py')", 1),
  (f"{A49}')", f"{A50}')", 1),
  ('Exact 0.2.49 engine restored; host label stays 0.2.50;', 'Exact 0.2.50 engine restored; host label stays 0.2.51;', 1)],
 ('check-delta.py', 'check-delta.py'): [
  ('"""SPEC-P-demo-batch-3 section 2: the 0.2.50 package differs from 0.2.49 in exactly `e2-editor-app.js`, and e2-editor-v29\'s files\nmove to e2-editor-v30 with the wasm and the loader byte for byte and the worker and manifest new -- read from the two archived\nMANIFEST.json files, not from prepare-release.py\'s own say-so.\n\nDerived from findings/evidence/host-0.2.49/check-delta.py (not edited).  Closed list of differences: this docstring; the declared\ndelta; the profile clauses of findings/evidence/host-0.2.45/check-delta.py; the red cases that follow from them.\n"""',
   '"""SPEC-P-demo-batch-3 section 3: the 0.2.51 package differs from 0.2.50 in exactly the nine page and shell files of the batch; Writer\nmoves to e2-editor-v31 and Calc to ods-editor-v3, every profile file new (both are real links), the two Calc packs the same bytes\nunder the new path -- read from the two archived MANIFEST.json files, not from prepare-release.py\'s own say-so.\n\nDerived from findings/evidence/host-0.2.50/check-delta.py (not edited).  Closed list of differences: this docstring; the declared\ndelta; two profiles move and no wasm stays; the red cases that follow.\n"""', 1),
  ("DECLARED = ['e2-editor-app.js']\nOLD_PROFILE, PROFILE = 'e2-editor-v29', 'e2-editor-v30'\nFILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')\nSAME_BYTES = ('probe.js', 'probe.wasm')\nNEW_BYTES = ('sdk-manifest.json', 'sdk-worker.js')\nADDED = sorted(f'profiles/{PROFILE}/{n}' for n in FILES)\nREMOVED = sorted(f'profiles/{OLD_PROFILE}/{n}' for n in FILES)\n", CONSTANTS, 1),
  ("""    for n in SAME_BYTES:
        was, now = of.get(f'profiles/{OLD_PROFILE}/{n}', {}), nf.get(f'profiles/{PROFILE}/{n}', {})
        if not was.get('sha256') or (was.get('sha256'), was.get('bytes')) != (now.get('sha256'), now.get('bytes')):
            problems.append(f'v30 {n} is not the removed v29 bytes')
    for n in NEW_BYTES:
        was, now = of.get(f'profiles/{OLD_PROFILE}/{n}', {}), nf.get(f'profiles/{PROFILE}/{n}', {})
        if not now.get('sha256') or was.get('sha256') == now.get('sha256'):
            problems.append(f'v30 {n} does not differ from v29')
    for page, record in old['source']['pages'].items():
        now = new['source']['pages'].get(page, {})
        want = PROFILE if record['profile'] == OLD_PROFILE else record['profile']
        if (want, record.get('wasmSha256')) != (now.get('profile'), now.get('wasmSha256')):
            problems.append(f'{page} changed profile or wasm')
""", """    for n in PACKS:
        was, now = of.get(f'profiles/{OLD_CALC}/{n}', {}), nf.get(f'profiles/{CALC}/{n}', {})
        if not was.get('sha256') or (was.get('sha256'), was.get('bytes')) != (now.get('sha256'), now.get('bytes')):
            problems.append(f'{n} is not the removed bytes')
    for gone, profile in ((OLD_PROFILE, PROFILE), (OLD_CALC, CALC)):
        for n in FILES:
            was, now = of.get(f'profiles/{gone}/{n}', {}), nf.get(f'profiles/{profile}/{n}', {})
            if not now.get('sha256') or was.get('sha256') == now.get('sha256'):
                problems.append(f'{profile} {n} does not differ from {gone}')
    moved = {OLD_PROFILE: PROFILE, OLD_CALC: CALC}
    for page, record in old['source']['pages'].items():
        now = new['source']['pages'].get(page, {})
        want = moved.get(record['profile'], record['profile'])
        if want != now.get('profile') or (record.get('wasmSha256') == now.get('wasmSha256')) != (record['profile'] not in moved):
            problems.append(f'{page} changed profile or wasm')
""", 1),
  ("    profile_file = next(n for n in new['files'] if n.startswith('profiles/ods-editor') and n.endswith('probe.wasm'))\n", "    profile_file = next(n for n in new['files'] if n.startswith('profiles/ods-viewer') and n.endswith('probe.wasm'))\n", 1),
  ("""        m['files']['profiles/e2-editor-v31/probe.wasm'] = {'sha256': '2' * 64}

    def wasm_moved(o, m):
        m['files'][f'profiles/{PROFILE}/probe.wasm'] = {**m['files'][f'profiles/{PROFILE}/probe.wasm'], 'sha256': '4' * 64}

    def worker_same(o, m):
        m['files'][f'profiles/{PROFILE}/sdk-worker.js'] = copy.deepcopy(o['files'][f'profiles/{OLD_PROFILE}/sdk-worker.js'])

    def still_on_v29(o, m):
        m['source']['pages']['e2-editor.html']['profile'] = OLD_PROFILE
""", """        m['files']['profiles/e2-editor-v32/probe.wasm'] = {'sha256': '2' * 64}

    def pack_moved(o, m):
        name = f'profiles/{CALC}/{PACKS[0]}'
        m['files'][name] = {**m['files'][name], 'sha256': '4' * 64}

    def wasm_same(o, m):
        m['files'][f'profiles/{PROFILE}/probe.wasm'] = copy.deepcopy(o['files'][f'profiles/{OLD_PROFILE}/probe.wasm'])

    def worker_same(o, m):
        m['files'][f'profiles/{CALC}/sdk-worker.js'] = copy.deepcopy(o['files'][f'profiles/{OLD_CALC}/sdk-worker.js'])

    def still_on_v30(o, m):
        m['source']['pages']['e2-editor.html']['profile'] = OLD_PROFILE

    def calc_still_on_v2(o, m):
        m['source']['pages']['ods-editor.html']['profile'] = OLD_CALC
""", 1),
  ("    for fn in (more, fewer, added, removed, profile_changed, page_moved, wasm_moved, worker_same, still_on_v29):\n", "    for fn in (more, fewer, added, removed, profile_changed, page_moved, pack_moved, wasm_same, worker_same, still_on_v30, calc_still_on_v2):\n", 1)],
 ('prepare-release.py', 'prepare-release.py'): [
  ('"""Package an isolated 0.2.50 host (finding 179: Shift+Up/Down/Home/End on e2-editor-v30, SPEC-P-demo-batch-3 section 2) from current\nverified dist, preserving the live predecessor.\n\nDerived from findings/evidence/host-0.2.49/prepare-release.py (not edited).',
   '"""Package an isolated 0.2.51 host (alignment on both apps, Calc text colour and cell fill, SPEC-P-demo-batch-3 section 3) from current\nverified dist, preserving the live predecessor.\n\nDerived from findings/evidence/host-0.2.50/prepare-release.py (not edited).  Closed list of differences: this paragraph; the\npredecessor is host 350cc4c (0.2.50) with the exact 0.2.50 engine, and the candidate is build/host-0.2.51; Writer is e2-editor-v31,\ngeneration 86, Calc is ods-editor-v3, the viewer stays; the delta is the nine page and shell files and the two profile moves; the\nevidence gate reads generation 86, P1, P2 and the Calc regression, C on this generation, and F3 through the clear-wait read (finding\n178\'s append); the names.\n\n0.2.50\'s docstring follows.\n\nDerived from findings/evidence/host-0.2.49/prepare-release.py (not edited).', 1),
  ("APP = SDK / 'build/host-0.2.50/litecore'", "APP = SDK / 'build/host-0.2.51/litecore'", 1),
  ("PARENT = '7782714'", "PARENT = '350cc4c'", 1),
  ("OLD = SDK / 'build/archive/host-0.2.49-engine-dd6159b571d9b966'", f"OLD = SDK / 'build/archive/{A50}'", 1),
  ("PROFILE = 'e2-editor-v30'\nOLD_PROFILE = 'e2-editor-v29'\nDECLARED_CHANGED = ['e2-editor-app.js']\nFILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')\nADDED = sorted(f'profiles/{PROFILE}/{n}' for n in FILES)\nREMOVED = sorted(f'profiles/{OLD_PROFILE}/{n}' for n in FILES)\n",
   CONSTANTS.replace('DECLARED =', 'DECLARED_CHANGED =') + "CALC_WASM = 'e6593b2c59af2a9fafd5110c09bbb1f88e298a0ca35028191978cfb6d99f48c0'\n", 1),
  ("from v85_four_arms_identity import identity  # noqa: E402", "from v86_four_arms_identity import identity  # noqa: E402", 1),
  ("    calc = load(BATCH2 / 'calc-sheet-view/run-02/report.json')\n", "    calc = load(BATCH3 / 'calc-sheet-view/run-86/report.json')\n", 1),
  ("    zoom = load(BATCH3 / 'writer-zoom/run-01/report.json')\n    f4 = load(BATCH3 / 'f4-85/aggregate-judge.json')\n    equal = json.loads((BATCH3 / 'f3-85/equal.stdout.txt').read_bytes())\n    self_test = json.loads((BATCH3 / 'f3-85/equal-self-test.stdout.txt').read_bytes())\n    v0 = load(BATCH3 / 'v0-02/v0-prime.json')\n    e1c = [load(BATCH3 / 'freeze-85/e1-c.json').get('intact'), load(BATCH3 / 'v0-02/e1-c-after-put-back.json').get('intact')]\n    shift_red = load(BATCH3 / 'shift-lines/red-on-v29/report.json')\n    shift = load(BATCH3 / 'shift-lines/live-page/report.json')\n",
   "    zoom = load(BATCH3 / 'writer-zoom/run-86/report.json')\n    f4 = load(BATCH3 / 'f4-86/aggregate-judge.json')\n    equal = json.loads((BATCH3 / 'f3-86/diag-clear-wait/equal.stdout.txt').read_bytes())\n    self_test = json.loads((BATCH3 / 'f3-86/diag-clear-wait/equal-self-test.stdout.txt').read_bytes())\n    original = json.loads((BATCH3 / 'f3-86/equal.stdout.txt').read_bytes())\n    v0 = load(BATCH3 / 'v0-86/v0-prime.json')\n    e1c = [load(BATCH3 / 'freeze-86/e1-c.json').get('intact'), load(BATCH3 / 'v0-86/e1-c-after-put-back.json').get('intact')]\n    shift_red = load(BATCH3 / 'shift-lines/red-on-v29/report.json')\n    shift = load(BATCH3 / 'shift-lines/live-page-86/report.json')\n    p1 = load(BATCH3 / 'p1/final-86/report.json')\n    p1_reds = [load(BATCH3 / f'p1/{n}/report.json').get('verdict') for n in ('red-no-undo', 'red-swap-worker')]\n    p2 = load(BATCH3 / 'p2/final-dist/report.json')\n    p2_reds = [load(BATCH3 / f'p2/{n}/report.json') for n in ('red-wrong-fill', 'red-engine-v2')]\n    regression = [load(BATCH3 / f'calc-regression/{n}/report.json') for n in ('cell-v3-01', 'range-v3-01', 'auto-v3-01')]\n", 1),
  ("        'S1': (shift.get('verdict'), 'S1_HOLDS'),\n", "        'S1': (shift.get('verdict'), 'S1_HOLDS'),\n        'P1': (p1.get('verdict'), 'P1_HOLDS'),\n        'P1-red-cases': (p1_reds, ['P1_RED', 'P1_RED']),\n        'P2': (all_pass(p2), True),\n        'P2-red-cases': ([all_pass(r) for r in p2_reds], [False, False]),\n        'Calc-regression-on-v3': ([all_pass(r) for r in regression], [True, True, True]),\n", 1),
  ("        'F3-85': (equal.get('verdict'), 'F3_83_EQUAL'),\n        'F3-85-self-test': (self_test.get('selfTest'), 'ALL_RED'),\n        'F4-85': ('PASS'", "        'F3-86': (equal.get('verdict'), 'F3_83_EQUAL'),\n        'F3-86-self-test': (self_test.get('selfTest'), 'ALL_RED'),\n        'F3-86-moved-cell-stays-on-record': ([m['check'] for m in original['reading2']['moved']], ['every-inline-format-reaches-the-document']),\n        'F4-86': ('PASS'", 1),
  ("        'V0prime-85': (v0.get('verdict'), 'V0_PRIME_HOLDS'),\n", "        'V0prime-86': (v0.get('verdict'), 'V0_PRIME_HOLDS'),\n", 1),
  ("raise ValueError('live predecessor differs from clean 7782714 (0.2.49)')", "raise ValueError('live predecessor differs from clean 350cc4c (0.2.50)')", 1),
  ("if '<version>0.2.50</version>' not in", "if '<version>0.2.51</version>' not in", 1),
  ("    if want['profile'] != PROFILE or want['shell'].get('generation') != 85:\n        raise ValueError('identity module does not name e2-editor-v30 / generation 85')\n", "    if want['profile'] != PROFILE or want['shell'].get('generation') != 86:\n        raise ValueError('identity module does not name e2-editor-v31 / generation 86')\n", 1),
  ("""    for html, module in (('ods-viewer.html', 'web/ods-viewer-app.js'), ('ods-editor.html', 'web/ods-editor-app.js')):
        if pages[html] != old['source']['pages'][html] or files[html] != old['files'][html]:
            raise ValueError('viewer/Calc identity changed: ' + html)
""", """    if pages['ods-viewer.html'] != old['source']['pages']['ods-viewer.html'] or files['ods-viewer.html'] != old['files']['ods-viewer.html']:
        raise ValueError('viewer identity changed')
    sheet = pages['ods-editor.html']
    if sheet['profile'] != CALC or sheet['wasmSha256'] != CALC_WASM or sheet['moduleSha256'] != sha(SDK / 'web/ods-editor-app.js'):
        raise ValueError('Calc page is not the verified ods-editor-v3 page')
""", 1),
  ("        raise ValueError('editor is not the verified generation-85 page')", "        raise ValueError('editor is not the verified generation-86 page')", 1),
  ("    if changed != DECLARED_CHANGED or added != ADDED or removed != REMOVED:\n        raise ValueError('delta against 0.2.49 is not exactly the page and the profile move: '\n", "    if changed != DECLARED_CHANGED or added != ADDED or removed != REMOVED:\n        raise ValueError('delta against 0.2.50 is not exactly the pages and the two profile moves: '\n", 1),
  ("archive = SDK / 'build/archive' / ('host-0.2.50-engine-' + manifest['buildId'])", "archive = SDK / 'build/archive' / ('host-0.2.51-engine-' + manifest['buildId'])", 1),
  ("""'# Exact host 0.2.50 engine package\\n\\n'
        f'Host commit {candidate}, predecessor {parent} (0.2.49, exact 0.2.49 engine). Writer on profile e2-editor-v30, shell '
        'generation 85: Shift+Up/Down/Home/End work again (finding 179, SPEC-P-demo-batch-3 section 2). Uncounted candidate.\\n')""",
   """'# Exact host 0.2.51 engine package\\n\\n'
        f'Host commit {candidate}, predecessor {parent} (0.2.50, exact 0.2.50 engine). Writer on profile e2-editor-v31, shell '
        'generation 86, Calc on ods-editor-v3: alignment on both apps, Calc text colour and cell fill (SPEC-P-demo-batch-3 section 3). Uncounted candidate.\\n')""", 1),
  ("release = {'version': '0.2.50',", "release = {'version': '0.2.51',", 1),
  ("'branch': 'host-0.2.50',", "'branch': 'host-0.2.51',", 1),
  ("'shellGeneration': 85,", "'shellGeneration': 86,", 1),
  ("'countBasis': 'K holds on 0.2.45 (release-0.2.45/k-verdict.json); this release changes the worker gate on the same engine bytes and is read by its own gates',", "'countBasis': 'K holds on 0.2.45 (release-0.2.45/k-verdict.json); this release links both engines anew and is read by its own gates, not counted',", 1)],
}
for (source, target), replacements in PLAN.items():
    text = (OLD / source).read_text(encoding='utf-8')
    for old, new, count in replacements:
        got = text.count(old)
        if got != count:
            raise SystemExit(f'{source}: {old[:70]!r} occurs {got} times, expected {count}')
        text = text.replace(old, new)
    (NEW / target).write_text(text, encoding='utf-8')
    print(target, 'written')
