#!/usr/bin/env python3
"""SPEC-M4-ods-in-nextcloud §6 (D5-A): does Firefox keep a 47,987,197-byte gzip
response -- the a11y+calc core's `probe.wasm`, gzip -9 -- in its HTTP cache?

X1 (`probe_m3_browser_cache.py`, 2026-09-28) measured 45,000,000 encoded bytes
kept and 60,000,000 not, on Firefox 156, through ddev.  The viewer's wasm falls
in the interval nobody measured, and the packager's K0-5 cap (45,000,000) is
that X1 point.  This is X1 with the server swapped: no ddev, a small local server
on 127.0.0.1 that sends what X1's lab sent (`Cache-Control: max-age=15778463,
immutable`, `Content-Type: application/wasm`, `Content-Encoding: gzip` on the
encoded file) plus the validators Apache adds (ETag, Last-Modified), and logs
every request it answers -- that log is the record of "did the second fetch
reach the server".

Files, each fetched as `<name>?v=1` (`rand-*` are random bytes, incompressible):
  must be kept      ctrl-1k, ctrl-5m, rand-20m, rand-45m   (X1: kept)
  must be refetched rand-60m                                (X1: not kept)
  the subject       enc-gzip-v14.wasm  (must decode to 135,237,060 bytes)
  locating the cap  rand-48m, rand-50m, rand-52m, rand-52.4m (51,200 KiB), rand-53m

Two runs, each with a NEW Firefox profile under build/ (on /home, as X1's
firefox-home).  A run: one same-origin page fetches every file, a navigation to
a new document, the same fetches again.  The judge (a pure function, --selftest)
decides the cap as the spec pins it (§6.3).

  probe_gzip_retention_firefox.py --selftest
  probe_gzip_retention_firefox.py
Report: findings/evidence/m4-ods/d5-gzip-retention/report-<UTC>.json
"""
from __future__ import annotations

import argparse
import copy
import email.utils
import gzip
import hashlib
import http.server
import json
import os
import shutil
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

WASM = PROJECT / "dist" / "profiles" / "e2-editor-v14" / "probe.wasm"
WASM_BYTES = 135_237_060
EVIDENCE = PROJECT.parent / "findings" / "evidence" / "m4-ods" / "d5-gzip-retention"
SUBJECT = "enc-gzip-v14.wasm"
KEPT_CONTROLS = {"ctrl-1k.wasm": 1_000, "ctrl-5m.wasm": 5_000_000,
                 "rand-20m.wasm": 20_000_000, "rand-45m.wasm": 45_000_000}
REFETCHED_CONTROLS = {"rand-60m.wasm": 60_000_000}
LOCATORS = {"rand-48m.wasm": 48_000_000, "rand-50m.wasm": 50_000_000,
            "rand-52m.wasm": 52_000_000, "rand-52.4m.wasm": 52_428_800,
            "rand-53m.wasm": 53_000_000}
ORDER = [*KEPT_CONTROLS, SUBJECT, *LOCATORS, *REFETCHED_CONTROLS]
RUNS = 2
PAGE = b"<!doctype html><meta charset=utf-8><title>gzip retention lab</title><p>lab</p>"
FETCH = """(() => { (async () => {
  const out = [];
  for (const name of NAMES) {
    const started = performance.now();
    try {
      const response = await fetch(`/lab/${name}?v=1`);
      const body = await response.arrayBuffer();
      out.push({name, status: response.status, decodedBytes: body.byteLength,
                ms: Math.round(performance.now() - started)});
    } catch (error) {
      out.push({name, error: String(error)});
    }
  }
  window.__cachelab = out;
})(); return true; })()"""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------- the lab ----
def make_lab(lab: Path) -> list[dict[str, Any]]:
    lab.mkdir(parents=True)
    for name, size in {**KEPT_CONTROLS, **LOCATORS, **REFETCHED_CONTROLS}.items():
        with (lab / name).open("wb") as out:
            left = size
            while left:
                step = min(left, 1_000_000)
                out.write(os.urandom(step))
                left -= step
    with WASM.open("rb") as source, (lab / SUBJECT).open("wb") as raw, \
            gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as out:
        shutil.copyfileobj(source, out, 1 << 20)
    return [{"name": name, "bytesOnWire": (lab / name).stat().st_size, "sha256": sha256_file(lab / name),
             "encoding": "gzip" if name == SUBJECT else None} for name in ORDER]


class LabServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, lab: Path):
        self.lab = lab
        self.log: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        super().__init__(("127.0.0.1", 0), LabHandler)

    def record(self, entry: dict[str, Any]) -> None:
        with self.lock:
            entry["seq"] = len(self.log)
            self.log.append(entry)

    def since(self, mark: int) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(e) for e in self.log[mark:]]

    def offset(self) -> int:
        with self.lock:
            return len(self.log)


class LabHandler(http.server.BaseHTTPRequestHandler):
    server: LabServer

    def log_message(self, *args: Any) -> None:   # the server's own log is the record
        pass

    def do_GET(self) -> None:  # noqa: N802
        parts = urlsplit(self.path)
        entry = {"path": parts.path, "query": parts.query,
                 "acceptEncoding": self.headers.get("Accept-Encoding"),
                 "conditional": {k: self.headers.get(k) for k in ("If-None-Match", "If-Modified-Since")
                                 if self.headers.get(k)}}
        if parts.path == "/page.html":
            self._send(200, PAGE, {"Content-Type": "text/html; charset=utf-8",
                                   "Cache-Control": "no-store"}, entry)
            return
        name = parts.path.removeprefix("/lab/")
        path = self.server.lab / name
        if not parts.path.startswith("/lab/") or "/" in name or not path.is_file():
            self._send(404, b"not found", {"Content-Type": "text/plain"}, entry)
            return
        stat = path.stat()
        headers = {
            "Content-Type": "application/wasm",
            "Cache-Control": "max-age=15778463, immutable",
            "ETag": f'"{stat.st_size:x}-{int(stat.st_mtime):x}"',
            "Last-Modified": email.utils.formatdate(stat.st_mtime, usegmt=True),
        }
        if name == SUBJECT:
            headers["Content-Encoding"] = "gzip"
        self._send(200, path, headers, entry)

    def _send(self, status: int, body: bytes | Path, headers: dict[str, str], entry: dict[str, Any]) -> None:
        size = body.stat().st_size if isinstance(body, Path) else len(body)
        self.send_response(status)
        for key, value in {**headers, "Content-Length": str(size)}.items():
            self.send_header(key, value)
        self.end_headers()
        sent = 0
        try:
            if isinstance(body, Path):
                with body.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1 << 20), b""):
                        self.wfile.write(chunk)
                        sent += len(chunk)
            else:
                self.wfile.write(body)
                sent = size
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.server.record({**entry, "status": status, "sent": sent})


# ---------------------------------------------------------------- the judge --
def run_verdict(run: dict[str, Any], files: dict[str, int]) -> dict[str, Any]:
    """Per file: was the first fetch served whole, and did the second reach the server."""
    first_page = {row.get("name"): row for row in (run.get("first") or {}).get("page") or []}
    first_server = {}
    for hit in (run.get("first") or {}).get("server") or []:
        first_server.setdefault(hit["name"], []).append(hit)
    second_server = {}
    for hit in (run.get("second") or {}).get("server") or []:
        second_server.setdefault(hit["name"], []).append(hit)
    rows = {}
    for name, wire in files.items():
        page = first_page.get(name) or {}
        served = [h for h in first_server.get(name, []) if h["status"] == 200 and h["sent"] == wire]
        rows[name] = {"bytesOnWire": wire, "firstServedWhole": bool(served),
                      "firstDecodedBytes": page.get("decodedBytes"), "firstStatus": page.get("status"),
                      "kept": not second_server.get(name)}
    problems = []
    for name, row in rows.items():
        if not row["firstServedWhole"] or row["firstStatus"] != 200:
            problems.append(f"{name}: the first fetch was not served whole")
    for name in KEPT_CONTROLS:
        if name in rows and not rows[name]["kept"]:
            problems.append(f"{name}: a must-keep control was refetched")
    for name in REFETCHED_CONTROLS:
        if name in rows and rows[name]["kept"]:
            problems.append(f"{name}: the must-refetch control was kept")
    subject = rows.get(SUBJECT) or {}
    if subject.get("firstDecodedBytes") != WASM_BYTES:
        problems.append(f"{SUBJECT} decoded to {subject.get('firstDecodedBytes')}, want {WASM_BYTES}")
    if run.get("fatal"):
        problems.append("the run died: " + run["fatal"].strip().splitlines()[-1])
    return {"rows": rows, "valid": not problems, "problems": problems}


