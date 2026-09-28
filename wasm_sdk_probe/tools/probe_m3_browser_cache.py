#!/usr/bin/env python3
"""M3 asset delivery, step 0, X1 -- which responses does a browser's HTTP
cache keep, by size and by Content-Encoding.

Step 0 (`probe_m3_assets.py`) saw both browsers, cache on, download all 169.6 MB
again on a second open -- including the 115 MB `probe.wasm` Apache serves with
`max-age=15778463`.  The suspect is a per-entry size cap in each browser's disk
cache (Firefox's `browser.cache.disk.max_entry_size`, Chrome's cache size / 8,
where the cache size follows the free space of the profile's disk).  This
measures it instead of assuming it.

Lab files, removed afterwards: `js/cachetest/` in the app's working tree (untracked;
`nc-link` symlinks each top-level entry of the repo, so a new top-level directory
is not served -- the first attempt 404'd on all of them; `js/` is linked), each fetched as
`<file>?v=1` so Nextcloud's own .htaccess sends `max-age=15778463, immutable`:

  ctrl-1k/5m.wasm  positive controls
  rand-<N>m.wasm   N MB of random bytes (incompressible: nothing on the way can
                   shrink them)
  raw.wasm         the shipped probe.wasm as it is served today (115 MB)
  enc-gzip.wasm    the shipped probe.wasm, gzip -9, sent with Content-Encoding gzip
  enc-zstd.wasm    the same, zstd -19, sent with Content-Encoding zstd
  (a lab .htaccess sets those two headers; Apache-only, lab-only)

Per browser profile: from a same-origin page, fetch each file, then each again.
The record of "did the second one reach the server" is the web container's
Apache access log.  Chrome runs twice, profile on /tmp and on /home, because
the suspected cap follows the profile disk's free space.

  probe_m3_browser_cache.py [--ddev DIR]
Report: findings/evidence/m3-assets/browser-cache-<UTC>.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_skeleton_open import DEFAULT_DDEV, Instance  # noqa: E402
from probe_m3_assets import AccessLog  # noqa: E402
from probe_m3_gate0_coep import DIST, EventChrome, firefox_profile, sha256_file, utc_now  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
EVIDENCE = REPO / "findings" / "evidence" / "m3-assets"
WASM = DIST / "profiles" / "e2-editor-v8" / "probe.wasm"
RANDOM_MB = [20, 45, 60, 80, 100, 120]
# Positive controls: small enough for any cache.  A run where these are not
# served from cache the second time says nothing about the big ones.
CONTROL_BYTES = {"ctrl-1k.wasm": 1_000, "ctrl-5m.wasm": 5_000_000}
LAB_HTACCESS = """# lab only (probe_m3_browser_cache.py); removed after the run
<Files "enc-gzip.wasm">
  Header set Content-Encoding gzip
</Files>
<Files "enc-zstd.wasm">
  Header set Content-Encoding zstd
