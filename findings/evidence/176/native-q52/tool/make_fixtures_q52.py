#!/usr/bin/env python3
"""Fixtures for the 083 path's native arm (ruling 3 Q5.2, ../PREDICTION.md).

Usage: python3 -I make_fixtures_q52.py OUT_DIR      (OUT_DIR must not exist)

New fixtures built with ../../native/tool/make_fixtures.py's own helpers (imported, not edited), byte copies of the
two first-run fixtures these cells reuse, and the host's blank template, copied only after its sha256 is checked.
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

TABLE_NS = ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
TABLE = ('<table:table table:name="T1"><table:table-column/><table:table-row>'
         '<table:table-cell office:value-type="string"><text:p>Cell text</text:p></table:table-cell>'
         '</table:table-row></table:table>\n')


def section(body):
    return f'<text:section text:name="S1">{body}</text:section>\n'


NEW = {
    # one empty bulleted paragraph (set-list-none's one-paragraph document; the already-bulleted no-op)
    'bulleted-only': doc(item(''), extra_auto=BULLETS),
    # one empty Heading 1 (set-paragraph-body's one-paragraph document); Q6.3's heading markup
    'heading-only': doc('<text:h text:style-name="Heading_20_1" text:outline-level="1"/>\n'),
    # a bullet item, then the empty last paragraph: SelectAll's FIRST block is in a list, the target is not
    'bullet-then-empty-last': doc(item('Bullet before') + EMPTY, extra_auto=BULLETS),
    'table-then-empty-last': doc(p('Plain first') + TABLE + EMPTY, extra_ns=TABLE_NS),
    # the body starts with a table: SelAll takes ExtendedSelectAll (select.cxx:186-201), read not measured
    'table-first-empty-last': doc(TABLE + EMPTY, extra_ns=TABLE_NS),
    'section-then-empty-last': doc(p('Plain first') + section(p('Section text').strip()) + EMPTY),
    # the caret in a section: the first SelAll selects the current section only (select.cxx:150-167), read
    'empty-last-in-section': doc(p('Plain first') + section('<text:p/>')),
    # cost: the readback of a whole-document selection grows with the document
    'long-then-empty-last': doc(''.join(p(f'Line {n:03d} of a long document, enough text to make a line.')
                                        for n in range(1, 301)) + EMPTY),
}
REUSED = ('empty-last.fodt', 'two-plain.fodt')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    for name, xml in NEW.items():
        (out / f'{name}.fodt').write_text(xml, encoding='utf-8')
    for name in REUSED:
        shutil.copyfile(FIRST_RUN / 'fixtures' / name, out / name)
    if sha(base.BLANK) != base.BLANK_SHA256:
        raise SystemExit(f'the host blank template changed: {sha(base.BLANK)}')
    shutil.copyfile(base.BLANK, out / 'blank-one.odt')
    with open(out / 'SHA256SUMS', 'w') as sums:
        for path in sorted(list(out.glob('*.fodt')) + [out / 'blank-one.odt']):
            sums.write(f'{sha(path)}  {path.name}\n')
    print((out / 'SHA256SUMS').read_text(), end='')


if __name__ == '__main__':
    main()
