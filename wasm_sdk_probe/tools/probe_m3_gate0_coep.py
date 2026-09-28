#!/usr/bin/env python3
"""M3 gate 0 -- can a cross-origin-isolated page live inside Nextcloud, and in
which shape.  Criteria and predictions: handoff/m3-gate-0/PREDICTION.md, written
before the first counted run.  This runner only MEASURES and SCORES; it never
changes the probe app, the product, or dist/.

The Nextcloud side is a DDEV project built with the owner's ddev-nextcloud-app
scaffold (default: ~/Projects/Nextcloud_Apps/litecoreprobe), core = the official
34.0.2 release tarball, the probe app `litecoreprobe` in apps-extra, and
wasm_sdk_probe/dist mounted read-only at /mnt/litecore-dist.

What a cell means is decided by the raw fields the page probe (js/probe.js)
records; the scoring below reads those fields and nothing the page concluded.
Every criterion that cannot be scored says NOT_MEASURED with the reason --
a missing field is never read as a pass.
"""

from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import re
import ssl
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate  # noqa: E402
from run_browser_probe import (  # noqa: E402
    WEBDRIVER_ELEMENT_KEY, ChromeSession, FirefoxSession)
from run_e2_c_page_smoke import POINT_AT, PRESS, READ_STATE, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
DIST = PROJECT / "dist"
EVIDENCE = REPO / "findings" / "evidence" / "m3-gate-0"
DEFAULT_DDEV = Path.home() / "Projects" / "Nextcloud_Apps" / "litecoreprobe"
MKCERT_CA = Path.home() / ".local" / "share" / "mkcert" / "rootCA.pem"
APP = "/apps/litecoreprobe"
# The files that decide what the editor arms ran.  Hashed from dist/ on the host;
# the container sees the same bytes through a read-only bind mount.
PRODUCT_FILES = [
    "e2-editor.html", "e2-editor-app.js", "sdk/document-sdk.js",
    "profiles/e2-editor-v8/sdk-worker.js", "profiles/e2-editor-v8/probe.js",
    "profiles/e2-editor-v8/probe.wasm", "profiles/e2-editor-v8/sdk-manifest.json",
]
# Chrome reports these for requests the page itself dropped (navigation away,
# a terminated worker); they are not blocks.
BENIGN_ERRORS = {"net::ERR_ABORTED"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------
# Nextcloud side


class Instance:
    def __init__(self, ddev_root: Path):
        self.root = ddev_root
        described = json.loads(self._run(["ddev", "describe", "-j"]))["raw"]
        self.base = described["primary_url"].rstrip("/")
        self.webserver = described.get("webserver_type")
        self.password = self._password()

    def _run(self, argv: list[str]) -> str:
        return subprocess.run(argv, cwd=self.root, check=True, capture_output=True,
                              text=True, timeout=300).stdout

    def _password(self) -> str:
        text = (self.root / ".ddev" / "config.local.yaml").read_text()
        match = re.search(r"NEXTCLOUD_ADMIN_PASSWORD=(\S+)", text)
        if not match:
            raise RuntimeError("no NEXTCLOUD_ADMIN_PASSWORD in .ddev/config.local.yaml")
        return match.group(1)

    def occ(self, *args: str) -> str:
        return self._run(["ddev", "occ", *args])

    def set_app(self, key: str, value: str) -> None:
        self.occ("config:app:set", "litecoreprobe", key, f"--value={value}")

    def describe(self) -> dict[str, Any]:
        status = json.loads(self.occ("status", "--output=json"))
        apps = json.loads(self.occ("app:list", "--output=json"))
        system = {key: self.occ("config:system:get", key).strip() for key in ("debug", "loglevel")}
        commit = self._run(["git", "rev-parse", "HEAD"]).strip()
        dirty = self._run(["git", "status", "--porcelain"]).strip()
        app_files = {}
        for name in self._run(["git", "ls-files"]).split():
            path = self.root / name
            if path.is_file() and not path.is_symlink():
                app_files[name] = sha256_file(path)
        return {
            "baseUrl": self.base, "webserver": self.webserver,
            "nextcloud": status, "enabledApps": sorted(apps.get("enabled", {})),
            "system": system, "canaryOrigin": self.occ(
                "config:app:get", "litecoreprobe", "canary_origin").strip(),
            "probeApp": {"repo": str(self.root), "commit": commit,
                         "dirty": dirty.splitlines(), "files": app_files},
        }


class Wire:
    """What the server sends, read without a browser -- the only header record
    Firefox arms get, and the check that an arm's headers are what it claims."""

    def __init__(self, instance: Instance):
        self.instance = instance
        context = ssl.create_default_context(cafile=str(MKCERT_CA))
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context),
            urllib.request.HTTPCookieProcessor(self.jar))

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):  # noqa: ANN002, ANN003
                return None
        self.raw = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context),
            urllib.request.HTTPCookieProcessor(self.jar), NoRedirect())

    def login(self) -> None:
        page = self.opener.open(self.instance.base + "/login", timeout=30).read().decode()
        token = re.search(r'data-requesttoken="([^"]+)"', page)
        if not token:
            raise RuntimeError("no requesttoken on the login page")
        body = urllib.parse.urlencode({
            "user": "admin", "password": self.instance.password,
            "requesttoken": token.group(1)}).encode()
        # Nextcloud 34 refuses a login POST whose Origin is not a trusted domain
        # (LoginController::tryLogin); a browser sends it, urllib does not.
        request = urllib.request.Request(self.instance.base + "/login", data=body,
                                         headers={"Origin": self.instance.base})
        final = self.opener.open(request, timeout=30)
        if "/login" in final.geturl():
            raise RuntimeError(f"wire login failed, ended at {final.geturl()}")

    def head(self, path: str) -> dict[str, Any]:
        url = self.instance.base + path
        try:
            response = self.raw.open(url, timeout=60)
            status, headers, body = response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            status, headers, body = error.code, error.headers, error.read()
        keep = ("cross-origin-opener-policy", "cross-origin-embedder-policy",
                "cross-origin-resource-policy", "document-isolation-policy",
                "content-security-policy", "content-type", "location")
        return {"path": path, "status": status,
                "headers": {k: headers.get(k) for k in keep if headers.get(k) is not None},
                "bodySha256": hashlib.sha256(body).hexdigest(), "bodyBytes": len(body)}


