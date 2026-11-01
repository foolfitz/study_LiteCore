#!/usr/bin/env python3
"""M3 host entry -- the page opens and saves through `globalThis.liteCoreHost`.

Criteria H1-H3, H5: specs/SPEC-M3-host-entry.md section 4, written before the
page changed.  (H4 -- nothing changes without a host -- is the product-path net
and `make test-e2-c-static`, not this runner.)  Host = the `litecore` Nextcloud
app, same instance as the M3 skeleton.

Arms, each in a fresh browser, the server file reset to the original first:
  open-save  (3 per browser)  Files click -> open -> caret + heading -> save.
                              H1 on the open, H2 on the server file afterwards.
  conflict   (3 per browser)  as open-save, but the runner overwrites the file
                              on the server before save.  H1 and H3.
  open-save also edits again (inserts a marker) and saves a second time by
                              Ctrl+S: the second write must chain on the first's version.
  conflict also waits 5 s (the view must not be reloaded) and presses save again;
                              the first save is refused and lands as a conflict copy,
                              the second goes to that copy (SPEC-M3-autosave §9.4
                              「計數」, O1 = B; until 0.2.12 both were refused and
                              both landed as copies).
  Every arm ends by going back to Files (so the page releases its token lock
                              at leaving) and polls the server's lock for 10 s
                              -- recorded, not scored.  A lock still there when
                              the next arm resets is recorded and cleared.
  conflict's intruder is admin -- the page's own user -- writing with its
                              own lock token from another client: since the
                              host locks (49cc4ab) a PUT without the token is
                              423 and no conflict could be made.  Same
                              principal + its token is a legitimate write (RFC
                              4918 §6.4), not finding 102 (another user).  The
                              arm is pinned to the branch it claims: intruder
                              2xx with a token, the first save one PUT (412,
                              token), the token still on the server
                              (SPEC-M3-install-elsewhere §3.4, fable's ruling).
  broken, broken-no-save      (1 each, Chrome) `liteCoreHost` forced to `{}` / to
                              a host without save() before any page script runs
                              (CDP addScriptToEvaluateOnNewDocument; the Firefox
                              driver here has no equivalent).  H5.

  check_m3_host_entry.py --label shakedown|counted
  check_m3_host_entry.py --score REPORT.json
  check_m3_host_entry.py --red-cases REPORT.json

Scoring reads raw fields: the server's bytes as the runner fetched them, the
page's state line, the requests Chrome saw, the host script's own records of
what it sent.  Never a boolean the page or host concluded.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import io
import json
import re
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_skeleton_open import (  # noqa: E402
    ACTION, DEFAULT_DDEV, FILES, FIXTURE, NAME, ROUTE, SAMPLE, Instance, product_state,
    state_until)
from probe_m3_gate0_coep import (  # noqa: E402
    DIST, PRODUCT_FILES, EventChrome, browser_login, firefox_profile, sha256_file,
    summarize_cdp, utc_now, wait_until)
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import POINT_AT, PRESS, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-host-entry"
BROWSERS = {"chrome", "firefox"}
PAGE = PROJECT / "web" / "e2-editor-app.js"
SAVED = re.compile(r"^存回 \d+ ms$")
MARKER = "LC2"
# The generation served_shell() compares dist/ with.  build_e2_c_shell_bundle.MANIFEST stays v76 (the tool is bound), and
# against v76 five files differ, so a counted run would refuse.  SPEC-M3-K-0.2.44 append 1, H3.
SHELL_MANIFEST = Path("e2/editor-shell-v2-bundle-v83.json")   # host 0.2.45 (engine v29, shell generation 83), 2026-11-02; was v82
# `liteCoreHost` replaced before any page script runs (the host script's own
# assignment then lands on a setter that ignores it).  Two wrong shapes: the
# spec refuses a host without load() OR without save().
BROKEN_HOSTS = {
    "broken": "{}",
    "broken-no-save": "{ load: async () => ({ bytes: new ArrayBuffer(8), name: 'x.odt' }) }",
}
BROKEN_HOST = """Object.defineProperty(globalThis, 'liteCoreHost', {
  configurable: true, get() { return HOST_SHAPE; }, set(value) {} });"""
PICKERS = """(() => ({
  fixtureDisabled: document.querySelector('#fixture').disabled,
  openFileDisabled: document.querySelector('#open-file').disabled,
  fileDisabled: document.querySelector('#file').disabled,
  fixtureOptions: document.querySelectorAll('#fixture option').length }))()"""
CTRL_S = """(() => { const sink = document.querySelector('#sink'); sink.focus();
  return sink.dispatchEvent(new KeyboardEvent('keydown', { key: 's', code: 'KeyS',
    ctrlKey: true, bubbles: true, cancelable: true })) === false; })()"""


def served_shell() -> dict[str, Any]:
    manifest = json.loads((PROJECT / SHELL_MANIFEST).read_text(encoding="utf-8"))
    served = {}
    for entry in manifest["included"]:
        path = entry["path"]
        in_dist = DIST / (path.split("/", 1)[1] if path.startswith("web/") else path)
        served[path] = sha256_file(in_dist) if in_dist.is_file() else None
    return {"manifest": str(SHELL_MANIFEST), "bundleSha256": manifest.get("bundleSha256"),
            "served": served,
            "differsFromManifest": sorted(e["path"] for e in manifest["included"]
                                          if served[e["path"]] != e["sha256"])}


def content_xml(odt: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(odt)) as archive:
        return archive.read("content.xml").decode("utf-8", "replace")


def paragraph_styles(odt: bytes) -> dict[str, Any]:
    """What the paragraphs are, as the file says -- so a red H2 carries its payload."""
    content = content_xml(odt)
    used = re.findall(r'<text:(p|h)\b[^>]*?text:style-name="([^"]+)"', content)
    parents = {}
    for tag in re.findall(r'<style:style\b[^>]*>', content):
        name = re.search(r'style:name="([^"]+)"', tag)
        parent = re.search(r'style:parent-style-name="([^"]+)"', tag)
        if name and parent and 'style:family="paragraph"' in tag:
            parents[name.group(1)] = parent.group(1)
    return {"headingElements": content.count("<text:h "),
            "paragraphs": [[kind, style, parents.get(style)] for kind, style in used]}


def has_heading(odt: bytes) -> bool:
    """A paragraph is a Heading 1: a `<text:h>`, or a paragraph styled
    `Heading_20_1` directly or through an automatic style's parent.  NOT
    `<text:h>` alone: the product's heading action writes
    `<text:p text:style-name="Heading_20_1">` -- measured 2026-08-19 and written
    down at run_e2_c_product_path.py `document_lines`, and measured again here
    by shakedown 2026-09-28T092945Z after the first predicate called it 'no
    heading'."""
    styles = paragraph_styles(odt)
    return styles["headingElements"] > 0 or any(
        "Heading_20_1" in (style, parent) for _, style, parent in styles["paragraphs"])


