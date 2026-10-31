#!/usr/bin/env python3
"""M3 versions: arm R1 of specs/SPEC-M3-versions.md §4.

Open a fresh file from Files with the `litecore` host (token lock held), save
twice, restore the oldest version as Files' Versions tab would (a MOVE with no
lock token, which a token lock does not stop), save a third time, leave. At
every step the runner reads Nextcloud's own version list and the bytes of every
non-current version, so "versions correct" is judged on the server's history,
not on the host's record of what it sent.

    python3 wasm_sdk_probe/tools/check_m3_versions.py --label shakedown --browsers chrome --repeats 1
    python3 wasm_sdk_probe/tools/check_m3_versions.py --label counted
    python3 wasm_sdk_probe/tools/check_m3_versions.py --score findings/evidence/m3-versions/runs/<file>.json
    python3 wasm_sdk_probe/tools/check_m3_versions.py --red-cases findings/evidence/m3-versions/shakedown/<file>.json

Everything that drives the page is borrowed from check_m3_locks.py, which is
not edited (its hash is bound to the LOCKS LAND counted run).
"""
from __future__ import annotations

import argparse
import copy
import email.utils
import hashlib
import http.client
import json
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from k_static_target import static_target  # noqa: E402
from check_m3_host_entry import host_record, requests_matching  # noqa: E402
from check_m3_locks import (  # noqa: E402
    ODT, PAGE_SHA256, PROJECT, REPO, LockChrome, Server, attempts, edit, edited, held_at_open, insert_marker, login,
    on_wire, one_copy, open_from_files, opened_ok, page_failed_with, save, wire)
from check_m3_skeleton_open import DEFAULT_DDEV, FIXTURE, Instance, binding_fields, host_binding  # noqa: E402
from probe_m3_gate0_coep import DIST, firefox_profile, sha256_file, summarize_cdp, utc_now  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

EVIDENCE = REPO / "findings" / "evidence" / "m3-versions"
VNAME = "M3 版本 測試.odt"
PLAN = {"versions": ("R1", ("chrome", "firefox"), 3)}
# SPEC-M3-asset-delivery K3 re-runs this unchanged against the asset-delivery host;
# the counted run of 2026-09-28 was bound to 49cc4ab, K3's to 5e53362. Ruling D's
# condition 7 re-runs it against 0.2.2 (the host a second apart and reading back):
# a binding, not a criterion (SPEC-M3-versions §3, written before the run).
# SPEC-M3-page-honesty §7.6/§7.11 re-runs it against 0.2.4 (finding 108), written
# 2026-09-29 before that run.
# SPEC-M3-zstd Z3 re-runs it against 0.2.5, written 2026-09-30 before that run.
HOST_COMMIT = "a97724f"   # host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was 3c01876; host 0.2.26 (engine v21, shell v74, finding 154's host rule), 2026-10-17 (host 0.2.26); was 1479e56 (finding 145, host 0.2.24), 2ccf1a9 (SPEC-M3-link-batch §17, host 0.2.23), 237f2cb, e028517, b245ae7, 6b53c2e, d87960d, 069de55, 4140e00, 0488586
NS = {"d": "DAV:", "nc": "http://nextcloud.org/ns"}
LISTING = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns">'
           b"<d:prop><d:getlastmodified/><d:getcontentlength/><nc:version-author/></d:prop></d:propfind>")
MTIME = b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:getlastmodified/></d:prop></d:propfind>'


