#!/usr/bin/env python3
"""Two-seat review 1 (F1-F3) and ruling 2 (§2.6) on read_results.py: each new red case, judged by the reader at HEAD and by the
fixed reader, on a copy of the committed smoke run (one round).  The copy keeps the last run-log entry per
cell, as the fixed self-test's control does (smoke/NOTES.md:23-26: d7i was re-run).

  python3 -I red_old_vs_new_results.py OLD_READER NEW_READER SMOKE_DIR
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


def keep_last(out):
    path = out / 'run-log.jsonl'
    last = {}
    for x in (json.loads(line) for line in path.read_text().splitlines() if line.strip()):
        last[(x['arm'], x['mode'], x['round'])] = x
    path.write_text(''.join(json.dumps(x) + '\n' for x in last.values()))


def e(out): (out / 'd7iii' / 'unipoll-r1.jsonl').unlink()


def f(out):
    def fn(r):
        if r['rec'] == 'measured':
            r['fired'], r['ops'] = False, []
        return r
    rewrite(out / 'd7ii' / 'q-r1.jsonl', fn)


def g(out):
    with open(out / 'run-log.jsonl', 'a') as fh:
        fh.write(json.dumps({'arm': 'd1', 'mode': 'seq', 'round': 1, 'exit': 0}) + '\n')


def h(out):
    path = out / 'run-log.jsonl'
    xs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    for x in xs:
        if (x['arm'], x['mode']) == ('d4', 'unipoll'):
            x['exit'] = -11
    path.write_text(''.join(json.dumps(x) + '\n' for x in xs))


def i(out):
    def fn(r):
        if r['rec'] == 'measured':
            r['ops'][0]['atReturn']['selText'] = ''
        return r
    rewrite(out / 'd5' / 'unipoll-r1.jsonl', fn)
    rewrite(out / 'd5' / 'unipoll-r1.jsonl', lambda r: {**r, 'rec': 'done-not'} if r['rec'] == 'done' else r)


def two_rounds(out):
    for arm in json.loads((out / 'arms.json').read_text()):
        d = out / arm['name']
        for mode in ('seq', 'q', 'unipoll'):
            for ext in ('jsonl', 'fodt.gz', 'stderr'):
                if (d / f'{mode}-r1.{ext}').exists():
                    shutil.copy(d / f'{mode}-r1.{ext}', d / f'{mode}-r2.{ext}')
    path = out / 'run-log.jsonl'
    xs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    path.write_text(''.join(json.dumps(x) + '\n' for x in xs + [{**x, 'round': 2} for x in xs]))


def b2(out):
    import gzip
    two_rounds(out)
    p = out / 'd3' / 'unipoll-r2.fodt.gz'
    p.write_bytes(gzip.compress(gzip.decompress(p.read_bytes()).replace(b'axbcd', b'xabcd')))


def j(out):
    def fn(r):
        if r['rec'] == 'measured':
            r['callbacks'] = [c for c in r['callbacks'] if c.get('payload') != '.uno:Bold=true']
        return r
    rewrite(out / 'd4' / 'unipoll-r1.jsonl', fn)


CASES = [('baseline (the smoke as recorded)', lambda out: None),
         ('(e) F1 a records-only D7 cell missing', e),
         ('(f) F1 D7 q trigger never fired', f),
         ('(g) F2 a cell with two run-log entries', g),
         ('(h) F2 a child exit -11 after its records', h),
         ('(i) F3 an unclean unipoll cell that would fail D8', i),
         ("(j) ruling 2: d4's Bold left no presence witness", j),
         ('two-round control (round 1 copied as round 2)', two_rounds),
         ("(b') ruling 1 §2.6 (b): unipoll rounds disagree", b2)]
ROUNDS = {'two-round control (round 1 copied as round 2)': 2, "(b') ruling 1 §2.6 (b): unipoll rounds disagree": 2}


def main(old_path, new_path, smoke):
    old, new = load(old_path, 'old_reader'), load(new_path, 'new_reader')
    print(f"{'case':52} {'HEAD':18} fixed")
    for label, mutate in CASES:
        row = []
        for mod in (old, new):
            with tempfile.TemporaryDirectory() as tmp:
                out = pathlib.Path(tmp) / 'out'
                shutil.copytree(smoke, out)
                keep_last(out)
                mutate(out)
                row.append(mod.judge(out, ROUNDS.get(label, 1))[0])
        print(f'{label:52} {row[0]:18} {row[1]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
