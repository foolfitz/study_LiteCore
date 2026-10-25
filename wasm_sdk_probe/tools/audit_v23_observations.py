#!/usr/bin/env python3
"""Audit actual SDK observation records without making a cohort verdict.

The reader verifies pinned R2 artifacts, actual successful opens, same-handle
editor-state/a11y evidence inside each open lifetime, and diagnostic proof-event
attribution. S-init cell indexes are expanded only after checking each cell's
recorded SHA-256. V22 cells are skipped only in that S-init baseline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from judge_v23_remaining import identity as r2_identity

PROFILE = "e2-editor-v23-diag-r2"
V22_PROFILE = "e2-editor-v22"
A11Y_UNAVAILABLE = "core-built-without-accessibility"
PAGE_SCHEMA = 1
ARTIFACT_KEYS = ("probe.js", "probe.wasm", "sdk-worker.js", "sdk-manifest.json")
STATE_OPERATIONS = {"editorGetStateV2", "editorGetState"}


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _field(record: dict, name: str):
    """Read a protocol property whether it is flattened or in message."""
    if name in record:
        return record[name]
    return _mapping(record.get("message")).get(name)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _operation(record: dict):
    return _field(record, "operation")


def _payload(record: dict) -> dict:
    return _mapping(_field(record, "payload"))


def _generation(record: dict):
    return _field(record, "generation")


def _request_id(record: dict):
    return _field(record, "requestId")


def _at(record: dict):
    return _field(record, "at")


def _response_message(record: dict) -> dict:
    return _mapping(record.get("message")) or record


def _response_result(record: dict) -> dict:
    message = _response_message(record)
    return _mapping(message.get("result"))


def _response_ok(record: dict):
    message = _response_message(record)
    if "ok" in message:
        return message.get("ok")
    return record.get("ok")


def _event_message(record: dict) -> dict:
    return _mapping(record.get("message")) or record


def _event_detail(record: dict) -> dict:
    message = _event_message(record)
    return _mapping(message.get("detail"))


def _a11y(message: dict) -> dict:
    return _mapping(message.get("a11y"))


def _doc_handle(value: Any):
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _problem(code: str, message: str, **evidence) -> dict:
    return {"code": code, "message": message, **evidence}


def audit_page(page: dict, expected_identity: dict, source: str,
               run_fatal=None) -> dict:
    """Audit one actual R2 page; return per-page counts and evidence paths."""
    problems = []
    page = _mapping(page)

    if page.get("schema") != PAGE_SCHEMA:
        problems.append(_problem("unknown-schema", "R2 page schema is absent or unsupported",
                                 actual=page.get("schema")))
    if page.get("profile") != PROFILE:
        problems.append(_problem("wrong-profile", "page is not the explicit R2 candidate",
                                 actual=page.get("profile")))
    if page.get("complete") is not True or run_fatal is not None or page.get("fatal") is not None:
        problems.append(_problem("unclean-page", "page is incomplete or carries a fatal payload",
                                 complete=page.get("complete"), runFatal=run_fatal,
                                 pageFatal=page.get("fatal")))

    artifacts = _mapping(page.get("artifacts"))
    artifact_problems = []
    for name in ARTIFACT_KEYS:
        if artifacts.get(name) != expected_identity.get(name):
            artifact_problems.append({"artifact": name,
                                      "expected": expected_identity.get(name),
                                      "actual": artifacts.get(name)})
    if artifact_problems:
        problems.append(_problem("artifact-identity", "page artifact hashes differ from actual R2 identity",
                                 mismatches=artifact_problems))

    requests = _list(page.get("requests"))
    responses = _list(page.get("responses"))
    events = _list(page.get("events"))
    opens = [(i, r) for i, r in enumerate(requests) if _operation(_mapping(r)) == "open"]
    if not opens:
        problems.append(_problem("no-open", "R2 page has no actual open request"))

    open_evidence = []
    response_index = {}
    for i, item in enumerate(responses):
        item = _mapping(item)
        key = (_generation(item), _request_id(item))
        response_index.setdefault(key, []).append((i, item))

    for open_index, open_record in opens:
        open_record = _mapping(open_record)
        generation = _generation(open_record)
        request_id = _request_id(open_record)
        request_at = _at(open_record)
        ref = {"requestIndex": open_index, "generation": generation,
               "requestId": request_id, "requestAt": request_at}
        problems_before = len(problems)

        if generation is None or request_id is None or not _number(request_at):
            problems.append(_problem("open-envelope", "open request lacks generation, request id, or timestamp",
                                     **ref))
            open_evidence.append({**ref, "status": "rejected"})
            continue

        matches = response_index.get((generation, request_id), [])
        if len(matches) != 1:
            problems.append(_problem("open-response-count", "open lacks one unique terminal response",
                                     **ref, responseIndexes=[x[0] for x in matches]))
            open_evidence.append({**ref, "status": "rejected",
                                  "responseIndexes": [x[0] for x in matches]})
            continue

        open_response_index, open_response = matches[0]
        open_message = _response_message(open_response)
        open_result = _response_result(open_response)
        response_at = _at(open_response)
        handle = _doc_handle(open_result.get("documentHandle"))
        if _response_ok(open_response) is not True or handle is None:
            problems.append(_problem("open-response", "open response is not successful or has no document handle",
                                     **ref, responseIndex=open_response_index,
                                     responseAt=response_at, responseOk=_response_ok(open_response),
                                     documentHandle=open_result.get("documentHandle")))
            open_evidence.append({**ref, "status": "rejected",
                                  "responseIndex": open_response_index,
                                  "responseAt": response_at})
            continue
        if not _number(response_at):
            problems.append(_problem("open-response-time", "successful open response has no timestamp",
                                     **ref, responseIndex=open_response_index))
            open_evidence.append({**ref, "status": "rejected",
                                  "responseIndex": open_response_index,
                                  "documentHandle": handle})
            continue

        # The state witness belongs to this open from its request until the next
        # same-generation open or close request. The actual editor-state event
        # may precede the successful open response, so the lower bound is the
        # open request timestamp rather than the response timestamp.
        boundaries = []
        for other_index, other in enumerate(requests):
            other = _mapping(other)
            if _generation(other) != generation or _operation(other) not in {"open", "close"}:
                continue
            other_at = _at(other)
            other_id = _request_id(other)
            if other_index == open_index:
                continue
            if _number(other_at) and other_at > request_at:
                boundaries.append((other_at, other_index, other_id, _operation(other)))
        boundary = min(boundaries, default=None)
        end_at = boundary[0] if boundary else math.inf
        window_valid = response_at >= request_at and end_at > request_at
        if not window_valid:
            problems.append(_problem("open-window", "open lifetime has an invalid request-time window",
                                     **ref, responseAt=response_at,
                                     nextBoundary=boundary))

        state_evidence = []
        wrong_generation = []
        wrong_handle = []
        wrong_status = []
        state_events = []
        for event_index, event_value in enumerate(events):
            event = _mapping(event_value)
            message = _event_message(event)
            if message.get("event") != "editor-state":
                continue
            event_at = _at(event)
            if not _number(event_at) or not (request_at <= event_at < end_at):
                continue
            event_gen = _generation(event)
            event_handle = _doc_handle(message.get("documentHandle"))
            if event_gen != generation:
                wrong_generation.append({"eventIndex": event_index, "generation": event_gen,
                                        "documentHandle": message.get("documentHandle"), "at": event_at})
                continue
            if event_handle != handle:
                wrong_handle.append({"eventIndex": event_index, "generation": event_gen,
                                    "documentHandle": message.get("documentHandle"), "at": event_at})
                continue
            a11y = _a11y(message)
            state_events.append({"eventIndex": event_index, "at": event_at,
                                 "documentHandle": event_handle,
                                 "a11yUnavailable": a11y.get("unavailable")})
            if a11y.get("unavailable") == A11Y_UNAVAILABLE:
                state_evidence.append({"kind": "editor-state-event", "eventIndex": event_index,
                                       "generation": event_gen, "documentHandle": event_handle,
                                       "at": event_at})
            else:
                wrong_status.append({"kind": "editor-state-event", "eventIndex": event_index,
                                     "actual": a11y.get("unavailable"), "at": event_at})

        for state_req_index, state_req_value in enumerate(requests):
            state_req = _mapping(state_req_value)
            if _operation(state_req) not in STATE_OPERATIONS or _generation(state_req) != generation:
                continue
            state_req_at = _at(state_req)
            if not _number(state_req_at) or not (request_at <= state_req_at < end_at):
                continue
            state_req_id = _request_id(state_req)
            if state_req_id is None:
                continue
            state_handle = _doc_handle(_payload(state_req).get("documentHandle"))
            state_matches = response_index.get((generation, state_req_id), [])
            if state_handle != handle:
                wrong_handle.append({"requestIndex": state_req_index, "generation": generation,
                                    "documentHandle": _payload(state_req).get("documentHandle"),
                                    "at": state_req_at})
                continue
            if len(state_matches) != 1:
                continue
            state_response_index, state_response = state_matches[0]
            result = _response_result(state_response)
            response_state_handle = _doc_handle(result.get("documentHandle"))
            state_response_at = _at(state_response)
            if _response_ok(state_response) is not True or response_state_handle != handle:
                wrong_handle.append({"responseIndex": state_response_index,
                                    "generation": _generation(state_response),
                                    "documentHandle": result.get("documentHandle"),
                                    "at": state_response_at})
                continue
            if (not _number(state_response_at) or
                    not (state_req_at <= state_response_at < end_at)):
                continue
            a11y = _a11y(result)
            if a11y.get("unavailable") == A11Y_UNAVAILABLE:
                state_evidence.append({"kind": "editor-state-response",
                                       "requestIndex": state_req_index,
                                       "responseIndex": state_response_index,
                                       "generation": generation,
                                       "documentHandle": handle,
                                       "at": state_response_at})
            else:
                wrong_status.append({"kind": "editor-state-response",
                                     "requestIndex": state_req_index,
                                     "responseIndex": state_response_index,
                                     "actual": a11y.get("unavailable"),
                                     "at": state_response_at})

        # A later bad same-handle observation remains a contradiction even if
        # an earlier valid witness exists. Wrong handles and generations are
        # only diagnostic candidates when no valid witness was found.
        if wrong_status:
            problems.append(_problem("a11y-status", "same-handle state has an unexpected accessibility status",
                                     **ref, documentHandle=handle, evidence=wrong_status))

        if not state_evidence:
            if wrong_generation:
                problems.append(_problem("state-wrong-generation",
                                         "state observations in the open window belong to another generation",
                                         **ref, documentHandle=handle, evidence=wrong_generation))
            if wrong_handle:
                problems.append(_problem("state-wrong-handle",
                                         "state observation does not belong to the opened document handle",
                                         **ref, documentHandle=handle, evidence=wrong_handle))
            if not (wrong_generation or wrong_handle or wrong_status):
                problems.append(_problem("state-witness-missing",
                                         "no same-generation, same-handle state event/response in the open window",
                                         **ref, documentHandle=handle,
                                         windowStart=request_at, windowEnd=end_at))

        open_evidence.append({**ref, "status": "checked",
                              "responseIndex": open_response_index,
                              "responseAt": response_at,
                              "documentHandle": handle,
                              "windowEnd": end_at,
                              "nextBoundary": ({"at": boundary[0], "requestIndex": boundary[1],
                                                "requestId": boundary[2], "operation": boundary[3]}
                                               if boundary else None),
                              "stateWitnessCount": len(state_evidence),
                              "stateWitnesses": state_evidence,
                              "sameHandleStateCount": len(state_events),
                              "wrongGenerationCount": len(wrong_generation),
                              "wrongHandleCount": len(wrong_handle),
                              "wrongStatusCount": len(wrong_status)})

    proof_requests = []
    for request_index, request_value in enumerate(requests):
        request = _mapping(request_value)
        if _operation(request) == "v23Diagnostic" and _payload(request).get("kind") == 2:
            proof_requests.append((request_index, request))
    proof_events = []
    for event_index, event_value in enumerate(events):
        event = _mapping(event_value)
        message = _event_message(event)
        detail = _event_detail(event)
        if message.get("event") == "diagnostic" and detail.get("type") == "v23-proof-absent":
            proof_events.append((event_index, event, detail))

    arm = page.get("arm")
    if arm == "proof":
        if len(proof_requests) != 1:
            problems.append(_problem("proof-request-count", "proof arm requires one actual kind-2 diagnostic request",
                                     requestIndexes=[i for i, _ in proof_requests]))
        if len(proof_events) != 1:
            problems.append(_problem("proof-event-count", "proof arm requires exactly one proof-absent event",
                                     eventIndexes=[i for i, _, _ in proof_events]))
        if len(proof_requests) == 1 and len(proof_events) == 1:
            req_index, req = proof_requests[0]
            event_index, event, detail = proof_events[0]
            if (_generation(event) != _generation(req) or
                    detail.get("requestId") != _request_id(req) or
                    detail.get("count") != 1 or
                    detail.get("callback") != "UNO_COMMAND_RESULT"):
                problems.append(_problem("proof-attribution", "proof event is not attributed to its actual kind-2 request",
                                         requestIndex=req_index, eventIndex=event_index,
                                         requestGeneration=_generation(req), requestId=_request_id(req),
                                         eventGeneration=_generation(event), detail=detail))
    elif proof_events:
        problems.append(_problem("ordinary-proof-event", "ordinary R2 page carries proof-absent events",
                                 arm=arm, eventIndexes=[i for i, _, _ in proof_events]))
    if arm != "proof" and proof_requests:
        problems.append(_problem("ordinary-proof-request", "kind-2 proof control appears outside proof arm",
                                 arm=arm, requestIndexes=[i for i, _ in proof_requests]))

    return {"source": source, "profile": page.get("profile"), "arm": arm,
            "schema": page.get("schema"), "requestCount": len(requests),
            "responseCount": len(responses), "eventCount": len(events),
            "openRequestCount": len(opens), "successfulOpenCount": sum(x["status"] == "checked" for x in open_evidence),
                              "stateWitnessCount": sum(x.get("stateWitnessCount", 0) for x in open_evidence),
            "proofRequestCount": len(proof_requests), "proofEventCount": len(proof_events),
            "opens": open_evidence, "problems": problems}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_sinit_index(report: dict) -> bool:
    rows = _list(report.get("runs"))
    return bool(rows) and all(isinstance(x, dict) and isinstance(x.get("path"), str)
                              and isinstance(x.get("sha256"), str) and "page" not in x
                              for x in rows)


def audit_reports(report_paths, expected_identity: dict) -> dict:
    problems = []
    report_results = []
    counts = {"reports": 0, "r2Instances": 0, "r2Pages": 0, "openRequests": 0,
              "successfulOpens": 0, "stateWitnesses": 0, "proofEvents": 0,
              "skippedV22SinitCells": 0, "problems": 0}

    for path_value in report_paths:
        path = Path(path_value)
        counts["reports"] += 1
        report_result = {"path": str(path), "kind": "direct-report", "instances": [], "problems": []}
        try:
            report = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            report_result["problems"].append(_problem("report-unreadable", str(exc)))
            report_results.append(report_result)
            continue
        if not isinstance(report, dict):
            report_result["problems"].append(_problem("report-schema", "report root is not an object"))
            report_results.append(report_result)
            continue

        sinit = _is_sinit_index(report)
        if sinit:
            report_result["kind"] = "s-init-sha-bound-cell-index"
            for i, cell_ref in enumerate(report["runs"]):
                cell_path = (path.parent / cell_ref["path"]).resolve()
                cell_source = f"{path}#/runs/{i} -> {cell_ref['path']}"
                try:
                    cell_path.relative_to(path.parent.resolve())
                except ValueError:
                    report_result["problems"].append(_problem("cell-path-escape",
                                                              "S-init cell path escapes report directory",
                                                              source=cell_source))
                    continue
                try:
                    raw = cell_path.read_bytes()
                except OSError as exc:
                    report_result["problems"].append(_problem("cell-missing", str(exc), source=cell_source))
                    continue
                actual_sha = _sha256(raw)
                if actual_sha != cell_ref["sha256"]:
                    report_result["problems"].append(_problem("cell-sha256",
                                                              "S-init cell bytes differ from indexed SHA-256",
                                                              source=cell_source,
                                                              expected=cell_ref["sha256"], actual=actual_sha))
                    continue
                try:
                    cell = json.loads(raw)
                except json.JSONDecodeError as exc:
                    report_result["problems"].append(_problem("cell-unreadable", str(exc), source=cell_source))
                    continue
                page = _mapping(cell.get("page"))
                cell_profile = page.get("profile", cell.get("profile"))
                if cell_profile == V22_PROFILE:
                    counts["skippedV22SinitCells"] += 1
                    report_result["instances"].append({"source": cell_source,
                                                        "profile": V22_PROFILE,
                                                        "status": "skipped-v22-sinit-baseline",
                                                        "sha256": actual_sha})
                    continue
                counts["r2Instances"] += 1
                if cell_profile != PROFILE or not page:
                    report_result["instances"].append({"source": cell_source,
                                                        "profile": cell_profile,
                                                        "status": "rejected",
                                                        "sha256": actual_sha,
                                                        "problems": [_problem("r2-cell-page-missing",
                                                                              "non-baseline S-init cell lacks an R2 page",
                                                                              profile=cell_profile)]})
                    report_result["problems"].append(_problem("r2-cell-page-missing",
                                                              "non-baseline S-init cell lacks an R2 page",
                                                              source=cell_source, profile=cell_profile))
                    continue
                page_result = audit_page(page, expected_identity, cell_source,
                                         run_fatal=cell.get("fatal"))
                # Validate the page's exact four artifacts independently of any
                # extra resources that S-init records alongside them.
                instance_problems = list(page_result["problems"])
                if cell.get("profile") not in (None, PROFILE):
                    instance_problems.append(_problem("cell-profile", "cell wrapper profile differs from its page",
                                                       wrapper=cell.get("profile"), page=PROFILE))
                page_result["problems"] = instance_problems
                counts["r2Pages"] += 1
                counts["openRequests"] += page_result["openRequestCount"]
                counts["successfulOpens"] += page_result["successfulOpenCount"]
                counts["stateWitnesses"] += page_result["stateWitnessCount"]
                counts["proofEvents"] += page_result["proofEventCount"]
                report_result["instances"].append(page_result)
        else:
            if report.get("profile") not in (None, PROFILE):
                report_result["problems"].append(_problem("report-profile",
                                                          "non-S-init report is not the explicit R2 candidate",
                                                          actual=report.get("profile")))
            if report.get("profile") == PROFILE and "identity" in report and report.get("identity") != expected_identity:
                report_result["problems"].append(_problem("report-identity",
                                                          "report identity differs from the actual R2 profile"))
            raw_runs = _list(report.get("runs"))
            if not raw_runs and isinstance(report.get("page"), dict):
                raw_runs = [{"page": report["page"], "fatal": report.get("fatal")}]
            for i, run_value in enumerate(raw_runs):
                run = _mapping(run_value)
                page = _mapping(run.get("page"))
                source = f"{path}#/runs/{i}/page"
                if not page and run.get("profile") == V22_PROFILE:
                    # V22 is only exempted in the S-init baseline, never here.
                    report_result["instances"].append({"source": source, "profile": V22_PROFILE,
                                                        "status": "rejected",
                                                        "problems": [_problem("v22-outside-sinit",
                                                                              "V22 page is only skippable in S-init baseline")]})
                    report_result["problems"].append(_problem("v22-outside-sinit",
                                                              "V22 page is only skippable in S-init baseline",
                                                              source=source))
                    continue
                if not page and run.get("schema") is not None:
                    page = run
                    source = f"{path}#/runs/{i}"
                if not page:
                    report_result["instances"].append({"source": source, "profile": run.get("profile"),
                                                        "status": "rejected",
                                                        "problems": [_problem("page-missing", "run has no actual page record")]})
                    report_result["problems"].append(_problem("page-missing", "run has no actual page record",
                                                              source=source))
                    continue
                counts["r2Instances"] += 1
                page_result = audit_page(page, expected_identity, source,
                                         run_fatal=run.get("fatal"))
                counts["r2Pages"] += 1
                counts["openRequests"] += page_result["openRequestCount"]
                counts["successfulOpens"] += page_result["successfulOpenCount"]
                counts["stateWitnesses"] += page_result["stateWitnessCount"]
                counts["proofEvents"] += page_result["proofEventCount"]
                report_result["instances"].append(page_result)

        if not report_result["problems"]:
            for instance in report_result["instances"]:
                report_result["problems"].extend(instance.get("problems", []))
        report_results.append(report_result)

    for result in report_results:
        problems.extend(result.get("problems", []))
        for instance in result.get("instances", []):
            problems.extend(instance.get("problems", []))
    if counts["r2Pages"] == 0:
        problems.append(_problem("zero-r2-pages", "input set contains no R2 page instances"))
    counts["problems"] = len(problems)
    return {"verdict": "FAIL" if problems else "PASS",
            "scope": "read-only observation accounting; not a cohort verdict",
            "profile": PROFILE,
            "identity": expected_identity,
            "counts": counts,
            "reports": report_results,
            "problems": problems}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--wasm-sha256", required=True,
                        help="explicit actual R2 candidate WASM SHA-256")
    args = parser.parse_args(argv)
    identity = r2_identity(PROFILE, args.wasm_sha256)
    result = audit_reports(args.reports, identity)
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
