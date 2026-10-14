#!/usr/bin/env python3
"""The blank documents the Nextcloud host writes for "+ New -> New document"
(study_LiteCore specs/SPEC-M3-new-document.md, sections 3.2 and 3.3).

A style-less ODT is not neutral in the shipped engine: it comes out Letter,
with a browser-dependent Asian language and `Noto Sans CJK KR` as the Asian font
(findings/evidence/new-document/analysis-1.md).  So every blank document the
host ships STATES its defaults: the three languages, the three fonts and the
page size, one file per (western, asian, paper) triple.  The host's
`lib/Template/BlankDocument.php` picks the triple for a user; this script makes
the bytes it picks from, deterministically:

  * every zip entry STORED (no zlib in the bytes), timestamp 1980-01-01 00:00,
    fixed order, `mimetype` first and without an extra field (the ODF package
    rule richdocuments' template.odt breaks);
  * the same source gives the same bytes on any machine, so a sha256 can be
    recorded and checked at write time.

  make_new_document_templates.py --out DIR          write the set and MANIFEST.json
  make_new_document_templates.py --check DIR        regenerate in memory, compare byte for byte
  make_new_document_templates.py --validate DIR     odfvalidator on every .odt (SPEC N10)
  make_new_document_templates.py --validate-one F   one file, prints the parsed verdict
  make_new_document_templates.py --describe F.odt   the defaults a saved or template ODT states
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ODT = "application/vnd.oasis.opendocument.text"
# The western tags the host's table can ask for (BlankDocument::WESTERN values
# plus its default), each paired with Asian zh-TW.
WESTERN = ["en-US", "en-GB", "de-DE", "fr-FR", "es-ES", "es-MX", "es-EC", "it-IT", "nl-NL", "pt-BR", "pt-PT"]
# The Asian tags (BlankDocument::ASIAN values); every one but zh-TW is paired
# with western en-US only, which is what a zh_HK / zh_CN / ja / ko user gets.
ASIAN_FONT = {"zh-TW": "Noto Sans CJK TC", "zh-HK": "Noto Sans CJK HK", "zh-CN": "Noto Sans CJK SC",
              "ja-JP": "Noto Sans CJK JP", "ko-KR": "Noto Sans CJK KR"}
DEFAULT_ASIAN = "zh-TW"
COMPLEX = "hi-IN"
WESTERN_FONT = "Liberation Serif"
COMPLEX_FONT = "Liberation Sans"
FONT_SIZE = "12pt"
PAPERS = {"A4": ("21cm", "29.7cm"), "Letter": ("8.5in", "11in")}
PAPER_MM = {"A4": (210.0, 297.0), "Letter": (215.9, 279.4)}
MARGIN = "2cm"
GENERATOR = "study_LiteCore new-document template generator"
EPOCH = (1980, 1, 1, 0, 0, 0)

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}


def triples() -> list[tuple[str, str, str]]:
    out = [(w, DEFAULT_ASIAN, p) for w in WESTERN for p in PAPERS]
    out += [("en-US", a, p) for a in ASIAN_FONT if a != DEFAULT_ASIAN for p in PAPERS]
    return out


def file_name(western: str, asian: str, paper: str) -> str:
    return f"{western}_{asian}_{paper}.odt"


def split_tag(tag: str) -> tuple[str, str]:
    language, country = tag.split("-", 1)
    return language, country


def _xml(text: str) -> bytes:
    """One line per element, no indentation games: the bytes are the spec."""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n' + text.strip() + "\n").encode("utf-8")


def manifest_xml() -> bytes:
    return _xml(f"""
<manifest:manifest xmlns:manifest="{NS['manifest']}" manifest:version="1.3">
 <manifest:file-entry manifest:full-path="/" manifest:version="1.3" manifest:media-type="{ODT}"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
</manifest:manifest>""")


def meta_xml() -> bytes:
    return _xml(f"""
<office:document-meta xmlns:office="{NS['office']}" xmlns:meta="{NS['meta']}" office:version="1.3">
 <office:meta>
  <meta:generator>{GENERATOR}</meta:generator>
 </office:meta>
