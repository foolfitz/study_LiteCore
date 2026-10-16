#!/usr/bin/env python3
"""Structure summary of a Writer flat ODT (.fodt, or .fodt.gz).

Prints what a Markdown paste is supposed to produce, and nothing that varies
between runs (rsids, automatic style names, xml:ids):

  - paragraphs in body order (inside lists and table cells too): heading or
    paragraph, outline level, the paragraph style's PROGRAMMATIC name as ODF
    stores it (e.g. Heading_20_1, Text_20_body -- never the localized UI name,
    finding 031), list membership (depth, list style, bullet or number), table
    cell coordinates, the text, and runs with bold / italic / monospace /
    strike-through / hyperlink;
  - tables (rows x cols), hyperlinks, images (linked URL or embedded).

Automatic styles (P1, T3, ...) are resolved to their properties and to the
first named (programmatic) style up their parent chain, so two saves of the
same structure compare equal even when the automatic names differ.

Usage:
  md_structure.py FILE                 human-readable summary
  md_structure.py --json FILE          JSON summary
  md_structure.py --signature FILE     the JSON signature used for comparisons
  md_structure.py --compare A B        exit 0 if the signatures are equal, 1 if not
"""

import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "loext": "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0",
}


def q(prefix, local):
    return "{%s}%s" % (NS[prefix], local)


MONO_NAME = re.compile(r"mono|courier|consol|code", re.I)


class Styles:
    def __init__(self, root):
        self.named = {}  # (family, name) -> element, office:styles
        self.auto = {}   # (family, name) -> element, automatic styles
        self.lists = {}  # name -> text:list-style
        self.fonts = {}  # font-face name -> (family, pitch)
        # Named list styles live in office:styles; automatic ones (L1, L2 ...)
        # are renamed per save, so the summary reports them as "(automatic)".
        self.named_lists = set()
        for section, store in (("styles", self.named), ("automatic-styles", self.auto)):
            for container in root.iter(q("office", section)):
                for st in container.findall(q("style", "style")):
                    store[(st.get(q("style", "family")), st.get(q("style", "name")))] = st
                for ls in container.findall(q("text", "list-style")):
                    self.lists[ls.get(q("style", "name"))] = ls
                    if section == "styles":
                        self.named_lists.add(ls.get(q("style", "name")))
        for ff in root.iter(q("style", "font-face")):
            self.fonts[ff.get(q("style", "name"))] = (
                ff.get(q("svg", "font-family"), ""), ff.get(q("style", "font-pitch"), ""))

    def get(self, family, name):
        if name is None:
            return None
        # Not "a or b": an Element with no children is falsy.
        found = self.auto.get((family, name))
        return found if found is not None else self.named.get((family, name))

    def named_style(self, family, name):
        """The first non-automatic style up the chain (programmatic name)."""
        seen = 0
        while name is not None and seen < 20:
            seen += 1
            if (family, name) in self.named:
                return name
            st = self.auto.get((family, name))
            if st is None:
                return name
            name = st.get(q("style", "parent-style-name"))
        return None

    def chain(self, family, name):
        """Style elements from the given style up to the root (most specific first)."""
        out = []
        seen = 0
        while name is not None and seen < 20:
            seen += 1
            st = self.get(family, name)
            if st is None:
                break
            out.append(st)
            name = st.get(q("style", "parent-style-name"))
        return out

    def text_props(self, family, name):
        """Merged text properties along the chain (specific wins)."""
        props = {}
        for st in reversed(self.chain(family, name)):
            for tp in st.findall(q("style", "text-properties")):
                for key, value in tp.attrib.items():
                    props[key] = value
        return props

    def list_numbered(self, list_style, depth):
        ls = self.lists.get(list_style)
        if ls is None:
            return None
        for child in ls:
            if child.get(q("text", "level")) == str(depth):
                local = child.tag.split("}")[1]
                return {"list-level-style-number": "number",
                        "list-level-style-bullet": "bullet",
                        "list-level-style-image": "image"}.get(local, local)
        return None


