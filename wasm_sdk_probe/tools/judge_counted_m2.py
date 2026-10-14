#!/usr/bin/env python3
"""Reader for the counted M2 of paragraph merge (SPEC-M3-paragraph-merge 30.2 and 31.2; 31.4 X7).

Written 2026-10-08, before any counted run exists.  It reads one directory of reports and decides, per
browser, M2-0, M2-1, M2-1b, M2-2, M2-3, the G01 barrier, M2-4 (with 31.2's per-press latency), the M2-1 red
case and the paired control.  It writes nothing.

  judge_counted_m2.py --dir DIR [--profile e2-editor-v19] [--browsers chrome firefox] [--uncounted] [--wasm PATH]

Files it reads in DIR, per browser B (the names the counted chain is to write):
  counted-B.json          --mode counted                 (the tool list, 3 rounds)
  counted-control-B.json  --mode counted --control       (spec 22.3's paired control)
  m2-1b-B.json            --mode m2-1b
  m2-4-B.json             --mode m2-4
  red-B.json              --mode m2-1-red --candidate-profile e2-editor-v8
and each one's kept documents (`<stem>.docs/`) and, when present, `<stem>.stderr.txt`.

What it trusts and what it does not:
  - NOT the runner's `pass` or `clauses` (handoff 10-08d rule x: two M2-4 reports say `pass: true` and are red
    under 31.2).  Every clause is recomputed from the recorded fields.
  - NOT the runner's document verdicts: every comparison is redone from the kept documents against the native
    references, and a report whose recorded content hash or text verdict disagrees with the kept file is NOT
    DONE for that record (the kept file is not the one the report compared).
  - NOT the reports' own word on what they are bound to (review 2026-10-08): a counted verdict needs every
    report of BOTH browsers to carry this tree's runner (`RUNNER_SHA`, the runner file's sha256[:16]) and the
    binding committed in it (`m.BINDING`, exactly `m.BOUND_KEYS`, each a sha256), and to have served exactly
    that binding (the red case: every value but the profile's own).  Re-judging later means checking out the
    commit the counted run used.  M2-4's native reference under build/ is pinned by its content hash.
  - The POPULATION is the reader's own: eshape.json read here, the two synthetic fixtures of spec 25, the
    decision -> expectation table of spec 17 / 22.1, and the counts of spec 25 (20 / 5 / 1).  The runner's
    `tool_cases` is used only for the ORDER of the list (the red case's "first three") and must name the same
    cases.  Shared with the runner, and tested there: `native_cases` (the native arms: caret, comment,
    reference paths), `odt_parts` and `reduce_content` (spec 24's reduction), `pair`, and the constants that name
    where things are: `FIXTURES` (round keys, directories), `MARKER_AT`/`MARKER`, `LIMIT_ROUND`/`LIMIT_FIXTURE`,
    `ESHAPE`, `PROFILE_BOUND`, `BOUND_KEYS`, `BINDING`.

Verdicts.  A clause is True, False, or None (not done: a number, a document or a record is missing).  A record
or criterion FAILS when any clause is False, is NOT DONE when none is False and one is None, and PASSES
otherwise.  The exit code carries the verdict (handoff rule p):
  0  every criterion PASSES on Chrome AND Firefox, and the reports are the counted run (bound, this runner);
  1  some criterion FAILS (a known miss outranks an unmeasured part: the verdict is not pass either way);
  3  nothing FAILS and something is NOT DONE (a report missing or unreadable, a population short, a number
     missing, the reports not bound);
  4  everything PASSES but it is not a counted verdict: --uncounted (a dry run on reports that are not bound)
     or --browsers narrower than both (review 2026-10-08: X7 is two browsers).
The last line is `VERDICT ...` and names every FAIL and NOT DONE.

Decisions written down here (2026-10-08):
  - M2-1 red: spec 30.2 says each case must NOT be `verified-key-undo` "(109's refusal + reopen)"; the
    parenthesis is taken as the clause.  A case that was never placed, or never answered, is not a red.
  - The M2-4 control is not read: spec 30.2 pairs a control with the counted run only.
  - M2-2's population is every M2-1 record of the counted run (20 cases x 3 rounds per browser); a record with
    no number (a refusal has no keyUndo) makes M2-2 NOT DONE while M2-1 FAILS on that record.

C (2026-10-15, task 10-15c P1; SPEC-M3-link-batch 10.5 and 10.7).  On a profile whose engine carries C, R0c's
`nothing-selected` (C29 Backspace at the document start, C30 Delete at its end) expects the no-op
`verified-boundary-noop` instead of the refusal; everything else in the table is unchanged.  Keyed as the runner
keys it (7e6c9acd, `m.boundary_noop_declared`): on the bytes of `dist/profiles/<profile>/probe.wasm` (or `--wasm`),
whose sha256 must equal every non-red report's `bound.wasmSha256`, or nothing is judged -- the expectation cannot
be read from bytes that did not run.  A no-op record's clauses (`noop_record`) are recomputed from the recorded
fields and the kept `<case>-r<n>-after-key.odt`; the kept-document counts of the paired control follow the keying.
34.4, repaired because of execution.  Witness: part B's eight v20 shakedown reports
(findings/evidence/link-batch/v20-shakedown/merge/, runner 73b2e9ff), red on the four C29/C30 records of every
shakedown and control report under the refusal table.  v19's X7 reports re-judge unchanged: v19's wasm does not
carry C.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_merge_wasm_shakedown as m  # noqa: E402

# ---- the spec's numbers, not any report's ----------------------------------------------------------------------
BROWSERS = ("chrome", "firefox")
ROUNDS = 3                                   # 30.2 計數執行
FIXTURES = ("boundaries", "boundaries-indent")   # 25: the M2-1 population is the two synthetic documents
POPULATION = Counter({"M2-1": 20, "M2-3": 5, "barrier": 1})   # 25 (16 + 4 merges, G01); 17 / 22.1 (five refusals)
M2_1B_RUNS = 10                              # 30.2: per typed-merge case and browser
M2_1B_TOTAL = 20                             # 30.2: N = 20 per browser
RED_CASES, RED_PROFILE = 3, "e2-editor-v8"   # 30.2 M2-1 紅案
LIMIT = {"case": "H03", "presses": 105, "steps": 100, "comment": "Delete paragraph",
         "fixtureSha256": "09b5ced0e619f8258bb60f46a196e4ab76861c75466f926e076b737f4ce3ecfb"}   # 30.2 M2-4
BOUND_MS = 1000                              # 30.2 M2-2 and 31.2: runner and engine, each strictly under
# 22.1: the reopen's own two toasts, in order (e2-editor-app.js `${lead}，正在重新載入…`, `${lead}，已重新載入…`).
STARTING, REOPENED = "，正在重新載入…", "，已重新載入"
SAVED = re.compile(r"已存出 [0-9]+(?:\.[0-9]+)? KB")   # the standalone page's save confirmation, the one toast a
                                                       # merge case may show after its key (one per save)
SAVE_TOKEN = "已存出 N KB"                             # 34.1 (b): what every SAVED becomes in the paired control
# M2-4's native reference (R0 run 4, round 1, press 105): content.xml sha256[:16], recorded by every v18 M2-4
# report as `finalDocument.theirs`.  The file lives under build/ (not in git); review 2026-10-08, opus S6.
LIMIT_REFERENCE_SHA16 = "60087d9401a68bf6"
RUNNER_SHA = hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()[:16]
UNCHANGED = "沒有被改動"                        # 22.1: never said after the key went out
# Where C's keying is read from by default: the served profile's engine, the same bytes the runner hashes as
# `wasmSha256` (module docstring, C).  A test replaces this directory with one of its own.
PROFILES = m.HERE / "dist" / "profiles"
FILES = {"counted": "counted-{}.json", "control": "counted-control-{}.json", "m2-1b": "m2-1b-{}.json",
         "m2-4": "m2-4-{}.json", "red": "red-{}.json"}
MODES = {"counted": "counted", "control": "counted", "m2-1b": "m2-1b", "m2-4": "m2-4", "red": "m2-1-red"}
# What each report carries: when it is missing, each of these is NOT DONE whatever another report says.
CARRIES = {"counted": ("M2-0", "M2-1", "M2-2", "M2-3", "barrier", "control"), "control": ("control",),
           "m2-1b": ("M2-0", "M2-1b", "M2-2"), "m2-4": ("M2-0", "M2-4"), "red": ("red",)}
M2_0 = {"counted": set(FIXTURES), "m2-1b": {"boundaries"}, "m2-4": {"undo-limit-105"}}


class Stop(Exception):
    """The population or the native side cannot be established: nothing can be judged."""


def expectation(decision: str, boundary_noop: bool = False) -> tuple | None:
    """Spec 17 and 22.1: R0c's decision -> (criterion, outcome, stage, keyPosted).  None = stop.
    `boundary_noop` (link-batch 10.5): the profile under test carries C, so `nothing-selected` expects the no-op;
    the default is the refusal, which is what every profile before v20 does."""
    if decision in ("merge", "typed-merge"):
        return "M2-1", "verified-key-undo", None, None
    if decision == "barrier":
        return "barrier", "verified-selection-delete", None, None
    if decision == "nothing-selected":
        if boundary_noop:
            return "M2-3", m.BOUNDARY_NOOP, None, None
        return "M2-3", "refused", "nothing-selected", False
    if decision.startswith("refused-k1-"):
        return "M2-3", "refused", "anchor-mismatch", False
    if decision.startswith("refused-k2-"):
        return "M2-3", "refused", "return-mismatch", False
    if decision == "key-noop":
        return "M2-3", "refused", "key-deadline", True
    return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keying(wasm: Path) -> tuple[bool, str]:
    """C's keying (module docstring): whether the engine in `wasm` carries C, and the sha256 every non-red report
    must have bound.  Read from the file, never from a report's own word."""
    if not wasm.is_file():
        raise Stop(f"{wasm} is not there: C's expectation cannot be read (spec 22.1: stop)")
    return m.boundary_noop_declared(wasm), sha256(wasm)