def paragraph_texts(odt: bytes) -> list[str]:
    """Each paragraph's text, tags stripped: enough to tell this document from
    another one with the same name."""
    content = content_xml(odt)
    body = content.split("<office:text>", 1)[-1]
    texts = re.findall(r"<text:(?:p|h)\b[^>]*?(?:/>|>(.*?)</text:(?:p|h)>)", body, re.S)
    return [html.unescape(re.sub(r"<[^>]+>", "", text or "")) for text in texts]


def server_file(instance: Instance, name: str = NAME) -> dict[str, Any]:
    _, body = instance.dav("GET", name)
    propfind = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:getetag/></d:prop></d:propfind>')
    _, answer = instance.dav("PROPFIND", name, propfind, {"Depth": "0", "Content-Type": "application/xml"})
    etag = re.search(rb"<d:getetag>([^<]*)</d:getetag>", answer)
    return {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
            "heading": has_heading(body), "styles": paragraph_styles(body),
            "texts": paragraph_texts(body),
            "etag": html.unescape(etag.group(1).decode()) if etag else None}


def conflict_copies(instance: Instance, remove: bool) -> list[dict[str, Any]]:
    """Files next to the document whose names say they are its conflict copies."""
    stem = NAME[:-len(".odt")]
    _, answer = instance.dav("PROPFIND", "", b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop>'
                             b"<d:displayname/></d:prop></d:propfind>", {"Depth": "1", "Content-Type": "application/xml"})
    names = [urllib.parse.unquote(href.rsplit("/", 1)[-1])
             for href in re.findall(r"<d:href>([^<]+)</d:href>", answer.decode())]
    found = []
    for name in sorted(n for n in names if n.startswith(stem + "（衝突副本")):
        found.append({"name": name, **server_file(instance, name)})
        if remove:
            instance.dav("DELETE", name)
    return found


LOCK_PROPS = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns"'
              b' xmlns:oc="http://owncloud.org/ns"><d:prop><nc:lock/><d:lockdiscovery/><oc:fileid/></d:prop></d:propfind>')


