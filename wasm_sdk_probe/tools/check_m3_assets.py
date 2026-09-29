#!/usr/bin/env python3
"""M3 asset delivery -- the `litecore` app serves its own packaged engine.

Criteria: specs/SPEC-M3-asset-delivery.md section 4 (K0-K2), written before
this runner.  It never changes the app, the product or dist/.

  K0  package   offline: engine/MANIFEST.json against the closure derived from
                dist/ now, every .gz against dist/, the build id, no `dist` in
                the app tree
  K1  wire      no browser: every packaged file with and without gzip, the
                paths that must 404, the Files entry's redirect, the editor
                document's headers
  K2  browser   per browser and repeat, one fresh profile with its HTTP cache
                ON: open from Files, smoke, save, back to Files, open again,
                smoke, save, back.  The record of each open is the web container's Apache
                access log between two offsets; after each "back", the
                server's lock on the file for up to 10 s (K2-5).

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
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_host_entry import saves_reached  # noqa: E402
from check_m3_page_honesty import READ_RECORD, RECORDER  # noqa: E402
from check_m3_skeleton_open import (  # noqa: E402
    ACTION, DEFAULT_DDEV, FILES, FIXTURE, NAME, Instance, binding_fields, host_binding, installed_app, product_state,
    state_until)
from package_m3_engine import MAX_GZ_BYTES, build_id  # noqa: E402
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
PAGE_SHA256 = "fc80050c22948df63f012fa87a254c63e4f19227aa387ded76747bd6c21d947e"
PLAN = {"chrome": 3, "firefox": 3}
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


def score_package(pkg: dict[str, Any]) -> list[str]:
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
          initial_state: bool = False) -> dict[str, Any]:
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
    if headers.get("content-encoding") == "gzip":
        try:
            body = gzip.decompress(body)
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


def wire_record(instance: Instance, manifest: dict[str, Any], file_id: int) -> dict[str, Any]:
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
        files[path] = {"gzip": fetch(wire, base + path, "gzip"), "identity": fetch(wire, base + path, "identity")}
        etag = files[path]["gzip"]["headers"].get("etag")
        files[path]["conditional"] = fetch(wire, base + path, "gzip", {"If-None-Match": etag} if etag else {})
    declared = manifest["source"].get("declaredNotLoaded") or []
    negatives = {
        "a declared-not-loaded pack": base + (declared[0] if declared else "profiles/resources/missing.data"),
        "another profile's wasm": base + "profiles/e2-editor-v14/probe.wasm",
        "dot-dot": base + "../appinfo/info.xml",
        "dot-dot encoded": base + "%2e%2e/appinfo/info.xml",
        "wrong address": instance.base + "/index.php" + asset_prefix("0" * 16 + "-" + "0" * 8) + "sdk/document-sdk.js",
        "the build id alone": instance.base + "/index.php" + asset_prefix(build) + "sdk/document-sdk.js",
        "old static dist": instance.base + "/apps-extra/litecore/dist/profiles/e2-editor-v8/probe.wasm",
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


def score_wire(w: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
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
        session = FirefoxSession("warm", profile_dir=firefox_profile(profile))
    record["profileDiskFree"] = shutil.disk_usage(profile).free
    record["version"] = getattr(session, "version", None)
    agent = "Chrome" if kind == "chrome" else "Firefox"
    try:
        record["login"] = browser_login(session, instance.base, instance.password)
        for label in ("first", "second"):
            start = log.offset()
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
    return bad


def run_context(report: dict[str, Any]) -> dict[str, Any]:
    package = report.get("package") or {}
    return {"manifest": package.get("manifest") or {}, "address": (report.get("wire") or {}).get("address") or "?",
            "noCache": package.get("noCacheFetches") or []}


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
    problems += score_package(report["package"]) if report.get("package") else ["K0 no package record"]
    problems += score_wire(report["wire"], manifest) if report.get("wire") and manifest else ["K1 no wire record"]
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
        for browser, count in PLAN.items():
            entry = tally.get(browser) or {"pass": 0, "runs": 0}
            if entry["runs"] != count or entry["pass"] != count:
                problems.append(f"K2 {browser} {entry['pass']}/{entry['runs']} of {count}")
    ok = not problems and all(not e["problems"] for e in tally.values())
    return {"verdict": ("ASSETS DELIVERED" if ok else "ASSETS NOT DELIVERED") if strict else ("clean" if ok else "red"),
            "tally": tally, "problems": problems}


def one_line(result: dict[str, Any]) -> str:
    cells = " ".join(f"{k}={v['pass']}/{v['runs']}" for k, v in sorted(result["tally"].items()))
    return f"{result['verdict']} {cells} problems={result['problems'][:6]}"


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
     lambda w, m: w["files"]["profiles/e2-editor-v8/sdk-manifest.json"]["conditional"].update(status=200, bodyBytes=2082)),
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
]


def red_cases(path: Path) -> int:
    report = json.loads(path.read_text())
    manifest = report["package"]["manifest"]
    failures = 0

    def judge(label: str, clause: str, problems: list[str]) -> None:
        nonlocal failures
        red = any(p.startswith(clause) for p in problems)
        failures += not red
        print(f"  {'red ' if red else 'GREEN'}  {clause} {label}")

    if score_package(report["package"]):
        print("  MISSING package cases: the package record is not clean")
        failures += len(PACKAGE_CASES)
    else:
        for clause, label, mutate in PACKAGE_CASES:
            pkg = copy.deepcopy(report["package"])
            mutate(pkg)
            judge(label, clause, score_package(pkg))
    if score_wire(report["wire"], manifest):
        print("  MISSING wire cases: the wire record is not clean")
        failures += len(WIRE_CASES)
    else:
        for clause, label, mutate in WIRE_CASES:
            w = copy.deepcopy(report["wire"])
            mutate(w, manifest)
            judge(label, clause, score_wire(w, manifest))
    ctx = run_context(report)
    for clause, label, mutate in RUN_CASES:
        for browser in PLAN:
            base = next((r for r in report["runs"] if r["browser"] == browser and not score_run(r, ctx)), None)
            if base is None:
                print(f"  MISSING {clause} {label} [{browser}]: no clean run to mutate")
                failures += 1
                continue
            mutated = copy.deepcopy(base)
            mutate(mutated, ctx)
            judge(f"{label} [{browser}]", clause, score_run(mutated, ctx))
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
    parser.add_argument("--browsers", default="chrome,firefox")
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
        "startedAt": utc_now(), "static": static,
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
