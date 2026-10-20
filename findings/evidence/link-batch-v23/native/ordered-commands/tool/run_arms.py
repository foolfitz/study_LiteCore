#!/usr/bin/env python3
"""Run the ordered-commands native arms (fable ruling 1 §2.6, v23): every arm x
every mode x every round, one process at a time.

Usage:
  python3 -I run_arms.py --binary BIN --install DIR --fixtures DIR --out DIR --work DIR
                         [--runs 5] [--only ARM[,ARM...]] [--modes seq,q,unipoll]

Each (arm, mode, round) is its own process, under `nice -n 10`, with a fresh empty
user profile and its own copy of the fixture. Rounds are run-major (round 1 of
every arm and mode, then round 2, ...), so a slow drift spreads over all cells.
The environment is set per mode: SAL_USE_VCLPLUGIN=svp always; SAL_LOK_OPTIONS
removed for seq and q, set to `unipoll` for unipoll (the harness records it in
its env record, and the reader checks it). Writes out/<arm>/<mode>-r<N>.jsonl,
.stderr and .fodt.gz, out/arms.json, and one line per process in out/run-log.jsonl.
"""
import argparse
import datetime
import gzip
import json
import os
import pathlib
import shutil
import subprocess
import time

LEFT, RIGHT, DOWN, HOME, END = 1026, 1027, 1024, 1028, 1029
BKSP, DEL = 1283, 1286
SH, MOD1 = 0x1000, 0x2000
BOLD_TRUE = '{"Bold":{"type":"boolean"`"value":true}}'   # ` = comma (oc_native.cpp)

MODES = ('seq', 'q', 'unipoll', 'uni1', 'uni1ai')
ARMS = []


def arm(name, fixture, script, note, decides=True):
    ARMS.append({'name': name, 'fixture': fixture, 'script': script, 'note': note, 'decides': decides})


# Decision arms (ruling §2.6 table). The trigger key moves the caret, so the q
# mode's in-callback firing has a cursor callback to fire on; every mode posts it.
arm('d1', 'numbered-second', f'Xd1@{DOWN}=K{HOME | MOD1};K{BKSP},S,L',
    "142's pair: trigger Down (P1.0 -> start of the numbered P2); Ctrl+Home; Backspace")
arm('d2', 'abcd', f'k{RIGHT}x3,Xd2@{RIGHT}=K{LEFT};U.uno:Delete,S,L',
    '137 delete: trigger Right (3 -> 4, the end); Left; .uno:Delete (sync)')
arm('d2p', 'abcd', f'k{RIGHT}x1,Xd2p@{RIGHT}=K{RIGHT};U.uno:SwBackspace,S,L',
    '137 delete, backward: trigger Right (1 -> 2, after b); Right; .uno:SwBackspace (sync)')
arm('d3', 'abcd', f'k{RIGHT}x1,Xd3@{LEFT}=K{RIGHT};Px,S,L',
    '137 typing: trigger Left (1 -> 0); Right; paste "x" (sync)')
arm('d4', 'abcd', f'Xd4@{RIGHT | SH}=K{LEFT};U.uno:Bold|{BOLD_TRUE},S,L',
    '137 format: trigger Shift+Right (selects a); Left; .uno:Bold with the engine\'s explicit true (sync)')
arm('d5', 'abcd', f'k{RIGHT}x3,Xd5@{RIGHT}=K{LEFT | SH};U.uno:Delete,S,L',
    'extend + delete: trigger Right (3 -> 4); Shift+Left; .uno:Delete (sync)')
arm('d6', 'abcd', f'k{RIGHT}x3,rpc,k{LEFT}x2,Xd6@{LEFT}=Cpc;Px,S,L',
    'mouse: point pc recorded at offset 3; trigger Left (1 -> 0); click at pc; paste "x" (sync)')
# D7: the user's own key at positions (i)-(iii) and a plain first paragraph; decides nothing
arm('d7i', 'bullet', f'Xd7i@{LEFT}=K{DEL},S,L',
    '(i) trigger an unshifted Left at the document start, which puts the caret in front of P1\'s label '
    '(review 6: x 2138 -> 1778, review-6-engine-code.md:23); Delete', decides=False)
arm('d7ii', 'bullet', f'k{RIGHT},Xd7ii@{LEFT}=K{BKSP},S,L',
    '(ii) trigger Left (1 -> 0, a bulleted first paragraph); Backspace', decides=False)
arm('d7iii', 'indent', f'k{RIGHT},Xd7iii@{LEFT}=K{BKSP},S,L',
    '(iii) trigger Left (1 -> 0, a first-line indent); Backspace', decides=False)
arm('d7plain', 'plain3', f'k{RIGHT},Xd7plain@{LEFT}=K{BKSP},S,L',
    'plain first paragraph: trigger Left (1 -> 0); Backspace', decides=False)


# N1 (SPEC-M3-ordered-commands §9.1, pinned at b9080313): run with --arms-set n1. The D arms above
# in uni1ai give N1a and N1b; tleave is N1b's positive control (uni1ai); join200 is N1c (uni1 and uni1ai).
N1_ARMS = [
    {'name': 'tleave', 'fixture': 'table-leave', 'script': f'Xtleave@{RIGHT}=K{DOWN},S,L',
     'note': 'N1b positive control: caret in A1, trigger Right; Down leaves the table', 'decides': False},
    {'name': 'join200', 'fixture': 'long200', 'script': f'Xjoin200@{DOWN}=K{BKSP},S',
     'note': 'N1c: trigger Down (P1.0 -> P2 start); Backspace joins P2 into P1 near the top of 200 paragraphs',
     'decides': False},
]


