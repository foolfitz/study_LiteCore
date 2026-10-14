#!/usr/bin/env python3
"""The judge of the v20 shakedown's reports (findings/evidence/link-batch/v20-shakedown/ARMS.md).

Reads every `report-*.json` in a directory (what `run_v20_shakedown.py` wrote), prints one verdict
per arm per browser with every failing line named, and exits 0 only when every criterion arm is
PASS on both browsers and no criterion arm is missing.  P2-c is a measurement: it prints its
reading (ESTABLISHED / NOT_ESTABLISHED) and never decides the exit code.

Red cases (`--self-test`, also `tests/test_v20_shakedown_judge.py`): synthetic reports that pass,
then one mutation per red case in ARMS.md; each must turn the targeted verdict red, and a report
without a measurement must read NOT_ESTABLISHED, never PASS.  §34.3: the two-seat review was run
2026-10-14 (v20-shakedown/review/, DISPOSITION.md); its fixes are the ones marked "review" below
and in run_v20_shakedown.py.  After it the judge is frozen for its first counted use (§34.4).

  judge_v20_shakedown.py --dir findings/evidence/link-batch/v20-shakedown --expect-page SHA256
  judge_v20_shakedown.py --self-test

`--expect-page` is required: without it no report is bound to the page under test (review, opus Q6).
One report per (browser, arm): a second one in the directory FAILS the cell whatever its verdict, so a
re-run left beside the report it supersedes cannot hide a FAIL (review, opus Q6 = codex 6); move the
superseded report under `witness/`, as README §6 does.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

CRITERION_ARMS = ("p1-60", "p1-mixed", "p2", "p3", "c1", "e2")
MEASUREMENT_ARMS = ("p2c",)
BROWSERS = ("chrome", "firefox")
C1_REQUIRED_ROUNDS = 6
E2_REQUIRED_INSTANCES = 6       # ARMS.md E2: C15, C16, C17, F01, F02 and the hold across a merge
PASS, FAIL, NE = "PASS", "FAIL", "NOT_ESTABLISHED"
# The page the synthetic reports claim to be about (ARMS.md's repointed v67 page); the self-test's
# expected page, so that the self-test exercises the binding too.
SYNTHETIC_PAGE = "53019168651b6b4686f1baaba9aa75e0b566d02a3e2cc8a8e8ed4339f360bfd7"


def m_of(text) -> int | None:
    """M from `第 … 頁，共 M 頁`."""
    match = re.search(r"共 (\d+) 頁", text or "")
    return int(match.group(1)) if match else None


def judge_p1(result: dict) -> tuple[str, list[str]]:
    positions = result.get("positions") or []
    if result.get("runnerError"):
        return NE, [f"runner error: {result['runnerError']}"]
    if not result.get("reply") or not positions:
        return NE, [result.get("verdictNote") or "no rectangles reply or no positions: nothing was measured"]
    lines = []
    for p in positions:
        if p.get("expected") is None:
            lines.append(f"{p['kind']} page {p['page']}: no expectation (region or rectangles missing)")
        elif p.get("hidden") is not False:
            lines.append(f"{p['kind']} page {p['page']}: #page-status hidden")
        elif p.get("text") != p.get("expected"):
            lines.append(f"{p['kind']} page {p['page']}: text {p.get('text')!r} != expected {p['expected']!r}")
    if result.get("partsEqualsCount") is not True:
        lines.append(f"M {result['reply'].get('count')} != parts {result['reply'].get('parts')}")
    return (FAIL if lines else PASS), lines


def judge_p2(result: dict) -> tuple[str, list[str]]:
    if result.get("runnerError"):
        return NE, [f"runner error: {result['runnerError']}"]
    add, remove = result.get("add") or {}, result.get("remove") or {}
    if not add or not add.get("presses"):
        return NE, [result.get("verdictNote") or "no Enter press was sent: nothing was measured"]
    lines = []
    for label, part in (("add", add), ("remove", remove)):
        if not part:
            lines.append(f"{label}: not run")
            continue
        text_m = m_of(part.get("textAt2s"))
        if part.get("hiddenAt2s") is not False:
            lines.append(f"{label}: #page-status hidden at +2 s")
        if text_m != part.get("expectedM"):
            lines.append(f"{label}: text at +2 s says M={text_m}, expected {part.get('expectedM')}")
        if part.get("countAt2s") != part.get("expectedM"):
            lines.append(f"{label}: the engine's latest reply has {part.get('countAt2s')} rectangles, expected {part.get('expectedM')}")
        if text_m is not None and part.get("countAt2s") is not None and text_m != part.get("countAt2s"):
            lines.append(f"{label}: text M {text_m} and reply count {part.get('countAt2s')} disagree")
        # ARMS: count = parts = M.  `None` was accepted before the review (codex 1): the runner's fallback
        # wrote the count into parts, so a missing parts was never seen; now it is a missing measurement.
        if part.get("partsAt2s") != part.get("expectedM"):
            lines.append(f"{label}: parts {part.get('partsAt2s')} != expected {part.get('expectedM')}")
    return (FAIL if lines else PASS), lines


def judge_p3(result: dict) -> tuple[str, list[str]]:
    if result.get("runnerError"):
        return NE, [f"runner error: {result['runnerError']}"]
    if not result.get("nonVacuous"):
        why = []
        if not result.get("paintsInWindow"):
            why.append("no paint request during the scroll")
        if not result.get("reachedBottom"):
            why.append("the scroll never reached the bottom")
        return NE, why or ["vacuous: the scroll did not drive the page"]
    lines = []
    if result.get("untriggeredRequests"):
        lines.append(f"{result['untriggeredRequests']} pageRectangles request(s) during the scroll with no size-change "
                     f"trigger in the 2 s before them (requests {result.get('pageRectanglesRequestsInWindow')}, "
                     f"triggers {result.get('triggersInWindow')})")
    return (FAIL if lines else PASS), lines


def judge_c1(result: dict) -> tuple[str, list[str]]:
    if result.get("runnerError"):
        return NE, [f"runner error: {result['runnerError']}"]
    rounds = result.get("rounds") or []
    judged = [r for r in rounds if "clauses" in r]
    if not judged:
        return NE, [f"no round was judged ({len(rounds)} rounds, "
                    f"{sum(1 for r in rounds if r.get('outcome') == 'placement-mismatch')} placement mismatches)"]
    lines = []
    for r in judged:
        for clause, held in r["clauses"].items():
            if held is not True:
                detail = ""
                if clause == "completionIsBoundaryNoop":
                    a = r.get("answer") or {}
                    detail = f" (ok={a.get('ok')} completion={a.get('completion')} code={a.get('code')} gen={r.get('generationAfter')})"
                if clause == "noSelectionAt500ms":
                    detail = f" (engine read: {json.dumps((r.get('engineRead') or {}).get('result'), ensure_ascii=False)})"
                lines.append(f"{r['case']} r{r['round']}: {clause} failed{detail}")
    if len(judged) < C1_REQUIRED_ROUNDS:
        lines.append(f"rounds judged {len(judged)} < {C1_REQUIRED_ROUNDS} "
                     f"(placement mismatches {result.get('placementMismatches')})")
    return (FAIL if lines else PASS), lines


def judge_e2(result: dict) -> tuple[str, list[str]]:
    if result.get("runnerError"):
        return NE, [f"runner error: {result['runnerError']}"]
    cases = result.get("cases") or []
    hold = result.get("hold") or {}
    # The hold is §10.6's "held across a merge": its refusal is an instance only after >= 1 merge.
    hold_judged = "judge" in hold and isinstance(hold.get("merges"), int) and hold["merges"] >= 1
    judged = [c for c in cases if "judge" in c] + ([hold] if hold_judged else [])
    notes = [f"{c['case']}: {c['outcome']} -- {c.get('note')}" for c in cases if c.get("note")]
    notes += [f"{c['case']}: {c['outcome']}" for c in cases if c.get("outcome") in ("placement-mismatch", "no-answer")]
    if hold and "judge" not in hold:
        notes.append(f"hold: {hold.get('outcome') or hold.get('error')} (merges {hold.get('merges')})")
    elif hold and not hold_judged:
        notes.append(f"hold: refused before any merge (merges {hold.get('merges')}); not an instance of the hold across a merge")
    if not judged:
        return NE, ["no refusal was observed: caretBefore could not be judged"] + notes
    lines = []
    for c in judged:
        label = c.get("case") or "hold"
        for clause, held in c["judge"]["clauses"].items():
            if held is not True:
                lines.append(f"{label}: {clause} failed (caretBefore {json.dumps(c['judge'].get('caretBefore'))}, "
                             f"reference {json.dumps((c['judge'].get('referenceCaret') or {}).get('caret'))})")
    # A partial run is not a PASS (§34.2 "只跑一部分"): C1's `< 6` had this, E2 did not, so a hold that
    # raised, a runner killed after two cases, or four placement mismatches read PASS (review, opus Q3).
    if len(judged) < E2_REQUIRED_INSTANCES:
        lines.append(f"instances judged {len(judged)} < {E2_REQUIRED_INSTANCES} (ARMS.md E2: five cases and the hold)")
    return (FAIL if lines else PASS), lines + notes


def judge_p2c(result: dict) -> tuple[str, list[str]]:
    if result.get("runnerError"):
        return NE, [f"runner error: {result['runnerError']}"]
    if not result.get("lokEventsSeen"):
        return NE, ["no lok events seen: the trace worker did not run, nothing is established either way"]
    lines = []
    for phase in result.get("phases") or []:
        o = phase.get("openAndSettle") or {}
        lines.append(f"{phase['fixture']}: lok {o.get('lokEvents')}, size changes {o.get('sizeChanges')}, "
                     f"lone {len(o.get('lone') or [])}, flanked {o.get('flanked')}, parts first/settled "
                     f"{phase.get('partsFirst')}/{phase.get('partsSettled')}, lazy layout {phase.get('lazyLayout')}, "
                     f"counter at open/settled {phase.get('documentSizeChangedCountAtOpen')}/{phase.get('documentSizeChangedCountSettled')}")
        e = (phase.get("edits") or {}).get("lokDuringSettles")
        if e:
            lines.append(f"{phase['fixture']} edits: lok {e.get('lokEvents')}, size changes {e.get('sizeChanges')}, "
                         f"lone {len(e.get('lone') or [])}, flanked {e.get('flanked')}")
            for n in (phase.get("edits") or {}).get("sizeChangeNeighbours") or []:
                lines.append(f"    size change at {n['tw']} ms, within ±25 ms: {n['near'] or 'nothing'}")
    reading = "ESTABLISHED" if result.get("loneSizeChanges") else NE
    return reading, lines


JUDGES = {"p1-60": judge_p1, "p1-mixed": judge_p1, "p2": judge_p2, "p3": judge_p3, "c1": judge_c1, "e2": judge_e2,
          "p2c": judge_p2c}


def judge_reports(reports: list[dict], expect_page: str | None) -> tuple[int, list[str]]:
    out: list[str] = []
    verdicts: dict[tuple[str, str], str] = {}
    if not expect_page:
        return 1, ["VERDICT NOT GIVEN: no expected page (--expect-page SHA256); without it no report is bound "
                   "to the page under test and nothing is judged"]
    for report in reports:
        browser = report.get("browser")
        ident = report.get("identity") or {}
        if ident.get("pageServedSha256") != expect_page:
            out.append(f"[{browser}] REPORT page {ident.get('pageServedSha256')} != expected {expect_page}: "
                       "this report is about another page and is not read")
            continue
        if report.get("counted") is not False:
            out.append(f"[{browser}] REPORT says counted={report.get('counted')}; a shakedown must say false")
        for arm, result in (report.get("results") or {}).items():
            if (browser, arm) in verdicts:
                # Order-independent: whichever of the two is read first, the cell is FAIL.
                out.append(f"[{browser}] {arm}: DUPLICATE -- a second report for this cell (the first read "
                           f"{verdicts[(browser, arm)]}); one report per (browser, arm), move the superseded one out")
                verdicts[(browser, arm)] = FAIL
                continue
            judge = JUDGES.get(arm)
            if judge is None:
                out.append(f"[{browser}] {arm}: no rule for an arm the runner declares")
                verdicts[(browser, arm)] = FAIL
                continue
            verdict, lines = judge(result)
            if arm in MEASUREMENT_ARMS and ident.get("instrumentedWorker") is not True:
                lines.append("the report does not say instrumentedWorker: true; p2c's bytes must be declared")
            if arm not in MEASUREMENT_ARMS and ident.get("instrumentedWorker") is True:
                verdict, lines = FAIL, lines + ["a criterion arm ran on the instrumented (trace) worker"]
            verdicts[(browser, arm)] = verdict
            out.append(f"[{browser}] {arm}: {verdict}" + (f" ({result.get('seconds')} s)" if result.get("seconds") else ""))
            out += [f"    {line}" for line in lines]
    missing = [(b, a) for b in BROWSERS for a in CRITERION_ARMS if (b, a) not in verdicts]
    for b, a in missing:
        out.append(f"[{b}] {a}: MISSING")
    # An arm the runner declares and this judge has no rule for is a failure (the 136 judge's precedent:
    # "no rule for an arm the probe declares"), not a line that scrolls past.
    failures = [k for k, v in verdicts.items() if (k[1] in CRITERION_ARMS or k[1] not in JUDGES) and v != PASS]
    verdict = PASS if not failures and not missing else FAIL
    out.append(f"VERDICT {verdict} ({len(failures)} criterion cells not PASS, {len(missing)} missing)")
    return (0 if verdict == PASS else 1), out


def load_reports(directory: Path) -> list[dict]:
    reports = []
    for path in sorted(directory.glob("report-*.json")):
        reports.append(json.loads(path.read_text(encoding="utf-8")))
    return reports


# ------------------------------------------------------------------ self-test (the red cases)

def synthetic_report(browser: str, instrumented: bool = False) -> dict:
    rects = [{"x": 284, "y": 284 + i * 17122, "width": 11906, "height": 16838} for i in range(60)]
    positions = []
    for i in range(60):
        positions.append({"kind": "centre", "page": i + 1, "expected": f"第 {i + 1} 頁，共 60 頁",
                          "text": f"第 {i + 1} 頁，共 60 頁", "hidden": False, "pass": True})
    for i in range(59):
        positions.append({"kind": "boundary", "page": i + 1, "expected": f"第 {i + 1}–{i + 2} 頁，共 60 頁",
                          "text": f"第 {i + 1}–{i + 2} 頁，共 60 頁", "hidden": False, "pass": True})
    c1_round = {"case": "C29", "round": 1, "answer": {"ok": True, "completion": "verified-boundary-noop", "changed": False,
                                                       "rev": 0, "beforeRev": 0, "boundaryNoop": {"waitedMs": 2251}},
                "engineRead": {"answered": True, "ok": True,
                               "result": {"sel": {"collapsed": True, "n": 0, "observed": True}, "selectionType": "none"}},
                "generationAfter": "1", "outcome": "noop", "toastsBeforeKey": 3, "toastsAfterKey": [],
                "clauses": {"completionIsBoundaryNoop": True, "changedFalse": True, "revisionUnchanged": True,
                            "waitedMsPresent": True, "generationStays1": True, "engineReadAnswered": True,
                            "noSelectionAt500ms": True, "noToast": True}, "pass": True}
    rounds = []
    for r in (1, 2, 3):
        for case in ("C29", "C30"):
            rounds.append({**copy.deepcopy(c1_round), "case": case, "round": r})
    caret = {"x": 2684, "y": 7266, "width": 0, "height": 276}
    e2_case = {"case": "C17", "outcome": "refused",
               "judge": {"caretBefore": {"rect": dict(caret), "sourceSequence": 40, "source": "P"},
                         "referenceCaret": {"caret": dict(caret), "seq": 41},
                         "clauses": {"caretBeforePresent": True, "rectNotNull": True, "rectEqualsReference": True,
                                     "sequenceNotAfterReference": True}}, "pass": True}
    e2_cases = [{**copy.deepcopy(e2_case), "case": case} for case in ("C15", "C16", "C17", "F01", "F02")]
    return {"browser": browser, "counted": False,
            "identity": {"pageServedSha256": SYNTHETIC_PAGE, "instrumentedWorker": instrumented},
            "results": {
                "p1-60": {"arm": "p1-60", "reply": {"parts": 60, "count": 60}, "positions": positions,
                          "partsEqualsCount": True, "ok": True},
                "p1-mixed": {"arm": "p1-mixed", "reply": {"parts": 8, "count": 8},
                             "positions": [{"kind": "centre", "page": 1, "expected": "第 1 頁，共 8 頁",
                                            "text": "第 1 頁，共 8 頁", "hidden": False, "pass": True}],
                             "partsEqualsCount": True, "ok": True},
                "p2": {"arm": "p2", "add": {"presses": 31, "textAt2s": "第 61 頁，共 61 頁", "hiddenAt2s": False,
                                           "countAt2s": 61, "partsAt2s": 61, "expectedM": 61, "pass": True},
                       "remove": {"presses": 31, "textAt2s": "第 60 頁，共 60 頁", "hiddenAt2s": False,
                                  "countAt2s": 60, "partsAt2s": 60, "expectedM": 60, "pass": True}, "ok": True},
                "p3": {"arm": "p3", "nonVacuous": True, "paintsInWindow": 40, "reachedBottom": True,
                       "pageRectanglesRequestsInWindow": 0, "untriggeredRequests": 0, "triggersInWindow": 0, "ok": True},
                "c1": {"arm": "c1", "rounds": rounds, "placementMismatches": 0, "ok": True},
                "e2": {"arm": "e2", "cases": e2_cases, "hold": {"outcome": "refused", "merges": 2,
                                                                 "judge": copy.deepcopy(e2_case["judge"]), "pass": True},
                       "refusalsObserved": 6, "ok": True},
            }}


def mutations() -> list[tuple[str, str, str, callable]]:
    """(name, arm, expected verdict, mutator)."""
    def p1_off_by_one(r):
        r["results"]["p1-60"]["positions"][5]["text"] = "第 7 頁，共 60 頁"
    def p1_hidden(r):
        r["results"]["p1-60"]["positions"][70]["hidden"] = True
    def p1_parts(r):
        r["results"]["p1-60"]["partsEqualsCount"] = False
        r["results"]["p1-60"]["reply"]["parts"] = 59
    def p1_no_reply(r):
        r["results"]["p1-60"]["reply"] = None
        r["results"]["p1-60"]["positions"] = []
    def p2_text_stale(r):
        r["results"]["p2"]["add"]["textAt2s"] = "第 60 頁，共 60 頁"
    def p2_disagree(r):
        r["results"]["p2"]["remove"]["countAt2s"] = 61
    def p2_no_press(r):
        r["results"]["p2"]["add"]["presses"] = 0
    def p3_untriggered(r):
        r["results"]["p3"]["pageRectanglesRequestsInWindow"] = 1
        r["results"]["p3"]["untriggeredRequests"] = 1
    def p3_no_paint(r):
        r["results"]["p3"]["paintsInWindow"] = 0
        r["results"]["p3"]["nonVacuous"] = False
    def p3_no_bottom(r):
        r["results"]["p3"]["reachedBottom"] = False
        r["results"]["p3"]["nonVacuous"] = False
    def c1_refused(r):   # v19's shape: the red case §5 named
        rd = r["results"]["c1"]["rounds"][0]
        rd["answer"] = {"ok": False, "code": "EDITOR_BOUNDARY_UNSUPPORTED", "mergeKey": {"stage": "nothing-selected"}}
        rd["generationAfter"] = "2"
        rd["clauses"]["completionIsBoundaryNoop"] = False
        rd["clauses"]["generationStays1"] = False
    def c1_selection(r):
        rd = r["results"]["c1"]["rounds"][3]
        rd["engineRead"]["result"]["sel"] = {"collapsed": False, "n": 1}
        rd["clauses"]["noSelectionAt500ms"] = False
    def c1_no_waited(r):
        rd = r["results"]["c1"]["rounds"][1]
        rd["answer"]["boundaryNoop"] = {"waitedMs": None}
        rd["clauses"]["waitedMsPresent"] = False
    def c1_all_mismatch(r):
        r["results"]["c1"]["rounds"] = [{"case": "C29", "round": 1, "outcome": "placement-mismatch"}]
        r["results"]["c1"]["placementMismatches"] = 1
    def c1_short(r):
        r["results"]["c1"]["rounds"] = r["results"]["c1"]["rounds"][:4]
    def e2_differs(r):
        c = r["results"]["e2"]["cases"][0]
        c["judge"]["caretBefore"]["rect"]["x"] = 2685
        c["judge"]["clauses"]["rectEqualsReference"] = False
    def e2_absent(r):
        c = r["results"]["e2"]["hold"]
        c["judge"]["caretBefore"] = None
        c["judge"]["clauses"]["caretBeforePresent"] = False
        c["judge"]["clauses"]["rectNotNull"] = False
        c["judge"]["clauses"]["rectEqualsReference"] = False
    def e2_null_rect(r):
        c = r["results"]["e2"]["cases"][0]
        c["judge"]["caretBefore"]["rect"] = None
        c["judge"]["clauses"]["rectNotNull"] = False
        c["judge"]["clauses"]["rectEqualsReference"] = False
    def e2_no_refusal(r):
        r["results"]["e2"]["cases"] = [{"case": "C17", "outcome": "verified-key-undo", "note": "verbatim"}]
        r["results"]["e2"]["hold"] = {"outcome": "hold-reached-no-refusal", "merges": 2}
    # --- review 2026-10-14 (opus Q3 D2-D5, Q6.2; codex 1): what the committed runner writes on a partial run.
    def e2_hold_raised(r):      # arm_e2 catches the hold's exception: out["hold"] = {"error": ...}; 5 cases judged
        r["results"]["e2"]["hold"] = {"error": "TimeoutError: CDP Input.dispatchKeyEvent"}
    def e2_killed_after_two(r):  # the runner killed after case 2's FLUSH: two cases, no hold
        r["results"]["e2"]["cases"] = r["results"]["e2"]["cases"][:2]
        r["results"]["e2"]["hold"] = None
    def e2_four_mismatches(r):  # placement failed on four of five cases; the hold reached no refusal
        for c in r["results"]["e2"]["cases"][1:]:
            c.pop("judge"); c.pop("pass"); c["outcome"] = "placement-mismatch"
        r["results"]["e2"]["hold"] = {"outcome": "hold-reached-no-refusal", "merges": 2}
    def e2_hold_no_merge(r):    # the hold's first press was the refusal: not "held across a merge"
        r["results"]["e2"]["hold"]["merges"] = 0
    def p2_parts_missing(r):    # no reply in the final wait and no parts carried from the presses
        r["results"]["p2"]["add"]["partsAt2s"] = None
    def criterion_on_trace_worker(r):
        r["identity"]["instrumentedWorker"] = True
    return [
        ("p1: a position's k off by one", "p1-60", FAIL, p1_off_by_one),
        ("p1: a position hidden", "p1-60", FAIL, p1_hidden),
        ("p1: M != parts", "p1-60", FAIL, p1_parts),
        ("p1: no rectangles reply (non-vacuity)", "p1-60", NE, p1_no_reply),
        ("p2: text at +2 s still says 60 after the add", "p2", FAIL, p2_text_stale),
        ("p2: text and reply count disagree", "p2", FAIL, p2_disagree),
        ("p2: no Enter press (non-vacuity)", "p2", NE, p2_no_press),
        ("p3: one untriggered pageRectangles request", "p3", FAIL, p3_untriggered),
        ("p3: no paint during the scroll (vacuous)", "p3", NE, p3_no_paint),
        ("p3: scroll never reached the bottom (vacuous)", "p3", NE, p3_no_bottom),
        ("c1: a refusal with generation 2 (v19's shape)", "c1", FAIL, c1_refused),
        ("c1: a selection present at +500 ms", "c1", FAIL, c1_selection),
        ("c1: waitedMs missing", "c1", FAIL, c1_no_waited),
        ("c1: every round placement-mismatch", "c1", NE, c1_all_mismatch),
        ("c1: fewer than six judged rounds", "c1", FAIL, c1_short),
        ("e2: caretBefore.rect differs from the prior caret", "e2", FAIL, e2_differs),
        ("e2: caretBefore absent", "e2", FAIL, e2_absent),
        ("e2: caretBefore.rect null", "e2", FAIL, e2_null_rect),
        ("e2: no refusal observed", "e2", NE, e2_no_refusal),
        ("e2: the hold raised, five cases judged (review D2)", "e2", FAIL, e2_hold_raised),
        ("e2: runner killed after two cases (review D3)", "e2", FAIL, e2_killed_after_two),
        ("e2: four placement mismatches, hold without refusal (review D4)", "e2", FAIL, e2_four_mismatches),
        ("e2: the hold refused before any merge (review D5)", "e2", FAIL, e2_hold_no_merge),
        ("p2: parts missing at +2 s (review codex 1)", "p2", FAIL, p2_parts_missing),
        ("identity: a criterion arm on the trace worker", "p1-60", FAIL, criterion_on_trace_worker),
    ]


def p2c_red_cases() -> list[tuple[str, str, dict]]:
    """The reader's own red cases: a lone 13 reads ESTABLISHED, a flanked one does not, no events is not quiet."""
    def result(lone: int, seen: bool) -> dict:
        return {"arm": "p2c", "lokEventsSeen": seen, "loneSizeChanges": lone,
                "phases": [{"fixture": "long60", "openAndSettle": {"lokEvents": 10 if seen else 0, "sizeChanges": 1,
                                                                   "lone": [{"tw": 1.0}] * lone, "flanked": 1 - lone}}]}
    return [("p2c: one lone size change", "ESTABLISHED", result(1, True)),
            ("p2c: size change flanked by tiles", NE, result(0, True)),
            ("p2c: no lok events at all", NE, result(0, False))]


