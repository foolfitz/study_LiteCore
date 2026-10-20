#!/usr/bin/env python3
"""M3 asset delivery, step 0 -- what the editor pulls from the server, and what
it pulls again.

Two passes against the `litecore` app, neither of which changes the app, the
product or dist/:

  wire     No browser.  Every file of the editor's closure (the page's static
           import graph plus what the worker's manifest names -- `closure()`),
           fetched through the app's `/r/` route once with `Accept-Encoding:
           gzip` and once without, redirects not followed.  Records status,
           the headers that decide caching and compression, and body size.

  browser  Per browser, ONE profile with its HTTP cache on ("warm"; every
           counted M3 run so far was "cold" = cache off): open the test file
           from Files, wait for the host's `done`, go back to Files, open it
           again, wait, go back.  The record of each open is the web
           container's Apache access log between two byte offsets -- every
           request that reached the server, its status and `%O` (bytes sent,
           headers included).  A request the browser answered from its cache
           is not in it.  Same instrument for both browsers.

  probe_m3_assets.py [--ddev DIR] [--browsers chrome,firefox]

Report: findings/evidence/m3-assets/assets-<UTC>.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
    DEFAULT_DDEV, FILES, FIXTURE, NAME, ROUTE, Instance)
from probe_m3_gate0_coep import (  # noqa: E402
    DIST, EventChrome, Wire, browser_login, firefox_profile, sha256_file, utc_now,
    wait_until)
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-assets"
PAGE_MODULE = "e2-editor-app.js"
# SPEC-M4-ods-in-nextcloud §3.5 (review C3): the package is the UNION of each
# page's closure -- that page's static import graph, its one hard-coded
# workerUrl, and that worker's manifest closure.  The editor and the read-only
# spreadsheet viewer share the SDK and the CJK pack; each has its own engine.
PAGES = {"e2-editor.html": "e2-editor-app.js", "ods-viewer.html": "ods-viewer-app.js"}
APP_ROUTE = "/apps/litecore/r/"
IMPORT = re.compile(r'^\s*(?:import|export)\b[^;]*?\bfrom\s*"(\.{1,2}/[^"]+)"', re.M | re.S)
WORKER_URL = re.compile(r'workerUrl:\s*"(\./[^"]+)"')
# Apache "combined" with mod_logio: %h %l %u %t "%r" %>s %O "%{Referer}i" "%{User-Agent}i"
LOG_LINE = re.compile(r'^(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+) [^"]*" (\d{3}) (\d+|-) "[^"]*" "([^"]*)"$')
LOG = "/var/log/apache2/access.log"


# --------------------------------------------------------------------------
# The closure, from the sources that decide it


def page_graph(root: Path, entry: str) -> list[str]:
    """The page's static module graph: every relative `import ... from` and
    `export ... from`, followed transitively.  No dynamic `import()` exists in
    these files (checked by `dynamic_imports`)."""
    seen: list[str] = []
    todo = [entry]
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.append(path)
        text = (root / path).read_text()
        base = Path(path).parent
        for spec in IMPORT.findall(text):
            target = (base / spec).as_posix()
            parts: list[str] = []
            for part in target.split("/"):
                if part == "..":
                    parts.pop()
                elif part not in (".", ""):
                    parts.append(part)
            todo.append("/".join(parts))
    return sorted(seen)


def dynamic_imports(root: Path, files: list[str]) -> dict[str, int]:
    return {f: n for f in files if (n := len(re.findall(r"\bimport\s*\(", (root / f).read_text())))}


def worker_closure(root: Path, worker: str) -> dict[str, Any]:
    """What the worker loads: itself, the manifest beside it, the manifest's
    artifactFiles, and the resource packs it loads at startup (sdk-worker.js
    `loadStartupResourcePacks`: `loadAtStartup === true` only; finding 085 --
    nothing ever loads the others)."""
    directory = Path(worker).parent
    manifest_path = directory / "sdk-manifest.json"
    manifest = json.loads((root / manifest_path).read_text())

    def norm(relative: str) -> str:
        parts: list[str] = []
        for part in (directory / relative).as_posix().split("/"):
            if part == "..":
                parts.pop()
            elif part not in (".", ""):
                parts.append(part)
        return "/".join(parts)

    files = {worker, manifest_path.as_posix()}
    files |= {norm(v) for v in manifest.get("artifactFiles", {}).values()}
    loaded, declared_only = [], []
    for pack in manifest.get("resourcePacks", []):
        pair = [norm(pack["data"]), norm(pack["metadata"])]
        (loaded if pack.get("loadAtStartup") is True else declared_only).extend(pair)
    files |= set(loaded)
    return {"files": sorted(files), "declaredNotLoaded": sorted(declared_only),
            "manifest": manifest_path.as_posix(), "profile": manifest.get("profile")}


def page_closure(root: Path, html: str, module: str) -> dict[str, Any]:
    """One page's closure: its static import graph, its ONE hard-coded workerUrl
    (comments included -- a second literal anywhere is refused), that worker's
    manifest closure, and the page itself."""
    page = page_graph(root, module)
    source = (root / module).read_text()
    workers = WORKER_URL.findall(source)
    if len(workers) != 1:
        raise RuntimeError(f"expected one hard-coded workerUrl in {module}, found {workers}")
    worker = worker_closure(root, workers[0][2:])
    return {"html": html, "module": module, "pageGraph": page,
            "dynamicImports": dynamic_imports(root, page), "worker": worker,
            "files": sorted(set(page) | set(worker["files"]) | {html})}


def closure(root: Path = DIST, pages: dict[str, str] = PAGES) -> dict[str, Any]:
    per_page = {html: page_closure(root, html, module) for html, module in pages.items()}
    files = sorted(set().union(*(set(p["files"]) for p in per_page.values())))
    # The editor page's own graph and worker stay at the top level: every older
    # reader of this record (the packager's `source.page`, K0's scorers) reads them there.
    editor = per_page.get("e2-editor.html") or next(iter(per_page.values()))
    return {
        "pages": per_page,
        "pageGraph": editor["pageGraph"], "dynamicImports": editor["dynamicImports"],
        "worker": editor["worker"],
        "files": [{"path": f, "bytes": (root / f).stat().st_size, "sha256": sha256_file(root / f)}
                  for f in files],
        "totalBytes": sum((root / f).stat().st_size for f in files),
    }


# --------------------------------------------------------------------------
# Wire pass


def wire_pass(instance: Instance, files: list[str]) -> list[dict[str, Any]]:
    wire = Wire(instance)
    wire.login()
    keep = ("content-type", "content-encoding", "content-length", "cache-control", "etag",
            "last-modified", "vary", "location", "cross-origin-embedder-policy",
            "content-security-policy")
    rows = []
    for path in files:
        if path == "e2-editor.html":
            continue
        row: dict[str, Any] = {"path": path}
        for label, encoding in (("gzip", "gzip"), ("identity", None)):
            request = urllib.request.Request(instance.base + APP_ROUTE + path)
            if encoding:
                request.add_header("Accept-Encoding", encoding)
            started = time.monotonic()
            try:
                response = wire.raw.open(request, timeout=300)
                status, headers, body = response.status, response.headers, response.read()
            except urllib.error.HTTPError as error:
                status, headers, body = error.code, error.headers, error.read()
            row[label] = {
                "status": status, "seconds": round(time.monotonic() - started, 3),
                "bodyBytes": len(body), "bodySha256": hashlib.sha256(body).hexdigest(),
                "headers": {k: headers.get(k) for k in keep if headers.get(k) is not None},
                # A response Nextcloud's PHP produced always carries its CSP; a file
                # Apache served from disk carries an ETag and no CSP.
                "servedBy": "php" if headers.get("content-security-policy") else "static",
            }
        rows.append(row)
    return rows


# --------------------------------------------------------------------------
# Browser pass


class AccessLog:
    def __init__(self, instance: Instance):
        self.instance = instance

    def offset(self) -> int:
        return int(self.instance._run(["ddev", "exec", "stat", "-c", "%s", LOG]).strip())

    def since(self, offset: int) -> list[dict[str, Any]]:
        text = self.instance._run(["ddev", "exec", "tail", "-c", f"+{offset + 1}", LOG])
        rows = []
        for line in text.splitlines():
            match = LOG_LINE.match(line)
            if not match:
                rows.append({"unparsed": line})
                continue
            client, when, method, target, status, sent, agent = match.groups()
            rows.append({"when": when, "method": method, "target": target,
                         "path": target.split("?", 1)[0], "status": int(status),
                         "sent": 0 if sent == "-" else int(sent), "agent": agent})
        return rows


def click_open(session, instance: Instance) -> dict[str, Any]:
    navigate(session, instance.base + FILES, timeout=120)
    selector = (f'[data-cy-files-list-row-name={json.dumps(NAME, ensure_ascii=False)}]'
                ' [data-cy-files-list-row-name-link]')
    record: dict[str, Any] = {"filesRow": wait_until(
        session, f"(() => document.querySelector({json.dumps(selector)}) !== null)()", 60)}
    started = time.monotonic()
    session.click(selector)
    record["landed"] = wait_until(
        session, f"(() => location.pathname.endsWith({json.dumps(ROUTE)}) && location.href)()", 60)
    raw = wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                              " return v && JSON.parse(v).done && v; })()", 300)
    record["secondsToDone"] = round(time.monotonic() - started, 2)
    record["host"] = json.loads(raw) if isinstance(raw, str) else {"notReported": raw}
    return record


def summarize(rows: list[dict[str, Any]], agent: str) -> dict[str, Any]:
    mine = [r for r in rows if agent in r.get("agent", "")]
    app = [r for r in mine if "/litecore/" in r["path"]]
    by_path: dict[str, dict[str, Any]] = {}
    for r in app:
        entry = by_path.setdefault(r["path"], {"requests": 0, "statuses": [], "sent": 0})
        entry["requests"] += 1
        entry["statuses"].append(r["status"])
        entry["sent"] += r["sent"]
    return {
        "requestsAll": len(mine), "sentAll": sum(r["sent"] for r in mine),
        "requestsApp": len(app), "sentApp": sum(r["sent"] for r in app),
        "app": dict(sorted(by_path.items())),
        "unparsed": [r["unparsed"] for r in rows if "unparsed" in r][:20],
    }


def browser_pass(kind: str, instance: Instance, scratch: Path) -> dict[str, Any]:
    log = AccessLog(instance)
    record: dict[str, Any] = {"browser": kind, "cache": "warm"}
    record["upload"] = instance.upload(FIXTURE, NAME)
    session = (EventChrome("warm") if kind == "chrome"
               else FirefoxSession("warm", profile_dir=firefox_profile(scratch)))
    record["version"] = getattr(session, "version", None)
    agent = "Chrome" if kind == "chrome" else "Firefox"
    try:
        record["login"] = browser_login(session, instance.base, instance.password)
        for label in ("first", "second"):
            start = log.offset()
            record[label] = click_open(session, instance)
            navigate(session, instance.base + FILES, timeout=120)
            time.sleep(3)   # the host's unlock on leaving lands in 0.3-0.4 s
            record[label]["log"] = summarize(log.since(start), agent)
    except Exception:  # noqa: BLE001 -- a pass that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        session.close()
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ddev", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--browsers", default="chrome,firefox")
    args = parser.parse_args()
    instance = Instance(args.ddev)
    report: dict[str, Any] = {"schema": "m3-assets-step0/1", "startedAt": utc_now(),
                              "probe": sha256_file(Path(__file__)), "instance": instance.describe()}
    report["closure"] = closure()
    report["wire"] = wire_pass(instance, [f["path"] for f in report["closure"]["files"]])
    with tempfile.TemporaryDirectory(dir=PROJECT / "build") as scratch:
        report["browsers"] = [browser_pass(kind, instance, Path(scratch) / kind)
                              for kind in args.browsers.split(",")]
    report["completedAt"] = utc_now()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"assets-{report['startedAt'].replace(':', '')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(out)
    for b in report["browsers"]:
        for label in ("first", "second"):
            log = b.get(label, {}).get("log", {})
            print(b["browser"], label, b.get(label, {}).get("secondsToDone"), "s",
                  log.get("requestsApp"), "app requests", log.get("sentApp"), "bytes to app")
        if "fatal" in b:
            print(b["browser"], "FATAL", b["fatal"].splitlines()[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
