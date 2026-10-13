import sys, pathlib
out = pathlib.Path(sys.argv[1])
HEAD = '''<?xml version="1.0" encoding="UTF-8"?>
<office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.text">
<office:automatic-styles>
 <style:style style:name="PI" style:family="paragraph"><style:paragraph-properties fo:text-indent="1cm"/></style:style>
 <style:style style:name="TH" style:family="text"><style:text-properties text:display="none"/></style:style>
 <text:list-style style:name="L1">
  <text:list-level-style-bullet text:level="1" text:bullet-char="&#x2022;">
   <style:list-level-properties text:list-level-position-and-space-mode="label-alignment">
    <style:list-level-label-alignment text:label-followed-by="listtab" text:list-tab-stop-position="1.27cm" fo:text-indent="-0.635cm" fo:margin-left="1.27cm"/>
   </style:list-level-properties>
  </text:list-level-style-bullet>
 </text:list-style>
</office:automatic-styles>
<office:body><office:text>
'''
TAIL = '</office:text></office:body></office:document>\n'
docs = {
  'bullet': '<text:list text:style-name="L1"><text:list-item><text:p>Alpha one</text:p></text:list-item></text:list>\n<text:p>Beta two</text:p>\n<text:list text:style-name="L1"><text:list-item><text:p>Gamma three</text:p></text:list-item></text:list>\n',
  'indent': '<text:p text:style-name="PI">Indented first</text:p>\n<text:p>Second</text:p>\n',
  'hidden-end': '<text:p>Start</text:p>\n<text:p>End<text:span text:style-name="TH">HIDDEN</text:span></text:p>\n',
  'hidden-start': '<text:p><text:span text:style-name="TH">HID</text:span>Start</text:p>\n<text:p>End</text:p>\n',
}
for name, body in docs.items():
    (out / f'{name}.fodt').write_text(HEAD + body + TAIL, encoding='utf-8')
    print(out / f'{name}.fodt')
