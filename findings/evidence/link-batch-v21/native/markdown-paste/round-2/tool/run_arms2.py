#!/usr/bin/env python3
"""Run round 2's Markdown-paste arms one process at a time and keep the evidence.

Usage: run_arms2.py PROBE2_BINARY SCRATCH_DIR OUT_DIR [--runs=N] [ARM_ID_PREFIX ...]

  PROBE2_BINARY  md-paste-probe2 compiled from md_paste_probe2.cpp (outside the repo)
  SCRATCH_DIR    per-run profiles and document copies (outside the repo)
  OUT_DIR        round-2/out
  prefixes       run only arms whose id starts with one of them (default: all)

Groups: T1-* (positions round 1 did not measure), T2-* (pastes that may add no
undo action), T3-* (round 2's S/W/H/N corpus pasted at round 1's P1, to check
the md4c classification against what Writer really does).

Every process: its own fresh empty user profile, its own copy of the input
document, `env -i` with HOME, PATH, LANG=zh_TW.UTF-8 and SAL_USE_VCLPLUGIN=svp
only, `nice -n 10`, `timeout`, and the probe's own watchdog (20 s) around every
blocking step. BEFORE each process the runner waits until no other LOK probe
runs (two scans 0.5 s apart): a process whose program name starts with
native-142, f142 or md-paste-probe, a soffice/soffice.bin/oosplash started from
this repo, or any non-shell process given an `.../instdir/program` argument
(round 1's rule). An office process from outside the repo (the owner's desktop
LibreOffice) is not waited for but recorded in summary.json, with the load
average. Every wait is logged with what was running, and its seconds are
stored in the run's summary.json.
A finished run (summary.json present) is not rerun.
"""

import collections
import gzip
import hashlib
import http.server
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROUND1_TOOL = os.path.abspath(os.path.join(HERE, "..", "..", "tool"))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 7))
INSTALL = os.path.join(REPO, "native-lok-26-8/build/instdir/program")
sys.path.insert(0, HERE)
import md_structure  # noqa: E402  (round 2's extended reader)

MD = "text/markdown;charset=utf-8"
ZH = "zh_TW.UTF-8"
LISTENER_PORT = 18765
CLOSER_PORT = 18768

SHIFT, MOD1 = 0x1000, 0x2000
DOWN, UP, LEFT, RIGHT, HOME, END = 1024, 1025, 1026, 1027, 1028, 1029
CH = HOME | MOD1  # Ctrl+Home

R1 = lambda name: os.path.join(ROUND1_TOOL, "inputs", name)  # noqa: E731
R2 = lambda name: os.path.join(HERE, "inputs", name)          # noqa: E731

