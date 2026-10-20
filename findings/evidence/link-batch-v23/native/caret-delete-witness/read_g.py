#!/usr/bin/env python3
"""Read the caret-delete witness arms (SPEC-M3-ordered-commands §15.1; fable ruling 2 §2.1 item 5).

Usage:
  python3 -I read_g.py OUT_DIR FIXTURES_DIR [--rounds N]     the verdict; see Exit below
  python3 -I read_g.py --self-test SMOKE_DIR FIXTURES_DIR      the red cases, built from a real one-round run

Cells come from ../ordered-commands/tool/run_arms.py --arms-set g --modes uni1,seq (OC_A11Y=1): every op
records .uno:Undo and the focused paragraph (getA11yFocusedParagraph) immediately before its call
("atStart") and at its return ("atReturn"), in the same poll, nothing in between.

Two deciders, applied per op to those recorded inputs:
  undo-only  the after-payload differs from the before-payload and parses to >= 1 action -> deleted; else noop
             (spec §5.4 as pinned).
  paired     undo-only says deleted -> deleted; else, if the before-read's caret is strictly inside the
             paragraph (Backspace: position >= 1; Delete: position < len(content)) and the content differs
             -> deleted; else noop (ruling 2 §2.1 item 3).
The oracle is independent of both: the characters the saved document lost against its fixture
(sum of paragraph text lengths, fixture minus saved).

Criteria (written before the counted run, ARMS.md):
  G-W     (hard, form 1 per uni1 cell) the paired decider's deleted count equals the characters lost:
          g1, g2, cjk lose 25; the controls t1, e1 lose 0.
  G-red   (non-vacuity, per uni1 cell of g1 and g2) the undo-only decider's count is below the loss
          (grouping was reached); otherwise NOT-ESTABLISHED.
  G-a11y  every op's atStart and atReturn a11y reads parse with a `content`; otherwise the cell is unclean.
  seq cells are recorded (both deciders' counts), not judged: in the threaded topology the at-return read
  can precede the posted key.
Every cell must be clean: exactly one run-log entry with exit 0, a `done` record, no fatal, env mode as
asked, OC_A11Y=1, a measured record, a saved file. An unclean cell gives NE, never FAIL.

VERDICT G-HOLDS: every uni1 cell clean, G-W in every one, G-red in every g1/g2 one. G-FAILS: a clean uni1
cell where G-W fails. Otherwise NOT-ESTABLISHED.
Exit: 0 iff a verdict was reached on N >= 5 rounds; 2 when --rounds < 5 (not a counted reading); 1 for NE.
"""
import argparse
import gzip
import json
import pathlib
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

TEXT_NS = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
BKSP, DEL = 1283, 1286
LOSS = {'g1': 25, 'g2': 25, 'cjk': 25, 't1': 0, 'e1': 0}
GROUPED = ('g1', 'g2')
COUNTED_ROUNDS = 5


def text_length(xml_bytes):
    root = ET.fromstring(xml_bytes)
    total = 0
    for el in root.iter():
        if el.tag in ('{%s}p' % TEXT_NS, '{%s}h' % TEXT_NS):
            total += len(''.join(el.itertext()))
    return total


def run_log(out):
    entries = {}
    path = out / 'run-log.jsonl'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                x = json.loads(line)
                entries.setdefault((x.get('arm'), x.get('mode'), x.get('round')), []).append(x)
    return entries


def parse_a11y(text):
    try:
        d = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(d, dict) or 'content' not in d or 'position' not in d:
        return None
    return d


def undo_actions(text):
    try:
        acts = json.loads(text).get('actions')
    except (TypeError, ValueError, AttributeError):
        return None
    return len(acts) if isinstance(acts, list) else 0


def undo_only(op):
    before, after = op['atStart']['undo'], op['atReturn']['undo']
    return before != after and (undo_actions(after) or 0) >= 1


def paired(op, a, b):
    if undo_only(op):
        return True
    key = int(op['op'][1:]) if op['op'].startswith('K') else None
    pos, content = int(a['position']), a['content']
    inside = (key == BKSP and pos >= 1) or (key == DEL and pos < len(content))
    return inside and a['content'] != b['content']


