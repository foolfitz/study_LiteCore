#!/usr/bin/env python3
"""M3 same-second saves: arm R2 of specs/SPEC-M3-versions.md §4.

fable's ruling D (findings/evidence/m3-same-second/ruling-2026-09-29-fable-d.md):
two saves from the host in one wall-clock second keep the ETag (finding 103), the
first is in no version once a third lands, and any restore after such a pair
loses the second (finding 104). Condition 1 measured that the page gets there
with two quick presses. Here, through the real page: ten pairs (button, then
Ctrl+S, no wait) pressed at phases .05, .15, ... .95 of a second, one more save,
then a pair at phase .05 and a restore of the fixture's version as Files'
Versions tab sends it. Judged on Nextcloud's own version list, save by save.

R3 (condition 6, finding 103 from someone else's side): a save at phase .05, a
write with the holder's token (finding 102) in the same second, then a second
save, which must not overwrite that write.

    python3 wasm_sdk_probe/tools/check_m3_same_second.py --label shakedown --browsers chrome --repeats 1
    python3 wasm_sdk_probe/tools/check_m3_same_second.py --label counted
    python3 wasm_sdk_probe/tools/check_m3_same_second.py --score findings/evidence/m3-same-second/runs/<file>.json
    python3 wasm_sdk_probe/tools/check_m3_same_second.py --red-cases findings/evidence/m3-same-second/shakedown/<file>.json

A separate runner, not an arm of check_m3_versions.py: that one is bound to
VERSIONS CORRECT and is re-run unchanged on 0.2.2 (ruling condition 7).
"""
from __future__ import annotations

import argparse
import copy
import email.utils
import hashlib
import http.client
import json
import re
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from k_static_target import static_target  # noqa: E402
from check_m3_host_entry import host_record, requests_matching  # noqa: E402
from check_m3_locks import (  # noqa: E402
    PAGE_SHA256, PROJECT, REPO, LockChrome, attempts, held_at_open, login, on_wire, one_copy, open_from_files, opened_ok,
    page_failed_with, save, wire)
from check_m3_skeleton_open import (  # noqa: E402
    DEFAULT_DDEV, FIXTURE, SAMPLE, Instance, binding_fields, host_binding, product_state)
from check_m3_versions import MTIME, NS, VServer, older  # noqa: E402
from probe_m3_gate0_coep import DIST, firefox_profile, sha256_file, summarize_cdp, utc_now  # noqa: E402
from probe_m3_same_second_saves import PAIR, SETTLED, drained  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import PRESS, navigate  # noqa: E402

EVIDENCE = REPO / "findings" / "evidence" / "m3-same-second"
SNAME = "M3 同秒 測試.odt"
PLAN = {"same-second": ("R2", ("chrome", "firefox"), 3), "same-second-foreign": ("R3", ("chrome", "firefox"), 3)}
# R3's press, as a phase of a wall-clock second: X has to land in S1's second.  On v21 S1 settled 0.30 s after the press and
# 0.05 fitted; on v28 press-to-bytes went from 0.22 s to 0.61 s, S1 settles at 0.67 s, X takes 0.32 s, so 0.05 + 0.67 + 0.32
# crosses into the next second (first contact 2026-10-31, 0/2, clause `premise`).  At 0.60 S1 lands near .25 of the next
# second and X near .60.  SPEC-M3-K-0.2.44 append 2.  On v29 (finding 177) S1 settles at +0.35 to +0.40 s and X is done by +0.85 s,
# so 0.60 crosses the second every time (0/6 on 0.2.45, clause `premise`) and 0.05 fits again, with about 0.10 s to spare.
# SPEC-M3-v29-tick-pacing append 7.
FOREIGN_PHASE = 0.05
# ruling D shipped as 0.2.2; SPEC-M3-page-honesty §7.6/§7.11 re-ran it on 0.2.4; SPEC-M3-zstd Z3
# re-runs it on 0.2.5 (written 2026-09-30 before that run).
HOST_VERSION = "0.2.45"   # host 0.2.45 (engine v29, shell generation 83), 2026-11-02; was 0.2.44; host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was 0.2.26; host 0.2.26 (engine v21, shell v74, finding 154's host rule), 2026-10-17; was 0.2.24 (finding 145, v73), 0.2.23 (SPEC-M3-link-batch §17), 0.2.14, 0.2.13, 0.2.12, 0.2.11, 0.2.10, 0.2.9, 0.2.8, 0.2.7
PAIRS = 10
SAVES = 2 * PAIRS + 1 + 2   # the ten pairs, the single save (S21), the restore pair (S22, S23)
BUTTON = PRESS.replace("ARG_ACTION", "save")


