#!/usr/bin/env python3
"""B + D at a table (README.md here).  Measurement only.  The instrument,
settle, summary, hold and server read are the held-into-refusal probe's own,
imported from it; the document is the E1 table fixture instead of the owner's.
The report carries no document text beyond paragraph indexes and counts.

  probe_table_refusal.py --out DIR [--browsers chrome,firefox] [--arms ...]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
_spec = importlib.util.spec_from_file_location(
    "held_probe", HERE.parents[1] / "132" / "held-into-refusal" / "probe_held_into_refusal.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)
ui, evaluate = probe.ui, probe.evaluate

DOC = ROOT / "wasm_sdk_probe" / "dist" / "e1-fixtures" / "table-boundary.odt"
ARMS = {"before-table-press-type": ([], "press"), "before-table-hold": ([], "hold"),
        "cell-press-type": (["ArrowDown"], "press"), "cell-hold": (["ArrowDown"], "hold")}


def nav(session, kind: str, key: str) -> dict[str, Any]:
    """ArrowDown is not in the shared key tables; the same two drivers, sent here."""
    before = ui.quiet(session)
    if kind == "chrome":
        for phase in ("rawKeyDown", "keyUp"):
            session.call("Input.dispatchKeyEvent", {"type": phase, "key": key, "code": key,
                                                    "windowsVirtualKeyCode": 40, "nativeVirtualKeyCode": 40})
    else:
        value = {"ArrowDown": ""}[key]
        session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": [
            {"type": "keyDown", "value": value}, {"type": "keyUp", "value": value}]}]})
        session.command("DELETE", "/actions")
    after = ui.quiet(session)
    return {"key": key, "revBefore": before.get("revision"), "revAfter": after.get("revision"),
            "latency": after.get("latency")}


def run_round(arm: str, kind: str, server, doc: bytes, original: list[str]) -> dict[str, Any]:
    base = server.instance.base
    record: dict[str, Any] = {"arm": arm, "browser": kind, "startedAt": probe.utc_now()}
    record["clearedLocks"] = server.clear_locks()
    record["upload"] = server.upload(server.admin, probe.NAME, doc)
    session = ui.new_session(kind)
    record["version"] = getattr(session, "version", None)
    moves, how = ARMS[arm]
    try:
        record["login"] = probe.login(session, base, "admin", server.instance.password)
        probe.open_from_files(session, base, "", probe.NAME, record)
        record["opened"] = ui.quiet(session, 90)
        evaluate(session, probe.INSTRUMENT)
        record["moves"] = [nav(session, kind, key) for key in moves] + [ui.keyed(session, kind, "End")]
        record["genBeforeKey"] = evaluate(session, ui.GEN)
        start = evaluate(session, probe.LOG_LENGTH)
        if how == "press":
            ui.press(session, kind, "Delete")
            record["sent"] = {"press": True}
        else:
            record["sent"] = probe.held.hold_key(session, kind, "Delete")
        record["settle"] = probe.settle(session)
        if how == "press":
            record["typedMark"] = [ui.keyed(session, kind, ch) for ch in probe.MARK]
            record["settleAfterMark"] = probe.settle(session)
        record["log"] = evaluate(session, probe.READ_LOG.replace("ARG_FROM", str(start)))
        record["limit"] = evaluate(session, ui.LIMIT)
        record["summary"] = probe.summarize(record["log"])
        if record["limit"].get("limit") not in probe.SETTLED_LIMITS:
            record["save"] = ui.save_and_settle(session, 60)
        record["server"] = probe.server_read(server, original)
    except Exception:  # noqa: BLE001 -- a round that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            record.setdefault("closeError", traceback.format_exc())
        record["completedAt"] = probe.utc_now()
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--arms", default=",".join(ARMS))
    args = parser.parse_args()
    probe.held.OPTIONS.update(holdMs=8000, holdDelayMs=500, holdIntervalMs=30)
    args.out.mkdir(parents=True, exist_ok=True)
    doc = DOC.read_bytes()
    original = probe.texts_of(doc)
    server = probe.Server(probe.Instance(probe.DEFAULT_DDEV), [])
    report: dict[str, Any] = {"probe": "probe_table_refusal.py", "startedAt": probe.utc_now(),
                              "static": ui.static_facts(probe.DEFAULT_DDEV),
                              "document": {"path": str(DOC.relative_to(ROOT)),
                                           "sha256": hashlib.sha256(doc).hexdigest(),
                                           "paragraphs": len(original)},
                              "hold": {k: probe.held.OPTIONS[k] for k in ("holdMs", "holdDelayMs", "holdIntervalMs")},
                              "runs": []}
    try:
        for kind in args.browsers.split(","):
            for arm in [a for a in args.arms.split(",") if a]:
                run = run_round(arm, kind, server, doc, original)
                report["runs"].append(run)
                (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
                srv = run.get("server", {})
                print(kind, arm, "fatal" if run.get("fatal") else json.dumps(
                    {"refusals": run["summary"]["refusals"], "gens": run["summary"]["generations"],
                     "limit": (run.get("limit") or {}).get("limit"),
                     **{k: srv.get(k) for k in ("marks", "markParagraphs", "paragraphs", "sameAsOriginal",
                                                "firstDiffFromOriginal", "charDelta")}}, ensure_ascii=False),
                      flush=True)
    finally:
        server.clear_locks()
        try:
            report["staticAfter"] = ui.static_facts(probe.DEFAULT_DDEV)
        except Exception:  # noqa: BLE001
            report["staticAfter"] = {"error": traceback.format_exc()}
        report["completedAt"] = probe.utc_now()
        (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