def read_cell(out, arm, fixture, mode, r, log, fixtures):
    cell = {'problems': []}
    mine = log.get((arm, mode, r), [])
    if len(mine) != 1:
        cell['problems'].append(f'{len(mine)} run-log entries (exactly one is required)')
    elif mine[0].get('exit') != 0:
        cell['problems'].append(f"child exit {mine[0].get('exit')!r}")
    path = out / arm / f'{mode}-r{r}.jsonl'
    if not path.exists():
        cell['problems'].append('no output')
        return cell
    by = {}
    for line in path.read_text().splitlines():
        if line.strip():
            x = json.loads(line)
            by.setdefault(x['rec'], []).append(x)
    env = (by.get('env') or [{}])[0]
    if 'fatal' in by:
        cell['problems'].append(f"fatal {by['fatal'][0].get('what')}")
    if 'done' not in by:
        cell['problems'].append('no done record')
    if env.get('mode') != mode:
        cell['problems'].append(f"env mode {env.get('mode')!r} != {mode}")
    if env.get('OC_A11Y') != '1':
        cell['problems'].append('OC_A11Y not set')
    m = (by.get('measured') or [None])[0]
    if m is None:
        cell['problems'].append('no measured record')
        return cell
    ops = m.get('ops') or []
    if not ops:
        cell['problems'].append('no ops')
    undo_n = paired_n = 0
    for i, op in enumerate(ops):
        a = parse_a11y((op.get('atStart') or {}).get('a11y'))
        b = parse_a11y((op.get('atReturn') or {}).get('a11y'))
        if a is None or b is None or 'undo' not in (op.get('atStart') or {}):
            cell['problems'].append(f'op {i + 1}: no a11y read (G-a11y)')
            continue
        undo_n += undo_only(op)
        paired_n += paired(op, a, b)
    saved = out / arm / f'{mode}-r{r}.fodt.gz'
    if not saved.exists():
        cell['problems'].append('no saved file')
        return cell
    cell['lost'] = text_length((fixtures / f'{fixture}.fodt').read_bytes()) - text_length(gzip.decompress(saved.read_bytes()))
    cell['undo'], cell['paired'], cell['ops'] = undo_n, paired_n, len(ops)
    return cell


def judge(out, fixtures, rounds):
    arms = json.loads((out / 'arms.json').read_text())
    log = run_log(out)
    lines, problems, fails, vacuous = [], [], [], []
    for a in arms:
        name = a['name']
        for mode in ('uni1', 'seq'):
            row = []
            for r in range(1, rounds + 1):
                c = read_cell(out, name, a['fixture'], mode, r, log, fixtures)
                if c['problems']:
                    problems += [f'{name} {mode} r{r}: {p}' for p in c['problems']]
                    row.append('unclean')
                    continue
                row.append(f"lost {c['lost']} paired {c['paired']} undo-only {c['undo']}")
                if mode != 'uni1':
                    continue
                if c['lost'] != LOSS.get(name, c['lost']):
                    vacuous.append(f'{name} r{r}: lost {c["lost"]}, the arm expects {LOSS[name]}')
                if c['paired'] != c['lost']:
                    fails.append(f"{name} uni1 r{r}: paired {c['paired']} != lost {c['lost']}")
                if name in GROUPED and c['undo'] >= c['lost']:
                    vacuous.append(f"{name} uni1 r{r}: undo-only {c['undo']} reaches the loss {c['lost']}: grouping not reached")
            lines.append(f"{name:4} {mode:5} " + ' | '.join(row))
    if problems:
        lines.append(f'unclean cells: {len(problems)}: ' + '; '.join(problems[:6]))
    if vacuous:
        lines.append('NOT REACHED: ' + '; '.join(vacuous[:6]))
    if fails:
        lines.append('G-W FAILS: ' + '; '.join(fails[:6]))
    if fails:
        verdict = 'G-FAILS'
    elif not problems and not vacuous:
        verdict = 'G-HOLDS'
    else:
        verdict = 'NOT-ESTABLISHED'
    lines.append(f'VERDICT {verdict}')
    return verdict, lines


