#!/usr/bin/env python3
"""Run the 083 path's native cells (ruling 3 Q5.2, ../PREDICTION.md) with run_cells.py's runner, unedited.

Usage: python3 -I run_cells_q52.py --binary BIN --install DIR --fixtures DIR --out DIR --work DIR [--runs 5] [--only C]

Imports ../../native/tool/run_cells.py, replaces its cell table with this one, and calls its main() (mode uni1ai,
one process per cell and round, run-major); then writes identity-q52.json beside its identity.json with this
directory's sources and the fixtures' sha256.
"""
import hashlib
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('run_cells', HERE.parents[1] / 'native/tool/run_cells.py')
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

DOWN, END, RETURN, MOD1 = rc.DOWN, rc.END, rc.RETURN, rc.MOD1
CTRL_END = MOD1 | END
BODY = ('{"Style":{"type":"string"`"value":"Text body"}`'
        '"FamilyName":{"type":"string"`"value":"ParagraphStyles"}}')   # styleApplyArguments(false)
ACTIONS = {'bullet': f'.uno:DefaultBullet|{rc.LIST_ON}', 'sham': f'.uno:DefaultBullet|{rc.LIST_OFF}',
           'number': f'.uno:DefaultNumbering|{rc.LIST_ON}', 'none': '.uno:RemoveBullets',
           'heading': f'.uno:StyleApply|{rc.HEADING}', 'body': f'.uno:StyleApply|{BODY}'}
FALLBACKS = {'sa': '.uno:SelectAll', 'cl': '.uno:CharLeftSel'}
# how the caret reaches the last paragraph, per fixture (PREDICTION.md, Cells)
REACH = {'blank-one.odt': ('', END), 'bulleted-only.fodt': ('', END), 'heading-only.fodt': ('', END),
         'empty-last.fodt': (f'k{DOWN}', END), 'bullet-then-empty-last.fodt': (f'k{DOWN}', END),
         'two-plain.fodt': (f'k{DOWN},k{END}', RETURN),
         'table-then-empty-last.fodt': (f'k{CTRL_END},k{CTRL_END}', END),
         'table-first-empty-last.fodt': (f'k{CTRL_END},k{CTRL_END}', END),
         'section-then-empty-last.fodt': (f'k{CTRL_END},k{CTRL_END}', END),
         'empty-last-in-section.fodt': (f'k{CTRL_END},k{CTRL_END}', END),
         'long-then-empty-last.fodt': (f'k{CTRL_END},k{CTRL_END}', END)}
cells = []


def cell(name, klass, group, fixture, action, note):
    setup, trigger = REACH[fixture]
    op = f'H{ACTIONS[action]}~{FALLBACKS[name[:2]]}'
    cells.append({'name': name, 'class': klass, 'group': group, 'fixture': fixture, 'action': action,
                  'script': (setup + ',' if setup else '') + f'X{name}@{trigger}={op},L,S',
                  'target': 'last', 'expect': 'none' if action == 'sham' else action, 'note': note})


cell('sa-a5-blank-one', 'A', 'SA-1', 'blank-one.odt', 'bullet', "the owner's case: the host's blank template")
cell('sa-n5-sham-blank-one', 'N', 'SA-1', 'blank-one.odt', 'sham', 'the sham on a5 (On:false: nothing applies)')
cell('sa-num-blank-one', 'S', 'SA-5', 'blank-one.odt', 'number', 'set-list-ordered on the blank template')
cell('sa-head-blank-one', 'S', 'SA-5', 'blank-one.odt', 'heading', 'set-paragraph-heading on the blank template')
cell('sa-none-bulleted-only', 'S', 'SA-5', 'bulleted-only.fodt', 'none', 'set-list-none on one empty bullet')
cell('sa-body-heading-only', 'S', 'SA-5', 'heading-only.fodt', 'body', 'set-paragraph-body on one empty heading')
cell('sa-a4-empty-last', 'A', 'SA-M', 'empty-last.fodt', 'bullet', "176's a4: text, then the empty last paragraph")
cell('sa-a7-enter-last', 'A', 'SA-M', 'two-plain.fodt', 'bullet', 'End of the last paragraph, Enter, bullet')
cell('sa-a8-after-bullet', 'A', 'SA-M', 'bullet-then-empty-last.fodt', 'bullet', 'a bullet item, then the empty one')
cell('sa-n4-sham-empty-last', 'N', 'SA-M', 'empty-last.fodt', 'sham', 'the sham on a4')
cell('sa-n8-sham-after-bullet', 'N', 'SA-M', 'bullet-then-empty-last.fodt', 'sham',
     "the first-block trap: the readback's first block is a bullet, the target is not")
cell('sa-t1-table-then-empty-last', 'A', 'SA-M', 'table-then-empty-last.fodt', 'bullet', 'a table before it')
cell('sa-t2-table-first-empty-last', 'A', 'SA-M', 'table-first-empty-last.fodt', 'bullet',
     'the body starts with a table (ExtendedSelectAll, read)')
cell('sa-s1-section-then-empty-last', 'A', 'SA-M', 'section-then-empty-last.fodt', 'bullet', 'a section before it')
cell('sa-s2-empty-last-in-section', 'A', 'SA-M', 'empty-last-in-section.fodt', 'bullet',
     'the empty last paragraph inside a section (SelAll selects the section only, read)')
cell('sa-ns2-sham-empty-last-in-section', 'N', 'SA-M', 'empty-last-in-section.fodt', 'sham', 'the sham on s2')
for _sa in [c for c in cells if c['group'] == 'SA-M' and c['name'] not in
            ('sa-t2-table-first-empty-last', 'sa-ns2-sham-empty-last-in-section')]:
    _name = 'cl-' + _sa['name'][3:]
    cell(_name, _sa['class'], 'CL', _sa['fixture'], _sa['action'], 'CharLeftSel twin: ' + _sa['note'])
cell('cl-a5-blank-one', 'R', 'R', 'blank-one.odt', 'bullet', 'CharLeftSel at the document start (predicted NONE)')
cell('sa-r1-noop-bulleted-only', 'R', 'R', 'bulleted-only.fodt', 'bullet', 'bullet on an already bulleted paragraph')
cell('sa-long-300', 'R', 'R', 'long-then-empty-last.fodt', 'bullet', 'cost: 300 paragraphs before the empty one')


def main():
    rc.CELLS[:] = cells
    rc.main()
    args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    out, fixtures = pathlib.Path(args['--out']), pathlib.Path(args['--fixtures'])
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'identity-q52.json').write_text(json.dumps({
        'sources': {n: digest(HERE / n) for n in ('f083_native.cpp', 'run_cells_q52.py', 'make_fixtures_q52.py')},
        'fixtures': {p.name: digest(p) for p in sorted(fixtures.iterdir()) if p.name != 'SHA256SUMS'}},
        indent=2) + '\n')


if __name__ == '__main__':
    main()