# --------------------------------------------------------------------------
# Browsers


class EventChrome(ChromeSession):
    """ChromeSession that keeps the CDP events the base class reads and drops.
    Only the ones the scoring uses are kept."""

    KEEP = {"Network.requestWillBeSent", "Network.responseReceived",
            "Network.loadingFailed", "Log.entryAdded", "Runtime.exceptionThrown"}

    def __init__(self, *args: Any, **kwargs: Any):
        self.events: list[dict[str, Any]] = []
        super().__init__(*args, **kwargs)
        self.call("Log.enable")

    def call(self, method: str, params: dict[str, Any] | None = None,
             timeout: float = 180, session_id: str | None = None) -> dict[str, Any]:
        self.next_id += 1
        message_id = self.next_id
        message = {"id": message_id, "method": method, "params": params or {}}
        if session_id is not None:
            message["sessionId"] = session_id
        self.websocket.send(json.dumps(message))
        while True:
            response = json.loads(self.websocket.recv(timeout=timeout))
            if "id" not in response:
                if response.get("method") in self.KEEP:
                    self.events.append(response)
                continue
            if response.get("id") != message_id:
                continue
            if "error" in response:
                raise RuntimeError(f"CDP {method}: {response['error']}")
            return response.get("result", {})

    def drain(self) -> list[dict[str, Any]]:
        self.call("Runtime.evaluate", {"expression": "1"})
        events, self.events = self.events, []
        return events


