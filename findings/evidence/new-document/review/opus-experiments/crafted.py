"""N6 predicate probes: saved files a broken engine could write, read with the
tool's own reader (gen.describe) and judged with N6's own comparator (gen.compare)."""
import io, json, sys, zipfile
from pathlib import Path
S = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(S / "tools"))
import make_new_document_templates as gen

files = gen.generate()
A4 = files["en-US_zh-TW_A4.odt"]
LT = files["en-US_zh-TW_Letter.odt"]

def repack(data, edits):
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        for info in src.infolist():
            body = src.read(info.filename)
            if info.filename in edits:
                body = edits[info.filename](body.decode()).encode()
            zf.writestr(info, body)
    return out.getvalue()

def judge(label, data, record):
    d = gen.describe(data)
    diff = gen.compare(record, d)
    print(f"{label:62} N6 diffs={diff}  (asian={d['asian']} paper={d['paper']} pageMm={d['pageMm']})")
    return d

# 1. content.xml: the paragraph the user typed into carries an automatic style
#    that says zh-CN / Noto Sans CJK KR (what a leak of the browser language into
#    typed text would look like).  styles.xml untouched.
def content_override(t):
    t = t.replace('xmlns:text=', 'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
                  'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:text=')
    t = t.replace('<office:body>', '<office:automatic-styles><style:style style:name="P1" style:family="paragraph" '
                  'style:parent-style-name="Standard"><style:text-properties style:font-name-asian="Noto Sans CJK KR" '
                  'style:language-asian="zh" style:country-asian="CN" fo:language="en" fo:country="GB"/></style:style>'
                  '</office:automatic-styles><office:body>')
    return t.replace('<text:p text:style-name="Standard"/>', '<text:p text:style-name="P1">zqx</text:p>')
judge("1 content.xml automatic style P1 = zh-CN/KR/en-GB on the typed text", repack(A4["bytes"], {"content.xml": content_override}), A4["record"])

# 2. styles.xml: the Standard paragraph style (what every paragraph inherits)
#    overrides the default-style's languages.
def standard_override(t):
    return t.replace('<style:style style:name="Standard" style:family="paragraph" style:class="text"/>',
                     '<style:style style:name="Standard" style:family="paragraph" style:class="text"><style:text-properties '
                     'style:language-asian="zh" style:country-asian="CN" style:font-name-asian="Noto Sans CJK KR"/></style:style>')
judge("2 styles.xml Standard style = zh-CN/KR over a correct default-style", repack(A4["bytes"], {"styles.xml": standard_override}), A4["record"])

# 3. styles.xml: two page layouts; the first (unused) is A4, the master page
#    Standard uses the second, which is Letter.  A TW-arm document whose pages are Letter.
def two_layouts(t):
    t = t.replace('<style:page-layout style:name="Mpm1">',
                  '<style:page-layout style:name="Mpm1"><style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm"/></style:page-layout>'
                  '<style:page-layout style:name="Mpm2">', 1)
    t = t.replace('fo:page-width="21cm" fo:page-height="29.7cm" style:print', 'fo:page-width="8.5in" fo:page-height="11in" style:print')
    return t.replace('style:page-layout-name="Mpm1"', 'style:page-layout-name="Mpm2"')
d = judge("3 Standard master page -> Mpm2 (Letter); an unused Mpm1 (A4) first", repack(A4["bytes"], {"styles.xml": two_layouts}), A4["record"])

# 4. styles.xml: the font-face declaration NAMED "Noto Sans CJK TC" whose family is KR.
def decl_family(t):
    return t.replace("svg:font-family=\"&apos;Noto Sans CJK TC&apos;\"", "svg:font-family=\"&apos;Noto Sans CJK KR&apos;\"")
judge("4 decl named 'Noto Sans CJK TC' with svg:font-family KR", repack(A4["bytes"], {"styles.xml": decl_family}), A4["record"])

# 5. (working product, Q2) the decl is renamed on save with a collision suffix: TC1 -> TC family.
def decl_suffix(t):
    t = t.replace('style:name="Noto Sans CJK TC"', 'style:name="Noto Sans CJK TC1"')
    return t.replace('style:font-name-asian="Noto Sans CJK TC"', 'style:font-name-asian="Noto Sans CJK TC1"')
judge("5 (working) decl renamed 'Noto Sans CJK TC1', family TC", repack(A4["bytes"], {"styles.xml": decl_suffix}), A4["record"])

# 6. (Q2) units: A4 written in inches as the WASM engine does (hand test: 8.2681in x 11.6929in); Letter in mm
def a4_inches(t):
    return t.replace('fo:page-width="21cm" fo:page-height="29.7cm"', 'fo:page-width="8.2681in" fo:page-height="11.6929in"')
judge("6 (working) A4 written 8.2681in x 11.6929in", repack(A4["bytes"], {"styles.xml": a4_inches}), A4["record"])
def letter_mm(t):
    return t.replace('fo:page-width="8.5in" fo:page-height="11in"', 'fo:page-width="215.9mm" fo:page-height="279.4mm"')
judge("6b (working) Letter written 215.9mm x 279.4mm", repack(LT["bytes"], {"styles.xml": letter_mm}), LT["record"])
def letter_pc(t):
    return t.replace('fo:page-width="8.5in" fo:page-height="11in"', 'fo:page-width="51pc" fo:page-height="66pc"')
judge("6c (working, ODF-legal unit) Letter written 51pc x 66pc", repack(LT["bytes"], {"styles.xml": letter_pc}), LT["record"])
