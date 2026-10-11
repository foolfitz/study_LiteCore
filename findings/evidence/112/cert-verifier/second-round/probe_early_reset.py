#!/usr/bin/env python3
"""Second round (PREDICTION.md, this directory): when, after launch, does headless Chrome reset its certificate
verifier, and which launch change makes the reset disappear?

One launch per invocation.  Chrome is started with exactly the runners' flags (wasm_sdk_probe/tools/
run_browser_probe.py:213-223) plus `--log-net-log=<file>` (every arm; the deviation is argued in PREDICTION.md) and
the arm's extra flags.  The page keeps fetches of a ~0.85 MB same-origin asset in flight (2 streams, the first
round's shape) from the first moment the origin is reachable until `--seconds` after launch; every
Network.loadingFailed is recorded with its time since launch.  After the window a deliberate fetch to a closed port
must fail (positive control for failure capture).  Chrome is then closed and its net log is parsed for the
verifier-change signature (SOCKET_POOL_CLOSING_SOCKET with reason "Cert verifier changed"; secondary: any event with
net_error -455, HTTP2_SESSION_CLOSE "Finished going away"), the network-time query (clients2.google.com/time/1/
current), what the browser had just finished fetching before each change, CERT_VERIFY_PROC jobs, and every host the
browser contacted.  Standalone: imports nothing from tools/.  The raw net log stays where `--netlog-dir` points
(gzipped after parsing; not evidence).

  probe_early_reset.py --label e1-01 --arm e1 --out e1-01.json --netlog-dir DIR [--seconds 16] [--idle-seconds 0]
                       [--extra-flag --disable-component-update] [--extra-flag --disable-features=X]
  probe_early_reset.py --reparse e1-01.json      # re-run the net-log reader on an existing report (reader fix)
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
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
ASSET = ORIGIN + "/dist/workflowengine-workflowengine.js"   # 847,387 bytes (first round's asset)
TIME_QUERY_MARK = "clients2.google.com/time/1/current"
STREAMS = 2
RESET_KIND = "pool-closing:Cert verifier changed"           # the instant signature of a verifier change
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
        await new Promise(res => setTimeout(res, 20));
      }
    }
  };
  for (let i = 0; i < %d; i++) one();
  return true;
})()
""" % (json.dumps(ASSET), STREAMS)
STOP_JS = "(() => { const c = globalThis.__cv; globalThis.__cv = null; return JSON.stringify(c || null); })()"
CONTROL_JS = """
(() => { globalThis.__ctl = null;
  fetch(%s, {cache: "no-store"}).then(r => { globalThis.__ctl = {status: r.status}; })
    .catch(e => { globalThis.__ctl = {error: String(e && e.message || e)}; });
  return true; })()
"""


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def host_of(url: str) -> str:
    return re.sub(r"^[a-z]+://([^/]+).*$", r"\1", url)


# ----------------------------------------------------------------------------------------------- net-log reader

