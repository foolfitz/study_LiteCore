#!/usr/bin/env python3
"""Derive findings/evidence/host-0.2.45/'s five small scripts from host-0.2.44's (SPEC-M3-v29-tick-pacing append 6).
Each replacement must match its stated count; the 0.2.44 files are not edited.  prepare-release.py is derived by
derive_host_0245_prepare.py (its gate needs a hand-written v29 section).
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[2]
OLD, NEW = EV / 'host-0.2.44', EV / 'host-0.2.45'

SLOT_OLD = '''def slot():
    record = json.loads((OUT / 'slot.json').read_bytes())
    now = datetime.datetime.now().astimezone()
    start, end = (datetime.datetime.fromisoformat(record[k]) for k in ('start', 'end'))
    if start.tzinfo is None or end.tzinfo is None or not start <= now < end:
        raise ValueError('owner slot is absent, not started or expired')
    if record.get('ownerNoSite') is not True or record.get('sharedDdevCoordinated') is not True:
        raise ValueError('owner no-site/shared-DDEV agreement not recorded')
    states = json.loads(command(['ddev', 'list', '-j']))['raw']
    busy = [p['name'] for p in states if p['status'] == 'running' and p['name'] != 'litecore']
    if busy or next(p['status'] for p in states if p['name'] == 'litecore') != 'running':
        raise ValueError('shared DDEV slot unavailable: ' + json.dumps(busy))
    return record, {p['name']: p['status'] for p in states}
'''
SLOT_NEW = '''def slot():
    # SPEC-M3-own-stack: the slot was there because ddev was shared.  What stays is that this is the stack it thinks it is;
    # without host-stack/bin first on PATH `ddev` is the real one, which lists other projects and this refuses.
    states = json.loads(command(['ddev', 'list', '-j']))['raw']
    if states != [{'name': 'litecore', 'status': 'running'}]:
        raise ValueError('not the own stack, or it is not running: ' + json.dumps(states))
    return {'ownStack': json.loads(command(['ddev', 'describe', '-j']))['raw']['primary_url']}, {p['name']: p['status'] for p in states}
'''

PLAN = {
 ('check-delta.py', 'check-delta.py'): [
  ('''"""Spec v28 7.4: the 0.2.44 package differs from 0.2.43 in exactly the page and the paragraph client, the four
profiles/e2-editor-v28/ files added and the four profiles/e2-editor-v27/ files removed, every added profile file
differing from the removed one (v28 is a relink) -- read from the two archived MANIFEST.json files, not from
prepare-release.py's own say-so (form two).

