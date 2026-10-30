#!/usr/bin/env python3
"""Fixtures for ruling 3 Q6.3's native cells (PREDICTION.md amendment 2).

Usage: python3 -I make_fixtures_q63.py OUT_DIR

Two new fixtures built with make_fixtures.py's own helpers (imported, not edited), and byte copies of the two
first-run fixtures these cells reuse, so the run reads one directory.
"""
import hashlib
import importlib.util
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('f176_fixtures', HERE / 'make_fixtures.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
doc, p, EMPTY = base.doc, base.p, base.EMPTY

NEW = {
    # an empty Heading 1 between two paragraphs (ruling 3 Q2.1: body on it shrinks the paragraph)
    'empty-heading-mid': doc(p('Plain first') + '<text:h text:style-name="Heading_20_1" text:outline-level="1"/>\n'
                             + p('E1-EMPTY-AFTER')),
    # an empty paragraph followed by another empty paragraph
    'empty-empty-mid': doc(p('Plain first') + EMPTY + EMPTY + p('E1-EMPTY-AFTER')),
}
REUSED = ('empty-mid.fodt', 'empty-bulleted-mid.fodt')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    for name, xml in NEW.items():
        (out / f'{name}.fodt').write_text(xml, encoding='utf-8')
    for name in REUSED:
        shutil.copyfile(HERE.parent / 'fixtures' / name, out / name)
    with open(out / 'SHA256SUMS', 'w') as sums:
        for path in sorted(out.glob('*.fodt')):
            sums.write(f'{sha(path)}  {path.name}\n')
    print((out / 'SHA256SUMS').read_text(), end='')


if __name__ == '__main__':
    main()
