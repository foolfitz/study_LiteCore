#!/usr/bin/env python3
"""SPEC-M4-ods-in-nextcloud §4 Phase H on the owner's ddev instance: H1, H2, H3, H6 -- the
read-only spreadsheet viewer through the Nextcloud host (host 0.2.29).  H4 is the 0.2.28 host arms'
own runners re-run on 0.2.29; H5 is the packager's --selftest and check_m3_assets' K0/H5-1 clauses;
H7 is the owner's.  Never changes the app, the product or dist/.

  H1  one Files listing holding an ODS, an ODT, an XLSX and a PDF: the LiteCore action is offered
      for the ODS and the ODT and NOT for the two sampled others, read from each row's action menu.
      The ODS row is the positive control of "offered".
  H2  the ODS opened from Files lands on the viewer route with that fileId; the page reports
      parts == 3 and documentType "spreadsheet"; the container's Apache access.log between the
      offsets around the session carries no LOCK/PUT/MOVE/PROPPATCH for that file, the browser sent
      only GETs for it, and the file's ETag and version count are unchanged.  POSITIVE CONTROL in
      the same run, the same log: the ODT opened through the editor route shows a LOCK.
      RED CASE (arm `lock-taking-host`): a fetch wrapper injected before the page's scripts LOCKs
      the file before the host's GET -- a viewer host that takes a lock -- and H2 must go red.
  H3  E9 through the host page: three tabs whose text is the engine's part names, a click on tab k
      reads back k from the session (the engine's answer), no adapter fallback.
  H6  the viewer document's COOP, COEP and CSP equal the editor document's, nonces removed, on the wire.

  check_m4_host_viewer.py --selftest
  check_m4_host_viewer.py --label shakedown|counted [--ddev-root DIR]
  check_m4_host_viewer.py --score REPORT.json
Report: findings/evidence/m4-ods/phase-h/<label>/<UTC>.json
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_skeleton_open import DEFAULT_DDEV, FILES, Instance  # noqa: E402
from probe_m3_assets import AccessLog  # noqa: E402
from probe_m3_gate0_coep import DIST, EventChrome, Wire, browser_login, sha256_file, utc_now, wait_until  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m4-ods" / "phase-h"
ODS_FIXTURE = PROJECT / "test-docs" / "ods" / "ladder" / "three-sheets-distinct.ods"
ODT_FIXTURE = DIST / "e1-fixtures" / "multi-paragraph.odt"
ODS_NAMES = ["Alpha", "Beta", "Gamma"]
MIMES = {"ods": "application/vnd.oasis.opendocument.spreadsheet", "odt": "application/vnd.oasis.opendocument.text",
         "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "pdf": "application/pdf"}
OFFERED = {"ods": True, "odt": True, "xlsx": False, "pdf": False}
ACTION_ID = "litecore-open"
VIEWER_ROUTE = "/ods-viewer.html"
EDITOR_ROUTE = "/e2-editor.html"
WRITES = {"LOCK", "PUT", "MOVE", "PROPPATCH", "DELETE", "MKCOL", "COPY"}
ARMS = ("plain", "lock-taking-host")
CLICK_ORDER = [1, 2, 0]
# Injected before any page script (the red case): the first GET of the file's bytes is preceded
# by a LOCK of the same URL -- what a viewer host must never do.
LOCK_TAKING_FETCH = """(() => { const native = globalThis.fetch; let armed = true;
  globalThis.fetch = async function (url, init) {
    const u = String(url);
    if (armed && u.includes('/remote.php/dav/files/') && (!init || !init.method || init.method === 'GET')) {
      armed = false;
      await native(u, { method: 'LOCK', credentials: 'same-origin', headers: {
        'Content-Type': 'application/xml; charset=utf-8', Timeout: 'Second-60',
        requesttoken: document.head.dataset.requesttoken || '', 'X-Requested-With': 'XMLHttpRequest' },
        body: '<?xml version="1.0" encoding="utf-8"?><d:lockinfo xmlns:d="DAV:"><d:lockscope><d:exclusive/>'
          + '</d:lockscope><d:locktype><d:write/></d:locktype><d:owner>red case</d:owner></d:lockinfo>' }).catch(() => {});
    }
    return native.call(this, url, init);
  }; })();"""
VIEWER_STATE = """(() => { const r = window.__odsViewer; const s = r && r.state; return JSON.stringify({
  state: s ? s.state : null, parts: s ? s.parts : null, documentType: s ? s.documentType : null,
  partNames: s ? s.partNames : null, namesFromEngine: s ? s.namesFromEngine : null,
  adapterFallbacks: s ? s.adapterFallbacks : null, currentPart: s ? s.currentPart : null,
  currentPartReadBack: s ? s.currentPartReadBack : null, error: s && s.error ? s.error.code : null,
  lastRefusal: s && s.lastRefusal ? s.lastRefusal.code : null, host: r ? r.host : null,
  hostError: r && r.hostError ? r.hostError.code : null,
  tabs: [...document.querySelectorAll('#tab-strip .ods-tab')].map((b) => ({ part: Number(b.dataset.part),
    text: b.textContent, selected: b.getAttribute('aria-selected'), disabled: b.disabled })) }); })()"""
HOST_RECORD = "(() => document.documentElement.getAttribute('data-litecore-viewer'))()"
EDITOR_HOST_RECORD = "(() => document.documentElement.getAttribute('data-litecore'))()"


# ---------------------------------------------------------------- fixtures --
def minimal_xlsx() -> bytes:
    """A zip Nextcloud types by its extension; the content only has to be a workbook shell."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets/></workbook>')
    return buffer.getvalue()


