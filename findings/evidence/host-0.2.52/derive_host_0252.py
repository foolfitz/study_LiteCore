#!/usr/bin/env python3
"""Derive host-0.2.52's scripts from host-0.2.51's (SPEC-P-demo-batch-4 section 5): each replacement must match its stated count; the 0.2.51 files
are not edited.  0.2.52 moves Writer from e2-editor-v31 to e2-editor-v32, a real link, so all four profile files are new.  Calc and the viewer do
not move, so the delta is simpler than 0.2.51's: the five Writer page and shell files and one profile move.
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[1]
OLD, NEW = EV / 'host-0.2.51', EV / 'host-0.2.52'
A50, A51 = 'host-0.2.50-engine-7e3edb640c50d628', 'host-0.2.51-engine-60fd728f61134b05'
DECLARED = ['e2-editor-app.js', 'e2-editor.html', 'editor-shell-v2/narrow-editor-v2-client.js', 'editor-shell-v2/narrow-editor-v2-session.js',
            'editor-shell-v2/paragraph-editor-client.js']
CONSTANTS = f"""OLD_PROFILE, PROFILE = 'e2-editor-v31', 'e2-editor-v32'
FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
ADDED = sorted(f'profiles/{{PROFILE}}/{{n}}' for n in FILES)
REMOVED = sorted(f'profiles/{{OLD_PROFILE}}/{{n}}' for n in FILES)
"""


def between(text, start, end):
    a = text.index(start)
    return text[a:text.index(end, a) + len(end)]


delta = (OLD / 'check-delta.py').read_text(encoding='utf-8')
release = (OLD / 'prepare-release.py').read_text(encoding='utf-8')
PLAN = {
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('only BUILD_ID rebound for candidate 0.2.51.', 'only BUILD_ID rebound for candidate 0.2.52.', 1),
  ('this docstring (0.2.50 -> 0.2.51 in its first line, and', 'this docstring (0.2.51 -> 0.2.52 in its first line, and', 1),
  ('rebinding; the 0.2.51 delta is judged', 'rebinding; the 0.2.52 delta is judged', 1)],
 ('capture-after.py', 'capture-after.py'): [('"""Read the installed 0.2.51 identity', '"""Read the installed 0.2.52 identity', 1)],
 ('install-0.2.51.py', 'install-0.2.52.py'): [
  ('"""Guarded 0.2.51 candidate install;', '"""Guarded 0.2.52 candidate install;', 1),
  ('names: host 350cc4c (0.2.50)\nwith the exact 0.2.50 engine archive.', 'names: host 1b8c667 (0.2.51)\nwith the exact 0.2.51 engine archive.', 1),
  ("candidate = SDK / 'build/host-0.2.51/litecore'", "candidate = SDK / 'build/host-0.2.52/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('# Functional engine rollback to exact 0.2.50 bytes, preserving host label 0.2.51', '# Functional engine rollback to exact 0.2.51 bytes, preserving host label 0.2.52', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.51', 'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.52', 1),
  ("spec_from_file_location('host051_install',out/'install-0.2.51.py')", "spec_from_file_location('host052_install',out/'install-0.2.52.py')", 1),
  (f"{A50}')", f"{A51}')", 1),
  ('Exact 0.2.50 engine restored; host label stays 0.2.51;', 'Exact 0.2.51 engine restored; host label stays 0.2.52;', 1)],
 ('check-delta.py', 'check-delta.py'): [
  (between(delta, '"""SPEC-P-demo-batch-3 section 3', 'the red cases that follow.\n"""'),
   '"""SPEC-P-demo-batch-4 section 5: the 0.2.52 package differs from 0.2.51 in exactly the five Writer page and shell files; Writer moves to\n'
   'e2-editor-v32 with every profile file new, a real link; Calc and the viewer do not move -- read from the two archived MANIFEST.json files, not\n'
   "from prepare-release.py's own say-so.\n\n"
   'Derived from findings/evidence/host-0.2.51/check-delta.py (not edited).  Closed list of differences: this docstring; the declared delta; one\n'
   'profile moves and the other two stay; the red cases that follow.\n"""', 1),
  (between(delta, 'DECLARED = [', "REMOVED = sorted([f'profiles/{OLD_PROFILE}/{n}' for n in FILES] + [f'profiles/{OLD_CALC}/{n}' for n in FILES + PACKS])\n"),
   f'DECLARED = {DECLARED!r}\n' + CONSTANTS, 1),
  (between(delta, '    for n in PACKS:\n', "problems.append(f'{page} changed profile or wasm')\n"),
   """    for n in FILES:
        was, now = of.get(f'profiles/{OLD_PROFILE}/{n}', {}), nf.get(f'profiles/{PROFILE}/{n}', {})
        if not now.get('sha256') or was.get('sha256') == now.get('sha256'):
            problems.append(f'{PROFILE} {n} does not differ from {OLD_PROFILE}')
    for page, record in old['source']['pages'].items():
        now = new['source']['pages'].get(page, {})
        want = PROFILE if record['profile'] == OLD_PROFILE else record['profile']
        if want != now.get('profile') or (record.get('wasmSha256') == now.get('wasmSha256')) != (record['profile'] != OLD_PROFILE):
            problems.append(f'{page} changed profile or wasm')
""", 1),
  ("m['files']['profiles/e2-editor-v32/probe.wasm'] = {'sha256': '2' * 64}", "m['files']['profiles/e2-editor-v33/probe.wasm'] = {'sha256': '2' * 64}", 1),
  (between(delta, '    def pack_moved(o, m):\n', "m['files'][f'profiles/{PROFILE}/probe.wasm'] = copy.deepcopy(o['files'][f'profiles/{OLD_PROFILE}/probe.wasm'])\n"),
   "    def wasm_same(o, m):\n        m['files'][f'profiles/{PROFILE}/probe.wasm'] = copy.deepcopy(o['files'][f'profiles/{OLD_PROFILE}/probe.wasm'])\n", 1),
  ("m['files'][f'profiles/{CALC}/sdk-worker.js'] = copy.deepcopy(o['files'][f'profiles/{OLD_CALC}/sdk-worker.js'])",
   "m['files'][f'profiles/{PROFILE}/sdk-worker.js'] = copy.deepcopy(o['files'][f'profiles/{OLD_PROFILE}/sdk-worker.js'])", 1),
  ("    def still_on_v30(o, m):\n", "    def still_on_v31(o, m):\n", 1),
  ("    def calc_still_on_v2(o, m):\n        m['source']['pages']['ods-editor.html']['profile'] = OLD_CALC\n\n",
   "    def calc_moved(o, m):\n        m['source']['pages']['ods-editor.html']['wasmSha256'] = '5' * 64\n\n", 1),
  ("for fn in (more, fewer, added, removed, profile_changed, page_moved, pack_moved, wasm_same, worker_same, still_on_v30, calc_still_on_v2):",
   "for fn in (more, fewer, added, removed, profile_changed, page_moved, wasm_same, worker_same, still_on_v31, calc_moved):", 1)],
 ('prepare-release.py', 'prepare-release.py'): [
  (between(release, '"""Package an isolated 0.2.51 host', '0.2.50\'s docstring follows.\n'),
   '"""Package an isolated 0.2.52 host (the heading menu, list toggles, findings 180, 181, 182, SPEC-P-demo-batch-4) from current verified dist,\n'
   'preserving the live predecessor.\n\n'
   'Derived from findings/evidence/host-0.2.51/prepare-release.py (not edited).  Closed list of differences: this paragraph; the predecessor is host\n'
   '1b8c667 (0.2.51) with the exact 0.2.51 engine, and the candidate is build/host-0.2.52; Writer is e2-editor-v32, generation 87, Calc and the viewer\n'
   'stay; the delta is the five Writer page and shell files and one profile move; the evidence gate reads generation 87, P4 and its red cases, P1 and\n'
   'C on this generation, F3 from its own run, whose runner now waits on the toast, and Calc\'s P2 and regression from batch 3, whose engine and page\n'
   "these bytes are; the names.\n\n0.2.51's docstring follows.\n\n"
   + between(release, '"""Package an isolated 0.2.51 host', '0.2.50\'s docstring follows.\n')[3:], 1),
  ("APP = SDK / 'build/host-0.2.51/litecore'", "APP = SDK / 'build/host-0.2.52/litecore'", 1),
  ("PARENT = '350cc4c'", "PARENT = '1b8c667'", 1),
  (f"OLD = SDK / 'build/archive/{A50}'", f"OLD = SDK / 'build/archive/{A51}'", 1),
  (between(release, 'DECLARED_CHANGED = [', "REMOVED = sorted([f'profiles/{OLD_PROFILE}/{n}' for n in FILES] + [f'profiles/{OLD_CALC}/{n}' for n in FILES + PACKS])\n"),
   f'DECLARED_CHANGED = {DECLARED!r}\n' + CONSTANTS + "CALC = 'ods-editor-v3'\n", 1),
  ("BATCH3 = ROOT / 'findings/evidence/demo-batch-3'\n", "BATCH3 = ROOT / 'findings/evidence/demo-batch-3'\nBATCH4 = ROOT / 'findings/evidence/demo-batch-4'\n", 1),
  ("from v86_four_arms_identity import identity  # noqa: E402", "from v87_four_arms_identity import identity  # noqa: E402", 1),
  ("    calc = load(BATCH3 / 'calc-sheet-view/run-86/report.json')\n", "    calc = load(BATCH4 / 'calc-sheet-view/run-87/report.json')\n", 1),
  (between(release, "    zoom = load(BATCH3 / 'writer-zoom/run-86/report.json')\n", "    shift_red = load(BATCH3 / 'shift-lines/red-on-v29/report.json')\n"),
   "    zoom = load(BATCH4 / 'writer-zoom/run-87/report.json')\n"
   "    f4 = load(BATCH4 / 'f4-87/aggregate-judge.json')\n"
   "    equal = json.loads((BATCH4 / 'f3-87/equal.stdout.txt').read_bytes())\n"
   "    self_test = json.loads((BATCH4 / 'f3-87/equal-self-test.stdout.txt').read_bytes())\n"
   "    v0 = load(BATCH4 / 'v0-87/v0-prime.json')\n"
   "    e1c = [load(BATCH4 / 'freeze-87/e1-c.json').get('intact'), load(BATCH4 / 'v0-87/e1-c-after-put-back.json').get('intact')]\n"
   "    shift_red = load(BATCH3 / 'shift-lines/red-on-v29/report.json')\n", 1),
  ("    shift = load(BATCH3 / 'shift-lines/live-page-86/report.json')\n    p1 = load(BATCH3 / 'p1/final-86/report.json')\n",
   "    shift = load(BATCH4 / 'shift-lines/live-page-87/report.json')\n    p1 = load(BATCH4 / 'p1/final-87/report.json')\n"
   "    p4 = load(BATCH4 / 'p4/final-87/report.json')\n"
   "    p4_reds = [load(BATCH4 / f'p4/{n}/report.json').get('verdict') for n in ('red-swap-levels-02', 'red-no-undo', 'red-no-second-press')]\n", 1),
  ("        'P1-red-cases': (p1_reds, ['P1_RED', 'P1_RED']),\n",
   "        'P1-red-cases': (p1_reds, ['P1_RED', 'P1_RED']),\n        'P4': (p4.get('verdict'), 'P4_HOLDS'),\n        'P4-red-cases': (p4_reds, ['P4_RED', 'P4_RED', 'P4_RED']),\n", 1),
  ("        'F3-86': (equal.get('verdict'), 'F3_83_EQUAL'),\n", "        'F3-87': (equal.get('verdict'), 'F3_83_EQUAL'),\n", 1),
  ("        'F3-86-self-test': (self_test.get('selfTest'), 'ALL_RED'),\n", "        'F3-87-self-test': (self_test.get('selfTest'), 'ALL_RED'),\n", 1),
  ("        'F3-86-moved-cell-stays-on-record': ([m['check'] for m in original['reading2']['moved']], ['every-inline-format-reaches-the-document']),\n",
   "        'F3-87-no-cell-moved': (equal['reading2']['moved'], []),\n", 1),
  ("        'F4-86': ('PASS'", "        'F4-87': ('PASS'", 1),
  ("        'V0prime-86': (v0.get('verdict'), 'V0_PRIME_HOLDS'),\n", "        'V0prime-87': (v0.get('verdict'), 'V0_PRIME_HOLDS'),\n", 1),
  ("raise ValueError('live predecessor differs from clean 350cc4c (0.2.50)')", "raise ValueError('live predecessor differs from clean 1b8c667 (0.2.51)')", 1),
  ("if '<version>0.2.51</version>' not in", "if '<version>0.2.52</version>' not in", 1),
  ("    if want['profile'] != PROFILE or want['shell'].get('generation') != 86:\n        raise ValueError('identity module does not name e2-editor-v31 / generation 86')\n",
   "    if want['profile'] != PROFILE or want['shell'].get('generation') != 87:\n        raise ValueError('identity module does not name e2-editor-v32 / generation 87')\n", 1),
  (between(release, "    sheet = pages['ods-editor.html']\n", "raise ValueError('Calc page is not the verified ods-editor-v3 page')\n"),
   "    if pages['ods-editor.html'] != old['source']['pages']['ods-editor.html'] or files['ods-editor.html'] != old['files']['ods-editor.html']:\n"
   "        raise ValueError('Calc identity changed')\n", 1),
  ("raise ValueError('editor is not the verified generation-86 page')", "raise ValueError('editor is not the verified generation-87 page')", 1),
  ("raise ValueError('delta against 0.2.50 is not exactly the pages and the two profile moves: '", "raise ValueError('delta against 0.2.51 is not exactly the five files and the profile move: '", 1),
  ("archive = SDK / 'build/archive' / ('host-0.2.51-engine-' + manifest['buildId'])", "archive = SDK / 'build/archive' / ('host-0.2.52-engine-' + manifest['buildId'])", 1),
  ("(archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.51 engine package\\n\\n'", "(archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.52 engine package\\n\\n'", 1),
  ("f'Host commit {candidate}, predecessor {parent} (0.2.50, exact 0.2.50 engine). Writer on profile e2-editor-v31, shell '", "f'Host commit {candidate}, predecessor {parent} (0.2.51, exact 0.2.51 engine). Writer on profile e2-editor-v32, shell '", 1),
  ("'generation 86, Calc on ods-editor-v3: alignment on both apps, Calc text colour and cell fill (SPEC-P-demo-batch-3 section 3). Uncounted candidate.\\n')",
   "'generation 87, Calc on ods-editor-v3: the heading menu, list toggles, findings 180, 181, 182 (SPEC-P-demo-batch-4). Uncounted candidate.\\n')", 1),
  ("release = {'version': '0.2.51',", "release = {'version': '0.2.52',", 1),
  ("'branch': 'host-0.2.51',", "'branch': 'host-0.2.52',", 1),
  ("'shellGeneration': 86,", "'shellGeneration': 87,", 1),
  ("this release links both engines anew and is read by its own gates, not counted", "this release links Writer anew and is read by its own gates, not counted", 1)],
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
