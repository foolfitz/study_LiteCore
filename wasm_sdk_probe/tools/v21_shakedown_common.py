#!/usr/bin/env python3
"""v21 WASM shakedown, shared instruments S-9 (pre-run checks, browser-run lock) and S-1 (the mirror).

Arms: findings/evidence/link-batch-v21/shakedown/ARMS.md (S-1, S-9; §2 "One browser run at a time",
"Foreign load"), ARMS-item1.md §2.1, §2.9 and §8 D-18 (ruling A'), ARMS-item2.md I-1.  Imported by
both items' runners; the interface is deliberately small:

  S-9   browser_lock(tool, wait_s=0)      context manager; fcntl.flock on BROWSER_LOCK; every tool of
                                          ours that starts a browser holds it (development runs too)
        pre_run_checks()                  KWallet, our processes, Chrome count, load average, top CPU
        foreign_cpu(seconds=2.0)          D-18 A': CPU over 2 s per process OUTSIDE this process's tree;
                                          `ok` is False when one of them used more than 50 % of a core
  S-1   build_mirror(target, ...)         dist/ mirrored; page repointed; lagging shell files from the
                                          tree; snippets injected before the page's module, in order;
                                          extra files added (never overwriting); returns the identity
        served(mirror)                    context manager: web/serve.py on a free port -> base URL
        open_browser(browser, window)     ChromeSession / FirefoxSession at a window size
        close_browser(session)            close, and hard-kill a browser that will not close

Nothing here writes under dist/, runs make, or touches the host.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_e2_c_product_path as pp  # noqa: E402
import run_merge_wasm_shakedown as mws  # noqa: E402

PROJECT = pp.PROJECT
REPO = PROJECT.parent
DIST = PROJECT / "dist"
BROWSER_LOCK = PROJECT / "build" / "v21-shakedown-browser.lock"
PAGE_SOURCE = pp.CUTOVER_PAGE_SOURCE                    # web/e2-editor-app.js (the tree's page)
HTML_SOURCE = PROJECT / "web" / "e2-editor.html"        # the tree's HTML (lags dist/ until v74)
MODULE_ANCHOR = '<script type="module" src="./e2-editor-app.js"></script>'
# SPEC-M3-link-batch-v22 §11.7 step 3 (fable ruling 5): the runners' default profile moves to v22, so a
# mirror built without `page_profile` is v22's.  A binding, not a repair (§34.4 0 / 0).  Tools that mean
# v21 now say so (diag_long_paragraph's v21 pages pass page_profile="e2-editor-v21").
DEFAULT_PROFILE = "e2-editor-v22"

# ARMS.md §1 (measured 2026-10-16).  A mirror that does not reproduce these is not the round's
# page or shell; the builder reports `identityOk` and the judges refuse on the page hash.
# Re-pinned 2026-10-17 after the tree fixes of fable ruling 1 (commit 712f955a; spec §12.3):
# page 3d5112161b23b060... -> 605cf24b3dff5a2d..., shell digest e0252c0b... -> e35923a0...
# (results README, "Identity after the fixes").  The smokes and diagnostics ran on the old pins.
EXPECTED = {
    "e2-editor-v21": {
        "probe.wasm": "db3408f55316bf67345258ce9f7cb58a1cb3777c9aabb9f7790bee69e1599f30",
        "probe.js": "0b6cf02a51aba353d880824ab32254e551a389c58d3c219439c7641f7ce76587",
        "sdk-worker.js": "0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350",
        "sdk-manifest.json": "72067d5a14a3a271137a17aea24317fc6f42380327ec4962ebff475589268f13",
        "pageServed": "605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f",
    },
    # v22 (2026-10-19): the archived link outputs (build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/) and
    # the tree's page after the v22 shell edits (01dd9921) repointed to v22 (build_cutover_page.py, no --write).
    "e2-editor-v22": {
        "probe.wasm": "f7a40bcce073d913e562245b96f32a1051766dda23da0da3911741f03934d49e",
        "probe.js": "dc4c2c84657e350668fbfc0048e2ded9c49ca5076610a6389944cf71ea4ba9af",
        "sdk-worker.js": "0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350",
        "sdk-manifest.json": "000921c176b57174cc1680825c73f878564b3a216e6849dd0d50c8078a9516d5",
        "pageServed": "3b96cb1661aba6de6add989c98c80ab393cd394307763bc6dc28c9440fba82e2",
    },
    "e2-editor-v20": {
        "probe.wasm": "313b08d5cb08589783a3e4d4d03eaee02d26f705ff5da96396ce9010680c5264",
        "sdk-worker.js": "478d0da1dbfcf93615a00025c3c2f9b72c3cfa486d04746f03dea5fcf757b099",
        "sdk-manifest.json": "50aade86f7996ba66c7ca9a3784d9b1074c8d98c05cbe9788902e89cc5a522a0",
    },
}
EXPECTED_SHELL_DIGEST = "e35923a08107662d600d874f6986ef31aa8e8583955386929c26ebec62d82b06"
OURS_PATTERN = "probe_|check_m3|run_e2_c|run_merge|run_v20|run_v21|judge_v21|v21_"
FOREIGN_CPU_LIMIT = 50.0        # % of one core (ARMS.md §2, item 1 §8 D-18 A')
FOREIGN_CPU_SECONDS = 2.0


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


# ------------------------------------------------------------------ S-9: the lock

class LockBusy(RuntimeError):
    """Another browser run of ours holds the lock."""


@contextlib.contextmanager
def browser_lock(tool: str, wait_s: float = 0.0, path: Path = BROWSER_LOCK):
    """Hold the one browser-run lock for the duration of the block.

    Exclusive `fcntl.flock`: released by the kernel when the process dies, so a crashed runner never
    leaves a stale lock.  The holder writes who it is into the file; a refused caller reads that and
    says it.  `wait_s` > 0 polls every 2 s up to that long before refusing.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+", encoding="utf-8")
    deadline = time.monotonic() + max(0.0, wait_s)
    try:
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    handle.seek(0)
                    holder = handle.read().strip()
                    raise LockBusy(f"browser-run lock {path} is held: {holder or 'holder unknown'}")
                time.sleep(2.0)
        holder = {"tool": tool, "pid": os.getpid(), "since": now_iso(), "argv": sys.argv[1:]}
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps(holder))
        handle.flush()
        yield holder
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


