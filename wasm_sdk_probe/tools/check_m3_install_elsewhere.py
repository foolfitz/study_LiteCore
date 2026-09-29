#!/usr/bin/env python3
"""M3 install elsewhere -- the release archive on another Nextcloud.

Criteria I0-I4: specs/SPEC-M3-install-elsewhere.md §4, written before this tool
(and revised after the adversarial review, before any counted run).

  check_m3_install_elsewhere.py install [--reinstall]
        unpack the release archive into litecoreprobe's apps-extra and enable it;
        a process baseline of the web container is sampled first (I4-1b);
        --reinstall removes a clean earlier install first (occ app:remove)
  check_m3_install_elsewhere.py equivalence
        every counted report of the four runners that existed at PRE, scored by
        the runners at PRE and now; the dev-instance recording path (host
        binding, K0 package record, instance description) old vs new (I3-8)
  check_m3_install_elsewhere.py selftest
        host_binding against a scratch copy of the release, clean and mutated
  check_m3_install_elsewhere.py run --label shakedown|counted [--dev-host-entry R]
        the window: archive records (I0), the dev instance's and litecoreprobe's
        access logs (I2), a process + open-file sampler with three positive
        controls and a live docker lifecycle stream (I4), the four runners
        against litecoreprobe (I3)
  check_m3_install_elsewhere.py --score REPORT
  check_m3_install_elsewhere.py --red-cases REPORT [--strict]

Scoring reads raw fields -- archive listings, git blobs' hashes, occ output,
access-log lines, ps rows, /proc fd links, docker events, the runners' own
reports re-scored and re-red-cased by their own functions -- and never a
boolean this tool concluded while running.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import datetime
import functools
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_m3_release as release_tool  # noqa: E402
import check_m3_assets  # noqa: E402
import check_m3_host_entry  # noqa: E402
import check_m3_locks  # noqa: E402
import check_m3_versions  # noqa: E402
from check_m3_skeleton_open import (  # noqa: E402
    DEFAULT_DDEV, RELEASE_RECORD, HOST_FILES, Instance, host_binding, installed_app, tree_listing,
    tree_oddities)
from probe_m3_assets import LOG  # noqa: E402
from probe_m3_gate0_coep import sha256_file, utc_now  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
TOOLS = Path(__file__).resolve().parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-install"
PROBE = Path.home() / "Projects" / "Nextcloud_Apps" / "litecoreprobe"
PROBE_URL = "https://litecoreprobe.ddev.site:8443"
DEV_URL = "https://litecore.ddev.site:8443"
WEB = "ddev-litecoreprobe-web"
APP_IN_CONTAINER = "/var/www/html/nextcloud/apps-extra/litecore"
MOUNT = "/mnt/litecore-dist"
PRE = "9748b714"            # study_LiteCore before the runners learned --ddev-root
CONTROL = "/tmp/litecore-ctl"
PROBE_KEYS = ("files_probe", "files_isolation")
INTERVAL = 0.5
GAP = 1.0                   # I4-2: no two good samples further apart (2 x INTERVAL)
QUIET = 60                  # I2-1: seconds of silence on the dev instance around the window
BASELINE_SECONDS = 120      # I4-1b: two ddev health-check cycles
RUNNER_TIMEOUT = 3 * 3600
MARK = "@@LC@@"
# One long-lived docker exec for the whole window: a shell loop printing, every
# INTERVAL s, the container's clock, every fd open on the dist mount with its
# holder's ppid and command line, then ps.  A docker exec per sample was slowed
# to 1.6 s by the controls' own execs in the second shakedown.  find runs
# before ps (review 2, item 6a) so a holder still alive at ps time has a ps
# row; one that died in between keeps the ppid and cmdline read here.  The
# ppid is the second field after the last ") " of /proc/<pid>/stat -- a comm
# may hold spaces (item 15).  ps -ww: without a terminal, args are cut at 80
# columns (item 15).  lstart gives each process an identity beyond its pid
# (review 2, item 2) -- but lstart is btime + ticks/HZ, and btime moves with
# every clock step (review 3, item 1: its fraction was .80, so a 0.2 s NTP step
# shifts every lstart by a second), so I4-1b keys on field 22 of
# /proc/<pid>/stat, the start in clock ticks since boot, which no clock step
# moves.  LC_ALL=C: under zh_TW ps prints lstart in Chinese and PS_ROW reads
# nothing (review 3, item 14).  An fd line is tab-separated:
# the fd, its holder's ppid, the file it points at (so an I2-3 problem names
# the file, and control 4's excuse holds for its own file only -- fable's
# ruling, condition 5), the holder's command line.
LOOP = (f"export LC_ALL=C; while :; do echo {MARK}T $(date +%s.%N); echo {MARK}F; "
        "find /proc/[0-9]*/fd -lname '*litecore-dist*' 2>/dev/null | while read f; do "
        "p=${f#/proc/}; p=${p%%/*}; "
        "printf '%s\\t%s\\t%s\\t%s\\n' \"$f\" \"$(sed 's/.*) //' /proc/$p/stat 2>/dev/null | cut -d' ' -f2)\" "
        "\"$(readlink $f)\" \"$(tr '\\0' ' ' </proc/$p/cmdline 2>/dev/null | cut -c1-160)\"; "
        f"done; echo {MARK}P; ps -ww -eo pid=,ppid=,comm=,lstart=,args=; echo {MARK}S; "
        f"cat /proc/[0-9]*/stat 2>/dev/null; echo {MARK}E; sleep {INTERVAL}; done")
PS_ROW = re.compile(r"^\s*(\d+)\s+(\d+)\s+(.*?)\s+([A-Z][a-z]{2} [A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d \d{4})\s?(.*)$")
EVENT_IMAGE = "ddev/ddev-utilities:latest"   # review 2, item 9: not the project-labelled web image
LIFECYCLE = ("create", "start", "restart", "unpause", "die", "kill", "stop", "pause", "destroy")
# name -> (tool, evidence dir, the verdict a counted run must reach; None = host entry's `lands`)
RUNNERS = {
    "assets": ("check_m3_assets.py", "m3-assets", "ASSETS DELIVERED"),
    "versions": ("check_m3_versions.py", "m3-versions", "VERSIONS CORRECT"),
    "host-entry": ("check_m3_host_entry.py", "m3-host-entry", None),
    "locks": ("check_m3_locks.py", "m3-locks", "LOCKS LAND"),
}
MODULES = {"assets": check_m3_assets, "versions": check_m3_versions,
           "host-entry": check_m3_host_entry, "locks": check_m3_locks}
REPORT_PATH = re.compile(r"(findings/evidence/[\w./+\-]+\.json)")
EXEC_FAMILY = re.compile(r"\b(exec|shell_exec|system|passthru|proc_open|popen|pcntl_exec|pcntl_fork)\s*\(|`")


def sh(argv: list[str], cwd: Path | None = None, timeout: float = 300) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def occ(*args: str) -> str:
    return sh(["ddev", "occ", *args], cwd=PROBE).stdout


def probe_switches() -> dict[str, str]:
    return {key: occ("config:app:get", "litecoreprobe", key).strip() for key in PROBE_KEYS}


def docker_set() -> list[str]:
    return sorted(sh(["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Image}}\t{{.CreatedAt}}\t{{.State}}"]).stdout.splitlines())


def log_size(root: Path) -> int:
    return int(sh(["ddev", "exec", "stat", "-c", "%s", LOG], cwd=root).stdout.strip())


def log_since(root: Path, offset: int) -> list[str]:
    return sh(["ddev", "exec", "tail", "-c", f"+{offset + 1}", LOG], cwd=root, timeout=600).stdout.splitlines()


def dev_quiet(seconds: float = QUIET) -> dict[str, Any]:
    """Wait until the dev instance has had no request through the router for
    `seconds`.  The first shakedown saw why: Apache logs a 408 for an idle
    backend connection the router opened, up to 40 s after the last real
    request (mod_reqtimeout header=20-40) -- debris landing in the window."""
    waited = 0.0
    while True:
        tail = sh(["ddev", "exec", "tail", "-n", "400", LOG], cwd=DEFAULT_DDEV).stdout.splitlines()
        stamps = [m.group(1) for line in tail if line.split(" ", 1)[0] != "127.0.0.1"
                  for m in [re.search(r"\[([^\]]+)\]", line)] if m]
        last = datetime.datetime.strptime(stamps[-1], "%d/%b/%Y:%H:%M:%S %z").timestamp() if stamps else 0.0
        quiet = time.time() - last
        if quiet >= seconds:
            return {"lastForeignLine": stamps[-1] if stamps else None, "quietSeconds": round(quiet, 1),
                    "waited": round(waited, 1)}
        pause = seconds - quiet + 1
        time.sleep(pause)
        waited += pause


def module_shas() -> dict[str, str]:
    """Every module of this directory the runners and this tool have loaded."""
    return {Path(m.__file__).name: sha256_file(Path(m.__file__)) for m in list(sys.modules.values())
            if getattr(m, "__file__", None) and Path(m.__file__).resolve().parent == TOOLS}


def tree_binding() -> dict[str, Any]:
    """What binds the tools between the equivalence check and the window
    (fable's ruling of 2026-09-29, Q3 C, conditions 9 and 11): the committed
    tree of wasm_sdk_probe/, the last commit that touched it, nothing under it
    differing from that tree (untracked files included), and the interpreters.
    It covers what module_shas cannot -- the runners are subprocesses with
    lazily imported modules, test-e2-c-static runs node tests, the Makefile --
    but not gitignored paths (dist/, build/); dist/ is bound by the page and
    engine shas the runners check themselves."""
    git = lambda *a: sh(["git", *a], cwd=REPO).stdout.strip()  # noqa: E731
    make = sh(["make", "--version"]).stdout.splitlines()
    return {"tree": git("rev-parse", "HEAD:wasm_sdk_probe"),
            "lastCommit": git("log", "-1", "--format=%H", "--", "wasm_sdk_probe"),
            "porcelain": git("status", "--porcelain", "--untracked-files=all", "--", "wasm_sdk_probe"),
            "python": sys.version, "node": sh(["node", "--version"]).stdout.strip(), "make": make[0] if make else ""}


def epoch(iso: str | None) -> float | None:
    try:
        return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


# --------------------------------------------------------------------------
# the sampler (I4, I2-3)


def parse_block(lines: list[str]) -> tuple[float, list[list[Any]], list[list[Any]]]:
    """One block of LOOP's output: its clock, the container's processes (the
    sampler's own shell and everything below it left out), the fds.  A row is
    [pid, ppid, comm, args, lstart, start ticks]; rows stored before the
    second review have neither, before the third no ticks."""
    stamp = float(lines[0].split()[1])
    fd_at, ps_at, stat_at = lines.index(f"{MARK}F"), lines.index(f"{MARK}P"), lines.index(f"{MARK}S")
    ticks = {}
    for line in lines[stat_at + 1:]:
        head, _, tail = line.rpartition(") ")
        fields = tail.split()
        if head and len(fields) > 19 and line.split(" ", 1)[0].isdigit():
            ticks[int(line.split(" ", 1)[0])] = int(fields[19])   # field 22: starttime, clock ticks since boot
    raw = []
    for line in lines[ps_at + 1:stat_at]:
        match = PS_ROW.match(line)
        if match:
            pid = int(match.group(1))
            raw.append([pid, int(match.group(2)), match.group(3).strip(), match.group(5)[:160], match.group(4),
                        ticks.get(pid)])
    by_pid = {r[0]: r for r in raw}
    rows = [r for r in raw if not any(MARK in a[3] for a in lineage(by_pid, r[0]))]
    fds = []
    for line in lines[fd_at + 1:ps_at]:
        parts = (line.split("\t") + ["", "", ""])[:4]
        match = re.match(r"/proc/(\d+)/fd/(\d+)$", parts[0].strip())
        if match:
            fds.append([int(match.group(1)), int(match.group(2)), int(parts[1]) if parts[1].isdigit() else None,
                        parts[3].strip()[:160], parts[2]])
    return stamp, rows, fds


class Sampler(threading.Thread):
    """LOOP's output, one sample per block.  A sample equal to the previous one
    is stored as `same` (lossless); `r` is when the host read it."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.samples: list[dict[str, Any]] = []
        self.stderr: list[str] = []
        hz = sh(["docker", "exec", WEB, "getconf", "CLK_TCK"]).stdout.strip()
        self.hz = int(hz) if hz.isdigit() else hz
        self.halt = threading.Event()
        self.process = subprocess.Popen(["docker", "exec", WEB, "sh", "-c", LOOP], stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
        # Drained so a full stderr pipe can never stall the loop (review 2, item 15).
        self.drain = threading.Thread(target=lambda: [self.stderr.append(line.rstrip("\n")[:300])
                                                      for line in self.process.stderr], daemon=True)
        self.drain.start()

    def run(self) -> None:
        last, block = None, []
        for line in self.process.stdout:
            line = line.rstrip("\n")
            if line.startswith(f"{MARK}T "):
                block = [line]
            elif line == f"{MARK}E" and block:
                try:
                    stamp, rows, fds = parse_block(block)
                    if not rows:
                        raise RuntimeError("no rows")
                    entry = {"t": round(stamp, 3), "r": round(time.time(), 3)}
                    entry.update({"same": True} if (rows, fds) == last else {"rows": rows, "fds": fds})
                    self.samples.append(entry)
                    last = (rows, fds)
                except Exception as error:  # noqa: BLE001 -- recorded; I4-2 counts only good samples
                    self.samples.append({"t": round(time.time(), 3), "error": f"{type(error).__name__}: {error}"})
                    last = None
                block = []
            elif block:
                block.append(line)
            if self.halt.is_set():
                break

    def stop(self) -> None:
        self.halt.set()
        self.process.terminate()
        self.join(timeout=30)
        # The loop runs in the container: end it there too.
        sh(["docker", "exec", WEB, "pkill", "-f", MARK])


def expand(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Undo `same`: every good sample with its rows and fds."""
    out, last = [], None
    for sample in samples:
        if "error" in sample:
            last = None
            continue
        if sample.get("same"):
            if last is None:
                continue
            rows, fds = last
        else:
            rows, fds = sample.get("rows"), sample.get("fds", [])
            if rows is None:
                continue
        out.append({"t": sample["t"], "rows": rows, "fds": fds})
        last = (rows, fds)
    return out


def lineage(by_pid: dict[int, list[Any]], pid: int) -> list[list[Any]]:
    """The process and its ancestors, nearest first."""
    chain, seen = [], set()
    row = by_pid.get(pid)
    while row is not None and row[0] not in seen and len(chain) < 64:
        chain.append(row)
        seen.add(row[0])
        row = by_pid.get(row[1])
    return chain


def is_control(chain: list[list[Any]]) -> bool:
    return any(CONTROL in str(r[3]) for r in chain)


def identity(row: list[Any]) -> tuple[Any, ...]:
    """A process across samples: pid, start in clock ticks since boot, comm.
    Rows without ticks (before review 3) never match rows with them, so an old
    baseline turns every window red rather than green."""
    return (row[0], row[5] if len(row) > 5 else None, row[2])


def late_in_baseline(samples: list[dict[str, Any]], hz: Any) -> list[str]:
    """Review 3, item 2: the baseline is retaken at every --reinstall, after
    app:remove, not before the app ever ran -- an orphan an earlier install or
    window left under PID 1 would be whitelisted by it.  Every PID-1 descendant
    in the baseline must have started within 10 s of PID 1 itself (the
    container's start), in ticks, so no clock enters."""
    if not isinstance(hz, int) or hz <= 0:
        return [f"no clock-tick rate recorded ({hz!r})"]
    late = set()
    for sample in expand(samples):
        by_pid = {r[0]: r for r in sample["rows"]}
        init = by_pid.get(1)
        for row in pid1_descendants(sample["rows"]):
            if init is None or len(row) < 6 or row[5] is None or init[5] is None or row[5] - init[5] > 10 * hz:
                late.add(f"{row[2]} (pid {row[0]}) started "
                         f"{'?' if init is None or len(row) < 6 or row[5] is None or init[5] is None else round((row[5] - init[5]) / hz, 1)} s after PID 1")
    return sorted(late)


def pid1_descendants(rows: list[list[Any]]) -> list[list[Any]]:
    by_pid = {r[0]: r for r in rows}
    return [r for r in rows if r[0] != 1 and any(a[0] == 1 for a in lineage(by_pid, r[0])[1:])]


def baseline_orphans(samples: list[dict[str, Any]]) -> set[tuple[Any, ...]]:
    """I4-1b's set: every descendant of PID 1 before the app was installed, by
    identity.  (Until review 2 it was the *names* of PID 1's *children*: an
    orphan named like one of them escaped, with its whole subtree.)"""
    return {identity(r) for s in expand(samples) for r in pid1_descendants(s["rows"])}


def process_findings(sample: dict[str, Any], orphans_ok: set[tuple[Any, ...]]) -> list[dict[str, Any]]:
    """I4-1a: below a php-fpm process and not php-fpm; or php-fpm below a php-fpm
    worker (a pcntl_fork child keeps the name; only the master's children are
    workers -- review 2, item 13).  I4-1b: a descendant of PID 1 (where every
    orphan goes) that was not one before the install.  I2-3: an open file
    under the dist mount."""
    by_pid = {r[0]: r for r in sample["rows"]}
    found = []
    for row in sample["rows"]:
        chain = lineage(by_pid, row[0])
        fpms = [r for r in chain[1:] if r[2] == "php-fpm"]
        if fpms and (row[2] != "php-fpm" or len(fpms) > 1):
            found.append({"rule": "I4-1a", "comm": row[2], "pid": row[0], "ppid": row[1], "args": row[3],
                          "control": is_control(chain), "via": [fpms[0][0], fpms[0][3]]})
    for row in pid1_descendants(sample["rows"]):
        if identity(row) not in orphans_ok:
            found.append({"rule": "I4-1b", "comm": row[2], "pid": row[0], "ppid": row[1], "args": row[3],
                          "control": is_control(lineage(by_pid, row[0]))})
    for entry in sample["fds"]:
        # [pid, fd, ppid, cmdline, target]; the first two shakedowns stored
        # [pid, fd] only, the third no target.
        pid, fd, ppid, cmdline, target = (list(entry) + [None, "", None])[:5]
        # The holder as ps saw it, or as /proc told the loop when ps missed it.
        chain = lineage(by_pid, pid) or [[pid, ppid, None, cmdline or ""], *lineage(by_pid, ppid)]
        found.append({"rule": "I2-3", "pid": pid, "fd": fd, "target": target,
                      "comm": chain[0][2] or (cmdline or "").split(" ")[0].split("/")[-1],
                      "args": chain[0][3], "control": is_control(chain)})
    return found


def positive_controls() -> dict[str, Any]:
    """What I4-1a, I4-1b and I2-3 must each see: a process named php-fpm with a
    `sleep` child; an orphan (`lcorphan`, a copy of sleep) left to PID 1 when
    that fake php-fpm exits; a shell holding a file of the dist mount open.
    And a container created and removed, which I4-3's stream must carry."""
    record: dict[str, Any] = {}
    setup = sh(["docker", "exec", WEB, "sh", "-c",
                f"mkdir -p {CONTROL} && cp /bin/bash {CONTROL}/php-fpm && cp /bin/sleep {CONTROL}/lcorphan"
                f" && cp /bin/bash {CONTROL}/lcfd"])
    started = time.time()
    # The orphan's stdio goes nowhere: holding the exec's pipes kept that exec
    # open ~4 s and stalled a concurrent one (review 2, item 6b).
    ran = sh(["docker", "exec", WEB, f"{CONTROL}/php-fpm", "-c",
              f"{CONTROL}/lcorphan 6 </dev/null >/dev/null 2>&1 & sleep 2; true"], timeout=60)
    time.sleep(6)
    record["process"] = {"start": round(started, 3), "end": round(time.time(), 3), "exit": ran.returncode}
    started = time.time()
    held = sh(["docker", "exec", WEB, f"{CONTROL}/lcfd", "-c", f"exec 3<{MOUNT}/e2-editor.html; sleep 3; true"],
              timeout=60)
    record["fd"] = {"start": round(started, 3), "end": round(time.time(), 3), "exit": held.returncode}
    record["fpm"] = fpm_control()
    record["container"] = container_control("litecore-ctl-events")
    cleaned = sh(["docker", "exec", WEB, "rm", "-rf", CONTROL])
    record["exits"] = [setup.returncode, cleaned.returncode]
    return record


# Control 4 (fable's ruling of 2026-09-29, Q1/Q2 C): the same things as
# controls 1 and 2, on the real path.  The pool's socket is 0666 and the
# container has the PHP CLI, so a 25-line FastCGI client asks the pool to run a
# script in an ordinary `php-fpm: pool www` worker -- no HTTP request, no file
# in the docroot, nothing in any access log (findings/evidence/m3-install/
# fpm-path-measurement-2026-09-29.md).  Order (condition 2): the orphan first,
# then the foreground child, then the mount file -- PHP's fopen does not set
# O_CLOEXEC, and a child started after it would inherit the fd.
FPM_CLIENT = r"""<?php
function rec($t, $c) { return pack('CCnnCx', 1, $t, 1, strlen($c), 0) . $c; }
function len($l) { return $l < 128 ? chr($l) : pack('N', $l | 0x80000000); }
$p = ['SCRIPT_FILENAME' => $argv[1], 'REQUEST_METHOD' => 'GET', 'SCRIPT_NAME' => '/lc.php',
      'QUERY_STRING' => '', 'SERVER_PROTOCOL' => 'HTTP/1.1', 'GATEWAY_INTERFACE' => 'CGI/1.1',
      'REMOTE_ADDR' => '127.0.0.1', 'SERVER_NAME' => 'localhost', 'SERVER_PORT' => '80', 'CONTENT_LENGTH' => '0'];
$b = ''; foreach ($p as $k => $v) { $b .= len(strlen($k)) . len(strlen($v)) . $k . $v; }
$s = stream_socket_client('unix:///run/php/php-fpm.sock', $en, $es, 5);
fwrite($s, rec(1, pack('nCx5', 1, 0)) . rec(4, $b) . rec(4, '') . rec(5, ''));
$out = '';
while (!feof($s)) {
  $h = fread($s, 8); if (strlen($h) < 8) break;
  $u = unpack('Cv/Ct/nid/nlen/Cpad/Cr', $h);
  $c = $u['len'] ? stream_get_contents($s, $u['len']) : '';
  if ($u['pad']) fread($s, $u['pad']);
  if ($u['t'] == 6 || $u['t'] == 7) $out .= $c;
  if ($u['t'] == 3) break;
}
echo $out;
"""
FPM_FILE = f"{MOUNT}/e2-editor.html"
FPM_SCRIPT = f"""<?php
$orphan = trim((string) exec('{CONTROL}/lcorphan4 8 </dev/null >/dev/null 2>&1 & echo $!'));
exec('{CONTROL}/lcfg 2');
$f = fopen('{FPM_FILE}', 'r');
sleep(3);
fclose($f);
echo "worker=", getmypid(), " orphan=", $orphan, "\\n";
"""


def fpm_control() -> dict[str, Any]:
    """Control 4: a real php-fpm worker backgrounds `lcorphan4` (I4-1b must
    see it under PID 1: no subreaper on this path, measured every window),
    runs `lcfg` in the foreground (I4-1a must see it under that worker, whose
    parent is the real master), and holds a mount file open for 3 s (I2-3 must
    see the worker's own fd on that file).  Distinct names from controls 1-2,
    so each control's wanted set is its own (condition 3)."""
    setup = sh(["docker", "exec", WEB, "sh", "-c",
                f"mkdir -p {CONTROL} && cp /bin/sleep {CONTROL}/lcorphan4 && cp /bin/sleep {CONTROL}/lcfg"])
    put = [subprocess.run(["docker", "exec", "-i", WEB, "sh", "-c", f"cat > {CONTROL}/{name}"], input=text,
                          capture_output=True, text=True).returncode
           for name, text in (("fcgi.php", FPM_CLIENT), ("fpm.php", FPM_SCRIPT))]
    started = time.time()
    ran = sh(["docker", "exec", WEB, "php", f"{CONTROL}/fcgi.php", f"{CONTROL}/fpm.php"], timeout=60)
    returned = time.time()   # after this the worker is an ordinary pool worker again (review 3, item 5)
    said = re.search(r"worker=(\d+) orphan=(\d+)", ran.stdout)
    time.sleep(max(0.0, started + 9 - time.time()))   # lcorphan4 sleeps 8 s from about `started`
    return {"start": round(started, 3), "returned": round(returned, 3), "end": round(time.time(), 3),
            "exit": ran.returncode, "worker": int(said.group(1)) if said else None, "orphan": int(said.group(2)) if said else None,
            "file": FPM_FILE, "stdout": ran.stdout[-300:], "stderr": ran.stderr[-300:],
            "exits": [setup.returncode, *put]}


def container_control(name: str) -> dict[str, Any]:
    """I4-3's positive control: create and remove a container.  Run at the
    window's start and again just before its end, so a stream that died on the
    way reads as a missing event, not as "no events" (review 2, item 3).  The
    image is ddev's utilities image: a stopped container of the project's web
    image would carry litecoreprobe's compose labels (item 9)."""
    started = time.time()
    made = sh(["docker", "create", "--name", name, EVENT_IMAGE, "true"])
    removed = sh(["docker", "rm", name])
    return {"start": round(started, 3), "end": round(time.time(), 3), "name": name, "image": EVENT_IMAGE,
            "exits": [made.returncode, removed.returncode]}


class Lifecycle(threading.Thread):
    """`docker events` streamed live for container lifecycle events -- the
    daemon keeps too few events to ask afterwards (the sampler alone makes six
    exec events a second)."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        argv = ["docker", "events", "--filter", "type=container", "--format", "{{json .}}"]
        for event in LIFECYCLE:
            argv += ["--filter", f"event={event}"]
        self.process = subprocess.Popen(argv, stdout=subprocess.PIPE, text=True)
        self.lines: list[str] = []

    def run(self) -> None:
        for line in self.process.stdout:
            self.lines.append(line.strip())

    def stop(self) -> None:
        # A stream that died mid-window reads as "no events"; say whether it
        # was still running when stopped (review 2, item 3).
        self.alive_at_stop = self.process.poll() is None
        self.process.terminate()
        self.join(timeout=10)


# --------------------------------------------------------------------------
# install (I1, and I4-1b's baseline)


def snapshot() -> dict[str, Any]:
    return {"appList": json.loads(occ("app:list", "--output=json")),
            "system": json.loads(occ("config:list", "system")),
            "apps": json.loads(occ("config:list")),
            "probe": probe_switches(),
            "users": occ("user:list", "--output=json").strip()}


def app_config() -> dict[str, Any]:
    """litecore's own app config keys, as occ lists them."""
    listed = json.loads(occ("config:list", "litecore") or "{}")
    return (listed.get("apps") or {}).get("litecore") or {}


def web_started() -> str:
    """The web container's start: I4-1b's baseline names processes by pid and
    start time, so it holds only within one container lifetime."""
    return sh(["docker", "inspect", WEB, "--format", "{{.State.StartedAt}}"]).stdout.strip()


def install(reinstall: bool) -> int:
    release = json.loads(RELEASE_RECORD.read_text())
    archive = REPO / release["archive"]["path"]
    target = installed_app(PROBE)
    if sha256_file(archive) != release["archive"]["sha256"]:
        print(f"refusing: {archive} is not the recorded archive")
        return 2
    removed = None
    if target.exists():
        if not reinstall:
            print(f"refusing: {target} already exists (--reinstall removes a clean one)")
            return 2
        dirty = host_binding(PROBE)["hostDirty"]
        if dirty:
            print(f"refusing to remove an install that is not the release:\n{dirty}")
            return 2
        done = sh(["ddev", "occ", "app:remove", "litecore"], cwd=PROBE)
        removed = {"exit": done.returncode, "stdout": done.stdout[-1000:], "stderr": done.stderr[-1000:],
                   "dirGone": not target.exists()}
        if target.exists():
            shutil.rmtree(target)
        # app:remove leaves the app's config (enabled: no, installed_version),
        # and app:enable then enables a known version instead of installing
        # (review 2, item 1).  The app has no migrations, jobs or repair steps
        # (appinfo/info.xml), so its app config is all the state there is.
        keys = app_config()
        removed["configDeleted"] = {key: sh(["ddev", "occ", "config:app:delete", "litecore", key],
                                            cwd=PROBE).returncode for key in keys}
        removed["configAfter"] = app_config()
    record: dict[str, Any] = {"startedAt": utc_now(), "tool": str(Path(__file__).relative_to(REPO)),
                              "toolSha256": sha256_file(Path(__file__)), "archive": release["archive"],
                              "target": str(target), "removedFirst": removed, "before": snapshot(),
                              "webStartedAt": web_started()}
    sampler = Sampler()
    sampler.start()
    time.sleep(BASELINE_SECONDS)
    sampler.stop()
    record["baseline"] = sampler.samples
    record["hz"] = sampler.hz
    with tarfile.open(archive) as bundle:
        bundle.extractall(target.parent, filter="data")
    enabled = sh(["ddev", "occ", "app:enable", "litecore"], cwd=PROBE)
    record["enable"] = {"exit": enabled.returncode, "stdout": enabled.stdout[-2000:], "stderr": enabled.stderr[-2000:]}
    record["after"] = snapshot()
    record["getpath"] = occ("app:getpath", "litecore").strip()
    files, links = tree_listing(target)
    record["tree"] = {"isSymlink": target.is_symlink(), "files": files, "links": links,
                      "others": tree_oddities(target)}
    record["completedAt"] = utc_now()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "install.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"enable": record["enable"]["exit"], "files": len(files), "links": links,
                      "baselineSamples": len(record["baseline"]), "getpath": record["getpath"]}))
    return 0 if enabled.returncode == 0 else 1


# --------------------------------------------------------------------------
# equivalence (I3-8) and the binding self-test (I1-2)

# The dev-instance recording path before the change (I3-8).  The runners at
# PRE computed hostRepo / hostDirty / hostFiles inline, so there is no old
# callable to call: these are the expressions, and transcription() checks each
# is in PRE's source of every runner that recorded it (review 2, item 10) --
# the equivalence check evaluates exactly the text it checked.
OLD_EXPRESSIONS = {
    "hostRepo": 'subprocess.run(["git", "log", "-1", "--format=%H %s"], cwd=DEFAULT_DDEV, '
                'capture_output=True, text=True).stdout.strip()',
    "hostDirty": 'subprocess.run(["git", "status", "--short"], cwd=DEFAULT_DDEV, '
                 'capture_output=True, text=True).stdout.strip()',
    "hostFiles": '{name: sha256_file(DEFAULT_DDEV / name) for name in ( "js/litecore-editor.js", '
                 '"lib/Controller/EditorController.php", "templates/editor.php")}',
    "package": 'package_record(DEFAULT_DDEV)',
}
# Where PRE put each expression: "key": EXPR in the report dict, or (assets,
# versions) "hostDirty": dirty after dirty = EXPR; K0's package record only in assets.
OLD_SITES = {
    "check_m3_assets.py": {"hostRepo": ['"hostRepo": {}'], "hostDirty": ['dirty = {}', '"hostDirty": dirty'],
                           "hostFiles": ['"hostFiles": {}'], "package": ['report["package"] = {}']},
    "check_m3_versions.py": {"hostRepo": ['"hostRepo": {}'], "hostDirty": ['dirty = {}', '"hostDirty": dirty'],
                             "hostFiles": ['"hostFiles": {}']},
    "check_m3_locks.py": {"hostRepo": ['"hostRepo": {}'], "hostDirty": ['"hostDirty": {}'],
                          "hostFiles": ['"hostFiles": {}']},
}

OLD_RECORDING = r"""
import json, subprocess, sys
sys.path.insert(0, sys.argv[1])
import check_m3_assets as assets
from check_m3_skeleton_open import DEFAULT_DDEV, Instance
from probe_m3_gate0_coep import sha256_file
names = {"subprocess": subprocess, "DEFAULT_DDEV": DEFAULT_DDEV, "sha256_file": sha256_file,
         "package_record": assets.package_record}
out = {key: eval(text, names) for key, text in json.loads(sys.argv[2]).items()}
out["describeApp"] = Instance(DEFAULT_DDEV).describe()["app"]
print(json.dumps(out, sort_keys=True))
"""

# The same fields as the runners record them now: through the callables the
# runners themselves call (binding_fields, package_for, Instance.describe).
NEW_RECORDING = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import check_m3_assets as assets
from check_m3_skeleton_open import DEFAULT_DDEV, Instance, binding_fields, host_binding
binding = host_binding(DEFAULT_DDEV)
fields = binding_fields(binding)
out = {key: fields[key] for key in ("hostRepo", "hostDirty", "hostFiles")}
out["package"] = assets.package_for(DEFAULT_DDEV, binding)
out["describeApp"] = Instance(DEFAULT_DDEV).describe()["app"]
print(json.dumps(out, sort_keys=True))
"""


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def transcription() -> dict[str, dict[str, bool]]:
    """Each old expression, at each site, in PRE's source of that runner."""
    out = {}
    for tool, sites in OLD_SITES.items():
        source = squash(sh(["git", "show", f"{PRE}:wasm_sdk_probe/tools/{tool}"], cwd=REPO).stdout)
        out[tool] = {key: bool(source) and all(squash(site.format(OLD_EXPRESSIONS[key])) in source for site in shapes)
                     for key, shapes in sites.items()}
    return out


def equivalence() -> int:
    rows = []
    with tempfile.TemporaryDirectory(prefix="m3-install-pre-", dir=PROJECT / "build") as scratch:
        old = Path(scratch)
        archive = subprocess.run(["git", "archive", PRE, "wasm_sdk_probe/tools"], cwd=REPO, capture_output=True,
                                 check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(old)], input=archive, check=True)
        (old / "wasm_sdk_probe" / "dist").symlink_to(PROJECT / "dist")
        old_tools = old / "wasm_sdk_probe" / "tools"
        for name, (tool, directory, _) in RUNNERS.items():
            listed = sh(["git", "ls-tree", "--name-only", PRE, f"findings/evidence/{directory}/runs/"], cwd=REPO)
            for report in sorted(n for n in listed.stdout.splitlines() if n.endswith(".json")):
                row: dict[str, Any] = {"runner": name, "report": report}
                for side, path in (("before", old_tools / tool), ("after", TOOLS / tool)):
                    done = sh([sys.executable, str(path), "--score", str(REPO / report)], cwd=REPO)
                    red = sh([sys.executable, str(path), "--red-cases", str(REPO / report)], cwd=REPO, timeout=900)
                    row[side] = {"exit": done.returncode, "line": (done.stdout.strip().splitlines() or [""])[-1],
                                 "redExit": red.returncode}
                rows.append(row)
        recording = {}
        for side, code, where, extra in (("before", OLD_RECORDING, old_tools, [json.dumps(OLD_EXPRESSIONS)]),
                                         ("after", NEW_RECORDING, TOOLS, [])):
            done = sh([sys.executable, "-c", code, str(where), *extra], cwd=REPO)
            recording[side] = json.loads(done.stdout) if done.returncode == 0 else {"error": done.stderr[-1500:]}
    record = {"at": utc_now(), "pre": PRE, "head": sh(["git", "rev-parse", "HEAD"], cwd=REPO).stdout.strip(),
              "runnerSha256": {name: sha256_file(TOOLS / tool) for name, (tool, _, _) in RUNNERS.items()},
              "moduleSha256": module_shas(), "rows": rows, "recording": recording,
              "transcription": transcription(), "treeBinding": tree_binding()}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "equivalence.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    same = sum(1 for r in rows if r["before"] == r["after"])
    transcribed = all(all(v.values()) for v in record["transcription"].values())
    print(f"{same}/{len(rows)} reports score and red-case the same; recording paths equal: "
          f"{recording['before'] == recording['after'] and 'error' not in recording['before']}; "
          f"old expressions found in {PRE}: {transcribed}")
    if record["treeBinding"]["porcelain"]:
        print(f"wasm_sdk_probe/ has uncommitted changes; a counted window cannot bind to this check:\n"
              f"{record['treeBinding']['porcelain']}")
    return 0 if rows and same == len(rows) and recording["before"] == recording["after"] and transcribed \
        and not record["treeBinding"]["porcelain"] else 1


def selftest() -> dict[str, Any]:
    """host_binding on a scratch instance holding the release, clean and then
    with each kind of drift; every drifted case must name itself."""
    release = json.loads(RELEASE_RECORD.read_text())
    out: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="m3-binding-", dir=PROJECT / "build") as scratch:
        root = Path(scratch) / "instance"
        apps = root / "nextcloud" / "apps-extra"
        apps.mkdir(parents=True)
        with tarfile.open(REPO / release["archive"]["path"]) as bundle:
            bundle.extractall(apps, filter="data")
        app = apps / "litecore"
        some = sorted(release["members"])[0]
        cases = {
            "clean": lambda: None,
            "changed": lambda: (app / some).write_bytes((app / some).read_bytes() + b" "),
            "extra": lambda: (app / "lib" / "Extra.php").write_text("<?php\n"),
            "missing": lambda: (app / some).unlink(),
            "symlink": lambda: (app / "lib" / "link.php").symlink_to(app / some),
            "fifo": lambda: os.mkfifo(app / "lib" / "pipe"),
            "empty-dir": lambda: (app / "lib" / "Empty").mkdir(),
            "root-symlink": lambda: (shutil.move(str(app), str(Path(scratch) / "real")),
                                     app.symlink_to(Path(scratch) / "real")),
        }
        pristine = Path(scratch) / "pristine"
        shutil.copytree(app, pristine)
        for name, mutate in cases.items():
            if app.is_symlink():
                app.unlink()
            elif app.exists():
                shutil.rmtree(app)
            for leftover in (Path(scratch) / "real",):
                if leftover.exists():
                    shutil.rmtree(leftover)
            shutil.copytree(pristine, app)
            mutate()
            binding = host_binding(root)
            out[name] = {"hostDirty": binding["hostDirty"], "hostRepo": binding["hostRepo"]}
    return out


