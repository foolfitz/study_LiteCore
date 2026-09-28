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
                ON: open from Files, smoke, back to Files, open again, smoke,
                back.  The record of each open is the web container's Apache
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
import copy
import gzip
import hashlib
import json
import os
import re
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
from check_m3_skeleton_open import (  # noqa: E402
    ACTION, DEFAULT_DDEV, FILES, FIXTURE, NAME, Instance, product_state, state_until)
from package_m3_engine import build_id  # noqa: E402
from probe_m3_assets import AccessLog, closure  # noqa: E402
from probe_m3_gate0_coep import (  # noqa: E402
    DIST, EventChrome, Wire, browser_login, firefox_profile, sha256_file, utc_now, wait_until)
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import POINT_AT, PRESS, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-assets"
PAGE_SHA256 = "fbfb59a4014995322f210812e3627ff828dbecae351d157305a75701e2d76632"
PLAN = {"chrome": 3, "firefox": 3}
DOC = "e2-editor.html"
ENTRY = "/apps/litecore/r/e2-editor.html"
YEAR = 31536000
SLACK = 4096          # K2-2: headers on top of the packaged bytes
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


def package_record(app: Path) -> dict[str, Any]:
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
    tracked = subprocess.run(["git", "ls-files"], cwd=app, capture_output=True, text=True).stdout.split("\n")
    return {"manifest": manifest,
            "derived": {f["path"]: f["sha256"] for f in derived["files"]},
            "files": files,
            "treeEntries": sorted(os.listdir(app)),
            "trackedDist": [t for t in tracked if t == "dist" or t.startswith("dist/")]}


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
    return bad


# --------------------------------------------------------------------------
# K1


def fetch(wire: Wire, url: str, encoding: str, extra: dict[str, str] | None = None) -> dict[str, Any]:
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
            record["decodedSha256"] = hashlib.sha256(gzip.decompress(body)).hexdigest()
        except Exception as error:  # noqa: BLE001 -- recorded
            record["decodedSha256"] = f"undecodable: {error}"
    return record


def wire_record(instance: Instance, manifest: dict[str, Any], file_id: int) -> dict[str, Any]:
    wire = Wire(instance)
    wire.login()
    build = manifest["buildId"]
    base = instance.base + "/index.php" + asset_prefix(build)
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
        "wrong build id": instance.base + "/index.php" + asset_prefix("0" * 16) + "sdk/document-sdk.js",
        "old static dist": instance.base + "/apps-extra/litecore/dist/profiles/e2-editor-v8/probe.wasm",
    }
    return {
        "files": files,
        "negatives": {label: {"url": url, **{k: v for k, v in fetch(wire, url, "gzip").items()
                                             if k in ("status", "headers")}}
                      for label, url in negatives.items()},
        "entry": {"fileId": file_id, **fetch(wire, f"{instance.base}{ENTRY}?fileId={file_id}", "gzip")},
        "document": fetch(wire, f"{base}{DOC}?fileId={file_id}", "gzip"),
    }


def max_age(cache_control: str) -> int:
    match = re.search(r"max-age=(\d+)", cache_control or "")
    return int(match.group(1)) if match else 0