# name -> document, setup script (once), place script (re-runnable), readback
# mode, expected read-back (None = recorded, not judged), flags, chmod
P4_PLACE = "k%d,k%d,k%d,k%dx6" % (CH, DOWN, HOME, RIGHT)          # round 1's para-middle
HDR_SETUP = "k%d,k%dx5,rbody,u.uno:JumpToHeader,k%dx6,rhdr" % (DOWN, RIGHT, RIGHT)  # 142 place-hdr-click
POS = {
    # Round 1's P1 (document start of the empty template), for T3.
    "P1": (R1("empty-template.odt"), "-", "k%d" % CH, "end", "", "-", None),
    # T1. Ctrl+Home x3 is an absolute anchor from anywhere in a body with one
    # table (cell start, table start, document start: finding 142 item 3).
    "P8": (R2("cells.fodt"), "-", "k%dx3,k%d,k%dx2" % (CH, DOWN, RIGHT), "end", " text", "-", None),
    "P9": (R2("cells.fodt"), "-", "k%dx3,k%dx2,k%d,k%d" % (CH, DOWN, END, RIGHT), "end", "", "-", None),
    "P10": (R2("header-footer.fodt"), HDR_SETUP, "cbody,chdr", "end", " line text", "-", None),
    # Expected read-backs marked (dry run) were learned from out/dry-run/ (one
    # process each) before the counted runs, not predicted.
    "P11": (R2("cells.fodt"), "-", "k%dx3,k%d,k%dx2,k%dx6" % (CH, DOWN, RIGHT, RIGHT | SHIFT),
            "sel", "A1 text\tB1 text\n", "-", None),  # (dry run): a two-cell table selection
    # T2.
    "P4": (R1("positions.fodt"), "-", P4_PLACE, "end", "Beta Gamma", "-", None),
    "SEC": (R2("protected-section.fodt"), "-", "k%dx3,k%d,k%dx6" % (CH, DOWN, RIGHT), "end",
            " locked section", "-", None),
    "SECRANGE": (R2("protected-section.fodt"), "-", "k%dx3,k%dx6,k%dx2" % (CH, RIGHT, DOWN | SHIFT),
                 "sel", "paragraph\nInside locked section\nAfter", "-", None),  # (dry run)
    "CELL": (R2("protected-cell.fodt"), "-", "k%dx3,k%d,k%d,k%d,k%dx6" % (CH, DOWN, END, RIGHT, RIGHT),
             "end", " cell", "-", None),
    "VIEWRO": (R1("positions.fodt"), "-", P4_PLACE, "end", "Beta Gamma", "viewro", None),
    # Controls added after the dry run (the read-only view did not stop paste()):
    # does the same view refuse ordinary typing? The call under test is one typed "x".
    "P4TYPE": (R1("positions.fodt"), "-", P4_PLACE, "end", "Beta Gamma", "typekey", None),
    "VIEWROTYPE": (R1("positions.fodt"), "-", P4_PLACE, "end", "Beta Gamma", "viewro,typekey", None),
    # (dry run) keys do not move the caret in a document opened read-only, so
    # it is placed at the document start, which is where it stays anyway.
    "FILERO": (R1("positions.fodt"), "-", "k%d" % CH, "end", "Start", "-", 0o444),
    "CCDROP": (R2("content-control.fodt"), "-", "k%d,k%dx7" % (CH, RIGHT), "end", "ed here", "-", None),  # (dry run) "R|ed"
    "CCPLAIN": (R2("content-control.fodt"), "-", "k%d,k%d,k%d,k%dx8" % (CH, DOWN, HOME, RIGHT), "end",
                "ain words here", "-", None),  # (dry run) "pl|ain words"
    "CCRICH": (R2("content-control.fodt"), "-", "k%d,k%dx2,k%d,k%dx8" % (CH, DOWN, HOME, RIGHT), "end",
               "ch words here", "-", None),  # (dry run) "ri|ch words"
    "INPUT": (R2("input-field.fodt"), "-", "k%d,k%dx12" % (CH, RIGHT), "end", None, "-", None),
    "PFORM": (R2("protect-form.fodt"), "-", P4_PLACE, "end", "Beta Gamma", "-", None),
    "PFIELDS": (R2("protect-fields.fodt"), "-", "k%d,k%d,k%d,k%dx2,k%d" % (CH, DOWN, HOME, RIGHT, END | SHIFT),
                "sel", None, "-", None),
    "FRAME": (R2("frame-protected.fodt"), "-", "a2385:4970,k%d,k%dx7" % (HOME, RIGHT), "end",
              "frame text", "-", None),
    "HDRSEC": (R2("header-protected-section.fodt"), HDR_SETUP, "cbody,chdr", "end", " line text", "-", None),
}


def corpus_path(name):
    for base in (os.path.join(HERE, "corpus"), os.path.join(ROUND1_TOOL, "corpus")):
        path = os.path.join(base, name + ".md")
        if os.path.exists(path):
            return path
    raise SystemExit("no corpus item " + name)


def arms():
    out = []

    def add(arm_id, pos, corpus, runs=3, note="", mime=MD):
        out.append({"id": arm_id, "position": pos, "corpus": corpus, "mime": mime, "lang": ZH,
                    "runs": runs, "note": note})

    # T1: spec 9.12 / opus S14.
    for pos in ("P8", "P9", "P10", "P11"):
        for m in ("M1", "M2", "M4", "M5", "M8"):
            add("T1-%s-%s" % (pos, m), pos, m)
    # T2: spec 9.4. M2 everywhere; M1 too where the content could matter.
    add("T2-ctl-normal-M2", "P4", "M2", note="positive control: a normal paste must change the undo payload")
    add("T2-ref-empty-M13", "P4", "M13", note="reference: round 1's empty input (payload changes, document does not)")
    # PFORM and PFIELDS were dropped after the dry run: the fixtures'
    # office:settings did not take effect (the saved before.fodt has
    # ProtectForm/ProtectFields false), so those arms would not test them.
    for pos in ("SEC", "SECRANGE", "CELL", "VIEWRO", "FILERO", "CCDROP", "CCPLAIN", "CCRICH", "INPUT",
                "FRAME", "HDRSEC"):
        add("T2-%s-M2" % pos.lower(), pos, "M2")
    add("T2-input-M1", "INPUT", "M1")
    add("T2-ctl-typekey", "P4TYPE", "M2", note="control: one typed x in a normal view must change the document")
    add("T2-viewro-typekey", "VIEWROTYPE", "M2", note="does the read-only view refuse typing at all?")
    # Added after the counted runs: the input-field paste corrupted the text and
    # one Undo did not restore it. Is that Markdown's, or does today's plain-text
    # paste (Ctrl+V's flavour, probe_engine.cpp hard-codes text/plain) do it too?
    add("T2-input-plain-M2", "INPUT", "M2", mime="text/plain;charset=utf-8",
        note="control: the same position and bytes as text/plain")
    add("T2-ccrich-M1", "CCRICH", "M1")
    # T3: the round-2 corpus at P1, plus round 1's M10/M11b/M13 for comparison
    # (those three already ran in round 1 at P1; not rerun).
    for name in sorted(os.listdir(os.path.join(HERE, "corpus"))):
        add("T3-P1-" + name[:-3], "P1", name[:-3])
    return out


