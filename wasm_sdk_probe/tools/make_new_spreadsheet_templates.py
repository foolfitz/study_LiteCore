#!/usr/bin/env python3
"""The blank spreadsheets the Nextcloud host writes for "+ New -> New spreadsheet" (study_LiteCore specs/SPEC-P-demo-batch-6.md, section 1.1).

The spreadsheet half of make_new_document_templates.py, and deliberately a copy of its rules: a style-less file is not neutral in this engine
(SPEC-M3-new-document.md), and in a spreadsheet the language also decides how numbers and dates are read.  So every blank spreadsheet STATES its
defaults: the three languages, the three fonts, the size and the page, one file per (western, asian, paper) triple, the same triples and the
same choice as the documents (`BlankDocument::choose()`).  The triples, fonts, papers, the packaging and odfvalidator are imported from the
document generator, not copied, so the two sets cannot drift apart.

Calc's own defaults where they differ from Writer's: the western font `Liberation Sans`, 10pt.  One sheet, `Sheet1` (`L-sheet-name`).

  make_new_spreadsheet_templates.py --out DIR          write the set and MANIFEST.json
  make_new_spreadsheet_templates.py --check DIR        regenerate in memory, compare byte for byte
  make_new_spreadsheet_templates.py --validate DIR     odfvalidator on every .ods
  make_new_spreadsheet_templates.py --describe F.ods   the defaults a saved or template ODS states
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import sys
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_new_document_templates as odt  # noqa: E402
from make_new_document_templates import (ASIAN_FONT, COMPLEX, COMPLEX_FONT, EPOCH, GENERATOR, MARGIN, NS, PAPERS, _q, _xml,  # noqa: E402
                                         classify_paper, sha256, split_tag, to_mm, triples)

ODS = "application/vnd.oasis.opendocument.spreadsheet"
WESTERN_FONT = "Liberation Sans"
FONT_SIZE = "10pt"
SHEET = "Sheet1"
TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"


def file_name(western: str, asian: str, paper: str) -> str:
    return f"{western}_{asian}_{paper}.ods"


def manifest_xml() -> bytes:
    return _xml(f"""
<manifest:manifest xmlns:manifest="{NS['manifest']}" manifest:version="1.3">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.3" manifest:media-type="{ODS}"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
</manifest:manifest>""")


def content_xml() -> bytes:
    return _xml(f"""
<office:document-content xmlns:office="{NS['office']}" xmlns:style="{NS['style']}" xmlns:table="{TABLE}" office:version="1.3">
 <office:automatic-styles>
  <style:style style:name="ta1" style:family="table" style:master-page-name="Default">
   <style:table-properties table:display="true" style:writing-mode="lr-tb"/>
  </style:style>
 </office:automatic-styles>
 <office:body>
  <office:spreadsheet>
   <table:table table:name="{SHEET}" table:style-name="ta1">
    <table:table-column table:default-cell-style-name="Default"/>
    <table:table-row>
     <table:table-cell/>
    </table:table-row>
   </table:table>
  </office:spreadsheet>
 </office:body>
</office:document-content>""")


def styles_xml(western: str, asian: str, paper: str) -> bytes:
    w_lang, w_country = split_tag(western)
    a_lang, a_country = split_tag(asian)
    c_lang, c_country = split_tag(COMPLEX)
    asian_font = ASIAN_FONT[asian]
    width, height = PAPERS[paper]
    return _xml(f"""
