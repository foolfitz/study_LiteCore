#!/usr/bin/env python3
"""Fixtures for amendment 3 of ../PREDICTION.md: real Heading 1 paragraphs, and one pseudo-heading with text.

Usage: python3 -I make_fixtures_q52_headings.py OUT_DIR      (OUT_DIR must not exist)

Amendment 2 found that 176's heading markup (`<text:h text:style-name="Heading_20_1" .../>` in a document with no
office:styles) loads as an automatic style with parent Standard and a direct outline level: a text:h that is not a
Heading 1 paragraph, which LibreOffice's HTML export writes as <p>.  Here the real fixtures define Heading_20_1 in
office:styles; whether they load as Heading 1 is a registered precondition (the untouched heading reads <h1>).
"""
import hashlib
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
FIRST_RUN = HERE.parents[1] / 'native'
_spec = importlib.util.spec_from_file_location('f176_fixtures', FIRST_RUN / 'tool/make_fixtures.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
doc, p, EMPTY = base.doc, base.p, base.EMPTY

STYLES = ('<office:styles>\n <style:style style:name="Heading_20_1" style:display-name="Heading 1" '
          'style:family="paragraph" style:default-outline-level="1"/>\n</office:styles>\n')


def real(body):
    return doc(body).replace('<office:automatic-styles>', STYLES + '<office:automatic-styles>', 1)


def h(text=''):
    inner = f'>{text}</text:h>' if text else '/>'
    return f'<text:h text:style-name="Heading_20_1" text:outline-level="1"{inner}\n'


NEW = {
    'realheading-then-empty-last': real(h('Heading before') + EMPTY),
    'realheading-last': real(p('Plain first') + h()),
    'real-empty-heading-mid': real(p('Plain first') + h() + p('E1-EMPTY-AFTER')),
    # 176's markup, kept on purpose: a pseudo-heading (no office:styles), this time with text, mid-document
    'pseudo-heading-text-mid': doc(p('Plain first') + h('Pseudo heading') + p('E1-TEXT-AFTER')),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    for name, xml in NEW.items():
        (out / f'{name}.fodt').write_text(xml, encoding='utf-8')
    with open(out / 'SHA256SUMS', 'w') as sums:
        for path in sorted(out.glob('*.fodt')):
            sums.write(f'{sha(path)}  {path.name}\n')
    print((out / 'SHA256SUMS').read_text(), end='')


if __name__ == '__main__':
    main()