def kept_expected(cases: dict) -> dict:
    """Spec 22.3: the documents the counted run and its control keep, by kind.  Merges and the barrier save
    after the key and after the follow-up Z; a refusal saves after the reopen; C's no-op saves after the key."""
    noops = sum(c["expected"][0] == m.BOUNDARY_NOOP for c in cases.values())
    merges = POPULATION["M2-1"] + POPULATION["barrier"]
    return {"after-key": (merges + noops) * ROUNDS, "follow": merges * ROUNDS,
            "reopened": (POPULATION["M2-3"] - noops) * ROUNDS}


def population(boundary_noop: bool = False) -> tuple[dict, list]:
    table = json.loads(m.ESHAPE.read_text())
    if table.get("kills") or table.get("stops"):
        raise Stop(f"eshape.json: KILL {table.get('kills')} STOP {table.get('stops')}")
    rounds = {m.FIXTURES[f][2]: f for f in FIXTURES}
    out = {}
    for key, decision in table["cases"].items():
        round_key, case = key.split(" ", 1)
        if round_key not in rounds:
            continue
        expected = expectation(decision, boundary_noop)
        if expected is None:
            raise Stop(f"{case}: R0c decision {decision!r} has no expectation (spec 22.1: stop)")
        try:
            native = m.native_cases(rounds[round_key])[case]
        except (SystemExit, KeyError) as error:
            raise Stop(f"{case}: native side: {error}") from error
        if native["decision"] != decision:
            raise Stop(f"{case}: eshape.json says {decision!r}, the runner's native side {native['decision']!r}")
        out[case] = {"fixture": rounds[round_key], "decision": decision, "criterion": expected[0],
                     "expected": expected[1:], "native": native}
    counts = Counter(v["criterion"] for v in out.values())
    if counts != POPULATION:
        raise Stop(f"population {dict(counts)} is not spec 25's {dict(POPULATION)}")
    try:
        order = list(m.tool_cases(frame_cell=False))
    except SystemExit as error:
        raise Stop(f"the runner's tool list: {error}") from error
    if set(order) != set(out):
        raise Stop(f"the runner's tool list {sorted(order)} is not the reader's {sorted(out)}")
    return out, order


