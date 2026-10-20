#!/usr/bin/env python3
"""Fixtures for the ordered-commands native arms (fable ruling 1 §2.6, v23).

Usage: python3 -I make_fixtures.py OUT_DIR

Flat ODT (.fodt) with one explicit page layout (A4, 2 cm margins), as the
finding-142 fixtures (findings/evidence/link-batch-v21/native/142-ctrl-home-end/
tool/make_fixtures.py), from which `doc`, the page layout and the number list
style are copied. `numbered-second` is 142's fixture, byte for byte in its body.
`bullet` and `indent` carry review 6's bodies (findings/evidence/link-batch/
review/review-6-artifacts/native/make_fixtures.py) for positions (i)-(iii) of
L-C-number-or-indent (SPEC-M3-link-batch.md §15.1), under this file's page
layout.
"""
import pathlib
import sys

NS = (
    ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
    ' xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"'
)

PAGE = '''<style:page-layout style:name="pm1">
  <style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" fo:margin-top="2cm" fo:margin-bottom="2cm" fo:margin-left="2cm" fo:margin-right="2cm"/>
 </style:page-layout>'''

NUMBER_LIST_STYLE = '''<text:list-style style:name="LN">
  <text:list-level-style-number text:level="1" style:num-format="1" style:num-suffix=".">
   <style:list-level-properties text:list-level-position-and-space-mode="label-alignment">
    <style:list-level-label-alignment text:label-followed-by="listtab" text:list-tab-stop-position="1.27cm" fo:text-indent="-0.635cm" fo:margin-left="1.27cm"/>
   </style:list-level-properties>
  </text:list-level-style-number>
 </text:list-style>'''

BULLET_LIST_STYLE = '''<text:list-style style:name="L1">
  <text:list-level-style-bullet text:level="1" text:bullet-char="&#x2022;">
   <style:list-level-properties text:list-level-position-and-space-mode="label-alignment">
    <style:list-level-label-alignment text:label-followed-by="listtab" text:list-tab-stop-position="1.27cm" fo:text-indent="-0.635cm" fo:margin-left="1.27cm"/>
   </style:list-level-properties>
  </text:list-level-style-bullet>
 </text:list-style>'''

INDENT_STYLE = '<style:style style:name="PI" style:family="paragraph"><style:paragraph-properties fo:text-indent="1cm"/></style:style>'


# The table namespace only where a table is used, so the fixtures of the counted run (24c5b635)
# keep their bytes.
TABLE_NS = ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'


def doc(body, extra_auto='', extra_ns=''):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<office:document{NS}{extra_ns}\n office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.text">\n'
        '<office:automatic-styles>\n ' + PAGE + '\n ' + extra_auto + '\n'
        '</office:automatic-styles>\n'
        '<office:master-styles>\n'
        ' <style:master-page style:name="Standard" style:page-layout-name="pm1"/>\n'
        '</office:master-styles>\n'
        '<office:body><office:text>\n' + body + '</office:text></office:body></office:document>\n'
    )


def p(text):
    return f'<text:p>{text}</text:p>\n'


FIXTURES = {
    # D2-D6: one paragraph, four letters (137's model traces use `abcd`)
    'abcd': doc(p('abcd')),
    # D1: 142's queued-pair discriminator
    'numbered-second': doc(
        p('Plain first')
        + '<text:list text:style-name="LN"><text:list-item><text:p>Numbered second</text:p></text:list-item></text:list>\n'
        + p('Plain third'),
        extra_auto=NUMBER_LIST_STYLE),
    # D7 (i) Delete at the end of P2, in front of P3's label; (ii) Backspace at the document start
    'bullet': doc(
        '<text:list text:style-name="L1"><text:list-item><text:p>Alpha one</text:p></text:list-item></text:list>\n'
        '<text:p>Beta two</text:p>\n'
        '<text:list text:style-name="L1"><text:list-item><text:p>Gamma three</text:p></text:list-item></text:list>\n',
        extra_auto=BULLET_LIST_STYLE),
    # D7 (iii) Backspace at the document start, first-line indent
    'indent': doc('<text:p text:style-name="PI">Indented first</text:p>\n<text:p>Second</text:p>\n',
                  extra_auto=INDENT_STYLE),
    # D7 plain: Backspace at the start of a plain first paragraph
    'plain3': doc(p('Alpha first paragraph') + p('Bravo second paragraph') + p('Charlie third paragraph')),
    # N1b's positive control (SPEC-M3-ordered-commands §9.1): a one-row table, then a paragraph;
    # the caret opens in A1, and Down leaves the table (STATE_CHANGED arrives late, 142 README:20)
    'table-leave': doc('<table:table table:name="T1"><table:table-column table:number-columns-repeated="2"/>'
                       '<table:table-row><table:table-cell office:value-type="string"><text:p>A1 text</text:p>'
                       '</table:table-cell><table:table-cell office:value-type="string"><text:p>B1 text</text:p>'
                       '</table:table-cell></table:table-row></table:table>\n' + p('After the table'),
                       extra_ns=TABLE_NS),
    # SPEC-M3-ordered-commands §15.1 (ruling 2 §2.1 item 5): undo grouping. A run of 30 equal characters,
    # and a run of 25 CJK characters (no spaces: the user's path), each deleted one key at a time.
    'underscores': doc(p('Name: ' + '_' * 30)),
    'cjk25': doc(p('中文沒有空格所以一句二十幾個字的長句子其實很平常啊')),
    # N1c: 200 paragraphs of about 300 characters each, so a join near the top re-lays-out the rest
    'long200': doc(''.join(p(f'Paragraph {i:03d}. ' + ' '.join(['lorem ipsum dolor sit amet consectetur'] * 8))
                           for i in range(1, 201))),
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
