#!/usr/bin/env python3
"""M3 autosave: the counted arms of specs/SPEC-M3-autosave.md §9.4 (AS-1 .. AS-7, O2-1).

Host 0.2.13 and the page that goes with it save by themselves (30 s idle, 3 s
after 5 minutes of edits, at once when the tab goes hidden) and, after a save
has gone to a conflict copy, keep saving to that copy.  Each arm drives the real
Files -> editor route in a fresh browser and reads the outcome from the server
and from the host's own record (`data-litecore`), never from the page's words.

Arm -> criterion (the spec's text is the authority, this table only indexes it):

    as2-key      AS-2 (a key), O2-1 (a) (c)       both x 3   ~45 s
    as2-toolbar  AS-2 (a toolbar action only)     both x 3   ~45 s
    as2h         AS-2h (tab goes hidden)          both x 3   ~15 s
    as2c         AS-2c (5-minute cap)             both x 1   ~6.5 min
    as3          AS-3 (opened while locked)       both x 3   ~2 min
    as4a         AS-4 (a) (conflict, autosave)    both x 3   ~2 min
    as4b         AS-4 (b), O2-1 (b) (d)           both x 3   ~30 s
    as4c         AS-4 (c) (lock stays valid)      both x 3   ~30 s
    as5          AS-5 (typing during an autosave) both x 3   ~1.5 min  (the owner's document)
    as5-held     AS-5 (one key held 1.5 s)        both x 3   ~1.5 min  (the owner's document)
    as6b         AS-6 (b) (leave after an auto copy)  both x 3  ~1 min
    as7          AS-7, O2-1 (e) (offline, Chrome) chrome x 3 ~2.5 min

AS-1 is not an arm: it is a rule on every `trigger: "auto"` record in the report.
AS-6 (a), 128-B, 129-B, 130-U and the old runners' re-count are other runners.

    python3 wasm_sdk_probe/tools/check_m3_autosave.py --label shakedown --arms as2-key --browsers chrome --repeats 1
    python3 wasm_sdk_probe/tools/check_m3_autosave.py --label counted
    python3 wasm_sdk_probe/tools/check_m3_autosave.py --score findings/evidence/m3-autosave/runs/<file>.json
    python3 wasm_sdk_probe/tools/check_m3_autosave.py --red-cases findings/evidence/m3-autosave/shakedown/<file>.json
    python3 wasm_sdk_probe/tools/check_m3_autosave.py --selftest      # offline: synthetic report, no browser, no server

One clock: the page records `Date.now()` for keydowns, revision changes,
visibilitychange and toasts, and the host's records are `started + relative ms`
of the same page, `started` and every relative ms taken with the same
`Date.now()`, so they compare.  (Was `performance.timeOrigin + performance.now()`
until the dual review: codex item 3 -- two clocks, and `PILL_NOW` / `SNAP` were
already `Date.now()`.)
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import re
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_m3_page_honesty as ph  # noqa: E402
import check_m3_production_ui as ui  # noqa: E402
from k_static_target import static_target  # noqa: E402
from check_m3_host_entry import MARKER, server_file  # noqa: E402
from check_m3_locks import (  # noqa: E402
    STRANDED, Server, attempts, edit, edited, idle, login, open_from_files, save, wire)
from check_m3_skeleton_open import (  # noqa: E402
    DEFAULT_DDEV, FIXTURE, NAME, SAMPLE, Instance, binding_fields, product_state, state_until)
from odt_paragraphs import paragraph_texts_from_xml  # noqa: E402
from probe_autosave_m1 import hold, type_letters  # noqa: E402
from probe_autosave_m3 import copy_facts  # noqa: E402
from probe_m3_gate0_coep import DIST, sha256_file, utc_now  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import PRESS  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-autosave"
BOTH = ("chrome", "firefox")
PASS, FAIL, NE = "PASS", "FAIL", "NOT_ESTABLISHED"

# Bindings for a counted run, written down by the main session after 0.2.13 is
# packaged and BEFORE the first counted run (spec §9.4).  None = not bound yet: a
# counted run refuses to start, and a counted report cannot score HOLDS.
# Re-pointed 2026-10-15 (task 10-15c P4, before binding v20) to host 0.2.23's page (shell v72, engine v20).  The previous pin was
# d761f1cee9d26c50c0b152348d74c3d05f540e9228927815d93ad6ec161e7dcd (autosave §9.19, 0.2.13/v62; the 0.2.13 and 0.2.14 counts ran on it).
PAGE_SHA256: str | None = "3b0a2ebb92c3db282f9c832ab194249f963592698cf5c73d771998dc10203a6a"   # host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was 605cf24b3dff5a2d; web/e2-editor-app.js, dist copy and the copy the host serves; was 901dd6a6 (0.2.24), ccb67a52 (0.2.23), d761f1ce
SESSION_SHA256: str | None = "d037eaa4c0b69bd3cc2e52099d461e0a54f3594a6b342c34ab0faca06955aac0"   # host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was f1509ff22e6e2d8d; editor-shell-v2/narrow-editor-v2-session.js, same three places; shell v74 (0.2.26); was f47c80ec (link-batch §17) (0.2.23); was 62a2a20e
HOST_VERSION: str | None = "0.2.44"   # host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was 0.2.26; appinfo/info.xml <version>; engine v21 + finding 154; was 0.2.24 (finding 145), 0.2.23 (link-batch §17), 0.2.14
HOST_COMMIT: str | None = "a97724f"   # host 0.2.44 (engine v28, shell generation 82), 2026-10-31; was 3c01876; the host repo's HEAD, a prefix is enough; 0.2.26; was 1479e56 (finding 145), 2ccf1a9 (link-batch §17), 237f2cb

# arm -> (criterion, browsers, counted runs per browser)
PLAN = {
    "as2-key": ("AS-2, O2-1 (a) (c)", BOTH, 3),
    "as2-toolbar": ("AS-2 toolbar", BOTH, 3),
    "as2h": ("AS-2h", BOTH, 3),
    "as2c": ("AS-2c", BOTH, 1),
    "as3": ("AS-3", BOTH, 3),
    "as4a": ("AS-4 (a)", BOTH, 3),
    "as4b": ("AS-4 (b), O2-1 (b) (d)", BOTH, 3),
    "as4c": ("AS-4 (c)", BOTH, 3),
    "as5": ("AS-5", BOTH, 3),
    "as5-held": ("AS-5 held key", BOTH, 3),
    "as6b": ("AS-6 (b)", BOTH, 3),
    "as7": ("AS-7, O2-1 (e)", ("chrome",), 3),
}
OWNER_DOC_ARMS = ("as5", "as5-held")   # the long first save is the point: the owner's document
KEY = "z"                              # in neither fixture, so "the server holds it" means something
AT_TEXT = ("0.35", "0.28")             # the point edit() clicks
LETTERS = "abcdefghijklmnoprstu"       # AS-5: twenty, 125 ms apart
HELD, HELD_REPEATS, HELD_GAP = "k", 45, 0.033   # AS-5 held: 1.5 s at ~33 ms
IDLE_S = 40.0                          # AS-3 / AS-4 (a): "idle 40 s"
KEYING_KEYS, KEYING_GAP = 155, 2.0     # AS-2c: a key every 2 s for 310 s
BUSY_AFTER_S = 29.0                    # AS-5: the pill goes busy for the auto no sooner than this

# ------------------------------------------------------------------ page-side instruments

RECORDER = """(() => {
  const at = () => Date.now();
  const log = window.__as = { keys: [], revisions: [], visibility: [], toasts: [] };
  const sink = document.querySelector('#sink'), rev = document.querySelector('#s-revision'),
        toast = document.querySelector('#toast');
  sink.addEventListener('keydown', (e) => log.keys.push({ t: at(), key: e.key, repeat: e.repeat }), true);
  document.addEventListener('visibilitychange', () => log.visibility.push({ t: at(), state: document.visibilityState }));
  new MutationObserver(() => log.revisions.push({ t: at(), revision: rev.textContent }))
    .observe(rev, { childList: true, characterData: true, subtree: true });
  new MutationObserver(() => { if (toast.classList.contains('show')) log.toasts.push({ t: at(), text: toast.textContent }); })
    .observe(toast, { childList: true, characterData: true, subtree: true, attributes: true });
  return true; })()"""
PAGE_LOG = "(() => window.__as)()"
SNAP = """(() => { const q = (s) => document.querySelector(s);
  const raw = document.documentElement.getAttribute('data-litecore');
  const label = q('#litecore-host-saved'), title = q('#litecore-host-title'), notice = q('#litecore-host-notice'),
        bar = q('#litecore-host-bar'), download = q('#litecore-host-download');
  return { now: Date.now(), host: raw ? JSON.parse(raw) : null,
    label: label ? { hidden: label.hidden, text: label.textContent } : null,
    title: title ? title.textContent : null, notice: notice ? notice.textContent : null,
    barHidden: bar ? bar.hidden : null, downloadHidden: download ? download.hidden : null,
    doc: q('#s-doc').textContent, toasts: window.__as ? window.__as.toasts.length : null }; })()"""
AUTOS = """(() => { const raw = document.documentElement.getAttribute('data-litecore');
  if (!raw) return null; const autos = (JSON.parse(raw).saves || []).filter((s) => s.trigger === 'auto');
  return { n: autos.length, settled: autos.filter((s) => s.settled === true).length }; })()"""
PILL_NOW = "(() => ({ state: document.querySelector('#state-pill').dataset.state, now: Date.now() }))()"
# The three HH:MM the label may show for a moment: a minute either side counts (spec O2-1 (b)).
# Asked of the browser itself: its time zone is the label's, not this script's.
HM = """(() => { const pad = (n) => String(n).padStart(2, '0');
  return [-60000, 0, 60000].map((d) => { const w = new Date(ARG_MS + d); return pad(w.getHours()) + ':' + pad(w.getMinutes()); }); })()"""
FILES_GO = "(() => { location.href = ARG_URL; return true; })()"

# ------------------------------------------------------------------ driving


def wait_autos(session, count: int, limit: float) -> dict[str, Any]:
    """Until `count` auto records have settled (polling also keeps a CDP socket awake)."""
    deadline, seen = time.monotonic() + limit, None
    while time.monotonic() < deadline:
        seen = evaluate(session, AUTOS)
        if seen and seen.get("settled", 0) >= count:
            return seen
        time.sleep(1.0)
    return {**(seen or {}), "timedOut": True}


def snap(session) -> dict[str, Any]:
    """The host record and everything the page shows about it right now, plus the
    HH:MM the O2 label may show for the host's latest record."""
    out = evaluate(session, SNAP)
    host, saves = out.get("host") or {}, (out.get("host") or {}).get("saves") or []
    out["allowed"] = None
    if saves and isinstance(host.get("started"), int):
        last = saves[-1]
        done = last.get("conflictCopy") if last.get("outcome") == "copy" else (last.get("attempts") or [None])[-1]
        at = (done or {}).get("respondedAt")
        if isinstance(at, int):
            out["allowed"] = evaluate(session, HM.replace("ARG_MS", str(host["started"] + at)))
    return out


