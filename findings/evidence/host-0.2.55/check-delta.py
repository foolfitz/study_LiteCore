#!/usr/bin/env python3
"""SPEC-P-calc-undo: the 0.2.55 package differs from 0.2.54 in exactly the Calc page's four files and the Calc profile's move from
ods-editor-v3 to ods-editor-v4 (six files each); Writer's profile files keep their bytes; every page but the Calc page keeps its profile
and wasm, and the Calc page has v4's -- read from the two archived MANIFEST.json files, not from prepare-release.py's own say-so.

Derived from findings/evidence/host-0.2.54/check-delta.py (not edited).  Closed list of differences: this docstring; the declared delta and
the profile move; the page clause wants v4 on the Calc page; the `fewer` red case is back and `calc_still_v3` is new.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECLARED = ['ods-editor-app.js', 'ods-editor.html', 'spreadsheet-shell/calc-document-sdk.js', 'spreadsheet-shell/calc-editor-session.js']
PROFILE = 'e2-editor-v32'
FILES = ('probe.js', 'probe.wasm', 'sdk-manifest.json', 'sdk-worker.js')
OLD_CALC, CALC = 'ods-editor-v3', 'ods-editor-v4'
PACKS = ('base-viewer-v3-no35.21bec6461a48d3ec.data', 'base-viewer-v3-no35.43da6a24481dc483.metadata')
ADDED = sorted(f'profiles/{CALC}/{n}' for n in FILES + PACKS)
REMOVED = sorted(f'profiles/{OLD_CALC}/{n}' for n in FILES + PACKS)
CALC_WASM = '9f37ed5a447bfc23db058b24e7a129087eab1c303e3c833e0de8e01bffd33b00'


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
    for n in FILES:
        was, now = of.get(f'profiles/{PROFILE}/{n}', {}), nf.get(f'profiles/{PROFILE}/{n}', {})
        if not now.get('sha256') or was.get('sha256') != now.get('sha256'):
            problems.append(f'{PROFILE} {n} moved')
    for page, record in old['source']['pages'].items():
        now = new['source']['pages'].get(page, {})
        want = (CALC, CALC_WASM) if page == 'ods-editor.html' else (record['profile'], record.get('wasmSha256'))
        if (now.get('profile'), now.get('wasmSha256')) != want:
            problems.append(f'{page} changed profile or wasm')
    return d, problems


def main():
    release = json.loads((HERE / 'release.json').read_bytes())
    old = json.loads((Path(release['oldArchive']) / 'MANIFEST.json').read_bytes())
    new = json.loads((Path(release['archive']) / 'MANIFEST.json').read_bytes())
    d, problems = judge(old, new)
    other = next(n for n in new['files'] if n not in DECLARED and not n.startswith('profiles/'))
    profile_file = next(n for n in new['files'] if n.startswith('profiles/ods-viewer') and n.endswith('probe.wasm'))

    def more(o, m):
        m['files'][other] = {**m['files'][other], 'sha256': '0' * 64}

    def fewer(o, m):
        m['files'][DECLARED[0]] = copy.deepcopy(o['files'][DECLARED[0]])

    def calc_still_v3(o, m):
        m['source']['pages']['ods-editor.html'] = copy.deepcopy(o['source']['pages']['ods-editor.html'])

    def added(o, m):
        m['files']['profiles/e2-editor-v33/probe.wasm'] = {'sha256': '2' * 64}

    def wasm_moved(o, m):
        m['files'][f'profiles/{PROFILE}/probe.wasm'] = {**m['files'][f'profiles/{PROFILE}/probe.wasm'], 'sha256': '4' * 64}

    def worker_moved(o, m):
        m['files'][f'profiles/{PROFILE}/sdk-worker.js'] = {**m['files'][f'profiles/{PROFILE}/sdk-worker.js'], 'sha256': '6' * 64}

    def writer_moved(o, m):
        m['source']['pages']['e2-editor.html']['wasmSha256'] = '7' * 64

    def calc_moved(o, m):
        m['source']['pages']['ods-editor.html']['wasmSha256'] = '5' * 64

    def removed(o, m):
        del m['files'][other]

    def profile_changed(o, m):
        m['files'][profile_file] = {**m['files'][profile_file], 'sha256': '3' * 64}

    def page_moved(o, m):
        m['source']['pages']['ods-editor.html']['profile'] = 'e2-editor-v29'

    reds = {}
    for fn in (more, fewer, calc_still_v3, added, removed, profile_changed, page_moved, wasm_moved, worker_moved, writer_moved, calc_moved):
        mutated_old, mutated = copy.deepcopy(old), copy.deepcopy(new)
        fn(mutated_old, mutated)
        reds[fn.__name__] = bool(judge(mutated_old, mutated)[1])
    holds = not problems and all(reds.values())
    print(json.dumps({'verdict': 'DELTA_HOLDS' if holds else 'DELTA_RED', 'oldBuildId': old['buildId'],
                      'buildId': new['buildId'], 'delta': d, 'problems': problems, 'redCases': reds}, indent=1))
    return 0 if holds else 1


if __name__ == '__main__':
    raise SystemExit(main())
