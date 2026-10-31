#!/usr/bin/env python3
"""M3 locks and permissions: arms K1-K11 of specs/SPEC-M3-locks-and-permissions.md §4.

The `litecore` app's host takes a WebDAV token lock before it reads the file,
refreshes it, releases it on pagehide, retries once without a dead token, and
gives every refused save a way out (a copy next to the file, else a download
button and a guard on leaving). Each arm drives the real Files -> editor route
path in a fresh browser and reads the outcome from the server, not only from
the host's own record.

    python3 wasm_sdk_probe/tools/check_m3_locks.py --label shakedown --arms hold --browsers chrome --repeats 1
    python3 wasm_sdk_probe/tools/check_m3_locks.py --label counted
    python3 wasm_sdk_probe/tools/check_m3_locks.py --score findings/evidence/m3-locks/runs/<file>.json
    python3 wasm_sdk_probe/tools/check_m3_locks.py --red-cases findings/evidence/m3-locks/shakedown/<file>.json

A second user `lcprobe` and three shares are made once per invocation (Nextcloud
allows 20 new shares per user per 10 min) and removed at the end.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import html
import json
import os
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from k_static_target import static_target  # noqa: E402
from check_m3_host_entry import CTRL_S, MARKER, PICKERS, host_record, requests_matching  # noqa: E402
from check_m3_skeleton_open import (  # noqa: E402
    ACTION, DEFAULT_DDEV, FIXTURE, NAME, ROUTE, SAMPLE, Instance, binding_fields, host_binding, product_state, state_until)
from probe_m3_gate0_coep import (  # noqa: E402
    DIST, EventChrome, firefox_profile, sha256_file, summarize_cdp, utc_now, wait_until)
from probe_m3_lock_semantics import Client  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import WEBDRIVER_ELEMENT_KEY, FirefoxSession, wait_http  # noqa: E402
from run_e2_c_page_smoke import POINT_AT, PRESS, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-locks"
# SPEC-M3-page-honesty §7.6: the reviewed page (b61e9fd9), written 2026-09-29 before
# the re-shakedown and counted runs on host 0.2.4 (369e6ed); was fbfb59a4….
# Re-pointed 2026-10-15 (task 10-15c P4, before binding v20) to host 0.2.23's page (shell v72, engine v20).  The previous pin was
# d761f1cee9d26c50c0b152348d74c3d05f540e9228927815d93ad6ec161e7dcd (SPEC-M3-autosave §9.19, 0.2.13/v62; the 0.2.13 and 0.2.14 counts ran on it).
# check_m3_versions.py and check_m3_same_second.py import this pin; they have none of their own.
PAGE_SHA256 = "3b0a2ebb92c3db282f9c832ab194249f963592698cf5c73d771998dc10203a6a"   # host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was 605cf24b3dff5a2d; host 0.2.26 (engine v21, shell v74, finding 154's host rule), 2026-10-17; was 901dd6a6 (host 0.2.24, v73, finding 145), ccb67a52 (host 0.2.23, v72), d761f1ce (autosave §9.19, host 0.2.13), 8909564e (production-ui §17 C′, host 0.2.12), 36c2b18b (§16 R⁗), 18c8afbe (§15 R‴, host 0.2.10), 537d62d7 (§14 R′, host 0.2.9), e00ab76a (§13.5, host 0.2.8)
ODT = "application/vnd.oasis.opendocument.text"
OTHER = "lcprobe"
RO_NAME = "M3 鎖 唯讀.odt"
RO_FOLDER = "M3 鎖 唯讀資料夾"
INNER = "M3 鎖 資料夾內.odt"
STRANDED = "存回失敗，而且沒有地方可以另存：內容還在這個頁面裡，請按「下載這份內容」。"
BOTH = ("chrome", "firefox")
# arm -> (spec id, browsers, counted runs per browser)
PLAN = {
    "hold": ("K1", BOTH, 3),
    "closetab": ("K2′", BOTH, 1),   # K2 withdrawn 2026-09-28: closing does not release
    "heartbeat": ("K3", BOTH, 1),
    "crash": ("K4", BOTH, 1),
    "foreign-lock": ("K5", BOTH, 3),
    "broken-then-written": ("K6", BOTH, 3),
    "expired": ("K7", BOTH, 3),
    "frozen": ("K8", ("chrome",), 1),
    # K9′/K10′ (SPEC-M3-page-honesty §7.4): writable at open, the share cut to
    # read-only after the edit, then the save.  A file read-only at open now
    # opens view-only and can no longer be saved at all (page-honesty V1).
    "readonly": ("K9′", BOTH, 3),
    "nowhere": ("K10′", BOTH, 3),
    "offline": ("K11", ("chrome",), 3),
    "unlock-refused": ("K12", BOTH, 3),   # added after the 2026-09-28 review, before any counted run
}
LOCK_PROPFIND = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns" '
                 b'xmlns:nc="http://nextcloud.org/ns"><d:prop><d:getetag/><oc:fileid/><d:lockdiscovery/>'
                 b"<nc:lock/><nc:lock-owner/><nc:lock-owner-type/></d:prop></d:propfind>")
HOST_DONE = ("(() => { const v = document.documentElement.getAttribute('data-litecore');"
             " return v && JSON.parse(v).done && v; })()")
BAR = """(() => ({ notice: document.querySelector('#litecore-host-notice').textContent,
  barHidden: document.querySelector('#litecore-host-bar').hidden,
  downloadHidden: document.querySelector('#litecore-host-download').hidden }))()"""
CENTER = """(() => { const r = document.querySelector(ARG).getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height }; })()"""
# Truthy while the host's 60 s refresh period (counted from the lock) is 5-40 s in.
QUIET_PHASE = ("(() => { const v = JSON.parse(document.documentElement.getAttribute('data-litecore'));"
               " const p = (Date.now() - v.started - v.lock.at) % 60000; return p > 5000 && p < 40000 && p; })()")


class LockChrome(EventChrome):
    KEEP = EventChrome.KEEP | {"Page.javascriptDialogOpening", "Page.downloadWillBegin", "Page.downloadProgress"}

    def real_click(self, selector: str) -> dict[str, Any]:
        """A trusted click (CDP Input): it gives the page user activation,
        which a DOM .click() does not -- and beforeunload needs it."""
        box = evaluate(self, CENTER.replace("ARG", json.dumps(selector)))
        for kind in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", {"type": kind, "x": box["x"], "y": box["y"],
                                                   "button": "left", "clickCount": 1})
        return box

    def leave_attempt(self, url: str, wait: float = 5.0) -> dict[str, Any]:
        """Navigate the way a link would (renderer-initiated, so beforeunload
        runs); a dialog blocks the page, so the evaluate is not awaited."""
        self.next_id += 1
        sent = self.next_id
        self.websocket.send(json.dumps({"id": sent, "method": "Runtime.evaluate",
                                        "params": {"expression": f"location.href = {json.dumps(url)}; true"}}))
        deadline = time.monotonic() + wait
        dialog = None
        while time.monotonic() < deadline:
            try:
                message = json.loads(self.websocket.recv(timeout=max(0.1, deadline - time.monotonic())))
            except TimeoutError:
                break
            if message.get("method") == "Page.javascriptDialogOpening":
                dialog = message["params"]
                break
            if message.get("method") in self.KEEP:
                self.events.append(message)
        return {"dialog": dialog}


def kill_tree(pid: int) -> list[int]:
    """SIGKILL a process and every descendant, collected first so none is
    reparented away before it is killed."""
    found, queue = [], [pid]
    while queue:
        current = queue.pop()
        found.append(current)
        children = subprocess.run(["pgrep", "-P", str(current)], capture_output=True, text=True).stdout.split()
        queue.extend(int(child) for child in children)
    for each in found:
        try:
            os.kill(each, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return found


class Server:
    """The server side of every check: admin and the second user over HTTP,
    and the lock table for the two arms that act on it directly."""

    def __init__(self, instance: Instance, log: list[dict[str, Any]]):
        self.instance = instance
        self.admin = Client(instance.base, "admin", instance.password, log)
        self.other: Client | None = None
        self.targets: dict[str, str] = {}
        self.shares: list[str] = []
        self.share_ids: dict[str, str] = {}
        self.fixture = FIXTURE.read_bytes()
        self.intruder = SAMPLE.read_bytes()

    def setup(self) -> dict[str, Any]:
        password = secrets.token_urlsafe(24)
        self.clear_locks()
        self.admin.call("setup", "DELETE", f"/ocs/v2.php/cloud/users/{OTHER}")
        made = self.admin.call("setup", "POST", "/ocs/v2.php/cloud/users", form={"userid": OTHER, "password": password})
        if made["status"] != 200:
            raise RuntimeError(f"cannot create {OTHER}: {made['status']} {made['body']}")
        self.other = Client(self.instance.base, OTHER, password, self.admin.log)
        self.other_password = password
        self.upload(self.admin, NAME)
        self.upload(self.admin, RO_NAME)
        self.admin.call("setup", "MKCOL", self.admin.dav_path(RO_FOLDER))
        self.upload(self.admin, f"{RO_FOLDER}/{INNER}")
        for key, path, permissions in (("rw", NAME, 3), ("ro", RO_NAME, 1), ("folder", RO_FOLDER, 1)):
            answer = self.admin.call("setup", "POST", "/ocs/v2.php/apps/files_sharing/api/v1/shares", form={
                "path": "/" + path, "shareType": 0, "shareWith": OTHER, "permissions": permissions})
            if answer["status"] != 200:
                raise RuntimeError(f"cannot share {path}: {answer['status']} (429 = share-creation limit)")
            data = json.loads(answer["body"])["ocs"]["data"]
            self.shares.append(str(data["id"]))
            self.share_ids[key] = str(data["id"])
            self.targets[key] = data["file_target"].lstrip("/")
        return {"targets": self.targets, "fileIds": {n: self.fileid(self.admin, n)
                                                    for n in (NAME, RO_NAME, f"{RO_FOLDER}/{INNER}")}}

    def set_share(self, key: str, permissions: int) -> dict[str, Any]:
        """Change one of setup's shares, then read it back (§7.4: the premise is
        read, not assumed)."""
        path = f"/ocs/v2.php/apps/files_sharing/api/v1/shares/{self.share_ids[key]}"
        put = self.admin.call(f"share {key} -> {permissions}", "PUT", path, form={"permissions": permissions})
        got = self.admin.call(f"share {key} readback", "GET", path)
        try:
            data = json.loads(got["body"])["ocs"]["data"]
            data = data[0] if isinstance(data, list) else data
            read = int(data["permissions"])
        except (TypeError, ValueError, KeyError, IndexError):
            read = None
        return {"status": put["status"], "readStatus": got["status"], "permissions": read}

    def teardown(self) -> None:
        self.admin.call("teardown", "DELETE", f"/ocs/v2.php/cloud/users/{OTHER}")
        for path in (RO_NAME, RO_FOLDER):
            self.admin.call("teardown", "DELETE", self.admin.dav_path(path))
        self.clear_locks()
        self.upload(self.admin, NAME)

    def upload(self, client: Client, path: str, body: bytes | None = None) -> int:
        return client.call("upload", "PUT", client.dav_path(path), self.fixture if body is None else body,
                           {"Content-Type": ODT})["status"]

    def fileid(self, client: Client, path: str) -> int | None:
        value = self.props(client, path).get("fileid")
        return int(value) if value else None

    def full(self, client: Client, step: str, method: str, path: str, body: bytes | None,
             headers: dict[str, str]) -> tuple[int, str]:
        """Like Client.call, but the whole body: Client keeps 1500 characters,
        and a folder listing or a lockdiscovery runs past that."""
        request = urllib.request.Request(client.base + client.dav_path(path), data=body, method=method,
                                         headers={"X-Requested-With": "XMLHttpRequest", **headers})
        request.add_header("Authorization", client.auth)
        try:
            with urllib.request.urlopen(request, context=client.tls, timeout=60) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        client.log.append({"step": step, "actor": client.user, "method": method, "path": path,
                           "status": status, "bytes": len(raw)})
        return status, raw.decode("utf-8", "replace")

    def props(self, client: Client, path: str) -> dict[str, Any]:
        status, body = self.full(client, "props", "PROPFIND", path, LOCK_PROPFIND,
                                 {"Depth": "0", "Content-Type": "application/xml"})
        grab = lambda tag: (body.split(f"<{tag}>", 1)[1].split(f"</{tag}>", 1)[0]  # noqa: E731
                            if f"<{tag}>" in body else None)
        token = None
        if "<d:locktoken>" in body:
            token = grab("d:locktoken").split("<d:href>", 1)[-1].split("</d:href>", 1)[0].strip()
        return {"status": status, "etag": html.unescape(grab("d:getetag") or "") or None,
                "fileid": grab("oc:fileid"), "lock": grab("nc:lock"), "lockOwner": grab("nc:lock-owner"),
                "lockOwnerType": grab("nc:lock-owner-type"), "token": token}

    def content(self, client: Client, path: str) -> dict[str, Any]:
        """The bytes' hash, read raw (the probe client keeps no zip bodies)."""
        request = urllib.request.Request(client.base + client.dav_path(path), method="GET")
        request.add_header("Authorization", client.auth)
        try:
            with urllib.request.urlopen(request, context=client.tls, timeout=60) as response:
                raw = response.read()
                return {"status": response.status, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        except urllib.error.HTTPError as error:
            return {"status": error.code, "sha256": None, "bytes": 0}

    def put(self, client: Client, path: str, body: bytes, headers: dict[str, str] | None = None) -> int:
        return client.call("put", "PUT", client.dav_path(path), body, {"Content-Type": ODT, **(headers or {})})["status"]

    def copies(self, client: Client, folder: str, stem: str, remove: bool) -> list[dict[str, Any]]:
        _, listing = self.full(client, "list", "PROPFIND", folder,
                               b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:displayname/></d:prop></d:propfind>',
                               {"Depth": "1", "Content-Type": "application/xml"})
        hrefs = [chunk.split("</d:href>", 1)[0] for chunk in listing.split("<d:href>")[1:]]
        names = [urllib.parse.unquote(href.rstrip("/").rsplit("/", 1)[-1]) for href in hrefs]
        found = []
        for name in sorted(n for n in names if n.startswith(stem + "（") and "副本" in n):
            path = f"{folder}/{name}" if folder else name
            found.append({"name": name, **self.content(client, path)})
            if remove:
                client.call("remove", "DELETE", client.dav_path(path))
        return found

    def clear_locks(self, fileid: int | None = None) -> str:
        where = f" WHERE file_id = {int(fileid)}" if fileid else ""
        result = subprocess.run(["ddev", "mysql", "-e", f"DELETE FROM oc_files_lock{where}; SELECT ROW_COUNT();"],
                                cwd=self.instance.root, capture_output=True, text=True, timeout=60)
        return (result.stdout.strip().splitlines() or ["?"])[-1]

    def poll_expiry(self, limit: float = 420, every: float = 15) -> list[dict[str, Any]]:
        """After the page is gone: the lock, every 15 s, until it lapses."""
        started = time.monotonic()
        polls = []
        while True:
            seen = self.props(self.admin, NAME)
            polls.append({"at": round(time.monotonic() - started, 1), "lock": seen.get("lock")})
            if seen.get("lock") == "" or time.monotonic() - started > limit:
                return polls
            time.sleep(every)

    def wait_unlocked(self, client: Client, path: str, limit: float, every: float = 1.0) -> dict[str, Any]:
        started = time.monotonic()
        polls = []
        while True:
            seen = self.props(client, path)
            polls.append({"at": round(time.monotonic() - started, 1), "lock": seen.get("lock")})
            if seen.get("lock") in ("", None) and seen.get("status") == 207:
                return {"released": True, "seconds": polls[-1]["at"], "polls": polls}
            if time.monotonic() - started > limit:
                return {"released": False, "polls": polls}
            time.sleep(every)


# --------------------------------------------------------------------------
# Driving


def login(session, base: str, user: str, password: str) -> Any:
    navigate(session, base + "/login", timeout=60)
    if isinstance(session, LockChrome):
        session.evaluate(
            "(() => { window.__m3login = null;"
            " fetch('/login', {method: 'POST', body: new URLSearchParams({"
            f"user: {json.dumps(user)}, password: {json.dumps(password)},"
            " requesttoken: document.head.dataset.requesttoken})})"
            ".then((r) => { window.__m3login = {status: r.status, url: r.url}; })"
            ".catch((e) => { window.__m3login = {error: String(e)}; }); return true; })()")
        return wait_until(session, "(() => window.__m3login)()", 30)
    wait_until(session, "(() => document.querySelector('#user') !== null)()", 30)
    for selector, text in (("#user", user), ("#password", password)):
        element = session.command("POST", "/element", {"using": "css selector", "value": selector})
        session.command("POST", f"/element/{element[WEBDRIVER_ELEMENT_KEY]}/value", {"text": text})
    session.click('button[type="submit"]')
    return wait_until(session, "(() => !location.pathname.endsWith('/login') && location.href)()", 30)


FILES_DOM = """(() => ({ readyState: document.readyState, title: document.title,
  url: location.href, scripts: document.scripts.length,
  filesList: document.querySelector('[data-cy-files-list]') !== null,
  rows: document.querySelectorAll('[data-cy-files-list-row]').length,
  bodyTextLength: (document.body && document.body.innerText || '').length,
  bodyText: (document.body && document.body.innerText || '').slice(0, 400) }))()"""


def files_row_diagnostic(session) -> dict[str, Any]:
    """Instrument only (finding 112): each part is kept even if another fails."""
    out: dict[str, Any] = {}
    try:
        out["dom"] = evaluate(session, FILES_DOM)
    except Exception as error:  # noqa: BLE001 -- the reason is the evidence
        out["dom"] = f"{type(error).__name__}: {error}"
    if isinstance(session, LockChrome):
        try:
            events = session.drain()
            answered = {e["params"]["requestId"] for e in events
                        if e["method"] in ("Network.responseReceived", "Network.loadingFailed")}
            sent = [e["params"] for e in events if e["method"] == "Network.requestWillBeSent"]
            out["cdp"] = summarize_cdp(events)
            out["requests"] = len(sent)
            out["unanswered"] = [p["request"]["url"] for p in sent if p["requestId"] not in answered]
            out["scripts"] = [p["request"]["url"] for p in sent if p.get("type") == "Script"]
        except Exception as error:  # noqa: BLE001
            out["cdp"] = f"{type(error).__name__}: {error}"
    try:
        out["screenshotPng"] = base64.b64encode(session.screenshot()).decode("ascii")
    except Exception as error:  # noqa: BLE001
        out["screenshotPng"] = f"{type(error).__name__}: {error}"
    return out


def open_from_files(session, base: str, folder: str, name: str, record: dict[str, Any]) -> None:
    navigate(session, base + "/apps/files/files?dir=" + urllib.parse.quote("/" + folder), timeout=120)
    selector = (f'[data-cy-files-list-row-name={json.dumps(name, ensure_ascii=False)}]'
                ' [data-cy-files-list-row-name-link]')
    waited = time.monotonic()
    record["filesRow"] = wait_until(session, f"(() => document.querySelector({json.dumps(selector)}) !== null)()", 60)
    # Finding 112 (m3-locks README rule 5, SPEC-M3-production-ui §12): how long
    # the row took on every run, and on a timeout what the browser saw.  The
    # events drained below used to be dropped, so the one red had none.
    record["filesRowSeconds"] = round(time.monotonic() - waited, 2)
    record["clickedFrom"] = evaluate(session, "(() => location.href)()")
    if isinstance(record["filesRow"], dict) and record["filesRow"].get("timedOut"):
        record["filesRowDiagnostic"] = files_row_diagnostic(session)
    if isinstance(session, LockChrome):
        session.drain()
    started = time.monotonic()
    session.click(selector)
    record["landed"] = wait_until(
        session, f"(() => location.pathname.endsWith({json.dumps(ROUTE)}) && location.href)()", 60)
    raw = wait_until(session, HOST_DONE, 300)
    record["host"] = json.loads(raw) if isinstance(raw, str) else {"notReported": raw}
    record["secondsToOpened"] = round(time.monotonic() - started, 2)
    record["pickers"] = evaluate(session, PICKERS)
    record["bar"] = evaluate(session, BAR)


def edit(session, record: dict[str, Any], key: str = "smoke") -> None:
    before = product_state(session)
    evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
    caret = state_until(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
    evaluate(session, PRESS.replace("ARG_ACTION", ACTION))
    acted = state_until(session, lambda s: s.get("revision") != caret.get("revision")
                        or "失敗" in (s.get("latency") or ""), 120)
    record[key] = {"before": before, "caret": caret, "acted": acted}


def insert_marker(session, record: dict[str, Any]) -> None:
    ahead = product_state(session)
    evaluate(session, f"(() => {{ document.querySelector('#text').value = {json.dumps(MARKER)}; return true; }})()")
    evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
    record["inserted"] = state_until(session, lambda s: s.get("revision") != ahead.get("revision")
                                     or "失敗" in (s.get("latency") or ""), 60)


def save(session, record: dict[str, Any], count: int, how: str = "button") -> dict[str, Any]:
    """Press save and wait until the host has settled that many saves, then
    for the page's own line to show the outcome."""
    if how == "button":
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
    else:
        record["ctrlS"] = evaluate(session, CTRL_S)
    record[f"save{count}Seen"] = wait_until(
        session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                 f" const s = v && JSON.parse(v).saves; return s && s.length >= {count}"
                 f" && s[{count - 1}].settled === true && s.length; }})()", 180)
    time.sleep(0.5)
    state = state_until(session, lambda s: (s.get("latency") or "").startswith("存回"), 60)
    record[f"save{count}State"] = state
    return state


def idle(session, seconds: float) -> None:
    """Wait without starving the CDP socket: unread events back up the
    websocket's queue until its keepalive ping times out (shakedown 112341Z)."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        time.sleep(min(10, max(0, deadline - time.monotonic())))
        if isinstance(session, LockChrome):
            session.call("Page.getNavigationHistory")


HOST_NOW = "(() => Date.now() - JSON.parse(document.documentElement.getAttribute('data-litecore')).started)()"


def wire(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chrome only: what actually went out to WebDAV, headers included -- the
    host's own record of If-Match and If is not evidence of the request."""
    rows = []
    for event in events:
        if event["method"] != "Network.requestWillBeSent":
            continue
        request = event["params"]["request"]
        if "/remote.php/dav/files/" not in request["url"]:
            continue
        headers = {k.lower(): v for k, v in (request.get("headers") or {}).items()}
        rows.append({"method": request["method"], "url": request["url"],
                     "ifMatch": headers.get("if-match"), "if": headers.get("if"),
                     "timeout": headers.get("timeout")})
    return rows


def chrome_download_dir(session: LockChrome, directory: Path) -> str:
    for method, params in (("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(directory)}),
                           ("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(directory)})):
        try:
            session.call(method, params)
            return method
        except Exception:  # noqa: BLE001 -- try the other
            continue
    return "none"


def downloaded(directory: Path, limit: float = 30) -> dict[str, Any]:
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        files = [p for p in directory.iterdir() if p.is_file() and not p.name.endswith((".part", ".crdownload"))]
        if files:
            time.sleep(0.5)
            path = max(files, key=lambda p: p.stat().st_mtime)
            return {"name": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
        time.sleep(0.5)
    return {"none": True, "listing": [p.name for p in directory.iterdir()]}


def run_arm(arm: str, kind: str, server: Server, scratch: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"arm": arm, "spec": PLAN[arm][0], "browser": kind, "startedAt": utc_now()}
    as_other = arm in ("readonly", "nowhere")
    client = server.other if as_other else server.admin
    folder = {"readonly": "", "nowhere": server.targets["folder"]}.get(arm, "")
    name = {"readonly": server.targets["ro"], "nowhere": INNER}.get(arm, NAME)
    path = f"{folder}/{name}" if folder else name
    admin_path = {"readonly": RO_NAME, "nowhere": f"{RO_FOLDER}/{INNER}"}.get(arm, NAME)
    record["file"] = {"user": client.user, "path": path, "adminPath": admin_path}
    record["clearedLocks"] = server.clear_locks()
    record["reset"] = {"upload": server.upload(server.admin, admin_path),
                       "fileId": server.fileid(server.admin, admin_path)}
    record["copiesBefore"] = server.copies(client, folder, name[:-4], remove=True)
    record["serverBefore"] = server.content(server.admin, admin_path)
    downloads = scratch / f"downloads-{arm}-{kind}-{time.monotonic_ns()}"
    downloads.mkdir()
    if kind == "chrome":
        session = LockChrome("cold")
        record["downloadVia"] = chrome_download_dir(session, downloads)
    else:
        session = FirefoxSession("cold", profile_dir=firefox_profile(scratch / f"ff-{time.monotonic_ns()}"),
                                 extra_prefs={"browser.download.folderList": 2, "browser.download.dir": str(downloads),
                                              "browser.download.useDownloadDir": True,
                                              "browser.download.always_ask_before_handling_new_types": False,
                                              "browser.helperApps.neverAsk.saveToDisk": ODT})
    record["version"] = getattr(session, "version", None)
    closed = False
    try:
        if arm == "foreign-lock":
            record["foreignLock"] = server.other.call("foreign lock", "LOCK", server.other.dav_path(server.targets["rw"]),
                                                      None, {"X-User-Lock": "1"})["status"]
        if arm in SHARE_OF:
            # K9′/K10′: writable at open.  Read back; a grant that did not take
            # is not this arm's premise, so it ends the run (fatal, red).
            record["grant"] = server.set_share(SHARE_OF[arm], 3)
            if record["grant"]["permissions"] != 3:
                raise RuntimeError(f"the share did not become writable: {record['grant']}")
        record["login"] = login(session, server.instance.base, client.user,
                                server.other_password if as_other else server.instance.password)
        open_from_files(session, server.instance.base, folder, name, record)
        record["afterOpen"] = server.props(server.admin, admin_path)
        if arm == "hold":
            record["seenByOther"] = server.props(server.other, server.targets["rw"])
            record["otherPut"] = server.put(server.other, server.targets["rw"], server.intruder)
            record["afterOtherPut"] = server.content(server.admin, NAME)
            edit(session, record)
            save(session, record, 1)
            insert_marker(session, record)
            save(session, record, 2, how="ctrl-s")
            record["host"] = host_record(session)
            record["serverAfter"] = server.content(server.admin, NAME)
            record["copiesAfter"] = server.copies(client, folder, name[:-4], remove=True)
            navigate(session, server.instance.base + "/apps/files/", timeout=120)
            record["release"] = server.wait_unlocked(server.admin, NAME, 15)
            record["otherPutAfter"] = server.put(server.other, server.targets["rw"], server.intruder)
        elif arm == "closetab":
            record["lockBefore"] = server.props(server.admin, NAME)
            if kind == "chrome":
                try:
                    session.call("Page.close", timeout=10)
                except Exception as error:  # noqa: BLE001 -- the socket goes with the tab
                    record["closeAnswer"] = f"{type(error).__name__}: {error}"
                time.sleep(2)
                record["pagesAfterClose"] = [t.get("url") for t in wait_http(f"{session.base_url}/json/list")
                                             if t.get("type") == "page"]
            else:
                record["editorWindow"] = session.command("GET", "/window")
                session.command("POST", "/window/new", {"type": "window"})
                record["windowsAfterClose"] = session.command("DELETE", "/window")
            record["expiry"] = server.poll_expiry()
        elif arm == "heartbeat":
            record["lockBefore"] = server.props(server.admin, NAME)
            idle(session, 330)
            record["lockAfter"] = server.props(server.admin, NAME)
            record["hostBeforeSave"] = host_record(session)
            save(session, record, 1)
            record["host"] = host_record(session)
            record["serverAfter"] = server.content(server.admin, NAME)
        elif arm == "crash":
            record["lockBefore"] = server.props(server.admin, NAME)
            record["killed"] = kill_tree(session.process.pid)
            closed = True
            time.sleep(1)
            record["aliveAfterKill"] = [pid for pid in record["killed"] if Path(f"/proc/{pid}").exists()
                                        and "zombie" not in Path(f"/proc/{pid}/status").read_text().lower()]
            record["expiry"] = server.poll_expiry()
        elif arm == "unlock-refused":
            # Another user's refused unlock still moves the ETag (files_lock
            # unlockFile propagates before it checks): our lock is alive, our
            # version is stale.
            fileid = record["reset"]["fileId"]
            record["refusedUnlock"] = server.other.call("refused unlock", "DELETE",
                                                        f"/ocs/v2.php/apps/files_lock/lock/{fileid}",
                                                        form={"lockType": 0})["status"]
            record["afterRefused"] = server.props(server.admin, NAME)
            edit(session, record)
            save(session, record, 1)
            record["host"] = host_record(session)
            record["lockAfterSave"] = server.props(server.admin, NAME)
            record["serverAfter"] = server.content(server.admin, NAME)
            record["copiesAfter"] = server.copies(client, folder, name[:-4], remove=True)
        elif arm == "foreign-lock":
            edit(session, record)
            save(session, record, 1)
            record["host"] = host_record(session)
            record["serverAfter"] = server.content(server.admin, NAME)
            record["copiesAfter"] = server.copies(client, folder, name[:-4], remove=True)
        elif arm == "broken-then-written":
            fileid = record["reset"]["fileId"]
            record["ownerUnlock"] = server.admin.call("owner unlock", "DELETE", f"/ocs/v2.php/apps/files_lock/lock/{fileid}",
                                                      form={"lockType": 0})["status"]
            record["intruded"] = server.put(server.admin, NAME, server.intruder)
            record["afterIntrusion"] = server.content(server.admin, NAME)
            edit(session, record)
            saved = save(session, record, 1)
            time.sleep(5)
            record["afterWait"] = product_state(session)
            record["savedRevision"] = saved.get("revision")
            record["host"] = host_record(session)
            record["serverAfter"] = server.content(server.admin, NAME)
            record["copiesAfter"] = server.copies(client, folder, name[:-4], remove=True)
        elif arm == "expired":
            edit(session, record)
            # Delete the row well away from a refresh (every 60 s from the lock),
            # so the save, not the heartbeat, is the first to meet the dead token.
            record["phaseWait"] = wait_until(session, QUIET_PHASE, 70, poll=0.5)
            record["deleted"] = server.clear_locks(record["reset"]["fileId"])
            record["afterDelete"] = server.props(server.admin, NAME)
            save(session, record, 1)
            record["host"] = host_record(session)
            record["serverAfter"] = server.content(server.admin, NAME)
            record["copiesAfter"] = server.copies(client, folder, name[:-4], remove=True)
        elif arm == "frozen":
            edit(session, record)
            record["freezeAt"] = evaluate(session, HOST_NOW)
            try:
                session.call("Page.setWebLifecycleState", {"state": "frozen"})
                record["frozen"] = True
            except Exception as error:  # noqa: BLE001 -- recorded, the arm then fails
                record["frozen"] = f"{type(error).__name__}: {error}"
            idle(session, 320)
            record["lockWhileFrozen"] = server.props(server.admin, NAME)
            idle(session, 10)
            session.call("Page.setWebLifecycleState", {"state": "active"})
            record["thawAt"] = evaluate(session, HOST_NOW)
            save(session, record, 1)
            record["host"] = host_record(session)
            record["serverAfter"] = server.content(server.admin, NAME)
            record["copiesAfter"] = server.copies(client, folder, name[:-4], remove=True)
        elif arm == "readonly":
            edit(session, record)
            revoke(server, session, record, "ro", admin_path)
            save(session, record, 1)
            record["host"] = host_record(session)
            record["serverAfter"] = server.content(server.admin, RO_NAME)
            record["copiesAfter"] = server.copies(client, folder, name[:-4], remove=True)
        elif arm == "nowhere":
            edit(session, record)
            revoke(server, session, record, "folder", admin_path)
            save(session, record, 1)
            record["host"] = host_record(session)
            record["barStranded"] = evaluate(session, BAR)
            if kind == "chrome":
                record["activation"] = session.real_click("#litecore-host-notice")
                record["leave1"] = session.leave_attempt(server.instance.base + "/apps/files/")
                if record["leave1"]["dialog"]:
                    session.call("Page.handleJavaScriptDialog", {"accept": False})
                time.sleep(1)
                record["stayed"] = evaluate(session, "(() => location.pathname)()")
                record["hostAfterLeave1"] = host_record(session)
                session.real_click("#litecore-host-download")
            else:
                session.click("#litecore-host-download")
            record["download"] = downloaded(downloads)
            record["hostAfterDownload"] = host_record(session)
            record["barAfterDownload"] = evaluate(session, BAR)
            if kind == "chrome":
                # A download the page cannot see complete does not lift the guard (spec S5).
                record["leave2"] = session.leave_attempt(server.instance.base + "/apps/files/")
                if record["leave2"]["dialog"]:
                    session.call("Page.handleJavaScriptDialog", {"accept": False})
                time.sleep(1)
                record["stayedAgain"] = evaluate(session, "(() => location.pathname)()")
                record["hostAfterLeave2"] = host_record(session)
            record["serverAfter"] = server.content(server.admin, admin_path)
            record["copiesAfter"] = server.copies(server.admin, RO_FOLDER, INNER[:-4], remove=True)
        elif arm == "offline":
            edit(session, record)
            session.call("Network.emulateNetworkConditions", {"offline": True, "latency": 0,
                                                              "downloadThroughput": -1, "uploadThroughput": -1})
            save(session, record, 1)
            record["barOffline"] = evaluate(session, BAR)
            # Stay offline across a refresh: a refresh that gets no answer must
            # not cost the lock (spec §3 K1).
            record["offlineRefresh"] = wait_until(
                session, "(() => { const v = JSON.parse(document.documentElement.getAttribute('data-litecore'));"
                         " return (v.lock.refreshes || []).some((r) => r.status === 'network') && v.lock.state; })()",
                75, poll=1.0)
            session.call("Network.emulateNetworkConditions", {"offline": False, "latency": 0,
                                                              "downloadThroughput": -1, "uploadThroughput": -1})
            insert_marker(session, record)
            save(session, record, 2, how="ctrl-s")
            record["host"] = host_record(session)
            record["barAfter"] = evaluate(session, BAR)
            record["serverAfter"] = server.content(server.admin, NAME)
            record["copiesAfter"] = server.copies(client, folder, name[:-4], remove=True)
        if isinstance(session, LockChrome) and arm not in ("closetab", "crash"):
            events = session.drain()
            record["cdp"] = summarize_cdp(events)
            record["fixtureRequests"] = requests_matching(events, "/e1-fixtures/")
            record["davRequests"] = wire(events)
            record["dialogs"] = [e["params"] for e in events if e["method"] == "Page.javascriptDialogOpening"]
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        if closed:
            session.process.wait(timeout=30)
        else:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                pass
        record["locksAtEnd"] = server.props(server.admin, admin_path)
        record["clearedAtEnd"] = server.clear_locks()
        if arm in SHARE_OF:
            record["restored"] = server.set_share(SHARE_OF[arm], 1)
    return record


# K9′/K10′: which of setup's shares the arm opens writable and then cuts.
SHARE_OF = {"readonly": "ro", "nowhere": "folder"}


def revoke(server: Server, session, record: dict[str, Any], key: str, admin_path: str) -> None:
    """After the edit, before the save: the share goes to read-only (1), read
    back; the server's lock at that moment is recorded (§7.4)."""
    record["hostBeforeRevoke"] = host_record(session)
    record["revoke"] = server.set_share(key, 1)
    record["lockAtRevoke"] = server.props(server.admin, admin_path)


# --------------------------------------------------------------------------
# Scoring -- raw fields only.


def opened_ok(run: dict[str, Any], report: dict[str, Any]) -> list[str]:
    """H1 of the host entry, for whichever user and file the arm opened."""
    bad = []
    fileid = (run.get("reset") or {}).get("fileId")
    landed = run.get("landed")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(landed).query) if isinstance(landed, str) else {}
    if not (isinstance(run.get("clickedFrom"), str) and "/apps/files/" in run["clickedFrom"]) \
            or query.get("fileId") != [str(fileid)]:
        bad.append(f"click path: from {run.get('clickedFrom')!r} to {landed!r}")
    host = run.get("host") or {}
    iso = host.get("isolation") or {}
    if iso.get("crossOriginIsolated") is not True or iso.get("sharedArrayBuffer") is not True:
        bad.append(f"isolation {iso}")
    if run.get("browser") == "chrome" and "cdp" in run:
        rows = [d for d in (run.get("cdp") or {}).get("documents") or [] if d.get("url") == landed]
        if not rows or rows[0].get("coop") != "same-origin" or rows[0].get("coep") != "require-corp":
            bad.append(f"document headers {rows}")
        if run.get("fixtureRequests") != []:
            bad.append(f"sample requests {run.get('fixtureRequests')}")
    fetched = host.get("fetched") or {}
    if fetched.get("status") != 200 or fetched.get("sha256") != report["original"]["sha256"]:
        bad.append(f"fetched {fetched}")
    name = (run.get("file") or {}).get("path", "").rsplit("/", 1)[-1]
    opened = next((s.get("state") or {} for s in host.get("steps") or [] if s.get("step") == "opened"), {})
    if opened.get("state") != "ready" or opened.get("doc") != name:
        bad.append(f"opened {opened}")
    if (run.get("pickers") or {}) != {"fixtureDisabled": True, "openFileDisabled": True, "fileDisabled": True,
                                      "fixtureOptions": 0}:
        bad.append(f"pickers {run.get('pickers')}")
    return bad


def edited(run: dict[str, Any], key: str = "smoke") -> list[str]:
    smoke = run.get(key) or {}
    caret, acted = smoke.get("caret") or {}, smoke.get("acted") or {}
    before, after = caret.get("revision") or "", acted.get("revision") or ""
    if not (before.isdigit() and after.isdigit() and int(after) == int(before) + 1
            and "失敗" not in (acted.get("latency") or "")):
        return [f"{key} {before!r}->{after!r} {acted.get('latency')!r}"]
    return []


def held_at_open(run: dict[str, Any], owner: str = "admin") -> list[str]:
    """The lock was taken, and taken before the read: the GET's version is the
    post-lock one (taking a lock moves the ETag; the server says which it is)."""
    bad = []
    host = run.get("host") or {}
    lock, fetched, after = host.get("lock") or {}, host.get("fetched") or {}, run.get("afterOpen") or {}
    if lock.get("status") != 200 or lock.get("state") not in ("held", "released", "lost"):
        bad.append(f"lock at open {lock.get('status')}/{lock.get('state')}")
    if not (isinstance(lock.get("at"), int) and isinstance(fetched.get("at"), int) and lock["at"] <= fetched["at"]):
        bad.append(f"lock at {lock.get('at')} vs fetched at {fetched.get('at')}")
    if after.get("lock") != "1" or after.get("lockOwnerType") != "2" or after.get("lockOwner") != owner:
        bad.append(f"server lock after open {after.get('lock')}/{after.get('lockOwnerType')}/{after.get('lockOwner')}")
    if not fetched.get("etag") or fetched.get("etag") != after.get("etag"):
        bad.append(f"fetched version {fetched.get('etag')} is not the post-lock {after.get('etag')}")
    return bad


def cut_after_open(run: dict[str, Any]) -> list[str]:
    """K9′/K10′ (§7.4): writable at open -- the lock taken, by the recipient,
    no read-only notice -- then the share cut to 1 and read back as 1, with the
    server's lock still there at that moment."""
    bad = held_at_open(run, OTHER)
    grant, cut = run.get("grant") or {}, run.get("revoke") or {}
    if grant.get("permissions") != 3 or cut.get("permissions") != 1:
        bad.append(f"share {grant.get('permissions')} at open -> {cut.get('permissions')} after the edit, wanted 3 -> 1")
    if ((run.get("hostBeforeRevoke") or {}).get("lock") or {}).get("state") != "held":
        bad.append(f"host lock before the cut {((run.get('hostBeforeRevoke') or {}).get('lock') or {}).get('state')}")
    if (run.get("lockAtRevoke") or {}).get("lock") != "1":
        bad.append(f"server lock at the cut {(run.get('lockAtRevoke') or {}).get('lock')!r}")
    if "唯讀" in (run.get("bar") or {}).get("notice", ""):
        bad.append(f"read-only notice at open {(run.get('bar') or {}).get('notice')!r}")
    return bad


def attempts(save: dict[str, Any]) -> list[tuple[Any, Any]]:
    return [(a.get("status"), a.get("withToken")) for a in save.get("attempts") or []]


def page_failed_with(state: dict[str, Any], *needles: str) -> list[str]:
    toast = state.get("toast") or ""
    if state.get("latency") != "存回 失敗" or not all(n in toast for n in needles):
        return [f"page says {state.get('latency')!r} / {toast!r}, wanted {needles}"]
    return []


def one_copy(run: dict[str, Any], label: str, sent: str | None) -> list[str]:
    copies = run.get("copiesAfter") or []
    if len(copies) != 1 or label not in copies[0]["name"] or copies[0].get("sha256") != sent:
        return [f"copies {[(c.get('name'), (c.get('sha256') or '')[:12]) for c in copies]}, wanted one {label} = {(sent or '')[:12]}"]
    return []


def on_wire(run: dict[str, Any], expected: list[tuple[Any, bool]]) -> list[str]:
    """Chrome: the PUTs to the document as sent -- If-Match equal to what the
    host recorded, and If carrying the server's own token exactly when expected."""
    if run.get("browser") != "chrome":
        return []
    name = (run.get("file") or {}).get("path", "")
    quoted = urllib.parse.quote(name)
    puts = [r for r in run.get("davRequests") or [] if r["method"] == "PUT" and r["url"].endswith(quoted)]
    attempts_ = [a for s in (run.get("host") or {}).get("saves") or [] for a in s.get("attempts") or []]
    token = (run.get("afterOpen") or {}).get("token")
    bad = []
    if len(puts) != len(expected) or len(attempts_) != len(expected):
        return [f"wire: {len(puts)} PUTs, host recorded {len(attempts_)}, expected {len(expected)}"]
    for put, attempt, (_, with_token) in zip(puts, attempts_, expected):
        if put["ifMatch"] != attempt.get("ifMatch") or not put["ifMatch"]:
            bad.append(f"wire If-Match {put['ifMatch']} vs recorded {attempt.get('ifMatch')}")
        if with_token and put["if"] != f"(<{token}>)":
            bad.append(f"wire If {put['if']} vs server token {token}")
        if not with_token and put["if"]:
            bad.append(f"wire If {put['if']} on an attempt without the token")
    locks = [i for i, r in enumerate(run.get("davRequests") or []) if r["method"] == "LOCK"]
    gets = [i for i, r in enumerate(run.get("davRequests") or []) if r["method"] == "GET"]
    if not locks or not gets or locks[0] > gets[0]:
        bad.append(f"wire order: LOCK at {locks[:1]}, GET at {gets[:1]}")
    return bad


def score_arm(run: dict[str, Any], report: dict[str, Any]) -> list[str]:
    if run.get("fatal"):
        return [f"fatal: {run['fatal'].strip().splitlines()[-1]}"]
    arm = run["arm"]
    bad = opened_ok(run, report)
    host = run.get("host") or {}
    saves = host.get("saves") or []
    original = report["original"]["sha256"]
    server_after = (run.get("serverAfter") or {}).get("sha256")
    if arm == "hold":
        bad += held_at_open(run) + edited(run)
        seen = run.get("seenByOther") or {}
        if seen.get("lock") != "1" or seen.get("lockOwnerType") != "2" or seen.get("lockOwner") != "admin":
            bad.append(f"seen by other {seen}")
        if run.get("otherPut") != 423 or (run.get("afterOtherPut") or {}).get("sha256") != original:
            bad.append(f"other PUT {run.get('otherPut')}, server {(run.get('afterOtherPut') or {}).get('sha256', '')[:12]}")
        fetched = (host.get("fetched") or {}).get("etag")
        if len(saves) != 2 or [attempts(s) for s in saves] != [[(204, True)], [(204, True)]]:
            bad.append(f"saves {[attempts(s) for s in saves]}")
        elif saves[0].get("ifMatch") != fetched or saves[1].get("ifMatch") != saves[0].get("etag"):
            bad.append(f"version chain {fetched} -> {saves[0].get('ifMatch')}, {saves[0].get('etag')} -> {saves[1].get('ifMatch')}")
        elif server_after != saves[1].get("sha256"):
            bad.append(f"server {server_after and server_after[:12]} != second save {saves[1].get('sha256', '')[:12]}")
        if run.get("copiesAfter"):
            bad.append(f"copies {run.get('copiesAfter')}")
        bad += on_wire(run, [(204, True), (204, True)])
        if not (run.get("release") or {}).get("released") or not (200 <= (run.get("otherPutAfter") or 0) < 300):
            bad.append(f"after leaving: release {run.get('release', {}).get('released')}, other PUT {run.get('otherPutAfter')}")
    elif arm == "closetab":
        bad += held_at_open(run)
        polls = run.get("expiry") or []
        if (run.get("lockBefore") or {}).get("lock") != "1":
            bad.append(f"no lock before closing {(run.get('lockBefore') or {}).get('lock')!r}")
        if not polls or polls[-1].get("lock") != "" or polls[-1].get("at", 9e9) > 315:
            bad.append(f"expiry {polls[-1:] if polls else None}")
        if run.get("browser") == "chrome" and ("pagesAfterClose" not in run
                                               or any(ROUTE in (u or "") for u in run["pagesAfterClose"])):
            bad.append(f"the editor tab is still there: {run.get('pagesAfterClose')}")
        if run.get("browser") == "firefox" and (not run.get("editorWindow")
                                                or run["editorWindow"] in (run.get("windowsAfterClose") or [run["editorWindow"]])):
            bad.append(f"the editor window is still there: {run.get('editorWindow')} in {run.get('windowsAfterClose')}")
    elif arm == "heartbeat":
        bad += held_at_open(run)
        before, after = run.get("lockBefore") or {}, run.get("lockAfter") or {}
        if after.get("lock") != "1" or not before.get("token") or before.get("token") != after.get("token"):
            bad.append(f"after 330 s: lock {after.get('lock')!r}, token {before.get('token')} -> {after.get('token')}")
        refreshes = ((run.get("hostBeforeSave") or {}).get("lock") or {}).get("refreshes") or []
        if len(refreshes) < 5 or any(r.get("status") != 200 for r in refreshes):
            bad.append(f"refreshes {[r.get('status') for r in refreshes]}")
        if len(saves) != 1 or attempts(saves[0]) != [(204, True)] or server_after != saves[0].get("sha256"):
            bad.append(f"save {[attempts(s) for s in saves]}")
    elif arm == "crash":
        bad += held_at_open(run)
        polls = run.get("expiry") or []
        if not polls or polls[0].get("lock") != "1":
            bad.append(f"first poll after kill {polls[:1]} (the lock must still be there)")
        if not polls or polls[-1].get("lock") != "" or polls[-1].get("at", 9e9) > 315:
            bad.append(f"expiry {polls[-1:] if polls else None}")
        if not run.get("killed") or run.get("aliveAfterKill") != []:
            bad.append(f"killed {run.get('killed')}, still alive {run.get('aliveAfterKill')}")
    elif arm == "unlock-refused":
        bad += held_at_open(run) + edited(run)
        after, before = run.get("afterRefused") or {}, run.get("afterOpen") or {}
        if run.get("refusedUnlock") != 423 or after.get("etag") == before.get("etag") or after.get("token") != before.get("token"):
            bad.append(f"refused unlock {run.get('refusedUnlock')}, etag {before.get('etag')} -> {after.get('etag')}, "
                       f"token {before.get('token')} -> {after.get('token')}")
        if len(saves) != 1 or attempts(saves[0]) != [(412, True)]:
            bad.append(f"save {[attempts(s) for s in saves]} (the token is alive: no retry without it)")
        else:
            bad += one_copy(run, "衝突副本", saves[0].get("sha256"))
            bad += page_failed_with(run.get("save1State") or {}, "CONFLICT", (saves[0].get("conflictCopy") or {}).get("name") or "?")
        kept = run.get("lockAfterSave") or {}
        if (host.get("lock") or {}).get("state") != "held" or kept.get("token") != before.get("token"):
            bad.append(f"lock after the save: host {(host.get('lock') or {}).get('state')}, server token {kept.get('token')}")
        if server_after != original:
            bad.append(f"server {server_after and server_after[:12]} changed")
        bad += on_wire(run, [(412, True)])
    elif arm == "foreign-lock":
        bad += edited(run)
        lock = host.get("lock") or {}
        if run.get("foreignLock") != 200 or lock.get("status") != 423 or lock.get("state") != "refused":
            bad.append(f"foreign {run.get('foreignLock')}, ours {lock.get('status')}/{lock.get('state')}")
        if OTHER not in (run.get("bar") or {}).get("notice", ""):
            bad.append(f"notice {(run.get('bar') or {}).get('notice')!r}")
        if len(saves) != 1 or attempts(saves[0]) != [(423, False)]:
            bad.append(f"save {[attempts(s) for s in saves]}")
        else:
            bad += one_copy(run, "衝突副本", saves[0].get("sha256"))
            bad += page_failed_with(run.get("save1State") or {}, "CONFLICT", (saves[0].get("conflictCopy") or {}).get("name") or "?")
        if server_after != original:
            bad.append(f"server {server_after and server_after[:12]} changed")
    elif arm == "broken-then-written":
        bad += held_at_open(run) + edited(run)
        if run.get("ownerUnlock") != 200 or not (200 <= (run.get("intruded") or 0) < 300):
            bad.append(f"owner unlock {run.get('ownerUnlock')}, intruder {run.get('intruded')}")
        if len(saves) != 1 or attempts(saves[0]) != [(412, True), (412, False)]:
            bad.append(f"save {[attempts(s) for s in saves]}")
        else:
            bad += one_copy(run, "衝突副本", saves[0].get("sha256"))
            bad += page_failed_with(run.get("save1State") or {}, "CONFLICT", (saves[0].get("conflictCopy") or {}).get("name") or "?")
        if server_after != report["intruder"]["sha256"]:
            bad.append(f"server {server_after and server_after[:12]} is not the intruder's")
        bad += on_wire(run, [(412, True), (412, False)])
        waited = run.get("afterWait") or {}
        if waited.get("state") != "ready" or waited.get("doc") != NAME or waited.get("revision") != run.get("savedRevision"):
            bad.append(f"view after 5 s {waited.get('state')}/{waited.get('doc')}/{waited.get('revision')} vs {run.get('savedRevision')}")
    elif arm == "expired":
        bad += held_at_open(run) + edited(run)
        if run.get("deleted") != "1" or (run.get("afterDelete") or {}).get("lock") != "":
            bad.append(f"lock row deleted {run.get('deleted')}, server lock {(run.get('afterDelete') or {}).get('lock')!r}")
        if len(saves) != 1 or attempts(saves[0]) != [(412, True), (204, False)] or server_after != saves[0].get("sha256"):
            bad.append(f"save {[attempts(s) for s in saves]}, server {server_after and server_after[:12]}")
        if run.get("copiesAfter"):
            bad.append(f"copies {run.get('copiesAfter')}")
        bad += on_wire(run, [(412, True), (204, False)])
        state = run.get("save1State") or {}
        if not (state.get("latency") or "").startswith("存回 ") or "失敗" in state.get("latency", ""):
            bad.append(f"page says {state.get('latency')!r}")
    elif arm == "frozen":
        bad += held_at_open(run) + edited(run)
        if run.get("frozen") is not True or (run.get("lockWhileFrozen") or {}).get("lock") != "":
            bad.append(f"frozen {run.get('frozen')}, lock at 320 s {(run.get('lockWhileFrozen') or {}).get('lock')!r}")
        lock = host.get("lock") or {}
        # SPEC-M3-autosave §9.4 「計數」, registered before 0.2.13 ran; witness
        # findings/evidence/m3-locks/shakedown/2026-10-12T075616+0000.json: the page
        # comes back from frozen hidden and may save by itself first.  The last record
        # is the manual save, expectation as before; auto records before it are
        # allowed, each passing AS-1 (the autosave runner's own rule, imported).
        from check_m3_autosave import conditions_problems  # noqa: PLC0415 -- it imports this file
        last = saves[-1] if saves else {}
        if not saves or last.get("trigger") != "manual" or server_after != last.get("sha256") \
                or (last.get("attempts") or [{}])[-1].get("status") != 204:
            bad.append(f"save {[(s.get('trigger'), attempts(s)) for s in saves]}, server {server_after and server_after[:12]}")
        for index, save in enumerate(saves[:-1]):
            problems = ["not an auto save"] if save.get("trigger") != "auto" else conditions_problems(save)
            bad += [f"save {index + 1} before the manual one: {p}" for p in problems]
        if run.get("copiesAfter") or lock.get("state") != "lost" or lock.get("lostBy") not in ("refresh", "save"):
            bad.append(f"copies {run.get('copiesAfter')}, lock {lock.get('state')}/{lock.get('lostBy')}")
        start, end = run.get("freezeAt"), run.get("thawAt")
        inside = [r for r in lock.get("refreshes") or [] if isinstance(start, int) and isinstance(end, int)
                  and start < r.get("at", -1) < end]
        if not (isinstance(start, int) and isinstance(end, int) and end - start >= 320_000) or inside:
            bad.append(f"freeze window {start}..{end}, refreshes inside it {inside}")
    elif arm == "readonly":
        bad += edited(run) + cut_after_open(run)
        # §7.4: 403 WITH the token.  412 means cutting the share moved the ETag:
        # that run went another way -- red, and stop and report, not a new expectation.
        if len(saves) != 1 or attempts(saves[0]) != [(403, True)]:
            bad.append(f"save {[attempts(s) for s in saves]}, wanted [(403, True)]")
        else:
            bad += one_copy(run, "另存副本", saves[0].get("sha256"))
            bad += page_failed_with(run.get("save1State") or {}, (saves[0].get("conflictCopy") or {}).get("name") or "?")
        bad += on_wire(run, [(403, True)])
        if server_after != original:
            bad.append(f"owner's file changed {server_after and server_after[:12]}")
    elif arm == "nowhere":
        bad += edited(run) + cut_after_open(run)
        copy_ = (saves[0].get("conflictCopy") or {}) if saves else {}
        if len(saves) != 1 or attempts(saves[0]) != [(403, True)] or copy_.get("status") != 403 or not copy_.get("failed"):
            bad.append(f"save {[attempts(s) for s in saves]}, copy {copy_}, wanted [(403, True)] and a failed copy")
        bad += on_wire(run, [(403, True)])
        stranded_bar = run.get("barStranded") or {}
        if stranded_bar.get("downloadHidden") is not False or stranded_bar.get("notice") != STRANDED:
            bad.append(f"bar while stranded {stranded_bar}")
        bad += page_failed_with(run.get("save1State") or {}, "下載這份內容")
        sent = saves[0].get("sha256") if saves else None
        if (run.get("download") or {}).get("sha256") != sent:
            bad.append(f"download {run.get('download')} != sent {(sent or '')[:12]}")
        after_download = run.get("hostAfterDownload") or {}
        if (run.get("barAfterDownload") or {}).get("downloadHidden") is not False \
                or (after_download.get("stranded") or {}).get("sha256") != sent \
                or ((after_download.get("downloaded") or [{}])[-1]).get("sha256") != sent:
            bad.append(f"after download: bar {run.get('barAfterDownload')}, stranded {after_download.get('stranded')}, "
                       f"downloaded {after_download.get('downloaded')}")
        if run.get("browser") == "chrome":
            dialog = (run.get("leave1") or {}).get("dialog") or {}
            if dialog.get("type") != "beforeunload" or not str(run.get("stayed", "")).endswith(ROUTE):
                bad.append(f"first leave: dialog {dialog.get('type')}, stayed at {run.get('stayed')}")
            dialog2 = (run.get("leave2") or {}).get("dialog") or {}
            if dialog2.get("type") != "beforeunload" or not str(run.get("stayedAgain", "")).endswith(ROUTE):
                bad.append(f"leaving after the download: dialog {dialog2.get('type')}, stayed at {run.get('stayedAgain')}")
            # §7.4 (review item 12): each ask is the host's, for the stranded bytes.
            for n in ("1", "2"):
                guards = (run.get(f"hostAfterLeave{n}") or {}).get("guards") or []
                if len(guards) < int(n) or "stranded" not in (guards[int(n) - 1].get("reasons") or []):
                    bad.append(f"leave{n}: host guards {guards}, wanted a `stranded` reason")
        if server_after != original or run.get("copiesAfter"):
            bad.append(f"server {server_after and server_after[:12]}, copies {run.get('copiesAfter')}")
    elif arm == "offline":
        bad += held_at_open(run) + edited(run)
        first = saves[0] if saves else {}
        copy_ = first.get("conflictCopy") or {}
        if attempts(first) != [("network", True)] or copy_.get("status") != "network" or not copy_.get("failed"):
            bad.append(f"offline save {attempts(first)}, copy {copy_}")
        if (run.get("barOffline") or {}).get("downloadHidden") is not False:
            bad.append(f"bar offline {run.get('barOffline')}")
        if run.get("offlineRefresh") != "held":
            bad.append(f"no refresh while offline, or it cost the lock: {run.get('offlineRefresh')!r}")
        second = saves[1] if len(saves) > 1 else {}
        bad += on_wire(run, [("network", True), (204, True)])
        if attempts(second) != [(204, True)] or server_after != second.get("sha256"):
            bad.append(f"online save {attempts(second)}, server {server_after and server_after[:12]}")
        if (run.get("barAfter") or {}).get("downloadHidden") is not True or host.get("stranded") is not None \
                or (host.get("unstranded") or {}).get("how") != "saved":
            bad.append(f"after the online save: bar {run.get('barAfter')}, stranded {host.get('stranded')}, {host.get('unstranded')}")
        if run.get("copiesAfter"):
            bad.append(f"copies {run.get('copiesAfter')}")
    return bad


def score(report: dict[str, Any], strict: bool) -> dict[str, Any]:
    problems: list[str] = []
    static = report.get("static") or {}
    if static.get("page") != {"dist": PAGE_SHA256, "web": PAGE_SHA256}:
        problems.append(f"page {static.get('page')}")
    if strict and static.get("testStatic") != 0:
        problems.append(f"make test-e2-c-static exit {static.get('testStatic')}")
    if strict and (report.get("hostDirty") or not report.get("hostFiles")):
        problems.append(f"host not bound: dirty {report.get('hostDirty')!r}, files {report.get('hostFiles')}")
    tally: dict[str, dict[str, Any]] = {}
    for run in report.get("runs") or []:
        key = f"{run['browser']}:{run['arm']}"
        entry = tally.setdefault(key, {"pass": 0, "runs": 0, "problems": []})
        entry["runs"] += 1
        bad = score_arm(run, report)
        if bad:
            entry["problems"].append(bad)
        else:
            entry["pass"] += 1
    if strict:
        for arm, (_, browsers, count) in PLAN.items():
            for browser in browsers:
                entry = tally.get(f"{browser}:{arm}") or {"pass": 0, "runs": 0}
                if entry["runs"] != count or entry["pass"] != count:
                    problems.append(f"{browser}:{arm} {entry['pass']}/{entry['runs']} of {count}")
    ok = not problems and all(not e["problems"] for e in tally.values())
    return {"verdict": ("LOCKS LAND" if ok else "LOCKS DO NOT LAND") if strict else ("clean" if ok else "red"),
            "tally": tally, "problems": problems}


def one_line(result: dict[str, Any]) -> str:
    cells = " ".join(f"{k}={v['pass']}/{v['runs']}" for k, v in sorted(result["tally"].items()))
    return f"{result['verdict']} {cells} problems={result['problems']}"


def _first(report: dict, arm: str, browser: str = "chrome") -> dict:
    return next(r for r in report["runs"] if r["arm"] == arm and r["browser"] == browser)


# Each mutation must turn its own arm red; the name says what was broken.
# (label, arm, mutation, browsers it applies to -- None = every browser the arm runs in)
C = ("chrome",)
_AS1_HELD = {"viewOnly": False, "state": "ready", "pending": 0, "composing": False, "queueDepth": 0,
             "dragging": False, "savesUnsettled": 0, "rescue": False, "reason": "hidden"}

RED_CASES = [
    ("opened: the bundled sample was fetched", "hold", lambda r: r.update(fixtureRequests=[{"url": "e1-fixtures/x"}]), C),
    ("opened: other bytes were opened", "hold", lambda r: r["host"]["fetched"].update(sha256="0" * 64), None),
    ("hold: lock taken after the read", "hold", lambda r: r["host"]["fetched"].update(etag='"stale"'), None),
    ("hold: other user's PUT not refused", "hold", lambda r: r.update(otherPut=204), None),
    ("hold: a save without the token (host record)", "hold", lambda r: r["host"]["saves"][1]["attempts"][0].update(withToken=False), None),
    ("hold: the wire PUT lacks If", "hold", lambda r: [x.update({"if": None}) for x in r["davRequests"] if x["method"] == "PUT"], C),
    ("hold: the wire If-Match is not the recorded one", "hold", lambda r: [x.update(ifMatch='"x"') for x in r["davRequests"] if x["method"] == "PUT"], C),
    ("hold: version chain broken", "hold", lambda r: r["host"]["saves"][1].update(ifMatch='"x"'), None),
    ("hold: server holds the first save, not the second", "hold", lambda r: r["serverAfter"].update(sha256=r["host"]["saves"][0]["sha256"]), None),
    ("hold: not released on leaving", "hold", lambda r: r["release"].update(released=False), None),
    ("closetab: never lapsed", "closetab", lambda r: r["expiry"][-1].update(lock="1"), None),
    ("closetab: lapsed too late", "closetab", lambda r: r["expiry"][-1].update(at=330.0), None),
    ("closetab: the tab was not closed (chrome)", "closetab", lambda r: r.update(pagesAfterClose=[ROUTE]), C),
    ("closetab: the window was not closed (firefox)", "closetab", lambda r: r.update(windowsAfterClose=[r.get("editorWindow")]), ("firefox",)),
    ("heartbeat: the lock lapsed", "heartbeat", lambda r: r["lockAfter"].update(lock=""), None),
    ("heartbeat: token changed", "heartbeat", lambda r: r["lockAfter"].update(token="opaquelocktoken:other"), None),
    ("heartbeat: a refresh refused", "heartbeat", lambda r: r["hostBeforeSave"]["lock"]["refreshes"][0].update(status=400), None),
    ("crash: released at once (no positive control)", "crash", lambda r: r["expiry"][0].update(lock=""), None),
    ("crash: never expired", "crash", lambda r: r["expiry"][-1].update(lock="1"), None),
    ("crash: the browser survived the kill", "crash", lambda r: r.update(aliveAfterKill=[1]), None),
    ("foreign-lock: overwrote", "foreign-lock", lambda r: r["serverAfter"].update(sha256="0" * 64), None),
    ("foreign-lock: notice without holder", "foreign-lock", lambda r: r["bar"].update(notice=""), None),
    ("foreign-lock: copy bytes differ", "foreign-lock", lambda r: r["copiesAfter"][0].update(sha256="0" * 64), None),
    ("broken: no retry without token", "broken-then-written", lambda r: r["host"]["saves"][0]["attempts"].pop(), None),
    ("broken: copy missing", "broken-then-written", lambda r: r.update(copiesAfter=[]), None),
    ("broken: the intruder's bytes were overwritten", "broken-then-written", lambda r: r["serverAfter"].update(sha256=r["original"] if "original" in r else "0" * 64), None),
    ("broken: the view was reloaded", "broken-then-written", lambda r: r["afterWait"].update(revision="999"), None),
    ("expired: gave up after the dead token", "expired", lambda r: r["host"]["saves"][0]["attempts"][1].update(status=412), None),
    ("expired: made a copy anyway", "expired", lambda r: r.update(copiesAfter=[{"name": "x（衝突副本）.odt"}]), None),
    ("expired: server bytes are not the save's", "expired", lambda r: r["serverAfter"].update(sha256="0" * 64), None),
    ("expired: the retry still carried If on the wire", "expired", lambda r: [x.update({"if": "(<t>)"}) for x in r["davRequests"] if x["method"] == "PUT"], C),
    ("frozen: lock never expired", "frozen", lambda r: r["lockWhileFrozen"].update(lock="1"), None),
    ("frozen: refreshed while frozen", "frozen", lambda r: r["host"]["lock"]["refreshes"].append({"at": r["freezeAt"] + 60000, "status": 200}), None),
    ("frozen: server bytes are not the save's", "frozen", lambda r: r["serverAfter"].update(sha256="0" * 64), None),
    # §9.4 「計數」: auto records before the manual save are allowed, each passing AS-1.
    ("frozen: the last save is not the manual one", "frozen", lambda r: r["host"]["saves"][-1].update(trigger="auto"), None),
    ("frozen: an auto save before it fails AS-1", "frozen",
     lambda r: r["host"]["saves"].insert(0, {"trigger": "auto", "conditions": dict(_AS1_HELD, composing=True)}), None),
    # §7.4: K9′/K10′ replace the two "sent a LOCK" cases.
    ("readonly: the cut did not take (read back 3)", "readonly", lambda r: r["revoke"].update(permissions=3), None),
    ("readonly: the PUT carried no token", "readonly",
     lambda r: r["host"]["saves"][0]["attempts"][0].update(withToken=False), None),
    ("readonly: the PUT was 412, not 403", "readonly",
     lambda r: r["host"]["saves"][0]["attempts"][0].update(status=412), None),
    ("readonly: no lock at open", "readonly", lambda r: r["afterOpen"].update(lock=""), None),
    ("readonly: a read-only notice at open", "readonly",
     lambda r: r["bar"].update(notice="唯讀：只能檢視，不能修改或存檔。"), None),
    ("nowhere: the cut did not take (read back 3)", "nowhere", lambda r: r["revoke"].update(permissions=3), None),
    ("nowhere: the PUT was 412, not 403", "nowhere",
     lambda r: r["host"]["saves"][0]["attempts"][0].update(status=412), None),
    ("nowhere: a guard without the stranded reason", "nowhere",
     lambda r: r["hostAfterLeave1"]["guards"][0].update(reasons=["page"]), C),
    ("readonly: copy bytes differ", "readonly", lambda r: r["copiesAfter"][0].update(sha256="0" * 64), None),
    ("readonly: owner's file changed", "readonly", lambda r: r["serverAfter"].update(sha256="0" * 64), None),
    ("nowhere: download bytes differ", "nowhere", lambda r: r["download"].update(sha256="0" * 64), None),
    ("nowhere: no download button while stranded", "nowhere", lambda r: r["barStranded"].update(downloadHidden=True), None),
    ("nowhere: owner's file changed", "nowhere", lambda r: r["serverAfter"].update(sha256="0" * 64), None),
    ("nowhere: no guard on leaving", "nowhere", lambda r: r["leave1"].update(dialog=None), C),
    ("nowhere: the download lifted the guard", "nowhere", lambda r: r["leave2"].update(dialog=None), C),
    ("nowhere: the download dropped the bytes", "nowhere", lambda r: r["hostAfterDownload"].update(stranded=None), None),
    ("offline: the offline save did not fail on the network", "offline", lambda r: r["host"]["saves"][0]["attempts"][0].update(status=204), None),
    ("offline: no refresh while offline", "offline", lambda r: r.update(offlineRefresh=None), None),
    ("offline: second save lost the token", "offline", lambda r: r["host"]["saves"][1]["attempts"][0].update(withToken=False), None),
    ("offline: still stranded", "offline", lambda r: r["host"].update(stranded={"sha256": "x"}), None),
    ("unlock-refused: dropped a live token and retried", "unlock-refused", lambda r: r["host"]["saves"][0]["attempts"].append({"status": 423, "withToken": False}), None),
    ("unlock-refused: the lock was lost", "unlock-refused", lambda r: r["lockAfterSave"].update(token=None), None),
    ("unlock-refused: no copy", "unlock-refused", lambda r: r.update(copiesAfter=[]), None),
]


def red_cases(path: Path) -> int:
    """Every case must find its run and turn it red. A missing run is a
    failure, not a skip: a red case that never ran proves nothing."""
    report = json.loads(path.read_text())
    failures = 0
    for label, arm, mutate, only in RED_CASES:
        for browser in (only or PLAN[arm][1]):
            if browser not in PLAN[arm][1]:
                continue
            try:
                base = _first(report, arm, browser)
            except StopIteration:
                print(f"  MISSING {label} [{browser}]: no {arm} run in this report")
                failures += 1
                continue
            if score_arm(base, report):
                print(f"  SKIP  {label} [{browser}]: the unmutated run is already red")
                failures += 1
                continue
            mutated = copy.deepcopy(base)
            mutated["original"] = report["original"]["sha256"]
            mutate(mutated)
            red = bool(score_arm(mutated, report))
            failures += not red
            print(f"  {'red ' if red else 'GREEN'}  {label} [{browser}]")
    static = copy.deepcopy(report)
    static["static"]["page"]["dist"] = "0" * 64
    red = bool(score(static, strict=True)["problems"])
    failures += not red
    print(f"  {'red ' if red else 'GREEN'}  static: the served page is not the spec's")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--label", choices=("shakedown", "counted"))
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV,
                        help="another instance: the app installed from the release archive (SPEC-M3-install-elsewhere)")
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--repeats", type=int, default=None, help="shakedown only")
    parser.add_argument("--arms", default=",".join(PLAN), help="shakedown only: a counted run runs the plan")
    parser.add_argument("--score", type=Path)
    parser.add_argument("--red-cases", type=Path)
    args = parser.parse_args()
    if args.score:
        report = json.loads(args.score.read_text())
        result = score(report, strict=report.get("label") == "counted")
        print(one_line(result))
        return 0 if result["verdict"] in ("LOCKS LAND", "clean") else 1
    if args.red_cases:
        return 1 if red_cases(args.red_cases) else 0
    if not args.label:
        parser.error("--label, --score or --red-cases")
    counted = args.label == "counted"
    static = {"page": {"dist": sha256_file(DIST / "e2-editor-app.js"),
                       "web": sha256_file(PROJECT / "web" / "e2-editor-app.js")}}
    if static["page"] != {"dist": PAGE_SHA256, "web": PAGE_SHA256}:
        if counted:
            print(f"refusing a counted run: page is {static['page']}, spec wants {PAGE_SHA256[:12]}…")
            return 2
    binding = host_binding(args.ddev_root)
    dirty = binding["hostDirty"]
    if counted and dirty:
        print(f"refusing a counted run: the host repo has uncommitted changes:\n{dirty}")
        return 2
    if counted:
        static.update(static_target(PROJECT))   # P6's reading of the named reds, not exit 0 (SPEC-M3-K-0.2.44 append 1, H2)
    instance = Instance(args.ddev_root)
    log: list[dict[str, Any]] = []
    server = Server(instance, log)
    report: dict[str, Any] = {
        "runner": "check_m3_locks.py", "runnerSha256": sha256_file(Path(__file__)), "label": args.label,
        "startedAt": utc_now(), "static": static,
        **binding_fields(binding),
        "baseUrl": instance.base,
        "original": {"source": str(FIXTURE.relative_to(DIST)), "sha256": sha256_file(FIXTURE)},
        "intruder": {"source": str(SAMPLE.relative_to(DIST)), "sha256": sha256_file(SAMPLE)},
        "runs": [],
    }
    arms = list(PLAN) if counted else args.arms.split(",")
    browsers = args.browsers.split(",")
    out = EVIDENCE / ("runs" if counted else "shakedown") / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        report["setup"] = server.setup()
        with tempfile.TemporaryDirectory(prefix="m3-locks-", dir=PROJECT / "build") as scratch:
            for arm in arms:
                spec, allowed, count = PLAN[arm]
                for browser in browsers:
                    if browser not in allowed:
                        continue
                    for index in range(count if counted or args.repeats is None else args.repeats):
                        print(f"{spec} {arm} {browser} #{index + 1}", flush=True)
                        report["runs"].append(run_arm(arm, browser, server, Path(scratch)))
                        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    finally:
        server.teardown()
        report["completedAt"] = utc_now()
        report["httpLog"] = log
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    result = score(report, strict=counted)
    report["score"] = result
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(REPO))
    print(one_line(result))
    return 0 if result["verdict"] in ("LOCKS LAND", "clean") else 1


if __name__ == "__main__":
    sys.exit(main())
