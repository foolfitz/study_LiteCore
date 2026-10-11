#!/usr/bin/env python3
"""Does headless Chrome reset its certificate verifier on its own after launch?  (PREDICTION.md, this directory.)

Launches Chrome with exactly the runners' flags (wasm_sdk_probe/tools/run_browser_probe.py:213-223), optionally plus
--disable-component-update; keeps fetches in flight against the ddev instance; records every Network.loadingFailed
and when each top-level entry of the fresh profile directory first appears.  Standalone: imports nothing from tools/.

  probe_cert_verifier.py --label e1-1 [--disable-component-update] [--seconds 360] --out FILE.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from websockets.sync.client import connect

ORIGIN = "https://litecore.ddev.site:8443"
START_URL = ORIGIN + "/status.php"
ASSET = ORIGIN + "/dist/workflowengine-workflowengine.js"   # ~0.85 MB: keeps a stream in flight most of the time
LOOP_JS = """
(() => {
  if (globalThis.__cv) return true;
  globalThis.__cv = {started: 0, ok: 0, failed: 0, errors: {}};
  const one = async () => {
    for (;;) {
      globalThis.__cv.started++;
      try {
        const r = await fetch(%s + "?r=" + Math.random(), {cache: "no-store"});
        await r.arrayBuffer();
        globalThis.__cv.ok++;
      } catch (e) {
        globalThis.__cv.failed++;
        const k = String(e && e.message || e);
        globalThis.__cv.errors[k] = (globalThis.__cv.errors[k] || 0) + 1;
        await new Promise(res => setTimeout(res, 50));
      }
    }
  };
  for (let i = 0; i < 2; i++) one();
  return true;
})()
""" % json.dumps(ASSET)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--disable-component-update", action="store_true")
    ap.add_argument("--seconds", type=float, default=360)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    chrome = shutil.which("google-chrome")
    profile = Path(tempfile.mkdtemp(prefix="cert-verifier-probe-"))
    port = free_port()
    flags = ["--headless=new", f"--remote-debugging-port={port}", "--remote-allow-origins=*",
             f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check"]
    if args.disable_component_update:
        flags.append("--disable-component-update")
    t0 = time.monotonic()
    launched_at = utc()
    proc = subprocess.Popen([chrome, *flags, "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report = {"label": args.label, "flags": flags, "launchedAt": launched_at, "seconds": args.seconds,
              "asset": ASSET, "profileEntries": {}, "loadingFailed": [], "otherEvents": {}}
    try:
        deadline = time.monotonic() + 20
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                    report["version"] = json.load(r).get("Browser")
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
                    page = next(t for t in json.load(r) if t["type"] == "page")
                break
            except Exception:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.2)
        ws = connect(page["webSocketDebuggerUrl"], origin="http://127.0.0.1", max_size=None)
        mid = 0

        def send(method, params=None):
            nonlocal mid
            mid += 1
            ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
            return mid

        pending = {}

        def handle(msg):
            m = msg.get("method")
            if m == "Network.loadingFailed":
                p = msg["params"]
                report["loadingFailed"].append({"t": round(time.monotonic() - t0, 3), "at": utc(),
                                                "errorText": p.get("errorText"), "type": p.get("type"),
                                                "canceled": p.get("canceled")})
            elif m:
                report["otherEvents"][m] = report["otherEvents"].get(m, 0) + 1
            if "id" in msg:
                pending[msg["id"]] = msg

        def call(method, params=None, timeout=30):
            i = send(method, params)
            end = time.monotonic() + timeout
            while i not in pending:
                handle(json.loads(ws.recv(timeout=max(0.05, end - time.monotonic()))))
            return pending.pop(i)

        call("Network.enable")
        call("Page.enable")
        call("Page.navigate", {"url": START_URL})
        time.sleep(1.5)
        report["loopStarted"] = call("Runtime.evaluate", {"expression": LOOP_JS, "returnByValue": True}).get("result")
        report["loopStartedT"] = round(time.monotonic() - t0, 3)
        next_ls = 0.0
        end = t0 + args.seconds
        while time.monotonic() < end:
            now = time.monotonic()
            if now >= next_ls:
                next_ls = now + 1.0
                for entry in sorted(profile.iterdir()):
                    if entry.name not in report["profileEntries"]:
                        report["profileEntries"][entry.name] = {"t": round(now - t0, 3), "at": utc(),
                                                                "dir": entry.is_dir()}
                # One level deeper in every top-level directory: a component's directory exists (empty) from
                # launch; its INSTALL is a version subdirectory appearing inside it (smoke run, 2026-10-11).
                for top in sorted(p for p in profile.iterdir() if p.is_dir()):
                    try:
                        children = sorted(top.iterdir())
                    except OSError:
                        continue
                    for entry in children:
                        key = top.name + "/" + entry.name
                        if key not in report["profileEntries"]:
                            report["profileEntries"][key] = {"t": round(now - t0, 3), "at": utc(),
                                                             "dir": entry.is_dir()}
            try:
                handle(json.loads(ws.recv(timeout=0.2)))
            except TimeoutError:
                pass
        res = call("Runtime.evaluate", {"expression": "JSON.stringify(globalThis.__cv || null)",
                                        "returnByValue": True})
        report["counters"] = json.loads(res.get("result", {}).get("result", {}).get("value") or "null")
        # Versions the component updater installed, as Chrome itself reports them.
        call("Page.navigate", {"url": "chrome://components"})
        time.sleep(1.5)
        res = call("Runtime.evaluate", {"expression": "document.body ? document.body.innerText : null",
                                        "returnByValue": True})
        report["chromeComponents"] = res.get("result", {}).get("result", {}).get("value")
        ws.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        report["completedAt"] = utc()
        report["profileDir"] = str(profile)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        shutil.rmtree(profile, ignore_errors=True)
    kinds = {}
    for f in report["loadingFailed"]:
        kinds[f["errorText"]] = kinds.get(f["errorText"], 0) + 1
    print(args.label, "counters", report.get("counters"), "failed kinds", kinds,
          "cert-ish entries", {k: v["t"] for k, v in report["profileEntries"].items()
                               if "/" in k and any(s in k for s in ("PKIMetadata/", "CertificateRevocation/",
                                                                    "SSLErrorAssistant/"))})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
