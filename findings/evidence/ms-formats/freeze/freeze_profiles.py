#!/usr/bin/env python3
"""SPEC-P-ms-formats step 4: freeze e2-editor-v33 and ods-editor-v5 -- after W holds on their development profiles (../w/).

Per profile: every file of build/<...>/profile must equal ../link/SHA256SUMS (the link's own receipt); dist/profiles/<name> must not
exist yet; the profile is copied to dist/profiles/<name> and to build/archive/<name>-<wasm 8>-worker-<worker 8>/ (with
ATTRIBUTION.md); the three copies must then equal file for file.  No page is switched here.  Writes freeze.json beside itself.
  python3 -I freeze_profiles.py dry|write          (from anywhere)
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3] / "wasm_sdk_probe"
SUMS = {line.split()[1]: line.split()[0] for line in (HERE.parent / "link/SHA256SUMS").read_text().splitlines() if line.strip()}
PROFILES = [
    ("e2-editor-v33", "build/e2/editor-v33/profile",
     "The v32 construction (`e2-editor-v32`) with `OXSDK_MS_FORMATS`: `src/document_format.hpp`'s table at the open and save boundaries "
     "(.odt and .docx open, odt and docx save), the MEMFS input under its accepted suffix, the open reply's `format`, capability bits "
     "OPEN_DOCX / SAVE_DOCX. `sdk-worker.js` is `tools/derive_ms_formats_worker.py`'s output: the frozen v32 worker plus "
     "`tests/v33-worker-delta.json`. The manifest is `tools/build_ms_formats_profile.py`'s development assembly (under `build/`)."),
    ("ods-editor-v5", "build/ods/editor-v5/profile",
     "The v4 construction (`ods-editor-v4`) with `OXSDK_MS_FORMATS`: the same table (.odt, .ods and .xlsx open; ods and xlsx save), "
     "the open reply's `format`, capability bits OPEN_XLSX / SAVE_XLSX. The two pack files are ods-editor-v4's bytes. `sdk-worker.js` is "
     "`tools/derive_ms_formats_worker.py`'s output: the frozen v4 worker plus `tests/ods-v5-worker-delta.json`. The manifest is the "
     "development assembly (under `build/`)."),
]


def files(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def main(mode):
    record = {"mode": mode, "profiles": []}
    problems = []
    plans = []
    for name, build, what in PROFILES:
        source = PROJECT / build
        have = files(source)
        expected = {k[len(build) + 1:]: v for k, v in SUMS.items() if k.startswith(build + "/")}
        if have != expected:
            problems.append(f"{name}: {build} differs from the link's SHA256SUMS")
        dist = PROJECT / "dist/profiles" / name
        if dist.exists():
            problems.append(f"{name}: {dist} exists already")
        archive = PROJECT / "build/archive" / f"{name}-{have['probe.wasm'][:8]}-worker-{have['sdk-worker.js'][:8]}"
        if archive.exists():
            problems.append(f"{name}: {archive} exists already")
        plans.append((name, source, dist, archive, what, have))
        record["profiles"].append({"profile": name, "source": build, "dist": str(dist.relative_to(PROJECT)),
                                   "archive": str(archive.relative_to(PROJECT)), "files": have})
    record["problems"] = problems
    if mode == "write" and not problems:
        for name, source, dist, archive, what, have in plans:
            shutil.copytree(source, dist)
            shutil.copytree(source, archive)
            (archive / "ATTRIBUTION.md").write_text(
                f"# {name}\n\nLinked 2026-11-03 21:10-21:15 +0800 by the agent at the owner's request, `tools/link_ms_formats_owner.sh` "
                f"(no core build). Receipts: `findings/evidence/ms-formats/link/` (the log and SHA256SUMS). Spec "
                f"`specs/SPEC-P-ms-formats.md` sections 5, 6, 9 and 10.\n\n{what} Frozen after W held on both browsers on this "
                f"development profile (`findings/evidence/ms-formats/w/`).\n")
            copies = {"dist": files(dist), "archive": {k: v for k, v in files(archive).items() if k != "ATTRIBUTION.md"}}
            if copies["dist"] != have or copies["archive"] != have:
                problems.append(f"{name}: a copy differs from the source")
        record["written"] = not problems
    (HERE / f"freeze-{mode}.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"mode": mode, "problems": problems, "written": record.get("written")}, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("dry", "write") else sys.exit("dry|write")))
