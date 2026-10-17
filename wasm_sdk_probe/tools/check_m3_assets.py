#!/usr/bin/env python3
"""M3 asset delivery -- the `litecore` app serves its own packaged engine.

Criteria: specs/SPEC-M3-asset-delivery.md section 4 (K0-K2), written before
this runner, and specs/SPEC-M3-zstd.md section 4 (Z0-Z2: the zstd
representation, written before its code).  It never changes the app, the
product or dist/.

  K0  package   offline: engine/MANIFEST.json against the closure derived from
                dist/ now, every .gz against dist/, the build id, no `dist` in
                the app tree; Z0 every .zst and its frame header
  K1  wire      no browser: every packaged file with and without gzip, the
                paths that must 404, the Files entry's redirect, the editor
                document's headers; Z1 every file as a browser asks (zstd),
                which coding each Accept-Encoding gets, ETags across codings
  K2  browser   per browser and repeat, one fresh profile with its HTTP cache
                ON: open from Files, smoke, save, back to Files, open again,
                smoke, save, back.  The record of each open is the web container's Apache
                access log between two offsets; after each "back", the
                server's lock on the file for up to 10 s (K2-5).  Z2: the
                first open's big files came as zstd (chrome, firefox) or as
                gzip (firefox-nozstd: Firefox with zstd taken out of its
                Accept-Encoding pref).

  check_m3_assets.py --label shakedown|counted     run, write a report
  check_m3_assets.py --score REPORT.json           re-score a report, one line
  check_m3_assets.py --red-cases REPORT.json       each mutation must turn its
                                                   own clause red

Every problem the scorer reports starts with its clause ("K2-3 ..."); a red case
counts only if the clause it targets is among the problems it causes.
"""

from __future__ import annotations

import argparse
import base64
import copy
import gzip
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from compression import zstd
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_m3_release  # noqa: E402
from check_m3_host_entry import saves_reached  # noqa: E402
from check_m3_page_honesty import READ_RECORD, RECORDER  # noqa: E402
from check_m3_skeleton_open import (  # noqa: E402
    ACTION, DEFAULT_DDEV, FILES, FIXTURE, NAME, Instance, binding_fields, host_binding, installed_app, product_state,
    state_until)
from package_m3_engine import MAX_GZ_BYTES, MAX_ZST_BYTES, MAX_ZSTD_WINDOW, build_id, zstd_frame  # noqa: E402
from probe_m3_assets import AccessLog, closure  # noqa: E402
from probe_m3_gate0_coep import (  # noqa: E402
    DIST, EventChrome, Wire, browser_login, firefox_profile, sha256_file, utc_now, wait_until)
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import POINT_AT, PRESS, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-assets"
# SPEC-M3-page-honesty §7.6: the reviewed page (b61e9fd9), written 2026-09-29 before
# the re-shakedown and counted runs on host 0.2.4 (369e6ed); was fbfb59a4….
# Re-pointed 2026-10-15 (task 10-15c P4, before binding v20) to host 0.2.23's page (shell v72, engine v20).  The previous pin was
# d761f1cee9d26c50c0b152348d74c3d05f540e9228927815d93ad6ec161e7dcd (SPEC-M3-autosave §9.19, 0.2.13/v62; the 0.2.13 and 0.2.14 counts ran on it).
PAGE_SHA256 = "605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f"   # host 0.2.26 (engine v21, shell v74, finding 154's host rule), 2026-10-17; was 901dd6a6 (host 0.2.24, v73, finding 145), ccb67a52 (host 0.2.23, v72), d761f1ce (autosave §9.19, 0.2.13), 8909564e (production-ui §17 C′), 36c2b18b (§16 R⁗), 18c8afbe (§15 R‴), 537d62d7 (§14 R′), e00ab76a (§13.5), e97d6e03
PLAN = {"chrome": 3, "firefox": 3, "firefox-nozstd": 3}
# A report is scored against the criteria its runner wrote into it (SPEC-M3-zstd
# §7, review item 3): reports from before the zstd step keep their own verdicts.
CRITERIA = ["SPEC-M3-asset-delivery", "SPEC-M3-zstd"]
LEGACY_PLAN = {"chrome": 3, "firefox": 3}
DOC = "e2-editor.html"
ENTRY = "/apps/litecore/r/e2-editor.html"
YEAR = 31536000
# K2-2: headers on top of the packaged bytes.  Measured headers are 875-930 B;
# with 1500 the check is blind only where a file's gzip saves less than about
# 600 B (state-machine.js, recovery-notice.js, the cjk metadata) -- K1-1 checks
# those files' bytes.
SLACK = 1500
ADDRESS = re.compile(r"^(?P<build>[0-9a-f]{16})-[0-9a-f]{8}$")
NO_CACHE_FETCH = re.compile(r'fetch\(new URL\("(\./[^"]+)",\s*self\.location\.href\),\s*\{\s*cache:\s*"no-cache"')
INITIAL_STATE = re.compile(r'id="initial-state-litecore-config" value="([^"]+)"')
TYPES = {".js": "text/javascript", ".json": "application/json", ".wasm": "application/wasm",
         ".data": "application/octet-stream", ".metadata": "application/octet-stream"}
# SPEC-M3-zstd §4, written 2026-09-30 before the code: the engine's decoded
# content did not change, only its codings.
ENGINE_SCHEMA = "litecore-engine/2"
BUILD_ID = "f5f0df762e1855f2"   # host 0.2.26's engine package (v21, page 605cf24b, shell v74; the same package as 0.2.25); was d3cd39bb (0.2.24, finding 145), c3c22d92 (0.2.23, link-batch §17), eb3f9408 (0.2.14), 59e6a9fe (0.2.13), 45cdcedf (0.2.12), b99f4b13 (0.2.11), bebc7e83 (0.2.10), 7bf6dbd6 (0.2.9), 63656ee4 (0.2.8), fabdb50e (0.2.7)
# What Chrome 151 and Firefox 156 are predicted to send over HTTPS (spec §2, P1).
BROWSER_AE = "gzip, deflate, br, zstd"
# Z1-2: Accept-Encoding -> the coding the host must pick.
SELECTION = {"zstd": "zstd", "ZSTD": "zstd", "gzip;q=0, zstd": "zstd", "zstd;q=0, gzip": "gzip",
             "gzip, deflate, br": "gzip", "zstd;q=0": "identity", "br": "identity"}
# The 0.2.4 counted run's address (runs/2026-09-29T151106): the zstd policy must move it (Z1-5).
PREVIOUS_ADDRESS = "7f4f4e2204b4a9ec-566647db"
# Z1-1: headers that differ between two requests for the same bytes (measured
# 2026-09-30: date, expires, x-request-id) and the three a coding owns.
PER_REQUEST = {"date", "expires", "x-request-id"}
PER_CODING = {"content-encoding", "content-length", "etag"}
# Z2-2: the fallback arm, Firefox without zstd in its HTTPS Accept-Encoding.
NOZSTD_PREFS = {"network.http.accept-encoding.secure": "gzip, deflate, br"}
KEEP = ("content-type", "content-encoding", "content-length", "cache-control", "vary", "location", "etag",
        "cross-origin-opener-policy", "cross-origin-embedder-policy")


def asset_prefix(build: str) -> str:
    return f"/apps/litecore/r/{build}/"


def strip_front(path: str) -> str:
    return path[len("/index.php"):] if path.startswith("/index.php/") else path


# --------------------------------------------------------------------------
# K0


def package_record(app: Path, repo: Path | None = None, rev: str | None = None) -> dict[str, Any]:
    """K0 from the app's directory.  The git clauses (K0-4's tracked half, K0-6)
    read `repo` -- the app's directory on the dev instance; on another instance
    the host repo at the commit the release archive was built from."""
    repo = repo or app
    manifest = json.loads((app / "engine" / "MANIFEST.json").read_text())
    derived = closure(DIST)
    files = {}
    for path in manifest.get("files", {}):
        packed = app / "engine" / "files" / (path + ".gz")
        body = packed.read_bytes() if packed.is_file() else b""
        try:
            decoded = hashlib.sha256(gzip.decompress(body)).hexdigest()
        except Exception as error:  # noqa: BLE001 -- recorded
            decoded = f"undecodable: {error}"
        files[path] = {"gzSha256": hashlib.sha256(body).hexdigest(), "decodedSha256": decoded,
                       "distSha256": sha256_file(DIST / path) if (DIST / path).is_file() else None}
        squeezed = app / "engine" / "files" / (path + ".zst")
        zbody = squeezed.read_bytes() if squeezed.is_file() else b""
        try:
            zdecoded = hashlib.sha256(zstd.decompress(zbody)).hexdigest()
        except Exception as error:  # noqa: BLE001 -- recorded
            zdecoded = f"undecodable: {error}"
        files[path].update(zstSha256=hashlib.sha256(zbody).hexdigest(), zstBytes=len(zbody),
                           zstDecodedSha256=zdecoded, zstFrame=zstd_frame(zbody))
    tracked = subprocess.run(["git", "ls-files"] if rev is None else ["git", "ls-tree", "-r", "--name-only", rev],
                             cwd=repo, capture_output=True, text=True).stdout.split("\n")
    git_time = lambda *a: subprocess.run(["git", "log", "-1", "--format=%ct", *([rev] if rev else []), *a],  # noqa: E731
                                         cwd=repo, capture_output=True, text=True).stdout.strip()
    return {"manifest": manifest,
            "noCacheFetches": no_cache_fetches(DIST, list(manifest.get("files", {}))),
            # K0-6: Nextcloud serves the host scripts as ?v=<md5(app version)>, immutable.
            "lastJsCommit": git_time("--", "js/"),
            "lastVersionCommit": git_time("-G<version>", "--", "appinfo/info.xml"),
            "derived": {f["path"]: f["sha256"] for f in derived["files"]},
            "files": files,
            "treeEntries": sorted(os.listdir(app)),
            "trackedDist": [t for t in tracked if t == "dist" or t.startswith("dist/")]}


