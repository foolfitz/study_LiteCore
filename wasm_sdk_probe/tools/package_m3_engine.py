#!/usr/bin/env python3
"""Package the shipped editor into the `litecore` app: `<app>/engine/`.

specs/SPEC-M3-asset-delivery.md section 3.1.  The files are the editor's
closure as `probe_m3_assets.closure()` derives it from dist/ (the page's static
import graph, the one hard-coded workerUrl, that worker's manifest) -- there is
no second list.  Each file is written twice, gzip -9 with mtime 0 and zstd
level 19 (specs/SPEC-M3-zstd.md section 3.1), so the same input gives the same
bytes for a given zlib and libzstd:

  engine/files/<path>.gz
  engine/files/<path>.zst
  engine/MANIFEST.json     per path: bytes, sha256, gzBytes, gzSha256, zstBytes,
                           zstSha256; buildId; where it came from

buildId = the first 16 hex of the sha256 of the canonical JSON {path: sha256}
of the DECODED files: it names the content, not the gzip or zstd bytes.

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
from compression import zstd
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_m3_assets import PAGE_MODULE, closure  # noqa: E402
from probe_m3_gate0_coep import DIST, sha256_file, utc_now  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV  # noqa: E402

SCHEMA = "litecore-engine/2"
# The largest encoded size Firefox 156 was measured to keep in its HTTP cache
# (45 MB kept, 60 MB not; findings/evidence/m3-assets/README.md, X1).  A file
# over it would silently lose the second-open benefit in Firefox, so packaging
# refuses instead.  The shipped wasm is 40.9 MB of gzip.
MAX_GZ_BYTES = 45_000_000
# Firefox and Chrome take zstd (SPEC-M3-zstd), so the same cap holds for it.
MAX_ZST_BYTES = MAX_GZ_BYTES
# Level 19 is the highest whose window is 2^23 = 8 MiB, the limit of the `zstd`
# content coding (RFC 9659); levels 20+ and long mode go over it.
ZSTD_LEVEL = 19
MAX_ZSTD_WINDOW = 1 << 23
# Every coding the engine carries: its file suffix and its manifest fields.  The
# release builder and install-elsewhere derive the engine's files from a
# manifest through this table, never from a suffix of their own (SPEC-M3-zstd
# §7, review item 1: a .gz-only release of a zstd host is dead in both browsers).
CODINGS = {"gzip": {"suffix": ".gz", "bytes": "gzBytes", "sha256": "gzSha256"},
           "zstd": {"suffix": ".zst", "bytes": "zstBytes", "sha256": "zstSha256"}}


def engine_members(manifest: dict[str, Any]) -> dict[str, str]:
    """{path under the app: sha256} for every packaged file the manifest names:
    one per coding field an entry carries.  An entry with a hash field this
    table does not know is refused, not skipped."""
    known = {c["sha256"] for c in CODINGS.values()} | {"sha256"}
    members = {}
    for path, entry in manifest["files"].items():
        unknown = [k for k in entry if k.endswith("Sha256") and k not in known]
        if unknown:
            raise RuntimeError(f"{path}: manifest fields {unknown} name no coding in CODINGS")
        for coding in CODINGS.values():
            if coding["sha256"] in entry:
                members[f"engine/files/{path}{coding['suffix']}"] = entry[coding["sha256"]]
    return members


def zstd_frame(body: bytes) -> dict[str, Any]:
    """The first zstd frame's header, read from the bytes (RFC 8878 3.1.1):
    its window size, whether it is single-segment, its declared content size,
    and how many bytes of `body` it spans (the rest is trailing)."""
    if len(body) < 6 or int.from_bytes(body[:4], "little") != 0xFD2FB528:
        return {"error": "not a zstd frame"}
    descriptor = body[4]
    single = bool(descriptor & 0x20)
    fcs_flag = descriptor >> 6
    position = 5
    window = None
    if not single:
        exponent, mantissa = body[position] >> 3, body[position] & 7
        base = 1 << (10 + exponent)
        window = base + (base >> 3) * mantissa
        position += 1
    position += (0, 1, 2, 4)[descriptor & 3]  # dictionary id
    fcs_size = (1 if single else 0, 2, 4, 8)[fcs_flag]
    content = None
    if fcs_size:
        content = int.from_bytes(body[position:position + fcs_size], "little") + (256 if fcs_size == 2 else 0)
    if single:
        window = content
    try:
        spans = zstd.get_frame_size(body)
    except Exception as error:  # noqa: BLE001 -- recorded
        return {"error": f"frame size: {error}"}
    return {"window": window, "singleSegment": single, "contentSize": content, "frameBytes": spans,
            "trailingBytes": len(body) - spans}


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
        squeezed = zstd.compress(raw, level=ZSTD_LEVEL)
        if len(squeezed) > MAX_ZST_BYTES:
            raise RuntimeError(f"{path}: {len(squeezed)} bytes of zstd, over {MAX_ZST_BYTES} (see MAX_ZST_BYTES)")
        frame = zstd_frame(squeezed)
        if frame.get("window") is None or frame["window"] > MAX_ZSTD_WINDOW or frame.get("trailingBytes"):
            raise RuntimeError(f"{path}: zstd frame {frame} is not one frame within {MAX_ZSTD_WINDOW}")
        target = staging / "files" / (path + ".gz")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(packed)
        (staging / "files" / (path + ".zst")).write_bytes(squeezed)
        files[path] = {"bytes": len(raw), "sha256": item["sha256"],
                       "gzBytes": len(packed), "gzSha256": hashlib.sha256(packed).hexdigest(),
                       "zstBytes": len(squeezed), "zstSha256": hashlib.sha256(squeezed).hexdigest()}
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
            "zstd": {"level": ZSTD_LEVEL, "libzstd": ".".join(map(str, zstd.zstd_version_info))},
            "tool": sha256_file(Path(__file__)),
            "packagedAt": utc_now(),
        },
        "totals": {"files": len(files), "bytes": sum(f["bytes"] for f in files.values()),
                   "gzBytes": sum(f["gzBytes"] for f in files.values()),
                   "zstBytes": sum(f["zstBytes"] for f in files.values())},
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
          f"{manifest['totals']['files']} files  {manifest['totals']['bytes']} -> {manifest['totals']['gzBytes']} gzip,"
          f" {manifest['totals']['zstBytes']} zstd bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