def summarize_cdp(events: list[dict[str, Any]]) -> dict[str, Any]:
    urls: dict[str, str] = {}
    documents, failed, logs, exceptions = [], [], [], []
    for event in events:
        method, params = event["method"], event.get("params", {})
        if method == "Network.requestWillBeSent":
            urls[params["requestId"]] = params["request"]["url"]
        elif method == "Network.responseReceived" and params.get("type") == "Document":
            headers = {k.lower(): v for k, v in params["response"].get("headers", {}).items()}
            documents.append({"url": params["response"]["url"], "status": params["response"]["status"],
                              "coop": headers.get("cross-origin-opener-policy"),
                              "coep": headers.get("cross-origin-embedder-policy"),
                              "dip": headers.get("document-isolation-policy")})
        elif method == "Network.loadingFailed":
            failed.append({"url": urls.get(params["requestId"]), "type": params.get("type"),
                           "errorText": params.get("errorText"),
                           "blockedReason": params.get("blockedReason"),
                           "corsError": (params.get("corsErrorStatus") or {}).get("corsError")})
        elif method == "Log.entryAdded" and params["entry"].get("level") == "error":
            logs.append({"source": params["entry"].get("source"), "text": params["entry"].get("text"),
                         "url": params["entry"].get("url")})
        elif method == "Runtime.exceptionThrown":
            details = params.get("exceptionDetails", {})
            exceptions.append((details.get("exception") or {}).get("description") or details.get("text"))
    return {"documents": documents, "loadingFailed": failed, "errorLogs": logs, "exceptions": exceptions}


def firefox_profile(scratch: Path) -> Path:
    """A profile that trusts the mkcert CA, so Firefox sees the same valid
    HTTPS origin Chrome does (Chrome reads ~/.pki/nssdb, where mkcert put it)."""
    profile = scratch / "firefox-profile"
    profile.mkdir(parents=True)
    subprocess.run(["certutil", "-N", "-d", f"sql:{profile}", "--empty-password"], check=True)
    subprocess.run(["certutil", "-A", "-d", f"sql:{profile}", "-n", "mkcert-dev-ca",
                    "-t", "C,,", "-i", str(MKCERT_CA)], check=True)
    return profile


def wait_until(session, script: str, timeout: float, poll: float = 0.3) -> Any:
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            value = evaluate(session, script)
            if value:
                return value
        except Exception as error:  # noqa: BLE001 -- kept, not swallowed
            last_error = f"{type(error).__name__}: {error}"
        time.sleep(poll)
    return {"timedOut": True, "lastError": last_error}


def browser_login(session, base: str, password: str) -> dict[str, Any]:
    navigate(session, base + "/login", timeout=60)
    if isinstance(session, ChromeSession):
        # CDP evaluates in the page's own global: a same-origin form POST.
        session.evaluate(
            "(() => { window.__m3login = null;"
            " fetch('/login', {method: 'POST', body: new URLSearchParams({"
            f"user: 'admin', password: {json.dumps(password)},"
            " requesttoken: document.head.dataset.requesttoken})})"
            ".then((r) => { window.__m3login = {status: r.status, url: r.url}; })"
            ".catch((e) => { window.__m3login = {error: String(e)}; }); return true; })()")
        result = wait_until(session, "(() => window.__m3login)()", 30)
    else:
        # WebDriver: the real form, typed.
        wait_until(session, "(() => document.querySelector('#user') !== null)()", 30)
        for selector, text in (("#user", "admin"), ("#password", password)):
            element = session.command("POST", "/element", {"using": "css selector", "value": selector})
            session.command("POST", f"/element/{element[WEBDRIVER_ELEMENT_KEY]}/value", {"text": text})
        session.click('button[type="submit"]')
        result = wait_until(session, "(() => !location.pathname.endsWith('/login') && location.href)()", 30)
    return {"result": result}


def read_probe(session, timeout: float = 120) -> dict[str, Any]:
    raw = wait_until(
        session, "(() => document.documentElement.getAttribute('data-m3'))()", timeout)
    if isinstance(raw, str):
        return json.loads(raw)
    return {"notReported": raw,
            "location": evaluate(session, "(() => location.href)()")}


def run_page(session, url: str) -> dict[str, Any]:
    if isinstance(session, EventChrome):
        session.drain()
    started = time.monotonic()
    navigate(session, url, timeout=120)
    page = read_probe(session)
    record = {"url": url, "page": page, "seconds": round(time.monotonic() - started, 2)}
    if isinstance(session, EventChrome):
        record["cdp"] = summarize_cdp(session.drain())
    return record