# ------------------------------------------------------------------ S-9: pre-run checks

def _run(cmd: list[str]) -> str:
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (done.stdout + done.stderr).strip()
    except Exception as error:  # noqa: BLE001 -- recorded verbatim, never swallowed into a default
        return f"unreadable: {error}"


def kwallet_locked(runner=_run) -> str:
    return runner(["busctl", "--user", "get-property", "org.freedesktop.secrets",
                   "/org/freedesktop/secrets/collection/kdewallet",
                   "org.freedesktop.Secret.Collection", "Locked"])


def _proc_table() -> dict[int, dict]:
    """pid -> {ppid, ticks (utime+stime), comm} for every readable process."""
    out = {}
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            raw = Path(f"/proc/{entry}/stat").read_text()
        except OSError:
            continue
        # comm is in parentheses and may contain spaces; fields after the last ')' are fixed.
        close = raw.rfind(")")
        fields = raw[close + 2:].split()
        try:
            out[int(entry)] = {"ppid": int(fields[1]), "ticks": int(fields[11]) + int(fields[12]),
                               "comm": raw[raw.find("(") + 1:close]}
        except (IndexError, ValueError):
            continue
    return out


def process_tree(root: int, table: dict[int, dict]) -> set[int]:
    """`root` and every descendant (the runner, its server, the browser and their children)."""
    children: dict[int, list[int]] = {}
    for pid, row in table.items():
        children.setdefault(row["ppid"], []).append(pid)
    tree, stack = set(), [root]
    while stack:
        pid = stack.pop()
        if pid in tree:
            continue
        tree.add(pid)
        stack.extend(children.get(pid, []))
    return tree


