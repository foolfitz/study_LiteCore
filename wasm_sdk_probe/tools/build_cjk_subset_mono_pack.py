#!/usr/bin/env python3
"""The v18 profile's CJK pack: `cjk-sub-e5` plus five Mono faces (finding 116;
owner's choice A, 2026-10-08; spec SPEC-M3-paragraph-merge section 28).

`cjk-sub-e5` (v16, v17) has no Noto Sans Mono CJK family.  fontconfig's stock
`65-nonlatin.conf` names `Noto Sans Mono CJK KR` as the only Mono CJK face on
the generic monospace list, so with the full TTC (v8) a `monospace` request --
and every fixed-pitch request, which LibreOffice extends with `monospace` --
resolves to it; with the subset it falls to Liberation Mono
(findings/evidence/v17/layout-corpus/fc-request/, findings/evidence/v17/mono-reach/).

This builds one ten-face collection, faces in the full TTC's order:
  0-4  the five Sans faces of `cjk-sub-e5`, read back from that collection as
       tools/build_cjk_subset_ttc_pack.py builds it (required byte-identical
       to the shipped pack first), every table unchanged;
  5-9  the same tier-E code points cut from the full TTC's Mono TC face (face
       8) with tools/build_cjk_subset.py's own `build` and `verify` (only the
       face number differs), named JP KR SC TC HK the way the e5 tool names
       the Sans faces; each face's name records must equal those of the full
       TTC's own Mono face for that region.
It is saved under a NEW path (`...-subset-E10.ttc`), packed into
dist/profiles/resources/cjk-sub-e10.<sha16>.{data,metadata}, and
sdk/v18-writer-review-manifest.json is written: v17's manifest with the
`cjk-sub-e5` pack replaced by this one and nothing else changed.

  build_cjk_subset_mono_pack.py             build the pack, write the v18 manifest
  build_cjk_subset_mono_pack.py --check     rebuild twice in scratch directories; fail unless
                                            the builds agree, verify, the committed v18
                                            manifest names exactly that pack, the pack's data
                                            and metadata on disk have the built bytes (sha256),
                                            and zstd -19 is within spec 28.4 W1's allowance
  build_cjk_subset_mono_pack.py --self-test the verifier's red cases (a Sans table altered, a
                                            Mono name record altered) must both be reported, and
                                            so must --check's (pack bytes on disk altered or
                                            missing, a size one byte over the allowance)

tools/build_cjk_subset_ttc_pack.py (v16/v17's) is not edited: their profile
rules depend on it and run its --check.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import compression.zstd as zstd
from fontTools.ttLib import TTCollection, TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cjk_subset as subset_tool  # noqa: E402
import build_cjk_subset_ttc_pack as e5_tool  # noqa: E402
from build_r5_profiles import create_pack  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
STEM = "cjk-sub-e10"
FONT_PATH = "/instdir/share/fonts/truetype/NotoSansCJK-Regular-subset-E10.ttc"
MONO_TC_FACE = 8                     # the full TTC: faces 0-4 Sans JP KR SC TC HK, 5-9 Mono JP KR SC TC HK
ZSTD_ALLOWANCE = 300_000             # spec 28.4 W1: zstd -19 bytes allowed over cjk-sub-e5
SOURCE_MANIFEST = HERE / "sdk/v17-writer-review-manifest.json"
V18_MANIFEST = HERE / "sdk/v18-writer-review-manifest.json"
RESOURCES = HERE / "dist/profiles/resources"
PURPOSE = ("CJK corpus: Traditional Chinese subset of Noto Sans CJK, tier E "
           "(Big5, HKSCS, U+4E00-U+9FFF, kana), as five Sans families (JP KR SC TC HK) "
           "sharing one glyph set plus five Noto Sans Mono CJK families sharing the "
           "same code points cut from the Mono TC face")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def size_problems(sizes: dict) -> list[str]:
    """Spec SPEC-M3-paragraph-merge 28.4 W1: the pack's zstd -19 size is at most `cjk-sub-e5`'s plus this."""
    over = sizes["zstd19"] - sizes["e5Zstd19"]
    if over > ZSTD_ALLOWANCE:
        return [f"zstd -19 is {sizes['zstd19']} bytes, {over} over cjk-sub-e5's {sizes['e5Zstd19']}; spec 28.4 W1 "
                f"allows {ZSTD_ALLOWANCE}: stop and return the decision to the owner"]
    return []


def on_disk_problems(built: dict, resources: Path) -> list[str]:
    """`built` maps each pack file name to the sha256 of what the tool just built; the file on disk must have it."""
    problems = []
    for name, digest in built.items():
        path = resources / name
        if not path.exists():
            problems.append(f"{path.relative_to(HERE) if path.is_relative_to(HERE) else path} is missing: "
                            "run the tool without --check")
        elif sha256(path) != digest:
            problems.append(f"{path.relative_to(HERE) if path.is_relative_to(HERE) else path} is not the bytes the "
                            f"tool builds (sha256 {sha256(path)[:16]} on disk, {digest[:16]} built)")
    return problems


def shipped_e5() -> Path:
    entry = [e for e in json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))["resourcePacks"]
             if e["id"] == e5_tool.STEM]
    if len(entry) != 1:
        raise SystemExit(f"expected exactly one {e5_tool.STEM} pack in {SOURCE_MANIFEST.name}")
    # `data` is relative to a profile directory (dist/profiles/<profile>/), i.e. ../resources/<name>.
    return RESOURCES / Path(entry[0]["data"]).name


def sans_collection(workdir: Path) -> Path:
    """`cjk-sub-e5`'s collection, rebuilt by its own tool and required to be the shipped bytes."""
    (workdir / "sans").mkdir()
    font = e5_tool.subset(workdir / "sans")       # verifies, and requires v15's exact tier-E font
    built = e5_tool.collection(font, workdir / "sans")
    if sha256(built) != sha256(shipped_e5()):
        raise SystemExit("the rebuilt cjk-sub-e5 collection is not the shipped one")
    return built


