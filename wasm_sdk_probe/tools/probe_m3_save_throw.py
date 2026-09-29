#!/usr/bin/env python3
"""M3 page honesty, review 2026-09-29 (implementation) BLOCKING 1 -- a save
whose lock dies while its PUT is on the wire.

Read from the host source (js/litecore-editor.js, 0.2.3): `put()` records
`withToken: true` and sends `If: (token)`; while that PUT is in flight the 60 s
`refreshLock()` can be answered LOST and `loseLock()` sets `token = null`; the
PUT then comes back 412 and `saveOnce` calls `tokenOnServer(token)` with null,
which throws a TypeError.  `save()` has no catch, so the save rejects with no
copy and nothing stranded; the page has already marked the session clean and
settles the save, so leaving is not asked about.

This probe makes the race deterministic (Chrome, CDP Fetch): open, edit, press
save; hold the document's PUT; delete the lock row behind the host's back
(`oc_files_lock`, as "removed elsewhere"); let every other request through,
including the host's LOCK refresh, until the host records its lock lost by that
refresh; then release the PUT.  Record how the save ended, where the bytes
went (original, a copy, stranded in the page), and whether leaving asks.

The verdict per run: the bytes the page sent are on the server (the original
or a copy), or the host stranded them and guards the leave -- else LOST.

    probe_m3_save_throw.py [--repeats 1]
Report: findings/evidence/m3-page-honesty/save-throw/<UTC>.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_host_entry import host_record  # noqa: E402
from check_m3_locks import (  # noqa: E402
    BAR, LockChrome, Server, edit, login, open_from_files)
from check_m3_skeleton_open import DEFAULT_DDEV, NAME, Instance, host_binding, product_state  # noqa: E402
from probe_m3_gate0_coep import sha256_file, utc_now  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import PRESS  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-page-honesty" / "save-throw"


class HoldChrome(LockChrome):
    KEEP = LockChrome.KEEP | {"Fetch.requestPaused"}


def pump(session: HoldChrome, held: dict[str, Any], until, timeout: float, log: list[dict[str, Any]]) -> Any:
    """Let every paused request through except the first PUT, which is kept in
    `held`; return `until()`'s first truthy value, or None at the timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pending = [e for e in session.events if e.get("method") == "Fetch.requestPaused"]
        session.events[:] = [e for e in session.events if e.get("method") != "Fetch.requestPaused"]
        try:
            message = json.loads(session.websocket.recv(timeout=0.2))
            if message.get("method") == "Fetch.requestPaused":
                pending.append(message)
            elif message.get("method") in session.KEEP:
                session.events.append(message)
        except TimeoutError:
            pass
        for event in pending:
            request = event["params"]["request"]
            entry = {"t": round(time.monotonic(), 2), "method": request["method"], "url": request["url"][-60:]}
            if request["method"] == "PUT" and "id" not in held:
                held["id"] = event["params"]["requestId"]
                entry["held"] = True
            else:
                session.next_id += 1
                session.websocket.send(json.dumps({"id": session.next_id, "method": "Fetch.continueRequest",
                                                   "params": {"requestId": event["params"]["requestId"]}}))
            log.append(entry)
        value = until()
        if value:
            return value
    return None


