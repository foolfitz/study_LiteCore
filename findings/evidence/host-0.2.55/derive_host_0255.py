#!/usr/bin/env python3
"""Derive host-0.2.55's scripts from host-0.2.54's (SPEC-P-calc-undo): each replacement must match its stated count; the 0.2.54 files are not
edited.  0.2.55 is Calc document undo: the Calc page's four files change and the Calc profile moves ods-editor-v3 -> ods-editor-v4 (six files
each, measured with the packager's own closure before writing this); the host source is info.xml alone; Writer and the viewer do not move.
The Calc half of the checks is 0.2.51's (the last Calc profile move); the gate adds the Calc undo evidence.
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[1]
OLD, NEW = EV / 'host-0.2.54', EV / 'host-0.2.55'
A53, A54 = 'host-0.2.53-engine-89860962782b3a21', 'host-0.2.54-engine-89860962782b3a21'
CALC_V4_WASM = '9f37ed5a447bfc23db058b24e7a129087eab1c303e3c833e0de8e01bffd33b00'
DECLARED = "['ods-editor-app.js', 'ods-editor.html', 'spreadsheet-shell/calc-document-sdk.js', 'spreadsheet-shell/calc-editor-session.js']"
CALC_MOVE = """OLD_CALC, CALC = 'ods-editor-v3', 'ods-editor-v4'
PACKS = ('base-viewer-v3-no35.21bec6461a48d3ec.data', 'base-viewer-v3-no35.43da6a24481dc483.metadata')
ADDED = sorted(f'profiles/{CALC}/{n}' for n in FILES + PACKS)
REMOVED = sorted(f'profiles/{OLD_CALC}/{n}' for n in FILES + PACKS)
CALC_WASM = '""" + CALC_V4_WASM + "'\n"


def between(text, start, end):
    a = text.index(start)
    return text[a:text.index(end, a) + len(end)]