</office:document-meta>""")


def content_xml() -> bytes:
    return _xml(f"""
<office:document-content xmlns:office="{NS['office']}" xmlns:text="{NS['text']}" office:version="1.3">
 <office:body>
  <office:text>
   <text:p text:style-name="Standard"/>
  </office:text>
 </office:body>
</office:document-content>""")


def styles_xml(western: str, asian: str, paper: str) -> bytes:
    w_lang, w_country = split_tag(western)
    a_lang, a_country = split_tag(asian)
    c_lang, c_country = split_tag(COMPLEX)
    asian_font = ASIAN_FONT[asian]
    width, height = PAPERS[paper]
    return _xml(f"""
<office:document-styles xmlns:office="{NS['office']}" xmlns:style="{NS['style']}" xmlns:text="{NS['text']}" xmlns:fo="{NS['fo']}" xmlns:svg="{NS['svg']}" office:version="1.3">
 <office:font-face-decls>
  <style:font-face style:name="{WESTERN_FONT}" svg:font-family="&apos;{WESTERN_FONT}&apos;" style:font-family-generic="roman" style:font-pitch="variable"/>
  <style:font-face style:name="{asian_font}" svg:font-family="&apos;{asian_font}&apos;" style:font-family-generic="system" style:font-pitch="variable"/>
  <style:font-face style:name="{COMPLEX_FONT}" svg:font-family="&apos;{COMPLEX_FONT}&apos;" style:font-family-generic="swiss" style:font-pitch="variable"/>
 </office:font-face-decls>
 <office:styles>
  <style:default-style style:family="paragraph">
   <style:paragraph-properties style:text-autospace="ideograph-alpha" style:punctuation-wrap="hanging" style:line-break="strict"/>
   <style:text-properties style:use-window-font-color="true" style:font-name="{WESTERN_FONT}" fo:font-size="{FONT_SIZE}" fo:language="{w_lang}" fo:country="{w_country}" style:font-name-asian="{asian_font}" style:font-size-asian="{FONT_SIZE}" style:language-asian="{a_lang}" style:country-asian="{a_country}" style:font-name-complex="{COMPLEX_FONT}" style:font-size-complex="{FONT_SIZE}" style:language-complex="{c_lang}" style:country-complex="{c_country}"/>
  </style:default-style>
  <style:style style:name="Standard" style:family="paragraph" style:class="text"/>
 </office:styles>
 <office:automatic-styles>
  <style:page-layout style:name="Mpm1">
   <style:page-layout-properties fo:page-width="{width}" fo:page-height="{height}" style:print-orientation="portrait" fo:margin-top="{MARGIN}" fo:margin-bottom="{MARGIN}" fo:margin-left="{MARGIN}" fo:margin-right="{MARGIN}"/>
  </style:page-layout>
 </office:automatic-styles>
 <office:master-styles>
  <style:master-page style:name="Standard" style:page-layout-name="Mpm1"/>
 </office:master-styles>