def run_after_click_through(session, first: str, then: str) -> dict[str, Any]:
    """A6: a renderer-initiated navigation from a non-isolated Nextcloud page."""
    navigate(session, first, timeout=120)
    if isinstance(session, EventChrome):
        session.drain()
    evaluate(session, f"(() => {{ location.assign({json.dumps(then)}); return true; }})()")
    time.sleep(1.0)
    page = read_probe(session)
    record = {"url": then, "from": first, "page": page}
    if isinstance(session, EventChrome):
        record["cdp"] = summarize_cdp(session.drain())
    return record


def run_editor(session, url: str, action: str, timeout: float) -> dict[str, Any]:
    """The page-smoke sequence of run_e2_c_page_smoke.py, on a Nextcloud route."""
    if isinstance(session, EventChrome):
        session.drain()
    record: dict[str, Any] = {"url": url, "steps": []}
    started = time.monotonic()
    navigate(session, url, timeout=120)

    def state_until(predicate, limit):
        deadline = time.monotonic() + limit
        state = None
        while time.monotonic() < deadline:
            try:
                state = evaluate(session, READ_STATE)
            except Exception as error:  # noqa: BLE001
                state = {"readError": f"{type(error).__name__}: {error}"}
            if state and predicate(state):
                return state
            time.sleep(0.5)
        return state

    booted = state_until(lambda s: s.get("state") in ("ready", "stopped", "expired",
                                                       "restart-required"), timeout)
    record["steps"].append({"step": "boot", "state": booted,
                            "seconds": round(time.monotonic() - started, 2)})
    record["canvas"] = evaluate(session, "(() => { const c = document.querySelector('#canvas');"
                                         " if (!c) return null; const r = c.getBoundingClientRect();"
                                         " return {width: r.width, height: r.height, top: r.top, left: r.left}; })()")
    record["failedAt"] = None
    if not booted or booted.get("state") != "ready":
        record["failedAt"] = "boot"
    else:
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        caret = state_until(lambda s: "定位游標" in (s.get("latency") or ""), 60)
        record["steps"].append({"step": "place-caret", "state": caret})
        if not caret or "失敗" in (caret.get("latency") or "") or "定位游標" not in (caret.get("latency") or ""):
            record["failedAt"] = "place-caret"
        else:
            evaluate(session, PRESS.replace("ARG_ACTION", action))
            acted = state_until(lambda s: s.get("revision") != caret["revision"]
                                or "失敗" in (s.get("latency") or ""), 120)
            record["steps"].append({"step": action, "state": acted})
            before, after = caret.get("revision"), (acted or {}).get("revision")
            record["revisionBefore"], record["revisionAfter"] = before, after
            if not (before and after and before.isdigit() and after.isdigit()
                    and int(after) == int(before) + 1 and "失敗" not in (acted.get("latency") or "")):
                record["failedAt"] = action
    record["passed"] = record["failedAt"] is None
    record["probe"] = read_probe(session, timeout=30)
    if isinstance(session, EventChrome):
        record["cdp"] = summarize_cdp(session.drain())
    return record


def open_browser(kind: str, instance: Instance, scratch: Path):
    if kind == "chrome":
        session = EventChrome("cold")
    else:
        session = FirefoxSession("cold", profile_dir=firefox_profile(scratch))
    login = browser_login(session, instance.base, instance.password)
    return session, login


# --------------------------------------------------------------------------
# Arms


def page_url(layout: str, coep: str, frame: str = "none") -> str:
    return f"{APP}/page?layout={layout}&coep={coep}&frame={frame}&canary=1"


def editor_url(mode: str, layout: str, coep: str) -> str:
    return f"{APP}/r/{mode}/e2-editor.html?layout={layout}&coep={coep}"


PAGE_ARMS = {
    "A0": page_url("user", "none"),
    "A1": page_url("user", "require-corp"),
    "A2": page_url("user", "credentialless"),
    "A4": page_url("user", "none", "coep"),
    "A4d": page_url("user", "none", "dip"),
}
EDITOR_ARMS = {
    "E1": editor_url("static", "user", "require-corp"),
    "E1h": editor_url("php", "user", "require-corp"),
    "E3": editor_url("php", "base", "require-corp"),
    # Negative control: the same page and assets as E1h with no isolation. It
    # must FAIL, or the sequence cannot tell isolation from its absence.
    "E0": editor_url("php", "user", "none"),
}
FILES = "/apps/files/"


