#!/usr/bin/env python3
"""DIAGNOSTIC ONLY.  Serves bench.html from this directory and runs it once in headless Chrome or Firefox (the
shared session classes the runners use), writing the page's result JSON.  Usage: run_bench.py --browser B --out F"""
import argparse, json, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
sys.path.insert(0, str(TOOLS))
import run_e2_c_product_path as pp  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--small", action="store_true", help="64 x 64 sources (fable's fifth ruling, Part 5 item 1)")
ap.add_argument("--restore", action="store_true", help="64 x 64 restores from a cached band (release A's design)")
a = ap.parse_args()
port = pp.free_port()
server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(HERE)],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
session, report = None, {"bench": "canvas-bench/bench.html", "browser": a.browser,
                         "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
try:
    pp.wait_page(f"http://127.0.0.1:{port}/bench.html")
    query = "?restore=1" if a.restore else "?small=1" if a.small else ""
    report["small"], report["restore"] = a.small, a.restore
    session = (pp.ChromeSession if a.browser == "chrome" else pp.FirefoxSession)("cold")
    report["version"] = getattr(session, "version", None)
    pp.navigate(session, f"http://127.0.0.1:{port}/bench.html{query}")
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        raw = pp.evaluate(session, "(() => document.documentElement.dataset.bench || null)()")
        if raw:
            report["result"] = json.loads(raw)
            break
        time.sleep(1)
    else:
        report["error"] = "timed out"
finally:
    report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    if session is not None:
        session.close()
    server.terminate()
    a.out.write_text(json.dumps(report, indent=1))
print(json.dumps(report.get("result", report), indent=None)[:3000])
