#!/usr/bin/env python3
"""M3 release archive -- what an admin would install (SPEC-M3-install-elsewhere §3.1).

  build_m3_release.py [--commit REV] [--record PATH]
                                         build twice, compare, write archive + record
                                         (--record: somewhere other than release.json,
                                         which an installed instance's binding reads)

Members, under `litecore/`: the host commit's tracked files below appinfo/ lib/
templates/ js/, read from git objects (not the working tree), plus
engine/MANIFEST.json and every packaged file it names (package_m3_engine.
engine_members: one per coding, .gz and .zst), read from the host's engine/
(untracked; package_m3_engine.py wrote it and assets' K0/Z0 checked it).  Deterministic: sorted names, one fixed mtime, uid/gid 0, modes 755/644,
a gzip header with mtime 0 and no file name.

The archive goes to wasm_sdk_probe/build/release/ (not in git, about 60 MB);
findings/evidence/m3-install/release.json binds it by sha256 and lists every
member's sha256 -- the list the runners bind an installed tree to
(check_m3_skeleton_open.host_binding).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_skeleton_open import DEFAULT_DDEV, RELEASE_RECORD  # noqa: E402
from package_m3_engine import engine_members  # noqa: E402
from probe_m3_gate0_coep import utc_now  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
OUT = PROJECT / "build" / "release"
PARTS = ("appinfo", "lib", "templates", "js")
TOP = "litecore"
MTIME = 1790640000   # 2026-09-29T00:00:00Z


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True).stdout


def tracked(repo: Path, commit: str) -> dict[str, dict[str, Any]]:
    """Every tracked file of `commit` under PARTS: git mode and bytes."""
    out = {}
    for line in git(repo, "ls-tree", "-r", commit, "--", *PARTS).decode().splitlines():
        meta, name = line.split("\t", 1)
        mode, kind, blob = meta.split()
        out[name] = {"mode": mode, "kind": kind, "blob": blob,
                     "bytes": git(repo, "cat-file", "blob", blob) if kind == "blob" else b""}
    return out


def collect(repo: Path, commit: str) -> tuple[dict[str, bytes], dict[str, Any]]:
    """The member bytes, keyed by path under the app directory."""
    files = {name: entry["bytes"] for name, entry in tracked(repo, commit).items()}
    raw = (repo / "engine" / "MANIFEST.json").read_bytes()
    manifest = json.loads(raw)
    files["engine/MANIFEST.json"] = raw
    for name in engine_members(manifest):
        files[name] = (repo / name).read_bytes()
    return files, manifest


def build(files: dict[str, bytes]) -> bytes:
    directories = sorted({"/".join(name.split("/")[:i]) for name in files
                          for i in range(1, name.count("/") + 1)})
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as archive:
        top = tarfile.TarInfo(TOP)
        top.type, top.mode, top.mtime = tarfile.DIRTYPE, 0o755, MTIME
        archive.addfile(top)
        for name in sorted(directories + list(files)):
            info = tarfile.TarInfo(f"{TOP}/{name}")
            info.mtime, info.uid, info.gid, info.uname, info.gname = MTIME, 0, 0, "", ""
            if name in files:
                info.mode, info.size = 0o644, len(files[name])
                archive.addfile(info, io.BytesIO(files[name]))
            else:
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                archive.addfile(info)
    packed = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=packed, mtime=0, compresslevel=9) as out:
        out.write(raw.getvalue())
    return packed.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--record", type=Path, default=RELEASE_RECORD)
    args = parser.parse_args()
    commit = git(args.repo, "rev-parse", args.commit).decode().strip()
    subject = git(args.repo, "log", "-1", "--format=%s", commit).decode().strip()
    files, manifest = collect(args.repo, commit)
    first, second = build(files), build(collect(args.repo, commit)[0])
    version = re.search(rb"<version>([^<]+)</version>", files["appinfo/info.xml"]).group(1).decode()
    OUT.mkdir(parents=True, exist_ok=True)
    archive = OUT / f"litecore-{version}.tar.gz"
    archive.write_bytes(first)
    record = {
        "schema": "litecore-release/1", "builtAt": utc_now(), "tool": str(Path(__file__).relative_to(REPO)),
        "sourceRepo": str(args.repo), "commit": commit, "subject": subject, "version": version,
        "buildId": manifest.get("buildId"),
        "archive": {"path": str(archive.relative_to(REPO)), "sha256": hashlib.sha256(first).hexdigest(),
                    "bytes": len(first)},
        "secondBuildSha256": hashlib.sha256(second).hexdigest(),
        "members": {name: hashlib.sha256(body).hexdigest() for name, body in sorted(files.items())},
    }
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({k: record[k] for k in ("commit", "version", "buildId", "archive", "secondBuildSha256")}
                     | {"members": len(record["members"])}, indent=1))
    return 0 if record["secondBuildSha256"] == record["archive"]["sha256"] else 1


if __name__ == "__main__":
    sys.exit(main())