class Listener(http.server.BaseHTTPRequestHandler):
    log = []

    def _record(self):
        Listener.log.append({"t": time.time(), "method": self.command, "path": self.path,
                             "userAgent": self.headers.get("User-Agent")})

    def _log(self):
        self._record()
        self.send_response(404)
        self.end_headers()

    def _unsupported(self):
        # Round 1's listener had no do_OPTIONS, so http.server answered 501;
        # keep that answer (WebDAV asks OPTIONS first), but log the request.
        self._record()
        self.send_error(501, "Unsupported method (%r)" % self.command)

    do_GET = do_HEAD = _log  # noqa: N815
    do_OPTIONS = do_PROPFIND = _unsupported  # noqa: N815

    def log_message(self, *args):
        pass


class Closer:
    """Accepts on 127.0.0.1/localhost:CLOSER_PORT, logs the first bytes, closes."""
    log = []

    def __init__(self, port):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", port))
        self.sock.listen(16)
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        while True:
            conn, _ = self.sock.accept()
            conn.settimeout(1.0)
            try:
                data = conn.recv(64)
            except OSError:
                data = b""
            Closer.log.append({"t": time.time(), "event": "accept", "firstBytesHex": data[:8].hex()})
            conn.close()


PROGRAM_PREFIXES = ("native-142", "f142", "md-paste-probe")
OFFICE_NAMES = ("soffice", "soffice.bin", "oosplash")


def _scan():
    """(probes, other offices): LOK probe processes, and office processes that
    are not this repo's (the owner's desktop LibreOffice)."""
    me = os.getpid()
    busy, offices = [], []
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == me:
            continue
        try:
            with open("/proc/%s/cmdline" % pid, "rb") as handle:
                args = [a.decode("utf-8", "replace") for a in handle.read().split(b"\0") if a]
        except OSError:
            continue
        if not args:
            continue
        prog = os.path.basename(args[0])
        if prog in ("bash", "sh", "python3", "python", "pgrep", "timeout", "nice"):
            continue
        line = "%s %s" % (pid, " ".join(args)[:160])
        if prog in OFFICE_NAMES:
            # Changed after the dry run: soffice counts as a probe only when it
            # runs from this repo's installs. At 15:45:53 the owner opened the
            # desktop LibreOffice (/opt/libreoffice26.8) on a document of their
            # own; it is not a probe, and waiting on it would wait for as long
            # as the owner works. It is recorded per run instead.
            (busy if args[0].startswith(REPO) else offices).append(line)
        elif prog.startswith(PROGRAM_PREFIXES) or any(a.rstrip("/").endswith("instdir/program") for a in args[1:]):
            busy.append(line)
    return busy, offices


def other_lok_running():
    return _scan()[0]


def wait_for_quiet(log):
    """Quiet = two scans 0.5 s apart that both find no probe (finding 142's
    runner starts its next process within a fraction of a second, and it waits
    for ours, so we only start in a real gap)."""
    seen = None
    start = time.time()
    while True:
        busy = other_lok_running()
        if not busy:
            time.sleep(0.5)
            busy = other_lok_running()
            if not busy:
                waited = time.time() - start
                if seen:
                    log.write("  waited %.0f s for: %s\n" % (waited, seen))
                    log.flush()
                return round(waited, 1)
        seen = "; ".join(busy)
        time.sleep(0.5)
        if time.time() - start > 3600:
            raise SystemExit("another LOK process has been running for 60 min: %s" % busy)


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def gz(src, dst):
    with open(src, "rb") as fin, gzip.GzipFile(dst, "wb", mtime=0) as fout:
        shutil.copyfileobj(fin, fout)


