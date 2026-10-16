#!/usr/bin/env python3
"""Run the Markdown-paste arms one process at a time and keep the evidence.

Usage: run_arms.py PROBE_BINARY SCRATCH_DIR OUT_DIR [ARM_ID_PREFIX ...]

  PROBE_BINARY  md-paste-probe compiled from md_paste_probe.cpp (outside the repo)
  SCRATCH_DIR   per-run profiles and document copies (outside the repo)
  OUT_DIR       out/ of this evidence folder
  prefixes      run only arms whose id starts with one of them (default: all)

Every process: its own fresh empty user profile, its own copy of the input
document, `env -i` with HOME, PATH, LANG and SAL_USE_VCLPLUGIN=svp only
(LC_ALL, LC_CTYPE, LANGUAGE unset), `nice -n 10`, `timeout 120` around the
whole process and the probe's own 20 s watchdog around paste(), each undo and
each save. Before each process the runner waits while any other process that
names an `instdir/program` LOK install is running (another session's probe).
A finished run (summary.json present) is not rerun.
"""

import gzip
import hashlib
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
INSTALL = os.path.join(REPO, "native-lok-26-8/build/instdir/program")
sys.path.insert(0, HERE)
import md_structure  # noqa: E402

MD = "text/markdown;charset=utf-8"
PLAIN = "text/plain;charset=utf-8"
ZH = "zh_TW.UTF-8"
LISTENER_PORT = 18765

DOCS = {
    "P1": ("inputs/empty-template.odt", "doc-start"),
    "P2": ("inputs/new-document-en-US_zh-TW_A4.odt", "doc-start"),
    "P3": ("inputs/positions.fodt", "para-start"),
    "P4": ("inputs/positions.fodt", "para-middle"),
    "P5": ("inputs/positions.fodt", "bullet-start"),
    "P6": ("inputs/positions.fodt", "range-single"),
    "P7": ("inputs/positions.fodt", "range-cross"),
}

EXPECTED_READBACK = {
    "doc-start": "", "para-start": "Alpha Beta Gamma", "para-middle": "Beta Gamma",
    "bullet-start": "Item one", "range-single": "Beta", "range-cross": "Beta Gamma\nDelta",
}

# Strings whose presence in the pasted result shows the bytes were decoded right.
EXPECTED_TEXT = {
    "M8": ["標題", "粗體中文", "第一項", "第二項", "第三項"],
    "M9": ["שלום"],
    "C1": ["# Heading one", "**bold**"],
}


def arms():
    out = []

    def add(arm_id, pos, corpus, mime=MD, lang=ZH, runs=3, strace=False, strace_calls="connect",
            watchdog=20):
        out.append({"id": arm_id, "position": pos, "corpus": corpus, "mime": mime,
                    "lang": lang, "runs": runs, "strace": strace, "straceCalls": strace_calls,
                    "watchdog": watchdog})

    for m in ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M11b",
              "M12", "M13", "M14a", "M14b"]:
        add("P1-" + m, "P1", m)
    add("P1-C1-plain", "P1", "C1", mime=PLAIN)          # red control: must stay literal
    for pos in ["P2", "P3", "P4", "P5", "P6", "P7"]:
        for m in ["M1", "M2", "M4", "M8"]:
            add(pos + "-" + m, pos, m)
    # Encoding: P1-M8 above is the zh_TW.UTF-8 arm.
    add("ENC-C.UTF-8-M8", "P1", "M8", lang="C.UTF-8")
    add("ENC-C-M8", "P1", "M8", lang="C")
    add("ENC-C-M9", "P1", "M9", lang="C")
    add("ENC-C-M2", "P1", "M2", lang="C")                # ASCII control under C
    add("ENC-C-M8-plain", "P1", "M8", mime=PLAIN, lang="C")  # text/plain is UTF-8 by construction
    add("MIME-nocharset-M8", "P1", "M8", mime="text/markdown")
    add("MIME-utf16-M8", "P1", "M8-utf16le", mime="text/markdown;charset=utf-16")
    add("ENC-C-M8-utf16", "P1", "M8-utf16le", mime="text/markdown;charset=utf-16", lang="C")
    add("P1-M11-strace", "P1", "M11", runs=1, strace=True)
    # Added after the first full run: when, relative to the paste() call, is the
    # image URL fetched? write() timestamps the probe's own output lines.
    add("P1-M11b-strace", "P1", "M11b", runs=1, strace=True, strace_calls="connect,write")
    # Added after the first full run: a server that accepts and never answers.
    # Watchdog 150 s so the call's own timeout (Inet ReadTimeout 60 s by default,
    # officecfg Inet.xcs:118-122) can show instead of the probe's watchdog.
    add("P1-M11c", "P1", "M11c", watchdog=150)
    return out


