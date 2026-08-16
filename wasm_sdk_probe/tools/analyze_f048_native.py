#!/usr/bin/env python3
"""Judge finding 048's native arm offline, against predictions written first.

The probe emits absolute timestamps and nothing else; every number below is
derived here.  The criteria are the ones in
findings/evidence/048/native/PREDICTION.md, which was written before
tools/f048_native_click_latency.cpp existed.

Two derived numbers per repetition, both inside the window
[event=post, event=drain-end]:

  firstCallbackMs  post -> the first callback of any type
  cursorRectMs     post -> the first LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR
                   whose rectangle is on the requested line

"On the requested line" uses half the rectangle's own height as the tolerance --
the rectangle IS the line box, so no twips constant has to be invented.  That is
the same rule the product's placeCaret uses.

Usage:
  python3 tools/analyze_f048_native.py RUN_DIR [RUN_DIR ...]
  python3 tools/analyze_f048_native.py --self-test RUN_DIR
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

CURSOR_CALLBACK = 1  # LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR

# The WASM profile every browser measurement in finding 048 was taken on.  A
# native run built from a different commit compares two things at once.
EXPECTED_CORE_COMMIT = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"

# Registered in PREDICTION.md before the probe was written.
DECISION_UPSTREAM_MS = 20.0
DECISION_OURS_MS = 2.0


def read_lines(run: Path) -> list[dict]:
    records = []
    for line in (run / "arms.jsonl").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            # A torn line is a measurement problem, not something to skip
            # quietly: the probe serialises its writes precisely so this cannot
            # happen, and if it did, the round is not usable.
            raise SystemExit(f"{run}: unparseable JSONL line: {line[:120]!r}")
    return records


def parse_rectangle(payload: str) -> tuple[int, int, int, int] | None:
    parts = [part.strip() for part in (payload or "").split(",")]
    if len(parts) < 4:
        return None
    try:
        return tuple(int(part) for part in parts[:4])  # type: ignore[return-value]
    except ValueError:
        return None


def windows(records: list[dict]) -> list[dict]:
    """Pair every post with its drain-end and collect the callbacks between."""
    result = []
    open_window: dict | None = None
    for record in records:
        if record.get("event") == "post":
            open_window = {
                "arm": record["arm"],
                "rep": record["rep"],
                "kind": record["kind"],
                "targetX": record["targetX"],
                "targetY": record["targetY"],
                "command": record.get("command"),
                "postMs": record["atMs"],
                "callbacks": [],
            }
            continue
        if record.get("event") == "drain-end":
            if open_window is None:
                raise SystemExit("drain-end without a post")
            open_window["drainEndMs"] = record["atMs"]
            result.append(open_window)
            open_window = None
            continue
        if open_window is not None and "callback" in record:
            open_window["callbacks"].append(record)
    if open_window is not None:
        raise SystemExit("a post never reached its drain-end")
    return result


def measure(window: dict) -> dict:
    post = window["postMs"]
    callbacks = window["callbacks"]
    first = callbacks[0]["atMs"] - post if callbacks else None

    cursor = None
    for record in callbacks:
        if record.get("callback") != CURSOR_CALLBACK:
            continue
        rectangle = parse_rectangle(record.get("payload", ""))
        if rectangle is None:
            continue
        _, y, _, height = rectangle
        target = window["targetY"]
        if target < 0:  # cursor commands aim at no coordinate
            cursor = record["atMs"] - post
            break
        # The click aims at the MIDDLE of the line (targetY = rect.y + h/2), so
        # the comparison has to be middle-against-middle.  Comparing the
        # callback rectangle's TOP against a mid-line target puts every correct
        # landing exactly on the tolerance boundary, where rounding decides the
        # verdict -- three of round one's five N2 repetitions were scored as
        # misses by that arithmetic while the caret was on the right line.
        tolerance = max(height // 2, 1)
        if abs((y + height // 2) - target) <= tolerance:
            cursor = record["atMs"] - post
            break

    return {
        "arm": window["arm"],
        "rep": window["rep"],
        "kind": window["kind"],
        "command": window.get("command"),
        "targetY": window["targetY"],
        "callbackCount": len(callbacks),
        "callbackNames": sorted({record.get("name", "?") for record in callbacks}),
        "firstCallbackMs": first,
        "cursorRectMs": cursor,
    }


def median(values: list[float]) -> float | None:
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def by_arm(measurements: list[dict]) -> dict[str, dict]:
    arms: dict[str, dict] = {}
    for entry in measurements:
        arm = arms.setdefault(entry["arm"], {"reps": [], "first": [], "cursor": [],
                                             "callbackCounts": []})
        arm["reps"].append(entry)
        arm["first"].append(entry["firstCallbackMs"])
        arm["cursor"].append(entry["cursorRectMs"])
        arm["callbackCounts"].append(entry["callbackCount"])
    for arm in arms.values():
        arm["firstCallbackMedianMs"] = median(arm["first"])
        arm["cursorRectMedianMs"] = median(arm["cursor"])
        arm["cursorRectSamples"] = len([v for v in arm["cursor"] if v is not None])
    return arms


def status_of(held: bool | None, measured_exists: bool) -> str:
    """HELD / FAILED / NOT_MEASURED -- never fold the third into the second.

    A prediction with no data behind it is not a refuted prediction.  Scoring
    P-N4 as FAILED when `.uno:GoDown` emitted no callback at all would report a
    measurement that never happened as a result, which is the confusion the
    `notValidated` rule exists to prevent everywhere else in this tree.
    """
    if not measured_exists:
        return "NOT_MEASURED"
    return "HELD" if held else "FAILED"


def score(arms: dict[str, dict]) -> list[dict]:
    """The five predictions, scored exactly as registered."""
    def arm(name: str) -> dict:
        return arms.get(name, {})

    def value(name: str, key: str):
        return arm(name).get(key)

    predictions = []

    n1_first = value("N1", "firstCallbackMedianMs")
    predictions.append({
        "id": "P-N1",
        "text": "N1.firstCallbackMs median < 5 ms",
        "measured": n1_first,
        "held": n1_first is not None and n1_first < 5.0,
        "status": status_of(n1_first is not None and n1_first < 5.0,
                            n1_first is not None),
    })

    n1_cursor = value("N1", "cursorRectMedianMs")
    gap = (abs(n1_cursor - n1_first)
           if n1_cursor is not None and n1_first is not None else None)
    predictions.append({
        "id": "P-N2",
        "text": "|N1.cursorRectMs - N1.firstCallbackMs| median < 2 ms "
                "(if it holds, hypothesis B does not)",
        "measured": gap,
        "held": gap is not None and gap < 2.0,
        "status": status_of(gap is not None and gap < 2.0, gap is not None),
    })

    n3_counts = arm("N3").get("callbackCounts", [])
    predictions.append({
        "id": "P-N3",
        "text": "N3 (click where the caret already is) produces zero callbacks",
        "measured": n3_counts,
        "held": bool(n3_counts) and all(count == 0 for count in n3_counts),
        "status": status_of(bool(n3_counts)
                            and all(count == 0 for count in n3_counts),
                            bool(n3_counts)),
    })

    n2_cursor = value("N2", "cursorRectMedianMs")
    n4_cursor = value("N4", "cursorRectMedianMs")
    within = (n2_cursor is not None and n4_cursor is not None and n2_cursor > 0
              and 0.5 <= (n4_cursor / n2_cursor) <= 2.0)
    predictions.append({
        "id": "P-N4",
        "text": "N4.cursorRectMs within 2x of N2.cursorRectMs",
        "measured": {"N2": n2_cursor, "N4": n4_cursor},
        "held": within,
        "status": status_of(within,
                            n2_cursor is not None and n4_cursor is not None),
    })

    n5_cursor = value("N5", "cursorRectMedianMs")
    predictions.append({
        "id": "P-N5",
        "text": "N5.cursorRectMs <= N2.cursorRectMs",
        "measured": {"N2": n2_cursor, "N5": n5_cursor},
        "held": n5_cursor is not None and n2_cursor is not None
                and n5_cursor <= n2_cursor,
        "status": status_of(n5_cursor is not None and n2_cursor is not None
                            and n5_cursor <= n2_cursor,
                            n2_cursor is not None and n5_cursor is not None),
    })

    return predictions


def decide(n2_medians: list[float]) -> dict:
    """The rule registered in advance, applied to N2's median across runs."""
    usable = [value for value in n2_medians if value is not None]
    if not usable:
        return {"verdict": "NO_DATA",
                "why": "no repetition produced a cursor rectangle on the "
                       "requested line"}
    across = statistics.median(usable)
    spread = (max(usable) / min(usable)) if min(usable) > 0 else float("inf")
    if len(usable) > 1 and spread >= 10:
        return {"verdict": "VOID", "medianMs": across, "spread": spread,
                "why": "executions disagree by an order of magnitude; this "
                       "measured the host, not the engine"}
    if across >= DECISION_UPSTREAM_MS:
        return {"verdict": "UPSTREAM_CANDIDATE", "medianMs": across,
                "why": f"native click latency >= {DECISION_UPSTREAM_MS} ms, so "
                       "the wait is core's own"}
    if across <= DECISION_OURS_MS:
        # Deliberately narrower than the branch was first worded.  PREDICTION.md
        # addendum A2 (registered while both attempts still held zero arm data)
        # records why: finding 040 was clean natively, broken on WASM, and still
        # upstream.  A fast native click rules core's click handling out; it does
        # not elect a culprit.
        return {"verdict": "OUR_SIDE", "medianMs": across,
                "why": f"native click latency <= {DECISION_OURS_MS} ms: the wait "
                       "is NOT in core's click handling.  Where it is -- our "
                       "transport and worker scheduling, or the Emscripten "
                       "main-loop integration -- is a further measurement, and "
                       "neither may be named until it is made"}
    return {"verdict": "NOT_SEPARATED", "medianMs": across,
            "why": f"between {DECISION_OURS_MS} and {DECISION_UPSTREAM_MS} ms: "
                   "name the next variable rather than picking the nearer edge"}


