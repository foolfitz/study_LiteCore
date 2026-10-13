#!/usr/bin/env python3
"""B + D at a table (README.md here).  Measurement only.  The instrument,
settle, summary, hold, the three marks and the server read are the
held-into-refusal probe's own, imported from it; the document is the E1 table
fixture instead of the owner's.  The report carries no document text beyond
paragraph indexes, counts and booleans.

Marks (finding 136, ruling-3 condition 3; task 2026-10-13c):
  press-type arms  CONTROL `kj` typed at the caret just before the Delete (run-3's
                   `--control kj`, now always), MARK `zqx` typed once reopened;
                   judged on `controlThenMark` (`kjzqx` contiguous).
  hold arms        AFTER `wvy` typed after release and settle; judged on the
                   paragraph holding it and `afterAtEnd` (end of paragraph 0 for
                   before-table-hold, end of paragraph 1 = cell A1 for cell-hold).
`scrollTop` is recorded as in the held probe; the table arms are exempt from
its rule (the fixture fits one screen).

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
FOCUS_SINK = "(() => { document.querySelector('#sink').focus({ preventScroll: true }); return document.activeElement.id; })()"
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


def run_round(arm: str, kind: str, server, doc: bytes, original: list[str], index: int = 0) -> dict[str, Any]:
    base = server.instance.base
    record: dict[str, Any] = {"arm": arm, "browser": kind, "round": index, "startedAt": probe.utc_now()}
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
        # run-1 sent every key to <body>: nothing had focused the sink (the owner-document probes click
        # into the text first).  The caret is at the document start after opening; focus the sink there.
        record["focused"] = evaluate(session, FOCUS_SINK)
        record["moves"] = [nav(session, kind, key) for key in moves] + [ui.keyed(session, kind, "End")]
        if how == "press":
            # run-3: a second mark typed where the caret is before the key, so the read-back says
            # where the user's caret was, beside where the reopened one put `zqx`.
            record["typedControl"] = probe.typed(session, kind, probe.CONTROL)
        record["genBeforeKey"] = evaluate(session, ui.GEN)
        record["stateBeforeKey"] = evaluate(session, probe.STATE_NOW)
        start = evaluate(session, probe.LOG_LENGTH)
        if how == "press":
            ui.press(session, kind, "Delete")
            record["sent"] = {"press": True}
        else:
            record["sent"] = probe.held.hold_key(session, kind, "Delete")
        record["settle"] = probe.settle(session)
        if how == "press":
            record["typedMark"] = probe.typed(session, kind, probe.MARK)
            record["settleAfterMark"] = probe.settle(session)
        else:
            record["typedAfter"] = probe.typed(session, kind, probe.AFTER)
            record["settleAfterAfter"] = probe.settle(session)
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
    arms = [a for a in args.arms.split(",") if a]
    unknown = sorted(set(arms) - set(ARMS))
    if unknown:
        parser.error(f"unknown arms {unknown}")
    probe.held.OPTIONS.update(holdMs=8000, holdDelayMs=500, holdIntervalMs=30)
    args.out.mkdir(parents=True, exist_ok=True)
    doc = DOC.read_bytes()
    original = probe.texts_of(doc)
    in_original = probe.marks_in(original)
    if any(in_original.values()):
        raise SystemExit(f"the fixture already holds a mark: {in_original}")
    server = probe.Server(probe.Instance(probe.DEFAULT_DDEV), [])
    report: dict[str, Any] = {"probe": "probe_table_refusal.py", "startedAt": probe.utc_now(),
                              "marks": {"mark": probe.MARK, "control": probe.CONTROL, "after": probe.AFTER},
                              "static": ui.static_facts(probe.DEFAULT_DDEV),
                              "document": {"path": str(DOC.relative_to(ROOT)),
                                           "sha256": hashlib.sha256(doc).hexdigest(),
                                           "paragraphs": len(original), "marksInOriginal": in_original},
                              "hold": {k: probe.held.OPTIONS[k] for k in ("holdMs", "holdDelayMs", "holdIntervalMs")},
                              "runs": []}
    try:
        for kind in args.browsers.split(","):
            for arm in arms:
                run = run_round(arm, kind, server, doc, original)
                report["runs"].append(run)
                (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
                srv = run.get("server", {})
                print(kind, arm, "fatal" if run.get("fatal") else json.dumps(
                    {"refusals": run["summary"]["refusals"], "gens": run["summary"]["generations"],
                     "limit": (run.get("limit") or {}).get("limit"),
                     **{k: srv.get(k) for k in ("marks", "controls", "afters", "markParagraphs", "controlParagraphs",
                                                "afterParagraphs", "controlThenMark", "afterAtEnd", "paragraphs",
                                                "sameAsOriginal", "firstDiffFromOriginal", "charDelta")}},
                    ensure_ascii=False),
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
