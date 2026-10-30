#!/usr/bin/env python3
"""Fixtures for amendment 4 of ../PREDICTION.md: byte copies of amendment 2's and the first run's, plus one new one.

Usage: python3 -I make_fixtures_q52_v6.py OUT_DIR      (OUT_DIR must not exist)
"""
import hashlib
import importlib.util
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
_spec = importlib.util.spec_from_file_location('f176_fixtures', HERE.parents[1] / 'native/tool/make_fixtures.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
COPIES = {'empty-last.fodt': 'fixtures-actions', 'number-then-empty-last.fodt': 'fixtures-actions',
          'bulleted-last.fodt': 'fixtures-actions', 'long-then-empty-last.fodt': 'fixtures'}
# two empty paragraphs at the end (ruling 4 Q4.4: type, Enter, Enter, bullet)
NEW = {'empty-empty-last': base.doc(base.p('Plain first') + base.EMPTY + base.EMPTY)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    for name, src in COPIES.items():
        shutil.copyfile(ROOT / src / name, out / name)
    for name, xml in NEW.items():
        (out / f'{name}.fodt').write_text(xml, encoding='utf-8')
    with open(out / 'SHA256SUMS', 'w') as sums:
        for path in sorted(out.glob('*.fodt')):
            sums.write(f'{sha(path)}  {path.name}\n')
    print((out / 'SHA256SUMS').read_text(), end='')


if __name__ == '__main__':
    main()
