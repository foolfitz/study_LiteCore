#!/usr/bin/env python3
"""Derive host-0.2.50's scripts from host-0.2.49's (SPEC-P-demo-batch-3 section 2): each replacement must match its stated count;
the 0.2.49 files are not edited.  0.2.50 moves Writer from e2-editor-v29 to e2-editor-v30: the page's worker URL, the profile's
worker and manifest; wasm and loader are the same bytes under the new path.
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[1]
OLD, NEW = EV / 'host-0.2.49', EV / 'host-0.2.50'
A48, A49 = 'host-0.2.48-engine-a632c4463e700493', 'host-0.2.49-engine-dd6159b571d9b966'
PLAN = {
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('only BUILD_ID rebound for candidate 0.2.49.', 'only BUILD_ID rebound for candidate 0.2.50.', 1),
  ('this docstring (0.2.48 -> 0.2.49 in its first line, and', 'this docstring (0.2.49 -> 0.2.50 in its first line, and', 1),
  ('rebinding; the 0.2.49 delta is judged', 'rebinding; the 0.2.50 delta is judged', 1)],
 ('capture-after.py', 'capture-after.py'): [('"""Read the installed 0.2.49 identity', '"""Read the installed 0.2.50 identity', 1)],
 ('install-0.2.49.py', 'install-0.2.50.py'): [
  ('"""Guarded 0.2.49 candidate install;', '"""Guarded 0.2.50 candidate install;', 1),
  ('names: host 0411329 (0.2.48)\nwith the exact 0.2.48 engine archive.', 'names: host 7782714 (0.2.49)\nwith the exact 0.2.49 engine archive.', 1),
  ("candidate = SDK / 'build/host-0.2.49/litecore'", "candidate = SDK / 'build/host-0.2.50/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('# Functional engine rollback to exact 0.2.48 bytes, preserving host label 0.2.49', '# Functional engine rollback to exact 0.2.49 bytes, preserving host label 0.2.50', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.49', 'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.50', 1),
  ("spec_from_file_location('host049_install',out/'install-0.2.49.py')", "spec_from_file_location('host050_install',out/'install-0.2.50.py')", 1),
  (f"{A48}')", f"{A49}')", 1),
  ('Exact 0.2.48 engine restored; host label stays 0.2.49;', 'Exact 0.2.49 engine restored; host label stays 0.2.50;', 1)],
 ('check-delta.py', 'check-delta.py'): [
  ('"""SPEC-P-demo-batch-2 append 2: the 0.2.49 package differs from 0.2.48 in exactly `ods-editor.html`, with no profile\nadded, removed or changed -- read from the two archived MANIFEST.json files, not from prepare-release.py\'s own say-so.\n\nDerived from findings/evidence/host-0.2.47/check-delta.py (not edited).  Closed list of differences: this docstring; the declared\ndelta, two records; one red case for the second record.\n"""',
   '"""SPEC-P-demo-batch-3 section 2: the 0.2.50 package differs from 0.2.49 in exactly `e2-editor-app.js`, and e2-editor-v29\'s files\nmove to e2-editor-v30 with the wasm and the loader byte for byte and the worker and manifest new -- read from the two archived\nMANIFEST.json files, not from prepare-release.py\'s own say-so.\n\nDerived from findings/evidence/host-0.2.49/check-delta.py (not edited).  Closed list of differences: this docstring; the declared\ndelta; the profile clauses of findings/evidence/host-0.2.45/check-delta.py; the red cases that follow from them.\n"""', 1),
  ("DECLARED = ['ods-editor.html']\n", "DECLARED = ['e2-editor-app.js']\nOLD_PROFILE, PROFILE = 'e2-editor-v29', 'e2-editor-v30'\nFILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')\nSAME_BYTES = ('probe.js', 'probe.wasm')\nNEW_BYTES = ('sdk-manifest.json', 'sdk-worker.js')\nADDED = sorted(f'profiles/{PROFILE}/{n}' for n in FILES)\nREMOVED = sorted(f'profiles/{OLD_PROFILE}/{n}' for n in FILES)\n", 1),
  ("    if d['added'] or d['removed']:\n", "    if d['added'] != ADDED or d['removed'] != REMOVED:\n", 1),
  ("""    for page, record in old['source']['pages'].items():
        now = new['source']['pages'].get(page, {})
        if (record['profile'], record.get('wasmSha256')) != (now.get('profile'), now.get('wasmSha256')):
            problems.append(f'{page} changed profile or wasm')
""", """    of, nf = old['files'], new['files']
    for n in SAME_BYTES:
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
""", 1),
  ("""    def fewer(o, m):
        m['files'][DECLARED[0]] = copy.deepcopy(o['files'][DECLARED[0]])

    def added(o, m):
        m['files']['profiles/e2-editor-v30/probe.wasm'] = {'sha256': '2' * 64}
""", """    def fewer(o, m):
        m['files'][DECLARED[0]] = copy.deepcopy(o['files'][DECLARED[0]])

    def added(o, m):
        m['files']['profiles/e2-editor-v31/probe.wasm'] = {'sha256': '2' * 64}

    def wasm_moved(o, m):
        m['files'][f'profiles/{PROFILE}/probe.wasm'] = {**m['files'][f'profiles/{PROFILE}/probe.wasm'], 'sha256': '4' * 64}

    def worker_same(o, m):
        m['files'][f'profiles/{PROFILE}/sdk-worker.js'] = copy.deepcopy(o['files'][f'profiles/{OLD_PROFILE}/sdk-worker.js'])

    def still_on_v29(o, m):
        m['source']['pages']['e2-editor.html']['profile'] = OLD_PROFILE
""", 1),
  ("    profile_file = next(n for n in new['files'] if n.startswith('profiles/') and n.endswith('probe.wasm'))\n", "    profile_file = next(n for n in new['files'] if n.startswith('profiles/ods-editor') and n.endswith('probe.wasm'))\n", 1),
  ("    for fn in (more, fewer, added, removed, profile_changed, page_moved):\n", "    for fn in (more, fewer, added, removed, profile_changed, page_moved, wasm_moved, worker_same, still_on_v29):\n", 1)],
 ('prepare-release.py', 'prepare-release.py'): [
  ('"""Package an isolated 0.2.49 host (the whole Calc page light under any theme, SPEC-P-demo-batch-2 append 2) from current verified dist,\npreserving the live predecessor.\n\nDerived from findings/evidence/host-0.2.47/prepare-release.py (not edited).',
   '"""Package an isolated 0.2.50 host (finding 179: Shift+Up/Down/Home/End on e2-editor-v30, SPEC-P-demo-batch-3 section 2) from current\nverified dist, preserving the live predecessor.\n\nDerived from findings/evidence/host-0.2.49/prepare-release.py (not edited).  Closed list of differences: this paragraph; the\npredecessor is host 7782714 (0.2.49) with the exact 0.2.49 engine, and the candidate is build/host-0.2.50; the profile is\ne2-editor-v30, generation 85; the delta is `e2-editor-app.js` and the profile\'s four files moving; the evidence gate reads\ndemo-batch-3; the Calc module is compared with the predecessor\'s package and not with web/, which already holds the next batch\'s\nCalc page, unshipped; the names.\n\n0.2.49\'s docstring follows.\n\nDerived from findings/evidence/host-0.2.47/prepare-release.py (not edited).', 1),
  ("APP = SDK / 'build/host-0.2.49/litecore'", "APP = SDK / 'build/host-0.2.50/litecore'", 1),
  ("PARENT = '0411329'", "PARENT = '7782714'", 1),
  ("OLD = SDK / 'build/archive/host-0.2.48-engine-a632c4463e700493'", "OLD = SDK / 'build/archive/host-0.2.49-engine-dd6159b571d9b966'", 1),
  ("PROFILE = 'e2-editor-v29'\nDECLARED_CHANGED = ['ods-editor.html']\n", "PROFILE = 'e2-editor-v30'\nOLD_PROFILE = 'e2-editor-v29'\nDECLARED_CHANGED = ['e2-editor-app.js']\nFILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')\nADDED = sorted(f'profiles/{PROFILE}/{n}' for n in FILES)\nREMOVED = sorted(f'profiles/{OLD_PROFILE}/{n}' for n in FILES)\n", 1),
  ("BATCH2 = ROOT / 'findings/evidence/demo-batch-2'\n", "BATCH2 = ROOT / 'findings/evidence/demo-batch-2'\nBATCH3 = ROOT / 'findings/evidence/demo-batch-3'\n", 1),
  ("from v84_four_arms_identity import identity  # noqa: E402", "from v85_four_arms_identity import identity  # noqa: E402", 1),
  ("    zoom = load(BATCH2 / 'writer-zoom/run-01/report.json')\n    f4 = load(BATCH2 / 'f4-84/aggregate-judge.json')\n    equal = json.loads((BATCH2 / 'f3-84/equal.stdout.txt').read_bytes())\n    self_test = json.loads((BATCH2 / 'f3-84/equal-self-test.stdout.txt').read_bytes())\n    v0 = load(BATCH2 / 'v0/v0-prime.json')\n    e1c = [load(BATCH / 'freeze-84/e1-c.json').get('intact'), load(BATCH2 / 'v0/e1-c-after-put-back.json').get('intact')]\n",
   "    zoom = load(BATCH3 / 'writer-zoom/run-01/report.json')\n    f4 = load(BATCH3 / 'f4-85/aggregate-judge.json')\n    equal = json.loads((BATCH3 / 'f3-85/equal.stdout.txt').read_bytes())\n    self_test = json.loads((BATCH3 / 'f3-85/equal-self-test.stdout.txt').read_bytes())\n    v0 = load(BATCH3 / 'v0-02/v0-prime.json')\n    e1c = [load(BATCH3 / 'freeze-85/e1-c.json').get('intact'), load(BATCH3 / 'v0-02/e1-c-after-put-back.json').get('intact')]\n    shift_red = load(BATCH3 / 'shift-lines/red-on-v29/report.json')\n    shift = load(BATCH3 / 'shift-lines/live-page/report.json')\n", 1),
  ("        'K-0.2.45': (k.get('verdict'), 'K_HOLDS'),\n", "        'K-0.2.45': (k.get('verdict'), 'K_HOLDS'),\n        'S1-red-on-v29': (shift_red.get('verdict'), 'S1_RED'),\n        'S1': (shift.get('verdict'), 'S1_HOLDS'),\n", 1),
  ("        'F3-84': (equal.get('verdict'), 'F3_83_EQUAL'),\n        'F3-84-self-test': (self_test.get('selfTest'), 'ALL_RED'),\n        'F4-84': ('PASS'", "        'F3-85': (equal.get('verdict'), 'F3_83_EQUAL'),\n        'F3-85-self-test': (self_test.get('selfTest'), 'ALL_RED'),\n        'F4-85': ('PASS'", 1),
  ("        'V0prime-84': (v0.get('verdict'), 'V0_PRIME_HOLDS'),\n", "        'V0prime-85': (v0.get('verdict'), 'V0_PRIME_HOLDS'),\n", 1),
  ("raise ValueError('live predecessor differs from clean 0411329 (0.2.48)')", "raise ValueError('live predecessor differs from clean 7782714 (0.2.49)')", 1),
  ("if '<version>0.2.49</version>' not in", "if '<version>0.2.50</version>' not in", 1),
  ("    if want['profile'] != PROFILE or want['shell'].get('generation') != 84:\n        raise ValueError('identity module does not name e2-editor-v29 / generation 84')\n", "    if want['profile'] != PROFILE or want['shell'].get('generation') != 85:\n        raise ValueError('identity module does not name e2-editor-v30 / generation 85')\n", 1),
  ("""        if pages[html] != old['source']['pages'][html] or pages[html]['moduleSha256'] != sha(SDK / module) \\
                or (html == 'ods-viewer.html' and files[html] != old['files'][html]):
            raise ValueError('viewer/Calc identity changed, or the viewer HTML moved: ' + html)
""", """        if pages[html] != old['source']['pages'][html] or files[html] != old['files'][html]:
            raise ValueError('viewer/Calc identity changed: ' + html)
""", 1),
  ("        raise ValueError('editor is not the verified generation-84 page')", "        raise ValueError('editor is not the verified generation-85 page')", 1),
  ("    if changed != DECLARED_CHANGED or added or removed:\n        raise ValueError('delta against 0.2.48 is not exactly ods-editor.html: '\n", "    if changed != DECLARED_CHANGED or added != ADDED or removed != REMOVED:\n        raise ValueError('delta against 0.2.49 is not exactly the page and the profile move: '\n", 1),
  ("archive = SDK / 'build/archive' / ('host-0.2.49-engine-' + manifest['buildId'])", "archive = SDK / 'build/archive' / ('host-0.2.50-engine-' + manifest['buildId'])", 1),
  ("""'# Exact host 0.2.49 engine package\\n\\n'
        f'Host commit {candidate}, predecessor {parent} (0.2.48, exact 0.2.48 engine). Writer on profile e2-editor-v29, shell '
        'generation 84; the whole Calc page light under any theme (SPEC-P-demo-batch-2 append 2). Uncounted candidate.\\n')""",
   """'# Exact host 0.2.50 engine package\\n\\n'
        f'Host commit {candidate}, predecessor {parent} (0.2.49, exact 0.2.49 engine). Writer on profile e2-editor-v30, shell '
        'generation 85: Shift+Up/Down/Home/End work again (finding 179, SPEC-P-demo-batch-3 section 2). Uncounted candidate.\\n')""", 1),
  ("release = {'version': '0.2.49',", "release = {'version': '0.2.50',", 1),
  ("'branch': 'host-0.2.49',", "'branch': 'host-0.2.50',", 1),
  ("'shellGeneration': 84,", "'shellGeneration': 85,", 1),
  ("'countBasis': 'K holds on 0.2.45 (release-0.2.45/k-verdict.json); this batch changes pages only and is read by its own gates',", "'countBasis': 'K holds on 0.2.45 (release-0.2.45/k-verdict.json); this release changes the worker gate on the same engine bytes and is read by its own gates',", 1)],
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