def mono_subset(workdir: Path) -> Path:
    """Tier E cut from the Mono TC face with the subset tool's own build/verify.  The tool reads its face number
    from a module global; it is set for the call and restored."""
    (workdir / "mono").mkdir()
    saved = subset_tool.TC_FACE
    subset_tool.TC_FACE = MONO_TC_FACE
    try:
        family = subset_tool.load_face()["name"].getDebugName(1)
        if family != "Noto Sans Mono CJK TC":
            raise SystemExit(f"face {MONO_TC_FACE} of {subset_tool.SOURCE.name} is {family!r}")
        font, wanted = subset_tool.build(e5_tool.TIER, workdir / "mono")
        problems: list[str] = []
        subset_tool.verify(font, wanted, subset_tool.load_face(), problems)
    finally:
        subset_tool.TC_FACE = saved
    if problems:
        raise SystemExit("Mono subset failed verification:\n  " + "\n  ".join(problems))
    return font


def mono_face(font: Path, code: str, lower: str, lang: int) -> TTFont:
    face = TTFont(font, recalcTimestamp=False, recalcBBoxes=False)
    if code != "TC":
        for record in face["name"].names:
            text = (record.toUnicode()
                    .replace("Noto Sans Mono CJK TC", f"Noto Sans Mono CJK {code}")
                    .replace("NotoSansMonoCJKtc", f"NotoSansMonoCJK{lower}"))
            if record.langID == 0x404:
                record.langID = lang
            record.string = text
    return face


def collection(sans: Path, mono: Path, out: Path) -> Path:
    faces = list(TTCollection(str(sans), recalcTimestamp=False, recalcBBoxes=False).fonts)
    faces += [mono_face(mono, *f) for f in e5_tool.FACES]
    ttc = TTCollection()
    ttc.fonts = faces
    target = out / Path(FONT_PATH).name
    ttc.save(str(target), shareTables=True)
    return target


def head_fields(face: TTFont) -> dict:
    out = dict(vars(face["head"]))
    for k in ("checkSumAdjustment", "tableTag"):
        out.pop(k, None)
    return out


def names(face: TTFont) -> set:
    return {(r.platformID, r.platEncID, r.langID, r.nameID, r.toUnicode()) for r in face["name"].names}


def verify(ttc: Path, sans: Path, mono: Path) -> list[str]:
    problems = []
    built = TTCollection(str(ttc))
    sans_faces = TTCollection(str(sans)).fonts
    mono_font = TTFont(mono)
    full = TTCollection(str(subset_tool.SOURCE), lazy=True)
    if len(built.fonts) != 2 * len(e5_tool.FACES):
        return [f"{len(built.fonts)} faces, expected {2 * len(e5_tool.FACES)}"]
    for i, face in enumerate(built.fonts):
        code = e5_tool.FACES[i % 5][0]
        mono_half = i >= 5
        source = mono_font if mono_half else sans_faces[i]
        want = f"Noto Sans {'Mono ' if mono_half else ''}CJK {code}"
        family = face["name"].getDebugName(1)
        if family != want:
            problems.append(f"face {i}: family {family!r}, expected {want!r}")
        tags = sorted(set(face.keys()) | set(source.keys()))
        for tag in tags:
            if tag in ("GlyphOrder", "head") or (mono_half and tag == "name"):
                continue
            if tag not in face or tag not in source or face.getTableData(tag) != source.getTableData(tag):
                problems.append(f"face {i} ({want}): table {tag!r} differs from its source")
        if head_fields(face) != head_fields(source):
            problems.append(f"face {i} ({want}): head differs beyond checkSumAdjustment")
        if mono_half and names(face) != names(full.fonts[5 + i % 5]):
            problems.append(f"face {i} ({want}): name records differ from the full TTC's own {want}")
    return problems


