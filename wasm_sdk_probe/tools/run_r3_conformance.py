#!/usr/bin/env python3
"""Run R3 ABI compatibility and public-surface conformance in a browser."""

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
        results = (last_state.get("metrics") or {}).get("conformance") or []
        if results and results[-1].get("pass"):
            return last_state
        status = last_state.get("status", "")
        if status in {"action failed", "module initialization failed"}:
            raise RuntimeError(
                f"R3 conformance failed ({status}):\n{last_state.get('log', '')}"
            )
        time.sleep(0.5)
    raise RuntimeError(
        f"R3 conformance timed out with status {last_state.get('status')}:\n"
        f"{last_state.get('log', '')}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument(
        "--url", default="http://127.0.0.1:8765/r3.html?memory=skip"
    )
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    args.evidence_dir.mkdir(parents=True, exist_ok=True)

    session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
    session = session_class("cold")
    prefix = f"{args.browser}-r3-conformance"
    state: dict[str, Any] = {}
    try:
        session.navigate(args.url)
        wait_for_ready(session, args.timeout)
        session.click("#run-conformance")
        state = wait_for_conformance(session, args.timeout)
        (args.evidence_dir / f"{prefix}.png").write_bytes(session.screenshot())
        (args.evidence_dir / f"{prefix}.log.txt").write_text(
            state.get("log", ""), encoding="utf-8"
        )
    finally:
        session.close()

    result = {
        "browser": args.browser,
        "browser_version": session.version,
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
