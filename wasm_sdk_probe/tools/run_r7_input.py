#!/usr/bin/env python3
"""Run the R7-B synthetic browser contract and desktop ODT checks."""

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
    validate_saved_odt,
    wait_page,
    write_json,
)
from run_browser_probe import free_port


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r7" / "browser" / "input",
    )
    args = parser.parse_args()
    if args.runs < 1:
        raise SystemExit("runs must be positive")

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
    browser_root = args.evidence_root / args.browser
    summaries = []
    try:
        base_url = f"http://127.0.0.1:{port}/r7-reference.html?automatic=1"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        for run_number in range(1, args.runs + 1):
            session = session_class("cold")
            try:
                session.navigate(f"{base_url}&run={run_number}")
                deadline = time.monotonic() + args.timeout
                metrics = None
                while time.monotonic() < deadline:
                    metrics = evaluate(session, "globalThis.__r7_reference || null")
                    if metrics and metrics.get("complete"):
                        break
                    time.sleep(0.25)
                if not metrics or not metrics.get("complete"):
                    raise RuntimeError(f"R7-B run {run_number} timed out")
                run_root = browser_root / f"run-{run_number}"
                run_root.mkdir(parents=True, exist_ok=True)
                output = base64.b64decode(str(evaluate(
                    session, "globalThis.__r7_get_output_base64()"
                )))
                odt = run_root / "output.odt"
                odt.write_bytes(output)
                log_text = str(evaluate(
                    session, "document.querySelector('#log').textContent"
                ))
                (run_root / "browser.log.txt").write_text(log_text, encoding="utf-8")
                (run_root / "page.png").write_bytes(session.screenshot())
                saved = validate_saved_odt(odt, metrics["input"]["commits"])
                desktop = desktop_pdf_roundtrip(odt, run_root / "output.pdf")
                result = {
                    "schemaVersion": 1,
                    "release": "R7-B",
                    "browser": args.browser,
                    "browserVersion": session.version,
                    "run": run_number,
                    "metrics": metrics,
                    "savedOdt": saved,
                    "desktopRoundtrip": desktop,
                    "pass": metrics.get("pass") is True
                    and saved["pass"]
                    and desktop["pass"],
                }
                write_json(run_root / "result.json", result)
                summaries.append({
                    "run": run_number,
                    "result": str(run_root / "result.json"),
                    "pass": result["pass"],
                })
            finally:
                session.close()
        summary = {
            "schemaVersion": 1,
            "release": "R7-B",
            "browser": args.browser,
            "requestedRuns": args.runs,
            "runs": summaries,
            "pass": len(summaries) == args.runs and all(item["pass"] for item in summaries),
        }
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