def copy_list(server: Server) -> list[dict[str, Any]]:
    stem = NAME[:-4]
    return [copy_facts(server, c["name"]) for c in server.copies(server.admin, "", stem, remove=False)]


def file_facts(server: Server) -> dict[str, Any]:
    got = server_file(server.instance, NAME)
    return {"sha256": got["sha256"], "heading": got["heading"], "texts": got["texts"]}


INSERT_FAILED = "插入文字 失敗"   # the page's run("插入文字") on failure (web/e2-editor-app.js run())


def insert(session, record: dict[str, Any], key: str, text: str) -> None:
    """One edit through the insert field and the toolbar (as check_m3_locks.insert_marker, any text).
    Only the insert's own failure ends the wait: a save before it leaves 「存回 失敗」 /
    「自動存回 失敗」 in the same line when it wrote a copy or stranded (shakedown
    2026-10-12T054150, as4a)."""
    ahead = product_state(session)
    evaluate(session, f"(() => {{ document.querySelector('#text').value = {json.dumps(text)}; return true; }})()")
    evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
    record[key] = state_until(session, lambda s: s.get("revision") != ahead.get("revision")
                              or s.get("latency") == INSERT_FAILED, 60)


def phase(session, server: Server, record: dict[str, Any], key: str, autos: int, since: float) -> None:
    """The edit is done at `since`: wait for the `autos`-th auto record to settle, idle
    on to IDLE_S after the edit (an extra auto would show), then take the facts."""
    waited = wait_autos(session, autos, 50)
    idle(session, max(0.0, IDLE_S - (time.monotonic() - since)))
    record.setdefault("phases", {})[key] = {"wait": waited, "snap": snap(session), "copies": copy_list(server)}


def break_lock(server: Server, record: dict[str, Any]) -> None:
    """K6: the owner removes our lock and someone writes the file -- our token is dead and our ETag stale."""
    record["ownerUnlock"] = server.admin.call("owner unlock", "DELETE",
                                              f"/ocs/v2.php/apps/files_lock/lock/{record['reset']['fileId']}",
                                              form={"lockType": 0})["status"]
    record["intruded"] = server.put(server.admin, NAME, server.intruder)
    record["afterIntrusion"] = server.content(server.admin, NAME)


def go_hidden(session, kind: str, record: dict[str, Any]) -> None:
    """A second tab in front.  Whether the page then saw `hidden` is the page's log, not this call's."""
    try:
        if kind == "chrome":
            made = session.call("Target.createTarget", {"url": "about:blank"})
            session.call("Target.activateTarget", {"targetId": made["targetId"]})
        else:
            record["editorHandle"] = session.command("GET", "/window")
            made = session.command("POST", "/window/new", {"type": "tab"})
            session.command("POST", "/window", {"handle": made["handle"]})
    except Exception as error:  # noqa: BLE001 -- the page's log decides; this is the reason it may be empty
        record["hideError"] = f"{type(error).__name__}: {error}"


def arm_as2(session, kind, server, record, how: str) -> None:
    if how == "toolbar":
        edit(session, record, "edit1")
    else:
        record["click"] = ui.click(session, AT_TEXT)
        ui.press(session, kind, KEY)
    if how == "hidden":
        time.sleep(1.5)
        go_hidden(session, kind, record)
        if kind == "chrome":
            record["wait"] = wait_autos(session, 1, 15)
        else:
            time.sleep(7)   # evaluate would hit the new tab: come back, then read
            if record.get("editorHandle"):
                session.command("POST", "/window", {"handle": record["editorHandle"]})
            record["wait"] = wait_autos(session, 1, 20)
    else:
        record["wait"] = wait_autos(session, 1, 50)
    record["snaps"]["end"] = snap(session)
    record["fileAfter"] = file_facts(server)


def arm_as2c(session, kind, server, record) -> None:
    record["click"] = ui.click(session, AT_TEXT)
    start = time.monotonic()
    for i in range(KEYING_KEYS):
        ui.press(session, kind, KEY)
        time.sleep(max(0.0, start + (i + 1) * KEYING_GAP - time.monotonic()))
    record["keying"] = {"n": KEYING_KEYS, "gapS": KEYING_GAP}
    record["wait"] = wait_autos(session, 1, 20)
    ui.press(session, kind, KEY)             # the extra key: the threshold must be back to 30 s
    for _ in range(6):                       # 12 s of quiet, polling so a CDP socket stays awake
        time.sleep(2.0)
        evaluate(session, AUTOS)
    record["snaps"]["end"] = snap(session)


def arm_as3(session, kind, server, record) -> None:
    edit(session, record, "edit1")
    phase(session, server, record, "1", 1, time.monotonic())
    insert(session, record, "inserted", MARKER)
    phase(session, server, record, "2", 2, time.monotonic())
    record["snaps"]["end"] = record["phases"]["2"]["snap"]
    record["serverAfter"] = server.content(server.admin, NAME)


def arm_as4a(session, kind, server, record) -> None:
    break_lock(server, record)
    edit(session, record, "edit1")
    phase(session, server, record, "1", 1, time.monotonic())
    insert(session, record, "inserted", MARKER)
    phase(session, server, record, "2", 2, time.monotonic())
    record["snaps"]["end"] = record["phases"]["2"]["snap"]
    record["serverAfter"] = server.content(server.admin, NAME)


def arm_as4b(session, kind, server, record) -> None:
    # O2-1 (b): one manual save that reaches the ORIGINAL, before the conflict.
    insert(session, record, "pre", "LC0")
    save(session, record, 1)
    record["snaps"]["afterPre"] = snap(session)
    break_lock(server, record)
    edit(session, record, "edit1")
    save(session, record, 2)                 # M3's shape: two manual saves, no idle between them
    record["snaps"]["afterCopy"] = snap(session)
    insert(session, record, "inserted", MARKER)
    save(session, record, 3)
    time.sleep(1.0)
    record["snaps"]["end"] = snap(session)
    record["copiesAfter"] = copy_list(server)
    record["serverAfter"] = server.content(server.admin, NAME)


def arm_as4c(session, kind, server, record) -> None:
    # K12: a refused unlock by the other user moves the ETag; our lock stays valid.
    record["refusedUnlock"] = server.other.call("refused unlock", "DELETE",
                                                f"/ocs/v2.php/apps/files_lock/lock/{record['reset']['fileId']}",
                                                form={"lockType": 0})["status"]
    record["afterRefused"] = server.props(server.admin, NAME)
    edit(session, record, "edit1")
    save(session, record, 1)
    insert(session, record, "inserted", MARKER)
    save(session, record, 2)
    time.sleep(1.0)
    record["snaps"]["end"] = snap(session)
    record["lockAfterSave"] = server.props(server.admin, NAME)
    record["copiesAfter"] = copy_list(server)
    record["serverAfter"] = server.content(server.admin, NAME)
    if kind == "chrome":
        record["davRequests"] = wire(session.drain())