def open_text(path: Path) -> str:
    if path.suffix == ".gz" or not path.exists() and path.with_suffix(path.suffix + ".gz").exists():
        p = path if path.suffix == ".gz" else path.with_suffix(path.suffix + ".gz")
        with gzip.open(p, "rt", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return path.read_text(encoding="utf-8", errors="replace")


def parse_netlog(path: Path, launch_epoch: float) -> dict:
    """Read Chrome's --log-net-log file (one event per line; tolerant of a truncated tail) into the summary
    PREDICTION.md reads.  Times are seconds after launch (constants.timeTickOffset + event.time, minus the launch
    epoch)."""
    gz = path.with_suffix(path.suffix + ".gz")
    actual = path if path.exists() else gz
    out: dict = {"file": str(actual), "bytes": actual.stat().st_size if actual.exists() else 0, "parsedOk": False}
    if not actual.exists():
        out["error"] = "no net log file"
        return out
    text = open_text(actual)
    marker = re.search(r'"events"\s*:\s*\[', text)
    if not marker:
        out["error"] = "no events array"
        return out
    head = text[:marker.start()].rstrip().rstrip(",")
    try:
        constants = json.loads(head + "}")["constants"]
    except Exception as exc:  # noqa: BLE001 -- the reader reports, it does not hide
        out["error"] = f"constants unparsable: {exc!r}"
        return out
    tick_offset_ms = float(constants.get("timeTickOffset", "0"))
    type_name = {v: k for k, v in constants.get("logEventTypes", {}).items()}
    phase_name = {v: k for k, v in constants.get("logEventPhase", {}).items()}
    source_name = {v: k for k, v in constants.get("logSourceType", {}).items()}
    net_error_name = {v: k for k, v in constants.get("netError", {}).items()}
    out["timeTickOffset"] = tick_offset_ms
    out["complete"] = '"polledData"' in text[-4_000_000:]   # Chrome appends polledData only on a clean finish

    def t_of(ev) -> float:
        return round((tick_offset_ms + float(ev["time"])) / 1000.0 - launch_epoch, 3)

    events = 0
    bad_lines = 0
    sources: dict[int, dict] = {}          # URL requests: id -> {url, host, start, end, netError}
    instant: list[dict] = []               # RESET_KIND events
    secondary: list[dict] = []             # -455 and "Finished going away"
    h2_hosts: dict[int, str] = {}
    h2_sessions: list[dict] = []
    h2_closes: list[dict] = []
    settings: list[dict] = []
    verify_procs: list[dict] = []
    hosts: dict[str, dict] = {}
    first_event_t = None
    last_event_t = None
    for line in text[marker.end():].splitlines():
        line = line.strip().rstrip(",")
        if not line.startswith("{"):
            continue
        if line.endswith("]}") or line.endswith("],"):   # the last event may carry the array's closing bracket
            line = line[:line.rfind("}") + 1]
        try:
            ev = json.loads(line)
        except Exception:  # noqa: BLE001
            bad_lines += 1
            continue
        events += 1
        try:
            t = t_of(ev)
        except Exception:  # noqa: BLE001
            bad_lines += 1
            continue
        first_event_t = t if first_event_t is None else min(first_event_t, t)
        last_event_t = t if last_event_t is None else max(last_event_t, t)
        tn = type_name.get(ev.get("type"), str(ev.get("type")))
        ph = phase_name.get(ev.get("phase"), str(ev.get("phase")))
        src = ev.get("source") or {}
        sid = src.get("id")
        params = ev.get("params") or {}
        if tn == "URL_REQUEST_START_JOB" and "url" in params:
            url = params["url"].split("?", 1)[0]      # path only: query strings carry keys and signed tokens
            host = host_of(url)
            sources.setdefault(sid, {"url": url if not url.startswith(ORIGIN) else ORIGIN + "/…",
                                     "host": host, "start": t, "end": None, "netError": None})
            h = hosts.setdefault(host, {"first": t, "count": 0})
            h["count"] += 1
            h["first"] = min(h["first"], t)
        if tn == "REQUEST_ALIVE" and ph == "PHASE_END" and sid in sources:
            sources[sid]["end"] = t
            if "net_error" in params:
                sources[sid]["netError"] = params["net_error"]
        if tn == "SOCKET_POOL_CLOSING_SOCKET":
            reason = str(params.get("reason", ""))
            if reason == "Cert verifier changed":
                instant.append({"t": t, "kind": RESET_KIND, "source": sid})
            elif "database" in reason.lower():
                instant.append({"t": t, "kind": "pool-closing:" + reason, "source": sid})
        ne = params.get("net_error")
        if ne == -455:
            secondary.append({"t": t, "kind": f"{tn}:net_error=-455", "source": sid,
                              "sourceType": source_name.get(src.get("type"))})
        if tn == "HTTP2_SESSION" and ph == "PHASE_BEGIN" and "host" in params:
            h2_hosts[sid] = params["host"]
        if tn == "HTTP2_SESSION_INITIALIZED":
            h2_sessions.append({"t": t, "source": sid, "host": h2_hosts.get(sid)})
        if tn == "HTTP2_SESSION_CLOSE":
            rec = {"t": t, "source": sid, "host": h2_hosts.get(sid), "netError": ne,
                   "netErrorName": net_error_name.get(ne) if ne is not None else None,
                   "description": params.get("description")}
            h2_closes.append(rec)
            if rec["description"] == "Finished going away":
                secondary.append({"t": t, "kind": "h2-close:Finished going away", "source": sid,
                                  "host": rec["host"]})
        if tn == "HTTP2_SESSION_RECV_SETTING":
            if "MAX_CONCURRENT" in str(params.get("id")).upper():
                settings.append({"t": t, "source": sid, "host": h2_hosts.get(sid), "value": params.get("value")})
        if tn == "CERT_VERIFY_PROC" and ph == "PHASE_BEGIN":
            verify_procs.append({"t": t, "host": params.get("host")})
    out.update({"parsedOk": True, "events": events, "badLines": bad_lines,
                "firstEventT": first_event_t, "lastEventT": last_event_t})
    tq = [s for s in sources.values() if TIME_QUERY_MARK in s["url"]]
    out["timeQuery"] = sorted(tq, key=lambda s: s["start"])
    # One "reset" = a cluster of instant signatures closer than 50 ms.  Secondary signatures are attached to the
    # nearest reset within [-0.05, +1.0] s (an H2 session finishes going away only when its active streams end).
    instant.sort(key=lambda s: s["t"])
    resets: list[dict] = []
    for s in instant:
        if resets and s["t"] - resets[-1]["tEnd"] < 0.05:
            resets[-1]["tEnd"] = s["t"]
            resets[-1]["sockets"] += 1
            resets[-1]["kinds"][s["kind"]] = resets[-1]["kinds"].get(s["kind"], 0) + 1
        else:
            resets.append({"t": s["t"], "tEnd": s["t"], "sockets": 1, "kinds": {s["kind"]: 1}, "h2GoingAway": [],
                           "minus455": 0, "justCompleted": [], "justStarted": []})
    non_origin = [s for s in sources.values() if s["host"] != host_of(ORIGIN)]
    for r in resets:
        for s in secondary:
            if -0.05 <= s["t"] - r["t"] <= 1.0:
                if s["kind"].startswith("h2-close"):
                    r["h2GoingAway"].append({"t": s["t"], "host": s.get("host")})
                else:
                    r["minus455"] += 1
        done = sorted((s for s in non_origin if s["end"] is not None and -1.0 <= r["t"] - s["end"] <= 0.5),
                      key=lambda s: s["end"], reverse=True)
        r["justCompleted"] = [{"end": s["end"], "start": s["start"], "url": s["url"][:160], "netError": s["netError"]}
                              for s in done[:6]]
        started = sorted((s for s in non_origin if 0 <= r["t"] - s["start"] <= 1.0),
                         key=lambda s: s["start"], reverse=True)
        r["justStarted"] = [{"start": s["start"], "url": s["url"][:120]} for s in started[:4]]
        r["originSessionWentAway"] = any(g["host"] and g["host"].startswith(host_of(ORIGIN)) for g in r["h2GoingAway"])
    out["resets"] = resets
    out["secondaryUnattached"] = [s for s in secondary
                                  if not any(-0.05 <= s["t"] - r["t"] <= 1.0 for r in resets)][:40]
    out["h2Sessions"] = h2_sessions
    out["h2Closes"] = h2_closes
    out["maxConcurrentStreamsSettings"] = settings[:12]
    out["certVerifyProcs"] = verify_procs[:60]
    out["hosts"] = dict(sorted(hosts.items(), key=lambda kv: kv[1]["first"]))
    out["browserRequests"] = sorted(({"start": s["start"], "end": s["end"], "url": s["url"][:160],
                                      "netError": s["netError"]} for s in non_origin), key=lambda s: s["start"])[:80]
    out["originRequests"] = sum(1 for s in sources.values() if s["host"] == host_of(ORIGIN))
    return out


# ----------------------------------------------------------------------------------------------- one launch

def launch(args) -> dict:
    chrome = shutil.which("google-chrome")
    profile = Path(tempfile.mkdtemp(prefix="early-reset-probe-"))
    args.netlog_dir.mkdir(parents=True, exist_ok=True)
    netlog = args.netlog_dir / f"{args.label}.netlog.json"
    port = free_port()
    control_url = f"https://127.0.0.1:{free_port()}/control"   # nothing listens there: ERR_CONNECTION_REFUSED
    flags = ["--headless=new", f"--remote-debugging-port={port}", "--remote-allow-origins=*",
             f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
             f"--log-net-log={netlog}", *args.extra_flag]
    launch_epoch = time.time()
    t0 = time.monotonic()
    proc = subprocess.Popen([chrome, *flags, "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report = {"label": args.label, "arm": args.arm, "flags": flags, "extraFlags": list(args.extra_flag),
              "launchedAt": datetime.fromtimestamp(launch_epoch, timezone.utc).isoformat(timespec="milliseconds"),
              "launchEpoch": launch_epoch, "seconds": args.seconds, "idleSeconds": args.idle_seconds,
              "asset": ASSET, "streams": STREAMS, "controlUrl": control_url, "loadingFailed": [], "otherEvents": {}}

    def since() -> float:
        return round(time.monotonic() - t0, 3)

    ws = None
    try:
        deadline = time.monotonic() + 20
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                    report["version"] = json.load(r).get("Browser")
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
                    page = next(tgt for tgt in json.load(r) if tgt["type"] == "page")
                break
            except Exception:  # noqa: BLE001
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.1)
        ws = connect(page["webSocketDebuggerUrl"], origin="http://127.0.0.1", max_size=None)
        mid = 0
        pending: dict[int, dict] = {}
        loaded = {"t": None}

        def send(method, params=None):
            nonlocal mid
            mid += 1
            ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
            return mid

        def handle(msg):
            m = msg.get("method")
            if m == "Network.loadingFailed":
                p = msg["params"]
                report["loadingFailed"].append({"t": since(), "at": utc(), "errorText": p.get("errorText"),
                                                "type": p.get("type"), "canceled": p.get("canceled")})
            elif m == "Page.loadEventFired":
                loaded["t"] = since()
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

        def pump(until: float):
            while time.monotonic() < until:
                try:
                    handle(json.loads(ws.recv(timeout=min(0.2, max(0.01, until - time.monotonic())))))
                except TimeoutError:
                    pass

        call("Network.enable")
        call("Page.enable")
        report["cdpReadyT"] = since()
        if args.idle_seconds > 0:
            # E3: no request at all until this many seconds after launch (the page stays about:blank).
            pump(t0 + args.idle_seconds)
        report["firstRequestT"] = since()
        call("Page.navigate", {"url": START_URL})
        pump_end = time.monotonic() + 10
        while loaded["t"] is None and time.monotonic() < pump_end:
            pump(time.monotonic() + 0.05)
        report["loadedT"] = loaded["t"]
        report["loopStarted"] = call("Runtime.evaluate", {"expression": LOOP_JS, "returnByValue": True}).get("result")
        report["loopStartedT"] = since()
        pump(t0 + args.seconds)
        res = call("Runtime.evaluate", {"expression": STOP_JS, "returnByValue": True})
        report["counters"] = json.loads(res.get("result", {}).get("result", {}).get("value") or "null")
        report["loopStoppedT"] = since()
        # Positive control: this fetch must fail, and the failure must show up as a Network.loadingFailed.
        before = len(report["loadingFailed"])
        call("Runtime.evaluate", {"expression": CONTROL_JS % json.dumps(control_url), "returnByValue": True})
        ctl_end = time.monotonic() + 5
        ctl = None
        while time.monotonic() < ctl_end:
            pump(time.monotonic() + 0.1)
            res = call("Runtime.evaluate", {"expression": "JSON.stringify(globalThis.__ctl)", "returnByValue": True})
            val = res.get("result", {}).get("result", {}).get("value")
            if val and val != "null":
                ctl = json.loads(val)
                break
        pump(time.monotonic() + 0.3)
        report["control"] = {"page": ctl, "loadingFailed": report["loadingFailed"][before:], "t": since()}
        # Close the browser the clean way so the net log is finalized.
        try:
            send("Browser.close")
        except Exception:  # noqa: BLE001
            pass
    finally:
        try:
            if ws is not None:
                ws.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            proc.wait(timeout=15)
            report["exit"] = "clean"
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=10)
                report["exit"] = "terminated"
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                report["exit"] = "killed"
        report["completedAt"] = utc()
        report["profileDir"] = str(profile)
        shutil.rmtree(profile, ignore_errors=True)
    report["netlog"] = parse_netlog(netlog, launch_epoch)
    if netlog.exists() and not args.keep_raw:
        subprocess.run(["gzip", "-1", "-f", str(netlog)], check=False)
        report["netlog"]["file"] = str(netlog) + ".gz"
    return report