def exit_rule_red_cases(base: list[dict]) -> list[tuple[str, bool]]:
    """The exit rule's own red cases (review, opus Q6 = codex 6): a duplicate cell in either order, and no
    expected page.  Each must exit 1; the duplicate must be named whichever file sorts first."""
    bad = copy.deepcopy(base[0])
    bad["results"]["p1-60"]["positions"][5]["text"] = "第 7 頁，共 60 頁"       # the FAIL of the first run
    rerun = copy.deepcopy(base[0])
    rerun["results"] = {"p1-60": rerun["results"]["p1-60"]}                   # the green re-run of that arm
    fail_first = judge_reports([bad, rerun, base[1]], SYNTHETIC_PAGE)
    pass_first = judge_reports([rerun, bad, base[1]], SYNTHETIC_PAGE)
    no_page = judge_reports(copy.deepcopy(base), None)
    dup = lambda lines: any(l.startswith("[chrome] p1-60: DUPLICATE") for l in lines)   # noqa: E731
    return [("exit: a FAIL then a green re-run of the same cell exits 1", fail_first[0] == 1 and dup(fail_first[1])),
            ("exit: the green re-run sorted first still exits 1", pass_first[0] == 1 and dup(pass_first[1])),
            ("exit: no expected page is not a verdict", no_page[0] == 1 and no_page[1][0].startswith("VERDICT NOT GIVEN"))]


