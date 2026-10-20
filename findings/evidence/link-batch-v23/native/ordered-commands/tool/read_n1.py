#!/usr/bin/env python3
"""Read N1 (SPEC-M3-ordered-commands §9.1, pinned at b9080313; ruling 1 addendum 1 §2.3).

Usage:
  python3 -I read_n1.py OUT_DIR [--rounds N]     the verdict; exit 0 iff the reading is complete
  python3 -I read_n1.py --self-test SMOKE_DIR    the red cases, built from a real one-round run

Cells come from run_arms.py --arms-set n1: the D arms and tleave in mode uni1ai (one op per
poll, anyInput answering "a reply is pending"), and join200 in uni1 (no anyInput) and uni1ai.
Each op's record carries `firstPollAfterReturnMs` and `lateCallbacks` (every callback that
arrived after the first poll following its return, within a fixed 1500 ms idle; oc_native.cpp).

  N1a (hard)    every uni1ai cell, every op: no late callback of the types a reply depends on:
                INVALIDATE_VISIBLE_CURSOR, TEXT_SELECTION, TEXT_SELECTION_START,
                TEXT_SELECTION_END, UNO_COMMAND_RESULT, INVALIDATE_TILES.
  N1b (record)  per late callback type in uni1ai cells: count, and min/median/max delay after
                the first poll. Positive control: every tleave round records at least one late
                STATE_CHANGED with a delay > 0; otherwise the harness does not see late
                callbacks and N1 is NOT-ESTABLISHED.
  N1c (hard)    join200's first-poll delay per round, uni1 against uni1ai. The pinned text: the
                mode without the pending-reply term must be longer; equal = NE. Read as, over
                the rounds: every uni1 round longer than every uni1ai round = PASS; every uni1ai
                round longer than every uni1 round = FAIL; ranges that overlap = NE (not told
                apart). This reading is written before the counted run.

Every cell must be clean: exit 0, a `done` record, no fatal, no capped settle, env
SAL_LOK_OPTIONS=unipoll, the init record, and `anyInputRegistered` as its mode needs.

VERDICT N1-HOLDS: N1a PASS, N1b's control present, N1c PASS. N1-FAILS: an N1a violation or
N1c FAIL. Otherwise NOT-ESTABLISHED.

Two-seat review 1 (ev/review/opus-review-1.md, codex-review-1.md):
- F2: a cell must have exactly one run-log.jsonl entry, with exit 0 (a reused directory, a re-run cell or
  a child that crashed after its records is unclean).
- F3: N1a and N1c are judged on clean cells only; a violation in an unclean cell makes the reading
  NOT-ESTABLISHED, never N1-FAILS.
- The window is bounded: lateCallbacks holds what arrived within 1500 ms after the first poll (oc_native.cpp
  uni1 steps). N1a says nothing about later callbacks; the committed run has none in the whole measured step
  (ev/review/disposition-1/n1-outside-window.txt).
- The residual blind spot: a reply-type callback that lands between op N+1's start and N+1's first poll
  reads as on time for N+1 (a window of a few ms).
- N1c's NE label: some scheduler task ran before the poll; which one is not identified (ruling 2 §2.6;
  the spec's first wording named the layout idle).
- Exit: 0 iff a verdict was reached (N1-HOLDS or N1-FAILS) on N >= 5 rounds; 2 when --rounds < 5.
- --on-time-list (ruling 2 §2.2, form 2): the (op, STATE_CHANGED key) pairs that arrived before the first
  poll in every clean uni1ai round where the op ran, and the late or mixed ones; generated from the records.
"""
import argparse
import json
import pathlib
import shutil
import statistics
import sys
import tempfile

# Ruling 2 §2.5: INVALIDATE_TILES withdrawn (no reply reads a tile; 0 tile callbacks in 282 native processes).
REPLY_TYPES = {'LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR', 'LOK_CALLBACK_TEXT_SELECTION',
               'LOK_CALLBACK_TEXT_SELECTION_START', 'LOK_CALLBACK_TEXT_SELECTION_END',
               'LOK_CALLBACK_UNO_COMMAND_RESULT'}