# --------------------------------------------------------------------------
# run: the window


def archive_records(release: dict[str, Any]) -> dict[str, Any]:
    """I0's raw material, gathered now: the archive as it is on disk, the git
    blobs and engine files it should hold, a third build, and what the
    installed PHP says about starting processes (registered, not scored)."""
    archive = REPO / release["archive"]["path"]
    listing = []
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            entry = {"name": member.name, "type": "file" if member.isfile() else "dir" if member.isdir()
                     else "symlink" if member.issym() else "hardlink" if member.islnk() else "other",
                     "mode": oct(member.mode)}
            if member.isfile():
                entry["sha256"] = hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
            listing.append(entry)
    repo = Path(release["sourceRepo"])
    tracked = release_tool.tracked(repo, release["commit"])
    manifest = json.loads((repo / "engine" / "MANIFEST.json").read_text())
    engine = {"engine/MANIFEST.json": sha256_file(repo / "engine" / "MANIFEST.json")}
    for path in manifest["files"]:
        packed = repo / "engine" / "files" / f"{path}.gz"
        engine[f"engine/files/{path}.gz"] = sha256_file(packed) if packed.is_file() else None
    rebuilt = release_tool.build(release_tool.collect(repo, release["commit"])[0])
    top = set(release_tool.git(repo, "ls-tree", "--name-only", release["commit"]).decode().split())
    scan = {}
    for php in sorted(installed_app(PROBE).rglob("*.php")):
        text = re.sub(r"/\*.*?\*/", "", php.read_text(errors="replace"), flags=re.S)
        text = re.sub(r"(^|\s)(//|#).*$", "", text, flags=re.M)
        hits = [m.group(0) for m in EXEC_FAMILY.finditer(text)]
        scan[php.relative_to(installed_app(PROBE)).as_posix()] = hits
    return {"archiveSha256": sha256_file(archive), "listing": listing,
            "gitTracked": {n: {"mode": e["mode"], "kind": e["kind"], "sha256": hashlib.sha256(e["bytes"]).hexdigest()}
                           for n, e in tracked.items()},
            "engineDir": engine, "engineBuildId": manifest.get("buildId"),
            "rebuiltSha256": hashlib.sha256(rebuilt).hexdigest(),
            "excludedTopLevel": sorted(top - set(release_tool.PARTS)),
            "execFamilyScan": scan}


