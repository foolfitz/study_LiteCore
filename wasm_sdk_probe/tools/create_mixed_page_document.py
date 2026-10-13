#!/usr/bin/env python3
"""A document of EIGHT pages in MIXED sizes and orientations (the fixture P1 needs).

Why it exists.  `specs/SPEC-M3-link-batch.md` section 5 P1 (as rewritten by
10.8) wants, beside the 60-page document, a fixture whose pages are not all the
same size, so that a page number computed from the rectangles the engine
reports cannot pass by assuming every page has the same height or the same x.
`tools/create_long_document.py` makes 60 identical A4 portrait pages; the
rectangles it produces cannot tell "per-page rectangles" from "equal page
heights" (findings/evidence/link-batch/page-rectangles/README.md says so).

Shape.  Exactly 8 pages, in this order of page styles:

    1  A4 portrait        21    x 29.7  cm      5  US Letter portrait 21.59 x 27.94 cm
    2  A4 landscape       29.7  x 21    cm      6  A4 portrait        21    x 29.7  cm
    3  A4 landscape       29.7  x 21    cm      7  A3 landscape       42    x 29.7  cm
    4  A5 portrait        14.8  x 21    cm      8  A4 portrait        21    x 29.7  cm

Each page has its OWN master page (so pages 2 and 3, which share a size, are
still two master pages, and pages 1, 6 and 8 are three).  The switch between
master pages is made by an automatic paragraph style with
`style:master-page-name` on that page's heading, which also forces the break:
the layout cannot fit two pages' text on one sheet whatever the font metrics
turn out to be.  Margins are 2 cm on every side of every page.

Page 1's master page is called `Standard` (LibreOffice insists on a page style
by that name; naming page 1's after it means the document carries exactly the
eight master pages and no ninth, unused one).  Pages 2..8 are `MP2`..`MP8`.

Markers.  `MP-PAGE-{n}` on each heading and `MP-P{n}-L{k}` on each line.  There
are 9 lines per page, so k is one digit and no marker is a prefix of another
(`MP-P1-L1` is not inside `MP-P1-L10`; with 10 lines it would be).  9 short
lines plus a 16 pt heading take about 6 cm of the 17 cm of text height A5 has,
the smallest page here, so no page can spill onto a second sheet; whether
native LibreOffice agrees is a measurement, not an assumption
(tools/run_native_mixed_page_rectangles.sh).

Deterministic.  Every zip member carries a fixed timestamp, so the same
arguments give the same bytes on every run.  (tools/create_long_document.py
does not: `writestr(name, ...)` stamps the current time, which is why its
60-page file hashed differently on two runs.)

Not part of any frozen corpus and never written into `dist/`.  The .odt is
not committed; the runner builds it into a scratch directory.

    create_mixed_page_document.py --out PATH      write the document, print its sha256
    create_mixed_page_document.py --verify PATH   check any .odt against this spec (exit 1 if it fails)
    create_mixed_page_document.py --self-test     verify what build() writes, and that verification
                                                  goes red on each of the built-in mutations
    create_mixed_page_document.py --self-test --mutate NAME
                                                  verify a MUTATED copy of the output (expected red, exit 1)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

LINES_PER_PAGE = 9  # one digit: no marker is a prefix of another

# (number, master page name, width cm, height cm, orientation)
PAGES: list[tuple[int, str, str, str, str]] = [
    (1, "Standard", "21cm", "29.7cm", "portrait"),   # A4 portrait
    (2, "MP2", "29.7cm", "21cm", "landscape"),       # A4 landscape
    (3, "MP3", "29.7cm", "21cm", "landscape"),       # A4 landscape
    (4, "MP4", "14.8cm", "21cm", "portrait"),        # A5 portrait
    (5, "MP5", "21.59cm", "27.94cm", "portrait"),    # US Letter portrait
    (6, "MP6", "21cm", "29.7cm", "portrait"),        # A4 portrait
    (7, "MP7", "42cm", "29.7cm", "landscape"),       # A3 landscape
    (8, "MP8", "21cm", "29.7cm", "portrait"),        # A4 portrait
]
PAGE_NAMES = {1: "A4 portrait", 2: "A4 landscape", 3: "A4 landscape",
              4: "A5 portrait", 5: "US Letter portrait", 6: "A4 portrait",
              7: "A3 landscape", 8: "A4 portrait"}
MARGIN = "2cm"

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
}


def q(prefix: str, local: str) -> str:
    return "{%s}%s" % (NS[prefix], local)


MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""

# Fixed for every member: the zip header has a timestamp, and a generator that
# lets the clock into the bytes cannot be asked "is this the same document?".
FIXED_DATE = (1980, 1, 1, 0, 0, 0)
MIMETYPE = "application/vnd.oasis.opendocument.text"
MEMBER_ORDER = ["mimetype", "META-INF/manifest.xml", "styles.xml", "content.xml"]


def build_styles() -> str:
    layouts = []
    masters = []
    for n, master, width, height, orientation in PAGES:
        layouts.append(
            f'  <style:page-layout style:name="MPLayout{n}">\n'
            f'   <style:page-layout-properties fo:page-width="{width}" '
            f'fo:page-height="{height}" style:print-orientation="{orientation}" '
            f'fo:margin-top="{MARGIN}" fo:margin-bottom="{MARGIN}" '
            f'fo:margin-left="{MARGIN}" fo:margin-right="{MARGIN}"/>\n'
            f'  </style:page-layout>\n')
        masters.append(
            f'  <style:master-page style:name="{master}" '
            f'style:page-layout-name="MPLayout{n}"/>\n')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<office:document-styles xmlns:office="%(office)s" xmlns:style="%(style)s" '
        'xmlns:fo="%(fo)s" office:version="1.2">\n'
        ' <office:styles>\n'
        '  <style:style style:name="Standard" style:family="paragraph" style:class="text"/>\n'
        '  <style:style style:name="Heading_20_1" style:display-name="Heading 1" '
        'style:family="paragraph" style:parent-style-name="Standard">\n'
        '   <style:text-properties fo:font-size="16pt"/>\n'
        '  </style:style>\n'
        ' </office:styles>\n'
        ' <office:automatic-styles>\n' % NS
        + "".join(layouts)
        + ' </office:automatic-styles>\n'
        ' <office:master-styles>\n'
        + "".join(masters)
        + ' </office:master-styles>\n'
        '</office:document-styles>\n')


def build_content(lines_per_page: int = LINES_PER_PAGE) -> str:
    styles = []
    body = []
    for n, master, *_ in PAGES:
        styles.append(
            f'  <style:style style:name="MPH{n}" style:family="paragraph" '
            f'style:parent-style-name="Heading_20_1" '
            f'style:master-page-name="{master}"/>\n')
        body.append(f'   <text:h text:style-name="MPH{n}" text:outline-level="1">'
                    f'MP-PAGE-{n}</text:h>\n')
        for k in range(1, lines_per_page + 1):
            body.append('   <text:p text:style-name="Standard">'
                        f'MP-P{n}-L{k} lorem ipsum dolor sit amet</text:p>\n')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<office:document-content xmlns:office="%(office)s" xmlns:text="%(text)s" '
        'xmlns:style="%(style)s" xmlns:fo="%(fo)s" office:version="1.2">\n'
        ' <office:automatic-styles>\n' % NS
        + "".join(styles)
        + ' </office:automatic-styles>\n'
        ' <office:body>\n'
        '  <office:text>\n'
        + "".join(body)
        + '  </office:text>\n'
        ' </office:body>\n'
        '</office:document-content>\n')


def pack(entries: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in MEMBER_ORDER:
            info = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            info.create_system = 3
            info.external_attr = 0o644 << 16
            # The ODF package rule: mimetype first and stored.
            info.compress_type = (zipfile.ZIP_STORED if name == "mimetype"
                                  else zipfile.ZIP_DEFLATED)
            archive.writestr(info, entries[name])
    return buffer.getvalue()


def build(lines_per_page: int = LINES_PER_PAGE) -> bytes:
    return pack({
        "mimetype": MIMETYPE,
        "META-INF/manifest.xml": MANIFEST,
        "styles.xml": build_styles(),
        "content.xml": build_content(lines_per_page),
    })


# ---------------------------------------------------------------------------
# Verification.  Reads a package (any .odt), never trusts build().
# ---------------------------------------------------------------------------

def verify_document(raw: bytes) -> list[str]:
    """Return the list of ways `raw` is not the fixture (empty = it is)."""
    problems: list[str] = []
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        styles = ElementTree.fromstring(archive.read("styles.xml"))
        content = ElementTree.fromstring(archive.read("content.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        return [f"package unreadable: {exc!r}"]

    infos = archive.infolist()
    if not infos or infos[0].filename != "mimetype" or infos[0].compress_type != zipfile.ZIP_STORED:
        problems.append("mimetype is not the first, stored member")
    if set(archive.namelist()) != set(MEMBER_ORDER):
        problems.append(f"unexpected members {sorted(archive.namelist())}")

    # --- page layouts and master pages ---------------------------------------
    layouts = {}
    for el in styles.iter(q("style", "page-layout")):
        props = el.find(q("style", "page-layout-properties"))
        layouts[el.get(q("style", "name"))] = props
    masters = [(el.get(q("style", "name")), el.get(q("style", "page-layout-name")))
               for el in styles.iter(q("style", "master-page"))]
    if len(masters) != 8:
        problems.append(f"{len(masters)} master pages, expected 8")
    if len({name for name, _ in masters}) != len(masters):
        problems.append("master page names are not distinct")
    if len(layouts) != 8:
        problems.append(f"{len(layouts)} page layouts, expected 8")
    by_master = dict(masters)
    for n, master, width, height, orientation in PAGES:
        layout_name = by_master.get(master)
        if layout_name is None:
            problems.append(f"page {n}: master page {master!r} missing")
            continue
        props = layouts.get(layout_name)
        if props is None:
            problems.append(f"page {n}: layout {layout_name!r} missing")
            continue
        got = {
            "width": props.get(q("fo", "page-width")),
            "height": props.get(q("fo", "page-height")),
            "orientation": props.get(q("style", "print-orientation")),
        }
        for side in ("top", "bottom", "left", "right"):
            got["margin-" + side] = props.get(q("fo", "margin-" + side))
        want = {"width": width, "height": height, "orientation": orientation,
                "margin-top": MARGIN, "margin-bottom": MARGIN,
                "margin-left": MARGIN, "margin-right": MARGIN}
        if got != want:
            problems.append(f"page {n} ({PAGE_NAMES[n]}): layout {got} != {want}")

    # --- the master page each page switches to, in order ---------------------
    switch = {}  # automatic paragraph style name -> master page name
    for el in content.find(q("office", "automatic-styles")).iter(q("style", "style")):
        mp = el.get(q("style", "master-page-name"))
        if mp is not None:
            switch[el.get(q("style", "name"))] = mp
    text = content.find(q("office", "body")).find(q("office", "text"))
    children = list(text)
    headings = [c for c in children if c.tag == q("text", "h")]
    switched = [switch.get(h.get(q("text", "style-name"))) for h in headings]
    if len(switch) != 8:
        problems.append(f"{len(switch)} paragraph styles carry a master page, expected 8")
    if switched != [m for _, m, *_ in PAGES]:
        problems.append(f"headings switch to {switched}, expected {[m for _, m, *_ in PAGES]}")
    for c in children:
        if c.tag == q("text", "p") and switch.get(c.get(q("text", "style-name"))) is not None:
            problems.append("a body line (not a heading) also switches master page")
            break
    if [("".join(h.itertext())) for h in headings] != [f"MP-PAGE-{n}" for n, *_ in PAGES]:
        problems.append("heading texts are not MP-PAGE-1..8 in order")

    # --- the lines: each exactly once, under its own heading ------------------
    current = 0
    seen: list[str] = []
    for c in children:
        t = "".join(c.itertext())
        if c.tag == q("text", "h"):
            current += 1
        elif c.tag == q("text", "p"):
            m = re.match(r"MP-P(\d+)-L(\d+) ", t)
            if not m or int(m.group(1)) != current:
                problems.append(f"line {t!r} is not under heading {current}")
            seen.append(f"MP-P{m.group(1)}-L{m.group(2)}" if m else t)
    want_lines = [f"MP-P{n}-L{k}" for n, *_ in PAGES for k in range(1, LINES_PER_PAGE + 1)]
    if seen != want_lines:
        problems.append(f"lines differ from MP-P{{1..8}}-L{{1..{LINES_PER_PAGE}}}: "
                        f"{len(seen)} found, {len(want_lines)} expected")
    # Rough bound that it cannot overflow the smallest page (A5: 17 cm of text
    # height): a 16 pt heading ~ 1 cm, each 12 pt line ~ 0.6 cm even if it wrapped twice.
    per_page = len(seen) / len(PAGES)
    if 1.0 + 2 * 0.6 * per_page > 17.0:
        problems.append("line count could overflow an A5 page")
    return problems


# ---------------------------------------------------------------------------
# Mutations of the generator's own output, for the self-test.  Each replaces
# text in one member and re-packs; `old` MUST be present, or the mutation did
# not happen and the test says so.
# ---------------------------------------------------------------------------

def _unpack(raw: bytes) -> dict[str, str]:
    archive = zipfile.ZipFile(io.BytesIO(raw))
    return {name: archive.read(name).decode("utf-8") for name in archive.namelist()}


def _mutate(raw: bytes, member: str, old: str, new: str) -> bytes:
    entries = _unpack(raw)
    if old not in entries[member]:
        raise RuntimeError(f"mutation did not apply: {old!r} not in {member}")
    entries[member] = entries[member].replace(old, new, 1)
    return pack(entries)


MUTATIONS = {
    # A5 turned into A4 width.
    "width-p4": ("styles.xml", 'fo:page-width="14.8cm"', 'fo:page-width="21cm"'),
    # A3 landscape given portrait dimensions.
    "swap-p7": ("styles.xml", 'fo:page-width="42cm" fo:page-height="29.7cm" style:print-orientation="landscape"',
                'fo:page-width="29.7cm" fo:page-height="42cm" style:print-orientation="landscape"'),
    # Letter's height becomes A4's.
    "height-p5": ("styles.xml", 'fo:page-height="27.94cm"', 'fo:page-height="29.7cm"'),
    # Page 2 loses its landscape orientation flag.
    "orientation-p2": ("styles.xml", 'fo:page-width="29.7cm" fo:page-height="21cm" style:print-orientation="landscape"',
                       'fo:page-width="29.7cm" fo:page-height="21cm" style:print-orientation="portrait"'),
    # A margin of 2 cm becomes 3 cm on one page.
    "margin-p6": ("styles.xml", 'style:name="MPLayout6">\n   <style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" style:print-orientation="portrait" fo:margin-top="2cm"',
                  'style:name="MPLayout6">\n   <style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" style:print-orientation="portrait" fo:margin-top="3cm"'),
    # Heading 5 switches to page 4's master page.
    "wrong-master-p5": ("content.xml", 'style:name="MPH5" style:family="paragraph" style:parent-style-name="Heading_20_1" style:master-page-name="MP5"',
                        'style:name="MPH5" style:family="paragraph" style:parent-style-name="Heading_20_1" style:master-page-name="MP4"'),
    # Page 3 loses its master page (7 left).
    "drop-master-p3": ("styles.xml", '  <style:master-page style:name="MP3" style:page-layout-name="MPLayout3"/>\n', ''),
    # A line goes missing.
    "drop-line": ("content.xml", '   <text:p text:style-name="Standard">MP-P4-L5 lorem ipsum dolor sit amet</text:p>\n', ''),
}


def self_test(mutate: str | None = None) -> int:
    """It has to be possible for this generator, and its verifier, to be wrong."""
    failures: list[str] = []
    checks = 0

    def verify(name: str, condition: bool, detail: str = "") -> None:
        nonlocal checks
        checks += 1
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    raw = build()

    if mutate is not None:
        # Show red once: verify a mutated copy and report its verdict honestly.
        member, old, new = MUTATIONS[mutate]
        mutated = _mutate(raw, member, old, new)
        problems = verify_document(mutated)
        print(f"mutation {mutate!r} ({member}):")
        for p in problems:
            print(f"  FAIL  {p}")
        if not problems:
            print("  (verification passed a mutated document: the verifier is blind to this)")
            return 0
        return 1

    problems = verify_document(raw)
    verify("the generator's own output passes verification", not problems, "; ".join(problems))
    archive = zipfile.ZipFile(io.BytesIO(raw))
    styles_xml = archive.read("styles.xml").decode("utf-8")
    content_xml = archive.read("content.xml").decode("utf-8")
    verify("8 master pages are declared", styles_xml.count("<style:master-page ") == 8)
    verify("8 paragraph styles switch master page, one per heading",
           content_xml.count("style:master-page-name=") == 8
           and content_xml.count("<text:h ") == 8)
    verify("page sizes are the listed ones",
           [(w, h) for _, _, w, h, _ in PAGES]
           == [("21cm", "29.7cm"), ("29.7cm", "21cm"), ("29.7cm", "21cm"),
               ("14.8cm", "21cm"), ("21.59cm", "27.94cm"), ("21cm", "29.7cm"),
               ("42cm", "29.7cm"), ("21cm", "29.7cm")])
    verify("pages 2, 3 and 7 are wider than tall, the others are not",
           [float(w[:-2]) > float(h[:-2]) for _, _, w, h, _ in PAGES]
           == [False, True, True, False, False, False, True, False])
    verify("every marker is unique (no marker is a prefix of another)",
           all(content_xml.count(f"MP-P{n}-L{k} ") == 1
               for n, *_ in PAGES for k in range(1, LINES_PER_PAGE + 1))
           and all(content_xml.count(f">MP-PAGE-{n}<") == 1 for n, *_ in PAGES))
    verify("the mimetype entry is first and stored",
           archive.infolist()[0].filename == "mimetype"
           and archive.infolist()[0].compress_type == zipfile.ZIP_STORED)
    verify("styles.xml and content.xml parse",
           _parses(styles_xml) and _parses(content_xml))
    verify("two builds in one process are byte-identical", build() == build())
    verify("every member carries the fixed timestamp",
           all(i.date_time == FIXED_DATE for i in archive.infolist()))

    # Every mutation must move the verdict from green to red.
    for name, (member, old, new) in MUTATIONS.items():
        try:
            mutated = _mutate(raw, member, old, new)
        except RuntimeError as exc:
            verify(f"mutation {name} applies", False, str(exc))
            continue
        verify(f"mutation {name} turns verification red",
               bool(verify_document(mutated)))

    print(f"\nself-test: {checks - len(failures)}/{checks} checks held")
    return 1 if failures else 0


def _parses(xml: str) -> bool:
    try:
        ElementTree.fromstring(xml)
        return True
    except ElementTree.ParseError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default=None)
    parser.add_argument("--verify", default=None, metavar="PATH")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--mutate", choices=sorted(MUTATIONS), default=None,
                        help="with --self-test: verify a mutated copy (expected red)")
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.mutate)
    if args.mutate:
        parser.error("--mutate needs --self-test")
    if args.verify:
        problems = verify_document(Path(args.verify).read_bytes())
        for p in problems:
            print(f"FAIL  {p}")
        print(f"{args.verify}: {'not the fixture' if problems else 'is the fixture'}")
        return 1 if problems else 0
    raw = build()
    digest = hashlib.sha256(raw).hexdigest()
    if args.out:
        Path(args.out).write_bytes(raw)
        print(f"{args.out}: 8 pages, {len(raw)} bytes, sha256 {digest}")
    else:
        print(f"8 pages, {len(raw)} bytes, sha256 {digest} (use --out to write it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