def package_for(root: Path, binding: dict[str, Any]) -> dict[str, Any]:
    """K0's record for the instance at `root`: the host repo on the dev
    instance; elsewhere the installed tree, with the git clauses read from the
    release's source repo at its commit.  The runner and the equivalence check
    (SPEC-M3-install-elsewhere I3-8) both call this."""
    if installed_app(root) is None:
        return package_record(DEFAULT_DDEV)
    return package_record(Path(binding["appDir"]), Path(binding["sourceRepo"]),
                          binding["hostRepo"].split(" ")[0] or "HEAD")


def score_package(pkg: dict[str, Any], zstd_step: bool = True) -> list[str]:
    bad = []
    manifest = pkg["manifest"]
    listed = manifest.get("files", {})
    if set(listed) != set(pkg["derived"]):
        bad.append(f"K0-1 manifest {sorted(set(listed) ^ set(pkg['derived']))} differ from the closure")
    for path, entry in listed.items():
        seen = pkg["files"].get(path, {})
        if not (seen.get("decodedSha256") == entry.get("sha256") == seen.get("distSha256")
                == pkg["derived"].get(path)):
            bad.append(f"K0-2 {path}: decoded {seen.get('decodedSha256')} manifest {entry.get('sha256')}"
                       f" dist {seen.get('distSha256')}")
        if seen.get("gzSha256") != entry.get("gzSha256"):
            bad.append(f"K0-2 {path}: .gz is {seen.get('gzSha256')}, manifest says {entry.get('gzSha256')}")
    if build_id(listed) != manifest.get("buildId"):
        bad.append(f"K0-3 buildId {manifest.get('buildId')} but the files give {build_id(listed)}")
    if "dist" in pkg["treeEntries"] or pkg["trackedDist"]:
        bad.append(f"K0-4 the app tree still has dist: {pkg['trackedDist'] or 'dist'}")
    for path, entry in listed.items():
        if entry.get("gzBytes", 0) > MAX_GZ_BYTES:
            bad.append(f"K0-5 {path}: {entry['gzBytes']} bytes of gzip, over {MAX_GZ_BYTES}")
    js, version = pkg.get("lastJsCommit") or "", pkg.get("lastVersionCommit") or ""
    if not (js.isdigit() and version.isdigit() and int(js) <= int(version)):
        bad.append(f"K0-6 host scripts changed after the last version bump (js {js!r}, version {version!r})")
    return bad + (score_zstd_package(pkg) if zstd_step else [])


def score_zstd_package(pkg: dict[str, Any]) -> list[str]:
    """Z0 (SPEC-M3-zstd §4)."""
    bad = []
    manifest = pkg["manifest"]
    for path, entry in manifest.get("files", {}).items():
        seen = pkg["files"].get(path, {})
        if not (seen.get("zstSha256") == entry.get("zstSha256") and seen.get("zstBytes") == entry.get("zstBytes")):
            bad.append(f"Z0-1 {path}: .zst is {str(seen.get('zstSha256'))[:12]} ({seen.get('zstBytes')} B),"
                       f" manifest says {str(entry.get('zstSha256'))[:12]} ({entry.get('zstBytes')} B)")
        if not (seen.get("zstDecodedSha256") == entry.get("sha256") == seen.get("distSha256")
                == pkg["derived"].get(path)):
            bad.append(f"Z0-1 {path}: .zst decodes to {str(seen.get('zstDecodedSha256'))[:12]},"
                       f" manifest {str(entry.get('sha256'))[:12]} dist {str(seen.get('distSha256'))[:12]}")
        frame = seen.get("zstFrame") or {}
        window = frame.get("window")
        if frame.get("error") or not isinstance(window, int) or window > MAX_ZSTD_WINDOW \
                or frame.get("trailingBytes") != 0:
            bad.append(f"Z0-2 {path}: frame {frame}")
        if not isinstance(entry.get("zstBytes"), int) or entry["zstBytes"] > MAX_ZST_BYTES:
            bad.append(f"Z0-3 {path}: {entry.get('zstBytes')} bytes of zstd, over {MAX_ZST_BYTES}")
    if manifest.get("schema") != ENGINE_SCHEMA or manifest.get("buildId") != BUILD_ID:
        bad.append(f"Z0-4 schema {manifest.get('schema')!r} buildId {manifest.get('buildId')!r},"
                   f" spec binds {ENGINE_SCHEMA} {BUILD_ID}")
    return bad


def no_cache_fetches(root: Path, files: list[str]) -> list[str]:
    """Closure paths the product itself fetches with cache: "no-cache" -- the only
    ones K2-3 lets come back 304 on a second open.  Read from the sources, as
    `closure()` is: `fetch(new URL("./x", self.location.href), {cache: "no-cache"})`."""
    found = set()
    for path in files:
        if not path.endswith(".js"):
            continue
        for spec in NO_CACHE_FETCH.findall((root / path).read_text()):
            found.add((Path(path).parent / spec[2:]).as_posix())
    return sorted(found)


# --------------------------------------------------------------------------
# K1


def fetch(wire: Wire, url: str, encoding: str, extra: dict[str, str] | None = None,
          initial_state: bool = False, full_headers: bool = False) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept-Encoding": encoding, **(extra or {})})
    started = time.monotonic()
    try:
        response = wire.raw.open(request, timeout=300)
        status, headers, body = response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        status, headers, body = error.code, error.headers, error.read()
    record = {"status": status, "seconds": round(time.monotonic() - started, 3), "bodyBytes": len(body),
              "bodySha256": hashlib.sha256(body).hexdigest(),
              "headers": {k: headers.get(k) for k in KEEP if headers.get(k) is not None}}
    if full_headers:
        record["allHeaders"] = sorted([k.lower(), v] for k, v in headers.items())
    decoder = {"gzip": gzip.decompress, "zstd": zstd.decompress}.get(headers.get("content-encoding") or "")
    if decoder:
        try:
            body = decoder(body)
            record["decodedSha256"] = hashlib.sha256(body).hexdigest()
        except Exception as error:  # noqa: BLE001 -- recorded
            record["decodedSha256"] = f"undecodable: {error}"
    if initial_state:
        # K1-5: what the document says it re-wrapped (its initial state's
        # editor.sourceSha256), read from the page Nextcloud rendered.
        match = INITIAL_STATE.search(body.decode(errors="replace"))
        try:
            record["initialState"] = json.loads(base64.b64decode(match.group(1))) if match else None
        except Exception as error:  # noqa: BLE001 -- recorded
            record["initialState"] = f"unreadable: {error}"
    return record