def flags_from_props(props, styles):
    flags = []
    weights = [(k, props.get(q(p, a))) for k, p, a in (
        ("W", "fo", "font-weight"), ("A", "style", "font-weight-asian"),
        ("C", "style", "font-weight-complex"))]
    bold = "".join(k for k, v in weights if v in ("bold", "700", "800", "900"))
    if bold:
        flags.append("bold:" + bold)
    styles_ = [(k, props.get(q(p, a))) for k, p, a in (
        ("W", "fo", "font-style"), ("A", "style", "font-style-asian"),
        ("C", "style", "font-style-complex"))]
    italic = "".join(k for k, v in styles_ if v in ("italic", "oblique"))
    if italic:
        flags.append("italic:" + italic)
    font = props.get(q("style", "font-name")) or props.get(q("fo", "font-family"))
    if font:
        family, pitch = styles.fonts.get(font, (font, ""))
        if pitch == "fixed" or MONO_NAME.search(font) or MONO_NAME.search(family or ""):
            flags.append("mono")
    strike = props.get(q("style", "text-line-through-style"))
    if strike and strike != "none":
        flags.append("strike")
    underline = props.get(q("style", "text-underline-style"))
    if underline and underline != "none":
        flags.append("underline")
    return flags


class Reader:
    def __init__(self, root):
        self.styles = Styles(root)
        self.paragraphs = []
        self.tables = []
        self.links = []
        self.images = []
        body = root.find(".//" + q("office", "body"))
        text = body.find(q("office", "text")) if body is not None else None
        if text is not None:
            self.walk_block(text, list_ctx=None, cell=None)

    # Block level -----------------------------------------------------------
    def walk_block(self, parent, list_ctx, cell):
        for child in parent:
            tag = child.tag
            if tag in (q("text", "p"), q("text", "h")):
                self.paragraph(child, list_ctx, cell)
            elif tag == q("text", "list"):
                style = child.get(q("text", "style-name"))
                depth = (list_ctx["depth"] + 1) if list_ctx else 1
                inherited = list_ctx["style"] if list_ctx else None
                ctx = {"depth": depth, "style": style or inherited}
                for item in child:
                    if item.tag in (q("text", "list-item"), q("text", "list-header")):
                        # A list item can carry its own list style
                        # (text:style-override): Writer writes a pasted
                        # numbered run inside a bullet list that way.
                        override = item.get(q("text", "style-override"))
                        item_ctx = dict(ctx, style=override) if override else ctx
                        self.walk_block(item, item_ctx, cell)
            elif tag == q("table", "table"):
                self.table(child, list_ctx)
            elif tag in (q("text", "section"), q("text", "index-body")):
                self.walk_block(child, list_ctx, cell)
            elif tag.endswith("}table-of-content") or tag.endswith("}alphabetical-index"):
                for sub in child.iter(q("text", "index-body")):
                    self.walk_block(sub, list_ctx, cell)

    def table(self, element, list_ctx):
        index = len(self.tables)
        rows = []
        header_rows = 0

        def collect(node, in_header):
            nonlocal header_rows
            for child in node:
                if child.tag == q("table", "table-row"):
                    rows.append(child)
                    if in_header:
                        header_rows += 1
                elif child.tag in (q("table", "table-header-rows"),):
                    collect(child, True)
                elif child.tag in (q("table", "table-rows"), q("table", "table-row-group")):
                    collect(child, in_header)
        collect(element, False)
        cols = 0
        for r, row in enumerate(rows):
            c = 0
            for cellel in row:
                if cellel.tag == q("table", "table-cell"):
                    span = int(cellel.get(q("table", "number-columns-repeated"), "1"))
                    for _ in range(span):
                        self.walk_block(cellel, list_ctx, [index, r, c])
                        c += 1
                elif cellel.tag == q("table", "covered-table-cell"):
                    c += int(cellel.get(q("table", "number-columns-repeated"), "1"))
            cols = max(cols, c)
        self.tables.append({"index": index, "rows": len(rows), "cols": cols,
                            "headerRows": header_rows})

    # Paragraph level -------------------------------------------------------
    def paragraph(self, element, list_ctx, cell):
        st = self.styles
        style_name = element.get(q("text", "style-name"))
        named = st.named_style("paragraph", style_name)
        para_props = st.text_props("paragraph", style_name)
        kind = "h" if element.tag == q("text", "h") else "p"
        level = element.get(q("text", "outline-level"))
        runs = []
        text_parts = []
        index = len(self.paragraphs)

        def add(text, flags, href):
            if not text:
                return
            text_parts.append(text)
            key = (tuple(flags), href)
            if runs and (tuple(runs[-1]["flags"]), runs[-1].get("href")) == key:
                runs[-1]["text"] += text
            else:
                run = {"text": text, "flags": list(flags)}
                if href:
                    run["href"] = href
                runs.append(run)

        def inline(node, props, char_style, href):
            if node.text:
                add(node.text, flags_from_props(props, st), href)
            for child in node:
                tag = child.tag
                if tag == q("text", "span"):
                    sname = child.get(q("text", "style-name"))
                    merged = dict(props)
                    merged.update(st.text_props("text", sname))
                    named_char = st.named_style("text", sname) or char_style
                    inline(child, merged, named_char, href)
                elif tag == q("text", "a"):
                    link = child.get(q("xlink", "href"))
                    merged = dict(props)
                    sname = child.get(q("text", "style-name"))
                    if sname:
                        merged.update(st.text_props("text", sname))
                    before = len("".join(text_parts))
                    inline(child, merged, char_style, link)
                    self.links.append({"href": link, "paragraph": index,
                                       "text": "".join(text_parts)[before:]})
                elif tag == q("text", "s"):
                    add(" " * int(child.get(q("text", "c"), "1")), flags_from_props(props, st), href)
                elif tag == q("text", "tab"):
                    add("\t", flags_from_props(props, st), href)
                elif tag == q("text", "line-break"):
                    add("\n", flags_from_props(props, st), href)
                elif tag == q("draw", "frame"):
                    self.frame(child, index)
                elif tag in (q("office", "annotation"), q("office", "annotation-end")):
                    pass
                elif tag in (q("text", "note"),):
                    pass
                else:
                    inline(child, props, char_style, href)
                if child.tail:
                    add(child.tail, flags_from_props(props, st), href)

        inline(element, para_props, None, None)
        # Named character styles are reported by their flags only; record the
        # names too so a reader can see e.g. Source_20_Text.
        char_styles = sorted({st.named_style("text", s.get(q("text", "style-name")))
                              for s in element.iter(q("text", "span"))
                              if s.get(q("text", "style-name"))} - {None})
        char_styles = [c for c in char_styles if (("text", c) in st.named)]
        list_info = None
        if list_ctx:
            list_style = list_ctx["style"]
            if list_style is None:
                pst = st.get("paragraph", style_name)
                while pst is not None and list_style is None:
                    list_style = pst.get(q("style", "list-style-name"))
                    pst = st.get("paragraph", pst.get(q("style", "parent-style-name")))
            list_info = {"depth": list_ctx["depth"],
                         "kind": st.list_numbered(list_style, list_ctx["depth"]),
                         "style": (list_style if list_style in st.named_lists else "(automatic)")
                         if list_style else None}
        self.paragraphs.append({
            "i": index, "kind": kind, "level": int(level) if level else None,
            "style": named, "list": list_info, "cell": cell,
            "text": "".join(text_parts), "runs": runs, "charStyles": char_styles,
        })

    def frame(self, frame, paragraph):
        image = frame.find(q("draw", "image"))
        entry = {"paragraph": paragraph,
                 "width": frame.get(q("svg", "width")), "height": frame.get(q("svg", "height"))}
        if image is not None:
            href = image.get(q("xlink", "href"))
            entry["href"] = href
            entry["embedded"] = image.find(q("office", "binary-data")) is not None
        else:
            entry["href"] = None
            entry["embedded"] = False
            entry["other"] = [c.tag.split("}")[1] for c in frame]
        self.images.append(entry)