def dav_answer(instance: Instance, method: str, name: str, body: bytes | None = None,
               headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    """instance.dav, but a refusal is an answer, not an exception."""
    try:
        return instance.dav(method, name, body, headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def server_lock(instance: Instance) -> dict[str, Any]:
    """The server's lock on the document: nc:lock, and the token lockdiscovery
    shows to anyone who can read the file (finding 102)."""
    status, answer = dav_answer(instance, "PROPFIND", NAME, LOCK_PROPS,
                                {"Depth": "0", "Content-Type": "application/xml"})
    text = answer.decode("utf-8", "replace")
    lock = re.search(r"<nc:lock>([^<]*)</nc:lock>", text)
    token = re.search(r"<d:locktoken>\s*<d:href>([^<]+)</d:href>", text)
    fileid = re.search(r"<oc:fileid>(\d+)</oc:fileid>", text)
    return {"status": status, "lock": lock.group(1) if lock else None,
            "token": token.group(1).strip() if token else None,
            "fileId": int(fileid.group(1)) if fileid else None}


def clear_lock(instance: Instance, fileid: int) -> str:
    """What check_m3_locks' clear_locks does, for this one file."""
    done = subprocess.run(["ddev", "mysql", "-e", f"DELETE FROM oc_files_lock WHERE file_id = {int(fileid)};"
                           " SELECT ROW_COUNT();"], cwd=instance.root, capture_output=True, text=True, timeout=60)
    return (done.stdout.strip().splitlines() or ["?"])[-1]


def leave_and_watch(session, instance: Instance) -> list[dict[str, Any]]:
    """Back to Files, then the server's lock for up to 10 s (as assets' K2-5)."""
    left = time.monotonic()
    navigate(session, instance.base + FILES, timeout=120)
    polls = []
    while True:
        lock = server_lock(instance)
        polls.append({"t": round(time.monotonic() - left, 2), "lock": lock["lock"], "status": lock["status"]})
        if lock["lock"] != "1" or time.monotonic() - left >= 10:
            return polls
        time.sleep(0.5)


def requests_matching(events: list[dict[str, Any]], needle: str) -> list[dict[str, Any]]:
    return [{"method": e["params"]["request"]["method"], "url": e["params"]["request"]["url"]}
            for e in events if e["method"] == "Network.requestWillBeSent"
            and needle in e["params"]["request"]["url"]]


def host_record(session) -> dict[str, Any]:
    raw = evaluate(session, "(() => document.documentElement.getAttribute('data-litecore'))()")
    return json.loads(raw) if isinstance(raw, str) else {"notReported": raw}


def open_from_files(session, instance: Instance, record: dict[str, Any]) -> float:
    record["login"] = browser_login(session, instance.base, instance.password)
    navigate(session, instance.base + FILES, timeout=120)
    selector = (f'[data-cy-files-list-row-name={json.dumps(NAME, ensure_ascii=False)}]'
                ' [data-cy-files-list-row-name-link]')
    record["filesRow"] = wait_until(
        session, f"(() => document.querySelector({json.dumps(selector)}) !== null)()", 60)
    record["clickedFrom"] = evaluate(session, "(() => location.href)()")
    if isinstance(session, EventChrome):
        session.drain()
    started = time.monotonic()
    session.click(selector)
    record["landed"] = wait_until(
        session, f"(() => location.pathname.endsWith({json.dumps(ROUTE)}) && location.href)()", 60)
    return started


def saves_reached(session, count: int, timeout: float = 180) -> Any:
    """Until the host has recorded `count` saves and the last one is settled --
    its write answered and, on a conflict, its copy written.  Then a moment for
    the page's own `run()` to put the outcome on the state line, which reads
    the same (`存回 失敗`) for a first and a second refused save."""
    seen = wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                               f" const s = v && JSON.parse(v).saves; return s && s.length >= {count}"
                               f" && s[{count - 1}].settled === true && s.length; }})()", timeout)
    time.sleep(0.5)
    return seen


def run_arm(arm: str, kind: str, instance: Instance, scratch: Path, intruder: bytes) -> dict[str, Any]:
    record: dict[str, Any] = {"arm": arm, "browser": kind}
    record["lockAtReset"] = server_lock(instance)
    if record["lockAtReset"]["lock"] == "1" and record["lockAtReset"]["fileId"]:
        record["staleLockCleared"] = clear_lock(instance, record["lockAtReset"]["fileId"])
    record["reset"] = instance.upload(FIXTURE, NAME)
    record["copiesBefore"] = conflict_copies(instance, remove=True)
    record["serverBefore"] = server_file(instance)
    session = (EventChrome("cold") if kind == "chrome"
               else FirefoxSession("cold", profile_dir=firefox_profile(scratch)))
    record["version"] = session.version
    try:
        if arm in BROKEN_HOSTS:
            session.call("Page.addScriptToEvaluateOnNewDocument",
                         {"source": BROKEN_HOST.replace("HOST_SHAPE", BROKEN_HOSTS[arm])})
        started = open_from_files(session, instance, record)
        if arm in BROKEN_HOSTS:
            record["final"] = state_until(session, lambda s: s.get("state") == "stopped", 120)
            record["pickers"] = evaluate(session, PICKERS)
            record["host"] = host_record(session)
        else:
            raw = wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                                      " return v && JSON.parse(v).done && v; })()", 300)
            record["host"] = json.loads(raw) if isinstance(raw, str) else {"notReported": raw}
            record["secondsToOpened"] = round(time.monotonic() - started, 2)
            record["pickers"] = evaluate(session, PICKERS)
            caret_before = product_state(session)
            evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
            caret = state_until(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
            evaluate(session, PRESS.replace("ARG_ACTION", ACTION))
            acted = state_until(session, lambda s: s.get("revision") != caret.get("revision")
                                or "失敗" in (s.get("latency") or ""), 120)
            record["smoke"] = {"before": caret_before, "caret": caret, "acted": acted}
            if arm == "conflict":
                # With the page's token: the lock refuses a PUT without it (423).
                held = server_lock(instance)
                token = held.get("token") or ""
                if token and not token.startswith("opaquelocktoken:"):
                    token = "opaquelocktoken:" + token
                status, _ = dav_answer(instance, "PUT", NAME, intruder, {
                    "Content-Type": "application/vnd.oasis.opendocument.text",
                    **({"If": f"(<{token}>)"} if token else {})})
                record["intruded"] = {"status": status, "lock": held, "server": server_file(instance)}
            # First save: the button.
            evaluate(session, PRESS.replace("ARG_ACTION", "save"))
            record["firstSaveSeen"] = saves_reached(session, 1)
            record["saved"] = state_until(session, lambda s: (s.get("latency") or "").startswith("存回"), 60)
            if arm == "open-save":
                # A second edit that leaves a marker, then the second save by
                # Ctrl+S: the host must chain on the version the first save got.
                evaluate(session, f"(() => {{ document.querySelector('#text').value = {json.dumps(MARKER)}; return true; }})()")
                evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
                record["inserted"] = state_until(
                    session, lambda s: s.get("revision") != record["saved"].get("revision")
                    or "失敗" in (s.get("latency") or ""), 60)
                record["ctrlS"] = evaluate(session, CTRL_S)
            else:
                # The user's view must not be reloaded under them after a
                # conflict, and pressing save again must not overwrite either.
                time.sleep(5)
                record["afterWait"] = product_state(session)
                evaluate(session, PRESS.replace("ARG_ACTION", "save"))
            record["secondSaveSeen"] = saves_reached(session, 2)
            record["savedAgain"] = state_until(
                session, lambda s: (s.get("latency") or "").startswith("存回"), 60)
            record["host"] = host_record(session)
            record["serverAfter"] = server_file(instance)
            record["copiesAfter"] = conflict_copies(instance, remove=True)
        if isinstance(session, EventChrome):
            events = session.drain()
            record["cdp"] = summarize_cdp(events)
            record["fixtureRequests"] = requests_matching(events, "/e1-fixtures/")
            record["davRequests"] = requests_matching(events, "/remote.php/dav/files/")
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            record["leave"] = leave_and_watch(session, instance)
        except Exception as error:  # noqa: BLE001 -- recorded, not scored
            record["leave"] = f"{type(error).__name__}: {error}"
        session.close()
    return record


# --------------------------------------------------------------------------
# Scoring -- raw fields only.


def h1(run: dict[str, Any], report: dict[str, Any]) -> list[str]:
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
    if run.get("browser") == "chrome":
        rows = [d for d in (run.get("cdp") or {}).get("documents") or [] if d.get("url") == landed]
        if not rows or rows[0].get("coop") != "same-origin" or rows[0].get("coep") != "require-corp":
            bad.append(f"document headers {rows}")
        if run.get("fixtureRequests") != []:
            bad.append(f"sample requests {run.get('fixtureRequests')}")
    fetched = host.get("fetched") or {}
    if fetched.get("status") != 200 or fetched.get("sha256") != report["original"]["sha256"]:
        bad.append(f"fetched {fetched}")
    opened = next((s.get("state") or {} for s in host.get("steps") or [] if s.get("step") == "opened"), {})
    if opened.get("state") != "ready" or opened.get("doc") != NAME:
        bad.append(f"opened {opened}")
    pickers = run.get("pickers") or {}
    if pickers != {"fixtureDisabled": True, "openFileDisabled": True, "fileDisabled": True, "fixtureOptions": 0}:
        bad.append(f"pickers {pickers}")
    return bad


def smoke_ok(run: dict[str, Any]) -> list[str]:
    smoke = run.get("smoke") or {}
    caret, acted = smoke.get("caret") or {}, smoke.get("acted") or {}
    before, after = caret.get("revision") or "", acted.get("revision") or ""
    if not (before.isdigit() and after.isdigit() and int(after) == int(before) + 1
            and "失敗" not in (acted.get("latency") or "") and acted.get("doc") == NAME):
        return [f"smoke {before!r}->{after!r} {acted.get('latency')!r} on {acted.get('doc')!r}"]
    return []


def h2(run: dict[str, Any], report: dict[str, Any]) -> list[str]:
    bad = smoke_ok(run)
    saves = (run.get("host") or {}).get("saves") or []
    after, before = run.get("serverAfter") or {}, run.get("serverBefore") or {}
    for key in ("saved", "savedAgain"):
        if not SAVED.match((run.get(key) or {}).get("latency") or ""):
            bad.append(f"{key}: page says {(run.get(key) or {}).get('latency')!r}")
    inserted = run.get("inserted") or {}
    if not (inserted.get("revision") or "").isdigit() or \
            int(inserted["revision"]) != int((run.get("saved") or {}).get("revision") or -9) + 1:
        bad.append(f"second edit {inserted.get('revision')!r} {inserted.get('latency')!r}")
    if run.get("ctrlS") is not True:
        bad.append("Ctrl+S was not taken by the page")
    if len(saves) != 2 or [s.get("status") for s in saves] != [204, 204]:
        bad.append(f"saves {[(s.get('status'), s.get('ifMatch'), s.get('etag')) for s in saves]}")
    elif saves[1].get("ifMatch") != saves[0].get("etag") or saves[0].get("ifMatch") != (run.get("host") or {}).get("fetched", {}).get("etag"):
        bad.append("the second save did not chain on the first save's version")
    elif after.get("sha256") != saves[1].get("sha256"):
        bad.append("server bytes are not the bytes of the last save")
    if after.get("sha256") == report["original"]["sha256"] or not after.get("heading"):
        bad.append(f"server file has no heading: {after.get('styles')}")
    texts = after.get("texts") or []
    if sum(t.count(MARKER) for t in texts) != 1 or [t.replace(MARKER, "") for t in texts] != report["original"]["texts"]:
        bad.append(f"server text {texts} vs original {report['original']['texts']}")
    if not before.get("etag") or after.get("etag") == before.get("etag"):
        bad.append(f"etag {before.get('etag')!r} -> {after.get('etag')!r}")
    if run.get("copiesAfter"):
        bad.append(f"conflict copies without a conflict: {[c['name'] for c in run['copiesAfter']]}")
    return bad


def h3(run: dict[str, Any], report: dict[str, Any]) -> list[str]:
    bad = smoke_ok(run)
    if (report.get("intruder") or {}).get("mode") == "lock-token":
        # The arm measures the live-lock branch; a refused intruder or a lock
        # that died must not pass as H3 (fable's ruling, condition 3).
        intruded = run.get("intruded") or {}
        if not isinstance(intruded.get("status"), int) or not 200 <= intruded["status"] < 300:
            bad.append(f"intruder {intruded.get('status')}: no conflict was made")
        if not (intruded.get("lock") or {}).get("token"):
            bad.append("intruder: the page held no lock token to write with")
        for save in ((run.get("host") or {}).get("saves") or [])[:1]:
            attempts = [(a.get("status"), a.get("withToken")) for a in save.get("attempts") or []]
            if attempts != [(412, True)] or save.get("tokenOnServer") is not True:
                bad.append(f"save 1: attempts {attempts}, tokenOnServer {save.get('tokenOnServer')!r}"
                           " -- not the live-lock branch")
    # SPEC-M3-autosave §9.4 「計數」 (O1 = B), registered before 0.2.13 ran; witness
    # findings/evidence/m3-host-entry/shakedown/2026-10-12T083454Z.json: the first
    # save is refused and lands as a copy, the second goes to that copy -- one PUT,
    # 204, no token -- and the page says so; the view keeps the original's name.
    saves = (run.get("host") or {}).get("saves") or []
    after = run.get("serverAfter") or {}
    copies = run.get("copiesAfter") or []
    copy_name = copies[0].get("name") if len(copies) == 1 else None
    saved, waited, again = run.get("saved") or {}, run.get("afterWait") or {}, run.get("savedAgain") or {}
    if saved.get("latency") != "存回 失敗" or "CONFLICT" not in (saved.get("toast") or ""):
        bad.append(f"saved: page says {saved.get('latency')!r} / {saved.get('toast')!r}")
    if not re.fullmatch(r"存回 \d+ ms", again.get("latency") or "") or not copy_name \
            or not (again.get("toast") or "").startswith(f"已存回 {copy_name}") or again.get("doc") != NAME:
        bad.append(f"savedAgain: page says {again.get('latency')!r} / {again.get('toast')!r}, doc {again.get('doc')!r}")
    if waited.get("state") != "ready" or waited.get("doc") != NAME or waited.get("revision") != saved.get("revision"):
        bad.append(f"the view changed after the conflict: {saved.get('revision')!r} -> {waited}")
    second = [(a.get("status"), a.get("withToken"), a.get("target")) for a in (saves[1].get("attempts") or [])] \
        if len(saves) == 2 else None
    if len(saves) != 2 or [s.get("status") for s in saves] != [412, 204] or second != [(204, False, copy_name)]:
        bad.append(f"saves {[s.get('status') for s in saves]}, second {second}")
    if after.get("sha256") != report["intruder"]["sha256"]:
        bad.append(f"server file after {after.get('sha256', '')[:12]}, intruder {report['intruder']['sha256'][:12]}")
    if not copy_name or len(saves) != 2 or copies[0].get("sha256") != saves[1].get("sha256"):
        bad.append(f"conflict copies {[(c.get('name'), c.get('sha256', '')[:12]) for c in copies]}")
    return bad


def h5(run: dict[str, Any]) -> list[str]:
    bad = []
    final = run.get("final") or {}
    if final.get("state") != "stopped" or "HOST_ENTRY_INVALID" not in (final.get("toast") or ""):
        bad.append(f"final {final.get('state')!r} {final.get('toast')!r}")
    if final.get("doc") not in ("—", None):
        bad.append(f"a document opened: {final.get('doc')!r}")
    pickers = run.get("pickers") or {}
    if run.get("fixtureRequests") != [] or pickers.get("fixtureOptions") != 0 \
            or not (pickers.get("fixtureDisabled") and pickers.get("openFileDisabled") and pickers.get("fileDisabled")):
        bad.append(f"sample or pickers {run.get('fixtureRequests')} {pickers}")
    # Positive control: the drain that saw no sample request did see the page.
    if not [d for d in (run.get("cdp") or {}).get("documents") or [] if d.get("url") == run.get("landed")]:
        bad.append("the drain has no record of the editor page itself")
    return bad


def score(report: dict[str, Any], strict: bool) -> dict[str, Any]:
    problems = []
    if report.get("original", {}).get("heading") is not False:
        problems.append("the original already has a heading; H2 cannot tell")
    if report.get("intruder", {}).get("sha256") == report.get("original", {}).get("sha256"):
        problems.append("intruder bytes equal the original; H3 cannot tell")
    if set(report.get("browsers") or {}) != BROWSERS:
        problems.append(f"browsers {sorted(report.get('browsers') or {})}")
    if strict and (report.get("label") != "counted" or report.get("repeats") != 3):
        problems.append(f"label {report.get('label')!r} repeats {report.get('repeats')!r}")
    if strict and (report.get("shell") or {}).get("differsFromManifest") != []:
        problems.append(f"served shell is not a frozen generation: {(report.get('shell') or {}).get('differsFromManifest')}")
    if (report.get("instance") or {}).get("app", {}).get("dirty"):
        problems.append("app tree dirty")
    if "lockAtEnd" in report and (report.get("intruder") or {}).get("mode") != "lock-token":
        problems.append("a report from the locking-host runner without the intruder's mode")
    per: dict[str, Any] = {}
    for kind, arms in (report.get("browsers") or {}).items():
        cells: dict[str, Any] = {}
        for arm, runs in arms.items():
            results = []
            for run in runs:
                if "fatal" in run:
                    results.append({"died": ["run died"]})
                elif arm in BROKEN_HOSTS:
                    results.append({"H5": h5(run)})
                else:
                    results.append({"H1": h1(run, report),
                                     ("H2" if arm == "open-save" else "H3"):
                                     (h2 if arm == "open-save" else h3)(run, report)})
            passed = sum(1 for r in results if not any(r.values()))
            cells[arm] = {"passed": passed, "of": len(runs),
                          "failing": [{k: v for k, v in r.items() if v} for r in results if any(r.values())]}
            want = 1 if arm in BROKEN_HOSTS else report.get("repeats")
            if len(runs) != want or passed != len(runs):
                problems.append(f"{kind} {arm} {passed}/{len(runs)}")
        per[kind] = cells
    for arm in BROKEN_HOSTS:
        if arm not in (report.get("browsers") or {}).get("chrome", {}):
            problems.append(f"no {arm} run in Chrome")
    return {"lands": not problems, "problems": problems, "browsers": per}


def one_line(result: dict[str, Any]) -> str:
    cells = " ".join(f"{k}:{a}={c['passed']}/{c['of']}" for k, arms in sorted(result["browsers"].items())
                     for a, c in arms.items())
    return f"HOST_ENTRY {'LANDS' if result['lands'] else 'NOT_ESTABLISHED'} {cells or '-'} problems={result['problems']}"


def _first(report: dict, kind: str, arm: str) -> dict:
    return report["browsers"][kind][arm][0]


RED_CASES = [
    ("H1-sample-fetched", lambda r: _first(r, "chrome", "open-save")["fixtureRequests"].append({"method": "GET", "url": "x/e1-fixtures/manifest.json"})),
    ("H1-picker-live", lambda r: _first(r, "firefox", "open-save")["pickers"].update(openFileDisabled=False)),
    ("H1-not-isolated", lambda r: _first(r, "firefox", "conflict")["host"]["isolation"].update(crossOriginIsolated=False)),
    ("H2-server-unchanged", lambda r: _first(r, "chrome", "open-save")["serverAfter"].update(sha256=r["original"]["sha256"])),
    ("H2-no-heading-on-server", lambda r: _first(r, "firefox", "open-save")["serverAfter"].update(heading=False)),
    ("H2-page-lies", lambda r: _first(r, "chrome", "open-save")["serverAfter"].update(sha256="0" * 64)),
    ("H2-etag-unchanged", lambda r: _first(r, "firefox", "open-save")["serverAfter"].update(etag=_first(r, "firefox", "open-save")["serverBefore"]["etag"])),
    ("H2-no-chaining", lambda r: _first(r, "chrome", "open-save")["host"]["saves"][1].update(ifMatch=_first(r, "chrome", "open-save")["host"]["saves"][0]["ifMatch"])),
    ("H2-second-save-lost", lambda r: _first(r, "firefox", "open-save")["serverAfter"].update(sha256=_first(r, "firefox", "open-save")["host"]["saves"][0]["sha256"])),
    ("H2-other-document", lambda r: _first(r, "chrome", "open-save")["serverAfter"].update(texts=["list", "contexts"])),
    ("H2-ctrl-s-ignored", lambda r: _first(r, "firefox", "open-save").update(ctrlS=False)),
    ("H3-overwrote", lambda r: _first(r, "chrome", "conflict")["serverAfter"].update(sha256=_first(r, "chrome", "conflict")["host"]["saves"][0]["sha256"])),
    ("H3-said-saved", lambda r: _first(r, "firefox", "conflict")["saved"].update(latency="存回 80 ms")),
    ("H3-view-reloaded", lambda r: _first(r, "chrome", "conflict")["afterWait"].update(revision="0")),
    # §9.4 「計數」: the second save now succeeds -- into the copy.  Red when it goes anywhere else, carries the
    # token, makes another copy, leaves the copy holding the first save, or renames the view.
    ("H3-second-press-overwrote", lambda r: _first(r, "firefox", "conflict")["host"]["saves"][1]["attempts"][0].update(target="original")),
    ("H3-second-save-carried-token", lambda r: _first(r, "chrome", "conflict")["host"]["saves"][1]["attempts"][0].update(withToken=True)),
    ("H3-second-copy", lambda r: _first(r, "firefox", "conflict")["copiesAfter"].append(dict(_first(r, "firefox", "conflict")["copiesAfter"][0], name="x（衝突副本）.odt"))),
    ("H3-copy-holds-first-save", lambda r: _first(r, "chrome", "conflict")["copiesAfter"][0].update(sha256=_first(r, "chrome", "conflict")["host"]["saves"][0]["sha256"])),
    ("H3-view-renamed", lambda r: _first(r, "firefox", "conflict")["savedAgain"].update(doc="x（衝突副本）.odt")),
    ("H3-edits-lost", lambda r: _first(r, "chrome", "conflict").update(copiesAfter=[])),
    ("H3-intruder-refused", lambda r: _first(r, "firefox", "conflict")["intruded"].update(status=423)),
    ("H3-lock-died", lambda r: _first(r, "chrome", "conflict")["host"]["saves"][0]["attempts"].append(
        {"status": 412, "withToken": False})),
    ("H5-opened-anyway", lambda r: _first(r, "chrome", "broken")["final"].update(state="ready", doc="list-contexts.odt")),
    ("H5-sample-fetched", lambda r: _first(r, "chrome", "broken")["fixtureRequests"].append({"method": "GET", "url": "x/e1-fixtures/list-contexts.odt"})),
    ("H5-no-save-accepted", lambda r: _first(r, "chrome", "broken-no-save")["final"].update(state="ready")),
    ("H5-drain-blind", lambda r: _first(r, "chrome", "broken")["cdp"].update(documents=[])),
    ("original-has-heading", lambda r: r["original"].update(heading=True)),
]


LOCK_TOKEN_CASES = {"H3-intruder-refused", "H3-lock-died"}


def red_cases(path: Path) -> int:
    base = json.loads(path.read_text())
    baseline = score(base, strict=False)
    print(("GREEN" if baseline["lands"] else "RED  ") + " base " + one_line(baseline))
    ok = baseline["lands"]
    for name, mutate in RED_CASES:
        if name in LOCK_TOKEN_CASES and (base.get("intruder") or {}).get("mode") != "lock-token":
            print(f"SKIP  {name:24} the report predates the token intruder; its H3 is not pinned")
            continue
        mutated = copy.deepcopy(base)
        mutate(mutated)
        result = score(mutated, strict=False)
        ok = ok and not result["lands"]
        print(("RED  " if not result["lands"] else "GREEN") + f" {name:24} " + one_line(result))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=("shakedown", "counted"))
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--arms", default="open-save,conflict,broken,broken-no-save",
                        help="shakedown only: a counted run always runs every arm")
    parser.add_argument("--score", type=Path)
    parser.add_argument("--red-cases", type=Path)
    args = parser.parse_args()
    if args.red_cases:
        return red_cases(args.red_cases)
    if args.score:
        report = json.loads(args.score.read_text())
        result = score(report, strict=report.get("label") == "counted")
        print(one_line(result))
        return 0 if result["lands"] else 1
    if not args.label:
        parser.error("--label is required for a run")

    instance = Instance(args.ddev_root)
    intruder = SAMPLE.read_bytes()
    report: dict[str, Any] = {
        "probe": "m3-host-entry", "label": args.label, "startedAt": utc_now(),
        "criteria": "specs/SPEC-M3-host-entry.md §4", "repeats": args.repeats,
        "runner": {"path": str(Path(__file__).relative_to(REPO)), "sha256": sha256_file(Path(__file__))},
        "instance": instance.describe(),
        "page": {"web": sha256_file(PAGE), "dist": sha256_file(DIST / "e2-editor-app.js")},
        "product": {name: sha256_file(DIST / name) for name in PRODUCT_FILES},
        # Every module of the shell bundle as served -- the seven product files
        # alone left eleven of the page's imports unbound (gate 0's correction).
        "shell": served_shell(),
        "original": {"source": str(FIXTURE.relative_to(DIST)), "sha256": sha256_file(FIXTURE),
                     "heading": has_heading(FIXTURE.read_bytes()),
                     "texts": paragraph_texts(FIXTURE.read_bytes())},
        "intruder": {"source": str(SAMPLE.relative_to(DIST)), "sha256": sha256_file(SAMPLE),
                     "mode": "lock-token", "principal": "admin, the page's own user"},
        "browsers": {},
    }
    if args.label == "counted" and (report["instance"]["app"]["dirty"]
                                    or report["page"]["web"] != report["page"]["dist"]
                                    or report["shell"]["differsFromManifest"]):
        print("refusing a counted run: dirty app tree, dist page differs from web/, or the served"
              " shell is not a frozen generation", file=sys.stderr)
        return 2
    (PROJECT / "build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m3-host-entry-", dir=PROJECT / "build") as scratch:
        for kind in args.browsers.split(","):
            wanted = set(args.arms.split(",")) if args.label == "shakedown" \
                else {"open-save", "conflict", *BROKEN_HOSTS}
            arms: dict[str, list] = {}
            for arm in ("open-save", "conflict"):
                if arm not in wanted:
                    continue
                arms[arm] = []
                for attempt in range(args.repeats):
                    arms[arm].append(run_arm(arm, kind, instance, Path(scratch) / f"{kind}-{arm}-{attempt}",
                                             intruder))
            for arm in BROKEN_HOSTS:
                if kind == "chrome" and arm in wanted:
                    arms[arm] = [run_arm(arm, kind, instance, Path(scratch) / f"chrome-{arm}", intruder)]
            report["browsers"][kind] = arms
    report["lockAtEnd"] = server_lock(instance)
    if report["lockAtEnd"]["lock"] == "1" and report["lockAtEnd"]["fileId"]:
        report["lockAtEnd"]["cleared"] = clear_lock(instance, report["lockAtEnd"]["fileId"])
    instance.upload(FIXTURE, NAME)   # leave the file as the runner found it
    conflict_copies(instance, remove=True)
    report["completedAt"] = utc_now()
    result = score(report, strict=args.label == "counted")
    report["score"] = result
    out = EVIDENCE / ("runs" if args.label == "counted" else "shakedown") / \
        f"{report['startedAt'].replace(':', '').replace('+0000', 'Z')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"report": str(out)}, ensure_ascii=False))
    print(one_line(result))
    return 0 if result["lands"] else 1


if __name__ == "__main__":
    sys.exit(main())
