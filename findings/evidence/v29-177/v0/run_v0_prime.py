#!/usr/bin/env python3
"""V0' for generation 83 (SPEC-M3-v29-tick-pacing section 6 T3): the carried-over counts and the generation-79, -80, -81 and
-82 readings still re-read.

Derived from findings/evidence/v28-083/v0/run_v0_prime.py (bound by its own committed result; not edited) by
../derive/derive_v0_prime.py.  The differences are a closed list: this docstring; a sixth stage, v82 (the four files of
generation 82, all from git 69c5583a9), which re-reads F4-82 with `judge_v82_product_four_arms.py` alongside the file
readers; the generation-82 F3 readings (`read_v25_f3.py` and `read_v82_f3_equal.py` on f3-82/run-01, with the argv their
committed results were made with) added to the file readers, read on the live tree and in every stage, `read_v25_f3.py`'s
on F3-82 with its recorded exit 1 -- EXPECTED_EXIT; F4-82's reader recorded among the live reds; the pre-check and the
put-back target generation 83 (only the page differs from 82) and its bundle line; web/e2-editor.html among the files every stage
restores and the put-back checks, because the four-arm readers bind it (`originalHtmlSha256`) and the tree now holds the icon toolbar.

  stage v82  page 3b0a2ebb, paragraph client d07a58e0, narrow client 50f5a2ac, narrow session d037eaa4 (git 69c5583a9)

Everything else as v82's, whose docstring is the parent's: the four-arm readers bind the live shell digest and are
NOT_ESTABLISHED on the generation-83 tree by construction, and are re-read in their stage, byte-identical with the argv of
the committed result; put back in `finally` with `git checkout HEAD --` and `make e2-c-assets`.  Writes only into this
directory.  Must not run while anything serves dist/.

Verdict V0_PRIME_HOLDS iff every re-read is byte-identical with its expected exit (0 unless EXPECTED_EXIT says
otherwise), every four-arm live read is a red (nonzero exit), every restore and the put-back hold.
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
HTML = 'web/e2-editor.html'
FILES = (PAGE, CLIENT, NCLIENT, NSESSION, HTML)
DIST = {PAGE: 'dist/e2-editor-app.js', CLIENT: 'dist/editor-shell-v2/paragraph-editor-client.js',
        NCLIENT: 'dist/editor-shell-v2/narrow-editor-v2-client.js',
        NSESSION: 'dist/editor-shell-v2/narrow-editor-v2-session.js', HTML: 'dist/e2-editor.html'}
NARROW = {NCLIENT: ('9f084bf06', '34378dec62df9b02af8d85616b038fc176d6c94fad268773bf77eb2d495b9a55'),
          NSESSION: ('9f084bf06', 'a4cf3105835fa57621e1d8afd9a4b9eb5dd44ccf35aa46a9cd5b475ac6746f0d')}
STAGES = {
    'v24': {PAGE: ('b241c83a4', 'b15a6d8e07b6a4f3e551f27971b7cfe8bec2cb743e5f6809013ca7f2082de669'),
            CLIENT: ('d14186167', '4616ae1715a57927fdf11aaf45004dfd4656bf3c816ee7cebeedd203c180a9c6'), **NARROW},
    'v25': {PAGE: ('d14186167', '6e66c930fe3d861903cfa6dfd16d000523298e934fae444385d4fe37d484c7cb'),
            CLIENT: ('d14186167', '4616ae1715a57927fdf11aaf45004dfd4656bf3c816ee7cebeedd203c180a9c6'), **NARROW},
    'v79': {PAGE: ('9f084bf06', '9cb6ea1f1d867c40284a917fcc89ec94175ec2ebf9fbd009334626f1e8685dd1'),
            CLIENT: ('9f084bf06', '7d1c1eb22e0baa7ad487d16d02eb0b2cc29ade3653679372bbf9e05b06e94396'), **NARROW},
    'v80': {PAGE: ('7745a26e9', '3b6c023ea3f8807ef28e2a031e2d49f24c9c08db4278392c4c0d7252bbc51f7b'),
            CLIENT: ('7745a26e9', '7d1c1eb22e0baa7ad487d16d02eb0b2cc29ade3653679372bbf9e05b06e94396'),
            NCLIENT: ('7745a26e9', '50f5a2acd5f34e1db42fc82a0cf8e1a75072e51f0fcc95e7f6e77da3fecd21d5'),
            NSESSION: ('7745a26e9', 'd037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0')},
    'v81': {PAGE: ('a9a04dc64', 'b63d8ee53659c8b6216ecfc6ddaf4e3ef909f99f96b5975204ff31039816b1c7'),
            CLIENT: ('a9a04dc64', '7d1c1eb22e0baa7ad487d16d02eb0b2cc29ade3653679372bbf9e05b06e94396'),
            NCLIENT: ('a9a04dc64', '50f5a2acd5f34e1db42fc82a0cf8e1a75072e51f0fcc95e7f6e77da3fecd21d5'),
            NSESSION: ('a9a04dc64', 'd037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0')},
    'v82': {PAGE: ('69c5583a9', '3b0a2ebb92c3db282f9c832ab194249f963592698cf5c73d771998dc10203a6a'),
            CLIENT: ('69c5583a9', 'd07a58e0c674dd992e45df9a37ba26ade9a0d53555f284d1eb5cff2c343b5f3b'),
            NCLIENT: ('69c5583a9', '50f5a2acd5f34e1db42fc82a0cf8e1a75072e51f0fcc95e7f6e77da3fecd21d5'),
            NSESSION: ('69c5583a9', 'd037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0')},
}
V83 = {PAGE: '022d0cd0b5152f1ee9cabc74b10f5af2eb55935299228119a419ab717957759b',
       CLIENT: 'd07a58e0c674dd992e45df9a37ba26ade9a0d53555f284d1eb5cff2c343b5f3b',
       NCLIENT: '50f5a2acd5f34e1db42fc82a0cf8e1a75072e51f0fcc95e7f6e77da3fecd21d5',
       NSESSION: 'd037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0',
       HTML: 'ca58f40f30b7ad115dab51b65ff82ce297724f2185c1cd199c0c16f7a32f601a'}
# The four-arm readers bind web/e2-editor.html too (`originalHtmlSha256`), and every generation before the icon toolbar has this
# one page (run-01, which restored only the JS, read NOT_ESTABLISHED in every stage).
for _files in STAGES.values():
    _files[HTML] = ('69c5583a9', 'b9c2b9751f57962585bb9788255e2aa42a228c0a8b9983755191d2004bab545a')
V80 = {PAGE: '3b6c023ea3f8807ef28e2a031e2d49f24c9c08db4278392c4c0d7252bbc51f7b',
       CLIENT: '7d1c1eb22e0baa7ad487d16d02eb0b2cc29ade3653679372bbf9e05b06e94396',
       NCLIENT: '50f5a2acd5f34e1db42fc82a0cf8e1a75072e51f0fcc95e7f6e77da3fecd21d5',
       NSESSION: 'd037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0'}
A4 = EV / 'link-batch-v24/four-arms-counted-01'
F4_25 = EV / 'link-batch-v25/f4'
F4_79 = EV / 'shell-v79-173/f4'
V79 = EV / 'shell-v79-173'
F4_80 = EV / 'select-all-v26/f4'
F3_80 = EV / 'select-all-v26/f3-clipboard'
F4_81 = EV / 'v27-176/f4-81'
F3_81 = EV / 'v27-176/f3-81'
F4_82 = EV / 'v28-083/f4-82'
F3_82 = EV / 'v28-083/f3-82'


def four_arm_argv(tool, runs, out, isolated=False):
    return ['python3'] + (['-I'] if isolated else []) + [tool, str(runs / 'chrome/report.v23-four-arms'),
                                                          str(runs / 'firefox/report.v23-four-arms'), '--out', str(out)]


FOUR_ARM = {  # name -> (argv builder, committed)
    'v24-a4': (lambda out: four_arm_argv('tools/judge_v24_product_four_arms.py', A4, out, isolated=True), A4 / 'aggregate-judge.json'),
    'v25-f4': (lambda out: four_arm_argv('tools/judge_v25_product_four_arms.py', F4_25, out), F4_25 / 'aggregate-judge.json'),
    'v79-f4': (lambda out: four_arm_argv('tools/judge_v79_product_four_arms.py', F4_79, out), F4_79 / 'aggregate-judge.json'),
    'v80-f4': (lambda out: four_arm_argv('tools/judge_v80_product_four_arms.py', F4_80, out), F4_80 / 'aggregate-judge.json'),
    # F4-81's committed result was made with this un-normalised spelling of its input paths (the reader records
    # them), so the argv has to spell them the same way to re-read byte for byte (fixed by execution, run-01).
    'v81-f4': (lambda out: four_arm_argv('tools/judge_v81_product_four_arms.py', SDK / '../findings/evidence/v27-176/f4-81', out),
               F4_81 / 'aggregate-judge.json'),
    'v82-f4': (lambda out: four_arm_argv('tools/judge_v82_product_four_arms.py', F4_82, out), F4_82 / 'aggregate-judge.json'),
}
FILE_READERS = {  # name -> (argv, committed); each prints its result on stdout
    'b1-self-test': (['python3', 'tools/check_v79_blank_bullet.py', '--self-test',
                      '../findings/evidence/shell-v79-173/b1/run-01/report.json'], V79 / 'b1/run-01/self-test.json'),
    'f3-79-read-01': (['python3', 'tools/read_v25_f3.py', '--v25', '../findings/evidence/shell-v79-173/f3/run-01'],
                      V79 / 'f3/read-01.json'),
    'f3-79-equal-01': (['python3', 'tools/read_v79_f3_equal.py', '--v79', '../findings/evidence/shell-v79-173/f3/run-01'],
                       V79 / 'f3/equal-01.json'),
    'f3-80-read-01': (['python3', 'tools/read_v25_f3.py', '--v25', '../findings/evidence/select-all-v26/f3-clipboard/run-01'],
                      F3_80 / 'read-01.json'),
    'f3-80-equal-01': (['python3', 'tools/read_v80_f3_equal.py', '--v80', '../findings/evidence/select-all-v26/f3-clipboard/run-01'],
                       F3_80 / 'equal-01.json'),
    'f3-81-read-01': (['python3', 'tools/read_v25_f3.py', '--v25', '../findings/evidence/v27-176/f3-81/run-01'],
                      F3_81 / 'read-01.json'),
    'f3-81-equal-01': (['python3', 'tools/read_v81_f3_equal.py', '--v81', '../findings/evidence/v27-176/f3-81/run-01'],
                       F3_81 / 'equal-01.json'),
    'f3-82-read-01': (['python3', 'tools/read_v25_f3.py', '--v25', '../findings/evidence/v28-083/f3-82/run-01'],
                      F3_82 / 'read-01.json'),
    'f3-82-equal-01': (['python3', 'tools/read_v82_f3_equal.py', '--v82', '../findings/evidence/v28-083/f3-82/run-01'],
                       F3_82 / 'equal-01.json'),
}
EXPECTED_EXIT = {'f3-81-read-01': 1, 'f3-82-read-01': 1}
OUTPUTS = ([HERE / f'live-red-{n}.json' for n in FOUR_ARM] + [HERE / f'live-{n}.json' for n in FILE_READERS]
           + [HERE / 'restored-v24-selection.json', HERE / 'restored-v24-a4.json', HERE / 'restored-v25-f4.json',
              HERE / 'restored-v79-f4.json', HERE / 'restored-v80-f4.json', HERE / 'restored-v81-f4.json', HERE / 'restored-v82-f4.json']
           + [HERE / f'restored-{s}-{n}.json' for s in ('v79', 'v80', 'v81', 'v82') for n in FILE_READERS]
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
    result['ok'] = result['exit'] == EXPECTED_EXIT.get(name, 0) and result['byteIdentical']
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
    if served() != {p: {'source': V83[p], 'dist': V83[p]} for p in V83}:
        raise SystemExit('the tree is not generation 83 before V0prime: ' + json.dumps(served()))
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
        stage = report['stages']['v80'] = {'restore': restore('v80')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v80-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v80-f4.json'), HERE / 'restored-v80-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v80-{name}.json')
        stage = report['stages']['v81'] = {'restore': restore('v81')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v81-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v81-f4.json'), HERE / 'restored-v81-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v81-{name}.json')
        stage = report['stages']['v82'] = {'restore': restore('v82')}
        if stage['restore']['ok']:
            builder, committed = FOUR_ARM['v82-f4']
            stage['f4'] = reread(builder(HERE / 'restored-v82-f4.json'), HERE / 'restored-v82-f4.json', committed)
            for name in FILE_READERS:
                stage[name] = reread_stdout(name, HERE / f'restored-v82-{name}.json')
    finally:
        checkout = run(['git', '-C', str(REPO), 'checkout', 'HEAD', '--'] + [f'wasm_sdk_probe/{p}' for p in FILES])
        make = run(['make', 'e2-c-assets'])
        hashes = served()
        bundle = run(['python3', 'tools/build_e2_c_shell_bundle.py', '--manifest', 'e2/editor-shell-v2-bundle-v83.json'])
        e1c = run(['python3', 'tools/check_e1_c_bundle_intact.py'])
        (HERE / 'e1-c-after-put-back.json').write_text(e1c['stdout'] if e1c['exit'] == 0 else '{}')
        report['putBack'] = {'checkout': slim(checkout), 'make': slim(make), 'hashes': hashes,
                             'bundleLineV83': bundle['exit'], 'e1c': {'exit': e1c['exit']},
                             'ok': checkout['exit'] == 0 and make['exit'] == 0 and bundle['exit'] == 0 and e1c['exit'] == 0
                             and all(hashes[p]['source'] == hashes[p]['dist'] == V83[p] for p in V83)}
    stages = report['stages']
    rereads = [stages.get('v24', {}).get('selection'), stages.get('v24', {}).get('a4'),
               stages.get('v25', {}).get('f4'), stages.get('v79', {}).get('f4'), stages.get('v80', {}).get('f4'),
               stages.get('v81', {}).get('f4'), stages.get('v82', {}).get('f4')]
    rereads += [stages.get(s, {}).get(n) for s in ('v79', 'v80', 'v81', 'v82') for n in FILE_READERS]
    live = [report['live'].get(n) for n in list(FOUR_ARM) + list(FILE_READERS)]
    holds = (all(r and r['ok'] for r in rereads + live) and report['putBack']['ok']
             and len(stages) == 6 and all(s['restore']['ok'] for s in stages.values()))
    report['verdict'] = 'V0_PRIME_HOLDS' if holds else 'V0_PRIME_RED'
    report['finishedAt'] = time.time()
    (HERE / 'v0-prime.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'])
    return 0 if holds else 1


if __name__ == '__main__':
    raise SystemExit(main())
