#!/usr/bin/env python3
"""Fixtures for the finding-142 native arms (Ctrl+Home / Ctrl+End on the key path).

Usage: python3 -I make_fixtures.py OUT_DIR

Every fixture is a flat ODT (.fodt) with one explicit page layout (A4, 2 cm
margins), so page geometry does not depend on the host locale. Paragraph texts
are short (no wrapping) and unique, so the locator in the probe (Shift+End then
Shift+Home from the caret) identifies a paragraph and an offset.

The two L-C-number-or-indent fixtures (`bullet.fodt`, `indent.fodt`) are NOT
generated here: they are produced byte-for-byte by review 6's own generator
(findings/evidence/link-batch/review/review-6-artifacts/native/make_fixtures.py),
which the runner calls separately. `numbered-first.fodt` is new (an ordered list).
"""
import pathlib
import sys

NS = (
    ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
    ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    ' xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"'
)

PAGE_PLAIN = '''<style:page-layout style:name="pm1">
  <style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" fo:margin-top="2cm" fo:margin-bottom="2cm" fo:margin-left="2cm" fo:margin-right="2cm"/>
 </style:page-layout>'''

PAGE_HF = '''<style:page-layout style:name="pm1">
  <style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" fo:margin-top="2cm" fo:margin-bottom="2cm" fo:margin-left="2cm" fo:margin-right="2cm"/>
  <style:header-style><style:header-footer-properties fo:min-height="0.6cm" fo:margin-bottom="0.4cm"/></style:header-style>
  <style:footer-style><style:header-footer-properties fo:min-height="0.6cm" fo:margin-top="0.4cm"/></style:footer-style>
 </style:page-layout>'''

NUMBER_LIST_STYLE = '''<text:list-style style:name="LN">
  <text:list-level-style-number text:level="1" style:num-format="1" style:num-suffix=".">
   <style:list-level-properties text:list-level-position-and-space-mode="label-alignment">
    <style:list-level-label-alignment text:label-followed-by="listtab" text:list-tab-stop-position="1.27cm" fo:text-indent="-0.635cm" fo:margin-left="1.27cm"/>
   </style:list-level-properties>
  </text:list-level-style-number>
 </text:list-style>'''


def doc(body, header=None, footer=None, extra_auto=''):
    page = PAGE_HF if (header or footer) else PAGE_PLAIN
    master_inner = ''
    if header:
        master_inner += f'<style:header><text:p>{header}</text:p></style:header>'
    if footer:
        master_inner += f'<style:footer><text:p>{footer}</text:p></style:footer>'
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<office:document{NS}\n office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.text">\n'
        '<office:automatic-styles>\n '
        + page + '\n ' + extra_auto + '\n'
        '</office:automatic-styles>\n'
        '<office:master-styles>\n'
        f' <style:master-page style:name="Standard" style:page-layout-name="pm1">{master_inner}</style:master-page>\n'
        '</office:master-styles>\n'
        '<office:body><office:text>\n'
        + body +
        '</office:text></office:body></office:document>\n'
    )


def p(text):
    return f'<text:p>{text}</text:p>\n'


def table(name, rows):
    cols = len(rows[0])
    out = f'<table:table table:name="{name}">\n'
    out += f' <table:table-column table:number-columns-repeated="{cols}"/>\n'
    for row in rows:
        out += ' <table:table-row>'
        for cell in row:
            out += f'<table:table-cell office:value-type="string"><text:p>{cell}</text:p></table:table-cell>'
        out += '</table:table-row>\n'
    out += '</table:table>\n'
    return out


PLAIN3 = p('Alpha first paragraph') + p('Bravo second paragraph') + p('Charlie third paragraph')

FIXTURES = {
    # arms 1-3, 6, 8, 9
    'plain3': doc(PLAIN3),
    # arm 4: text before and after a 3x3 table
    'table-mid': doc(
        p('Before the table')
        + table('T1', [['A1 text', 'B1 text', 'C1 text'],
                       ['A2 text', 'B2 text', 'C2 text'],
                       ['A3 text', 'B3 text', 'C3 text']])
        + p('After the table')),
    # arm 5: a document that starts with a table
    'table-first': doc(
        table('T1', [['A1 first', 'B1 first'], ['A2 first', 'B2 first']])
        + p('Body after table') + p('Last body line')),
    # arm 5: a document that ends with a table
    'table-last': doc(
        p('First body line') + p('Body before table')
        + table('T1', [['A1 last', 'B1 last'], ['A2 last', 'B2 last']])),
    # arm 7: a page header and footer
    'header-footer': doc(PLAIN3, header='Header line text', footer='Footer line text'),
    # extra (GoStart/GoEnd try the current section first, move.cxx:285-290, :344)
    'section-mid': doc(
        p('Before the section')
        + '<text:section text:name="S1">\n' + p('Inside section one') + p('Inside section two') + '</text:section>\n'
        + p('After the section')),
    # extra: a numbered (ordered-list) first paragraph
    'numbered-first': doc(
        '<text:list text:style-name="LN"><text:list-item><text:p>Numbered first</text:p></text:list-item></text:list>\n'
        + p('Plain second') + p('Plain third'),
        extra_auto=NUMBER_LIST_STYLE),
    # queued-pair discriminator: a numbered SECOND paragraph. At its start Writer's
    # key handler does Backspace itself (NumOrNoNum, edtwin.cxx:2048-2110) instead
    # of handing it to the accelerator table.
    'numbered-second': doc(
        p('Plain first')
        + '<text:list text:style-name="LN"><text:list-item><text:p>Numbered second</text:p></text:list-item></text:list>\n'
        + p('Plain third'),
        extra_auto=NUMBER_LIST_STYLE),
}


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, xml in FIXTURES.items():
        path = out / f'{name}.fodt'
        path.write_text(xml, encoding='utf-8')
        print(path)


if __name__ == '__main__':
    main()