def runner_predicate_red_cases(rv) -> list[tuple[str, bool]]:
    """The runner predicates the judge reads as booleans, made red at the predicate (review Q7: before,
    every C1/E2 red case set the boolean by hand, so the predicate itself was never exercised)."""
    answer = {"ok": True, "completion": "verified-boundary-noop", "changed": False, "rev": 0, "beforeRev": 0,
              "boundaryNoop": {"waitedMs": 2251}}
    asked = {"answered": True, "ok": True, "result": {"sel": {"collapsed": True, "n": 0, "observed": True},
                                                      "selectionType": "none"}}
    green = rv.c1_clauses(answer, asked, "1", "1", [])
    fresh_text = rv.c1_clauses(answer, {**asked, "result": {**asked["result"], "selectionType": "text"}}, "1", "1", [])
    n_absent = rv.c1_clauses(answer, {**asked, "result": {"sel": {"collapsed": True, "n": None}, "selectionType": "none"}},
                             "1", "1", [])
    rev_absent = rv.c1_clauses({**answer, "rev": None, "beforeRev": None}, asked, "1", "1", [])
    toast = rv.c1_clauses(answer, asked, "1", "1", ["EDITOR_BOUNDARY_UNSUPPORTED：游標已在文件開頭"])
    # E2's reference: a push logged right after the request shares its 0.1 ms `t`; `s` orders them.
    a, b = {"x": 2684, "y": 7266, "width": 0, "height": 276}, {"x": 3000, "y": 7266, "width": 0, "height": 276}
    trace = [{"k": "ev", "s": 0, "g": 1, "t": 100.0, "caret": a, "seq": 10},
             {"k": "rq", "s": 1, "g": 1, "t": 101.0, "rq": 5},
             {"k": "ev", "s": 2, "g": 1, "t": 101.0, "caret": b, "seq": 11}]
    ref = rv.reference_caret(trace, trace[1])
    # P2's +2 s reading with no reply in the final wait: the presses' last reply, with ITS parts.
    g = {"text": "第 60 頁，共 61 頁", "hidden": False}
    fallback = rv.at_2s(None, {"count": 61, "parts": 60}, g, 61)
    direct = rv.at_2s({"rects": "; ".join(["284, 284, 11906, 16838"] * 61), "parts": 61}, {"count": 1, "parts": 1}, g, 61)
    return [("c1 predicate: the green round holds every clause", all(green.values())),
            ("c1 predicate: fresh read says text, cache collapsed -> noSelectionAt500ms false (review 1a)",
             fresh_text["noSelectionAt500ms"] is False),
            ("c1 predicate: rectangle count absent -> noSelectionAt500ms false (review codex 1)",
             n_absent["noSelectionAt500ms"] is False),
            ("c1 predicate: both revisions absent -> revisionUnchanged false (review codex 1)",
             rev_absent["revisionUnchanged"] is False),
            ("c1 predicate: any toast after the key -> noToast false (review 1b)", toast["noToast"] is False),
            ("e2 reference: the push logged after the request at the same t is not the reference (review codex 1)",
             ref is not None and ref["caret"] == a),
            ("p2 +2 s: no reply in the wait -> parts is the last reply's parts, not its count", fallback["partsAt2s"] == 60
             and fallback["pass"] is False),
            ("p2 +2 s: a reply in the wait is read directly", direct["countAt2s"] == 61 and direct["partsAt2s"] == 61
             and direct["pass"] is True)]