def one_run(server: Server, index: int) -> dict[str, Any]:
    base = server.instance.base
    record: dict[str, Any] = {"run": index, "startedAt": utc_now()}
    record["clearedLocks"] = server.clear_locks()
    record["reset"] = {"upload": server.upload(server.admin, NAME), "fileId": server.fileid(server.admin, NAME)}
    server.copies(server.admin, "", NAME[:-4], remove=True)
    record["serverBefore"] = server.content(server.admin, NAME)
    session = HoldChrome("cold")
    record["version"] = getattr(session, "version", None)
    requests: list[dict[str, Any]] = []
    record["requests"] = requests
    try:
        login(session, base, "admin", server.instance.password)
        open_from_files(session, base, "", NAME, record)
        record["afterOpen"] = server.props(server.admin, NAME)
        edit(session, record)
        session.call("Fetch.enable", {"patterns": [{"urlPattern": "*/remote.php/dav/files/*", "requestStage": "Request"}]})
        held: dict[str, Any] = {}
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        record["putHeld"] = pump(session, held, lambda: held.get("id"), 60, requests) is not None
        if not record["putHeld"]:
            raise RuntimeError("the save's PUT never came")
        record["heldAt"] = host_record(session)
        # The lock dies behind the host's back while the PUT waits.
        record["lockRowsDeleted"] = server.clear_locks()
        record["lockAfterDelete"] = server.props(server.admin, NAME)

        def lost_by_refresh():
            lock = (host_record(session).get("lock") or {})
            return lock if lock.get("state") == "lost" else None
        record["lostLock"] = pump(session, held, lost_by_refresh, 100, requests)
        if not record["lostLock"]:
            raise RuntimeError("the host's refresh never lost the lock")
        session.call("Fetch.continueRequest", {"requestId": held["id"]})
        record["releasedPut"] = True
        pump(session, held, lambda: True, 0.5, requests)
        session.call("Fetch.disable")
        record["settled"] = pump(session, held, lambda: all(
            s.get("settled") for s in (host_record(session).get("saves") or [{}])), 60, requests)
        time.sleep(1.5)
        record["host"] = host_record(session)
        record["page"] = product_state(session)
        record["bar"] = evaluate(session, BAR)
        record["serverAfterSave"] = server.content(server.admin, NAME)
        record["copiesAfterSave"] = server.copies(server.admin, "", NAME[:-4], remove=False)
        record["activation"] = session.real_click("#text")
        record["leave"] = session.leave_attempt(base + "/apps/files/")
        if record["leave"]["dialog"]:
            session.call("Page.handleJavaScriptDialog", {"accept": False})
        time.sleep(1.5)
        record["pathAfterLeave"] = evaluate(session, "(() => location.pathname)()")
    except Exception:  # noqa: BLE001 -- recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass
        record["serverAtEnd"] = server.content(server.admin, NAME)
        record["copiesAtEnd"] = server.copies(server.admin, "", NAME[:-4], remove=True)
        record["clearedAtEnd"] = server.clear_locks()
        record["completedAt"] = utc_now()
    record["verdict"] = verdict(record)
    return record


def verdict(record: dict[str, Any]) -> dict[str, Any]:
    if "fatal" in record:
        return {"outcome": "NO RUN", "why": record["fatal"].strip().splitlines()[-1]}
    saves = (record.get("host") or {}).get("saves") or []
    sent = saves[0].get("sha256") if saves else None
    on_original = (record.get("serverAfterSave") or {}).get("sha256") == sent
    in_copy = any(c.get("sha256") == sent for c in record.get("copiesAfterSave") or [])
    stranded = ((record.get("host") or {}).get("stranded") or {}).get("sha256") == sent
    guarded = bool((record.get("leave") or {}).get("dialog"))
    kept = on_original or in_copy or (stranded and guarded)
    return {"outcome": "KEPT" if kept else "LOST", "onOriginal": on_original, "inCopy": in_copy,
            "stranded": stranded, "leaveAsked": guarded,
            "attempts": [(a.get("status"), a.get("withToken")) for s in saves for a in s.get("attempts") or []],
            "tokenOnServer": saves[0].get("tokenOnServer") if saves else None,
            "lostBy": (record.get("lostLock") or {}).get("lostBy"),
            "pageLatency": (record.get("page") or {}).get("latency"), "pageToast": (record.get("page") or {}).get("toast")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    instance = Instance(DEFAULT_DDEV)
    log: list[dict[str, Any]] = []
    server = Server(instance, log)
    binding = host_binding(DEFAULT_DDEV)
    report: dict[str, Any] = {"probe": Path(__file__).name, "probeSha256": sha256_file(Path(__file__)),
                              "startedAt": utc_now(), "host": {k: binding.get(k) for k in ("hostRepo", "hostDirty")},
                              "hostScriptSha256": sha256_file(Path(binding["appDir"]) / "js" / "litecore-editor.js"),
                              "runs": []}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"{report['startedAt'].replace(':', '')}.json"
    try:
        server.setup()
        for index in range(args.repeats):
            run = one_run(server, index + 1)
            report["runs"].append(run)
            print(f"run {index + 1}: {json.dumps(run['verdict'], ensure_ascii=False)}", flush=True)
            out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    finally:
        server.teardown()
        report["completedAt"] = utc_now()
        report["httpLog"] = log
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
