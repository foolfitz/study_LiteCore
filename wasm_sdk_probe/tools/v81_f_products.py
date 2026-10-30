#!/usr/bin/env python3
"""The products for SPEC-M3-v27-finding-176 7.3 (S3, S2′), each served from its own bytes.

Derived from tools/v80_f_products.py (not edited: S1-80/S2-80's evidence binds it).  Generation 81 does not exist
until S3 and S2′ hold (spec 7.3), so `after` is written against generation 80 plus a closed list of one file:

  before             generation 80 as frozen: the page from git at BEFORE_COMMIT (7745a26e9, page 3b6c023e, the
                     last page before any v27 change); the rest dist/.  Every module of generation 80 served with
                     exactly the sha256 that manifest records; profile e2-editor-v26 = the v26 archive.
  after              dist/ as served: every module of generation 80 EXCEPT the page served with 80's sha256; the
                     page equal to the tree's source AND different from 80's; profile e2-editor-v27 = the v27
                     archive; the page points at profiles/e2-editor-v27/.
  hide-review-toast  before, with the page's `review` branch not showing its toast (S3 mutation: ruling 3's
                     B case, the review hidden instead of answered).
  cosmetic-review    before, with the page's `review` branch writing `${label} N ms` to the strip, no toast and no
                     `[review]` console line: on the page it looks exactly like v27 (S3 mutation, review item 4 --
                     only the worker reply row can tell).

The two page variants are exact replacements in generation 80's page (each anchor must occur once).  Nothing under
dist/ is written; the overrides are materialised in the mirror.
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

BEFORE_COMMIT = "7745a26e9"
GENERATION_80 = "e2/editor-shell-v2-bundle-v80.json"
PAGE = "web/e2-editor-app.js"
DECLARED = (PAGE,)
PROFILES = {"before": ("e2-editor-v26", "build/archive/e2-editor-v26-44cb15ea-worker-95d6e7ae"),
            "after": ("e2-editor-v27", "build/archive/e2-editor-v27-c089dfd6-worker-8152448a")}
PROFILE_FILES = ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json")
NAMES = ("before", "after", "hide-review-toast", "cosmetic-review")
BEFORE_LIKE = ("before", "hide-review-toast", "cosmetic-review")

REVIEW_TOAST = "      toast(`${label}：${sentence}`, false);\n      throw error;\n    }\n"
REVIEW_OPEN = '    if (recovery === "review") {\n      const shape = error?.details?.formatBarrier?.failureShape ?? null;\n'
VARIANTS = {
    "hide-review-toast": [(REVIEW_TOAST, "      throw error;\n    }\n")],
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
            raise SystemExit(f"{name}: anchor occurs {page.count(old)} times in generation 80's page, not once")
        page = page.replace(old, new)
    return page.encode("utf-8")


def overrides(name: str, snippets: list[str]) -> dict[str, bytes]:
    """Mirror overrides: the HTML with the instruments, and for the before-like products the page."""
    if name not in NAMES:
        raise SystemExit(f"unknown product {name}")
    html = common.inject((common.DIST / "e2-editor.html").read_text(encoding="utf-8"), list(snippets))
    out = {"e2-editor.html": html.encode("utf-8")}
    if name in BEFORE_LIKE:
        out[pp.served_in_dist(PAGE)] = page_bytes(name)
    return out


def identity(name: str, mirror: Path) -> dict:
    """What the mirror actually serves for `name`, checked file by file.  `ok` is all of `checks`."""
    profile, archive_rel = PROFILES["after" if name == "after" else "before"]
    archive = PROJECT / archive_rel
    sums = dict(line.split()[::-1] for line in (archive / "SHA256SUMS").read_text().splitlines() if line.strip())
    served_profile = {f: sha256((mirror / "profiles" / profile / f).read_bytes()) for f in PROFILE_FILES}
    generation = json.loads((PROJECT / GENERATION_80).read_text(encoding="utf-8"))
    recorded = {e["path"]: e["sha256"] for e in generation["included"]}
    served = {p: sha256((mirror / pp.served_in_dist(p)).read_bytes()) for p in recorded}
    page = (mirror / "e2-editor-app.js").read_text(encoding="utf-8")
    checks = {
        "pagePointsAtProfile": f'workerUrl: "./profiles/{profile}/sdk-worker.js"' in page,
        "declaredInGeneration80": all(p in recorded for p in DECLARED),
        "profileEqualsArchive": all(served_profile[f] == sums.get(f) for f in PROFILE_FILES),
        "othersEqualGeneration80": all(served[p] == recorded[p] for p in recorded if p not in DECLARED),
    }
    if name == "before":
        checks["pageIsGeneration80"] = served[PAGE] == recorded[PAGE]
    elif name == "after":
        checks["pageEqualsTree"] = served[PAGE] == sha256((PROJECT / PAGE).read_bytes())
        checks["pageDiffersFromGeneration80"] = served[PAGE] != recorded[PAGE]
    else:
        checks["pageIsTheVariantOfGeneration80"] = served[PAGE] == sha256(page_bytes(name))
        checks["variantDiffersFromGeneration80"] = served[PAGE] != recorded[PAGE]
        checks["gitPageIsGeneration80"] = sha256(git_bytes(PAGE)) == recorded[PAGE]
    return {"product": name, "profile": profile, "archive": archive_rel, "generation": GENERATION_80,
            "generationDigest": generation["bundleSha256"], "servedProfile": served_profile,
            "page": served[PAGE], "shellMismatchesAgainst80": sorted(p for p in recorded if served[p] != recorded[p]),
            "checks": checks, "ok": all(checks.values())}