class Listener(http.server.BaseHTTPRequestHandler):
    log = []

    def do_GET(self):  # noqa: N802
        Listener.log.append({"t": time.time(), "path": self.path,
                             "headers": dict(self.headers)})
        self.send_response(404)
        self.end_headers()

    def do_HEAD(self):  # noqa: N802
        self.do_GET()

    def log_message(self, *args):
        pass


class Tarpit:
    """Accepts connections on 127.0.0.1:LISTENER_PORT+1 and never answers."""
    log = []

    def __init__(self, port):
        import socket
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", port))
        self.sock.listen(16)
        self.held = []
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        while True:
            conn, _ = self.sock.accept()
            Tarpit.log.append({"t": time.time(), "event": "accept"})
            self.held.append(conn)
            threading.Thread(target=self.drain, args=(conn,), daemon=True).start()

    def drain(self, conn):
        first = True
        while True:
            try:
                data = conn.recv(4096)
            except OSError:
                data = b""
            if first and data:
                Tarpit.log.append({"t": time.time(), "event": "request",
                                   "line": data.split(b"\r\n", 1)[0].decode("latin-1")})
                first = False
            if not data:
                Tarpit.log.append({"t": time.time(), "event": "closed-by-client"})
                return


def other_lok_running():
    """Processes (not shells or Python runners) that were given a LOK install
    path as an argument: another session's probe, or a leftover of ours."""
    me = os.getpid()
    busy = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == me:
            continue
        try:
            with open("/proc/%s/cmdline" % pid, "rb") as handle:
                args = [a.decode("utf-8", "replace") for a in handle.read().split(b"\0") if a]
        except OSError:
            continue
        if not args or os.path.basename(args[0]) in ("bash", "sh", "python3", "python"):
            continue
        if any(a.rstrip("/").endswith("instdir/program") for a in args[1:]):
            busy.append("%s %s" % (pid, " ".join(args)[:160]))
    return busy


def wait_for_quiet(log):
    waited = 0
    while True:
        busy = other_lok_running()
        if not busy:
            if waited:
                log.write("waited %d s for: %s\n" % (waited, busy_seen[-1] if busy_seen else ""))
            return waited
        busy_seen.append("; ".join(busy))
        time.sleep(2)
        waited += 2
        if waited > 1800:
            raise SystemExit("another LOK process has been running for 30 min: %s" % busy)


busy_seen = []


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def gz(src, dst):
    with open(src, "rb") as fin, gzip.GzipFile(dst, "wb", mtime=0) as fout:
        shutil.copyfileobj(fin, fout)


def compact(summary, keep=60):
    """Whole summary for small documents; counts and the first paragraphs otherwise."""
    if summary["paragraphCount"] <= keep:
        return summary
    shapes = {}
    for t in summary["tables"]:
        key = "%dx%d(h%d)" % (t["rows"], t["cols"], t["headerRows"])
        shapes[key] = shapes.get(key, 0) + 1
    return {"paragraphCount": summary["paragraphCount"], "truncatedTo": keep,
            "paragraphs": summary["paragraphs"][:keep], "tableShapes": shapes,
            "links": len(summary["links"]), "images": len(summary["images"])}


