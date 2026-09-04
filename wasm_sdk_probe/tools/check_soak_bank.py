#!/usr/bin/env python3
"""Judge a soak bank as a whole: is the gate's counting criterion satisfied?

WHY THIS EXISTS (work item W-4 of
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`).  `check_usable_editor.py`
reconciles ONE report at a time.  Nothing read the twelve together, so "the gate
is open" would have rested on the drafting party narrating a count -- which
`AGENTS.md` §8 forbids for exactly this decision.  This tool makes the bank's
state re-derivable by someone who was not here, from one command.

It is NOT a criterion.  It changes who can verify the gate, not what the gate
demands; every clause below is quoted from criterion 1 as amended 2026-08-29.

IT DOES NOT REIMPLEMENT THE PER-RUN VERDICT.  `check_usable_editor.py` is
invoked as a subprocess per report and its reconciliation is read.  A second
implementation of "is this run clean" would drift from the first one silently,
and the two would disagree on the day nobody was checking.

## The clean-run predicate, as amended for candidate `e2-editor-v12`

  * `ok: true` and `complete: true` in the run's own report;
  * `check_usable_editor.py --report` reconciles `ok: true`, with
    `reconciledFor.kind == "candidate-cutover"` and the profile named;
  * composition is 38 PASS / 2 NOT_ESTABLISHED, NE set exactly
    {notice-action-recovers-the-session,
     a-refused-action-is-reported-and-changes-nothing};
  * `candidateCutover.pageSha256` equals the expected page sha.

## The membership rule, and why it is not a hand-kept list

Every `*.json` in the bank directory is classified as a banked run or as a
declared non-run.  **An unclassified file is RED**, not ignored.  RUNS.md
already records why: a file called `soak-run-02-...` that is not run 2 is
exactly what a later glob miscounts.  So the glob is the enumeration, and the
tool refuses to answer when it meets a file it cannot account for.

Gate condition 2's diagnostic runs (`diagnostic-*.json`) share the directory.
They are excluded from the twelve by the identity rule, so they are classified
rather than counted -- and LISTED in the verdict, because a file this tool
silently skipped would be indistinguishable from one it never saw.  Condition 2
is judged by `check_caret_diagnostics.py`, not here.

A judge's own output banked beside the evidence (`VERDICT-*.json`) is a third
class again: not a run, not condition 2's evidence, and never counted -- a
verdict counted as a run would inflate the number this tool exists to state.
It is listed rather than skipped, for the same reason the diagnostics are.

Reports banked in place OUTSIDE the directory (run 1 is the split probe's
criterion-2 run, cited rather than copied, because evidence in this tree is not
moved) are passed with `--also`.  Omitting one can only UNDERCOUNT, which makes
the gate harder to open and never easier; adding a bogus one is resolved and
goes red.  That asymmetry is the reason this shape is acceptable.

## Calendar-day attribution, per the amendment of 2026-09-03

Criterion 1 also requires >=3 calendar days with >=2 runs each.  Until
2026-09-03 no report carried a wall-clock timestamp at all, so the day was
knowable only from filesystem mtime (not evidence; a clone replaces it) or from
the drafting party's narration.  Adjudicated: the runner now writes
`completedAt`, and

  * a run's day is the **UTC date** of its own `completedAt`;
  * a report WITHOUT the field contributes NO day, and still counts toward
    twelve -- reports banked before the field existed are dayless by
    construction;
  * a NAIVE `completedAt` (no UTC offset) is **RED**, not dayless.  Ambiguity
    is the defect the amendment removes, so a report that reintroduces it is a
    defect rather than a report the clause politely skips.

`mtime` is still printed, under a label that says it is out of band, and the
JUDGEMENT NEVER READS IT.  It is an AGENTS.md §3 registration of what the
pre-field runs assert, not a source the criterion consumes.

Usage:
  check_soak_bank.py                                   # the v12 bank
  check_soak_bank.py --bank <dir> --expect-page-sha256 <sha> --expect-runs 12
  check_soak_bank.py --self-test                       # prove it can say no
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
WORKSPACE = PROJECT.parent
CHECKER = PROJECT / "tools" / "check_usable_editor.py"

DEFAULT_BANK = (WORKSPACE / "findings" / "evidence" / "queue-v12-cutover-soak")
# Empty since 2026-09-05.  It held the split probe's criterion-2 run, banked in
# place as soak run 1 -- taken on page sha `3dfdcfef...`, which the human round
# of 2026-09-04 moved.  The file stays where it is because it is that probe's
# evidence too; it is dropped from here because it is no longer this count's.
DEFAULT_ALSO: list[Path] = []
DEFAULT_SHA = ("20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d09"
               "0d95")
DEFAULT_PROFILE = "e2-editor-v12"
EXPECTED_NE = {"notice-action-recovers-the-session",
               "a-refused-action-is-reported-and-changes-nothing"}
EXPECTED_PASS = 38

# Files in the bank directory that are deliberately NOT counted runs.  Each
# needs a reason, because "ignore what does not parse" is how a bank quietly
# loses a member.  RUNS.md carries the same dispositions in prose.
NON_RUNS = {
    "interrupted-2026-08-29-0050-partial.json":
        "partial snapshot of an interrupted run: complete=false, no ok, "
        "6 checks. Renamed out of the soak-run-* namespace rather than "
        "deleted, so the interruption stays visible.",
}

# Condition 2's evidence lives in the same directory and is NOT condition 1's.
# `--caret-source-diagnostic` mirrors the page and adds an engine probe, so the
# identity rule excludes these from the twelve -- but excluded is not the same
# as invisible, and a file this tool cannot name is red.  They are listed in the
# verdict under `conditionTwoFiles` so a reader sees that they exist and that
# this tool did not judge them.
DIAGNOSTIC_PREFIX = "diagnostic-"

# A judge's own output, banked beside the evidence it judged.  It is neither a
# run nor condition 2's evidence -- it is a VERDICT, and a verdict counted as a
# run would inflate the very number this tool exists to state.  Named, because
# the alternative that presented itself was widening the glob, and a bank whose
# tool skips what it does not recognise has stopped being a census.
VERDICT_PREFIX = "VERDICT-"


def rel(path: Path) -> str:
    """Workspace-relative when it can be, absolute otherwise.

    `relative_to` RAISES for a path outside the tree, and the self-test builds
    banks in a temp directory -- so the first run of the self-test crashed here
    rather than reporting. Kept as a note: the red cases found a defect in the
    judge before the judge had judged anything.
    """
    try:
        return str(path.relative_to(WORKSPACE))
    except ValueError:
        return str(path)


def reconcile(report_path: Path) -> dict:
    """Ask `check_usable_editor.py` -- do not re-decide it here."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        out = Path(handle.name)
    try:
        proc = subprocess.run(
            [sys.executable, str(CHECKER), "--report", str(report_path),
             "--output", str(out)],
            capture_output=True, text=True, cwd=str(PROJECT))
        if not out.is_file() or not out.stat().st_size:
            return {"ok": False,
                    "error": f"checker produced nothing (exit {proc.returncode})",
                    "stderr": proc.stderr[-400:]}
        return json.loads(out.read_text(encoding="utf-8"))
    finally:
        out.unlink(missing_ok=True)


