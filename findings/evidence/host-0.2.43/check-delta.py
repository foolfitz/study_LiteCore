#!/usr/bin/env python3
"""Spec v27 7.4: the 0.2.43 package differs from 0.2.42 in exactly the page, the four profiles/e2-editor-v27/ files
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
  worker equal to v26's, another old page on e2-editor-v26, the new editor page still naming e2-editor-v26.
Read-only.  Exit 0 iff DELTA_HOLDS and every red case is red.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE, OLD_PROFILE = 'e2-editor-v27', 'e2-editor-v26'
PROFILE_FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
SAME_BYTES = ()
SUCCESSOR_FILES = PROFILE_FILES
DECLARED = ['e2-editor-app.js']
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
            problems.append(f'v27 {n} is not the removed v26 bytes')
    for n in SUCCESSOR_FILES:
        was, now = of.get(f'profiles/{OLD_PROFILE}/{n}', {}), nf.get(f'profiles/{PROFILE}/{n}', {})
        if not now.get('sha256') or was.get('sha256') == now.get('sha256'):
            problems.append(f'v27 {n} does not differ from v26')
    on_old = sorted(h for h, p in old['source']['pages'].items() if p['profile'] == OLD_PROFILE)
    if on_old != ['e2-editor.html']:
        problems.append(f'old pages on {OLD_PROFILE}: {on_old}')
    if any(p['profile'] == OLD_PROFILE for p in new['source']['pages'].values()):
        problems.append(f'a new page is still on {OLD_PROFILE}')
    if (old['source']['pages']['e2-editor.html']['profile'], new['source']['pages']['e2-editor.html']['profile']) \
            != (OLD_PROFILE, PROFILE):
        problems.append('editor profile is not e2-editor-v26 -> e2-editor-v27')
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
        m['files'][DECLARED[0]] = copy.deepcopy(o['files'][DECLARED[0]])

    def added(o, m):
        m['files']['profiles/e2-editor-v28/probe.wasm'] = {'sha256': '2' * 64}

    def removed(o, m):
        del m['files'][other]

    def wasm_same(o, m):
        path = f'profiles/{PROFILE}/probe.wasm'
        m['files'][path] = {**m['files'][path], 'sha256': o['files'][f'profiles/{OLD_PROFILE}/probe.wasm']['sha256']}

    def worker_same(o, m):
        path = f'profiles/{PROFILE}/sdk-worker.js'
        m['files'][path] = {**m['files'][path], 'sha256': o['files'][f'profiles/{OLD_PROFILE}/sdk-worker.js']['sha256']}

    def other_page_on_v26(o, m):
        o['source']['pages']['ods-viewer.html']['profile'] = OLD_PROFILE

    def editor_still_v26(o, m):
        m['source']['pages']['e2-editor.html']['profile'] = OLD_PROFILE

    reds = {}
    for fn in (more, fewer, added, removed, wasm_same, worker_same, other_page_on_v26, editor_still_v26):
        mutated_old, mutated = copy.deepcopy(old), copy.deepcopy(new)
        fn(mutated_old, mutated)
        reds[fn.__name__] = bool(judge(mutated_old, mutated)[1])
    holds = not problems and all(reds.values())
    print(json.dumps({'verdict': 'DELTA_HOLDS' if holds else 'DELTA_RED', 'oldBuildId': old['buildId'],
                      'buildId': new['buildId'], 'delta': d, 'problems': problems, 'redCases': reds}, indent=1))
    return 0 if holds else 1


if __name__ == '__main__':
    raise SystemExit(main())
