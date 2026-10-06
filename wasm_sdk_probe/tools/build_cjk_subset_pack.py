#!/usr/bin/env python3
"""The v15 profile's CJK pack: tier E of the Traditional Chinese subset (owner's
choice, 2026-10-07; findings/evidence/cjk-subset/README.md).

Builds the subset with tools/build_cjk_subset.py, re-verifies it (coverage and
identity against the original face; no pack is written from an unverified
font), packs it with build_r5_profiles.create_pack into
dist/profiles/resources/cjk-sub-e.<sha16>.{data,metadata}, and writes
sdk/v15-writer-review-manifest.json: sdk/r6-writer-review-manifest.json with
the `cjk-r5` resource pack replaced by this one and nothing else changed.

The subset is deterministic (the source's head.modified is kept), so the pack's
hash is a function of the source TTC, the tier and fontTools' version.

  build_cjk_subset_pack.py            build the pack, write the v15 manifest
  build_cjk_subset_pack.py --check    rebuild into a scratch directory and fail
                                      unless the committed v15 manifest names
                                      exactly that pack and differs from r6 only
                                      there (writes nothing in the tree)
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cjk_subset as subset_tool  # noqa: E402
from build_r5_profiles import create_pack  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
TIER = "E"
STEM = "cjk-sub-e"
FONT_PATH = "/instdir/share/fonts/truetype/NotoSansCJKtc-Regular-subset-E.otf"
SOURCE_MANIFEST = HERE / "sdk/r6-writer-review-manifest.json"
V15_MANIFEST = HERE / "sdk/v15-writer-review-manifest.json"
RESOURCES = HERE / "dist/profiles/resources"
PURPOSE = ("CJK corpus: Traditional Chinese subset of Noto Sans CJK, tier E "
           "(Big5, HKSCS, U+4E00-U+9FFF, kana)")


def build_pack(workdir: Path, output: Path) -> dict:
    font, wanted = subset_tool.build(TIER, workdir)
    problems: list[str] = []
    subset_tool.verify(font, wanted, subset_tool.load_face(), problems)
    if problems:
        raise SystemExit("subset failed verification:\n  " + "\n  ".join(problems))
    size = font.stat().st_size
    return create_pack(font, [{"filename": FONT_PATH, "start": 0, "end": size}], output, STEM)


def v15_manifest(pack: dict) -> dict:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    out = copy.deepcopy(manifest)
    replaced = 0
    for index, entry in enumerate(out["resourcePacks"]):
        if entry["id"] == "cjk-r5":
            out["resourcePacks"][index] = {
                "bytes": pack["bytes"],
                "data": f"../resources/{pack['data']}",
                "id": STEM,
                "loadAtStartup": True,
                "metadata": f"../resources/{pack['metadata']}",
                "purpose": PURPOSE,
                "sha256": pack["sha256"],
            }
            replaced += 1
    if replaced != 1:
        raise SystemExit(f"expected exactly one cjk-r5 pack in {SOURCE_MANIFEST.name}, found {replaced}")
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
            expected = dump(v15_manifest(pack))
        committed = V15_MANIFEST.read_text(encoding="utf-8") if V15_MANIFEST.exists() else ""
        problems = []
        if committed != expected:
            problems.append(f"{V15_MANIFEST.name} is not what the tool generates from "
                            f"{SOURCE_MANIFEST.name} and today's subset (pack {pack['data']})")
        for name in (pack["data"], pack["metadata"]):
            if not (RESOURCES / name).exists():
                problems.append(f"{RESOURCES.relative_to(HERE)}/{name} is missing: run the tool without --check")
        for p in problems:
            print("FAIL " + p)
        if not problems:
            print(f"ok: {pack['data']} ({pack['bytes']} bytes) matches {V15_MANIFEST.name}")
        return 1 if problems else 0
    workdir = HERE / "build/cjk-subset"
    workdir.mkdir(parents=True, exist_ok=True)
    RESOURCES.mkdir(parents=True, exist_ok=True)
    pack = build_pack(workdir, RESOURCES)
    V15_MANIFEST.write_text(dump(v15_manifest(pack)), encoding="utf-8")
    print(f"wrote {RESOURCES.relative_to(HERE)}/{pack['data']}, {pack['metadata']} "
          f"({pack['bytes']} bytes, sha256 {pack['sha256'][:16]}) and {V15_MANIFEST.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