def compose(report: dict) -> dict:
    """PASS/NE composition straight from the run's own checks."""
    checks = report.get("checks") or []
    outcomes: dict[str, int] = {}
    ne_ids = []
    for entry in checks:
        outcome = entry.get("outcome")
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        if outcome == "NOT_ESTABLISHED":
            ne_ids.append(entry.get("id"))
    return {"total": len(checks), "outcomes": outcomes,
            "notEstablished": sorted(ne_ids)}


def day_of(report: dict) -> dict:
    """The run's UTC day, from its OWN `completedAt` and nothing else.

    Three outcomes, and they are not the same thing:
      * dated   -- an aware ISO-8601 stamp; the day is its UTC date.
      * dayless -- no field at all: a report written before the field existed.
                   It counts toward twelve and contributes no day.
      * naive   -- a stamp with no offset. RED. The amendment exists to remove
                   the ambiguity of an unzoned day, so a report that puts it
                   back is a defect, not a report to skip politely.
    """
    raw = report.get("completedAt")
    if raw is None:
        return {"utcDay": None, "dayless": True, "naive": False}
    try:
        stamp = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return {"utcDay": None, "dayless": False, "naive": True}
    if stamp.tzinfo is None or stamp.tzinfo.utcoffset(stamp) is None:
        return {"utcDay": None, "dayless": False, "naive": True}
    return {"utcDay": stamp.astimezone(timezone.utc).date().isoformat(),
            "dayless": False, "naive": False}