delta = (OLD / 'check-delta.py').read_text(encoding='utf-8')
release = (OLD / 'prepare-release.py').read_text(encoding='utf-8')
PLAN = {
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('only BUILD_ID rebound for candidate 0.2.54.', 'only BUILD_ID rebound for candidate 0.2.55.', 1),
  ('this docstring (0.2.53 -> 0.2.54 in its first line, and', 'this docstring (0.2.54 -> 0.2.55 in its first line, and', 1),
  ('rebinding; the 0.2.54 delta is judged', 'rebinding; the 0.2.55 delta is judged', 1)],
 ('capture-after.py', 'capture-after.py'): [('"""Read the installed 0.2.54 identity', '"""Read the installed 0.2.55 identity', 1)],
 ('install-0.2.54.py', 'install-0.2.55.py'): [
  ('"""Guarded 0.2.54 candidate install;', '"""Guarded 0.2.55 candidate install;', 1),
  ('names: host 6b1660c (0.2.53)\nwith the exact 0.2.53 engine archive.', 'names: host 8c95b50 (0.2.54)\nwith the exact 0.2.54 engine archive.', 1),
  ("candidate = SDK / 'build/host-0.2.54/litecore'", "candidate = SDK / 'build/host-0.2.55/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  (between((OLD / 'rollback-package.sh').read_text(), '# Functional engine rollback to exact 0.2.53 bytes', 'not this script.\n'),
   '# Functional engine rollback to exact 0.2.54 bytes, preserving host label 0.2.55 (derived from host-0.2.47/rollback-package.sh, not edited).\n'
   '# The 0.2.54 engine package has the Calc page on ods-editor-v3: rolling back takes Calc undo away and nothing else.\n', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.54', 'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.55', 1),
  ("spec_from_file_location('host054_install',out/'install-0.2.54.py')", "spec_from_file_location('host055_install',out/'install-0.2.55.py')", 1),
  (f"{A53}')", f"{A54}')", 1),
  ('Exact 0.2.53 engine restored; host label stays 0.2.54;', 'Exact 0.2.54 engine restored; host label stays 0.2.55;', 1)],
 ('check-delta.py', 'check-delta.py'): [
  (between(delta, '"""SPEC-P-demo-batch-6', 'there is no declared file to put back.\n"""'),
   '"""SPEC-P-calc-undo: the 0.2.55 package differs from 0.2.54 in exactly the Calc page\'s four files and the Calc profile\'s move from\n'
   "ods-editor-v3 to ods-editor-v4 (six files each); Writer's profile files keep their bytes; every page but the Calc page keeps its profile\n"
   "and wasm, and the Calc page has v4's -- read from the two archived MANIFEST.json files, not from prepare-release.py's own say-so.\n\n"
   'Derived from findings/evidence/host-0.2.54/check-delta.py (not edited).  Closed list of differences: this docstring; the declared delta and\n'
   "the profile move; the page clause wants v4 on the Calc page; the `fewer` red case is back and `calc_still_v3` is new.\n\"\"\"", 1),
  ("DECLARED = []\n", f"DECLARED = {DECLARED}\n", 1),
  ("ADDED, REMOVED = [], []\n", CALC_MOVE, 1),
  ("""        if record['profile'] != now.get('profile') or record.get('wasmSha256') != now.get('wasmSha256'):
            problems.append(f'{page} changed profile or wasm')""",
   """        want = (CALC, CALC_WASM) if page == 'ods-editor.html' else (record['profile'], record.get('wasmSha256'))
        if (now.get('profile'), now.get('wasmSha256')) != want:
            problems.append(f'{page} changed profile or wasm')""", 1),
  ("    def added(o, m):\n",
   "    def fewer(o, m):\n        m['files'][DECLARED[0]] = copy.deepcopy(o['files'][DECLARED[0]])\n\n"
   "    def calc_still_v3(o, m):\n        m['source']['pages']['ods-editor.html'] = copy.deepcopy(o['source']['pages']['ods-editor.html'])\n\n"
   "    def added(o, m):\n", 1),
  ("for fn in (more, added, removed,", "for fn in (more, fewer, calc_still_v3, added, removed,", 1)],
 ('prepare-release.py', 'prepare-release.py'): [
  (between(release, '"""Package an isolated 0.2.54 host', "0.2.53's docstring follows.\n"),
   '"""Package an isolated 0.2.55 host (Calc document undo, SPEC-P-calc-undo) from current verified dist, preserving the live predecessor.\n\n'
   'Derived from findings/evidence/host-0.2.54/prepare-release.py (not edited).  Closed list of differences: this paragraph; the predecessor is host\n'
   "8c95b50 (0.2.54) with the exact 0.2.54 engine, and the candidate is build/host-0.2.55; the host source delta is info.xml alone again, so\n"
   "0.2.54's blank-ods and G1/G3 re-run go (G1 to G3 stay in the gate); the served delta is the Calc page's four files and the Calc profile move\n"
   "to ods-editor-v4, judged as 0.2.51 judged its move (the page's profile, wasm and module), and the buildId may no longer equal the\n"
   "predecessor's; the gate adds Calc undo: CU on the frozen v4, its red on v3, the field-guard mutation, C on v4, the cell, range,\n"
   "autosave and P2 arms on v4, NU-3, the pre-link syntax and export checks, the v4 manifest's capability bits; the names.\n\n"
   "0.2.54's docstring follows.\n\n" + between(release, '"""Package an isolated 0.2.54 host', "0.2.53's docstring follows.\n")[3:], 1),
  ("APP = SDK / 'build/host-0.2.54/litecore'", "APP = SDK / 'build/host-0.2.55/litecore'", 1),
  ("PARENT = '6b1660c'", "PARENT = '8c95b50'", 1),
  ("STATIC = OUT / 'static'\n", "STATIC = OUT.parent / 'host-0.2.54/static'  # batch 6's static criteria, read where they were run\n", 1),
  (f"OLD = SDK / 'build/archive/{A53}'", f"OLD = SDK / 'build/archive/{A54}'", 1),
  ("DECLARED_CHANGED = []\n", f"DECLARED_CHANGED = {DECLARED}\n", 1),
  ("ADDED, REMOVED = [], []\nCALC = 'ods-editor-v3'\nCALC_WASM = 'e6593b2c59af2a9fafd5110c09bbb1f88e298a0ca35028191978cfb6d99f48c0'\n", CALC_MOVE, 1),
  ("BATCH5 = ROOT / 'findings/evidence/demo-batch-5'\n", "BATCH5 = ROOT / 'findings/evidence/demo-batch-5'\nUNDO = ROOT / 'findings/evidence/calc-undo'\n", 1),
  ("    g3_red = (STATIC / 'g3-red-manifest-missing-one.stdout.txt').read_text()\n",
   "    g3_red = (STATIC / 'g3-red-manifest-missing-one.stdout.txt').read_text()\n"
   "    cu = load(UNDO / 'after-freeze/cu/report.json')\n"
   "    cu_red = load(UNDO / 'cu/red-on-v3-03/report.json')\n"
   "    cu_mutation = load(UNDO / 'cu/mutation-field-guard/report.json')\n"
   "    c_v4 = load(UNDO / 'after-freeze/calc-sheet-view-v4/report.json')\n"
   "    arms_v4 = [load(UNDO / p) for p in ('after-freeze/cell-v4-dist/report.json', 'cu8-dev/range-v4/report.json',\n"
   "                                                    'cu8-dev/auto/report.json', 'cu8-dev/p2-v4/report.json')]\n"
   "    nu3 = [load(UNDO / f'nu3-{v}/report.json')['table'] for v in ('undo', 'control')]\n"
   "    syntax = load(UNDO / 'pre-link-syntax-03/report.json')['verdict']\n"
   "    ships, ships_red = load(UNDO / 'pre-link-ships/green.json'), load(UNDO / 'pre-link-ships/red-before-fix.json')\n"
   "    v4_manifest = load(SDK / 'dist/profiles/ods-editor-v4/sdk-manifest.json')\n"
   "    cu12 = ['CU-1/input', 'CU-1/cell-bold', 'CU-1/range-fill', 'CU-2/ctrl-z-input', 'CU-2/ctrl-y-input', 'CU-2/ctrl-z-bold', 'CU-2/ctrl-shift-z-bold']\n", 1),
  ("        'G3-red-manifest-missing-one': ('is not in MANIFEST.json' in g3_red, True),\n",
   "        'G3-red-manifest-missing-one': ('is not in MANIFEST.json' in g3_red, True),\n"
   "        'CU-v4': (cu.get('verdict'), 'CU_HOLDS'),\n"
   "        'CU-v4-browsers': (sorted(r['browser'] for r in cu['runs']), ['chrome', 'firefox']),\n"
   "        'CU-red-on-v3': ([all(i in {c['id'] for c in r['checks'] if not c['pass']} for i in cu12) and not r['fatal'] for r in cu_red['runs']],\n"
   "                         [True, True]),\n"
   "        'CU-field-guard-mutation': ([sorted(c['id'] for c in r['checks'] if not c['pass']) for r in cu_mutation['runs']],\n"
   "                                    [['CU-3/field-keeps-its-undo'], ['CU-3/field-keeps-its-undo']]),\n"
   "        'C-v4': (all_pass(c_v4), True),\n"
   "        'Calc-arms-on-v4': ([all_pass(r) for r in arms_v4], [True, True, True, True]),\n"
   "        'NU-3': ([{k: t[k] for k in ('cell-bold', 'cell-italic', 'draft-then-bold')} for t in nu3],\n"
   "                 [{'cell-bold': 1, 'cell-italic': 1, 'draft-then-bold': 2}, {'cell-bold': 3, 'cell-italic': 3, 'draft-then-bold': 4}]),\n"
   "        'pre-link-syntax': (all(syntax.values()) and len(syntax) == 4, True),\n"
   "        'pre-link-ships': ([ships.get('verdict'), ships_red.get('missing')], ['SHIPS', ['oxsdk_document_redo', 'oxsdk_document_undo']]),\n"
   "        'v4-manifest': ([v4_manifest.get('profile'), v4_manifest.get('expectedCapabilityBits'), 'undo' in v4_manifest.get('capabilities', [])],\n"
   "                        ['ods-editor-v4', 1046835, True]),\n", 1),
  ("raise ValueError('live predecessor differs from clean 6b1660c (0.2.53)')", "raise ValueError('live predecessor differs from clean 8c95b50 (0.2.54)')", 1),
  ("if '<version>0.2.54</version>' not in", "if '<version>0.2.55</version>' not in", 1),
  (between(release, "    blank_ods = sorted(load(APP / 'blank-ods/MANIFEST.json')['files'])\n",
           "            raise ValueError(name + ' does not hold on the candidate: ' + json.dumps(static_now[name]))\n"),
   "    source_delta = git(APP, 'diff', '--name-only', parent, candidate).splitlines()\n"
   "    if source_delta != ['appinfo/info.xml']:\n"
   "        raise ValueError('candidate host source delta is not only its version: ' + json.dumps(source_delta))\n", 1),
  ("    if manifest['buildId'] != old['buildId']:\n        raise ValueError('the engine package is not 0.2.53\\'s: ' + manifest['buildId'])\n", "", 1),
  ("""    if pages['ods-editor.html'] != old['source']['pages']['ods-editor.html'] or files['ods-editor.html'] != old['files']['ods-editor.html']:
        raise ValueError('Calc identity changed')
""", """    sheet = pages['ods-editor.html']
    if sheet['profile'] != CALC or sheet['wasmSha256'] != CALC_WASM or sheet['moduleSha256'] != sha(SDK / 'web/ods-editor-app.js'):
        raise ValueError('Calc page is not the verified ods-editor-v4 page')
""", 1),
  ("raise ValueError('delta against 0.2.53 is not empty: '", "raise ValueError('delta against 0.2.54 is not the Calc page and the v4 move: '", 1),
  ("archive = SDK / 'build/archive' / ('host-0.2.54-engine-' + manifest['buildId'])", "archive = SDK / 'build/archive' / ('host-0.2.55-engine-' + manifest['buildId'])", 1),
  ("(archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.54 engine package\\n\\n'", "(archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.55 engine package\\n\\n'", 1),
  ("f'Host commit {candidate}, predecessor {parent} (0.2.53, exact 0.2.53 engine). Writer on profile e2-editor-v32, shell '",
   "f'Host commit {candidate}, predecessor {parent} (0.2.54, exact 0.2.54 engine). Writer on profile e2-editor-v32, shell '", 1),
  ("""        'generation 88, Calc on ods-editor-v3; the same bytes as 0.2.53\\'s package. The host adds New spreadsheet and LibreOffice\\'s icons '
        '(SPEC-P-demo-batch-6). Uncounted candidate.\\n')""",
   """        'generation 88, Calc on ods-editor-v4: Calc document undo (SPEC-P-calc-undo). Uncounted candidate.\\n')""", 1),
  ("release = {'version': '0.2.54',", "release = {'version': '0.2.55',", 1),
  ("'branch': 'host-0.2.54',", "'branch': 'host-0.2.55',", 1),
  ("this release changes host source only, on 0.2.53\\'s engine package, and is read by its own gates, not counted",
   "this release moves Calc to ods-editor-v4 with its page, Writer and the viewer unchanged, and is read by its own gates, not counted", 1),
  ("'hostSourceDelta': source_delta, 'staticOnCandidate': static_now}", "'hostSourceDelta': source_delta}", 1)],
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