def wire_checks(wire: Wire) -> list[dict[str, Any]]:
    paths = list(PAGE_ARMS.values()) + [f"{APP}/bare?isolation={i}" for i in ("coep", "dip")]
    paths += list(EDITOR_ARMS.values())
    paths += ["/apps-extra/litecoreprobe/js/probe-worker.js",
              "/apps-extra/litecoreprobe/js/coep/probe-worker.js",
              f"{APP}/w/probe-worker.js",
              f"{APP}/r/static/profiles/e2-editor-v8/sdk-worker.js",
              f"{APP}/r/php/profiles/e2-editor-v8/sdk-worker.js",
              f"{APP}/r/php/profiles/e2-editor-v8/probe.js",
              f"{APP}/r/php/profiles/e2-editor-v8/probe.wasm",
              "/apps-extra/litecoreprobe/dist/profiles/e2-editor-v8/probe.js"]
    return [wire.head(path) for path in paths]


# C7 (observation): which of the files a profile needs does the web server hand
# out as a static app file.  Nextcloud's .htaccess routes extensions outside its
# whitelist to index.php once pretty URLs are on; the answer is read off the
# wire, not off the whitelist, so it stays true if Nextcloud changes the list.
STATIC_FILES = [
    "e2-editor-app.js", "e1-fixtures/list-contexts.odt",
    "profiles/e2-editor-v8/sdk-worker.js", "profiles/e2-editor-v8/probe.wasm",
    "profiles/e2-editor-v8/sdk-manifest.json",
    "profiles/e2-editor-v14/sdk-manifest.json",
    "profiles/e2-editor-v14/base-e2-editor-v14.9901e9be29c9ded2.data",
    "profiles/e2-editor-v14/base-e2-editor-v14.b1e48f2b7ac50b60.metadata",
]


def static_checks(wire: Wire) -> list[dict[str, Any]]:
    rows = []
    for name in STATIC_FILES:
        row = wire.head(f"/apps-extra/litecoreprobe/dist/{name}")
        row["onDisk"] = {"bytes": (DIST / name).stat().st_size, "sha256": sha256_file(DIST / name)}
        row["servedTheFile"] = row["status"] == 200 and row["bodySha256"] == row["onDisk"]["sha256"]
        rows.append(row)
    return rows


def set_files_isolation(instance: Instance, wire: Wire, on: bool) -> dict[str, Any]:
    """Nextcloud 34 caches app config in the web server's APCu for 3 s
    (AppConfig::LOCAL_CACHE_TTL) and occ cannot clear it, so a toggle is only
    believed once the Files response on the wire shows it."""
    instance.set_app("files_isolation", "on" if on else "off")
    deadline = time.monotonic() + 30
    row = None
    while time.monotonic() < deadline:
        row = wire.head(FILES)
        if (row["headers"].get("cross-origin-embedder-policy") == "require-corp") == on:
            return {"verified": True, "wire": row}
        time.sleep(1)
    return {"verified": False, "wire": row}