def typed_runs(raw: bytes) -> Counter:
    """The runs `z` + lowercase letters in a document's paragraphs (a document's own words count too)."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        joined = "\n".join(paragraph_texts_from_xml(archive.read("content.xml")))
    return Counter(re.findall(r"z[a-z]*", joined))


def arm_as5(session, kind, server, record, held: bool) -> None:
    record["quiet"] = ui.quiet(session, 90)
    record["click"] = ui.click(session, ui.IN_TEXT)
    ui.press(session, kind, KEY)
    key_at = evaluate(session, "(() => window.__as.keys.length ? window.__as.keys[0].t : null)()")
    deadline, busy = time.monotonic() + 60, None
    while time.monotonic() < deadline and key_at is not None:
        seen = evaluate(session, PILL_NOW)
        if seen["now"] - key_at >= BUSY_AFTER_S * 1000 and seen["state"] == "busy":
            busy = seen
            break
        time.sleep(1.0 if seen["now"] - key_at < (BUSY_AFTER_S - 1) * 1000 else 0.05)
    record["busySeen"] = busy
    if busy is None:
        raise RuntimeError(f"the pill never went busy 29 s or more after the key (key seen by the page: {key_at is not None})")
    if held:
        hold(session, kind, HELD, HELD_REPEATS, HELD_GAP)
        record["sent"] = HELD * HELD_REPEATS
    else:
        type_letters(session, kind, LETTERS, 0.125)
        record["sent"] = LETTERS
    record["wait"] = wait_autos(session, 2, 90)
    record["snaps"]["end"] = snap(session)
    raw = server.instance.dav("GET", NAME)[1]
    new = typed_runs(raw) - typed_runs(ui.DOC.read_bytes())
    longest = max(new.elements(), key=len, default=None)
    server_hash = server.content(server.admin, NAME)
    record["server"] = {"sha256": server_hash["sha256"], "bytes": server_hash["bytes"],
                        "received": longest[1:] if longest else None}


def arm_as6b(session, kind, server, record) -> None:
    break_lock(server, record)
    edit(session, record, "edit1")
    record["wait"] = wait_autos(session, 1, 50)
    record["snaps"]["end"] = snap(session)
    record["page"] = evaluate(session, PAGE_LOG)
    nonce = ph.install_recorder(session, record)
    ph.activate(session, kind, record)
    files = server.instance.base + "/apps/files/"
    ph.leave(session, kind, FILES_GO.replace("ARG_URL", json.dumps(files)), record, "leave", nonce)
    record["copiesAfter"] = copy_list(server)
    record["serverAfter"] = server.content(server.admin, NAME)


OFFLINE = {"offline": True, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1}


def arm_as7(session, kind, server, record) -> None:
    session.call("Network.emulateNetworkConditions", OFFLINE)
    edit(session, record, "edit1")
    phase(session, server, record, "1", 1, time.monotonic())
    insert(session, record, "inserted", MARKER)
    phase(session, server, record, "2", 2, time.monotonic())
    session.call("Network.emulateNetworkConditions", {**OFFLINE, "offline": False})
    insert(session, record, "back", "LC3")
    phase(session, server, record, "3", 3, time.monotonic())
    record["snaps"]["end"] = record["phases"]["3"]["snap"]
    record["serverAfter"] = server.content(server.admin, NAME)


def before_open_as3(server: Server, record: dict[str, Any]) -> None:
    """K5: the second user takes the lock first."""
    record["foreignLock"] = server.other.call("foreign lock", "LOCK", server.other.dav_path(server.targets["rw"]),
                                              None, {"X-User-Lock": "1"})["status"]


DRIVE = {
    "as2-key": lambda s, k, v, r: arm_as2(s, k, v, r, "key"),
    "as2-toolbar": lambda s, k, v, r: arm_as2(s, k, v, r, "toolbar"),
    "as2h": lambda s, k, v, r: arm_as2(s, k, v, r, "hidden"),
    "as2c": arm_as2c, "as3": arm_as3, "as4a": arm_as4a, "as4b": arm_as4b, "as4c": arm_as4c,
    "as5": lambda s, k, v, r: arm_as5(s, k, v, r, False),
    "as5-held": lambda s, k, v, r: arm_as5(s, k, v, r, True),
    "as6b": arm_as6b, "as7": arm_as7,
}
BEFORE_OPEN = {"as3": before_open_as3}


def run_arm(arm: str, kind: str, server: Server, scratch: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"arm": arm, "spec": PLAN[arm][0], "browser": kind, "startedAt": utc_now()}
    session = None
    try:
        owner_doc = None
        if arm in OWNER_DOC_ARMS:
            # The owner's document (gitignored): only its hash goes in the report, never its text.
            owner_doc = ui.DOC.read_bytes()
            record["docSha256"] = sha256_file(ui.DOC)
        record["clearedLocks"] = server.clear_locks()
        record["reset"] = {"upload": server.upload(server.admin, NAME, owner_doc),
                           "fileId": server.fileid(server.admin, NAME)}
        server.copies(server.admin, "", NAME[:-4], remove=True)
        record["serverBefore"] = server.content(server.admin, NAME)
        session = ui.new_session(kind) if arm in OWNER_DOC_ARMS else ph.new_session(kind, scratch)
        record["version"] = getattr(session, "version", None)
        if arm in BEFORE_OPEN:
            BEFORE_OPEN[arm](server, record)
        record["login"] = login(session, server.instance.base, "admin", server.instance.password)
        open_from_files(session, server.instance.base, "", NAME, record)
        record["opened"] = record.get("host")
        record["afterOpen"] = server.props(server.admin, NAME)
        record["snaps"] = {"open": snap(session)}
        evaluate(session, RECORDER)
        DRIVE[arm](session, kind, server, record)
        if "page" not in record:
            record["page"] = evaluate(session, PAGE_LOG)
        record["host"] = record["snaps"]["end"]["host"]
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            if session is not None:
                session.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            record["copiesRemoved"] = [c["name"] for c in server.copies(server.admin, "", NAME[:-4], remove=True)]
            record["clearedAtEnd"] = server.clear_locks()
        except Exception:  # noqa: BLE001
            record["cleanupError"] = traceback.format_exc()
        record["completedAt"] = utc_now()
    return record


# ------------------------------------------------------------------ scoring -- raw fields only
# A scorer returns problems.  A problem that starts with NE_TAG says "this run could not
# establish the criterion" (not "the criterion failed"); everything else is a failure.

NE_TAG = "NE: "
HELD_TOAST = "有字沒有輸入"
COPY_SAYS = "之後的存檔都會存到這份"
LABEL_RE = re.compile(r"上次儲存：(\d\d:\d\d)(（自動）)?")


def zero(value: Any) -> bool:
    return type(value) is int and value == 0


def autos_of(host: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [s for s in (host or {}).get("saves") or [] if s.get("trigger") == "auto"]


def when(host: dict[str, Any], rel: int) -> int:
    """A host record's relative ms on the page's epoch clock."""
    return host["started"] + rel


def conditions_problems(record: dict[str, Any]) -> list[str]:
    c = record.get("conditions")
    if not isinstance(c, dict):
        return ["no conditions"]
    held = [("viewOnly", c.get("viewOnly") is False), ("state", c.get("state") == "ready"),
            ("pending", zero(c.get("pending"))), ("composing", c.get("composing") is False),
            ("queueDepth", zero(c.get("queueDepth"))), ("dragging", c.get("dragging") is False),
            ("savesUnsettled", zero(c.get("savesUnsettled"))), ("rescue", c.get("rescue") is False)]
    return [f"{name}={c.get(name)!r}" for name, ok in held if not ok]


def as1(report: dict[str, Any]) -> tuple[str, list[str], int]:
    """AS-1, per record: every auto record in the report carries conditions and each one held."""
    count, bad = 0, []
    for run in report.get("runs") or []:
        for index, record in enumerate(autos_of(run.get("host"))):
            count += 1
            bad += [f"{run.get('arm')}/{run.get('browser')} auto #{index + 1}: {p}" for p in conditions_problems(record)]
    return (NE if count == 0 else FAIL if bad else PASS), bad, count


def label_absent(snapshot: dict[str, Any], tag: str) -> list[str]:
    label = snapshot.get("label")
    if label is None or label.get("hidden") is True or not label.get("text"):
        return []
    return [f"{tag}: the label shows before any write: {label!r}"]


def label_shows(snapshot: dict[str, Any], auto: bool, tag: str) -> list[str]:
    label = snapshot.get("label") or {}
    m = LABEL_RE.fullmatch(label.get("text") or "")
    if label.get("hidden") is not False or not m:
        return [f"{tag}: label {label!r}, wanted 上次儲存：HH:MM{'（自動）' if auto else ''}"]
    bad = []
    if bool(m.group(2)) != auto:
        bad.append(f"{tag}: label {label['text']!r} {'lacks' if auto else 'has'} （自動）")
    if m.group(1) not in (snapshot.get("allowed") or []):
        bad.append(f"{tag}: label time {m.group(1)} is not the record's {snapshot.get('allowed')}")
    return bad


def inserted(run: dict[str, Any], key: str) -> list[str]:
    got = run.get(key) or {}
    return [] if got and not got.get("timedOut") and got.get("latency") != INSERT_FAILED \
        else [f"premise: {key} did not complete ({got.get('latency')!r}, timed out {got.get('timedOut')})"]


def last_new_revision(revisions: list[dict[str, Any]]) -> float | None:
    """When `#s-revision` last took a NEW value.  The page rewrites the same value many times (each one a
    mutation the recorder logs), and a rewrite during the autosave is not the action's completion
    (shakedown 2026-10-12T054605, as2-toolbar: the last mutation came 0.3 s after the auto began)."""
    ref = None
    for before, after in zip(revisions, revisions[1:]):
        if after["revision"] != before["revision"]:
            ref = after["t"]
    return ref


def s_as2(run, report, how: str) -> list[str]:
    host, page, autos = run["host"], run["page"], autos_of(run["host"])
    bad = label_absent(run["snaps"]["open"], "O2-1(a)")
    if how == "toolbar":
        bad += edited(run, "edit1")
        if page["keys"]:
            bad.append("AS-2: the toolbar arm saw keydowns")
        ref, what = last_new_revision(page["revisions"]), "the action's completion"
    else:
        if len(page["keys"]) != 1:
            bad.append(f"AS-2: {len(page['keys'])} keydowns seen, wanted exactly one")
        ref, what = (page["keys"][-1]["t"] if page["keys"] else None), "the last keydown"
    if ref is None:
        return bad + [f"AS-2: the page saw no {what}"]
    if not autos:
        return bad + ["AS-2: no auto record"]
    delta = (when(host, autos[0]["at"]) - ref) / 1000
    if not 30.0 <= delta <= 35.0:
        bad.append(f"AS-2: the first auto record began {delta:.1f} s after {what}, wanted 30.0-35.0")
    if autos[0].get("outcome") != "saved":
        bad.append(f"AS-2: outcome {autos[0].get('outcome')!r}")
    held = run["fileAfter"]
    if how == "toolbar":
        if held.get("heading") is not True:
            bad.append("AS-2: the server file has no heading: the toolbar edit is not in it")
    elif sum(t.count(KEY) for t in held.get("texts") or []) != 1:
        bad.append(f"AS-2: the server file does not hold the one letter {KEY!r}")
    return bad + label_shows(run["snaps"]["end"], True, "O2-1(c)")


def s_as2h(run, report) -> list[str]:
    host, page, autos = run["host"], run["page"], autos_of(run["host"])
    hidden = [v for v in page["visibility"] if v["state"] == "hidden"]
    if not hidden:
        return [NE_TAG + "the page never saw visibilitychange to hidden" + (f" ({run['hideError']})" if run.get("hideError") else "")]
    if len(page["keys"]) != 1:
        return [f"AS-2h: {len(page['keys'])} keydowns seen, wanted exactly one"]
    gap = (hidden[0]["t"] - page["keys"][0]["t"]) / 1000
    if gap > 5.0:
        return [NE_TAG + f"the tab went hidden {gap:.1f} s after the key, the arm wants 5 s or less"]
    if not autos:
        return ["AS-2h: no auto record after the tab went hidden"]
    bad = []
    delta = (when(host, autos[0]["at"]) - hidden[0]["t"]) / 1000
    if not 0.0 <= delta <= 2.0:
        bad.append(f"AS-2h: the first auto record began {delta:.1f} s after the hidden event, wanted 0-2")
    if autos[0].get("outcome") != "saved":
        bad.append(f"AS-2h: outcome {autos[0].get('outcome')!r}")
    if sum(t.count(KEY) for t in run["fileAfter"].get("texts") or []) != 1:
        bad.append(f"AS-2h: the server file does not hold the one letter {KEY!r}")
    return bad


def s_as2c(run, report) -> list[str]:
    host, autos, n = run["host"], autos_of(run["host"]), run["keying"]["n"]
    keys = [k["t"] for k in run["page"]["keys"]]
    if len(keys) != n + 1:
        return [f"AS-2c: {len(keys)} keydowns seen, wanted {n} + the extra one"]
    last = keys[n - 1]
    bad = []
    if last - keys[0] < 300_000:
        bad.append(f"AS-2c: the keying lasted {(last - keys[0]) / 1000:.0f} s: the 5-minute cap was never reached")
    early = [a for a in autos if when(host, a["at"]) < last]
    if early:
        bad.append(f"AS-2c: {len(early)} auto record(s) began while the keys were still coming")
    if not autos:
        return bad + ["AS-2c: no auto record after the keying stopped"]
    after = [a for a in autos if when(host, a["at"]) >= last]
    delta = (when(host, after[0]["at"]) - last) / 1000 if after else None
    if delta is None or not 3.0 <= delta <= 6.0:
        bad.append(f"AS-2c: the first auto record after the last key began {delta} s later, wanted 3-6")
    if after and after[0].get("outcome") != "saved":
        bad.append(f"AS-2c: outcome {after[0].get('outcome')!r}")
    if len(autos) != 1:
        bad.append(f"AS-2c: {len(autos)} auto records, wanted 1 (the threshold must be 30 s again after the save)")
    if after and keys[n] < when(host, after[0]["at"]):
        bad.append("AS-2c: the extra key came before the capped auto record: nothing was tested after it")
    quiet = (run["snaps"]["end"]["now"] - keys[n]) / 1000
    if quiet < 10.0:
        bad.append(f"AS-2c: {quiet:.1f} s of quiet after the extra key, wanted 10")
    return bad


def copy_flow(run, report, tag: str, first: dict[str, Any], name: str | None, later: list[dict[str, Any]],
              copies: list[dict[str, Any]]) -> list[str]:
    """The part AS-3 and AS-4 share: one copy, saves go on into it, it holds the last edit."""
    bad = []
    if first.get("outcome") != "copy" or not name:
        bad.append(f"{tag}: first outcome {first.get('outcome')!r}, copy {name!r}")
    for record in later:
        if record.get("outcome") != "saved" or record.get("target") != name:
            bad.append(f"{tag}: a later save went {record.get('outcome')!r} to {record.get('target')!r}, wanted saved to the copy")
    last = (later or [first])[-1]
    if len(copies) != 1:
        bad.append(f"{tag}: {len(copies)} copies, wanted 1: {[c.get('name') for c in copies]}")
    elif copies[0].get("holdsMarker") is not True or copies[0].get("sha256") != last.get("sha256") \
            or (name and copies[0].get("name") != name):
        bad.append(f"{tag}: the copy {copies[0].get('name')!r} does not hold the last save's bytes / the second edit")
    return bad


def s_as3(run, report) -> list[str]:
    host, autos = run["host"], autos_of(run["host"])
    p1, p2 = run["phases"]["1"], run["phases"]["2"]
    bad = edited(run, "edit1") + inserted(run, "inserted")
    if run.get("foreignLock") != 200 or (run["snaps"]["open"]["host"].get("lock") or {}).get("state") != "refused":
        bad.append("AS-3: premise: the file was not opened while another user held the lock")
    for tag, got, want in (("first", p1, 1), ("second", p2, 2)):
        if len(autos_of(got["snap"]["host"])) != want:
            bad.append(f"AS-3: {len(autos_of(got['snap']['host']))} auto records after the {tag} idle, wanted exactly {want}")
    if len(autos) < 2:
        return bad + ["AS-3: fewer than two auto records"]
    name = (autos[0].get("conflictCopy") or {}).get("name")
    bad += copy_flow(run, report, "AS-3", autos[0], name, autos[1:2], p2["copies"])
    if len(p1["copies"]) != 1:
        bad.append(f"AS-3: {len(p1['copies'])} copies after the first idle, wanted 1")
    first = p1["snap"]
    if not name or name not in (first.get("notice") or "") or first.get("title") != name:
        bad.append(f"AS-3: host bar {first.get('notice')!r} / title {first.get('title')!r} do not name the copy")
    if run["serverAfter"]["sha256"] != report["original"]["sha256"]:
        bad.append("AS-3: the original file changed")
    return bad


def s_as4a(run, report) -> list[str]:
    host, autos = run["host"], autos_of(run["host"])
    p1, p2 = run["phases"]["1"], run["phases"]["2"]
    bad = edited(run, "edit1") + inserted(run, "inserted")
    if run.get("ownerUnlock") != 200 or not 200 <= (run.get("intruded") or 0) < 300:
        bad.append(f"AS-4(a): premise: owner unlock {run.get('ownerUnlock')}, intruder write {run.get('intruded')}")
    for tag, got, want in (("first", p1, 1), ("second", p2, 2)):
        if len(autos_of(got["snap"]["host"])) != want:
            bad.append(f"AS-4(a): {len(autos_of(got['snap']['host']))} auto records after the {tag} idle, wanted exactly {want}")
    if len(autos) < 2:
        return bad + ["AS-4(a): fewer than two auto records"]
    name = (autos[0].get("conflictCopy") or {}).get("name")
    bad += copy_flow(run, report, "AS-4(a)", autos[0], name, autos[1:2], p2["copies"])
    first = p1["snap"]
    if not name or name not in (first.get("notice") or "") or COPY_SAYS not in (first.get("notice") or ""):
        bad.append(f"AS-4(a): host bar {first.get('notice')!r} must name the copy and say {COPY_SAYS!r}")
    if first.get("title") != name or first.get("doc") != NAME:
        bad.append(f"AS-4(a): title {first.get('title')!r} (want the copy), #s-doc {first.get('doc')!r} (want {NAME!r})")
    if run["serverAfter"]["sha256"] != report["intruder"]["sha256"]:
        bad.append("AS-4(a): the original is no longer the other writer's bytes")
    return bad


def s_as4b(run, report) -> list[str]:
    host = run["host"]
    saves = host.get("saves") or []
    bad = inserted(run, "pre") + edited(run, "edit1") + inserted(run, "inserted")
    if run.get("ownerUnlock") != 200 or not 200 <= (run.get("intruded") or 0) < 300:
        bad.append(f"AS-4(b): premise: owner unlock {run.get('ownerUnlock')}, intruder write {run.get('intruded')}")
    if autos_of(host):
        bad.append("AS-4(b): premise: an autosave fired between the manual saves")
    if len(saves) != 3 or saves[0].get("outcome") != "saved" or saves[0].get("target") != "original":
        return bad + [f"AS-4(b): saves {[(s.get('outcome'), s.get('target')) for s in saves]}, wanted original, copy, copy"]
    bad += label_shows(run["snaps"]["afterPre"], False, "O2-1(b)")
    name = (saves[1].get("conflictCopy") or {}).get("name")
    bad += copy_flow(run, report, "AS-4(b)", saves[1], name, saves[2:], run["copiesAfter"])
    after = run["snaps"]["afterCopy"]
    saved = (after.get("host") or {}).get("lastSaved") or {}
    if after.get("title") != name or saved.get("target") != name \
            or saved.get("at") != (saves[1].get("conflictCopy") or {}).get("respondedAt"):
        bad.append(f"O2-1(d): after the copy: title {after.get('title')!r}, host lastSaved {saved}")
    bad += label_shows(after, False, "O2-1(d)")
    if run["serverAfter"]["sha256"] != report["intruder"]["sha256"]:
        bad.append("AS-4(b): the original is no longer the other writer's bytes")
    return bad


def s_as4c(run, report) -> list[str]:
    host = run["host"]
    saves = host.get("saves") or []
    bad = edited(run, "edit1") + inserted(run, "inserted")
    if autos_of(host):
        bad.append("AS-4(c): premise: an autosave fired between the manual saves")
    if run.get("refusedUnlock") != 423 or len(saves) != 2:
        return bad + [f"AS-4(c): premise: refused unlock {run.get('refusedUnlock')}, {len(saves)} saves"]
    if attempts(saves[0]) != [(412, True)]:
        bad.append(f"AS-4(c): first save attempts {attempts(saves[0])}, wanted [(412, True)]: the token is alive")
    name = (saves[0].get("conflictCopy") or {}).get("name")
    bad += copy_flow(run, report, "AS-4(c)", saves[0], name, saves[1:], run["copiesAfter"])
    kept = run["lockAfterSave"]
    if (host.get("lock") or {}).get("state") != "held" or kept.get("lock") != "1" \
            or kept.get("token") != (run.get("afterOpen") or {}).get("token"):
        bad.append(f"AS-4(c): the lock did not stay: host {(host.get('lock') or {}).get('state')}, server token {kept.get('token')}")
    if run["browser"] == "chrome":
        puts = [r for r in run.get("davRequests") or [] if r["method"] == "PUT"
                and urllib.parse.unquote(r["url"]).endswith(name or "\0")]
        version = (saves[0].get("conflictCopy") or {}).get("etag")
        if len(puts) != 2:
            bad.append(f"AS-4(c): {len(puts)} PUTs to the copy on the wire, wanted 2 (create, then the second save)")
        elif puts[1].get("ifMatch") != version or not version or puts[1].get("if"):
            bad.append(f"AS-4(c): second PUT to the copy: If-Match {puts[1].get('ifMatch')!r} (copy's {version!r}), If {puts[1].get('if')!r} (want none)")
    return bad


def s_as5(run, report, held: bool) -> list[str]:
    host, page, autos = run["host"], run["page"], autos_of(run["host"])
    bad = []
    if ui.DOC_SHA256 is not None and run.get("docSha256") != ui.DOC_SHA256:
        bad.append(f"AS-5: premise: document {str(run.get('docSha256'))[:12]}, not the owner's {ui.DOC_SHA256[:12]}")
    if len(autos) != 2 or [a.get("outcome") for a in autos] != ["saved", "saved"]:
        return bad + [f"AS-5: auto outcomes {[a.get('outcome') for a in autos]}, wanted saved, saved (the typing one, then the one that carries it)"]
    key = page["keys"][0]["t"] if page["keys"] else None
    if key is None or (when(host, autos[0]["at"]) - key) / 1000 < BUSY_AFTER_S:
        bad.append("AS-5: premise: the first auto record did not begin 29 s or more after the key")
    sent, received = run["sent"], (run.get("server") or {}).get("received")
    # The criterion types DURING the auto's engine part: the first typed key must come before
    # the host part begins (the host record's `at`).  Otherwise nothing overlapped and the arm
    # established nothing (dual review, codex item 2).
    if len(page["keys"]) > 1 and page["keys"][1]["t"] >= when(host, autos[0]["at"]):
        bad.append(NE_TAG + f"the typing began {(page['keys'][1]['t'] - when(host, autos[0]['at'])) / 1000:.2f} s "
                   "after the auto's engine part ended: nothing typed during it")
    if len(page["keys"]) - 1 != len(sent):
        bad.append(f"AS-5: the page saw {len(page['keys']) - 1} keydowns after the first, the runner sent {len(sent)}")
    lost = len(sent) - len(received or "")
    if held:
        if received is None or received != sent[:len(received)]:
            bad.append(f"AS-5: received {received!r} is not a run of the held key")
        shown = [t for t in page["toasts"] if t["text"].startswith(HELD_TOAST) and t["t"] >= run["busySeen"]["now"]]
        if lost > 0 and not shown:
            bad.append(f"AS-5: {lost} of {len(sent)} held keys were lost and the page showed no {HELD_TOAST!r} toast")
    elif received != sent:
        bad.append(f"AS-5: {len(sent)} letters typed during the save, the server holds {received!r}")
    return bad


def s_as6b(run, report) -> list[str]:
    host, autos = run["host"], autos_of(run["host"])
    bad = edited(run, "edit1")
    if run.get("ownerUnlock") != 200 or not 200 <= (run.get("intruded") or 0) < 300:
        bad.append(f"AS-6(b): premise: owner unlock {run.get('ownerUnlock')}, intruder write {run.get('intruded')}")
    if len(autos) != 1 or autos[0].get("outcome") != "copy":
        return bad + [f"AS-6(b): auto outcomes {[a.get('outcome') for a in autos]}, wanted one copy"]
    bad += [p.replace("leave:", "AS-6(b): leaving:") for p in ph.not_asked(run, "leave")]
    copies = run["copiesAfter"]
    if len(copies) != 1 or copies[0].get("sha256") != autos[0].get("sha256"):
        bad.append(f"AS-6(b): after leaving, copies {[(c.get('name'), str(c.get('sha256'))[:12]) for c in copies]} vs the auto record's bytes")
    return bad


def s_as7(run, report) -> list[str]:
    host, autos = run["host"], autos_of(run["host"])
    p1, p2 = run["phases"]["1"], run["phases"]["2"]
    bad = inserted(run, "inserted") + inserted(run, "back") + edited(run, "edit1")
    if [a.get("outcome") for a in autos] != ["stranded", "stranded", "saved"]:
        return bad + [f"AS-7: auto outcomes {[a.get('outcome') for a in autos]}, wanted stranded, stranded, saved"]
    s1, s2, s3 = p1["snap"], p2["snap"], run["snaps"]["end"]
    if s1.get("notice") != STRANDED or s1.get("downloadHidden") is not False:
        bad.append(f"AS-7: host bar after the first strand: {s1.get('notice')!r}, download hidden {s1.get('downloadHidden')}")
    if s1.get("toasts") != 0 or s2.get("toasts") != 0:
        bad.append(f"AS-7: a toast appeared while stranded ({s1.get('toasts')}, {s2.get('toasts')})")
    if p1["copies"] or p2["copies"]:
        bad.append("AS-7: a copy appeared while offline")
    before = run["snaps"]["open"].get("label")
    for tag, got in (("first", s1), ("second", s2)):
        if got.get("label") != before:
            bad.append(f"O2-1(e): the label changed after the {tag} stranded save: {before!r} -> {got.get('label')!r}")
    if autos[0].get("sha256") == autos[1].get("sha256"):
        bad.append("AS-7: both stranded saves sent the same bytes: the check cannot tell whether strand() renewed them")
    if ((s2.get("host") or {}).get("stranded") or {}).get("sha256") != autos[1].get("sha256"):
        bad.append(f"AS-7: the host keeps {((s2.get('host') or {}).get('stranded') or {}).get('sha256')!r}, the second auto sent {autos[1].get('sha256')!r}")
    shost = s3.get("host") or {}
    if shost.get("stranded") is not None or (shost.get("unstranded") or {}).get("how") != "saved":
        bad.append(f"AS-7: after the online save: stranded {shost.get('stranded')}, unstranded {shost.get('unstranded')}")
    if s3.get("notice") != "" or s3.get("barHidden") is not True:
        bad.append(f"AS-7: host bar after the online save: {s3.get('notice')!r}, hidden {s3.get('barHidden')}")
    bad += label_shows(s3, True, "O2-1(c)")
    if run["serverAfter"]["sha256"] != autos[2].get("sha256"):
        bad.append("AS-7: the server file is not the online auto's bytes")
    return bad


SCORERS = {
    "as2-key": lambda r, rep: s_as2(r, rep, "key"), "as2-toolbar": lambda r, rep: s_as2(r, rep, "toolbar"),
    "as2h": s_as2h, "as2c": s_as2c, "as3": s_as3, "as4a": s_as4a, "as4b": s_as4b, "as4c": s_as4c,
    "as5": lambda r, rep: s_as5(r, rep, False), "as5-held": lambda r, rep: s_as5(r, rep, True),
    "as6b": s_as6b, "as7": s_as7,
}


def score_run(run: dict[str, Any], report: dict[str, Any]) -> tuple[str, list[str]]:
    if run.get("fatal"):
        return FAIL, [f"fatal: {run['fatal'].strip().splitlines()[-1]}"]
    try:
        bad = list(ph.opened_ready(run)) + SCORERS[run["arm"]](run, report)
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as error:
        return FAIL, [f"record incomplete: {type(error).__name__}: {error}"]
    hard = [p for p in bad if not p.startswith(NE_TAG)]
    if hard:
        return FAIL, hard
    soft = [p[len(NE_TAG):] for p in bad]
    return (NE if soft else PASS), soft


def binding_problems(report: dict[str, Any]) -> list[str]:
    """A counted report is about the bound page, session and host, and nothing else."""
    pins = {"PAGE_SHA256": PAGE_SHA256, "SESSION_SHA256": SESSION_SHA256, "HOST_VERSION": HOST_VERSION,
            "HOST_COMMIT": HOST_COMMIT}
    if any(v is None for v in pins.values()):
        return [f"not bound yet: {sorted(k for k, v in pins.items() if v is None)}"]
    st, bad = report.get("static") or {}, []
    if st.get("page") != {"dist": PAGE_SHA256, "web": PAGE_SHA256, "served": PAGE_SHA256}:
        bad.append(f"page {st.get('page')}")
    if st.get("session") != {"tree": SESSION_SHA256, "dist": SESSION_SHA256, "served": SESSION_SHA256}:
        bad.append(f"session {st.get('session')}")
    if st.get("hostVersion") != HOST_VERSION:
        bad.append(f"host version {st.get('hostVersion')}")
    if not str(report.get("hostRepo") or "").startswith(HOST_COMMIT):
        bad.append(f"host commit {str(report.get('hostRepo'))[:12]}, pinned {HOST_COMMIT}")
    if report.get("hostDirty"):
        bad.append(f"host repo dirty: {report.get('hostDirty')!r}")
    if st.get("testStatic") != 0:
        bad.append(f"make test-e2-c-static {st.get('testStatic')}")
    return bad


def score(report: dict[str, Any], strict: bool) -> dict[str, Any]:
    cells: dict[str, dict[str, Any]] = {}
    for run in report.get("runs") or []:
        status, problems = score_run(run, report)
        cell = cells.setdefault(f"{run['arm']}/{run['browser']}", {PASS: 0, FAIL: 0, NE: 0, "runs": 0, "problems": []})
        cell["runs"] += 1
        cell[status] += 1
        if problems:
            cell["problems"].append(problems)
        if run["arm"] == "as5-held" and not run.get("fatal"):
            # The criterion is conditional on a loss; say how often the toast path was exercised.
            lost = len(run.get("sent") or "") - len((run.get("server") or {}).get("received") or "")
            cell["lossRuns"] = cell.get("lossRuns", 0) + (lost > 0)
    for key, cell in cells.items():
        # AS-5 held is conditional on a loss: a cell where no run lost a key never ran the toast
        # path, and green would look the same as a toast path that is not there (dual review,
        # fable's position on judgement call 1).
        if key.startswith("as5-held/") and cell.get("lossRuns") == 0 and cell[PASS]:
            cell[NE], cell[PASS] = cell[NE] + cell[PASS], 0
            cell["problems"].append([NE_TAG + "no held key was lost in any run: the toast path never ran"])
    status1, bad1, count1 = as1(report)
    problems = binding_problems(report) if strict else []
    if strict:
        for arm, (_, browsers, count) in PLAN.items():
            for browser in browsers:
                runs = cells.get(f"{arm}/{browser}", {}).get("runs", 0)
                if runs != count:
                    problems.append(f"{arm}/{browser}: {runs} runs, plan {count}")
    fails = any(c[FAIL] for c in cells.values()) or status1 == FAIL
    unsure = any(c[NE] for c in cells.values()) or status1 == NE
    if strict:
        verdict = ("AUTOSAVE DOES NOT HOLD" if fails or problems else
                   "AUTOSAVE NOT ESTABLISHED" if unsure else "AUTOSAVE HOLDS")
    else:
        verdict = "red" if fails else "unestablished" if unsure else "clean"
    return {"verdict": verdict, "cells": cells, "as1": [status1, bad1, count1], "problems": problems}


def report_lines(result: dict[str, Any]) -> list[str]:
    status1, bad1, count1 = result["as1"]
    out = [f"AS-1 {status1}  auto records read: {count1}" + ("  (none: NOT_ESTABLISHED, never PASS)" if count1 == 0 else "")]
    out += [f"    {p}" for p in bad1]
    for key, cell in sorted(result["cells"].items()):
        status = FAIL if cell[FAIL] else NE if cell[NE] else PASS
        out.append(f"{key:18} {status:16} pass {cell[PASS]}/{cell['runs']}"
                   + (f"  (held key lost letters in {cell['lossRuns']}/{cell['runs']} runs)" if "lossRuns" in cell else ""))
        out += [f"    {p}" for problems in cell["problems"] for p in problems]
    out += [f"problem: {p}" for p in result["problems"]]
    out.append(f"VERDICT {result['verdict']}")
    return out


# ------------------------------------------------------------------ red cases
# One mutation per criterion on a clean run of the arm it targets.  A case counts only if
# the scorer names the criterion's own problem (a substring), not merely any problem.


def each_host(run: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [run.get("host")] + [s.get("host") for s in (run.get("snaps") or {}).values()] \
        + [p["snap"].get("host") for p in (run.get("phases") or {}).values()]
    seen, out = set(), []
    for host in candidates:
        if host is not None and id(host) not in seen:
            seen.add(id(host))
            out.append(host)
    return out


def on_autos(run: dict[str, Any], fn) -> None:
    for host in each_host(run):
        for index, record in enumerate(autos_of(host)):
            fn(index, record, host)


def drop_auto(run: dict[str, Any], index: int) -> None:
    for host in each_host(run):
        autos = autos_of(host)
        if len(autos) > index:
            host["saves"].remove(autos[index])


def set_copies(run: dict[str, Any], keys: tuple[str, ...], extra: dict[str, Any]) -> None:
    for key in keys:
        holder = run if key == "copiesAfter" else run["phases"][key]
        field = "copiesAfter" if key == "copiesAfter" else "copies"
        holder[field].append(dict(holder[field][0], **extra))


# (label, arm, browsers or None, mutation, expected substring, kind)
# kind "run": the run must score FAIL with the substring; "ne": NOT_ESTABLISHED; "as1": AS-1 on a one-run report.
RED_CASES = [
    ("AS-1: an auto record whose composing is true", "as2-key", None,
     lambda r: on_autos(r, lambda i, a, h: a["conditions"].update(composing=True)), "composing", "as1"),
    ("AS-1: an auto record with no conditions", "as2-key", None,
     lambda r: on_autos(r, lambda i, a, h: a.pop("conditions")), "no conditions", "as1"),
    ("AS-1: zero auto records is NOT_ESTABLISHED, not PASS", "as2-key", None,
     lambda r: [h.update(saves=[]) for h in each_host(r)], "", "as1-ne"),
    ("AS-2: first auto at 300 s", "as2-key", None,
     lambda r: on_autos(r, lambda i, a, h: a.update(at=a["at"] + 270_000) if i == 0 else None), "AS-2:", "run"),
    ("AS-2: first auto before 30 s (a shorter threshold)", "as2-key", None,
     lambda r: on_autos(r, lambda i, a, h: a.update(at=a["at"] - 3_000) if i == 0 else None), "AS-2:", "run"),
    ("AS-2: the toolbar action does not count as activity (timer left from the click)", "as2-toolbar", None,
     lambda r: on_autos(r, lambda i, a, h: a.update(at=a["at"] - 1_800) if i == 0 else None), "AS-2:", "run"),
    ("AS-2: the toolbar edit is not in the server file", "as2-toolbar", None,
     lambda r: r["fileAfter"].update(heading=False), "no heading", "run"),
    ("AS-2: the auto outcome is not saved", "as2-key", None,
     lambda r: on_autos(r, lambda i, a, h: a.update(outcome="stranded")), "outcome", "run"),
    ("O2-1 (a): the label is shown before any write", "as2-key", None,
     lambda r: r["snaps"]["open"].update(label={"hidden": False, "text": "上次儲存：12:00"}), "O2-1(a)", "run"),
    ("O2-1 (c): an auto save's label lacks （自動）", "as2-key", None,
     lambda r: r["snaps"]["end"]["label"].update(text="上次儲存：12:00"), "O2-1(c)", "run"),
    ("O2-1: the label time is not the record's", "as2-key", None,
     lambda r: r["snaps"]["end"].update(allowed=["03:00", "03:01", "03:02"]), "O2-1(c)", "run"),
    ("AS-2h: the auto begins 10 s after the tab went hidden", "as2h", None,
     lambda r: on_autos(r, lambda i, a, h: a.update(at=a["at"] + 10_000) if i == 0 else None), "AS-2h", "run"),
    ("AS-2h: the page never saw hidden is NOT_ESTABLISHED, not red", "as2h", None,
     lambda r: r["page"].update(visibility=[]), "hidden", "ne"),
    ("AS-2c: an auto record while the keys were coming", "as2c", None,
     lambda r: on_autos(r, lambda i, a, h: a.update(at=a["at"] - 60_000) if i == 0 else None), "while the keys", "run"),
    ("AS-2c: no cap (the auto comes 30 s after the last key)", "as2c", None,
     lambda r: on_autos(r, lambda i, a, h: a.update(at=a["at"] + 27_000) if i == 0 else None), "AS-2c", "run"),
    ("AS-2c: the threshold is not back to 30 s (a second auto after the extra key)", "as2c", None,
     lambda r: [h["saves"].append(dict(autos_of(h)[0], at=autos_of(h)[0]["at"] + 6_000)) for h in each_host(r) if autos_of(h)],
     "auto records, wanted 1", "run"),
    ("AS-3: the second edit is not autosaved (no new auto record)", "as3", None,
     lambda r: drop_auto(r, 1), "auto records", "run"),
    ("AS-3: no auto record at all (a rule that skips a file opened under a lock)", "as3", None,
     lambda r: [h.update(saves=[]) for h in each_host(r)], "auto records", "run"),
    ("AS-3: the second auto wrote another copy", "as3", None,
     lambda r: set_copies(r, ("2",), {"name": "x（衝突副本）.odt"}), "copies, wanted 1", "run"),
    ("AS-3: the host bar does not name the copy", "as3", None,
     lambda r: r["phases"]["1"]["snap"].update(notice="正被別人鎖定編輯"), "do not name the copy", "run"),
    ("AS-4 (a): the host does not switch target (two copies)", "as4a", None,
     lambda r: set_copies(r, ("2",), {"name": "y（衝突副本）.odt"}), "copies, wanted 1", "run"),
    ("AS-4 (a): the title bar still shows the original's name", "as4a", None,
     lambda r: r["phases"]["1"]["snap"].update(title=NAME), "title", "run"),
    ("AS-4 (a): the host bar does not say later saves go to the copy", "as4a", None,
     lambda r: r["phases"]["1"]["snap"].update(notice=r["phases"]["1"]["snap"]["notice"].replace(COPY_SAYS, "")), COPY_SAYS, "run"),
    ("AS-4 (a): the original is overwritten", "as4a", None,
     lambda r: r["serverAfter"].update(sha256="0" * 64), "other writer", "run"),
    ("AS-4 (b): two copies (0.2.12)", "as4b", None,
     lambda r: set_copies(r, ("copiesAfter",), {"name": "z（衝突副本）.odt"}), "copies, wanted 1", "run"),
    ("O2-1 (b): a manual save's label says （自動）", "as4b", None,
     lambda r: r["snaps"]["afterPre"]["label"].update(text="上次儲存：12:00（自動）"), "O2-1(b)", "run"),
    ("O2-1 (d): the copy write does not update the label", "as4b", None,
     lambda r: r["snaps"]["afterCopy"]["host"]["lastSaved"].update(at=1), "O2-1(d)", "run"),
    ("AS-4 (c): the copy PUT carries an If header", "as4c", ("chrome",),
     lambda r: [x.update({"if": "(<opaquelocktoken:t>)"}) for x in r["davRequests"] if x["method"] == "PUT"][-1:], "If", "run"),
    ("AS-4 (c): the copy PUT's If-Match is not the copy's version", "as4c", ("chrome",),
     lambda r: [x.update(ifMatch='"other"') for x in r["davRequests"] if x["method"] == "PUT"][-1:], "If-Match", "run"),
    ("AS-4 (c): the lock was lost", "as4c", None,
     lambda r: r["lockAfterSave"].update(token="opaquelocktoken:other"), "lock did not stay", "run"),
    ("AS-4 (c): the second save made another copy", "as4c", None,
     lambda r: set_copies(r, ("copiesAfter",), {"name": "w（衝突副本）.odt"}), "copies, wanted 1", "run"),
    ("AS-5: a letter typed during the save is lost", "as5", None,
     lambda r: r["server"].update(received=r["server"]["received"][:-1]), "AS-5", "run"),
    ("AS-5: letters out of order", "as5", None,
     lambda r: r["server"].update(received=r["server"]["received"][::-1]), "AS-5", "run"),
    ("AS-5: the typing began after the auto's engine part (no overlap) is NOT_ESTABLISHED", "as5", None,
     lambda r: [k.update(t=when(r["host"], autos_of(r["host"])[0]["at"]) + 100 + i * 125)
                for i, k in enumerate(r["page"]["keys"][1:])], "engine part ended", "ne"),
    ("AS-5 held: letters lost and the page showed no toast", "as5-held", None,
     lambda r: (r["page"].update(toasts=[]), r["server"].update(received="k" * 10)), HELD_TOAST, "run"),
    ("AS-6 (b): leaving after the auto copy is asked about", "as6b", None,
     lambda r: r["leaves"]["leave"]["record"].append({"what": "preventDefault", "who": "host"}), "asked by", "run"),
    ("AS-6 (b): the copy does not hold the last edit", "as6b", None,
     lambda r: r["copiesAfter"][0].update(sha256="0" * 64), "after leaving", "run"),
    ("AS-7: strand() keeps the first bytes (host sha256 is the first record's)", "as7", None,
     lambda r: [h.update(stranded={"sha256": autos_of(h)[0]["sha256"]}) for h in each_host(r) if len(autos_of(h)) == 2 and h.get("stranded")], "the host keeps", "run"),
    ("AS-7: no second auto after a strand (paused)", "as7", None,
     lambda r: drop_auto(r, 1), "auto outcomes", "run"),
    ("AS-7: the stranded save raised a toast", "as7", None,
     lambda r: r["phases"]["1"]["snap"].update(toasts=1), "toast", "run"),
    ("O2-1 (e): the label is updated by a stranded save", "as7", None,
     lambda r: r["phases"]["1"]["snap"].update(label={"hidden": False, "text": "上次儲存：12:00（自動）"}), "O2-1(e)", "run"),
    ("AS-7: the stranded notice stays after the online save", "as7", None,
     lambda r: r["snaps"]["end"].update(notice=STRANDED), "after the online save", "run"),
    ("AS-7: the stranded bytes are not cleared", "as7", None,
     lambda r: r["snaps"]["end"]["host"].update(stranded={"sha256": "x"}), "after the online save", "run"),
]


def red_case_result(case, base: dict[str, Any], report: dict[str, Any]) -> tuple[bool, str]:
    label, arm, _, mutate, expect, kind = case
    mutated = copy.deepcopy(base)
    mutate(mutated)
    if kind in ("as1", "as1-ne"):
        status, bad, _ = as1({"runs": [mutated]})
        if kind == "as1-ne":
            return status == NE, f"AS-1 {status}"
        return status == FAIL and any(expect in p for p in bad), f"AS-1 {status} {bad}"
    status, problems = score_run(mutated, report)
    if kind == "ne":
        return status == NE and any(expect in p for p in problems), f"{status} {problems}"
    return status == FAIL and any(expect in p for p in problems), f"{status} {problems}"


def run_red_cases(report: dict[str, Any]) -> int:
    failures = 0
    for case in RED_CASES:
        label, arm, only, *_ = case
        for browser in only or PLAN[arm][1]:
            base = next((r for r in report["runs"] if r["arm"] == arm and r["browser"] == browser
                         and score_run(r, report)[0] == PASS), None)
            if base is None:
                print(f"  MISSING {label} [{browser}]: no clean {arm} run in this report")
                failures += 1
                continue
            try:
                red, why = red_case_result(case, base, report)
            except (KeyError, IndexError, TypeError, StopIteration, AttributeError) as error:
                print(f"  MISSING {label} [{browser}]: the clean run has nothing to mutate ({error!r})")
                failures += 1
                continue
            failures += not red
            print(f"  {'red ' if red else 'GREEN'}  {label} [{browser}]" + ("" if red else f"  -> {why}"))
    return failures


# ------------------------------------------------------------------ self-test (offline: no browser, no server)
# A clean report made by hand in the shape the driver writes, scored strict; then every
# red case, and the report-level ones.  What it proves is the scorer's reach, not the
# product: the first shakedown on the real host is what shows the shapes agree.

T0 = 1_760_000_000_000
ORIG, INTRUDER = "0" * 63 + "1", "0" * 63 + "2"
COPY = "M3 骨架 測試（衝突副本 2026-10-12 120000）.odt"
HMS = ["11:59", "12:00", "12:01"]
OK_CONDITIONS = {"viewOnly": False, "state": "ready", "pending": 0, "composing": False, "queueDepth": 0,
                 "dragging": False, "savesUnsettled": 0, "rescue": False, "reason": "idle"}


def lab(auto: bool) -> dict[str, Any]:
    return {"hidden": False, "text": "上次儲存：12:00" + ("（自動）" if auto else "")}


def sv(at, trigger="auto", outcome="saved", sha="a", target="original", status=204, with_token=True, copy_name=None):
    rec: dict[str, Any] = {"at": at, "name": NAME, "bytes": 10, "trigger": trigger, "sha256": sha, "outcome": outcome,
                           "settled": True, "attempts": [{"at": at + 20, "respondedAt": at + 120, "status": status,
                                                          "withToken": with_token, "ifMatch": '"v"'}]}
    if target:
        rec["target"] = target
    if trigger == "auto":
        rec["conditions"] = dict(OK_CONDITIONS)
    if copy_name:
        rec["conflictCopy"] = {"name": copy_name, "url": "u", "status": 201, "etag": '"cv"', "respondedAt": at + 220}
    return rec


def sn(saves, label=None, title=NAME, notice="", bar=True, dl=True, toasts=0, allowed=None, now=None, **host_extra):
    host = {"started": T0, "done": True, "stranded": None, "lock": {"state": "held"},
            "steps": [{"step": "opened", "state": {"state": "ready", "doc": NAME}}],
            "saves": copy.deepcopy(saves), **host_extra}
    return {"now": now or T0 + 400_000, "host": host, "label": label, "title": title, "notice": notice,
            "barHidden": bar, "downloadHidden": dl, "doc": NAME, "toasts": toasts, "allowed": allowed}


def base(arm, kind, **open_host):
    return {"arm": arm, "spec": PLAN[arm][0], "browser": kind,
            "opened": {"steps": [{"step": "opened", "at": 1, "state": {"state": "ready", "doc": NAME}}]},
            "reset": {"fileId": 7}, "afterOpen": {"lock": "1", "token": "opaquelocktoken:t"},
            "snaps": {"open": sn([], **open_host)}, "serverBefore": {"sha256": ORIG},
            "page": {"keys": [], "revisions": [], "visibility": [], "toasts": []}}


def synth(arm: str, kind: str) -> dict[str, Any]:
    r, K = base(arm, kind, **({"lock": {"state": "refused"}} if arm == "as3" else {})), T0 + 5_000
    ok_edit = {"revision": "4", "latency": "插入 9 ms"}
    if arm in ("as2-key", "as2-toolbar", "as2h"):
        ref, delay = K, 30_800
        if arm == "as2-toolbar":
            r["edit1"] = {"caret": {"revision": "3"}, "acted": {"revision": "4", "latency": "設定標題 12 ms"}}
            # The real shape: the same value rewritten before and after the change, one rewrite after the
            # auto began (shakedown 2026-10-12T054605).
            r["page"]["revisions"] = [{"t": K, "revision": "3"}, {"t": K + 50, "revision": "3"},
                                      {"t": K + 300, "revision": "4"}, {"t": K + 600, "revision": "4"},
                                      {"t": K + 300 + 31_100, "revision": "4"}]
            ref = K + 300
            r["fileAfter"] = {"sha256": "f", "heading": True, "texts": ["E1-MULTI-START alpha"]}
        else:
            r["page"]["keys"] = [{"t": K, "key": KEY, "repeat": False}]
            r["fileAfter"] = {"sha256": "f", "heading": False, "texts": ["E1-MULTI-START alpha", "zE1-MULTI-END omega"]}
        if arm == "as2h":
            r["page"]["visibility"] = [{"t": K + 1_500, "state": "hidden"}, {"t": K + 7_000, "state": "visible"}]
            ref, delay = K + 1_500, 1_200
        r["snaps"]["end"] = sn([sv(ref + delay - T0)], label=lab(True), allowed=HMS)
    elif arm == "as2c":
        keys = [K + 2_000 * i for i in range(KEYING_KEYS)]
        extra = keys[-1] + 6_000
        r["keying"] = {"n": KEYING_KEYS, "gapS": KEYING_GAP}
        r["page"]["keys"] = [{"t": t, "key": KEY} for t in keys + [extra]]
        r["snaps"]["end"] = sn([sv(keys[-1] + 3_700 - T0)], now=extra + 12_000)
    elif arm in ("as3", "as4a"):
        a1 = sv(40_000, outcome="copy", sha="s1", target=COPY, status=412, with_token=False, copy_name=COPY)
        a2 = sv(100_000, sha="s2", target=COPY, with_token=False)
        note = f"檔案正被 lcprobe 鎖定編輯：你的存檔會另存副本。你的內容存在「{COPY}」，{COPY_SAYS}。"
        r["phases"] = {
            "1": {"wait": {"settled": 1}, "snap": sn([a1], title=COPY, notice=note, bar=False),
                  "copies": [{"name": COPY, "sha256": "s1", "holdsMarker": False}]},
            "2": {"wait": {"settled": 2}, "snap": sn([a1, a2], title=COPY, notice=note, bar=False),
                  "copies": [{"name": COPY, "sha256": "s2", "holdsMarker": True}]}}
        r["snaps"]["end"] = copy.deepcopy(r["phases"]["2"]["snap"])
        if arm == "as3":
            r.update(foreignLock=200, serverAfter={"sha256": ORIG})
        else:
            r.update(ownerUnlock=200, intruded=204, serverAfter={"sha256": INTRUDER})
    elif arm == "as4b":
        pre = sv(10_000, "manual", sha="p")
        s1 = sv(20_000, "manual", "copy", "s1", COPY, 412, True, COPY)
        s2 = sv(30_000, "manual", "saved", "s2", COPY, 204, False)
        saved = {"at": s1["conflictCopy"]["respondedAt"], "trigger": "manual", "target": COPY}
        r["pre"] = ok_edit
        r["snaps"].update(afterPre=sn([pre], label=lab(False), allowed=HMS),
                          afterCopy=sn([pre, s1], label=lab(False), allowed=HMS, title=COPY, lastSaved=saved),
                          end=sn([pre, s1, s2], label=lab(False), allowed=HMS, title=COPY, lastSaved=saved))
        r.update(copiesAfter=[{"name": COPY, "sha256": "s2", "holdsMarker": True}], serverAfter={"sha256": INTRUDER},
                 ownerUnlock=200, intruded=204)
    elif arm == "as4c":
        s1 = sv(10_000, "manual", "copy", "s1", COPY, 412, True, COPY)
        s2 = sv(20_000, "manual", "saved", "s2", COPY, 204, False)
        r["snaps"]["end"] = sn([s1, s2], title=COPY)
        r.update(refusedUnlock=423, lockAfterSave={"lock": "1", "token": "opaquelocktoken:t"},
                 copiesAfter=[{"name": COPY, "sha256": "s2", "holdsMarker": True}], serverAfter={"sha256": ORIG})
        if kind == "chrome":
            url = "https://nc.test/remote.php/dav/files/admin/"
            r["davRequests"] = [
                {"method": "PUT", "url": url + urllib.parse.quote(NAME), "ifMatch": '"v"', "if": "(<opaquelocktoken:t>)"},
                {"method": "PUT", "url": url + urllib.parse.quote(COPY), "ifMatch": None, "if": None},
                {"method": "PUT", "url": url + urllib.parse.quote(COPY), "ifMatch": '"cv"', "if": None}]
    elif arm in ("as5", "as5-held"):
        held = arm == "as5-held"
        sent, busy = (HELD * HELD_REPEATS if held else LETTERS), K + 30_100
        r.update(docSha256=ui.DOC_SHA256 or "d" * 64, busySeen={"state": "busy", "now": busy}, sent=sent,
                 server={"sha256": "a2", "bytes": 1, "received": sent[:33] if held else sent})
        r["page"]["keys"] = [{"t": K, "key": KEY}] + [{"t": busy + 100 + 125 * i, "key": sent[0]} for i in range(len(sent))]
        r["page"]["toasts"] = ([{"t": busy + 500, "text": HELD_TOAST + "：打得比引擎處理得快，請檢查最後打的字"}] if held else [])
        r["snaps"]["end"] = sn([sv(K + 30_700 - T0, sha="a1"), sv(busy + 6_000 + 30_700 - T0, sha="a2")])
    elif arm == "as6b":
        a = sv(40_000, outcome="copy", sha="s1", target=COPY, status=412, with_token=False, copy_name=COPY)
        r.update(ownerUnlock=200, intruded=204, copiesAfter=[{"name": COPY, "sha256": "s1", "holdsMarker": False}])
        r["snaps"]["end"] = sn([a], title=COPY, bar=False)
        r["leaves"] = {"leave": {"dialog": None, "pathAfter": "/apps/files/", "record": [
            {"what": "installed", "at": 1},
            {"what": "fired", "lastGuard": None, "guards": None, "pending": "0", "handlerProperty": False}]}}
    elif arm == "as7":
        x1, x2 = (sv(at, outcome="stranded", sha=sha, status="network", target=None) for at, sha in ((40_000, "x1"), (100_000, "x2")))
        x3 = sv(160_000, sha="x3")
        strand = lambda sha: {"sha256": sha, "bytes": 1, "at": 1}  # noqa: E731
        r["phases"] = {
            "1": {"wait": {}, "snap": sn([x1], notice=STRANDED, bar=False, dl=False, stranded=strand("x1")), "copies": []},
            "2": {"wait": {}, "snap": sn([x1, x2], notice=STRANDED, bar=False, dl=False, stranded=strand("x2")), "copies": []},
            "3": {"wait": {}, "snap": sn([x1, x2, x3], label=lab(True), allowed=HMS,
                                         unstranded={"how": "saved", "sha256": "x2", "at": 1}), "copies": []}}
        r.update(edit1={"caret": {"revision": "3"}, "acted": {"revision": "4", "latency": "設定標題 12 ms"}},
                 inserted=ok_edit, back=ok_edit, serverAfter={"sha256": "x3"})
        r["snaps"]["end"] = copy.deepcopy(r["phases"]["3"]["snap"])
    if arm in ("as3", "as4a", "as4b", "as4c", "as6b"):
        r["edit1"] = {"caret": {"revision": "3"}, "acted": {"revision": "4", "latency": "設定標題 12 ms"}}
    if arm in ("as3", "as4a", "as4b", "as4c"):
        r["inserted"] = ok_edit
    r["host"] = r["snaps"]["end"]["host"]
    return r


def synthetic_report() -> dict[str, Any]:
    runs = [synth(arm, browser) for arm, (_, browsers, count) in PLAN.items() for browser in browsers for _ in range(count)]
    return {"label": "counted", "runs": runs, "original": {"sha256": ORIG}, "intruder": {"sha256": INTRUDER},
            "static": {"page": {"dist": PAGE_SHA256, "web": PAGE_SHA256, "served": PAGE_SHA256},
                       "session": {"tree": SESSION_SHA256, "dist": SESSION_SHA256, "served": SESSION_SHA256},
                       "hostVersion": HOST_VERSION, "testStatic": 0},
            "hostRepo": f"{HOST_COMMIT}def Host {HOST_VERSION}", "hostDirty": ""}


def selftest() -> int:
    global PAGE_SHA256, SESSION_SHA256, HOST_VERSION, HOST_COMMIT
    PAGE_SHA256, SESSION_SHA256, HOST_VERSION, HOST_COMMIT = "p" * 64, "s" * 64, "0.2.13", "abc1234"
    report = synthetic_report()
    failures = 0

    def check(label: str, ok: bool, detail: Any = "") -> None:
        nonlocal failures
        failures += not ok
        print(f"  {'ok   ' if ok else 'FAIL '} {label}" + ("" if ok else f"  -> {detail}"))

    clean = score(report, strict=True)
    check("the clean synthetic report scores AUTOSAVE HOLDS", clean["verdict"] == "AUTOSAVE HOLDS", report_lines(clean))
    print(f"  ({len(report['runs'])} runs, {clean['as1'][2]} auto records read)")
    print("red cases (each on a clean run of its own arm):")
    failures += run_red_cases(report)
    covered = {case[1] for case in RED_CASES if case[5] == "run"}
    check("every arm in PLAN has at least one red case (the list is derived from PLAN)",
          covered >= set(PLAN), sorted(set(PLAN) - covered))
    print("report-level cases:")
    zero_autos = copy.deepcopy(report)
    for run in zero_autos["runs"]:
        for host in each_host(run):
            host["saves"] = [s for s in host["saves"] if s.get("trigger") != "auto"]
    result = score(zero_autos, strict=True)
    check("zero auto records: AS-1 is NOT_ESTABLISHED and the verdict is not HOLDS",
          result["as1"][0] == NE and result["verdict"] != "AUTOSAVE HOLDS", result["as1"][:1])
    short = copy.deepcopy(report)
    short["runs"].remove(next(r for r in short["runs"] if r["arm"] == "as2-key" and r["browser"] == "chrome"))
    result = score(short, strict=True)
    check("one run short of the plan: AUTOSAVE DOES NOT HOLD", result["verdict"] == "AUTOSAVE DOES NOT HOLD"
          and any("as2-key/chrome" in p for p in result["problems"]), result["problems"])
    unbound = copy.deepcopy(report)
    unbound["static"]["page"]["served"] = "0" * 64
    check("the host serves another page: AUTOSAVE DOES NOT HOLD",
          score(unbound, strict=True)["verdict"] == "AUTOSAVE DOES NOT HOLD")
    dirty = copy.deepcopy(report)
    dirty["hostDirty"] = " M js/litecore-editor.js"
    check("host repo dirty: AUTOSAVE DOES NOT HOLD", score(dirty, strict=True)["verdict"] == "AUTOSAVE DOES NOT HOLD")
    no_hidden = copy.deepcopy(report)
    for run in no_hidden["runs"]:
        if run["arm"] == "as2h":
            run["page"]["visibility"] = []
    result = score(no_hidden, strict=True)
    check("as2h NOT_ESTABLISHED in both browsers: AUTOSAVE NOT ESTABLISHED (not HOLDS, not DOES NOT HOLD)",
          result["verdict"] == "AUTOSAVE NOT ESTABLISHED", result["verdict"])
    no_loss = copy.deepcopy(report)
    for run in no_loss["runs"]:
        if run["arm"] == "as5-held" and run["browser"] == "firefox":
            run["server"]["received"] = run["sent"]
    result = score(no_loss, strict=True)
    check("as5-held lost no key in any Firefox run: that cell NOT_ESTABLISHED, verdict AUTOSAVE NOT ESTABLISHED",
          result["cells"]["as5-held/firefox"][NE] == 3 and result["verdict"] == "AUTOSAVE NOT ESTABLISHED",
          (result["cells"]["as5-held/firefox"], result["verdict"]))
    fatal = copy.deepcopy(report)
    fatal["runs"][0]["fatal"] = "Traceback\nRuntimeError: boom"
    check("a fatal run is a failed cell", score(fatal, strict=True)["cells"]["as2-key/chrome"][FAIL] == 1)
    broken = copy.deepcopy(report)
    del next(r for r in broken["runs"] if r["arm"] == "as3")["phases"]
    check("a record missing its fields is red, not a crash",
          score_run(next(r for r in broken["runs"] if r["arm"] == "as3"), broken)[0] == FAIL)
    saved = (PAGE_SHA256, SESSION_SHA256, HOST_VERSION, HOST_COMMIT)
    PAGE_SHA256 = None
    check("unpinned constants: a counted report cannot HOLD",
          score(report, strict=True)["verdict"] == "AUTOSAVE DOES NOT HOLD")
    PAGE_SHA256 = saved[0]
    print(f"selftest: {failures} failure(s)")
    return 1 if failures else 0


# ------------------------------------------------------------------ main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--label", choices=("shakedown", "counted"))
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--repeats", type=int, default=None, help="shakedown only")
    parser.add_argument("--arms", default=",".join(PLAN), help="shakedown only: a counted run runs the plan")
    parser.add_argument("--score", type=Path)
    parser.add_argument("--red-cases", type=Path, metavar="REPORT",
                        help="each mutation must turn its own arm red, on clean runs of a shakedown REPORT")
    parser.add_argument("--selftest", action="store_true", help="offline: a synthetic report, the scorer and every red case")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if args.score:
        report = json.loads(args.score.read_text())
        result = score(report, strict=report.get("label") == "counted")
        print("\n".join(report_lines(result)))
        return 0 if result["verdict"] in ("AUTOSAVE HOLDS", "clean") else 1
    if args.red_cases:
        failures = run_red_cases(json.loads(args.red_cases.read_text()))
        print(f"red cases: {failures} not red or missing")
        return 1 if failures else 0
    if not args.label:
        parser.error("--label, --score, --red-cases or --selftest")
    counted = args.label == "counted"
    arms = list(PLAN) if counted else args.arms.split(",")
    if [a for a in arms if a not in PLAN]:
        parser.error(f"unknown arm(s): {[a for a in arms if a not in PLAN]}")
    if counted and any(v is None for v in (PAGE_SHA256, SESSION_SHA256, HOST_VERSION, HOST_COMMIT)):
        print("refusing a counted run: PAGE_SHA256 / SESSION_SHA256 / HOST_VERSION / HOST_COMMIT are not written down yet")
        return 2
    static, binding = ph.static_facts(args.ddev_root)
    if counted:
        static.update(static_target(PROJECT))   # P6's reading of the named reds, not exit 0 (SPEC-M3-K-0.2.44 append 1, H2)
        refuse = binding_problems({"static": static, "hostRepo": binding["hostRepo"], "hostDirty": binding["hostDirty"]})
        if refuse:
            print("refusing a counted run: " + "; ".join(refuse))
            return 2
    instance = Instance(args.ddev_root)
    log: list[dict[str, Any]] = []
    server = Server(instance, log)
    report: dict[str, Any] = {
        "runner": Path(__file__).name, "runnerSha256": sha256_file(Path(__file__)), "label": args.label,
        "spec": "specs/SPEC-M3-autosave.md", "startedAt": utc_now(), "static": static,
        **binding_fields(binding), "baseUrl": instance.base,
        "original": {"source": str(FIXTURE.relative_to(DIST)), "sha256": sha256_file(FIXTURE)},
        "intruder": {"sha256": sha256_file(SAMPLE)}, "runs": [],
    }
    out = EVIDENCE / ("runs" if counted else "shakedown") / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        report["setup"] = server.setup()
        with tempfile.TemporaryDirectory(prefix="m3-autosave-", dir=PROJECT / "build") as scratch:
            for arm in arms:
                _, allowed, count = PLAN[arm]
                for browser in args.browsers.split(","):
                    if browser not in allowed:
                        continue
                    for index in range(count if counted or args.repeats is None else args.repeats):
                        print(f"{arm} {browser} #{index + 1}", flush=True)
                        run = run_arm(arm, browser, server, Path(scratch))
                        report["runs"].append(run)
                        status, problems = score_run(run, report)
                        print(f"  {status} {problems if problems else ''}", flush=True)
                        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    finally:
        server.teardown()
        report["completedAt"] = utc_now()
        report["httpLog"] = log
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    result = score(report, strict=counted)
    print(out.relative_to(REPO))
    print("\n".join(report_lines(result)))
    return 0 if result["verdict"] in ("AUTOSAVE HOLDS", "clean") else 1


if __name__ == "__main__":
    sys.exit(main())