def run_one(probe, scratch, out_dir, arm, k, log):
    run_dir = os.path.join(out_dir, arm["id"], "run%d" % k)
    if os.path.exists(os.path.join(run_dir, "summary.json")):
        return
    os.makedirs(run_dir, exist_ok=True)
    work = os.path.join(scratch, arm["id"], "run%d" % k)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.join(work, "profile"))
    os.makedirs(os.path.join(work, "out"))
    doc_rel, position = DOCS[arm["position"]]
    ext = os.path.splitext(doc_rel)[1]
    doc = os.path.join(work, "doc" + ext)
    shutil.copyfile(os.path.join(HERE, doc_rel), doc)
    corpus_file = os.path.join(HERE, "corpus", arm["corpus"] + (".bin" if arm["corpus"].endswith("le") else ".md"))
    env = {"HOME": os.environ["HOME"], "PATH": "/usr/bin:/bin", "LANG": arm["lang"],
           "SAL_USE_VCLPLUGIN": "svp"}
    watchdog = arm.get("watchdog", 20)
    cmd = ["nice", "-n", "10", "timeout", str(max(120, watchdog + 90))]
    if arm["strace"]:
        calls = arm.get("straceCalls", "connect")
        name = "strace-connect.txt" if calls == "connect" else "strace-" + calls.replace(",", "-") + ".txt"
        cmd += ["strace", "-f", "-tt", "-e", "trace=" + calls, "-o", os.path.join(run_dir, name)]
    cmd += [probe, INSTALL, "file://" + os.path.join(work, "profile"), "file://" + doc,
            os.path.join(work, "out"), arm["mime"], corpus_file, position, str(watchdog)]
    waited = wait_for_quiet(log)
    Listener.log = []
    Tarpit.log = []
    started = time.time()
    proc = subprocess.run(cmd, env=env, capture_output=True, cwd=work)
    elapsed = time.time() - started
    with open(os.path.join(run_dir, "stdout.jsonl"), "wb") as handle:
        handle.write(proc.stdout)
    stderr = proc.stderr
    if len(stderr) > 40000:
        stderr = stderr[:20000] + b"\n...[cut %d bytes]...\n" % (len(stderr) - 40000) + stderr[-20000:]
    with open(os.path.join(run_dir, "stderr.txt"), "wb") as handle:
        handle.write(stderr)
    with open(os.path.join(run_dir, "cmd.txt"), "w") as handle:
        handle.write("env -i " + " ".join("%s=%s" % kv for kv in env.items()) + " " +
                     " ".join(cmd).replace(REPO, "<repo>").replace(scratch, "<scratch>") + "\n")
    records = []
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        try:
            records.append(json.loads(line))
        except ValueError:
            records.append({"probe": "unparsed", "line": line[:300]})
    by = {}
    for r in records:
        by.setdefault(r.get("probe"), []).append(r)
    summary = {"arm": arm, "run": k, "returncode": proc.returncode,
               "processSeconds": round(elapsed, 2), "waitedForOtherLokSeconds": waited,
               "corpusSha256": sha(corpus_file), "inputSha256": sha(doc)}
    if "blocked" in by:
        summary["blocked"] = {"step": by["blocked"][0]["step"], "afterMs": by["blocked"][0]["afterMs"],
                              "callbackNames": sorted({c["name"] for c in by["blocked"][0]["callbacks"]})}
    if "opened" in by:
        summary["threadTextEncoding"] = by["opened"][0]["threadTextEncoding"]
    if "position" in by:
        p = by["position"][0]
        summary["positionReadback"] = p["readback"]
        summary["positionReadbackAsExpected"] = p["readback"] == EXPECTED_READBACK[position]
    if "paste" in by:
        summary["pasteReturned"] = by["paste"][0]["returned"]
        summary["pasteCallMs"] = by["paste"][0]["callMs"]
    if "callbacks" in by:
        cbs = by["callbacks"][0]["list"]
        names = {}
        for c in cbs:
            names[c["name"]] = names.get(c["name"], 0) + 1
        core = by["callbacks"][0].get("coreLog", {})
        names["LOK_CALLBACK_CORE_LOG"] = core.get("count", names.get("LOK_CALLBACK_CORE_LOG", 0))
        if not names["LOK_CALLBACK_CORE_LOG"]:
            del names["LOK_CALLBACK_CORE_LOG"]
        summary["callbacks"] = {"listed": len(cbs), "byName": names, "coreLog": core,
                                "duringCall": sum(1 for c in cbs if c["duringCall"]),
                                "lastMs": cbs[-1]["ms"] if cbs else None,
                                "dialogLike": sorted({c["name"] for c in cbs if any(
                                    w in c["name"] for w in ("WINDOW", "JSDIALOG", "ERROR", "DIALOG"))})}
    if "undo-before" in by and "undo-after" in by:
        before = int(by["undo-before"][0]["undo"]["count"] or 0)
        after = int(by["undo-after"][0]["undo"]["count"] or 0)
        try:
            actions = json.loads(by["undo-after"][0]["undo"]["actions"]).get("actions") or []
            comments = [a.get("comment") for a in actions] if isinstance(actions, list) else []
        except ValueError:
            comments = ["(unparsed)"]
        summary["undo"] = {"countBefore": before, "countAfter": after,
                           "newActions": comments[: max(after - before, 0)]}
    if "paint" in by:
        summary["paintMs"] = by["paint"][0]["ms"]
    work_out = os.path.join(work, "out")
    before_f = os.path.join(work_out, "before.fodt")
    after_f = os.path.join(work_out, "after.fodt")
    full = {}
    if os.path.exists(before_f):
        full["before"] = md_structure.summarize(before_f)
        summary["before"] = compact(full["before"])
        gz(before_f, os.path.join(run_dir, "before.fodt.gz"))
    if os.path.exists(after_f):
        full["after"] = md_structure.summarize(after_f)
        summary["after"] = compact(full["after"])
        summary["afterSignatureSha256"] = hashlib.sha256(json.dumps(
            md_structure.signature(full["after"]), ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        summary["afterHuman"] = "\n".join(md_structure.human(full["after"]).splitlines()[:40])
        if not (arm["corpus"] == "M14b" and k > 1):
            gz(after_f, os.path.join(run_dir, "after.fodt.gz"))
        text = "\n".join(p["text"] for p in full["after"]["paragraphs"])
        if arm["corpus"] in EXPECTED_TEXT or arm["corpus"].startswith("M8"):
            wanted = EXPECTED_TEXT.get(arm["corpus"], EXPECTED_TEXT["M8"])
            summary["expectedTextPresent"] = {w: (w in text) for w in wanted}
    if "before" in full:
        sig_before = md_structure.signature(full["before"])
        steps = []
        restored_at = None
        for r in by.get("undo", []):
            f = os.path.join(work_out, "undo-%d.fodt" % r["step"])
            same = os.path.exists(f) and md_structure.signature(md_structure.summarize(f)) == sig_before
            steps.append({"step": r["step"], "countAfterStep": r["countAfterStep"],
                          "sameAsBefore": same, "result": r["result"][:120]})
            if same and restored_at is None:
                restored_at = r["step"]
        summary["undoSteps"] = steps
        summary["undoStepsToRestore"] = restored_at
        if "after" in full:
            summary["afterSameAsBefore"] = md_structure.signature(full["after"]) == sig_before
    if arm["corpus"] == "M11c":
        summary["tarpit"] = [dict(e, dt=round(e["t"] - started, 3)) for e in Tarpit.log]
    if arm["corpus"] == "M11b":
        summary["listenerStartedAt"] = started
        summary["listenerRequests"] = [{"dt": round(r["t"] - started, 3), "path": r["path"],
                                        "userAgent": r["headers"].get("User-Agent")}
                                       for r in Listener.log]
    with open(os.path.join(run_dir, "summary.json"), "w") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=1)
    log.write("%s run%d rc=%s returned=%s callMs=%s undo=%s restore=%s blocked=%s %.1fs\n" % (
        arm["id"], k, proc.returncode, summary.get("pasteReturned"), summary.get("pasteCallMs"),
        summary.get("undo"), summary.get("undoStepsToRestore"), summary.get("blocked"), elapsed))
    log.flush()
    shutil.rmtree(work, ignore_errors=True)


def main(argv):
    probe, scratch, out_dir = argv[1:4]
    prefixes = argv[4:]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", LISTENER_PORT), Listener)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    Tarpit(LISTENER_PORT + 1)
    with open(os.path.join(out_dir, "runner.log"), "a") as log:
        log.write("=== %s start, prefixes=%s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), prefixes))
        for arm in arms():
            if prefixes and not any(arm["id"].startswith(p) for p in prefixes):
                continue
            for k in range(1, arm["runs"] + 1):
                run_one(probe, scratch, out_dir, arm, k, log)
        log.write("=== %s end\n" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