def build_pack(output: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        sans, mono = sans_collection(work), mono_subset(work)
        (work / "one").mkdir()
        (work / "two").mkdir()
        first, second = collection(sans, mono, work / "one"), collection(sans, mono, work / "two")
        if sha256(first) != sha256(second):
            raise SystemExit("two builds of the collection differ: not deterministic")
        problems = verify(first, sans, mono)
        if problems:
            raise SystemExit("collection failed verification:\n  " + "\n  ".join(problems))
        data = first.read_bytes()
        sizes = {"raw": len(data), "zstd19": len(zstd.compress(data, level=19)),
                 "e5Raw": sans.stat().st_size, "e5Zstd19": len(zstd.compress(sans.read_bytes(), level=19))}
        pack = create_pack(first, [{"filename": FONT_PATH, "start": 0, "end": len(data)}], output, STEM)
        return {**pack, "sizes": sizes}


def v18_manifest(pack: dict) -> dict:
    out = copy.deepcopy(json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8")))
    hits = [i for i, e in enumerate(out["resourcePacks"]) if e["id"] == e5_tool.STEM]
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one {e5_tool.STEM} pack in {SOURCE_MANIFEST.name}, found {len(hits)}")
    out["resourcePacks"][hits[0]] = {
        "bytes": pack["bytes"], "data": f"../resources/{pack['data']}", "id": STEM,
        "loadAtStartup": True, "metadata": f"../resources/{pack['metadata']}",
        "purpose": PURPOSE, "sha256": pack["sha256"]}
    return out


def self_test() -> int:
    """Red cases: the verifier must report an altered Sans table and an altered Mono name record."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        sans, mono = sans_collection(work), mono_subset(work)
        (work / "ok").mkdir()
        ok = collection(sans, mono, work / "ok")
        results = {"unaltered": verify(ok, sans, mono)}
        for case in ("sans-table", "mono-name"):
            faces = list(TTCollection(str(ok), recalcTimestamp=False, recalcBBoxes=False).fonts)
            if case == "sans-table":
                faces[0]["OS/2"].usWeightClass += 1
            else:
                record = next(r for r in faces[6]["name"].names if r.nameID == 4 and r.langID == 0x409)
                record.string = record.toUnicode() + " X"
            ttc = TTCollection()
            ttc.fonts = faces
            (work / case).mkdir()
            altered = work / case / "altered.ttc"
            ttc.save(str(altered), shareTables=True)
            results[case] = verify(altered, sans, mono)
    # --check's own comparisons (opus review item 5): a pack file on disk that is not the built bytes, a missing
    # one, and a size one byte over the allowance must be reported; the built bytes and a size exactly at the
    # allowance must not.
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "p.data").write_bytes(b"built")
        built = {"p.data": sha256(work / "p.data")}
        results["disk-same"] = on_disk_problems(built, work)
        (work / "p.data").write_bytes(b"altered")
        results["disk-altered"] = on_disk_problems(built, work)
        results["disk-missing"] = on_disk_problems({"q.data": built["p.data"]}, work)
    results["size-at-allowance"] = size_problems({"zstd19": 100 + ZSTD_ALLOWANCE, "e5Zstd19": 100})
    results["size-over"] = size_problems({"zstd19": 101 + ZSTD_ALLOWANCE, "e5Zstd19": 100})
    for case, problems in results.items():
        print(f"{case}: {len(problems)} problem(s)" + "".join(f"\n  {p}" for p in problems))
    good = (not results["unaltered"] and any("OS/2" in p for p in results["sans-table"])
            and any("name records" in p for p in results["mono-name"])
            and not results["disk-same"] and any("not the bytes" in p for p in results["disk-altered"])
            and any("missing" in p for p in results["disk-missing"])
            and not results["size-at-allowance"] and any("allows" in p for p in results["size-over"]))
    print("SELF-TEST " + ("PASS" if good else "FAIL"))
    return 0 if good else 1


def dump(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.check:
        with tempfile.TemporaryDirectory() as tmp:
            pack = build_pack(Path(tmp))
            expected = dump(v18_manifest(pack))
            built = {name: sha256(Path(tmp) / name) for name in (pack["data"], pack["metadata"])}
        committed = V18_MANIFEST.read_text(encoding="utf-8") if V18_MANIFEST.exists() else ""
        problems = []
        if committed != expected:
            problems.append(f"{V18_MANIFEST.name} is not what the tool generates from "
                            f"{SOURCE_MANIFEST.name} and today's collection (pack {pack['data']})")
        problems += on_disk_problems(built, RESOURCES)
        problems += size_problems(pack["sizes"])
        for p in problems:
            print("FAIL " + p)
        if not problems:
            print(f"ok: {pack['data']} ({pack['bytes']} bytes; sizes {pack['sizes']}) matches {V18_MANIFEST.name}")
        return 1 if problems else 0
    RESOURCES.mkdir(parents=True, exist_ok=True)
    pack = build_pack(RESOURCES)
    V18_MANIFEST.write_text(dump(v18_manifest(pack)), encoding="utf-8")
    print(f"wrote {RESOURCES.relative_to(HERE)}/{pack['data']}, {pack['metadata']} "
          f"({pack['bytes']} bytes, sha256 {pack['sha256'][:16]}; sizes {pack['sizes']}) "
          f"and {V18_MANIFEST.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
