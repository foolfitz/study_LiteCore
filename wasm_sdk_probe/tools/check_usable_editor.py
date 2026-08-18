#!/usr/bin/env python3
"""Does the acceptance checklist point at things that exist?

Written 2026-08-17, after the short-term goal was described as 零碎 and the
stocktake found no written definition of done.

The obvious response -- write a prose page listing what a usable editor needs --
is the wrong one, and this tree already knows why: a document that cannot be
shown to be wrong is not evidence.  A checklist whose lines are prose drifts the
moment the code moves, and nobody notices, which is the same failure mode as the
`summary.json` that still said "no verdict" a day after the verdict (finding
044).

So the checklist is data, and every line has to name something real:

  * `check`   -- a check id in tools/run_e2_c_product_path.py
  * `queue`   -- an item id in e2/relink-queue-v3.json
  * `finding` -- a numbered file under findings/

This tool resolves all three, and fails when a reference does not resolve.
"Done" for the product goal then means: this is green, every `done` row's check
is green in the runner, and the `blocked` rows' queue items have shipped.

Usage:
  check_usable_editor.py             # resolve every reference, exit 1 on a miss
  check_usable_editor.py --self-test # prove it can say no
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
WORKSPACE = PROJECT.parent

CHECKLIST = PROJECT / "e2" / "usable-editor-checklist.json"
RUNNER = PROJECT / "tools" / "run_e2_c_product_path.py"
QUEUE = PROJECT / "e2" / "relink-queue-v3.json"
FINDINGS = WORKSPACE / "findings"

# The vocabulary lives in the checklist's own `statuses` block, not here.  It
# was duplicated for about ten minutes on 2026-08-17 and immediately drifted:
# adding `partial` to the file left the tool rejecting it, which is the right
# failure but for the wrong reason -- two sources of truth for one list.
def valid_statuses(checklist: dict) -> tuple:
    return tuple(checklist.get("statuses", {}))


def check_ids(runner_text: str) -> set[str]:
    """Every check id the product-path runner can emit.

    Read out of the source rather than by running it: the runner needs a browser
    and several minutes, and this has to be cheap enough to sit in the static
    suite.
    """
    return set(re.findall(r'''\bcheck\(\s*["']([a-z0-9-]+)["']''', runner_text))


def resolve(checklist: dict, runner_text: str, queue: dict,
            findings_dir: Path, report: dict | None = None) -> dict:
    known_checks = check_ids(runner_text)
    known_queue = {item["id"] for item in queue.get("items", [])}
    known_findings = {path.name[:3] for path in findings_dir.glob("*.md")
                      if path.name[:3].isdigit()}

    statuses = valid_statuses(checklist)
    rows, problems = [], []
    if not statuses:
        problems.append("the checklist declares no `statuses` vocabulary")
    for capability in checklist.get("capabilities", []):
        cid = capability.get("id", "?")
        if capability.get("status") not in statuses:
            problems.append(f"{cid}: status {capability.get('status')!r} is not "
                            f"one of {statuses}")
        evidence = capability.get("evidence") or []
        if not evidence:
            # A row with no evidence is the prose this file exists to prevent.
            problems.append(f"{cid}: names no check, queue item or finding")
        resolved = []
        for item in evidence:
            (kind, name), = item.items()
            if kind == "check":
                ok = name in known_checks
                where = "tools/run_e2_c_product_path.py"
            elif kind == "queue":
                ok = name in known_queue
                where = "e2/relink-queue-v3.json"
            elif kind == "finding":
                ok = name in known_findings
                where = "findings/"
            else:
                ok, where = False, "unknown evidence kind"
            if not ok:
                problems.append(f"{cid}: {kind} {name!r} does not exist in {where}")
            resolved.append({"kind": kind, "name": name, "resolves": ok})
        rows.append({"id": cid, "status": capability.get("status"),
                     "evidence": resolved})

    by_status = {s: [r["id"] for r in rows if r["status"] == s]
                 for s in statuses}
    reconciled = reconcile(checklist, report) if report is not None else None
    if reconciled:
        problems.extend(reconciled)
    return {
        "schemaVersion": 1,
        "release": "usable-editor-acceptance",
        "capabilities": rows,
        "byStatus": by_status,
        # None means nobody asked; [] means it was asked and answered.
        "reconciledAgainstReport": None if report is None else {
            "browser": report.get("browser"),
            "servedShell": (report.get("servedShell") or {}).get("servedSha256"),
            "problems": reconciled,
        },
        "problems": problems,
        "ok": not problems,
    }


# --------------------------------------------------------------- the report
#
# Resolving the references answers "does this checklist point at real things".
# It does not answer "are those things GREEN", and until 2026-08-18 nothing did:
# a row could say `done`, its check could be red in every run, and this file
# stayed green.  That is finding 044's shape (a verdict-bound summary still
# saying there was no verdict) moved one file outwards.
#
# The rules below are deliberately two-directional.  A checklist that can only
# go red when something breaks will quietly keep calling a fixed thing
# `blocked`, which is how work gets done twice.  The runner already declares a
# KNOWN_RED stale the moment it passes; this gives the checklist the same
# property.

FINDING_IN_PROSE = re.compile(r"finding\s+(\d{3})")


def baseline_problems(report: dict) -> list[str]:
    """Is this report a run that may be cited as acceptance evidence?

    Not "did it pass" -- whether it describes THIS product.  A mutation run, a
    shim run and a run against an older shell generation all produce perfectly
    well-formed reports, and all three would otherwise be citable.

    The discriminator is `servedShell`, which the runner derives by hashing the
    twelve bundled modules out of the root it actually served.  It is not a flag
    anybody sets, so it cannot be forgotten.
    """
    problems = []
    if report.get("release") != "e2-c-product-path":
        problems.append(f"report is not a product-path run: "
                        f"release={report.get('release')!r}")
    if report.get("mutation") is not None:
        problems.append(f"report is a mutation run ({report['mutation']!r}); a "
                        "mutation run measures the harness, not the product")
    served = report.get("servedShell")
    if not served:
        problems.append("report has no `servedShell`: it predates shell "
                        "identity and cannot be tied to a generation")
        return problems
    if served.get("missing"):
        problems.append(f"the served root was missing bundled modules: "
                        f"{served['missing']}")
    if served.get("servedSha256") != served.get("declaredSha256"):
        problems.append(
            f"the shell that ran is not the declared generation "
            f"({served.get('bundle')}): served "
            f"{str(served.get('servedSha256'))[:16]}, declared "
            f"{str(served.get('declaredSha256'))[:16]} -- a mirror, a shim or an "
            "older run")
    return problems


def reconcile(checklist: dict, report: dict) -> list[str]:
    """Every checklist status, against what the runner actually measured."""
    problems = baseline_problems(report)
    if problems:
        # Deliberately first and alone: reconciling a report that does not
        # describe this product would produce confident nonsense.
        return problems

    outcomes = {c["id"]: c for c in report.get("checks") or []}
    known_red = report.get("knownRed") or {}
    statuses = checklist.get("statuses", {})
    cited_known_red: set[str] = set()

    for capability in checklist.get("capabilities", []):
        cid = capability.get("id", "?")
        status = capability.get("status")
        evidence = capability.get("evidence") or []
        checks = [item["check"] for item in evidence if "check" in item]
        findings = {item["finding"] for item in evidence if "finding" in item}

        # `done` and `partial` are both defined in the checklist's own
        # vocabulary as "有一格會失敗的檢查在跑，而且它是綠的".  A row that
        # names only a finding or a queue item satisfies that sentence by
        # citation rather than by measurement.
        if status in ("done", "partial") and not checks:
            problems.append(
                f"{cid}: status {status!r} but the row names no check -- "
                f"{statuses.get(status, 'that status')} requires one")

        # `partial` is the one status that may cite a KNOWN_RED check, because
        # its whole meaning is "green as far as it goes, and the part it does
        # not cover is named".  A named, filed defect IS such a part.  It still
        # has to rest on at least one GREEN check, or "partial" would be a way
        # to hold a row up on nothing.  `done` may never cite one.
        green_checks = [n for n in checks
                        if n not in known_red
                        and (outcomes.get(n) or {}).get("outcome") == "PASS"]
        if status == "partial" and checks and not green_checks:
            problems.append(
                f"{cid}: status 'partial' but no check of its own is green; "
                f"partial means green as far as it goes")

        for name in checks:
            entry = outcomes.get(name)
            if status in ("done", "partial"):
                if entry is None:
                    problems.append(f"{cid}: check {name!r} did not run in this "
                                    "report")
                elif name in known_red:
                    cited_known_red.add(name)
                    named = set(FINDING_IN_PROSE.findall(known_red[name]))
                    if status == "done":
                        problems.append(
                            f"{cid}: status 'done' but check {name!r} is "
                            f"declared KNOWN_RED -- {known_red[name]}")
                    elif not (named & findings):
                        problems.append(
                            f"{cid}: check {name!r} is KNOWN_RED for "
                            f"{sorted(named) or 'an unnamed defect'} but the row "
                            f"cites {sorted(findings) or 'no finding'}")
                elif entry.get("outcome") != "PASS":
                    problems.append(
                        f"{cid}: status {status!r} but check {name!r} is "
                        f"{entry.get('outcome')}")
            else:
                if entry is not None and entry.get("outcome") == "PASS":
                    problems.append(
                        f"{cid}: status {status!r} is out of date -- check "
                        f"{name!r} PASSED in this report")
                if name in known_red:
                    # A red row is allowed to be red for a named defect, and
                    # only for one the row itself cites.  Binding it to the
                    # FINDING rather than to the status word is what lets
                    # `partial` and `unverified` carry a known defect without
                    # letting `done` do it.
                    cited_known_red.add(name)
                    named = set(FINDING_IN_PROSE.findall(known_red[name]))
                    if not (named & findings):
                        problems.append(
                            f"{cid}: check {name!r} is KNOWN_RED for "
                            f"{sorted(named) or 'an unnamed defect'} but the row "
                            f"cites {sorted(findings) or 'no finding'}")

    for name in known_red:
        if name not in cited_known_red:
            problems.append(
                f"check {name!r} is declared KNOWN_RED but no checklist row "
                "cites it -- the checklist does not know about that defect")
    return problems


def load() -> tuple[dict, str, dict]:
    return (json.loads(CHECKLIST.read_text(encoding="utf-8")),
            RUNNER.read_text(encoding="utf-8"),
            json.loads(QUEUE.read_text(encoding="utf-8")))


def self_test() -> int:
    failures: list[str] = []

    def verify(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    checklist, runner_text, queue = load()
    report = resolve(checklist, runner_text, queue, FINDINGS)
    verify("the checklist as it stands resolves", report["ok"],
           json.dumps(report["problems"], ensure_ascii=False))

    # The extractor has to actually find checks, or every `check:` reference
    # would resolve to nothing and the run above would be red for one reason
    # while looking red for another.
    found = check_ids(runner_text)
    verify("the runner's check ids are extractable", len(found) >= 5,
           f"found {len(found)}")

    # Three negative controls, one per evidence kind.  Each must be REJECTED --
    # a reference that resolves to nothing is exactly what this tool exists to
    # catch, and if any of them passes, the corresponding kind is unchecked.
    for kind, bogus in (("check", "no-such-check-anywhere"),
                        ("queue", "no-such-queue-item"),
                        ("finding", "999")):
        broken = json.loads(json.dumps(checklist))
        broken["capabilities"][0]["evidence"] = [{kind: bogus}]
        verify(f"a {kind} that does not exist is caught",
               not resolve(broken, runner_text, queue, FINDINGS)["ok"])

    # And a row with no evidence at all -- prose wearing a checklist's clothes.
    empty = json.loads(json.dumps(checklist))
    empty["capabilities"][0]["evidence"] = []
    verify("a row with no evidence is caught",
           not resolve(empty, runner_text, queue, FINDINGS)["ok"])

    # A status outside the declared set, so the vocabulary cannot drift either.
    drifted = json.loads(json.dumps(checklist))
    drifted["capabilities"][0]["status"] = "mostly-fine"
    verify("an undeclared status is caught",
           not resolve(drifted, runner_text, queue, FINDINGS)["ok"])

    # And the vocabulary itself: with `statuses` removed there is nothing to
    # validate against, and silently accepting every status would be worse than
    # rejecting every one.
    vocabulary_gone = json.loads(json.dumps(checklist))
    vocabulary_gone.pop("statuses", None)
    verify("a checklist with no status vocabulary is caught",
           not resolve(vocabulary_gone, runner_text, queue, FINDINGS)["ok"])

    # ------------------------------------------------- reconciling a report
    #
    # Every case below is a report that a checklist-with-no-report would accept
    # without comment.  If any of them passes, the corresponding rule is not
    # doing anything.

    def synthetic_report(source: dict) -> dict:
        """The report a clean run would produce for `source`, by construction.

        Built from the checklist rather than pasted from a real run, so the
        self-test follows the checklist instead of freezing a copy of it.
        """
        checks, known_red = [], {}
        for capability in source.get("capabilities", []):
            status = capability.get("status")
            findings = [item["finding"]
                        for item in capability.get("evidence") or []
                        if "finding" in item]
            for item in capability.get("evidence") or []:
                if "check" not in item:
                    continue
                name = item["check"]
                if status in ("done", "partial"):
                    checks.append({"id": name, "ok": True, "outcome": "PASS"})
                elif status == "blocked":
                    checks.append({"id": name, "ok": False, "outcome": "FAIL"})
                    known_red[name] = ("finding "
                                       + (findings[0] if findings else "000")
                                       + ": declared for the self-test")
                else:
                    checks.append({"id": name, "ok": False,
                                   "outcome": "NOT_ESTABLISHED"})
        return {
            "release": "e2-c-product-path",
            "browser": "chrome",
            "mutation": None,
            "servedShell": {"bundle": "e2/editor-shell-v2-bundle-v16.json",
                            "declaredSha256": "deadbeef", "servedSha256": "deadbeef",
                            "missing": []},
            "checks": checks,
            "knownRed": known_red,
        }

    baseline = synthetic_report(checklist)
    verify("a clean baseline report reconciles",
           not reconcile(checklist, baseline),
           json.dumps(reconcile(checklist, baseline), ensure_ascii=False))

    # Non-vacuity: the positive control above must have had rows to judge.  A
    # reconcile() that silently examined nothing would pass it.
    verify("the baseline report actually exercises checks",
           len(baseline["checks"]) >= 5, f"{len(baseline['checks'])} checks")

    def rejects(name: str, mutate) -> None:
        broken = json.loads(json.dumps(baseline))
        broken_list = json.loads(json.dumps(checklist))
        mutate(broken, broken_list)
        verify(name, bool(reconcile(broken_list, broken)))

    rejects("a mutation run is refused as acceptance evidence",
            lambda r, c: r.update(mutation="caret"))
    rejects("a run against another shell generation is refused",
            lambda r, c: r["servedShell"].update(servedSha256="0" * 64))
    rejects("a run with a bundled module missing is refused",
            lambda r, c: r["servedShell"].update(missing=["sdk/document-sdk.js"]))
    rejects("a report with no served-shell identity is refused",
            lambda r, c: r.pop("servedShell"))
    rejects("a report that is not a product-path run is refused",
            lambda r, c: r.update(release="something-else"))

    def first_with(source: dict, status: str) -> dict | None:
        for capability in source.get("capabilities", []):
            if capability.get("status") == status and any(
                    "check" in item for item in capability.get("evidence") or []):
                return capability
        return None

    def done_row(c: dict) -> dict:
        return first_with(c, "done")

    rejects("a `done` row whose check FAILED is caught",
            lambda r, c: [ch.update(ok=False, outcome="FAIL")
                          for ch in r["checks"]
                          if ch["id"] in {i["check"] for i
                                          in done_row(c)["evidence"]
                                          if "check" in i}])
    rejects("a `done` row whose check did not run is caught",
            lambda r, c: r.update(checks=[
                ch for ch in r["checks"]
                if ch["id"] not in {i["check"] for i in done_row(c)["evidence"]
                                    if "check" in i}]))
    rejects("a `done` row that names no check at all is caught",
            lambda r, c: done_row(c).update(
                evidence=[{"finding": "058"}]))
    rejects("a `blocked` row whose check PASSED is caught as stale",
            lambda r, c: [ch.update(ok=True, outcome="PASS")
                          for ch in r["checks"]
                          if ch["id"] in {i["check"] for i
                                          in first_with(c, "blocked")["evidence"]
                                          if "check" in i}])
    rejects("a KNOWN_RED check on a `done` row is caught",
            lambda r, c: r["knownRed"].update({
                next(i["check"] for i in done_row(c)["evidence"]
                     if "check" in i): "finding 059: declared"}))
    rejects("a KNOWN_RED for a defect the row does not cite is caught",
            lambda r, c: r["knownRed"].update({
                k: "finding 123: something else" for k in r["knownRed"]}))
    def partial_row(c: dict) -> dict:
        return first_with(c, "partial")

    rejects("a `partial` row resting only on a KNOWN_RED check is caught",
            lambda r, c: (
                r["knownRed"].update({
                    n: "finding 059: declared"
                    for n in [i["check"] for i in partial_row(c)["evidence"]
                              if "check" in i]}),
                partial_row(c).update(evidence=partial_row(c)["evidence"]
                                      + [{"finding": "059"}])))
    rejects("a `partial` row citing a KNOWN_RED for a defect it does not name "
            "is caught",
            lambda r, c: (
                r["checks"].append({"id": "extra-red", "ok": False,
                                    "outcome": "FAIL"}),
                r["knownRed"].update({"extra-red": "finding 777: elsewhere"}),
                partial_row(c)["evidence"].append({"check": "extra-red"})))

    rejects("a KNOWN_RED no checklist row cites is caught",
            lambda r, c: r["knownRed"].update({
                "a-check-nobody-lists": "finding 059: orphaned"}))

    total = 24
    print(f"\nself-test: {total - len(failures)}/{total} checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path,
                        help="a product-path run's JSON; reconcile every "
                             "status against what it measured")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    checklist, runner_text, queue = load()
    run = (json.loads(args.report.read_text(encoding="utf-8"))
           if args.report else None)
    report = resolve(checklist, runner_text, queue, FINDINGS, run)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
