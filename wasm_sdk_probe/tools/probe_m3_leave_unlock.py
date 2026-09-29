#!/usr/bin/env python3
"""M3 asset delivery, shakedown finding -- does leaving the editor release the lock?

The first `check_m3_assets.py` shakedown (Firefox, cache on, new host): the
first open's LOCK 200, then leaving sent no UNLOCK at all (access log), and the
second open's LOCK was 423 -- the page told the user they had the file open
elsewhere and would save to a copy.  Step 0 (old host, cache on, no edit) had
UNLOCKs from both browsers.  Every counted M3 run had the cache off.

Arms: browser x cache (warm|cold) x edit (smoke action or none).  Per run: open
from Files, wait for the host's `done`, record a `pagehide` listener's view
(fired? persisted = went into the back/forward cache?) into localStorage,
optionally do the smoke action, navigate to Files, then poll the server's lock
for 10 s and read the access log for UNLOCKs.  A stale token lock from an
earlier run is released with its own token before the upload, and recorded.

Since host 0.2.3 (SPEC-M3-page-honesty §7.8, condition 9): the page-honesty
leave recorder is installed after the smoke and read after the navigation, so
each run says whether its leave was GUARDED (the host asked, reason `page`) or
not.  On 0.2.3 the edit arm is the guarded leave -- only the pagehide UNLOCK
remains, finding 105's unfixed path -- and the none arm is its unguarded
control.  An edit run without a `page` guard, or a none run with any guard, is
an instrument failure and is not counted.

  probe_m3_leave_unlock.py [--arms firefox:warm:edit,...] [--repeats 2]
  (condition 9: --arms firefox:warm:edit,firefox:warm:none --repeats 12)
Report: findings/evidence/m3-assets/leave-unlock-<UTC>.json
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_assets import open_and_smoke  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, FILES, FIXTURE, NAME, Instance  # noqa: E402
from probe_m3_assets import AccessLog  # noqa: E402
from probe_m3_gate0_coep import (  # noqa: E402
    EventChrome, browser_login, firefox_profile, sha256_file, utc_now, wait_until)
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402
import check_m3_assets  # noqa: E402
from check_m3_page_honesty import READ_RECORD  # noqa: E402
from check_m3_page_honesty import RECORDER as LEAVE_RECORDER  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-assets"
DEFAULT_ARMS = ("firefox:warm:edit,firefox:warm:none,firefox:cold:edit,"
                "chrome:warm:edit,chrome:warm:none")
LOCK_PROPS = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns"><d:prop>'
              b'<nc:lock/><nc:lock-owner-type/><nc:lock-token/><nc:lock-time/></d:prop></d:propfind>')
RECORDER = """(() => { addEventListener('pagehide', (e) => {
  try { localStorage.setItem('lc-pagehide', JSON.stringify({persisted: e.persisted, at: Date.now()})); } catch (x) {}
}); localStorage.removeItem('lc-pagehide'); return true; })()"""


def lock_state(instance: Instance) -> dict[str, Any]:
    _, answer = instance.dav("PROPFIND", NAME, LOCK_PROPS, {"Depth": "0", "Content-Type": "application/xml"})
    text = answer.decode()
    pick = lambda tag: (re.search(rf"<nc:{tag}>([^<]*)</nc:{tag}>", text) or [None, None])[1]  # noqa: E731
    return {"lock": pick("lock"), "type": pick("lock-owner-type"), "token": pick("lock-token"),
            "time": pick("lock-time")}


def release_stale(instance: Instance) -> dict[str, Any] | None:
    state = lock_state(instance)
    if state["lock"] != "1" or not state["token"]:
        return None
    status, _ = instance.dav("UNLOCK", NAME, None, {"Lock-Token": f"<opaquelocktoken:{state['token']}>"})  # PROPFIND gives the bare uuid
    return {"was": state, "unlockStatus": status, "after": lock_state(instance)}


def run(arm: str, instance: Instance, scratch: Path) -> dict[str, Any]:
    kind, cache, edit = arm.split(":")
    record: dict[str, Any] = {"arm": arm, "released": release_stale(instance)}
    record["upload"] = instance.upload(FIXTURE, NAME)
    log = AccessLog(instance)
    if kind == "chrome":
        session = EventChrome(cache)
    else:
        session = FirefoxSession(cache, profile_dir=firefox_profile(scratch / f"ff-{time.monotonic_ns()}"))
    agent = "Chrome" if kind == "chrome" else "Firefox"
    try:
        browser_login(session, instance.base, instance.password)
        if edit == "edit":
            record["open"] = open_and_smoke(session, instance)
        else:
            record["open"] = open_only(session, instance)
        record["hostLock"] = record["open"]["host"].get("lock")
        record["recorder"] = evaluate(session, RECORDER)
        nonce = secrets.token_hex(8)
        record["leaveRecorder"] = evaluate(session, LEAVE_RECORDER.replace("ARG_NONCE", json.dumps(nonce)))
        record["secondsDoneToLeave"] = evaluate(session, check_m3_assets.DONE_TO_LEAVE)
        record["lockBeforeLeave"] = lock_state(instance)
        start = log.offset()
        left = time.monotonic()
        navigate(session, instance.base + FILES, timeout=120)
        record["navigated"] = round(time.monotonic() - left, 2)
        polls = []
        while time.monotonic() - left < 10:
            state = lock_state(instance)
            polls.append({"t": round(time.monotonic() - left, 2), "lock": state["lock"]})
            if state["lock"] != "1":
                break
            time.sleep(0.5)
        record["polls"] = polls
        record["pagehide"] = evaluate(session, "(() => localStorage.getItem('lc-pagehide'))()")
        raw = wait_until(session, READ_RECORD.replace("ARG_NONCE", json.dumps(nonce)), 10)
        record["leftRecord"] = json.loads(raw) if isinstance(raw, str) else {"missing": raw}
        record["unlocks"] = [{k: r[k] for k in ("when", "method", "status")} for r in log.since(start)
                             if agent in r.get("agent", "") and r.get("method") in ("UNLOCK", "LOCK")]
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
    finally:
        session.close()
    return record


def guarded(record: dict[str, Any]) -> list[str] | None:
    """The host's guard reasons at this run's leave, [] for an unguarded leave,
    None when the recorder saw no `fired` (the run says nothing)."""
    entries = record.get("leftRecord") if isinstance(record.get("leftRecord"), list) else []
    fired = [e for e in entries if e.get("what") == "fired"]
    if not fired:
        return None
    return list((fired[-1].get("lastGuard") or {}).get("reasons") or [])


def instrument_ok(record: dict[str, Any]) -> bool:
    """Condition 9: edit = guarded for `page`, none = not guarded."""
    reasons = guarded(record)
    if reasons is None or "fatal" in record:
        return False
    return ("page" in reasons) if record["arm"].endswith(":edit") else reasons == []


def open_only(session, instance: Instance) -> dict[str, Any]:
    navigate(session, instance.base + FILES, timeout=120)
    selector = (f'[data-cy-files-list-row-name={json.dumps(NAME, ensure_ascii=False)}]'
                ' [data-cy-files-list-row-name-link]')
    wait_until(session, f"(() => document.querySelector({json.dumps(selector)}) !== null)()", 60)
    session.click(selector)
    raw = wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore');"
                              " return v && JSON.parse(v).done && v; })()", 300)
    return {"host": json.loads(raw) if isinstance(raw, str) else {"notReported": raw}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arms", default=DEFAULT_ARMS)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    instance = Instance(DEFAULT_DDEV)
    report: dict[str, Any] = {
        "schema": "m3-leave-unlock/1", "startedAt": utc_now(), "probe": sha256_file(Path(__file__)),
        "host": subprocess.run(["git", "log", "-1", "--format=%H %s"], cwd=DEFAULT_DDEV,
                               capture_output=True, text=True).stdout.strip(),
        "hostDirty": subprocess.run(["git", "status", "--short"], cwd=DEFAULT_DDEV,
                                    capture_output=True, text=True).stdout.strip(),
        "controllerSha256": sha256_file(DEFAULT_DDEV / "lib/Controller/EditorController.php"),
        "hostScriptSha256": sha256_file(DEFAULT_DDEV / "js/litecore-editor.js"),
        "runs": []}
    out = EVIDENCE / f"leave-unlock-{report['startedAt'].replace(':', '')}.json"
    with tempfile.TemporaryDirectory(prefix="m3-leave-", dir=PROJECT / "build") as scratch:
        for arm in args.arms.split(","):
            for index in range(args.repeats):
                print(arm, index + 1, flush=True)
                report["runs"].append(run(arm, instance, Path(scratch)))
                out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    report["releasedAtEnd"] = release_stale(instance)
    report["completedAt"] = utc_now()
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(REPO))
    for r in report["runs"]:
        last = (r.get("polls") or [{}])[-1]
        print(f"{r['arm']:22} hostLock={(r.get('hostLock') or {}).get('state')} pagehide={r.get('pagehide')}"
              f" releasedBy={(r.get('hostLock') or {}).get('releasedBy')}"
              f" unlockedAt={last.get('t') if last.get('lock') != '1' else 'STILL LOCKED'}"
              f" log={[(u['method'], u['status']) for u in r.get('unlocks', [])]}"
              f" guard={guarded(r)} counted={instrument_ok(r)}"
              f"{' FATAL ' + r['fatal'].splitlines()[-1] if 'fatal' in r else ''}")
    for arm in args.arms.split(","):
        runs = [r for r in report["runs"] if r["arm"] == arm]
        counted = [r for r in runs if instrument_ok(r)]
        released = [r for r in counted if (r.get("polls") or [{}])[-1].get("lock") not in ("1", None)]
        print(f"{arm}: released within 10 s {len(released)}/{len(counted)} counted"
              f" ({len(runs) - len(counted)} instrument failures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
