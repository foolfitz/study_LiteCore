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
    DEFAULT_DDEV, RELEASE_RECORD, HOST_FILES, Instance, host_binding, installed_app, tree_listing)
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
# INTERVAL s, the container's clock, ps, and every fd open on the dist mount
# with its holder's ppid and command line (a holder forked between ps and find
# has no ps row -- the second shakedown's control `sleep`).  A docker exec per
# sample was slowed to 1.6 s by the controls' own execs in the same shakedown.
LOOP = (f"while :; do echo {MARK}T $(date +%s.%N); ps -eo pid=,ppid=,comm=,args=; echo {MARK}F; "
        "find /proc/[0-9]*/fd -lname '*litecore-dist*' 2>/dev/null | while read f; do "
        "p=${f#/proc/}; p=${p%%/*}; "
        "echo \"$f $(cut -d' ' -f4 /proc/$p/stat 2>/dev/null) $(tr '\\0' ' ' </proc/$p/cmdline 2>/dev/null | cut -c1-160)\"; "
        f"done; echo {MARK}E; sleep {INTERVAL}; done")
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
EXEC_FAMILY = re.compile(r"\b(exec|shell_exec|system|passthru|proc_open|popen|pcntl_exec)\s*\(|`")


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


def epoch(iso: str | None) -> float | None:
    try:
        return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


# --------------------------------------------------------------------------
# the sampler (I4, I2-3)


def parse_block(lines: list[str]) -> tuple[float, list[list[Any]], list[list[Any]]]:
    """One block of LOOP's output: its clock, the container's processes (the
    sampler's own shell and everything below it left out), the fds."""
    stamp = float(lines[0].split()[1])
    split = lines.index(f"{MARK}F")
    raw = []
    for line in lines[1:split]:
        parts = line.split(None, 3)
        if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
            raw.append([int(parts[0]), int(parts[1]), parts[2], (parts[3] if len(parts) > 3 else "")[:160]])
    by_pid = {r[0]: r for r in raw}
    rows = [r for r in raw if not any(MARK in a[3] for a in lineage(by_pid, r[0]))]
    fds = []
    for line in lines[split + 1:]:
        match = re.match(r"/proc/(\d+)/fd/(\d+) (\d*) ?(.*)$", line.strip())
        if match:
            fds.append([int(match.group(1)), int(match.group(2)),
                        int(match.group(3)) if match.group(3) else None, match.group(4)[:160]])
    return stamp, rows, fds