class VServer(Server):
    """No second user and no shares: R1 is admin alone, plus raw version requests."""

    def setup(self) -> dict[str, Any]:
        return {"clearedLocks": self.clear_locks()}

    def teardown(self) -> None:
        self.clear_locks()
        self.admin.call("teardown", "DELETE", self.admin.dav_path(VNAME))

    def raw(self, step: str, method: str, path: str, body: bytes | None = None,
            headers: dict[str, str] | None = None) -> tuple[Any, bytes]:
        client = self.admin
        request = urllib.request.Request(client.base + path, data=body, method=method,
                                         headers={"X-Requested-With": "XMLHttpRequest", **(headers or {})})
        request.add_header("Authorization", client.auth)
        try:
            with urllib.request.urlopen(request, context=client.tls, timeout=60) as response:
                status, data = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, data = error.code, error.read()
        except (http.client.RemoteDisconnected, ConnectionError, urllib.error.URLError) as error:
            status, data = f"no response: {type(error).__name__}", b""
        client.log.append({"step": step, "actor": client.user, "method": method, "path": urllib.parse.unquote(path),
                           "status": status, "bytes": len(data)})
        return status, data

    def listing(self, step: str, path: str, get_current: bool = False) -> dict[str, Any]:
        """The file's mtime and every version row, with the bytes of every row but the current
        one (revision == mtime). The current row is fetched only when asked (before any restore):
        its GET is 404 when no .v<mtime> file exists, and a server-side TypeError right after a
        restore (evidence README, V3). A 200 there means a version file was written without the
        mtime moving -- the failure shape rows 1 and 3 guard (review item 1)."""
        status, data = self.raw(step, "PROPFIND", self.admin.dav_path(path), MTIME,
                                {"Depth": "0", "Content-Type": "application/xml"})
        if status != 207:
            return {"status": status}
        stamp = ET.fromstring(data).findtext(".//d:getlastmodified", namespaces=NS)
        mtime = int(email.utils.parsedate_to_datetime(stamp).timestamp())
        fileid = self.fileid(self.admin, path)
        status, data = self.raw(step, "PROPFIND", f"/remote.php/dav/versions/admin/versions/{fileid}", LISTING,
                                {"Depth": "1", "Content-Type": "application/xml"})
        if status != 207:
            return {"status": status, "mtime": mtime}
        entries = []
        for response in ET.fromstring(data).iterfind("d:response", NS):
            href = urllib.parse.unquote(response.findtext("d:href", namespaces=NS)).rstrip("/")
            if href.endswith(f"/versions/{fileid}"):
                continue   # the collection itself
            revision = href.rsplit("/", 1)[1]
            entry = {"revision": int(revision), "current": int(revision) == mtime,
                     "author": response.findtext(".//nc:version-author", namespaces=NS)}
            if not entry["current"] or get_current:
                got, body = self.raw(step + " (bytes)", "GET", href[href.index("/remote.php"):])
                entry["get"] = got
                entry["sha256"] = hashlib.sha256(body).hexdigest() if got == 200 else f"GET {got}"
            entries.append(entry)
        return {"status": 207, "mtime": mtime, "fileid": fileid, "entries": sorted(entries, key=lambda e: e["revision"])}


def older(listing: dict[str, Any]) -> list[str]:
    return [e.get("sha256") for e in listing.get("entries") or [] if not e["current"]]


def shape(listing: dict[str, Any]) -> list[tuple[Any, ...]]:
    return [(e["revision"], e["current"], e.get("sha256")) for e in listing.get("entries") or []]