COUNTED_ROUNDS = 5  # spec §9.1


def run_log(out):
    """(arm, mode, round) -> the run-log entries of that cell (review 1, F2)."""
    entries = {}
    path = out / 'run-log.jsonl'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                x = json.loads(line)
                entries.setdefault((x.get('arm'), x.get('mode'), x.get('round')), []).append(x)
    return entries


def read_cell(out, arm, mode, r, log=None):
    path = out / arm / f'{mode}-r{r}.jsonl'
    cell = {'problems': [], 'ops': []}
    if log is not None:
        mine = log.get((arm, mode, r), [])
        if len(mine) != 1:
            cell['problems'].append(f'{len(mine)} run-log entries (exactly one is required)')
        elif mine[0].get('exit') != 0:
            cell['problems'].append(f"child exit {mine[0].get('exit')!r}")
    if not path.exists():
        cell['problems'].append('no output')
        return cell
    by = {}
    for line in path.read_text().splitlines():
        if line.strip():
            x = json.loads(line)
            by.setdefault(x['rec'], []).append(x)
    env = (by.get('env') or [{}])[0]
    init = (by.get('init') or [{}])[0]
    if 'fatal' in by:
        cell['problems'].append(f"fatal {by['fatal'][0].get('what')}")
    if 'done' not in by:
        cell['problems'].append('no done record')
    if env.get('mode') != mode:
        cell['problems'].append(f"env mode {env.get('mode')!r} != {mode}")
    if env.get('SAL_LOK_OPTIONS') != 'unipoll':
        cell['problems'].append(f"env SAL_LOK_OPTIONS {env.get('SAL_LOK_OPTIONS')!r}")
    if not init.get('sofficeMainSkipped'):
        cell['problems'].append('no unipoll init record')
    if init.get('anyInputRegistered') is not (mode == 'uni1ai'):
        cell['problems'].append(f"anyInputRegistered {init.get('anyInputRegistered')!r} in {mode}")
    m = (by.get('measured') or [None])[0]
    if m is None:
        cell['problems'].append('no measured record')
    else:
        if m.get('capped'):
            cell['problems'].append('settle capped')
        cell['ops'] = m.get('ops') or []
        if not cell['ops'] or any('lateCallbacks' not in o for o in cell['ops']):
            cell['problems'].append('an op without a late-callback record')
    return cell