# ---- clauses ---------------------------------------------------------------------------------------------------
def status(clauses: dict) -> str:
    values = list(clauses.values())
    return "FAIL" if False in values else "NOT DONE" if None in values else "PASS"


def worst(statuses) -> str:
    statuses = list(statuses)
    return "FAIL" if "FAIL" in statuses else "NOT DONE" if "NOT DONE" in statuses else "PASS"


def kept(path: Path, name: str) -> bytes | None:
    target = path.parent / f"{path.stem}.docs" / f"{name}.odt"
    return target.read_bytes() if target.is_file() else None


def against(raw: bytes | None, reference: Path, recorded: dict | None, with_bytes: bool) -> dict:
    """A kept document against a native one: paragraph text, and spec 24's reduced bytes when asked.  None when
    the document is missing or is not the one the report compared (its recorded hash or text verdict)."""
    if not reference.is_file():
        raise Stop(f"native reference {reference} is missing")
    if raw is None:
        return {"text": None, "bytes": None}
    mine, theirs = m.odt_parts(raw), m.odt_parts(reference.read_bytes())
    text = mine["paragraphs"] == theirs["paragraphs"]
    if recorded is not None and (recorded.get("mine") != mine["sha"] or recorded.get("textEqual") is not text):
        return {"text": None, "bytes": None, "disagrees": True}
    return {"text": text, "bytes": (m.reduce_content(mine["content"]) == m.reduce_content(theirs["content"])
                                    if with_bytes else None)}


def fast(ms) -> bool | None:
    if ms is None:
        return None
    # Review 2026-10-08 (codex S2): a negative or non-finite time is not an answer to the key.
    return (isinstance(ms, (int, float)) and not isinstance(ms, bool) and math.isfinite(ms)
            and 0 <= ms < BOUND_MS)


def only_saves(toasts, saves: int) -> bool | None:
    """Review 2026-10-08 (codex B5): from the key to the end of the case, only the case's own saves.  None when
    the runner did not record it (a report from before the review)."""
    if toasts is None:
        return None
    return (isinstance(toasts, list) and len(toasts) == saves
            and all(isinstance(t, str) and SAVED.fullmatch(t) for t in toasts))


def reopen_pair(toasts) -> bool:
    """Review 2026-10-08 (codex B8): the reopen's start and end, in that order, about one refusal."""
    if not isinstance(toasts, list) or len(toasts) != 2 or not all(isinstance(t, str) for t in toasts):
        return False
    if not toasts[0].endswith(STARTING):
        return False
    lead = toasts[0][: -len(STARTING)]
    return bool(lead) and toasts[1].startswith(lead + REOPENED)


def same_generation(record: dict) -> bool:
    gen = record.get("generation") or [None, None]
    return gen[0] is not None and gen[0] == gen[1]


def next_generation(value) -> str | None:
    try:
        return str(int(value) + 1)
    except (TypeError, ValueError):
        return None


def merge_record(record: dict, case: dict, path: Path) -> dict:
    """M2-1 (22.1, 24; typed merges by paragraph text only, 12) and the G01 barrier (10.2 R0)."""
    native, typed = case["native"], case["decision"] == "typed-merge"
    name = f"{record['case']}-r{record['round']}"
    after = against(kept(path, f"{name}-after-key"), native["key"], record.get("afterKeyDocument"), not typed)
    follow = against(kept(path, f"{name}-follow"), native["follow"], record.get("followDocument"), False)
    key_undo = record.get("keyUndo") or {}
    clauses = {"placed": (record.get("place") or {}).get("ok") is True,
               "outcome": record.get("outcome") == case["expected"][0],
               "generation": same_generation(record),
               "afterKeyText": after["text"],
               "followText": follow["text"],
               "noToast": record.get("toasts") == [],
               "noToastThroughFollow": only_saves(record.get("toastsAtEnd"), 2)}
    if not typed:
        clauses["afterKeyBytes"] = after["bytes"]
    if case["criterion"] == "M2-1":
        clauses["comment"] = native["nativeComment"] is not None and key_undo.get("comment") == native["nativeComment"]
        clauses["restorePresses"] = key_undo.get("restorePresses") == 0
    return clauses


