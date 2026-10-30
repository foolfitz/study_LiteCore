#!/usr/bin/env python3
"""Fixtures for amendment 2 of ../PREDICTION.md: the four other paragraph actions on the multi-paragraph last line.

Usage: python3 -I make_fixtures_q52_actions.py OUT_DIR      (OUT_DIR must not exist)

Built with ../../native/tool/make_fixtures.py's helpers and N1's numbered list style (imported, not edited), plus a
byte copy of empty-last.fodt.
"""
import hashlib
import importlib.util
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
FIRST_RUN = HERE.parents[1] / 'native'
_spec = importlib.util.spec_from_file_location('f176_fixtures', FIRST_RUN / 'tool/make_fixtures.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
doc, p, item, EMPTY, BULLETS = base.doc, base.p, base.item, base.EMPTY, base.BULLETS
NUMBERS = base.n1.NUMBER_LIST_STYLE

HEADING_EMPTY = '<text:h text:style-name="Heading_20_1" text:outline-level="1"/>\n'
NEW = {
    'bulleted-last': doc(p('Plain first') + item(''), extra_auto=BULLETS),
    'heading-last': doc(p('Plain first') + HEADING_EMPTY),
    'number-then-empty-last': doc('<text:list text:style-name="LN"><text:list-item><text:p>Numbered before</text:p>'
                                  '</text:list-item></text:list>\n' + EMPTY, extra_auto=NUMBERS),
    'heading-then-empty-last': doc('<text:h text:style-name="Heading_20_1" text:outline-level="1">Heading before'
                                   '</text:h>\n' + EMPTY),
}
REUSED = ('empty-last.fodt',)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    for name, xml in NEW.items():
        (out / f'{name}.fodt').write_text(xml, encoding='utf-8')
    for name in REUSED:
        shutil.copyfile(FIRST_RUN / 'fixtures' / name, out / name)
    with open(out / 'SHA256SUMS', 'w') as sums:
        for path in sorted(out.glob('*.fodt')):
            sums.write(f'{sha(path)}  {path.name}\n')
    print((out / 'SHA256SUMS').read_text(), end='')


if __name__ == '__main__':
    main()
