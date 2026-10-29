#!/usr/bin/env python3
"""The before and after products for SPEC-M3-shell-v79-finding-173 5.3 (B1), each served from its own bytes.

WHY THIS EXISTS.  The fix changes two shell files (the page and editor-shell-v2/paragraph-editor-client.js),
and after `make e2-c-assets` dist/ serves the fixed pair.  tools/v25_f_products.py pins v25 to page 6e66c930
and generation 78 -- correctly refuses the new dist/ -- and is bound by F1/F2's evidence, so it is not edited.
Here each product is a set of mirror overrides plus an identity that is checked, not assumed:

  before  the page and paragraph-editor-client.js from git at BEFORE_COMMIT (finding 173's commit), the rest
          dist/: every module of generation 78 served with exactly the sha256 that manifest records
  after   dist/ as served: every module of generation 78 EXCEPT the two declared files served with 78's
          sha256; the two declared files equal to the tree's source AND different from 78 (a closed list)

For both, the v25 profile's four served files must equal the v25 archive's SHA256SUMS and the page must point
at profiles/e2-editor-v25/.  Generation 79 does not exist until B1 holds (spec 7), so the after identity is
written against 78 plus the closed list; the two sha256s it serves are reported so the freeze can check them
against 79 (spec 5.6).  Nothing under dist/ is written; the overrides are materialised in the mirror.
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

BEFORE_COMMIT = "d14186167"
GENERATION_78 = "e2/editor-shell-v2-bundle-v78.json"
DECLARED = ("web/e2-editor-app.js", "editor-shell-v2/paragraph-editor-client.js")
PROFILE = "e2-editor-v25"
ARCHIVE = "build/archive/e2-editor-v25-44cb15ea-worker-75557b22"
PROFILE_FILES = ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json")
NAMES = ("before", "after")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{BEFORE_COMMIT}:wasm_sdk_probe/{path}"])


def overrides(name: str, snippets: list[str]) -> dict[str, bytes]:
    """Mirror overrides: the HTML with the instruments, and (before only) the two declared files from git."""
    if name not in NAMES:
        raise SystemExit(f"unknown product {name}")
    html = common.inject((common.DIST / "e2-editor.html").read_text(encoding="utf-8"), snippets)
    out = {"e2-editor.html": html.encode("utf-8")}
    if name == "before":
        for path in DECLARED:
            out[pp.served_in_dist(path)] = git_bytes(path)
    return out


def identity(name: str, mirror: Path) -> dict:
    """What the mirror actually serves for `name`, checked file by file.  `ok` is all of `checks`."""
    archive = PROJECT / ARCHIVE
    sums = dict(line.split()[::-1] for line in (archive / "SHA256SUMS").read_text().splitlines() if line.strip())
    served_profile = {f: sha256((mirror / "profiles" / PROFILE / f).read_bytes()) for f in PROFILE_FILES}
    generation = json.loads((PROJECT / GENERATION_78).read_text(encoding="utf-8"))
    recorded = {e["path"]: e["sha256"] for e in generation["included"]}
    served = {p: sha256((mirror / pp.served_in_dist(p)).read_bytes()) for p in recorded}
    page = (mirror / "e2-editor-app.js").read_text(encoding="utf-8")
    checks = {
        "profileEqualsArchive": all(served_profile[f] == sums.get(f) for f in PROFILE_FILES),
        "pagePointsAtProfile": f'workerUrl: "./profiles/{PROFILE}/sdk-worker.js"' in page,
        "declaredInGeneration78": all(p in recorded for p in DECLARED),
    }
    if name == "before":
        checks["shellEqualsGeneration78"] = all(served[p] == recorded[p] for p in recorded)
    else:
        checks["othersEqualGeneration78"] = all(served[p] == recorded[p] for p in recorded if p not in DECLARED)
        checks["declaredEqualTree"] = all(served.get(p) == sha256((PROJECT / p).read_bytes()) for p in DECLARED)
        checks["declaredDifferFromGeneration78"] = all(served.get(p) != recorded.get(p) for p in DECLARED)
    return {"product": name, "profile": PROFILE, "archive": ARCHIVE, "generation": GENERATION_78,
            "generationDigest": generation["bundleSha256"], "servedProfile": served_profile,
            "declared": {p: served.get(p) for p in DECLARED},
            "shellMismatchesAgainst78": sorted(p for p in recorded if served[p] != recorded[p]),
            "checks": checks, "ok": all(checks.values())}
