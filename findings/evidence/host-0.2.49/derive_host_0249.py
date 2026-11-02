#!/usr/bin/env python3
"""Derive host-0.2.49's scripts from host-0.2.48's (SPEC-P-demo-batch-2 append 2): each replacement must match its stated count; the
0.2.48 files are not edited.  0.2.49 differs from 0.2.48 in `ods-editor.html` alone.
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[1]
OLD, NEW = EV / 'host-0.2.48', EV / 'host-0.2.49'
A47, A48 = 'host-0.2.47-engine-268e3009dbf33a5a', 'host-0.2.48-engine-a632c4463e700493'
NAMES = [('0.2.48', '0.2.49', None)]
PLAN = {
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('only BUILD_ID rebound for candidate 0.2.48.', 'only BUILD_ID rebound for candidate 0.2.49.', 1),
  ('this docstring (0.2.47 -> 0.2.48 in its first line, and', 'this docstring (0.2.48 -> 0.2.49 in its first line, and', 1),
  ('rebinding; the 0.2.48 delta is judged', 'rebinding; the 0.2.49 delta is judged', 1)],
 ('capture-after.py', 'capture-after.py'): [('"""Read the installed 0.2.48 identity', '"""Read the installed 0.2.49 identity', 1)],
 ('install-0.2.48.py', 'install-0.2.49.py'): [
  ('"""Guarded 0.2.48 candidate install;', '"""Guarded 0.2.49 candidate install;', 1),
  ('names: host d6cbbd9 (0.2.47)\nwith the exact 0.2.47 engine archive.', 'names: host 0411329 (0.2.48)\nwith the exact 0.2.48 engine archive.', 1),
  ("candidate = SDK / 'build/host-0.2.48/litecore'", "candidate = SDK / 'build/host-0.2.49/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('# Functional engine rollback to exact 0.2.47 bytes, preserving host label 0.2.48', '# Functional engine rollback to exact 0.2.48 bytes, preserving host label 0.2.49', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.48', 'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.49', 1),
  ("spec_from_file_location('host048_install',out/'install-0.2.48.py')", "spec_from_file_location('host049_install',out/'install-0.2.49.py')", 1),
  (f"{A47}')", f"{A48}')", 1),
  ('Exact 0.2.47 engine restored; host label stays 0.2.48;', 'Exact 0.2.48 engine restored; host label stays 0.2.49;', 1)],
 ('check-delta.py', 'check-delta.py'): [
  ('"""SPEC-P-demo-batch-2: the 0.2.48 package differs from 0.2.47 in exactly `e2-editor.html` and `ods-editor.html`, with no profile\n',
   '"""SPEC-P-demo-batch-2 append 2: the 0.2.49 package differs from 0.2.48 in exactly `ods-editor.html`, with no profile\n', 1),
  ("DECLARED = ['e2-editor.html', 'ods-editor.html']", "DECLARED = ['ods-editor.html']", 1),
  ("    def fewer_calc(o, m):\n        m['files'][DECLARED[1]] = copy.deepcopy(o['files'][DECLARED[1]])\n\n", "", 1),
  ("for fn in (more, fewer, fewer_calc, added, removed, profile_changed, page_moved):", "for fn in (more, fewer, added, removed, profile_changed, page_moved):", 1)],
 ('prepare-release.py', 'prepare-release.py'): [
  ('"""Package an isolated 0.2.48 host (Save and Close where Collabora has them, SPEC-P-demo-batch-2) from current verified dist,\n',
   '"""Package an isolated 0.2.49 host (the whole Calc page light under any theme, SPEC-P-demo-batch-2 append 2) from current verified dist,\n', 1),
  ("APP = SDK / 'build/host-0.2.48/litecore'", "APP = SDK / 'build/host-0.2.49/litecore'", 1),
  ("PARENT = 'd6cbbd9'", "PARENT = '0411329'", 1),
  (f"OLD = SDK / 'build/archive/{A47}'", f"OLD = SDK / 'build/archive/{A48}'", 1),
  ("DECLARED_CHANGED = ['e2-editor.html', 'ods-editor.html']", "DECLARED_CHANGED = ['ods-editor.html']", 1),
  ("calc = load(BATCH2 / 'calc-sheet-view/run-01/report.json')", "calc = load(BATCH2 / 'calc-sheet-view/run-02/report.json')", 1),
  ("        'K-0.2.45': (k.get('verdict'), 'K_HOLDS'),\n",
   "        'K-0.2.45': (k.get('verdict'), 'K_HOLDS'),\n        'T6-red-on-0.2.48': (load(BATCH2 / 't6-red-on-0248/report.json').get('verdict'), 'T6_RED'),\n", 1),
  ("raise ValueError('live predecessor differs from clean d6cbbd9 (0.2.47)')", "raise ValueError('live predecessor differs from clean 0411329 (0.2.48)')", 1),
  ("'<version>0.2.48</version>'", "'<version>0.2.49</version>'", 1),
  ("!= ['appinfo/info.xml', 'templates/viewer.php']:\n        raise ValueError('candidate host source delta is not its version and the viewer bar')",
   "!= ['appinfo/info.xml']:\n        raise ValueError('candidate host source delta is not only its version')", 1),
  ("raise ValueError('delta against 0.2.47 is not exactly the two page HTML files: '", "raise ValueError('delta against 0.2.48 is not exactly ods-editor.html: '", 1),
  ("('host-0.2.48-engine-' + manifest['buildId'])", "('host-0.2.49-engine-' + manifest['buildId'])", 1),
  ("'# Exact host 0.2.48 engine package\\n\\n'", "'# Exact host 0.2.49 engine package\\n\\n'", 1),
  ("(0.2.47, exact 0.2.47 engine). Writer on profile", "(0.2.48, exact 0.2.48 engine). Writer on profile", 1),
  ("Save and Close where Collabora has them (SPEC-P-demo-batch-2). Uncounted candidate.", "the whole Calc page light under any theme (SPEC-P-demo-batch-2 append 2). Uncounted candidate.", 1),
  ("release = {'version': '0.2.48',", "release = {'version': '0.2.49',", 1),
  ("'branch': 'host-0.2.48',", "'branch': 'host-0.2.49',", 1)],
}
for (parent, child), replacements in PLAN.items():
    text = (OLD / parent).read_text(encoding='utf-8')
    for old, new, count in replacements:
        got = text.count(old)
        if got != count:
            raise SystemExit(f'{parent}: {old[:70]!r} occurs {got} times, expected {count}')
        text = text.replace(old, new)
    (NEW / child).write_text(text, encoding='utf-8')
print('derived')