class Sampler(threading.Thread):
    """LOOP's output, one sample per block.  A sample equal to the previous one
    is stored as `same` (lossless); `r` is when the host read it."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.samples: list[dict[str, Any]] = []
        self.halt = threading.Event()
        self.process = subprocess.Popen(["docker", "exec", WEB, "sh", "-c", LOOP], stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)

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


def baseline_orphans(samples: list[dict[str, Any]]) -> set[str]:
    """I4-1b's set: the names of PID 1's children before the app was installed."""
    return {r[2] for s in expand(samples) for r in s["rows"] if r[1] == 1}


def process_findings(sample: dict[str, Any], orphans_ok: set[str]) -> list[dict[str, Any]]:
    """I4-1a: below a php-fpm process, not php-fpm.  I4-1b: a child of PID 1
    (where every orphan goes) whose name PID 1's children did not have before
    the install.  I2-3: an open file under the dist mount."""
    by_pid = {r[0]: r for r in sample["rows"]}
    found = []
    for row in sample["rows"]:
        chain = lineage(by_pid, row[0])
        fpm = next((r for r in chain[1:] if r[2] == "php-fpm"), None)
        if fpm is not None and row[2] != "php-fpm":
            found.append({"rule": "I4-1a", "comm": row[2], "pid": row[0], "args": row[3],
                          "control": is_control(chain), "via": [fpm[0], fpm[3]]})
        if row[1] == 1 and row[2] not in orphans_ok:
            found.append({"rule": "I4-1b", "comm": row[2], "pid": row[0], "args": row[3],
                          "control": is_control(chain)})
    for entry in sample["fds"]:
        # The first two shakedowns' sampler stored [pid, fd] only.
        pid, fd, ppid, cmdline = (list(entry) + [None, ""])[:4]
        # The holder as ps saw it, or as /proc told the loop when ps missed it.
        chain = lineage(by_pid, pid) or [[pid, ppid, None, cmdline], *lineage(by_pid, ppid)]
        found.append({"rule": "I2-3", "pid": pid, "fd": fd, "comm": chain[0][2] or cmdline.split(" ")[0].split("/")[-1],
                      "args": chain[0][3], "control": is_control(chain)})
    return found


def positive_controls() -> dict[str, Any]:
    """What I4-1a, I4-1b and I2-3 must each see: a process named php-fpm with a
    `sleep` child; an orphan (`lcorphan`, a copy of sleep) left to PID 1 when
    that fake php-fpm exits; a shell holding a file of the dist mount open."""
    record: dict[str, Any] = {}
    setup = sh(["docker", "exec", WEB, "sh", "-c",
                f"mkdir -p {CONTROL} && cp /bin/bash {CONTROL}/php-fpm && cp /bin/sleep {CONTROL}/lcorphan"
                f" && cp /bin/bash {CONTROL}/lcfd"])
    started = time.time()
    ran = sh(["docker", "exec", WEB, f"{CONTROL}/php-fpm", "-c", f"{CONTROL}/lcorphan 6 & sleep 2; true"], timeout=60)
    time.sleep(6)
    record["process"] = {"start": round(started, 3), "end": round(time.time(), 3), "exit": ran.returncode}
    started = time.time()
    held = sh(["docker", "exec", WEB, f"{CONTROL}/lcfd", "-c", f"exec 3<{MOUNT}/e2-editor.html; sleep 3; true"],
              timeout=60)
    record["fd"] = {"start": round(started, 3), "end": round(time.time(), 3), "exit": held.returncode}
    image = sh(["docker", "inspect", WEB, "--format", "{{.Config.Image}}"]).stdout.strip()
    started = time.time()
    made = sh(["docker", "create", "--name", "litecore-ctl-events", image, "true"])
    removed = sh(["docker", "rm", "litecore-ctl-events"])
    record["container"] = {"start": round(started, 3), "end": round(time.time(), 3), "name": "litecore-ctl-events",
                           "exits": [made.returncode, removed.returncode]}
    cleaned = sh(["docker", "exec", WEB, "rm", "-rf", CONTROL])
    record["exits"] = [setup.returncode, cleaned.returncode]
    return record


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
    record: dict[str, Any] = {"startedAt": utc_now(), "tool": str(Path(__file__).relative_to(REPO)),
                              "toolSha256": sha256_file(Path(__file__)), "archive": release["archive"],
                              "target": str(target), "removedFirst": removed, "before": snapshot()}
    sampler = Sampler()
    sampler.start()
    time.sleep(BASELINE_SECONDS)
    sampler.stop()
    record["baseline"] = sampler.samples
    with tarfile.open(archive) as bundle:
        bundle.extractall(target.parent, filter="data")
    enabled = sh(["ddev", "occ", "app:enable", "litecore"], cwd=PROBE)
    record["enable"] = {"exit": enabled.returncode, "stdout": enabled.stdout[-2000:], "stderr": enabled.stderr[-2000:]}
    record["after"] = snapshot()
    record["getpath"] = occ("app:getpath", "litecore").strip()
    files, links = tree_listing(target)
    record["tree"] = {"isSymlink": target.is_symlink(), "files": files, "links": links}
    record["completedAt"] = utc_now()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "install.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"enable": record["enable"]["exit"], "files": len(files), "links": links,
                      "baselineSamples": len(record["baseline"]), "getpath": record["getpath"]}))
    return 0 if enabled.returncode == 0 else 1


# --------------------------------------------------------------------------
# equivalence (I3-8) and the binding self-test (I1-2)

OLD_RECORDING = r"""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import check_m3_assets as assets
from check_m3_skeleton_open import DEFAULT_DDEV, Instance
from probe_m3_gate0_coep import sha256_file
git = lambda *a: subprocess.run(["git", *a], cwd=DEFAULT_DDEV, capture_output=True, text=True).stdout.strip()
out = {"hostRepo": git("log", "-1", "--format=%H %s"), "hostDirty": git("status", "--short"),
       "hostFiles": {n: sha256_file(DEFAULT_DDEV / n) for n in (
           "js/litecore-editor.js", "lib/Controller/EditorController.php", "templates/editor.php")},
       "package": assets.package_record(DEFAULT_DDEV),
       "describeApp": Instance(DEFAULT_DDEV).describe()["app"]}