def minimal_pdf() -> bytes:
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>"]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def fixtures() -> dict[str, bytes]:
    return {"ods": ODS_FIXTURE.read_bytes(), "odt": ODT_FIXTURE.read_bytes(), "xlsx": minimal_xlsx(), "pdf": minimal_pdf()}


# -------------------------------------------------------------- the server --
def dav_raw(instance: Instance, method: str, url: str, body: bytes | None = None,
            headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    import base64
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    request.add_header("Authorization", "Basic " + base64.b64encode(f"admin:{instance.password}".encode()).decode())
    try:
        with urllib.request.urlopen(request, context=instance.tls, timeout=60) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def put_file(instance: Instance, name: str, data: bytes, mime: str) -> dict[str, Any]:
    status, _ = instance.dav("PUT", name, data, {"Content-Type": mime})
    return {"putStatus": status, "name": name, "mime": mime, "bytes": len(data), **server_file(instance, name)}


def server_file(instance: Instance, name: str) -> dict[str, Any]:
    body = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">'
            b"<d:prop><oc:fileid/><d:getetag/><d:getcontentlength/><d:getlastmodified/></d:prop></d:propfind>")
    _, answer = instance.dav("PROPFIND", name, body, {"Depth": "0", "Content-Type": "application/xml"})
    fileid = re.search(rb"<oc:fileid>(\d+)</oc:fileid>", answer)
    etag = re.search(rb"<d:getetag>([^<]*)</d:getetag>", answer)
    record = {"fileId": int(fileid.group(1)) if fileid else None,
              "etag": etag.group(1).decode().strip('"').replace("&quot;", "") if etag else None,
              "encodedName": urllib.parse.quote(name)}
    if record["fileId"]:
        status, versions = dav_raw(instance, "PROPFIND", f"{instance.base}/remote.php/dav/versions/admin/versions/{record['fileId']}",
                                   b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:getlastmodified/></d:prop></d:propfind>',
                                   {"Depth": "1", "Content-Type": "application/xml"})
        record["versionsStatus"] = status
        record["versions"] = max(0, versions.count(b"<d:response>") - 1) if status == 207 else None
    return record


def log_window(log: AccessLog, start: int, end: int) -> list[dict[str, Any]]:
    rows = log.since(start)
    # `since` reads to the end of the file; keep what the end offset covers by re-reading is not
    # possible per row, so the window is "from start, as of the moment `end` was taken" -- the runner
    # takes `end` right after the browser left the page.
    return rows


