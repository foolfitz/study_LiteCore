#!/usr/bin/env python3
"""Judge SPEC E2-C phase D0 against the frozen matrix.

Reads saved files only, so the verdict can be recomputed without a browser --
and, more to the point, so the criteria and the run are separable.  The criteria
are in e2/validation-matrix-v1.json and were frozen before the first round; this
applies them.

`--self-test` flips each predicate and requires the flip to go red.  E2-B's
lesson: an analyzer written after a prediction once replaced a pre-registered
criterion, and the replacement made the arm pass.  Ad hoc mutation checks catch
that once; a self-test catches it every time.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e2_c_matrix_entry import require_entry  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
MATRIX = PROJECT / "e2" / "validation-matrix-v1.json"

BODY_OPEN = b"<office:body>"
BODY_CLOSE = b"</office:body>"

MOVE = {"move-character-left", "move-character-right"}
DELETE = {"delete-backward", "delete-forward"}
FORMAT = {"set-bold", "set-italic", "set-underline", "set-strikethrough"}
PARAGRAPH = {"set-list-none", "set-list-unordered", "set-list-ordered",
             "set-paragraph-heading", "set-paragraph-body"}
FORBIDDEN_FIELDS = ("keyCode", "unoCommand", "command", "method")


def body_bytes(odt: Path) -> bytes | None:
    """The <office:body> element verbatim -- not content.xml.

    Automatic styles renumber on their own and meta carries timestamps, so
    comparing whole files reports differences that are not mutations.  Same
    criterion the E2-B negative matrix used.
    """
    if not odt.is_file():
        return None
    with zipfile.ZipFile(odt) as archive:
        content = archive.read("content.xml")
    start = content.find(BODY_OPEN)
    end = content.find(BODY_CLOSE)
    if start < 0 or end < 0:
        return None
    return content[start:end + len(BODY_CLOSE)]


def envelope_problems(action: str, attempt: dict) -> list[str]:
    envelope = attempt.get("envelope") or {}
    payload = envelope.get("payload") or {}
    result = attempt.get("result") or {}
    out: list[str] = []
    if envelope.get("operation") != "editorActionV2":
        out.append(f"{action}: dispatched through {envelope.get('operation')}")
    if payload.get("action") != action:
        out.append(f"{action}: envelope carries {payload.get('action')}")
    if not isinstance(payload.get("documentHandle"), int) \
            or payload.get("documentHandle", 0) <= 0:
        out.append(f"{action}: no document handle in the envelope")
    if payload.get("expectedRevision") != result.get("beforeRevision"):
        out.append(f"{action}: expectedRevision {payload.get('expectedRevision')} "
                   f"but the result says before {result.get('beforeRevision')}")
    if payload.get("extendSelection") is not False:
        out.append(f"{action}: extendSelection is {payload.get('extendSelection')}")
    expected_enabled = action in FORMAT
    if payload.get("enabled") is not expected_enabled:
        out.append(f"{action}: enabled is {payload.get('enabled')}, "
                   f"expected {expected_enabled}")
    for field in FORBIDDEN_FIELDS:
        if field in payload:
            out.append(f"{action}: envelope carries the forbidden field {field}")
    return out


def result_problems(action: str, attempt: dict) -> list[str]:
    result = attempt.get("result")
    if not result:
        return [f"{action}: no typed result ({(attempt.get('error') or {}).get('code')})"]
    before = result.get("beforeRevision")
    after = result.get("revision")
    completion = str(result.get("completion") or "")
    changed = result.get("changed")
    out: list[str] = []
    if action in MOVE:
        if after != before or changed is not False \
                or not completion.startswith("documented-callback-"):
            out.append(f"{action}: movement postcondition not met ({result})")
    elif action in DELETE:
        if completion != "verified-selection-delete" or changed is not True \
                or after != before + 1:
            out.append(f"{action}: delete postcondition not met ({result})")
    elif action in PARAGRAPH:
        if completion != "verified-format-readback" or changed is not None \
                or after != before + 1:
            out.append(f"{action}: route C postcondition not met ({result})")
    else:
        if completion != "uno-command-result" or changed is not True \
                or after != before + 1:
            out.append(f"{action}: mutation postcondition not met ({result})")
    return out


def judge(result: dict, evidence: Path, matrix: dict) -> dict:
    cells = result.get("cells") or {}
    declared = set(matrix["productActions"])
    problems: list[str] = []
    per_cell: dict[str, dict] = {}

    if not result.get("complete") or result.get("error"):
        problems.append(f"run did not complete: {result.get('error')}")
    if (result.get("attribution") or {}).get("consistent") is not True:
        problems.append("attribution inconsistent: the page ran on a different "
                        "artifact than the runner hashed")

    inventory = cells.get("d0-inventory") or {}
    baseline = matrix["baseline"]
    for field in ("wasmSha256", "loaderSha256", "workerSha256"):
        if inventory.get(field) != baseline[field]:
            problems.append(f"d0-inventory: {field} is not the frozen baseline")
    if set(inventory.get("declaredActions") or []) != declared:
        problems.append("d0-inventory: the profile declares a different action set "
                        "than the matrix froze")
    per_cell["d0-inventory"] = {"pass": not problems}

    reach = cells.get("d0-reachability-single-client") or {}
    attempts = {item["action"]: item for item in reach.get("attempts") or []}
    reach_problems: list[str] = []
    missing = sorted(declared - set(attempts))
    if missing:
        reach_problems.append(f"never attempted: {missing}")
    for action in sorted(declared & set(attempts)):
        attempt = attempts[action]
        if not attempt.get("dispatched"):
            reach_problems.append(f"{action}: not dispatched exactly once")
            continue
        reach_problems += envelope_problems(action, attempt)
        reach_problems += result_problems(action, attempt)
    per_cell["d0-reachability-single-client"] = {
        "pass": not reach_problems, "problems": reach_problems,
        "reached": sum(1 for a in attempts.values() if a.get("result")),
        "declared": len(declared),
    }
    problems += reach_problems

    control = cells.get("d0-reachability-control-undeclared") or {}
    control_ok = (control.get("refused") is True
                  and control.get("actionsDispatched") == 0)
    if not control_ok:
        problems.append("the undeclared-action control did not refuse cleanly")
    per_cell["d0-reachability-control-undeclared"] = {"pass": control_ok}

    session = cells.get("d0-session-opens") or {}
    session_ok = (session.get("state") == "ready"
                  and session.get("clientReplacements") == 1)
    if not session_ok:
        problems.append(f"the v2 session did not reach ready: {session}")
    per_cell["d0-session-opens"] = {"pass": session_ok}

    surface = cells.get("d0-no-diagnostic-surface") or {}
    surface_ok = (not surface.get("diagnosticCapabilities")
                  and (surface.get("editorActionV1") or {}).get("refused") is True)
    if not surface_ok:
        problems.append("the profile exposes a diagnostic surface or accepted "
                        "editorActionV1")
    per_cell["d0-no-diagnostic-surface"] = {"pass": surface_ok}

    # Zero mutation, judged on the saved bytes rather than on the refusal code.
    # A cell that only checked the code would pass just as happily if the engine
    # had refused loudly and mutated anyway.
    for cell_id, label in (("d0-unknown-action", "unknown-action"),
                           ("d0-forbidden-keycode", "forbidden-keyCode"),
                           ("d0-forbidden-unocommand", "forbidden-unoCommand"),
                           ("d0-forbidden-command", "forbidden-command")):
        cell = cells.get(cell_id) or {}
        before = body_bytes(evidence / "saved" / f"before-{label}.odt")
        after = body_bytes(evidence / "saved" / f"after-{label}.odt")
        cell_problems: list[str] = []
        if cell.get("refused") is not True:
            cell_problems.append(f"{cell_id}: not refused")
        if cell.get("actionsDispatched") not in (None, 0):
            cell_problems.append(f"{cell_id}: dispatched "
                                 f"{cell.get('actionsDispatched')} actions")
        if before is None or after is None:
            cell_problems.append(f"{cell_id}: saved documents missing")
        elif before != after:
            cell_problems.append(f"{cell_id}: <office:body> changed")
        per_cell[cell_id] = {"pass": not cell_problems, "problems": cell_problems}
        problems += cell_problems

    return {"problems": problems, "cells": per_cell,
            "pass": not problems}


def projection(result: dict, matrix: dict) -> dict:
    """The fields the matrix says must be identical across browsers."""
    include = set(matrix["comparisonProjection"]["include"])
    cells = result.get("cells") or {}
    out: dict[str, dict] = {}
    for action_entry in (cells.get("d0-reachability-single-client") or {}).get(
            "attempts") or []:
        payload = (action_entry.get("envelope") or {}).get("payload") or {}
        row = {
            "action": action_entry.get("action"),
            "dispatched": action_entry.get("dispatched"),
            "completion": (action_entry.get("result") or {}).get("completion"),
            "changed": (action_entry.get("result") or {}).get("changed"),
            "revisionDelta": (
                (action_entry.get("result") or {}).get("revision", 0)
                - (action_entry.get("result") or {}).get("beforeRevision", 0)
                if action_entry.get("result") else None),
            "enabled": payload.get("enabled"),
            "extendSelection": payload.get("extendSelection"),
        }
        out[str(action_entry.get("action"))] = {
            key: value for key, value in row.items()
            if key in include or key in ("enabled", "extendSelection")}
    return out


SELF_TEST_MUTATIONS = [
    ("a wrong wasm hash", lambda r: r["cells"]["d0-inventory"].update(
        {"wasmSha256": "0" * 64})),
    ("a missing action", lambda r: r["cells"]["d0-reachability-single-client"][
        "attempts"].pop()),
    ("a wrong enabled flag", lambda r: r["cells"]["d0-reachability-single-client"][
        "attempts"][6]["envelope"]["payload"].update({"enabled": False})),
    ("a v1 completion on a paragraph action",
     lambda r: next(a for a in r["cells"]["d0-reachability-single-client"]["attempts"]
                    if a["action"] in PARAGRAPH)["result"].update(
                        {"completion": "uno-command-result", "changed": True})),
    ("route C's shape on a delete",
     lambda r: next(a for a in r["cells"]["d0-reachability-single-client"]["attempts"]
                    if a["action"] in DELETE)["result"].update(
                        {"completion": "verified-format-readback", "changed": None})),
    ("an accepted undeclared action",
     lambda r: r["cells"]["d0-reachability-control-undeclared"].update(
         {"refused": False})),
    ("an accepted editorActionV1",
     lambda r: r["cells"]["d0-no-diagnostic-surface"]["editorActionV1"].update(
         {"refused": False})),
    ("a session that did not open",
     lambda r: r["cells"]["d0-session-opens"].update({"state": "recoverable-error"})),
    ("an accepted forbidden field",
     lambda r: r["cells"]["d0-forbidden-keycode"].update({"refused": False})),
    ("a dispatch behind a refusal",
     lambda r: r["cells"]["d0-unknown-action"].update({"actionsDispatched": 1})),
    ("a broken attribution",
     lambda r: r["attribution"].update({"consistent": False})),
]


def self_test(evidence: Path) -> int:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    result = json.loads((evidence / "result.json").read_text(encoding="utf-8"))
    base = judge(result, evidence, matrix)
    failures = []
    if not base["pass"]:
        failures.append(f"the evidence itself does not pass: {base['problems']}")
    for label, mutate in SELF_TEST_MUTATIONS:
        mutated = copy.deepcopy(result)
        try:
            mutate(mutated)
        except Exception as error:                       # noqa: BLE001
            failures.append(f"{label}: mutation could not be applied ({error})")
            continue
        if judge(mutated, evidence, matrix)["pass"]:
            failures.append(f"{label}: the analyzer still said pass")
    print(json.dumps({"selfTest": len(SELF_TEST_MUTATIONS),
                      "failures": failures,
                      "pass": not failures}, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path, nargs="?",
                        help="a D0 evidence directory (…/<profile>-<hash>/<browser>)")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--matrix", type=Path, default=MATRIX)
    args = parser.parse_args()

    if args.self_test:
        if args.evidence is None:
            parser.error("--self-test needs an evidence directory to mutate")
        return self_test(args.evidence)

    if args.evidence is None:
        parser.error("an evidence directory is required")
    # Same assertion as the runner's, applied again here: a verdict is written
    # from this file, and the runner's refusal does not travel with the
    # evidence.  Judging is where the matrix's authority is actually used.
    entry = require_entry(args.matrix)
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    result = json.loads((args.evidence / "result.json").read_text(encoding="utf-8"))
    verdict = judge(result, args.evidence, matrix)
    verdict["matrixEntryAssertion"] = entry
    verdict["browser"] = result.get("browserName")
    verdict["artifact"] = result.get("artifact")
    verdict["projection"] = projection(result, matrix)
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