def analyse(run: Path) -> dict:
    records = read_lines(run)
    measurements = [measure(window) for window in windows(records)]
    arms = by_arm(measurements)
    context = {}
    context_path = run / "context.json"
    if context_path.is_file():
        context = json.loads(context_path.read_text(encoding="utf-8"))
    commit = context.get("coreCommit")
    return {
        "run": str(run),
        "coreCommit": commit,
        "coreCommitMatchesWasmProfile": commit == EXPECTED_CORE_COMMIT,
        "arms": {name: {key: arm[key] for key in
                        ("firstCallbackMedianMs", "cursorRectMedianMs",
                         "cursorRectSamples", "callbackCounts")}
                 for name, arm in arms.items()},
        "measurements": measurements,
        "predictions": score(arms),
    }


def self_test(run: Path) -> int:
    """Every predicate that can turn the verdict has to be shown to move.

    The mutations run against a COPY of the recorded numbers and never write
    into findings/.  A self-test that only demands "it goes red" stops working
    on evidence that is already red, which is exactly when the judgement
    matters -- so each mutation must CHANGE the outcome, in either direction.
    """
    baseline = analyse(run)
    failures = []

    def held(report: dict, prediction_id: str):
        for prediction in report["predictions"]:
            if prediction["id"] == prediction_id:
                return prediction["status"]
        return None

    records = read_lines(run)
    base_windows = windows(records)

    def rebuild(mutate) -> dict:
        cloned = json.loads(json.dumps(base_windows))
        mutate(cloned)
        arms = by_arm([measure(window) for window in cloned])
        return {"predictions": score(arms), "arms": arms}

    def delay_all(cloned, arm_name, amount):
        for window in cloned:
            if window["arm"] != arm_name:
                continue
            for callback in window["callbacks"]:
                callback["atMs"] += amount

    mutations = [
        ("P-N1 moves when N1's callbacks are delayed 50 ms",
         lambda cloned: delay_all(cloned, "N1", 50.0), "P-N1"),
        ("P-N3 moves when N3 gains a callback",
         lambda cloned: [window["callbacks"].append(
             {"callback": 1, "name": "INVALIDATE_VISIBLE_CURSOR",
              "payload": "0, 0, 0, 0", "atMs": window["postMs"] + 1})
             for window in cloned if window["arm"] == "N3"], "P-N3"),
        ("P-N5 moves when N5's callbacks are delayed 500 ms",
         lambda cloned: delay_all(cloned, "N5", 500.0), "P-N5"),
        # N4 emitted nothing on this fixture, so delaying its callbacks moves
        # nothing.  The mutation that has to move the verdict is the one that
        # gives the arm data: NOT_MEASURED -> HELD/FAILED is a change of
        # verdict, and it is the change this arm can actually undergo.
        ("P-N4 moves when N4 gains a cursor rectangle",
         lambda cloned: [window["callbacks"].append(
             {"callback": 1, "name": "INVALIDATE_VISIBLE_CURSOR",
              "payload": "0, -1, 0, 0", "atMs": window["postMs"] + 300.0})
             for window in cloned if window["arm"] == "N4"], "P-N4"),
    ]

    for name, mutate, prediction_id in mutations:
        mutated = rebuild(mutate)
        before = held(baseline, prediction_id)
        after = next(p["status"] for p in mutated["predictions"]
                     if p["id"] == prediction_id)
        if before == after:
            failures.append(f"{name}: verdict unchanged ({before})")

    # The decision rule itself has to be shown to move, or the whole offline
    # judgement is decoration.
    for medians, expected in ((([0.4], "OUR_SIDE"),
                               ([25.0], "UPSTREAM_CANDIDATE"),
                               ([8.0], "NOT_SEPARATED"),
                               ([0.5, 40.0], "VOID"),
                               ([], "NO_DATA"))):
        got = decide(medians)["verdict"]
        if got != expected:
            failures.append(f"decide({medians}) = {got}, expected {expected}")

    for failure in failures:
        print(f"FAIL {failure}")
    print(f"self-test: {len(mutations) + 5 - len(failures)}/{len(mutations) + 5} "
          "checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.self_test:
        return self_test(args.runs[0])

    reports = [analyse(run) for run in args.runs]
    n2_medians = [report["arms"].get("N2", {}).get("cursorRectMedianMs")
                  for report in reports]
    summary = {
        "schemaVersion": 1,
        "finding": "048",
        "arm": "native",
        "runs": reports,
        "decision": decide(n2_medians),
        "predictionFile": "findings/evidence/048/native/PREDICTION.md",
    }
    text = json.dumps(summary, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