def score_wire(w: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    bad = []
    build = manifest["buildId"]
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
    entry = w["entry"]
    location = entry["headers"].get("location") or ""
    # "//..." is scheme-relative: a browser takes the next segment for a host.
    if entry["status"] != 303 or location.startswith("//") or not location.endswith(
            f"/index.php{asset_prefix(build)}{DOC}?fileId={entry['fileId']}"):
        bad.append(f"K1-4 entry: {entry['status']} -> {location!r}")
    d = w["document"]
    dh = d["headers"]
    if (d["status"] != 200 or dh.get("cross-origin-opener-policy") != "same-origin"
            or dh.get("cross-origin-embedder-policy") != "require-corp"):
        bad.append(f"K1-5 document: {d['status']} COOP {dh.get('cross-origin-opener-policy')} "
                   f"COEP {dh.get('cross-origin-embedder-policy')}")
    if "immutable" in dh.get("cache-control", "") or max_age(dh.get("cache-control", "")) > 0:
        bad.append(f"K1-5 document is cacheable: {dh.get('cache-control')!r}")
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
    record["before"] = product_state(session)
    evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
    record["caret"] = state_until(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
    evaluate(session, PRESS.replace("ARG_ACTION", ACTION))
    record["acted"] = state_until(session, lambda s: s.get("revision") != record["caret"].get("revision")
                                  or "失敗" in (s.get("latency") or ""), 120)
    return record


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
            record[label]["leave"] = leave_and_watch(session, instance)
            record[label]["log"] = [
                {k: r[k] for k in ("method", "target", "path", "status", "sent")}
                for r in log.since(start) if agent in r.get("agent", "") and "/litecore/" in r.get("path", "")]
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        session.close()
        if kind == "chrome":
            shutil.rmtree(profile, ignore_errors=True)
    return record


def score_run(run: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    if "fatal" in run:
        return [f"K2 fatal: {run['fatal'].splitlines()[-1]}"]
    bad = []
    build = manifest["buildId"]
    prefix = asset_prefix(build)
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
        if lock.get("state") != "held" or lock.get("status") != 200:
            bad.append(f"K2-5 {label}: the host's lock at open is {lock.get('state')!r} ({lock.get('status')})")
        leave = o.get("leave") or []
        if not leave or leave[-1].get("lock") == "1" or leave[-1].get("t", 99) > 10.5:
            bad.append(f"K2-5 {label}: the lock was still on the server {leave[-1:]} after leaving")
    first = [dict(r, path=strip_front(r["path"])) for r in (run.get("first") or {}).get("log") or []]
    second = [dict(r, path=strip_front(r["path"])) for r in (run.get("second") or {}).get("log") or []]
    under = [r for r in first if r["path"].startswith(prefix)]
    requested = {r["path"][len(prefix):] for r in under}
    if requested != listed:
        bad.append(f"K2-1 first open requested {sorted(requested ^ listed)} off the manifest")
    for r in first:
        if r["status"] >= 400:
            bad.append(f"K2-1 first open: {r['status']} {r['path']}")
        elif r["path"].startswith(prefix) and r["status"] != 200:
            bad.append(f"K2-1 first open: {r['status']} {r['path']}")
        elif r["path"].startswith("/apps/litecore/r/") and not r["path"].startswith(prefix) \
                and not (r["path"] == ENTRY and r["status"] == 303):
            bad.append(f"K2-1 first open: {r['status']} {r['path']} is neither the entry nor this build")
    for r in under:
        name = r["path"][len(prefix):]
        if name != DOC and name in manifest["files"] and r["sent"] >= manifest["files"][name]["gzBytes"] + SLACK:
            bad.append(f"K2-2 {name}: {r['sent']} bytes sent, packaged {manifest['files'][name]['gzBytes']}")
    # The worker revalidates its manifest by design (cache: "no-cache"); a 304
    # carries no body.  Anything else under the build on a second open is bytes
    # downloaded again.
    again = [r for r in second if r["path"].startswith(prefix) and r["path"][len(prefix):] != DOC
             and r["status"] != 304]
    if again:
        bad.append(f"K2-3 second open fetched {len(again)} assets again: "
                   f"{sorted({(r['path'][len(prefix):], r['status']) for r in again})}")
    docs = [r for r in second if r["path"] == prefix + DOC]
    if len(docs) != 1:
        bad.append(f"K2-3 second open: {len(docs)} requests for the editor document")
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
    manifest = (report.get("package") or {}).get("manifest") or {}
    problems += score_package(report["package"]) if report.get("package") else ["K0 no package record"]
    problems += score_wire(report["wire"], manifest) if report.get("wire") and manifest else ["K1 no wire record"]
    tally: dict[str, dict[str, Any]] = {}
    for run in report.get("runs") or []:
        entry = tally.setdefault(run["browser"], {"pass": 0, "runs": 0, "problems": []})
        entry["runs"] += 1
        bad = score_run(run, manifest)
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


def _first_asset(run: dict, manifest: dict, suffix: str) -> dict:
    prefix = asset_prefix(manifest["buildId"])
    return next(r for r in run["first"]["log"] if strip_front(r["path"]).startswith(prefix)
                and strip_front(r["path"]).endswith(suffix))


def _wasm_path(m: dict) -> str:
    return next(p for p in m["files"] if p.endswith("probe.wasm"))


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
    ("K1-3", "a wrong build id redirects", lambda w, m: w["negatives"]["wrong build id"].update(status=303)),
    ("K1-3", "dot-dot is served", lambda w, m: w["negatives"]["dot-dot"].update(status=200)),
    ("K1-6", "no ETag", lambda w, m: w["files"][_wasm_path(m)]["gzip"]["headers"].pop("etag")),
    ("K1-6", "a conditional request answered with the body",
     lambda w, m: w["files"]["profiles/e2-editor-v8/sdk-manifest.json"]["conditional"].update(status=200, bodyBytes=2082)),
    ("K1-4", "the entry is not a redirect", lambda w, m: w["entry"].update(status=200)),
    ("K1-4", "the entry redirects to a scheme-relative URL",
     lambda w, m: w["entry"]["headers"].update(location=f"//index.php/apps/litecore/r/{m['buildId']}/{DOC}?fileId={w['entry']['fileId']}")),
    ("K1-5", "the document is immutable",
     lambda w, m: w["document"]["headers"].update({"cache-control": "private, max-age=31536000, immutable"})),
    ("K1-5", "the document has no COEP", lambda w, m: w["document"]["headers"].pop("cross-origin-embedder-policy")),
]

RUN_CASES = [
    ("K2-1", "a packaged file was never requested",
     lambda r, m: r["first"].update(log=[x for x in r["first"]["log"] if not x["path"].endswith("probe.js")])),
    ("K2-1", "a request off the manifest",
     lambda r, m: r["first"]["log"].append(dict(r["first"]["log"][0], path=f"/index.php{asset_prefix(m['buildId'])}x.js",
                                                target="x", status=200))),
    ("K2-1", "a 404 under the app",
     lambda r, m: r["first"]["log"].append(dict(r["first"]["log"][0], path="/apps-extra/litecore/js/x.js", status=404))),
    ("K2-1", "an asset answered 206", lambda r, m: _first_asset(r, m, "probe.wasm").update(status=206)),
    ("K2-2", "the wasm went over the wire uncompressed",
     lambda r, m: _first_asset(r, m, "probe.wasm").update(sent=m["files"][_wasm_path(m)]["bytes"])),
    ("K2-3", "the second open fetched the wasm again",
     lambda r, m: r["second"]["log"].append(dict(_first_asset(r, m, "probe.wasm")))),
    ("K2-3", "the second open fetched one small script again",
     lambda r, m: r["second"]["log"].append(dict(_first_asset(r, m, "sdk/document-sdk.js")))),
    ("K2-3", "the manifest revalidation came back with a body (shakedown 164501)",
     lambda r, m: r["second"]["log"].append(dict(_first_asset(r, m, "sdk-manifest.json"), status=200))),
    ("K2-3", "the second open never loaded the document",
     lambda r, m: r["second"].update(log=[x for x in r["second"]["log"] if not x["path"].endswith("/" + DOC)])),
    ("K2-4", "the host never finished the second open", lambda r, m: r["second"]["host"].update(done=False)),
    ("K2-4", "the host stranded the first open",
     lambda r, m: r["first"]["host"].update(stranded={"bytes": 1})),
    ("K2-4", "the caret was never placed", lambda r, m: r["first"]["caret"].update(latency="", timedOut=True)),
    ("K2-4", "the action did not land",
     lambda r, m: r["second"]["acted"].update(revision=r["second"]["caret"].get("revision"))),
    ("K2-5", "the second open was refused the lock (finding 105)",
     lambda r, m: r["second"]["host"].update(lock={"state": "refused", "status": 423})),
    ("K2-5", "leaving kept the lock",
     lambda r, m: r["first"]["leave"].append({"t": 10.1, "lock": "1"})),
    ("K2-5", "no watch after leaving", lambda r, m: r["second"].update(leave=[])),
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
    for clause, label, mutate in RUN_CASES:
        for browser in PLAN:
            base = next((r for r in report["runs"] if r["browser"] == browser and not score_run(r, manifest)), None)
            if base is None:
                print(f"  MISSING {clause} {label} [{browser}]: no clean run to mutate")
                failures += 1
                continue
            mutated = copy.deepcopy(base)
            mutate(mutated, manifest)
            judge(f"{label} [{browser}]", clause, score_run(mutated, manifest))
    static = copy.deepcopy(report)
    static["static"]["page"]["dist"] = "0" * 64
    judge("the served page is not the spec's", "static: page", score(static, strict=False)["problems"])
    return failures


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", choices=("shakedown", "counted"))
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
    dirty = subprocess.run(["git", "status", "--short"], cwd=DEFAULT_DDEV, capture_output=True, text=True).stdout.strip()
    if counted and dirty:
        print(f"refusing a counted run: the host repo has uncommitted changes:\n{dirty}")
        return 2
    if counted:
        static["testStatic"] = subprocess.run(["make", "-C", str(PROJECT), "test-e2-c-static"],
                                              capture_output=True, text=True).returncode
    instance = Instance(DEFAULT_DDEV)
    report: dict[str, Any] = {
        "runner": "check_m3_assets.py", "runnerSha256": sha256_file(Path(__file__)), "label": args.label,
        "startedAt": utc_now(), "static": static,
        "hostRepo": subprocess.run(["git", "log", "-1", "--format=%H %s"], cwd=DEFAULT_DDEV,
                                   capture_output=True, text=True).stdout.strip(),
        "hostDirty": dirty,
        "hostFiles": {name: sha256_file(DEFAULT_DDEV / name) for name in (
            "js/litecore-editor.js", "lib/Controller/EditorController.php", "templates/editor.php")},
        "instance": instance.describe(),
        "runs": [],
    }
    out = EVIDENCE / ("runs" if counted else "shakedown") / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        report["package"] = package_record(DEFAULT_DDEV)
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
