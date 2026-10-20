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
from probe_m3_assets import PAGE_MODULE, PAGES, closure, page_closure  # noqa: E402
from probe_m3_gate0_coep import DIST, sha256_file, utc_now  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV  # noqa: E402

# Schema 3 (SPEC-M4-ods-in-nextcloud §3.5): the package carries a PAGE TABLE,
# `source.pages`, one entry per shipped page with its module, its engine
# profile and that engine's wasm sha256; the files are the union of the pages'
# closures.  A schema-3 manifest without every page in PAGES is refused by the
# host's controller and by validate_manifest() here.
SCHEMA = "litecore-engine/3"
# The largest gzip response Firefox keeps in its HTTP cache, MEASURED on Firefox
# 157 with the viewer engine's own 47,987,215-byte gzip wasm (SPEC-M4 addendum 2,
# findings/evidence/m4-ods/d5-gzip-retention/report-2026-10-20T114325Z.json):
# 52,428,800 kept, 53,000,000 not -- the same number as Firefox's documented
# default browser.cache.disk.max_entry_size, 51,200 KiB.  A file over it would
# silently lose the second-open benefit in Firefox, so packaging refuses instead.
# This replaces the 45,000,000 of the X1 measurement (Firefox 156, 45 MB kept,
# 60 MB not) with a tighter measurement, not a looser rule (K0-5, re-judged with
# this reason).  The editor's wasm is 40.9 MB of gzip, the viewer's 48.0 MB.
MAX_GZ_BYTES = 52_428_800
# zstd: both browsers were measured to keep 45 MB (SPEC-M3-zstd); unchanged.
MAX_ZST_BYTES = 45_000_000
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


def check_caps(path: str, gz_bytes: int, zst_bytes: int) -> None:
    """K0-5 / Z0-3 / SPEC-M4 H5: refuse a file either browser cache would not keep."""
    if gz_bytes > MAX_GZ_BYTES:
        raise RuntimeError(f"{path}: {gz_bytes} bytes of gzip, over the {MAX_GZ_BYTES} measured to stay"
                           " in Firefox's cache (see MAX_GZ_BYTES)")
    if zst_bytes > MAX_ZST_BYTES:
        raise RuntimeError(f"{path}: {zst_bytes} bytes of zstd, over {MAX_ZST_BYTES} (see MAX_ZST_BYTES)")


def validate_manifest(manifest: dict[str, Any], pages: dict[str, str] = PAGES, only_pages: bool = False) -> list[str]:
    """What a schema-3 manifest must say (SPEC-M4 §3.5, H5), as a list of
    problems; empty when it holds.  Read by the host's controller in PHP
    (EditorController::engine) with the same conditions.  `only_pages` leaves
    the schema, build id and caps to the clauses that already own them (K0-3,
    K0-5, Z0-3, Z0-4) and judges the page table alone (H5-1)."""
    bad = []
    files = manifest.get("files")
    if not only_pages:
        if manifest.get("schema") != SCHEMA:
            bad.append(f"schema {manifest.get('schema')!r}, want {SCHEMA}")
    if not isinstance(files, dict) or not files:
        return bad + ["no files"]
    if not only_pages and (not isinstance(manifest.get("buildId"), str) or manifest["buildId"] != build_id(files)):
        bad.append(f"buildId {manifest.get('buildId')!r} is not the files'")
    table = (manifest.get("source") or {}).get("pages")
    if not isinstance(table, dict) or set(table) != set(pages):
        bad.append(f"source.pages {sorted(table) if isinstance(table, dict) else table!r}, want {sorted(pages)}")
        table = table if isinstance(table, dict) else {}
    shas = {entry.get("sha256") for entry in files.values()}
    for html, entry in table.items():
        if html not in files:
            bad.append(f"{html}: the page is not among the files")
        if not isinstance(entry, dict) or entry.get("module") != pages.get(html):
            bad.append(f"{html}: module {entry.get('module') if isinstance(entry, dict) else entry!r}, want {pages.get(html)}")
            continue
        if entry.get("module") not in files:
            bad.append(f"{html}: its module {entry['module']} is not among the files")
        if not isinstance(entry.get("profile"), str) or not entry["profile"]:
            bad.append(f"{html}: no profile")
        if entry.get("wasmSha256") not in shas:
            bad.append(f"{html}: wasmSha256 {str(entry.get('wasmSha256'))[:12]} names no packaged file")
    if only_pages:
        return bad
    for path, entry in files.items():
        if not isinstance(entry.get("gzBytes"), int) or entry["gzBytes"] > MAX_GZ_BYTES:
            bad.append(f"{path}: gzBytes {entry.get('gzBytes')} over {MAX_GZ_BYTES}")
        if not isinstance(entry.get("zstBytes"), int) or entry["zstBytes"] > MAX_ZST_BYTES:
            bad.append(f"{path}: zstBytes {entry.get('zstBytes')} over {MAX_ZST_BYTES}")
    return bad