# -------------------------------------------------------------- the browser --
def row_actions(session, name: str) -> dict[str, Any]:
    """Open the row's action menu and read every action id offered, then close it."""
    row = f'[data-cy-files-list-row-name={json.dumps(name, ensure_ascii=False)}]'
    present = wait_until(session, f"(() => document.querySelector({json.dumps(row)}) !== null)()", 60)
    opened = evaluate(session, f"""(() => {{ const r = document.querySelector({json.dumps(row)}); if (!r) return 'no row';
      const b = r.querySelector('[data-cy-files-list-row-actions] button'); if (!b) return 'no menu button';
      b.click(); return 'clicked'; }})()""")
    time.sleep(0.8)
    actions = evaluate(session, "(() => [...document.querySelectorAll('[data-cy-files-list-row-action]')]"
                                ".map((e) => e.getAttribute('data-cy-files-list-row-action')))()") or []
    evaluate(session, "(() => { document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); "
                      "document.body.click(); return true; })()")
    time.sleep(0.3)
    return {"rowPresent": present is True or isinstance(present, bool), "menu": opened, "actions": actions,
            "offered": ACTION_ID in actions}


def open_by_click(session, name: str, route: str) -> dict[str, Any]:
    selector = (f'[data-cy-files-list-row-name={json.dumps(name, ensure_ascii=False)}]'
                ' [data-cy-files-list-row-name-link]')
    record: dict[str, Any] = {"filesRow": wait_until(session, f"(() => document.querySelector({json.dumps(selector)}) !== null)()", 60)}
    if isinstance(session, EventChrome):
        session.drain()
    record["clickedFrom"] = evaluate(session, "(() => location.href)()")
    session.click(selector)
    record["landed"] = wait_until(session, f"(() => location.pathname.endsWith({json.dumps(route)}) && location.href)()", 60)
    return record


def dav_requests(events: list[dict[str, Any]], encoded_name: str) -> list[dict[str, str]]:
    return [{"method": e["params"]["request"]["method"], "url": e["params"]["request"]["url"]}
            for e in events if e["method"] == "Network.requestWillBeSent"
            and encoded_name in e["params"]["request"]["url"]]


def run_arm(arm: str, instance: Instance, log: AccessLog, files: dict[str, dict[str, Any]]) -> dict[str, Any]:
    record: dict[str, Any] = {"arm": arm, "startedAt": utc_now()}
    session = EventChrome("cold")
    record["browser"] = session.version
    try:
        if arm == "lock-taking-host":
            session.call("Page.addScriptToEvaluateOnNewDocument", {"source": LOCK_TAKING_FETCH})
        record["login"] = browser_login(session, instance.base, instance.password)
        navigate(session, instance.base + FILES, timeout=120)
        # H1: every row's menu, the ODS row first (the positive control of "offered").
        record["h1"] = {kind: row_actions(session, files[kind]["name"]) for kind in ("ods", "odt", "xlsx", "pdf")}
        # H2 / H3: the ODS through its row.
        ods = files["ods"]
        record["odsBefore"] = server_file(instance, ods["name"])
        record["logStart"] = log.offset()
        record["open"] = open_by_click(session, ods["name"], VIEWER_ROUTE)
        raw = wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore-viewer');"
                                  " return v && JSON.parse(v).done && v; })()", 300)
        record["host"] = json.loads(raw) if isinstance(raw, str) else {"notReported": raw}
        record["page"] = json.loads(evaluate(session, VIEWER_STATE))
        record["clicks"] = []
        for k in CLICK_ORDER:
            session.click(f'.ods-tab[data-part="{k}"]')
            state = wait_until(session, f"(() => {{ const s = window.__odsViewer && window.__odsViewer.state;"
                                        f" return s && (s.currentPartReadBack === {k} || s.lastRefusal) && JSON.stringify(s); }})()", 60)
            page = json.loads(evaluate(session, VIEWER_STATE))
            record["clicks"].append({"requested": k, "currentPart": page["currentPart"],
                                     "currentPartReadBack": page["currentPartReadBack"], "lastRefusal": page["lastRefusal"],
                                     "timedOut": isinstance(state, dict) and state.get("timedOut")})
        record["browserDav"] = dav_requests(session.drain(), ods["encodedName"]) if isinstance(session, EventChrome) else None
        navigate(session, instance.base + FILES, timeout=120)
        time.sleep(2)
        record["logEnd"] = log.offset()
        record["odsAfter"] = server_file(instance, ods["name"])
        record["odsLog"] = [r for r in log.since(record["logStart"]) if ods["encodedName"] in r.get("target", "")]
        # The positive control: the ODT through the editor route, in the same log.
        odt = files["odt"]
        record["controlLogStart"] = log.offset()
        record["controlOpen"] = open_by_click(session, odt["name"], EDITOR_ROUTE)
        raw = wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                                  " return v && JSON.parse(v).done && v; })()", 300)
        record["controlHost"] = {"lock": (json.loads(raw).get("lock") if isinstance(raw, str) else None),
                                 "reported": isinstance(raw, str)}
        navigate(session, instance.base + FILES, timeout=120)
        time.sleep(2)
        record["controlLogEnd"] = log.offset()
        record["odtLog"] = [r for r in log.since(record["controlLogStart"]) if odt["encodedName"] in r.get("target", "")]
    except Exception as error:  # noqa: BLE001 -- recorded
        import traceback
        record["error"] = f"{type(error).__name__}: {error}"
        record["traceback"] = traceback.format_exc()[-2000:]
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass
    record["completedAt"] = utc_now()
    return record