def original_plus_marker(record: dict, case: dict) -> list:
    """The paragraph text a marker-typing case (a refusal, C's no-op) must read back: the fixture's original with
    the marker at the other marker case's native caret, exactly once."""
    fixture = case["fixture"]
    marker_case = next((c for c in m.MARKER_AT.get(fixture, ()) if c != record["case"]), None)
    if marker_case is None:
        raise Stop(f"{record['case']}: no marker place in {fixture}")
    target = m.native_cases(fixture)[marker_case]
    original = m.odt_parts(case["native"]["original"].read_bytes())["paragraphs"]
    if original.count(target["search"]) != 1:
        raise Stop(f"marker target {target['search']!r} occurs {original.count(target['search'])} times")
    return [(m.MARKER + p if target["backward"] else p + m.MARKER) if p == target["search"] else p
            for p in original]


def kept_by_content(record: dict, path: Path, kind: str, field: str) -> list | None:
    """The kept `<case>-r<n>-<kind>.odt`'s paragraphs, or None when it is missing or is not the document the
    record names by content (`<field>.sha`, `<field>.paragraphs`; review 2026-10-08, opus NOTE 6)."""
    raw = kept(path, f"{record['case']}-r{record['round']}-{kind}")
    parts = m.odt_parts(raw) if raw is not None else None
    mine = parts["paragraphs"] if parts else None
    recorded = record.get(field) or {}
    if parts and (recorded.get("paragraphs") != len(mine) or recorded.get("sha") != parts["sha"]):
        return None
    return mine


def refusal_record(record: dict, case: dict, path: Path) -> dict:
    """M2-3 as narrowed by 22.1 and 22.2: stage, keyPosted, reopen, original + marker, checkpoint, toasts."""
    _, stage, posted = case["expected"]
    expected_text = original_plus_marker(record, case)
    mine = kept_by_content(record, path, "reopened", "reopenedDocument")
    window = record.get("toastWindow") or {}
    toasts = window.get("toasts")
    before, after = record.get("beforeKey") or {}, record.get("afterKey") or {}
    reopened = next_generation((record.get("generation") or [None])[0])
    clauses = {"markerPlaced": (record.get("markerPlace") or {}).get("ok") is True,
               "placed": (record.get("place") or {}).get("ok") is True,
               "outcome": record.get("outcome") == "refused",
               "stage": record.get("stage") == stage,
               "keyPosted": record.get("keyPosted") is posted,
               "generation": (reopened is not None and window.get("generation") == reopened
                              and (record.get("generation") or [None, None])[1] == reopened),
               "toastWindowClosed": window.get("closed") is True,
               "reopenedText": None if mine is None else mine == expected_text,
               "markerOnce": None if mine is None else sum(m.MARKER in p for p in mine) == 1,
               "checkpointRevision": (before.get("revision") is not None
                                      and after.get("checkpoint") == f"有（r{before.get('revision')}）"),
               "onlyTheReopenToasts": reopen_pair(toasts)}
    if posted:
        clauses["noUnchanged"] = isinstance(toasts, list) and not any(UNCHANGED in (t or "") for t in toasts)
    return clauses


def noop_record(record: dict, case: dict, path: Path) -> dict:
    """M2-3 under C (link-batch 10.5, 10.7): no refusal, generation and revision unchanged, no toast, the document
    saved after the key is the original plus the marker (the marker exactly once), and the caret where the
    placement left it.  `caretUnchanged` is None on a record without `caretAfterKey` (a runner before 7e6c9acd
    did not read it): not established, never inferred."""
    expected_text = original_plus_marker(record, case)
    mine = kept_by_content(record, path, "after-key", "afterKeyDocument")
    before, after = record.get("beforeKey") or {}, record.get("afterKey") or {}
    placed = record.get("place") or {}
    if "caretAfterKey" not in record:
        caret_unchanged = None
    else:
        seen = record.get("caretAfterKey") or {}
        caret_unchanged = (m.caret_tuple(seen) is not None and m.caret_tuple(seen) == placed.get("engineCaret")
                           and seen.get("generation") == placed.get("caretGeneration"))
    return {"markerPlaced": (record.get("markerPlace") or {}).get("ok") is True,
            "placed": placed.get("ok") is True,
            "outcome": record.get("outcome") == m.BOUNDARY_NOOP,
            "generation": same_generation(record),
            "revision": before.get("revision") is not None and before.get("revision") == after.get("revision"),
            "noToast": record.get("toasts") == [],
            "unchangedText": None if mine is None else mine == expected_text,
            "markerOnce": None if mine is None else sum(m.MARKER in p for p in mine) == 1,
            "caretUnchanged": caret_unchanged}


def m2_3_record(record: dict, case: dict, path: Path) -> dict:
    return (noop_record if case["expected"][0] == m.BOUNDARY_NOOP else refusal_record)(record, case, path)


def latency(record: dict, engine_ms) -> dict:
    return {"runner": fast(record.get("keyToResponseMs")), "engine": fast(engine_ms)}