def run_browser(kind: str, instance: Instance, wire: Wire, scratch: Path, repeats: int,
                action: str, editor_timeout: float) -> dict[str, Any]:
    result: dict[str, Any] = {"browser": kind, "pages": {}, "editor": {}}
    session, login = open_browser(kind, instance, scratch / f"{kind}-pages")
    result["login"] = login
    result["version"] = session.version
    try:
        for arm, path in PAGE_ARMS.items():
            result["pages"][arm] = run_page(session, instance.base + path)
        # A5: the Files page, control then isolated (listener switched by occ).
        instance.set_app("files_probe", "on")
        try:
            toggle = set_files_isolation(instance, wire, False)
            result["pages"]["A5-control"] = run_page(session, instance.base + FILES)
            result["pages"]["A5-control"]["toggle"] = toggle
            toggle = set_files_isolation(instance, wire, True)
            result["pages"]["A5"] = run_page(session, instance.base + FILES)
            result["pages"]["A5"]["toggle"] = toggle
        finally:
            result["filesRestored"] = set_files_isolation(instance, wire, False)
            instance.set_app("files_probe", "off")
        time.sleep(4)  # past the 3 s APCu window, so A6 starts from a plain Files page
        result["pages"]["A6"] = run_after_click_through(
            session, instance.base + FILES, instance.base + PAGE_ARMS["A1"])
        # Noise control for C3: the control page again, last.
        result["pages"]["A0b"] = run_page(session, instance.base + PAGE_ARMS["A0"])
    finally:
        session.close()

    for arm, path in EDITOR_ARMS.items():
        runs = []
        for attempt in range(1 if arm == "E0" else repeats):
            session, login = open_browser(kind, instance, scratch / f"{kind}-{arm}-{attempt}")
            try:
                record = run_editor(session, instance.base + path, action, editor_timeout)
                record["login"] = login
                runs.append(record)
            finally:
                session.close()
        result["editor"][arm] = runs
    return result


# --------------------------------------------------------------------------
# Scoring -- reads only raw fields.


def failed_loads(record: dict[str, Any], canary_origin: str) -> dict[str, list[str]]:
    """Loads that failed on this page, split into Nextcloud's own and the
    probe's (canary, workers), because C3 asks only about Nextcloud's."""
    page = record.get("page") or {}
    urls = set()
    for image in page.get("images") or []:
        if image.get("broken"):
            urls.add(image["src"])
    for error in page.get("errors") or []:
        if error.get("kind") == "element":
            urls.add(error["url"])
    for failure in (record.get("cdp") or {}).get("loadingFailed") or []:
        if failure.get("url") and (failure.get("blockedReason")
                                   or failure.get("errorText") not in BENIGN_ERRORS):
            urls.add(failure["url"])
    own = sorted(u for u in urls if not (u.startswith(canary_origin) or "/litecoreprobe/" in u))
    probe = sorted(u for u in urls if u not in own)
    return {"nextcloud": own, "probe": probe}


FINGERPRINT_FIELDS = ("present", "elements", "idCount", "appMenu", "userMenu", "images",
                      "imagesLoaded", "buttons", "links", "filesRows", "appMenuEntries")


def fingerprint(record: dict[str, Any]) -> dict[str, Any] | None:
    page = record.get("page") or {}
    header = page.get("header")
    if not header:
        return None
    values = {k: header.get(k) for k in FINGERPRINT_FIELDS if k != "appMenuEntries"}
    values["appMenuEntries"] = (page.get("appMenuOpened") or {}).get("entries")
    return values


def compare(control: dict | None, again: dict | None, subject: dict | None,
            noisy_from: list[str] | None = None) -> dict[str, Any]:
    """Fields equal between the control and its repeat are judged; fields that
    differ between two runs of the SAME page are noise and are only reported.
    A page without its own repeat (Files) borrows the noise measured on A0/A0b."""
    if control is None or subject is None:
        return {"judged": [], "noisy": [], "differs": ["<missing fingerprint>"], "equal": False}
    noisy = [k for k in FINGERPRINT_FIELDS if (again is not None and control.get(k) != again.get(k))
             or (noisy_from is not None and k in noisy_from)]
    judged = [k for k in FINGERPRINT_FIELDS if k not in noisy]
    differs = [k for k in judged if control.get(k) != subject.get(k)]
    return {"judged": judged, "noisy": noisy, "differs": differs, "equal": not differs}


def isolated(record: dict[str, Any]) -> bool | None:
    page = record.get("page") or {}
    value = (page.get("isolation") or {}).get("crossOriginIsolated")
    return value if isinstance(value, bool) else None


def canary_loaded(record: dict[str, Any]) -> bool | None:
    canary = (record.get("page") or {}).get("canary")
    if not canary:
        return None
    return canary.get("event") == "load" and (canary.get("naturalWidth") or 0) > 0


def workers(record: dict[str, Any]) -> dict[str, str]:
    return {w["id"]: w.get("outcome") for w in (record.get("page") or {}).get("workers") or []}


