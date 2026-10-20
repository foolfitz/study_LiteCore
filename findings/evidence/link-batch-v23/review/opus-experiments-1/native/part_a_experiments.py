#!/usr/bin/env python3
"""Opus seat, review 1, Part A experiments.  Read-only on the repository: every mutation is made on a
copy under this script's directory, from the scratch extraction (git archive HEAD) of the committed
evidence.  Run: python3 -I part_a_experiments.py <scratch>/tree/findings/evidence/link-batch-v23/native/ordered-commands

A2  d4 unipoll cells with their ops removed (only the trigger ran)       -> what read_results prints
A3  D7: the .uno:Undo top at return and after, for EVERY round (the reader prints round 1 only)
A4  q output relabelled as unipoll on d5, env left threaded (an unclean cell) -> verdict and exit
A5  every REPLY_TYPES name of read_n1.py: does it occur anywhere in out-n1's callback records?
A6  N1a non-vacuity: per op, did any reply-type callback arrive between its return and its first poll?
A7  D8 evaluated on an unclean cell: d5 unipoll r1 'saved' false AND selText '' at return -> verdict
A8  D4: does the reader's evidence show .uno:Bold ran under unipoll?  (UNO_COMMAND_RESULT in callbacks)
"""
import collections
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

OC = pathlib.Path(sys.argv[1])
HERE = pathlib.Path(__file__).resolve().parent
WORK = HERE / 'work'
TOOL = OC / 'tool'


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOL / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rr = load('read_results')
rn = load('read_n1')


def fresh(src, name):
    dst = WORK / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def rewrite(path, fn):
    recs = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    path.write_text(''.join(json.dumps(fn(r)) + '\n' for r in recs))