def judge_run(path: Path, expect_sha: str, expect_profile: str) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    candidate = report.get("candidateCutover") or {}
    composition = compose(report)
    verdict = reconcile(path)
    reconciled_for = (verdict or {}).get("reconciledFor") or {}

    clauses = {
        "run-ok": report.get("ok") is True,
        "run-complete": report.get("complete") is True,
        "reconciled-ok": verdict.get("ok") is True,
        "reconciled-as-candidate":
            reconciled_for.get("kind") == "candidate-cutover",
        "reconciled-profile":
            (reconciled_for.get("profile") or candidate.get("profile"))
            == expect_profile,
        "pass-count": composition["outcomes"].get("PASS") == EXPECTED_PASS,
        "ne-set-exact": set(composition["notEstablished"]) == EXPECTED_NE,
        "page-sha": candidate.get("pageSha256") == expect_sha,
    }
    stat = path.stat()
    day = day_of(report)
    return {
        "report": rel(path),
        "clean": all(clauses.values()),
        "clauses": clauses,
        "composition": composition,
        "profile": candidate.get("profile"),
        "pageSha256": candidate.get("pageSha256"),
        "completedAt": report.get("completedAt"),
        "utcDay": day["utcDay"],
        "dayless": day["dayless"],
        "naiveTimestamp": day["naive"],
        # OUT-OF-BAND. Registration, not a source; the judgement never reads it.
        "mtimeUtc_OUT_OF_BAND": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def judge(bank: Path, also: list[Path], expect_sha: str, expect_profile: str,
          expect_runs: int, expect_days: int = 3) -> dict:
    if not bank.is_dir():
        return {"ok": False, "error": f"bank directory does not exist: {bank}"}

    present = sorted(p for p in bank.glob("*.json"))
    # NON-EMPTINESS. A census that searched zero files and reported "zero
    # problems" is the failure mode this tree names explicitly; a renamed
    # directory must go RED, not quiet.
    if not present:
        return {"ok": False,
                "error": f"bank directory holds no *.json at all: {bank}"}

    diagnostics = [p.name for p in present
                   if p.name.startswith(DIAGNOSTIC_PREFIX)]
    verdicts = [p.name for p in present
                if p.name.startswith(VERDICT_PREFIX)]
    unclassified = [p.name for p in present
                    if not p.name.startswith("soak-run-")
                    and not p.name.startswith(DIAGNOSTIC_PREFIX)
                    and not p.name.startswith(VERDICT_PREFIX)
                    and p.name not in NON_RUNS]
    declared_missing = [name for name in NON_RUNS
                        if not (bank / name).is_file()]

    runs = [judge_run(p, expect_sha, expect_profile)
            for p in present if p.name.startswith("soak-run-")]
    for extra in also:
        if not extra.is_file():
            runs.append({"report": rel(extra), "clean": False,
                         "clauses": {"exists": False}})
        else:
            runs.append(judge_run(extra, expect_sha, expect_profile))

    clean = [r for r in runs if r["clean"]]
    shas = sorted({r.get("pageSha256") for r in runs})

    # THE DAY CLAUSE, over in-band-dated CLEAN runs only.
    dated: dict[str, list[str]] = {}
    dayless = []
    naive = []
    for run in clean:
        if run.get("naiveTimestamp"):
            naive.append(run["report"])
        elif run.get("dayless"):
            dayless.append(run["report"])
        else:
            dated.setdefault(run["utcDay"], []).append(run["report"])
    qualifying = sorted(day for day, members in dated.items()
                        if len(members) >= 2)

    clauses = {
        "no-unclassified-file": not unclassified,
        "declared-non-runs-present": not declared_missing,
        "every-run-clean": len(clean) == len(runs) and bool(runs),
        "count-reached": len(clean) >= expect_runs,
        "one-page-sha": len(shas) == 1 and shas[0] == expect_sha,
        "no-naive-timestamp": not naive,
        "day-spread": len(qualifying) >= expect_days,
    }

    return {
        "criterion": "soak criterion 1 -- counting clauses only",
        "bank": rel(bank),
        "expected": {"runs": expect_runs, "days": expect_days,
                     "profile": expect_profile,
                     "pageSha256": expect_sha,
                     "passCount": EXPECTED_PASS,
                     "notEstablished": sorted(EXPECTED_NE)},
        "cleanRuns": len(clean),
        "totalRuns": len(runs),
        "unclassifiedFiles": unclassified,
        "conditionTwoFiles_NOT_JUDGED_HERE": sorted(diagnostics),
        "verdictFiles_NOT_EVIDENCE": sorted(verdicts),
        "declaredNonRunsMissing": declared_missing,
        "distinctPageSha256": shas,
        "runs": runs,
        "clauses": clauses,
        "ok": all(clauses.values()),
        "calendarDayClause": {
            "rule": "a run's day is the UTC date of its own `completedAt`; "
                    "a report without the field counts toward the twelve and "
                    "contributes no day; a naive stamp is RED "
                    "(plan amendment 2026-09-03)",
            "requires": f">={expect_days} UTC days with >=2 clean runs on each",
            "qualifyingDays": qualifying,
            "runsPerUtcDay": {day: sorted(members)
                              for day, members in sorted(dated.items())},
            "daylessRuns": sorted(dayless),
            "naiveTimestampRuns": sorted(naive),
            "outOfBandMtimeDays_NOT_JUDGED": sorted({
                r["mtimeUtc_OUT_OF_BAND"][:10] for r in runs
                if "mtimeUtc_OUT_OF_BAND" in r}),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--also", type=Path, nargs="*", default=None,
                        help="reports banked in place outside the directory")
    parser.add_argument("--expect-page-sha256", default=DEFAULT_SHA)
    parser.add_argument("--expect-profile", default=DEFAULT_PROFILE)
    parser.add_argument("--expect-runs", type=int, default=12)
    parser.add_argument("--expect-days", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    also = DEFAULT_ALSO if args.also is None else list(args.also)
    verdict = judge(args.bank, also, args.expect_page_sha256,
                    args.expect_profile, args.expect_runs,
                    args.expect_days)
    text = json.dumps(verdict, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if verdict.get("ok") else 1


def self_test() -> int:
    """Prove it can say no.  A checker that has only ever returned green has
    shown that it returns green (`AGENTS.md` §6)."""
    import shutil
    cases: list[tuple[str, dict]] = []
    real = DEFAULT_BANK
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # RED 1: a directory that does not exist -- the renamed-directory case.
        cases.append(("missing bank directory",
                      judge(root / "nope", [], DEFAULT_SHA, DEFAULT_PROFILE, 12)))

        # RED 2: an empty directory must not read as "zero problems".
        empty = root / "empty"
        empty.mkdir()
        cases.append(("empty bank directory",
                      judge(empty, [], DEFAULT_SHA, DEFAULT_PROFILE, 12)))

        # RED 3: a stray file the tool cannot account for.
        stray = root / "stray"
        stray.mkdir()
        for src in real.glob("*.json"):
            shutil.copy2(src, stray / src.name)
        (stray / "notes-i-left-here.json").write_text("{}\n", encoding="utf-8")
        cases.append(("unclassified file present",
                      judge(stray, [], DEFAULT_SHA, DEFAULT_PROFILE, 12)))

        # RED 4: the declared non-run vanished -- the bank lost a member and
        # the count would silently still look tidy.
        lost = root / "lost"
        lost.mkdir()
        for src in real.glob("soak-run-*.json"):
            shutil.copy2(src, lost / src.name)
        cases.append(("declared non-run missing",
                      judge(lost, [], DEFAULT_SHA, DEFAULT_PROFILE, 12)))

        # RED 5: the wrong page sha -- a run against different bytes.
        cases.append(("wrong expected page sha",
                      judge(real, DEFAULT_ALSO, "0" * 64, DEFAULT_PROFILE, 12)))

        # RED 6: the incumbent's lineage offered as the candidate's bank.
        void = WORKSPACE / "findings" / "evidence" / \
            "queue-v11-cutover-soak-not-started"
        if void.is_dir():
            cases.append(("void v11 lineage offered as the v12 bank",
                          judge(void, [], DEFAULT_SHA, DEFAULT_PROFILE, 12)))

        # RED 7: a bank that is genuinely clean but short of the count.
        cases.append(("clean but short of twelve",
                      judge(real, DEFAULT_ALSO, DEFAULT_SHA, DEFAULT_PROFILE,
                            10_000)))

        # ---- the day clause. Three red cases named by the 2026-09-03
        # adjudication, because a day rule that has only ever been evaluated
        # over dayless reports has not been evaluated.

        def stamped(dest: Path, stamps: list[str | None]) -> Path:
            """A synthetic bank: the real COMPLETE reports, restamped.

            `complete: true` is not decoration here.  The first version globbed
            the live bank, and a soak run was writing into it -- so a partial
            report became a source, the green control went red, and three
            red cases above had been red for a reason nobody had checked.  A
            self-test that reads a directory being written to is not a test.
            """
            dest.mkdir()
            sources = [q for q in sorted(real.glob("soak-run-*.json"))
                       if json.loads(q.read_text(encoding="utf-8"))
                       .get("complete") is True]
            if not sources:
                raise SystemExit(
                    "self-test has no complete report to build from: it would "
                    "otherwise pass by measuring nothing")
            for name in NON_RUNS:
                shutil.copy2(real / name, dest / name)
            for index, stamp in enumerate(stamps):
                src = sources[index % len(sources)]
                body = json.loads(src.read_text(encoding="utf-8"))
                if stamp is None:
                    body.pop("completedAt", None)
                else:
                    body["completedAt"] = stamp
                (dest / f"soak-run-{index + 20:02d}-candidate.json").write_text(
                    json.dumps(body), encoding="utf-8")
            return dest

        # RED 8: every dated run on ONE UTC day. The count can be reached and
        # the spread still absent.
        one_day = stamped(root / "one-day",
                          [f"2026-09-03T{hour:02d}:30:00+08:00"
                           for hour in (9, 11, 13, 15, 17, 19)])
        cases.append(("all dated runs on one UTC day",
                      judge(one_day, [], DEFAULT_SHA, DEFAULT_PROFILE, 6, 3)))

        # RED 9: a naive stamp -- no offset. This is the ambiguity the
        # amendment removes, so it must be RED rather than quietly dayless.
        naive = stamped(root / "naive",
                        ["2026-09-03T09:30:00", "2026-09-03T11:30:00",
                         "2026-09-04T09:30:00", "2026-09-04T11:30:00",
                         "2026-09-05T09:30:00", "2026-09-05T11:30:00"])
        cases.append(("naive timestamp, no offset",
                      judge(naive, [], DEFAULT_SHA, DEFAULT_PROFILE, 6, 3)))

        # RED 10: the count is reached, but every run is dayless -- the spread
        # is supplied by reports that carry no day at all.
        blank = stamped(root / "dayless", [None] * 6)
        cases.append(("count reached, every run dayless",
                      judge(blank, [], DEFAULT_SHA, DEFAULT_PROFILE, 6, 3)))

        # GREEN control. Without one, the three cases above would also be red
        # if `stamped()` were simply producing broken reports -- and a red case
        # that is red for the wrong reason proves nothing.
        good = stamped(root / "spread",
                       ["2026-09-03T09:30:00+08:00", "2026-09-03T11:30:00+08:00",
                        "2026-09-04T09:30:00+08:00", "2026-09-04T11:30:00+08:00",
                        "2026-09-05T09:30:00+08:00", "2026-09-05T11:30:00+08:00"])
        control = judge(good, [], DEFAULT_SHA, DEFAULT_PROFILE, 6, 3)

    failures = [name for name, verdict in cases if verdict.get("ok")]
    for name, verdict in cases:
        mark = "RED (correct)" if not verdict.get("ok") else "GREEN (WRONG)"
        print(f"  {mark:14s} {name}")
    mark = "GREEN (correct)" if control.get("ok") else "RED (WRONG)"
    print(f"  {mark:14s} control: 6 dated runs spanning 3 UTC days")
    if not control.get("ok"):
        bad = [k for k, ok in control["clauses"].items() if not ok]
        print(f"    control failed on: {bad}")
        print(f"    days: {control['calendarDayClause']['qualifyingDays']}")
    if failures or not control.get("ok"):
        print(f"\nself-test FAILED: {len(failures)} case(s) returned green"
              f"{'; the control did not go green' if not control.get('ok') else ''}"
              f"{': ' + str(failures) if failures else ''}")
        return 1
    print(f"\nself-test passed: {len(cases)} red cases all red, "
          f"and the green control is green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
