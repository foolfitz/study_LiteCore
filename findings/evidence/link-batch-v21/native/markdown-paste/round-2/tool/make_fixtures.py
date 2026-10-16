#!/usr/bin/env python3
"""Write round 2's flat-ODT fixtures into OUT_DIR. Deterministic.

Usage: make_fixtures.py OUT_DIR

Every fixture sets its own page layout (A4, 2 cm margins), as finding 142's
fixtures do, so the host locale does not change the geometry the click-based
placements rely on. header-footer.fodt is copied byte for byte from finding
142's fixtures (the same document its hf-* / place-hdr-click arms used).
"""

import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
F142 = os.path.join(HERE, *[".."] * 3, "142-ctrl-home-end", "fixtures", "header-footer.fodt")

NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
      'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
      'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
      'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
      'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
      'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
      'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0" '
      'xmlns:dc="http://purl.org/dc/elements/1.1/" '
      'xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" '
      'xmlns:loext="urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0"')

PAGE = ('<style:page-layout style:name="pm1"><style:page-layout-properties fo:page-width="21cm" '
        'fo:page-height="29.7cm" fo:margin-top="2cm" fo:margin-bottom="2cm" fo:margin-left="2cm" '
        'fo:margin-right="2cm"/>%s</style:page-layout>')
HF_STYLE = ('<style:header-style><style:header-footer-properties fo:min-height="0.6cm" '
            'fo:margin-bottom="0.4cm"/></style:header-style>')


def doc(body, auto="", master_inner="", settings="", page_extra=""):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<office:document %s office:version="1.3" '
            'office:mimetype="application/vnd.oasis.opendocument.text">\n'
            '%s'
            '<office:automatic-styles>\n %s\n %s\n</office:automatic-styles>\n'
            '<office:master-styles>\n <style:master-page style:name="Standard" '
            'style:page-layout-name="pm1">%s</style:master-page>\n</office:master-styles>\n'
            '<office:body><office:text>\n%s\n</office:text></office:body></office:document>\n'
            % (NS, settings, PAGE % page_extra, auto, master_inner, body))


def settings_item(name, value):
    return ('<office:settings><config:config-item-set config:name="ooo:configuration-settings">'
            '<config:config-item config:name="%s" config:type="boolean">%s</config:config-item>'
            '</config:config-item-set></office:settings>\n' % (name, value))


def cell(text, protected=False):
    attr = ' table:protected="true"' if protected else ""
    inner = "<text:p>%s</text:p>" % text if text else "<text:p/>"
    return '<table:table-cell office:value-type="string"%s>%s</table:table-cell>' % (attr, inner)


FIXTURES = {
    # T1: P8 (mid cell text), P9 (empty cell B2), P11 (range A1 -> B1).
    "cells.fodt": doc(
        '<text:p>Before the table</text:p>\n'
        '<table:table table:name="T1">\n <table:table-column table:number-columns-repeated="3"/>\n'
        ' <table:table-row>%s%s%s</table:table-row>\n'
        ' <table:table-row>%s%s%s</table:table-row>\n'
        ' <table:table-row>%s%s%s</table:table-row>\n'
        '</table:table>\n<text:p>After the table</text:p>'
        % (cell("A1 text"), cell("B1 text"), cell("C1 text"),
           cell("A2 text"), cell(""), cell("C2 text"),
           cell("A3 text"), cell("B3 text"), cell("C3 text"))),
    # T2 candidates.
    "protected-section.fodt": doc(
        '<text:p>Start paragraph</text:p>\n'
        '<text:section text:name="Locked" text:protected="true"><text:p>Inside locked section</text:p>'
        '</text:section>\n<text:p>After section</text:p>'),
    "protected-cell.fodt": doc(
        '<text:p>Before the table</text:p>\n'
        '<table:table table:name="T1">\n <table:table-column table:number-columns-repeated="2"/>\n'
        ' <table:table-row>%s%s</table:table-row>\n</table:table>\n<text:p>After the table</text:p>'
        % (cell("Open cell"), cell("Locked cell", protected=True))),
    "content-control.fodt": doc(
        '<text:p>Pick <loext:content-control loext:dropdown="true">'
        '<loext:list-item loext:display-text="Red" loext:value="R"/>'
        '<loext:list-item loext:display-text="Blue" loext:value="B"/>Red</loext:content-control> here</text:p>\n'
        '<text:p>Type <loext:content-control loext:plain-text="true">plain words</loext:content-control> here</text:p>\n'
        '<text:p>Rich <loext:content-control>rich words</loext:content-control> here</text:p>'),
    "input-field.fodt": doc(
        '<text:p>Name: <text:text-input text:description="Your name">Field value</text:text-input> end</text:p>\n'
        '<text:p>Second paragraph</text:p>'),
    "protect-form.fodt": doc(
        '<text:p>Start</text:p>\n<text:p>Alpha Beta Gamma</text:p>\n<text:p>End</text:p>',
        settings=settings_item("ProtectForm", "true")),
    "protect-fields.fodt": doc(
        '<text:p>Start</text:p>\n<text:p>Date: <text:date text:date-value="2026-10-16" '
        'text:fixed="true">2026-10-16</text:date> end.</text:p>\n<text:p>End</text:p>',
        settings=settings_item("ProtectFields", "true")),
    "frame-protected.fodt": doc(
        '<draw:frame draw:style-name="fr1" draw:name="Frame1" text:anchor-type="page" '
        'text:anchor-page-number="1" svg:x="3cm" svg:y="8cm" svg:width="8cm" draw:z-index="0">'
        '<draw:text-box fo:min-height="2cm"><text:p>Inside frame text</text:p></draw:text-box></draw:frame>\n'
        '<text:p>Body paragraph</text:p>',
        auto='<style:style style:name="fr1" style:family="graphic"><style:graphic-properties '
             'style:protect="content" style:wrap="none" style:vertical-pos="from-top" '
             'style:vertical-rel="page" style:horizontal-pos="from-left" style:horizontal-rel="page" '
             'fo:border="0.06pt solid #000000" fo:padding="0.1cm"/></style:style>'),
    "header-protected-section.fodt": doc(
        '<text:p>Alpha first paragraph</text:p>\n<text:p>Bravo second paragraph</text:p>',
        master_inner='<style:header><text:section text:name="HeaderLocked" text:protected="true">'
                     '<text:p>Header line text</text:p></text:section></style:header>',
        page_extra=HF_STYLE),
}


def main(argv):
    out = argv[1]
    os.makedirs(out, exist_ok=True)
    for name, text in FIXTURES.items():
        with open(os.path.join(out, name), "w", encoding="utf-8") as handle:
            handle.write(text)
    shutil.copyfile(F142, os.path.join(out, "header-footer.fodt"))
    for name in sorted(os.listdir(out)):
        with open(os.path.join(out, name), "rb") as handle:
            print(hashlib.sha256(handle.read()).hexdigest(), name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