class SServer(VServer):
    def raw(self, step: str, method: str, path: str, body: bytes | None = None,
            headers: dict[str, str] | None = None) -> tuple[Any, bytes]:
        """A body shorter than its Content-Length is recorded, not fatal: after a
        restore that follows a same-second pair (0.2.1), that row's length is off
        by a byte (finding 104's evidence). Such a row matches no save."""
        try:
            return super().raw(step, method, path, body, headers)
        except http.client.IncompleteRead as error:
            self.admin.log.append({"step": step, "actor": self.admin.user, "method": method, "path": path,
                                   "status": "incomplete", "bytes": len(error.partial), "expected": error.expected})
            return "incomplete", error.partial

    def teardown(self) -> None:
        self.clear_locks()
        self.admin.call("teardown", "DELETE", self.admin.dav_path(SNAME))

    def mtime(self, step: str) -> int | None:
        status, data = self.raw(step, "PROPFIND", self.admin.dav_path(SNAME), MTIME,
                                {"Depth": "0", "Content-Type": "application/xml"})
        if status != 207:
            return None
        return int(email.utils.parsedate_to_datetime(ET.fromstring(data).findtext(".//d:getlastmodified", namespaces=NS)).timestamp())


def press(session, server: SServer, script: str, expect: int, label: str, phase: float | None) -> dict[str, Any]:
    """Press at `phase` of a wall-clock second (runner, browser and ddev share one
    kernel clock), then wait until the host has settled `expect` more saves and
    nothing new came for a second."""
    before = evaluate(session, SETTLED)[0]
    if phase is not None:
        wait = (phase - time.time() % 1) % 1
        time.sleep(wait if wait > 0.02 else wait + 1)
    pressed_at = time.time()
    pressed = evaluate(session, script)
    settled = drained(session, before + expect, quiet=1.0)
    return {"label": label, "phase": phase, "pressedAt": round(pressed_at, 3), "pressed": pressed,
            "savesBefore": before, "settled": settled, "state": product_state(session),
            "mtimeAfter": server.mtime(f"mtime after {label}")}


def fresh(arm: str, kind: str, server: SServer, scratch: Path) -> tuple[dict[str, Any], Any]:
    """A new file (new fileid, empty history), no copies, a new browser."""
    record: dict[str, Any] = {"arm": arm, "spec": PLAN[arm][0], "browser": kind, "startedAt": utc_now(),
                              "file": {"user": "admin", "path": SNAME, "adminPath": SNAME}}
    record["clearedLocks"] = server.clear_locks()
    record["removedOld"] = server.admin.call("reset", "DELETE", server.admin.dav_path(SNAME))["status"]
    record["reset"] = {"upload": server.upload(server.admin, SNAME), "fileId": server.fileid(server.admin, SNAME)}
    record["copiesBefore"] = server.copies(server.admin, "", SNAME[:-4], remove=True)
    if kind == "chrome":
        session = LockChrome("cold")
    else:
        session = FirefoxSession("cold", profile_dir=firefox_profile(scratch / f"ff-{time.monotonic_ns()}"))
    record["version"] = getattr(session, "version", None)
    return record, session


def finish(record: dict[str, Any], server: SServer, session) -> None:
    if isinstance(session, LockChrome):
        events = session.drain()
        record["cdp"] = summarize_cdp(events)
        record["fixtureRequests"] = requests_matching(events, "/e1-fixtures/")
        record["davRequests"] = wire(events)
    navigate(session, server.instance.base + "/apps/files/", timeout=120)


