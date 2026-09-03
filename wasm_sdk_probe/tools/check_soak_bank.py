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

Reports banked in place OUTSIDE the directory (run 1 is the split probe's
criterion-2 run, cited rather than copied, because evidence in this tree is not
moved) are passed with `--also`.  Omitting one can only UNDERCOUNT, which makes
the gate harder to open and never easier; adding a bogus one is resolved and
goes red.  That asymmetry is the reason this shape is acceptable.

## Calendar-day attribution is deliberately NOT judged here

Criterion 1 also requires >=3 calendar days with >=2 runs each, and RUNS.md
attributes a run to "the day of the report's completion timestamp".  **The
reports carry no wall-clock timestamp** -- verified 2026-09-03 across every
banked report, and `run_e2_c_product_path.py` records only `performance.now()`.
So the day is knowable only from filesystem mtime, which is not evidence and
does not survive a clone.

This tool therefore REPORTS the day clause as `NOT_ESTABLISHED` with its reason,
and reports mtimes explicitly labelled as an out-of-band source.  It does not
decide the disposition; that is under adjudication.  Judging the clause from
mtime and calling it green would be the instrument answering confidently about
something it never looked at, which is the failure this gate was built after.

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
DEFAULT_ALSO = [WORKSPACE / "findings" / "evidence" / "queue-v11-split-probe"
                / "criterion-2-net-v12.json"]
DEFAULT_SHA = ("3dfdcfef4abfe6b723b573f35e8ec8f885dcc42a8ed4d8338ad2381eb386"
               "f50f")
DEFAULT_PROFILE = "e2-editor-v12"
EXPECTED_NE = {"notice-action-recovers-the-session",
               "a-refused-action-is-reported-and-changes-nothing"}
EXPECTED_PASS = 38

# Files in the bank directory that are deliberately NOT runs.  Each needs a
# reason, because "ignore what does not parse" is how a bank quietly loses a
# member.  RUNS.md carries the same dispositions in prose.
NON_RUNS = {
    "interrupted-2026-08-29-0050-partial.json":
        "partial snapshot of an interrupted run: complete=false, no ok, "
        "6 checks. Renamed out of the soak-run-* namespace rather than "
        "deleted, so the interruption stays visible.",
}


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
    return {
        "report": rel(path),
        "clean": all(clauses.values()),
        "clauses": clauses,
        "composition": composition,
        "profile": candidate.get("profile"),
        "pageSha256": candidate.get("pageSha256"),
        # OUT-OF-BAND. Not evidence; see the module docstring.
        "mtimeUtc_OUT_OF_BAND": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def judge(bank: Path, also: list[Path], expect_sha: str, expect_profile: str,
          expect_runs: int) -> dict:
    if not bank.is_dir():
        return {"ok": False, "error": f"bank directory does not exist: {bank}"}

    present = sorted(p for p in bank.glob("*.json"))
    # NON-EMPTINESS. A census that searched zero files and reported "zero
    # problems" is the failure mode this tree names explicitly; a renamed
    # directory must go RED, not quiet.
    if not present:
        return {"ok": False,
                "error": f"bank directory holds no *.json at all: {bank}"}

    unclassified = [p.name for p in present
                    if not p.name.startswith("soak-run-")
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

    clauses = {
        "no-unclassified-file": not unclassified,
        "declared-non-runs-present": not declared_missing,
        "every-run-clean": len(clean) == len(runs) and bool(runs),
        "count-reached": len(clean) >= expect_runs,
        "one-page-sha": len(shas) == 1 and shas[0] == expect_sha,
    }

    return {
        "criterion": "soak criterion 1 -- counting clauses only",
        "bank": rel(bank),
        "expected": {"runs": expect_runs, "profile": expect_profile,
                     "pageSha256": expect_sha,
                     "passCount": EXPECTED_PASS,
                     "notEstablished": sorted(EXPECTED_NE)},
        "cleanRuns": len(clean),
        "totalRuns": len(runs),
        "unclassifiedFiles": unclassified,
        "declaredNonRunsMissing": declared_missing,
        "distinctPageSha256": shas,
        "runs": runs,
        "clauses": clauses,
        "ok": all(clauses.values()),
        "calendarDayClause": {
            "status": "NOT_ESTABLISHED",
            "requires": ">=3 calendar days, >=2 runs on each",
            "reason": "The reports carry no wall-clock timestamp; "
                      "`run_e2_c_product_path.py` records only "
                      "performance.now(). The day is knowable only from "
                      "filesystem mtime, which is not part of the evidence and "
                      "does not survive a clone. Verified 2026-09-03. "
                      "Disposition under adjudication; this tool reports the "
                      "clause rather than judging it.",
            "outOfBandMtimeDays": sorted({
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
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    also = DEFAULT_ALSO if args.also is None else list(args.also)
    verdict = judge(args.bank, also, args.expect_page_sha256,
                    args.expect_profile, args.expect_runs)
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

    failures = [name for name, verdict in cases if verdict.get("ok")]
    for name, verdict in cases:
        mark = "RED (correct)" if not verdict.get("ok") else "GREEN (WRONG)"
        print(f"  {mark:14s} {name}")
    if failures:
        print(f"\nself-test FAILED: {len(failures)} case(s) returned green: "
              f"{failures}")
        return 1
    print(f"\nself-test passed: {len(cases)} red cases, all red")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
