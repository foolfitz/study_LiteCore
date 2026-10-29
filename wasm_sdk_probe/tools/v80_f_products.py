#!/usr/bin/env python3
"""The products for SPEC-M3-select-all-v26 5.4 (S1) and 5.5 (S2), each served from its own bytes.

Derived from tools/v79_f_products.py (not edited: B1-79's evidence binds it).  Generation 80 does not exist until
S1 and S2 hold (spec 5.8), so `after` is written against generation 79 plus a closed list of three files:

  before      the page, narrow-editor-v2-client.js and narrow-editor-v2-session.js from git at BEFORE_COMMIT
              (the spec's pin, the last tree before any v26 change); the rest dist/.  Every module of generation 79
              served with exactly the sha256 that manifest records; profile e2-editor-v25 = the v25 archive.
  after       dist/ as served: every module of generation 79 EXCEPT the three declared files served with 79's
              sha256; the three equal to the tree's source AND different from 79; profile e2-editor-v26 = the v26
              archive; the page points at profiles/e2-editor-v26/.
  unoffered   after, with profiles/e2-editor-v26/sdk-manifest.json replaced by a scratch whose select-all is
              withheld again (`gestures: []`, v25's entry); every other manifest value v26's.
  fake        after; the HTML also carries FAKE_REWRITER, which turns the select-all reply the page receives into
              a collapsed selection (2026-08-19's "reported success, selected nothing", built on the page's side).
  v25-worker  after, with profiles/e2-editor-v26/sdk-worker.js replaced by the v25 archive's worker and the
              manifest's workerSha256 set back to it: the extend arm's red case (spec 5.5, review item 4).

Nothing under dist/ is written; the overrides are materialised in the mirror.
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

BEFORE_COMMIT = "9f084bf06"
GENERATION_79 = "e2/editor-shell-v2-bundle-v79.json"
DECLARED = ("web/e2-editor-app.js", "editor-shell-v2/narrow-editor-v2-client.js",
            "editor-shell-v2/narrow-editor-v2-session.js")
PROFILES = {"before": ("e2-editor-v25", "build/archive/e2-editor-v25-44cb15ea-worker-75557b22"),
            "after": ("e2-editor-v26", "build/archive/e2-editor-v26-44cb15ea-worker-95d6e7ae")}
PROFILE_FILES = ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json")
NAMES = ("before", "after", "unoffered", "fake", "v25-worker")
V26_DIR = "profiles/e2-editor-v26"

FAKE_REWRITER = """<script>
(() => {
  // SPEC-M3-select-all-v26 5.4, product `fake`: the select-all reply the page receives says the selection is
  // collapsed -- 2026-08-19's shape, constructed on the page's side.  Registered before the page's own listener
  // (this script runs first), so the page reads the rewritten reply.
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) { super(url, options);
      this.addEventListener('message', (ev) => {
        const d = ev.data;
        if (d?.kind === 'response' && d.ok && d.result?.action === 'select-all' && d.result.state) {
          d.result.state.selection = {...(d.result.state.selection || {}), observed: true, collapsed: true,
                                      start: null, end: null, rectangles: []};
          (window.__fakeRewrites = (window.__fakeRewrites || 0) + 1);
        }
      }); }
  };
})();
</script>"""


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{BEFORE_COMMIT}:wasm_sdk_probe/{path}"])


def _archive(name: str) -> Path:
    return PROJECT / PROFILES["before" if name == "before" else "after"][1]


def overrides(name: str, snippets: list[str]) -> dict[str, bytes]:
    """Mirror overrides: the HTML with the instruments (fake: the rewriter FIRST), and per product the rest."""
    if name not in NAMES:
        raise SystemExit(f"unknown product {name}")
    pieces = ([FAKE_REWRITER] if name == "fake" else []) + list(snippets)
    html = common.inject((common.DIST / "e2-editor.html").read_text(encoding="utf-8"), pieces)
    out = {"e2-editor.html": html.encode("utf-8")}
    if name == "before":
        for path in DECLARED:
            out[pp.served_in_dist(path)] = git_bytes(path)
    v26 = PROJECT / PROFILES["after"][1]
    v25 = PROJECT / PROFILES["before"][1]
    if name == "unoffered":
        manifest = json.loads((v26 / "sdk-manifest.json").read_bytes())
        manifest["editorContract"]["actions"]["select-all"] = json.loads(
            (v25 / "sdk-manifest.json").read_bytes())["editorContract"]["actions"]["select-all"]
        out[f"{V26_DIR}/sdk-manifest.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    if name == "v25-worker":
        worker = (v25 / "sdk-worker.js").read_bytes()
        manifest = json.loads((v26 / "sdk-manifest.json").read_bytes())
        manifest["editorContract"]["workerSha256"] = sha256(worker)
        out[f"{V26_DIR}/sdk-worker.js"] = worker
        out[f"{V26_DIR}/sdk-manifest.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    return out


def identity(name: str, mirror: Path) -> dict:
    """What the mirror actually serves for `name`, checked file by file.  `ok` is all of `checks`."""
    profile, archive_rel = PROFILES["before" if name == "before" else "after"]
    archive = PROJECT / archive_rel
    sums = dict(line.split()[::-1] for line in (archive / "SHA256SUMS").read_text().splitlines() if line.strip())
    served_profile = {f: sha256((mirror / "profiles" / profile / f).read_bytes()) for f in PROFILE_FILES}
    generation = json.loads((PROJECT / GENERATION_79).read_text(encoding="utf-8"))
    recorded = {e["path"]: e["sha256"] for e in generation["included"]}
    served = {p: sha256((mirror / pp.served_in_dist(p)).read_bytes()) for p in recorded}
    page = (mirror / "e2-editor-app.js").read_text(encoding="utf-8")
    html = (mirror / "e2-editor.html").read_text(encoding="utf-8")
    checks = {
        "pagePointsAtProfile": f'workerUrl: "./profiles/{profile}/sdk-worker.js"' in page,
        "declaredInGeneration79": all(p in recorded for p in DECLARED),
    }
    changed = {"unoffered": {"sdk-manifest.json"}, "v25-worker": {"sdk-manifest.json", "sdk-worker.js"}}.get(name, set())
    checks["profileEqualsArchive"] = all(served_profile[f] == sums.get(f) for f in PROFILE_FILES if f not in changed)
    if changed:
        checks["profileDiffersExactlyWhereDeclared"] = all(served_profile[f] != sums.get(f) for f in changed)
    if name == "unoffered":
        manifest = json.loads((mirror / V26_DIR / "sdk-manifest.json").read_bytes())
        checks["selectAllWithheld"] = manifest["editorContract"]["actions"]["select-all"]["gestures"] == []
        checks["profileNameStillV26"] = manifest["profile"] == "e2-editor-v26"
    if name == "v25-worker":
        manifest = json.loads((mirror / V26_DIR / "sdk-manifest.json").read_bytes())
        v25_sums = dict(line.split()[::-1] for line in (PROJECT / PROFILES["before"][1] / "SHA256SUMS")
                        .read_text().splitlines() if line.strip())
        checks["workerIsV25s"] = served_profile["sdk-worker.js"] == v25_sums["sdk-worker.js"]
        checks["manifestBindsServedWorker"] = manifest["editorContract"]["workerSha256"] == served_profile["sdk-worker.js"]
    checks["fakeRewriterPresentIffFake"] = ("__fakeRewrites" in html) == (name == "fake")
    if name == "before":
        checks["shellEqualsGeneration79"] = all(served[p] == recorded[p] for p in recorded)
    else:
        checks["othersEqualGeneration79"] = all(served[p] == recorded[p] for p in recorded if p not in DECLARED)
        checks["declaredEqualTree"] = all(served.get(p) == sha256((PROJECT / p).read_bytes()) for p in DECLARED)
        checks["declaredDifferFromGeneration79"] = all(served.get(p) != recorded.get(p) for p in DECLARED)
    return {"product": name, "profile": profile, "archive": archive_rel, "generation": GENERATION_79,
            "generationDigest": generation["bundleSha256"], "servedProfile": served_profile,
            "declared": {p: served.get(p) for p in DECLARED},
            "shellMismatchesAgainst79": sorted(p for p in recorded if served[p] != recorded[p]),
            "checks": checks, "ok": all(checks.values())}