def load(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rb") as handle:
        root = ET.parse(handle).getroot()
    return root


def summarize(path):
    reader = Reader(load(path))
    return {
        "paragraphCount": len(reader.paragraphs),
        "paragraphs": reader.paragraphs,
        "tables": reader.tables,
        "links": reader.links,
        "images": reader.images,
    }


def signature(summary):
    """What must be equal for two documents to count as the same structure."""
    return {
        "paragraphs": [
            [p["kind"], p["level"], p["style"],
             [p["list"]["depth"], p["list"]["kind"]] if p["list"] else None,
             p["cell"], [[r["text"], r["flags"], r.get("href")] for r in p["runs"]],
             p["charStyles"]]
            for p in summary["paragraphs"]],
        "tables": [[t["rows"], t["cols"], t["headerRows"]] for t in summary["tables"]],
        "images": [[i["paragraph"], i.get("href") if not (i.get("href") or "").startswith("Pictures/") else "Pictures/*",
                    i.get("embedded")] for i in summary["images"]],
    }


def human(summary):
    shapes = {}
    for t in summary["tables"]:
        key = "%dx%d(h%d)" % (t["rows"], t["cols"], t["headerRows"])
        shapes[key] = shapes.get(key, 0) + 1
    lines = ["paragraphs: %d  tables: %s  links: %d  images: %d" % (
        summary["paragraphCount"],
        ", ".join("%s%s" % (k, (" x%d" % n) if n > 1 else "") for k, n in shapes.items()) or "0",
        len(summary["links"]), len(summary["images"]))]
    for p in summary["paragraphs"]:
        where = []
        if p["kind"] == "h":
            where.append("h%s" % p["level"])
        if p["list"]:
            where.append("list d%d %s" % (p["list"]["depth"], p["list"]["kind"]))
        if p["cell"]:
            where.append("cell t%d r%d c%d" % tuple(p["cell"]))
        runs = " ".join(
            "[%s%s]%r" % (",".join(r["flags"]), (" ->" + r["href"]) if r.get("href") else "", r["text"])
            for r in p["runs"] if r["flags"] or r.get("href"))
        lines.append("  [%d] %-22s %-28s %r%s%s" % (
            p["i"], p["style"], " ".join(where), p["text"],
            ("  runs: " + runs) if runs else "",
            ("  charStyles: " + ",".join(p["charStyles"])) if p["charStyles"] else ""))
    for link in summary["links"]:
        lines.append("  link p%d %s %r" % (link["paragraph"], link["href"], link["text"]))
    for image in summary["images"]:
        lines.append("  image p%d href=%s embedded=%s %sx%s" % (
            image["paragraph"], (image.get("href") or "")[:80], image.get("embedded"),
            image.get("width"), image.get("height")))
    return "\n".join(lines)


def main(argv):
    if len(argv) >= 2 and argv[1] == "--json":
        print(json.dumps(summarize(argv[2]), ensure_ascii=False, indent=1))
    elif len(argv) >= 2 and argv[1] == "--signature":
        print(json.dumps(signature(summarize(argv[2])), ensure_ascii=False))
    elif len(argv) >= 2 and argv[1] == "--compare":
        a = signature(summarize(argv[2]))
        b = signature(summarize(argv[3]))
        same = a == b
        print("SAME" if same else "DIFFERENT")
        return 0 if same else 1
    elif len(argv) == 2:
        print(human(summarize(argv[1])))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
