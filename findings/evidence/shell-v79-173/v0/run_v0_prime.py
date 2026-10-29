#!/usr/bin/env python3
"""V0' for generation 79 (SPEC-M3-shell-v79-finding-173 5.5): the carried-over counts still re-read.

Three readers bind the live shell digest and are therefore NOT_ESTABLISHED on the generation-79 tree by
construction: v24's `read_v24_remaining_cohort.py` and `judge_v24_product_four_arms.py` (generation 77) and
v25's `judge_v25_product_four_arms.py` (generation 78).  This time BOTH declared shell files are restored
(source and dist/, through `make e2-c-assets`), unlike the cutover's V0' which had one:

  stage v24  page b15a6d8e (git b241c83a4) + paragraph-editor-client.js 4616ae17 (git d14186167) = generation 77
  stage v25  page 6e66c930 (git d14186167) + the same client                                       = generation 78

Each reader's output must be byte-identical to its committed result, with the argv that result was produced
with (absolute run dirs).  Put back in `finally` with `git checkout HEAD --` and `make e2-c-assets`; then the
two files must equal generation 79's record in source and dist/, the v79 bundle line must exit 0, and E1-C
must be intact.  Writes only into this directory.  Must not run while anything serves dist/.

Verdict V0_PRIME_HOLDS iff all three are byte-identical with exit 0 and the put-back holds.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SDK = REPO / 'wasm_sdk_probe'
EV = REPO / 'findings/evidence'
PAGE, CLIENT = 'web/e2-editor-app.js', 'editor-shell-v2/paragraph-editor-client.js'
DIST = {PAGE: 'dist/e2-editor-app.js', CLIENT: 'dist/editor-shell-v2/paragraph-editor-client.js'}
STAGES = {
    'v24': {PAGE: ('b241c83a4', 'b15a6d8e07b6a4f3e551f27971b7cfe8bec2cb743e5f6809013ca7f2082de669'),
            CLIENT: ('d14186167', '4616ae1715a57927fdf11aaf45004dfd4656bf3c816ee7cebeedd203c180a9c6')},
    'v25': {PAGE: ('d14186167', '6e66c930fe3d861903cfa6dfd16d000523298e934fae444385d4fe37d484c7cb'),
            CLIENT: ('d14186167', '4616ae1715a57927fdf11aaf45004dfd4656bf3c816ee7cebeedd203c180a9c6')},
}
V79 = {PAGE: '9cb6ea1f1d867c40284a917fcc89ec94175ec2ebf9fbd009334626f1e8685dd1',
       CLIENT: '7d1c1eb22e0baa7ad487d16d02eb0b2cc29ade3653679372bbf9e05b06e94396'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv):
    started = time.monotonic()
    p = subprocess.run(argv, cwd=SDK, capture_output=True, text=True)
    return {'argv': argv, 'cwd': str(SDK), 'exit': p.returncode, 'seconds': round(time.monotonic() - started, 3),
            'stdoutTail': p.stdout[-2000:], 'stderrTail': p.stderr[-2000:]}


def served():
    return {p: {'source': sha(SDK / p), 'dist': sha(SDK / DIST[p])} for p in (PAGE, CLIENT)}


def restore(stage):
    for path, (commit, _) in STAGES[stage].items():
        (SDK / path).write_bytes(subprocess.check_output(['git', '-C', str(REPO), 'show', f'{commit}:wasm_sdk_probe/{path}']))
    make = run(['make', 'e2-c-assets'])
    hashes = served()
    ok = make['exit'] == 0 and all(hashes[p]['source'] == hashes[p]['dist'] == want for p, (_, want) in STAGES[stage].items())
    return {'make': make, 'hashes': hashes, 'ok': ok}


def reread(name, argv, out, committed):
    result = run(argv)
    result['byteIdentical'] = out.is_file() and out.read_bytes() == committed.read_bytes()
    result['committed'] = str(committed.relative_to(REPO))
    result['ok'] = result['exit'] == 0 and result['byteIdentical']
    return result


def main():
    report = {'tool': str(Path(__file__).relative_to(REPO)), 'startedAt': time.time(), 'stages': {}}
    if served() != {p: {'source': V79[p], 'dist': V79[p]} for p in V79}:
        raise SystemExit('the tree is not generation 79 before V0prime: ' + json.dumps(served()))
    try:
        stage = report['stages']['v24'] = {'restore': restore('v24')}
        if stage['restore']['ok']:
            stage['selection'] = reread('selection', [
                'python3', 'tools/read_v24_remaining_cohort.py',
                '--cohort', '../findings/evidence/link-batch-v24/remaining-counted-01/cohort.json',
                '--out', str(HERE / 'restored-v24-selection.json')],
                HERE / 'restored-v24-selection.json', EV / 'link-batch-v24/remaining-counted-01/completion-read-01.json')
            a4 = EV / 'link-batch-v24/four-arms-counted-01'
            stage['a4'] = reread('a4', [
                'python3', '-I', 'tools/judge_v24_product_four_arms.py',
                str(a4 / 'chrome/report.v23-four-arms'), str(a4 / 'firefox/report.v23-four-arms'),
                '--out', str(HERE / 'restored-v24-a4.json')],
                HERE / 'restored-v24-a4.json', a4 / 'aggregate-judge.json')
        stage = report['stages']['v25'] = {'restore': restore('v25')}
        if stage['restore']['ok']:
            f4 = EV / 'link-batch-v25/f4'
            stage['f4'] = reread('f4', [
                'python3', 'tools/judge_v25_product_four_arms.py',
                str(f4 / 'chrome/report.v23-four-arms'), str(f4 / 'firefox/report.v23-four-arms'),
                '--out', str(HERE / 'restored-v25-f4.json')],
                HERE / 'restored-v25-f4.json', f4 / 'aggregate-judge.json')
    finally:
        checkout = run(['git', '-C', str(REPO), 'checkout', 'HEAD', '--', f'wasm_sdk_probe/{PAGE}', f'wasm_sdk_probe/{CLIENT}'])
        make = run(['make', 'e2-c-assets'])
        hashes = served()
        bundle = run(['python3', 'tools/build_e2_c_shell_bundle.py', '--manifest', 'e2/editor-shell-v2-bundle-v79.json'])
        e1c = run(['python3', 'tools/check_e1_c_bundle_intact.py'])
        (HERE / 'e1-c-after-put-back.json').write_text(e1c['stdoutTail'] if e1c['exit'] == 0 else '{}')
        report['putBack'] = {'checkout': checkout, 'make': make, 'hashes': hashes, 'bundleLineV79': bundle['exit'],
                             'e1c': {'exit': e1c['exit']},
                             'ok': checkout['exit'] == 0 and make['exit'] == 0 and bundle['exit'] == 0 and e1c['exit'] == 0
                             and all(hashes[p]['source'] == hashes[p]['dist'] == V79[p] for p in V79)}
    rereads = [report['stages'].get('v24', {}).get('selection'), report['stages'].get('v24', {}).get('a4'),
               report['stages'].get('v25', {}).get('f4')]
    holds = all(r and r['ok'] for r in rereads) and report['putBack']['ok'] and all(
        s['restore']['ok'] for s in report['stages'].values())
    report['verdict'] = 'V0_PRIME_HOLDS' if holds else 'V0_PRIME_RED'
    report['finishedAt'] = time.time()
    (HERE / 'v0-prime.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'])
    return 0 if holds else 1


if __name__ == '__main__':
    raise SystemExit(main())
