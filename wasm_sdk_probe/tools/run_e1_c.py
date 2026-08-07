#!/usr/bin/env python3
"""Run the frozen E1-C editor integration matrix in Chrome or Firefox."""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from e1_support import inspect_odt, sha256, write_json
from r7_support import evaluate, process_snapshot, wait_page
from run_browser_probe import ChromeSession, FirefoxSession, free_port


@dataclass(frozen=True)
class Case:
    phase: str
    name: str
    scenario: str
    fixture: str
    repetition: int = 1


INTEGRATION = tuple(
    Case("integration", f"integration-{index:02d}", "integration", "plain-grapheme", index)
    for index in range(1, 4)
)
RECOVERY = (
    Case("recovery", "boundary-start", "boundary-start", "plain-grapheme"),
    Case("recovery", "boundary-table", "boundary-table", "table-boundary"),
    Case("recovery", "crash-preedit", "crash-preedit", "plain-grapheme"),
    Case("recovery", "crash-queued", "crash-queued", "plain-grapheme"),
    Case("recovery", "crash-unsaved", "crash-unsaved", "plain-grapheme"),
    Case("recovery", "crash-saved", "crash-saved", "plain-grapheme"),
)
CORPUS = tuple(
    Case("corpus", fixture, "corpus", fixture)
    for fixture in ("l0-t1", "l0-t2", "l0-t3", "l1-review-odt", "l4-stress-100")
)
LIFECYCLE = tuple(
    Case("lifecycle", f"cycle-{index:02d}", "lifecycle", "plain-grapheme", index)
    for index in range(1, 11)
)
LIFECYCLE_WARMUP_CYCLES = 10
PLANS = {
    "integration": INTEGRATION,
    "recovery": RECOVERY,
    "corpus": CORPUS,
    "lifecycle": LIFECYCLE,
}


def attempt_directory(base: Path) -> Path:
    if not (base / "result.json").exists():
        return base
    attempt = 2
    while (base / f"attempt-{attempt:02d}").exists():
        attempt += 1
    return base / f"attempt-{attempt:02d}"


def case_root(evidence: Path, browser: str, case: Case) -> Path:
    category = "browser" if case.phase == "integration" else case.phase
    return evidence / category / browser / case.name


def memory_gate(samples: list[dict], browser: str) -> dict:
    values = [
        sample.get("pssBytes") if sample.get("pssBytes") is not None else sample.get("rssBytes")
        for sample in samples
    ]
    values = [int(value) for value in values if isinstance(value, int)]
    if len(values) < 2:
        return {
            "browser": browser,
            "metric": "unavailable",
            "samples": len(values),
            "pass": False,
        }
    growth = values[-1] - values[0]
    ratio = growth / max(values[0], 1)
    return {
        "browser": browser,
        "metric": "pss-or-rss-process-tree",
        "samples": len(values),
        "firstBytes": values[0],
        "lastBytes": values[-1],
        "growthBytes": growth,
        "growthRatio": ratio,
        "maximumGrowthBytes": 536_870_912,
        "maximumGrowthRatio": 0.35,
        "pass": growth <= 536_870_912 and ratio <= 0.35,
    }


def run_case(
    session: ChromeSession | FirefoxSession,
    base_url: str,
    browser: str,
    evidence: Path,
    case: Case,
    timeout: float,
) -> dict:
    base = case_root(evidence, browser, case)
    output = attempt_directory(base)
    output.mkdir(parents=True, exist_ok=True)
    metrics = None
    before_sample = process_snapshot(session.process.pid, {
        "checkpoint": f"before-{case.name}", "cycle": case.repetition,
    })
    try:
        query = urlencode({
            "scenario": case.scenario,
            "fixture": case.fixture,
            "repetition": case.repetition,
        })
        session.navigate(f"{base_url}?{query}")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__e1_c || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.2)
        if not metrics or not metrics.get("complete"):
            raise RuntimeError(f"E1-C {case.name} timed out after {timeout}s")
        (output / "page.png").write_bytes(session.screenshot())
        log_text = str(evaluate(
            session, "document.querySelector('#log')?.textContent || ''"
        ))
        (output / "page.log.txt").write_text(log_text, encoding="utf-8")
        encoded = str(evaluate(
            session, "globalThis.__e1_c_get_output_base64?.() || ''"
        ))
        saved = None
        if encoded:
            saved_path = output / "output.odt"
            saved_path.write_bytes(base64.b64decode(encoded))
            saved = {
                "path": str(saved_path),
                "bytes": saved_path.stat().st_size,
                "sha256": sha256(saved_path),
            }
        after_sample = process_snapshot(session.process.pid, {
            "checkpoint": f"after-{case.name}", "cycle": case.repetition,
        })
        result = {
            **metrics,
            "browserName": browser,
            "browserVersion": session.version,
            "case": {
                "phase": case.phase,
                "name": case.name,
                "scenario": case.scenario,
                "fixture": case.fixture,
                "repetition": case.repetition,
            },
            "savedOutput": saved,
            "processSamples": [before_sample, after_sample],
            "evidenceDirectory": str(output),
        }
        result["pass"] = result.get("pass") is True and saved is not None
    except Exception as error:  # noqa: BLE001 - raw failure evidence is required
        result = {
            "schemaVersion": 1,
            "release": "E1-C-editor-validation",
            "browserName": browser,
            "browserVersion": getattr(session, "version", "unknown"),
            "case": {
                "phase": case.phase,
                "name": case.name,
                "scenario": case.scenario,
                "fixture": case.fixture,
                "repetition": case.repetition,
            },
            "lastMetrics": metrics,
            "processSamples": [before_sample],
            "error": {"name": type(error).__name__, "message": str(error)},
            "evidenceDirectory": str(output),
            "pass": False,
        }
    write_json(output / "result.json", result)
    return {
        "phase": case.phase,
        "name": case.name,
        "scenario": case.scenario,
        "fixture": case.fixture,
        "repetition": case.repetition,
        "result": str(output / "result.json"),
        "pass": result.get("pass") is True,
        "processSamples": result.get("processSamples", []),
    }