def score_browser(result: dict[str, Any], canary_origin: str, repeats: int) -> dict[str, Any]:
    pages = result["pages"]
    a0, a1 = pages.get("A0", {}), pages.get("A1", {})
    scores: dict[str, Any] = {}

    c1 = {"A0.isolated": isolated(a0), "A1.isolated": isolated(a1),
          "A0.canaryLoaded": canary_loaded(a0), "A1.canaryLoaded": canary_loaded(a1),
          "A1.canaryReportedFailed": any(u.startswith(canary_origin)
                                         for u in failed_loads(a1, canary_origin)["probe"])}
    c1["holds"] = (c1["A0.isolated"] is False and c1["A1.isolated"] is True
                   and c1["A0.canaryLoaded"] is True and c1["A1.canaryLoaded"] is False
                   and c1["A1.canaryReportedFailed"] is True)
    scores["C1"] = c1

    e = {}
    for arm, runs in result["editor"].items():
        e[arm] = {"passed": sum(1 for r in runs if r.get("passed")), "of": len(runs),
                  "failedAt": [r.get("failedAt") for r in runs],
                  "canvas": [r.get("canvas") for r in runs],
                  "bootStates": [((r.get("steps") or [{}])[0].get("state") or {}).get("state") for r in runs]}
    scores["C2"] = e

    if not c1["holds"]:
        scores["C3"] = {"verdict": "VOID", "why": "C1 does not hold: the failed-load detector is unproven"}
    else:
        f0, f1 = failed_loads(a0, canary_origin), failed_loads(a1, canary_origin)
        new = sorted(set(f1["nextcloud"]) - set(f0["nextcloud"]))
        fp0, fp0b, fp1 = fingerprint(a0), fingerprint(pages.get("A0b", {})), fingerprint(a1)
        comparison = compare(fp0, fp0b, fp1)
        # The menu check is dead if the control itself shows no entries.
        menu_live = bool(fp0 and (fp0.get("appMenuEntries") or 0) > 0)
        scores["C3"] = {"newFailuresInA1": new, "A0.failures": f0["nextcloud"],
                        "fingerprintA0": fp0, "fingerprintA0b": fp0b, "fingerprintA1": fp1,
                        "comparison": comparison, "appMenuCheckLive": menu_live,
                        "holds": not new and comparison["equal"] and menu_live}

    def frame_isolation(arm: str) -> Any:
        frame = (pages.get(arm, {}).get("page") or {}).get("frame") or {}
        report = frame.get("report") or {}
        return {"outcome": frame.get("outcome"),
                "isolated": (report.get("isolation") or {}).get("crossOriginIsolated"),
                "workers": {w["id"]: w.get("outcome") for w in report.get("workers") or []}}
    scores["C4"] = {"A4": frame_isolation("A4"), "A4d": frame_isolation("A4d")}

    ctrl, a5 = pages.get("A5-control", {}), pages.get("A5", {})
    c5 = {"A5.isolated": isolated(a5), "A5-control.isolated": isolated(ctrl),
          "A5.canaryLoaded": canary_loaded(a5), "A5-control.canaryLoaded": canary_loaded(ctrl)}
    if c1["holds"]:
        fc, f5 = failed_loads(ctrl, canary_origin), failed_loads(a5, canary_origin)
        c5["newFailuresInA5"] = sorted(set(f5["nextcloud"]) - set(fc["nextcloud"]))
        c5["comparison"] = compare(fingerprint(ctrl), None, fingerprint(a5),
                                   noisy_from=scores["C3"]["comparison"]["noisy"])
        c5["toggleVerified"] = [(pages.get(k, {}).get("toggle") or {}).get("verified")
                                for k in ("A5-control", "A5")]
    else:
        c5["newFailuresInA5"] = "VOID (C1)"
    scores["C5"] = c5

    scores["C6"] = {arm: workers(pages.get(arm, {})) for arm in ("A0", "A1", "A2", "A5", "A6")}
    scores["A2"] = {"isolated": isolated(pages.get("A2", {})), "canaryLoaded": canary_loaded(pages.get("A2", {}))}
    scores["A6"] = {"isolated": isolated(pages.get("A6", {})),
                    "referrer": (pages.get("A6", {}).get("page") or {}).get("referrer")}
    return scores