def judge(out, rounds):
    arms = [a['name'] for a in json.loads((out / 'arms.json').read_text())]
    lines, problems, n1a = [], [], []
    late = {}
    log = run_log(out)
    ai_arms = [a for a in arms if a != 'join200']
    for arm in ai_arms:
        for r in range(1, rounds + 1):
            c = read_cell(out, arm, 'uni1ai', r, log)
            problems += [f'{arm} uni1ai r{r}: {p}' for p in c['problems']]
            if c['problems']:
                continue  # F3: an unclean cell is not judged
            for o in c['ops']:
                for cb in o.get('lateCallbacks', []):
                    late.setdefault(cb['type'], []).append((arm, cb['t']))
                    if cb['type'] in REPLY_TYPES:
                        n1a.append(f"{arm} r{r} {o['op']}: {cb['type']} {cb['t']:.1f} ms after the first poll")
    # N1b and its control
    lines.append('N1b (record): late callbacks after the first poll, uni1ai cells')
    for t, v in sorted(late.items()):
        ds = [d for _, d in v]
        lines.append(f"  {t:40} n={len(ds):4}  min {min(ds):8.1f}  median {statistics.median(ds):8.1f}  max {max(ds):8.1f} ms")
    control_ok = True
    for r in range(1, rounds + 1):
        c = read_cell(out, 'tleave', 'uni1ai', r, log)
        sc = [cb['t'] for o in c['ops'] for cb in o.get('lateCallbacks', []) if cb['type'] == 'LOK_CALLBACK_STATE_CHANGED']
        if not sc or max(sc) <= 0:
            control_ok = False
            lines.append(f'  control: tleave r{r} has no late STATE_CHANGED')
    lines.append(f"  control (tleave late STATE_CHANGED every round): {'present' if control_ok else 'ABSENT'}")
    # N1c
    delays = {}
    for mode in ('uni1', 'uni1ai'):
        delays[mode] = []
        for r in range(1, rounds + 1):
            c = read_cell(out, 'join200', mode, r, log)
            problems += [f'join200 {mode} r{r}: {p}' for p in c['problems']]
            if c['ops'] and not c['problems']:  # F3
                delays[mode].append(c['ops'][0].get('firstPollAfterReturnMs'))
    d0, d1 = delays['uni1'], delays['uni1ai']
    if len(d0) < rounds or len(d1) < rounds or None in d0 + d1:
        n1c = 'NE'
        why = 'missing rounds'
    elif min(d0) > max(d1):
        n1c, why = 'PASS', 'every uni1 round longer than every uni1ai round'
    elif min(d1) > max(d0):
        n1c, why = 'FAIL', 'every uni1ai round longer than every uni1 round'
    else:
        n1c, why = 'NE', 'the two ranges overlap'
    lines.append(f"N1c     {n1c:4} {why}; uni1 {[round(x, 3) for x in d0 if x is not None]} ms, "
                 f"uni1ai {[round(x, 3) for x in d1 if x is not None]} ms")
    n1a_v = 'FAIL' if n1a else ('NE' if problems else 'PASS')
    lines.insert(0, f"N1a     {n1a_v:4} " + (('; '.join(n1a[:5])) if n1a else
                                             f'{len(ai_arms)} arms x {rounds} rounds, no late reply callback'))
    if problems:
        lines.append('unclean: ' + '; '.join(problems[:6]))
    if n1a or n1c == 'FAIL':
        verdict = 'N1-FAILS'
    elif n1a_v == 'PASS' and control_ok and n1c == 'PASS' and not problems:
        verdict = 'N1-HOLDS'
    else:
        verdict = 'NOT-ESTABLISHED'
    lines.append(f'VERDICT {verdict}')
    return verdict, lines


def state_key(payload):
    """'.uno:Bold=true' -> '.uno:Bold'; a JSON payload -> its commandName."""
    text = (payload or '').strip()
    if text.startswith('{'):
        try:
            return json.loads(text).get('commandName') or '<json>'
        except ValueError:
            return '<unparsed json>'
    return text.split('=', 1)[0]


def on_time_list(out, rounds):
    """Ruling 2 §2.2 (form 2): per (op, state key), on time in every clean uni1ai round, or late/mixed.

    An op's own items are the STATE_CHANGED callbacks of its step window (its start to the next op's start, or
    the step's end); the late ones are those in its index-based lateCallbacks; the rest arrived before its
    first poll.  Only clean cells count.
    """
    arms = [a['name'] for a in json.loads((out / 'arms.json').read_text()) if a['name'] != 'join200']
    log = run_log(out)
    seen = {}
    for arm in arms:
        for r in range(1, rounds + 1):
            c = read_cell(out, arm, 'uni1ai', r, log)
            if c['problems']:
                continue
            recs = [json.loads(x) for x in (out / arm / f'uni1ai-r{r}.jsonl').read_text().splitlines() if x.strip()]
            m = next(x for x in recs if x['rec'] == 'measured')
            ops = m['ops']
            for i, op in enumerate(ops):
                end = ops[i + 1]['startMs'] if i + 1 < len(ops) else float('inf')
                late = {state_key(cb['payload']) for cb in op.get('lateCallbacks', [])
                        if cb['type'] == 'LOK_CALLBACK_STATE_CHANGED'}
                mine = {state_key(cb['payload']) for cb in m['callbacks']
                        if cb['type'] == 'LOK_CALLBACK_STATE_CHANGED' and op['startMs'] <= cb['t'] < end}
                for key in mine | late:
                    seen.setdefault((op['op'], key), []).append('late' if key in late else 'on time')
    result = {'onTime': [], 'lateOrMixed': []}
    for (op, key), v in sorted(seen.items()):
        entry = {'op': op, 'key': key, 'rounds': len(v), 'late': v.count('late')}
        (result['onTime'] if entry['late'] == 0 else result['lateOrMixed']).append(entry)
    return result