def limit_record(record: dict, report: dict, path: Path) -> tuple[dict, dict]:
    """M2-4 (30.2) with 31.2's per-press latency.  Returns the clauses and the descriptive counts."""
    presses = record.get("presses") or []
    after = [p.get("actionsAfter") for p in presses]
    full = next((i for i, a in enumerate(after, 1) if a == LIMIT["steps"]), None)
    per_press = [latency(p, p.get("keyToUndoMs")) for p in presses]
    flat = [v for lat in per_press for v in lat.values()]
    reference = m.LIMIT_ROUND / "docs" / f"r1-{LIMIT['case']}-key{LIMIT['presses']}.odt"
    if not reference.is_file() or m.odt_parts(reference.read_bytes())["sha"] != LIMIT_REFERENCE_SHA16:
        raise Stop(f"M2-4's native reference {reference} is missing or not content {LIMIT_REFERENCE_SHA16}")
    final = against(kept(path, f"{LIMIT['case']}-r1-after-key"), reference, record.get("finalDocument"), True)
    clauses = {"fixture": ((report.get("limit") or {}).get("fixtureSha256") == LIMIT["fixtureSha256"]
                           and sha256(m.LIMIT_FIXTURE) == LIMIT["fixtureSha256"]) or None,   # another run: NOT DONE
               "placed": (record.get("place") or {}).get("ok") is True,
               "presses": len(presses) == LIMIT["presses"],
               "everyPressVerified": len(presses) == LIMIT["presses"] and all(
                   p.get("ok") is True and p.get("completion") == "verified-key-undo" for p in presses),
               "comment": len(presses) == LIMIT["presses"] and all(p.get("comment") == LIMIT["comment"]
                                                                   for p in presses),
               "restorePresses": len(presses) == LIMIT["presses"] and all(p.get("restorePresses") == 0
                                                                          for p in presses),
               "limitReached": (full is not None and full <= LIMIT["steps"]
                                and all(a == LIMIT["steps"] for a in after[full - 1:])),
               "latency": (False if False in flat else None if None in flat or not presses else True),
               "generation": same_generation(record),
               "noToast": record.get("toasts") == [],
               "noToastThroughSave": only_saves(record.get("toastsAtEnd"), 1),
               "finalBytes": final["bytes"],
               "finalText": final["text"]}
    engine = [p.get("keyToUndoMs") for p in presses if isinstance(p.get("keyToUndoMs"), (int, float))]
    counts = {"presses": len(presses),
              "withBothNumbers": sum(None not in lat.values() for lat in per_press),
              "slow": sum(False in lat.values() for lat in per_press),
              "limitAtPress": full,
              # Spec 33.4: the clock-guard argument is re-read against v19's minimum.
              "engineMs": [min(engine), statistics.median(engine), max(engine)] if engine else None}
    return clauses, counts


def red_record(record: dict) -> dict:
    gen = record.get("generation") or [None, None]
    return {"placed": (record.get("place") or {}).get("ok") is True,
            "refused": record.get("outcome") == "refused",
            "reopened": next_generation(gen[0]) is not None and gen[1] == next_generation(gen[0])}


def m2_0_record(record: dict, path: Path) -> dict:
    fixture = record.get("fixture")
    reference = (m.LIMIT_ROUND / "docs" / "original.odt" if fixture == "undo-limit-105"
                 else m.FIXTURES[fixture][1] / "docs" / "original.odt")
    result = against(kept(path, f"m2-0-{fixture}"), reference, record.get("document"), True)
    return {"reducedBytes": result["bytes"], "text": result["text"]}


# ---- one browser -----------------------------------------------------------------------------------------------
def load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as error:
        return error


def describe(values: list) -> str:
    values = [v for v in values if isinstance(v, (int, float))]
    if not values:
        return "none"
    return f"n={len(values)} min={min(values)} median={statistics.median(values)} max={max(values)}"