def gate(scores: dict[str, dict[str, Any]], repeats: int) -> dict[str, Any]:
    browsers = sorted(scores)
    unmeasured = [b for b in browsers if "NOT_MEASURED" in scores[b]]
    if unmeasured:
        return {"browsers": browsers, "verdict": "NOT_MEASURED", "unmeasured": unmeasured}
    shapes = []
    for arm in ("E1", "E1h", "E3"):
        if all(scores[b]["C2"].get(arm, {}).get("passed") == repeats
               and scores[b]["C2"].get(arm, {}).get("of") == repeats for b in browsers):
            shapes.append(arm)
    control_failed = all(scores[b]["C2"].get("E0", {}).get("passed") == 0
                         and scores[b]["C2"].get("E0", {}).get("of") == 1 for b in browsers)
    return {"browsers": browsers, "shapesPassingBothBrowsers": shapes,
            "negativeControlFailedEverywhere": control_failed,
            "C1HoldsEverywhere": all(scores[b]["C1"]["holds"] for b in browsers),
            "verdict": ("PASS" if shapes and control_failed else
                        "INSTRUMENT" if not control_failed else "STOP")}


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--action", default="set-paragraph-heading")
    parser.add_argument("--editor-timeout", type=float, default=240)
    parser.add_argument("--label", choices=("shakedown", "counted"), required=True,
                        help="shakedown runs check the instrument and never count toward a criterion")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    instance = Instance(args.ddev_root)
    report: dict[str, Any] = {
        "probe": "m3-gate-0", "label": args.label, "startedAt": utc_now(),
        "criteria": "handoff/m3-gate-0/PREDICTION.md",
        "instance": instance.describe(),
        "product": {name: sha256_file(DIST / name) for name in PRODUCT_FILES},
        "runner": {"path": str(Path(__file__).relative_to(REPO)), "sha256": sha256_file(Path(__file__))},
        "repeats": args.repeats, "action": args.action,
    }
    if args.label == "counted" and report["instance"]["probeApp"]["dirty"]:
        raise SystemExit("refusing a counted run: the probe app has uncommitted changes, "
                         "so the report could not name the bytes that ran")
    canary_origin = report["instance"]["canaryOrigin"]
    wire = Wire(instance)
    wire.login()
    report["wire"] = wire_checks(wire)
    report["staticFiles"] = static_checks(wire)

    report["browsers"] = {}
    # Under build/, not /tmp: snap-packaged Firefox and geckodriver have a
    # private /tmp and cannot see a profile created there.
    (PROJECT / "build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m3-gate0-", dir=PROJECT / "build") as scratch:
        for kind in args.browsers.split(","):
            try:
                report["browsers"][kind] = run_browser(kind, instance, wire, Path(scratch), args.repeats,
                                                       args.action, args.editor_timeout)
            except Exception:  # noqa: BLE001 -- recorded, and scored as not measured
                report["browsers"][kind] = {"browser": kind, "fatal": traceback.format_exc()}
    report["scores"] = {kind: (score_browser(result, canary_origin, args.repeats) if "fatal" not in result
                               else {"NOT_MEASURED": result["fatal"].strip().splitlines()[-1]})
                        for kind, result in report["browsers"].items()}
    # Provisional only. fable's ruling (handoff/m3-gate-0/RULING.md, D1-D7) showed
    # this function green on false inputs; the verdict is check_m3_gate0_report.py's.
    report["provisionalGate"] = gate(report["scores"], args.repeats)
    report["provisionalGate"]["note"] = "not the verdict: run tools/check_m3_gate0_report.py on this file"
    report["completedAt"] = utc_now()

    out = args.out or (EVIDENCE / ("runs" if args.label == "counted" else "shakedown") /
                       f"{report['startedAt'].replace(':', '').replace('+0000', 'Z')}-{instance.webserver}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"report": str(out), "provisionalGate": report["provisionalGate"],
                      "scores": report["scores"]}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