def run_versions(kind: str, server: VServer, scratch: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"arm": "versions", "spec": "R1", "browser": kind, "startedAt": utc_now(),
                              "file": {"user": "admin", "path": VNAME, "adminPath": VNAME}}
    record["clearedLocks"] = server.clear_locks()
    record["removedOld"] = server.admin.call("reset", "DELETE", server.admin.dav_path(VNAME))["status"]
    record["reset"] = {"upload": server.upload(server.admin, VNAME), "fileId": server.fileid(server.admin, VNAME)}
    record["copiesBefore"] = server.copies(server.admin, "", VNAME[:-4], remove=True)
    record["L0"] = server.listing("L0", VNAME, get_current=True)
    if kind == "chrome":
        session = LockChrome("cold")
    else:
        session = FirefoxSession("cold", profile_dir=firefox_profile(scratch / f"ff-{time.monotonic_ns()}"))
    record["version"] = getattr(session, "version", None)
    try:
        record["login"] = login(session, server.instance.base, "admin", server.instance.password)
        open_from_files(session, server.instance.base, "", VNAME, record)
        record["afterOpen"] = server.props(server.admin, VNAME)
        record["L1"] = server.listing("L1 after open", VNAME, get_current=True)
        edit(session, record)
        save(session, record, 1)
        time.sleep(3)
        insert_marker(session, record)
        record["inserted1"] = record.pop("inserted")
        save(session, record, 2, how="ctrl-s")
        record["serverAfterSaves"] = server.content(server.admin, VNAME)
        record["afterSaves"] = server.props(server.admin, VNAME)
        record["L2"] = server.listing("L2 after two saves", VNAME, get_current=True)
        oldest = next((e["revision"] for e in record["L2"].get("entries") or [] if not e["current"]), None)
        record["restoredRevision"] = oldest
        record["restore"], _ = server.raw(
            "restore (Files' request, no token)", "MOVE",
            f"/remote.php/dav/versions/admin/versions/{record['reset']['fileId']}/{oldest}", None,
            {"Destination": f"{server.instance.base}/remote.php/dav/versions/admin/restore/target"})
        record["serverAfterRestore"] = server.content(server.admin, VNAME)
        record["afterRestore"] = server.props(server.admin, VNAME)
        record["L3"] = server.listing("L3 after restore", VNAME)
        insert_marker(session, record)
        record["inserted2"] = record.pop("inserted")
        save(session, record, 3)
        record["host"] = host_record(session)
        record["serverAfter"] = server.content(server.admin, VNAME)
        record["lockAfterSave"] = server.props(server.admin, VNAME)
        record["L4"] = server.listing("L4 after the refused save", VNAME)
        found = server.copies(server.admin, "", VNAME[:-4], remove=False)
        record["copyListings"] = [server.listing("copy", c["name"]) for c in found]
        record["copiesAfter"] = server.copies(server.admin, "", VNAME[:-4], remove=True)
        if isinstance(session, LockChrome):
            events = session.drain()
            record["cdp"] = summarize_cdp(events)
            record["fixtureRequests"] = requests_matching(events, "/e1-fixtures/")
            record["davRequests"] = wire(events)
        navigate(session, server.instance.base + "/apps/files/", timeout=120)
        record["release"] = server.wait_unlocked(server.admin, VNAME, 15)
        record["L5"] = server.listing("L5 after leaving", VNAME)
        record["serverAtEnd"] = server.content(server.admin, VNAME)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass
        record["locksAtEnd"] = server.props(server.admin, VNAME)
        record["clearedAtEnd"] = server.clear_locks()
    return record


# --------------------------------------------------------------------------
# Scoring -- raw fields only, one line per row of the spec's table.


def inserted(run: dict[str, Any], key: str) -> list[str]:
    state = run.get(key) or {}
    if "失敗" in (state.get("latency") or "") or not state.get("revision"):
        return [f"{key} {state.get('revision')!r} {state.get('latency')!r}"]
    return []