print(json.dumps(out, sort_keys=True))
"""

NEW_RECORDING = r"""
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import check_m3_assets as assets
from check_m3_skeleton_open import DEFAULT_DDEV, Instance, host_binding
b = host_binding(DEFAULT_DDEV)
out = {"hostRepo": b["hostRepo"], "hostDirty": b["hostDirty"], "hostFiles": b["hostFiles"],
       "package": assets.package_record(DEFAULT_DDEV),
       "describeApp": Instance(DEFAULT_DDEV).describe()["app"]}
print(json.dumps(out, sort_keys=True))
"""


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
                    row[side] = {"exit": done.returncode, "line": (done.stdout.strip().splitlines() or [""])[-1]}
                rows.append(row)
        recording = {}
        for side, code, where in (("before", OLD_RECORDING, old_tools), ("after", NEW_RECORDING, TOOLS)):
            done = sh([sys.executable, "-c", code, str(where)], cwd=REPO)
            recording[side] = json.loads(done.stdout) if done.returncode == 0 else {"error": done.stderr[-1500:]}
    record = {"at": utc_now(), "pre": PRE, "head": sh(["git", "rev-parse", "HEAD"], cwd=REPO).stdout.strip(),
              "runnerSha256": {name: sha256_file(TOOLS / tool) for name, (tool, _, _) in RUNNERS.items()},
              "moduleSha256": module_shas(), "rows": rows, "recording": recording}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "equivalence.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    same = sum(1 for r in rows if r["before"] == r["after"])
    print(f"{same}/{len(rows)} reports score the same; recording paths equal: "
          f"{recording['before'] == recording['after'] and 'error' not in recording['before']}")
    return 0 if rows and same == len(rows) and recording["before"] == recording["after"] else 1


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
    report: dict[str, Any] = {
        "tool": str(Path(__file__).relative_to(REPO)), "toolSha256": sha256_file(Path(__file__)),
        "label": args.label, "startedAt": utc_now(), "criteria": "specs/SPEC-M3-install-elsewhere.md §4",
        "release": release, "install": json.loads((EVIDENCE / "install.json").read_text()),
        "equivalence": json.loads((EVIDENCE / "equivalence.json").read_text())
        if (EVIDENCE / "equivalence.json").is_file() else None,
        "archive": archive_records(release), "binding": binding, "bindingSelftest": selftest(),
        "getpath": occ("app:getpath", "litecore").strip(), "moduleSha256Start": module_shas(),
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
                              "probeLogOffset": log_size(PROBE)}
    lifecycle = Lifecycle()
    lifecycle.start()
    sampler = Sampler()
    sampler.start()
    time.sleep(2)
    window["start"] = round(time.time(), 3)
    window["controls"] = positive_controls()
    report["window"] = window
    report["runners"] = {}
    try:
        names = list(RUNNERS) if counted else args.runners.split(",")
        for name in names:
            extra = [] if counted else ["--repeats", str(args.repeats),
                                        *(["--arms", args.locks_arms] if name == "locks" and args.locks_arms else [])]
            print(f"{name} …", flush=True)
            report["runners"][name] = run_runner(name, args.label, extra)
            print(f"  exit {report['runners'][name]['exit']} {report['runners'][name]['report']}", flush=True)
            out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    finally:
        window["end"] = round(time.time(), 3)
        time.sleep(2)
        sampler.stop()
        lifecycle.stop()
        window["lifecycleEvents"] = lifecycle.lines
        window["dockerAfter"] = docker_set()
        window["probeAfter"] = probe_switches()
        probe_lines = log_since(PROBE, window["probeLogOffset"])
        window["probeLog"] = {"lines": len(probe_lines),
                              "engineRoute": sum(1 for line in probe_lines if "/apps/litecore/r/" in line),
                              "probeApp": [line for line in probe_lines if "/litecoreprobe/" in line]}
        time.sleep(QUIET)   # a 408 caused inside the window lands up to 40 s after it
        window["devLogLines"] = log_since(DEFAULT_DDEV, window["devLogOffset"])
        window["devLogRead"] = round(time.time(), 3)
        report["samples"] = sampler.samples
        report["moduleSha256End"] = module_shas()
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
    with contextlib.redirect_stdout(io.StringIO()):
        failures = module.red_cases(REPO / path)
    return int(bool(failures))


def runner_verdict(name: str, body: dict[str, Any], strict: bool = True) -> tuple[bool, str]:
    module = MODULES["host-entry" if name == "dev-host-entry" else name]
    result = module.score(copy.deepcopy(body), strict=strict)
    if RUNNERS.get(name, (None, None, None))[2] is None:
        return bool(result.get("lands")), "LANDS" if result.get("lands") else f"NOT LANDS {result.get('problems')}"
    return (result.get("verdict") == (RUNNERS[name][2] if strict else "clean"),
            f"{result.get('verdict')} {result.get('problems')} {result.get('tally')}")


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
    tree = install.get("tree") or {}
    if tree.get("isSymlink") is not False or tree.get("links") or tree.get("files") != release.get("members"):
        problems.append(f"I1-2 installed tree: symlink {tree.get('isSymlink')}, links {tree.get('links')}, "
                        f"files equal {tree.get('files') == release.get('members')}")
    if (report.get("binding") or {}).get("hostDirty") or not (report.get("binding") or {}).get("hostRepo"):
        problems.append(f"I1-2 at the window: {str((report.get('binding') or {}).get('hostDirty'))[:300]}")
    for label, seen in (("install", install.get("getpath")), ("window", report.get("getpath"))):
        if seen != APP_IN_CONTAINER:
            problems.append(f"I1-2 Nextcloud serves litecore from {seen!r} at {label}")
    selftest_seen = report.get("bindingSelftest") or {}
    if (selftest_seen.get("clean") or {}).get("hostDirty") != "" or not (selftest_seen.get("clean") or {}).get("hostRepo"):
        problems.append(f"I1-2 binding self-test: a clean copy reads {selftest_seen.get('clean')}")
    for case in ("changed", "extra", "missing", "symlink", "root-symlink"):
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
            if not ok or (dev.get("instance") or {}).get("baseUrl") != DEV_URL \
                    or not str(app.get("commit", "")).startswith(commit):
                problems.append(f"I3-7 dev host entry: {verdict[:200]}, {(dev.get('instance') or {}).get('baseUrl')}")
            if (entry.get("redCases") or {}).get("exit") != 0 or red_cases_now(
                    "check_m3_host_entry.py", entry.get("report") or "", entry.get("reportSha256") or "") != 0:
                problems.append("I3-7 dev host entry: red cases did not all go red (or the report changed)")
            if epoch(dev.get("completedAt")) is None or not start or epoch(dev.get("completedAt")) > start:
                problems.append("I3-7 the dev host-entry run did not finish before the window")
            if strict and (dev.get("runner") or {}).get("sha256") != shas_now.get("host-entry"):
                problems.append("I3-7 dev host entry ran with another runner than the one checked")
    rows = equivalence_seen.get("rows") or []
    if strict or rows:
        if {r.get("runner") for r in rows} != set(RUNNERS):
            problems.append(f"I3-8 equivalence covers {sorted({r.get('runner') for r in rows})}")
        for row in rows:
            if row.get("before") != row.get("after"):
                problems.append(f"I3-8 {row.get('runner')} {row.get('report')}: {row.get('before')} -> {row.get('after')}")
        recording = equivalence_seen.get("recording") or {}
        if not recording.get("before") or "error" in recording.get("before", {}) \
                or recording.get("before") != recording.get("after"):
            problems.append("I3-8 the dev-instance recording path changed (host binding, K0 record or description)")
    if strict:
        modules = equivalence_seen.get("moduleSha256") or {}
        for label, seen in (("start", report.get("moduleSha256Start")), ("end", report.get("moduleSha256End"))):
            differ = sorted(n for n in set(modules) | set(seen or {}) if modules.get(n) != (seen or {}).get(n))
            if not modules or differ:
                problems.append(f"I3-8 tools changed between the equivalence check and the window {label}: {differ[:5]}")
    # I4 (and I2-3, which the same sampler reads)
    orphans_ok = baseline_orphans(install.get("baseline") or [])
    baseline_good = expand(install.get("baseline") or [])
    if len(baseline_good) < BASELINE_SECONDS or not orphans_ok:
        problems.append(f"I4-1 the pre-install baseline has {len(baseline_good)} samples, orphan names {sorted(orphans_ok)}")
    controls = window.get("controls") or {}
    spans = {rule: controls.get(key) or {} for rule, key in (("I4-1a", "process"), ("I4-1b", "process"),
                                                            ("I2-3", "fd"))}
    good = [s for s in expand(report.get("samples") or []) if start and end and start <= s["t"] <= end]
    seen_control: set[str] = set()
    for sample in good:
        for bad in process_findings(sample, orphans_ok):
            span = spans[bad["rule"]]
            if bad["control"] and span.get("start", 0) - 1 <= sample["t"] <= span.get("end", 0) + 1:
                seen_control.add(f"{bad['rule']} {bad['comm']}")
            else:
                problems.append(f"{bad['rule']} {bad['comm']} (pid {bad['pid']}, {str(bad['args'])[:80]!r}) at {sample['t']}"
                                + (f" under php-fpm {bad['via']}" if bad.get("via") else ""))
    for wanted in ("I4-1a sleep", "I4-1b lcorphan", "I2-3 lcfd"):
        if wanted not in seen_control:
            problems.append(f"{wanted.split()[0]} the positive control ({wanted.split()[1]}) was not seen")
    stamps = [start] + [s["t"] for s in good] + [end] if start and end else []
    widest = max((b - a for a, b in zip(stamps, stamps[1:])), default=None)
    if not start or not end or len(good) < (end - start) or widest is None or widest > GAP:
        problems.append(f"I4-2 {len(good)} samples over {round((end or 0) - (start or 0))} s, widest gap {widest}")
    if any(not any(r[2] == "php-fpm" for r in s["rows"]) for s in good):
        problems.append("I4-2 a sample with no php-fpm process")
    if not window.get("dockerBefore") or window.get("dockerBefore") != window.get("dockerAfter"):
        problems.append(f"I4-3 containers changed: {sorted(set(window.get('dockerBefore') or []) ^ set(window.get('dockerAfter') or []))[:4]}")
    events = [json.loads(line) for line in window.get("lifecycleEvents") or [] if line.startswith("{")]
    name_of = lambda e: ((e.get("Actor") or {}).get("Attributes") or {}).get("name")  # noqa: E731
    ctl = controls.get("container") or {}
    if not any(name_of(e) == ctl.get("name") and e.get("Action") == "create" for e in events):
        problems.append("I4-3 the positive control's container create was not streamed")
    others = [f"{e.get('Action')} {name_of(e)}" for e in events if name_of(e) != ctl.get("name")]
    if others:
        problems.append(f"I4-3 container lifecycle events in the window: {others[:5]}")
    if strict and report.get("label") != "counted":
        problems.append(f"label {report.get('label')!r}")
    ok = not problems
    return {"verdict": ("INSTALLS ELSEWHERE" if ok else "DOES NOT INSTALL ELSEWHERE") if strict
            else ("clean" if ok else "red"), "problems": problems, "samples": len(good),
            "controlsSeen": sorted(seen_control)}


def one_line(result: dict[str, Any]) -> str:
    return f"{result['verdict']} samples={result['samples']} problems={result['problems'][:6]}"


# --------------------------------------------------------------------------
# red cases: one mutation per clause; each must add a problem under that clause


def _mid(r: dict[str, Any]) -> float:
    return round((r["window"]["start"] + r["window"]["end"]) / 2, 3)


def _inject(r: dict[str, Any], extra_rows: list[list[Any]], extra_fds: list[list[int]] = ()) -> None:
    base = next(s for s in expand(r["samples"]) if s["t"] >= _mid(r))
    r["samples"] = [s for s in expand(r["samples"])]
    r["samples"].append({"t": _mid(r) + 0.001, "rows": base["rows"] + extra_rows, "fds": base["fds"] + list(extra_fds)})
    r["samples"].sort(key=lambda s: s["t"])


def _fpm(r: dict[str, Any]) -> int:
    return next(row[0] for s in expand(r["samples"]) for row in s["rows"] if row[2] == "php-fpm")


def _blackout(r: dict[str, Any]) -> None:
    good = expand(r["samples"])
    mid = _mid(r)
    r["samples"] = [s for s in good if not mid <= s["t"] <= mid + 1.6]


REPORT_CASES = [
    ("I0-1", "an extra member", lambda r, L: r["archive"]["listing"].append(
        {"name": "litecore/lib/Extra.php", "type": "file", "mode": "0o644", "sha256": "0" * 64})),
    ("I0-2", "a member that is not its git blob", lambda r, L: next(
        e for e in r["archive"]["listing"] if e["name"] == "litecore/appinfo/info.xml").update(sha256="1" * 64)),
    ("I0-2", "an engine file that is not the host's", lambda r, L: r["archive"]["engineDir"].update(
        {"engine/MANIFEST.json": "2" * 64})),
    ("I0-3", "a rebuild that differs", lambda r, L: r["archive"].update(rebuiltSha256="3" * 64)),
    ("I0-4", "a symlink member", lambda r, L: r["archive"]["listing"].append(
        {"name": "litecore/dist", "type": "symlink", "mode": "0o777"})),
    ("I1-1", "enable failed", lambda r, L: r["install"]["enable"].update(exit=1)),
    ("I1-2", "a symlink in the installed tree", lambda r, L: r["install"]["tree"].update(links=["engine"])),
    ("I1-2", "the tree drifted by the window", lambda r, L: r["binding"].update(hostDirty="changed js/litecore-editor.js")),
    ("I1-2", "served from another app path", lambda r, L: r.update(getpath="/var/www/html/nextcloud/apps/litecore")),
    ("I1-2", "a binding that cannot see a root symlink", lambda r, L: r["bindingSelftest"]["root-symlink"].update(
        hostDirty="", hostRepo="x")),
    ("I1-3", "system config changed", lambda r, L: r["install"]["after"]["system"].setdefault("system", {}).update(
        debug=True)),
    ("I1-4", "the probe app turned on", lambda r, L: r["window"]["probeAfter"].update(files_probe="on")),
    ("I2-1", "the dev instance was reached", lambda r, L: r["window"]["devLogLines"].append(
        '172.24.0.5 - - [29/Sep/2026:10:00:00 +0800] "GET /apps/litecore/r/x HTTP/1.1" 200 1 "-" "Chrome"')),
    ("I2-1", "the dev log read nothing", lambda r, L: r["window"].update(devLogLines=[])),
    ("I2-1", "the window opened right after dev traffic", lambda r, L: r["window"]["devQuiet"].update(quietSeconds=5)),
    ("I2-2", "a runner on the dev instance", lambda r, L: L["versions"].update(baseUrl=DEV_URL)),
    ("I2-3", "a dist file held open", lambda r, L: _inject(r, [[999992, 1, "apache2", "/usr/sbin/apache2"]],
                                                          [[999992, 17, 1, "/usr/sbin/apache2"]])),
    ("I2-3", "a holder ps missed", lambda r, L: _inject(r, [], [[999994, 17, 1, "php-fpm: pool www"]])),
    ("I2-3", "no fd control", lambda r, L: r["window"]["controls"]["fd"].update(start=0, end=0)),
    ("I2-4", "the probe app served a file", lambda r, L: r["window"]["probeLog"]["probeApp"].append(
        '172.24.0.5 - - [x] "GET /index.php/apps/litecoreprobe/r/php/app.js HTTP/1.1" 200 1 "-" "Chrome"')),
    ("I2-4", "the probe log read nothing", lambda r, L: r["window"]["probeLog"].update(engineRoute=0)),
    ("I3-1", "an assets run died", lambda r, L: L["assets"]["runs"][-1].update(fatal="Traceback: mutated")),
    ("I3-2", "a versions run died", lambda r, L: L["versions"]["runs"][-1].update(fatal="Traceback: mutated")),
    ("I3-3", "a locks run died", lambda r, L: L["locks"]["runs"][-1].update(fatal="Traceback: mutated")),
    ("I3-4", "a host-entry run died", lambda r, L: L["host-entry"]["browsers"]["firefox"]["open-save"][-1].update(
        fatal="Traceback: mutated")),
    ("I3-5", "a report bound to a dirty tree", lambda r, L: L["locks"].update(hostDirty="changed lib/x.php")),
    ("I3-5", "a report from before the window", lambda r, L: L["versions"].update(startedAt="2026-01-01T00:00:00+00:00")),
    ("I3-6", "red cases that stayed green", lambda r, L: r["runners"]["assets"]["redCases"].update(exit=1)),
    ("I3-6", "a report rewritten after the run", lambda r, L: r["runners"]["assets"].update(reportSha256="5" * 64)),
    ("I3-7", "the dev host entry did not land", lambda r, L: L["dev-host-entry"]["browsers"]["chrome"]["open-save"][-1].update(
        fatal="Traceback: mutated")),
    ("I3-7", "the dev host entry ran inside the window", lambda r, L: L["dev-host-entry"].update(
        completedAt=datetime.datetime.fromtimestamp(_mid(r), datetime.UTC).isoformat())),
    ("I3-8", "a report scoring differently", lambda r, L: r["equivalence"]["rows"][0]["after"].update(exit=9)),
    ("I3-8", "a changed recording path", lambda r, L: r["equivalence"]["recording"]["after"].update(hostDirty="x")),
    ("I3-8", "a counted run with an unchecked runner", lambda r, L: L["assets"].update(runnerSha256="4" * 64)),
    ("I3-8", "a module changed after the check", lambda r, L: r["moduleSha256End"].update(
        {"check_m3_skeleton_open.py": "6" * 64})),
    ("I4-1a", "a shell under php-fpm", lambda r, L: _inject(r, [[999991, _fpm(r), "sh", "sh -c soffice --headless"]])),
    ("I4-1a", "no fpm-child control", lambda r, L: r["window"]["controls"]["process"].update(start=0, end=0)),
    ("I4-1b", "a daemon left to PID 1", lambda r, L: _inject(r, [[999993, 1, "soffice.bin", "soffice.bin --headless"]])),
    ("I4-1", "no pre-install baseline", lambda r, L: r["install"].update(baseline=[])),
    ("I4-2", "a third of the samples", lambda r, L: r.update(samples=expand(r["samples"])[::3])),
    ("I4-2", "a 1.6 s blackout", lambda r, L: _blackout(r)),
    ("I4-2", "a sample without php-fpm", lambda r, L: _inject(r, []) or next(
        s for s in r["samples"] if s["t"] == _mid(r) + 0.001).update(
        rows=[row for row in expand(r["samples"])[0]["rows"] if row[2] != "php-fpm"])),
    ("I4-3", "a new container", lambda r, L: r["window"]["dockerAfter"].append("ddev-other-web\timage\tnow\trunning")),
    ("I4-3", "a container started", lambda r, L: r["window"]["lifecycleEvents"].append(
        json.dumps({"Action": "start", "Actor": {"Attributes": {"name": "oxool-dev"}}}))),
    ("I4-3", "the event stream saw nothing", lambda r, L: r["window"].update(lifecycleEvents=[])),
]
STRICT_ONLY = {"a counted run with an unchecked runner", "a module changed after the check"}


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
    for clause, label, mutate in REPORT_CASES:
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
        found = [p for p in score(r, strict, L)["problems"] if p not in base
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
