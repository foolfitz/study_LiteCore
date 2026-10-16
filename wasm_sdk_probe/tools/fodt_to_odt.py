#!/usr/bin/env python3
"""S-6: flat ODT (.fodt) -> ODT (.odt), deterministic, byte-verbatim slices.

Arms: findings/evidence/link-batch-v21/shakedown/ARMS.md S-6; ARMS-item1.md §2.5 and §8 D-4 (ruling B
with the addition: place EVERY top-level child of office:document and refuse one without a rule);
ARMS-item2.md I-11.

Placement (a top-level child with no rule here makes the conversion fail, loudly):

  office:meta              -> meta.xml      (office:document-meta)
  office:settings          -> settings.xml  (office:document-settings)
  office:scripts           -> content.xml
  office:font-face-decls   -> content.xml and styles.xml
  office:styles            -> styles.xml
  office:automatic-styles  -> per child: style:page-layout -> styles.xml only; every other child -> both
  office:master-styles     -> styles.xml
  office:body              -> content.xml

Every element is copied as the exact byte slice it occupies in the source.  The new roots carry the
source root's namespace declarations and office:version verbatim (office:mimetype goes to the
`mimetype` member).  The zip: `mimetype` first and stored, the other members deflated in a fixed order,
every timestamp 1980-01-01 00:00:00, so the same source always gives the same bytes.

  fodt_to_odt.py SRC.fodt DST.odt          convert one file (refuses to overwrite)
  fodt_to_odt.py --batch SRC_DIR DST_DIR   every *.fodt; writes SHA256SUMS of the outputs
  fodt_to_odt.py --verify SRC.fodt DST.odt proof (ii): every slice is in its part, verbatim

Proof (i) (paragraphs through the S-7 adapter equal the flat file's) is in the test file and in the
batch run's output; proof (iii) is per run, in the runners.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import re
import sys
import xml.parsers.expat
import zipfile
from pathlib import Path

OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
STYLE = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
MIMETYPE_DEFAULT = "application/vnd.oasis.opendocument.text"
DATE = (1980, 1, 1, 0, 0, 0)
XML_HEAD = b'<?xml version="1.0" encoding="UTF-8"?>\n'

# Where each top-level child goes.  "split" = office:automatic-styles, decided per child.
PLACEMENT = {
    "meta": ("meta",),
    "settings": ("settings",),
    "scripts": ("content",),
    "font-face-decls": ("content", "styles"),
    "styles": ("styles",),
    "automatic-styles": "split",
    "master-styles": ("styles",),
    "body": ("content",),
}
# Schema order of the children inside each new root.
PART_ORDER = {
    "content": ["scripts", "font-face-decls", "automatic-styles", "body"],
    "styles": ["font-face-decls", "styles", "automatic-styles", "master-styles"],
    "meta": ["meta"],
    "settings": ["settings"],
}
PART_ROOT = {"content": "document-content", "styles": "document-styles",
             "meta": "document-meta", "settings": "document-settings"}
PART_FILE = {"content": "content.xml", "styles": "styles.xml", "meta": "meta.xml", "settings": "settings.xml"}


class ConversionError(ValueError):
    pass


def read_flat(path: Path) -> bytes:
    raw = Path(path).read_bytes()
    return gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw


def _end_of(raw: bytes, start: int, end_event: int) -> int:
    """The byte just after an element whose start tag begins at `start`; `end_event` is where expat
    reported its end (the start of `</...>`, or the start tag itself for an empty element)."""
    if raw[end_event:end_event + 2] == b"</":
        return raw.index(b">", end_event) + 1
    close = raw.index(b"/>", start)
    return close + 2


def slices(raw: bytes) -> dict:
    """Parse once with expat and return the byte slices the conversion places.

    {"root": {"name", "start_tag", "attrs"}, "children": [(local, bytes)], "auto": [(qname_local, ns, bytes)]}
    Refuses a document whose root is not office:document, and any top-level child without a rule.
    """
    parser = xml.parsers.expat.ParserCreate(namespace_separator=" ")
    stack: list[tuple[str, str, int]] = []
    out = {"root": None, "children": [], "auto": []}

    def start(name, attrs):
        ns, _, local = name.rpartition(" ")
        pos = parser.CurrentByteIndex
        if not stack:
            if (ns, local) != (OFFICE, "document"):
                raise ConversionError(f"root is {{{ns}}}{local}, not office:document")
            tag_end = raw.index(b">", pos) + 1
            out["root"] = {"start": pos, "start_tag": raw[pos:tag_end], "attrs": dict(attrs)}
        stack.append((ns, local, pos))

    def end(name):
        ns, local, pos = stack.pop()
        depth = len(stack)
        if depth == 1:
            if ns != OFFICE or local not in PLACEMENT:
                raise ConversionError(f"top-level child {{{ns}}}{local} has no placement rule")
            out["children"].append((local, raw[pos:_end_of(raw, pos, parser.CurrentByteIndex)]))
        elif depth == 2 and stack[1][:2] == (OFFICE, "automatic-styles"):
            out["auto"].append((local, ns, raw[pos:_end_of(raw, pos, parser.CurrentByteIndex)]))

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.Parse(raw, True)
    if out["root"] is None:
        raise ConversionError("no root element")
    seen = [name for name, _ in out["children"]]
    duplicated = sorted({name for name in seen if seen.count(name) > 1})
    if duplicated:
        raise ConversionError(f"top-level children appear more than once: {duplicated}")
    return out


def _root_tag(start_tag: bytes, new_local: bytes) -> tuple[bytes, bytes]:
    """The new root's start and end tags: the source root's namespace declarations and office:version
    verbatim, office:mimetype dropped (it belongs to the `mimetype` member)."""
    m = re.match(rb"<([A-Za-z_][\w.-]*):document(\s[^>]*)?>", start_tag)
    if not m:
        raise ConversionError(f"cannot read the root start tag: {start_tag[:80]!r}")
    prefix, attrs = m.group(1), m.group(2) or b""
    attrs = re.sub(rb"\s+" + re.escape(prefix) + rb':mimetype="[^"]*"', b"", attrs)
    return (b"<" + prefix + b":" + new_local + attrs + b">", b"</" + prefix + b":" + new_local + b">")


def plan(raw: bytes) -> dict:
    """part -> ordered list of (label, bytes); plus the mimetype.  Every slice goes somewhere."""
    s = slices(raw)
    children = dict(s["children"])
    placed: dict[str, list[tuple[str, bytes]]] = {part: [] for part in PART_ORDER}
    for part, order in PART_ORDER.items():
        for local in order:
            if local not in children:
                continue
            if local == "automatic-styles":
                rule = "split"
            else:
                rule = PLACEMENT[local]
                if part not in rule:
                    continue
            if rule == "split":
                kept = [(f"automatic-styles/{name}", body) for name, ns, body in s["auto"]
                        if part == "content" and not (ns == STYLE and name == "page-layout")
                        or part == "styles"]
                placed[part].append(("automatic-styles", kept))
            else:
                placed[part].append((local, children[local]))
    mimetype = s["root"]["attrs"].get(f"{OFFICE} mimetype", MIMETYPE_DEFAULT)
    return {"root": s["root"], "placed": placed, "children": s["children"], "auto": s["auto"],
            "mimetype": mimetype}


def _part_bytes(start_tag: bytes, part: str, entries) -> bytes:
    open_tag, close_tag = _root_tag(start_tag, PART_ROOT[part].encode())
    prefix = open_tag[1:open_tag.index(b":")]
    body = []
    for label, value in entries:
        if label == "automatic-styles":
            body.append(b"<" + prefix + b":automatic-styles>" + b"".join(v for _, v in value)
                        + b"</" + prefix + b":automatic-styles>")
        else:
            body.append(value)
    return XML_HEAD + open_tag + b"".join(body) + close_tag


def convert(raw: bytes) -> bytes:
    p = plan(raw)
    members: list[tuple[str, bytes]] = []
    for part in ("content", "styles", "meta", "settings"):
        entries = p["placed"][part]
        if part in ("meta", "settings") and not entries:
            continue
        members.append((PART_FILE[part], _part_bytes(p["root"]["start_tag"], part, entries)))
    version = p["root"]["attrs"].get(f"{OFFICE} version", "1.3")
    manifest = ['<?xml version="1.0" encoding="UTF-8"?>\n<manifest:manifest xmlns:manifest='
                '"urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="%s">' % version,
                ' <manifest:file-entry manifest:full-path="/" manifest:version="%s" manifest:media-type="%s"/>'
                % (version, p["mimetype"])]
    for name, _ in members:
        manifest.append(' <manifest:file-entry manifest:full-path="%s" manifest:media-type="text/xml"/>' % name)
    manifest.append("</manifest:manifest>\n")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        def put(name: str, data: bytes, method: int) -> None:
            info = zipfile.ZipInfo(name, date_time=DATE)
            info.compress_type = method
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
        put("mimetype", p["mimetype"].encode("ascii"), zipfile.ZIP_STORED)
        for name, data in members:
            put(name, data, zipfile.ZIP_DEFLATED)
        put("META-INF/manifest.xml", "\n".join(manifest).encode("utf-8"), zipfile.ZIP_DEFLATED)
    return buffer.getvalue()


def verify(raw: bytes, odt: bytes) -> list[str]:
    """Proof (ii): every top-level slice and every automatic-style slice is present, verbatim, in each
    part its rule names; every top-level child was placed; mimetype first and stored.  [] = proven."""
    problems = []
    p = plan(raw)
    with zipfile.ZipFile(io.BytesIO(odt)) as archive:
        names = archive.namelist()
        if not names or names[0] != "mimetype" or archive.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            problems.append("mimetype is not the first, stored member")
        parts = {part: archive.read(PART_FILE[part]) for part in PART_FILE if PART_FILE[part] in names}
    for local, body in p["children"]:
        if local == "automatic-styles":
            continue
        for part in PLACEMENT[local]:
            if body not in parts.get(part, b""):
                problems.append(f"{local} slice ({len(body)} bytes) missing from {PART_FILE[part]}")
    for name, ns, body in p["auto"]:
        targets = ["styles"] if (ns == STYLE and name == "page-layout") else ["content", "styles"]
        for part in targets:
            if body not in parts.get(part, b""):
                problems.append(f"automatic-styles/{name} slice missing from {PART_FILE[part]}")
    if p["root"]["attrs"].get(f"{OFFICE} mimetype", MIMETYPE_DEFAULT) != p["mimetype"]:
        problems.append("mimetype differs")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--batch", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    if args.verify:
        problems = verify(read_flat(Path(args.src)), Path(args.dst).read_bytes())
        print("\n".join(problems) if problems else "verified: every slice placed, verbatim")
        return 1 if problems else 0
    if args.batch:
        src, dst = Path(args.src), Path(args.dst)
        dst.mkdir(parents=True, exist_ok=True)
        sums = []
        for fodt in sorted(src.glob("*.fodt")):
            target = dst / (fodt.stem + ".odt")
            if target.exists():
                raise SystemExit(f"refusing to overwrite {target}")
            out = convert(read_flat(fodt))
            problems = verify(read_flat(fodt), out)
            if problems:
                raise SystemExit(f"{fodt.name}: proof (ii) failed: {problems}")
            target.write_bytes(out)
            sums.append(f"{hashlib.sha256(out).hexdigest()}  {target.name}")
            print(f"{fodt.name} -> {target.name} {hashlib.sha256(out).hexdigest()}")
        (dst / "SHA256SUMS").write_text("\n".join(sums) + "\n")
        return 0
    target = Path(args.dst)
    if target.exists():
        raise SystemExit(f"refusing to overwrite {target}")
    raw = read_flat(Path(args.src))
    out = convert(raw)
    problems = verify(raw, out)
    if problems:
        raise SystemExit(f"proof (ii) failed: {problems}")
    target.write_bytes(out)
    print(hashlib.sha256(out).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
