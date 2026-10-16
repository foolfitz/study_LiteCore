#!/usr/bin/env python3
"""The item-2 comparator ("normalised structure", ARMS-item2.md I-7; ARMS.md S-7), on top of Agent D's
container adapter (tools/v21_odt_adapter.py).

  The reader is the one committed with the native round:
  findings/evidence/link-batch-v21/native/markdown-paste/round-2/tool/md_structure.py (round 1's reader
  plus header/footer, nested tables and text frames when present; it reproduces every round-1 signature,
  round-2/out/reader-compat.txt).  It is imported, not copied.

  What this adds (spec §9.12: ODT and FODT normalised alike, styles merged, images compared by their DATA):
    1. any container -> one office:document root (S-7 `flat_document`; a missing styles.xml or a part
       that does not parse is an error, never an empty document);
    2. every draw:image whose data is in the document -- `office:binary-data` (flat files) or a
       `Pictures/*` member (ODT) -- is rewritten as an embedded image whose binary-data text is
       "sha256:<hex of the decoded bytes>"; an href to a picture that is not in the container is an
       error; a linked image (http, file) keeps its href;
    3. signature(raw) = the reader's signature of that root, plus "imageData": per draw:frame in body
       order, the image's sha256 (or its link, or None for a frame without an image), so two documents
       whose images differ by one byte are DIFFERENT although the reader alone calls them equal;
    4. fingerprint(raw) = round 2's reader-free detector (round-2/tool/run_arms2.py:275-296: the text
       under office:body and office:master-styles, and the counts of 12 structural tags), on the same
       root, with ONE change: the text is taken per text:p / text:h (document order), not as one string
       over the whole region.  Round 2 compared flat files with flat files; between an ODT and a
       pretty-printed flat file the whitespace-only text nodes BETWEEN block elements differ (seen in this
       module's own cross-container test), and they carry no content.  Text inside a paragraph is kept
       exactly, whitespace included, except inside its drawing objects (draw:*), where a flat file is
       indented too; images are compared by imageData and counted by tag.

  signature(raw) / fingerprint(raw) / summary(raw) / paragraph_texts(raw)
  compare(a, b) -> {"same", "signatureSame", "fingerprintSame", "firstDifference"}
  ComparatorError, and the adapter's AdapterError, are raised -- never returned as a difference.

  v21_item2_compare.py A B      prints SAME or DIFFERENT (exit 0 / 1), or the error (exit 2)
Tests: tests/test_v21_item2_compare.py (cross-container equality, missing styles, a broken and a missing
picture, a changed paragraph).
"""
from __future__ import annotations

import base64
import binascii
import collections
import hashlib
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v21_odt_adapter as s7  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
READER_PATH = REPO / "findings/evidence/link-batch-v21/native/markdown-paste/round-2/tool/md_structure.py"
_spec = importlib.util.spec_from_file_location("v21_round2_md_structure", READER_PATH)
md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md)

NS = md.NS
DRAW_IMAGE = "{%s}image" % NS["draw"]
DRAW_FRAME = "{%s}frame" % NS["draw"]
BINARY = "{%s}binary-data" % NS["office"]
HREF = "{%s}href" % NS["xlink"]
BODY = "{%s}body" % NS["office"]
MASTER = "{%s}master-styles" % NS["office"]
STRUCT_TAGS = ("text:p", "text:h", "text:list-item", "table:table", "table:table-row", "table:table-cell",
               "draw:frame", "draw:image", "text:section", "text:a", "loext:content-control",
               "text:text-input")


class ComparatorError(ValueError):
    pass


def reader_sha256() -> str:
    return hashlib.sha256(READER_PATH.read_bytes()).hexdigest()


def self_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def normalized_root(raw: bytes) -> ET.Element:
    root = ET.fromstring(s7.flat_document(raw))
    pictures = s7.pictures(raw)
    for image in root.iter(DRAW_IMAGE):
        binary = image.find(BINARY)
        href = image.get(HREF)
        data = None
        if binary is not None:
            try:
                data = base64.b64decode("".join(binary.itertext()), validate=False)
            except (binascii.Error, ValueError) as error:
                raise ComparatorError(f"office:binary-data does not decode: {error}") from error
        elif href and not href.startswith(("http:", "https:", "file:", "data:")):
            key = href[2:] if href.startswith("./") else href
            if key not in pictures:
                raise ComparatorError(f"image {href!r} is not in the container (pictures: {sorted(pictures)[:8]})")
            data = pictures[key]
        if data is None:
            continue
        if href is not None:
            del image.attrib[HREF]
        if binary is None:
            binary = ET.SubElement(image, BINARY)
        for child in list(binary):
            binary.remove(child)
        binary.text = "sha256:" + hashlib.sha256(data).hexdigest()
    return root