def wire_headers(instance: Instance, files: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """H6: both documents' isolation headers, read without a browser."""
    wire = Wire(instance)
    wire.login()
    out = {}
    for kind, route in (("ods", "ods-viewer.html"), ("odt", "e2-editor.html")):
        url = f"{instance.base}/index.php/apps/litecore/r/{route}?fileId={files[kind]['fileId']}"
        try:
            response = wire.opener.open(url, timeout=120)
            headers = response.headers
            out[kind] = {"status": response.status, "url": response.geturl(),
                         "coop": headers.get("cross-origin-opener-policy"), "coep": headers.get("cross-origin-embedder-policy"),
                         "csp": headers.get("content-security-policy")}
        except urllib.error.HTTPError as error:
            out[kind] = {"status": error.code, "url": error.geturl(), "body": error.read()[:300].decode(errors="replace")}
    return out


# ---------------------------------------------------------------- judges --
def strip_nonce(csp: str | None) -> str | None:
    return re.sub(r"'nonce-[^']*'", "'nonce-X'", csp) if isinstance(csp, str) else csp


def h1(run: dict[str, Any]) -> list[str]:
    bad = []
    rows = run.get("h1") or {}
    for kind, want in OFFERED.items():
        row = rows.get(kind) or {}
        if not isinstance(row.get("actions"), list) or row.get("menu") != "clicked":
            bad.append(f"H1 {kind}: the row's menu was not read ({row.get('menu')})")
        elif row.get("offered") != want:
            bad.append(f"H1 {kind}: action {'offered' if row.get('offered') else 'not offered'}, want {'offered' if want else 'not offered'}"
                       f" (menu: {row.get('actions')})")
    return bad


def h2(run: dict[str, Any], expect_red: bool = False) -> list[str]:
    bad = []
    landed = str((run.get("open") or {}).get("landed") or "")
    file_id = (run.get("odsBefore") or {}).get("fileId")
    if VIEWER_ROUTE + "?" not in landed and not landed.endswith(VIEWER_ROUTE) or f"fileId={file_id}" not in landed:
        bad.append(f"H2 landed on {landed!r}, not the viewer route with fileId={file_id}")
    page = run.get("page") or {}
    if page.get("parts") != 3 or page.get("documentType") != "spreadsheet" or page.get("state") != "ready":
        bad.append(f"H2 page parts {page.get('parts')} documentType {page.get('documentType')} state {page.get('state')}")
    writes = [r for r in run.get("odsLog") or [] if r.get("method") in WRITES]
    if writes:
        bad.append(f"H2 writes in the log window for the ODS: {[(r['method'], r['status']) for r in writes]}")
    browser_writes = [r for r in run.get("browserDav") or [] if r.get("method") != "GET"]
    if browser_writes:
        bad.append(f"H2 the browser sent {browser_writes} for the ODS")
    before, after = run.get("odsBefore") or {}, run.get("odsAfter") or {}
    if not before.get("etag") or before.get("etag") != after.get("etag"):
        bad.append(f"H2 ETag moved: {before.get('etag')} -> {after.get('etag')}")
    if before.get("versions") is None or before.get("versions") != after.get("versions"):
        bad.append(f"H2 version count moved: {before.get('versions')} -> {after.get('versions')}")
    if run.get("logEnd") is None or run.get("logStart") is None:
        bad.append("H2 no log window")
    control = [r for r in run.get("odtLog") or [] if r.get("method") == "LOCK"]
    if not control:
        bad.append("H2 positive control: no LOCK for the ODT in the same log -- the window cannot be trusted")
    return bad


def h3(run: dict[str, Any]) -> list[str]:
    bad = []
    page = run.get("page") or {}
    texts = [t.get("text") for t in page.get("tabs") or []]
    if texts != ODS_NAMES or page.get("partNames") != ODS_NAMES:
        bad.append(f"H3 tabs {texts} / partNames {page.get('partNames')}, want {ODS_NAMES}")
    if page.get("namesFromEngine") is not True:
        bad.append(f"H3 namesFromEngine {page.get('namesFromEngine')}")
    if page.get("adapterFallbacks") != []:
        bad.append(f"H3 adapterFallbacks {page.get('adapterFallbacks')}")
    clicks = run.get("clicks") or []
    if sorted(c.get("requested") for c in clicks) != sorted(CLICK_ORDER):
        bad.append(f"H3 clicked {[c.get('requested') for c in clicks]}, want {CLICK_ORDER}")
    for c in clicks:
        if c.get("currentPartReadBack") != c.get("requested") or c.get("lastRefusal"):
            bad.append(f"H3 tab {c.get('requested')}: read back {c.get('currentPartReadBack')}, refusal {c.get('lastRefusal')}")
    return bad


def h6(report: dict[str, Any]) -> list[str]:
    bad = []
    wire = report.get("wire") or {}
    ods, odt = wire.get("ods") or {}, wire.get("odt") or {}
    if ods.get("status") != 200 or odt.get("status") != 200:
        return [f"H6 documents not fetched: viewer {ods.get('status')}, editor {odt.get('status')}"]
    for header in ("coop", "coep"):
        if not ods.get(header) or ods.get(header) != odt.get(header):
            bad.append(f"H6 {header}: viewer {ods.get(header)!r}, editor {odt.get(header)!r}")
    if not ods.get("csp") or strip_nonce(ods.get("csp")) != strip_nonce(odt.get("csp")):
        bad.append("H6 csp differs between the viewer and the editor documents (nonces removed)")
    return bad


def score(report: dict[str, Any]) -> dict[str, Any]:
    problems: list[str] = []
    runs = {r.get("arm"): r for r in report.get("runs") or []}
    plain = runs.get("plain")
    if plain is None:
        problems.append("no plain arm")
    else:
        if plain.get("error"):
            problems.append(f"plain arm errored: {plain['error']}")
        problems += h1(plain) + h2(plain) + h3(plain)
    problems += h6(report)
    red = runs.get("lock-taking-host")
    if red is None:
        problems.append("red case: the lock-taking-host arm was not run")
    else:
        red_problems = h2(red)
        lock_seen = any(r.get("method") == "LOCK" for r in red.get("odsLog") or [])
        if not lock_seen or not any(p.startswith("H2 writes") or p.startswith("H2 the browser sent") for p in red_problems):
            problems.append(f"red case: a lock-taking host did not turn H2 red (lock seen {lock_seen}; {red_problems[:2]})")
    verdict = "VIEWER HOST HOLDS" if not problems else "RED"
    return {"verdict": verdict, "problems": problems}


# -------------------------------------------------------------- selftest --
def synthetic() -> dict[str, Any]:
    def arm(name, lock_in_ods_window=False):
        return {"arm": name, "error": None,
                "h1": {k: {"menu": "clicked", "actions": ["litecore-open", "details"] if v else ["details"], "offered": v}
                       for k, v in OFFERED.items()},
                "open": {"landed": f"https://x/index.php/apps/litecore/r/abc-def/ods-viewer.html?fileId=42"},
                "odsBefore": {"fileId": 42, "etag": "e1", "versions": 0, "encodedName": "x.ods"},
                "odsAfter": {"fileId": 42, "etag": "e1", "versions": 0, "encodedName": "x.ods"},
                "logStart": 10, "logEnd": 20,
                "odsLog": [{"method": "GET", "target": "/remote.php/dav/files/admin/x.ods", "status": 200}]
                + ([{"method": "LOCK", "target": "/remote.php/dav/files/admin/x.ods", "status": 200}] if lock_in_ods_window else []),
                "browserDav": [{"method": "GET", "url": "https://x/remote.php/dav/files/admin/x.ods"}]
                + ([{"method": "LOCK", "url": "https://x/remote.php/dav/files/admin/x.ods"}] if lock_in_ods_window else []),
                "page": {"state": "ready", "parts": 3, "documentType": "spreadsheet", "partNames": list(ODS_NAMES),
                         "namesFromEngine": True, "adapterFallbacks": [], "currentPart": 0, "currentPartReadBack": 0,
                         "tabs": [{"part": k, "text": n} for k, n in enumerate(ODS_NAMES)]},
                "clicks": [{"requested": k, "currentPartReadBack": k, "lastRefusal": None} for k in CLICK_ORDER],
                "odtLog": [{"method": "LOCK", "target": "/remote.php/dav/files/admin/x.odt", "status": 200},
                           {"method": "GET", "target": "/remote.php/dav/files/admin/x.odt", "status": 200}]}
    csp = "default-src 'none';script-src 'nonce-AAA' 'strict-dynamic';worker-src 'self'"
    return {"runs": [arm("plain"), arm("lock-taking-host", lock_in_ods_window=True)],
            "wire": {"ods": {"status": 200, "coop": "same-origin", "coep": "require-corp", "csp": csp},
                     "odt": {"status": 200, "coop": "same-origin", "coep": "require-corp", "csp": csp.replace("AAA", "BBB")}}}


def selftest() -> int:
    def plain(b):
        return b["runs"][0]
    mutations = [
        ("H1", "the ODS row does not offer the action", lambda b: plain(b)["h1"]["ods"].update(offered=False, actions=["details"])),
        ("H1", "the XLSX row offers the action", lambda b: plain(b)["h1"]["xlsx"].update(offered=True, actions=["litecore-open"])),
        ("H1", "a row's menu was not read", lambda b: plain(b)["h1"]["pdf"].update(menu="no menu button", actions=None)),
        ("H2", "a PUT in the ODS log window", lambda b: plain(b)["odsLog"].append({"method": "PUT", "target": "x.ods", "status": 204})),
        ("H2", "a PROPPATCH in the ODS log window", lambda b: plain(b)["odsLog"].append({"method": "PROPPATCH", "target": "x.ods", "status": 207})),
        ("H2", "the browser sent a LOCK", lambda b: plain(b)["browserDav"].append({"method": "LOCK", "url": "x.ods"})),
        ("H2", "the ETag moved", lambda b: plain(b)["odsAfter"].update(etag="e2")),
        ("H2", "a version appeared", lambda b: plain(b)["odsAfter"].update(versions=1)),
        ("H2", "landed on the editor route", lambda b: plain(b)["open"].update(landed="https://x/r/abc/e2-editor.html?fileId=42")),
        ("H2", "the page reports text, 1 part", lambda b: plain(b)["page"].update(parts=1, documentType="text")),
        ("H2", "the positive control shows no LOCK", lambda b: plain(b).update(odtLog=[{"method": "GET", "target": "x.odt", "status": 200}])),
        ("H3", "a tab's text is synthesised", lambda b: plain(b)["page"]["tabs"][1].update(text="工作表 2")),
        ("H3", "names not from the engine", lambda b: plain(b)["page"].update(namesFromEngine=False)),
        ("H3", "a click read back another part", lambda b: plain(b)["clicks"][0].update(currentPartReadBack=0)),
        ("H3", "a click was refused", lambda b: plain(b)["clicks"][2].update(lastRefusal="PART_OUT_OF_RANGE")),
        ("H6", "the viewer document has no COEP", lambda b: b["wire"]["ods"].update(coep=None)),
        ("H6", "the viewer's CSP differs beyond the nonce", lambda b: b["wire"]["ods"].update(csp="default-src 'self'")),
        ("H6", "the viewer document 500s", lambda b: b["wire"]["ods"].update(status=500)),
        ("red case", "a lock-taking host left H2 green", lambda b: (b["runs"][1].update(odsLog=[{"method": "GET", "target": "x.ods", "status": 200}],
                                                                                        browserDav=[{"method": "GET", "url": "x"}]))),
        ("red case", "the red arm was not run", lambda b: b["runs"].pop(1)),
    ]
    control = score(synthetic())
    results = [("control (every criterion met, the red case red)", control["verdict"] == "VIEWER HOST HOLDS", control["problems"])]
    for clause, label, edit in mutations:
        broken = copy.deepcopy(synthetic())
        edit(broken)
        got = score(broken)["problems"]
        ok = any(p.startswith(clause) for p in got)
        results.append((f"{clause}: {label}", ok, got[:2]))
    for label, ok, detail in results:
        print(("PASS " if ok else "FAIL ") + label + (f"  {detail}" if not ok else ""))
    passed = sum(ok for _, ok, _ in results)
    print(f"selftest: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


# ------------------------------------------------------------------ main --
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--label", choices=("shakedown", "counted"))
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--score", type=Path)
    parser.add_argument("--arms", default=",".join(ARMS))
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if args.score:
        result = score(json.loads(args.score.read_text()))
        print(result["verdict"], *result["problems"], sep="\n  ")
        return 0 if result["verdict"] == "VIEWER HOST HOLDS" else 1
    if not args.label:
        parser.error("--selftest, --label or --score")
    instance = Instance(args.ddev_root)
    log = AccessLog(instance)
    report: dict[str, Any] = {"runner": "check_m4_host_viewer.py", "runnerSha256": sha256_file(Path(__file__)),
                              "label": args.label, "startedAt": utc_now(), "spec": "SPEC-M4-ods-in-nextcloud §4 H1-H3, H6",
                              "instance": instance.describe(), "fixtures": {}, "runs": []}
    out = EVIDENCE / args.label / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = fixtures()
        for arm in args.arms.split(","):
            files = {}
            for kind, mime in MIMES.items():
                name = f"M4 檢視 測試 {arm}.{kind}"
                files[kind] = put_file(instance, name, data[kind], mime)
                files[kind]["sha256"] = __import__("hashlib").sha256(data[kind]).hexdigest()
            report["fixtures"][arm] = files
            if arm == "plain":
                report["wire"] = wire_headers(instance, files)
            print(f"arm {arm}", flush=True)
            report["runs"].append(run_arm(arm, instance, log, files))
            out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    finally:
        report["completedAt"] = utc_now()
        report["score"] = score(report)
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(REPO))
    print(report["score"]["verdict"], *report["score"]["problems"], sep="\n  ")
    return 0 if report["score"]["verdict"] == "VIEWER HOST HOLDS" else 1


if __name__ == "__main__":
    sys.exit(main())
