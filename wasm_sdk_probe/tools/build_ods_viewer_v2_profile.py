#!/usr/bin/env python3
"""ods-viewer-v2, the spreadsheet viewer's second engine (SPEC-M4-viewer-v2 §3.5, E8′).

THE BASE PACK.  v1's was e2-editor-v14's base pack `9901e9be…` minus one file, and E8 required every
other file to be byte-identical.  v2's core is a new tree with DB connectivity on, so its filesystem
image is not v1's and that E8 cannot hold.  What carries over is the PROCEDURE: v14's base pack is
`build_r5_profiles.classify()`'s "base" group of the core image (a property of path prefixes and font
basenames, not of the core), and that is checked here every time -- the same procedure on
build-a11y-gate0's image must reproduce 9901e9be byte for byte (the positive control; measured
2026-10-21: 1,489 files, it does).  v2's base pack is the same group of v2's image minus
35-lang-normalize.conf (finding 114), exactly as v1's.

WHAT CHANGED against v1's base is not judged here, it is RECORDED -- added, removed and changed file
names, with sizes -- in the report (`--report`), and read before the link is handed over (§3.5).

THE OTHER PACKS are v1's, by path: `cjk-sub-e10` (at startup) and `fallback-fonts-r5` (declared).

THE MANIFEST is v1's shape plus `part-info`, and `form-controls` when the core's own
config_features.h says HAVE_FEATURE_DBCONNECTIVITY 1 -- the same header the engine was compiled
against (sdk_api.cpp), so the worker's bit check at init holds them together.

  build_ods_viewer_v2_profile.py --check [--core DIR] [--report PATH]
      build the base pack in a scratch directory, run the positive control, diff against v1; writes
      only --report
  build_ods_viewer_v2_profile.py --red-drop PATH [--core DIR]
      red case: also drop PATH; the diff against v1 must show it removed
  build_ods_viewer_v2_profile.py --core DIR --loader L --wasm W --worker K --worker-sha256 S
                                 --exports X --output DIR [--report PATH]
      package the profile from the link's outputs (the Makefile's packaging rule)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_ods_viewer_profile as v1  # noqa: E402
from build_r5_profiles import classify, create_pack, sha256_file  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
PROFILE = "ods-viewer-v2"
DEFAULT_CORE = HERE.parent / "wasm-lite/build-ods-viewer-v2"
REFERENCE_CORE = HERE.parent / "wasm-lite/build-a11y-gate0"
V1 = HERE / "dist/profiles/ods-viewer-v1"
V1_BASE_DATA = V1 / "base-a11y-no35.6f7424a1c1427ad7.data"
V1_BASE_METADATA = V1 / "base-a11y-no35.8aae00e7cef956a0.metadata"
STEM = "base-viewer-v2-no35"
CORE_COMMIT = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"  # libreoffice-26-8, plus wasm-lite/patches
CAPABILITIES_V2 = v1.CAPABILITIES + [("part-info", 1 << 14)]
FORM_CONTROLS = ("form-controls", 1 << 15)
EXPORTS_REQUIRED = v1.EXPORTS_REQUIRED + ["_oxsdk_document_part_info"]


def image(core: Path) -> tuple[Path, dict]:
    program = core / "instdir" / "program"
    data, meta = program / "soffice.data", program / "soffice.data.js.metadata"
    if not data.is_file() or not meta.is_file():
        raise SystemExit(f"{core} has no filesystem image ({data.name}, {meta.name})")
    return data, json.loads(meta.read_text(encoding="utf-8"))


def base_group(core: Path, drop: tuple[str, ...]) -> tuple[Path, list[dict]]:
    data, meta = image(core)
    base = classify(meta["files"])["base"]
    names = [e["filename"] for e in base]
    for name in drop:
        if names.count(name) != 1:
            raise SystemExit(f"{core.name}: {name} is in the base group {names.count(name)} times, not once")
    return data, [{"filename": e["filename"], "start": e["start"], "end": e["end"]}
                  for e in base if e["filename"] not in drop]


def positive_control() -> list[str]:
    """The procedure is v14's: on gate0's image it gives 9901e9be."""
    data, entries = base_group(REFERENCE_CORE, ())
    with tempfile.TemporaryDirectory() as tmp:
        pack = create_pack(data, entries, Path(tmp), "base-gate0")
    if pack["sha256"] != v1.A11Y_BASE_SHA256:
        return [f"classify() on {REFERENCE_CORE.name} gives {pack['sha256'][:16]}, not 9901e9be: "
                f"the procedure is not the one v1's base came from"]
    return []


def slices(metadata: dict, data: Path) -> dict[str, tuple[int, str]]:
    out = {}
    with data.open("rb") as handle:
        for e in metadata["files"]:
            handle.seek(e["start"])
            body = handle.read(e["end"] - e["start"])
            out[e["filename"]] = (len(body), hashlib.sha256(body).hexdigest())
    return out


def diff_against_v1(metadata: dict, data: Path) -> dict:
    old = slices(json.loads(V1_BASE_METADATA.read_text(encoding="utf-8")), V1_BASE_DATA)
    new = slices(metadata, data)
    changed = sorted(n for n in set(old) & set(new) if old[n] != new[n])
    return {
        "v1Files": len(old), "v2Files": len(new),
        "added": [{"filename": n, "bytes": new[n][0]} for n in sorted(set(new) - set(old))],
        "removed": [{"filename": n, "bytes": old[n][0]} for n in sorted(set(old) - set(new))],
        "changed": [{"filename": n, "v1Bytes": old[n][0], "v2Bytes": new[n][0]} for n in changed],
        "unchanged": len(set(old) & set(new)) - len(changed),
    }


def core_has_forms(core: Path) -> bool:
    header = core / "config_host" / "config_features.h"
    match = re.search(r"^#define HAVE_FEATURE_DBCONNECTIVITY\s+(\d)", header.read_text(), re.M)
    if not match:
        raise SystemExit(f"{header} does not define HAVE_FEATURE_DBCONNECTIVITY")
    return match.group(1) == "1"


def capabilities(core: Path) -> list[tuple[str, int]]:
    return CAPABILITIES_V2 + ([FORM_CONTROLS] if core_has_forms(core) else [])


def build_base(core: Path, output: Path, drop: tuple[str, ...] = (v1.DROP,)) -> tuple[dict, dict, list[str]]:
    problems = positive_control()
    data, entries = base_group(core, drop)
    pack = create_pack(data, entries, output, STEM)
    metadata = json.loads((output / pack["metadata"]).read_text(encoding="utf-8"))
    return pack, diff_against_v1(metadata, output / pack["data"]), problems


def manifest(base: dict, packs: list[dict], caps: list[tuple[str, int]]) -> dict:
    out = v1.manifest(base, packs, CORE_COMMIT)
    out["capabilities"] = [name for name, _ in caps]
    out["expectedCapabilityBits"] = sum(bit for _, bit in caps)
    out["profile"] = PROFILE
    out["sdkVersion"] = f"0.6.0-r6-worker+{PROFILE}"
    return out


def check_exports(path: Path) -> list[str]:
    names = set(path.read_text(encoding="utf-8").split())
    problems = [f"the export list lacks {n}" for n in EXPORTS_REQUIRED if n not in names]
    problems += [f"the export list carries {n}" for n in v1.EXPORTS_FORBIDDEN if n in names]
    problems += [f"the export list carries an editor symbol {n}" for n in sorted(names)
                 if n.startswith("_oxsdk_editor")]
    return problems


def write_report(path: Path | None, body: dict) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summary(core: Path, pack: dict, diff: dict, problems: list[str]) -> dict:
    return {"core": str(core), "profile": PROFILE, "basePack": pack,
            "capabilities": [name for name, _ in capabilities(core)],
            "positiveControl": "9901e9be reproduced from build-a11y-gate0" if not problems else problems,
            "diffAgainstV1Base": diff, "problems": problems}


def package(a: argparse.Namespace) -> int:
    problems = []
    if sha256_file(a.worker) != a.worker_sha256:
        problems.append(f"{a.worker} is not the pinned worker {a.worker_sha256[:16]}")
    problems += check_exports(a.exports)
    packs, shared_problems = v1.shared_packs()
    problems += shared_problems
    if problems:
        return report(None, problems)
    out = a.output
    out.mkdir(parents=True, exist_ok=True)
    base, diff, base_problems = build_base(a.core, out)
    write_report(a.report, summary(a.core, base, diff, base_problems))
    if base_problems:
        return report(base, base_problems)
    shutil.copyfile(a.loader, out / "probe.js")
    shutil.copyfile(a.wasm, out / "probe.wasm")
    shutil.copyfile(a.worker, out / "sdk-worker.js")
    (out / "sdk-manifest.json").write_text(
        json.dumps(manifest(base, packs, capabilities(a.core)), indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(f"wrote {out}: probe.js, probe.wasm, sdk-worker.js, {base['data']}, {base['metadata']}, sdk-manifest.json")
    return report(base, [], diff)


def report(pack: dict | None, problems: list[str], diff: dict | None = None) -> int:
    for p in problems:
        print("FAIL " + p)
    if not problems and pack:
        print(f"ok: {pack['data']} ({pack['bytes']} bytes, {pack['files']} files, sha256 {pack['sha256'][:16]}); "
              f"the procedure reproduces 9901e9be on build-a11y-gate0")
        if diff:
            print(f"against v1's base: {len(diff['added'])} added, {len(diff['removed'])} removed, "
                  f"{len(diff['changed'])} changed, {diff['unchanged']} unchanged (recorded, not judged)")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--red-drop", metavar="PATH")
    ap.add_argument("--core", type=Path, default=DEFAULT_CORE)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--loader", type=Path)
    ap.add_argument("--wasm", type=Path)
    ap.add_argument("--worker", type=Path)
    ap.add_argument("--worker-sha256")
    ap.add_argument("--exports", type=Path)
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    if a.check or a.red_drop:
        drop = (v1.DROP,) + ((a.red_drop,) if a.red_drop else ())
        with tempfile.TemporaryDirectory() as tmp:
            pack, diff, problems = build_base(a.core, Path(tmp), drop)
        if a.red_drop and not any(r["filename"] == a.red_drop for r in diff["removed"]):
            problems.append(f"red case: {a.red_drop} was dropped and the diff against v1 does not show it")
        elif a.red_drop:
            print(f"red case seen: {a.red_drop} is in the diff's removed list")
        _, shared_problems = v1.shared_packs()
        write_report(a.report, summary(a.core, pack, diff, problems + shared_problems))
        return report(pack, problems + shared_problems, diff)
    missing = [n for n in ("loader", "wasm", "worker", "worker_sha256", "exports", "output") if not getattr(a, n)]
    if missing:
        ap.error("packaging needs " + ", ".join("--" + m.replace("_", "-") for m in missing))
    return package(a)


if __name__ == "__main__":
    sys.exit(main())
