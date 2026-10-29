#!/usr/bin/env python3
"""The v24 and v25 products for SPEC-M3-link-batch-v25 6.3 F1/F2, each served from its own bytes.

WHY THIS EXISTS.  After the v25 cutover (e06d10a1b) `dist/` serves v25: the page repoints to
`profiles/e2-editor-v25/`.  A tool that says "v24 = dist/ as served" (diag_format.py:6, written the
morning before) would silently measure v25 under v24's name.  So each product here is a set of
mirror overrides plus an identity that is checked, not assumed:

  v24  page b15a6d8e taken from git at V24_PAGE_COMMIT (the cutover's parent), profile
       e2-editor-v24, whose four served files must equal the v24 archive's SHA256SUMS
  v25  dist/ as served: page 6e66c930, profile e2-editor-v25, checked against the v25 archive

and for both, every module of the shell generation the product shipped with (v24: 77, v25: 78)
must be served by the mirror with exactly the sha256 that generation's manifest records -- the
page included.  Nothing under dist/ is written; the overrides are materialised in the mirror.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
sys.path.insert(0, str(PROJECT / "tools"))
import run_e2_c_product_path as pp  # noqa: E402
import v21_shakedown_common as common  # noqa: E402

V24_PAGE_COMMIT = "b241c83a4"
PRODUCTS = {
    "v24": {"profile": "e2-editor-v24", "generation": "e2/editor-shell-v2-bundle-v77.json",
            "page": "b15a6d8e07b6a4f3e551f27971b7cfe8bec2cb743e5f6809013ca7f2082de669",
            "archive": "build/archive/e2-editor-v24-27615808-worker-41041fe7"},
    "v25": {"profile": "e2-editor-v25", "generation": "e2/editor-shell-v2-bundle-v78.json",
            "page": "6e66c930fe3d861903cfa6dfd16d000523298e934fae444385d4fe37d484c7cb",
            "archive": "build/archive/e2-editor-v25-44cb15ea-worker-75557b22"},
}
PROFILE_FILES = ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def page_bytes(name: str) -> bytes:
    """The product's page source.  v25 is the tree's (= dist/'s, checked); v24 is git's."""
    if name == "v24":
        raw = subprocess.check_output(
            ["git", "-C", str(REPO), "show", f"{V24_PAGE_COMMIT}:wasm_sdk_probe/web/e2-editor-app.js"])
    else:
        raw = (common.DIST / "e2-editor-app.js").read_bytes()
    if sha256(raw) != PRODUCTS[name]["page"]:
        raise SystemExit(f"{name}: page sha256 {sha256(raw)} is not {PRODUCTS[name]['page']}")
    return raw


def overrides(name: str, snippets: list[str]) -> dict[str, bytes]:
    """Mirror overrides: the HTML with the instruments, and (v24 only) the page."""
    html = common.inject((common.DIST / "e2-editor.html").read_text(encoding="utf-8"), snippets)
    out = {"e2-editor.html": html.encode("utf-8")}
    if name == "v24":
        out["e2-editor-app.js"] = page_bytes("v24")
    else:
        page_bytes("v25")  # dist/ must still serve the cutover page
    return out


def identity(name: str, mirror: Path) -> dict:
    """What the mirror actually serves for `name`, checked file by file.  `ok` is all of `checks`."""
    spec = PRODUCTS[name]
    archive = PROJECT / spec["archive"]
    sums = dict(line.split()[::-1] for line in (archive / "SHA256SUMS").read_text().splitlines() if line.strip())
    served_profile = {f: sha256((mirror / "profiles" / spec["profile"] / f).read_bytes()) for f in PROFILE_FILES}
    generation = json.loads((PROJECT / spec["generation"]).read_text(encoding="utf-8"))
    shell = {e["path"]: (e["sha256"], sha256((mirror / pp.served_in_dist(e["path"])).read_bytes()))
             for e in generation["included"]}
    page = (mirror / "e2-editor-app.js").read_text(encoding="utf-8")
    checks = {
        "profileEqualsArchive": all(served_profile[f] == sums.get(f) for f in PROFILE_FILES),
        "shellEqualsGeneration": all(recorded == served for recorded, served in shell.values()),
        "pageServed": sha256(page.encode("utf-8")) == spec["page"],
        "pagePointsAtProfile": f'workerUrl: "./profiles/{spec["profile"]}/sdk-worker.js"' in page,
    }
    return {"profile": spec["profile"], "generation": spec["generation"],
            "generationDigest": generation["bundleSha256"], "archive": spec["archive"],
            "servedProfile": served_profile,
            "shellMismatches": sorted(p for p, (r, s) in shell.items() if r != s),
            "checks": checks, "ok": all(checks.values())}
