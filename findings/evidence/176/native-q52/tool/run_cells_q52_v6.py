#!/usr/bin/env python3
"""Run amendment 4's cells (../PREDICTION.md) with run_cells.py's runner, unedited.

Usage: python3 -I run_cells_q52_v6.py --binary BIN --install DIR --fixtures DIR --out DIR --work DIR

Takes the four number/none cells from run_cells_q52_actions.py's table unchanged (by name), adds V7's three cells,
replaces run_cells.py's table and calls its main(); then writes identity-q52-v6.json.
"""
import hashlib
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('run_cells_q52_actions', HERE / 'run_cells_q52_actions.py')
act = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(act)
rc, END = act.rc, act.END
DISPATCH = {**act.DISPATCH, 'bullet-off': f'.uno:DefaultBullet|{act.rc.LIST_OFF}'}
CTRL_END = act.q52.CTRL_END
V6 = ('cl-num-empty-last', 'cl-nnum-after-number', 'cl-none-bulleted-last', 'cl-nnone-noop-bulleted-last')
cells = [{**c, 'group': 'V6'} for c in act.cells if c['name'] in V6]
assert sorted(c['name'] for c in cells) == sorted(V6)


def cell(name, klass, fixture, dispatch, note):
    cells.append({'name': name, 'class': klass, 'group': 'V7', 'fixture': fixture, 'action': 'bullet',
                  'dispatch': dispatch,
                  'script': f'k{CTRL_END},k{CTRL_END},X{name}@{END}=H{DISPATCH[dispatch]}~.uno:CharLeftSel,L,S',
                  'target': 'last', 'expect': 'bullet', 'note': note})


cell('cl-long-300', 'A', 'long-then-empty-last.fodt', 'bullet-on', 'CL on 300 lines then the empty last paragraph')
cell('cl-a6-end', 'A', 'empty-empty-last.fodt', 'bullet-on', 'two empty paragraphs at the end, bullet the last')
cell('cl-n6-end', 'N', 'empty-empty-last.fodt', 'bullet-off', 'the sham on the same')


def main():
    rc.CELLS[:] = cells
    rc.main()
    args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    out, fixtures = pathlib.Path(args['--out']), pathlib.Path(args['--fixtures'])
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'identity-q52-v6.json').write_text(json.dumps({
        'sources': {n: digest(HERE / n) for n in ('f083_native.cpp', 'run_cells_q52_actions.py', 'run_cells_q52_v6.py',
                                                  'make_fixtures_q52_v6.py')},
        'fixtures': {p.name: digest(p) for p in sorted(fixtures.iterdir()) if p.name != 'SHA256SUMS'}},
        indent=2) + '\n')


if __name__ == '__main__':
    main()