def run_reader(tool, out, rounds):
    p = subprocess.run([sys.executable, '-I', str(TOOL / tool), str(out), '--rounds', str(rounds)],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def head(text, n=40):
    return '\n'.join(text.splitlines()[:n])


print('== A2: d4, unipoll, ops removed from every round (the trigger only) ==')
out = fresh(OC / 'out', 'A2')
for r in range(1, 6):
    def drop_ops(rec):
        if rec['rec'] == 'measured':
            rec['ops'] = []
        return rec
    rewrite(out / 'd4' / f'unipoll-r{r}.jsonl', drop_ops)
    # the trigger alone (Shift+Right selects a) saves the fixture unchanged: no bold run, as seq does
    shutil.copy(out / 'd4' / f'seq-r{r}.fodt.gz', out / 'd4' / f'unipoll-r{r}.fodt.gz')
code, text = run_reader('read_results.py', out, 5)
print(f'exit {code}')
print('\n'.join(l for l in text.splitlines() if l.startswith(('d4', 'D8', 'VERDICT'))))
# the locator: what the trigger-only state reads, compared with seq's recorded caret
for m in ('seq', 'unipoll'):
    loc = [json.loads(x) for x in (OC / 'out' / 'd4' / f'{m}-r1.jsonl').read_text().splitlines() if '"locate"' in x][0]
    print(f'  recorded {m} r1 locate: {loc}')
print('  NOTE the A2 caret is the recorded unipoll locator (which ran after Left+Bold); a trigger-only run')
print('  would start the locator from the selection a (anchor 0, point 1): Shift+End -> "abcd", Shift+Home -> ""')
print('  = ["", "abcd"], the same pair seq records.  That last step is inferred, not run.')

print('\n== A3: D7, the .uno:Undo top per round (reader prints round 1 only) ==')
for arm in ('d7i', 'd7ii', 'd7iii', 'd7plain'):
    for m in ('seq', 'q', 'unipoll'):
        tops = []
        for r in range(1, 6):
            recs = [json.loads(x) for x in (OC / 'out' / arm / f'{m}-r{r}.jsonl').read_text().splitlines() if x.strip()]
            meas = [x for x in recs if x['rec'] == 'measured'][0]
            tops.append((rr.undo_top(meas['ops'][0]['atReturn']['undo']), rr.undo_top(meas['after']['undo'])))
        same = len(set(tops)) == 1
        print(f'  {arm:8} {m:8} 5 rounds identical={same}  {tops[0]}' + ('' if same else f'  ALL={tops}'))

print('\n== A4: q relabelled as unipoll on d5 only, env left threaded (SAL_LOK_OPTIONS absent) ==')
out = fresh(OC / 'smoke', 'A4')
d = out / 'd5'
shutil.copy(d / 'q-r1.fodt.gz', d / 'unipoll-r1.fodt.gz')
init = next(json.loads(x) for x in (d / 'unipoll-r1.jsonl').read_text().splitlines() if '"init"' in x)
body = [json.loads(x) for x in (d / 'q-r1.jsonl').read_text().splitlines() if x.strip()]
for rec in body:
    if rec['rec'] == 'env':
        rec['mode'] = 'unipoll'          # SAL_LOK_OPTIONS stays None: the topology that ran is threaded
    if rec['rec'] == 'measured':
        rec['mode'] = 'unipoll'
body.insert(1, init)
(d / 'unipoll-r1.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in body))
code, text = run_reader('read_results.py', out, 1)
print(f'exit {code}')
print('\n'.join(l for l in text.splitlines() if l.startswith(('d5', 'D8', 'VERDICT'))))

print('\n== A5: REPLY_TYPES names against the callback types recorded in out-n1 ==')
seen = collections.Counter()
for f in (OC / 'out-n1').glob('*/*.jsonl'):
    for x in f.read_text().splitlines():
        if '"measured"' in x:
            rec = json.loads(x)
            for cb in rec['callbacks']:
                seen[cb['type']] += 1
for t in sorted(rn.REPLY_TYPES):
    print(f'  {t:42} recorded {seen.get(t, 0)} times in measured callbacks')
print('  all types seen:', dict(sorted(seen.items())))

print('\n== A6: per op, reply-type callbacks between its return and its first poll (uni1ai) ==')
empty = []
tot = 0
for f in sorted((OC / 'out-n1').glob('*/uni1ai-r*.jsonl')):
    rec = [json.loads(x) for x in f.read_text().splitlines() if '"measured"' in x][0]
    cbs = rec['callbacks']
    for o in rec['ops']:
        lo = o['returnedMs'] - 1e-6
        hi = o['returnedMs'] + o['firstPollAfterReturnMs'] + 2.0  # the at-return reads sit between returnedMs and the harness's opReturnedMs
        # callbacks are timed relative to the X step's t0, like the op's startMs/returnedMs
        start = o['startMs']
        ontime = [c['type'] for c in cbs if start <= c['t'] <= hi and c['type'] in rn.REPLY_TYPES]
        tot += 1
        if not ontime:
            empty.append(f'{f.parent.name}/{f.name} {o["op"]}')
print(f'  ops: {tot}; ops with NO reply-type callback before their first poll: {len(empty)}')
for e in empty[:20]:
    print('   ', e)

print('\n== A7: D8 evaluated on an unclean cell (d5 unipoll r1: saved=false and selText "" at return) ==')
out = fresh(OC / 'smoke', 'A7')
def unclean_and_d8(rec):
    if rec['rec'] == 'saved':
        rec['ok'] = False
    if rec['rec'] == 'measured':
        rec['ops'][0]['atReturn']['selText'] = ''
    return rec
rewrite(out / 'd5' / 'unipoll-r1.jsonl', unclean_and_d8)
code, text = run_reader('read_results.py', out, 1)
print(f'exit {code}')
print('\n'.join(l for l in text.splitlines() if l.startswith(('d5', 'D8', 'VERDICT'))))

print('\n== A8: D4 under unipoll, the evidence that .uno:Bold ran ==')
for m in ('seq', 'unipoll'):
    for r in (1,):
        rec = [json.loads(x) for x in (OC / 'out' / 'd4' / f'{m}-r{r}.jsonl').read_text().splitlines() if '"measured"' in x][0]
        res = [c['payload'][:160] for c in rec['callbacks'] if c['type'] == 'LOK_CALLBACK_UNO_COMMAND_RESULT']
        bold = [c['payload'] for c in rec['callbacks'] if c['type'] == 'LOK_CALLBACK_STATE_CHANGED' and 'Bold' in c['payload']]
        print(f'  d4 {m} r{r}: UNO_COMMAND_RESULT {res}; STATE_CHANGED with Bold {bold[:3]}')
print('  read_results.py reads neither (its landing is the saved shape and the locator).')
