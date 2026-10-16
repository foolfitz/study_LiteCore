#!/usr/bin/env python3
"""S-7: the ODT container adapter.  An ODT's parts presented as ONE office:document root.

Arms: findings/evidence/link-batch-v21/shakedown/ARMS.md S-7; ARMS-item1.md §2.7 (D1's reader);
ARMS-item2.md I-7 (the item-2 comparator is built on top of this by Agent M).

  flat_document(raw)  -> bytes   one `office:document` (UTF-8 XML) for an .odt, a .fodt or a .fodt.gz:
                                 meta (meta.xml), settings (settings.xml), scripts and body (content.xml),
                                 font-face-decls (content's, plus styles' faces content does not name),
                                 styles (styles.xml), automatic-styles (content's and styles' children;
                                 the same family+name with different content refuses), master-styles
                                 (styles.xml).  A flat file is returned as it is (gunzipped).
  pictures(raw)       -> {path: bytes}  every `Pictures/*` member of an .odt ({} for a flat file)
  AdapterError                   raised with the parser's or the zip's own message as its payload: a
                                 missing content.xml or styles.xml, a part that does not parse, a member
                                 that is not a zip.  Never an empty document in place of an error.

Readers keep their own red cases: D1's are in `v21_item1_marker.py`; the comparator's are Agent M's.
"""
from __future__ import annotations

import gzip
import io
import zipfile
import xml.etree.ElementTree as ET

OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
STYLE = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
O = "{%s}" % OFFICE
S = "{%s}" % STYLE

PREFIXES = {
    "office": OFFICE, "style": STYLE,
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "dc": "http://purl.org/dc/elements/1.1/",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "number": "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "chart": "urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
    "dr3d": "urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",
    "form": "urn:oasis:names:tc:opendocument:xmlns:form:1.0",
    "script": "urn:oasis:names:tc:opendocument:xmlns:script:1.0",
    "loext": "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
}
for _prefix, _uri in PREFIXES.items():
    ET.register_namespace(_prefix, _uri)


class AdapterError(ValueError):
    pass


def is_zip(raw: bytes) -> bool:
    return raw[:4] == b"PK\x03\x04"


def _parse(name: str, data: bytes):
    try:
        return ET.fromstring(data)
    except ET.ParseError as error:
        raise AdapterError(f"{name} does not parse: {error}") from error


def _members(raw: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            return {info.filename: archive.read(info.filename) for info in archive.infolist()}
    except zipfile.BadZipFile as error:
        raise AdapterError(f"not a zip container: {error}") from error


def _style_key(element) -> tuple:
    return (element.tag, element.get(S + "family"), element.get(S + "name"))


def flat_document(raw: bytes) -> bytes:
    """One office:document root for any of .odt / .fodt / .fodt.gz (see the module docstring)."""
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    if not is_zip(raw):
        root = _parse("flat document", raw)
        if root.tag != O + "document":
            raise AdapterError(f"flat document root is {root.tag}, not office:document")
        return raw
    members = _members(raw)
    for required in ("content.xml", "styles.xml"):
        if required not in members:
            raise AdapterError(f"{required} missing from the container (members: {sorted(members)[:12]})")
    content = _parse("content.xml", members["content.xml"])
    styles = _parse("styles.xml", members["styles.xml"])
    meta = _parse("meta.xml", members["meta.xml"]) if "meta.xml" in members else None
    settings = _parse("settings.xml", members["settings.xml"]) if "settings.xml" in members else None
    if content.tag != O + "document-content" or styles.tag != O + "document-styles":
        raise AdapterError(f"unexpected part roots: {content.tag}, {styles.tag}")

    doc = ET.Element(O + "document")
    for key, value in content.attrib.items():
        doc.set(key, value)
    doc.set(O + "mimetype", members.get("mimetype", b"").decode("ascii", "replace"))

    def child(root, local):
        return root.find(O + local) if root is not None else None

    for part, local in ((meta, "meta"), (settings, "settings"), (content, "scripts")):
        node = child(part, local)
        if node is not None:
            doc.append(node)
    faces = ET.SubElement(doc, O + "font-face-decls")
    names = set()
    for source in (child(content, "font-face-decls"), child(styles, "font-face-decls")):
        for face in list(source) if source is not None else []:
            name = face.get(S + "name")
            if name in names:
                continue
            names.add(name)
            faces.append(face)
    node = child(styles, "styles")
    if node is not None:
        doc.append(node)
    automatic = ET.SubElement(doc, O + "automatic-styles")
    seen: dict[tuple, bytes] = {}
    for source in (child(content, "automatic-styles"), child(styles, "automatic-styles")):
        for element in list(source) if source is not None else []:
            key = _style_key(element)
            serial = ET.tostring(element)
            if key in seen:
                if seen[key] != serial and key[2] is not None:
                    raise AdapterError(f"automatic style {key[1]}/{key[2]} differs between content.xml and styles.xml")
                continue
            seen[key] = serial
            automatic.append(element)
    for local, root in (("master-styles", styles), ("body", content)):
        node = child(root, local)
        if node is not None:
            doc.append(node)
    if doc.find(O + "body") is None:
        raise AdapterError("content.xml has no office:body")
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(doc, encoding="utf-8").split(b"?>", 1)[-1].lstrip()


def pictures(raw: bytes) -> dict[str, bytes]:
    if raw[:2] == b"\x1f\x8b" or not is_zip(raw):
        return {}
    return {name: data for name, data in _members(raw).items() if name.startswith("Pictures/")}


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.stdout.buffer.write(flat_document(Path(sys.argv[1]).read_bytes()))
