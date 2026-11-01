#!/usr/bin/env python3
"""Spec v29 append 6: the 0.2.45 package differs from 0.2.44 in exactly the page and its HTML, the four
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
  refusal.
Read-only.  Exit 0 iff DELTA_HOLDS and every red case is red.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE, OLD_PROFILE = 'e2-editor-v29', 'e2-editor-v28'
PROFILE_FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
SAME_BYTES = ('sdk-worker.js',)
SUCCESSOR_FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json')
DECLARED = ['e2-editor-app.js', 'e2-editor.html']
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
            problems.append(f'v29 {n} is not the removed v28 bytes')
    for n in SUCCESSOR_FILES:
        was, now = of.get(f'profiles/{OLD_PROFILE}/{n}', {}), nf.get(f'profiles/{PROFILE}/{n}', {})
        if not now.get('sha256') or was.get('sha256') == now.get('sha256'):
            problems.append(f'v29 {n} does not differ from v28')
    on_old = sorted(h for h, p in old['source']['pages'].items() if p['profile'] == OLD_PROFILE)
    if on_old != ['e2-editor.html']:
        problems.append(f'old pages on {OLD_PROFILE}: {on_old}')
    if any(p['profile'] == OLD_PROFILE for p in new['source']['pages'].values()):
        problems.append(f'a new page is still on {OLD_PROFILE}')
    if (old['source']['pages']['e2-editor.html']['profile'], new['source']['pages']['e2-editor.html']['profile']) \
            != (OLD_PROFILE, PROFILE):
        problems.append('editor profile is not e2-editor-v28 -> e2-editor-v29')
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

    def fewer_html(o, m):
        m['files'][DECLARED[1]] = copy.deepcopy(o['files'][DECLARED[1]])

    def added(o, m):
        m['files']['profiles/e2-editor-v30/probe.wasm'] = {'sha256': '2' * 64}

    def removed(o, m):
        del m['files'][other]

    def wasm_same(o, m):
        path = f'profiles/{PROFILE}/probe.wasm'
        m['files'][path] = {**m['files'][path], 'sha256': o['files'][f'profiles/{OLD_PROFILE}/probe.wasm']['sha256']}

    def worker_moved(o, m):
        path = f'profiles/{PROFILE}/sdk-worker.js'
        m['files'][path] = {**m['files'][path], 'sha256': '3' * 64}

    def other_page_on_v28(o, m):
        o['source']['pages']['ods-viewer.html']['profile'] = OLD_PROFILE

    def editor_still_v28(o, m):
        m['source']['pages']['e2-editor.html']['profile'] = OLD_PROFILE

    reds = {}
    for fn in (more, fewer, fewer_html, added, removed, wasm_same, worker_moved, other_page_on_v28, editor_still_v28):
        mutated_old, mutated = copy.deepcopy(old), copy.deepcopy(new)
        fn(mutated_old, mutated)
        reds[fn.__name__] = bool(judge(mutated_old, mutated)[1])
    holds = not problems and all(reds.values())
    print(json.dumps({'verdict': 'DELTA_HOLDS' if holds else 'DELTA_RED', 'oldBuildId': old['buildId'],
                      'buildId': new['buildId'], 'delta': d, 'problems': problems, 'redCases': reds}, indent=1))
    return 0 if holds else 1


if __name__ == '__main__':
    raise SystemExit(main())