def score_run(run: dict[str, Any], report: dict[str, Any]) -> list[str]:
    if run.get("fatal"):
        return [f"fatal: {run['fatal'].strip().splitlines()[-1]}"]
    F = report["original"]["sha256"]
    host = run.get("host") or {}
    saves = host.get("saves") or []
    sent = [s.get("sha256") for s in saves]
    bad = opened_ok(run, report) + held_at_open(run) + edited(run)
    bad += inserted(run, "inserted1") + inserted(run, "inserted2")
    # 1: taking the lock makes no version, not even a version file under the current row
    l1 = run.get("L1") or {}
    if [(e["current"], e.get("get")) for e in l1.get("entries") or []] != [(True, 404)]:
        bad.append(f"L1 {[(e['current'], e.get('get')) for e in l1.get('entries') or []]}: want the current row only, GET 404")
    # 2: two saves, both 204 with the token, server holds the second
    if len(saves) != 3 or [attempts(s) for s in saves[:2]] != [[(204, True)], [(204, True)]] \
            or sent[0] == sent[1] or (run.get("serverAfterSaves") or {}).get("sha256") != sent[1]:
        bad.append(f"saves {[attempts(s) for s in saves]}, server after two "
                   f"{((run.get('serverAfterSaves') or {}).get('sha256') or '')[:12]}")
        return bad   # every later row names S1..S3
    S1, S2, S3 = sent
    if len({F, S1, S2, S3}) != 4:
        bad.append(f"the four states are not distinct: {[x and x[:12] for x in (F, S1, S2, S3)]}")
    # 3: history = [F, S1] + current, all by admin; the current row has no version file
    l2 = run.get("L2") or {}
    currents = [e for e in l2.get("entries") or [] if e["current"]]
    if older(l2) != [F, S1] or len(currents) != 1:
        bad.append(f"L2 {shape(l2)}: want [F, S1] + one current")
    elif currents[0].get("get") != 404:
        bad.append(f"L2 current row GET {currents[0].get('get')}: a version file sits under the current mtime")
    if any(e.get("author") != "admin" for e in l2.get("entries") or []):
        bad.append(f"L2 authors {[e.get('author') for e in l2.get('entries') or []]}")
    # 4: the restore goes through the token lock, the lock stays
    opened, restored = run.get("afterOpen") or {}, run.get("afterRestore") or {}
    if run.get("restore") != 201 or (run.get("serverAfterRestore") or {}).get("sha256") != F \
            or restored.get("token") != opened.get("token") or not opened.get("token") \
            or restored.get("etag") == (run.get("afterSaves") or {}).get("etag"):
        bad.append(f"restore {run.get('restore')}, server {((run.get('serverAfterRestore') or {}).get('sha256') or '')[:12]}, "
                   f"token {opened.get('token')} -> {restored.get('token')}")
    # 5: the pre-restore content is kept
    l3 = run.get("L3") or {}
    if older(l3) != [S1, S2]:
        bad.append(f"L3 {shape(l3)}: want [S1, S2] as the older rows")
    if len([e for e in l3.get("entries") or [] if e["current"]]) != 1:
        bad.append(f"L3 {shape(l3)}: want one current row")
    # 6: the third save is refused once, not retried, and goes to a copy; the lock is kept
    if attempts(saves[2]) != [(412, True)]:
        bad.append(f"third save {attempts(saves[2])} (the token is alive: no retry without it)")
    elif saves[2]["attempts"][0].get("ifMatch") != (run.get("afterSaves") or {}).get("etag"):
        bad.append(f"third save's If-Match {saves[2]['attempts'][0].get('ifMatch')} is not the version before the restore "
                   f"{(run.get('afterSaves') or {}).get('etag')}: its 412 is not about the restore")
    else:
        bad += one_copy(run, "衝突副本", S3)
        bad += page_failed_with(run.get("save3State") or {}, "CONFLICT", (saves[2].get("conflictCopy") or {}).get("name") or "?")
    kept = run.get("lockAfterSave") or {}
    if (host.get("lock") or {}).get("state") != "held" or kept.get("token") != opened.get("token"):
        bad.append(f"lock after the third save: host {(host.get('lock') or {}).get('state')}, server token {kept.get('token')}")
    if (run.get("serverAfter") or {}).get("sha256") != F:
        bad.append(f"server {((run.get('serverAfter') or {}).get('sha256') or '')[:12]} is not the restored F")
    bad += on_wire(run, [(204, True), (204, True), (412, True)])
    # 7: a refused save makes no new row and does not move the mtime; the copy has no history
    if shape(run.get("L4") or {}) != shape(l3) or (run.get("L4") or {}).get("mtime") != l3.get("mtime"):
        bad.append(f"L4 {shape(run.get('L4') or {})} != L3")
    copies = run.get("copyListings") or []
    if len(copies) != 1 or [e["current"] for e in copies[0].get("entries") or []] != [True]:
        bad.append(f"copy listings {[shape(c) for c in copies]}: want one copy, current entry only")
    # 8: leaving releases the lock and makes no version
    if not (run.get("release") or {}).get("released"):
        bad.append(f"release {run.get('release')}")
    if shape(run.get("L5") or {}) != shape(run.get("L4") or {}) \
            or (run.get("L5") or {}).get("mtime") != (run.get("L4") or {}).get("mtime"):
        bad.append(f"L5 {shape(run.get('L5') or {})} != L4")
    # total: all four states can be had back, byte for byte, read after leaving
    held = [("F", (run.get("serverAtEnd") or {}).get("sha256") == F), ("S1", S1 in older(run.get("L5") or {})),
            ("S2", S2 in older(run.get("L5") or {})),
            ("S3", [c.get("sha256") for c in run.get("copiesAfter") or []] == [S3])]
    if not all(ok for _, ok in held):
        bad.append(f"not retrievable at the end: {[k for k, ok in held if not ok]}")
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
    if strict and not (report.get("hostRepo") or "").startswith(HOST_COMMIT):
        problems.append(f"host is {report.get('hostRepo')!r}, spec §3 names {HOST_COMMIT}")
    tally: dict[str, dict[str, Any]] = {}
    for run in report.get("runs") or []:
        entry = tally.setdefault(f"{run['browser']}:{run['arm']}", {"pass": 0, "runs": 0, "problems": []})
        entry["runs"] += 1
        bad = score_run(run, report)
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
    return {"verdict": ("VERSIONS CORRECT" if ok else "VERSIONS NOT CORRECT") if strict else ("clean" if ok else "red"),
            "tally": tally, "problems": problems}


