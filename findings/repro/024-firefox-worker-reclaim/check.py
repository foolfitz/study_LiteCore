#!/usr/bin/env python3
"""Automated repro driver (stdlib only; needs geckodriver + firefox in PATH).

Starts serve.py, opens the self-renavigating page in headless Firefox, and
watches the navigation counter in the URL.  When the counter stops advancing
for --stall-seconds, the current navigation is the wedge point.  The page
itself never errors on the worker-slot path -- the silence is the bug.

Examples:
  python3 check.py                          # worker-slot budget (~66 on FF153)
  python3 check.py --touch 700              # memory budget (~8 on FF153)
  python3 check.py --pref dom.workers.maxPerDomain=64   # wall moves to ~9
  python3 check.py --firefox-binary ~/nightly/firefox   # test a nightly
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(method: str, url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.loads(response.read())


def wait_http(url: str, timeout: float = 20) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError(url)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--touch", type=int, default=0,
                        help="MiB of shared memory to commit per navigation")
    parser.add_argument("--pref", action="append", default=[],
                        metavar="NAME=JSON", help="extra Firefox pref")
    parser.add_argument("--firefox-binary", help="path to a firefox binary")
    parser.add_argument("--stall-seconds", type=float, default=90)
    parser.add_argument("--max-navigations", type=int, default=200)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    serve_port = free_port()
    driver_port = free_port()
    log_dir = Path(tempfile.mkdtemp(prefix="repro024-"))
    serve_log = open(log_dir / "serve.log", "w", buffering=1)
    server = subprocess.Popen(
        [sys.executable, str(here / "serve.py"), "--port", str(serve_port)],
        stdout=serve_log, stderr=subprocess.STDOUT, text=True,
    )
    geckodriver = shutil.which("geckodriver")
    if not geckodriver:
        raise SystemExit("geckodriver not found in PATH")
    driver = subprocess.Popen(
        [geckodriver, "--port", str(driver_port), "--log", "error"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{driver_port}"
    session_id = None
    try:
        wait_http(f"http://127.0.0.1:{serve_port}/index.html")
        wait_http(f"{base}/status")
        prefs: dict[str, object] = {"browser.cache.disk.enable": False,
                                    "browser.cache.memory.enable": False}
        for item in args.pref:
            name, _, raw = item.partition("=")
            try:
                prefs[name] = json.loads(raw)
            except json.JSONDecodeError:
                prefs[name] = raw
        options: dict[str, object] = {"args": ["-headless"], "prefs": prefs}
        if args.firefox_binary:
            options["binary"] = str(Path(args.firefox_binary).resolve())
        value = request("POST", f"{base}/session", {
            "capabilities": {"alwaysMatch": {
                "browserName": "firefox", "moz:firefoxOptions": options,
            }},
        })["value"]
        session_id = value["sessionId"]
        version = value["capabilities"].get("browserVersion", "unknown")

        query = f"?n=1&touch={args.touch}" if args.touch else "?n=1"
        request("POST", f"{base}/session/{session_id}/url",
                {"url": f"http://127.0.0.1:{serve_port}/index.html{query}"})

        last_n = 0
        last_change = time.monotonic()
        wedge_kind = None
        while True:
            time.sleep(2)
            url = request("GET", f"{base}/session/{session_id}/url", None)["value"]
            n = int(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                    .get("n", ["0"])[0])
            if n != last_n:
                last_n = n
                last_change = time.monotonic()
                print(f"navigation {n}", flush=True)
            title = request("GET", f"{base}/session/{session_id}/title", None)["value"]
            if title.startswith(("WEDGED", "ABORT", "ERROR")):
                wedge_kind = title
                break
            if time.monotonic() - last_change > args.stall_seconds:
                wedge_kind = f"stalled at nav {last_n} (no title change)"
                break
            if last_n >= args.max_navigations:
                wedge_kind = None
                break
        print(json.dumps({
            "browserVersion": version,
            "touchMib": args.touch,
            "prefs": {k: v for k, v in prefs.items() if k.startswith("dom.")},
            "wall": last_n if wedge_kind else None,
            "outcome": wedge_kind or f"clean through {last_n} navigations",
        }, ensure_ascii=False), flush=True)
    finally:
        if session_id:
            try:
                request("DELETE", f"{base}/session/{session_id}", None)
            except Exception:
                pass
        driver.terminate()
        server.terminate()
        serve_log.close()


if __name__ == "__main__":
    main()
