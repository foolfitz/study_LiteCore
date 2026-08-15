#!/usr/bin/env python3
"""Drive SPEC E2-C phase D0 in one browser and save what came back.

No verdict here.  The runner collects; tools/analyze_e2_c_d0.py applies the
criteria that e2/validation-matrix-v1.json froze before any of this ran, and it
does that without a browser so the verdict can be recomputed from the files.

Attribution is checked rather than assumed: the runner hashes the profile on
disk and the page reports the hashes the manifest gave it.  Evidence filed
under an artifact that never ran it is finding 027's failure mode, and it costs
nothing to notice.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1_support import sha256, write_json  # noqa: E402
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent


def artifact_hashes(profile: str) -> dict[str, str]:
    directory = PROJECT / "dist" / "profiles" / profile
    return {
        "profile": profile,
        "wasmSha256": sha256(directory / "probe.wasm"),
        "loaderSha256": sha256(directory / "probe.js"),
        "workerSha256": sha256(directory / "sdk-worker.js"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--profile", default="e2-editor-v2")
    parser.add_argument("--fixture", default="list-contexts.odt")
    parser.add_argument("--timeout", type=float, default=900)
    # Parameterised so the same collection path serves the D1 pre-flight probe:
    # a second copy of this file would be a second place for the attribution
    # check to rot.  The defaults are D0's, so `run_e2_c_d0.py` with no flags
    # still reproduces the D0 evidence exactly.
    parser.add_argument("--page", default="e2-c-d0.html")
    parser.add_argument("--namespace", default="__e2c_d0")
    parser.add_argument("--output", type=Path,
                        default=PROJECT.parent / "findings" / "evidence" / "sdk-e2"
                        / "e2-c-validation" / "d0")
    args = parser.parse_args()

    artifact = artifact_hashes(args.profile)
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    metrics = None
    saves: list[dict] = []
    log_text = ""
    try:
        base = f"http://127.0.0.1:{port}/{args.page}"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(f"{base}?profile={args.profile}&fixture={args.fixture}")
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            metrics = evaluate(session, f"globalThis.{args.namespace} || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.5)
        if not metrics or not metrics.get("complete"):
            metrics = {"schemaVersion": 1, "release": "spec-e2c-d0",
                       "complete": False,
                       "error": {"code": "RUNNER_TIMEOUT",
                                 "message": "page never completed"}}
        else:
            # One at a time: a single evaluate carrying every saved document is
            # the kind of call that truncates without saying so.
            count = evaluate(
                session, f"globalThis.{args.namespace}_save_count()") or 0
            for index in range(int(count)):
                saves.append(evaluate(
                    session, f"globalThis.{args.namespace}_save({index})"))
        log_text = str(evaluate(
            session, "document.querySelector('#log')?.textContent || ''"))
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    inventory = (metrics.get("cells") or {}).get("d0-inventory") or {}
    reported = {key: inventory.get(key)
                for key in ("wasmSha256", "loaderSha256", "workerSha256")}
    metrics["artifact"] = artifact
    metrics["attribution"] = {
        "runnerProfile": args.profile,
        "pageReported": reported,
        "consistent": all(reported.get(key) == artifact[key] for key in reported),
    }
    metrics["browserName"] = args.browser

    evidence = args.output / f"{args.profile}-{artifact['wasmSha256'][:8]}" / args.browser
    (evidence / "saved").mkdir(parents=True, exist_ok=True)
    written = []
    for entry in saves:
        if not entry or not entry.get("b64"):
            continue
        name = f"{entry['label']}.odt"
        (evidence / "saved" / name).write_bytes(base64.b64decode(entry["b64"]))
        written.append({"label": entry["label"], "file": f"saved/{name}"})
    metrics["savedDocuments"] = written
    write_json(evidence / "result.json", metrics)
    (evidence / "page.log").write_text(log_text, encoding="utf-8")
    print(json.dumps({
        "evidence": str(evidence),
        "complete": metrics.get("complete"),
        "cells": len(metrics.get("cells") or {}),
        "saved": len(written),
        "attributionConsistent": metrics["attribution"]["consistent"],
        "error": metrics.get("error"),
    }, indent=2, ensure_ascii=False))
    return 0 if metrics.get("complete") and not metrics.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
