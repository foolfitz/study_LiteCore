#!/usr/bin/env python3
"""Run ruling 3 Q6.3's native cells (PREDICTION.md amendment 2) with run_cells.py's runner, unedited.

Usage: python3 -I run_cells_q63.py --binary BIN --install DIR --fixtures fixtures-q63 --out out-q63 --work DIR

Imports run_cells.py, replaces its cell table with this one, and calls its main(); writes this file's sha256 and
the fixtures' next to its identity.json as identity-q63.json.
"""
import hashlib
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('run_cells', HERE / 'run_cells.py')
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

DOWN, END = rc.DOWN, rc.END
BODY = ('{"Style":{"type":"string"`"value":"Text body"}`'
        '"FamilyName":{"type":"string"`"value":"ParagraphStyles"}}')   # styleApplyArguments(false)
cells = []


def cell(name, klass, fixture, op, target, expect, note):
    cells.append({'name': name, 'class': klass, 'fixture': fixture,
                  'script': f'k{DOWN},X{name}@{END}={op},L,S', 'target': target, 'expect': expect, 'note': note})


cell('b0-heading-control', 'R', 'empty-heading-mid.fodt', f'F.uno:StyleApply|{rc.HEADING}', 1, 'heading',
     'fixture control: the empty paragraph loads as a heading')
cell('b1f-body-on-empty-heading', 'R', 'empty-heading-mid.fodt', f'F.uno:StyleApply|{BODY}', 1, 'body',
     "ruling 3 Q2.1's hypothesis about F's restore after a heading shrinks")
cell('b1g-body-on-empty-heading', 'G', 'empty-heading-mid.fodt', f'G.uno:StyleApply|{BODY}', 1, 'body',
     'the same under G')
cell('a6f-empty-empty', 'R', 'empty-empty-mid.fodt', rc.F_BULLET, 1, 'bullet', 'empty paragraph, another empty after it')
cell('a6g-empty-empty', 'G', 'empty-empty-mid.fodt', rc.G_BULLET, 1, 'bullet', 'the same under G')
cell('n6f-sham-empty-empty', 'R', 'empty-empty-mid.fodt', rc.F_SHAM, 1, 'none', 'sham, F')
cell('n6g-sham-empty-empty', 'G', 'empty-empty-mid.fodt', rc.G_SHAM, 1, 'none', 'sham, G')
cell('g-r3-number-empty-mid', 'G', 'empty-mid.fodt', f'G.uno:DefaultNumbering|{rc.LIST_ON}', 1, 'number',
     "r3's G twin")
cell('g-r4-none-empty-bulleted', 'G', 'empty-bulleted-mid.fodt', 'G.uno:RemoveBullets', 1, 'none', "r4's G twin")
cell('g-r5-heading-empty-mid', 'G', 'empty-mid.fodt', f'G.uno:StyleApply|{rc.HEADING}', 1, 'heading',
     "r5's G twin")


def main():
    rc.CELLS[:] = cells
    rc.main()
    args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    out, fixtures = pathlib.Path(args['--out']), pathlib.Path(args['--fixtures'])
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'identity-q63.json').write_text(json.dumps({
        'runner': {'run_cells_q63.py': digest(HERE / 'run_cells_q63.py'),
                   'make_fixtures_q63.py': digest(HERE / 'make_fixtures_q63.py')},
        'fixtures': {p.name: digest(p) for p in sorted(fixtures.glob('*.fodt'))}}, indent=2) + '\n')


if __name__ == '__main__':
    main()
