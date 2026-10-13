#!/usr/bin/env python3
"""Where text typed during D's caret-restore window lands (README.md here).

One arm: last line + End, ONE Delete (refused at the end, the page reopens),
poll the generation until it changes, then type `zqx` at once -- inside the
~0.7 s in which D is putting the caret back.  Measurement only: not an
acceptance arm, so the acceptance judge's ARMS stay as they are.  The
instrument, settle, summary and server read are the held-into-refusal probe's
own, imported from it.  The report carries no document text.

  probe_restore_window.py --out DIR [--browsers chrome,firefox] [--rounds 3]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "held_probe", HERE.parents[1] / "132" / "held-into-refusal" / "probe_held_into_refusal.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)
ui, evaluate = probe.ui, probe.evaluate

KEY_GAP_S = 0.05
POLL_S = 0.02
NOW = "(() => Math.round((performance.now()) * 10) / 10)()"


def run_round(kind: str, server, doc: bytes, original: list[str], index: int) -> dict[str, Any]:
    base = server.instance.base
    record: dict[str, Any] = {"arm": "end-press-type-fast", "browser": kind, "round": index,
                              "startedAt": probe.utc_now()}
    record["clearedLocks"] = server.clear_locks()
    record["upload"] = server.upload(server.admin, probe.NAME, doc)
    session = ui.new_session(kind)
    record["version"] = getattr(session, "version", None)
    try:
        record["login"] = probe.login(session, base, "admin", server.instance.password)
        probe.open_from_files(session, base, "", probe.NAME, record)
        record["opened"] = ui.quiet(session, 90)
        evaluate(session, probe.INSTRUMENT)
        record["placed"] = ui.click(session, ui.LAST_LINE)
        record["moved"] = ui.keyed(session, kind, "End")
        record["genBeforeKey"] = evaluate(session, ui.GEN)
        start = evaluate(session, probe.LOG_LENGTH)
        ui.press(session, kind, "Delete")
        polled, deadline = 0, time.monotonic() + 20
        while time.monotonic() < deadline and evaluate(session, ui.GEN) == record["genBeforeKey"]:
            polled += 1
            time.sleep(POLL_S)
        record["genSeenAt"] = evaluate(session, NOW)
        record["polls"] = polled
        typed = []
        for ch in probe.MARK:
            ui.press(session, kind, ch)
            typed.append({"key": ch, "sentAt": evaluate(session, NOW)})
            time.sleep(KEY_GAP_S)
        record["typed"] = typed
        record["settle"] = probe.settle(session)
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
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    doc = ui.DOC.read_bytes()
    original = probe.texts_of(doc)
    server = probe.Server(probe.Instance(probe.DEFAULT_DDEV), [])
    report: dict[str, Any] = {"probe": "probe_restore_window.py", "startedAt": probe.utc_now(),
                              "static": ui.static_facts(probe.DEFAULT_DDEV),
                              "document": {"sha256": hashlib.sha256(doc).hexdigest(), "paragraphs": len(original)},
                              "keyGapS": KEY_GAP_S, "pollS": POLL_S, "runs": []}
    try:
        for kind in args.browsers.split(","):
            for index in range(args.rounds):
                run = run_round(kind, server, doc, original, index)
                report["runs"].append(run)
                (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
                srv = run.get("server", {})
                print(kind, index, "fatal" if run.get("fatal") else json.dumps(
                    {"refusals": run["summary"]["refusals"], "gens": run["summary"]["generations"],
                     **{k: srv.get(k) for k in ("marks", "markParagraphs", "paragraphs", "sameAsOriginal",
                                                "charDelta")}}, ensure_ascii=False), flush=True)
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