</Files>
"""
FETCH = """(() => { (async () => {
  const out = [];
  for (const name of NAMES) {
    const started = performance.now();
    try {
      const response = await fetch(`URL_BASE${name}?v=1`);
      const body = await response.arrayBuffer();
      out.push({name, status: response.status, decodedBytes: body.byteLength,
                ms: Math.round(performance.now() - started)});
    } catch (error) {
      out.push({name, error: String(error)});
    }
  }
  window.__cachelab = out;
})(); return true; })()"""


def make_files(lab: Path) -> list[dict[str, Any]]:
    lab.mkdir()
    made = []
    for name, size in CONTROL_BYTES.items():
        (lab / name).write_bytes(os.urandom(size))
        made.append(lab / name)
    for mb in RANDOM_MB:
        path = lab / f"rand-{mb}m.wasm"
        with path.open("wb") as out:
            for _ in range(mb):
                out.write(os.urandom(1_000_000))
        made.append(path)
    subprocess.run(f"gzip -9 -c {WASM} > {lab / 'enc-gzip.wasm'}", shell=True, check=True)
    subprocess.run(["zstd", "-19", "-T0", "-q", "-f", str(WASM), "-o", str(lab / "enc-zstd.wasm")], check=True)
    shutil.copyfile(WASM, lab / "raw.wasm")
    made += [lab / "raw.wasm", lab / "enc-gzip.wasm", lab / "enc-zstd.wasm"]
    (lab / ".htaccess").write_text(LAB_HTACCESS)
    return [{"name": p.name, "bytesOnDisk": p.stat().st_size, "sha256": sha256_file(p)} for p in made]


def run_profile(label: str, kind: str, instance: Instance, names: list[str], log: AccessLog,
                profile_parent: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"label": label, "browser": kind, "profileParent": str(profile_parent),
                              "profileDiskFree": shutil.disk_usage(profile_parent).free}
    profile = Path(tempfile.mkdtemp(prefix=f"cachelab-{label}-", dir=profile_parent))
    try:
        session = (EventChrome("warm", profile_dir=profile) if kind == "chrome"
                   else FirefoxSession("warm", profile_dir=firefox_profile(profile)))
        record["version"] = getattr(session, "version", None)
        try:
            navigate(session, instance.base + "/login", timeout=60)
            script = (FETCH.replace("NAMES", json.dumps(names))
                      .replace("URL_BASE", "/apps-extra/litecore/js/cachetest/"))
            for round_ in ("first", "second"):
                # A new document before each round, as reopening the editor is:
                # a fetch repeated inside one document can be answered by that
                # document's own memory cache, which says nothing about the
                # HTTP cache a reopened editor goes through.
                navigate(session, instance.base + ("/login" if round_ == "first" else "/login?again=1"),
                         timeout=60)
                start = log.offset()
                evaluate(session, script)
                deadline = time.monotonic() + 600
                result = None
                while time.monotonic() < deadline:
                    result = evaluate(session, "(() => window.__cachelab || null)()")
                    if result:
                        break
                    time.sleep(0.5)
                evaluate(session, "(() => { window.__cachelab = null; return true; })()")
                time.sleep(1)
                hits = [r for r in log.since(start) if "/cachetest/" in r.get("path", "")]
                record[round_] = {"page": result, "server": [
                    {"path": r["path"].rsplit("/", 1)[-1], "status": r["status"], "sent": r["sent"]}
                    for r in hits]}
        finally:
            session.close()
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ddev", type=Path, default=DEFAULT_DDEV)
    args = parser.parse_args()
    instance = Instance(args.ddev)
    lab = args.ddev / "js" / "cachetest"
    if lab.exists():
        raise SystemExit(f"{lab} exists; remove it first")
    report: dict[str, Any] = {"schema": "m3-browser-cache/1", "startedAt": utc_now(),
                              "probe": sha256_file(Path(__file__)), "baseUrl": instance.base}
    log = AccessLog(instance)
    try:
        report["files"] = make_files(lab)
        names = [f["name"] for f in report["files"]]
        report["wire"] = {}
        for name in names:
            out = subprocess.run(
                ["curl", "-sk", "-o", "/dev/null", "-D", "-", "-H", "Accept-Encoding: gzip, zstd",
                 f"{instance.base}/apps-extra/litecore/js/cachetest/{name}?v=1"],
                capture_output=True, text=True, timeout=120).stdout
            report["wire"][name] = [line for line in out.splitlines()
                                    if line.lower().split(":")[0] in
                                    ("http/2 200", "content-encoding", "content-length", "content-type",
                                     "cache-control") or line.startswith("HTTP/")]
        report["profiles"] = [
            run_profile("chrome-tmp", "chrome", instance, names, log, Path("/tmp")),
            run_profile("chrome-home", "chrome", instance, names, log, PROJECT / "build"),
            run_profile("firefox-home", "firefox", instance, names, log, PROJECT / "build"),
        ]
    finally:
        shutil.rmtree(lab, ignore_errors=True)
        report["labRemoved"] = not lab.exists()
    report["completedAt"] = utc_now()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / f"browser-cache-{report['startedAt'].replace(':', '')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(out)
    for p in report["profiles"]:
        if "fatal" in p:
            print(p["label"], "FATAL", p["fatal"].splitlines()[-1])
            continue
        # The raw statuses, not a verdict: the first version of this line printed
        # "REFETCH" for files that had 404'd both times.
        first = {s["path"]: s["status"] for s in p["first"]["server"]}
        again = {s["path"]: s["status"] for s in p["second"]["server"]}
        print(f"{p['label']:13} free={p['profileDiskFree'] / 1e9:.0f}GB")
        for row in p["first"]["page"] or []:
            n = row["name"]
            print(f"   {n:15} first={first.get(n)} decoded={row.get('decodedBytes')}"
                  f" second-at-server={again.get(n, 'none')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
