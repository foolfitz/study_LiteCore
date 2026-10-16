#!/usr/bin/env python3
"""Run the finding-142 native arms: every arm x every round, one process at a time.

Usage:
  python3 -I run_arms.py --binary BIN --install DIR --fixtures DIR --out DIR --work DIR
                         [--runs 3] [--only ARM[,ARM...]]

Each (arm, round) is its own process, under `nice -n 10`, with a fresh empty user
profile and its own copy of the fixture (LibreOffice writes a lock file next to
what it loads). Rounds are run-major (round 1 of every arm, then round 2, ...).
Writes out/<arm>/r<N>.jsonl, r<N>.stderr, r<N>.fodt.gz (only arms that save),
out/arms.json (the arm table below, for the reader) and appends one line per
process to out/run-log.jsonl.
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

CH = 1028 | 0x2000   # Ctrl+Home: css::awt::Key::HOME | KEY_MOD1
CE = 1029 | 0x2000   # Ctrl+End
HOME, END, DOWN, UP, LEFT, RIGHT = 1028, 1029, 1024, 1025, 1026, 1027
BKSP, DEL = 1283, 1286

ARMS = []


def arm(name, fixture, script, group, note, tool='main'):
    ARMS.append({'name': name, 'fixture': fixture, 'script': script, 'group': group, 'note': note,
                 'saves': ',S' in script or script.startswith('S'), 'tool': tool})


def presses(label, code, n):
    return ','.join(f'M{label}{i + 1}={code}' for i in range(n))


MID = f'k{DOWN},k{RIGHT}x5'  # plain3: "Bravo|second paragraph" (P2, offset 5)

# arm 1, 2, 3
arm('a1-home-mid', 'plain3', f'{MID},Mch={CH},L', '1', 'Ctrl+Home from mid-text (P2 offset 5)')
arm('a2-end-mid', 'plain3', f'{MID},Mce={CE},L', '2', 'Ctrl+End from mid-text (P2 offset 5)')
arm('a3-home-at-start', 'plain3', f'k{DOWN},k{UP},Mch={CH},L', '3', 'Ctrl+Home with the caret placed at P1 offset 0 (Down, Up)')
arm('a3-home-after-load', 'plain3', f'Mch={CH},L', '3', 'Ctrl+Home right after load, no placement')
arm('a3-end-at-end', 'plain3', f'k{DOWN}x2,k{END},Mce={CE},L', '3', 'Ctrl+End with the caret placed at the end of P3 (Down x2, End)')
arm('a3-home-twice', 'plain3', f'{MID},{presses("ch", CH, 2)},L', '3', 'Ctrl+Home twice from mid-text (second press at the start)')
arm('a3-end-twice', 'plain3', f'{MID},{presses("ce", CE, 2)},L', '3', 'Ctrl+End twice from mid-text (second press at the end)')

# arm 4: table in the middle (3x3), text before and after
A1MID = f'k{DOWN},k{RIGHT}x2'               # "A1| text"
B2MID = f'k{DOWN}x2,k{END},k{RIGHT}x3'      # A2 end, Right -> B2 start, Right x2 -> "B2| text"
for n in (1, 2, 3):
    arm(f't-home-A1-n{n}', 'table-mid', f'{A1MID},{presses("ch", CH, n)},L', '4', f'Ctrl+Home x{n} from mid first cell (A1 offset 2)')
    arm(f't-home-B2-n{n}', 'table-mid', f'{B2MID},{presses("ch", CH, n)},L', '4', f'Ctrl+Home x{n} from mid middle cell (B2 offset 2)')
    arm(f't-end-A1-n{n}', 'table-mid', f'{A1MID},{presses("ce", CE, n)},L', '4', f'Ctrl+End x{n} from mid first cell (A1 offset 2)')
    arm(f't-end-B2-n{n}', 'table-mid', f'{B2MID},{presses("ce", CE, n)},L', '4', f'Ctrl+End x{n} from mid middle cell (B2 offset 2)')

# arm 5: a document that starts / ends with a table
for n in (1, 2, 3):
    arm(f'tf-home-n{n}', 'table-first', f'k{DOWN}x2,k{RIGHT}x4,{presses("ch", CH, n)},L', '5',
        f'table-first doc: Ctrl+Home x{n} from body text after the table ("Body| after table")')
    arm(f'tl-end-n{n}', 'table-last', f'k{DOWN},k{RIGHT}x4,{presses("ce", CE, n)},S,L', '5',
        f'table-last doc: Ctrl+End x{n} from body text before the table ("Body| before table"); save')

# arm 6: ranges made by the engine's text-handles path (RESET+START at a, END at b)
ONE = f'k{DOWN},k{RIGHT}x6,rp2a,k{RIGHT}x6,rp2b,sp2a:p2b'                         # "second"
CROSS = f'k{DOWN},k{RIGHT}x6,rp2a,k{DOWN},k{HOME},k{RIGHT}x7,rp3b'                # P2.6 .. P3.7
arm('r-one-home', 'plain3', f'{ONE},Mch={CH},L', '6', 'single-paragraph range "second" (forward), Ctrl+Home')
arm('r-one-end', 'plain3', f'{ONE},Mce={CE},L', '6', 'single-paragraph range "second" (forward), Ctrl+End')
arm('r-cross-home', 'plain3', f'{CROSS},sp2a:p3b,Mch={CH},L', '6', 'cross-paragraph range P2.6-P3.7 (forward), Ctrl+Home')
arm('r-cross-end', 'plain3', f'{CROSS},sp2a:p3b,Mce={CE},L', '6', 'cross-paragraph range P2.6-P3.7 (forward), Ctrl+End')
arm('r-bwd-home', 'plain3', f'{CROSS},sp3b:p2a,Mch={CH},L', '6', 'cross-paragraph range P3.7-P2.6 (backward), Ctrl+Home')
arm('r-bwd-end', 'plain3', f'{CROSS},sp3b:p2a,Mce={CE},L', '6', 'cross-paragraph range P3.7-P2.6 (backward), Ctrl+End')

# arm 7: header and footer
HDR = f'u.uno:JumpToHeader,k{RIGHT}x6'   # "Header| line text"
FTR = f'u.uno:JumpToFooter,k{RIGHT}x6'   # "Footer| line text"
for n in (1, 2, 3):
    arm(f'hf-home-hdr-n{n}', 'header-footer', f'{HDR},{presses("ch", CH, n)},L', '7',
        f'caret in the page header (.uno:JumpToHeader, Right x6), Ctrl+Home x{n}')
    arm(f'hf-end-ftr-n{n}', 'header-footer', f'{FTR},{presses("ce", CE, n)},L', '7',
        f'caret in the page footer (.uno:JumpToFooter, Right x6), Ctrl+End x{n}')
arm('hf-home-hdr-click', 'header-footer',
    f'{MID},rbody,{HDR},rhdr,cbody,chdr,Mch={CH},L', '7',
    'header reached by an engine click at the header caret point (found via JumpToHeader), Ctrl+Home')

# extra: a section in the middle (GoStart/GoEnd try the current section first)
for n in (1, 2, 3):
    arm(f'sec-home-n{n}', 'section-mid', f'k{DOWN}x2,k{RIGHT}x6,{presses("ch", CH, n)},L', 'x-section',
        f'caret mid "Inside section two", Ctrl+Home x{n}')
    arm(f'sec-end-n{n}', 'section-mid', f'k{DOWN},k{RIGHT}x6,{presses("ce", CE, n)},L', 'x-section',
        f'caret mid "Inside section one", Ctrl+End x{n}')

# arm 8: the finding-142 red sequence, natively
arm('red-home-bksp', 'plain3', f'{MID},Mch={CH},Mbksp={BKSP},S,L', '8', 'mid-text, Ctrl+Home, then Backspace; save')
arm('red-end-del', 'plain3', f'{MID},Mce={CE},Mdel={DEL},S,L', '8', 'mid-text, Ctrl+End, then Delete; save')
arm('red-home-k1', 'plain3', f'{MID},Mch={CH},Kk1,L', '8', 'mid-text, Ctrl+Home, then K1 for Backspace (Shift+Left)')
arm('red-end-k1r', 'plain3', f'{MID},Mce={CE},Jk1r,L', '8', 'mid-text, Ctrl+End, then K1 for Delete (Shift+Right)')
arm('b2b-home-bksp', 'plain3', f'{MID},Bch+bksp={CH}+{BKSP},S,L', '8',
    'mid-text, Ctrl+Home and Backspace posted back-to-back (no wait); save')
arm('b2b-end-del', 'plain3', f'{MID},Bce+del={CE}+{DEL},S,L', '8',
    'mid-text, Ctrl+End and Delete posted back-to-back (no wait); save')

# arm 9: positive controls
arm('ctl-home', 'plain3', f'{MID},Mhome={HOME},L', '9', 'plain Home from mid-text')
arm('ctl-down', 'plain3', f'{MID},Mdown={DOWN},L', '9', 'plain Down from mid-text')
arm('ctl-bksp', 'plain3', f'{MID},Mbksp={BKSP},S,L', '9', 'plain Backspace from mid-text; save (the comparison must go red)')
arm('ctl-k1', 'plain3', f'{MID},Kk1,L', '9', 'K1 (Shift+Left) from mid-text (must select one character)')
arm('ctl-k1r', 'plain3', f'{MID},Jk1r,L', '9', 'K1 (Shift+Right) from mid-text (must select one character)')

# extra: L-C-number-or-indent first paragraphs
arm('x-bullet-home-bksp', 'bullet', f'k{DOWN},k{HOME},k{RIGHT}x2,Mch={CH},Mbksp={BKSP},S,L', 'x-lc',
    'bulleted first paragraph (review 6 fixture): caret "Be|ta two", Ctrl+Home, Backspace; save')
arm('x-numbered-home-bksp', 'numbered-first', f'k{DOWN},k{HOME},k{RIGHT}x3,Mch={CH},Mbksp={BKSP},S,L', 'x-lc',
    'numbered first paragraph: caret "Pla|in second", Ctrl+Home, Backspace; save')
arm('x-indent-home-bksp', 'indent', f'k{DOWN},k{HOME},k{RIGHT}x3,Mch={CH},Mbksp={BKSP},S,L', 'x-lc',
    'first-line-indent first paragraph (review 6 fixture): caret "Sec|ond", Ctrl+Home, Backspace; save')

arm('x-indent-home', 'indent', f'k{DOWN},k{HOME},k{RIGHT}x3,Mch={CH},L', 'x-lc',
    'first-line-indent first paragraph: Ctrl+Home only, then the locator (names where Ctrl+Home lands); '
    'added after the main run started')

# placement checks: every starting caret above, followed only by the locator, so
# each "before" rectangle in a measured arm maps to a text position
arm('place-plain3-mid', 'plain3', f'{MID},L', 'P', 'placement used by arms 1, 2, 8, 9')
arm('place-plain3-start', 'plain3', f'k{DOWN},k{UP},L', 'P', 'placement of a3-home-at-start')
arm('place-plain3-end', 'plain3', f'k{DOWN}x2,k{END},L', 'P', 'placement of a3-end-at-end')
arm('place-table-A1', 'table-mid', f'{A1MID},L', 'P', 'placement of t-*-A1-*')
arm('place-table-B2', 'table-mid', f'{B2MID},L', 'P', 'placement of t-*-B2-*')
arm('place-tf-body', 'table-first', f'k{DOWN}x2,k{RIGHT}x4,L', 'P', 'placement of tf-home-*')
arm('place-tl-body', 'table-last', f'k{DOWN},k{RIGHT}x4,L', 'P', 'placement of tl-end-*')
arm('place-hdr', 'header-footer', f'{HDR},L', 'P', 'placement of hf-home-hdr-n*')
arm('place-ftr', 'header-footer', f'{FTR},L', 'P', 'placement of hf-end-ftr-n*')
arm('place-hdr-click', 'header-footer', f'{MID},rbody,{HDR},rhdr,cbody,chdr,L', 'P', 'placement of hf-home-hdr-click')
arm('place-sec-two', 'section-mid', f'k{DOWN}x2,k{RIGHT}x6,L', 'P', 'placement of sec-home-*')
arm('place-sec-one', 'section-mid', f'k{DOWN},k{RIGHT}x6,L', 'P', 'placement of sec-end-*')
arm('place-bullet', 'bullet', f'k{DOWN},k{HOME},k{RIGHT}x2,L', 'P', 'placement of x-bullet-home-bksp')
arm('place-numbered', 'numbered-first', f'k{DOWN},k{HOME},k{RIGHT}x3,L', 'P', 'placement of x-numbered-home-bksp')
arm('place-indent', 'indent', f'k{DOWN},k{HOME},k{RIGHT}x3,L', 'P', 'placement of x-indent-home-bksp')


# queued pair (tool f142_native_queued_pair.cpp, binary given by --binary-queued):
# trigger Right moves P2.4 -> P2.5 ("Bravo|"), and the pair is posted from inside
# that move's INVALIDATE_VISIBLE_CURSOR callback, so both keys are queued in core
# before core runs either. Added after the main run started; see README.
Q4 = f'k{DOWN},k{RIGHT}x4'
arm('q-home-bksp', 'plain3', f'{Q4},Qch+bksp={CH}+{BKSP}@{RIGHT},S,L', 'Q',
    'Ctrl+Home and Backspace both queued in core (posted inside a callback); save', tool='queued')
arm('q-end-del', 'plain3', f'{Q4},Qce+del={CE}+{DEL}@{RIGHT},S,L', 'Q',
    'Ctrl+End and Delete both queued in core (posted inside a callback); save', tool='queued')
arm('q-ctl-home-bksp', 'plain3', f'{Q4},Qhome+bksp={HOME}+{BKSP}@{RIGHT},S,L', 'Q',
    'control: plain Home and Backspace both queued the same way (no accelerator involved); save', tool='queued')

# queued-pair discriminator (added with the fixture numbered-second after the
# first queued arms read FIFO): Down from P1.0 lands at the start of the numbered
# P2, where Writer's key handler does Backspace itself (NumOrNoNum) rather than
# through the accelerator table. If Ctrl+Home's own dispatch is posted as a later
# event, a Backspace queued behind it acts on P2 before the caret moves.
arm('place-numsecond', 'numbered-second', f'k{DOWN},L', 'P', 'placement of the *-at-num arms')
arm('ctl-bksp-at-num', 'numbered-second', f'k{DOWN},Mbksp={BKSP},S,L', 'Q',
    'control: what Writer\'s own Backspace does at the start of the numbered P2; save')
arm('b2b-home-bksp-at-num', 'numbered-second', f'k{DOWN},Bch+bksp={CH}+{BKSP},S,L', 'Q',
    'caret at the start of the numbered P2, Ctrl+Home and Backspace posted back-to-back; save')
arm('q-home-bksp-at-num', 'numbered-second', f'Qch+bksp={CH}+{BKSP}@{DOWN},S,L', 'Q',
    'trigger Down (P1.0 -> start of numbered P2), Ctrl+Home and Backspace queued inside its callback; save',
    tool='queued')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--binary', required=True, help='f142_native_ctrl_home_end.cpp build (tool "main")')
    ap.add_argument('--binary-queued', default='', help='f142_native_queued_pair.cpp build (tool "queued")')
    ap.add_argument('--install', required=True)
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    work = pathlib.Path(a.work)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'arms.json').write_text(json.dumps(ARMS, indent=1) + '\n')
    only = set(filter(None, a.only.split(',')))
    binaries = {'main': a.binary, 'queued': a.binary_queued}
    arms = [x for x in ARMS if (not only or x['name'] in only) and binaries[x['tool']]]
    env = dict(os.environ)
    env['SAL_USE_VCLPLUGIN'] = 'svp'
    env.pop('SAL_LOK_OPTIONS', None)
    log = (out / 'run-log.jsonl').open('a')
    for r in range(1, a.runs + 1):
        for x in arms:
            d = work / f"{x['name']}-r{r}"
            if d.exists():
                shutil.rmtree(d)
            (d / 'prof').mkdir(parents=True)
            fx = d / f"{x['fixture']}.fodt"
            shutil.copyfile(pathlib.Path(a.fixtures) / f"{x['fixture']}.fodt", fx)
            saved = d / 'saved.fodt'
            od = out / x['name']
            od.mkdir(exist_ok=True)
            cmd = ['nice', '-n', '10', binaries[x['tool']], a.install, f'file://{d}/prof', f'file://{fx}',
                   x['script'], f'file://{saved}']
            start = utc()
            t0 = time.monotonic()
            with open(od / f'r{r}.jsonl', 'w') as so, open(od / f'r{r}.stderr', 'w') as se:
                rc = subprocess.run(cmd, stdout=so, stderr=se, env=env, timeout=300).returncode
            dur = time.monotonic() - t0
            if saved.exists():
                with open(saved, 'rb') as f, gzip.GzipFile(od / f'r{r}.fodt.gz', 'wb', mtime=0) as g:
                    g.write(f.read())
            log.write(json.dumps({'arm': x['name'], 'round': r, 'start': start, 'seconds': round(dur, 1),
                                  'exit': rc, 'loadavg': open('/proc/loadavg').read().split()[:3],
                                  'cmd': cmd}) + '\n')
            log.flush()
            print(f"{start} r{r} {x['name']}: exit {rc}, {dur:.1f}s", flush=True)
            shutil.rmtree(d)


if __name__ == '__main__':
    main()
