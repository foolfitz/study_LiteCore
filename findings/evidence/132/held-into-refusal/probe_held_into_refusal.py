#!/usr/bin/env python3
"""SPEC-M3-held-key §13: a held Backspace/Delete that runs into a boundary refusal.

Read from source (§13.1): a refused delete reopens the editing engine (one
Worker generation), the reopened caret is at the document START, and the held
key's repeats reach the engine again once the sink has its focus back.  So
(i) Backspace held at the start is refused again and again up to the
generation ceiling, and (ii) Delete held at the END, once reopened, deletes
from the start until the key comes up.  Measured here; no product byte is
touched.  Not a counted runner.

Arms (each round a fresh page load, so the generation starts at 1):
  start-press  `zqx` typed mid-text, first line + Home, ONE Backspace;
               once reopened, `wvy` typed
  start-hold   the same, five letters typed at the start, Backspace held;
               after release and settle, `wvy` typed
  end-hold     last line + End, `zqx` typed there, Delete held;
               after release and settle, `wvy` typed
  end-press-type  last line + End, `kj` typed there, ONE Delete; once
               reopened, `zqx` typed (finding 134, ruling-1 condition 3: where
               does the next input land)

Three marks (finding 136, ruling-3 condition 3; task 2026-10-13c).  None of
them is in the owner's document (checked on every run, `marksInOriginal`).
  MARK    `zqx`  unchanged: unsaved work typed before the key (start-*,
                 end-hold), or the first input after the reopen (end-press-type).
  CONTROL `kj`   typed at the caret just before the key on end-press-type: the
                 reopened `zqx` must follow it directly (`controlThenMark`), so
                 the read-back sees placement INSIDE the paragraph.
  AFTER   `wvy`  typed after the reopen (start-press) or after release and
                 settle (the hold arms); the read-back says whether its
                 paragraph starts (`afterAtStart`) or ends (`afterAtEnd`) with it.

Exception to condition 3's literal text: start-press gets NO control.  Its key
is Backspace at the document start.  Typing `kj` first would put two characters
before the caret, so the Backspace would delete the `j` and no longer be
refused -- the arm would stop measuring a refusal at all.  It types AFTER once
reopened instead and is judged by the hold rule: AFTER at the start of
paragraph 0, which is where a control would have put it at the document start.

`kjkjk` (start-hold) contains CONTROL.  The reader strips all three marks
before comparing with the original, so a residue of `kjkjk` could vanish from
that comparison; the counts catch every residue (`kjkj`, `kjk`, `kj` leave
CONTROL ≥ 1 where none was typed; `k` leaves a difference).

`#desk.scrollTop` is sampled with every state entry and on every scroll event
of `#desk` (a scroll is not a DOM mutation); the last sample before the key is
recorded as `stateBeforeKey`.  Judged since ruling-3 condition 4.

The report carries no document text: counts, indexes, booleans and hashes only.

  probe_held_into_refusal.py --out DIR [--browsers chrome,firefox] [--hold-ms 8000]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
import traceback
import zipfile
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parents[4] / "wasm_sdk_probe" / "tools"
sys.path.insert(0, str(TOOLS))
import check_m3_production_ui as ui  # noqa: E402
import probe_hand_test_0212 as held  # noqa: E402
from check_m3_locks import Server, login, open_from_files  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, Instance  # noqa: E402
from odt_paragraphs import paragraph_texts_from_xml  # noqa: E402
from probe_m3_gate0_coep import utc_now  # noqa: E402
from r7_support import evaluate  # noqa: E402

NAME = "probe-held-refusal.odt"
MARK = ui.MARK                # "zqx": unsaved work at the moment of the key, or end-press-type's first input after the reopen
CONTROL = "kj"                # ruling-3 condition 3: typed at the caret just before the key (press-type arms, not start-press)
AFTER = "wvy"                 # typed after the reopen (start-press) or after release and settle (hold arms)
MARKS = (MARK, CONTROL, AFTER)
START_TEXT = "kjkjk"          # start-hold: what the hold deletes before it reaches the start
ARMS = ("start-press", "start-hold", "end-hold", "end-press-type")
SETTLED_LIMITS = {"saved", "failed", "lost", "clean", "pending"}

# One clock for the page's state and the keys.  `focus` says where a keydown
# landed: the sink, or (while the queue is blocked and the sink disabled) not.
INSTRUMENT = """(() => { const t0 = performance.now(); const log = window.__r = [];
  const sink = document.querySelector('#sink'), toastEl = document.querySelector('#toast');
  const now = () => Math.round((performance.now() - t0) * 10) / 10;
  const read = () => ({ state: document.querySelector('#state-pill').dataset.state,
    gen: document.querySelector('#s-generation').textContent,
    rev: document.querySelector('#s-revision').textContent,
    latency: document.querySelector('#s-latency').textContent,
    toast: toastEl.classList.contains('show') ? toastEl.textContent : null,
    limit: document.querySelector('#notice').dataset.limit ?? null,
    scroll: document.querySelector('#desk').scrollTop });
  let last = '';
  const tick = () => { const r = read(); const k = JSON.stringify(r);
    if (k !== last) { last = k; log.push({ t: now(), what: 'state', ...r }); } };
  new MutationObserver(tick).observe(document.body, { attributes: true, childList: true, characterData: true, subtree: true });
  window.addEventListener('keydown', (e) => log.push({ t: now(), what: 'keydown', key: e.key, repeat: e.repeat,
    focus: document.activeElement === sink ? 'sink'
      : (document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : null),
    sinkDisabled: sink.disabled }), true);
  sink.addEventListener('beforeinput', (e) => log.push({ t: now(), what: 'beforeinput', type: e.inputType }), true);
  document.querySelector('#desk').addEventListener('scroll', tick, { passive: true });
  window.__rread = read;
  tick(); return true; })()"""
LOG_LENGTH = "(() => window.__r.length)()"
STATE_NOW = "(() => window.__rread())()"
READ_LOG = "(() => window.__r.slice(ARG_FROM))()"


def texts_of(odt: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(odt)) as archive:
        return paragraph_texts_from_xml(archive.read("content.xml"))


def strip_marks(text: str) -> str:
    for mark in MARKS:
        text = text.replace(mark, "")
    return text


def server_read(server: Server, original: list[str]) -> dict[str, Any]:
    """Counts, paragraph indexes and booleans for the three marks; no text."""
    status, raw = server.instance.dav("GET", NAME)
    texts = texts_of(raw)
    stripped = [strip_marks(t) for t in texts]
    holding = {mark: [i for i, t in enumerate(texts) if mark in t] for mark in MARKS}
    with_after = [texts[i] for i in holding[AFTER]]
    return {"status": status, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "marks": sum(t.count(MARK) for t in texts),
            "controls": sum(t.count(CONTROL) for t in texts),
            "afters": sum(t.count(AFTER) for t in texts),
            "paragraphs": len(texts),
            "markParagraphs": holding[MARK], "controlParagraphs": holding[CONTROL],
            "afterParagraphs": holding[AFTER],
            # CONTROL immediately followed by the post-reopen mark (`zqx` on every press-type arm).
            "controlThenMark": any(CONTROL + MARK in t for t in texts),
            # end-hold: `zqx` typed before the hold, `wvy` after it.
            "markThenAfter": any(MARK + AFTER in t for t in texts),
            "afterAtStart": bool(with_after) and all(t.startswith(AFTER) for t in with_after),
            "afterAtEnd": bool(with_after) and all(t.endswith(AFTER) for t in with_after),
            "paragraphsOriginal": len(original),
            "firstDiffFromOriginal": ui.first_difference_index(stripped, original),
            "charDelta": sum(map(len, stripped)) - sum(map(len, original)),
            "sameAsOriginal": stripped == original}


def marks_in(texts: list[str]) -> dict[str, int]:
    return {mark: sum(t.count(mark) for t in texts) for mark in MARKS}


def typed(session, kind: str, text: str) -> list[dict[str, Any]]:
    return [ui.keyed(session, kind, ch) for ch in text]


def settle(session) -> dict[str, Any]:
    """After the key is up: until the limit notice has settled, or the session
    has been ready with an empty queue for 2.5 s.  40 s at most."""
    time.sleep(1.0)
    started, since, seen = time.monotonic(), None, {}
    while time.monotonic() - started < 40:
        limit = (evaluate(session, ui.LIMIT) or {}).get("limit")
        if limit in SETTLED_LIMITS:
            return {"by": "limit", "limit": limit, "afterS": round(time.monotonic() - started + 1.0, 2)}
        seen = ui.state(session)
        if seen.get("state") == "ready" and str(seen.get("pending")) == "0":
            since = since or time.monotonic()
            if time.monotonic() - since >= 2.5:
                return {"by": "ready", "afterS": round(time.monotonic() - started + 1.0, 2)}
        else:
            since = None
        time.sleep(0.15)
    return {"by": "timeout", "last": seen}


def summarize(log: list[dict[str, Any]]) -> dict[str, Any]:
    downs = [e for e in log if e["what"] == "keydown"]
    states = [e for e in log if e["what"] == "state"]
    first = downs[0]["t"] if downs else None
    refusals, reloads, gens, toasts = [], [], [], []
    deletes, prev = 0, None
    for e in states:
        if e["gen"] not in gens:
            gens.append(e["gen"])
        if e["toast"] and e["toast"] not in toasts:
            toasts.append(e["toast"])
        if prev is not None:
            if e["state"] == "restart-required" and prev["state"] != "restart-required":
                refusals.append(e["t"])
            if e["state"] == "ready" and e["gen"] != prev["gen"]:
                reloads.append(e["t"])
            if (e["gen"] == prev["gen"] and e["rev"] != prev["rev"]
                    and (e["latency"] or "")[:1] in ("⌫", "⌦") and "失敗" not in (e["latency"] or "")):
                deletes += 1
        prev = e
    saved = next((e["t"] for e in states if e["limit"] == "saved"), None)
    rel = (lambda t: None if t is None or first is None else round(t - first, 1))
    return {
        "keydowns": len(downs), "repeatsFlagged": sum(1 for e in downs if e["repeat"]),
        "keydownsIntoSink": sum(1 for e in downs if e["focus"] == "sink"),
        "keydownsElsewhere": sorted({str(e["focus"]) for e in downs if e["focus"] != "sink"}),
        "beforeinputs": sum(1 for e in log if e["what"] == "beforeinput"),
        "deletesSeen": deletes, "refusalsMs": [rel(t) for t in refusals], "refusals": len(refusals),
        "readyInNewGenerationMs": [rel(t) for t in reloads], "generations": gens,
        "limitSavedMs": rel(saved), "toasts": toasts,
    }


def run_round(arm: str, kind: str, server: Server, doc: bytes, original: list[str], index: int) -> dict[str, Any]:
    base = server.instance.base
    record: dict[str, Any] = {"arm": arm, "browser": kind, "round": index, "startedAt": utc_now()}
    record["clearedLocks"] = server.clear_locks()
    record["upload"] = server.upload(server.admin, NAME, doc)
    session = ui.new_session(kind)
    record["version"] = getattr(session, "version", None)
    try:
        record["login"] = login(session, base, "admin", server.instance.password)
        open_from_files(session, base, "", NAME, record)
        record["opened"] = ui.quiet(session, 90)
        evaluate(session, INSTRUMENT)
        record["genOpened"] = evaluate(session, ui.GEN)
        if arm in ("start-press", "start-hold"):
            key = "Backspace"
            record["inText"] = ui.click(session, ui.IN_TEXT)
            record["typedMark"] = typed(session, kind, MARK)
            record["placed"] = ui.click(session, ui.FIRST_LINE)
            record["moved"] = ui.keyed(session, kind, "Home")
            if arm == "start-hold":
                record["typedStart"] = typed(session, kind, START_TEXT)
            # start-press: no CONTROL -- it would turn the refused Backspace into a deleted `j` (docstring).
        else:
            key = "Delete"
            record["placed"] = ui.click(session, ui.LAST_LINE)
            record["moved"] = ui.keyed(session, kind, "End")
            if arm == "end-hold":
                record["typedMark"] = typed(session, kind, MARK)
            else:
                record["typedControl"] = typed(session, kind, CONTROL)
        record["key"] = key
        record["genBeforeKey"] = evaluate(session, ui.GEN)
        record["stateBeforeKey"] = evaluate(session, STATE_NOW)
        start = evaluate(session, LOG_LENGTH)
        if arm in ("start-press", "end-press-type"):
            ui.press(session, kind, key)
            record["sent"] = {"press": True}
        else:
            record["sent"] = held.hold_key(session, kind, key)
        record["settle"] = settle(session)
        if arm == "end-press-type":
            # The next input after the reopen: where the user's typing lands.
            record["genBeforeMark"] = evaluate(session, ui.GEN)
            record["typedMark"] = typed(session, kind, MARK)
            record["settleAfterMark"] = settle(session)
        else:
            # start-press: the first input after the reopen; hold arms: after release and settle.
            record["genBeforeAfter"] = evaluate(session, ui.GEN)
            record["typedAfter"] = typed(session, kind, AFTER)
            record["settleAfterAfter"] = settle(session)
        record["log"] = evaluate(session, READ_LOG.replace("ARG_FROM", str(start)))
        record["limit"] = evaluate(session, ui.LIMIT)
        record["genAfter"] = evaluate(session, ui.GEN)
        record["summary"] = summarize(record["log"])
        # Whatever the session holds goes to the server before it is read; at the
        # ceiling the rescue already put it there.
        if record["limit"].get("limit") not in SETTLED_LIMITS:
            record["save"] = ui.save_and_settle(session, 60)
        record["server"] = server_read(server, original)
    except Exception:  # noqa: BLE001 -- a round that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            record.setdefault("closeError", traceback.format_exc())
        record["completedAt"] = utc_now()
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--arms", default=",".join(ARMS))
    parser.add_argument("--start-hold-rounds", type=int, default=2)
    parser.add_argument("--end-hold-rounds", type=int, default=2)
    parser.add_argument("--end-press-type-rounds", type=int, default=1)
    parser.add_argument("--hold-ms", type=int, default=8000)
    parser.add_argument("--hold-delay-ms", type=int, default=500, help="the first repeat (GNOME `delay`)")
    parser.add_argument("--hold-interval-ms", type=int, default=30, help="between repeats (GNOME `repeat-interval`)")
    args = parser.parse_args()
    held.OPTIONS.update(holdMs=args.hold_ms, holdDelayMs=args.hold_delay_ms, holdIntervalMs=args.hold_interval_ms)
    rounds = {"start-press": 1, "start-hold": args.start_hold_rounds, "end-hold": args.end_hold_rounds,
              "end-press-type": args.end_press_type_rounds}
    arms = [a for a in args.arms.split(",") if a]
    unknown = sorted(set(arms) - set(ARMS))
    if unknown:
        parser.error(f"unknown arms {unknown}")
    args.out.mkdir(parents=True, exist_ok=True)
    doc = ui.DOC.read_bytes()
    original = texts_of(doc)
    in_original = marks_in(original)
    if any(in_original.values()):
        raise SystemExit(f"the document already holds a mark: {in_original}")
    server = Server(Instance(DEFAULT_DDEV), [])
    report: dict[str, Any] = {"probe": "probe_held_into_refusal.py", "startedAt": utc_now(),
                              "static": ui.static_facts(DEFAULT_DDEV), "arms": arms, "rounds": rounds,
                              "hold": {k: held.OPTIONS[k] for k in ("holdMs", "holdDelayMs", "holdIntervalMs")},
                              "deskRepeat": held.desk_repeat_settings(),
                              "document": {"sha256": hashlib.sha256(doc).hexdigest(), "paragraphs": len(original),
                                           "marksInOriginal": in_original},
                              "marks": {"mark": MARK, "control": CONTROL, "after": AFTER},
                              "runs": []}
    try:
        for kind in args.browsers.split(","):
            for arm in arms:
                for index in range(rounds[arm]):
                    run = run_round(arm, kind, server, doc, original, index)
                    report["runs"].append(run)
                    (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
                    print(kind, arm, index, "fatal" if run.get("fatal") else json.dumps(
                        {**run.get("summary", {}), "toasts": len(run.get("summary", {}).get("toasts", [])),
                         "server": {k: run.get("server", {}).get(k) for k in
                                    ("marks", "controls", "afters", "markParagraphs", "afterParagraphs",
                                     "controlThenMark", "markThenAfter", "afterAtStart", "afterAtEnd",
                                     "firstDiffFromOriginal", "charDelta", "sameAsOriginal")}},
                        ensure_ascii=False), flush=True)
    finally:
        server.clear_locks()
        try:
            report["staticAfter"] = ui.static_facts(DEFAULT_DDEV)
        except Exception:  # noqa: BLE001
            report["staticAfter"] = {"error": traceback.format_exc()}
        report["completedAt"] = utc_now()
        (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