class Browser:
    def __init__(self, directory: Path, browser: str, profile: str, uncounted: bool, cases: dict, order: list,
                 wasm_sha: str):
        self.d, self.b, self.profile, self.uncounted = directory, browser, profile, uncounted
        self.cases, self.order, self.wasm_sha = cases, order, wasm_sha
        self.kept = kept_expected(cases)
        self.lines: list[str] = []
        self.verdicts: dict[str, str] = {}
        self.reports: dict = {}

    def say(self, name: str, verdict: str, detail: str) -> None:
        self.verdicts[name] = worst([self.verdicts.get(name, "PASS"), verdict])
        self.lines.append(f"{name:<10} {verdict:<8} {detail}")

    def records(self, report: dict, judge) -> tuple[str, list]:
        bad = []
        for record in report.get("cases") or []:
            clauses = judge(record)
            verdict = status(clauses)
            if verdict != "PASS":
                bad.append((verdict, f"{record.get('case')} r{record.get('round')}",
                            sorted(k for k, v in clauses.items() if v is not True)))
        return worst(v for v, _, _ in bad), bad

    def population_of(self, report: dict, wanted: set) -> tuple[bool, str]:
        keys = Counter((c.get("case"), c.get("round")) for c in report.get("cases") or [])
        missing, extra = wanted - set(keys), set(keys) - wanted
        repeated = [k for k, n in keys.items() if n > 1]
        ok = not (missing or extra or repeated)
        return ok, ("" if ok else f" population: missing {sorted(missing)[:6]} extra {sorted(extra)[:6]} "
                                  f"repeated {repeated[:6]}")

    def identity(self, kind: str, report: dict, path: Path) -> dict:
        control = kind == "control"
        stderr = path.with_suffix(".stderr.txt")
        clauses = {"completedAt": bool(report.get("completedAt")),
                   "boot": (report.get("boot") or {}).get("state") == "ready",
                   "restOfShellEqualsSource": report.get("restOfShellEqualsSource") is True,
                   "mode": report.get("mode") == MODES[kind],
                   "browser": report.get("browser") == self.b,
                   "control": report.get("control") is control and report.get("instrumented") is (not control),
                   "toolList": (report.get("caseList") == "tool" and report.get("frameCell") is False
                                and report.get("ownerDocument") is False),
                   "eshape": report.get("eshapeSha256") == sha256(m.ESHAPE),
                   "profile": (report.get("candidate") or {}).get("profile") == (
                       RED_PROFILE if kind == "red" else self.profile),
                   "noRunnerError": not any(c.get("outcome") == "runner-error" for c in report.get("cases") or []),
                   "observerClosed": ("error" not in (report.get("observerAtEnd") or {})
                                      and not report.get("teardownError")),
                   # A counted chain writes every stderr (review 2026-10-08, opus NOTE); a dry run may not.
                   "stderrEmpty": (stderr.is_file() or self.uncounted)
                   and ((not stderr.is_file()) or stderr.stat().st_size == 0)}
        if not self.uncounted:
            clauses["counted"] = report.get("counted") is True and report.get("binding") is not None
        return clauses

    def run(self) -> dict:
        reports = {}
        for kind, pattern in FILES.items():
            path = self.d / pattern.format(self.b)
            report = load(path)
            if not isinstance(report, dict):
                self.say("reports", "NOT DONE", f"{path.name}: {report}")
                for name in CARRIES[kind]:
                    self.say(name, "NOT DONE", f"{path.name} is missing or unreadable")
                continue
            # C's keying (module docstring): the expectation was read from one file's bytes, and every report
            # but the red case (v8's own engine) must have run and bound exactly those bytes.
            bound_wasm = (report.get("bound") or {}).get("wasmSha256")
            if kind != "red" and bound_wasm != self.wasm_sha:
                raise Stop(f"{path.name}: bound wasm {str(bound_wasm)[:16]} is not the keyed {self.wasm_sha[:16]}; "
                           f"C's expectation cannot be read from bytes that did not run")
            reports[kind] = (report, path)
            clauses = self.identity(kind, report, path)
            verdict = status({k: (None if v is False else v) for k, v in clauses.items()})
            self.say("identity", verdict, f"{path.name}: runner {report.get('runner')} page "
                     f"{str((report.get('candidate') or {}).get('pageSha256'))[:16]} "
                     + ("ok" if verdict == "PASS" else f"off: {sorted(k for k, v in clauses.items() if not v)}"))
        self.reports = reports
        if "counted" in reports:
            self.counted(*reports["counted"])
        if "counted" in reports and "control" in reports:
            self.control(reports["counted"], reports["control"])
        if "m2-1b" in reports:
            self.m2_1b(*reports["m2-1b"])
        if "m2-4" in reports:
            self.m2_4(*reports["m2-4"])
        if "red" in reports:
            self.red(*reports["red"])
        for kind, names in M2_0.items():
            if kind not in reports:
                continue
            report, path = reports[kind]
            got = {r.get("fixture"): m2_0_record(r, path) for r in report.get("m2_0") or []
                   if r.get("fixture") in names}
            verdict = worst([status(c) for c in got.values()] + (["NOT DONE"] if set(got) != names else []))
            self.say("M2-0", verdict, f"{path.name}: " + ", ".join(
                f"{f} {status(got[f]) if f in got else 'missing'}" for f in sorted(names)))
        for name in ("M2-0", "M2-1", "M2-1b", "M2-2", "M2-3", "barrier", "M2-4", "red", "control"):
            self.verdicts.setdefault(name, "NOT DONE")
        return self.verdicts

    def counted(self, report: dict, path: Path) -> None:
        wanted = {(c, r) for c in self.cases for r in range(1, ROUNDS + 1)}
        ok, note = self.population_of(report, wanted)
        records = [c for c in report.get("cases") or [] if c.get("case") in self.cases]
        decisions = [c["case"] for c in records if c.get("decision") != self.cases[c["case"]]["decision"]]
        if decisions:
            ok, note = False, note + f" decision differs from eshape.json on {decisions[:6]}"
        for criterion in ("M2-1", "M2-3", "barrier"):
            mine = {"cases": [c for c in records if self.cases[c["case"]]["criterion"] == criterion]}
            judge = m2_3_record if criterion == "M2-3" else merge_record
            verdict, bad = self.records(mine, lambda r: judge(r, self.cases[r["case"]], path))
            n = len(mine["cases"])
            expected = POPULATION[criterion] * ROUNDS
            if n != expected or not ok:
                verdict = worst([verdict, "NOT DONE"])
            self.say(criterion, verdict, f"{n} records (expected {expected}: {POPULATION[criterion]} cases x "
                     f"{ROUNDS} rounds); not passing: {bad if bad else 'none'}{note}")
        m2_1 = [c for c in records if self.cases[c["case"]]["criterion"] == "M2-1"]
        self.m2_2(m2_1, POPULATION["M2-1"] * ROUNDS, "counted")

    def m2_2(self, records: list, expected: int, source: str) -> None:
        """30.2 M2-2: every completion, the runner's and the engine's latency, each < BOUND_MS."""
        per = [(c, latency(c, (c.get("keyUndo") or {}).get("keyToUndoMs"))) for c in records]
        bad = [(f"{c.get('case')} r{c.get('round')}", c.get("keyToResponseMs"),
                (c.get("keyUndo") or {}).get("keyToUndoMs")) for c, lat in per if status(lat) != "PASS"]
        verdict = worst([status(lat) for _, lat in per] + (["NOT DONE"] if len(records) != expected else []))
        self.say("M2-2", verdict, f"{source}: {len(records)} completions (expected {expected}); runner "
                 f"{describe([c.get('keyToResponseMs') for c in records])}; engine "
                 f"{describe([(c.get('keyUndo') or {}).get('keyToUndoMs') for c in records])}; "
                 f"not under {BOUND_MS} ms or missing: {bad if bad else 'none'}")

    def control(self, counted: tuple, control: tuple) -> None:
        (counted_report, counted_path), (control_report, control_path) = counted, control
        wanted = {(c, r) for c in self.cases for r in range(1, ROUNDS + 1)}
        ok, note = self.population_of(control_report, wanted)
        try:
            paired = m.pair(counted_path, control_path)
        except SystemExit as error:
            self.say("control", "NOT DONE", f"pair: {error}")
            return
        # Spec 34.1 (b), fable's ruling of 2026-10-08 (findings/evidence/v19/x7-counted-m2/fable-ruling-control.md),
        # witness: v19's X7 reports (b8324a85).  `pair()` compares `toastsAtEnd` verbatim, but a save confirmation's
        # figure is the saved file's size rounded to 0.1 KB, and dc:date and the Rsid move it by a byte or two on
        # every save: C03 straddles 14.25 KB and flipped inside one arm.  §33.3 writes that toast `已存出 N KB`.  A
        # row is forgiven only when `toastsAtEnd` is its one false field and the two lists are equal once each
        # element that FULL-matches SAVED is one token; count, order and every other toast stay verbatim.  `pair()`
        # itself (the runner) is unchanged, so the runner's standalone `--pair` still reports the raw rows.
        cases = {side: {(c.get("case"), c.get("round")): c for c in report.get("cases") or []}
                 for side, report in (("counted", counted_report), ("control", control_report))}

        def saves_as_one(toasts):
            return [SAVE_TOKEN if isinstance(t, str) and SAVED.fullmatch(t) else t for t in toasts]

        def kb_only(row: dict) -> bool:
            if row.get("toastsAtEnd") is not False or any(
                    v is not True for k, v in row.items() if k not in ("case", "round", "toastsAtEnd", "same")):
                return False
            mine, theirs = (cases[side].get((row["case"], row["round"]), {}).get("toastsAtEnd")
                            for side in ("counted", "control"))
            return (isinstance(mine, list) and isinstance(theirs, list)
                    and saves_as_one(mine) == saves_as_one(theirs))

        forgiven = [row for row in paired["differ"] if kb_only(row)]
        differ = [row for row in paired["differ"] if row not in forgiven]
        sides = {}
        for path in (counted_path, control_path):
            docs = path.parent / f"{path.stem}.docs"
            files = {f.name for f in docs.glob("*.odt")} if docs.is_dir() else set()
            sides[path.name] = {kind: {n for n in files if n.endswith(f"-{kind}.odt")} for kind in self.kept}
        a, b = sides.values()
        counts = {kind: [len(a[kind]), len(b[kind])] for kind in self.kept}
        clauses = {"population": ok or None,
                   "pairs": paired["pairs"] == len(wanted) or None,
                   "sameOrder": paired.get("sameOrder") is True,
                   "differ": differ == [],
                   "kept": all(n == [self.kept[k]] * 2 for k, n in counts.items()) or None,
                   "sameKept": all(a[k] == b[k] for k in self.kept)}
        self.say("control", status(clauses), f"pairs {paired['pairs']} (expected {len(wanted)}), differ "
                 f"{len(differ)}; {len(forgiven)} pairs equal up to the KB figure (34.1 (b)"
                 + (f": {[(r['case'], r['round']) for r in forgiven]}" if forgiven else "")
                 + f"); documents compared per kind [counted, control] {counts} (expected "
                 f"{self.kept}){note}" + (f"; differ {differ[:4]}" if differ else ""))

    def m2_1b(self, report: dict, path: Path) -> None:
        typed = [c for c in self.order if self.cases[c]["decision"] == "typed-merge"]
        wanted = {(c, r) for c in typed for r in range(1, M2_1B_RUNS + 1)}
        ok, note = self.population_of(report, wanted)
        records = [c for c in report.get("cases") or [] if c.get("case") in typed]
        verdict, bad = self.records({"cases": records}, lambda r: merge_record(r, self.cases[r["case"]], path))
        if len(wanted) != M2_1B_TOTAL or len(records) != M2_1B_TOTAL or not ok:
            verdict = worst([verdict, "NOT DONE"])
        self.say("M2-1b", verdict, f"{len(records)} records (expected {M2_1B_TOTAL}: {typed} x {M2_1B_RUNS}); "
                 f"not passing: {bad if bad else 'none'}{note}")
        self.m2_2(records, M2_1B_TOTAL, "M2-1b")

    def m2_4(self, report: dict, path: Path) -> None:
        records = [c for c in report.get("cases") or [] if c.get("case") == LIMIT["case"]]
        if len(records) != 1 or len(report.get("cases") or []) != 1:
            self.say("M2-4", "NOT DONE", f"{len(records)} {LIMIT['case']} records of {len(report.get('cases') or [])}")
            return
        clauses, counts = limit_record(records[0], report, path)
        self.say("M2-4", status(clauses), f"{counts}; not true: "
                 f"{sorted(k for k, v in clauses.items() if v is not True) or 'none'}")

    def red(self, report: dict, path: Path) -> None:
        first = [c for c in self.order if self.cases[c]["criterion"] == "M2-1"][:RED_CASES]
        ok, note = self.population_of(report, {(c, 1) for c in first})
        verdict, bad = self.records(report, red_record)
        if not ok:
            verdict = worst([verdict, "NOT DONE"])
        self.say("red", verdict, f"{[c.get('case') for c in report.get('cases') or []]} (expected {first}, on "
                 f"{RED_PROFILE}, each placed, refused and reopened); not red: {bad if bad else 'none'}{note}")


