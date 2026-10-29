#!/usr/bin/env python3
"""V0' for generation 80 (SPEC-M3-select-all-v26 5.7): the carried-over counts and the generation-79 readings
still re-read.

Derived from findings/evidence/shell-v79-173/v0/run_v0_prime.py (bound by its own committed result; not edited).
The differences are a closed list: this docstring; FOUR declared files instead of two (generation 80 changed the
page and the two narrow-editor-v2 files; the stages before 79 also need the older paragraph-editor-client); a
third stage, v79, that re-reads F4-79 with `judge_v79_product_four_arms.py`; the generation-79 B1 and F3-79
readings re-read twice (on the live tree and in stage v79); the four-arm readers' live reds recorded by this
script (v79's V0' recorded them by hand); the put-back target generation 80 and its bundle line; a refusal when
any output already exists (the readers open their --out exclusively, which would otherwise read as a red).

  stage v24  page b15a6d8e (git b241c83a4) + paragraph client 4616ae17 (git d14186167)  = generation 77
  stage v25  page 6e66c930 (git d14186167) + the same client                           = generation 78
  stage v79  page 9cb6ea1f + paragraph client 7d1c1eb2 (both git 9f084bf06)             = generation 79
  all three  narrow client 34378dec, narrow session a4cf3105 from git 9f084bf06 (unchanged 77-79)

The four-arm readers bind the live shell digest and are NOT_ESTABLISHED on the generation-80 tree by
construction; they are re-read in their stage, and their output must be byte-identical to the committed result,
with the argv that result was produced with (absolute run dirs).  The B1 self-test and the two F3-79 readers
read only files; they are read on the live tree AND in stage v79, byte-identical both times (spec 5.7 lists
them among the readers that go NE; this measures whether they do).  Put back in `finally` with
`git checkout HEAD --` and `make e2-c-assets`; then the four files must equal generation 80 in source and dist/,
the v80 bundle line must exit 0, and E1-C must be intact.  Writes only into this directory.  Must not run while
anything serves dist/.

Verdict V0_PRIME_HOLDS iff every re-read is byte-identical with exit 0, every four-arm live read is a red
(nonzero exit), every restore and the put-back hold.
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
NCLIENT, NSESSION = 'editor-shell-v2/narrow-editor-v2-client.js', 'editor-shell-v2/narrow-editor-v2-session.js'
FILES = (PAGE, CLIENT, NCLIENT, NSESSION)
DIST = {PAGE: 'dist/e2-editor-app.js', CLIENT: 'dist/editor-shell-v2/paragraph-editor-client.js',
        NCLIENT: 'dist/editor-shell-v2/narrow-editor-v2-client.js',
        NSESSION: 'dist/editor-shell-v2/narrow-editor-v2-session.js'}
NARROW = {NCLIENT: ('9f084bf06', '34378dec62df9b02af8d85616b038fc176d6c94fad268773bf77eb2d495b9a55'),
          NSESSION: ('9f084bf06', 'a4cf3105835fa57621e1d8afd9a4b9eb5dd44ccf35aa46a9cd5b475ac6746f0d')}
STAGES = {
    'v24': {PAGE: ('b241c83a4', 'b15a6d8e07b6a4f3e551f27971b7cfe8bec2cb743e5f6809013ca7f2082de669'),
            CLIENT: ('d14186167', '4616ae1715a57927fdf11aaf45004dfd4656bf3c816ee7cebeedd203c180a9c6'), **NARROW},
    'v25': {PAGE: ('d14186167', '6e66c930fe3d861903cfa6dfd16d000523298e934fae444385d4fe37d484c7cb'),
            CLIENT: ('d14186167', '4616ae1715a57927fdf11aaf45004dfd4656bf3c816ee7cebeedd203c180a9c6'), **NARROW},
    'v79': {PAGE: ('9f084bf06', '9cb6ea1f1d867c40284a917fcc89ec94175ec2ebf9fbd009334626f1e8685dd1'),
            CLIENT: ('9f084bf06', '7d1c1eb22e0baa7ad487d16d02eb0b2cc29ade3653679372bbf9e05b06e94396'), **NARROW},
}
V80 = {PAGE: '3b6c023ea3f8807ef28e2a031e2d49f24c9c08db4278392c4c0d7252bbc51f7b',
       CLIENT: '7d1c1eb22e0baa7ad487d16d02eb0b2cc29ade3653679372bbf9e05b06e94396',
       NCLIENT: '50f5a2acd5f34e1db42fc82a0cf8e1a75072e51f0fcc95e7f6e77da3fecd21d5',
       NSESSION: 'd037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0'}
A4 = EV / 'link-batch-v24/four-arms-counted-01'
F4_25 = EV / 'link-batch-v25/f4'
F4_79 = EV / 'shell-v79-173/f4'
V79 = EV / 'shell-v79-173'


def four_arm_argv(tool, runs, out, isolated=False):
    return ['python3'] + (['-I'] if isolated else []) + [tool, str(runs / 'chrome/report.v23-four-arms'),
                                                          str(runs / 'firefox/report.v23-four-arms'), '--out', str(out)]


FOUR_ARM = {  # name -> (argv builder, committed)
    'v24-a4': (lambda out: four_arm_argv('tools/judge_v24_product_four_arms.py', A4, out, isolated=True), A4 / 'aggregate-judge.json'),
    'v25-f4': (lambda out: four_arm_argv('tools/judge_v25_product_four_arms.py', F4_25, out), F4_25 / 'aggregate-judge.json'),
    'v79-f4': (lambda out: four_arm_argv('tools/judge_v79_product_four_arms.py', F4_79, out), F4_79 / 'aggregate-judge.json'),
}
FILE_READERS = {  # name -> (argv, committed); each prints its result on stdout
    'b1-self-test': (['python3', 'tools/check_v79_blank_bullet.py', '--self-test',
                      '../findings/evidence/shell-v79-173/b1/run-01/report.json'], V79 / 'b1/run-01/self-test.json'),
    'f3-79-read-01': (['python3', 'tools/read_v25_f3.py', '--v25', '../findings/evidence/shell-v79-173/f3/run-01'],
                      V79 / 'f3/read-01.json'),
    'f3-79-equal-01': (['python3', 'tools/read_v79_f3_equal.py', '--v79', '../findings/evidence/shell-v79-173/f3/run-01'],
                       V79 / 'f3/equal-01.json'),
}
OUTPUTS = ([HERE / f'live-red-{n}.json' for n in FOUR_ARM] + [HERE / f'live-{n}.json' for n in FILE_READERS]
           + [HERE / 'restored-v24-selection.json', HERE / 'restored-v24-a4.json', HERE / 'restored-v25-f4.json',
              HERE / 'restored-v79-f4.json'] + [HERE / f'restored-v79-{n}.json' for n in FILE_READERS]
           + [HERE / 'v0-prime.json', HERE / 'e1-c-after-put-back.json'])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv):
    started = time.monotonic()
    p = subprocess.run(argv, cwd=SDK, capture_output=True, text=True)
    return {'argv': argv, 'cwd': str(SDK), 'exit': p.returncode, 'seconds': round(time.monotonic() - started, 3),
            'stdout': p.stdout, 'stdoutTail': p.stdout[-2000:], 'stderrTail': p.stderr[-2000:]}


def slim(result):
    return {k: v for k, v in result.items() if k != 'stdout'}


def served():
    return {p: {'source': sha(SDK / p), 'dist': sha(SDK / DIST[p])} for p in FILES}


def restore(stage):
    for path, (commit, _) in STAGES[stage].items():
        (SDK / path).write_bytes(subprocess.check_output(['git', '-C', str(REPO), 'show', f'{commit}:wasm_sdk_probe/{path}']))
    make = run(['make', 'e2-c-assets'])
    hashes = served()
    ok = make['exit'] == 0 and all(hashes[p]['source'] == hashes[p]['dist'] == want for p, (_, want) in STAGES[stage].items())
    return {'make': slim(make), 'hashes': hashes, 'ok': ok}


def reread(argv, out, committed):
    result = slim(run(argv))
    result['byteIdentical'] = out.is_file() and out.read_bytes() == committed.read_bytes()
    result['committed'] = str(committed.relative_to(REPO))
    result['ok'] = result['exit'] == 0 and result['byteIdentical']
    return result


def reread_stdout(name, out):
    argv, committed = FILE_READERS[name]
    result = run(argv)
    out.write_text(result['stdout'])
    result = slim(result)
    result['byteIdentical'] = out.read_bytes() == committed.read_bytes()
    result['committed'] = str(committed.relative_to(REPO))
    result['ok'] = result['exit'] == 0 and result['byteIdentical']
    return result


def live_red(name):
    builder, committed = FOUR_ARM[name]
    out = HERE / f'live-red-{name}.json'
    result = slim(run(builder(out)))
    outcomes = None
    if out.is_file():
        outcomes = {k: v['outcome'] for k, v in json.loads(out.read_text())['arms'].items()}
    result['armOutcomes'] = outcomes
    result['committed'] = str(committed.relative_to(REPO))
    result['ok'] = result['exit'] != 0 and out.is_file() and all(v != 'PASS' for v in outcomes.values())
    return result


def main():
    present = [str(p.relative_to(REPO)) for p in OUTPUTS if p.exists()]
    if present:
        raise SystemExit('outputs already exist, refusing: ' + json.dumps(present))
    report = {'tool': str(Path(__file__).relative_to(REPO)), 'startedAt': time.time(), 'live': {}, 'stages': {}}
    if served() != {p: {'source': V80[p], 'dist': V80[p]} for p in V80}:
        raise SystemExit('the tree is not generation 80 before V0prime: ' + json.dumps(served()))
    try:
        for name in FOUR_ARM:
            report['live'][name] = live_red(name)
        for name in FILE_READERS:
            report['live'][name] = reread_stdout(name, HERE / f'live-{name}.json')
        stage = report['stages']['v24'] = {'restore': restore('v24')}
        if stage['restore']['ok']:
            stage['selection'] = reread([
                'python3', 'tools/read_v24_remaining_cohort.py',
                '--cohort', '../findings/evidence/link-batch-v24/remaining-counted-01/cohort.json',
                '--out', str(HERE / 'restored-v24-selection.json')],
                HERE / 'restored-v24-selection.json', EV / 'link-batch-v24/remaining-counted-01/completion-read-01.json')
            builder, committed = FOUR_ARM['v24-a4']
            stage['a4'] = reread(builder(HERE / 'restored-v24-a4.json'), HERE / 'restored-v24-a4.json', committed)
        stage = report['stages']['v25'] = {'restore': restore('v25')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v25-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v25-f4.json'), HERE / 'restored-v25-f4.json', committed)
        stage = report['stages']['v79'] = {'restore': restore('v79')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v79-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v79-f4.json'), HERE / 'restored-v79-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v79-{name}.json')
    finally:
        checkout = run(['git', '-C', str(REPO), 'checkout', 'HEAD', '--'] + [f'wasm_sdk_probe/{p}' for p in FILES])
        make = run(['make', 'e2-c-assets'])
        hashes = served()
        bundle = run(['python3', 'tools/build_e2_c_shell_bundle.py', '--manifest', 'e2/editor-shell-v2-bundle-v80.json'])
        e1c = run(['python3', 'tools/check_e1_c_bundle_intact.py'])
        (HERE / 'e1-c-after-put-back.json').write_text(e1c['stdout'] if e1c['exit'] == 0 else '{}')
        report['putBack'] = {'checkout': slim(checkout), 'make': slim(make), 'hashes': hashes,
                             'bundleLineV80': bundle['exit'], 'e1c': {'exit': e1c['exit']},
                             'ok': checkout['exit'] == 0 and make['exit'] == 0 and bundle['exit'] == 0 and e1c['exit'] == 0
                             and all(hashes[p]['source'] == hashes[p]['dist'] == V80[p] for p in V80)}
    stages = report['stages']
    rereads = [stages.get('v24', {}).get('selection'), stages.get('v24', {}).get('a4'),
               stages.get('v25', {}).get('f4'), stages.get('v79', {}).get('f4')]
    rereads += [stages.get('v79', {}).get(n) for n in FILE_READERS]
    live = [report['live'].get(n) for n in list(FOUR_ARM) + list(FILE_READERS)]
    holds = (all(r and r['ok'] for r in rereads + live) and report['putBack']['ok']
             and len(stages) == 3 and all(s['restore']['ok'] for s in stages.values()))
    report['verdict'] = 'V0_PRIME_HOLDS' if holds else 'V0_PRIME_RED'
    report['finishedAt'] = time.time()
    (HERE / 'v0-prime.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'])
    return 0 if holds else 1


if __name__ == '__main__':
    raise SystemExit(main())