def judge(report: dict[str, Any]) -> dict[str, Any]:
    """SPEC-M4 §6.3.  The cap is the largest encoded size kept in EVERY valid run,
    provided every run is valid, the runs agree file by file, and nothing larger
    was kept while something smaller was refetched."""
    files = {f["name"]: f["bytesOnWire"] for f in report.get("files") or []}
    runs = [run_verdict(run, files) for run in report.get("runs") or []]
    reasons = []
    if len(runs) != RUNS:
        reasons.append(f"{len(runs)} runs, want {RUNS}")
    if not files:
        reasons.append("no files")
    for index, verdict in enumerate(runs):
        reasons += [f"run {index}: {p}" for p in verdict["problems"]]
    if runs and not reasons:
        kept_sets = [{n for n, row in v["rows"].items() if row["kept"]} for v in runs]
        if any(s != kept_sets[0] for s in kept_sets):
            reasons.append("the runs disagree: " + json.dumps([sorted(s) for s in kept_sets]))
    if runs and not reasons:
        kept = kept_sets[0]
        ordered = sorted(files.items(), key=lambda item: item[1])
        largest_kept = max((size for name, size in ordered if name in kept), default=None)
        smallest_refetched = min((size for name, size in ordered if name not in kept), default=None)
        if largest_kept is not None and smallest_refetched is not None and largest_kept > smallest_refetched:
            reasons.append(f"not monotonic: {largest_kept} kept, {smallest_refetched} refetched")
    if reasons:
        return {"outcome": "NOT-ESTABLISHED", "reasons": reasons, "gzipCap": None,
                "subjectKept": None, "runs": runs,
                "consequence": "D5-B (spec §6.4): no gzip cap, L-ods-gzip-fallback-uncached-in-firefox-nozstd"}
    subject_kept = SUBJECT in kept
    cap = largest_kept if subject_kept else 45_000_000
    return {"outcome": "ESTABLISHED", "reasons": [], "gzipCap": cap, "subjectKept": subject_kept,
            "largestKept": largest_kept, "smallestRefetched": smallest_refetched, "runs": runs,
            "consequence": (f"gzip cap {cap} (spec §6.3)" if subject_kept else
                            "the subject is not kept: the gzip cap stays 45,000,000 and the viewer's gzip "
                            "is not served to requests without zstd (spec §6.3)")}


