#!/usr/bin/env python3
"""Leaving the editor with an edit that was never saved: is the user asked?  A measurement.

Source reading (2026-09-29): nothing on the page, in the shell or in the host listens for
`beforeunload` on unsaved edits -- the host's only guard is for bytes that could not be saved
anywhere (stranded) or a save in flight (spec S4-S6).  This checks that reading through the product.

Chrome only (the dialog is observed through CDP `Page.javascriptDialogOpening`, as in
check_m3_locks.py's K10), dev instance, RUNS fresh opens per arm:

  control  open, edit, a trusted click (user activation), then the probe itself adds a
           beforeunload listener that asks, and navigates to Files: a dialog MUST open (else the
           instrument cannot see one and the other arm means nothing); dismissed, the page stays.
  unsaved  open, edit, a trusted click, navigate to Files.  Recorded: whether a dialog opened,
           where the tab ended up, and whether the server's file has the edit.

  probe_m3_unsaved_leave.py [--runs 3]

Writes findings/evidence/m3-unsaved-leave/<startedAt>.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_host_entry import clear_lock, conflict_copies, host_record, open_from_files, server_lock  # noqa: E402
from check_m3_locks import LockChrome, edit  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, FIXTURE, NAME, ROUTE, Instance, binding_fields, host_binding  # noqa: E402
from probe_m3_gate0_coep import sha256_file, utc_now, wait_until  # noqa: E402
from r7_support import evaluate  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "findings" / "evidence" / "m3-unsaved-leave"
ASK = ("(() => { addEventListener('beforeunload', (e) => { e.preventDefault(); e.returnValue = ''; },"
       " { once: true }); return true; })()")


def run_arm(arm: str, instance: Instance) -> dict[str, Any]:
    record: dict[str, Any] = {"arm": arm, "lockAtReset": server_lock(instance)}
    if record["lockAtReset"]["lock"] == "1" and record["lockAtReset"]["fileId"]:
        record["staleLockCleared"] = clear_lock(instance, record["lockAtReset"]["fileId"])
    record["reset"] = instance.upload(FIXTURE, NAME)
    record["copiesBefore"] = conflict_copies(instance, remove=True)
    session = LockChrome("cold")
    try:
        open_from_files(session, instance, record)
        wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                            " return v && JSON.parse(v).done; })()", 300)
        edit(session, record)
        record["activation"] = session.real_click("#text")
        if arm == "control":
            record["asked"] = evaluate(session, ASK)
        record["hostBeforeLeave"] = {k: v for k, v in host_record(session).items() if k in ("saves", "stranded", "lock")}
        record["leave"] = session.leave_attempt(instance.base + "/apps/files/")
        if record["leave"]["dialog"]:
            session.call("Page.handleJavaScriptDialog", {"accept": False})
        time.sleep(3)
        record["pathAfter"] = evaluate(session, "(() => location.pathname)()")
        _, body = instance.dav("GET", NAME)
        record["serverAfter"] = {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        record["copiesAfter"] = conflict_copies(instance, remove=True)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        session.close()
    edited = (record.get("smoke") or {})
    before, after = (edited.get("caret") or {}).get("revision"), (edited.get("acted") or {}).get("revision")
    record["summary"] = {
        "edited": bool(before and after and before != after), "dialog": bool((record.get("leave") or {}).get("dialog")),
        "stayed": str(record.get("pathAfter", "")).endswith(ROUTE),
        "serverUnchanged": (record.get("serverAfter") or {}).get("sha256") == record["reset"]["sha256"],
        "saves": len((record.get("hostBeforeLeave") or {}).get("saves") or []), "fatal": bool(record.get("fatal"))}
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    instance = Instance(DEFAULT_DDEV)
    report: dict[str, Any] = {"probe": Path(__file__).name, "probeSha256": sha256_file(Path(__file__)),
                              "startedAt": utc_now(), **binding_fields(host_binding(DEFAULT_DDEV)),
                              "instance": instance.base, "runs": []}
    out = EVIDENCE / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    for index in range(args.runs):
        for arm in ("control", "unsaved"):
            record = run_arm(arm, instance)
            record["index"] = index
            report["runs"].append(record)
            out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
            print(f"  {index} {arm:<8} {record['summary']}", flush=True)
    report["completedAt"] = utc_now()
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
