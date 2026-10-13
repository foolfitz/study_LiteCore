#!/usr/bin/env python3
"""Generate extend-signatures.fodt (fixture of tools/link_native_extend_signatures.cpp).

The tool carries its own copy of the paragraph texts (kParas) and the runner
refuses to run if `tool --paragraphs` and the fixture's paragraphs differ.
Usage: gen_extend_signatures.py [OUT.fodt]   (default: next to this script)
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

WRAP = ("W1 this paragraph is deliberately long so that it wraps onto several displayed lines "
        "because it keeps adding ordinary words one after another until the first line is full "
        "and then the second line is full as well and a third line is needed to hold the rest "
        "of the sentence which goes on for a little while longer before it finally stops here")

# (kind, text).  kind: p | h | li | cell
PARAS = [
    ("p", "P1 plain paragraph above"),
    ("p", "P2 ALPHA BETA GAMMA DELTA"),
    ("p", "P3 plain paragraph below"),
    ("p", ""),
    ("p", WRAP),
    ("p", "中文段落測試，這是第二句。"),
    ("h", "Heading one for the test"),
    ("li", "List item one"),
    ("cell", "A1 cell text"),
    ("cell", "B1 cell text"),
    ("cell", "A2 cell text"),
    ("cell", "B2 cell text"),
    ("p", "Final paragraph ends the document."),
]


def body() -> str:
    out = []
    cells = [t for k, t in PARAS if k == "cell"]
    tbl_done = False
    for kind, text in PARAS:
        t = escape(text)
        if kind == "p":
            out.append("   <text:p/>" if text == "" else f"   <text:p>{t}</text:p>")
        elif kind == "h":
            out.append(f'   <text:h text:style-name="Heading_20_1" text:outline-level="1">{t}</text:h>')
        elif kind == "li":
            out.append('   <text:list text:style-name="LBullet"><text:list-item>'
                       f"<text:p>{t}</text:p></text:list-item></text:list>")
        elif kind == "cell" and not tbl_done:
            tbl_done = True
            c = [escape(x) for x in cells]
            out.append('   <table:table table:name="T1">\n'
                       '    <table:table-column table:number-columns-repeated="2"/>\n'
                       '    <table:table-row>\n'
                       f'     <table:table-cell office:value-type="string"><text:p>{c[0]}</text:p></table:table-cell>\n'
                       f'     <table:table-cell office:value-type="string"><text:p>{c[1]}</text:p></table:table-cell>\n'
                       '    </table:table-row>\n'
                       '    <table:table-row>\n'
                       f'     <table:table-cell office:value-type="string"><text:p>{c[2]}</text:p></table:table-cell>\n'
                       f'     <table:table-cell office:value-type="string"><text:p>{c[3]}</text:p></table:table-cell>\n'
                       '    </table:table-row>\n'
                       '   </table:table>')
    return "\n".join(out)


DOC = f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.text">
 <office:styles>
  <style:style style:name="Heading_20_1" style:display-name="Heading 1" style:family="paragraph" style:default-outline-level="1">
   <style:text-properties fo:font-size="18pt" fo:font-weight="bold"/>
  </style:style>
  <text:list-style style:name="LBullet">
   <text:list-level-style-bullet text:level="1" text:bullet-char="•">
    <style:list-level-properties text:list-level-position-and-space-mode="label-alignment">
     <style:list-level-label-alignment text:label-followed-by="listtab" text:list-tab-stop-position="1.27cm" fo:text-indent="-0.635cm" fo:margin-left="1.27cm"/>
    </style:list-level-properties>
   </text:list-level-style-bullet>
  </text:list-style>
 </office:styles>
 <office:body>
  <office:text>
{body()}
  </office:text>
 </office:body>
</office:document>
"""

if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("extend-signatures.fodt")
    out.write_text(DOC, encoding="utf-8")
    print(f"wrote {out}")