def selftest() -> int:
    sizes = {**KEPT_CONTROLS, SUBJECT: 47_987_197, **LOCATORS, **REFETCHED_CONTROLS}

    def good_run(kept_up_to: int) -> dict[str, Any]:
        page = [{"name": n, "status": 200, "decodedBytes": WASM_BYTES if n == SUBJECT else s}
                for n, s in sizes.items()]
        first = [{"name": n, "status": 200, "sent": s} for n, s in sizes.items()]
        second = [{"name": n, "status": 200, "sent": s} for n, s in sizes.items() if s > kept_up_to]
        return {"first": {"page": page, "server": first}, "second": {"server": second}}

    base = {"files": [{"name": n, "bytesOnWire": s} for n, s in sizes.items()],
            "runs": [good_run(52_000_000), good_run(52_000_000)]}

    def second(report, index):
        return report["runs"][index]["second"]["server"]

    cases = [
        ("control: cap at 52,000,000", lambda b: None,
         lambda v: v["outcome"] == "ESTABLISHED" and v["gzipCap"] == 52_000_000 and v["subjectKept"]),
        ("no runs", lambda b: b.update(runs=[]), lambda v: v["outcome"] == "NOT-ESTABLISHED"),
        ("one run only", lambda b: b["runs"].pop(), lambda v: v["outcome"] == "NOT-ESTABLISHED"),
        ("a must-keep control refetched",
         lambda b: second(b, 0).append({"name": "ctrl-5m.wasm", "status": 200, "sent": 5_000_000}),
         lambda v: v["outcome"] == "NOT-ESTABLISHED"),
        ("the must-refetch control kept",
         lambda b: b["runs"][1]["second"].update(server=[h for h in second(b, 1) if h["name"] != "rand-60m.wasm"]),
         lambda v: v["outcome"] == "NOT-ESTABLISHED"),
        ("the subject decoded short",
         lambda b: b["runs"][0]["first"]["page"][4].update(decodedBytes=47_987_197),
         lambda v: v["outcome"] == "NOT-ESTABLISHED"),
        ("a first fetch cut short",
         lambda b: b["runs"][0]["first"]["server"][6].update(sent=1),
         lambda v: v["outcome"] == "NOT-ESTABLISHED"),
        ("the runs disagree on rand-52m",
         lambda b: second(b, 1).append({"name": "rand-52m.wasm", "status": 200, "sent": 52_000_000}),
         lambda v: v["outcome"] == "NOT-ESTABLISHED"),
        ("not monotonic (rand-50m refetched, rand-52m kept), in both runs",
         lambda b: [second(b, i).append({"name": "rand-50m.wasm", "status": 200, "sent": 50_000_000})
                    for i in range(2)],
         lambda v: v["outcome"] == "NOT-ESTABLISHED"),
        ("the subject refetched in both runs -> cap stays 45,000,000",
         lambda b: b.update(runs=[good_run(45_000_000), good_run(45_000_000)]),
         lambda v: v["outcome"] == "ESTABLISHED" and v["gzipCap"] == 45_000_000 and not v["subjectKept"]),
        ("a run that died",
         lambda b: b["runs"][0].update(fatal="Traceback\nRuntimeError: geckodriver is unavailable"),
         lambda v: v["outcome"] == "NOT-ESTABLISHED"),
    ]
    passed = 0
    for label, edit, want in cases:
        broken = copy.deepcopy(base)
        edit(broken)
        verdict = judge(broken)
        ok = want(verdict)
        passed += ok
        print(("PASS " if ok else "FAIL ") + label + f"  -> {verdict['outcome']} cap={verdict['gzipCap']}"
              + (f" {verdict['reasons'][:1]}" if verdict["reasons"] else ""))
    print(f"selftest: {passed}/{len(cases)}")
    return 0 if passed == len(cases) else 1


# ------------------------------------------------------------- the browser --
def read_pref(session, name: str) -> Any:
    """The pref as Firefox holds it, read in chrome context; a failure is recorded."""
    try:
        session.command("POST", "/moz/context", {"context": "chrome"})
        try:
            return session.execute(
                "const n = arguments[0]; const t = Services.prefs.getPrefType(n);"
                "return t === Services.prefs.PREF_INT ? Services.prefs.getIntPref(n)"
                " : t === Services.prefs.PREF_BOOL ? Services.prefs.getBoolPref(n)"
                " : t === Services.prefs.PREF_STRING ? Services.prefs.getStringPref(n) : null;", [name])
        finally:
            session.command("POST", "/moz/context", {"context": "content"})
    except Exception as error:  # noqa: BLE001 -- recorded, not hidden
        return {"error": f"{type(error).__name__}: {error}"}


