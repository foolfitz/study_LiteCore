#!/usr/bin/env python3
"""Judge E2-A from the evidence tree against the frozen matrix.

Two rules shape this file.

The matrix is the authority for *how much* was required, not the evidence.  A
validator that iterates over the runs it finds can only ever report on what
happened to run, and a fixture nobody executed then looks the same as one that
passed.  So the required set is expanded from the matrix first and every cell is
resolved to covered or missing.

The document is the authority for *what happened*.  Every postcondition here is
read out of the saved ODT; the completion event says what the engine believed
and is recorded next to it, never in place of it (finding 020).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_e2_discovery import (  # noqa: E402
    A3_ANCHORS,
    EXPECTED_POSTCONDITIONS,
    inspect_target_paragraph,
    judge_postcondition,
)

# A3's positive matrix, in order.  Each entry is one dispatch whose document
# state is judged on its own -- a cycle that ends correctly after a step went
# the wrong way and was corrected is not a pass.
A3_STEPS = ("cycle-list-unordered", "cycle-list-ordered", "cycle-list-none",
            "roundtrip-heading", "roundtrip-body")

# A3 runs the positive matrix; the other two are A5's job and are named here so
# the coverage report can say they are absent rather than omit them.
A3_FIXTURES = ("styled-list", "multi-paragraph", "plain-grapheme")
A5_ONLY_FIXTURES = ("table-boundary",)

COMPLETION = "verified-format-readback"

# A5's fixed order, matching the app.  table-boundary's own case is inserted
# only for that fixture.
A5_CASES = ("unsupported-action", "stale-revision", "state-crosstalk",
            "list-teardown", "timeout-after-dispatch")
A5_FIXTURES = A3_FIXTURES + A5_ONLY_FIXTURES

# A4's sequence, mirroring the app: drive each action to its target, then press
# it twice more on a paragraph already there.
A4_ACTIONS = ("list-unordered", "list-ordered", "list-none",
              "paragraph-heading", "paragraph-body")
A4_STEPS = tuple(f"{key}-{suffix}" for key in A4_ACTIONS
                 for suffix in ("set", "repeat-1", "repeat-2"))


# A5's cases, and what each one has to show.  Every judgement below is made
# from something the evidence carries, not from the case's own status word:
# "completed" says the client's promise resolved, which is not the same claim
# as "the document agrees".
#
# The crosstalk case is judged on the readback markup's *text*.  The serialiser
# writes the paragraph's content, so "which paragraph did the barrier read" is
# directly visible -- and a check that reads it cannot pass on both answers the
# way the earlier structural check did (finding 033: the crosstalk anchor was
# itself a Heading 1 while the case dispatched set-paragraph-heading).
A5_DISPATCH_ANCHORS = dict(A3_ANCHORS, **{"table-boundary": "E1-CELL-A1"})
A5_CROSSTALK_ANCHORS = {
    "styled-list": "E1-LIST-ONE",
    "multi-paragraph": "E1-MULTI-START",
    "plain-grapheme": "E1-PLAIN-START",
    "table-boundary": "E1-TABLE-BEFORE",
}


def _barrier(case: dict[str, Any]) -> dict[str, Any]:
    outcome = case.get("outcome")
    if isinstance(outcome, dict) and outcome.get("formatBarrier"):
        return outcome["formatBarrier"]
    return ((case.get("error") or {}).get("details") or {}).get("formatBarrier") or {}


def judge_a5_case(case: dict[str, Any], fixture: str, close_ms: Any,
                  close_budget_ms: int) -> dict[str, Any]:
    name = case.get("case")
    status = case.get("status")
    code = (case.get("error") or {}).get("code")
    outcome = case.get("outcome") if isinstance(case.get("outcome"), dict) else {}
    barrier = _barrier(case)
    readback = barrier.get("readback") or {}
    html = readback.get("html") or ""
    note: str
    ok: bool

    if name == "unsupported-action":
        ok = status == "rejected" and code == "EDITOR_ACTION_UNSUPPORTED"
        note = "typed rejection before anything is dispatched"
    elif name == "stale-revision":
        # "Zero mutation" is a claim about the *stale* dispatch, not about the
        # case: the case ages the revision on purpose by performing a real
        # action first, so revisionBefore != revisionAfter is expected and
        # asserting otherwise would fail a correct product.  What must hold is
        # that the aging action moved the revision and the refused one did not.
        aged = case.get("staleRevision") != case.get("currentRevision")
        ok = (status == "rejected" and code == "STALE_REVISION" and aged
              and case.get("revisionAfter") == case.get("currentRevision"))
        note = ("typed rejection, and the revision sits where the aging action"
                " left it -- the refused dispatch moved nothing")
    elif name == "state-crosstalk":
        dispatched = A5_DISPATCH_ANCHORS.get(fixture)
        moved = A5_CROSSTALK_ANCHORS.get(fixture)
        ok = (status == "completed"
              and outcome.get("completion") == COMPLETION
              and readback.get("restoreConfirmed") is True
              and readback.get("blockTag") == "h1"
              # The discriminating half: the markup names the paragraph.
              and bool(dispatched) and dispatched in html
              and bool(moved) and moved not in html)
        note = ("the readback markup contains the dispatched paragraph's text and"
                " not the paragraph the caller tried to move to")
    elif name == "table-boundary":
        # Revised 2026-08-11: the frozen "typed rejection" was contradicted by
        # measurement.  Either outcome is acceptable; what is not acceptable is
        # a completion the document does not support.
        if status == "completed":
            ok = (outcome.get("completion") == COMPLETION
                  and readback.get("listTag") == "ul"
                  and A5_DISPATCH_ANCHORS[fixture] in html)
        else:
            ok = bool(code) and case.get("revisionBefore") == case.get("revisionAfter")
        note = "a typed outcome, and the readback agrees with it"
    elif name == "list-teardown":
        ok = (status == "completed" and case.get("cycleComplete") is True
              and isinstance(close_ms, (int, float))
              and close_ms < close_budget_ms)
        note = "the list cycle completed and close returned inside the timeout"
    elif name == "timeout-after-dispatch":
        # The caller must actually have timed out, or the case measured nothing;
        # and no retry may be issued on its behalf.
        ok = (case.get("timedOut") is True
              and (case.get("timeoutError") or {}).get("code") == "TIMEOUT")
        note = "the caller timed out and nothing was replayed for it"
    else:
        return {"case": name, "judged": False,
                "why": "no registered expectation for this case"}
    return {"case": name, "judged": True, "pass": ok, "status": status,
            "code": code, "asks": note}


def judge_a5_attempt(path: Path, fixture: str,
                     close_budget_ms: int) -> dict[str, Any]:
    result = json.loads((path / "result.json").read_text(encoding="utf-8"))
    expected = list(A5_CASES)
    if fixture == "table-boundary":
        expected.insert(3, "table-boundary")
    present = {case.get("case"): case for case in result.get("a5", [])}
    cases = []
    for name in expected:
        case = present.get(name)
        if case is None:
            cases.append({"case": name, "judged": True, "pass": False,
                          "why": "case missing from the run"})
            continue
        cases.append(judge_a5_case(case, fixture, result.get("closeMs"),
                                   close_budget_ms))
    return {
        "path": str(path),
        "browser": result.get("browser"),
        "browserVersion": result.get("browserVersion"),
        "wasmSha256": (result.get("manifest") or {}).get(
            "diagnostic", {}).get("wasmSha256"),
        "cases": cases,
        "pass": all(case.get("pass") for case in cases),
    }


def attempts(root: Path, browser: str, fixture: str,
             tree: str = "browser") -> list[Path]:
    base = root / tree / browser / fixture
    if not base.is_dir():
        return []
    found = []
    if (base / "result.json").is_file():
        found.append(base)
    found.extend(sorted(path for path in base.glob("attempt-*")
                        if (path / "result.json").is_file()))
    return found


def judge_attempt(path: Path, fixture: str,
                  labels: tuple = A3_STEPS) -> dict[str, Any]:
    result = json.loads((path / "result.json").read_text(encoding="utf-8"))
    dispatch = {entry.get("label"): entry for entry in result.get("dispatch", [])}
    steps: list[dict[str, Any]] = []
    for label in labels:
        entry = dispatch.get(label)
        if entry is None:
            steps.append({"label": label, "present": False, "pass": False,
                          "why": "step missing from the run"})
            continue
        completion = (entry.get("result") or {}).get("completion")
        readback = ((entry.get("result") or {}).get("formatBarrier") or {}).get(
            "readback") or {}
        document = path / f"after-{label}.odt"
        inspection = inspect_target_paragraph(document, A3_ANCHORS[fixture])
        verdict = judge_postcondition(label, inspection)
        # `changed` must not be claimed: the readback answers what the document
        # is, not who put it there (SPEC E2-A 2.9).
        claimed_changed = (entry.get("result") or {}).get("changed")
        steps.append({
            "label": label,
            "present": True,
            "completion": completion,
            "completionOk": completion == COMPLETION,
            "changedClaim": claimed_changed,
            "changedNotClaimed": claimed_changed is None,
            "restoreConfirmed": readback.get("restoreConfirmed"),
            "readback": {key: readback.get(key)
                         for key in ("listTag", "blockTag", "bytes")},
            "document": {key: inspection.get(key)
                         for key in ("insideList", "listKind", "listLevel",
                                     "paragraphStyle", "resolvedParagraphStyle")},
            "postcondition": verdict,
            "expected": EXPECTED_POSTCONDITIONS.get(label),
            "pass": bool(
                completion == COMPLETION
                and claimed_changed is None
                and readback.get("restoreConfirmed") is True
                and verdict.get("met") is True),
        })
    return {
        "path": str(path),
        "browser": result.get("browser"),
        "browserVersion": result.get("browserVersion"),
        "profile": result.get("profile"),
        "wasmSha256": (result.get("manifest") or {}).get(
            "diagnostic", {}).get("wasmSha256"),
        "steps": steps,
        "pass": all(step["pass"] for step in steps) and len(steps) == len(labels),
    }


def main() -> int:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path,
                        default=project.parent / "findings" / "evidence"
                        / "sdk-e2" / "discovery")
    parser.add_argument("--matrix", type=Path,
                        default=project / "e2" / "discovery-matrix-v1.json")
    parser.add_argument(
        "--profile", default="e2-format-discovery",
        help="which built profile's hash counts as 'the engine in dist right "
             "now'.  Task #47 P3 re-runs the same matrix against "
             "e2-combination; without this the binding check would compare "
             "those runs to the discovery hash and score every cell zero.")
    parser.add_argument("--output", type=Path,
                        default=project.parent / "findings" / "evidence"
                        / "sdk-e2" / "summary.json")
    args = parser.parse_args()

    # Finding 027's rule, applied to E2-A: recompute the identity of the thing
    # under test at verdict time instead of trusting what the evidence says
    # about itself.  A3 and A4 passed on one engine build; changing the engine
    # afterwards does not make their evidence wrong, it makes it evidence about
    # a different artifact, and the verdict has to say so out loud.
    profile_manifest = (project / "dist" / "profiles" / args.profile
                        / "sdk-manifest.json")
    current_wasm = None
    if profile_manifest.is_file():
        current_wasm = json.loads(profile_manifest.read_text(encoding="utf-8"))[
            "diagnostic"]["wasmSha256"]

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    required = matrix["thresholds"]["positiveRepetitionsPerBrowser"]
    browsers = list(matrix["browsers"])

    coverage: dict[str, Any] = {}
    runs: list[dict[str, Any]] = []
    for browser in browsers:
        for fixture in A3_FIXTURES:
            found = attempts(args.evidence_root, browser, fixture)
            judged = [judge_attempt(path, fixture) for path in found]
            runs.extend(judged)
            # Only runs of the engine that is in dist/ right now can cover a
            # cell.  Older runs are kept and counted as superseded rather than
            # deleted -- they are real measurements, of a different artifact.
            bound = [item for item in judged
                     if item.get("wasmSha256") == current_wasm]
            passing = sum(1 for item in bound if item["pass"])
            coverage[f"{browser}/{fixture}"] = {
                "required": required,
                "found": len(found),
                "bound": len(bound),
                "superseded": len(judged) - len(bound),
                "passing": passing,
                # Missing is a distinct state from failing, and the verdict has
                # to be able to say which one it is.
                "state": ("missing" if not found else
                          "short" if passing < required else "covered"),
            }

    a4_coverage: dict[str, Any] = {}
    a4_runs: list[dict[str, Any]] = []
    for browser in browsers:
        for fixture in A3_FIXTURES:
            found = attempts(args.evidence_root, browser, fixture, tree="repeat")
            judged = [judge_attempt(path, fixture, A4_STEPS) for path in found]
            a4_runs.extend(judged)
            bound = [item for item in judged
                     if item.get("wasmSha256") == current_wasm]
            passing = sum(1 for item in bound if item["pass"])
            a4_coverage[f"{browser}/{fixture}"] = {
                "required": required, "found": len(found), "bound": len(bound),
                "superseded": len(judged) - len(bound), "passing": passing,
                "state": ("missing" if not bound else
                          "short" if passing < required else "covered"),
            }

    # A5 had no verdict at all until now: the cases ran and were read by hand.
    # A negative suite nobody judges is the same shape as a check that cannot
    # fail, so it gets the same treatment as A3/A4 -- required cells expanded
    # from the matrix, coverage resolved to covered or missing, artifact-bound.
    negative_required = matrix["thresholds"]["negativeRepetitionsPerBrowser"]
    close_budget = matrix["thresholds"]["openSaveTimeoutMs"]
    a5_coverage: dict[str, Any] = {}
    a5_runs: list[dict[str, Any]] = []
    for browser in browsers:
        for fixture in A5_FIXTURES:
            found = attempts(args.evidence_root, browser, fixture, tree="negative")
            judged = [judge_a5_attempt(path, fixture, close_budget)
                      for path in found]
            a5_runs.extend(judged)
            bound = [item for item in judged
                     if item.get("wasmSha256") == current_wasm]
            passing = sum(1 for item in bound if item["pass"])
            a5_coverage[f"{browser}/{fixture}"] = {
                "required": negative_required, "found": len(found),
                "bound": len(bound), "superseded": len(judged) - len(bound),
                "passing": passing,
                "state": ("missing" if not bound else
                          "short" if passing < negative_required else "covered"),
            }
    a5_gaps = {key: value for key, value in a5_coverage.items()
               if value["state"] != "covered"}
    a5_covered = [key for key, value in a5_coverage.items()
                  if value["state"] == "covered"]
    a5_decision = ("A5_NOT_RUN" if not a5_covered else
                   "A5_PARTIAL_COVERAGE" if a5_gaps else "A5_PASS")

    def binding(runs_: list) -> dict[str, Any]:
        seen = sorted({item.get("wasmSha256") for item in runs_ if item.get("wasmSha256")})
        stale = [value for value in seen if value != current_wasm]
        return {
            "currentProfileWasmSha256": current_wasm,
            "evidenceWasmSha256": seen,
            # Renamed 2026-08-11.  This was "boundToCurrentBuild", which read as
            # a statement about the verdict and printed false beside A3_PASS --
            # two fields of one report contradicting each other.  It has always
            # answered a narrower question: is every run in the tree, including
            # the superseded ones kept on purpose, from the current build.
            "allEvidenceIsCurrentBuild": bool(seen) and not stale,
            # The verdict's own rule, stated rather than inferred: coverage
            # counts only runs whose wasmSha256 matches the profile in dist/.
            "verdictCountsOnlyCurrentBuild": True,
            "staleBuilds": stale,
        }

    covered = [key for key, value in coverage.items() if value["state"] == "covered"]
    gaps = {key: value for key, value in coverage.items()
            if value["state"] != "covered"}

    if not covered:
        decision = "A3_NOT_RUN"
    elif gaps:
        decision = "A3_PARTIAL_COVERAGE"
    else:
        decision = "A3_PASS"

    a4_gaps = {key: value for key, value in a4_coverage.items()
               if value["state"] != "covered"}
    a4_covered = [key for key, value in a4_coverage.items()
                  if value["state"] == "covered"]
    a4_decision = ("A4_NOT_RUN" if not a4_covered else
                   "A4_PARTIAL_COVERAGE" if a4_gaps else "A4_PASS")

    summary = {
        "schemaVersion": 1,
        "release": "E2-A",
        "phase": "A3",
        "decision": decision,
        "matrixStatus": matrix["status"],
        "requiredPerBrowserPerFixture": required,
        "coverage": coverage,
        "artifactBinding": binding(runs),
        "coveredCells": covered,
        "gaps": gaps,
        # Named so a reader does not have to infer why table-boundary is absent.
        "fixturesDeferredToA5": list(A5_ONLY_FIXTURES),
        "a5": {
            "decision": a5_decision,
            "coverage": a5_coverage,
            "artifactBinding": binding(a5_runs),
            "gaps": a5_gaps,
            "runs": a5_runs,
            "asks": "the negative and boundary cases. state-crosstalk is judged on the"
                    " readback markup's own text -- the serialiser writes the paragraph"
                    " content, so which paragraph the barrier read is directly visible"
                    " rather than inferred from a structural tag that both answers could"
                    " satisfy (finding 033).",
            "revised": "table-boundary's frozen expectation was 'typed rejection, then a"
                       " fresh Worker'. Measured: the cell paragraph accepts"
                       " set-list-unordered. The expectation is now 'a typed outcome, and"
                       " the readback agrees'; see the matrix revisions array.",
        },
        "runs": runs,
        "a4": {
            "decision": a4_decision,
            "coverage": a4_coverage,
            "artifactBinding": binding(a4_runs),
            "gaps": a4_gaps,
            "runs": a4_runs,
            "asks": "each action driven to its target once, then pressed twice more"
                    " on a paragraph already there: the document must stay put"
                    " (a toggle would invert) and the barrier must still complete"
                    " even though core broadcasts nothing when nothing changes",
        },
        "narrowings": [
            "set-paragraph-body's postcondition is 'not a heading', not 'is Text body':"
            " the serialiser writes <p> for both Text body and the default style"
            " (SPEC E2-A 2.8 narrowing 2). The saved-ODT check here is stricter than"
            " the barrier's -- it compares the resolved paragraph style -- so the two"
            " are recorded separately rather than merged.",
            "The readback markup is a serialiser output, not a documented contract."
            " Matching it whole pins a serialiser; cross-version stability is A7's job"
            " and is not validated here. A7's round-trip slice has since measured the"
            " saved documents against a different LibreOffice version (see"
            " discovery/a7-roundtrip/report.json), which narrows this but does not"
            " close it: it says the packages reopen, not that the readback markup this"
            " barrier matches on is stable across versions.",
        ],
        "notValidated": [
            "A6 secondary capabilities have not run.",
            "A7's round-trip slice has run (discovery/a7-roundtrip/report.json);"
            " A7's regression half -- R6-R8, E1-A/B/C, workspace preflight -- has not,"
            " so A7 as a whole is still unmet and there is still no E2-A verdict.",
            "The commandName attribution added for finding 033 is not demonstrated by"
            " this evidence: selectionBeforeResultCount is 0 on every run, so no foreign"
            " selection ever reached it. The BUSY gate is what the crosstalk case shows.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")

    print(f"A3 decision: {decision}")
    print(f"required per browser per fixture: {required}")
    for key, value in coverage.items():
        print(f"   {key:<28} {value['state']:<8} bound={value.get('bound')} "
              f"superseded={value.get('superseded')} passing={value['passing']}")
    print(f"A5 decision: {a5_decision}")
    for key, value in a5_coverage.items():
        print(f"   {key:<28} {value['state']:<8} bound={value.get('bound')} "
              f"superseded={value.get('superseded')} passing={value['passing']}")
    print(f"A4 decision: {a4_decision}")
    for key, value in a4_coverage.items():
        print(f"   {key:<28} {value['state']:<8} bound={value.get('bound')} "
              f"superseded={value.get('superseded')} passing={value['passing']}")
    failing = [item for item in runs + a4_runs if not item["pass"]]
    if failing:
        print("\nfailing runs:")
        for item in failing:
            bad = [step["label"] for step in item["steps"] if not step["pass"]]
            print(f"   {item['path']}: {bad}")
    a5_failing = [item for item in a5_runs if not item["pass"]]
    if a5_failing:
        print("\nfailing A5 runs:")
        for item in a5_failing:
            bad = [case["case"] for case in item["cases"] if not case.get("pass")]
            print(f"   {item['path']}: {bad}")
    print(f"\nwritten: {args.output}")
    return 0 if (decision == "A3_PASS" and a4_decision == "A4_PASS"
                 and a5_decision == "A5_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
