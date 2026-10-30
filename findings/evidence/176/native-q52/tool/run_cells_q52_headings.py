#!/usr/bin/env python3
"""Run amendment 3's cells (../PREDICTION.md) with run_cells.py's runner, unedited.

Usage: python3 -I run_cells_q52_headings.py --binary BIN --install DIR --fixtures DIR --out DIR --work DIR [--only C]

Imports run_cells_q52_actions.py for its dispatch strings (its own table is discarded).  Every cell runs op H with
the CharLeftSel fallback: on a paragraph .uno:SelectText can read (the mid-document cells) H is G, the v27
collapsed route, and the fallback does not run.  Writes identity-q52-headings.json.
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
rc, DOWN, END, DISPATCH = act.rc, act.DOWN, act.END, act.DISPATCH
cells = []


def cell(name, klass, fixture, dispatch, judged_as, route, note):
    cells.append({'name': name, 'class': klass, 'group': 'V5', 'route': route, 'fixture': fixture,
                  'action': judged_as, 'dispatch': dispatch,
                  'script': f'k{DOWN},X{name}@{END}=H{DISPATCH[dispatch]}~.uno:CharLeftSel,L,S',
                  'target': 'last' if route == '083' else 1, 'expect': judged_as, 'note': note})


cell('cl-nhead-after-realheading', 'N', 'realheading-then-empty-last.fodt', 'no-such-style', 'heading', '083',
     'the heading trap with a real Heading 1 before the empty last paragraph')
cell('cl-body-realheading-last', 'A', 'realheading-last.fodt', 'body', 'body', '083',
     'set-paragraph-body on a real empty Heading 1 that is the last paragraph')
cell('cl-nbody-realheading-last', 'N', 'realheading-last.fodt', 'no-such-style', 'body', '083',
     'nothing applies to the real empty last heading')
cell('g-body-real-empty-heading-mid', 'R', 'real-empty-heading-mid.fodt', 'body', 'body', 'collapsed',
     "176 Q6.3's b1 on a real Heading 1 (the v27 route)")
cell('g-nbody-real-empty-heading-mid', 'R', 'real-empty-heading-mid.fodt', 'no-such-style', 'body', 'collapsed',
     'the same, nothing applies')
cell('g-nbody-pseudo-heading-text-mid', 'R', 'pseudo-heading-text-mid.fodt', 'no-such-style', 'body', 'collapsed',
     "a pseudo-heading WITH text on today's verified one-block route; nothing applies")


def main():
    rc.CELLS[:] = cells
    rc.main()
    args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    out, fixtures = pathlib.Path(args['--out']), pathlib.Path(args['--fixtures'])
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'identity-q52-headings.json').write_text(json.dumps({
        'sources': {n: digest(HERE / n) for n in ('f083_native.cpp', 'run_cells_q52_actions.py',
                                                  'run_cells_q52_headings.py', 'make_fixtures_q52_headings.py')},
        'fixtures': {p.name: digest(p) for p in sorted(fixtures.iterdir()) if p.name != 'SHA256SUMS'}},
        indent=2) + '\n')


if __name__ == '__main__':
    main()
