#!/usr/bin/env python3
"""SPEC-M3-autosave §4 M3: after a conflict, what do two saves leave on the server?

Not a counted runner; no product byte is touched (host 0.2.12, page 8909564e).
The premise it tests is §2.1's inference, read from the host's source and never
measured: after a save is written to a copy, the host keeps the ETag and hash it
had (litecore-editor.js saveOnce), so every later save meets the same conflict and
writes one more copy.  The owner chose O1 = B (§8.2: after a copy, the session
saves to that copy); this probe's result is the red case B has to turn green.

One browser session per round, the locks runner's K6 shape (check_m3_locks.py
"broken-then-written"): open the file from Files (the host takes its token lock),
then the owner removes that lock through files_lock's OCS route and writes other
bytes over the file -- our token is dead and our ETag stale.  Then:

  edit 1  set-paragraph-heading at (0.35, 0.28) of the paper   -> save 1 (button)
  edit 2  insert the text MARKER through the insert field     -> save 2 (button)

and the server is read: the original's hash, every copy next to it (name, hash,
whether its content.xml holds MARKER), the host's record of both saves, the
host bar and the title bar.

Prediction (written before the first run, from litecore-editor.js 0.2.12):
  save 1  attempts (412, with token), then (412, without token)   -> outcome copy
  save 2  attempts (412, without token)                            -> outcome copy
  2 copies; the first's hash is save 1's bytes, the second holds MARKER;
  the original keeps the intruder's bytes; the host bar shows the lost-lock
  notice, not where the content went.

  probe_autosave_m3.py --out DIR [--browsers chrome,firefox] [--rounds 2]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_host_entry import host_record  # noqa: E402
from check_m3_locks import (  # noqa: E402
    BAR, ODT, LockChrome, Server, edit, insert_marker, login, open_from_files, save)
from check_m3_host_entry import MARKER  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, Instance, product_state  # noqa: E402
from probe_m3_gate0_coep import firefox_profile, utc_now  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
PROBE_NAME = "probe-autosave-m3.odt"
TITLE = """(() => { const t = document.querySelector('#litecore-host-title'),
  u = document.querySelector('#litecore-host-unsaved');
  return { title: t && t.textContent, unsavedShown: !!u && !u.hidden }; })()"""


def copy_facts(server: Server, name: str) -> dict[str, Any]:
    status, raw = server.instance.dav("GET", name)
    out: dict[str, Any] = {"name": name, "status": status, "bytes": len(raw),
                           "sha256": hashlib.sha256(raw).hexdigest()}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            out["holdsMarker"] = MARKER in archive.read("content.xml").decode("utf-8", "replace")
    except (zipfile.BadZipFile, KeyError) as error:
        out["holdsMarker"] = None
        out["zipError"] = str(error)
    return out


def run_round(kind: str, server: Server, scratch: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"browser": kind, "startedAt": utc_now()}
    stem = PROBE_NAME[:-4]
    record["clearedLocks"] = server.clear_locks()
    record["copiesRemovedBefore"] = server.copies(server.admin, "", stem, remove=True)
    record["upload"] = server.upload(server.admin, PROBE_NAME)
    record["fileId"] = server.fileid(server.admin, PROBE_NAME)
    record["original"] = server.content(server.admin, PROBE_NAME)
    session = (LockChrome("cold") if kind == "chrome"
               else FirefoxSession("cold", profile_dir=firefox_profile(scratch / f"ff-{time.monotonic_ns()}")))
    record["version"] = getattr(session, "version", None)
    try:
        record["login"] = login(session, server.instance.base, "admin", server.instance.password)
        open_from_files(session, server.instance.base, "", PROBE_NAME, record)
        record["afterOpen"] = server.props(server.admin, PROBE_NAME)
        record["ownerUnlock"] = server.admin.call(
            "owner unlock", "DELETE", f"/ocs/v2.php/apps/files_lock/lock/{record['fileId']}",
            form={"lockType": 0})["status"]
        record["intruded"] = server.put(server.admin, PROBE_NAME, server.intruder)
        record["afterIntrusion"] = server.content(server.admin, PROBE_NAME)
        edit(session, record, "edit1")
        save(session, record, 1)
        record["bar1"] = evaluate(session, BAR)
        record["title1"] = evaluate(session, TITLE)
        insert_marker(session, record)
        save(session, record, 2)
        time.sleep(1.0)
        record["bar2"] = evaluate(session, BAR)
        record["title2"] = evaluate(session, TITLE)
        record["state"] = product_state(session)
        record["host"] = host_record(session)
        record["serverAfter"] = server.content(server.admin, PROBE_NAME)
        listed = server.copies(server.admin, "", stem, remove=False)
        record["copies"] = [copy_facts(server, c["name"]) for c in listed]
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            record.setdefault("closeError", traceback.format_exc())
        record["copiesRemovedAfter"] = [c["name"] for c in server.copies(server.admin, "", stem, remove=True)]
        record["clearedLocksAfter"] = server.clear_locks()
        record["completedAt"] = utc_now()
    saves = (record.get("host") or {}).get("saves") or []
    record["summary"] = {
        "attempts": [[(a.get("status"), a.get("withToken")) for a in s.get("attempts") or []] for s in saves],
        "outcomes": [s.get("outcome") for s in saves],
        "copyNames": [(s.get("conflictCopy") or {}).get("name") for s in saves],
        "copies": len(record.get("copies") or []),
        "copyShaIsSave": [c.get("sha256") == (saves[i].get("sha256") if i < len(saves) else None)
                          for i, c in enumerate(record.get("copies") or [])],
        "copyHoldsMarker": [c.get("holdsMarker") for c in record.get("copies") or []],
        "originalIsIntruder": (record.get("serverAfter") or {}).get("sha256") == hashlib.sha256(server.intruder).hexdigest(),
        "notice2": (record.get("bar2") or {}).get("notice"),
    }
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--rounds", type=int, default=2)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    log: list[dict[str, Any]] = []
    server = Server(Instance(DEFAULT_DDEV), log)
    report: dict[str, Any] = {"probe": "probe_autosave_m3.py", "startedAt": utc_now(),
                              "intruderSha256": hashlib.sha256(server.intruder).hexdigest(),
                              "fixtureSha256": hashlib.sha256(server.fixture).hexdigest(), "runs": []}
    try:
        with tempfile.TemporaryDirectory(prefix="m3-autosave-", dir=PROJECT / "build") as scratch:
            for _ in range(args.rounds):
                for kind in args.browsers.split(","):
                    run = run_round(kind, server, Path(scratch))
                    report["runs"].append(run)
                    (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
                    print(kind, "fatal" if run.get("fatal") else json.dumps(run["summary"], ensure_ascii=False),
                          flush=True)
    finally:
        report["completedAt"] = utc_now()
        report["httpLog"] = log
        (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