</office:document-styles>""")


def build(western: str, asian: str, paper: str) -> bytes:
    """The ODT package for one triple.  Byte-deterministic: STORED entries,
    fixed timestamps and order, no extra fields, 0644 as the external attr."""
    entries = [
        ("mimetype", ODT.encode("ascii")),
        ("META-INF/manifest.xml", manifest_xml()),
        ("meta.xml", meta_xml()),
        ("styles.xml", styles_xml(western, asian, paper)),
        ("content.xml", content_xml()),
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=EPOCH)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    return buffer.getvalue()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate() -> dict[str, dict[str, Any]]:
    """Every file of the set: name -> {bytes, record}."""
    out: dict[str, dict[str, Any]] = {}
    for western, asian, paper in triples():
        data = build(western, asian, paper)
        out[file_name(western, asian, paper)] = {
            "bytes": data,
            "record": {"sha256": sha256(data), "bytes": len(data), "western": western, "asian": asian,
                       "complex": COMPLEX, "paper": paper,
                       "fonts": {"western": WESTERN_FONT, "asian": ASIAN_FONT[asian], "complex": COMPLEX_FONT}},
        }
    return out


def manifest(files: dict[str, dict[str, Any]]) -> dict[str, Any]:
    me = Path(__file__).resolve()
    return {
        "spec": "specs/SPEC-M3-new-document.md",
        "generator": {"path": "wasm_sdk_probe/tools/" + me.name, "sha256": sha256(me.read_bytes())},
        "odfVersion": "1.3",
        "files": {name: entry["record"] for name, entry in sorted(files.items())},
    }


def manifest_bytes(files: dict[str, dict[str, Any]]) -> bytes:
    return (json.dumps(manifest(files), indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    files = generate()
    stale = [p.name for p in out.glob("*.odt") if p.name not in files]
    for name, entry in files.items():
        (out / name).write_bytes(entry["bytes"])
    (out / "MANIFEST.json").write_bytes(manifest_bytes(files))
    return {"written": len(files), "manifest": str(out / "MANIFEST.json"), "staleNotRemoved": stale}


def check(out: Path) -> list[str]:
    """Regenerate in memory and compare with what is on disk.  Empty = identical."""
    files = generate()
    problems = []
    for name, entry in files.items():
        path = out / name
        if not path.is_file():
            problems.append(f"missing {name}")
        elif path.read_bytes() != entry["bytes"]:
            problems.append(f"differs {name}")
    on_disk = out / "MANIFEST.json"
    if not on_disk.is_file():
        problems.append("missing MANIFEST.json")
    else:
        want = json.loads(manifest_bytes(files))
        have = json.loads(on_disk.read_text(encoding="utf-8"))
        if want["files"] != have.get("files"):
            problems.append("MANIFEST.json files differ from the generated set")
        if want["generator"] != have.get("generator"):
            problems.append("MANIFEST.json names another generator")
    extra = sorted(p.name for p in out.glob("*.odt") if p.name not in files)
    problems += [f"extra {name}" for name in extra]
    return problems


# --------------------------------------------------------------------------
# Reading back: what an ODT states, template or saved (the runner and the
# native check both use this; SPEC N6 and N11 compare its fields).


def _q(ns: str, attr: str) -> str:
    return "{%s}%s" % (NS[ns], attr)


def to_mm(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.fullmatch(r"\s*([0-9.]+)\s*(cm|mm|in|pt|inch)\s*", value)
    if not match:
        return None
    number, unit = float(match.group(1)), match.group(2)
    return {"cm": number * 10, "mm": number, "in": number * 25.4, "inch": number * 25.4, "pt": number * 25.4 / 72}[unit]


def classify_paper(width_mm: float | None, height_mm: float | None, tolerance: float = 1.0) -> str | None:
    if width_mm is None or height_mm is None:
        return None
    for name, (w, h) in PAPER_MM.items():
        if abs(width_mm - w) <= tolerance and abs(height_mm - h) <= tolerance:
            return name
    return "other"


def describe(odt: bytes) -> dict[str, Any]:
    """The defaults an ODT states: languages, fonts, page.  Raises on a file
    that is not an ODF package (a 0-byte or corrupt result must not describe)."""
    with zipfile.ZipFile(io.BytesIO(odt)) as zf:
        names = zf.namelist()
        mimetype = zf.read("mimetype").decode("ascii", "replace") if "mimetype" in names else None
        root = ET.fromstring(zf.read("styles.xml"))
    default = root.find("office:styles/style:default-style[@style:family='paragraph']", NS)
    props = default.find("style:text-properties", NS) if default is not None else None
    get = (lambda a: props.get(a)) if props is not None else (lambda a: None)  # noqa: E731
    tag = lambda lang, country: None if lang is None else (lang if country in (None, "none") else f"{lang}-{country}")  # noqa: E731
    layout = root.find("office:automatic-styles/style:page-layout/style:page-layout-properties", NS)
    width = to_mm(layout.get(_q("fo", "page-width"))) if layout is not None else None
    height = to_mm(layout.get(_q("fo", "page-height"))) if layout is not None else None
    return {
        "mimetype": mimetype,
        "entries": names,
        "western": tag(get(_q("fo", "language")), get(_q("fo", "country"))),
        "asian": tag(get(_q("style", "language-asian")), get(_q("style", "country-asian"))),
        "complex": tag(get(_q("style", "language-complex")), get(_q("style", "country-complex"))),
        "fonts": {"western": get(_q("style", "font-name")), "asian": get(_q("style", "font-name-asian")),
                  "complex": get(_q("style", "font-name-complex"))},
        "pageMm": [None if width is None else round(width, 2), None if height is None else round(height, 2)],
        "paper": classify_paper(width, height),
        "standardStyle": root.find("office:styles/style:style[@style:name='Standard']", NS) is not None,
        "fontFaceDecls": [f.get(_q("style", "name")) for f in root.findall("office:font-face-decls/style:font-face", NS)],
    }


def expected(record: dict[str, Any]) -> dict[str, Any]:
    """The describe() fields a MANIFEST record predicts for a saved file."""
    return {"western": record["western"], "asian": record["asian"], "complex": record["complex"],
            "fonts": dict(record["fonts"]), "paper": record["paper"]}


def compare(record: dict[str, Any], described: dict[str, Any]) -> list[str]:
    """Where a described ODT departs from what its record states.  Empty = states its defaults."""
    want = expected(record)
    bad = [f"{k}: {described.get(k)!r} != {v!r}" for k, v in want.items() if k != "fonts" and described.get(k) != v]
    bad += [f"font {k}: {(described.get('fonts') or {}).get(k)!r} != {v!r}"
            for k, v in want["fonts"].items() if (described.get("fonts") or {}).get(k) != v]
    return bad


# --------------------------------------------------------------------------
# odfvalidator (SPEC N10).  It exits 0 even with errors, so the verdict is read
# from the output: `Validation: Yes` and no `Error:` line.


def validate(path: Path, binary: str = "odfvalidator") -> dict[str, Any]:
    done = subprocess.run([binary, "-e", str(path)], capture_output=True, text=True, timeout=300)
    text = done.stdout + done.stderr
    errors = [line.strip() for line in text.splitlines() if "Error:" in line]
    validation = re.search(r"^Validation:\s*(\S+)", text, re.M)
    return {"file": path.name, "exit": done.returncode, "validation": validation.group(1) if validation else None,
            "errors": errors, "passed": bool(validation and validation.group(1) == "Yes" and not errors),
            "output": text.strip()}


def validate_set(out: Path) -> dict[str, Any]:
    results = [validate(p) for p in sorted(out.glob("*.odt"))]
    manifest_on_disk = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    hashes = {name: sha256((out / name).read_bytes()) == rec["sha256"] for name, rec in manifest_on_disk["files"].items()}
    return {"validated": len(results), "passed": sum(1 for r in results if r["passed"]),
            "failed": [r for r in results if not r["passed"]], "hashesMatch": all(hashes.values()),
            "hashMismatches": sorted(n for n, ok in hashes.items() if not ok), "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", type=Path)
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--validate-one", type=Path)
    parser.add_argument("--describe", type=Path)
    args = parser.parse_args()
    if args.out:
        print(json.dumps(write(args.out), ensure_ascii=False))
        return 0
    if args.check:
        problems = check(args.check)
        print(json.dumps({"identical": not problems, "problems": problems}, ensure_ascii=False))
        return 0 if not problems else 1
    if args.validate:
        result = validate_set(args.validate)
        print(json.dumps({k: v for k, v in result.items() if k != "results"}, ensure_ascii=False, indent=1))
        return 0 if result["passed"] == result["validated"] and result["hashesMatch"] else 1
    if args.validate_one:
        result = validate(args.validate_one)
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0 if result["passed"] else 1
    if args.describe:
        print(json.dumps(describe(args.describe.read_bytes()), ensure_ascii=False, indent=1))
        return 0
    parser.error("one of --out, --check, --validate, --validate-one, --describe")
    return 2


if __name__ == "__main__":
    sys.exit(main())
