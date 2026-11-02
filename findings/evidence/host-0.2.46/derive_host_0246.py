#!/usr/bin/env python3
"""Derive host-0.2.46's small scripts from host-0.2.45's (SPEC-P-demo-batch-1 section 4).  Each replacement must match its stated
count; the 0.2.45 files are not edited.  prepare-release.py is written by hand: nothing about its gate carries over except the
parent, and 0.2.45 is the counted parent.
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[1]
OLD, NEW = EV / 'host-0.2.45', EV / 'host-0.2.46'
PLAN = {
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('only BUILD_ID rebound for candidate 0.2.45.', 'only BUILD_ID rebound for candidate 0.2.46.', 1),
  ('Derived from findings/evidence/host-0.2.44/offline-package-check.py (not edited), itself a copy of 0.2.43\'s,',
   'Derived from findings/evidence/host-0.2.45/offline-package-check.py (not edited), itself a copy of 0.2.44\'s, 0.2.43\'s,', 1),
  ('this docstring (0.2.44 -> 0.2.45 in its first line, and', 'this docstring (0.2.45 -> 0.2.46 in its first line, and', 1),
  ('rebinding; the 0.2.45 delta is judged', 'rebinding; the 0.2.46 delta is judged', 1)],
 ('capture-after.py', 'capture-after.py'): [
  ('"""Read the installed 0.2.45 identity', '"""Read the installed 0.2.46 identity', 1),
  ('Derived from findings/evidence/host-0.2.44/capture-after.py (not edited; itself a copy of 0.2.43\'s,',
   'Derived from findings/evidence/host-0.2.45/capture-after.py (not edited; itself a copy of 0.2.44\'s, 0.2.43\'s,', 1),
  ('code is 0.2.44\'s byte for byte.', 'code is 0.2.45\'s byte for byte.', 1)],
 ('install-0.2.45.py', 'install-0.2.46.py'): [
  ('"""Guarded 0.2.45 candidate install;', '"""Guarded 0.2.46 candidate install;', 1),
  ('Derived from findings/evidence/host-0.2.44/install-0.2.44.py (not edited).  Closed list of differences: the\n'
   'version in this line, this paragraph, the isolated candidate path (build/host-0.2.44 -> build/host-0.2.45), and\n'
   'slot(): the owner slot existed because ddev was shared, and this host is the project\'s own stack\n'
   '(SPEC-M3-own-stack), so slot.json is gone and slot() checks that `ddev` is the adapter answering for the running\n'
   'litecore stack.  Run with host-stack/bin first on PATH.  The live predecessor it verifies is whatever release.json\n'
   'names: host a97724f (0.2.44) with the exact 0.2.44 engine archive (host-0.2.44-engine-dacdfa20fd4ff1ea).  The\n'
   'preflight-only mode and every other check below are 0.2.44\'s, unchanged.',
   'Derived from findings/evidence/host-0.2.45/install-0.2.45.py (not edited).  Closed list of differences: the\n'
   'version in this line, this paragraph, the isolated candidate path (build/host-0.2.45 -> build/host-0.2.46).  Run with\n'
   'host-stack/bin first on PATH.  The live predecessor it verifies is whatever release.json names: host eeac22c (0.2.45)\n'
   'with the exact 0.2.45 engine archive.  The preflight-only mode and every other check below are 0.2.45\'s, unchanged.', 1),
  ("candidate = SDK / 'build/host-0.2.45/litecore'", "candidate = SDK / 'build/host-0.2.46/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('# Functional engine rollback to exact 0.2.44 bytes, preserving host label 0.2.45 (derived from host-0.2.44/rollback-package.sh, not edited).',
   '# Functional engine rollback to exact 0.2.45 bytes, preserving host label 0.2.46 (derived from host-0.2.45/rollback-package.sh, not edited).', 1),
  ('# Closed list of differences: these comment lines; EVIDENCE host-0.2.44 -> host-0.2.45; the installer it loads (install-0.2.45.py,',
   '# Closed list of differences: these comment lines; EVIDENCE host-0.2.45 -> host-0.2.46; the installer it loads (install-0.2.46.py,', 1),
  ('# module name host045_install); the oldArchive assert names the exact 0.2.44 archive (host-0.2.44-engine-dacdfa20fd4ff1ea);',
   '# module name host046_install); the oldArchive assert names the exact 0.2.45 archive (host-0.2.45-engine-623f51d295ff6030);', 1),
  ('# the message 0.2.43/0.2.44 -> 0.2.44/0.2.45.', '# the message 0.2.44/0.2.45 -> 0.2.45/0.2.46.', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.45', 'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.46', 1),
  ("spec_from_file_location('host045_install',out/'install-0.2.45.py')", "spec_from_file_location('host046_install',out/'install-0.2.46.py')", 1),
  ("host-0.2.44-engine-dacdfa20fd4ff1ea')", "host-0.2.45-engine-623f51d295ff6030')", 1),
  ('Exact 0.2.44 engine restored; host label stays 0.2.45;', 'Exact 0.2.45 engine restored; host label stays 0.2.46;', 1)],
}
for (parent, child), replacements in PLAN.items():
    text = (OLD / parent).read_text(encoding='utf-8')
    for old, new, count in replacements:
        got = text.count(old)
        if got != count:
            raise SystemExit(f'{parent}: {old[:60]!r} occurs {got} times, expected {count}')
        text = text.replace(old, new)
    (NEW / child).write_text(text, encoding='utf-8')
    print(child, 'written')