def self_test(verbose: bool = True) -> int:
    failures = []
    base = [synthetic_report("chrome"), synthetic_report("firefox")]
    code, lines = judge_reports(copy.deepcopy(base), SYNTHETIC_PAGE)
    if code != 0 or not lines[-1].startswith("VERDICT PASS"):
        failures.append(f"the synthetic PASS set does not pass: {lines[-1]}")
    for name, arm, expected, mutate in mutations():
        reports = copy.deepcopy(base)
        mutate(reports[0])
        code, lines = judge_reports(reports, SYNTHETIC_PAGE)
        cell = next((l for l in lines if l.startswith(f"[chrome] {arm}:")), "")
        got = cell.split(": ", 1)[1].split(" ")[0] if ": " in cell else "?"
        ok = got == expected and code == 1
        other = [l for l in lines if l.startswith("[firefox] ") and not l.endswith(" PASS") and "p2c" not in l]
        if other:
            ok = False
        if verbose:
            print(f"{'ok ' if ok else 'RED-CASE FAILED'} {name}: chrome {arm} -> {got} (expected {expected}), exit {code}")
        if not ok:
            failures.append(name)
    for name, expected, result in p2c_red_cases():
        reading, _ = judge_p2c(result)
        ok = reading == expected
        if verbose:
            print(f"{'ok ' if ok else 'RED-CASE FAILED'} {name}: {reading} (expected {expected})")
        if not ok:
            failures.append(name)
    for name, ok in exit_rule_red_cases(base):
        if verbose:
            print(f"{'ok ' if ok else 'RED-CASE FAILED'} {name}")
        if not ok:
            failures.append(name)
    # The lone-flush detector itself, on a synthetic trace (the runner's function, imported here).
    try:
        import run_v20_shakedown as rv
        for name, ok in runner_predicate_red_cases(rv):
            if verbose:
                print(f"{'ok ' if ok else 'RED-CASE FAILED'} {name}")
            if not ok:
                failures.append(name)
        lone = rv.lok_summary([{"k": "mt", "type": "lok", "id": 13, "tw": 100.0}])
        flanked = rv.lok_summary([{"k": "mt", "type": "lok", "id": 13, "tw": 100.0},
                                  {"k": "mt", "type": "lok", "id": 0, "tw": 103.0}])
        far = rv.lok_summary([{"k": "mt", "type": "lok", "id": 13, "tw": 100.0},
                              {"k": "mt", "type": "lok", "id": 0, "tw": 140.0}])
        for name, ok in (("detector: lone 13", len(lone["lone"]) == 1 and lone["flanked"] == 0),
                         ("detector: 13 with tiles at +3 ms is flanked", len(flanked["lone"]) == 0 and flanked["flanked"] == 1),
                         ("detector: tiles 40 ms away do not flank", len(far["lone"]) == 1)):
            if verbose:
                print(f"{'ok ' if ok else 'RED-CASE FAILED'} {name}")
            if not ok:
                failures.append(name)
        # The span rule: the runner's Python implementation against the native mixed string.
        rects = rv.parse_rects("284, 284, 11906, 16838; 284, 17406, 16838, 11906; 284, 29596, 16838, 11906")
        one = rv.status_text(rv.span_of(rects, {"x": 0, "y": 5000, "width": 24379, "height": 9000}))
        two = rv.status_text(rv.span_of(rects, {"x": 0, "y": 16000, "width": 24379, "height": 9000}))
        edge = rv.span_of(rects, {"x": 0, "y": 17122, "width": 24379, "height": 284})   # exactly the gap: strict
        for name, ok in (("span: one page", one == "第 1 頁，共 3 頁"), ("span: two pages", two == "第 1–2 頁，共 3 頁"),
                         ("span: a region exactly in the gap hits nothing", edge is None)):
            if verbose:
                print(f"{'ok ' if ok else 'RED-CASE FAILED'} {name}")
            if not ok:
                failures.append(name)
    except Exception as error:  # noqa: BLE001
        failures.append(f"runner import failed: {error}")
    if verbose:
        print(f"self-test: {len(failures)} failure(s)")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path)
    ap.add_argument("--expect-page", default=None,
                    help="the served page's sha256 every report must carry (required with --dir)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.dir is None:
        raise SystemExit("--dir or --self-test")
    reports = load_reports(args.dir)
    if not reports:
        print("no report-*.json found")
        return 1
    code, lines = judge_reports(reports, args.expect_page)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