def write_phase_summary(
    evidence: Path,
    browser: str,
    phase: str,
    expected: int,
    results: list[dict],
    warmups: list[dict] | None = None,
) -> dict:
    warmups = warmups or []
    category = "browser" if phase == "integration" else phase
    samples = [
        entry
        for item in results
        for entry in item.get("processSamples", [])
        if str(entry.get("checkpoint", "")).startswith("after-")
    ]
    memory = memory_gate(samples, browser) if phase == "lifecycle" else {
        "status": "recorded-not-lifecycle-gate",
        "samples": len(samples),
        "pass": True,
    }
    summary = {
        "schemaVersion": 1,
        "release": "E1-C-editor-validation",
        "browser": browser,
        "browserVersion": next((item.get("browserVersion") for item in results if item.get("browserVersion")), None),
        "phase": phase,
        "expectedCases": expected,
        "completedCases": len(results),
        "warmup": {
            "expectedCycles": LIFECYCLE_WARMUP_CYCLES if phase == "lifecycle" else 0,
            "completedCycles": len(warmups),
            "results": [
                {key: value for key, value in item.items() if key != "processSamples"}
                for item in warmups
            ],
            "pass": phase != "lifecycle"
            or (len(warmups) == LIFECYCLE_WARMUP_CYCLES
                and all(item.get("pass") is True for item in warmups)),
        },
        "results": [
            {key: value for key, value in item.items() if key != "processSamples"}
            for item in results
        ],
        "memory": memory,
        "pass": len(results) == expected
        and all(item.get("pass") is True for item in results)
        and (phase != "lifecycle"
             or (len(warmups) == LIFECYCLE_WARMUP_CYCLES
                 and all(item.get("pass") is True for item in warmups)))
        and memory.get("pass") is True,
    }
    write_json(evidence / category / browser / "summary.json", summary)
    return summary


def preserve_previous(path: Path) -> None:
    if not path.is_file():
        return
    attempt = 1
    while True:
        candidate = path.with_name(f"{path.stem}-attempt-{attempt:02d}{path.suffix}")
        if not candidate.exists():
            shutil.copy2(path, candidate)
            return
        attempt += 1


