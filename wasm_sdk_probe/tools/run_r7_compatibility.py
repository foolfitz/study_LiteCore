#!/usr/bin/env python3
"""Run the R7-C repeat/full browser groups and preserve every result."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

from r7_support import (
    ChromeSession,
    FirefoxSession,
    desktop_pdf_roundtrip,
    evaluate,
    load_json,
    validate_saved_odt,
    wait_page,
    write_json,
)
from run_browser_probe import free_port


FORMAL_PLANS = [("repeat", run) for run in range(1, 4)] + [("full", 1)]


def collect_browser_summary(browser: str, browser_root: Path) -> dict[str, object]:
    runs = []
    for group, run_number in FORMAL_PLANS:
        path = browser_root / group / f"run-{run_number}" / "result.json"
        result = load_json(path) if path.is_file() else {"pass": False}
        runs.append({
            "group": group,
            "run": run_number,
            "result": str(path),
            "pass": result.get("pass") is True,
        })
    return {
        "schemaVersion": 1,
        "release": "R7-C",
        "browser": browser,
        "runs": runs,
        "pass": all(item["pass"] for item in runs),
    }


def selected_group_documents(
    documents: list[dict[str, object]], group: str,
) -> list[dict[str, object]]:
    if group == "full":
        return [
            item for item in documents
            if item.get("tier") in {"L2", "L3", "L4"}
            or str(item.get("id") or "").startswith("l1-hyperlink-font")
        ]
    return [
        item for item in documents
        if item.get("tier") == "L0"
        or any(
            str(item.get("id") or "").startswith(prefix)
            for prefix in ("l1-plain", "l1-layout-table-image", "l1-review")
        )
    ]


def full_batches(documents: list[dict[str, object]], batch_size: int) -> list[list[dict[str, object]]]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    selected = selected_group_documents(documents, "full")
    return [selected[offset:offset + batch_size]
            for offset in range(0, len(selected), batch_size)]


def firefox_batches(
    documents: list[dict[str, object]], group: str, worker_budget: int = 3,
) -> list[list[dict[str, object]]]:
    """Split a group into pages, capped at `worker_budget` Workers per page.

    The default of 3 is finding 014's "observed large-WASM Worker ceiling".
    That ceiling turned out to be our own harness (finding 023's unread
    serve.py pipe): a single Firefox page has since sustained 50 engine
    generations cleanly.  --firefox-worker-budget raises the cap so the
    workaround can be tested for whether it is still needed; the default is
    unchanged, so existing evidence keeps its shape.
    """
    if worker_budget < 1:
        raise ValueError("worker_budget must be positive")
    batches: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    current_workers = 0
    for item in selected_group_documents(documents, group):
        # l0-t2 needs one replacement Worker for bounded close recovery.
        workers = 2 if item.get("id") == "l0-t2" else 1
        if current and current_workers + workers > worker_budget:
            batches.append(current)
            current = []
            current_workers = 0
        current.append(item)
        current_workers += workers
    if current:
        batches.append(current)
    return batches


def run_firefox_group_batches(
    session_class: type[FirefoxSession],
    base_url: str,
    timeout: float,
    browser_root: Path,
    documents: list[dict[str, object]],
    manifest_items: dict[str, dict[str, object]],
    group: str,
    run_number: int,
    cooldown_seconds: float,
    worker_budget: int = 3,
) -> dict[str, object]:
    run_root = browser_root / group / f"run-{run_number}"
    batches = firefox_batches(documents, group, worker_budget)
    cases: list[dict[str, object]] = []
    batch_evidence = []
    versions = []
    worker_counts = {"created": 0, "terminated": 0}
    outputs: dict[str, object] = {}
    offset = 0
    session = session_class("cold")
    for batch_number, batch in enumerate(batches, 1):
        batch_root = run_root / "batches" / f"batch-{batch_number}"
        batch_root.mkdir(parents=True, exist_ok=True)
        metrics = None
        keep_session = False
        try:
            session.navigate(
                f"{base_url}?group={group}&run={run_number}"
                f"&batchStart={offset}&batchSize={len(batch)}"
            )
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                metrics = evaluate(session, "globalThis.__r7_compatibility || null")
                if metrics and metrics.get("complete"):
                    break
                time.sleep(0.5)
            if not metrics or not metrics.get("complete"):
                raise RuntimeError(
                    f"R7-C {group} run {run_number} batch {batch_number} timed out"
                )
            (batch_root / "page.png").write_bytes(session.screenshot())
            (batch_root / "browser.log.txt").write_text(
                str(evaluate(session, "document.querySelector('#log').textContent")),
                encoding="utf-8",
            )
            output_ids = list(evaluate(
                session, "globalThis.__r7_compatibility_output_ids()"
            ))
            batch_outputs = {}
            for identifier in output_ids:
                raw = base64.b64decode(str(evaluate(
                    session,
                    f"globalThis.__r7_compatibility_get_output_base64({json.dumps(identifier)})",
                )))
                output_path = batch_root / f"{identifier}-output.odt"
                output_path.write_bytes(raw)
                case = next(
                    item for item in metrics["cases"] if item["id"] == identifier
                )
                replacement = case["mutation"]["replacement"]
                saved = validate_saved_odt(output_path, [{"text": replacement}])
                desktop = desktop_pdf_roundtrip(
                    output_path, batch_root / f"{identifier}-output.pdf"
                )
                batch_outputs[identifier] = {
                    "path": str(output_path),
                    "savedOdt": saved,
                    "desktopRoundtrip": desktop,
                    "pass": saved["pass"] and desktop["pass"],
                }
            expected_ids = [str(item["id"]) for item in batch]
            observed_ids = [str(item.get("id")) for item in metrics.get("cases", [])]
            batch_pass = (
                metrics.get("pass") is True
                and observed_ids == expected_ids
                and all(item["pass"] for item in batch_outputs.values())
            )
            result = {
                "schemaVersion": 1,
                "release": "R7-C",
                "browser": "firefox",
                "browserVersion": session.version,
                "group": group,
                "run": run_number,
                "batch": batch_number,
                "offset": offset,
                "expectedIds": expected_ids,
                "metrics": metrics,
                "outputs": batch_outputs,
                "pass": batch_pass,
            }
            write_json(batch_root / "result.json", result)
            batch_evidence.append({
                "batch": batch_number,
                "result": str(batch_root / "result.json"),
                "ids": expected_ids,
                "pass": batch_pass,
            })
            cases.extend(metrics.get("cases", []))
            outputs.update(batch_outputs)
            versions.append(session.version)
            for name in worker_counts:
                worker_counts[name] += int(metrics.get("workers", {}).get(name, 0))
            keep_session = batch_pass and batch_number < len(batches)
            if not batch_pass:
                break
        finally:
            if not keep_session:
                session.close()
        offset += len(batch)
        if batch_number < len(batches):
            session.navigate("about:blank")
            if cooldown_seconds > 0:
                time.sleep(cooldown_seconds)

    expected_ids = [str(item["id"]) for batch in batches for item in batch]
    observed_ids = [str(item.get("id")) for item in cases]
    metrics = {
        "schemaVersion": 1,
        "release": "R7-C",
        "group": group,
        "batched": True,
        "batchSizes": [len(batch) for batch in batches],
        # The budget actually used, not the default.  This was the literal 3
        # until 2026-08-08, so any run that passed --firefox-worker-budget
        # recorded a value contradicting what it ran (finding 014).
        "workerBudget": worker_budget,
        "cooldownSeconds": cooldown_seconds,
        "cases": cases,
        "workers": worker_counts,
        "complete": len(batch_evidence) == len(batches),
        "pass": (
            len(batch_evidence) == len(batches)
            and all(item["pass"] for item in batch_evidence)
            and observed_ids == expected_ids
        ),
        "decisionCandidate": "PARTIAL_GO_ODT_FIRST",
    }
    case_checks = [
        {
            "id": str(case["id"]),
            "manifestHash": manifest_items[str(case["id"])]["sha256"],
            "inputHash": case.get("inputSha256"),
            "hashPass": manifest_items[str(case["id"])]["sha256"]
            == case.get("inputSha256"),
            "casePass": case.get("pass") is True,
        }
        for case in cases
    ]
    result = {
        "schemaVersion": 1,
        "release": "R7-C",
        "browser": "firefox",
        "browserVersion": versions[0] if versions else "unknown",
        "browserVersions": versions,
        "group": group,
        "run": run_number,
        "metrics": metrics,
        "caseChecks": case_checks,
        "outputs": outputs,
        "batches": batch_evidence,
        "pass": metrics["pass"]
        and all(item["hashPass"] and item["casePass"] for item in case_checks),
    }
    write_json(run_root / "result.json", result)
    return {
        "group": group,
        "run": run_number,
        "result": str(run_root / "result.json"),
        "pass": result["pass"],
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--group", choices=("all", "repeat", "full"), default="all")
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--firefox-batch-cooldown", type=float, default=8.0)
    parser.add_argument(
        "--firefox-worker-budget", type=int, default=3,
        help="max large-WASM Workers per page for firefox (default 3 = finding "
        "014's supposed ceiling, whose cause turned out to be our own harness). "
        "Raise it to test whether the per-page split is still needed",
    )
    parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r7" / "browser" / "compatibility",
    )
    args = parser.parse_args()
    manifest = load_json(project / "test-docs" / "r7-compat" / "manifest.json")
    manifest_items = {item["id"]: item for item in manifest["documents"]}
    browser_root = args.evidence_root / args.browser
    if args.summarize_only:
        summary = collect_browser_summary(args.browser, browser_root)
        write_json(browser_root / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if not summary["pass"]:
            raise SystemExit(1)
        return
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(port)],
        # DEVNULL, not PIPE: nothing ever read these pipes, and the request
        # log fills 64 KiB after a workload-dependent number of navigations --
        # the handler thread then blocks before sending the response body and
        # every later fetch hangs (finding 023).
        cwd=project, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        text=True,
    )
    summaries = []
    try:
        base_url = f"http://127.0.0.1:{port}/r7-compatibility.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        plans = []
        if args.group in {"all", "repeat"}:
            plans.extend(("repeat", run) for run in range(1, 4))
        if args.group in {"all", "full"}:
            plans.append(("full", 1))
        for group, run_number in plans:
            if args.browser == "firefox":
                item = run_firefox_group_batches(
                    session_class,
                    base_url,
                    args.timeout,
                    browser_root,
                    manifest["documents"],
                    manifest_items,
                    group,
                    run_number,
                    args.firefox_batch_cooldown,
                    args.firefox_worker_budget,
                )
                summaries.append(item)
                if not item["pass"]:
                    break
                continue
            session = session_class("cold")
            try:
                session.navigate(f"{base_url}?group={group}&run={run_number}")
                deadline = time.monotonic() + args.timeout
                metrics = None
                while time.monotonic() < deadline:
                    metrics = evaluate(session, "globalThis.__r7_compatibility || null")
                    if metrics and metrics.get("complete"):
                        break
                    time.sleep(0.5)
                if not metrics or not metrics.get("complete"):
                    raise RuntimeError(f"R7-C {group} run {run_number} timed out")
                run_root = browser_root / group / f"run-{run_number}"
                run_root.mkdir(parents=True, exist_ok=True)
                (run_root / "page.png").write_bytes(session.screenshot())
                log_text = str(evaluate(session, "document.querySelector('#log').textContent"))
                (run_root / "browser.log.txt").write_text(log_text, encoding="utf-8")
                output_ids = list(evaluate(
                    session, "globalThis.__r7_compatibility_output_ids()"
                ))
                outputs = {}
                for identifier in output_ids:
                    raw = base64.b64decode(str(evaluate(
                        session,
                        f"globalThis.__r7_compatibility_get_output_base64({json.dumps(identifier)})",
                    )))
                    output_path = run_root / f"{identifier}-output.odt"
                    output_path.write_bytes(raw)
                    case = next(item for item in metrics["cases"] if item["id"] == identifier)
                    replacement = case["mutation"]["replacement"]
                    saved = validate_saved_odt(output_path, [{"text": replacement}])
                    desktop = desktop_pdf_roundtrip(
                        output_path, run_root / f"{identifier}-output.pdf"
                    )
                    outputs[identifier] = {
                        "path": str(output_path), "savedOdt": saved,
                        "desktopRoundtrip": desktop,
                        "pass": saved["pass"] and desktop["pass"],
                    }
                case_checks = []
                for case in metrics["cases"]:
                    manifest_item = manifest_items[case["id"]]
                    case_checks.append({
                        "id": case["id"],
                        "manifestHash": manifest_item["sha256"],
                        "inputHash": case["inputSha256"],
                        "hashPass": manifest_item["sha256"] == case["inputSha256"],
                        "casePass": case["pass"],
                    })
                result = {
                    "schemaVersion": 1,
                    "release": "R7-C",
                    "browser": args.browser,
                    "browserVersion": session.version,
                    "group": group,
                    "run": run_number,
                    "metrics": metrics,
                    "caseChecks": case_checks,
                    "outputs": outputs,
                    "pass": metrics.get("pass") is True
                    and all(item["hashPass"] and item["casePass"] for item in case_checks)
                    and all(item["pass"] for item in outputs.values()),
                }
                write_json(run_root / "result.json", result)
                summaries.append({
                    "group": group, "run": run_number,
                    "result": str(run_root / "result.json"), "pass": result["pass"],
                })
                if not result["pass"]:
                    break
            finally:
                session.close()
            if summaries and not summaries[-1]["pass"]:
                break
        summary = collect_browser_summary(args.browser, browser_root)
        write_json(browser_root / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if not summary["pass"]:
            raise SystemExit(1)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
