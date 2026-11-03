#!/usr/bin/env python3
"""The red case of check_writer_enter_range.canonical(), run before E5 used it.  An rsid-only automatic paragraph style must read as its parent;
a style with any other property, or changed text, must not.  python3 -I reader_check.py  (prints READER_HOLDS or READER_RED)"""
import io
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "wasm_sdk_probe/tools"))
import check_writer_enter_range as e  # noqa: E402
import check_writer_toggle as t  # noqa: E402

raw = t.LEVELS.read_bytes()
xml = zipfile.ZipFile(io.BytesIO(raw)).read("content.xml").decode()
xml = xml.replace("<office:document-content ", '<office:document-content xmlns:officeooo="http://openoffice.org/2009/office" ', 1)
AUTO = "<office:automatic-styles>"


def rebuilt(content):
    out, source = io.BytesIO(), zipfile.ZipFile(io.BytesIO(raw))
    with zipfile.ZipFile(out, "w") as archive:
        for info in source.infolist():
            archive.writestr(info, content.encode() if info.filename == "content.xml" else source.read(info.filename))
    return out.getvalue()


def variant(props):
    style = f'<style:style style:name="PX" style:family="paragraph" style:parent-style-name="Text_20_body">{props}</style:style>'
    return rebuilt(xml.replace(AUTO, AUTO + style, 1).replace('text:style-name="Text_20_body">BRAVO', 'text:style-name="PX">BRAVO', 1))


base = e.canonical(rebuilt(xml))
cases = {"rsid only (keeps the newline after it)": (variant('<style:paragraph-properties officeooo:paragraph-rsid="00aa"/><style:text-properties officeooo:rsid="00bb"/>'), True),
         "bold and an rsid": (variant('<style:text-properties fo:font-weight="bold" officeooo:rsid="00bb"/>'), False),
         "a margin": (variant('<style:paragraph-properties fo:margin-left="1cm"/>'), False),
         "the text changed": (rebuilt(xml.replace("BRAVO plain", "BRAVO plainX", 1)), False)}
held = True
for name, (document, same) in cases.items():
    got = e.canonical(document) == base
    held &= got == same
    print(f"{name:40} {'equal' if got else 'different':9} expected {'equal' if same else 'different'}")
print("READER_HOLDS" if held else "READER_RED")
raise SystemExit(0 if held else 1)