<office:document-styles xmlns:office="{NS['office']}" xmlns:style="{NS['style']}" xmlns:fo="{NS['fo']}" xmlns:svg="{NS['svg']}" office:version="1.3">
 <office:font-face-decls>
  <style:font-face style:name="{WESTERN_FONT}" svg:font-family="&apos;{WESTERN_FONT}&apos;" style:font-family-generic="swiss" style:font-pitch="variable"/>
  <style:font-face style:name="{asian_font}" svg:font-family="&apos;{asian_font}&apos;" style:font-family-generic="system" style:font-pitch="variable"/>
 </office:font-face-decls>
 <office:styles>
  <style:default-style style:family="table-cell">
   <style:text-properties style:font-name="{WESTERN_FONT}" fo:font-size="{FONT_SIZE}" fo:language="{w_lang}" fo:country="{w_country}" style:font-name-asian="{asian_font}" style:font-size-asian="{FONT_SIZE}" style:language-asian="{a_lang}" style:country-asian="{a_country}" style:font-name-complex="{COMPLEX_FONT}" style:font-size-complex="{FONT_SIZE}" style:language-complex="{c_lang}" style:country-complex="{c_country}"/>
  </style:default-style>
  <style:style style:name="Default" style:family="table-cell"/>
 </office:styles>
 <office:automatic-styles>
  <style:page-layout style:name="Mpm1">
   <style:page-layout-properties fo:page-width="{width}" fo:page-height="{height}" style:print-orientation="portrait" fo:margin-top="{MARGIN}" fo:margin-bottom="{MARGIN}" fo:margin-left="{MARGIN}" fo:margin-right="{MARGIN}"/>
  </style:page-layout>
 </office:automatic-styles>
 <office:master-styles>
  <style:master-page style:name="Default" style:page-layout-name="Mpm1"/>
 </office:master-styles>
