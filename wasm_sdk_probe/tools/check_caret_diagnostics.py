#!/usr/bin/env python3
"""Judge gate condition 2 -- the caret diagnostic runs -- from their reports.

The runner reports; this judges.  Separate tools for the same reason
`check_4a.py` is separate from `probe_aria_projection.py`: a judge that shares
a process with the thing it judges can only ever confirm it.

Condition 2, verbatim from
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` (soak section), with the
profile as amended 2026-08-29 to `e2-editor-v12`:

    Three diagnostic runs, additionally, to keep bounding the 084 class:

        --candidate-profile e2-editor-v12 --caret-source-diagnostic \\
            --caret-rounds 12 --caret-engine-probe stalled

    Required: 0 dropped commits in 36, and `staleWritesRefusedTotal > 0` in at
    least one -- because a run whose guard never fired has only shown that the
    race was not lost that time.  These are diagnostic and do NOT count toward
    the twelve.

## Why `engineProbeMode` is part of the identity term and not a footnote

The first three-layer caret probe asked the engine for its caret before every
commit, and under it 24 of 24 commits followed the caret while the identical
configuration WITHOUT the probe dropped 10 of 48 (Fisher exact p = 0.012).  The
instrument suppressed the defect it was built to measure.  `stalled` -- the
default since -- sends the engine nothing on a commit the sink followed.  A run
taken with `every-round` is therefore not weaker evidence for this condition,
it is evidence about a different system, so this judge REFUSES it rather than
counting it.

Usage:
  check_caret_diagnostics.py                      # the v12 bank's diagnostics
  check_caret_diagnostics.py --report A.json B.json C.json
  check_caret_diagnostics.py --self-test          # prove it can say no
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
WORKSPACE = PROJECT.parent
DEFAULT_DIR = WORKSPACE / "findings" / "evidence" / "queue-v12-cutover-soak"
DEFAULT_GLOB = "diagnostic-*.json"
DEFAULT_SHA = ("20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d09"
               "0d95")
DEFAULT_PROFILE = "e2-editor-v12"
CARET_CHECK = "caret-follows-the-text-you-type"

REQUIRED_RUNS = 3
REQUIRED_ROUNDS_PER_RUN = 12
REQUIRED_ROUNDS_TOTAL = REQUIRED_RUNS * REQUIRED_ROUNDS_PER_RUN   # 36


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(WORKSPACE))
    except ValueError:
        return str(path)


def caret_observation(report: dict) -> dict:
    for entry in report.get("checks") or []:
        if entry.get("id") == CARET_CHECK:
            return {"outcome": entry.get("outcome"),
                    "observed": entry.get("observed") or {}}
    return {"outcome": None, "observed": {}}


def read_run(path: Path, expect_sha: str, expect_profile: str) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    diagnostic = report.get("caretSourceDiagnostic") or {}
    candidate = report.get("candidateCutover") or {}
    caret = caret_observation(report)
    observed = caret["observed"]
    rounds = observed.get("rounds") or []
    # A round that did not advance the document is not a dropped commit -- it
    # is a round that never committed.  `moved` is only meaningful where
    # `revisionAdvanced`, which is the same subset the runner scores.
    committed = [r for r in rounds if r.get("revisionAdvanced")]
    dropped = [i for i, r in enumerate(committed) if r.get("moved") is not True]
    return {
        "report": rel(path),
        "isDiagnostic": bool(diagnostic),
        "engineProbeMode": diagnostic.get("engineProbeMode"),
        "profile": candidate.get("profile"),
        "pageSha256": candidate.get("pageSha256"),
        "complete": report.get("complete"),
        "caretOutcome": caret["outcome"],
        "roundsThatReachedTheDocument":
            observed.get("roundsThatReachedTheDocument"),
        "committedRounds": len(committed),
        "droppedRoundIndexes": dropped,
        "staleWritesRefusedTotal": observed.get("staleWritesRefusedTotal"),
        "sinkTracksTheCaret": observed.get("sinkTracksTheCaret"),
        "identityOk": (bool(diagnostic)
                       and diagnostic.get("engineProbeMode") == "stalled"
                       and candidate.get("profile") == expect_profile
                       and candidate.get("pageSha256") == expect_sha),
    }


def judge(paths: list[Path], expect_sha: str, expect_profile: str) -> dict:
    if not paths:
        return {"criterion": "gate condition 2", "ok": False,
                "error": "no diagnostic report given, and a judge that "
                         "searched nothing must not report zero problems"}
    runs = [read_run(p, expect_sha, expect_profile) for p in paths]
    complete = [r for r in runs if r["complete"] is True]

    total_committed = sum(r["committedRounds"] for r in complete)
    total_dropped = sum(len(r["droppedRoundIndexes"]) for r in complete)
    stale = [r["staleWritesRefusedTotal"] for r in complete
             if isinstance(r["staleWritesRefusedTotal"], int)]

    terms = {
        "1-identity": {
            "ok": bool(complete) and all(r["identityOk"] for r in complete),
            "detail": [{"report": r["report"], "isDiagnostic": r["isDiagnostic"],
                        "engineProbeMode": r["engineProbeMode"],
                        "profile": r["profile"],
                        "pageShaMatches": r["pageSha256"] == expect_sha}
                       for r in complete],
        },
        "2-count": {
            "ok": len(complete) >= REQUIRED_RUNS,
            "completeRuns": len(complete), "given": len(runs),
            "required": REQUIRED_RUNS,
        },
        "3-rounds": {
            # `>= 36 committed rounds AND zero dropped` -- both, because a run
            # that committed nothing drops nothing and would otherwise pass.
            "ok": (total_committed >= REQUIRED_ROUNDS_TOTAL
                   and total_dropped == 0
                   and all(r["caretOutcome"] == "PASS" for r in complete)
                   and all(r["roundsThatReachedTheDocument"]
                           == REQUIRED_ROUNDS_PER_RUN for r in complete)),
            "committedRounds": total_committed,
            "requiredRounds": REQUIRED_ROUNDS_TOTAL,
            "droppedCommits": total_dropped,
            "perRun": [{"report": r["report"],
                        "reached": r["roundsThatReachedTheDocument"],
                        "dropped": r["droppedRoundIndexes"],
                        "outcome": r["caretOutcome"]} for r in complete],
        },
        "4-guard-fired": {
            # GREEN IS NOT ENOUGH.  A clean run whose guard never fired has
            # shown only that the race was not lost that time; the guard
            # refusing a stale write is the positive evidence that the window
            # finding 084 lived in is still being entered and still closed.
            "ok": bool(stale) and max(stale) > 0,
            "perRun": {r["report"]: r["staleWritesRefusedTotal"]
                       for r in complete},
            "max": max(stale) if stale else None,
        },
    }
    return {"criterion": "gate condition 2 -- the caret diagnostic runs",
            "expected": {"runs": REQUIRED_RUNS,
                         "roundsPerRun": REQUIRED_ROUNDS_PER_RUN,
                         "profile": expect_profile, "pageSha256": expect_sha,
                         "engineProbeMode": "stalled"},
            "runs": runs, "terms": terms,
            "ok": all(term["ok"] for term in terms.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, nargs="*", default=None)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--expect-page-sha256", default=DEFAULT_SHA)
    parser.add_argument("--expect-profile", default=DEFAULT_PROFILE)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    paths = (list(args.report) if args.report
             else sorted(args.dir.glob(DEFAULT_GLOB)))
    verdict = judge(paths, args.expect_page_sha256, args.expect_profile)
    text = json.dumps(verdict, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if verdict["ok"] else 1


def self_test() -> int:
    """Prove it can say no, and prove the green case is green for the right
    reason -- the control exists because three red cases built from a broken
    fixture would all be red without the judge working at all."""
    sources = [p for p in sorted(DEFAULT_DIR.glob(DEFAULT_GLOB))
               if json.loads(p.read_text(encoding="utf-8"))
               .get("complete") is True]
    if not sources:
        print("self-test has no COMPLETE diagnostic report to build from; "
              "it would otherwise pass by measuring nothing")
        return 1
    # THE BASE IS CHOSEN, NOT TAKEN.  The green control is three copies of one
    # real report, so that report must be able to satisfy every term the
    # control asserts -- including term 4, which needs the guard to have fired.
    # Taking `sources[0]` worked only while every banked run happened to have
    # refused a stale write; the 2026-09-06 take has a run with 0, and the
    # control went red on a fixture the judge was right about.  A control that
    # is red for a reason outside the judge teaches nothing, so this refuses
    # instead of reporting it.
    def guard_fired(path: Path) -> bool:
        body = json.loads(path.read_text(encoding="utf-8"))
        for entry in body.get("checks") or []:
            if entry.get("id") == CARET_CHECK:
                total = (entry.get("observed") or {}).get(
                    "staleWritesRefusedTotal")
                return isinstance(total, int) and total > 0
        return False

    usable = [p for p in sources if guard_fired(p)]
    if not usable:
        print("self-test has no COMPLETE diagnostic report whose guard fired; "
              "the green control would be red on term 4 for a reason that is "
              "about the fixture and not about the judge")
        return 1
    base = json.loads(usable[0].read_text(encoding="utf-8"))

    def write(root: Path, name: str, mutate) -> Path:
        body = json.loads(json.dumps(base))
        mutate(body)
        path = root / name
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def caret(body: dict) -> dict:
        for entry in body["checks"]:
            if entry["id"] == CARET_CHECK:
                return entry
        raise AssertionError("fixture has no caret check")

    cases = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        trio = [write(root, f"diagnostic-0{i}.json", lambda b: None)
                for i in (1, 2, 3)]

        cases.append(("nothing given at all", judge([], DEFAULT_SHA,
                                                    DEFAULT_PROFILE)))
        cases.append(("two runs where three are required",
                      judge(trio[:2], DEFAULT_SHA, DEFAULT_PROFILE)))

        def drop_one(body):
            observed = caret(body)["observed"]
            for entry in observed["rounds"]:
                if entry.get("revisionAdvanced"):
                    entry["moved"] = False
                    break
        dropped = write(root, "dropped.json", drop_one)
        cases.append(("one dropped commit in 36",
                      judge([trio[0], trio[1], dropped], DEFAULT_SHA,
                            DEFAULT_PROFILE)))

        def guard_silent(body):
            caret(body)["observed"]["staleWritesRefusedTotal"] = 0
        silent = [write(root, f"silent-{i}.json", guard_silent)
                  for i in (1, 2, 3)]
        cases.append(("clean but the guard never fired",
                      judge(silent, DEFAULT_SHA, DEFAULT_PROFILE)))

        def not_diagnostic(body):
            body.pop("caretSourceDiagnostic", None)
        plain = write(root, "plain.json", not_diagnostic)
        cases.append(("a plain run offered as a diagnostic",
                      judge([trio[0], trio[1], plain], DEFAULT_SHA,
                            DEFAULT_PROFILE)))

        def every_round(body):
            body["caretSourceDiagnostic"]["engineProbeMode"] = "every-round"
        probed = write(root, "every-round.json", every_round)
        cases.append(("engine probed every round -- the confound",
                      judge([trio[0], trio[1], probed], DEFAULT_SHA,
                            DEFAULT_PROFILE)))

        cases.append(("wrong expected page sha",
                      judge(trio, "0" * 64, DEFAULT_PROFILE)))

        def no_commits(body):
            observed = caret(body)["observed"]
            for entry in observed["rounds"]:
                entry["revisionAdvanced"] = False
            observed["roundsThatReachedTheDocument"] = 0
        empty = [write(root, f"empty-{i}.json", no_commits) for i in (1, 2, 3)]
        cases.append(("no commits at all -- drops nothing, proves nothing",
                      judge(empty, DEFAULT_SHA, DEFAULT_PROFILE)))

        control = judge(trio, DEFAULT_SHA, DEFAULT_PROFILE)

    for name, verdict in cases:
        mark = "RED (correct)" if not verdict.get("ok") else "GREEN (WRONG)"
        print(f"  {mark:15s} {name}")
    mark = "GREEN (correct)" if control.get("ok") else "RED (WRONG)"
    print(f"  {mark:15s} control: three unmodified diagnostic runs")
    failures = [name for name, verdict in cases if verdict.get("ok")]
    if failures or not control.get("ok"):
        if not control.get("ok"):
            bad = [k for k, t in control["terms"].items() if not t["ok"]]
            print(f"    control failed on: {bad}")
        print(f"\nself-test FAILED: green cases {failures}")
        return 1
    print(f"\nself-test passed: {len(cases)} red cases all red, "
          "and the green control is green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