def wire_record(instance: Instance, manifest: dict[str, Any], file_id: int, zstd_step: bool = True) -> dict[str, Any]:
    wire = Wire(instance)
    wire.login()
    build = manifest["buildId"]
    entry = {"fileId": file_id, **fetch(wire, f"{instance.base}{ENTRY}?fileId={file_id}", "gzip")}
    # The address is whatever the entry sends the browser to; K1-4 judges it.
    location = entry["headers"].get("location") or ""
    address = location.split("/r/", 1)[1].split("/", 1)[0] if "/r/" in location else "?"
    base = instance.base + "/index.php" + asset_prefix(address)
    files = {}
    for path in manifest["files"]:
        if path == DOC:
            continue
        files[path] = {"gzip": fetch(wire, base + path, "gzip", full_headers=zstd_step),
                       "identity": fetch(wire, base + path, "identity")}
        etag = files[path]["gzip"]["headers"].get("etag")
        files[path]["conditional"] = fetch(wire, base + path, "gzip", {"If-None-Match": etag} if etag else {})
        if not zstd_step:
            continue
        # Z1: as a browser asks, and each coding's validator against the other.
        files[path]["zstd"] = fetch(wire, base + path, BROWSER_AE, full_headers=True)
        zetag = files[path]["zstd"]["headers"].get("etag")
        files[path]["zstdConditional"] = fetch(wire, base + path, BROWSER_AE, {"If-None-Match": zetag} if zetag else {})
        files[path]["zstdWithGzipEtag"] = fetch(wire, base + path, BROWSER_AE, {"If-None-Match": etag} if etag else {})
        files[path]["gzipWithZstdEtag"] = fetch(wire, base + path, "gzip", {"If-None-Match": zetag} if zetag else {})
        # Z1-2 on every path (review item 4), bodies kept only as hashes.
        files[path]["selection"] = {encoding: fetch(wire, base + path, encoding) for encoding in SELECTION}
    declared = manifest["source"].get("declaredNotLoaded") or []
    negatives = {
        "a declared-not-loaded pack": base + (declared[0] if declared else "profiles/resources/missing.data"),
        "another profile's wasm": base + "profiles/e2-editor-v14/probe.wasm",
        "dot-dot": base + "../appinfo/info.xml",
        "dot-dot encoded": base + "%2e%2e/appinfo/info.xml",
        "wrong address": instance.base + "/index.php" + asset_prefix("0" * 16 + "-" + "0" * 8) + "sdk/document-sdk.js",
        "the build id alone": instance.base + "/index.php" + asset_prefix(build) + "sdk/document-sdk.js",
        "old static dist": instance.base + "/apps-extra/litecore/dist/profiles/e2-editor-v19/probe.wasm",
        "engine dir, static": instance.base + "/apps-extra/litecore/engine/MANIFEST.json",
    }
    return {
        "address": address,
        "files": files,
        "negatives": {label: {"url": url, **{k: v for k, v in fetch(wire, url, "gzip").items()
                                             if k in ("status", "headers")}}
                      for label, url in negatives.items()},
        "entry": entry,
        "oldAddress": {"fileId": file_id, **fetch(
            wire, instance.base + "/index.php" + asset_prefix(build) + f"{DOC}?fileId={file_id}", "gzip")},
        "document": fetch(wire, f"{base}{DOC}?fileId={file_id}", "gzip", initial_state=True),
    }


def max_age(cache_control: str) -> int:
    match = re.search(r"max-age=(\d+)", cache_control or "")
    return int(match.group(1)) if match else 0


def score_wire(w: dict[str, Any], manifest: dict[str, Any], zstd_step: bool = True) -> list[str]:
    bad = []
    build = manifest["buildId"]
    address = w.get("address") or ""
    match = ADDRESS.match(address)
    if not match or match.group("build") != build:
        bad.append(f"K1-4 address {address!r} is not <buildId {build}>-<8 hex>")
    for path, entry in manifest["files"].items():
        if path == DOC:
            continue
        row = w["files"].get(path)
        if row is None:
            bad.append(f"K1-1 {path} was not fetched")
            continue
        g, i = row["gzip"], row["identity"]
        h = g["headers"]
        want = TYPES.get(Path(path).suffix, "?")
        if g["status"] != 200 or h.get("content-encoding") != "gzip":
            bad.append(f"K1-1 {path}: gzip request got {g['status']} encoding {h.get('content-encoding')}")
        if g["bodySha256"] != entry["gzSha256"] or g.get("decodedSha256") != entry["sha256"]:
            bad.append(f"K1-1 {path}: body {g['bodySha256'][:12]} decoded {str(g.get('decodedSha256'))[:12]}")
        cc = h.get("cache-control", "")
        if "immutable" not in cc or max_age(cc) < YEAR:
            bad.append(f"K1-1 {path}: cache-control {cc!r}")
        if "accept-encoding" not in (h.get("vary") or "").lower():
            bad.append(f"K1-1 {path}: vary {h.get('vary')!r}")
        if not (h.get("content-type") or "").startswith(want):
            bad.append(f"K1-1 {path}: content-type {h.get('content-type')!r}, want {want}")
        if path.endswith(".js") and h.get("cross-origin-embedder-policy") != "require-corp":
            bad.append(f"K1-1 {path}: script without COEP require-corp")
        c = row.get("conditional") or {}
        if not h.get("etag") or c.get("status") != 304 or c.get("bodyBytes") != 0:
            bad.append(f"K1-6 {path}: etag {h.get('etag')!r}, conditional {c.get('status')} {c.get('bodyBytes')} bytes")
        if i["status"] != 200 or i["headers"].get("content-encoding") or i["bodySha256"] != entry["sha256"]:
            bad.append(f"K1-2 {path}: identity request got {i['status']} encoding"
                       f" {i['headers'].get('content-encoding')} body {i['bodySha256'][:12]}")
    for label, row in w["negatives"].items():
        if row["status"] != 404:
            bad.append(f"K1-3 {label}: {row['status']} for {row['url']}")
    want_location = f"/index.php{asset_prefix(address)}{DOC}?fileId={w['entry']['fileId']}"
    for label in ("entry", "oldAddress"):
        entry = w[label]
        location = entry["headers"].get("location") or ""
        # "//..." is scheme-relative: a browser takes the next segment for a host.
        if entry["status"] != 303 or location.startswith("//") or not location.endswith(want_location):
            bad.append(f"K1-4 {label}: {entry['status']} -> {location!r}")
    if zstd_step:
        bad += score_zstd_wire(w, manifest)
    d = w["document"]
    dh = d["headers"]
    if (d["status"] != 200 or dh.get("cross-origin-opener-policy") != "same-origin"
            or dh.get("cross-origin-embedder-policy") != "require-corp"):
        bad.append(f"K1-5 document: {d['status']} COOP {dh.get('cross-origin-opener-policy')} "
                   f"COEP {dh.get('cross-origin-embedder-policy')}")
    if "immutable" in dh.get("cache-control", "") or max_age(dh.get("cache-control", "")) > 0:
        bad.append(f"K1-5 document is cacheable: {dh.get('cache-control')!r}")
    state = d.get("initialState")
    said = ((state or {}).get("editor") or {}).get("sourceSha256") if isinstance(state, dict) else None
    if said != manifest["files"].get(DOC, {}).get("sha256"):
        bad.append(f"K1-5 the document re-wrapped {str(said)[:12]}, not the packaged {DOC}")
    return bad


def representation(record: dict[str, Any], entry: dict[str, Any]) -> str:
    """Which coding a response carried, judged by its header AND its bytes."""
    encoding = record.get("headers", {}).get("content-encoding")
    body = record.get("bodySha256")
    if encoding == "zstd" and body == entry.get("zstSha256"):
        return "zstd"
    if encoding == "gzip" and body == entry.get("gzSha256"):
        return "gzip"
    if encoding is None and body == entry.get("sha256"):
        return "identity"
    return f"? ({encoding}, {str(body)[:12]})"


def unquote(etag: str | None) -> str | None:
    return etag[1:-1] if etag and len(etag) > 1 and etag[0] == etag[-1] == '"' else etag


def score_zstd_wire(w: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """Z1 (SPEC-M3-zstd §4)."""
    bad = []
    for path, entry in manifest["files"].items():
        if path == DOC:
            continue
        row = w["files"].get(path) or {}
        z = row.get("zstd")
        if z is None:
            bad.append(f"Z1-1 {path} was not fetched as a browser asks")
            continue
        h = z["headers"]
        if z["status"] != 200 or representation(z, entry) != "zstd" or z.get("decodedSha256") != entry["sha256"]:
            bad.append(f"Z1-1 {path}: {z['status']} {representation(z, entry)} decoded {str(z.get('decodedSha256'))[:12]}")
        if h.get("content-length") != str(entry.get("zstBytes")) or unquote(h.get("etag")) != entry.get("zstSha256"):
            bad.append(f"Z1-1 {path}: content-length {h.get('content-length')!r} etag {h.get('etag')!r}")
        cc = h.get("cache-control", "")
        if "immutable" not in cc or max_age(cc) < YEAR or "accept-encoding" not in (h.get("vary") or "").lower() \
                or not (h.get("content-type") or "").startswith(TYPES.get(Path(path).suffix, "?")) \
                or (path.endswith(".js") and h.get("cross-origin-embedder-policy") != "require-corp"):
            bad.append(f"Z1-1 {path}: headers {h}")
        # Every other header -- CSP included -- as the gzip response has it (review item 2).
        same = [[k, v] for k, v in z.get("allHeaders") or [] if k not in PER_REQUEST | PER_CODING]
        other = [[k, v] for k, v in (row.get("gzip") or {}).get("allHeaders") or [] if k not in PER_REQUEST | PER_CODING]
        if not same or same != other:
            bad.append(f"Z1-1 {path}: headers beside the coding differ from gzip's:"
                       f" {[x for x in same if x not in other]} vs {[x for x in other if x not in same]}")
        c, cross, back = row.get("zstdConditional") or {}, row.get("zstdWithGzipEtag") or {}, row.get("gzipWithZstdEtag") or {}
        if c.get("status") != 304 or c.get("bodyBytes") != 0:
            bad.append(f"Z1-3 {path}: its own ETag got {c.get('status')} {c.get('bodyBytes')} bytes")
        if cross.get("status") != 200 or representation(cross, entry) != "zstd":
            bad.append(f"Z1-3 {path}: a browser with the gzip ETag got {cross.get('status')} {representation(cross, entry)}")
        if back.get("status") != 200 or representation(back, entry) != "gzip":
            bad.append(f"Z1-3 {path}: gzip with the zstd ETag got {back.get('status')} {representation(back, entry)}")
        etags = [(row.get(k) or {}).get("headers", {}).get("etag") for k in ("zstd", "gzip", "identity")]
        if None in etags or len(set(etags)) != 3:
            bad.append(f"Z1-4 {path}: ETags zstd/gzip/identity {etags}")
        for encoding, want in SELECTION.items():
            got = (row.get("selection") or {}).get(encoding)
            if got is None or got["status"] != 200 or representation(got, entry) != want:
                bad.append(f"Z1-2 {path} Accept-Encoding {encoding!r}: want {want}, got"
                           f" {got and got['status']} {got and representation(got, entry)}")
    if w.get("address") == PREVIOUS_ADDRESS:
        bad.append(f"Z1-5 the address is still 0.2.4's {PREVIOUS_ADDRESS}: the coding is not in the serving policy")
    return bad


# --------------------------------------------------------------------------
# K2


LOCK_PROPS = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns"><d:prop>'
              b'<nc:lock/><nc:lock-owner-type/><nc:lock-time/></d:prop></d:propfind>')


