#!/usr/bin/env python3
"""Run R7-D DOM/focus/accessibility assertions in Chrome and Firefox."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from r7_support import ChromeSession, FirefoxSession, evaluate, wait_page, write_json
from run_browser_probe import free_port


def ax_summary(tree: dict) -> dict:
    names = []
    roles = []
    for node in tree.get("nodes", []):
        role = node.get("role", {}).get("value")
        name = node.get("name", {}).get("value")
        if role:
            roles.append(role)
        if name:
            names.append(name)
    required_names = ["第一頁", "下一頁", "150%", "搜尋", "下載本機 ODT"]
    return {
        "nodeCount": len(tree.get("nodes", [])),
        "roles": sorted(set(roles)),
        "requiredNames": [
            {"name": expected, "found": any(expected in name for name in names)}
            for expected in required_names
        ],
        "pass": bool(tree.get("nodes"))
        and all(any(expected in name for name in names) for expected in required_names)
        and "status" in roles,
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument(
        "--evidence-root", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r7" / "browser" / "usability",
    )
    args = parser.parse_args()
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
    session = None
    try:
        base_url = f"http://127.0.0.1:{port}/r7-reference.html"
        wait_page(base_url)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(f"{base_url}?usability=1&pageCount=100")
        deadline = time.monotonic() + args.timeout
        metrics = None
        while time.monotonic() < deadline:
            metrics = evaluate(session, "globalThis.__r7_reference || null")
            if metrics and metrics.get("complete"):
                break
            time.sleep(0.5)
        if not metrics or not metrics.get("complete"):
            raise RuntimeError("R7-D usability timed out")
        root = args.evidence_root / args.browser
        root.mkdir(parents=True, exist_ok=True)
        (root / "page.png").write_bytes(session.screenshot())
        (root / "browser.log.txt").write_text(
            str(evaluate(session, "document.querySelector('#log').textContent")),
            encoding="utf-8",
        )
        ax = {"status": "firefox-dom-webdriver-only", "pass": None}
        if isinstance(session, ChromeSession):
            session.call("Accessibility.enable")
            tree = session.call("Accessibility.getFullAXTree")
            write_json(root / "ax-tree.json", tree)
            ax = {"status": "checked", **ax_summary(tree)}
        result = {
            "schemaVersion": 1,
            "release": "R7-D-usability",
            "browser": args.browser,
            "browserVersion": session.version,
            "sessionType": "headless-automatic",
            "metrics": metrics.get("usability"),
            "accessibilityTree": ax,
            "documentContentAccessibility": "unsupported",
            "pass": metrics.get("pass") is True and (ax["pass"] is not False),
        }
        write_json(root / "result.json", result)
        print(json.dumps({"result": str(root / "result.json"), "pass": result["pass"]}, ensure_ascii=False))
        if not result["pass"]:
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
