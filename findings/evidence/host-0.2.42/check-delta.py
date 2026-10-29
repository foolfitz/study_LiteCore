#!/usr/bin/env python3
"""Spec v26 5.9: the 0.2.42 package differs from 0.2.41 in exactly the three declared shell files, the four
profiles/e2-editor-v26/ files added and the four profiles/e2-editor-v25/ files removed, the added probe.wasm and
probe.js being the removed bytes -- read from the two archived MANIFEST.json files, not from prepare-release.py's
own say-so (form two).

Derived from findings/evidence/host-0.2.41/check-delta.py (not edited).  Closed list of differences:
- the declared delta: changed = e2-editor-app.js, editor-shell-v2/narrow-editor-v2-client.js,
  editor-shell-v2/narrow-editor-v2-session.js; added = profiles/e2-editor-v26/{probe.js, probe.wasm,
  sdk-manifest.json, sdk-worker.js}; removed = profiles/e2-editor-v25/{the same four} (0.2.41: two changed,
  nothing added or removed);
- new clauses: the added probe.wasm and probe.js equal the removed ones (sha256 and byte count); the added
  sdk-manifest.json and sdk-worker.js differ from the removed ones; the old package's pages on e2-editor-v25
  are exactly e2-editor.html (no other page loses its profile) and no page of the new package is on it;
- the editor-profile clause: old e2-editor-v25 -> new e2-editor-v26 (0.2.41: unchanged profile);
- red cases: one more changed record, one fewer, an added record (profiles/e2-editor-v27/probe.wasm, since
  0.2.41's added record is now declared), a removed record, the v26 probe.wasm differing from the removed v25
  one (replaces 0.2.41's "a changed profile file", which in 0.2.42 is the "one more" case), and one per new
  clause: the v26 probe.js differing, the v26 worker equal to v25's, another old page on e2-editor-v25, the
  new editor page still naming e2-editor-v25.
Read-only.  Exit 0 iff DELTA_HOLDS and every red case is red.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE, OLD_PROFILE = 'e2-editor-v26', 'e2-editor-v25'
PROFILE_FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
SAME_BYTES = ('probe.js', 'probe.wasm')
SUCCESSOR_FILES = ('sdk-manifest.json', 'sdk-worker.js')
DECLARED = ['e2-editor-app.js', 'editor-shell-v2/narrow-editor-v2-client.js',
            'editor-shell-v2/narrow-editor-v2-session.js']
ADDED = sorted(f'profiles/{PROFILE}/{n}' for n in PROFILE_FILES)
REMOVED = sorted(f'profiles/{OLD_PROFILE}/{n}' for n in PROFILE_FILES)


def delta(old, new):
    of, nf = old['files'], new['files']
    return {'changed': sorted(n for n in nf if n in of and of[n] != nf[n]),
            'added': sorted(set(nf) - set(of)), 'removed': sorted(set(of) - set(nf)),
            'same': sum(1 for n in nf if of.get(n) == nf[n])}


def judge(old, new):
    d = delta(old, new)
    problems = []
    if d['changed'] != DECLARED:
        problems.append(f"changed {d['changed']}")
    if d['added'] != ADDED or d['removed'] != REMOVED:
        problems.append(f"added {d['added']} removed {d['removed']}")
    if any(n.startswith('profiles/') for n in d['changed']):
        problems.append('a profile file changed')
    of, nf = old['files'], new['files']
    for n in SAME_BYTES:
        was, now = of.get(f'profiles/{OLD_PROFILE}/{n}', {}), nf.get(f'profiles/{PROFILE}/{n}', {})
        if not was.get('sha256') or (was.get('sha256'), was.get('bytes')) != (now.get('sha256'), now.get('bytes')):
            problems.append(f'v26 {n} is not the removed v25 bytes')
    for n in SUCCESSOR_FILES:
        was, now = of.get(f'profiles/{OLD_PROFILE}/{n}', {}), nf.get(f'profiles/{PROFILE}/{n}', {})
        if not now.get('sha256') or was.get('sha256') == now.get('sha256'):
            problems.append(f'v26 {n} does not differ from v25')
    on_old = sorted(h for h, p in old['source']['pages'].items() if p['profile'] == OLD_PROFILE)
    if on_old != ['e2-editor.html']:
        problems.append(f'old pages on {OLD_PROFILE}: {on_old}')
    if any(p['profile'] == OLD_PROFILE for p in new['source']['pages'].values()):
        problems.append(f'a new page is still on {OLD_PROFILE}')
    if (old['source']['pages']['e2-editor.html']['profile'], new['source']['pages']['e2-editor.html']['profile']) \
            != (OLD_PROFILE, PROFILE):
        problems.append('editor profile is not e2-editor-v25 -> e2-editor-v26')
    return d, problems


def main():
    release = json.loads((HERE / 'release.json').read_bytes())
    old = json.loads((Path(release['oldArchive']) / 'MANIFEST.json').read_bytes())
    new = json.loads((Path(release['archive']) / 'MANIFEST.json').read_bytes())
    d, problems = judge(old, new)
    other = next(n for n in new['files'] if n not in DECLARED and not n.startswith('profiles/'))

    def more(o, m):
        m['files'][other] = {**m['files'][other], 'sha256': '0' * 64}

    def fewer(o, m):
        m['files'][DECLARED[1]] = copy.deepcopy(o['files'][DECLARED[1]])

    def added(o, m):
        m['files']['profiles/e2-editor-v27/probe.wasm'] = {'sha256': '2' * 64}

    def removed(o, m):
        del m['files'][other]

    def wasm_differs(o, m):
        path = f'profiles/{PROFILE}/probe.wasm'
        m['files'][path] = {**m['files'][path], 'sha256': '1' * 64}

    def js_differs(o, m):
        path = f'profiles/{PROFILE}/probe.js'
        m['files'][path] = {**m['files'][path], 'sha256': '3' * 64}

    def worker_same(o, m):
        path = f'profiles/{PROFILE}/sdk-worker.js'
        m['files'][path] = {**m['files'][path], 'sha256': o['files'][f'profiles/{OLD_PROFILE}/sdk-worker.js']['sha256']}

    def other_page_on_v25(o, m):
        o['source']['pages']['ods-viewer.html']['profile'] = OLD_PROFILE

    def editor_still_v25(o, m):
        m['source']['pages']['e2-editor.html']['profile'] = OLD_PROFILE

    reds = {}
    for fn in (more, fewer, added, removed, wasm_differs, js_differs, worker_same, other_page_on_v25, editor_still_v25):
        mutated_old, mutated = copy.deepcopy(old), copy.deepcopy(new)
        fn(mutated_old, mutated)
        reds[fn.__name__] = bool(judge(mutated_old, mutated)[1])
    holds = not problems and all(reds.values())
    print(json.dumps({'verdict': 'DELTA_HOLDS' if holds else 'DELTA_RED', 'oldBuildId': old['buildId'],
                      'buildId': new['buildId'], 'delta': d, 'problems': problems, 'redCases': reds}, indent=1))
    return 0 if holds else 1


if __name__ == '__main__':
    raise SystemExit(main())
