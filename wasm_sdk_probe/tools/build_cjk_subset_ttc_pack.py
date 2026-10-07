#!/usr/bin/env python3
"""The v16 profile's CJK pack: tier E as a five-family collection (finding 113;
owner's choice A, 2026-10-07).

v15 shipped tier E as one font whose only family is `Noto Sans CJK TC`.  The
full TTC it replaced carried five families (JP KR SC TC HK), and LibreOffice
resolves the default Asian font -- and any document naming SC, JP or KR -- to
one of those names; on v15 they fall to Liberation Sans and every CJK line gets
a Latin line height (findings/evidence/v15-shakedown/cjk-ab/).

This builds the SAME tier-E font (rebuilt by tools/build_cjk_subset.py,
verified, and required to be byte-identical to the font v15 shipped) five
times, in the original TTC's face order, with only the `name` table differing
per face, and saves them as one collection with shared tables.  It packs that
into dist/profiles/resources/cjk-sub-e5.<sha16>.{data,metadata} and writes
sdk/v16-writer-review-manifest.json: sdk/r6-writer-review-manifest.json with
the `cjk-r5` pack replaced by this one and nothing else changed.

  build_cjk_subset_ttc_pack.py          build the pack, write the v16 manifest
  build_cjk_subset_ttc_pack.py --check  rebuild in a scratch directory and fail
                                        unless the committed v16 manifest names
                                        exactly that pack and it is present
                                        (writes nothing in the tree)

tools/build_cjk_subset_pack.py (v15's) is left as it was: v15's profile rule
depends on it and runs its --check.
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
import build_cjk_subset as subset_tool  # noqa: E402
from build_r5_profiles import create_pack  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
TIER = "E"
STEM = "cjk-sub-e5"
FONT_PATH = "/instdir/share/fonts/truetype/NotoSansCJK-Regular-subset-E.ttc"
# The font v15 shipped (its pack's data is exactly this font's bytes).
SHIPPED_SUBSET_SHA256 = "2d8240354ce1cf78b9a15155030b7e1835b04aec0234aed6a3483c18584b8eb5"
SOURCE_MANIFEST = HERE / "sdk/r6-writer-review-manifest.json"
V16_MANIFEST = HERE / "sdk/v16-writer-review-manifest.json"
RESOURCES = HERE / "dist/profiles/resources"
PURPOSE = ("CJK corpus: Traditional Chinese subset of Noto Sans CJK, tier E "
           "(Big5, HKSCS, U+4E00-U+9FFF, kana), as five families (JP KR SC TC HK) "
           "sharing one glyph set")
# The original NotoSansCJK-Regular.ttc's first five faces, in its order, with
# the language ID its localized name records carry (read from that file).
FACES = [("JP", "jp", 0x411), ("KR", "kr", 0x412), ("SC", "sc", 0x804),
         ("TC", "tc", 0x404), ("HK", "hk", 0xC04)]
SHARED = ("cmap", "hmtx", "vmtx", "hhea", "vhea", "OS/2", "CFF ", "GSUB", "GPOS",
          "GDEF", "BASE", "VORG", "head", "maxp", "post")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def subset(workdir: Path) -> Path:
    font, wanted = subset_tool.build(TIER, workdir)
    problems: list[str] = []
    subset_tool.verify(font, wanted, subset_tool.load_face(), problems)
    if problems:
        raise SystemExit("subset failed verification:\n  " + "\n  ".join(problems))
    if sha256(font) != SHIPPED_SUBSET_SHA256:
        raise SystemExit(f"the rebuilt tier-E font is not the one v15 shipped ({sha256(font)[:16]})")
    return font


def collection(font: Path, out: Path) -> Path:
    faces = []
    for code, lower, lang in FACES:
        face = TTFont(font, recalcTimestamp=False, recalcBBoxes=False)
        if code != "TC":
            for record in face["name"].names:
                text = (record.toUnicode()
                        .replace("Noto Sans CJK TC", f"Noto Sans CJK {code}")
                        .replace("NotoSansCJKtc", f"NotoSansCJK{lower}"))
                if record.langID == 0x404:
                    record.langID = lang
                record.string = text
        faces.append(face)
    ttc = TTCollection()
    ttc.fonts = faces
    target = out / "NotoSansCJK-Regular-subset-E.ttc"
    ttc.save(str(target), shareTables=True)
    return target


def verify(ttc: Path, font: Path) -> list[str]:
    problems = []
    original = TTFont(font)
    built = TTCollection(str(ttc))
    if len(built.fonts) != len(FACES):
        return [f"{len(built.fonts)} faces, expected {len(FACES)}"]
    for (code, _, lang), face in zip(FACES, built.fonts):
        family = face["name"].getDebugName(1)
        if family != f"Noto Sans CJK {code}":
            problems.append(f"face {code}: family {family!r}")
        local = {r.langID for r in face["name"].names if r.langID != 0x409}
        if local != {lang}:
            problems.append(f"face {code}: localized records {sorted(map(hex, local))}")
        if code == "TC" and face["name"].compile(face) != original["name"].compile(original):
            problems.append("face TC: name table differs from the shipped font's")
        for table in SHARED:
            if table == "head":
                # checkSumAdjustment is the whole file's checksum, so it cannot
                # survive being put in a collection (measured: the only field
                # that differs, and the five faces share one `head`).  Every
                # other field must be the shipped font's.
                mine, theirs = dict(vars(face["head"])), dict(vars(original["head"]))
                for d in (mine, theirs):
                    d.pop("checkSumAdjustment", None)
                    d.pop("tableTag", None)
                if mine != theirs:
                    problems.append(f"face {code}: head differs beyond checkSumAdjustment")
            elif face.getTableData(table) != original.getTableData(table):
                problems.append(f"face {code}: table {table!r} differs from the shipped font")
    return problems


def build_pack(workdir: Path, output: Path) -> dict:
    font = subset(workdir)
    with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
        first, second = collection(font, Path(one)), collection(font, Path(two))
        if sha256(first) != sha256(second):
            raise SystemExit("two builds of the collection differ: not deterministic")
        problems = verify(first, font)
        if problems:
            raise SystemExit("collection failed verification:\n  " + "\n  ".join(problems))
        size = first.stat().st_size
        return create_pack(first, [{"filename": FONT_PATH, "start": 0, "end": size}], output, STEM)


def v16_manifest(pack: dict) -> dict:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    out = copy.deepcopy(manifest)
    hits = [i for i, e in enumerate(out["resourcePacks"]) if e["id"] == "cjk-r5"]
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one cjk-r5 pack in {SOURCE_MANIFEST.name}, found {len(hits)}")
    out["resourcePacks"][hits[0]] = {
        "bytes": pack["bytes"], "data": f"../resources/{pack['data']}", "id": STEM,
        "loadAtStartup": True, "metadata": f"../resources/{pack['metadata']}",
        "purpose": PURPOSE, "sha256": pack["sha256"]}
    return out


def dump(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        with tempfile.TemporaryDirectory() as tmp:
            pack = build_pack(Path(tmp), Path(tmp))
            expected = dump(v16_manifest(pack))
        committed = V16_MANIFEST.read_text(encoding="utf-8") if V16_MANIFEST.exists() else ""
        problems = []
        if committed != expected:
            problems.append(f"{V16_MANIFEST.name} is not what the tool generates from "
                            f"{SOURCE_MANIFEST.name} and today's collection (pack {pack['data']})")
        for name in (pack["data"], pack["metadata"]):
            if not (RESOURCES / name).exists():
                problems.append(f"{RESOURCES.relative_to(HERE)}/{name} is missing: run the tool without --check")
        for p in problems:
            print("FAIL " + p)
        if not problems:
            print(f"ok: {pack['data']} ({pack['bytes']} bytes) matches {V16_MANIFEST.name}")
        return 1 if problems else 0
    with tempfile.TemporaryDirectory() as tmp:
        RESOURCES.mkdir(parents=True, exist_ok=True)
        pack = build_pack(Path(tmp), RESOURCES)
    V16_MANIFEST.write_text(dump(v16_manifest(pack)), encoding="utf-8")
    print(f"wrote {RESOURCES.relative_to(HERE)}/{pack['data']}, {pack['metadata']} "
          f"({pack['bytes']} bytes, sha256 {pack['sha256'][:16]}) and {V16_MANIFEST.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