def run_same_second(kind: str, server: SServer, scratch: Path) -> dict[str, Any]:
    record, session = fresh("same-second", kind, server, scratch)
    try:
        record["login"] = login(session, server.instance.base, "admin", server.instance.password)
        open_from_files(session, server.instance.base, "", SNAME, record)
        record["afterOpen"] = server.props(server.admin, SNAME)
        presses = record["presses"] = []
        for k in range(PAIRS):
            presses.append(press(session, server, PAIR, 2, f"pair {k}", round(0.05 + 0.1 * k, 2)))
            time.sleep(1.5)
        presses.append(press(session, server, BUTTON, 1, "single", None))
        record["Lb"] = server.listing("Lb after the single save", SNAME)
        time.sleep(1.5)
        presses.append(press(session, server, PAIR, 2, "restore pair", 0.05))
        record["beforeRestore"] = server.props(server.admin, SNAME)
        F = sha256_file(FIXTURE)
        rows = [e for e in record["Lb"].get("entries") or [] if not e["current"]]
        revision = next((e["revision"] for e in rows if e.get("sha256") == F), rows[0]["revision"] if rows else None)
        record["restoredRevision"] = revision
        record["restore"], _ = server.raw(
            "restore (Files' request, no token)", "MOVE",
            f"/remote.php/dav/versions/admin/versions/{record['reset']['fileId']}/{revision}", None,
            {"Destination": f"{server.instance.base}/remote.php/dav/versions/admin/restore/target"})
        record["serverAfterRestore"] = server.content(server.admin, SNAME)
        record["Lc"] = server.listing("Lc after the restore", SNAME)
        record["host"] = host_record(session)
        record["copiesAfter"] = server.copies(server.admin, "", SNAME[:-4], remove=True)
        finish(record, server, session)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass
        record["clearedAtEnd"] = server.clear_locks()
    record["registered"] = registered(record)
    return record


def run_foreign(kind: str, server: SServer, scratch: Path) -> dict[str, Any]:
    record, session = fresh("same-second-foreign", kind, server, scratch)
    try:
        record["login"] = login(session, server.instance.base, "admin", server.instance.password)
        open_from_files(session, server.instance.base, "", SNAME, record)
        record["afterOpen"] = server.props(server.admin, SNAME)
        before = evaluate(session, SETTLED)[0]
        wait = (FOREIGN_PHASE - time.time() % 1) % 1
        time.sleep(wait if wait > 0.02 else wait + 1)
        record["pressedAt"] = round(time.time(), 3)
        evaluate(session, BUTTON)
        deadline, seen = time.monotonic() + 60, None
        while time.monotonic() < deadline:   # no sleep: X has to land inside S1's second
            seen = evaluate(session, SETTLED)
            if seen[0] >= before + 1 and seen[1]:
                break
        record["s1SeenSettledAt"] = round(time.time(), 3)
        record["foreignPut"] = server.put(server.admin, SNAME, server.intruder,
                                          {"If": f"(<{record['afterOpen'].get('token')}>)"})
        record["foreignDoneAt"] = round(time.time(), 3)
        record["afterForeign"] = server.props(server.admin, SNAME)
        record["foreignMtime"] = server.mtime("mtime after X")
        time.sleep(1.5)
        save(session, record, 2)
        record["host"] = host_record(session)
        record["serverAfter"] = server.content(server.admin, SNAME)
        record["lockAfterSave"] = server.props(server.admin, SNAME)
        record["copiesAfter"] = server.copies(server.admin, "", SNAME[:-4], remove=True)
        finish(record, server, session)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass
        record["clearedAtEnd"] = server.clear_locks()
    host = record.get("host") or {}
    record["registered"] = [{"s1": s.get("attempts"), "sha256": s.get("sha256")} for s in host.get("saves") or []]
    return record


