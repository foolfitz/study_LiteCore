#!/usr/bin/env python3
"""Derive host-0.2.53's scripts from host-0.2.52's (SPEC-P-demo-batch-5): each replacement must match its stated count; the 0.2.52 files are not
edited.  0.2.53 changes one served file, e2-editor-app.js.  No profile moves: the delta check's profile-move clauses become "nothing moved".
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[1]
OLD, NEW = EV / 'host-0.2.52', EV / 'host-0.2.53'
A51, A52 = 'host-0.2.51-engine-60fd728f61134b05', 'host-0.2.52-engine-21985315bc752e57'
CONSTANTS_52 = """OLD_PROFILE, PROFILE = 'e2-editor-v31', 'e2-editor-v32'
FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
ADDED = sorted(f'profiles/{PROFILE}/{n}' for n in FILES)
REMOVED = sorted(f'profiles/{OLD_PROFILE}/{n}' for n in FILES)
"""
CONSTANTS_53 = """PROFILE = 'e2-editor-v32'
FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
ADDED, REMOVED = [], []
"""
DECLARED_52 = "['e2-editor-app.js', 'e2-editor.html', 'editor-shell-v2/narrow-editor-v2-client.js', 'editor-shell-v2/narrow-editor-v2-session.js', 'editor-shell-v2/paragraph-editor-client.js']"


def between(text, start, end):
    a = text.index(start)
    return text[a:text.index(end, a) + len(end)]


delta = (OLD / 'check-delta.py').read_text(encoding='utf-8')
release = (OLD / 'prepare-release.py').read_text(encoding='utf-8')
PLAN = {
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('only BUILD_ID rebound for candidate 0.2.52.', 'only BUILD_ID rebound for candidate 0.2.53.', 1),
  ('this docstring (0.2.51 -> 0.2.52 in its first line, and', 'this docstring (0.2.52 -> 0.2.53 in its first line, and', 1),
  ('rebinding; the 0.2.52 delta is judged', 'rebinding; the 0.2.53 delta is judged', 1)],
 ('capture-after.py', 'capture-after.py'): [('"""Read the installed 0.2.52 identity', '"""Read the installed 0.2.53 identity', 1)],
 ('install-0.2.52.py', 'install-0.2.53.py'): [
  ('"""Guarded 0.2.52 candidate install;', '"""Guarded 0.2.53 candidate install;', 1),
  ('names: host 1b8c667 (0.2.51)\nwith the exact 0.2.51 engine archive.', 'names: host c657aba (0.2.52)\nwith the exact 0.2.52 engine archive.', 1),
  ("candidate = SDK / 'build/host-0.2.52/litecore'", "candidate = SDK / 'build/host-0.2.53/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('# Functional engine rollback to exact 0.2.51 bytes, preserving host label 0.2.52', '# Functional engine rollback to exact 0.2.52 bytes, preserving host label 0.2.53', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.52', 'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.53', 1),
  ("spec_from_file_location('host052_install',out/'install-0.2.52.py')", "spec_from_file_location('host053_install',out/'install-0.2.53.py')", 1),
  (f"{A51}')", f"{A52}')", 1),
  ('Exact 0.2.51 engine restored; host label stays 0.2.52;', 'Exact 0.2.52 engine restored; host label stays 0.2.53;', 1)],
 ('check-delta.py', 'check-delta.py'): [
  (between(delta, '"""SPEC-P-demo-batch-4 section 5', 'the red cases that follow.\n"""'),
   '"""SPEC-P-demo-batch-5: the 0.2.53 package differs from 0.2.52 in exactly e2-editor-app.js; no profile moves, every profile file keeps its bytes\n'
   "-- read from the two archived MANIFEST.json files, not from prepare-release.py's own say-so.\n\n"
   'Derived from findings/evidence/host-0.2.52/check-delta.py (not edited).  Closed list of differences: this docstring; the declared delta; the\n'
   'profile-move clauses turned into "nothing moved"; the red cases that follow.\n"""', 1),
  (f'DECLARED = {DECLARED_52}\n' + CONSTANTS_52, "DECLARED = ['e2-editor-app.js']\n" + CONSTANTS_53, 1),
  (between(delta, '    for n in FILES:\n', "problems.append(f'{page} changed profile or wasm')\n"),
   """    for n in FILES:
        was, now = of.get(f'profiles/{PROFILE}/{n}', {}), nf.get(f'profiles/{PROFILE}/{n}', {})
        if not now.get('sha256') or was.get('sha256') != now.get('sha256'):
            problems.append(f'{PROFILE} {n} moved')
    for page, record in old['source']['pages'].items():
        now = new['source']['pages'].get(page, {})
        if record['profile'] != now.get('profile') or record.get('wasmSha256') != now.get('wasmSha256'):
            problems.append(f'{page} changed profile or wasm')
""", 1),
  ("    def wasm_same(o, m):\n        m['files'][f'profiles/{PROFILE}/probe.wasm'] = copy.deepcopy(o['files'][f'profiles/{OLD_PROFILE}/probe.wasm'])\n",
   "    def wasm_moved(o, m):\n        m['files'][f'profiles/{PROFILE}/probe.wasm'] = {**m['files'][f'profiles/{PROFILE}/probe.wasm'], 'sha256': '4' * 64}\n", 1),
  ("    def worker_same(o, m):\n        m['files'][f'profiles/{PROFILE}/sdk-worker.js'] = copy.deepcopy(o['files'][f'profiles/{OLD_PROFILE}/sdk-worker.js'])\n",
   "    def worker_moved(o, m):\n        m['files'][f'profiles/{PROFILE}/sdk-worker.js'] = {**m['files'][f'profiles/{PROFILE}/sdk-worker.js'], 'sha256': '6' * 64}\n", 1),
  ("    def still_on_v31(o, m):\n        m['source']['pages']['e2-editor.html']['profile'] = OLD_PROFILE\n",
   "    def writer_moved(o, m):\n        m['source']['pages']['e2-editor.html']['wasmSha256'] = '7' * 64\n", 1),
  ("for fn in (more, fewer, added, removed, profile_changed, page_moved, wasm_same, worker_same, still_on_v31, calc_moved):",
   "for fn in (more, fewer, added, removed, profile_changed, page_moved, wasm_moved, worker_moved, writer_moved, calc_moved):", 1)],
 ('prepare-release.py', 'prepare-release.py'): [
  (between(release, '"""Package an isolated 0.2.52 host', "0.2.51's docstring follows.\n"),
   '"""Package an isolated 0.2.53 host (Enter over a selection, the empty-copy sentence, SPEC-P-demo-batch-5) from current verified dist,\n'
   'preserving the live predecessor.\n\n'
   'Derived from findings/evidence/host-0.2.52/prepare-release.py (not edited).  Closed list of differences: this paragraph; the predecessor is host\n'
   'c657aba (0.2.52) with the exact 0.2.52 engine, and the candidate is build/host-0.2.53; Writer stays e2-editor-v32, generation 88; the delta is\n'
   'e2-editor-app.js alone; the evidence gate reads generation 88 and P5 with its red case, P4\'s red cases from batch 4; the names.\n\n'
   "0.2.52's docstring follows.\n\n" + between(release, '"""Package an isolated 0.2.52 host', "0.2.51's docstring follows.\n")[3:], 1),
  ("APP = SDK / 'build/host-0.2.52/litecore'", "APP = SDK / 'build/host-0.2.53/litecore'", 1),
  ("PARENT = '1b8c667'", "PARENT = 'c657aba'", 1),
  (f"OLD = SDK / 'build/archive/{A51}'", f"OLD = SDK / 'build/archive/{A52}'", 1),
  (f'DECLARED_CHANGED = {DECLARED_52}\n' + CONSTANTS_52, "DECLARED_CHANGED = ['e2-editor-app.js']\n" + CONSTANTS_53, 1),
  ("BATCH4 = ROOT / 'findings/evidence/demo-batch-4'\n", "BATCH4 = ROOT / 'findings/evidence/demo-batch-4'\nBATCH5 = ROOT / 'findings/evidence/demo-batch-5'\n", 1),
  ("from v87_four_arms_identity import identity  # noqa: E402", "from v88_four_arms_identity import identity  # noqa: E402", 1),
  ("load(BATCH4 / 'calc-sheet-view/run-87/report.json')", "load(BATCH5 / 'calc-sheet-view/run-88/report.json')", 1),
  ("load(BATCH4 / 'writer-zoom/run-87/report.json')", "load(BATCH5 / 'writer-zoom/run-88/report.json')", 1),
  ("load(BATCH4 / 'f4-87/aggregate-judge.json')", "load(BATCH5 / 'f4-88/aggregate-judge.json')", 1),
  ("(BATCH4 / 'f3-87/equal.stdout.txt')", "(BATCH5 / 'f3-88/equal.stdout.txt')", 1),
  ("(BATCH4 / 'f3-87/equal-self-test.stdout.txt')", "(BATCH5 / 'f3-88/equal-self-test.stdout.txt')", 1),
  ("load(BATCH4 / 'v0-87/v0-prime.json')", "load(BATCH5 / 'v0-88/v0-prime.json')", 1),
  ("[load(BATCH4 / 'freeze-87/e1-c.json').get('intact'), load(BATCH4 / 'v0-87/e1-c-after-put-back.json').get('intact')]",
   "[load(BATCH5 / 'freeze-88/e1-c.json').get('intact'), load(BATCH5 / 'v0-88/e1-c-after-put-back.json').get('intact')]", 1),
  ("load(BATCH4 / 'shift-lines/live-page-87/report.json')", "load(BATCH5 / 'shift-lines/live-page-88/report.json')", 1),
  ("load(BATCH4 / 'p1/final-87/report.json')", "load(BATCH5 / 'p1/final-88/report.json')", 1),
  ("    p4 = load(BATCH4 / 'p4/final-87/report.json')\n",
   "    p4 = load(BATCH5 / 'p4/final-88/report.json')\n    p5 = load(BATCH5 / 'p5/final-88/report.json')\n"
   "    p5_red = load(BATCH5 / 'p5/red-on-generation-87/report.json')\n", 1),
  ("        'P4-red-cases': (p4_reds, ['P4_RED', 'P4_RED', 'P4_RED']),\n",
   "        'P4-red-cases': (p4_reds, ['P4_RED', 'P4_RED', 'P4_RED']),\n        'P5': (p5.get('verdict'), 'P5_HOLDS'),\n"
   "        'P5-red-on-generation-87': (sorted({c['id'].split('/')[0] for r in p5_red['runs'] for c in r['checks'] if not c['pass']}), ['E1', 'E6', 'E7']),\n", 1),
  ("        'F3-87': (", "        'F3-88': (", 1),
  ("        'F3-87-self-test': (", "        'F3-88-self-test': (", 1),
  ("        'F3-87-no-cell-moved': (", "        'F3-88-no-cell-moved': (", 1),
  ("        'F4-87': ('PASS'", "        'F4-88': ('PASS'", 1),
  ("        'V0prime-87': (", "        'V0prime-88': (", 1),
  ("raise ValueError('live predecessor differs from clean 1b8c667 (0.2.51)')", "raise ValueError('live predecessor differs from clean c657aba (0.2.52)')", 1),
  ("if '<version>0.2.52</version>' not in", "if '<version>0.2.53</version>' not in", 1),
  ("    if want['profile'] != PROFILE or want['shell'].get('generation') != 87:\n        raise ValueError('identity module does not name e2-editor-v32 / generation 87')\n",
   "    if want['profile'] != PROFILE or want['shell'].get('generation') != 88:\n        raise ValueError('identity module does not name e2-editor-v32 / generation 88')\n", 1),
  ("raise ValueError('editor is not the verified generation-87 page')", "raise ValueError('editor is not the verified generation-88 page')", 1),
  ("raise ValueError('delta against 0.2.51 is not exactly the five files and the profile move: '", "raise ValueError('delta against 0.2.52 is not exactly e2-editor-app.js: '", 1),
  ("archive = SDK / 'build/archive' / ('host-0.2.52-engine-' + manifest['buildId'])", "archive = SDK / 'build/archive' / ('host-0.2.53-engine-' + manifest['buildId'])", 1),
  ("(archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.52 engine package\\n\\n'", "(archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.53 engine package\\n\\n'", 1),
  ("f'Host commit {candidate}, predecessor {parent} (0.2.51, exact 0.2.51 engine). Writer on profile e2-editor-v32, shell '",
   "f'Host commit {candidate}, predecessor {parent} (0.2.52, exact 0.2.52 engine). Writer on profile e2-editor-v32, shell '", 1),
  ("'generation 87, Calc on ods-editor-v3: the heading menu, list toggles, findings 180, 181, 182 (SPEC-P-demo-batch-4). Uncounted candidate.\\n')",
   "'generation 88, Calc on ods-editor-v3: Enter over a selection, the empty-copy sentence (SPEC-P-demo-batch-5). Uncounted candidate.\\n')", 1),
  ("release = {'version': '0.2.52',", "release = {'version': '0.2.53',", 1),
  ("'branch': 'host-0.2.52',", "'branch': 'host-0.2.53',", 1),
  ("'shellGeneration': 87,", "'shellGeneration': 88,", 1),
  ("this release links Writer anew and is read by its own gates, not counted", "this release changes the Writer page on the same engine and is read by its own gates, not counted", 1)],
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