STRUCT_TAGS = ("text:p", "text:h", "text:list-item", "table:table", "table:table-row", "table:table-cell",
               "draw:frame", "draw:image", "text:section", "text:a", "loext:content-control",
               "text:text-input")
NSMAP = {"text": md_structure.NS["text"], "table": md_structure.NS["table"],
         "draw": md_structure.NS["draw"], "loext": md_structure.NS["loext"],
         "office": md_structure.NS["office"]}


def fingerprint(path):
    """A second, reader-independent change detector: every text node under
    office:body and office:master-styles, plus counts of the structural tags."""
    root = ET.parse(path).getroot()
    texts = []
    counts = collections.Counter()
    for section in ("body", "master-styles"):
        for node in root.iter("{%s}%s" % (NSMAP["office"], section)):
            texts.append("".join(node.itertext()))
            for tag in STRUCT_TAGS:
                prefix, local = tag.split(":")
                counts[tag] += sum(1 for _ in node.iter("{%s}%s" % (NSMAP[prefix], local)))
    blob = json.dumps({"text": texts, "counts": dict(sorted(counts.items()))}, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest(), dict(sorted(counts.items()))


def sig_sha(summary):
    return hashlib.sha256(json.dumps(md_structure.signature(summary), ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()


def run_one(probe, scratch, out_dir, arm, k, log):
    run_dir = os.path.join(out_dir, arm["id"], "run%d" % k)
    if os.path.exists(os.path.join(run_dir, "summary.json")):
        return
    os.makedirs(run_dir, exist_ok=True)
    work = os.path.join(scratch, arm["id"], "run%d" % k)
    if os.path.exists(work):
        for root, dirs, files in os.walk(work):
            for name in dirs + files:
                os.chmod(os.path.join(root, name), 0o755)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.join(work, "profile"))
    os.makedirs(os.path.join(work, "out"))
    doc_src, setup, place, readback_mode, expected, flags, mode = POS[arm["position"]]
    doc = os.path.join(work, "doc" + os.path.splitext(doc_src)[1])
    shutil.copyfile(doc_src, doc)
    if mode is not None:
        os.chmod(doc, mode)
    corpus_file = corpus_path(arm["corpus"])
    env = {"HOME": os.environ["HOME"], "PATH": "/usr/bin:/bin", "LANG": arm["lang"],
           "SAL_USE_VCLPLUGIN": "svp"}
    cmd = ["nice", "-n", "10", "timeout", "120", probe, INSTALL, "file://" + os.path.join(work, "profile"),
           "file://" + doc, os.path.join(work, "out"), arm["mime"], corpus_file, setup, place,
           readback_mode, flags, "20"]
    waited = wait_for_quiet(log)
    with open("/proc/loadavg") as handle:
        loadavg = handle.read().split()[:3]
    other_offices = _scan()[1]
    Listener.log = []
    Closer.log = []
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
                     " ".join("'%s'" % c if (" " in c or not c) else c for c in cmd)
                     .replace(REPO, "<repo>").replace(scratch, "<scratch>") +
                     ("\n# document mode %o before load\n" % mode if mode is not None else "\n"))
    records = []
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        try:
            records.append(json.loads(line))
        except ValueError:
            records.append({"probe": "unparsed", "line": line[:300]})
    by = {}
    for r in records:
        by.setdefault(r.get("probe"), []).append(r)
    summary = {"arm": arm, "run": k, "returncode": proc.returncode, "processSeconds": round(elapsed, 2),
               "waitedForOtherLokSeconds": waited, "loadavgAtStart": loadavg,
               "nonRepoOfficeProcessesAtStart": other_offices, "corpusSha256": sha(corpus_file),
               "inputSha256": sha(doc_src), "positionSpec": {
                   "document": os.path.relpath(doc_src, REPO), "setup": setup, "place": place,
                   "readback": readback_mode, "expectedReadback": expected, "flags": flags,
                   "chmod": oct(mode) if mode is not None else None}}
    if "error" in by:
        summary["probeError"] = by["error"]
    if "blocked" in by:
        summary["blocked"] = {"step": by["blocked"][0]["step"], "afterMs": by["blocked"][0]["afterMs"],
                              "callbackNames": sorted({c["name"] for c in by["blocked"][0]["callbacks"]})}
    if "opened" in by:
        summary["threadTextEncoding"] = by["opened"][0]["threadTextEncoding"]
        summary["readOnlyAtOpen"] = by["opened"][0]["readOnly"]
    if "setup" in by:
        summary["setupSteps"] = by["setup"][0]["steps"]
    if "position" in by:
        p = by["position"][0]
        summary["positionReadback"] = p["readback"]
        summary["positionReadbackAsExpected"] = (p["readback"] == expected) if expected is not None else None
        summary["cursorAtReadback"] = p["cursorAtReadback"]
        summary["cursorAtPaste"] = p["cursorAtPaste"]
        summary["selectionAtPaste"] = p["selectionAtPaste"]
        summary["selectionTypeAtPaste"] = p["selectionTypeAtPaste"]
    if "paste" in by:
        summary["pasteReturned"] = by["paste"][0]["returned"]
        summary["pasteCallMs"] = by["paste"][0]["callMs"]
        summary["pasteGetError"] = by["paste"][0]["getError"]
    if "callbacks" in by:
        cbs = by["callbacks"][0]["list"]
        names = {}
        for c in cbs:
            names[c["name"]] = names.get(c["name"], 0) + 1
        core = by["callbacks"][0].get("coreLog", {})
        if core.get("count"):
            names["LOK_CALLBACK_CORE_LOG"] = core["count"]
        summary["callbacks"] = {"listed": len(cbs), "byName": names, "coreLog": core,
                                "duringCall": sum(1 for c in cbs if c["duringCall"]),
                                "lastMs": cbs[-1]["ms"] if cbs else None,
                                "dialogLike": sorted({c["name"] for c in cbs if any(
                                    w in c["name"] for w in ("WINDOW", "JSDIALOG", "ERROR", "DIALOG", "INFOBAR"))}),
                                "modifiedStatus": [c["payload"] for c in cbs
                                                   if c["payload"].startswith(".uno:ModifiedStatus=")]}
    if "state-before" in by and "state-after" in by:
        sb = by["state-before"][0]["state"]
        sa = by["state-after"][0]["state"]
        before = int(sb["undoCount"] or 0)
        after = int(sa["undoCount"] or 0)
        try:
            actions = json.loads(sa["undoPayload"]).get("actions") or []
            comments = [a.get("comment") for a in actions] if isinstance(actions, list) else []
        except ValueError:
            comments = ["(unparsed)"]
        summary["undo"] = {"countBefore": before, "countAfter": after,
                           "newActions": comments[: max(after - before, 0)],
                           "payloadBefore": sb["undoPayload"], "payloadAfter": sa["undoPayload"],
                           "payloadChanged": sb["undoPayload"] != sa["undoPayload"],
                           "lastUndoStateBefore": sb["lastUndoState"], "lastUndoStateAfter": sa["lastUndoState"]}
        summary["readOnlyBefore"] = sb["readOnly"]
        summary["pasteStateBefore"] = sb["lastPasteState"]
        summary["pasteStateAfter"] = sa["lastPasteState"]
        summary["selectionAfter"] = sa["selection"]
    if "paint" in by:
        summary["paintMs"] = by["paint"][0]["ms"]
    work_out = os.path.join(work, "out")
    before_f = os.path.join(work_out, "before.fodt")
    after_f = os.path.join(work_out, "after.fodt")
    full = {}
    if os.path.exists(before_f):
        full["before"] = md_structure.summarize(before_f)
        summary["beforeHuman"] = "\n".join(md_structure.human(full["before"]).splitlines()[:40])
        summary["beforeFingerprint"], summary["beforeTagCounts"] = fingerprint(before_f)
        gz(before_f, os.path.join(run_dir, "before.fodt.gz"))
    if os.path.exists(after_f):
        full["after"] = md_structure.summarize(after_f)
        summary["afterSignatureSha256"] = sig_sha(full["after"])
        summary["afterHuman"] = "\n".join(md_structure.human(full["after"]).splitlines()[:60])
        summary["afterFingerprint"], summary["afterTagCounts"] = fingerprint(after_f)
        summary["afterImages"] = [{"paragraph": i["paragraph"], "href": (i.get("href") or "")[:120],
                                   "embedded": i.get("embedded")} for i in full["after"]["images"]]
        summary["afterParagraphCount"] = full["after"]["paragraphCount"]
        gz(after_f, os.path.join(run_dir, "after.fodt.gz"))
    if "before" in full:
        sig_before = md_structure.signature(full["before"])
        steps = []
        restored_at = None
        for r in by.get("undo", []):
            f = os.path.join(work_out, "undo-%d.fodt" % r["step"])
            same = os.path.exists(f) and md_structure.signature(md_structure.summarize(f)) == sig_before
            same_fp = os.path.exists(f) and fingerprint(f)[0] == summary["beforeFingerprint"]
            steps.append({"step": r["step"], "countAfterStep": r["countAfterStep"], "sameAsBefore": same,
                          "sameFingerprintAsBefore": same_fp, "result": r["result"][:120]})
            if same and same_fp and restored_at is None:
                restored_at = r["step"]
            if os.path.exists(f) and not (same and same_fp):
                gz(f, os.path.join(run_dir, "undo-%d.fodt.gz" % r["step"]))  # kept: did not restore
        summary["undoSteps"] = steps
        summary["undoStepsToRestore"] = restored_at
        if "after" in full:
            summary["afterSameAsBefore"] = md_structure.signature(full["after"]) == sig_before
            summary["afterSameFingerprintAsBefore"] = summary["afterFingerprint"] == summary["beforeFingerprint"]
    summary["listenerRequests"] = [{"dt": round(r["t"] - started, 3), "method": r["method"], "path": r["path"],
                                    "userAgent": r["userAgent"]} for r in Listener.log]
    summary["closerEvents"] = [{"dt": round(e["t"] - started, 3), "event": e["event"],
                                "firstBytesHex": e["firstBytesHex"]} for e in Closer.log]
    with open(os.path.join(run_dir, "summary.json"), "w") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=1)
    u = summary.get("undo", {})
    log.write("%s run%d rc=%s returned=%s callMs=%s undo=%s->%s payloadChanged=%s docChanged=%s/%s "
              "readback=%r ok=%s restore=%s blocked=%s http=%d close=%d wait=%.0fs %.1fs\n" % (
                  arm["id"], k, proc.returncode, summary.get("pasteReturned"), summary.get("pasteCallMs"),
                  u.get("countBefore"), u.get("countAfter"), u.get("payloadChanged"),
                  None if "afterSameAsBefore" not in summary else not summary["afterSameAsBefore"],
                  None if "afterSameFingerprintAsBefore" not in summary else not summary["afterSameFingerprintAsBefore"],
                  summary.get("positionReadback"), summary.get("positionReadbackAsExpected"),
                  summary.get("undoStepsToRestore"), summary.get("blocked"), len(Listener.log),
                  len(Closer.log), waited, elapsed))
    log.flush()
    for root, dirs, files in os.walk(work):
        for name in dirs + files:
            try:
                os.chmod(os.path.join(root, name), stat.S_IRWXU)
            except OSError:
                pass
    shutil.rmtree(work, ignore_errors=True)