def run_profile(index: int, server: LabServer, base: str, scratch: Path) -> dict[str, Any]:
    from r7_support import evaluate                     # noqa: E402
    from run_browser_probe import FirefoxSession        # noqa: E402
    from run_e2_c_page_smoke import navigate            # noqa: E402

    profile = scratch / f"profile-{index}"
    record: dict[str, Any] = {"index": index, "profileParent": str(scratch),
                              "profileDiskFree": shutil.disk_usage(scratch).free}
    try:
        session = FirefoxSession("warm", profile_dir=profile)
        record["version"] = session.version
        try:
            record["prefs"] = {name: read_pref(session, name) for name in (
                "browser.cache.disk.max_entry_size", "browser.cache.disk.capacity",
                "browser.cache.disk.smart_size.enabled", "browser.cache.disk.enable",
                "browser.cache.memory.max_entry_size", "network.http.accept-encoding")}
            script = FETCH.replace("NAMES", json.dumps(ORDER))
            for round_ in ("first", "second"):
                # A new document before each round, as reopening the viewer is:
                # a fetch repeated inside one document can be answered by that
                # document's memory cache (X1's instrument error `…160045`).
                navigate(session, base + ("/page.html" if round_ == "first" else "/page.html?again=1"),
                         timeout=60)
                mark = server.offset()
                evaluate(session, script)
                deadline = time.monotonic() + 600
                result = None
                while time.monotonic() < deadline:
                    result = evaluate(session, "(() => window.__cachelab || null)()")
                    if result:
                        break
                    time.sleep(0.5)
                time.sleep(1)
                hits = [h for h in server.since(mark) if h["path"].startswith("/lab/")]
                record[round_] = {"page": result, "server": [
                    {"name": h["path"].removeprefix("/lab/"), "status": h["status"], "sent": h["sent"],
                     "acceptEncoding": h["acceptEncoding"], "conditional": h["conditional"]} for h in hits]}
        finally:
            session.close()
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()

    started = utc_now()
    scratch = PROJECT / "build" / f"gzip-retention-{started}"
    if scratch.exists():
        raise SystemExit(f"{scratch} exists")
    report: dict[str, Any] = {"schema": "m4-gzip-retention/1", "spec": "specs/SPEC-M4-ods-in-nextcloud.md §6",
                              "startedAt": started, "probe": sha256_file(Path(__file__)),
                              "wasm": {"path": str(WASM.relative_to(PROJECT)), "bytes": WASM.stat().st_size,
                                       "sha256": sha256_file(WASM)}}
    server = None
    try:
        report["files"] = make_lab(scratch / "lab")
        server = LabServer(scratch / "lab")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        report["baseUrl"] = base
        report["runs"] = [run_profile(index, server, base, scratch) for index in range(RUNS)]
        report["serverLog"] = server.since(0)
    finally:
        if server is not None:
            server.shutdown()
        shutil.rmtree(scratch, ignore_errors=True)
        report["labRemoved"] = not scratch.exists()
    report["completedAt"] = utc_now()
    verdict = judge(report)
    report["verdict"] = {k: v for k, v in verdict.items() if k != "runs"}
    report["perRun"] = verdict["runs"]
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"report-{started}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)
    for run, per in zip(report["runs"], verdict["runs"]):
        print(f"run {run['index']}: Firefox {run.get('version')} prefs={run.get('prefs')}")
        for name, row in per["rows"].items():
            print(f"   {name:18} wire={row['bytesOnWire']:>11,} first={row['firstStatus']} "
                  f"decoded={row['firstDecodedBytes']} kept={row['kept']}")
        if per["problems"]:
            print("   problems:", per["problems"])
    print(json.dumps(report["verdict"], ensure_ascii=False, indent=1))
    return 0 if verdict["outcome"] == "ESTABLISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