def _summary_of(root: ET.Element) -> dict:
    reader = md.Reader(root)
    out = {"paragraphCount": len(reader.paragraphs), "paragraphs": reader.paragraphs, "tables": reader.tables,
           "links": reader.links, "images": reader.images}
    if reader.header_footer:
        out["headerFooter"] = reader.header_footer
    return out


def summary(raw: bytes) -> dict:
    return _summary_of(normalized_root(raw))


def _image_data(root: ET.Element, expected: int) -> list:
    body = root.find(BODY)
    data = []
    for frame in body.iter(DRAW_FRAME):
        image = frame.find(DRAW_IMAGE)
        if image is None:
            data.append(None)
            continue
        binary = image.find(BINARY)
        data.append(binary.text if binary is not None else image.get(HREF))
    if len(data) != expected:
        raise ComparatorError(f"{len(data)} draw:frame in the body, the reader recorded {expected} images")
    return data


def signature(raw: bytes) -> dict:
    root = normalized_root(raw)
    summary_ = _summary_of(root)
    sig = md.signature(summary_)
    sig["imageData"] = _image_data(root, len(summary_["images"]))
    return sig


DRAW_PREFIX = "{%s}" % NS["draw"]


def _own_text(element: ET.Element) -> str:
    """A paragraph's text without what is inside its drawing objects (a pretty-printed flat file indents
    inside draw:frame; images are compared by imageData and counted by tag instead)."""
    out = [element.text or ""]
    for child in element:
        if not child.tag.startswith(DRAW_PREFIX):
            out.append(_own_text(child))
        out.append(child.tail or "")
    return "".join(out)


def fingerprint(raw: bytes) -> tuple[str, dict]:
    root = normalized_root(raw)
    texts, counts = [], collections.Counter()
    para = ("{%s}p" % NS["text"], "{%s}h" % NS["text"])
    for local in (BODY, MASTER):
        for node in root.iter(local):
            texts.append([_own_text(p) for p in node.iter() if p.tag in para])
            for tag in STRUCT_TAGS:
                prefix, name = tag.split(":")
                counts[tag] += sum(1 for _ in node.iter("{%s}%s" % (NS[prefix], name)))
    blob = json.dumps({"text": texts, "counts": dict(sorted(counts.items()))}, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest(), dict(sorted(counts.items()))


def signature_sha256(raw: bytes) -> str:
    return hashlib.sha256(json.dumps(signature(raw), ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def paragraph_texts(raw: bytes) -> list[str]:
    return [p["text"] for p in summary(raw)["paragraphs"]]


def _first_difference(a, b, path="") -> str | None:
    if type(a) is not type(b):
        return f"{path or '/'}: {type(a).__name__} != {type(b).__name__}"
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                return f"{path}/{key}: present on one side only"
            found = _first_difference(a[key], b[key], f"{path}/{key}")
            if found:
                return found
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            found = _first_difference(x, y, f"{path}[{i}]")
            if found:
                return found
        return None
    return None if a == b else f"{path}: {str(a)[:120]!r} != {str(b)[:120]!r}"


def compare(a: bytes, b: bytes) -> dict:
    sa, sb = signature(a), signature(b)
    fa, fb = fingerprint(a)[0], fingerprint(b)[0]
    return {"same": sa == sb and fa == fb, "signatureSame": sa == sb, "fingerprintSame": fa == fb,
            "firstDifference": _first_difference(sa, sb)}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    try:
        result = compare(Path(argv[1]).read_bytes(), Path(argv[2]).read_bytes())
    except (ComparatorError, s7.AdapterError) as error:
        print(f"ERROR {type(error).__name__}: {error}")
        return 2
    print("SAME" if result["same"] else f"DIFFERENT {result['firstDifference']}")
    return 0 if result["same"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