def page_table(derived: dict[str, Any], files: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    table = {}
    for html, page in derived["pages"].items():
        worker_dir = str(Path(page["worker"]["manifest"]).parent)
        table[html] = {
            "module": page["module"],
            "moduleSha256": files[page["module"]]["sha256"],
            "profile": page["worker"]["profile"],
            "wasmSha256": files[f"{worker_dir}/probe.wasm"]["sha256"],
            "declaredNotLoaded": page["worker"]["declaredNotLoaded"],
        }
    return table


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
        squeezed = zstd.compress(raw, level=ZSTD_LEVEL)
        check_caps(path, len(packed), len(squeezed))
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
            # Schema 3: one entry per shipped page (SPEC-M4 §3.5).
            "pages": page_table(derived, files),
            # The editor's entry, as schema 2 wrote it: older readers look here.
            "page": {PAGE_MODULE: sha256_file(dist / PAGE_MODULE)},
            "profile": derived["worker"]["profile"],
            "wasmSha256": files[str(Path(derived["worker"]["manifest"]).parent) + "/probe.wasm"]["sha256"],
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
    problems = validate_manifest(manifest)
    if problems:
        shutil.rmtree(staging)
        raise RuntimeError(f"the manifest this tool just built does not hold: {problems}")
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


# -------------------------------------------------------------- selftest --
def selftest() -> int:
    """SPEC-M4 H5's red cases, on synthetic input: a file over each cap, a page
    with zero or two worker literals, and a one-page or schema-2 manifest."""
    import tempfile
    results = []

    def expect_raise(label, fn):
        try:
            fn()
        except RuntimeError as error:
            results.append((label, True, str(error)[:90]))
        else:
            results.append((label, False, "no refusal"))

    results.append(("gzip exactly at the cap is accepted", not _raises(lambda: check_caps("x", MAX_GZ_BYTES, 1)), ""))
    expect_raise("gzip one byte over the cap", lambda: check_caps("x", MAX_GZ_BYTES + 1, 1))
    expect_raise("zstd one byte over the cap", lambda: check_caps("x", 1, MAX_ZST_BYTES + 1))
    with tempfile.TemporaryDirectory(prefix="pkg-selftest-") as scratch:
        root = Path(scratch)
        (root / "profiles" / "p").mkdir(parents=True)
        (root / "profiles" / "p" / "sdk-manifest.json").write_text(json.dumps({"profile": "p", "artifactFiles": {}}))
        (root / "profiles" / "p" / "sdk-worker.js").write_text("// worker")
        (root / "none.html").write_text("<html></html>")
        (root / "none-app.js").write_text("const a = 1;\n")
        expect_raise("a page with zero worker literals", lambda: page_closure(root, "none.html", "none-app.js"))
        (root / "two.html").write_text("<html></html>")
        (root / "two-app.js").write_text('const a = { workerUrl: "./profiles/p/sdk-worker.js" };\n'
                                          '// workerUrl: "./profiles/q/sdk-worker.js"\n')
        expect_raise("a page with two worker literals (one in a comment)", lambda: page_closure(root, "two.html", "two-app.js"))
        (root / "one.html").write_text("<html></html>")
        (root / "one-app.js").write_text('const a = { workerUrl: "./profiles/p/sdk-worker.js" };\n')
        one = page_closure(root, "one.html", "one-app.js")
        results.append(("a page with one worker literal closes", one["worker"]["profile"] == "p"
                        and set(one["files"]) >= {"one.html", "one-app.js", "profiles/p/sdk-worker.js"}, one["files"]))
    entry = lambda sha: {"bytes": 1, "sha256": sha, "gzBytes": 1, "gzSha256": "g", "zstBytes": 1, "zstSha256": "z"}  # noqa: E731
    files = {"e2-editor.html": entry("a"), "e2-editor-app.js": entry("b"), "ods-viewer.html": entry("c"),
             "ods-viewer-app.js": entry("d"), "profiles/e/probe.wasm": entry("w1"), "profiles/v/probe.wasm": entry("w2")}
    good = {"schema": SCHEMA, "buildId": build_id(files), "files": files, "source": {"pages": {
        "e2-editor.html": {"module": "e2-editor-app.js", "profile": "e", "wasmSha256": "w1"},
        "ods-viewer.html": {"module": "ods-viewer-app.js", "profile": "v", "wasmSha256": "w2"}}}}
    results.append(("a two-page schema-3 manifest holds", validate_manifest(good) == [], validate_manifest(good)))
    import copy
    for label, edit in [
        ("a one-page manifest under schema 3", lambda m: m["source"]["pages"].pop("ods-viewer.html")),
        ("a schema-2 manifest", lambda m: m.update(schema="litecore-engine/2")),
        ("a page whose wasm is not packaged", lambda m: m["source"]["pages"]["ods-viewer.html"].update(wasmSha256="nope")),
        ("a page whose module is another file", lambda m: m["source"]["pages"]["ods-viewer.html"].update(module="e2-editor-app.js")),
        ("a build id that is not the files'", lambda m: m.update(buildId="f" * 16)),
        ("a file over the gzip cap in the manifest", lambda m: m["files"]["profiles/v/probe.wasm"].update(gzBytes=MAX_GZ_BYTES + 1)),
    ]:
        broken = copy.deepcopy(good)
        edit(broken)
        problems = validate_manifest(broken)
        results.append((label, bool(problems), problems[:2]))
    for label, ok, detail in results:
        print(("PASS " if ok else "FAIL ") + label + (f"  {detail}" if detail and not ok else ""))
    passed = sum(ok for _, ok, _ in results)
    print(f"selftest: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


def _raises(fn) -> bool:
    try:
        fn()
    except RuntimeError:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--app", type=Path, default=DEFAULT_DDEV)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    manifest = package(args.app)
    print(f"{args.app / 'engine'}  buildId {manifest['buildId']}  "
          f"{manifest['totals']['files']} files  {manifest['totals']['bytes']} -> {manifest['totals']['gzBytes']} gzip,"
          f" {manifest['totals']['zstBytes']} zstd bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
