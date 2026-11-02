#!/usr/bin/env python3
"""Derive host-0.2.48's scripts from host-0.2.47's (SPEC-P-demo-batch-2): each replacement must match its stated count; the 0.2.47
files are not edited.  0.2.48 differs from 0.2.47 in `e2-editor.html` and `ods-editor.html`, and on the host side in
`templates/viewer.php` (spec append 1).
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[1]
OLD, NEW = EV / 'host-0.2.47', EV / 'host-0.2.48'
ARCHIVE_47 = 'host-0.2.47-engine-268e3009dbf33a5a'
ARCHIVE_46 = 'host-0.2.46-engine-99fd34739f4f68a9'
PLAN = {
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('only BUILD_ID rebound for candidate 0.2.47.', 'only BUILD_ID rebound for candidate 0.2.48.', 1),
  ("Derived from findings/evidence/host-0.2.46/offline-package-check.py (not edited), itself a copy of 0.2.45's,",
   "Derived from findings/evidence/host-0.2.47/offline-package-check.py (not edited), itself a copy of 0.2.46's, 0.2.45's,", 1),
  ('this docstring (0.2.46 -> 0.2.47 in its first line, and', 'this docstring (0.2.47 -> 0.2.48 in its first line, and', 1),
  ('rebinding; the 0.2.47 delta is judged', 'rebinding; the 0.2.48 delta is judged', 1)],
 ('capture-after.py', 'capture-after.py'): [
  ('"""Read the installed 0.2.47 identity', '"""Read the installed 0.2.48 identity', 1),
  ("Derived from findings/evidence/host-0.2.46/capture-after.py (not edited; itself a copy of 0.2.45's,",
   "Derived from findings/evidence/host-0.2.47/capture-after.py (not edited; itself a copy of 0.2.46's, 0.2.45's,", 1),
  ("code is 0.2.46's byte for byte.", "code is 0.2.47's byte for byte.", 1)],
 ('install-0.2.47.py', 'install-0.2.48.py'): [
  ('"""Guarded 0.2.47 candidate install;', '"""Guarded 0.2.48 candidate install;', 1),
  ('Derived from findings/evidence/host-0.2.46/install-0.2.46.py (not edited).', 'Derived from findings/evidence/host-0.2.47/install-0.2.47.py (not edited).', 1),
  ('the isolated candidate path (build/host-0.2.46 -> build/host-0.2.47)', 'the isolated candidate path (build/host-0.2.47 -> build/host-0.2.48)', 1),
  ('names: host b9d33d7 (0.2.46)\nwith the exact 0.2.46 engine archive.', 'names: host d6cbbd9 (0.2.47)\nwith the exact 0.2.47 engine archive.', 1),
  ("every other check below are 0.2.46's, unchanged.", "every other check below are 0.2.47's, unchanged.", 1),
  ("candidate = SDK / 'build/host-0.2.47/litecore'", "candidate = SDK / 'build/host-0.2.48/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('# Functional engine rollback to exact 0.2.46 bytes, preserving host label 0.2.47 (derived from host-0.2.46/rollback-package.sh, not edited).',
   '# Functional engine rollback to exact 0.2.47 bytes, preserving host label 0.2.48 (derived from host-0.2.47/rollback-package.sh, not edited).', 1),
  ('EVIDENCE host-0.2.46 -> host-0.2.47; the installer it loads (install-0.2.47.py,', 'EVIDENCE host-0.2.47 -> host-0.2.48; the installer it loads (install-0.2.48.py,', 1),
  (f'# module name host047_install); the oldArchive assert names the exact 0.2.46 archive ({ARCHIVE_46});',
   f'# module name host048_install); the oldArchive assert names the exact 0.2.47 archive ({ARCHIVE_47});', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.47', 'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.48', 1),
  ("spec_from_file_location('host047_install',out/'install-0.2.47.py')", "spec_from_file_location('host048_install',out/'install-0.2.48.py')", 1),
  (f"{ARCHIVE_46}')", f"{ARCHIVE_47}')", 1),
  ('Exact 0.2.46 engine restored; host label stays 0.2.47;', 'Exact 0.2.47 engine restored; host label stays 0.2.48;', 1)],
 ('check-delta.py', 'check-delta.py'): [
  ('"""SPEC-P-demo-batch-1 append 1: the 0.2.47 package differs from 0.2.46 in exactly `e2-editor.html`, with no profile added,\n'
   "removed or changed -- read from the two archived MANIFEST.json files, not from prepare-release.py's own say-so.\n\n"
   'Derived from findings/evidence/host-0.2.46/check-delta.py (not edited).  Closed list of differences: this docstring; the declared\n'
   'delta, one record; the red cases that named the other four records are gone.\n',
   '"""SPEC-P-demo-batch-2: the 0.2.48 package differs from 0.2.47 in exactly `e2-editor.html` and `ods-editor.html`, with no profile\n'
   "added, removed or changed -- read from the two archived MANIFEST.json files, not from prepare-release.py's own say-so.\n\n"
   'Derived from findings/evidence/host-0.2.47/check-delta.py (not edited).  Closed list of differences: this docstring; the declared\n'
   'delta, two records; one red case for the second record.\n', 1),
  ("DECLARED = ['e2-editor.html']", "DECLARED = ['e2-editor.html', 'ods-editor.html']", 1),
  ("    def added(o, m):\n", "    def fewer_calc(o, m):\n        m['files'][DECLARED[1]] = copy.deepcopy(o['files'][DECLARED[1]])\n\n    def added(o, m):\n", 1),
  ("for fn in (more, fewer, added, removed, profile_changed, page_moved):", "for fn in (more, fewer, fewer_calc, added, removed, profile_changed, page_moved):", 1)],
 ('prepare-release.py', 'prepare-release.py'): [
  ('"""Package an isolated 0.2.47 host (0.2.46 with the desk\'s scrollbar gutter, SPEC-P-demo-batch-1 append 1) from current verified\n'
   'dist, preserving the live predecessor.\n\n'
   'Derived from findings/evidence/host-0.2.46/prepare-release.py (not edited).  Closed list of differences: this paragraph; the\n',
   '"""Package an isolated 0.2.48 host (Save and Close where Collabora has them, SPEC-P-demo-batch-2) from current verified dist,\n'
   'preserving the live predecessor.\n\n'
   'Derived from findings/evidence/host-0.2.47/prepare-release.py (not edited).  Closed list of differences: this paragraph; the\n'
   'predecessor is host d6cbbd9 (0.2.47) with the exact 0.2.47 engine, and the candidate is build/host-0.2.48; the host source delta\n'
   'adds templates/viewer.php; the delta is exactly `e2-editor.html` and `ods-editor.html`; the evidence gate reads the runs on these\n'
   'two pages under demo-batch-2 and the layout red on 0.2.47, the zoom mutations and the Calc red stay demo-batch-1\'s; the Calc page\'s\n'
   'HTML may move, the viewer\'s may not; the names.\n\n'
   '0.2.47\'s docstring follows.\n\n'
   'Derived from findings/evidence/host-0.2.46/prepare-release.py (not edited).  Closed list of differences: that paragraph; the\n', 1),
  ("APP = SDK / 'build/host-0.2.47/litecore'", "APP = SDK / 'build/host-0.2.48/litecore'", 1),
  ("PARENT = 'b9d33d7'", "PARENT = 'd6cbbd9'", 1),
  (f"OLD = SDK / 'build/archive/{ARCHIVE_46}'", f"OLD = SDK / 'build/archive/{ARCHIVE_47}'", 1),
  ("DECLARED_CHANGED = ['e2-editor.html']", "DECLARED_CHANGED = ['e2-editor.html', 'ods-editor.html']", 1),
  ("BATCH = ROOT / 'findings/evidence/demo-batch-1'\n", "BATCH = ROOT / 'findings/evidence/demo-batch-1'\nBATCH2 = ROOT / 'findings/evidence/demo-batch-2'\n", 1),
  ("calc = load(BATCH / 'calc-sheet-view/green-01/report.json')", "calc = load(BATCH2 / 'calc-sheet-view/run-01/report.json')", 1),
  ("zoom = load(BATCH / 'writer-zoom/run-02/report.json')", "zoom = load(BATCH2 / 'writer-zoom/run-01/report.json')", 1),
  ("f4 = load(BATCH / 'f4-84-final/aggregate-judge.json')", "f4 = load(BATCH2 / 'f4-84/aggregate-judge.json')", 1),
  ("(BATCH / 'f3-84-final/equal.stdout.txt')", "(BATCH2 / 'f3-84/equal.stdout.txt')", 1),
  ("(BATCH / 'f3-84-final/equal-self-test.stdout.txt')", "(BATCH2 / 'f3-84/equal-self-test.stdout.txt')", 1),
  ("v0 = load(BATCH / 'v0-02/v0-prime.json')", "v0 = load(BATCH2 / 'v0/v0-prime.json')", 1),
  ("load(BATCH / 'v0-02/e1-c-after-put-back.json')", "load(BATCH2 / 'v0/e1-c-after-put-back.json')", 1),
  ("    z10_red = load(ROOT / 'findings/evidence/host-0.2.46/z10-red-on-0246/report.json')\n",
   "    z10_red = load(ROOT / 'findings/evidence/host-0.2.46/z10-red-on-0246/report.json')\n"
   "    layout_red = load(BATCH2 / 'red-on-0247/report.json')\n", 1),
  ("        'K-0.2.45': (k.get('verdict'), 'K_HOLDS'),\n",
   "        'K-0.2.45': (k.get('verdict'), 'K_HOLDS'),\n"
   "        'Layout-red-on-0.2.47': (all(i in {c['id'] for r in layout_red['runs'] for c in r['checks'] if not c['pass']}\n"
   "                                     for i in ('T1/close-right-gap-equal', 'T2/save-is-first', 'T4/writer-contrast')), True),\n", 1),
  ("raise ValueError('live predecessor differs from clean b9d33d7 (0.2.46)')", "raise ValueError('live predecessor differs from clean d6cbbd9 (0.2.47)')", 1),
  ("'<version>0.2.47</version>'", "'<version>0.2.48</version>'", 1),
  ("if git(APP, 'diff', '--name-only', parent, candidate).splitlines() != ['appinfo/info.xml']:\n        raise ValueError('candidate host source delta is not only its version')",
   "if git(APP, 'diff', '--name-only', parent, candidate).splitlines() != ['appinfo/info.xml', 'templates/viewer.php']:\n        raise ValueError('candidate host source delta is not its version and the viewer bar')", 1),
  ("""        if pages[html] != old['source']['pages'][html] or files[html] != old['files'][html] \\
                or pages[html]['moduleSha256'] != sha(SDK / module):
            raise ValueError('viewer/Calc identity or HTML changed: ' + html)
""", """        if pages[html] != old['source']['pages'][html] or pages[html]['moduleSha256'] != sha(SDK / module) \\
                or (html == 'ods-viewer.html' and files[html] != old['files'][html]):
            raise ValueError('viewer/Calc identity changed, or the viewer HTML moved: ' + html)
""", 1),
  ("raise ValueError('delta against 0.2.46 is not exactly e2-editor.html: '", "raise ValueError('delta against 0.2.47 is not exactly the two page HTML files: '", 1),
  ("('host-0.2.47-engine-' + manifest['buildId'])", "('host-0.2.48-engine-' + manifest['buildId'])", 1),
  ("'# Exact host 0.2.47 engine package\\n\\n'", "'# Exact host 0.2.48 engine package\\n\\n'", 1),
  ("(0.2.46, exact 0.2.46 engine). Writer on profile", "(0.2.47, exact 0.2.47 engine). Writer on profile", 1),
  ("'generation 84, with the desk\\'s scrollbar gutter (SPEC-P-demo-batch-1 append 1). Uncounted candidate.\\n')",
   "'generation 84; Save and Close where Collabora has them (SPEC-P-demo-batch-2). Uncounted candidate.\\n')", 1),
  ("release = {'version': '0.2.47',", "release = {'version': '0.2.48',", 1),
  ("'branch': 'host-0.2.47',", "'branch': 'host-0.2.48',", 1)],
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