def one_line(report: dict) -> str:
    nl = report.get("netlog") or {}
    kinds: dict[str, int] = {}
    for f in report.get("loadingFailed", []):
        kinds[f["errorText"]] = kinds.get(f["errorText"], 0) + 1
    tq = nl.get("timeQuery") or []
    return (f"{report['label']} arm={report.get('arm')} counters={report.get('counters')} failed={kinds} "
            f"cdpReady={report.get('cdpReadyT')} firstRequest={report.get('firstRequestT')} loop={report.get('loopStartedT')} "
            f"timeQuery={[(q['start'], q['end'], q['netError']) for q in tq]} "
            f"resets={[(r['t'], r['sockets'], len(r['h2GoingAway']), r['minus455'], r['originSessionWentAway']) for r in nl.get('resets', [])]} "
            f"events={nl.get('events')} complete={nl.get('complete')} lastEventT={nl.get('lastEventT')} "
            f"exit={report.get('exit')} control={report.get('control', {}).get('page')} "
            f"controlFailed={[f['errorText'] for f in report.get('control', {}).get('loadingFailed', [])]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label")
    ap.add_argument("--arm", default="")
    ap.add_argument("--seconds", type=float, default=16)
    ap.add_argument("--idle-seconds", type=float, default=0)
    ap.add_argument("--extra-flag", action="append", default=[])
    ap.add_argument("--netlog-dir", type=Path)
    ap.add_argument("--keep-raw", action="store_true", help="do not gzip the raw net log after parsing")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--reparse", type=Path, help="re-run the net-log reader on this report (its netlog.file)")
    args = ap.parse_args()
    if args.reparse:
        report = json.loads(args.reparse.read_text(encoding="utf-8"))
        f = Path(report["netlog"]["file"])
        report["netlog"] = parse_netlog(f if f.suffix != ".gz" else f.with_suffix(""), report["launchEpoch"])
        report["reparsedAt"] = utc()
        args.reparse.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(one_line(report))
        return 0
    if not (args.label and args.out and args.netlog_dir):
        ap.error("--label, --out and --netlog-dir are required for a launch")
    report = launch(args)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(one_line(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