def self_test(smoke, fixtures):
    results = []

    def rewrite(path, fn):
        recs = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        path.write_text(''.join(json.dumps(fn(r)) + '\n' for r in recs))

    def ops_of(path, fn):
        def g(r):
            if r['rec'] == 'measured':
                for i, o in enumerate(r['ops']):
                    fn(i, o)
            return r
        rewrite(path, g)

    def case(label, mutate, expect, needle=None):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / 'out'
            shutil.copytree(smoke, out)
            mutate(out)
            verdict, lines = judge(out, fixtures, 1)
            text = '\n'.join(lines)
            ok = verdict == expect and (needle is None or needle in text)
            results.append(ok)
            print(f"{'ok  ' if ok else 'BAD '} {label}: VERDICT {verdict} (expected {expect}"
                  + (f', with {needle!r}' if needle else '') + ')')

    def stale_return(out):      # the a11y read at return still shows the pre-key paragraph (g2)
        def fn(i, o):
            o['atReturn']['a11y'] = o['atStart']['a11y']
        ops_of(out / 'g2' / 'uni1-r1.jsonl', fn)

    def t1_content_at_start(out):   # t1: content differs at position 0; the guard keeps it a noop
        def fn(i, o):
            d = json.loads(o['atReturn']['a11y'])
            d['content'] = 'changed ' + d['content']
            o['atReturn']['a11y'] = json.dumps(d)
        ops_of(out / 't1' / 'uni1-r1.jsonl', fn)

    def t1_content_inside(out):     # the same, with the before caret inside: now it counts as deleted
        def fn(i, o):
            d = json.loads(o['atReturn']['a11y'])
            d['content'] = 'changed ' + d['content']
            o['atReturn']['a11y'] = json.dumps(d)
            s = json.loads(o['atStart']['a11y'])
            s['position'] = '3'
            o['atStart']['a11y'] = json.dumps(s)
        ops_of(out / 't1' / 'uni1-r1.jsonl', fn)

    def no_a11y(out):
        def fn(i, o):
            o['atReturn'].pop('a11y', None)
        ops_of(out / 'cjk' / 'uni1-r1.jsonl', fn)

    def every_undo_differs(out):    # grouping not reached: every payload differs
        def fn(i, o):
            o['atReturn']['undo'] = o['atReturn']['undo'].replace('"actions"', f'"op{i}": 0, "actions"', 1)
        ops_of(out / 'g1' / 'uni1-r1.jsonl', fn)

    def runlog_dup(out):
        with open(out / 'run-log.jsonl', 'a') as f:
            f.write(json.dumps({'arm': 'e1', 'mode': 'uni1', 'round': 1, 'exit': 0}) + '\n')

    case('control: the smoke run as recorded', lambda out: None, 'G-HOLDS')
    case('a stale a11y read at return (g2)', stale_return, 'G-FAILS', 'g2 uni1 r1: paired')
    case('t1 content differs at position 0: the guard keeps it a noop', t1_content_at_start, 'G-HOLDS')
    case('t1 content differs with the caret inside: counted, and wrong', t1_content_inside, 'G-FAILS', 't1 uni1 r1: paired 3 != lost 0')
    case('no a11y read at return (cjk)', no_a11y, 'NOT-ESTABLISHED', 'no a11y read')
    case('every undo payload differs (g1): grouping not reached', every_undo_differs, 'NOT-ESTABLISHED', 'grouping not reached')
    case('a cell with two run-log entries', runlog_dup, 'NOT-ESTABLISHED', '2 run-log entries')
    print(f'self-test: {sum(results)}/{len(results)} as required')
    return 0 if all(results) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?')
    ap.add_argument('fixtures', nargs='?')
    ap.add_argument('--rounds', type=int, default=5)
    ap.add_argument('--self-test', nargs=2, metavar=('SMOKE_DIR', 'FIXTURES_DIR'))
    a = ap.parse_args()
    if a.self_test:
        return self_test(pathlib.Path(a.self_test[0]), pathlib.Path(a.self_test[1]))
    verdict, lines = judge(pathlib.Path(a.out), pathlib.Path(a.fixtures), a.rounds)
    print('\n'.join(lines))
    print(f'N = {a.rounds} rounds' + ('' if a.rounds >= COUNTED_ROUNDS else
                                       f' < {COUNTED_ROUNDS}: NOT a counted reading (ruling 2 §2.1 item 5)'))
    if a.rounds < COUNTED_ROUNDS:
        return 2
    return 0 if verdict in ('G-HOLDS', 'G-FAILS') else 1


if __name__ == '__main__':
    sys.exit(main())
