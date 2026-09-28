#!/usr/bin/env python3
"""Package the shipped editor into the `litecore` app: `<app>/engine/`.

specs/SPEC-M3-asset-delivery.md section 3.1.  The files are the editor's
closure as `probe_m3_assets.closure()` derives it from dist/ (the page's static
import graph, the one hard-coded workerUrl, that worker's manifest) -- there is
no second list.  Each file is written gzip -9 with mtime 0, so the same input
gives the same bytes:

  engine/files/<path>.gz
  engine/MANIFEST.json     per path: bytes, sha256, gzBytes, gzSha256; buildId;
                           where it came from

buildId = the first 16 hex of the sha256 of the canonical JSON {path: sha256}
of the DECODED files: it names the content, not the gzip bytes.

  package_m3_engine.py [--app DIR]

Reads dist/, never writes it.  Replaces `<app>/engine/` whole: builds
`engine.new/` beside it, then swaps.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_m3_assets import PAGE_MODULE, closure  # noqa: E402
from probe_m3_gate0_coep import DIST, sha256_file, utc_now  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV  # noqa: E402

SCHEMA = "litecore-engine/1"
# The largest encoded size Firefox 156 was measured to keep in its HTTP cache
# (45 MB kept, 60 MB not; findings/evidence/m3-assets/README.md, X1).  A file
# over it would silently lose the second-open benefit in Firefox, so packaging
# refuses instead.  The shipped wasm is 40.9 MB of gzip.
MAX_GZ_BYTES = 45_000_000


def build_id(files: dict[str, dict[str, Any]]) -> str:
    canonical = json.dumps({path: entry["sha256"] for path, entry in files.items()},
                           sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def package(app: Path, dist: Path = DIST) -> dict[str, Any]:
    derived = closure(dist)
    staging = app / "engine.new"
    if staging.exists():
        shutil.rmtree(staging)
    files: dict[str, dict[str, Any]] = {}
    for item in derived["files"]:
        path = item["path"]
        raw = (dist / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise RuntimeError(f"{path} changed while packaging")
        packed = gzip.compress(raw, compresslevel=9, mtime=0)
        if len(packed) > MAX_GZ_BYTES:
            raise RuntimeError(f"{path}: {len(packed)} bytes of gzip, over the {MAX_GZ_BYTES} measured to stay"
                               " in Firefox's cache (see MAX_GZ_BYTES)")
        target = staging / "files" / (path + ".gz")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(packed)
        files[path] = {"bytes": len(raw), "sha256": item["sha256"],
                       "gzBytes": len(packed), "gzSha256": hashlib.sha256(packed).hexdigest()}
    manifest = {
        "schema": SCHEMA,
        "buildId": build_id(files),
        "source": {
            # Relative: the manifest ships in the release archive.
            "dist": "study_LiteCore/" + str(dist.relative_to(dist.parents[1])),
            "page": {PAGE_MODULE: sha256_file(dist / PAGE_MODULE)},
            "profile": derived["worker"]["profile"],
            "wasmSha256": next(f["sha256"] for p, f in files.items() if p.endswith("/probe.wasm")),
            "declaredNotLoaded": derived["worker"]["declaredNotLoaded"],
            "tool": sha256_file(Path(__file__)),
            "packagedAt": utc_now(),
        },
        "totals": {"files": len(files), "bytes": sum(f["bytes"] for f in files.values()),
                   "gzBytes": sum(f["gzBytes"] for f in files.values())},
        "files": dict(sorted(files.items())),
    }
    (staging / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    # Two renames, then the delete: requests see the old engine or the new one,
    # except for the moment between the renames (404 from the route).
    current, retired = app / "engine", app / "engine.old"
    if retired.exists():
        shutil.rmtree(retired)
    if current.exists():
        current.rename(retired)
    staging.rename(current)
    if retired.exists():
        shutil.rmtree(retired)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app", type=Path, default=DEFAULT_DDEV)
    args = parser.parse_args()
    manifest = package(args.app)
    print(f"{args.app / 'engine'}  buildId {manifest['buildId']}  "
          f"{manifest['totals']['files']} files  {manifest['totals']['bytes']} -> {manifest['totals']['gzBytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
