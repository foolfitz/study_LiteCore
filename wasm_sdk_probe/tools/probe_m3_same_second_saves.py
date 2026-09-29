#!/usr/bin/env python3
"""Can the host's own saves land in one wall-clock second?  A measurement, not a gate.

fable's ruling of 2026-09-29 (D, condition 1): before any host change for
findings 103/104, measure through the real page -- the harness's saves so far
were always >= 1.18 s apart, which is the harness's path, not the user's.
Dev instance, host as it is (0.2.1), both browsers, one editor session each:

  pairs  the save button, then Ctrl+S with no wait; PAIRS times, 1.5 s apart.
  held   Ctrl+S held about a second: keydown every 33 ms for 1 s, the first
         with repeat false and the rest true (what a held key sends; the page
         does not filter event.repeat); HELD trials, each until the queue drains.

Per save, the host's own record (`data-litecore`): when each PUT was sent,
If-Match, status, the ETag it got back.  A same-second pair is two 2xx saves in
a row with the same ETag -- Nextcloud keeps the ETag for a second write in the
same second (finding 103); after such a pair any restore loses the second
write (finding 104).  The version list is read after each phase.

  probe_m3_same_second_saves.py [--browsers chrome,firefox] [--pairs 12] [--held 3]

Writes findings/evidence/m3-same-second/<startedAt>.json and prints a summary.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import tempfile
import time
import traceback
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_host_entry import (  # noqa: E402
    CTRL_S, clear_lock, conflict_copies, host_record, leave_and_watch, open_from_files, server_file,
    server_lock)
from check_m3_skeleton_open import DEFAULT_DDEV, FIXTURE, NAME, Instance, binding_fields, host_binding  # noqa: E402
from probe_m3_gate0_coep import EventChrome, firefox_profile, sha256_file, utc_now, wait_until  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import PRESS  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-same-second"
# Both presses in one evaluation: the button, then Ctrl+S, no wait between.  One
# array expression -- Firefox's evaluate wraps the script as `return <expr>;`,
# so two statements would run only the first (r7_support.evaluate).
PAIR = "[" + PRESS.replace("ARG_ACTION", "save").strip() + ", " + CTRL_S.strip() + "]"
HELD = """(() => { const sink = document.querySelector('#sink'); sink.focus();
  for (let i = 0; i < 30; i++) setTimeout(() => sink.dispatchEvent(new KeyboardEvent('keydown', {
    key: 's', code: 'KeyS', ctrlKey: true, repeat: i > 0, bubbles: true, cancelable: true })), i * 33);
  return true; })()"""
SETTLED = """(() => { const v = document.documentElement.getAttribute('data-litecore');
  const s = v && JSON.parse(v).saves; return s ? [s.length, s.every(x => x.settled === true)] : [0, true]; })()"""


def versions(instance: Instance, fileid: int) -> list[str]:
    """The revisions files_versions lists for the file (their names are mtime seconds)."""
    url = f"{instance.base}/remote.php/dav/versions/admin/versions/{fileid}"
    body = b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:getcontentlength/></d:prop></d:propfind>'
    request = urllib.request.Request(url, data=body, method="PROPFIND",
                                     headers={"Depth": "1", "Content-Type": "application/xml"})
    request.add_header("Authorization", "Basic " + base64.b64encode(f"admin:{instance.password}".encode()).decode())
    with urllib.request.urlopen(request, context=instance.tls, timeout=60) as response:
        text = response.read().decode()
    return sorted(h.rsplit("/", 1)[-1] for h in re.findall(r"<d:href>([^<]+)</d:href>", text)
                  if not h.rstrip("/").endswith(f"/versions/{fileid}"))


def drained(session, count_at_least: int, quiet: float = 3.0, timeout: float = 240) -> list[Any]:
    """Until the host has at least `count_at_least` saves, all settled, and no
    new one for `quiet` seconds."""
    deadline, last, since = time.monotonic() + timeout, None, time.monotonic()
    while time.monotonic() < deadline:
        seen = evaluate(session, SETTLED)
        if seen != last:
            last, since = seen, time.monotonic()
        elif isinstance(seen, list) and seen[0] >= count_at_least and seen[1] and time.monotonic() - since >= quiet:
            return seen
        time.sleep(0.25)
    return [{"timedOut": True, "last": last}]


def run_browser(kind: str, instance: Instance, scratch: Path, pairs: int, held: int) -> dict[str, Any]:
    record: dict[str, Any] = {"browser": kind}
    record["lockAtReset"] = server_lock(instance)
    if record["lockAtReset"]["lock"] == "1" and record["lockAtReset"]["fileId"]:
        record["staleLockCleared"] = clear_lock(instance, record["lockAtReset"]["fileId"])
    record["reset"] = instance.upload(FIXTURE, NAME)
    record["copiesBefore"] = conflict_copies(instance, remove=True)
    fileid = record["reset"]["fileId"]
    # The file keeps its id across resets, so its version list is long; keep
    # the count before and every revision each phase added.
    known = versions(instance, fileid)
    record["versionsBefore"] = {"count": len(known), "last": known[-3:]}
    session = (EventChrome("cold") if kind == "chrome"
               else FirefoxSession("cold", profile_dir=firefox_profile(scratch)))
    record["version"] = session.version
    try:
        open_from_files(session, instance, record)
        raw = wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                                  " return v && JSON.parse(v).done && v; })()", 300)
        record["opened"] = isinstance(raw, str)
        phases = record["phases"] = []
        for index in range(pairs):
            before = evaluate(session, SETTLED)[0]
            phase = {"kind": "pair", "index": index, "savesBefore": before, "sentAt": round(time.time(), 3),
                     "pressed": evaluate(session, PAIR)}
            phase["settled"] = drained(session, before + 2, quiet=1.0)
            phases.append(phase)
            time.sleep(1.5)
        now = versions(instance, fileid)
        record["versionsAddedByPairs"], known = sorted(set(now) - set(known)), now
        for index in range(held):
            before = evaluate(session, SETTLED)[0]
            phase = {"kind": "held", "index": index, "savesBefore": before, "sentAt": round(time.time(), 3),
                     "pressed": evaluate(session, HELD)}
            phase["settled"] = drained(session, before + 1, quiet=3.0)
            phase["drainedAt"] = round(time.time(), 3)
            phases.append(phase)
            time.sleep(1.5)
        record["host"] = host_record(session)
        now = versions(instance, fileid)
        record["versionsAddedByHeld"] = sorted(set(now) - set(known))
        record["serverAfter"] = server_file(instance)
        record["copiesAfter"] = conflict_copies(instance, remove=True)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            record["leave"] = leave_and_watch(session, instance)
        except Exception as error:  # noqa: BLE001
            record["leave"] = f"{type(error).__name__}: {error}"
        session.close()
    return record


def analyse(record: dict[str, Any]) -> dict[str, Any]:
    """From the host's own save records: each pair of consecutive saves, its
    send-to-send gap, and whether both were 2xx with the same ETag."""
    saves = (record.get("host") or {}).get("saves") or []
    rows = []
    for i, save in enumerate(saves):
        first = (save.get("attempts") or [{}])[0]
        rows.append({"i": i, "sentAt": first.get("at"), "status": save.get("status"), "ifMatch": save.get("ifMatch"),
                     "etag": save.get("etag"), "attempts": len(save.get("attempts") or [])})
    phase_of = {}
    for phase in record.get("phases") or []:
        count = (phase.get("settled") or [0])[0]
        for i in range(phase.get("savesBefore", 0), count if isinstance(count, int) else 0):
            phase_of[i] = f"{phase['kind']}{phase['index']}"
    pairs = []
    for a, b in zip(rows, rows[1:]):
        ok = isinstance(a["status"], int) and isinstance(b["status"], int) and a["status"] < 300 and b["status"] < 300
        pairs.append({"saves": [a["i"], b["i"]], "phase": [phase_of.get(a["i"]), phase_of.get(b["i"])],
                      "gapMs": (b["sentAt"] - a["sentAt"]) if a["sentAt"] is not None and b["sentAt"] is not None else None,
                      "bothOk": ok, "sameEtag": ok and a["etag"] is not None and a["etag"] == b["etag"]})
    held = []
    for phase in record.get("phases") or []:
        if phase["kind"] == "held":
            mine = [r for r in rows if phase_of.get(r["i"]) == f"held{phase['index']}"]
            held.append({"index": phase["index"], "saves": len(mine),
                         "tailSeconds": round((mine[-1]["sentAt"] - mine[0]["sentAt"]) / 1000, 2) if len(mine) > 1 else 0})
    within = [p for p in pairs if p["phase"][0] == p["phase"][1] and p["phase"][0]]
    return {"saves": len(rows), "statuses": sorted({str(r["status"]) for r in rows}),
            "withinPhasePairs": len(within), "sameEtagPairs": sum(p["sameEtag"] for p in within),
            "gapsMs": sorted(p["gapMs"] for p in within if p["gapMs"] is not None),
            "held": held, "pairs": pairs, "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--pairs", type=int, default=12)
    parser.add_argument("--held", type=int, default=3)
    args = parser.parse_args()
    instance = Instance(DEFAULT_DDEV)
    report: dict[str, Any] = {"probe": Path(__file__).name, "probeSha256": sha256_file(Path(__file__)),
                              "startedAt": utc_now(), "ruling": "findings/evidence/m3-same-second/ruling-2026-09-29-fable-d.md",
                              **binding_fields(host_binding(DEFAULT_DDEV)), "instance": instance.base,
                              "pairs": args.pairs, "heldTrials": args.held, "browsers": {}}
    out = EVIDENCE / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m3-same-second-", dir=PROJECT / "build") as scratch:
        for kind in args.browsers.split(","):
            print(f"{kind} …", flush=True)
            record = run_browser(kind, instance, Path(scratch), args.pairs, args.held)
            record["analysis"] = analyse(record)
            report["browsers"][kind] = record
            out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
            a = record["analysis"]
            print(f"  saves {a['saves']} statuses {a['statuses']} same-ETag pairs {a['sameEtagPairs']}/"
                  f"{a['withinPhasePairs']} gaps(ms) min {a['gapsMs'][:1]} max {a['gapsMs'][-1:]} held {a['held']}"
                  + (" FATAL" if record.get("fatal") else ""), flush=True)
    report["completedAt"] = utc_now()
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
