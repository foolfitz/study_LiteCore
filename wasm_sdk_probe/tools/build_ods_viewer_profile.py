#!/usr/bin/env python3
"""ods-viewer-v1, the read-only spreadsheet viewer's profile (SPEC-M4-ods-in-nextcloud §3.2, E8; O3).

THE BASE PACK.  The a11y+calc core's base pack is e2-editor-v14's `base-e2-editor-v14.9901e9be…` (1,489
files: base-r5's 1,241 plus 248 Calc files).  It still carries
`/instdir/share/fontconfig/conf.d/35-lang-normalize.conf`, finding 114's cause (`zh-tw` rewritten to
`tw` by a substring test, zh-TW text laid out with a Latin line height), which the editor has dropped
since v17 (`build_base_no35_pack.py`).  The viewer's base pack is 9901e9be minus that one entry, built
twice -- from 9901e9be's data, and from the a11y core's original image by ITS offsets, after the
original is first required to reproduce 9901e9be itself -- and both must give the same sha (E8).  It
lives in the viewer's own profile directory, as v14's did; nothing is added to profiles/resources/.

THE OTHER PACKS are the shipping ones, referenced by path and not copied, so the browser's cache entry
is the editor's: `cjk-sub-e10` (loaded at startup) and `fallback-fonts-r5` (declared, not loaded).

THE MANIFEST is the reader's shape: no editor contract, the capabilities the engine reports under
OXSDK_ODS_VIEWER (sdk_api.cpp), and their bits; no save.

  build_ods_viewer_profile.py --check
      rebuild the base pack in a scratch directory and reconcile it (E8); writes nothing
  build_ods_viewer_profile.py --red-drop PATH
      red case: also drop PATH; the reconciliation must fail
  build_ods_viewer_profile.py --loader L --wasm W --worker K --worker-sha256 S --exports X --output DIR
      package the profile from the link's outputs (the Makefile's packaging rule)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_r5_profiles import create_pack, sha256_file  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
PROFILE = "ods-viewer-v1"
V14 = HERE / "dist/profiles/e2-editor-v14"
A11Y_BASE_DATA = V14 / "base-e2-editor-v14.9901e9be29c9ded2.data"
A11Y_BASE_METADATA = V14 / "base-e2-editor-v14.b1e48f2b7ac50b60.metadata"
A11Y_BASE_SHA256 = "9901e9be29c9ded2661ba63930078fd2360e98cbc9523ba485387e2baa8df6dd"
ORIGINAL = HERE.parent / "wasm-lite/build-a11y-gate0/instdir/program/soffice.data"
DROP = "/instdir/share/fontconfig/conf.d/35-lang-normalize.conf"
DROP_BYTES = 48_949
STEM = "base-a11y-no35"
RESOURCES = HERE / "dist/profiles/resources"
SHARED_PACKS = [
    # (id, data, data sha256, metadata, metadata sha256, loadAtStartup, purpose) -- e2-editor-v22's
    ("cjk-sub-e10", "cjk-sub-e10.06976180177c8bd2.data",
     "06976180177c8bd2a0c7bb7c18837bd12ce116481aefc56b60807948b585ffab",
     "cjk-sub-e10.4144b2b2a44dd797.metadata",
     "4144b2b2a44dd797cd54170bc28a6b27e01a27397bd1f8307c4f13229856a93b", True,
     "CJK corpus: the editor's Traditional Chinese subset of Noto Sans CJK (tier E), shared"),
    ("fallback-fonts-r5", "fallback-fonts-r5.33856e2a082148dd.data",
     "33856e2a082148ddbb753652861a5dd05af911e0d3587a3e8c75948a345de3a9",
     "fallback-fonts-r5.924fb0ed8b459946.metadata",
     "924fb0ed8b4599463e9a9d53f6c1aa06cc306cced8ef112424275605ed0c907a", False,
     "optional complex-script and fidelity fallback"),
]
# sdk_api.cpp under OXSDK_ODS_VIEWER: OPEN_ODT | RGBA_TILE | CANCEL_QUEUED | SEARCH | OPEN_ODS |
# PART_SWITCH | PART_TEXT -- no SAVE_ODT.  Named and summed here; the worker refuses a manifest whose
# bits differ from what the engine reports at init.
CAPABILITIES = [("open-odt", 1 << 0), ("rgba-tile", 1 << 1), ("cancel-queued", 1 << 4),
                ("search", 1 << 5), ("open-ods", 1 << 11), ("part-switch", 1 << 12),
                ("part-text", 1 << 13)]
EXPORTS_REQUIRED = ["_oxsdk_document_open", "_oxsdk_document_paint", "_oxsdk_document_close",
                    "_oxsdk_document_set_part", "_oxsdk_document_current_part",
                    "_oxsdk_document_part_name", "_oxsdk_document_part_text"]
EXPORTS_FORBIDDEN = ["_oxsdk_document_save", "_oxsdk_document_click", "_oxsdk_document_insert_text",
                     "_oxsdk_document_get_selection", "_oxsdk_document_replace_selection",
                     "_oxsdk_document_undo", "_oxsdk_document_redo"]


def entries(metadata: dict, drop: tuple[str, ...]) -> list[dict]:
    kept = [e for e in metadata["files"] if e["filename"] not in drop]
    if len(metadata["files"]) - len(kept) != len(drop):
        raise SystemExit(f"expected to drop exactly {list(drop)}, dropped {len(metadata['files']) - len(kept)}")
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
            raise SystemExit(f"{e['filename']}: size differs between 9901e9be and the original")
        chosen.append({"filename": e["filename"], "start": start, "end": end})
    return create_pack(ORIGINAL, chosen, output, stem)


def reconcile(new_metadata: dict, new_data: Path, old_metadata: dict) -> list[str]:
    """E8: the new pack is 9901e9be minus exactly DROP, every other file byte-identical."""
    problems = []
    old_names = [e["filename"] for e in old_metadata["files"]]
    new_names = [e["filename"] for e in new_metadata["files"]]
    if new_names != [n for n in old_names if n != DROP]:
        problems.append("file list is not 9901e9be's minus exactly " + DROP)
    if new_metadata["remote_package_size"] != old_metadata["remote_package_size"] - DROP_BYTES:
        problems.append(f"remote_package_size {new_metadata['remote_package_size']} != "
                        f"{old_metadata['remote_package_size'] - DROP_BYTES}")
    old_at = {e["filename"]: e for e in old_metadata["files"]}
    with A11Y_BASE_DATA.open("rb") as old, new_data.open("rb") as new:
        for e in new_metadata["files"]:
            o = old_at.get(e["filename"])
            if o is None:
                problems.append(f"{e['filename']}: not in 9901e9be")
                continue
            old.seek(o["start"])
            new.seek(e["start"])
            if (hashlib.sha256(old.read(o["end"] - o["start"])).digest()
                    != hashlib.sha256(new.read(e["end"] - e["start"])).digest()):
                problems.append(f"{e['filename']}: bytes differ from 9901e9be's slice")
    return problems


def build_base(output: Path, drop: tuple[str, ...] = (DROP,)) -> tuple[dict, list[str]]:
    if sha256_file(A11Y_BASE_DATA) != A11Y_BASE_SHA256:
        raise SystemExit(f"{A11Y_BASE_DATA.name} is not e2-editor-v14's base pack")
    old_metadata = json.loads(A11Y_BASE_METADATA.read_text(encoding="utf-8"))
    pack = create_pack(A11Y_BASE_DATA, entries(old_metadata, drop), output, STEM)
    new_metadata = json.loads((output / pack["metadata"]).read_text(encoding="utf-8"))
    problems = reconcile(new_metadata, output / pack["data"], old_metadata)
    if not ORIGINAL.exists():
        problems.append(f"{ORIGINAL} is missing: the second build (E8) cannot run")
        return pack, problems
    with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
        same = from_original(old_metadata["files"], (), Path(one), "base-a11y")
        if same["sha256"] != A11Y_BASE_SHA256:
            problems.append("the a11y core's original image does not reproduce 9901e9be: it is not the source")
        again = from_original(old_metadata["files"], drop, Path(two), STEM)
        if again["sha256"] != pack["sha256"]:
            problems.append(f"built from the original: {again['sha256'][:16]}, from 9901e9be: {pack['sha256'][:16]}")
    return pack, problems


def shared_packs() -> tuple[list[dict], list[str]]:
    packs, problems = [], []
    for pack_id, data, data_sha, meta, meta_sha, startup, purpose in SHARED_PACKS:
        for name, want in ((data, data_sha), (meta, meta_sha)):
            path = RESOURCES / name
            if not path.is_file():
                problems.append(f"{path} is missing")
            elif sha256_file(path) != want:
                problems.append(f"{path.name} is not the shipping bytes")
        packs.append({"id": pack_id, "data": f"../resources/{data}", "metadata": f"../resources/{meta}",
                      "bytes": (RESOURCES / data).stat().st_size if (RESOURCES / data).is_file() else None,
                      "sha256": data_sha, "loadAtStartup": startup, "purpose": purpose})
    return packs, problems


def manifest(base: dict, packs: list[dict], core_commit: str) -> dict:
    return {
        "abiVersion": 65537,
        "abiVersionText": "1.1",
        "artifactFiles": {
            "probe.js": "./probe.js",
            "probe.wasm": "./probe.wasm",
            "soffice.data": f"./{base['data']}",
            "soffice.data.js.metadata": f"./{base['metadata']}",
        },
        "capabilities": [name for name, _ in CAPABILITIES],
        "coreCommit": core_commit,
        "expectedCapabilityBits": sum(bit for _, bit in CAPABILITIES),
        "profile": PROFILE,
        "protocolVersion": 1,
        "providerContractVersion": "1.0",
        "resourcePacks": packs,
        "sdkVersion": f"0.6.0-r6-worker+{PROFILE}",
    }


def check_exports(path: Path) -> list[str]:
    names = set(path.read_text(encoding="utf-8").split())
    problems = [f"the export list lacks {n}" for n in EXPORTS_REQUIRED if n not in names]
    problems += [f"the export list carries {n}" for n in EXPORTS_FORBIDDEN if n in names]
    problems += [f"the export list carries an editor symbol {n}" for n in sorted(names)
                 if n.startswith("_oxsdk_editor")]
    return problems


def package(a: argparse.Namespace) -> int:
    problems = []
    if sha256_file(a.worker) != a.worker_sha256:
        problems.append(f"{a.worker} is not the pinned worker {a.worker_sha256[:16]}")
    problems += check_exports(a.exports)
    packs, shared_problems = shared_packs()
    problems += shared_problems
    if problems:
        return report(None, problems)
    out = a.output
    out.mkdir(parents=True, exist_ok=True)
    base, base_problems = build_base(out)
    if base_problems:
        return report(base, base_problems)
    shutil.copyfile(a.loader, out / "probe.js")
    shutil.copyfile(a.wasm, out / "probe.wasm")
    shutil.copyfile(a.worker, out / "sdk-worker.js")
    core_commit = json.loads((V14 / "sdk-manifest.json").read_text(encoding="utf-8"))["coreCommit"]
    (out / "sdk-manifest.json").write_text(
        json.dumps(manifest(base, packs, core_commit), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}: probe.js, probe.wasm, sdk-worker.js, {base['data']}, {base['metadata']}, sdk-manifest.json")
    return report(base, [])


def report(pack: dict | None, problems: list[str]) -> int:
    for p in problems:
        print("FAIL " + p)
    if not problems and pack:
        print(f"ok: {pack['data']} ({pack['bytes']} bytes, {pack['files']} files, sha256 {pack['sha256'][:16]}); "
              f"E8 reconciles; same sha from the a11y core's original image")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--red-drop", metavar="PATH")
    ap.add_argument("--loader", type=Path)
    ap.add_argument("--wasm", type=Path)
    ap.add_argument("--worker", type=Path)
    ap.add_argument("--worker-sha256")
    ap.add_argument("--exports", type=Path)
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    if a.check or a.red_drop:
        drop = (DROP,) + ((a.red_drop,) if a.red_drop else ())
        with tempfile.TemporaryDirectory() as tmp:
            pack, problems = build_base(Path(tmp), drop)
            if a.red_drop:
                # The red case keeps the drop list and the reconciliation apart: dropping a second file must
                # be seen by reconcile(), not explained away by the drop list it was built from.
                new_metadata = json.loads((Path(tmp) / pack["metadata"]).read_text(encoding="utf-8"))
                old_metadata = json.loads(A11Y_BASE_METADATA.read_text(encoding="utf-8"))
                problems = reconcile(new_metadata, Path(tmp) / pack["data"], old_metadata)
        _, shared_problems = shared_packs()
        return report(pack, problems + shared_problems)
    missing = [n for n in ("loader", "wasm", "worker", "worker_sha256", "exports", "output") if not getattr(a, n)]
    if missing:
        ap.error("packaging needs " + ", ".join("--" + m.replace("_", "-") for m in missing))
    return package(a)


if __name__ == "__main__":
    sys.exit(main())
