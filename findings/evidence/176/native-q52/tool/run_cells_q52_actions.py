#!/usr/bin/env python3
"""Run amendment 2's cells (../PREDICTION.md) with run_cells.py's runner, unedited.

Usage: python3 -I run_cells_q52_actions.py --binary BIN --install DIR --fixtures DIR --out DIR --work DIR

Imports run_cells_q52.py for its key codes and dispatch strings (its own 27-cell table is discarded), replaces
run_cells.py's cell table with this one and calls its main(); then writes identity-q52-actions.json.
"""
import hashlib
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('run_cells_q52', HERE / 'run_cells_q52.py')
q52 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(q52)
rc, DOWN, END = q52.rc, q52.DOWN, q52.END
NO_SUCH_STYLE = ('{"Style":{"type":"string"`"value":"LiteCore No Such Style"}`'
                 '"FamilyName":{"type":"string"`"value":"ParagraphStyles"}}')
DISPATCH = {'number': q52.ACTIONS['number'], 'none': q52.ACTIONS['none'], 'heading': q52.ACTIONS['heading'],
            'body': q52.ACTIONS['body'], 'number-off': f'.uno:DefaultNumbering|{rc.LIST_OFF}',
            'no-such-style': f'.uno:StyleApply|{NO_SUCH_STYLE}', 'bullet-on': q52.ACTIONS['bullet']}
cells = []


def cell(name, klass, fixture, dispatch, judged_as, note):
    cells.append({'name': name, 'class': klass, 'group': 'V4', 'fixture': fixture, 'action': judged_as,
                  'dispatch': dispatch,
                  'script': f'k{DOWN},X{name}@{END}=H{DISPATCH[dispatch]}~.uno:CharLeftSel,L,S',
                  'target': 'last', 'expect': judged_as, 'note': note})


cell('cl-num-empty-last', 'A', 'empty-last.fodt', 'number', 'number', 'set-list-ordered on the empty last paragraph')
cell('cl-none-bulleted-last', 'A', 'bulleted-last.fodt', 'none', 'none', 'set-list-none on an empty last bullet')
cell('cl-head-empty-last', 'A', 'empty-last.fodt', 'heading', 'heading', 'set-paragraph-heading on the empty last one')
cell('cl-body-heading-last', 'A', 'heading-last.fodt', 'body', 'body', 'set-paragraph-body on an empty last heading')
cell('cl-nnum-after-number', 'N', 'number-then-empty-last.fodt', 'number-off', 'number',
     'the trap: the previous block is ol, nothing applies')
cell('cl-nhead-after-heading', 'N', 'heading-then-empty-last.fodt', 'no-such-style', 'heading',
     'the trap: the previous block is h1, nothing applies')
cell('cl-nnone-noop-bulleted-last', 'N', 'bulleted-last.fodt', 'bullet-on', 'none',
     'judged as set-list-none; the dispatch is a no-op on the bullet')
cell('cl-nbody-sham-heading-last', 'N', 'heading-last.fodt', 'no-such-style', 'body',
     'judged as set-paragraph-body; nothing applies to the heading')


def main():
    rc.CELLS[:] = cells
    rc.main()
    args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    out, fixtures = pathlib.Path(args['--out']), pathlib.Path(args['--fixtures'])
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'identity-q52-actions.json').write_text(json.dumps({
        'sources': {n: digest(HERE / n) for n in ('f083_native.cpp', 'run_cells_q52.py', 'run_cells_q52_actions.py',
                                                  'make_fixtures_q52_actions.py')},
        'fixtures': {p.name: digest(p) for p in sorted(fixtures.iterdir()) if p.name != 'SHA256SUMS'}},
        indent=2) + '\n')


if __name__ == '__main__':
    main()
