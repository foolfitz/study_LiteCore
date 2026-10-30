#!/usr/bin/env python3
"""Derive findings/evidence/host-0.2.44/'s five small scripts from host-0.2.43's (SPEC-M3-v28-last-line-fallback 7.4).
Each replacement must match its stated count; the 0.2.43 files are not edited.  prepare-release.py is derived by
derive_host_0244_prepare.py (its gate needs a hand-written v28 section).
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[2]
OLD, NEW = EV / 'host-0.2.43', EV / 'host-0.2.44'

PLAN = {
 ('check-delta.py', 'check-delta.py'): [
  ('''"""Spec v27 7.4: the 0.2.43 package differs from 0.2.42 in exactly the page, the four profiles/e2-editor-v27/ files
added and the four profiles/e2-editor-v26/ files removed, every added profile file differing from the removed one
(v27 is a relink) -- read from the two archived MANIFEST.json files, not from prepare-release.py's own say-so
(form two).

Derived from findings/evidence/host-0.2.42/check-delta.py (not edited).  Closed list of differences:
- the declared delta: changed = e2-editor-app.js only; added = profiles/e2-editor-v27/{probe.js, probe.wasm,
  sdk-manifest.json, sdk-worker.js}; removed = profiles/e2-editor-v26/{the same four};
- the successor clause: ALL FOUR added files must differ from the removed ones (0.2.42: probe.wasm and probe.js
  equal, the other two different) -- v27's probe.wasm equal to v26's would mean no new engine (spec 7.4 red case);
- the page clauses: old pages on e2-editor-v26 exactly e2-editor.html, no new page on it; the editor profile
  e2-editor-v26 -> e2-editor-v27;
