#!/usr/bin/env python3
"""Spec v79 5.7: the 0.2.41 package differs from 0.2.40 in exactly the two declared shell files -- read from the
two archived MANIFEST.json files, not from prepare-release.py's own say-so (form two).

prepare-release.py refuses any other delta inline; this re-derives the delta from the produced artifacts and
shows each clause can turn red: one more changed record, one fewer, a changed profile file, an added and a
removed record.  Read-only.  Exit 0 iff DELTA_HOLDS and every red case is red.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECLARED = ['e2-editor-app.js', 'editor-shell-v2/paragraph-editor-client.js']


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
    if d['added'] or d['removed']:
        problems.append(f"added {d['added']} removed {d['removed']}")
    if any(n.startswith('profiles/') for n in d['changed']):
        problems.append('a profile file changed')
    page = new['source']['pages']['e2-editor.html']
    if page['profile'] != old['source']['pages']['e2-editor.html']['profile']:
        problems.append('editor profile changed')
    return d, problems


def main():
    release = json.loads((HERE / 'release.json').read_bytes())
    old = json.loads((Path(release['oldArchive']) / 'MANIFEST.json').read_bytes())
    new = json.loads((Path(release['archive']) / 'MANIFEST.json').read_bytes())
    d, problems = judge(old, new)
    profile = next(n for n in new['files'] if n.startswith('profiles/e2-editor-v25/'))
    other = next(n for n in new['files'] if n not in DECLARED and not n.startswith('profiles/'))

    def more(m):
        m['files'][other] = {**m['files'][other], 'sha256': '0' * 64}

    def fewer(m):
        m['files'][DECLARED[1]] = copy.deepcopy(old['files'][DECLARED[1]])

    def profile_changed(m):
        m['files'][profile] = {**m['files'][profile], 'sha256': '1' * 64}

    def added(m):
        m['files']['profiles/e2-editor-v26/probe.wasm'] = {'sha256': '2' * 64}

    def removed(m):
        del m['files'][other]

    reds = {}
    for fn in (more, fewer, profile_changed, added, removed):
        mutated = copy.deepcopy(new)
        fn(mutated)
        reds[fn.__name__] = bool(judge(old, mutated)[1])
    holds = not problems and all(reds.values())
    print(json.dumps({'verdict': 'DELTA_HOLDS' if holds else 'DELTA_RED', 'oldBuildId': old['buildId'],
                      'buildId': new['buildId'], 'delta': d, 'problems': problems, 'redCases': reds}, indent=1))
    return 0 if holds else 1


if __name__ == '__main__':
    raise SystemExit(main())