def run_runner(name: str, label: str, extra: list[str]) -> dict[str, Any]:
    tool = RUNNERS[name][0]
    argv = [sys.executable, str(TOOLS / tool), "--label", label, "--ddev-root", str(PROBE), *extra]
    started = time.time()
    try:
        done = subprocess.run(argv, cwd=REPO, capture_output=True, text=True, timeout=RUNNER_TIMEOUT)
        exit_code, stdout, stderr = done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired as error:
        exit_code, stdout, stderr = "timeout", str(error.stdout or ""), str(error.stderr or "")
    found = REPORT_PATH.findall(stdout)
    record = {"argv": argv[1:], "start": round(started, 3), "end": round(time.time(), 3),
              "exit": exit_code, "stdoutTail": stdout[-3000:], "stderrTail": stderr[-3000:],
              "report": found[-1] if found else None}
    if record["report"]:
        record["reportSha256"] = sha256_file(REPO / record["report"])
        red = sh([sys.executable, str(TOOLS / tool), "--red-cases", str(REPO / record["report"])], cwd=REPO)
        record["redCases"] = {"exit": red.returncode, "tail": red.stdout[-1500:]}
    return record


def run(args: argparse.Namespace) -> int:
    counted = args.label == "counted"
    release = json.loads(RELEASE_RECORD.read_text())
    if counted and not args.dev_host_entry:
        print("refusing a counted run: --dev-host-entry (I3-7) is required")
        return 2
    binding = host_binding(PROBE)
    if counted and binding["hostDirty"]:
        print(f"refusing a counted run: the installed tree differs from the release:\n{binding['hostDirty']}")
        return 2
    tree_start = tree_binding()
    if counted and tree_start["porcelain"]:
        print(f"refusing a counted run: wasm_sdk_probe/ has uncommitted changes:\n{tree_start['porcelain']}")
        return 2
    report: dict[str, Any] = {
        "tool": str(Path(__file__).relative_to(REPO)), "toolSha256": sha256_file(Path(__file__)),
        "label": args.label, "startedAt": utc_now(), "criteria": "specs/SPEC-M3-install-elsewhere.md §4",
        "release": release, "install": json.loads((EVIDENCE / "install.json").read_text()),
        "equivalence": json.loads((EVIDENCE / "equivalence.json").read_text())
        if (EVIDENCE / "equivalence.json").is_file() else None,
        "archive": archive_records(release), "binding": binding, "bindingSelftest": selftest(),
        "getpath": occ("app:getpath", "litecore").strip(), "moduleSha256Start": module_shas(),
        "treeBindingStart": tree_start,
    }
    if args.dev_host_entry:
        path = REPO / args.dev_host_entry
        red = sh([sys.executable, str(TOOLS / "check_m3_host_entry.py"), "--red-cases", str(path)], cwd=REPO)
        report["devHostEntry"] = {"report": args.dev_host_entry, "reportSha256": sha256_file(path),
                                  "redCases": {"exit": red.returncode, "tail": red.stdout[-1500:]}}
    out = EVIDENCE / ("runs" if counted else "shakedown") / f"{report['startedAt'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    window: dict[str, Any] = {"devQuiet": dev_quiet(), "probeBefore": probe_switches(),
                              "dockerBefore": docker_set(), "devLogOffset": log_size(DEFAULT_DDEV),
                              "probeLogOffset": log_size(PROBE), "webStartedAt": web_started()}
    lifecycle = Lifecycle()
    lifecycle.start()
    sampler = Sampler()
    sampler.start()
    time.sleep(2)
    window["start"] = round(time.time(), 3)
    report["window"] = window
    report["runners"] = {}
    try:
        # Inside the try: if a control raises, the sampler and the stream are
        # still stopped and the report still written (review 3, item 7).
        window["controls"] = positive_controls()
        names = list(RUNNERS) if counted else args.runners.split(",")
        for name in names:
            extra = [] if counted else ["--repeats", str(args.repeats),
                                        *(["--arms", args.locks_arms] if name == "locks" and args.locks_arms else [])]
            print(f"{name} …", flush=True)
            report["runners"][name] = run_runner(name, args.label, extra)
            print(f"  exit {report['runners'][name]['exit']} {report['runners'][name]['report']}", flush=True)
            out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    finally:
        window["controlsEnd"] = {"container": container_control("litecore-ctl-events-end")}
        window["end"] = round(time.time(), 3)
        time.sleep(2)
        sampler.stop()
        lifecycle.stop()
        window["lifecycleEvents"] = lifecycle.lines
        window["lifecycleAlive"] = lifecycle.alive_at_stop
        window["samplerStderr"] = sampler.stderr[-50:]
        window["dockerAfter"] = docker_set()
        window["probeAfter"] = probe_switches()
        probe_lines = log_since(PROBE, window["probeLogOffset"])
        window["probeLog"] = {"lines": len(probe_lines),
                              "engineRoute": sum(1 for line in probe_lines if "/apps/litecore/r/" in line),
                              "probeApp": [line for line in probe_lines if "/litecoreprobe/" in line]}
        time.sleep(QUIET)   # a 408 caused inside the window lands up to 40 s after it
        window["devLogRead"] = round(time.time(), 3)   # when the read began (review 2, item 15)
        window["devLogLines"] = log_since(DEFAULT_DDEV, window["devLogOffset"])
        report["samples"] = sampler.samples
        report["moduleSha256End"] = module_shas()
        report["treeBindingEnd"] = tree_binding()
        report["completedAt"] = utc_now()
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    result = score(report, strict=counted)
    report["score"] = result
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(out.relative_to(REPO))
    print(one_line(result))
    return 0 if result["verdict"] in ("INSTALLS ELSEWHERE", "clean") else 1


