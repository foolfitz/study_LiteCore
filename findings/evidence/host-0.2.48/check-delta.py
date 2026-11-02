#!/usr/bin/env python3
"""SPEC-P-demo-batch-2: the 0.2.48 package differs from 0.2.47 in exactly `e2-editor.html` and `ods-editor.html`, with no profile
added, removed or changed -- read from the two archived MANIFEST.json files, not from prepare-release.py's own say-so.

Derived from findings/evidence/host-0.2.47/check-delta.py (not edited).  Closed list of differences: this docstring; the declared
delta, two records; one red case for the second record.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECLARED = ['e2-editor.html', 'ods-editor.html']


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
    for page, record in old['source']['pages'].items():
        now = new['source']['pages'].get(page, {})
        if (record['profile'], record.get('wasmSha256')) != (now.get('profile'), now.get('wasmSha256')):
            problems.append(f'{page} changed profile or wasm')
    return d, problems


def main():
    release = json.loads((HERE / 'release.json').read_bytes())
    old = json.loads((Path(release['oldArchive']) / 'MANIFEST.json').read_bytes())
    new = json.loads((Path(release['archive']) / 'MANIFEST.json').read_bytes())
    d, problems = judge(old, new)
    other = next(n for n in new['files'] if n not in DECLARED and not n.startswith('profiles/'))
    profile_file = next(n for n in new['files'] if n.startswith('profiles/') and n.endswith('probe.wasm'))

    def more(o, m):
        m['files'][other] = {**m['files'][other], 'sha256': '0' * 64}

    def fewer(o, m):
        m['files'][DECLARED[0]] = copy.deepcopy(o['files'][DECLARED[0]])

    def fewer_calc(o, m):
        m['files'][DECLARED[1]] = copy.deepcopy(o['files'][DECLARED[1]])

    def added(o, m):
        m['files']['profiles/e2-editor-v30/probe.wasm'] = {'sha256': '2' * 64}

    def removed(o, m):
        del m['files'][other]

    def profile_changed(o, m):
        m['files'][profile_file] = {**m['files'][profile_file], 'sha256': '3' * 64}

    def page_moved(o, m):
        m['source']['pages']['ods-editor.html']['profile'] = 'e2-editor-v29'

    reds = {}
    for fn in (more, fewer, fewer_calc, added, removed, profile_changed, page_moved):
        mutated_old, mutated = copy.deepcopy(old), copy.deepcopy(new)
        fn(mutated_old, mutated)
        reds[fn.__name__] = bool(judge(mutated_old, mutated)[1])
    holds = not problems and all(reds.values())
    print(json.dumps({'verdict': 'DELTA_HOLDS' if holds else 'DELTA_RED', 'oldBuildId': old['buildId'],
                      'buildId': new['buildId'], 'delta': d, 'problems': problems, 'redCases': reds}, indent=1))
    return 0 if holds else 1


if __name__ == '__main__':
    raise SystemExit(main())