def self_test(smoke):
    results = []

    def rewrite(path, fn):
        recs = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        path.write_text(''.join(json.dumps(fn(r)) + '\n' for r in recs))

    def case(label, mutate, expect, needle=None):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / 'out'
            shutil.copytree(smoke, out)
            mutate(out)
            verdict, lines = judge(out, 1)
            text = '\n'.join(lines)
            ok = verdict == expect and (needle is None or needle in text)
            results.append(ok)
            print(f"{'ok  ' if ok else 'BAD '} {label}: VERDICT {verdict} (expected {expect}"
                  + (f", with {needle!r}" if needle else '') + ')')

    def late_cursor(out):       # a reply callback moved after the first poll
        def fn(r):
            if r['rec'] == 'measured':
                r['ops'][0]['lateCallbacks'].append({'t': 12.5, 'type': 'LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR',
                                                     'payload': '0, 0, 0, 0'})
            return r
        rewrite(out / 'd2' / 'uni1ai-r1.jsonl', fn)

    def no_control(out):        # tleave without its late STATE_CHANGED
        def fn(r):
            if r['rec'] == 'measured':
                for o in r['ops']:
                    o['lateCallbacks'] = [c for c in o['lateCallbacks'] if c['type'] != 'LOK_CALLBACK_STATE_CHANGED']
            return r
        rewrite(out / 'tleave' / 'uni1ai-r1.jsonl', fn)

    def set_delay(mode, value):
        def mutate(out):
            def fn(r):
                if r['rec'] == 'measured':
                    r['ops'][0]['firstPollAfterReturnMs'] = value
                return r
            rewrite(out / 'join200' / f'{mode}-r1.jsonl', fn)
        return mutate

    def equal(out):
        set_delay('uni1', 0.1)(out)
        set_delay('uni1ai', 0.1)(out)

    def reversed_(out):
        set_delay('uni1', 0.1)(out)
        set_delay('uni1ai', 5.0)(out)

    def no_anyinput(out):       # uni1ai labelled, anyInput not registered
        rewrite(out / 'join200' / 'uni1ai-r1.jsonl',
                lambda r: {**r, 'anyInputRegistered': False} if r['rec'] == 'init' else r)

    case('control: the smoke run as recorded', lambda out: None, 'N1-HOLDS')
    case('N1a: a cursor callback after the first poll', late_cursor, 'N1-FAILS', 'INVALIDATE_VISIBLE_CURSOR 12.5')
    case('N1b: tleave without a late STATE_CHANGED', no_control, 'NOT-ESTABLISHED', 'ABSENT')
    case('N1c: equal delays', equal, 'NOT-ESTABLISHED', 'overlap')
    case('N1c: the pending-reply term makes it later', reversed_, 'N1-FAILS', 'N1c     FAIL')
    case('a uni1ai cell without anyInput registered', no_anyinput, 'NOT-ESTABLISHED', 'anyInputRegistered')

    def runlog_dup(out):        # F2: a cell executed twice
        with open(out / 'run-log.jsonl', 'a') as f:
            f.write(json.dumps({'arm': 'd1', 'mode': 'uni1ai', 'round': 1, 'exit': 0}) + '\n')

    def runlog_exit(out):       # F2: a child that wrote its records and then exited non-zero
        path = out / 'run-log.jsonl'
        xs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        for x in xs:
            if (x['arm'], x['mode']) == ('d3', 'uni1ai'):
                x['exit'] = -6
        path.write_text(''.join(json.dumps(x) + '\n' for x in xs))

    def unclean_late(out):      # F3: a late cursor in a cell whose child crashed
        late_cursor(out)
        rewrite(out / 'd2' / 'uni1ai-r1.jsonl', lambda r: {**r, 'rec': 'done-not'} if r['rec'] == 'done' else r)

    def unclean_reversed(out):  # F3: N1c reversed, the uni1ai join200 cell unclean
        reversed_(out)
        rewrite(out / 'join200' / 'uni1ai-r1.jsonl', lambda r: {**r, 'capped': True} if r['rec'] == 'measured' else r)

    def late_type(kind):        # ruling 2 §2.6: one synthetic late callback per reply type name
        def mutate(out):
            def fn(r):
                if r['rec'] == 'measured':
                    r['ops'][0]['lateCallbacks'].append({'t': 7.5, 'type': kind, 'payload': 'synthetic'})
                return r
            rewrite(out / 'd3' / 'uni1ai-r1.jsonl', fn)
        return mutate

    for kind in sorted(REPLY_TYPES - {'LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR'}):
        case(f'N1a: a late {kind[13:]}', late_type(kind), 'N1-FAILS', f'{kind} 7.5')
    case('N1a: a late INVALIDATE_TILES is no longer a reply type', late_type('LOK_CALLBACK_INVALIDATE_TILES'), 'N1-HOLDS')
    case('F2: a cell with two run-log entries', runlog_dup, 'NOT-ESTABLISHED', '2 run-log entries')
    case('F2: a child exit -6 after its records', runlog_exit, 'NOT-ESTABLISHED', 'child exit -6')
    case('F3: a late cursor in an unclean cell', unclean_late, 'NOT-ESTABLISHED', 'no done record')
    case('F3: N1c reversed on an unclean cell', unclean_reversed, 'NOT-ESTABLISHED', 'settle capped')
    # the on-time list (ruling 2 §2.2): Bold on time in d4 as recorded; a late copy of it moves Bold out
    def bold_late(out):
        def fn(r):
            if r['rec'] == 'measured':
                for o in r['ops']:
                    if o['op'].startswith('U.uno:Bold'):
                        o['lateCallbacks'].append({'t': 3.0, 'type': 'LOK_CALLBACK_STATE_CHANGED', 'payload': '.uno:Bold=true'})
            return r
        rewrite(out / 'd4' / 'uni1ai-r1.jsonl', fn)

    for label, mutate, want in (('on-time list: Bold on time as recorded', lambda out: None, 'onTime'),
                                ('on-time list: Bold made late moves it out', bold_late, 'lateOrMixed')):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / 'out'
            shutil.copytree(smoke, out)
            mutate(out)
            lst = on_time_list(out, 1)
            where = [k for k in ('onTime', 'lateOrMixed')
                     if any(e['key'] == '.uno:Bold' and e['op'].startswith('U.uno:Bold') for e in lst[k])]
            ok = where == [want]
            results.append(ok)
            print(f"{'ok  ' if ok else 'BAD '} {label}: .uno:Bold in {where} (expected [{want!r}])")
    print(f"self-test: {sum(results)}/{len(results)} as required")
    return 0 if all(results) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?')
    ap.add_argument('--rounds', type=int, default=5)
    ap.add_argument('--self-test', metavar='SMOKE_DIR')
    ap.add_argument('--on-time-list', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test(pathlib.Path(a.self_test))
    if a.on_time_list:
        print(json.dumps(on_time_list(pathlib.Path(a.out), a.rounds), indent=1, ensure_ascii=False))
        return 0
    verdict, lines = judge(pathlib.Path(a.out), a.rounds)
    print('\n'.join(lines))
    print(f'N = {a.rounds} rounds' + ('' if a.rounds >= COUNTED_ROUNDS else
                                       f' < {COUNTED_ROUNDS}: NOT a counted reading (spec §9.1)'))
    if a.rounds < COUNTED_ROUNDS:
        return 2
    return 0 if verdict in ('N1-HOLDS', 'N1-FAILS') else 1


if __name__ == '__main__':
    sys.exit(main())