# --------------------------------------------------------------------------
# scoring


def load_reports(report: dict[str, Any]) -> dict[str, Any]:
    loaded = {}
    for name, entry in (report.get("runners") or {}).items():
        path = entry.get("report")
        loaded[name] = json.loads((REPO / path).read_text()) if path and (REPO / path).is_file() else None
    dev = (report.get("devHostEntry") or {}).get("report")
    loaded["dev-host-entry"] = json.loads((REPO / dev).read_text()) if dev and (REPO / dev).is_file() else None
    return loaded


@functools.lru_cache(maxsize=None)
def red_cases_now(tool: str, path: str, sha: str) -> int:
    """A runner's own red cases on its report, re-run while scoring (the exit
    code recorded at run time is a conclusion; this is the check)."""
    if not (REPO / path).is_file() or sha256_file(REPO / path) != sha:
        return -1
    module = {RUNNERS[n][0]: MODULES[n] for n in RUNNERS}[tool]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            failures = module.red_cases(REPO / path)
    except Exception:  # noqa: BLE001 -- a crash is not "all red"; it must not end the scoring (review 2, item 15)
        return -2
    return int(bool(failures))


def runner_verdict(name: str, body: dict[str, Any], strict: bool = True) -> tuple[bool, str]:
    module = MODULES["host-entry" if name == "dev-host-entry" else name]
    result = module.score(copy.deepcopy(body), strict=strict)
    if RUNNERS.get(name, (None, None, None))[2] is None:
        return bool(result.get("lands")), "LANDS" if result.get("lands") else f"NOT LANDS {result.get('problems')}"
    return (result.get("verdict") == (RUNNERS[name][2] if strict else "clean"),
            f"{result.get('verdict')} {result.get('problems')} {result.get('tally')}")