def manual_handler(project: Path, evidence: Path):
    class E1CManualHandler(SimpleHTTPRequestHandler):
        def end_headers(self) -> None:
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
            self.send_header("Cache-Control", "no-cache")
            super().end_headers()

        def send_json(self, status: int, value: dict) -> None:
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
            parsed = urlparse(self.path)
            if parsed.path != "/e1-c-manual-submit":
                self.send_json(404, {"error": "unknown endpoint"})
                return
            browser = parse_qs(parsed.query).get("browser", [""])[0]
            if browser not in {"chrome", "firefox"}:
                self.send_json(400, {"error": "browser must be chrome or firefox"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0 or length > 16 * 1024 * 1024:
                self.send_json(413, {"error": "manual evidence body is empty or oversized"})
                return
            try:
                payload = json.loads(self.rfile.read(length))
                encoded = payload.pop("outputBase64")
                output_bytes = base64.b64decode(encoded, validate=True)
                if payload.get("release") != "E1-C-editor-validation":
                    raise ValueError("unexpected release")
                if payload.get("manual") is not True:
                    raise ValueError("manual mode marker is missing")
            except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
                self.send_json(400, {"error": f"invalid manual evidence: {error}"})
                return

            manual_root = evidence / "manual"
            manual_root.mkdir(parents=True, exist_ok=True)
            output_path = manual_root / f"{browser}-output.odt"
            json_path = manual_root / f"{browser}-chewing.json"
            preserve_previous(output_path)
            preserve_previous(json_path)
            output_path.write_bytes(output_bytes)
            inspected = inspect_odt(output_path)
            output_valid = all(inspected.get(key) is True for key in ("exists", "zip", "crc", "xml"))
            payload["savedOutput"] = {
                "path": str(output_path),
                "bytes": len(output_bytes),
                "sha256": sha256(output_path),
            }
            payload["serverValidation"] = {
                "exists": inspected.get("exists"),
                "zip": inspected.get("zip"),
                "crc": inspected.get("crc"),
                "xml": inspected.get("xml"),
                "pass": output_valid,
            }
            payload["pass"] = payload.get("pass") is True and output_valid
            write_json(json_path, payload)
            self.send_json(200, {
                "status": "saved",
                "browser": browser,
                "pass": payload["pass"],
                "evidence": str(json_path),
                "output": str(output_path),
            })

    return partial(E1CManualHandler, directory=str(project / "dist"))


def serve_manual(project: Path, evidence: Path, port: int) -> None:
    server = ThreadingHTTPServer(
        ("127.0.0.1", port), manual_handler(project, evidence),
    )
    url = f"http://127.0.0.1:{port}/e1-editor-validation.html?manual=1"
    print(json.dumps({"manualUrl": url, "evidence": str(evidence / "manual")}, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"))
    parser.add_argument(
        "--phase",
        choices=("all", "integration", "recovery", "corpus", "lifecycle"),
        default="all",
    )
    parser.add_argument("--case", help="run only one frozen case name")
    parser.add_argument("--timeout-per-case", type=float, default=420)
    parser.add_argument("--manual-server", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "editor-validation",
    )
    args = parser.parse_args()
    evidence = args.evidence_root.resolve()
    if args.manual_server:
        serve_manual(project, evidence, args.port)
        return
    if not args.browser:
        parser.error("--browser is required unless --manual-server is used")
    phases = list(PLANS) if args.phase == "all" else [args.phase]

    server_port = free_port()
    # The server's output goes to a real file, never a pipe.  finding 023: with
    # stdout/stderr=PIPE and no reader, the request log filled the 64 KiB pipe
    # after a workload-dependent number of navigations; the handler thread then
    # blocked in log_message() *before sending the response body*, every later
    # fetch hung, and init "timed out" at a deterministic session depth (22/30
    # heavy, 26/34 light).  The log doubles as per-case request evidence.
    evidence.mkdir(parents=True, exist_ok=True)
    serve_log = open(evidence / f"serve-{args.browser}.log", "w", buffering=1)
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(server_port)],
        cwd=project,
        stdout=serve_log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    session = None
    all_summaries = []
    try:
        base_url = f"http://127.0.0.1:{server_port}/e1-editor-validation.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        for phase in phases:
            frozen = list(PLANS[phase])
            selected = [case for case in frozen if not args.case or case.name == args.case]
            if not selected:
                raise SystemExit(f"unknown --case {args.case!r} for phase {phase}")
            warmups = []
            if phase == "lifecycle" and not args.case:
                for index in range(1, LIFECYCLE_WARMUP_CYCLES + 1):
                    warmup = Case(
                        "lifecycle", f"warmup-{index:02d}", "lifecycle",
                        "plain-grapheme", 100 + index,
                    )
                    result = run_case(
                        session, base_url, args.browser, evidence, warmup,
                        args.timeout_per_case,
                    )
                    result["browserVersion"] = session.version
                    warmups.append(result)
                    print(json.dumps({
                        "browser": args.browser,
                        "phase": phase,
                        "warmup": warmup.name,
                        "pass": result["pass"],
                        "result": result["result"],
                    }, ensure_ascii=False), flush=True)
                    if not result["pass"]:
                        break
            results = []
            if phase == "lifecycle" and len(warmups) != LIFECYCLE_WARMUP_CYCLES:
                summary = write_phase_summary(
                    evidence, args.browser, phase, len(frozen), results, warmups,
                )
                all_summaries.append(summary)
                break
            for case in selected:
                result = run_case(
                    session, base_url, args.browser, evidence, case, args.timeout_per_case,
                )
                result["browserVersion"] = session.version
                results.append(result)
                print(json.dumps({
                    "browser": args.browser,
                    "phase": phase,
                    "case": case.name,
                    "pass": result["pass"],
                    "result": result["result"],
                }, ensure_ascii=False), flush=True)
                if not result["pass"]:
                    break
            expected = len(selected) if args.case else len(frozen)
            summary = write_phase_summary(
                evidence, args.browser, phase, expected, results, warmups,
            )
            all_summaries.append(summary)
            if not summary["pass"]:
                break
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
        serve_log.close()

    passed = bool(all_summaries) and all(item["pass"] for item in all_summaries)
    print(json.dumps({
        "browser": args.browser,
        "phases": [item["phase"] for item in all_summaries],
        "pass": passed,
    }, ensure_ascii=False))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