def _cmdline(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")[:200]
    except OSError:
        return ""


def foreign_cpu(seconds: float = FOREIGN_CPU_SECONDS, limit_pct: float = FOREIGN_CPU_LIMIT,
                root: int | None = None) -> dict:
    """ARMS.md §2 "Foreign load" (item 1 §8 D-18 A'): CPU over `seconds`, per process, for every process
    outside `root`'s tree (default: this process).  `ok` is False when any of them used more than
    `limit_pct` of one core.  The sample is returned whole so a report can keep it."""
    root = os.getpid() if root is None else root
    tick = os.sysconf("SC_CLK_TCK")
    before, t0 = _proc_table(), time.monotonic()
    time.sleep(seconds)
    after, t1 = _proc_table(), time.monotonic()
    elapsed = t1 - t0
    own = process_tree(root, after) | process_tree(root, before)
    rows = []
    for pid, row in after.items():
        if pid not in before:
            continue
        pct = 100.0 * (row["ticks"] - before[pid]["ticks"]) / tick / elapsed
        if pct <= 0.5:
            continue
        rows.append({"pid": pid, "comm": row["comm"], "pct": round(pct, 1), "own": pid in own,
                     "cmd": _cmdline(pid)})
    rows.sort(key=lambda r: -r["pct"])
    foreign = [r for r in rows if not r["own"]]
    over = [r for r in foreign if r["pct"] > limit_pct]
    return {"seconds": round(elapsed, 3), "limitPct": limit_pct, "rootPid": root, "ok": not over,
            "overLimit": over, "topForeign": foreign[:5], "topOwn": [r for r in rows if r["own"]][:5],
            "loadavg": Path("/proc/loadavg").read_text().split()[:3], "at": now_iso()}


def pre_run_checks(runner=_run) -> dict:
    """ARMS-item1.md §2.9: recorded, not assumed.  `refuse` names why a browser must not start."""
    me = str(os.getpid())
    ours = [line for line in runner(["pgrep", "-af", OURS_PATTERN]).splitlines()
            if line.strip() and "pgrep" not in line and line.split(" ", 1)[0] != me
            and not line.split(" ", 1)[-1].startswith(("bash", "/bin/bash", "sh "))]
    locked = kwallet_locked(runner)
    out = {"kwalletLocked": locked, "chromeProcesses": runner(["pgrep", "-c", "chrome"]),
           "firefoxProcesses": runner(["pgrep", "-c", "firefox"]), "oursRunning": ours,
           "loadavg": Path("/proc/loadavg").read_text().split()[:3],
           "topCpu": runner(["ps", "-eo", "pid,pcpu,comm", "--sort=-pcpu"]).splitlines()[:6],
           "at": now_iso()}
    refuse = []
    if locked.strip() == "b true":
        refuse.append("KWallet is locked; headless Chrome would hang")
    if not locked.strip().startswith("b "):
        refuse.append(f"KWallet state unreadable: {locked!r}")
    out["refuse"] = refuse
    return out


# ------------------------------------------------------------------ S-1: the mirror

def inject(html: str, snippets: list[str] | tuple[str, ...]) -> str:
    """Each snippet (a complete <script> block) before the page's module script, in the given order."""
    if html.count(MODULE_ANCHOR) != 1:
        raise SystemExit("the page's module script is not where the instruments expect it (exactly once)")
    for snippet in snippets:
        if not snippet.lstrip().startswith("<script") or not snippet.rstrip().endswith("</script>"):
            raise SystemExit("a snippet must be one complete <script>...</script> block")
    return html.replace(MODULE_ANCHOR, "".join(snippets) + MODULE_ANCHOR, 1)


def build_mirror(target: Path, *, page_profile: str = DEFAULT_PROFILE, snippets=(),
                 extra_files: dict[str, bytes] | None = None, worker_override: bytes | None = None,
                 source_page: str | None = None, shell_from_tree: bool = True,
                 root: Path | None = None) -> dict:
    """ARMS.md S-1.  `target` must not exist.  Returns the identity block (ARMS-item1.md §1).

    page_profile     the profile the page is repointed to (S-5 uses "e2-editor-v20")
    snippets         instrument <script> blocks, injected before the page's module, in order
    extra_files      mirror-relative path -> bytes (fixtures, corpora, harness files); never overwrite
    worker_override  bytes served as the profile's sdk-worker.js (a NON-shipped worker, S-10);
                     the identity then says instrumentedWorker: true
    source_page      the page source to repoint (default: the tree's web/e2-editor-app.js);
                     the 0.2.24 red cases pass dist/e2-editor-app.js
    shell_from_tree  True (the round's shell): the lagging shell files and the HTML from the tree.
                     False (the 0.2.24 red cases): the root's shell and HTML as they are
    root             what the mirror links to (default dist/).  v22 §11.4: the 0.2.24 red case is the
                     0.2.24 host package decompressed, because dist/ has moved on (v74, then v75)
    """
    target = Path(target)
    if target.exists():
        raise SystemExit(f"refusing to build a mirror over an existing path: {target}")
    base = Path(root) if root is not None else DIST
    manifest = base / "profiles" / page_profile / "sdk-manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"no profile {page_profile} in {base}")
    source = source_page if source_page is not None else PAGE_SOURCE.read_text(encoding="utf-8")
    page, pin_before, wasm = pp.repointed_page(source, page_profile, manifest)
    lagging = pp.shell_lagging_source(base) if shell_from_tree else []
    html_source = (HTML_SOURCE if shell_from_tree else base / "e2-editor.html").read_text(encoding="utf-8")
    html_served = inject(html_source, list(snippets))
    overrides: dict[str, bytes] = {"e2-editor-app.js": page.encode("utf-8"),
                                   "e2-editor.html": html_served.encode("utf-8")}
    served_lagging = {}
    for relative in lagging:
        if relative == "web/e2-editor.html":
            served_lagging[relative] = sha256_bytes(html_source.encode("utf-8"))
            continue
        raw = (PROJECT / relative).read_bytes()
        overrides[pp.served_in_dist(relative)] = raw
        served_lagging[relative] = sha256_bytes(raw)
    worker_path = base / "profiles" / page_profile / "sdk-worker.js"
    if worker_override is not None:
        overrides[f"profiles/{page_profile}/sdk-worker.js"] = worker_override
    pp.build_mirror(base, target, overrides)
    extras = {}
    for relative, raw in (extra_files or {}).items():
        path = target / relative
        if path.exists() or path.is_symlink():
            raise SystemExit(f"refusing to overwrite {path} in the mirror")
        # A directory the mirror symlinks INTO dist/ must never be written through: checked before mkdir.
        inside = [ancestor for ancestor in path.parents if ancestor == target or target in ancestor.parents]
        if any(ancestor.is_symlink() for ancestor in inside):
            raise SystemExit(f"refusing to write through a symlinked directory: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        extras[relative] = sha256_bytes(raw)
    profile_hashes = {name: sha256_file(base / "profiles" / page_profile / name)
                      for name in ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json")}
    worker_served = sha256_file(target / "profiles" / page_profile / "sdk-worker.js")
    identity = {
        "treeHead": _run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"]),
        "profile": page_profile, "profileHashes": profile_hashes,
        "workerServedSha256": worker_served,
        "instrumentedWorker": worker_served != profile_hashes["sdk-worker.js"],
        "pageSourceSha256": sha256_bytes(source.encode("utf-8")),
        "pageServedSha256": sha256_bytes(page.encode("utf-8")),
        "pinBefore": pin_before, "pinAfter": wasm[:16],
        "htmlSourceSha256": sha256_bytes(html_source.encode("utf-8")),
        "htmlServedSha256": sha256_bytes(html_served.encode("utf-8")),
        "snippetSha256": [sha256_bytes(s.encode("utf-8")) for s in snippets],
        "laggingServedFromTree": served_lagging,
        "shellDigest": mws.shell_digest(target),
        "extraFiles": extras,
        "shellFromTree": shell_from_tree, "dist": str(base), "mirror": str(target),
    }
    expected = EXPECTED.get(page_profile, {})
    checks = {name: profile_hashes.get(name) == value for name, value in expected.items() if name != "pageServed"}
    if "pageServed" in expected and source_page is None:
        checks["pageServed"] = identity["pageServedSha256"] == expected["pageServed"]
    if source_page is None and shell_from_tree:
        checks["shellDigest"] = identity["shellDigest"] == EXPECTED_SHELL_DIGEST
    identity["identityChecks"] = checks
    identity["identityOk"] = all(checks.values()) and not identity["instrumentedWorker"]
    return identity


# ------------------------------------------------------------------ S-1: serving and browsers

@contextlib.contextmanager
def served(mirror: Path):
    """web/serve.py on a free port over `mirror`; yields the page URL."""
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
                               "--root", str(mirror)], cwd=PROJECT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        yield base
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


def open_browser(browser: str, window: tuple[int, int] = (1400, 1000), firefox_prefs: dict | None = None):
    if browser == "chrome":
        session = pp.ChromeSession("cold")
        session.call("Emulation.setDeviceMetricsOverride",
                     {"width": window[0], "height": window[1], "deviceScaleFactor": 1, "mobile": False})
        return session
    if browser == "firefox":
        os.environ["MOZ_HEADLESS_WIDTH"] = str(window[0])
        os.environ["MOZ_HEADLESS_HEIGHT"] = str(window[1])
        return pp.FirefoxSession("cold", extra_prefs=firefox_prefs) if firefox_prefs else pp.FirefoxSession("cold")
    raise SystemExit(f"unknown browser {browser}")


def close_browser(session) -> dict:
    """Close; kill a browser that would not close (v20 README §6)."""
    out = {}
    try:
        session.close()
    except Exception as error:  # noqa: BLE001
        out["closeError"] = f"{type(error).__name__}: {error}"
    process = getattr(session, "process", None)
    if process is not None and process.poll() is None:
        process.kill()
        out["browserKilled"] = True
    return out


if __name__ == "__main__":
    # `python3 tools/v21_shakedown_common.py --check`: read-only, prints the pre-run checks, a 2 s
    # foreign-CPU sample and whether the lock is free.  Starts no browser.
    print(json.dumps({"preRun": pre_run_checks(), "foreignCpu": foreign_cpu()}, indent=1, ensure_ascii=False))
    try:
        with browser_lock("v21_shakedown_common --check"):
            print("lock: free")
    except LockBusy as error:
        print(f"lock: {error}")
