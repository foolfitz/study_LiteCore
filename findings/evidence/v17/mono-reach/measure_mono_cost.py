#!/usr/bin/env python3
"""M1 of PREDICTION.md: what adding Mono faces to the CJK pack costs in bytes.  Offline (fontTools).

Positive control first: rebuild the shipped five-face collection with tools/build_cjk_subset_ttc_pack.py's own
`subset` + `collection` and require it byte-identical to dist/profiles/resources/cjk-sub-e5.<sha16>.data.  Then cut
the same tier-E code points from the full TTC's Mono TC face (face 8) with tools/build_cjk_subset.py's own `build`
and `verify` (only the face number differs; it is set on the module for the call and restored), name it per region
the way the pack tool names the Sans faces, and save E5+K (one Mono KR face) and E5+M5 (five Mono faces) as shared-
table collections.  Writes only under wasm_sdk_probe/build/mono-reach/ (refuses an existing one) and mono-cost.json
beside this file.
"""
import hashlib
import json
import sys
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont

HERE = Path(__file__).resolve().parent
PROBE = HERE.parents[3] / "wasm_sdk_probe"
sys.path.insert(0, str(PROBE / "tools"))
import build_cjk_subset as subset_tool  # noqa: E402
import build_cjk_subset_ttc_pack as ttc_pack  # noqa: E402

OUT = PROBE / "build/mono-reach"
SHIPPED = PROBE / "dist/profiles/resources/cjk-sub-e5.ce59153d3861ef9c.data"
MONO_TC_FACE = 8


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mono_subset(workdir: Path) -> tuple[Path, dict]:
    saved = subset_tool.TC_FACE
    subset_tool.TC_FACE = MONO_TC_FACE
    try:
        source = subset_tool.load_face()
        family = source["name"].getDebugName(1)
        if family != "Noto Sans Mono CJK TC":
            raise SystemExit(f"face {MONO_TC_FACE} of the full TTC is {family!r}, not Noto Sans Mono CJK TC")
        font, wanted = subset_tool.build(ttc_pack.TIER, workdir)
        problems: list[str] = []
        info = subset_tool.verify(font, wanted, subset_tool.load_face(), problems)
    finally:
        subset_tool.TC_FACE = saved
    if problems:
        raise SystemExit("Mono subset failed verification:\n  " + "\n  ".join(problems))
    return font, info


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


def save(faces: list[TTFont], name: str) -> Path:
    ttc = TTCollection()
    ttc.fonts = faces
    target = OUT / name
    ttc.save(str(target), shareTables=True)
    return target


def tables(font: TTFont) -> dict:
    return {tag: font.reader[tag] for tag in sorted(font.reader.keys())}


def check(built: Path, sources: list[tuple[str, TTFont]]) -> list[str]:
    """Every face's tables equal its source's, except `name` on renamed Mono faces; report the family names."""
    out, problems = [], []
    collection = TTCollection(str(built))
    if len(collection.fonts) != len(sources):
        return [f"{built.name}: {len(collection.fonts)} faces, expected {len(sources)}"]
    for face, (expected_family, source) in zip(collection.fonts, sources):
        family = face["name"].getDebugName(1)
        out.append(family)
        if family != expected_family:
            problems.append(f"{built.name}: face named {family!r}, expected {expected_family!r}")
        a, b = tables(face), tables(source)
        skip = {"name"} if "Mono" in expected_family and not expected_family.endswith("TC") else set()
        for tag in sorted((set(a) | set(b)) - skip):
            if a.get(tag) != b.get(tag):
                problems.append(f"{built.name}: {family}: table {tag!r} differs from its source")
    return problems or [f"ok: {', '.join(out)}"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "sans").mkdir()
    (OUT / "mono").mkdir()
    report = {"script": sha256(Path(__file__)), "tools": {
        "build_cjk_subset.py": sha256(PROBE / "tools/build_cjk_subset.py"),
        "build_cjk_subset_ttc_pack.py": sha256(PROBE / "tools/build_cjk_subset_ttc_pack.py")},
        "shipped": {"path": str(SHIPPED.relative_to(PROBE)), "sha256": sha256(SHIPPED),
                    **subset_tool.sizes(SHIPPED)}}
    # Positive control: the shipped pack, rebuilt.
    sans_font = ttc_pack.subset(OUT / "sans")              # verifies, and requires v15's exact tier-E font
    e5 = ttc_pack.collection(sans_font, OUT / "sans")
    report["control"] = {"sha256": sha256(e5), "identicalToShipped": sha256(e5) == sha256(SHIPPED)}
    if not report["control"]["identicalToShipped"]:
        (HERE / "mono-cost.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        raise SystemExit("the rebuilt five-face collection is not the shipped cjk-sub-e5; deltas would mean nothing")
    mono_font, info = mono_subset(OUT / "mono")
    report["monoSubset"] = {"sourceFace": MONO_TC_FACE, "sha256": sha256(mono_font), **info,
                            **subset_tool.sizes(mono_font)}
    sans_faces = list(TTCollection(str(e5)).fonts)
    sans_sources = [(f["name"].getDebugName(1), f) for f in TTCollection(str(e5)).fonts]
    mono_source = TTFont(mono_font)
    kr = next(f for f in ttc_pack.FACES if f[0] == "KR")
    variants = {"E5+K": [kr], "E5+M5": list(ttc_pack.FACES)}
    report["variants"] = {}
    for name, faces in variants.items():
        built = save(sans_faces + [mono_face(mono_font, *f) for f in faces], f"{name}.ttc")
        sources = sans_sources + [(f"Noto Sans Mono CJK {f[0]}", mono_source) for f in faces]
        sizes = subset_tool.sizes(built)
        report["variants"][name] = {"sha256": sha256(built), "check": check(built, sources), **sizes,
                                    "delta": {k: sizes[k] - report["shipped"][k] for k in sizes}}
    (HERE / "mono-cost.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