SELFTEST_DRIFTS = ("changed", "extra", "missing", "symlink", "root-symlink", "fifo", "empty-dir")
# Each positive control (window.controls[key]): the rules it trips, and what
# must be seen during its span (±1 s).  Control 4 ("fpm") is fable's ruling of
# 2026-09-29; its names differ from controls 1-2 so no control can satisfy
# another's wanted set (condition 3).
CONTROL_RULES = {"process": ("I4-1a", "I4-1b"), "fd": ("I2-3",), "fpm": ("I4-1a", "I4-1b", "I2-3")}
CONTROL_WANTS = {"process": ("I4-1a sleep", "I4-1b lcorphan"), "fd": ("I2-3 lcfd",),
                 "fpm": ("I4-1a lcfg", "I4-1b lcorphan4", "I2-3 worker")}


def control_label(key: str, ctl: dict[str, Any], bad: dict[str, Any], by_pid: dict[int, list[Any]],
                  t: float) -> str | None:
    """The finding at sample time t as control `key` accounts for it, or None
    if it does not.  A control's own processes are recognised by
    /tmp/litecore-ctl in their lineage.  Control 4's worker is not (its args
    are the pool's): while its request runs -- not after (review 3, item 5) --
    its fd on the file the script opened is accounted for by the pid the script
    reported (conditions 4 and 5), and so is a php-fpm-named child of it: the
    instant between exec()'s fork and its exec (review 3, item 12).  `lcfg`
    counts as seen only below that worker, whose parent is php-fpm with a parent
    of its own -- the real master, not control 1's fake one, which docker exec
    starts (ppid 0).  An orphan counts as seen only as a direct child of PID 1,
    and control 4's only with the pid the script reported (condition 8; review
    3, item 10)."""
    if bad["rule"] not in CONTROL_RULES[key]:
        return None
    worker = ctl.get("worker") if key == "fpm" else None
    running = worker is not None and t <= (ctl.get("returned") or 0) + 1
    if running and bad["rule"] == "I2-3" and bad["pid"] == worker:
        return "I2-3 worker" if bad.get("target") == ctl.get("file") else None
    if running and bad["rule"] == "I4-1a" and bad["comm"] == "php-fpm" and bad.get("ppid") == worker:
        return "I4-1a fork of the worker"
    if not bad["control"]:
        return None
    if key == "fpm" and bad["rule"] == "I4-1a" and bad["comm"] == "lcfg":
        row = by_pid.get(worker)
        master = by_pid.get(row[1]) if row else None
        real = bad["via"][0] == worker and master is not None and master[2] == "php-fpm" and master[1] != 0
        return "I4-1a lcfg" if real else "I4-1a lcfg, not below the real worker"
    if bad["rule"] == "I4-1b":
        direct = bad.get("ppid") == 1 and (key != "fpm" or bad["pid"] == ctl.get("orphan"))
        return f"I4-1b {bad['comm']}" + ("" if direct else ", not the reported direct child of PID 1")
    return f"{bad['rule']} {bad['comm']}"


