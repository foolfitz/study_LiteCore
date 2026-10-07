#!/usr/bin/env python3
"""A CANDIDATE, not a product build: tier E as a five-family collection.

Written 2026-10-07 after findings/evidence/v15-shakedown/cjk-ab/: on v15 the
Asian font slot of every document that names no Asian font -- and of every
document naming Noto Sans CJK SC, JP or KR -- resolves to Liberation Sans,
because the shipped subset carries one family (TC) where the full TTC carried
five (JP KR SC TC HK).  CJK lines then get a Latin line height (16 px against
20 on v8 in the probe).

This builds the SAME tier-E font five times over, in the original TTC's face
order, with only the `name` table differing per face (family, full and
PostScript names; the face's own language records, as in the original TTC),
and saves them as one collection with shared tables -- so the glyphs, metrics
and layout tables exist once.  The TC face keeps the shipped subset's name
table unchanged.

It then packs the collection into dist/profiles/resources (content-addressed,
stem `cjk-sub-e-ttc5-ab`) and writes an r6-based source manifest naming it
into --manifest-out (outside the tree).  The profile itself is built by
tools/build_e2_editor_v4_profile.py with a diagnostic name.  Nothing here
touches sdk/, the shipped v15 profile or any committed file.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_r5_profiles import create_pack  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
SUBSET = HERE / "build/cjk-subset/NotoSansCJKtc-Regular-subset-E.otf"
SHIPPED_PACK_SHA256 = "2d8240354ce1cf78b9a15155030b7e1835b04aec0234aed6a3483c18584b8eb5"
SOURCE_MANIFEST = HERE / "sdk/r6-writer-review-manifest.json"
RESOURCES = HERE / "dist/profiles/resources"
STEM = "cjk-sub-e-ttc5-ab"
FONT_PATH = "/instdir/share/fonts/truetype/NotoSansCJK-Regular-subset-E.ttc"
# The original NotoSansCJK-Regular.ttc's first five faces, in its order, with
# the language ID its localized name records carry (read from that file).
FACES = [("JP", "jp", 0x411), ("KR", "kr", 0x412), ("SC", "sc", 0x804),
         ("TC", "tc", 0x404), ("HK", "hk", 0xC04)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out: Path) -> Path:
    faces = []
    for code, lower, lang in FACES:
        font = TTFont(SUBSET, recalcTimestamp=False, recalcBBoxes=False)
        if code != "TC":
            for record in font["name"].names:
                text = record.toUnicode()
                renamed = (text.replace("Noto Sans CJK TC", f"Noto Sans CJK {code}")
                               .replace("NotoSansCJKtc", f"NotoSansCJK{lower}"))
                if record.langID == 0x404:
                    record.langID = lang
                record.string = renamed
        faces.append(font)
    collection = TTCollection()
    collection.fonts = faces
    target = out / "NotoSansCJK-Regular-subset-E.ttc"
    collection.save(str(target), shareTables=True)
    return target


def verify(ttc: Path) -> list[str]:
    problems = []
    original = TTFont(SUBSET)
    collection = TTCollection(str(ttc))
    if len(collection.fonts) != len(FACES):
        return [f"{len(collection.fonts)} faces, expected {len(FACES)}"]
    for (code, _, lang), face in zip(FACES, collection.fonts):
        family = face["name"].getDebugName(1)
        if family != f"Noto Sans CJK {code}":
            problems.append(f"face {code}: family {family!r}")
        local = {r.langID for r in face["name"].names if r.langID != 0x409}
        if local != {lang}:
            problems.append(f"face {code}: localized records {sorted(map(hex, local))}")
        for table in ("cmap", "hmtx", "vmtx", "hhea", "OS/2", "CFF ", "GSUB", "GPOS"):
            if face.getTableData(table) != original.getTableData(table):
                problems.append(f"face {code}: table {table} differs from the shipped subset")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest-out", type=Path, required=True,
                    help="where the r6-based source manifest is written (outside the tree)")
    a = ap.parse_args()
    if sha256(SUBSET) != SHIPPED_PACK_SHA256:
        raise SystemExit(f"{SUBSET} is not the font the v15 pack carries")
    with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
        first, second = build(Path(one)), build(Path(two))
        if sha256(first) != sha256(second):
            raise SystemExit("two builds differ: the collection is not deterministic")
        problems = verify(first)
        if problems:
            raise SystemExit("candidate failed verification:\n  " + "\n  ".join(problems))
        size = first.stat().st_size
        pack = create_pack(first, [{"filename": FONT_PATH, "start": 0, "end": size}],
                           RESOURCES, STEM)
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    out = copy.deepcopy(manifest)
    hits = [i for i, e in enumerate(out["resourcePacks"]) if e["id"] == "cjk-r5"]
    if len(hits) != 1:
        raise SystemExit("expected exactly one cjk-r5 pack in the r6 manifest")
    out["resourcePacks"][hits[0]] = {
        "bytes": pack["bytes"], "data": f"../resources/{pack['data']}", "id": STEM,
        "loadAtStartup": True, "metadata": f"../resources/{pack['metadata']}",
        "purpose": "CANDIDATE (unshipped): tier E as a five-family collection",
        "sha256": pack["sha256"]}
    a.manifest_out.write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(json.dumps({"ttcBytes": size, "subsetBytes": SUBSET.stat().st_size,
                      "pack": pack["data"], "metadata": pack["metadata"],
                      "sha256": pack["sha256"], "manifest": str(a.manifest_out)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