def one_line(result: dict[str, Any]) -> str:
    cells = " ".join(f"{k}={v['pass']}/{v['runs']}" for k, v in sorted(result["tally"].items()))
    return f"{result['verdict']} {cells} problems={result['problems']}"


def _each(run: dict, keys: tuple[str, ...], change) -> None:
    for key in keys:
        change(run[key])


def _current(listing: dict) -> dict:
    return next(e for e in listing["entries"] if e["current"])


def _extra(sha: str):
    return lambda listing: listing["entries"].append({"revision": 9_999_999_999, "current": False, "sha256": sha})


def _s(run: dict, n: int) -> str:
    return run["host"]["saves"][n]["sha256"]


def _lose_third_edit(run: dict) -> None:
    run["host"]["saves"][2]["sha256"] = _s(run, 1)
    run["copiesAfter"][0]["sha256"] = _s(run, 1)


def _stale_third(run: dict) -> None:
    run["host"]["saves"][2]["ifMatch"] = '"older"'
    run["host"]["saves"][2]["attempts"][0]["ifMatch"] = '"older"'
    puts = [x for x in run.get("davRequests") or [] if x["method"] == "PUT" and x["url"].endswith(urllib.parse.quote(VNAME))]
    if puts:
        puts[-1]["ifMatch"] = '"older"'


C = ("chrome",)
# (label, mutation, browsers it applies to -- None = both). Each case is meant to be caught by
# its own clause: a clause turned off should leave at least one case green (review item 8).
# The total row's S1/S2 half is implied by rows 5, 7 and 8 together and has no case of its own.
RED_CASES = [
    ("1 other bytes were opened", lambda r: r["host"]["fetched"].update(sha256="0" * 64), None),
    ("1 the read is not the post-lock version", lambda r: r["host"]["fetched"].update(etag='"stale"'), None),
    ("1 lock taken after the read", lambda r: r["host"]["lock"].update(at=r["host"]["fetched"]["at"] + 1), None),
    ("1 L1 taking the lock made a row", lambda r: r["L1"]["entries"].insert(0, {"revision": 1, "current": False, "sha256": "x"}), None),
    ("1 L1 a version file under the current row", lambda r: _current(r["L1"]).update(get=200), None),
    ("2 a save without the token", lambda r: r["host"]["saves"][1]["attempts"][0].update(withToken=False), None),
    ("2 server holds the first save", lambda r: r["serverAfterSaves"].update(sha256=_s(r, 0)), None),
    ("2 the first marker insert failed", lambda r: r["inserted1"].update(latency="插入 失敗"), None),
    ("2 the third edit is lost (S3 == S2)", _lose_third_edit, None),
    ("3 L2 lost the first save", lambda r: r["L2"]["entries"].pop(1), None),
    ("3 L2 version by someone else", lambda r: r["L2"]["entries"][0].update(author="lcprobe"), None),
    ("3 L2 two current rows", lambda r: r["L2"]["entries"].append({**_current(r["L2"]), "revision": 9_999_999_999}), None),
    ("3 L2 a version file under the current row", lambda r: _current(r["L2"]).update(get=200), None),
    ("4 restore refused", lambda r: r.update(restore=423), None),
    ("4 restore did not write", lambda r: r["serverAfterRestore"].update(sha256=_s(r, 1)), None),
    ("4 restore cost the lock", lambda r: r["afterRestore"].update(token=None), None),
    ("4 the ETag did not move", lambda r: r["afterRestore"].update(etag=r["afterSaves"]["etag"]), None),
    ("5 an extra older row after the restore", lambda r: _each(r, ("L3", "L4", "L5"), _extra(r["L2"]["entries"][0]["sha256"])), None),
    ("5 no current row after the restore",
     lambda r: _each(r, ("L3", "L4", "L5"), lambda l: l.update(entries=[e for e in l["entries"] if not e["current"]])), None),
    ("6 third save retried without the token", lambda r: r["host"]["saves"][2]["attempts"].append({"status": 204, "withToken": False}), None),
    ("6 third save's If-Match predates the restore", _stale_third, None),
    ("6 no copy", lambda r: r.update(copiesAfter=[]), None),
    ("6 page says it saved", lambda r: r["save3State"].update(latency="存回 成功"), None),
    ("6 the second marker insert failed", lambda r: r["inserted2"].update(latency="插入 失敗"), None),
    ("6 the lock was lost", lambda r: r["lockAfterSave"].update(token=None), None),
    ("6 the original is not F after the third save", lambda r: r["serverAfter"].update(sha256=_s(r, 2)), None),
    ("6 the wire PUT lacks If", lambda r: [x.update({"if": None}) for x in r["davRequests"] if x["method"] == "PUT"], C),
    ("7 the refused save made a row", lambda r: _each(r, ("L4", "L5"), _extra("z")), None),
    ("7 the refused save moved the mtime", lambda r: _each(r, ("L4", "L5"), lambda l: l.update(mtime=l["mtime"] + 1)), None),
    ("7 the copy has a history", lambda r: r["copyListings"][0]["entries"].insert(0, {"revision": 1, "current": False, "sha256": "w"}), None),
    ("8 not released on leaving", lambda r: r["release"].update(released=False), None),
    ("8 leaving made a row", lambda r: _extra("v")(r["L5"]), None),
    ("8 leaving moved the mtime", lambda r: r["L5"].update(mtime=r["L5"]["mtime"] + 1), None),
    ("total the original is not F at the end", lambda r: r["serverAtEnd"].update(sha256=_s(r, 0)), None),
]