- red cases: one more changed record, one fewer (the page reverted), an added record
  (profiles/e2-editor-v28/probe.wasm), a removed record, v27's probe.wasm equal to v26's (no new engine), v27's
  worker equal to v26's, another old page on e2-editor-v26, the new editor page still naming e2-editor-v26.''',
   '''"""Spec v28 7.4: the 0.2.44 package differs from 0.2.43 in exactly the page and the paragraph client, the four
profiles/e2-editor-v28/ files added and the four profiles/e2-editor-v27/ files removed, every added profile file
differing from the removed one (v28 is a relink) -- read from the two archived MANIFEST.json files, not from
prepare-release.py's own say-so (form two).

Derived from findings/evidence/host-0.2.43/check-delta.py (not edited).  Closed list of differences:
- the declared delta: changed = e2-editor-app.js and editor-shell-v2/paragraph-editor-client.js (spec v28 7.4,
  review item 20: 0.2.43's package carries the client); added = profiles/e2-editor-v28/{the four}; removed =
  profiles/e2-editor-v27/{the same four};
- v27 -> v28 and v26 -> v27 in the names and messages;
- red cases: 0.2.43's eight with the names moved on (the added record is profiles/e2-editor-v29/probe.wasm), plus
  one: the client reverted (`fewer_client`; `fewer` reverts the page).''', 1),
  ("PROFILE, OLD_PROFILE = 'e2-editor-v27', 'e2-editor-v26'", "PROFILE, OLD_PROFILE = 'e2-editor-v28', 'e2-editor-v27'", 1),
  ("DECLARED = ['e2-editor-app.js']", "DECLARED = ['e2-editor-app.js', 'editor-shell-v2/paragraph-editor-client.js']", 1),
  ("f'v27 {n} is not the removed v26 bytes'", "f'v28 {n} is not the removed v27 bytes'", 1),
  ("f'v27 {n} does not differ from v26'", "f'v28 {n} does not differ from v27'", 1),
  ("'editor profile is not e2-editor-v26 -> e2-editor-v27'", "'editor profile is not e2-editor-v27 -> e2-editor-v28'", 1),
  ("""    def added(o, m):
        m['files']['profiles/e2-editor-v28/probe.wasm'] = {'sha256': '2' * 64}""",
   """    def fewer_client(o, m):
        m['files'][DECLARED[1]] = copy.deepcopy(o['files'][DECLARED[1]])

    def added(o, m):
        m['files']['profiles/e2-editor-v29/probe.wasm'] = {'sha256': '2' * 64}""", 1),
  ("def other_page_on_v26(o, m):", "def other_page_on_v27(o, m):", 1),
  ("def editor_still_v26(o, m):", "def editor_still_v27(o, m):", 1),
  ("for fn in (more, fewer, added, removed, wasm_same, worker_same, other_page_on_v26, editor_still_v26):",
   "for fn in (more, fewer, fewer_client, added, removed, wasm_same, worker_same, other_page_on_v27, editor_still_v27):", 1),
 ],
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('''"""Existing K0/Z0/H5 package reader and its red cases, only BUILD_ID rebound for candidate 0.2.43.

Derived from findings/evidence/host-0.2.42/offline-package-check.py (not edited), itself a copy of 0.2.41's and
0.2.40's.  Closed list of differences: this docstring (0.2.42 -> 0.2.43 in its first line, and this derivation
note).  The reader has no profile names and no delta clause of its own (check_m3_assets' K0/Z0/H5 clauses are
profile-agnostic), so nothing else needs rebinding; the 0.2.43 delta is judged by prepare-release.py inline and by
check-delta.py from the two archived MANIFEST.json files.''',
   '''"""Existing K0/Z0/H5 package reader and its red cases, only BUILD_ID rebound for candidate 0.2.44.

Derived from findings/evidence/host-0.2.43/offline-package-check.py (not edited), itself a copy of 0.2.42's,
0.2.41's and 0.2.40's.  Closed list of differences: this docstring (0.2.43 -> 0.2.44 in its first line, and this
derivation note).  The reader has no profile names and no delta clause of its own (check_m3_assets' K0/Z0/H5
clauses are profile-agnostic), so nothing else needs rebinding; the 0.2.44 delta is judged by prepare-release.py
inline and by check-delta.py from the two archived MANIFEST.json files.''', 1)],
 ('install-0.2.43.py', 'install-0.2.44.py'): [
  ('''"""Guarded 0.2.43 candidate install; no service lifecycle, root command or global lock write.

Derived from findings/evidence/host-0.2.42/install-0.2.42.py (not edited).  Closed list of differences: the
version in this line, this paragraph and the isolated candidate path (build/host-0.2.42 -> build/host-0.2.43).
The live predecessor it verifies is whatever release.json names: host 93b1ebc (0.2.42) with the exact 0.2.42
engine archive (host-0.2.42-engine-01e6c3fb62626d16).  The slot it reads is this directory's slot.json
(findings/evidence/host-0.2.43/slot.json), with the same required fields as 0.2.42's: timezone-aware `start`
and `end` around now, `ownerNoSite: true`, `sharedDdevCoordinated: true`; and, read live, no running DDEV
project but litecore.  The preflight-only mode and every check below are 0.2.42's, unchanged.''',
   '''"""Guarded 0.2.44 candidate install; no service lifecycle, root command or global lock write.

Derived from findings/evidence/host-0.2.43/install-0.2.43.py (not edited).  Closed list of differences: the
version in this line, this paragraph and the isolated candidate path (build/host-0.2.43 -> build/host-0.2.44).
The live predecessor it verifies is whatever release.json names: host ae8240d (0.2.43) with the exact 0.2.43
engine archive (host-0.2.43-engine-741afd80a36e673b).  The slot it reads is this directory's slot.json
(findings/evidence/host-0.2.44/slot.json), with the same required fields as 0.2.43's: timezone-aware `start`
and `end` around now, `ownerNoSite: true`, `sharedDdevCoordinated: true`; and, read live, no running DDEV
project but litecore.  The preflight-only mode and every check below are 0.2.43's, unchanged.''', 1),
  ("candidate = SDK / 'build/host-0.2.43/litecore'", "candidate = SDK / 'build/host-0.2.44/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('''# Functional engine rollback to exact 0.2.42 bytes, preserving host label 0.2.43 (derived from host-0.2.42/rollback-package.sh, not edited).
# Closed list of differences: these comment lines; EVIDENCE host-0.2.42 -> host-0.2.43; the installer it loads (install-0.2.43.py,
# module name host043_install); the oldArchive assert names the exact 0.2.42 archive (host-0.2.42-engine-01e6c3fb62626d16);
# the message 0.2.41/0.2.42 -> 0.2.42/0.2.43.''',
   '''# Functional engine rollback to exact 0.2.43 bytes, preserving host label 0.2.44 (derived from host-0.2.43/rollback-package.sh, not edited).
# Closed list of differences: these comment lines; EVIDENCE host-0.2.43 -> host-0.2.44; the installer it loads (install-0.2.44.py,
# module name host044_install); the oldArchive assert names the exact 0.2.43 archive (host-0.2.43-engine-741afd80a36e673b);
# the message 0.2.42/0.2.43 -> 0.2.43/0.2.44.''', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.43',
   'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.44', 1),
  ("spec_from_file_location('host043_install',out/'install-0.2.43.py')",
   "spec_from_file_location('host044_install',out/'install-0.2.44.py')", 1),
  ("build/archive/host-0.2.42-engine-01e6c3fb62626d16", "build/archive/host-0.2.43-engine-741afd80a36e673b", 1),
  ("print('Exact 0.2.42 engine restored; host label stays 0.2.43; full K remains unestablished.')",
   "print('Exact 0.2.43 engine restored; host label stays 0.2.44; full K remains unestablished.')", 1)],
 ('capture-after.py', 'capture-after.py'): [
  ('''"""Read the installed 0.2.43 identity after the owned-document Files workflow run.

Derived from findings/evidence/host-0.2.42/capture-after.py (not edited; itself a copy of 0.2.41's, 0.2.40's and
0.2.39's).  Closed list of differences: the version in the first line and this paragraph; the code is 0.2.42's
byte for byte.

Inherited named limit (host-0.2.41/README.md, found by post-install-red/flipped-check-only-the-cell/; spec v27
7.4 keeps it):''',
   '''"""Read the installed 0.2.44 identity after the owned-document Files workflow run.

Derived from findings/evidence/host-0.2.43/capture-after.py (not edited; itself a copy of 0.2.42's, 0.2.41's,
0.2.40's and 0.2.39's).  Closed list of differences: the version in the first line and this paragraph; the code is
0.2.43's byte for byte.  0.2.43's named limit L-capture-after-expired-lock-lazily-deleted (host-0.2.43/README.md)
is inherited unchanged.

Inherited named limit (host-0.2.41/README.md, found by post-install-red/flipped-check-only-the-cell/; spec v28
7.4 keeps it):''', 1)],
}

for (src, dst), reps in PLAN.items():
    text = (OLD / src).read_text(encoding='utf-8')
    for old, new, count in reps:
        got = text.count(old)
        if got != count:
            raise SystemExit(f'{src}: {old[:70]!r} occurs {got} times, expected {count}')
        text = text.replace(old, new)
    (NEW / dst).write_text(text, encoding='utf-8')
    if dst.endswith('.sh'):
        (NEW / dst).chmod(0o755)
    print(dst, 'written')