# G (SPEC-M3-ordered-commands §15.1; fable ruling 2 §2.1 item 5): the caret-delete witness. Run with
# --arms-set g --modes uni1,seq; the runner sets OC_A11Y=1, so every op records .uno:Undo and the focused
# paragraph immediately before its call and at its return. g1/g2/cjk delete through a run the undo stack
# groups; t1 and e1 are no-op controls (Writer restores at a paragraph start after a table; Delete at the
# document end).
BKSP25 = ';'.join([f'K{BKSP}'] * 25)
G_ARMS = [
    {'name': 'g1', 'fixture': 'underscores', 'script': f'Xg1@{END}={BKSP25},S',
     'note': 'trigger End (caret to the end of Name: + 30 _); 25 x Backspace', 'decides': False},
    {'name': 'g2', 'fixture': 'underscores', 'script': f'k{RIGHT}x5,Xg2@{RIGHT}=' + ';'.join([f'K{DEL}'] * 25) + ',S',
     'note': 'Right x5, trigger Right (caret after "Name: "); 25 x Delete', 'decides': False},
    {'name': 'cjk', 'fixture': 'cjk25', 'script': f'Xcjk@{END}={BKSP25},S',
     'note': 'trigger End (caret after 25 CJK characters); 25 x Backspace', 'decides': False},
    {'name': 't1', 'fixture': 'table-leave', 'script': f'k{DOWN},k{END},Xt1@{HOME}=' + ';'.join([f'K{BKSP}'] * 3) + ',S',
     'note': 'control: Down leaves the table, End; trigger Home (start of "After the table"); 3 x Backspace (Writer restores)',
     'decides': False},
    {'name': 'e1', 'fixture': 'abcd', 'script': f'k{END | MOD1},k{LEFT},Xe1@{RIGHT}=' + ';'.join([f'K{DEL}'] * 3) + ',S',
     'note': 'control: Ctrl+End, Left; trigger Right (the document end); 3 x Delete (nothing to delete)',
     'decides': False},
]


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--binary', required=True)
    ap.add_argument('--install', required=True)
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--runs', type=int, default=5)
    ap.add_argument('--only', default='')
    ap.add_argument('--modes', default='seq,q,unipoll')
    ap.add_argument('--arms-set', choices=('d', 'n1', 'g'), default='d')
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    work = pathlib.Path(a.work)
    out.mkdir(parents=True, exist_ok=True)
    table = {'d': ARMS, 'n1': ARMS + N1_ARMS, 'g': G_ARMS}[a.arms_set]
    (out / 'arms.json').write_text(json.dumps(table, indent=1) + '\n')
    only = set(filter(None, a.only.split(',')))
    modes = [m for m in a.modes.split(',') if m]
    assert all(m in MODES for m in modes), modes
    arms = [x for x in table if not only or x['name'] in only]
    log = (out / 'run-log.jsonl').open('a')
    for r in range(1, a.runs + 1):
        for x in arms:
            for mode in modes:
                env = dict(os.environ)
                env['SAL_USE_VCLPLUGIN'] = 'svp'
                env.pop('SAL_LOK_OPTIONS', None)
                env.pop('OC_A11Y', None)
                if a.arms_set == 'g':
                    env['OC_A11Y'] = '1'
                if mode in ('unipoll', 'uni1', 'uni1ai'):
                    env['SAL_LOK_OPTIONS'] = 'unipoll'
                d = work / f"{x['name']}-{mode}-r{r}"
                if d.exists():
                    shutil.rmtree(d)
                (d / 'prof').mkdir(parents=True)
                fx = d / f"{x['fixture']}.fodt"
                shutil.copyfile(pathlib.Path(a.fixtures) / f"{x['fixture']}.fodt", fx)
                saved = d / 'saved.fodt'
                od = out / x['name']
                od.mkdir(exist_ok=True)
                cmd = ['nice', '-n', '10', a.binary, mode, a.install, f'file://{d}/prof', f'file://{fx}',
                       x['script'], f'file://{saved}']
                start = utc()
                t0 = time.monotonic()
                with open(od / f'{mode}-r{r}.jsonl', 'w') as so, open(od / f'{mode}-r{r}.stderr', 'w') as se:
                    try:
                        rc = subprocess.run(cmd, stdout=so, stderr=se, env=env, timeout=300).returncode
                    except subprocess.TimeoutExpired:
                        rc = 'timeout'
                dur = time.monotonic() - t0
                if saved.exists():
                    with open(saved, 'rb') as f, gzip.GzipFile(od / f'{mode}-r{r}.fodt.gz', 'wb', mtime=0) as g:
                        g.write(f.read())
                log.write(json.dumps({'arm': x['name'], 'mode': mode, 'round': r, 'start': start,
                                      'seconds': round(dur, 1), 'exit': rc,
                                      'loadavg': open('/proc/loadavg').read().split()[:3], 'cmd': cmd}) + '\n')
                log.flush()
                print(f"{start} r{r} {x['name']} {mode}: exit {rc}, {dur:.1f}s", flush=True)
                shutil.rmtree(d)


if __name__ == '__main__':
    main()
