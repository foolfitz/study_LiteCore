#!/usr/bin/env python3
"""Two-seat review 1, F2/F3 on read_n1.py: each new red case, judged by the reader at HEAD and by the fixed
reader, on a copy of the committed N1 smoke run (one round; its run-log has one entry per cell).

  python3 -I red_old_vs_new_n1.py OLD_READER NEW_READER SMOKE_N1_DIR
"""
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rewrite(path, fn):
    recs = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    path.write_text(''.join(json.dumps(fn(r)) + '\n' for r in recs))


def late_cursor(out):
    def fn(r):
        if r['rec'] == 'measured':
            r['ops'][0]['lateCallbacks'].append({'t': 12.5, 'type': 'LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR', 'payload': '0, 0, 0, 0'})
        return r
    rewrite(out / 'd2' / 'uni1ai-r1.jsonl', fn)


def set_delay(out, mode, value):
    def fn(r):
        if r['rec'] == 'measured':
            r['ops'][0]['firstPollAfterReturnMs'] = value
        return r
    rewrite(out / 'join200' / f'{mode}-r1.jsonl', fn)


def runlog_dup(out):
    with open(out / 'run-log.jsonl', 'a') as f:
        f.write(json.dumps({'arm': 'd1', 'mode': 'uni1ai', 'round': 1, 'exit': 0}) + '\n')


def runlog_exit(out):
    path = out / 'run-log.jsonl'
    xs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    for x in xs:
        if (x['arm'], x['mode']) == ('d3', 'uni1ai'):
            x['exit'] = -6
    path.write_text(''.join(json.dumps(x) + '\n' for x in xs))


def unclean_late(out):
    late_cursor(out)
    rewrite(out / 'd2' / 'uni1ai-r1.jsonl', lambda r: {**r, 'rec': 'done-not'} if r['rec'] == 'done' else r)


def unclean_reversed(out):
    set_delay(out, 'uni1', 0.1)
    set_delay(out, 'uni1ai', 5.0)
    rewrite(out / 'join200' / 'uni1ai-r1.jsonl', lambda r: {**r, 'capped': True} if r['rec'] == 'measured' else r)


def late_tiles(out):
    def fn(r):
        if r['rec'] == 'measured':
            r['ops'][0]['lateCallbacks'].append({'t': 7.5, 'type': 'LOK_CALLBACK_INVALIDATE_TILES', 'payload': 'synthetic'})
        return r
    rewrite(out / 'd3' / 'uni1ai-r1.jsonl', fn)


CASES = [('baseline (the smoke as recorded)', lambda out: None),
         ('F2 a cell with two run-log entries', runlog_dup),
         ('F2 a child exit -6 after its records', runlog_exit),
         ('F3 a late cursor in an unclean cell', unclean_late),
         ('F3 N1c reversed on an unclean cell', unclean_reversed),
         ('ruling 2 §2.5: a late INVALIDATE_TILES (withdrawn)', late_tiles)]


def main(old_path, new_path, smoke):
    old, new = load(old_path, 'old_reader'), load(new_path, 'new_reader')
    print(f"{'case':44} {'HEAD':18} fixed")
    for label, mutate in CASES:
        row = []
        for mod in (old, new):
            with tempfile.TemporaryDirectory() as tmp:
                out = pathlib.Path(tmp) / 'out'
                shutil.copytree(smoke, out)
                mutate(out)
                row.append(mod.judge(out, 1)[0])
        print(f'{label:44} {row[0]:18} {row[1]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
