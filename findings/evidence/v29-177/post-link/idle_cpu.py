#!/usr/bin/env python3
"""SPEC-M3-v29-tick-pacing T2: CPU seconds of the browser's whole process tree over 10 quiet seconds.

  idle_cpu.py VARIANT BROWSER DOCUMENT OUT      VARIANT = v28 | v29 | spin (v28 with the tick forced to full speed, the red case)

The tree is every process that appeared after a snapshot taken before the browser started, less this tool's own helpers, so
a browser already open on the owner's desktop is not counted.  dist/ and web/ do not change.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4] / "wasm_sdk_probe"
sys.path.insert(0, str(ROOT / "tools"))
import probe_typing_latency as t

pp, p111 = t.pp, t.p111
TICK = os.sysconf("SC_CLK_TCK")
HELPERS = {"python3", "python", "sh", "bash", "sleep", "ps", "cat", "grep", "git", "uptime"}
SPIN = ("mode=2;value=0;if(!MainLoop.setImmediate){const channel=new MessageChannel();const queue=[];"
        "channel.port1.onmessage=()=>queue.shift()();MainLoop.setImmediate=tick=>{queue.push(tick);channel.port2.postMessage(0)}}")
MARKER = "var _emscripten_set_main_loop_timing=(mode,value)=>{"


def pids():
    return {int(n) for n in os.listdir("/proc") if n.isdigit()}


def cpu(before):
    """{pid: cpu seconds}.  Per process: a sum over the live set falls when a process exits inside the window, which gave
    negative readings in run 01 (idle-run-01-sum-of-live-processes/)."""
    out = {}
    for pid in pids() - before:
        try:
            raw = Path(f"/proc/{pid}/stat").read_text()
        except OSError:
            continue
        comm = raw[raw.index("(") + 1:raw.rindex(")")]
        fields = raw[raw.rindex(")") + 2:].split()
        if comm not in HELPERS:
            out[pid] = (int(fields[11]) + int(fields[12])) / TICK
    return out


def window(before, seconds=10.0):
    start = cpu(before)
    time.sleep(seconds)
    end = cpu(before)
    # A process alive at both ends counts its delta, one born inside counts all it used, one gone counts nothing it used
    # after the last reading, so a reading can be low by a dying process but never negative.
    used = sum(value - start.get(pid, 0.0) for pid, value in end.items())
    assert used >= 0
    return {"cpuSeconds": round(used, 3), "overSeconds": seconds, "processes": len(end), "gone": len(set(start) - set(end))}


def main():
    variant, browser, document, out = sys.argv[1:5]
    doc, click = t.PLACES[document]
    overrides = {}
    if variant == "v29":
        source = pp.CUTOVER_PAGE_SOURCE.read_text(encoding="utf-8")
        page, _, _ = pp.repointed_page(source, "e2-editor-v29", t.DIST / "profiles/e2-editor-v29/sdk-manifest.json")
        overrides["e2-editor-app.js"] = page.encode("utf-8")
    elif variant == "spin":
        relative = "profiles/e2-editor-v28/probe.js"
        text = (t.DIST / relative).read_text(encoding="utf-8")
        assert text.count(MARKER) == 1
        overrides[relative] = text.replace(MARKER, MARKER + SPIN).encode("utf-8")
    mirror = Path(tempfile.mkdtemp(prefix="idle-")) / "root"
    pp.build_mirror(t.DIST, mirror, overrides)
    (mirror / "doc.odt").write_bytes(doc.read_bytes())
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(t.HERE / "web" / "serve.py"), "--port", str(port), "--root", str(mirror)],
                              cwd=t.HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    report = {"variant": variant, "browser": browser, "document": document}
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        before = pids()
        session = (pp.ChromeSession if browser == "chrome" else pp.FirefoxSession)("cold")
        report["version"] = getattr(session, "version", None)
        pp.navigate(session, base)
        pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        pp.evaluate(session, pp.INSTALL)
        pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./doc.odt").replace("ARG_NAME", "doc.odt"))
        pp.wait_for(session, lambda s: (s.get("doc") or "") == "doc.odt" and s.get("state") == "ready", 180)
        p111.quiet(session)
        was = (pp.evaluate(session, pp.READ_STATE) or {}).get("latency")
        pp.evaluate(session, pp.POINT_AT.replace("ARG_X", click[0]).replace("ARG_Y", click[1]))
        pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or "") and s.get("latency") != was, 30)
        p111.quiet(session)
        time.sleep(3.0)
        report["opened"] = window(before)
        p111.burst(session, browser, [chr(ord("a") + i) for i in range(10)], 200)
        p111.quiet(session)
        time.sleep(2.0)
        report["typed"] = window(before)
    finally:
        if session is not None:
            session.close()
        server.terminate()
    Path(out).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
