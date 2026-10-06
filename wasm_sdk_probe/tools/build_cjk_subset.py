#!/usr/bin/env python3
"""CJK glyph subset for the product's font pack (owner's choice D, 2026-10-07;
research/RESEARCH-2026-10-06-wasm-size-status.md section 7).

Takes the Traditional Chinese face of the NotoSansCJK-Regular.ttc that the
shipped `cjk-r5` pack carries (face 3, "Noto Sans CJK TC"; all ten faces share
one CFF table, so face-splitting alone saves ~0.2 MB) and keeps only the glyphs
a tier of code points needs, then checks the result against the original face:

  coverage  every code point of the tier that the original face maps, the
            subset maps to the same glyph (by CID name);
  identity  every glyph the subset keeps has the original's outline (drawn
            through a decomposing recording pen) and advance/side bearing,
            horizontal and vertical;
  corpus    every code point used in the corpus documents that the original
            face can draw, the subset can draw (per document: which ones not).

`locl` is dropped: in the TC face the cmap already gives Traditional forms, and
`locl` only swaps in Japanese/Korean/Simplified forms for text tagged with
those languages -- which would pull their glyphs back in.  Such text renders
in Traditional forms.  Everything else in GSUB/GPOS (vertical forms included)
is kept.

Tiers (code points the TC face maps, intersected):
  C  Latin, punctuation, symbols, Bopomofo, fullwidth, CJK radicals and
     compatibility blocks + Big5 + HKSCS
  E  C + kana + every CJK Unified Ideograph U+4E00-U+9FFF
  F  E + GBK + Extension A + Hangul

Usage:
  build_cjk_subset.py --tier C|E|F|all --outdir DIR [--corpus PATH ...] [--json OUT]
  build_cjk_subset.py --self-test --outdir DIR      (red cases; needs a built tier)
Exit 1 on any failed check, or when the corpus held no document (non-vacuity).
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import zipfile
from pathlib import Path

import compression.zstd as zstd
from fontTools import subset
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent.parent
SOURCE = HERE / "dist/profiles/resources/cjk-r5.b76b0433203017ca.data"  # the TTC, whole
TC_FACE = 3

BASE_RANGES = [
    (0x0020, 0x007E), (0x00A0, 0x024F), (0x02B0, 0x02FF), (0x0370, 0x03FF), (0x0400, 0x04FF),
    (0x2000, 0x206F), (0x2070, 0x209F), (0x20A0, 0x20CF), (0x2100, 0x214F), (0x2150, 0x218F),
    (0x2190, 0x21FF), (0x2200, 0x22FF), (0x2300, 0x23FF), (0x2460, 0x24FF), (0x2500, 0x257F),
    (0x2580, 0x259F), (0x25A0, 0x25FF), (0x2600, 0x26FF), (0x2700, 0x27BF),
    (0x2E80, 0x2EFF), (0x2F00, 0x2FDF), (0x2FF0, 0x2FFF), (0x3000, 0x303F),
    (0x3100, 0x312F), (0x31A0, 0x31BF), (0x31C0, 0x31EF), (0x3200, 0x32FF), (0x3300, 0x33FF),
    (0xFE10, 0xFE1F), (0xFE30, 0xFE4F), (0xFE50, 0xFE6F), (0xFF00, 0xFFEF),
]


def codec_set(name: str) -> set[int]:
    out: set[int] = set()
    for lead in range(0x81, 0xFF):
        for trail in range(0x40, 0xFF):
            try:
                text = bytes((lead, trail)).decode(name)
            except UnicodeDecodeError:
                continue
            if len(text) == 1:
                out.add(ord(text))
    return out


def tier_points(tier: str) -> set[int]:
    points = {cp for lo, hi in BASE_RANGES for cp in range(lo, hi + 1)}
    points |= codec_set("big5") | codec_set("big5hkscs")
    if tier in ("E", "F"):
        points |= set(range(0x3040, 0x3100)) | set(range(0x4E00, 0xA000))
    if tier == "F":
        points |= codec_set("gbk") | set(range(0x3400, 0x4DC0))
        points |= set(range(0xAC00, 0xD7B0)) | set(range(0x1100, 0x1200)) | set(range(0x3130, 0x3190))
    return points


def load_face() -> TTFont:
    return TTFont(str(SOURCE), fontNumber=TC_FACE, lazy=False)


def build(tier: str, outdir: Path) -> tuple[Path, set[int]]:
    face = load_face()
    cmap = face.getBestCmap()
    wanted = tier_points(tier) & set(cmap)
    opts = subset.Options()
    opts.parse_opts(["--layout-features=*", "--layout-features-=locl", "--name-IDs=*",
                     "--name-languages=*", "--name-legacy", "--notdef-outline",
                     "--notdef-glyph", "--recalc-bounds", "--drop-tables-=DSIG"])
    subsetter = subset.Subsetter(options=opts)
    subsetter.populate(unicodes=sorted(wanted))
    subsetter.subset(face)
    out = outdir / f"NotoSansCJKtc-Regular-subset-{tier}.otf"
    face.save(str(out))
    return out, wanted


def outline(glyphset, name: str):
    pen = DecomposingRecordingPen(glyphset)
    glyphset[name].draw(pen)
    return pen.value


def verify(path: Path, wanted: set[int], original: TTFont, problems: list[str]) -> dict:
    sub = TTFont(str(path))
    ocmap, scmap = original.getBestCmap(), sub.getBestCmap()
    for cp in sorted(wanted):
        if scmap.get(cp) != ocmap[cp]:
            problems.append(f"{path.name}: U+{cp:04X} maps to {scmap.get(cp)} not {ocmap[cp]}")
    ogs, sgs = original.getGlyphSet(), sub.getGlyphSet()
    kept = [g for g in sub.getGlyphOrder() if g != ".notdef"]
    for table in ("hmtx", "vmtx"):
        if table in original and table in sub:
            for g in kept:
                if sub[table][g] != original[table][g]:
                    problems.append(f"{path.name}: {table} differs for {g}")
                    break
    differing = [g for g in kept if outline(sgs, g) != outline(ogs, g)]
    if differing:
        problems.append(f"{path.name}: {len(differing)} outlines differ, first {differing[:3]}")
    return {"glyphs": len(kept), "codePoints": len(wanted)}


TEXT_TAG = re.compile(rb"<[^>]+>")


def document_points(path: Path) -> set[int]:
    if path.suffix in (".odt", ".ods", ".odp"):
        with zipfile.ZipFile(path) as z:
            blobs = [z.read(n) for n in ("content.xml", "styles.xml") if n in z.namelist()]
    else:
        blobs = [path.read_bytes()]
    text = b" ".join(TEXT_TAG.sub(b" ", b) for b in blobs).decode("utf-8", "replace")
    return {ord(ch) for ch in text if ord(ch) >= 0x80}


def corpus_files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            out += sorted(q for q in p.rglob("*") if q.suffix in (".odt", ".fodt", ".ods", ".fods"))
        elif p.exists():
            out.append(p)
    return out


def sizes(path: Path) -> dict:
    data = path.read_bytes()
    return {"raw": len(data), "gzip9": len(gzip.compress(data, 9, mtime=0)),
            "zstd19": len(zstd.compress(data, level=19))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["C", "E", "F", "all"])
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--corpus", action="append", default=[])
    ap.add_argument("--json")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    original = load_face()
    ocmap = original.getBestCmap()
    if a.self_test:
        return self_test(outdir, original)
    problems: list[str] = []
    docs = corpus_files(a.corpus)
    if not docs:
        problems.append("no corpus document found -- the corpus check would prove nothing")
    doc_points = {str(d): document_points(d) & set(ocmap) for d in docs}
    report = {"source": str(SOURCE.relative_to(HERE)), "face": TC_FACE,
              "faceSizes": None, "tiers": {}, "corpusDocuments": len(docs)}
    for tier in (["C", "E", "F"] if a.tier == "all" else [a.tier]):
        path, wanted = build(tier, outdir)
        row = verify(path, wanted, original, problems)
        row.update(sizes(path))
        cmap = set(TTFont(str(path)).getBestCmap())
        missing = {d: sorted(p - cmap) for d, p in doc_points.items() if p - cmap}
        row["corpusMissing"] = {d: [f"U+{cp:04X}" for cp in m] for d, m in missing.items()}
        report["tiers"][tier] = row
    print(json.dumps({t: {k: v for k, v in r.items() if k != "corpusMissing"} | {
        "docsWithMissing": len(r["corpusMissing"])} for t, r in report["tiers"].items()}, indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    for p in problems:
        print("FAIL " + p)
    return 1 if problems else 0


def self_test(outdir: Path, original: TTFont) -> int:
    """Red cases: each mutation of a built subset must be caught."""
    built = sorted(outdir.glob("NotoSansCJKtc-Regular-subset-*.otf"))
    if not built:
        print("FAIL build a tier first")
        return 1
    path = built[0]
    wanted = set(TTFont(str(path)).getBestCmap()) & set(original.getBestCmap())
    results = []
    # 1. a required code point dropped from the subset's cmap
    f = TTFont(str(path))
    victim = sorted(wanted)[len(wanted) // 2]
    for t in f["cmap"].tables:
        t.cmap.pop(victim, None)
    p1 = outdir / "red-cmap.otf"
    f.save(str(p1))
    probs: list[str] = []
    verify(p1, wanted, original, probs)
    results.append(("dropped code point", any(f"U+{victim:04X}" in x for x in probs)))
    # 2. an advance width changed
    f = TTFont(str(path))
    g = f.getBestCmap()[victim]
    adv, lsb = f["hmtx"][g]
    f["hmtx"][g] = (adv + 1, lsb)
    p2 = outdir / "red-hmtx.otf"
    f.save(str(p2))
    probs = []
    verify(p2, wanted, original, probs)
    results.append(("advance changed", any("hmtx" in x for x in probs)))
    # 3. an outline replaced by another glyph's
    f = TTFont(str(path))
    cff = f["CFF "].cff
    top = cff.topDictIndex[0]
    names = [n for n in f.getGlyphOrder() if n != ".notdef"]
    a_, b_ = f.getBestCmap()[victim], names[0] if names[0] != f.getBestCmap()[victim] else names[1]
    top.CharStrings[a_].bytecode = None
    top.CharStrings[a_].program = list(top.CharStrings[b_].program)
    p3 = outdir / "red-outline.otf"
    f.save(str(p3))
    probs = []
    verify(p3, wanted, original, probs)
    results.append(("outline swapped", any("outlines differ" in x for x in probs)))
    for name, caught in results:
        print(("ok   " if caught else "MISS ") + name)
    return 0 if all(c for _, c in results) else 1


if __name__ == "__main__":
    sys.exit(main())