def server_lock(instance: Instance) -> str | None:
    _, answer = instance.dav("PROPFIND", NAME, LOCK_PROPS, {"Depth": "0", "Content-Type": "application/xml"})
    match = re.search(r"<nc:lock>([^<]*)</nc:lock>", answer.decode())
    return match.group(1) if match else None


def leave_and_watch(session, instance: Instance) -> list[dict[str, Any]]:
    """Back to Files, then the server's lock for up to 10 s (K2-5)."""
    left = time.monotonic()
    navigate(session, instance.base + FILES, timeout=120)
    polls = []
    while True:
        lock = server_lock(instance)
        polls.append({"t": round(time.monotonic() - left, 2), "lock": lock})
        if lock != "1" or time.monotonic() - left >= 10:
            return polls
        time.sleep(0.5)


def open_and_smoke(session, instance: Instance) -> dict[str, Any]:
    navigate(session, instance.base + FILES, timeout=120)
    selector = (f'[data-cy-files-list-row-name={json.dumps(NAME, ensure_ascii=False)}]'
                ' [data-cy-files-list-row-name-link]')
    record: dict[str, Any] = {"filesRow": wait_until(
        session, f"(() => document.querySelector({json.dumps(selector)}) !== null)()", 60)}
    if record["filesRow"] is not True:
        # What the page was, not just that the row was missing.
        record["filesPage"] = evaluate(session, "(() => ({href: location.href, title: document.title,"
                                                " rows: [...document.querySelectorAll('[data-cy-files-list-row-name]')]"
                                                ".map((e) => e.getAttribute('data-cy-files-list-row-name')).slice(0, 20),"
                                                " text: document.body.innerText.slice(0, 600)}))()")
        raise RuntimeError(f"no Files row for {NAME}: {json.dumps(record['filesPage'], ensure_ascii=False)}")
    started = time.monotonic()
    session.click(selector)
    record["landed"] = wait_until(
        session, f"(() => location.pathname.endsWith({json.dumps('/' + DOC)}) && location.href)()", 60)
    raw = wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                              " return v && JSON.parse(v).done && v; })()", 300)
    record["secondsToDone"] = round(time.monotonic() - started, 2)
    record["host"] = json.loads(raw) if isinstance(raw, str) else {"notReported": raw}
    # K2-5 asks the server, not the host: is there a lock on the file now?
    record["serverLock"] = server_lock(instance)
    record["before"] = product_state(session)
    evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
    record["caret"] = state_until(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
    evaluate(session, PRESS.replace("ARG_ACTION", ACTION))
    record["acted"] = state_until(session, lambda s: s.get("revision") != record["caret"].get("revision")
                                  or "失敗" in (s.get("latency") or ""), 120)
    return record


# The save before each leave: SPEC-M3-page-honesty §7.8 (ruling A').  Host 0.2.3
# guards a leave with unsaved edits and keeps the lock for the user who stays,
# which leaves only the pagehide UNLOCK -- finding 105's unfixed path.  K2-5
# measures the UNGUARDED leave (the one 105's fix was measured on); before 0.2.3
# K2's leave was unguarded because the host did not guard on edits, now because
# it saves first.  Said openly, and proved per leave: the save is a 204 with the
# token, and the leave's own record shows no guard (the two `K2 instrument`
# clauses).  Not in `open_and_smoke`: probe_m3_leave_unlock imports it, and its
# edit arm must keep leaving unsaved.
DONE_TO_LEAVE = ("(() => { const v = JSON.parse(document.documentElement.getAttribute('data-litecore'));"
                 " return Math.round(Date.now() - v.started - v.finished) / 1000; })()")
HOST_SAVES = ("(() => { const v = document.documentElement.getAttribute('data-litecore');"
              " return v ? (JSON.parse(v).saves || []) : null; })()")


def save_before_leaving(session) -> dict[str, Any]:
    evaluate(session, PRESS.replace("ARG_ACTION", "save"))
    saved: dict[str, Any] = {"settled": saves_reached(session, 1)}
    saved["state"] = state_until(session, lambda s: (s.get("latency") or "").startswith("存回"), 60)
    saves = evaluate(session, HOST_SAVES) or []
    saved["hostSave"] = saves[-1] if saves else None
    saved["hostSaves"] = len(saves)
    return saved


def run_browser(kind: str, instance: Instance, scratch: Path) -> dict[str, Any]:
    log = AccessLog(instance)
    record: dict[str, Any] = {"browser": kind, "cache": "warm"}
    record["upload"] = instance.upload(FIXTURE, NAME)
    if kind == "chrome":
        profile = Path(tempfile.mkdtemp(prefix="m3-assets-chrome-"))
        session = EventChrome("warm", profile_dir=profile)
    else:
        profile = scratch / f"firefox-{time.monotonic_ns()}"
        prefs = NOZSTD_PREFS if kind == "firefox-nozstd" else None
        record["prefs"] = prefs
        session = FirefoxSession("warm", profile_dir=firefox_profile(profile), extra_prefs=prefs)
    record["profileDiskFree"] = shutil.disk_usage(profile).free
    record["version"] = getattr(session, "version", None)
    agent = "Chrome" if kind == "chrome" else "Firefox"
    try:
        record["login"] = browser_login(session, instance.base, instance.password)
        for label in ("first", "second"):
            start = log.offset()
            mark = len(getattr(session, "events", []))
            record[label] = open_and_smoke(session, instance)
            record[label]["saved"] = save_before_leaving(session)
            nonce = secrets.token_hex(8)
            record[label]["recorder"] = evaluate(session, RECORDER.replace("ARG_NONCE", json.dumps(nonce)))
            record[label]["secondsDoneToLeave"] = evaluate(session, DONE_TO_LEAVE)
            record[label]["leave"] = leave_and_watch(session, instance)
            raw = wait_until(session, READ_RECORD.replace("ARG_NONCE", json.dumps(nonce)), 10)
            record[label]["leftRecord"] = json.loads(raw) if isinstance(raw, str) else {"missing": raw}
            rows = log.since(start)
            record[label]["log"] = [
                {k: r[k] for k in ("method", "target", "path", "status", "sent")}
                for r in rows if agent in r.get("agent", "") and "/litecore/" in r.get("path", "")]
            # The instrument's own gaps, kept so the scorer can refuse them: lines it
            # could not parse, and app requests from any other client in the window.
            record[label]["unparsed"] = [r["unparsed"] for r in rows if "unparsed" in r]
            if kind == "chrome":
                record[label]["cdp"] = page_responses(session.events[mark:])
            record[label]["otherAgents"] = [
                {k: r[k] for k in ("path", "status", "agent")} for r in rows
                if "unparsed" not in r and agent not in r.get("agent", "") and "/litecore/" in r.get("path", "")]
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        session.close()
        if kind == "chrome":
            shutil.rmtree(profile, ignore_errors=True)
    return record


def page_responses(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chrome's own account of the page-level responses under the app route
    (CDP Network.responseReceived; the worker's requests are not in it).
    Recorded, not scored: a direct reading beside Z2's %O inference (review
    item 13)."""
    out = []
    for event in events:
        if event.get("method") != "Network.responseReceived":
            continue
        response = event["params"]["response"]
        if "/apps/litecore/r/" not in response.get("url", ""):
            continue
        headers = {k.lower(): v for k, v in (response.get("headers") or {}).items()}
        out.append({"path": response["url"].split("/apps/litecore/r/", 1)[1].split("?")[0],
                    "status": response.get("status"), "contentEncoding": headers.get("content-encoding"),
                    "fromDiskCache": response.get("fromDiskCache"), "type": event["params"].get("type")})
    return out


def score_run(run: dict[str, Any], ctx: dict[str, Any]) -> list[str]:
    """ctx: the manifest, the address K1 saw, and the paths the product fetches
    with cache: "no-cache" (from the package record)."""
    if "fatal" in run:
        return [f"K2 fatal: {run['fatal'].splitlines()[-1]}"]
    bad = []
    manifest = ctx["manifest"]
    prefix = asset_prefix(ctx["address"])
    listed = set(manifest["files"])
    for label in ("first", "second"):
        o = run.get(label) or {}
        host = o.get("host") or {}
        if host.get("done") is not True or host.get("stranded"):
            bad.append(f"K2-4 {label}: host done {host.get('done')!r} stranded {host.get('stranded')!r}")
        caret, acted = o.get("caret") or {}, o.get("acted") or {}
        if caret.get("timedOut") or "定位游標" not in (caret.get("latency") or ""):
            bad.append(f"K2-4 {label}: caret not placed ({caret.get('latency')!r})")
        if acted.get("timedOut") or acted.get("revision") == caret.get("revision") \
                or "失敗" in (acted.get("latency") or ""):
            bad.append(f"K2-4 {label}: action did not advance the revision ({acted.get('latency')!r})")
        lock = host.get("lock") or {}
        if o.get("serverLock") != "1" or lock.get("status") != 200 or lock.get("verified") is not True:
            bad.append(f"K2-5 {label}: at open the server lock is {o.get('serverLock')!r}, the host's LOCK"
                       f" {lock.get('status')} verified {lock.get('verified')!r}")
        leave = o.get("leave") or []
        # Exactly "": the property answered and said unlocked.  None is no answer.
        if not leave or leave[-1].get("lock") != "" or leave[-1].get("t", 99) > 10.5:
            bad.append(f"K2-5 {label}: after leaving the server lock is {leave[-1:]}")
        saved = o.get("saved") or {}
        attempts = (saved.get("hostSave") or {}).get("attempts") or [{}]
        if attempts[0].get("status") != 204 or attempts[0].get("withToken") is not True \
                or not re.fullmatch(r"存回 \d+ ms", (saved.get("state") or {}).get("latency") or ""):
            bad.append(f"K2 instrument {label}: pre-leave save did not land ({attempts[0].get('status')!r},"
                       f" token {attempts[0].get('withToken')!r}, {(saved.get('state') or {}).get('latency')!r})")
        left = o.get("leftRecord") if isinstance(o.get("leftRecord"), list) else []
        fired = [e for e in left if e.get("what") == "fired"]
        if not fired or fired[-1].get("lastGuard") is not None or fired[-1].get("guards") not in (0, None):
            bad.append(f"K2 instrument {label}: leave was guarded"
                       f" {(fired[-1].get('lastGuard') or {}).get('reasons') if fired else None} / no fired record")
        if o.get("unparsed") or o.get("otherAgents"):
            bad.append(f"K2 instrument {label}: {len(o.get('unparsed') or [])} unparsed log lines,"
                       f" {len(o.get('otherAgents') or [])} app requests from other clients")
        rows = [dict(r, path=strip_front(r["path"])) for r in o.get("log") or []]
        for r in rows:
            if r["status"] >= 400:
                bad.append(f"K2-1 {label} open: {r['status']} {r['path']}")
            elif r["path"].startswith(prefix) and r["status"] not in ((200,) if label == "first" else (200, 304)):
                bad.append(f"K2-1 {label} open: {r['status']} {r['path']}")
            elif r["path"].startswith("/apps/litecore/r/") and not r["path"].startswith(prefix) \
                    and not (r["path"] == ENTRY and r["status"] == 303):
                bad.append(f"K2-1 {label} open: {r['status']} {r['path']} is neither the entry nor this address")
        docs = [r for r in rows if r["path"] == prefix + DOC]
        if len(docs) != 1 or docs[0]["status"] != 200:
            bad.append(f"K2-1 {label} open: {[d['status'] for d in docs]} for the editor document")
        if label == "first":
            under = [r for r in rows if r["path"].startswith(prefix)]
            requested = {r["path"][len(prefix):] for r in under}
            if requested != listed:
                bad.append(f"K2-1 first open requested {sorted(requested ^ listed)} off the manifest")
            for r in under:
                name = r["path"][len(prefix):]
                if name != DOC and name in manifest["files"] \
                        and r["sent"] >= manifest["files"][name]["gzBytes"] + SLACK:
                    bad.append(f"K2-2 {name}: {r['sent']} bytes sent, packaged {manifest['files'][name]['gzBytes']}")
        else:
            # Nothing with a body; a 304 only where the product itself asks the
            # server every time (cache: "no-cache", read from the sources).
            again = [(r["path"][len(prefix):], r["status"]) for r in rows if r["path"].startswith(prefix)
                     and r["path"][len(prefix):] != DOC
                     and not (r["status"] == 304 and r["path"][len(prefix):] in ctx["noCache"])]
            if again:
                bad.append(f"K2-3 second open reached the server for {sorted(set(again))}")
    return bad + (score_zstd_run(run, ctx) if ctx.get("zstd") else [])


def distinguishable(manifest: dict[str, Any]) -> list[str]:
    """Z2's D: the files whose gzip is at least SLACK bytes bigger than their
    zstd, so a gzip response can never pass Z2-1 (%O counts the body)."""
    return sorted(p for p, e in manifest.get("files", {}).items()
                  if p != DOC and e.get("gzBytes", 0) - e.get("zstBytes", 1 << 62) >= SLACK)


def gzip_distinguishable(manifest: dict[str, Any]) -> list[str]:
    """D' (review item 8): the members of D whose raw bytes are also at least
    SLACK over their gzip, so identity can never pass Z2-2 either."""
    files = manifest.get("files", {})
    return [p for p in distinguishable(manifest) if files[p]["bytes"] - files[p]["gzBytes"] >= SLACK]


def score_zstd_run(run: dict[str, Any], ctx: dict[str, Any]) -> list[str]:
    """Z2 (SPEC-M3-zstd §4), on the first open's log."""
    manifest = ctx["manifest"]
    files = manifest.get("files", {})
    kind = run.get("browser")
    d = gzip_distinguishable(manifest) if kind == "firefox-nozstd" else distinguishable(manifest)
    must = [p for p in files if p.endswith("/probe.wasm") or p.endswith(".data")]
    bad = []
    if not must or not set(must) <= set(d):
        bad.append(f"Z2 D is {d}; it must hold the wasm and the .data files {must}")
    if kind not in ("chrome", "firefox", "firefox-nozstd"):
        return bad + [f"Z2 unknown browser {kind!r}"]
    prefix = asset_prefix(ctx["address"])
    for r in (run.get("first") or {}).get("log") or []:
        name = strip_front(r["path"])[len(prefix):] if strip_front(r["path"]).startswith(prefix) else None
        if name not in d:
            continue
        entry = files[name]
        if kind == "firefox-nozstd":
            if not entry["gzBytes"] <= r["sent"] < entry["gzBytes"] + SLACK:
                bad.append(f"Z2-2 {name}: {r['sent']} bytes sent, gzip is {entry['gzBytes']}")
        elif r["sent"] >= entry["zstBytes"] + SLACK:
            bad.append(f"Z2-1 {name}: {r['sent']} bytes sent, zstd is {entry['zstBytes']}")
    return bad


def zstd_step(report: dict[str, Any]) -> bool:
    return "SPEC-M3-zstd" in (report.get("criteria") or [])


def run_context(report: dict[str, Any]) -> dict[str, Any]:
    package = report.get("package") or {}
    return {"manifest": package.get("manifest") or {}, "address": (report.get("wire") or {}).get("address") or "?",
            "noCache": package.get("noCacheFetches") or [], "zstd": zstd_step(report)}


# --------------------------------------------------------------------------
# Z4-1: the release builder's members


def release_record(root: Path, binding: dict[str, Any]) -> dict[str, Any]:
    """The engine members build_m3_release.collect() would put in the archive of
    this host commit, as {name: sha256}.  Dev instance: the host repo at HEAD;
    elsewhere: the release's source repo at its commit (as package_for)."""
    if installed_app(root) is None:
        repo, commit = DEFAULT_DDEV, "HEAD"
    else:
        repo, commit = Path(binding["sourceRepo"]), binding["hostRepo"].split(" ")[0] or "HEAD"
    files, _ = build_m3_release.collect(repo, commit)
    return {"repo": str(repo), "commit": commit,
            "engineMembers": {n: hashlib.sha256(b).hexdigest() for n, b in sorted(files.items())
                              if n.startswith("engine/")}}


def score_release(release: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """Z4-1: the builder ships MANIFEST.json and, for every path, its .gz and its
    .zst -- enumerated here from the manifest, not through the builder's table."""
    members = release.get("engineMembers") or {}
    want = {"engine/MANIFEST.json"}
    bad = []
    for path, entry in manifest.get("files", {}).items():
        for suffix, field in ((".gz", "gzSha256"), (".zst", "zstSha256")):
            name = f"engine/files/{path}{suffix}"
            want.add(name)
            if members.get(name) != entry.get(field):
                bad.append(f"Z4-1 release member {name}: {str(members.get(name))[:12]}, manifest {str(entry.get(field))[:12]}")
    if set(members) != want:
        bad.append(f"Z4-1 release engine members differ: {sorted(set(members) ^ want)[:6]}")
    return bad


# --------------------------------------------------------------------------
# Scoring


def score(report: dict[str, Any], strict: bool) -> dict[str, Any]:
    problems: list[str] = []
    static = report.get("static") or {}
    if static.get("page") != {"dist": PAGE_SHA256, "web": PAGE_SHA256}:
        problems.append(f"static: page {static.get('page')}")
    if strict and static.get("testStatic") != 0:
        problems.append(f"static: make test-e2-c-static exit {static.get('testStatic')}")
    if strict and (report.get("hostDirty") or not report.get("hostRepo")):
        problems.append(f"static: host not bound: dirty {report.get('hostDirty')!r}")
    ctx = run_context(report)
    manifest = ctx["manifest"]
    step = ctx["zstd"]
    problems += score_package(report["package"], step) if report.get("package") else ["K0 no package record"]
    problems += score_wire(report["wire"], manifest, step) if report.get("wire") and manifest else ["K1 no wire record"]
    if step:
        problems += score_release(report.get("release") or {}, manifest)
    tally: dict[str, dict[str, Any]] = {}
    for run in report.get("runs") or []:
        entry = tally.setdefault(run["browser"], {"pass": 0, "runs": 0, "problems": []})
        entry["runs"] += 1
        bad = score_run(run, ctx)
        if bad:
            entry["problems"].append(bad)
        else:
            entry["pass"] += 1
    if strict:
        for browser, count in (PLAN if step else LEGACY_PLAN).items():
            entry = tally.get(browser) or {"pass": 0, "runs": 0}
            if entry["runs"] != count or entry["pass"] != count:
                problems.append(f"K2 {browser} {entry['pass']}/{entry['runs']} of {count}")
    ok = not problems and all(not e["problems"] for e in tally.values())
    # The verdict string stays: install-elsewhere reads it.  SPEC-M3-zstd's
    # ZSTD DELIVERED is this verdict on a report whose criteria include it.
    return {"verdict": ("ASSETS DELIVERED" if ok else "ASSETS NOT DELIVERED") if strict else ("clean" if ok else "red"),
            "criteria": report.get("criteria") or ["SPEC-M3-asset-delivery"], "tally": tally, "problems": problems}


def one_line(result: dict[str, Any]) -> str:
    cells = " ".join(f"{k}={v['pass']}/{v['runs']}" for k, v in sorted(result["tally"].items()))
    return f"{result['verdict']} [{'+'.join(result['criteria'])}] {cells} problems={result['problems'][:6]}"


# --------------------------------------------------------------------------
# Red cases: each must turn ITS clause red.


def _first_asset(run: dict, c: dict, suffix: str) -> dict:
    prefix = asset_prefix(c["address"])
    return next(r for r in run["first"]["log"] if strip_front(r["path"]).startswith(prefix)
                and strip_front(r["path"]).endswith(suffix))


def _fired(run: dict, label: str) -> dict:
    return next(e for e in run[label]["leftRecord"] if e.get("what") == "fired")


def _wasm_path(m: dict) -> str:
    return next(p for p in m["files"] if p.endswith("probe.wasm"))


def _manifest_path(m: dict) -> str:
    # The served profile's manifest, next to its wasm (K1-6 named e2-editor-v19's literally until the v20 count).
    return _wasm_path(m).rsplit("/", 1)[0] + "/sdk-manifest.json"


def _second_rows(run: dict, c: dict, rows: list[dict]) -> None:
    run["second"]["log"].extend(rows)


PACKAGE_CASES = [
    ("K0-1", "the manifest lists a file the closure does not",
     lambda p: p["manifest"]["files"].update({"extra.js": {"sha256": "0" * 64, "gzSha256": "0" * 64}})),
    ("K0-1", "the closure has a file the manifest does not", lambda p: p["derived"].update({"extra.js": "0" * 64})),
    ("K0-2", "a .gz decodes to other bytes",
     lambda p: p["files"][next(iter(p["files"]))].update(decodedSha256="1" * 64)),
    ("K0-2", "a .gz is not the manifest's", lambda p: p["files"][next(iter(p["files"]))].update(gzSha256="1" * 64)),
    ("K0-2", "dist changed since packaging", lambda p: p["files"][next(iter(p["files"]))].update(distSha256="1" * 64)),
    ("K0-3", "the build id is not the files'", lambda p: p["manifest"].update(buildId="f" * 16)),
    ("K0-4", "dist is still in the app tree", lambda p: p["treeEntries"].append("dist")),
    ("K0-4", "dist is still tracked", lambda p: p["trackedDist"].append("dist")),
    ("K0-5", "the wasm grew past Firefox's measured cache room",
     lambda p: p["manifest"]["files"][_wasm_path(p["manifest"])].update(gzBytes=MAX_GZ_BYTES + 1)),
    ("K0-6", "a host script changed after the last version bump",
     lambda p: p.update(lastJsCommit=str(int(p["lastVersionCommit"]) + 60))),
    ("K0-6", "no version bump found", lambda p: p.update(lastVersionCommit="")),
    ("Z0-1", "a .zst is not the manifest's",
     lambda p: p["files"][_wasm_path(p["manifest"])].update(zstSha256="5" * 64)),
    ("Z0-1", "a .zst decodes to other bytes",
     lambda p: p["files"]["sdk/document-sdk.js"].update(zstDecodedSha256="5" * 64)),
    ("Z0-1", "a .zst is missing", lambda p: p["files"]["sdk/document-sdk.js"].update(
        zstSha256=hashlib.sha256(b"").hexdigest(), zstBytes=0, zstDecodedSha256="undecodable: empty", zstFrame={"error": "x"})),
    ("Z0-2", "a 16 MiB window, read from a real frame (level 1, window_log 24)",
     lambda p: p["files"][_wasm_path(p["manifest"])].update(zstFrame=zstd_frame(_wide_frame()))),
    ("Z0-2", "trailing bytes after the frame", lambda p: p["files"][_wasm_path(p["manifest"])].update(
        zstFrame=zstd_frame(zstd.compress(b"litecore") + b"x"))),
    ("Z0-3", "a .zst over Firefox's measured cache room",
     lambda p: p["manifest"]["files"][_wasm_path(p["manifest"])].update(zstBytes=MAX_ZST_BYTES + 1)),
    ("Z0-4", "a schema-1 manifest", lambda p: p["manifest"].update(schema="litecore-engine/1")),
    ("Z0-4", "another engine", lambda p: p["manifest"].update(
        buildId=build_id(dict(p["manifest"]["files"], **{"x.js": {"sha256": "0" * 64}})))),
]

WIRE_CASES = [
    ("K1-1", "gzip request answered without Content-Encoding",
     lambda w, m: w["files"][_wasm_path(m)]["gzip"]["headers"].pop("content-encoding")),
    ("K1-1", "gzip body is not the packaged bytes",
     lambda w, m: w["files"][_wasm_path(m)]["gzip"].update(bodySha256="2" * 64)),
    ("K1-1", "not immutable",
     lambda w, m: w["files"][_wasm_path(m)]["gzip"]["headers"].update({"cache-control": "private, max-age=31536000"})),
    ("K1-1", "max-age under a year",
     lambda w, m: w["files"][_wasm_path(m)]["gzip"]["headers"].update({"cache-control": "private, max-age=3600, immutable"})),
    ("K1-1", "no Vary", lambda w, m: w["files"][_wasm_path(m)]["gzip"]["headers"].pop("vary")),
    ("K1-1", "wasm not application/wasm",
     lambda w, m: w["files"][_wasm_path(m)]["gzip"]["headers"].update({"content-type": "application/octet-stream"})),
    ("K1-1", "a script without COEP",
     lambda w, m: w["files"]["sdk/document-sdk.js"]["gzip"]["headers"].pop("cross-origin-embedder-policy")),
    ("K1-2", "identity request answered with gzip",
     lambda w, m: w["files"][_wasm_path(m)]["identity"]["headers"].update({"content-encoding": "gzip"})),
    ("K1-2", "identity body is not the file",
     lambda w, m: w["files"][_wasm_path(m)]["identity"].update(bodySha256="3" * 64)),
    ("K1-3", "an unlisted pack is served", lambda w, m: w["negatives"]["a declared-not-loaded pack"].update(status=200)),
    ("K1-3", "the old static dist is served", lambda w, m: w["negatives"]["old static dist"].update(status=200)),
    ("K1-3", "a wrong address redirects", lambda w, m: w["negatives"]["wrong address"].update(status=303)),
    ("K1-3", "the build id alone still serves files", lambda w, m: w["negatives"]["the build id alone"].update(status=200)),
    ("K1-3", "the engine directory is served statically",
     lambda w, m: w["negatives"]["engine dir, static"].update(status=200)),
    ("K1-3", "dot-dot is served", lambda w, m: w["negatives"]["dot-dot"].update(status=200)),
    ("K1-6", "no ETag", lambda w, m: w["files"][_wasm_path(m)]["gzip"]["headers"].pop("etag")),
    ("K1-6", "a conditional request answered with the body",
     lambda w, m: w["files"][_manifest_path(m)]["conditional"].update(status=200, bodyBytes=2082)),
    ("K1-4", "the entry is not a redirect", lambda w, m: w["entry"].update(status=200)),
    ("K1-4", "the entry redirects to a scheme-relative URL",
     lambda w, m: w["entry"]["headers"].update(location=f"//index.php/apps/litecore/r/{w['address']}/{DOC}?fileId={w['entry']['fileId']}")),
    ("K1-4", "the address has no serving-policy hash (review item 1)",
     lambda w, m: w.update(address=m["buildId"])),
    ("K1-4", "an old address's document is a 404 (review item 11)", lambda w, m: w["oldAddress"].update(status=404)),
    ("K1-5", "the document is immutable",
     lambda w, m: w["document"]["headers"].update({"cache-control": "private, max-age=31536000, immutable"})),
    ("K1-5", "the document has no COEP", lambda w, m: w["document"]["headers"].pop("cross-origin-embedder-policy")),
    ("K1-5", "the document re-wrapped some other page (review item 10)",
     lambda w, m: w["document"]["initialState"]["editor"].update(sourceSha256="4" * 64)),
    ("Z1-1", "a browser request answered with gzip",
     lambda w, m: w["files"][_wasm_path(m)].update(zstd=copy.deepcopy(w["files"][_wasm_path(m)]["gzip"]))),
    ("Z1-1", "zstd body is not the packaged bytes",
     lambda w, m: w["files"][_wasm_path(m)]["zstd"].update(bodySha256="6" * 64)),
    ("Z1-1", "Content-Length is the gzip's", lambda w, m: w["files"][_wasm_path(m)]["zstd"]["headers"].update(
        {"content-length": str(m["files"][_wasm_path(m)]["gzBytes"])})),
    ("Z1-1", "the zstd ETag is the gzip's", lambda w, m: w["files"]["sdk/document-sdk.js"]["zstd"]["headers"].update(
        etag=w["files"]["sdk/document-sdk.js"]["gzip"]["headers"]["etag"])),
    ("Z1-1", "zstd without Vary", lambda w, m: w["files"][_wasm_path(m)]["zstd"]["headers"].pop("vary")),
    ("Z1-1", "zstd script without COEP",
     lambda w, m: w["files"]["sdk/document-sdk.js"]["zstd"]["headers"].pop("cross-origin-embedder-policy")),
    ("Z1-1", "a looser CSP on the zstd representation (review item 2)",
     lambda w, m: w["files"]["sdk/document-sdk.js"]["zstd"].update(allHeaders=[
         [k, v + " 'unsafe-eval'" if k == "content-security-policy" else v]
         for k, v in w["files"]["sdk/document-sdk.js"]["zstd"]["allHeaders"]])),
    ("Z1-1", "a header only the zstd representation carries",
     lambda w, m: w["files"][_wasm_path(m)]["zstd"]["allHeaders"].append(["x-extra", "1"])),
    ("Z1-2", "zstd;q=0 ignored", lambda w, m: _sel(w, "sdk/document-sdk.js").update(
        {"zstd;q=0, gzip": copy.deepcopy(_sel(w, "sdk/document-sdk.js")["zstd"])})),
    ("Z1-2", "a zstd-less browser gets identity", lambda w, m: _sel(w, "sdk/document-sdk.js").update(
        {"gzip, deflate, br": copy.deepcopy(_sel(w, "sdk/document-sdk.js")["br"])})),
    ("Z1-2", "the token is matched case-sensitively", lambda w, m: _sel(w, "sdk/document-sdk.js").update(
        {"ZSTD": copy.deepcopy(_sel(w, "sdk/document-sdk.js")["br"])})),
    ("Z1-2", "only the wasm ignores zstd;q=0 (review item 4)", lambda w, m: _sel(w, _wasm_path(m)).update(
        {"zstd;q=0, gzip": copy.deepcopy(_sel(w, _wasm_path(m))["zstd"])})),
    ("Z1-5", "the address did not move (review item 9)", lambda w, m: w.update(address=PREVIOUS_ADDRESS)),
    ("Z1-3", "the gzip ETag revalidates the zstd representation",
     lambda w, m: w["files"][_wasm_path(m)]["zstdWithGzipEtag"].update(status=304, bodyBytes=0, bodySha256=hashlib.sha256(b"").hexdigest())),
    ("Z1-3", "zstd's own ETag answered with the body",
     lambda w, m: w["files"]["sdk/document-sdk.js"]["zstdConditional"].update(status=200, bodyBytes=3930)),
    ("Z1-3", "a gzip request with the zstd ETag got 304",
     lambda w, m: w["files"]["sdk/document-sdk.js"]["gzipWithZstdEtag"].update(status=304, bodyBytes=0)),
    ("Z1-4", "one ETag for every coding", lambda w, m: w["files"]["sdk/document-sdk.js"]["identity"]["headers"].update(
        etag=w["files"]["sdk/document-sdk.js"]["zstd"]["headers"]["etag"])),
]

RUN_CASES = [
    ("K2-1", "a packaged file was never requested",
     lambda r, c: r["first"].update(log=[x for x in r["first"]["log"] if not x["path"].endswith("probe.js")])),
    ("K2-1", "a request off the manifest",
     lambda r, c: r["first"]["log"].append(dict(r["first"]["log"][0], path=f"/index.php{asset_prefix(c['address'])}x.js",
                                                target="x", status=200))),
    ("K2-1", "a 404 under the app",
     lambda r, c: r["first"]["log"].append(dict(r["first"]["log"][0], path="/apps-extra/litecore/js/x.js", status=404))),
    ("K2-1", "an asset answered 206", lambda r, c: _first_asset(r, c, "probe.wasm").update(status=206)),
    ("K2-1", "a 404 on the second open (review item 5 D)",
     lambda r, c: _second_rows(r, c, [dict(r["first"]["log"][0], path="/apps-extra/litecore/js/missing.js", status=404)])),
    ("K2-1", "the wasm again under another address on the second open (review item 5 E)",
     lambda r, c: _second_rows(r, c, [dict(_first_asset(r, c, "probe.wasm"), path=_first_asset(r, c, "probe.wasm")["path"]
                                            .replace(c["address"], "0" * 16 + "-" + "0" * 8))])),
    ("K2-2", "the wasm went over the wire uncompressed",
     lambda r, c: _first_asset(r, c, "probe.wasm").update(sent=c["manifest"]["files"][_wasm_path(c["manifest"])]["bytes"])),
    ("K2-3", "the second open fetched the wasm again",
     lambda r, c: _second_rows(r, c, [dict(_first_asset(r, c, "probe.wasm"))])),
    ("K2-3", "the second open fetched one small script again",
     lambda r, c: _second_rows(r, c, [dict(_first_asset(r, c, "sdk/document-sdk.js"))])),
    ("K2-3", "the manifest revalidation came back with a body (shakedown 164501)",
     lambda r, c: _second_rows(r, c, [dict(_first_asset(r, c, "sdk-manifest.json"), status=200)])),
    ("K2-3", "every asset revalidated with a 304 (review item 5 A)",
     lambda r, c: _second_rows(r, c, [dict(x, status=304, sent=300) for x in r["first"]["log"]
                                      if strip_front(x["path"]).startswith(asset_prefix(c["address"]))
                                      and not x["path"].endswith("/" + DOC)])),
    ("K2-1", "the second open never loaded the document",
     lambda r, c: r["second"].update(log=[x for x in r["second"]["log"] if not x["path"].endswith("/" + DOC)])),
    ("K2-4", "the host never finished the second open", lambda r, c: r["second"]["host"].update(done=False)),
    ("K2-4", "the host stranded the first open",
     lambda r, c: r["first"]["host"].update(stranded={"bytes": 1})),
    ("K2-4", "the caret was never placed", lambda r, c: r["first"]["caret"].update(latency="", timedOut=True)),
    ("K2-4", "the action did not land",
     lambda r, c: r["second"]["acted"].update(revision=r["second"]["caret"].get("revision"))),
    ("K2-5", "the second open was refused the lock (finding 105)",
     lambda r, c: r["second"]["host"].update(lock={"state": "refused", "status": 423})),
    ("K2-5", "no lock on the server after the open", lambda r, c: r["first"].update(serverLock="")),
    ("K2-5", "the host never verified its token (review item 6)",
     lambda r, c: r["first"]["host"]["lock"].update(verified=None)),
    ("K2-5", "leaving kept the lock",
     lambda r, c: r["first"]["leave"].append({"t": 10.1, "lock": "1"})),
    ("K2-5", "the lock property never answered after leaving (review item 6)",
     lambda r, c: r["second"]["leave"].append({"t": 2.0, "lock": None})),
    ("K2-5", "no watch after leaving", lambda r, c: r["second"].update(leave=[])),
    ("K2 instrument", "an unparsed access-log line (review item 13)",
     lambda r, c: r["second"].update(unparsed=["garbled"])),
    ("K2 instrument", "another client in the window", lambda r, c: r["first"].update(
        otherAgents=[{"path": "/apps/litecore/r/x", "status": 200, "agent": "curl"}])),
    # SPEC-M3-page-honesty §7.8: the save before the leave, and the leave unguarded.
    ("K2 instrument", "the pre-leave save was refused (412)",
     lambda r, c: r["first"]["saved"]["hostSave"]["attempts"][0].update(status=412)),
    ("K2 instrument", "the leave was guarded (reason page)",
     lambda r, c: _fired(r, "second").update(lastGuard={"reasons": ["page"]}, guards=1)),
    ("K2 instrument", "no fired record",
     lambda r, c: r["first"].update(leftRecord=[e for e in r["first"]["leftRecord"] if e.get("what") != "fired"])),
    # SPEC-M3-zstd: which browsers each applies to is the fourth field.
    ("Z2-1", "the wasm came as gzip", lambda r, c: _first_asset(r, c, "probe.wasm").update(
        sent=c["manifest"]["files"][_wasm_path(c["manifest"])]["gzBytes"] + 900), ("chrome", "firefox")),
    ("Z2-1", "the page module came as gzip", lambda r, c: _first_asset(r, c, "/e2-editor-app.js").update(
        sent=c["manifest"]["files"]["e2-editor-app.js"]["gzBytes"] + 900), ("chrome", "firefox")),
    ("Z2-2", "the fallback arm got zstd", lambda r, c: _first_asset(r, c, "probe.wasm").update(
        sent=c["manifest"]["files"][_wasm_path(c["manifest"])]["zstBytes"] + 900), ("firefox-nozstd",)),
    ("Z2-2", "the fallback arm got identity", lambda r, c: _first_asset(r, c, "cjk-sub-e10.06976180177c8bd2.data").update(
        sent=c["manifest"]["files"]["profiles/resources/cjk-sub-e10.06976180177c8bd2.data"]["bytes"] + 900), ("firefox-nozstd",)),
    ("Z2 D", "D lost the wasm (zstd no smaller than gzip)", lambda r, c: c["manifest"]["files"][_wasm_path(c["manifest"])]
     .update(zstBytes=c["manifest"]["files"][_wasm_path(c["manifest"])]["gzBytes"])),
    ("Z2 D", "D' lost the cjk pack (gzip saves under 1500; review item 8)", lambda r, c: c["manifest"]["files"][
        "profiles/resources/cjk-sub-e10.06976180177c8bd2.data"].update(bytes=c["manifest"]["files"][
            "profiles/resources/cjk-sub-e10.06976180177c8bd2.data"]["gzBytes"] + 100), ("firefox-nozstd",)),
]


def _sel(w: dict, path: str) -> dict:
    return w["files"][path]["selection"]


def _without(members: dict, name: str) -> dict:
    members.pop(name)
    return members


RELEASE_CASES = [
    ("Z4-1", "the release carries no .zst (review item 1)", lambda r, m: r.update(engineMembers={
        n: d for n, d in r["engineMembers"].items() if not n.endswith(".zst")})),
    ("Z4-1", "one .zst missing", lambda r, m: _without(r["engineMembers"], f"engine/files/{_wasm_path(m)}.zst")),
    ("Z4-1", "a .zst that is not the manifest's",
     lambda r, m: r["engineMembers"].update({f"engine/files/{_wasm_path(m)}.zst": "7" * 64})),
    ("Z4-1", "an extra engine member", lambda r, m: r["engineMembers"].update({"engine/files/x.br": "7" * 64})),
]


def _wide_frame() -> bytes:
    """A real frame over the limit: 20 MiB at window_log 24 (16 MiB)."""
    data = hashlib.sha256(b"litecore").digest() * (20 * (1 << 20) // 32)
    return zstd.compress(data, options={zstd.CompressionParameter.compression_level: 1,
                                        zstd.CompressionParameter.window_log: 24})


def red_cases(path: Path) -> int:
    report = json.loads(path.read_text())
    manifest = report["package"]["manifest"]
    failures = 0

    def judge(label: str, clause: str, problems: list[str]) -> None:
        nonlocal failures
        red = any(p.startswith(clause) for p in problems)
        failures += not red
        print(f"  {'red ' if red else 'GREEN'}  {clause} {label}")

    step = zstd_step(report)
    # A report from before the zstd step is mutated only in its own clauses.
    mine = lambda cases: [c for c in cases if step or not c[0].startswith("Z")]  # noqa: E731
    if score_package(report["package"], step):
        print("  MISSING package cases: the package record is not clean")
        failures += len(mine(PACKAGE_CASES))
    else:
        for clause, label, mutate in mine(PACKAGE_CASES):
            pkg = copy.deepcopy(report["package"])
            mutate(pkg)
            judge(label, clause, score_package(pkg, step))
    if score_wire(report["wire"], manifest, step):
        print("  MISSING wire cases: the wire record is not clean")
        failures += len(mine(WIRE_CASES))
    else:
        for clause, label, mutate in mine(WIRE_CASES):
            w = copy.deepcopy(report["wire"])
            mutate(w, manifest)
            judge(label, clause, score_wire(w, manifest, step))
    if step:
        if score_release(report.get("release") or {}, manifest):
            print("  MISSING release cases: the release record is not clean")
            failures += len(RELEASE_CASES)
        for clause, label, mutate in RELEASE_CASES:
            r = copy.deepcopy(report.get("release") or {"engineMembers": {}})
            mutate(r, manifest)
            judge(label, clause, score_release(r, manifest))
    ctx = run_context(report)
    for clause, label, mutate, *only in mine(RUN_CASES):
        for browser in only[0] if only else (PLAN if step else LEGACY_PLAN):
            base = next((r for r in report["runs"] if r["browser"] == browser and not score_run(r, ctx)), None)
            if base is None:
                print(f"  MISSING {clause} {label} [{browser}]: no clean run to mutate")
                failures += 1
                continue
            mutated, c = copy.deepcopy(base), copy.deepcopy(ctx)
            mutate(mutated, c)
            judge(f"{label} [{browser}]", clause, score_run(mutated, c))
    static = copy.deepcopy(report)
    static["static"]["page"]["dist"] = "0" * 64
    judge("the served page is not the spec's", "static: page", score(static, strict=False)["problems"])
    return failures


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", choices=("shakedown", "counted"))
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV,
                        help="another instance: the app installed from the release archive (SPEC-M3-install-elsewhere)")
    parser.add_argument("--browsers", default=",".join(PLAN))
    parser.add_argument("--repeats", type=int, default=None, help="shakedown only")
    parser.add_argument("--score", type=Path)
    parser.add_argument("--red-cases", type=Path)
    args = parser.parse_args()
    if args.score:
        report = json.loads(args.score.read_text())
        result = score(report, strict=report.get("label") == "counted")
        print(one_line(result))
        return 0 if result["verdict"] in ("ASSETS DELIVERED", "clean") else 1
    if args.red_cases:
        return 1 if red_cases(args.red_cases) else 0
    if not args.label:
        parser.error("--label, --score or --red-cases")
    counted = args.label == "counted"
    static = {"page": {"dist": sha256_file(DIST / "e2-editor-app.js"),
                       "web": sha256_file(PROJECT / "web" / "e2-editor-app.js")}}
    if counted and static["page"] != {"dist": PAGE_SHA256, "web": PAGE_SHA256}:
        print(f"refusing a counted run: page is {static['page']}, spec wants {PAGE_SHA256[:12]}…")
        return 2
    binding = host_binding(args.ddev_root)
    dirty = binding["hostDirty"]
    if counted and dirty:
        print(f"refusing a counted run: the host repo has uncommitted changes:\n{dirty}")
        return 2
    if counted:
        static["testStatic"] = subprocess.run(["make", "-C", str(PROJECT), "test-e2-c-static"],
                                              capture_output=True, text=True).returncode
    instance = Instance(args.ddev_root)
    report: dict[str, Any] = {
        "runner": "check_m3_assets.py", "runnerSha256": sha256_file(Path(__file__)), "label": args.label,
        "startedAt": utc_now(), "static": static, "criteria": CRITERIA,
        **binding_fields(binding),
        "instance": instance.describe(),
        "runs": [],
    }
    out = EVIDENCE / ("runs" if counted else "shakedown") / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        report["package"] = package_for(args.ddev_root, binding)
        uploaded = instance.upload(FIXTURE, NAME)
        report["wire"] = wire_record(instance, report["package"]["manifest"], uploaded["fileId"])
        report["release"] = release_record(args.ddev_root, binding)
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
        with tempfile.TemporaryDirectory(prefix="m3-assets-", dir=PROJECT / "build") as scratch:
            for browser in args.browsers.split(","):
                for index in range(PLAN[browser] if counted or args.repeats is None else args.repeats):
                    print(f"K2 {browser} #{index + 1}", flush=True)
                    report["runs"].append(run_browser(browser, instance, Path(scratch)))
                    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    finally:
        report["completedAt"] = utc_now()
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    result = score(report, strict=counted)
    report["score"] = result
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(REPO))
    print(one_line(result))
    return 0 if result["verdict"] in ("ASSETS DELIVERED", "clean") else 1


if __name__ == "__main__":
    sys.exit(main())
