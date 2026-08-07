#!/usr/bin/env python3
"""Run the R2 SDK lifecycle and ABI conformance checks in a browser."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from run_browser_probe import (
    ChromeSession,
    FirefoxSession,
    browser_state,
    wait_for_ready,
)


def wait_for_conformance(session: Any, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last_state = browser_state(session)
        conformance = (last_state.get("metrics") or {}).get("conformance") or []
        if conformance and conformance[-1].get("pass"):
            return last_state
        status = last_state.get("status", "")
        if status.startswith("error:") or status in {
            "action failed",
            "event handling error",
            "module initialization failed",
        }:
            raise RuntimeError(
                f"R2 conformance failed ({status}):\n{last_state.get('log', '')}"
            )
        time.sleep(0.5)
    raise RuntimeError(
        f"R2 conformance timed out with status {last_state.get('status')}:\n"
        f"{last_state.get('log', '')}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--doc", type=Path, required=True)
    parser.add_argument(
        "--url", default="http://127.0.0.1:8765/r2.html?memory=skip"
    )
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.doc.is_file():
        raise SystemExit(f"missing document: {args.doc}")
    args.evidence_dir.mkdir(parents=True, exist_ok=True)

    session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
    session = session_class("cold")
    prefix = f"{args.browser}-{args.doc.stem}-r2-conformance"
    state: dict[str, Any] = {}
    try:
        session.navigate(args.url)
        wait_for_ready(session, args.timeout)
        session.set_file("#file", args.doc)
        session.click("#run-conformance")
        state = wait_for_conformance(session, args.timeout)
        (args.evidence_dir / f"{prefix}.png").write_bytes(session.screenshot())
    finally:
        if state:
            (args.evidence_dir / f"{prefix}.log.txt").write_text(
                state.get("log", ""), encoding="utf-8"
            )
        session.close()

    result = {
        "browser": args.browser,
        "browser_version": session.version,
        "doc": args.doc.name,
        "conformance": state["metrics"]["conformance"][-1],
        "manifest": state["metrics"].get("manifest"),
        "isolation": state["metrics"].get("isolation"),
    }
    output_path = args.evidence_dir / f"{prefix}.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(output_path)


if __name__ == "__main__":
    main()
