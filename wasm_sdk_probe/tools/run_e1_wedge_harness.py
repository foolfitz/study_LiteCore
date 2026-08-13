#!/usr/bin/env python3
"""Drive one of the finding 038 harnesses on the shipped editor artifact.

Two pages share this runner, because they ask two halves of one question:

  e1-session-wedge-recovery   what the product EditorSession does when the
                              wedge fires -- does it escalate, does restart
                              work, what does the user lose (task 035)
  e1-post-wedge-liveness      whether the engine is dead after the wedging
                              selection or only the state read is

Re-hashes the shipped artifact before the run and records it beside the result,
because a verdict that does not name the artifact it was measured on is exactly
what finding 027 was about.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

from e1_support import sha256, write_json
from r7_support import evaluate, wait_page
from run_browser_probe import ChromeSession, FirefoxSession, free_port


HARNESSES = {
    "session-wedge": {
        "page": "e1-session-wedge-recovery.html",
        "global": "__e1_session_wedge",
        "evidence": "session-wedge-recovery",
    },
    "post-wedge-liveness": {
        "page": "e1-post-wedge-liveness.html",
        "global": "__e1_post_wedge",
        "evidence": "post-wedge-liveness",
    },
    "checkpoint-cost": {
        "page": "e1-checkpoint-cost.html",
        "global": "__e1_checkpoint_cost",
        "evidence": "checkpoint-cost",
    },
}


def next_evidence_directory(base: Path) -> Path:
    if not (base / "result.json").exists():
        return base
    attempt = 2
    while (base / f"attempt-{attempt:02d}").exists():
        attempt += 1
    return base / f"attempt-{attempt:02d}"


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument(
        "--harness",
        choices=("session-wedge", "post-wedge-liveness", "checkpoint-cost"),
        default="session-wedge")
    parser.add_argument("--profile", default="e1-editor-v1")
    parser.add_argument("--fixture", default="frame-contexts.odt")
    parser.add_argument("--exhaust", choices=("0", "1"), default="1")
    # session-wedge: three wedges at ~30 s each, three opens of a document that
    # carries as-char frames, and the close paths finding 012 makes slow.
    # post-wedge-liveness: ten fresh engines, half of them probing a wedge.
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--evidence-root", type=Path, default=None)
    args = parser.parse_args()

    harness = HARNESSES[args.harness]
    evidence_root = args.evidence_root or (
        workspace / "findings" / "evidence" / "sdk-e1" / harness["evidence"])

    artifact = project / "dist" / "profiles" / args.profile / "probe.wasm"
    if not artifact.exists():
        raise SystemExit(f"artifact missing: {artifact}")
    artifact_hash = sha256(artifact)

    server_port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(project / "web" / "serve.py"), "--port", str(server_port)],
        cwd=project,
        # finding 023: nothing reads these pipes, and a full pipe buffer stalls
        # the handler thread mid-response.
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    session = None
    evidence = next_evidence_directory(evidence_root / args.browser)
    evidence.mkdir(parents=True, exist_ok=True)
    try:
        base_url = f"http://127.0.0.1:{server_port}/{harness['page']}"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        query = urlencode({
            "profile": args.profile,
            "fixture": args.fixture,
            "exhaust": args.exhaust,
        })
        session.navigate(f"{base_url}?{query}")
        deadline = time.monotonic() + args.timeout
        metrics = None
        while time.monotonic() < deadline:
            metrics = evaluate(session, f"globalThis.{harness['global']} || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.5)
        if not metrics or not metrics.get("complete"):
            metrics = {
                **(metrics or {}),
                "complete": False,
                "error": {
                    "code": "RUNNER_TIMEOUT",
                    "message": f"page timed out after {args.timeout}s",
                },
            }
        log_text = str(evaluate(session, "document.querySelector('#log')?.textContent || ''"))
        (evidence / "page.log.txt").write_text(log_text, encoding="utf-8")
        (evidence / "ARTIFACT.sha256").write_text(
            f"{artifact_hash}  dist/profiles/{args.profile}/probe.wasm\n", encoding="utf-8")
        result = {
            **metrics,
            "browserName": args.browser,
            "browserVersion": session.version,
            "artifactSha256": artifact_hash,
            "evidenceDirectory": str(evidence),
        }
        write_json(evidence / "result.json", result)
        predictions = result.get("predictions") or {}
        print(json.dumps({
            "harness": args.harness,
            "browser": args.browser,
            "artifact": artifact_hash[:8],
            "result": str(evidence / "result.json"),
            "complete": result.get("complete") is True,
            "predictionsHeld": {k: v.get("held") for k, v in predictions.items()},
            "summary": result.get("summary"),
        }, ensure_ascii=False, indent=2))
        # The runner does not decide whether the finding is good news.  It exits
        # non-zero only when the run did not produce a readable measurement --
        # a prediction that failed is a result, not a broken run.
        if result.get("complete") is not True:
            raise SystemExit(1)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
