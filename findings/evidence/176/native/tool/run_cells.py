#!/usr/bin/env python3
"""Run finding 176's native cells (engine item C): every cell x every round, one process at a time, mode uni1ai.

Usage:
  python3 -I run_cells.py --binary BIN --install DIR --fixtures DIR --out DIR --work DIR [--runs 5] [--only C[,C]]

The runner of the N1 arms (link-batch-v23/native/ordered-commands/tool/run_arms.py) cut to one mode: uni1ai is the
engine's cadence (one command per poll, anyInput answering "a reply is pending" until the first poll after the
command returns, SPEC-M3-ordered-commands §5.2).  Each (cell, round) is its own process under `nice -n 10`, with a
fresh empty profile and its own copy of the fixture; SAL_USE_VCLPLUGIN=svp, SAL_LOK_OPTIONS=unipoll.  Rounds are
run-major.  --out must not exist.  Writes out/cells.json, out/identity.json, out/<cell>/r<N>.jsonl, .stderr and
.fodt.gz, and one line per process in out/run-log.jsonl.
"""
import argparse
import datetime
import gzip
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import time

DOWN, HOME, END, RETURN = 1024, 1028, 1029, 1280
MOD1 = 0x2000
LIST_ON = '{"On":{"type":"boolean"`"value":true}}'     # ` = comma (oc_native.cpp); kListOnArguments
LIST_OFF = '{"On":{"type":"boolean"`"value":false}}'   # the sham: nothing to switch off on a plain paragraph
HEADING = ('{"Style":{"type":"string"`"value":"Heading 1"}`'
           '"FamilyName":{"type":"string"`"value":"ParagraphStyles"}}')   # styleApplyArguments(true)

CELLS = []


def cell(name, klass, fixture, setup, trigger, op, target, expect, note):
    """klass A: the witness must say applied; N: nothing applies, the witness must not say so; R: recorded only."""
    CELLS.append({'name': name, 'class': klass, 'fixture': fixture,
                  'script': (setup + ',' if setup else '') + f'X{name}@{trigger}={op},S',
                  'target': target, 'expect': expect, 'note': note})


F_BULLET = f'F.uno:DefaultBullet|{LIST_ON}'
cell('a1-text-mid', 'A', 'text-mid.fodt', f'k{DOWN}', END, F_BULLET, 1, 'bullet',
     'control: a paragraph with text (the verified path today)')
cell('a2-empty-mid', 'A', 'empty-mid.fodt', f'k{DOWN}', END, F_BULLET, 1, 'bullet',
     "finding 046's cell: an empty paragraph with a paragraph after it")
cell('a3-enter-mid', 'A', 'two-plain.fodt', f'k{END}', RETURN, F_BULLET, 1, 'bullet',
     "F3's recipe shape: End of the first paragraph, Enter (the trigger), bullet the new empty one")
cell('a4-empty-last', 'A', 'empty-last.fodt', f'k{DOWN}', END, F_BULLET, 1, 'bullet',
     "083's path: the empty paragraph is the last one")
cell('a5-blank-one', 'A', 'blank-one.odt', '', END, F_BULLET, 0, 'bullet',
     "083/173's path: the host's blank template, one empty paragraph")
F_SHAM = f'F.uno:DefaultBullet|{LIST_OFF}'
cell('n1-sham-empty-mid', 'N', 'empty-mid.fodt', f'k{DOWN}', END, F_SHAM, 1, 'none',
     "the engine's sequence with a dispatch that changes nothing (On:false on a plain paragraph)")
cell('n2-sham-empty-before-list', 'N', 'empty-before-list.fodt', f'k{DOWN}', END, F_SHAM, 1, 'none',
     'the same, and the overshoot reaches a bulleted paragraph')
cell('n3-sham-empty-after-list', 'N', 'empty-after-list.fodt', f'k{DOWN}', END, F_SHAM, 1, 'none',
     "the same, the paragraph above is a bullet (046's upward counterexample's neighbour)")
cell('r1-noop-empty-bulleted', 'R', 'empty-bulleted-mid.fodt', f'k{DOWN}', END, F_BULLET, 1, 'bullet',
     'bullet on an empty paragraph that is already a bullet (finding 030 predicts no item)')
cell('r2-dispatch-only-empty-mid', 'R', 'empty-mid.fodt', f'k{DOWN}', END, f'U.uno:DefaultBullet|{LIST_ON}', 1,
     'bullet', 'attribution: the dispatch alone, no readback')
cell('r3-number-empty-mid', 'R', 'empty-mid.fodt', f'k{DOWN}', END, f'F.uno:DefaultNumbering|{LIST_ON}', 1,
     'number', 'set-list-ordered on the 046 cell')