def main(argv):
    probe, scratch, out_dir = argv[1:4]
    runs_override = [int(a.split("=", 1)[1]) for a in argv[4:] if a.startswith("--runs=")]
    prefixes = [a for a in argv[4:] if not a.startswith("--runs=")]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", LISTENER_PORT), Listener)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    Closer(CLOSER_PORT)
    with open(os.path.join(out_dir, "runner.log"), "a") as log:
        log.write("=== %s start, prefixes=%s, probe sha256 %s\n" % (
            time.strftime("%Y-%m-%dT%H:%M:%S%z"), prefixes, sha(probe)))
        total_wait = 0.0
        for arm in arms():
            if prefixes and not any(arm["id"].startswith(p) for p in prefixes):
                continue
            for k in range(1, (runs_override[0] if runs_override else arm["runs"]) + 1):
                before = os.path.exists(os.path.join(out_dir, arm["id"], "run%d" % k, "summary.json"))
                run_one(probe, scratch, out_dir, arm, k, log)
                if not before:
                    with open(os.path.join(out_dir, arm["id"], "run%d" % k, "summary.json")) as handle:
                        total_wait += json.load(handle).get("waitedForOtherLokSeconds", 0)
        log.write("=== %s end, waited %.0f s in total this invocation\n" % (
            time.strftime("%Y-%m-%dT%H:%M:%S%z"), total_wait))
    server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
