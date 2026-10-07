#!/usr/bin/env python3
"""The v17 profile's base pack: `base-r5` without `35-lang-normalize.conf`.

Finding 114; SPEC-M3-paragraph-merge 26 (owner: fix now as v17; fable: omit
the file).  LibreOffice adds the font language to a fontconfig pattern as a
STRING, and fontconfig's `conf.d/35-lang-normalize.conf` tests `lang` with
`contains`, which on strings is a substring test: `zh-tw` becomes `tw` (Twi)
and zh-TW text whose font the profile lacks lays out with a Latin line height.
66 of the 282 tags LibreOffice can send are rewritten; upstream fontconfig
does not enable the file, LibreOffice's packaging does
(external/fontconfig/ExternalPackage_fontconfig_data.mk:34).

The pack is `base-r5`'s entries minus that one, sliced by `create_pack`.  It is
built twice -- from the shipped `base-r5` data and from the original image the
r5 split was cut from -- and both must give the same sha256 (spec 26.3 V1); the
original is first required to reproduce `base-r5` itself, so the second build
is a check of the source and not just of the slicing.  It writes
dist/profiles/resources/base-r5-no35.<sha16>.{data,metadata} and
sdk/v17-writer-review-manifest.json: v16's source manifest with the two
`soffice.data` artifact entries replaced and nothing else changed.

  build_base_no35_pack.py          build the pack, write the v17 manifest
  build_base_no35_pack.py --check  rebuild in a scratch directory; fail unless
                                   the committed v17 manifest names exactly that
                                   pack, the pack is present, and V1 reconciles
                                   (writes nothing in the tree)
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_r5_profiles import create_pack, sha256_file  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
RESOURCES = HERE / "dist/profiles/resources"
BASE_DATA = RESOURCES / "base-r5.ba15a988a7fec468.data"
BASE_METADATA = RESOURCES / "base-r5.ef11ef80faf373bc.metadata"
BASE_SHA256 = "ba15a988a7fec4683a0d5dec32b015cc98cc03df428d322316bc0745dd7b4f35"
# The image the r5 split was cut from: the Makefile's CORE_DATA (LOBUILD).  Not
# wasm-lite/build/ -- that image differs (bootstraprc size; measured 2026-10-07).
ORIGINAL = HERE.parent / "wasm-lite/build-headless-probe/instdir/program/soffice.data"
DROP = "/instdir/share/fontconfig/conf.d/35-lang-normalize.conf"
DROP_BYTES = 48_949
STEM = "base-r5-no35"
SOURCE_MANIFEST = HERE / "sdk/v16-writer-review-manifest.json"
V17_MANIFEST = HERE / "sdk/v17-writer-review-manifest.json"
# Spec 26.3 V6: the corpus comparison's control keeps 20.3's one variable (the
# CJK subset) by carrying the SAME base pack: r6's manifest (cjk-r5, the full
# TTC) with base-r5-no35.
AB_SOURCE_MANIFEST = HERE / "sdk/r6-writer-review-manifest.json"
V17_AB_MANIFEST = HERE / "sdk/v17-cjk-r5-ab-writer-review-manifest.json"


def entries(metadata: dict, drop: tuple[str, ...]) -> list[dict]:
    kept = [e for e in metadata["files"] if e["filename"] not in drop]
    if len(metadata["files"]) - len(kept) != len(drop):
        raise SystemExit(f"expected to drop exactly {list(drop)}, dropped "
                         f"{len(metadata['files']) - len(kept)} entries")
    return [{"filename": e["filename"], "start": e["start"], "end": e["end"]} for e in kept]


def from_original(base_files: list[dict], drop: tuple[str, ...], output: Path, stem: str) -> dict:
    """The same entry list, sliced from the original image by ITS offsets."""
    meta = json.loads((ORIGINAL.parent / "soffice.data.js.metadata").read_text(encoding="utf-8"))
    where = {e["filename"]: (e["start"], e["end"]) for e in meta["files"]}
    chosen = []
    for e in base_files:
        if e["filename"] in drop:
            continue
        start, end = where[e["filename"]]
        if end - start != e["end"] - e["start"]:
            raise SystemExit(f"{e['filename']}: size differs between base-r5 and the original")
        chosen.append({"filename": e["filename"], "start": start, "end": end})
    return create_pack(ORIGINAL, chosen, output, stem)


def reconcile(new_metadata: dict, new_data: Path, old_metadata: dict) -> list[str]:
    """Spec 26.3 V1: the new pack is the old one minus exactly DROP."""
    problems = []
    old_names = [e["filename"] for e in old_metadata["files"]]
    new_names = [e["filename"] for e in new_metadata["files"]]
    if new_names != [n for n in old_names if n != DROP]:
        problems.append("file list is not base-r5's minus exactly " + DROP)
    if new_metadata["remote_package_size"] != old_metadata["remote_package_size"] - DROP_BYTES:
        problems.append(f"remote_package_size {new_metadata['remote_package_size']} != "
                        f"{old_metadata['remote_package_size'] - DROP_BYTES}")
    old_at = {e["filename"]: e for e in old_metadata["files"]}
    with BASE_DATA.open("rb") as old, new_data.open("rb") as new:
        for e in new_metadata["files"]:
            o = old_at.get(e["filename"])
            if o is None:
                continue
            old.seek(o["start"])
            new.seek(e["start"])
            a, b = old.read(o["end"] - o["start"]), new.read(e["end"] - e["start"])
            if hashlib.sha256(a).digest() != hashlib.sha256(b).digest():
                problems.append(f"{e['filename']}: bytes differ from base-r5's slice")
    return problems


def build(output: Path, drop: tuple[str, ...] = (DROP,)) -> tuple[dict, list[str]]:
    if sha256_file(BASE_DATA) != BASE_SHA256:
        raise SystemExit(f"{BASE_DATA.name} is not the shipped base-r5")
    old_metadata = json.loads(BASE_METADATA.read_text(encoding="utf-8"))
    pack = create_pack(BASE_DATA, entries(old_metadata, drop), output, STEM)
    new_metadata = json.loads((output / pack["metadata"]).read_text(encoding="utf-8"))
    problems = reconcile(new_metadata, output / pack["data"], old_metadata)
    if not ORIGINAL.exists():
        problems.append(f"{ORIGINAL} is missing: the second build (spec 26.3 V1) cannot run")
        return pack, problems
    with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
        same = from_original(old_metadata["files"], (), Path(one), "base-r5")
        if same["sha256"] != BASE_SHA256:
            problems.append("the original image does not reproduce base-r5: it is not the source")
        again = from_original(old_metadata["files"], drop, Path(two), STEM)
        if again["sha256"] != pack["sha256"]:
            problems.append(f"built from the original: {again['sha256'][:16]}, from base-r5: "
                            f"{pack['sha256'][:16]}")
    return pack, problems


def v17_manifest(pack: dict, source: Path = SOURCE_MANIFEST) -> dict:
    out = copy.deepcopy(json.loads(source.read_text(encoding="utf-8")))
    files = out["artifactFiles"]
    if (files.get("soffice.data") != f"../resources/{BASE_DATA.name}"
            or files.get("soffice.data.js.metadata") != f"../resources/{BASE_METADATA.name}"):
        raise SystemExit(f"{source.name} does not point at base-r5 as expected")
    files["soffice.data"] = f"../resources/{pack['data']}"
    files["soffice.data.js.metadata"] = f"../resources/{pack['metadata']}"
    return out


def dump(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def report(pack: dict, problems: list[str]) -> int:
    for p in problems:
        print("FAIL " + p)
    if not problems:
        print(f"ok: {pack['data']} ({pack['bytes']} bytes, {pack['files']} files, "
              f"sha256 {pack['sha256'][:16]}); V1 reconciles; same sha from the original image")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--red-drop", metavar="PATH", default=None,
                    help="red case for V1: also drop PATH; reconciliation must fail")
    a = ap.parse_args()
    if a.check or a.red_drop:
        drop = (DROP,) + ((a.red_drop,) if a.red_drop else ())
        with tempfile.TemporaryDirectory() as tmp:
            pack, problems = build(Path(tmp), drop)
            expected = {V17_MANIFEST: dump(v17_manifest(pack)),
                        V17_AB_MANIFEST: dump(v17_manifest(pack, AB_SOURCE_MANIFEST))}
        if not a.red_drop:
            for path, text in expected.items():
                committed = path.read_text(encoding="utf-8") if path.exists() else ""
                if committed != text:
                    problems.append(f"{path.name} is not what the tool generates (pack {pack['data']})")
            for name in (pack["data"], pack["metadata"]):
                if not (RESOURCES / name).exists():
                    problems.append(f"{RESOURCES.relative_to(HERE)}/{name} is missing: run without --check")
        return report(pack, problems)
    pack, problems = build(RESOURCES)
    if problems:
        return report(pack, problems)
    V17_MANIFEST.write_text(dump(v17_manifest(pack)), encoding="utf-8")
    V17_AB_MANIFEST.write_text(dump(v17_manifest(pack, AB_SOURCE_MANIFEST)), encoding="utf-8")
    print(f"wrote {RESOURCES.relative_to(HERE)}/{pack['data']}, {pack['metadata']}, "
          f"{V17_MANIFEST.relative_to(HERE)} and {V17_AB_MANIFEST.relative_to(HERE)}")
    return report(pack, problems)


if __name__ == "__main__":
    sys.exit(main())