cell('r4-none-empty-bulleted', 'R', 'empty-bulleted-mid.fodt', f'k{DOWN}', END, 'F.uno:RemoveBullets', 1, 'none',
     'set-list-none on an empty bullet with a paragraph after it')
cell('r5-heading-empty-mid', 'R', 'empty-mid.fodt', f'k{DOWN}', END, f'F.uno:StyleApply|{HEADING}', 1, 'heading',
     'set-paragraph-heading on the 046 cell')
cell('r6-bullet-empty-before-list', 'R', 'empty-before-list.fodt', f'k{DOWN}', END, F_BULLET, 1, 'bullet',
     "046's unmeasured variant: an empty paragraph followed by a list item")

# Amendment 1 (PREDICTION.md, after the smoke): the G variant -- F without the restore before .uno:SelectText --
# on the deciding cells, recorded only.
G_BULLET = f'G.uno:DefaultBullet|{LIST_ON}'
G_SHAM = f'G.uno:DefaultBullet|{LIST_OFF}'
for _base in [c for c in CELLS if c['class'] in ('A', 'N')]:
    _op = _base['script'].split('=', 1)[1].rsplit(',S', 1)[0]
    _g = G_BULLET if _op == F_BULLET else G_SHAM
    CELLS.append({**_base, 'name': 'g-' + _base['name'], 'class': 'R',
                  'script': _base['script'].replace(f"X{_base['name']}@", f"Xg-{_base['name']}@").replace(_op, _g),
                  'note': 'G variant (no restore before the select): ' + _base['note']})


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    for name in ('--binary', '--install', '--fixtures', '--out', '--work'):
        ap.add_argument(name, required=True)
    ap.add_argument('--runs', type=int, default=5)
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    out, work, fixtures = pathlib.Path(a.out), pathlib.Path(a.work), pathlib.Path(a.fixtures)
    out.mkdir(parents=True, exist_ok=False)
    only = set(filter(None, a.only.split(',')))
    cells = [c for c in CELLS if not only or c['name'] in only]
    (out / 'cells.json').write_text(json.dumps(cells, indent=1) + '\n')
    tool = pathlib.Path(__file__).resolve().parent
    identity = {'binary': str(pathlib.Path(a.binary).resolve()), 'binarySha256': digest(a.binary),
                'install': a.install, 'versionrc': (pathlib.Path(a.install) / 'versionrc').read_text(),
                'sources': {n: digest(tool / n) for n in ('f176_native.cpp', 'run_cells.py', 'make_fixtures.py')},
                'fixtures': {n: digest(fixtures / n) for n in sorted({c['fixture'] for c in cells})},
                'argv': os.sys.argv}
    (out / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    log = (out / 'run-log.jsonl').open('a')
    for r in range(1, a.runs + 1):
        for c in cells:
            env = dict(os.environ)
            env['SAL_USE_VCLPLUGIN'] = 'svp'
            env['SAL_LOK_OPTIONS'] = 'unipoll'
            env.pop('OC_A11Y', None)
            d = work / f"{c['name']}-r{r}"
            if d.exists():
                shutil.rmtree(d)
            (d / 'prof').mkdir(parents=True)
            fx = d / c['fixture']
            shutil.copyfile(fixtures / c['fixture'], fx)
            saved = d / 'saved.fodt'
            od = out / c['name']
            od.mkdir(exist_ok=True)
            cmd = ['nice', '-n', '10', a.binary, 'uni1ai', a.install, f'file://{d}/prof', f'file://{fx}',
                   c['script'], f'file://{saved}']
            start = utc()
            t0 = time.monotonic()
            with open(od / f'r{r}.jsonl', 'w') as so, open(od / f'r{r}.stderr', 'w') as se:
                try:
                    rc = subprocess.run(cmd, stdout=so, stderr=se, env=env, timeout=300).returncode
                except subprocess.TimeoutExpired:
                    rc = 'timeout'
            dur = time.monotonic() - t0
            if saved.exists():
                with open(saved, 'rb') as f, gzip.GzipFile(od / f'r{r}.fodt.gz', 'wb', mtime=0) as g:
                    g.write(f.read())
            log.write(json.dumps({'cell': c['name'], 'round': r, 'start': start, 'seconds': round(dur, 1),
                                  'exit': rc, 'loadavg': open('/proc/loadavg').read().split()[:3],
                                  'cmd': cmd}) + '\n')
            log.flush()
            print(f"{start} r{r} {c['name']}: exit {rc}, {dur:.1f}s", flush=True)
            shutil.rmtree(d)


if __name__ == '__main__':
    main()
