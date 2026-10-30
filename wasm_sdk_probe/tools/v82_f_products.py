#!/usr/bin/env python3
"""The products for SPEC-M3-v28-last-line-fallback 7.3 (S4), each served from its own bytes.

Derived from tools/v81_f_products.py (not edited: S3's and S2′'s evidence binds it).  Generation 82 does not exist
until S4 holds (spec 7.3), so `after` is written against generation 81 plus a closed list of two files:

  before          generation 81 as frozen: the page and the client from git at BEFORE_COMMIT (a9a04dc64, the last
                  commit before any v28 shell change; page b63d8ee5, client 7d1c1eb2); the rest dist/.  Every module
                  of generation 81 served with exactly the sha256 that manifest records; profile e2-editor-v27 = the
                  v27 archive.
  after           dist/ as served: every module of generation 81 EXCEPT the page and the client served with 81's
                  sha256; the page and the client equal to the tree's sources AND different from 81's; profile
                  e2-editor-v28 = the v28 archive; the page points at profiles/e2-editor-v28/.
  cosmetic-review before, with the page's `review` branch writing `${label} N ms` to the strip, no toast and no
                  `[review]` console line: on the page it looks exactly like v28 (S4-a mutation, v27 S3's lesson --
                  only the worker reply row can tell).

The page variant is an exact replacement in generation 81's page (the anchor must occur once).  Nothing under dist/
is written; the overrides are materialised in the mirror.
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

BEFORE_COMMIT = "a9a04dc64"
GENERATION_81 = "e2/editor-shell-v2-bundle-v81.json"
PAGE = "web/e2-editor-app.js"
CLIENT = "editor-shell-v2/paragraph-editor-client.js"
DECLARED = (PAGE, CLIENT)
PROFILES = {"before": ("e2-editor-v27", "build/archive/e2-editor-v27-c089dfd6-worker-8152448a"),
            "after": ("e2-editor-v28", "build/archive/e2-editor-v28-13f674e4-worker-a5df83db")}
PROFILE_FILES = ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json")
NAMES = ("before", "after", "cosmetic-review")
BEFORE_LIKE = ("before", "cosmetic-review")

REVIEW_OPEN = '    if (recovery === "review") {\n      const shape = error?.details?.formatBarrier?.failureShape ?? null;\n'
VARIANTS = {
    "cosmetic-review": [(REVIEW_OPEN, '    if (recovery === "review") {\n'
                                      "      el.s.latency.textContent = `${label} ${Math.round(performance.now() - started)} ms`;\n"
                                      "      throw error;\n"
                                      "      const shape = error?.details?.formatBarrier?.failureShape ?? null;\n")],
}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{BEFORE_COMMIT}:wasm_sdk_probe/{path}"])


def page_bytes(name: str) -> bytes:
    page = git_bytes(PAGE).decode("utf-8")
    for old, new in VARIANTS.get(name, []):
        if page.count(old) != 1:
            raise SystemExit(f"{name}: anchor occurs {page.count(old)} times in generation 81's page, not once")
        page = page.replace(old, new)
    return page.encode("utf-8")


def overrides(name: str, snippets: list[str]) -> dict[str, bytes]:
    """Mirror overrides: the HTML with the instruments, and for the before-like products the page and the client."""
    if name not in NAMES:
        raise SystemExit(f"unknown product {name}")
    html = common.inject((common.DIST / "e2-editor.html").read_text(encoding="utf-8"), list(snippets))
    out = {"e2-editor.html": html.encode("utf-8")}
    if name in BEFORE_LIKE:
        out[pp.served_in_dist(PAGE)] = page_bytes(name)
        out[pp.served_in_dist(CLIENT)] = git_bytes(CLIENT)
    return out


def identity(name: str, mirror: Path) -> dict:
    """What the mirror actually serves for `name`, checked file by file.  `ok` is all of `checks`."""
    profile, archive_rel = PROFILES["after" if name == "after" else "before"]
    archive = PROJECT / archive_rel
    sums = dict(line.split()[::-1] for line in (archive / "SHA256SUMS").read_text().splitlines() if line.strip())
    served_profile = {f: sha256((mirror / "profiles" / profile / f).read_bytes()) for f in PROFILE_FILES}
    generation = json.loads((PROJECT / GENERATION_81).read_text(encoding="utf-8"))
    recorded = {e["path"]: e["sha256"] for e in generation["included"]}
    served = {p: sha256((mirror / pp.served_in_dist(p)).read_bytes()) for p in recorded}
    page = (mirror / "e2-editor-app.js").read_text(encoding="utf-8")
    checks = {
        "pagePointsAtProfile": f'workerUrl: "./profiles/{profile}/sdk-worker.js"' in page,
        "declaredInGeneration81": all(p in recorded for p in DECLARED),
        "profileEqualsArchive": all(served_profile[f] == sums.get(f) for f in PROFILE_FILES),
        "othersEqualGeneration81": all(served[p] == recorded[p] for p in recorded if p not in DECLARED),
    }
    if name == "before":
        checks["pageIsGeneration81"] = served[PAGE] == recorded[PAGE]
        checks["clientIsGeneration81"] = served[CLIENT] == recorded[CLIENT]
    elif name == "after":
        for path, key in ((PAGE, "page"), (CLIENT, "client")):
            checks[f"{key}EqualsTree"] = served[path] == sha256((PROJECT / path).read_bytes())
            checks[f"{key}DiffersFromGeneration81"] = served[path] != recorded[path]
    else:
        checks["pageIsTheVariantOfGeneration81"] = served[PAGE] == sha256(page_bytes(name))
        checks["variantDiffersFromGeneration81"] = served[PAGE] != recorded[PAGE]
        checks["gitPageIsGeneration81"] = sha256(git_bytes(PAGE)) == recorded[PAGE]
        checks["clientIsGeneration81"] = served[CLIENT] == recorded[CLIENT]
    return {"product": name, "profile": profile, "archive": archive_rel, "generation": GENERATION_81,
            "generationDigest": generation["bundleSha256"], "servedProfile": served_profile,
            "page": served[PAGE], "client": served[CLIENT],
            "shellMismatchesAgainst81": sorted(p for p in recorded if served[p] != recorded[p]),
            "checks": checks, "ok": all(checks.values())}