def is_sha256(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def together(reports: list, uncounted: bool) -> tuple[str, str]:
    """Review 2026-10-08 (opus B2; codex B2, B3): across EVERY report of EVERY browser, one runner and one
    candidate page; for a counted verdict the runner is this tree's runner file and the binding is the one
    committed in it (`m.BINDING`), with exactly `m.BOUND_KEYS`, each a sha256 -- not two claims from the same
    report vouching for each other."""
    runners = {r.get("runner") for _, r in reports}
    pages = {(r.get("candidate") or {}).get("pageSha256") for kind, r in reports if kind != "red"}
    clauses = {"reports": bool(reports), "oneRunner": len(runners) == 1, "onePage": len(pages) == 1}
    if not uncounted:
        binding = m.BINDING
        clauses["bindingCommitted"] = (isinstance(binding, dict) and set(binding) == set(m.BOUND_KEYS)
                                       and all(is_sha256(v) for v in binding.values()))
        clauses["thisRunner"] = runners == {RUNNER_SHA}
        clauses["pageIsBound"] = isinstance(binding, dict) and pages == {binding.get("pageSha256")}
        for kind, report in reports:
            bound = report.get("bound") or {}
            keys = [k for k in m.BOUND_KEYS if kind != "red" or k not in m.PROFILE_BOUND]
            clauses[f"bound:{report.get('browser')}:{kind}"] = (
                report.get("counted") is True and report.get("binding") == binding
                and isinstance(binding, dict) and set(bound) == set(m.BOUND_KEYS)
                and all(bound.get(k) == binding.get(k) for k in keys))
    verdict = status({k: (None if v is False else v) for k, v in clauses.items()})
    return verdict, (f"runners {sorted(map(str, runners))} (this runner {RUNNER_SHA}) pages "
                     f"{sorted(str(p)[:16] for p in pages)} "
                     + ("ok" if verdict == "PASS" else f"off: {sorted(k for k, v in clauses.items() if not v)}"))


def judge(directory: Path, profile: str, browsers, uncounted: bool, wasm: Path | None = None) -> tuple[int, list[str]]:
    wasm = wasm or PROFILES / profile / "probe.wasm"
    try:
        boundary_noop, wasm_sha = keying(wasm)
        cases, order = population(boundary_noop)
    except Stop as error:
        return 3, [f"VERDICT NOT DONE: {error}"]
    lines = [f"population (eshape.json {sha256(m.ESHAPE)[:16]}): "
             + ", ".join(f"{k} {sorted(c for c in cases if cases[c]['criterion'] == k)}" for k in POPULATION),
             f"keyed on {wasm} ({wasm_sha[:16]}): C {'declared' if boundary_noop else 'not declared'}, "
             f"nothing-selected expects {expectation('nothing-selected', boundary_noop)[1]}"]
    verdicts, everything = {}, []
    for browser in browsers:
        one = Browser(directory, browser, profile, uncounted, cases, order, wasm_sha)
        try:
            verdicts[browser] = one.run()
        except Stop as error:
            one.say("reports", "NOT DONE", str(error))
            verdicts[browser] = {**one.verdicts, "reports": "NOT DONE"}
        lines += ["", f"## {browser}", *one.lines]
        everything += [(kind, report) for kind, (report, _) in one.reports.items()]
    verdicts["all"] = {}
    verdicts["all"]["identity"], detail = together(everything, uncounted)
    lines += ["", "## all", f"{'identity':<10} {verdicts['all']['identity']:<8} {detail}"]
    fails = [f"{b} {k}" for b, v in verdicts.items() for k, s in v.items() if s == "FAIL"]
    undone = [f"{b} {k}" for b, v in verdicts.items() for k, s in v.items() if s == "NOT DONE"]
    # Review 2026-10-08 (opus B1, codex B1): X7 is both browsers; a narrower run is never a counted verdict.
    partial = sorted(browsers) != sorted(BROWSERS) or len(browsers) != len(BROWSERS)
    if fails:
        code, verdict = 1, f"VERDICT FAIL: {fails}" + (f"; NOT DONE: {undone}" if undone else "")
    elif undone:
        code, verdict = 3, f"VERDICT NOT DONE: {undone}"
    elif uncounted or partial:
        why = [w for w, on in (("uncounted", uncounted), (f"browsers {list(browsers)}", partial)) if on]
        code, verdict = 4, f"VERDICT PASS (NOT A COUNTED VERDICT: {', '.join(why)})"
    else:
        code, verdict = 0, (f"VERDICT PASS ({', '.join(BROWSERS)}; runner {RUNNER_SHA}; page "
                            f"{m.BINDING['pageSha256'][:16]}; wasm {m.BINDING['wasmSha256'][:16]})")
    return code, lines + ["", verdict]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--profile", default="e2-editor-v19")
    ap.add_argument("--browsers", nargs="+", default=list(BROWSERS), choices=BROWSERS)
    ap.add_argument("--uncounted", action="store_true",
                    help="a dry run on reports that are not bound: binding clauses are not judged, and a full "
                         "pass exits 4, never 0")
    ap.add_argument("--wasm", type=Path,
                    help="the engine C's keying is read from (default dist/profiles/<profile>/probe.wasm); its "
                         "sha256 must be what every non-red report bound, e.g. an archived copy for a re-judge")
    args = ap.parse_args()
    code, lines = judge(args.dir, args.profile, args.browsers, args.uncounted, args.wasm)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