Derived from findings/evidence/host-0.2.43/check-delta.py (not edited).  Closed list of differences:
- the declared delta: changed = e2-editor-app.js and editor-shell-v2/paragraph-editor-client.js (spec v28 7.4,
  review item 20: 0.2.43's package carries the client); added = profiles/e2-editor-v28/{the four}; removed =
  profiles/e2-editor-v27/{the same four};
- v27 -> v28 and v26 -> v27 in the names and messages;
- red cases: 0.2.43's eight with the names moved on (the added record is profiles/e2-editor-v29/probe.wasm), plus
  one: the client reverted (`fewer_client`; `fewer` reverts the page).''',
   '''"""Spec v29 append 6: the 0.2.45 package differs from 0.2.44 in exactly the page and its HTML, the four
profiles/e2-editor-v29/ files added and the four profiles/e2-editor-v28/ files removed; the worker is v28's by bytes,
the other three differ -- read from the two archived MANIFEST.json files, not from prepare-release.py's own say-so
(form two).

Derived from findings/evidence/host-0.2.44/check-delta.py (not edited).  Closed list of differences:
- the declared delta: changed = e2-editor-app.js and e2-editor.html; added = profiles/e2-editor-v29/{the four};
  removed = profiles/e2-editor-v28/{the same four};
- SAME_BYTES = sdk-worker.js, SUCCESSOR_FILES = the other three (spec v29 2: the worker is v28's);
- v28 -> v29 and v27 -> v28 in the names and messages;
- red cases: 0.2.44's nine with the names moved on (the added record is profiles/e2-editor-v30/probe.wasm;
  `fewer_client` becomes `fewer_html`), and `worker_same` becomes `worker_moved`: v29's worker differing is now the
  refusal.''', 1),
  ("PROFILE, OLD_PROFILE = 'e2-editor-v28', 'e2-editor-v27'", "PROFILE, OLD_PROFILE = 'e2-editor-v29', 'e2-editor-v28'", 1),
  ("SAME_BYTES = ()\nSUCCESSOR_FILES = PROFILE_FILES", "SAME_BYTES = ('sdk-worker.js',)\nSUCCESSOR_FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json')", 1),
  ("DECLARED = ['e2-editor-app.js', 'editor-shell-v2/paragraph-editor-client.js']", "DECLARED = ['e2-editor-app.js', 'e2-editor.html']", 1),
  ("f'v28 {n} is not the removed v27 bytes'", "f'v29 {n} is not the removed v28 bytes'", 1),
  ("f'v28 {n} does not differ from v27'", "f'v29 {n} does not differ from v28'", 1),
  ("'editor profile is not e2-editor-v27 -> e2-editor-v28'", "'editor profile is not e2-editor-v28 -> e2-editor-v29'", 1),
  ("def fewer_client(o, m):", "def fewer_html(o, m):", 1),
  ("m['files']['profiles/e2-editor-v29/probe.wasm'] = {'sha256': '2' * 64}", "m['files']['profiles/e2-editor-v30/probe.wasm'] = {'sha256': '2' * 64}", 1),
  ("""    def worker_same(o, m):
        path = f'profiles/{PROFILE}/sdk-worker.js'
        m['files'][path] = {**m['files'][path], 'sha256': o['files'][f'profiles/{OLD_PROFILE}/sdk-worker.js']['sha256']}
""", """    def worker_moved(o, m):
        path = f'profiles/{PROFILE}/sdk-worker.js'
        m['files'][path] = {**m['files'][path], 'sha256': '3' * 64}
""", 1),
  ("def other_page_on_v27(o, m):", "def other_page_on_v28(o, m):", 1),
  ("def editor_still_v27(o, m):", "def editor_still_v28(o, m):", 1),
  ("for fn in (more, fewer, fewer_client, added, removed, wasm_same, worker_same, other_page_on_v27, editor_still_v27):",
   "for fn in (more, fewer, fewer_html, added, removed, wasm_same, worker_moved, other_page_on_v28, editor_still_v28):", 1),
 ],
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('''"""Existing K0/Z0/H5 package reader and its red cases, only BUILD_ID rebound for candidate 0.2.44.

Derived from findings/evidence/host-0.2.43/offline-package-check.py (not edited), itself a copy of 0.2.42's,
0.2.41's and 0.2.40's.  Closed list of differences: this docstring (0.2.43 -> 0.2.44 in its first line, and this
derivation note).  The reader has no profile names and no delta clause of its own (check_m3_assets' K0/Z0/H5
clauses are profile-agnostic), so nothing else needs rebinding; the 0.2.44 delta is judged by prepare-release.py
inline and by check-delta.py from the two archived MANIFEST.json files.''',
   '''"""Existing K0/Z0/H5 package reader and its red cases, only BUILD_ID rebound for candidate 0.2.45.

Derived from findings/evidence/host-0.2.44/offline-package-check.py (not edited), itself a copy of 0.2.43's,
0.2.42's, 0.2.41's and 0.2.40's.  Closed list of differences: this docstring (0.2.44 -> 0.2.45 in its first line, and
this derivation note).  The reader has no profile names and no delta clause of its own, so nothing else needs
rebinding; the 0.2.45 delta is judged by prepare-release.py inline and by check-delta.py from the two archived
MANIFEST.json files.''', 1)],
 ('install-0.2.44.py', 'install-0.2.45.py'): [
  ('''"""Guarded 0.2.44 candidate install; no service lifecycle, root command or global lock write.

Derived from findings/evidence/host-0.2.43/install-0.2.43.py (not edited).  Closed list of differences: the
version in this line, this paragraph and the isolated candidate path (build/host-0.2.43 -> build/host-0.2.44).
The live predecessor it verifies is whatever release.json names: host ae8240d (0.2.43) with the exact 0.2.43
engine archive (host-0.2.43-engine-741afd80a36e673b).  The slot it reads is this directory's slot.json
(findings/evidence/host-0.2.44/slot.json), with the same required fields as 0.2.43's: timezone-aware `start`
and `end` around now, `ownerNoSite: true`, `sharedDdevCoordinated: true`; and, read live, no running DDEV
project but litecore.  The preflight-only mode and every check below are 0.2.43's, unchanged.
''',
   '''"""Guarded 0.2.45 candidate install; no service lifecycle, root command or global lock write.

Derived from findings/evidence/host-0.2.44/install-0.2.44.py (not edited).  Closed list of differences: the
version in this line, this paragraph, the isolated candidate path (build/host-0.2.44 -> build/host-0.2.45), and
slot(): the owner slot existed because ddev was shared, and this host is the project's own stack
(SPEC-M3-own-stack), so slot.json is gone and slot() checks that `ddev` is the adapter answering for the running
litecore stack.  Run with host-stack/bin first on PATH.  The live predecessor it verifies is whatever release.json
names: host a97724f (0.2.44) with the exact 0.2.44 engine archive (host-0.2.44-engine-dacdfa20fd4ff1ea).  The
preflight-only mode and every other check below are 0.2.44's, unchanged.
''', 1),
  ("candidate = SDK / 'build/host-0.2.44/litecore'", "candidate = SDK / 'build/host-0.2.45/litecore'", 1),
  (SLOT_OLD, SLOT_NEW, 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('''# Functional engine rollback to exact 0.2.43 bytes, preserving host label 0.2.44 (derived from host-0.2.43/rollback-package.sh, not edited).
# Closed list of differences: these comment lines; EVIDENCE host-0.2.43 -> host-0.2.44; the installer it loads (install-0.2.44.py,
# module name host044_install); the oldArchive assert names the exact 0.2.43 archive (host-0.2.43-engine-741afd80a36e673b);
# the message 0.2.42/0.2.43 -> 0.2.43/0.2.44.
# Prepared only. Requires the owner-confirmed shared slot used by the install.''',
   '''# Functional engine rollback to exact 0.2.44 bytes, preserving host label 0.2.45 (derived from host-0.2.44/rollback-package.sh, not edited).
# Closed list of differences: these comment lines; EVIDENCE host-0.2.44 -> host-0.2.45; the installer it loads (install-0.2.45.py,
# module name host045_install); the oldArchive assert names the exact 0.2.44 archive (host-0.2.44-engine-dacdfa20fd4ff1ea);
# the message 0.2.43/0.2.44 -> 0.2.44/0.2.45.
# Prepared only. Run with host-stack/bin first on PATH (the installer's slot() checks it).''', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.44',
   'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.45', 1),
  ("spec_from_file_location('host044_install',out/'install-0.2.44.py')",
   "spec_from_file_location('host045_install',out/'install-0.2.45.py')", 1),
  ("build/archive/host-0.2.43-engine-741afd80a36e673b", "build/archive/host-0.2.44-engine-dacdfa20fd4ff1ea", 1),
  ("print('Exact 0.2.43 engine restored; host label stays 0.2.44; full K remains unestablished.')",
   "print('Exact 0.2.44 engine restored; host label stays 0.2.45; full K remains unestablished.')", 1)],
 ('capture-after.py', 'capture-after.py'): [
  ('''"""Read the installed 0.2.44 identity after the owned-document Files workflow run.

Derived from findings/evidence/host-0.2.43/capture-after.py (not edited; itself a copy of 0.2.42's, 0.2.41's,
0.2.40's and 0.2.39's).  Closed list of differences: the version in the first line and this paragraph; the code is
0.2.43's byte for byte.  0.2.43's named limit L-capture-after-expired-lock-lazily-deleted (host-0.2.43/README.md)
is inherited unchanged.
''',
   '''"""Read the installed 0.2.45 identity after the owned-document Files workflow run.

Derived from findings/evidence/host-0.2.44/capture-after.py (not edited; itself a copy of 0.2.43's, 0.2.42's,
0.2.41's, 0.2.40's and 0.2.39's).  Closed list of differences: the version in the first line and this paragraph; the
code is 0.2.44's byte for byte.  Run with host-stack/bin first on PATH.  0.2.43's named limit
L-capture-after-expired-lock-lazily-deleted (host-0.2.43/README.md) is inherited unchanged.
''', 1)],
}

for (src, dst), reps in PLAN.items():
    text = (OLD / src).read_text(encoding='utf-8')
    for old, new, count in reps:
        got = text.count(old)
        if got != count:
            raise SystemExit(f'{src}: {old[:70]!r} occurs {got} times, expected {count}')
        text = text.replace(old, new)
    if dst.endswith('.py'):
        compile(text, dst, 'exec')
    (NEW / dst).write_text(text, encoding='utf-8')
    if dst.endswith('.sh'):
        (NEW / dst).chmod(0o755)
    print(dst, 'written')
