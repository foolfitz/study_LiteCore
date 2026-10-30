#!/usr/bin/env python3
"""Fixtures for finding 176's native arm (engine item C, fable ruling 2026-10-30 §3.3 step 1).

Usage: python3 -I make_fixtures.py OUT_DIR

Flat ODT built with the N1 fixtures' own `doc`, `p` and bullet list style
(findings/evidence/link-batch-v23/native/ordered-commands/tool/make_fixtures.py, imported, not copied),
plus `blank-one.odt`: the host's blank template, byte for byte (the file B1 and S2 pin by sha256), so the
083 path is measured on the document the owner's new-document route opens.
"""
import hashlib
import importlib.util
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
N1 = HERE.parents[2] / 'link-batch-v23/native/ordered-commands/tool/make_fixtures.py'
_spec = importlib.util.spec_from_file_location('n1_fixtures', N1)
n1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(n1)
doc, p, BULLETS = n1.doc, n1.p, n1.BULLET_LIST_STYLE

BLANK = pathlib.Path('/home/jiajun/Projects/Nextcloud_Apps/litecore/blank/en-US_zh-TW_A4.odt')
BLANK_SHA256 = '7e6221b697d408fc011b820226b98e4ad908afbadce8aac3ded48140349b5475'


def item(text):
    body = f'<text:p>{text}</text:p>' if text else '<text:p/>'
    return f'<text:list text:style-name="L1"><text:list-item>{body}</text:list-item></text:list>\n'


EMPTY = '<text:p/>\n'
FIXTURES = {
    # a paragraph with text between two others: today's verified path (the control)
    'text-mid': doc(p('Plain first') + p('Middle text') + p('E1-TEXT-AFTER')),
    # finding 046's cell: an empty paragraph with a paragraph after it
    'empty-mid': doc(p('Plain first') + EMPTY + p('E1-EMPTY-AFTER')),
    # F3's recipe shape: the empty paragraph is made by Enter at the end of the first one
    'two-plain': doc(p('Plain first') + p('E1-EMPTY-AFTER')),
    # 083's path: the empty paragraph is the last one
    'empty-last': doc(p('Plain first') + EMPTY),
    # the overshoot reaches a bulleted paragraph (SelectionHasBullet over that selection is true by source)
    'empty-before-list': doc(p('Plain first') + EMPTY + item('Bullet after'), extra_auto=BULLETS),
    # 046's upward counterexample's neighbour: the paragraph above is already a bullet
    'empty-after-list': doc(item('Bullet before') + EMPTY + p('Plain after'), extra_auto=BULLETS),
    # an empty paragraph that is already a bullet, a paragraph after it
    'empty-bulleted-mid': doc(p('Plain first') + item('') + p('E1-EMPTY-AFTER'), extra_auto=BULLETS),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, xml in FIXTURES.items():
        path = out / f'{name}.fodt'
        path.write_text(xml, encoding='utf-8')
        print(path, sha(path))
    if sha(BLANK) != BLANK_SHA256:
        raise SystemExit(f'the host blank template changed: {sha(BLANK)}')
    shutil.copyfile(BLANK, out / 'blank-one.odt')
    print(out / 'blank-one.odt', sha(out / 'blank-one.odt'))


if __name__ == '__main__':
    main()