</office:document-styles>""")


def build(western: str, asian: str, paper: str) -> bytes:
    """The ODS package for one triple, packed exactly as the documents are (STORED, fixed time and order, mimetype first)."""
    entries = [("mimetype", ODS.encode("ascii")), ("META-INF/manifest.xml", manifest_xml()), ("meta.xml", odt.meta_xml()),
               ("styles.xml", styles_xml(western, asian, paper)), ("content.xml", content_xml())]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=EPOCH)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    return buffer.getvalue()


def generate() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for western, asian, paper in triples():
        data = build(western, asian, paper)
        out[file_name(western, asian, paper)] = {
            "bytes": data,
            "record": {"sha256": sha256(data), "bytes": len(data), "western": western, "asian": asian, "complex": COMPLEX, "paper": paper,
                       "fonts": {"western": WESTERN_FONT, "asian": ASIAN_FONT[asian], "complex": COMPLEX_FONT}, "sheet": SHEET},
        }
    return out


def manifest(files: dict[str, dict[str, Any]]) -> dict[str, Any]:
    me = Path(__file__).resolve()
    return {"spec": "specs/SPEC-P-demo-batch-6.md", "generator": {"path": "wasm_sdk_probe/tools/" + me.name, "sha256": sha256(me.read_bytes())},
            "odfVersion": "1.3", "files": {name: entry["record"] for name, entry in sorted(files.items())}}


def manifest_bytes(files: dict[str, dict[str, Any]]) -> bytes:
    return (json.dumps(manifest(files), indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    files = generate()
    stale = [p.name for p in out.glob("*.ods") if p.name not in files]
    for name, entry in files.items():
        (out / name).write_bytes(entry["bytes"])
    (out / "MANIFEST.json").write_bytes(manifest_bytes(files))
    return {"written": len(files), "manifest": str(out / "MANIFEST.json"), "staleNotRemoved": stale}


def check(out: Path) -> list[str]:
    files = generate()
    problems = [f"missing {n}" if not (out / n).is_file() else f"differs {n}" for n, e in files.items()
                if not (out / n).is_file() or (out / n).read_bytes() != e["bytes"]]
    on_disk = out / "MANIFEST.json"
    if not on_disk.is_file():
        problems.append("missing MANIFEST.json")
    else:
        want, have = json.loads(manifest_bytes(files)), json.loads(on_disk.read_text(encoding="utf-8"))
        if want["files"] != have.get("files"):
            problems.append("MANIFEST.json files differ from the generated set")
        if want["generator"] != have.get("generator"):
            problems.append("MANIFEST.json names another generator")
    problems += [f"extra {p.name}" for p in sorted(out.glob("*.ods")) if p.name not in files]
    return problems


def describe(ods: bytes) -> dict[str, Any]:
    """The defaults an ODS states: languages, fonts, size, page, sheets.  Raises on a file that is not an ODF package."""
    with zipfile.ZipFile(io.BytesIO(ods)) as zf:
        names = zf.namelist()
        mimetype = zf.read("mimetype").decode("ascii", "replace") if "mimetype" in names else None
        root = ET.fromstring(zf.read("styles.xml"))
        content = ET.fromstring(zf.read("content.xml"))
    default = root.find("office:styles/style:default-style[@style:family='table-cell']", NS)
    props = default.find("style:text-properties", NS) if default is not None else None
    get = (lambda a: props.get(a)) if props is not None else (lambda a: None)  # noqa: E731
    tag = lambda lang, country: None if lang is None else (lang if country in (None, "none") else f"{lang}-{country}")  # noqa: E731
    layouts = root.findall(".//style:page-layout", NS)
    masters = {m.get(_q("style", "name")): m.get(_q("style", "page-layout-name")) for m in root.findall(".//style:master-page", NS)}
    chosen = next((l for l in layouts if l.get(_q("style", "name")) == masters.get("Default")), layouts[0] if layouts else None)
    page = chosen.find("style:page-layout-properties", NS) if chosen is not None else None
    width = to_mm(page.get(_q("fo", "page-width"))) if page is not None else None
    height = to_mm(page.get(_q("fo", "page-height"))) if page is not None else None
    return {"mimetype": mimetype, "entries": names,
            "western": tag(get(_q("fo", "language")), get(_q("fo", "country"))),
            "asian": tag(get(_q("style", "language-asian")), get(_q("style", "country-asian"))),
            "complex": tag(get(_q("style", "language-complex")), get(_q("style", "country-complex"))),
            "fonts": {"western": get(_q("style", "font-name")), "asian": get(_q("style", "font-name-asian")), "complex": get(_q("style", "font-name-complex"))},
            "size": get(_q("fo", "font-size")),
            "pageMm": [None if width is None else round(width, 2), None if height is None else round(height, 2)], "paper": classify_paper(width, height),
            "sheets": [t.get("{%s}name" % TABLE) for t in content.iter("{%s}table" % TABLE)]}


def compare(record: dict[str, Any], described: dict[str, Any]) -> list[str]:
    """Where a described ODS departs from its record.  Empty = states its defaults."""
    bad = [f"{k}: {described.get(k)!r} != {record[k]!r}" for k in ("western", "asian", "complex", "paper") if described.get(k) != record[k]]
    bad += [f"font {k}: {(described.get('fonts') or {}).get(k)!r} != {v!r}" for k, v in record["fonts"].items() if (described.get("fonts") or {}).get(k) != v]
    return bad


def validate_set(out: Path) -> dict[str, Any]:
    results = [odt.validate(p) for p in sorted(out.glob("*.ods"))]
    on_disk = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    hashes = {n: sha256((out / n).read_bytes()) == r["sha256"] for n, r in on_disk["files"].items()}
    return {"validated": len(results), "passed": sum(1 for r in results if r["passed"]), "failed": [r for r in results if not r["passed"]],
            "hashesMatch": all(hashes.values()), "hashMismatches": sorted(n for n, ok in hashes.items() if not ok), "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path)
    group.add_argument("--check", type=Path)
    group.add_argument("--validate", type=Path)
    group.add_argument("--describe", type=Path)
    args = parser.parse_args()
    if args.out:
        print(json.dumps(write(args.out), indent=1))
        return 0
    if args.check:
        problems = check(args.check)
        print(json.dumps({"identical": not problems, "problems": problems}, indent=1))
        return 0 if not problems else 1
    if args.validate:
        result = validate_set(args.validate)
        print(json.dumps({k: v for k, v in result.items() if k != "results"}, indent=1, ensure_ascii=False))
        return 0 if result["passed"] == result["validated"] and result["hashesMatch"] else 1
    print(json.dumps(describe(args.describe.read_bytes()), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
