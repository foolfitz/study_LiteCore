#!/usr/bin/env python3
"""Derive host-0.2.47's scripts from host-0.2.46's (SPEC-P-demo-batch-1 append 1): each replacement must match its stated count;
the 0.2.46 files are not edited.  0.2.47 differs from 0.2.46 in `e2-editor.html` alone.
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[1]
OLD, NEW = EV / 'host-0.2.46', EV / 'host-0.2.47'
PLAN = {
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('only BUILD_ID rebound for candidate 0.2.46.', 'only BUILD_ID rebound for candidate 0.2.47.', 1),
  ('Derived from findings/evidence/host-0.2.45/offline-package-check.py (not edited), itself a copy of 0.2.44\'s, 0.2.43\'s,',
   'Derived from findings/evidence/host-0.2.46/offline-package-check.py (not edited), itself a copy of 0.2.45\'s, 0.2.44\'s, 0.2.43\'s,', 1),
  ('this docstring (0.2.45 -> 0.2.46 in its first line, and', 'this docstring (0.2.46 -> 0.2.47 in its first line, and', 1),
  ('rebinding; the 0.2.46 delta is judged', 'rebinding; the 0.2.47 delta is judged', 1)],
 ('capture-after.py', 'capture-after.py'): [
  ('"""Read the installed 0.2.46 identity', '"""Read the installed 0.2.47 identity', 1),
  ('Derived from findings/evidence/host-0.2.45/capture-after.py (not edited; itself a copy of 0.2.44\'s, 0.2.43\'s,',
   'Derived from findings/evidence/host-0.2.46/capture-after.py (not edited; itself a copy of 0.2.45\'s, 0.2.44\'s, 0.2.43\'s,', 1),
  ('code is 0.2.45\'s byte for byte.', 'code is 0.2.46\'s byte for byte.', 1)],
 ('install-0.2.46.py', 'install-0.2.47.py'): [
  ('"""Guarded 0.2.46 candidate install;', '"""Guarded 0.2.47 candidate install;', 1),
  ('Derived from findings/evidence/host-0.2.45/install-0.2.45.py (not edited).', 'Derived from findings/evidence/host-0.2.46/install-0.2.46.py (not edited).', 1),
  ('the isolated candidate path (build/host-0.2.45 -> build/host-0.2.46)', 'the isolated candidate path (build/host-0.2.46 -> build/host-0.2.47)', 1),
  ('names: host eeac22c (0.2.45)\nwith the exact 0.2.45 engine archive.', 'names: host b9d33d7 (0.2.46)\nwith the exact 0.2.46 engine archive.', 1),
  ("every other check below are 0.2.45's, unchanged.", "every other check below are 0.2.46's, unchanged.", 1),
  ("candidate = SDK / 'build/host-0.2.46/litecore'", "candidate = SDK / 'build/host-0.2.47/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('# Functional engine rollback to exact 0.2.45 bytes, preserving host label 0.2.46 (derived from host-0.2.45/rollback-package.sh, not edited).',
   '# Functional engine rollback to exact 0.2.46 bytes, preserving host label 0.2.47 (derived from host-0.2.46/rollback-package.sh, not edited).', 1),
  ('EVIDENCE host-0.2.45 -> host-0.2.46; the installer it loads (install-0.2.46.py,', 'EVIDENCE host-0.2.46 -> host-0.2.47; the installer it loads (install-0.2.47.py,', 1),
  ('# module name host046_install); the oldArchive assert names the exact 0.2.45 archive (host-0.2.45-engine-623f51d295ff6030);',
   '# module name host047_install); the oldArchive assert names the exact 0.2.46 archive (host-0.2.46-engine-99fd34739f4f68a9);', 1),
  ('# the message 0.2.45/0.2.46 -> 0.2.46/0.2.47', '# the message 0.2.46/0.2.47', 0),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.46', 'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.47', 1),
  ("spec_from_file_location('host046_install',out/'install-0.2.46.py')", "spec_from_file_location('host047_install',out/'install-0.2.47.py')", 1),
  ("host-0.2.45-engine-623f51d295ff6030')", "host-0.2.46-engine-99fd34739f4f68a9')", 1),
  ('Exact 0.2.45 engine restored; host label stays 0.2.46;', 'Exact 0.2.46 engine restored; host label stays 0.2.47;', 1)],
 ('check-delta.py', 'check-delta.py'): [
  ('"""SPEC-P-demo-batch-1 section 4: the 0.2.46 package differs from 0.2.45 in exactly the five page files of the batch, with no\n'
   'profile added, removed or changed -- read from the two archived MANIFEST.json files, not from prepare-release.py\'s own say-so.\n\n'
   'Derived from findings/evidence/host-0.2.45/check-delta.py (not edited).  Closed list of differences: the declared delta (five\n'
   'changed, nothing added or removed); the profile clauses are replaced by "no record under profiles/ differs and every page keeps\n'
   'its profile and wasm"; red cases: more, fewer, fewer_html, added and removed carried over, `fewer_calc` and `fewer_viewer` new,\n'
   'a profile file changed, a page moved to another profile.\n',
   '"""SPEC-P-demo-batch-1 append 1: the 0.2.47 package differs from 0.2.46 in exactly `e2-editor.html`, with no profile added,\n'
   'removed or changed -- read from the two archived MANIFEST.json files, not from prepare-release.py\'s own say-so.\n\n'
   'Derived from findings/evidence/host-0.2.46/check-delta.py (not edited).  Closed list of differences: this docstring; the declared\n'
   'delta, one record; the red cases that named the other four records are gone.\n', 1),
  ("DECLARED = ['e2-editor-app.js', 'e2-editor.html', 'ods-editor-app.js', 'ods-viewer-app.js',\n            'spreadsheet-shell/calc-editor-session.js']",
   "DECLARED = ['e2-editor.html']", 1),
  ("    def fewer_html(o, m):\n        m['files'][DECLARED[1]] = copy.deepcopy(o['files'][DECLARED[1]])\n\n"
   "    def fewer_calc(o, m):\n        m['files'][DECLARED[4]] = copy.deepcopy(o['files'][DECLARED[4]])\n\n"
   "    def fewer_viewer(o, m):\n        m['files'][DECLARED[3]] = copy.deepcopy(o['files'][DECLARED[3]])\n\n", "", 1),
  ("for fn in (more, fewer, fewer_html, fewer_calc, fewer_viewer, added, removed, profile_changed, page_moved):",
   "for fn in (more, fewer, added, removed, profile_changed, page_moved):", 1)],
 ('prepare-release.py', 'prepare-release.py'): [
  ('"""Package an isolated 0.2.46 host (Writer on profile e2-editor-v29, shell generation 84; the toolbar zoom and each sheet\'s own\n'
   'view) from current verified dist, preserving the live predecessor.\n\n'
   'Written by hand (SPEC-P-demo-batch-1 section 4).',
   '"""Package an isolated 0.2.47 host (0.2.46 with the desk\'s scrollbar gutter, SPEC-P-demo-batch-1 append 1) from current verified\n'
   'dist, preserving the live predecessor.\n\n'
   'Derived from findings/evidence/host-0.2.46/prepare-release.py (not edited).  Closed list of differences: this paragraph; the\n'
   'predecessor is host b9d33d7 (0.2.46) with the exact 0.2.46 engine, and the candidate is build/host-0.2.47; the delta is exactly\n'
   '`e2-editor.html`; the evidence gate reads the runs on the final HTML (writer-zoom run-02 and mutation-02-*, f4-84-final,\n'
   'f3-84-final, v0-02) and the Z10 red on 0.2.46; the viewer and Calc pages must now equal the predecessor\'s; the names.\n\n'
   '0.2.46\'s docstring follows.\n\n'
   'Written by hand (SPEC-P-demo-batch-1 section 4).', 1),
  ("APP = SDK / 'build/host-0.2.46/litecore'", "APP = SDK / 'build/host-0.2.47/litecore'", 1),
  ("PARENT = 'eeac22c'", "PARENT = 'b9d33d7'", 1),
  ("OLD = SDK / 'build/archive/host-0.2.45-engine-623f51d295ff6030'", "OLD = SDK / 'build/archive/host-0.2.46-engine-99fd34739f4f68a9'", 1),
  ("DECLARED_CHANGED = ['e2-editor-app.js', 'e2-editor.html', 'ods-editor-app.js', 'ods-viewer-app.js',\n                    'spreadsheet-shell/calc-editor-session.js']",
   "DECLARED_CHANGED = ['e2-editor.html']", 1),
  ("zoom = load(BATCH / 'writer-zoom/run-01/report.json')", "zoom = load(BATCH / 'writer-zoom/run-02/report.json')", 1),
  ("f4 = load(BATCH / 'f4-84/aggregate-judge.json')", "f4 = load(BATCH / 'f4-84-final/aggregate-judge.json')", 1),
  ("(BATCH / 'f3-84/equal.stdout.txt')", "(BATCH / 'f3-84-final/equal.stdout.txt')", 1),
  ("(BATCH / 'f3-84/equal-self-test.stdout.txt')", "(BATCH / 'f3-84-final/equal-self-test.stdout.txt')", 1),
  ("v0 = load(BATCH / 'v0/v0-prime.json')", "v0 = load(BATCH / 'v0-02/v0-prime.json')", 1),
  ("load(BATCH / 'v0/e1-c-after-put-back.json')", "load(BATCH / 'v0-02/e1-c-after-put-back.json')", 1),
  ("f'writer-zoom/mutation-{m}/report.json'", "f'writer-zoom/mutation-02-{m}/report.json'", 1),
  ("        'K-0.2.45': (k.get('verdict'), 'K_HOLDS'),\n",
   "        'K-0.2.45': (k.get('verdict'), 'K_HOLDS'),\n"
   "        'Z10-red-on-0.2.46': (sorted(c['id'] for r in z10_red['runs'] for c in r['checks'] if not c['pass']),\n"
   "                              ['Z10/fit-has-no-side-scroll', 'Z10/fit-returns-to-the-width-it-opened-at']),\n", 1),
  ("    calc = load(BATCH / 'calc-sheet-view/green-01/report.json')\n",
   "    calc = load(BATCH / 'calc-sheet-view/green-01/report.json')\n"
   "    z10_red = load(ROOT / 'findings/evidence/host-0.2.46/z10-red-on-0246/report.json')\n", 1),
  ("raise ValueError('live predecessor differs from clean eeac22c (0.2.45)')", "raise ValueError('live predecessor differs from clean b9d33d7 (0.2.46)')", 1),
  ("'<version>0.2.46</version>'", "'<version>0.2.47</version>'", 1),
  ("""        was, now = old['source']['pages'][html], pages[html]
        if {k: v for k, v in was.items() if k != 'moduleSha256'} != {k: v for k, v in now.items() if k != 'moduleSha256'}:
            raise ValueError('viewer/Calc profile or closure changed: ' + html)
        if now['moduleSha256'] != sha(SDK / module) or files[html] != old['files'][html]:
            raise ValueError('viewer/Calc module is not this tree, or its HTML moved: ' + html)
""", """        if pages[html] != old['source']['pages'][html] or files[html] != old['files'][html] \\
                or pages[html]['moduleSha256'] != sha(SDK / module):
            raise ValueError('viewer/Calc identity or HTML changed: ' + html)
""", 1),
  ("raise ValueError('delta against 0.2.45 is not exactly the five page files: '", "raise ValueError('delta against 0.2.46 is not exactly e2-editor.html: '", 1),
  ("('host-0.2.46-engine-' + manifest['buildId'])", "('host-0.2.47-engine-' + manifest['buildId'])", 1),
  ("'# Exact host 0.2.46 engine package\\n\\n'", "'# Exact host 0.2.47 engine package\\n\\n'", 1),
  ("f'Host commit {candidate}, predecessor {parent} (0.2.45, exact 0.2.45 engine). Writer on profile e2-editor-v29, shell '",
   "f'Host commit {candidate}, predecessor {parent} (0.2.46, exact 0.2.46 engine). Writer on profile e2-editor-v29, shell '", 1),
  ("'generation 84; the toolbar zoom and each sheet\\'s own view (SPEC-P-demo-batch-1). Uncounted candidate.\\n')",
   "'generation 84, with the desk\\'s scrollbar gutter (SPEC-P-demo-batch-1 append 1). Uncounted candidate.\\n')", 1),
  ("release = {'version': '0.2.46',", "release = {'version': '0.2.47',", 1),
  ("'branch': 'host-0.2.46',", "'branch': 'host-0.2.47',", 1)],
}
for (parent, child), replacements in PLAN.items():
    text = (OLD / parent).read_text(encoding='utf-8')
    for old, new, count in replacements:
        got = text.count(old)
        if got != count:
            raise SystemExit(f'{parent}: {old[:70]!r} occurs {got} times, expected {count}')
        text = text.replace(old, new)
    (NEW / child).write_text(text, encoding='utf-8')
    print(child, 'written')
