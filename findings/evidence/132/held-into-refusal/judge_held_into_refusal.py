#!/usr/bin/env python3
"""Judge a report of probe_held_into_refusal.py or probe_table_refusal.py against
finding 134's acceptance (SPEC-M3-held-key §14; ruling-1 condition 3) and
ruling-3 conditions 3 and 4 (finding 136, L-134-restore-flash; task 2026-10-13c).

Tool-closed over both probes: the probe is picked by report["probe"]; its arms
are read by `ast` from that probe's own ARMS (a tuple in the held probe; a dict
literal in the table probe, whose keys are the arms).  An arm the probe
declares with no rule here is a FAIL, and so is a required browser with fewer
rounds of an arm than the minimum, and a run of an arm the probe does not
declare.  Exit 0 only when every arm passes on every required browser and the
served and dist page are the one named.

Per round, every arm:
  one reopen     1 refusal, generations 1 -> 2, no limit notice;
  document kept  the server's paragraphs equal the original once the reader
                 has stripped the three marks (`zqx`, `kj`, `wvy`);
  mark counts    each mark exactly once where the arm types it, and absent
                 where it does not (`kjkjk` contains `kj`: a residue of it would
                 be stripped from the comparison, the count catches it).
Placement (booleans and indexes computed by the probe's reader, no text):
  start-press, start-hold   `wvy` in paragraph 0 only, at its start
  end-hold                  `wvy` in the last paragraph only, at its end, right
                            after `zqx` (`zqxwvy` closes the last paragraph)
  end-press-type            `zqx` in the last paragraph only; `kjzqx` contiguous
  before-table-press-type,
  cell-press-type           `kjzqx` contiguous
  before-table-hold         `wvy` in paragraph 0 only, at its end
  cell-hold                 `wvy` in paragraph 1 (cell A1) only, at its end
  cell-start-hold           (ruling-3 addendum 4) positive control first: the
                            refusal stage the probe read from the page's toast
                            is `anchor-mismatch` -- any other stage FAILs as
                            "measures that stage, not D"; then `wvy` in
                            paragraph 1 only, at its start; `kjkjk` fully gone
                            (`kj` count 0 and the document otherwise original)
scrollTop (ruling-3 condition 4).  Samples: the probe's `stateBeforeKey`, then
every state entry of the log, in order.
  end-hold, end-press-type  every sample from the first `restart-required`
                            through the first sample whose toast contains
                            「已重新載入」 (inclusive) is >= 0.5 x the last sample
                            before that refusal.  The window must exist and
                            close, and that last sample must be > 0: at 0 the
                            rule would hold for any page.
  start-press, start-hold   every sample is 0.
  table arms                exempt (the fixture fits one screen); the series is printed.
Rounds per required browser: 2 for start-hold, end-hold and cell-start-hold, 1 otherwise.

A field a report predates is a FAIL "... not recorded", never a pass.  One
exception, for the red case on table run-3 only: that run's reader put
`controlThenMark` under run["control"] (`control_read`, the same definition:
`kj` + `zqx` in one paragraph); it is read there when the server read lacks
it, and the printed source says so.

  judge_held_into_refusal.py REPORT --page SHA256 [--browsers chrome,firefox]
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
PROBES = {
    "probe_held_into_refusal.py": HERE / "probe_held_into_refusal.py",
    "probe_table_refusal.py": HERE.parents[1] / "134" / "table" / "probe_table_refusal.py",
}
STATIC_KEYS = ("hostVersion", "hostCommit", "buildId", "servedPage", "distPage")
RELOADED = "已重新載入"
MISSING = object()


def probe_arms(path: Path) -> tuple[str, ...]:
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "ARMS" for t in node.targets):
            value = ast.literal_eval(node.value)
            return tuple(value.keys()) if isinstance(value, dict) else tuple(value)
    raise SystemExit(f"ARMS not found in {path}")


def field(run: dict[str, Any], name: str) -> tuple[Any, str]:
    srv = run.get("server") or {}
    if name in srv:
        return srv[name], "server"
    if name == "controlThenMark" and name in (run.get("control") or {}):
        return run["control"][name], "run.control (table run-3 reader)"
    return MISSING, "not recorded"


def need(run: dict[str, Any], name: str, failed: list[str]) -> Any:
    value, _ = field(run, name)
    if value is MISSING:
        failed.append(f"{name} not recorded")
    return value


# ------------------------------------------------------------------ rules

def one_reopen(run: dict[str, Any]) -> list[str]:
    s = run["summary"]
    failed = []
    if s["refusals"] != 1:
        failed.append(f"refusals {s['refusals']} != 1")
    if s["generations"] != ["1", "2"]:
        failed.append(f"generations {s['generations']} != ['1', '2']")
    if s["limitSavedMs"] is not None or (run.get("limit") or {}).get("limit") is not None:
        failed.append(f"limit notice {(run.get('limit') or {}).get('limit')!r}")
    return failed


def document_kept(run: dict[str, Any]) -> list[str]:
    srv = run.get("server") or {}
    if srv.get("sameAsOriginal") is True:
        return []
    return [f"server differs after the reader stripped its marks: firstDiff {srv.get('firstDiffFromOriginal')} "
            f"charDelta {srv.get('charDelta')} paragraphs {srv.get('paragraphs')}/{srv.get('paragraphsOriginal')}"]


def counts(mark: int, control: int, after: int) -> Callable[[dict[str, Any]], list[str]]:
    def rule(run: dict[str, Any]) -> list[str]:
        failed: list[str] = []
        for name, want in (("marks", mark), ("controls", control), ("afters", after)):
            got = need(run, name, failed)
            if got is not MISSING and got != want:
                failed.append(f"{name} {got} != {want}")
        return failed
    return rule


def last_index(run: dict[str, Any]) -> int | None:
    paragraphs = (run.get("server") or {}).get("paragraphs")
    return paragraphs - 1 if isinstance(paragraphs, int) else None


def after_at(where: str, index: int | str) -> Callable[[dict[str, Any]], list[str]]:
    """`wvy` only in paragraph `index` ("last" = the last), at its start or end."""
    flag = {"start": "afterAtStart", "end": "afterAtEnd"}[where]

    def rule(run: dict[str, Any]) -> list[str]:
        failed: list[str] = []
        want = last_index(run) if index == "last" else index
        paragraphs, at = need(run, "afterParagraphs", failed), need(run, flag, failed)
        if paragraphs is not MISSING and paragraphs != [want]:
            failed.append(f"AFTER in paragraphs {paragraphs}, expected [{want}]")
        if at is not MISSING and at is not True:
            failed.append(f"AFTER not at the {where} of its paragraph ({flag} {at})")
        return failed
    return rule


def mark_then_after(run: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    value = need(run, "markThenAfter", failed)
    if value is not MISSING and value is not True:
        failed.append(f"MARK then AFTER not contiguous (markThenAfter {value})")
    return failed


def mark_at_end(run: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    paragraphs = need(run, "markParagraphs", failed)
    if paragraphs is not MISSING and paragraphs != [last_index(run)]:
        failed.append(f"mark in paragraphs {paragraphs}, last is {last_index(run)}")
    return failed


def contiguous(run: dict[str, Any]) -> list[str]:
    failed: list[str] = []
    value = need(run, "controlThenMark", failed)
    if value is not MISSING and value is not True:
        failed.append(f"CONTROL then MARK not contiguous (controlThenMark {value})")
    return failed


def samples(run: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    before = run.get("stateBeforeKey")
    if isinstance(before, dict):
        out.append({**before, "t": "beforeKey"})
    out += [e for e in run.get("log") or [] if e.get("what") == "state"]
    return out


def scroll_window(run: dict[str, Any]) -> dict[str, Any]:
    ss = samples(run)
    first = next((k for k, e in enumerate(ss) if e.get("state") == "restart-required"), None)
    if first is None:
        return {"error": "no restart-required sample"}
    if first == 0:
        return {"error": "no sample before the refusal"}
    close = next((k for k in range(first, len(ss)) if RELOADED in (ss[k].get("toast") or "")), None)
    return {"pre": ss[first - 1].get("scroll"), "preAt": ss[first - 1].get("t"),
            "window": [e.get("scroll") for e in ss[first:(close + 1 if close is not None else len(ss))]],
            "from": ss[first].get("t"), "to": ss[close].get("t") if close is not None else None,
            "closed": close is not None}


def scroll_end(run: dict[str, Any]) -> list[str]:
    w = scroll_window(run)
    if "error" in w:
        return [f"scrollTop: {w['error']}"]
    pre, window = w["pre"], w["window"]
    if not w["closed"]:
        return [f"scrollTop: no sample with 「{RELOADED}」 after the refusal"]
    if not isinstance(pre, (int, float)) or pre <= 0:
        return [f"scrollTop: last sample before the refusal is {pre!r} (the rule needs the view away from the start)"]
    low = [s for s in window if not isinstance(s, (int, float)) or s < 0.5 * pre]
    if low:
        return [f"scrollTop: {len(low)} of {len(window)} samples in the reopen window < 0.5 x {pre} "
                f"(lowest {min((s for s in low if isinstance(s, (int, float))), default=None)})"]
    return []


def scroll_start(run: dict[str, Any]) -> list[str]:
    ss = samples(run)
    if not ss:
        return ["scrollTop: no samples"]
    off = [e.get("scroll") for e in ss if e.get("scroll") != 0]
    return [f"scrollTop: {len(off)} of {len(ss)} samples not 0 ({sorted({str(s) for s in off})[:5]})"] if off else []


def anchor_mismatch(run: dict[str, Any]) -> list[str]:
    if "refusalStage" not in run:
        return ["refusalStage not recorded"]
    stage = (run["refusalStage"] or {}).get("stage")
    return [] if stage == "anchor-mismatch" else [f"refusal stage {stage!r}: measures that stage, not D"]


def all_of(*rules: Callable[[dict[str, Any]], list[str]]) -> Callable[[dict[str, Any]], list[str]]:
    return lambda run: [f for rule in rules for f in rule(run)]


RULES: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    # held probe
    "start-press": all_of(one_reopen, document_kept, counts(1, 0, 1), after_at("start", 0), scroll_start),
    "start-hold": all_of(one_reopen, document_kept, counts(1, 0, 1), after_at("start", 0), scroll_start),
    "end-hold": all_of(one_reopen, document_kept, counts(1, 0, 1), after_at("end", "last"), mark_then_after,
                       scroll_end),
    "end-press-type": all_of(one_reopen, document_kept, counts(1, 1, 0), mark_at_end, contiguous, scroll_end),
    # table probe (scrollTop exempt)
    "before-table-press-type": all_of(one_reopen, document_kept, counts(1, 1, 0), contiguous),
    "before-table-hold": all_of(one_reopen, document_kept, counts(0, 0, 1), after_at("end", 0)),
    "cell-press-type": all_of(one_reopen, document_kept, counts(1, 1, 0), contiguous),
    "cell-hold": all_of(one_reopen, document_kept, counts(0, 0, 1), after_at("end", 1)),
    "cell-start-hold": all_of(one_reopen, anchor_mismatch, document_kept, counts(0, 0, 1), after_at("start", 1)),
}
MIN_ROUNDS = {"start-press": 1, "start-hold": 2, "end-hold": 2, "end-press-type": 1,
              "before-table-press-type": 1, "before-table-hold": 1, "cell-press-type": 1, "cell-hold": 1,
              "cell-start-hold": 2}
SCROLL = {"start-press": "start", "start-hold": "start", "end-hold": "end", "end-press-type": "end"}


# ------------------------------------------------------------------ printing

def scroll_series(run: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    for e in samples(run):
        if "scroll" in e and (not out or out[-1] != e["scroll"]):
            out.append(e["scroll"])
    return out


def raw_lines(arm: str, run: dict[str, Any]) -> list[str]:
    s, srv = run["summary"], run.get("server") or {}
    show = lambda name: (lambda v: "-" if v[0] is MISSING else f"{v[0]}" + (  # noqa: E731
        "" if v[1] == "server" else f" [{v[1]}]"))(field(run, name))
    lines = [
        f"    reopen   refusals {s['refusals']} gens {s['generations']} limit {(run.get('limit') or {}).get('limit')}",
        f"    server   same {srv.get('sameAsOriginal')} firstDiff {srv.get('firstDiffFromOriginal')} "
        f"charDelta {srv.get('charDelta')} paragraphs {srv.get('paragraphs')}/{srv.get('paragraphsOriginal')}",
        f"    counts   marks {show('marks')} controls {show('controls')} afters {show('afters')}",
        f"    where    mark {show('markParagraphs')} control {show('controlParagraphs')} after {show('afterParagraphs')}",
        f"    bools    controlThenMark {show('controlThenMark')} markThenAfter {show('markThenAfter')} "
        f"afterAtStart {show('afterAtStart')} afterAtEnd {show('afterAtEnd')}",
    ]
    if arm == "cell-start-hold":
        lines.append(f"    cell     refusalStage {run.get('refusalStage', '-')} cellStart {run.get('cellStart', '-')}")
    kind = SCROLL.get(arm)
    if kind == "end":
        w = scroll_window(run)
        lines.append(f"    scroll   series {scroll_series(run)} | window {w}")
    else:
        lines.append(f"    scroll   series {scroll_series(run)}" + ("" if kind else " (exempt)"))
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--page", required=True, help="sha256 the served and dist page must both be")
    parser.add_argument("--browsers", default="chrome,firefox")
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    failures: list[str] = []

    path = PROBES.get(report.get("probe"))
    if path is None:
        print(f"FAIL report['probe'] {report.get('probe')!r} is none of {sorted(PROBES)}")
        print("verdict FAIL (1)")
        return 1
    arms = probe_arms(path)
    print("probe", report["probe"], "arms", list(arms))

    static, after = report.get("static") or {}, report.get("staticAfter") or {}
    print("static", {k: static.get(k) for k in STATIC_KEYS})
    for key in ("servedPage", "distPage"):
        if static.get(key) != args.page:
            failures.append(f"static: {key} {static.get(key)} != {args.page}")
    if any(static.get(k) != after.get(k) for k in STATIC_KEYS):
        failures.append(f"static: staticAfter differs {[k for k in STATIC_KEYS if static.get(k) != after.get(k)]}")

    for run in report["runs"]:
        if run["arm"] not in arms:
            failures.append(f"{run['browser']} {run['arm']} r{run.get('round', 0)}: arm not in the probe's ARMS")
    for arm in arms:
        rule = RULES.get(arm)
        if rule is None or arm not in MIN_ROUNDS:
            failures.append(f"{arm}: no rule for an arm the probe declares")
            continue
        for browser in args.browsers.split(","):
            runs = [r for r in report["runs"] if r["arm"] == arm and r["browser"] == browser]
            if len(runs) < MIN_ROUNDS[arm]:
                failures.append(f"{browser} {arm}: {len(runs)} rounds < {MIN_ROUNDS[arm]}")
            for run in runs:
                head = f"{browser} {arm} r{run.get('round', 0)}"
                if run.get("fatal"):
                    failures.append(f"{head}: fatal {run['fatal'].strip().splitlines()[-1]}")
                    print(head, "FAIL fatal")
                    continue
                failed = rule(run)
                print(head, "FAIL" if failed else "PASS")
                for line in raw_lines(arm, run):
                    print(line)
                for f in failed:
                    print("    -", f)
                failures.extend(f"{head}: {f}" for f in failed)
    for f in failures:
        print("FAIL", f)
    print("verdict", "PASS" if not failures else f"FAIL ({len(failures)})")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