def red_cases(path: Path) -> int:
    """Every case must find its run and turn it red; a case with no clean run to
    mutate is a failure, not a skip."""
    report = json.loads(path.read_text())
    failures = 0
    for label, mutate, only in RED_CASES:
        for browser in (only or PLAN["versions"][1]):
            base = next((r for r in report["runs"] if r["browser"] == browser and not score_run(r, report)), None)
            if base is None:
                print(f"  MISSING {label} [{browser}]: no clean run to mutate")
                failures += 1
                continue
            mutated = copy.deepcopy(base)
            mutate(mutated)
            red = bool(score_run(mutated, report))
            failures += not red
            print(f"  {'red ' if red else 'GREEN'}  {label} [{browser}]")
    # A shakedown is not bound (no testStatic, maybe not the host commit), so its strict score
    # already has problems: the case is red only if the mutation adds a page problem of its own.
    static = copy.deepcopy(report)
    static["static"]["page"]["dist"] = "0" * 64
    added = [p for p in score(static, strict=True)["problems"] if p not in score(report, strict=True)["problems"]]
    red = any(p.startswith("page ") for p in added)
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
    parser.add_argument("--score", type=Path)
    parser.add_argument("--red-cases", type=Path)
    args = parser.parse_args()
    if args.score:
        report = json.loads(args.score.read_text())
        result = score(report, strict=report.get("label") == "counted")
        print(one_line(result))
        return 0 if result["verdict"] in ("VERSIONS CORRECT", "clean") else 1
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
        static.update(static_target(PROJECT))   # P6's reading of the named reds, not exit 0 (SPEC-M3-K-0.2.44 append 1, H2)
    instance = Instance(args.ddev_root)
    log: list[dict[str, Any]] = []
    server = VServer(instance, log)
    report: dict[str, Any] = {
        "runner": "check_m3_versions.py", "runnerSha256": sha256_file(Path(__file__)), "label": args.label,
        "startedAt": utc_now(), "static": static,
        **binding_fields(binding),
        "baseUrl": instance.base,
        "original": {"source": str(FIXTURE.relative_to(DIST)), "sha256": sha256_file(FIXTURE)},
        "runs": [],
    }
    out = EVIDENCE / ("runs" if counted else "shakedown") / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        report["setup"] = server.setup()
        with tempfile.TemporaryDirectory(prefix="m3-versions-", dir=PROJECT / "build") as scratch:
            _, allowed, count = PLAN["versions"]
            for browser in args.browsers.split(","):
                if browser not in allowed:
                    continue
                for index in range(count if counted or args.repeats is None else args.repeats):
                    print(f"R1 versions {browser} #{index + 1}", flush=True)
                    report["runs"].append(run_versions(browser, server, Path(scratch)))
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
    return 0 if result["verdict"] in ("VERSIONS CORRECT", "clean") else 1


if __name__ == "__main__":
    sys.exit(main())