def registered(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Recorded, not judged (ruling conditions 3, 4): per press, where in the second
    each PUT went out, the gap, how long the host held the second one back (0.2.2
    records it), and what the page's own line said once it was done."""
    host = run.get("host") or {}
    saves, started = host.get("saves") or [], host.get("started") or 0
    rows = []
    for p in run.get("presses") or []:
        count = (p.get("settled") or [0])[0]
        mine = saves[p["savesBefore"]:count if isinstance(count, int) else p["savesBefore"]]
        puts = [a for s in mine for a in s.get("attempts") or []]
        rows.append({"label": p["label"], "phase": p["phase"],
                     "putPhases": [round((started + a["at"]) / 1000 % 1, 3) for a in puts if isinstance(a.get("at"), int)],
                     "sendGapMs": [b["at"] - a["at"] for a, b in zip(puts, puts[1:])],
                     "waitedMs": [a.get("waited") for a in puts],
                     "answeredAfterMs": [a["respondedAt"] - a["at"] if isinstance(a.get("respondedAt"), int) else None for a in puts],
                     "checkMs": [(a.get("check") or {}).get("ms") for a in puts],
                     "page": (p.get("state") or {}).get("latency"), "mtimeAfter": p.get("mtimeAfter")})
    return rows


# --------------------------------------------------------------------------
# Scoring -- raw fields only. One line per failing instance, prefixed with its
# clause, so a mutation counts as caught only by a line of its own clause.


def score_foreign(run: dict[str, Any], report: dict[str, Any]) -> list[str]:
    F, X = report["original"]["sha256"], report["intruder"]["sha256"]
    saves = (run.get("host") or {}).get("saves") or []
    name = {s.get("sha256"): f"S{i + 1}" for i, s in enumerate(saves)} | {F: "F", X: "X"}
    bad = [f"open: {p}" for p in opened_ok(run, report) + held_at_open(run)]
    if len(saves) != 2 or attempts(saves[0]) != [(204, True)] or len({F, X, *(s.get("sha256") for s in saves)}) != 4:
        return bad + [f"shape: saves {[attempts(s) for s in saves]}, want two, the first one 204 with the token, "
                      "and F, X, S1, S2 all different"]
    s1, s2 = saves
    etag_after_x = (run.get("afterForeign") or {}).get("etag")
    if run.get("foreignPut") != 204 or not s1.get("etag") or etag_after_x != s1["etag"]:
        bad.append(f"premise: X {run.get('foreignPut')}, the ETag after X {etag_after_x} vs S1's {s1.get('etag')}"
                   " -- X did not land in S1's second, so this run measured nothing about 103")
    kept = (run.get("serverAfter") or {}).get("sha256")
    if kept != X:
        bad.append(f"kept: the file holds {name.get(kept, (kept or '?')[:12])} after the second save, not X")
    bad += [f"copy: {p}" for p in one_copy(run, "衝突副本", s2.get("sha256"))]
    copy_name = (s2.get("conflictCopy") or {}).get("name") or "?"
    bad += [f"page: {p}" for p in page_failed_with(run.get("save2State") or {}, "CONFLICT", copy_name)]
    opened, after = run.get("afterOpen") or {}, run.get("lockAfterSave") or {}
    if ((run.get("host") or {}).get("lock") or {}).get("state") != "held" or not opened.get("token") \
            or after.get("token") != opened.get("token"):
        bad.append(f"lock: host {((run.get('host') or {}).get('lock') or {}).get('state')}, "
                   f"server token {opened.get('token')} -> {after.get('token')}")
    # The read-back is what stopped S2 (review item 4): no PUT for it, in the host's record and on the wire.
    if attempts(s2) != [("changed", True)]:
        bad.append(f"blocked: S2 {attempts(s2)}, want one attempt 'changed' with the token (no PUT)")
    if run["browser"] == "chrome":
        quoted = urllib.parse.quote(SNAME)
        puts = [r for r in run.get("davRequests") or [] if r["method"] == "PUT" and r["url"].endswith(quoted)]
        first = (s1.get("attempts") or [{}])[0]
        if len(puts) != 1 or puts[0].get("ifMatch") != first.get("ifMatch") \
                or puts[0].get("if") != f"(<{opened.get('token')}>)":
            bad.append(f"wire: {len(puts)} PUTs to the file {[(x.get('ifMatch'), x.get('if')) for x in puts]}, "
                       f"want only S1's, If-Match {first.get('ifMatch')}, the server's token")
    return bad


def score_run(run: dict[str, Any], report: dict[str, Any]) -> list[str]:
    if run.get("fatal"):
        return [f"fatal: {run['fatal'].strip().splitlines()[-1]}"]
    if run["arm"] == "same-second-foreign":
        return score_foreign(run, report)
    F = report["original"]["sha256"]
    saves = (run.get("host") or {}).get("saves") or []
    sent = [s.get("sha256") for s in saves]
    name = {h: f"S{i + 1}" for i, h in enumerate(sent)} | {F: "F"}
    bad = [f"open: {p}" for p in opened_ok(run, report) + held_at_open(run)]
    if len(saves) != SAVES:
        bad.append(f"shape: {len(saves)} saves, want {SAVES}")
    for i, s in enumerate(saves):
        if attempts(s) != [(204, True)]:
            bad.append(f"shape: S{i + 1} {attempts(s)}, want one 204 with the token")
    # (a) no two saves in a row with the same ETag
    for i in range(1, len(saves)):
        a, b = saves[i - 1], saves[i]
        if isinstance(a.get("status"), int) and isinstance(b.get("status"), int) and a["status"] < 300 \
                and b["status"] < 300 and b.get("etag") and b.get("etag") == a.get("etag"):
            bad.append(f"(a) S{i + 1} has S{i}'s ETag {b['etag']}")
    if len(set(sent + [F])) != len(sent) + 1 or None in sent:
        bad.append("distinct: F and the saves' bytes are not all different")
    if len(saves) != SAVES:
        return bad   # (b) and (c) name S1..S23
    # (b) after the single save: [F, S1..S20] in revision order, one current row
    lb = run.get("Lb") or {}
    got, want = older(lb), [F] + sent[:20]
    bad += [f"(b) Lb lacks {name[h]}" for h in want if h not in got]
    bad += [f"(b) Lb has a row that is {name.get(h, (h or '?')[:12])}, not one of F, S1..S20" for h in got if h not in want]
    if [h for h in got if h in want] != [h for h in want if h in got]:
        bad.append("(b) Lb rows are not in save order")
    if len([e for e in lb.get("entries") or [] if e["current"]]) != 1:
        bad.append("(b) Lb does not have exactly one current row")
    # (c) the restore of F writes F, and keeps everything: [S1..S23], S23 being finding 104's cell
    if run.get("restore") != 201 or (run.get("serverAfterRestore") or {}).get("sha256") != F:
        bad.append(f"(c) restore {run.get('restore')}, server after it {name.get((run.get('serverAfterRestore') or {}).get('sha256'), '?')}")
    lc = run.get("Lc") or {}
    got, want = older(lc), sent[:23]
    if sent[22] not in got:
        bad.append("(c) 104: Lc lacks S23, the later save of the restore pair")
    bad += [f"(c) Lc lacks {name[h]}" for h in want[:22] if h not in got]
    bad += [f"(c) Lc has a row that is {name.get(h, (h or '?')[:12])}, not one of S1..S23" for h in got if h not in want]
    if [h for h in got if h in want] != [h for h in want if h in got]:
        bad.append("(c) Lc rows are not in save order")
    if len([e for e in lc.get("entries") or [] if e["current"]]) != 1:
        bad.append("(c) Lc does not have exactly one current row")
    if run.get("copiesAfter"):
        bad.append(f"copies: {[c.get('name') for c in run['copiesAfter']]}")
    bad += [f"wire: {p}" for p in on_wire(run, [(204, True)] * SAVES)]
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
    if strict and report.get("hostVersion") != HOST_VERSION:
        problems.append(f"host is version {report.get('hostVersion')!r}, the ruling's fix is {HOST_VERSION}")
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
    verdict = ("SAME-SECOND SAVES KEPT" if ok else "SAME-SECOND SAVES NOT KEPT") if strict else ("clean" if ok else "red")
    return {"verdict": verdict, "tally": tally, "problems": problems}


def clauses(problems: list[str]) -> list[str]:
    """Which clauses a run is red in; finding 104's own cell is named apart from the rest of (c)."""
    return sorted({"(c) 104" if p.startswith("(c) 104") else p[:3] if p.startswith("(") else p.split(":", 1)[0]
                   for p in problems})


def admission(report: dict[str, Any]) -> dict[str, Any]:
    """R3's entry condition, measured once (spec §4 R3): per browser, over R2's saves,
    the median read-back GET is no slower than the median PUT (host's own record)."""
    out = {}
    for browser in PLAN["same-second"][1]:
        gets, puts = [], []
        for run in report.get("runs") or []:
            if run["browser"] == browser and run["arm"] == "same-second" and not run.get("fatal"):
                for row in run.get("registered") or []:
                    gets += [m for m in row.get("checkMs") or [] if isinstance(m, int)]
                    puts += [m for m in row.get("answeredAfterMs") or [] if isinstance(m, int)]
        if gets and puts:
            g, q = statistics.median(gets), statistics.median(puts)
            out[browser] = {"getMedianMs": g, "putMedianMs": q, "gets": len(gets), "puts": len(puts), "holds": g <= q}
    return out


def one_line(result: dict[str, Any]) -> str:
    cells = " ".join(f"{k}={v['pass']}/{v['runs']}" for k, v in sorted(result["tally"].items()))
    red = [clauses(bad) for e in result["tally"].values() for bad in e["problems"]]
    return f"{result['verdict']} {cells} problems={result['problems']} red-clauses-per-run={red}"


def _row(listing: dict, sha: str) -> dict:
    return next(e for e in listing["entries"] if e.get("sha256") == sha)


def _same_etag(run: dict) -> None:
    """The first save whose ETag differs from the one before takes that one's."""
    saves = run["host"]["saves"]
    i = next(i for i in range(1, len(saves)) if saves[i]["etag"] != saves[i - 1]["etag"])
    saves[i]["etag"] = saves[i - 1]["etag"]


def _drop_last_known(key: str):
    """Drop the newest row that holds a save's (or F's) bytes -- on 0.2.1 the newest row
    can be one that matches nothing, and dropping that would add no line."""
    def mutate(run: dict) -> None:
        known = {s["sha256"] for s in run["host"]["saves"]} | {_F[0]}
        rows = [e for e in run[key]["entries"] if not e["current"] and e.get("sha256") in known]
        run[key]["entries"].remove(rows[-1])
    return mutate


_F: list[str] = []   # the report's F, set by red_cases before any mutation runs


def _swap_known(key: str):
    """Swap the bytes of the two newest rows that hold saves: same rows, wrong order."""
    def mutate(run: dict) -> None:
        known = {s["sha256"] for s in run["host"]["saves"]}
        rows = [e for e in run[key]["entries"] if not e["current"] and e.get("sha256") in known]
        rows[-1]["sha256"], rows[-2]["sha256"] = rows[-2]["sha256"], rows[-1]["sha256"]
    return mutate


def _drop_save(key: str, n: int):
    def mutate(run: dict) -> None:
        sha = run["host"]["saves"][n]["sha256"]
        run[key]["entries"] = [e for e in run[key]["entries"] if e.get("sha256") != sha]
    return mutate


def _file_puts(run: dict) -> list[dict]:
    quoted = urllib.parse.quote(SNAME)
    return [x for x in run["davRequests"] if x["method"] == "PUT" and x["url"].endswith(quoted)]


def _wire_put(change):
    return lambda r: change(_file_puts(r)[3])


def _wire_drop_put(run: dict) -> None:
    run["davRequests"].remove(_file_puts(run)[3])


def _wire_dup_put(run: dict) -> None:
    run["davRequests"].append(dict(_file_puts(run)[0]))


def _wire_get_first(run: dict) -> None:
    rows = run["davRequests"]
    lock = next(i for i, x in enumerate(rows) if x["method"] == "LOCK")
    rows.append(rows.pop(lock))


C = ("chrome",)
# (label, clause prefix that must catch it, mutation, browsers -- None = both). Each case
# counts only if the mutated run has a NEW problem line under its own clause, so the same
# cases run on the red 0.2.1 shakedown (before the fix) and on a clean one (spec R2).
RED_CASES = [
    ("open: other bytes were opened", "open", lambda r: r["host"]["fetched"].update(sha256="0" * 64), None),
    ("open: lock taken after the read", "open", lambda r: r["host"]["lock"].update(at=r["host"]["fetched"]["at"] + 1), None),
    ("shape: a save went to a conflict copy", "shape",
     lambda r: r["host"]["saves"][5].update(status=412, attempts=[{"status": 412, "withToken": True}]), None),
    ("shape: a save retried without the token", "shape",
     lambda r: r["host"]["saves"][7]["attempts"].append({"status": 204, "withToken": False}), None),
    ("shape: a save is missing", "shape", lambda r: r["host"]["saves"].pop(), None),
    ("(a) two saves in a row share an ETag", "(a)", _same_etag, None),
    ("distinct: two saves sent the same bytes", "distinct",
     lambda r: r["host"]["saves"][3].update(sha256=r["host"]["saves"][2]["sha256"]), None),
    ("(b) Lb lost a save", "(b)", _drop_last_known("Lb"), None),
    ("(b) Lb holds bytes nobody saved", "(b)",
     lambda r: r["Lb"]["entries"].append({"revision": 9_999_999_999, "current": False, "sha256": "e" * 64}), None),
    ("(b) Lb has two current rows", "(b)",
     lambda r: r["Lb"]["entries"].append({**next(e for e in r["Lb"]["entries"] if e["current"]), "revision": 9_999_999_998}), None),
    ("(c) restore refused", "(c)", lambda r: r.update(restore=423), None),
    ("(c) restore wrote something else", "(c)", lambda r: r["serverAfterRestore"].update(sha256=r["host"]["saves"][22]["sha256"]), None),
    ("(c) Lc lost the newest save it held", "(c)", _drop_last_known("Lc"), None),
    ("(c) Lc rows out of order", "(c)", lambda r: r["Lc"].update(entries=list(reversed(r["Lc"]["entries"]))), None),
    ("copies: a conflict copy was left", "copies", lambda r: r.update(copiesAfter=[{"name": "x（衝突副本）.odt"}]), None),
    ("wire: a PUT without If", "wire", lambda r: [x.update({"if": None}) for x in r["davRequests"] if x["method"] == "PUT"], C),
    # review item 3: one case for every sub-clause that had none
    ("(b) Lb rows out of save order", "(b)", _swap_known("Lb"), None),
    ("(c) Lc lost S1 (not only S23)", "(c)", _drop_save("Lc", 0), None),
    ("(c) Lc holds bytes nobody saved", "(c)",
     lambda r: r["Lc"]["entries"].append({"revision": 9_999_999_999, "current": False, "sha256": "e" * 64}), None),
    ("(c) Lc has two current rows", "(c)",
     lambda r: r["Lc"]["entries"].append({**next(e for e in r["Lc"]["entries"] if e["current"]), "revision": 9_999_999_998}), None),
    ("wire: a PUT's If-Match is not the recorded one", "wire", _wire_put(lambda x: x.update(ifMatch='"other"')), C),
    ("wire: one PUT fewer on the wire than recorded", "wire", _wire_drop_put, C),
    ("wire: the GET went out before the LOCK", "wire", _wire_get_first, C),
]
RED_CASES_R3 = [
    ("open: other bytes were opened", "open", lambda r: r["host"]["fetched"].update(sha256="0" * 64), None),
    ("shape: S1 was retried without the token", "shape",
     lambda r: r["host"]["saves"][0]["attempts"].append({"status": 204, "withToken": False}), None),
    ("premise: X was refused", "premise", lambda r: r.update(foreignPut=423), None),
    ("premise: X landed in another second (the ETag moved)", "premise", lambda r: r["afterForeign"].update(etag='"moved"'), None),
    ("kept: the file holds something else", "kept", lambda r: r["serverAfter"].update(sha256=_F[0]), None),
    ("copy: two copies", "copy", lambda r: r.update(copiesAfter=[{"name": "a（衝突副本）.odt", "sha256": "1"},
                                                                 {"name": "b（衝突副本）.odt", "sha256": "2"}]), None),
    ("page: the page blames the network", "page",
     lambda r: r["save2State"].update(latency="存回 失敗", toast="存回：連不上伺服器。"), None),
    ("lock: the lock was lost", "lock", lambda r: r["lockAfterSave"].update(token=None), None),
    ("lock: the host says it no longer holds the lock", "lock", lambda r: r["host"]["lock"].update(state="lost"), None),
    ("shape: S2 sent S1's bytes", "shape", lambda r: r["host"]["saves"][1].update(sha256=r["host"]["saves"][0]["sha256"]), None),
    ("blocked: S2 was refused by If-Match instead", "blocked",
     lambda r: r["host"]["saves"][1].update(attempts=[{"status": 412, "withToken": True}]), None),
    ("blocked: S2 was read back, then PUT anyway", "blocked",
     lambda r: r["host"]["saves"][1]["attempts"].append({"status": 204, "withToken": True}), None),
    ("wire: a second PUT to the file", "wire", _wire_dup_put, C),
    ("wire: S1's PUT went out without the token", "wire", lambda r: _file_puts(r)[0].update({"if": None}), C),
]


def red_cases(path: Path) -> int:
    report = json.loads(path.read_text())
    _F[:] = [report["original"]["sha256"]]
    failures = 0
    cases = [(case, "same-second") for case in RED_CASES] + [(case, "same-second-foreign") for case in RED_CASES_R3]
    for (label, clause, mutate, only), arm in cases:
        for browser in (only or PLAN[arm][1]):
            # A clean base when there is one (review item 11): on an already-red base a case can
            # "add a line" by changing a message's text without its clause newly firing.
            mine = [r for r in report["runs"] if r["browser"] == browser and r["arm"] == arm and not r.get("fatal")]
            base = next((r for r in mine if not score_run(r, report)), mine[0] if mine else None)
            if base is None:
                print(f"  MISSING {label} [{browser}]: no run to mutate")
                failures += 1
                continue
            before = set(score_run(base, report))
            mutated = copy.deepcopy(base)
            mutate(mutated)
            new = [p for p in score_run(mutated, report) if p not in before]
            red = any(p.startswith(clause) for p in new)
            failures += not red
            print(f"  {'red ' if red else 'GREEN'}  {PLAN[arm][0]} {label} [{browser}]" + ("" if red else f"  new lines: {new}"))
    # Strict problems, compared with the report's own: a shakedown is not bound, so it has some already.
    for label, change in (
            ("static: the served page is not the spec's", lambda r: r["static"]["page"].update(dist="0" * 64)),
            ("static: the host is not 0.2.2",
             lambda r: r.update(hostVersion="0.2.1" if r.get("hostVersion") == HOST_VERSION else None))):
        mutated = copy.deepcopy(report)
        change(mutated)
        added = [p for p in score(mutated, strict=True)["problems"] if p not in score(report, strict=True)["problems"]]
        failures += not added
        print(f"  {'red ' if added else 'GREEN'}  {label}")
    return failures


def read_version(app_dir: str) -> str | None:
    info = Path(app_dir) / "appinfo" / "info.xml"
    found = re.search(r"<version>([^<]+)</version>", info.read_text()) if info.exists() else None
    return found.group(1) if found else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--label", choices=("shakedown", "counted"))
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--arms", default=",".join(PLAN), help="shakedown only")
    parser.add_argument("--repeats", type=int, default=None, help="shakedown only")
    parser.add_argument("--score", type=Path)
    parser.add_argument("--red-cases", type=Path)
    args = parser.parse_args()
    if args.score:
        report = json.loads(args.score.read_text())
        result = score(report, strict=report.get("label") == "counted")
        print(one_line(result))
        print(f"R3 entry condition (median GET <= median PUT): {admission(report) or 'no data (a 0.2.1 host records neither)'}")
        return 0 if result["verdict"] in ("SAME-SECOND SAVES KEPT", "clean") else 1
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
    if counted and binding["hostDirty"]:
        print(f"refusing a counted run: the host repo has uncommitted changes:\n{binding['hostDirty']}")
        return 2
    version = read_version(binding["appDir"])
    if counted and version != HOST_VERSION:
        print(f"refusing a counted run: the host is {version!r}, the ruling's fix is {HOST_VERSION}")
        return 2
    if counted:
        static.update(static_target(PROJECT))   # P6's reading of the named reds, not exit 0 (SPEC-M3-K-0.2.44 append 1, H2)
    instance = Instance(args.ddev_root)
    log: list[dict[str, Any]] = []
    server = SServer(instance, log)
    report: dict[str, Any] = {
        "runner": "check_m3_same_second.py", "runnerSha256": sha256_file(Path(__file__)), "label": args.label,
        "startedAt": utc_now(), "static": static, **binding_fields(binding), "hostVersion": version,
        "baseUrl": instance.base,
        "original": {"source": str(FIXTURE.relative_to(DIST)), "sha256": sha256_file(FIXTURE)},
        "intruder": {"source": str(SAMPLE.relative_to(DIST)), "sha256": hashlib.sha256(server.intruder).hexdigest()},
        "runs": [],
    }
    out = EVIDENCE / ("runs" if counted else "shakedown") / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        report["setup"] = server.setup()
        with tempfile.TemporaryDirectory(prefix="m3-same-second-", dir=PROJECT / "build") as scratch:
            arms = list(PLAN) if counted else args.arms.split(",")
            for browser in args.browsers.split(","):
                for arm in arms:
                    spec, allowed, count = PLAN[arm]
                    if browser not in allowed:
                        continue
                    for index in range(count if counted or args.repeats is None else args.repeats):
                        print(f"{spec} {arm} {browser} #{index + 1}", flush=True)
                        runner = run_same_second if arm == "same-second" else run_foreign
                        run = runner(browser, server, Path(scratch))
                        report["runs"].append(run)
                        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
                        print(f"  red clauses: {clauses(score_run(run, report))}", flush=True)
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
    return 0 if result["verdict"] in ("SAME-SECOND SAVES KEPT", "clean") else 1


if __name__ == "__main__":
    sys.exit(main())