def score(report: dict[str, Any], strict: bool, loaded: dict[str, Any] | None = None) -> dict[str, Any]:
    problems: list[str] = []
    release, archive = report.get("release") or {}, report.get("archive") or {}
    commit = release.get("commit") or "?"
    window = report.get("window") or {}
    start, end = window.get("start"), window.get("end")
    # I0
    listing = archive.get("listing") or []
    files = {e["name"]: e for e in listing if e.get("type") == "file"}
    expected = ({f"litecore/{n}" for n in archive.get("gitTracked") or {}}
                | {f"litecore/{n}" for n in archive.get("engineDir") or {}})
    if not files or set(files) != expected:
        problems.append(f"I0-1 members differ: {sorted(set(files) ^ expected)[:10]}")
    for name, entry in (archive.get("gitTracked") or {}).items():
        if (files.get(f"litecore/{name}") or {}).get("sha256") != entry.get("sha256"):
            problems.append(f"I0-2 {name} is not the git blob of {commit[:12]}")
    for name, digest in (archive.get("engineDir") or {}).items():
        if digest is None or (files.get(f"litecore/{name}") or {}).get("sha256") != digest:
            problems.append(f"I0-2 {name} is not the host's engine file")
    if archive.get("engineBuildId") != release.get("buildId"):
        problems.append(f"I0-2 engine buildId {archive.get('engineBuildId')} vs record {release.get('buildId')}")
    if {f"litecore/{n}": d for n, d in (release.get("members") or {}).items()} != \
            {n: e.get("sha256") for n, e in files.items()}:
        problems.append("I0-2 the release record's member list is not the archive's")
    shas = {archive.get("archiveSha256"), (release.get("archive") or {}).get("sha256"),
            release.get("secondBuildSha256"), archive.get("rebuiltSha256")}
    if len(shas) != 1 or None in shas:
        problems.append(f"I0-3 builds differ: {sorted(str(s)[:12] for s in shas)}")
    for entry in listing:
        name = entry.get("name", "")
        if entry.get("type") not in ("file", "dir") or name.startswith("/") or ".." in name.split("/") \
                or not (name == "litecore" or name.startswith("litecore/")):
            problems.append(f"I0-4 member {name!r} is a {entry.get('type')}")
    # I1
    install = report.get("install") or {}
    enabled = ((install.get("after") or {}).get("appList") or {}).get("enabled") or {}
    if (install.get("enable") or {}).get("exit") != 0 or enabled.get("litecore") != release.get("version"):
        problems.append(f"I1-1 enable exit {(install.get('enable') or {}).get('exit')}, "
                        f"litecore {enabled.get('litecore')!r} (archive {release.get('version')!r})")
    # An install, not a re-enable: before it, Nextcloud had no config for the app (review 2, item 1).
    before_apps = ((install.get("before") or {}).get("apps") or {}).get("apps")
    if not isinstance(before_apps, dict) or "litecore" in before_apps:
        problems.append(f"I1-1 litecore had app config before the install: "
                        f"{(before_apps or {}).get('litecore') if isinstance(before_apps, dict) else before_apps!r}")
    tree = install.get("tree") or {}
    if tree.get("isSymlink") is not False or tree.get("links") or tree.get("others") != [] \
            or tree.get("files") != release.get("members"):
        problems.append(f"I1-2 installed tree: symlink {tree.get('isSymlink')}, links {tree.get('links')}, "
                        f"others {tree.get('others')}, files equal {tree.get('files') == release.get('members')}")
    if (report.get("binding") or {}).get("hostDirty") or not (report.get("binding") or {}).get("hostRepo"):
        problems.append(f"I1-2 at the window: {str((report.get('binding') or {}).get('hostDirty'))[:300]}")
    for label, seen in (("install", install.get("getpath")), ("window", report.get("getpath"))):
        if seen != APP_IN_CONTAINER:
            problems.append(f"I1-2 Nextcloud serves litecore from {seen!r} at {label}")
    selftest_seen = report.get("bindingSelftest") or {}
    if (selftest_seen.get("clean") or {}).get("hostDirty") != "" or not (selftest_seen.get("clean") or {}).get("hostRepo"):
        problems.append(f"I1-2 binding self-test: a clean copy reads {selftest_seen.get('clean')}")
    for case in SELFTEST_DRIFTS:
        if not (selftest_seen.get(case) or {}).get("hostDirty") or (selftest_seen.get(case) or {}).get("hostRepo"):
            problems.append(f"I1-2 binding self-test: {case} reads clean")
    before, after = install.get("before") or {}, install.get("after") or {}
    if not before.get("system") or before.get("system") != after.get("system"):
        problems.append("I1-3 system config changed across the install")
    off = {k: "off" for k in PROBE_KEYS}
    for label, seen in (("install", before.get("probe")), ("window start", window.get("probeBefore")),
                        ("window end", window.get("probeAfter"))):
        if seen != off:
            problems.append(f"I1-4 probe app switches at {label}: {seen}")
    # I2
    lines = window.get("devLogLines") or []
    health = [line for line in lines if line.startswith("127.0.0.1 ") and '"GET /phpstatus ' in line]
    if not start or not end or len(health) < int((end - start) // 60) - 1:
        problems.append(f"I2-1 {len(health)} health checks read over {round((end or 0) - (start or 0))} s: "
                        "the instrument is not reading the dev log")
    foreign = [line for line in lines if line.split(" ", 1)[0] != "127.0.0.1"]
    if foreign:
        problems.append(f"I2-1 the dev instance was reached: {foreign[:3]}")
    if (window.get("devQuiet") or {}).get("quietSeconds", 0) < QUIET:
        problems.append(f"I2-1 the window opened {window.get('devQuiet')} after the dev instance's last request")
    if window.get("devLogRead", 0) < (end or 0) + QUIET:
        problems.append("I2-1 the dev log was read before 60 s had passed after the window")
    loaded = load_reports(report) if loaded is None else loaded
    for name in RUNNERS:
        body = loaded.get(name)
        if body is None:
            problems.append(f"I3 {name}: no report")
            continue
        base = (body.get("instance") or {}).get("baseUrl") or body.get("baseUrl")
        if base != PROBE_URL:
            problems.append(f"I2-2 {name} ran against {base!r}")
    probe_log = window.get("probeLog") or {}
    if not probe_log.get("engineRoute"):
        problems.append("I2-4 no engine request in litecoreprobe's log: the instrument is not reading it")
    reached = [line for line in probe_log.get("probeApp") or []
               if re.search(r'"[A-Z]+ [^ "]*/apps(-extra)?/litecoreprobe/', line)]
    if reached:
        problems.append(f"I2-4 the probe app served: {reached[:3]}")
    # I3
    clauses = {"assets": "I3-1", "versions": "I3-2", "locks": "I3-3", "host-entry": "I3-4"}
    equivalence_seen = report.get("equivalence") or {}
    shas_now = equivalence_seen.get("runnerSha256") or {}
    for name, clause in clauses.items():
        body = loaded.get(name)
        if body is None:
            continue
        entry = (report.get("runners") or {}).get(name) or {}
        ok, verdict = runner_verdict(name, body, strict)
        if not ok:
            problems.append(f"{clause} {name}: {verdict[:1200]}")
        if name == "host-entry":
            app = (body.get("instance") or {}).get("app") or {}
            bound = not app.get("dirty") and str(app.get("commit", "")).startswith(commit)
            sha = (body.get("runner") or {}).get("sha256")
        else:
            bound = not body.get("hostDirty") and str(body.get("hostRepo", "")).startswith(commit)
            sha = body.get("runnerSha256")
        if not bound:
            problems.append(f"I3-5 {name} is not bound to the release {commit[:12]}")
        began, ended = epoch(body.get("startedAt")), epoch(body.get("completedAt"))
        if not (start and end and began and ended and start <= began <= ended <= end):
            problems.append(f"I3-5 {name}'s report was not made inside the window "
                            f"({body.get('startedAt')} – {body.get('completedAt')})")
        if (entry.get("redCases") or {}).get("exit") != 0 or \
                red_cases_now(RUNNERS[name][0], entry.get("report") or "", entry.get("reportSha256") or "") != 0:
            problems.append(f"I3-6 {name}: red cases did not all go red (or the report changed since the run)")
        if strict and sha != shas_now.get(name):
            problems.append(f"I3-8 {name} ran with runner {str(sha)[:12]}, equivalence checked {str(shas_now.get(name))[:12]}")
    dev = loaded.get("dev-host-entry")
    if strict or dev is not None:
        if dev is None:
            problems.append("I3-7 no host-entry report from the dev instance")
        else:
            entry = report.get("devHostEntry") or {}
            ok, verdict = runner_verdict("dev-host-entry", dev, strict)
            app = (dev.get("instance") or {}).get("app") or {}
            if not ok:
                problems.append(f"I3-7 dev host entry: {verdict[:200]}")
            if (dev.get("instance") or {}).get("baseUrl") != DEV_URL:
                problems.append(f"I3-7 dev host entry ran against {(dev.get('instance') or {}).get('baseUrl')!r}")
            if not str(app.get("commit", "")).startswith(commit):
                problems.append(f"I3-7 dev host entry is bound to {app.get('commit')!r}, not {commit[:12]}")
            if (entry.get("redCases") or {}).get("exit") != 0 or red_cases_now(
                    "check_m3_host_entry.py", entry.get("report") or "", entry.get("reportSha256") or "") != 0:
                problems.append("I3-7 dev host entry's red cases did not all go red (or the report changed)")
            if epoch(dev.get("completedAt")) is None or not start or epoch(dev.get("completedAt")) > start:
                problems.append("I3-7 the dev host-entry run did not finish before the window")
            # Its lazily imported modules are bound only by the tree check (condition 12).
            checked = epoch(equivalence_seen.get("at"))
            if epoch(dev.get("startedAt")) is None or checked is None or epoch(dev.get("startedAt")) < checked:
                problems.append(f"I3-7 the dev host-entry run started {dev.get('startedAt')} before the equivalence "
                                f"check {equivalence_seen.get('at')}")
            if strict and (dev.get("runner") or {}).get("sha256") != shas_now.get("host-entry"):
                problems.append(f"I3-7 dev host entry ran with runner {str((dev.get('runner') or {}).get('sha256'))[:12]}, "
                                f"equivalence checked {str(shas_now.get('host-entry'))[:12]}")
    rows = equivalence_seen.get("rows") or []
    if strict or rows:
        if {r.get("runner") for r in rows} != set(RUNNERS):
            problems.append(f"I3-8 equivalence covers {sorted({r.get('runner') for r in rows})}")
        for row in rows:
            if any("redExit" not in (row.get(side) or {}) for side in ("before", "after")):
                problems.append(f"I3-8 {row.get('runner')} {row.get('report')}: no red-case exit recorded")
            if row.get("before") != row.get("after"):
                problems.append(f"I3-8 {row.get('runner')} {row.get('report')}: {row.get('before')} -> {row.get('after')}")
        recording = equivalence_seen.get("recording") or {}
        if not recording.get("before") or "error" in recording.get("before", {}) \
                or recording.get("before") != recording.get("after"):
            problems.append("I3-8 the dev-instance recording path changed (host binding, K0 record or description)")
        transcribed = equivalence_seen.get("transcription") or {}
        missing = sorted(f"{tool} {key}" for tool, keys in OLD_SITES.items() for key in keys
                         if (transcribed.get(tool) or {}).get(key) is not True)
        if missing:
            problems.append(f"I3-8 old recording expressions not transcribed from {PRE}: {missing[:6]}")
    if strict:
        tree_eq = equivalence_seen.get("treeBinding") or {}
        for label, seen in (("equivalence check", tree_eq), ("window start", report.get("treeBindingStart") or {}),
                            ("window end", report.get("treeBindingEnd") or {})):
            if not seen.get("tree") or seen.get("porcelain") != "":
                problems.append(f"I3-8 wasm_sdk_probe/ at the {label}: tree {seen.get('tree')!r}, "
                                f"uncommitted {str(seen.get('porcelain'))[:200]!r}")
            differ = [k for k in ("tree", "lastCommit", "python", "node", "make") if seen.get(k) != tree_eq.get(k)]
            if differ:
                problems.append(f"I3-8 wasm_sdk_probe/ or the interpreters changed between the equivalence check "
                                f"and the {label}: {differ}")
        modules = equivalence_seen.get("moduleSha256") or {}
        for label, seen in (("start", report.get("moduleSha256Start")), ("end", report.get("moduleSha256End"))):
            differ = sorted(n for n in set(modules) | set(seen or {}) if modules.get(n) != (seen or {}).get(n))
            if not modules or differ:
                problems.append(f"I3-8 tools changed between the equivalence check and the window {label}: {differ[:5]}")
    # I4 (and I2-3, which the same sampler reads)
    orphans_ok = baseline_orphans(install.get("baseline") or [])
    baseline_good = expand(install.get("baseline") or [])
    if len(baseline_good) < BASELINE_SECONDS or not orphans_ok:
        problems.append(f"I4-1 the pre-install baseline has {len(baseline_good)} samples, "
                        f"PID-1 descendants {sorted(orphans_ok, key=str)}")
    late = late_in_baseline(install.get("baseline") or [], install.get("hz"))
    if late:
        problems.append(f"I4-1 the pre-install baseline whitelists what started after the container: {late[:4]}")
    if not window.get("webStartedAt") or install.get("webStartedAt") != window.get("webStartedAt"):
        problems.append(f"I4-1b the web container started {window.get('webStartedAt')!r} at the window, "
                        f"{install.get('webStartedAt')!r} at the baseline: not one lifetime, so the baseline's "
                        "processes are not this window's (reinstall to retake it)")
    controls = window.get("controls") or {}
    good = [s for s in expand(report.get("samples") or []) if start and end and start <= s["t"] <= end]
    seen_control: dict[str, set[str]] = {key: set() for key in CONTROL_WANTS}
    for sample in good:
        by_pid = {r[0]: r for r in sample["rows"]}
        for bad in process_findings(sample, orphans_ok):
            accounted = None
            for key in CONTROL_WANTS:
                ctl = controls.get(key) or {}
                if ctl.get("start", 0) - 1 <= sample["t"] <= ctl.get("end", 0) + 1:
                    accounted = control_label(key, ctl, bad, by_pid, sample["t"])
                    if accounted:
                        seen_control[key].add(accounted)
                        break
            if not accounted:
                problems.append(f"{bad['rule']} {bad['comm']} (pid {bad['pid']}, {str(bad['args'])[:80]!r}) at {sample['t']}"
                                + (f" under php-fpm {bad['via']}" if bad.get("via") else "")
                                + (f" holding {bad['target']}" if bad.get("target") else ""))
    for key, wants in CONTROL_WANTS.items():
        for wanted in wants:
            if wanted not in seen_control[key]:
                rule, name = wanted.split(" ", 1)
                problems.append(f"{rule} the positive control {key} ({name}) was not seen")
    stamps = [start] + [s["t"] for s in good] + [end] if start and end else []
    widest = max((b - a for a, b in zip(stamps, stamps[1:])), default=None)
    if not start or not end or len(good) < (end - start):
        problems.append(f"I4-2 {len(good)} samples over {round((end or 0) - (start or 0))} s")
    if widest is None or widest > GAP:
        problems.append(f"I4-2 widest gap between good samples {widest} s (limit {GAP})")
    if any(not any(r[2] == "php-fpm" for r in s["rows"]) for s in good):
        problems.append("I4-2 a sample with no php-fpm process")
    if not window.get("dockerBefore") or window.get("dockerBefore") != window.get("dockerAfter"):
        problems.append(f"I4-3 containers changed: {sorted(set(window.get('dockerBefore') or []) ^ set(window.get('dockerAfter') or []))[:4]}")
    events = [json.loads(line) for line in window.get("lifecycleEvents") or [] if line.startswith("{")]
    name_of = lambda e: ((e.get("Actor") or {}).get("Attributes") or {}).get("name")  # noqa: E731
    # Two container controls, at the window's start and just before its end
    # (review 2, item 3): a stream that died on the way misses the second.
    ctls = {"start": controls.get("container") or {},
            "end": (window.get("controlsEnd") or {}).get("container") or {}}
    for when, ctl in ctls.items():
        if not ctl.get("name") or not any(name_of(e) == ctl["name"] and e.get("Action") == "create" for e in events):
            problems.append(f"I4-3 the positive control's container create at the window's {when} was not streamed")
    if window.get("lifecycleAlive") is not True:
        problems.append(f"I4-3 the event stream was not running when stopped ({window.get('lifecycleAlive')!r})")
    others = [f"{e.get('Action')} {name_of(e)}" for e in events
              if name_of(e) not in {c.get("name") for c in ctls.values()}]
    if others:
        problems.append(f"I4-3 container lifecycle events in the window: {others[:5]}")
    if strict and report.get("label") != "counted":
        problems.append(f"label {report.get('label')!r}")
    ok = not problems
    return {"verdict": ("INSTALLS ELSEWHERE" if ok else "DOES NOT INSTALL ELSEWHERE") if strict
            else ("clean" if ok else "red"), "problems": problems, "samples": len(good),
            "controlsSeen": sorted(f"{key}: {label}" for key, labels in seen_control.items() for label in labels),
            "registered": {"execRoots": exec_roots(good)}}


def exec_roots(good: list[dict[str, Any]]) -> dict[str, int]:
    """Registered, not scored (review 2, item 8): roots with ppid 0 other than
    PID 1 -- docker exec's children (the health check, `php occ`, `runc init`,
    the service tree's `bash -c start.sh`).  I4-1a/b do not look below them: a
    process started with `docker exec -d` is unseen by I4-1.  Counted by how
    many in-window samples each (comm, args) root appears in."""
    seen: dict[str, int] = {}
    for sample in good:
        for key in {f"{r[2]} {str(r[3])[:80]}" for r in sample["rows"] if r[1] == 0 and r[0] != 1}:
            seen[key] = seen.get(key, 0) + 1
    return dict(sorted(seen.items()))


def one_line(result: dict[str, Any]) -> str:
    return f"{result['verdict']} samples={result['samples']} problems={result['problems'][:6]}"


# --------------------------------------------------------------------------
# red cases: one mutation per clause; each must add a problem under that clause


def _mid(r: dict[str, Any]) -> float:
    return round((r["window"]["start"] + r["window"]["end"]) / 2, 3)


START = "Tue Sep 29 12:00:00 2026"   # an lstart for injected rows


def _inject(r: dict[str, Any], extra_rows: list[list[Any]], extra_fds: list[list[Any]] = ()) -> None:
    base = next(s for s in expand(r["samples"]) if s["t"] >= _mid(r))
    r["samples"] = [s for s in expand(r["samples"])]
    r["samples"].append({"t": _mid(r) + 0.001, "rows": base["rows"] + extra_rows, "fds": base["fds"] + list(extra_fds)})
    r["samples"].sort(key=lambda s: s["t"])


def _inject_at(r: dict[str, Any], t: float, extra_rows: list[list[Any]]) -> None:
    """A sample at time t: the next stored sample's rows plus extra_rows."""
    good = expand(r["samples"])
    base = next(s for s in good if s["t"] >= t)
    r["samples"] = good + [{"t": round(t, 3), "rows": base["rows"] + extra_rows, "fds": base["fds"]}]
    r["samples"].sort(key=lambda s: s["t"])


def _rows(r: dict[str, Any], change) -> None:
    """Every stored sample, each row replaced by change(row, sample rows)."""
    r["samples"] = [{**s, "rows": [change(list(row), s["rows"]) for row in s["rows"]]} for s in expand(r["samples"])]


def _window_rows(r: dict[str, Any], change) -> None:
    w = r["window"]
    r["samples"] = [{**s, "rows": [change(list(row)) if w["start"] <= s["t"] <= w["end"] else row
                                   for row in s["rows"]]} for s in expand(r["samples"])]


def _fake_master(r: dict[str, Any], comm: str, ppid: int) -> None:
    """Control 4's worker below a new parent row: comm, with that ppid."""
    worker = _worker_of(r)
    r["samples"] = [{**s, "rows": [[row[0], 999980, *row[2:]] if row[0] == worker else row for row in s["rows"]]
                     + [[999980, ppid, comm, f"{comm}: fake", START, 1]]} for s in expand(r["samples"])]


def _lcfg_below_another_fpm(r: dict[str, Any]) -> None:
    worker = _worker_of(r)
    out = []
    for s in expand(r["samples"]):
        rows = [[row[0], 999986, *row[2:]] if row[2] == "lcfg" else row for row in s["rows"]]
        if any(row[2] == "lcfg" for row in s["rows"]):
            rows.append([999986, worker, "php-fpm", "php-fpm: pool www", START, 1])
        out.append({**s, "rows": rows})
    r["samples"] = out


def _late_baseline(r: dict[str, Any]) -> None:
    hz = r["install"]["hz"]
    r["install"]["baseline"] = [
        {**s, "rows": s["rows"] + [[999984, 1, "soffice.bin", "soffice.bin --headless", START,
                                    next(row[5] for row in s["rows"] if row[0] == 1) + 60 * hz]]}
        for s in expand(r["install"]["baseline"])]


def _mid_rows(r: dict[str, Any]) -> list[list[Any]]:
    return next(s for s in expand(r["samples"]) if s["t"] >= _mid(r))["rows"]


def _fpm(r: dict[str, Any]) -> int:
    return next(row[0] for s in expand(r["samples"]) for row in s["rows"] if row[2] == "php-fpm")


def _worker(r: dict[str, Any]) -> int:
    """A php-fpm worker in the mid-window sample: php-fpm whose parent is php-fpm."""
    rows = _mid_rows(r)
    by_pid = {row[0]: row for row in rows}
    return next(row[0] for row in rows if row[2] == "php-fpm" and (by_pid.get(row[1]) or [0, 0, ""])[2] == "php-fpm")


def _pid1_child(r: dict[str, Any]) -> int:
    return next(row[0] for row in _mid_rows(r) if row[1] == 1)


def _drop(r: dict[str, Any], comm: str) -> None:
    r["samples"] = [{**s, "rows": [row for row in s["rows"] if row[2] != comm]} for s in expand(r["samples"])]


def _worker_of(r: dict[str, Any]) -> int:
    return r["window"]["controls"]["fpm"]["worker"]


def _drop_fds(r: dict[str, Any], pid: int) -> None:
    r["samples"] = [{**s, "fds": [e for e in s["fds"] if e[0] != pid]} for s in expand(r["samples"])]


def _retarget(r: dict[str, Any], pid: int, target: str) -> None:
    r["samples"] = [{**s, "fds": [[*e[:4], target] if e[0] == pid else e for e in s["fds"]]}
                    for s in expand(r["samples"])]


def _reparent(r: dict[str, Any], pid: int, ppid: int) -> None:
    r["samples"] = [{**s, "rows": [[row[0], ppid, *row[2:]] if row[0] == pid else row for row in s["rows"]]}
                    for s in expand(r["samples"])]


def _blackout(r: dict[str, Any]) -> None:
    good = expand(r["samples"])
    mid = _mid(r)
    r["samples"] = [s for s in good if not mid <= s["t"] <= mid + 1.6]


def _selftest_blind(case: str):
    return lambda r, L: r["bindingSelftest"][case].update(hostDirty="", hostRepo="x")


# (clause, label, mutation, a substring the added problem must carry).  The
# substring pins each mutation to its branch: a mutation meant for one branch
# of a clause is not passed by another branch of the same clause (review 2,
# item 7 -- I0-2's git blob and I4-1b's control were caught only incidentally).
REPORT_CASES = [
    ("I0-1", "an extra member", lambda r, L: r["archive"]["listing"].append(
        {"name": "litecore/lib/Extra.php", "type": "file", "mode": "0o644", "sha256": "0" * 64}), "members differ"),
    ("I0-2", "a member that is not its git blob", lambda r, L: next(
        e for e in r["archive"]["listing"] if e["name"] == "litecore/appinfo/info.xml").update(sha256="1" * 64),
     "appinfo/info.xml is not the git blob"),
    ("I0-2", "an engine file that is not the host's", lambda r, L: r["archive"]["engineDir"].update(
        {"engine/MANIFEST.json": "2" * 64}), "is not the host's engine file"),
    ("I0-2", "an engine buildId that differs", lambda r, L: r["archive"].update(engineBuildId="0" * 16),
     "engine buildId"),
    ("I0-2", "a record that lists another member", lambda r, L: r["release"]["members"].update(
        {"appinfo/info.xml": "7" * 64}), "member list"),
    ("I0-3", "a rebuild that differs", lambda r, L: r["archive"].update(rebuiltSha256="3" * 64), "builds differ"),
    ("I0-4", "a symlink member", lambda r, L: r["archive"]["listing"].append(
        {"name": "litecore/dist", "type": "symlink", "mode": "0o777"}), "is a symlink"),
    ("I1-1", "enable failed", lambda r, L: r["install"]["enable"].update(exit=1), "enable exit"),
    ("I1-1", "a re-enable, not an install", lambda r, L: r["install"]["before"]["apps"]["apps"].update(
        litecore={"enabled": "no", "installed_version": "0.2.1"}), "app config before"),
    ("I1-2", "a symlink in the installed tree", lambda r, L: r["install"]["tree"].update(links=["engine"]),
     "installed tree"),
    ("I1-2", "an installed root that is a symlink", lambda r, L: r["install"]["tree"].update(isSymlink=True),
     "installed tree"),
    ("I1-2", "an installed file that differs", lambda r, L: r["install"]["tree"]["files"].update(
        {"appinfo/info.xml": "8" * 64}), "installed tree"),
    ("I1-2", "a FIFO in the installed tree", lambda r, L: r["install"]["tree"].update(
        others=["special file lib/pipe"]), "installed tree"),
    ("I1-2", "the tree drifted by the window", lambda r, L: r["binding"].update(
        hostDirty="changed js/litecore-editor.js"), "at the window"),
    ("I1-2", "served from another app path at install", lambda r, L: r["install"].update(
        getpath="/var/www/html/nextcloud/apps/litecore"), "at install"),
    ("I1-2", "served from another app path at the window", lambda r, L: r.update(
        getpath="/var/www/html/nextcloud/apps/litecore"), "at window"),
    ("I1-2", "a self-test that reads a clean copy dirty", lambda r, L: r["bindingSelftest"]["clean"].update(
        hostDirty="changed x"), "a clean copy"),
    *[("I1-2", f"a binding blind to {case}", _selftest_blind(case), f": {case} reads clean")
      for case in SELFTEST_DRIFTS],
    ("I1-3", "system config changed", lambda r, L: r["install"]["after"]["system"].setdefault("system", {}).update(
        debug=True), "system config"),
    ("I1-4", "the probe app turned on", lambda r, L: r["window"]["probeAfter"].update(files_probe="on"),
     "at window end"),
    ("I2-1", "the dev instance was reached", lambda r, L: r["window"]["devLogLines"].append(
        '172.24.0.5 - - [29/Sep/2026:10:00:00 +0800] "GET /apps/litecore/r/x HTTP/1.1" 200 1 "-" "Chrome"'),
     "was reached"),
    ("I2-1", "the dev log read nothing", lambda r, L: r["window"].update(devLogLines=[]), "health checks read"),
    ("I2-1", "the window opened right after dev traffic", lambda r, L: r["window"]["devQuiet"].update(
        quietSeconds=5), "the window opened"),
    ("I2-1", "the dev log read too early", lambda r, L: r["window"].update(devLogRead=r["window"]["end"] + 10),
     "read before 60 s"),
    ("I2-2", "a runner on the dev instance", lambda r, L: L["versions"].update(baseUrl=DEV_URL), "versions ran against"),
    ("I2-3", "a dist file held open", lambda r, L: _inject(r, [[999992, 1, "apache2", "/usr/sbin/apache2", START]],
                                                          [[999992, 17, 1, "/usr/sbin/apache2"]]), "I2-3 apache2"),
    ("I2-3", "a holder ps missed", lambda r, L: _inject(r, [], [[999994, 17, 1, "php-fpm: pool www"]]),
     "I2-3 php-fpm"),
    ("I2-3", "no fd control", lambda r, L: r["window"]["controls"]["fd"].update(start=0, end=0), "(lcfd) was not seen"),
    ("I2-4", "the probe app served a file", lambda r, L: r["window"]["probeLog"]["probeApp"].append(
        '172.24.0.5 - - [x] "GET /index.php/apps/litecoreprobe/r/php/app.js HTTP/1.1" 200 1 "-" "Chrome"'),
     "the probe app served"),
    ("I2-4", "the probe log read nothing", lambda r, L: r["window"]["probeLog"].update(engineRoute=0),
     "no engine request"),
    ("I3", "a runner with no report", lambda r, L: L.update(assets=None), "assets: no report"),
    ("I3-1", "an assets run died", lambda r, L: L["assets"]["runs"][-1].update(fatal="Traceback: mutated"), "assets:"),
    ("I3-2", "a versions run died", lambda r, L: L["versions"]["runs"][-1].update(fatal="Traceback: mutated"),
     "versions:"),
    ("I3-3", "a locks run died", lambda r, L: L["locks"]["runs"][-1].update(fatal="Traceback: mutated"), "locks:"),
    ("I3-4", "a host-entry run died", lambda r, L: L["host-entry"]["browsers"]["firefox"]["open-save"][-1].update(
        fatal="Traceback: mutated"), "host-entry:"),
    ("I3-5", "a report bound to a dirty tree", lambda r, L: L["locks"].update(hostDirty="changed lib/x.php"),
     "locks is not bound"),
    ("I3-5", "a report from before the window", lambda r, L: L["versions"].update(
        startedAt="2026-01-01T00:00:00+00:00"), "not made inside the window"),
    ("I3-6", "red cases that stayed green", lambda r, L: r["runners"]["assets"]["redCases"].update(exit=1),
     "assets: red cases"),
    ("I3-6", "a report rewritten after the run", lambda r, L: r["runners"]["assets"].update(reportSha256="5" * 64),
     "assets: red cases"),
    ("I3-7", "the dev host entry did not land", lambda r, L: L["dev-host-entry"]["browsers"]["chrome"]["open-save"][
        -1].update(fatal="Traceback: mutated"), "dev host entry: NOT LANDS"),
    ("I3-7", "the dev report is from another instance", lambda r, L: L["dev-host-entry"]["instance"].update(
        baseUrl=PROBE_URL), "dev host entry ran against"),
    ("I3-7", "the dev report on another commit", lambda r, L: L["dev-host-entry"]["instance"]["app"].update(
        commit="0" * 40), "dev host entry is bound to"),
    ("I3-7", "dev red cases that stayed green", lambda r, L: r["devHostEntry"]["redCases"].update(exit=1),
     "red cases did not"),
    ("I3-7", "the dev host entry ran inside the window", lambda r, L: L["dev-host-entry"].update(
        completedAt=datetime.datetime.fromtimestamp(_mid(r), datetime.UTC).isoformat()), "did not finish before"),
    ("I3-7", "no dev host-entry report", lambda r, L: L.update({"dev-host-entry": None}), "no host-entry report"),
    ("I3-7", "a dev run with an unchecked runner", lambda r, L: L["dev-host-entry"]["runner"].update(sha256="9" * 64),
     "ran with runner 999999999999"),
    ("I3-8", "a report scoring differently", lambda r, L: r["equivalence"]["rows"][0]["after"].update(exit=9), "->"),
    ("I3-8", "a report whose red cases now pass", lambda r, L: r["equivalence"]["rows"][0]["after"].update(
        redExit=1), "->"),
    ("I3-8", "equivalence missing a runner", lambda r, L: r["equivalence"].update(
        rows=[x for x in r["equivalence"]["rows"] if x["runner"] != "locks"]), "equivalence covers"),
    ("I3-8", "a changed recording path", lambda r, L: r["equivalence"]["recording"]["after"].update(hostDirty="x"),
     "recording path changed"),
    ("I3-8", "an old expression not found in PRE", lambda r, L: r["equivalence"]["transcription"][
        "check_m3_locks.py"].update(hostDirty=False), "not transcribed"),
    ("I3-8", "a counted run with an unchecked runner", lambda r, L: L["assets"].update(runnerSha256="4" * 64),
     "ran with runner"),
    ("I3-8", "a module changed after the check", lambda r, L: r["moduleSha256End"].update(
        {"check_m3_skeleton_open.py": "6" * 64}), "tools changed"),
    ("label", "a shakedown scored as counted", lambda r, L: r.update(label="rehearsal"), "label"),
    # the tree binding (fable's ruling, conditions 12 and 13)
    ("I3-8", "wasm_sdk_probe changed by the window start", lambda r, L: r["treeBindingStart"].update(tree="0" * 40),
     "changed between"),
    ("I3-8", "uncommitted tools at the window end", lambda r, L: r["treeBindingEnd"].update(
        porcelain=" M wasm_sdk_probe/tools/x.py"), "uncommitted ' M"),
    ("I3-8", "another last commit at the window end", lambda r, L: r["treeBindingEnd"].update(lastCommit="1" * 40),
     "changed between"),
    ("I3-8", "another interpreter at the window start", lambda r, L: r["treeBindingStart"].update(node="v0.0.0"),
     "changed between"),
    ("I3-7", "the dev run started before the equivalence check", lambda r, L: L["dev-host-entry"].update(
        startedAt="2026-01-01T00:00:00+00:00"), "started 2026-01-01T00:00:00+00:00 before the equivalence check"),
    ("I4-1a", "a shell under php-fpm", lambda r, L: _inject(r, [[999991, _fpm(r), "sh", "sh -c soffice --headless",
                                                               START]]), "I4-1a sh "),
    ("I4-1a", "php-fpm forked by a worker", lambda r, L: _inject(r, [[999997, _worker(r), "php-fpm",
                                                                    "php-fpm: pool www", START]]), "I4-1a php-fpm"),
    ("I4-1a", "no fpm-child control", lambda r, L: r["window"]["controls"]["process"].update(start=0, end=0),
     "(sleep) was not seen"),
    ("I4-1b", "a daemon left to PID 1", lambda r, L: _inject(r, [[999993, 1, "soffice.bin", "soffice.bin --headless",
                                                                 START]]), "I4-1b soffice.bin"),
    ("I4-1b", "a baseline name under a new pid", lambda r, L: _inject(r, [[999995, 1, "cat", "cat", START]]),
     "I4-1b cat"),
    ("I4-1b", "a grandchild of PID 1", lambda r, L: _inject(r, [[999996, _pid1_child(r), "soffice.bin",
                                                                "soffice.bin --headless", START]]), "I4-1b soffice.bin"),
    ("I4-1b", "the orphan control not seen", lambda r, L: _drop(r, "lcorphan"), "(lcorphan) was not seen"),
    # control 4 (fable's ruling, condition 6)
    ("I2-3", "control 4's worker fd not seen", lambda r, L: _drop_fds(r, _worker_of(r)), "(worker) was not seen"),
    ("I2-3", "control 4 reporting another worker", lambda r, L: r["window"]["controls"]["fpm"].update(
        worker=_worker_of(r) + 100000), "I2-3 php-fpm"),
    ("I2-3", "control 4's worker holding another mount file", lambda r, L: _retarget(
        r, _worker_of(r), f"{MOUNT}/other.js"), f"holding {MOUNT}/other.js"),
    ("I4-1b", "control 4's orphan not seen", lambda r, L: _drop(r, "lcorphan4"), "(lcorphan4) was not seen"),
    ("I4-1a", "control 4's child not seen", lambda r, L: _drop(r, "lcfg"), "(lcfg) was not seen"),
    ("I4-1a", "control 4's worker under a fake master", lambda r, L: _reparent(r, _worker_of(r), 0),
     "(lcfg) was not seen"),
    ("I4-1a", "control 4's span moved", lambda r, L: r["window"]["controls"]["fpm"].update(start=1.0, end=2.0),
     "I4-1a lcfg (pid"),
    # review 3: branches no case pinned, and this round's new ones
    ("I4-1a", "control 4's worker below a php-fpm started by docker exec", lambda r, L: _fake_master(r, "php-fpm", 0),
     "(lcfg) was not seen"),
    ("I4-1a", "control 4's worker below something not php-fpm", lambda r, L: _fake_master(r, "supervisord", 16),
     "(lcfg) was not seen"),
    ("I4-1a", "lcfg below a php-fpm that is not the worker", lambda r, L: _lcfg_below_another_fpm(r),
     "(lcfg) was not seen"),
    ("I4-1a", "a violation inside control 1's span", lambda r, L: _inject_at(
        r, r["window"]["controls"]["process"]["start"] + 1, [[999981, _fpm(r), "sh", "sh -c soffice", START, 1]]),
     "I4-1a sh (pid 999981"),
    ("I4-1b", "a violation inside control 4's span", lambda r, L: _inject_at(
        r, r["window"]["controls"]["fpm"]["start"] + 2, [[999982, 1, "soffice.bin", "soffice.bin --headless", START, 1]]),
     "I4-1b soffice.bin (pid 999982"),
    ("I4-1a", "a child of control 4's worker that is not the control's", lambda r, L: _inject_at(
        r, r["window"]["controls"]["fpm"]["start"] + 1, [[999983, _worker_of(r), "soffice", "soffice --headless",
                                                          START, 1]]), "I4-1a soffice (pid 999983"),
    ("I4-1a", "a php-fpm fork of the worker after its request", lambda r, L: _inject_at(
        r, r["window"]["controls"]["fpm"]["returned"] + 2.5, [[999985, _worker_of(r), "php-fpm", "php-fpm: pool www",
                                                               START, 1]]), "I4-1a php-fpm (pid 999985"),
    ("I2-3", "the worker's fd after its request returned", lambda r, L: r["window"]["controls"]["fpm"].update(
        returned=r["window"]["controls"]["fpm"]["start"] - 5), "I2-3 php-fpm (pid"),
    ("I4-1b", "control 4's orphan not a direct child of PID 1", lambda r, L: _rows(
        r, lambda row, rows: [row[0], 8, *row[2:]] if row[2] == "lcorphan4" else row), "(lcorphan4) was not seen"),
    ("I4-1b", "control 4 reporting another orphan", lambda r, L: r["window"]["controls"]["fpm"].update(
        orphan=r["window"]["controls"]["fpm"]["orphan"] + 100000), "(lcorphan4) was not seen"),
    ("I4-1b", "control 1's orphan not a direct child of PID 1", lambda r, L: _rows(
        r, lambda row, rows: [row[0], 8, *row[2:]] if row[2] == "lcorphan" else row), "(lcorphan) was not seen"),
    ("I4-1b", "the baseline's cat restarted", lambda r, L: _window_rows(
        r, lambda row: [*row[:5], row[5] + 1] if row[0] == 8 else row), "I4-1b cat (pid 8"),
    ("I4-1b", "the baseline's cat renamed", lambda r, L: _window_rows(
        r, lambda row: [row[0], row[1], "soffice.bin", *row[3:]] if row[0] == 8 else row), "I4-1b soffice.bin (pid 8"),
    ("I4-1b", "no container start recorded", lambda r, L: (r["window"].update(webStartedAt=""),
                                                           r["install"].update(webStartedAt="")), "not one lifetime"),
    ("I4-1", "a baseline descendant started after the container", lambda r, L: _late_baseline(r),
     "whitelists what started after the container"),
    ("I4-1", "no clock-tick rate recorded", lambda r, L: r["install"].update(hz=None), "no clock-tick rate"),
    ("I3-5", "host entry bound to a dirty tree", lambda r, L: L["host-entry"]["instance"]["app"].update(
        dirty=["M lib/x.php"]), "host-entry is not bound"),
    ("I3-5", "host entry bound to another commit", lambda r, L: L["host-entry"]["instance"]["app"].update(
        commit="0" * 40), "host-entry is not bound"),
    ("I3-8", "host entry with an unchecked runner", lambda r, L: L["host-entry"]["runner"].update(sha256="4" * 64),
     "host-entry ran with runner 444444444444"),
    ("I3-8", "a recording path that errored on both sides", lambda r, L: r["equivalence"]["recording"].update(
        before={"error": "x"}, after={"error": "x"}), "recording path changed"),
    ("I3-8", "an equivalence row without its red-case exit", lambda r, L: [
        side.pop("redExit") for side in (r["equivalence"]["rows"][0]["before"], r["equivalence"]["rows"][0]["after"])],
     "no red-case exit recorded"),
    ("I4-1b", "the container restarted since the baseline", lambda r, L: r["window"].update(
        webStartedAt="2026-01-01T00:00:00Z"), "not one lifetime"),
    ("I4-1", "no pre-install baseline", lambda r, L: r["install"].update(baseline=[]), "pre-install baseline"),
    ("I4-1", "a baseline too short", lambda r, L: r["install"].update(baseline=r["install"]["baseline"][:10]),
     "pre-install baseline"),
    ("I4-2", "a third of the samples", lambda r, L: r.update(samples=expand(r["samples"])[::3]), "samples over"),
    ("I4-2", "a 1.6 s blackout", lambda r, L: _blackout(r), "widest gap"),
    ("I4-2", "a sample without php-fpm", lambda r, L: _inject(r, []) or next(
        s for s in r["samples"] if s["t"] == _mid(r) + 0.001).update(
        rows=[row for row in expand(r["samples"])[0]["rows"] if row[2] != "php-fpm"]), "no php-fpm"),
    ("I4-3", "a new container", lambda r, L: r["window"]["dockerAfter"].append("ddev-other-web\timage\tnow\trunning"),
     "containers changed"),
    ("I4-3", "a container started", lambda r, L: r["window"]["lifecycleEvents"].append(
        json.dumps({"Action": "start", "Actor": {"Attributes": {"name": "oxool-dev"}}})), "oxool-dev"),
    ("I4-3", "the event stream saw nothing", lambda r, L: r["window"].update(lifecycleEvents=[]),
     "window's start was not streamed"),
    ("I4-3", "a stream that died before the end", lambda r, L: r["window"].update(lifecycleEvents=[
        line for line in r["window"]["lifecycleEvents"] if "litecore-ctl-events-end" not in line]),
     "window's end was not streamed"),
    ("I4-3", "a stream not running when stopped", lambda r, L: r["window"].update(lifecycleAlive=False),
     "not running when stopped"),
]
# Clauses only a counted run is scored on; a shakedown shows them red with --strict.
STRICT_ONLY = {"a counted run with an unchecked runner", "a module changed after the check",
               "a dev run with an unchecked runner", "no dev host-entry report", "a shakedown scored as counted",
               "wasm_sdk_probe changed by the window start", "uncommitted tools at the window end",
               "another last commit at the window end", "another interpreter at the window start",
               "host entry with an unchecked runner"}


def red_cases(path: Path, force_strict: bool) -> int:
    """Each mutation must add a problem, under its own clause, to what the
    report already has -- so a report that is not clean (a shakedown scored
    strictly) can still show every strict branch going red."""
    report = json.loads(path.read_text())
    loaded = load_reports(report)
    strict = force_strict or report.get("label") == "counted"
    base = set(score(report, strict, copy.deepcopy(loaded))["problems"])
    if base:
        print(f"  base report has {len(base)} problems; judging each mutation by the problems it adds")
    failures = skipped = 0
    for clause, label, mutate, expect in REPORT_CASES:
        r, L = copy.deepcopy(report), copy.deepcopy(loaded)
        if label in STRICT_ONLY and not strict:
            print(f"  SKIP   {clause} {label}: a counted-run clause, not scored on a shakedown")
            skipped += 1
            continue
        try:
            mutate(r, L)
        except (KeyError, IndexError, StopIteration, TypeError, AttributeError) as error:
            print(f"  FAIL   {clause} {label}: the mutation does not apply to this report ({type(error).__name__})")
            failures += 1
            continue
        found = [p for p in score(r, strict, L)["problems"] if p not in base and expect in p
                 and (p.startswith(clause + " ") or p.startswith(clause + "-"))]
        print(f"  {'red ' if found else 'GREEN'}  {clause} {label}")
        failures += 0 if found else 1
    print(f"{len(REPORT_CASES) - failures - skipped} of {len(REPORT_CASES)} red, {skipped} skipped, {failures} failed")
    return 0 if failures == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=("install", "equivalence", "selftest", "run"))
    parser.add_argument("--reinstall", action="store_true")
    parser.add_argument("--label", choices=("shakedown", "counted"))
    parser.add_argument("--dev-host-entry", help="a counted host-entry report from the dev instance (I3-7)")
    parser.add_argument("--runners", default=",".join(RUNNERS), help="shakedown only")
    parser.add_argument("--repeats", type=int, default=1, help="shakedown only")
    parser.add_argument("--locks-arms", default=None, help="shakedown only")
    parser.add_argument("--score", type=Path)
    parser.add_argument("--red-cases", type=Path)
    parser.add_argument("--strict", action="store_true", help="red cases: score a shakedown report strictly")
    args = parser.parse_args()
    if args.red_cases:
        return red_cases(args.red_cases, args.strict)
    if args.score:
        report = json.loads(args.score.read_text())
        result = score(report, strict=report.get("label") == "counted")
        print(one_line(result))
        return 0 if result["verdict"] in ("INSTALLS ELSEWHERE", "clean") else 1
    if args.command == "install":
        return install(args.reinstall)
    if args.command == "equivalence":
        return equivalence()
    if args.command == "selftest":
        print(json.dumps(selftest(), indent=1))
        return 0
    if args.command == "run" and args.label:
        return run(args)
    parser.error("install | equivalence | selftest | run --label … | --score | --red-cases")
    return 2


if __name__ == "__main__":
    sys.exit(main())
