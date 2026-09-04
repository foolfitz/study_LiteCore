#!/usr/bin/env python3
"""Serve the CANDIDATE page for a human round, and say which bytes it is.

`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` condition 3 (the manual
round) with 4b folded in.  The round has to happen on the page a cutover would
ship, not on the page the product serves today and not on a `--profile` mirror
with a shim in it -- otherwise the human tested something nobody will ship.

So this builds the page with `repointed_page()`, the SAME function
`tools/build_cutover_page.py` writes with and `--candidate-profile` runs
measure, mirrors `dist/` around it, and serves that.  It prints the page's
sha256 before the URL: if that number is not the one the banked soak reports
carry, the human round is about different bytes and the operator must stop.

Nothing under `dist/`, `web/` or `sdk/` is written.

Usage:
  serve_candidate_page.py --profile e2-editor-v12 [--port 8765]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))
from run_e2_c_product_path import build_mirror, repointed_page       # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="e2-editor-v12")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--expect-sha256", default=None,
                        help="refuse to serve if the page is not these bytes")
    args = parser.parse_args()

    manifest = PROJECT / "dist" / "profiles" / args.profile / "sdk-manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"no manifest for {args.profile} at {manifest}")
    source = (PROJECT / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
    page, pin_before, wasm = repointed_page(source, args.profile, manifest)
    digest = hashlib.sha256(page.encode("utf-8")).hexdigest()

    if args.expect_sha256 and digest != args.expect_sha256:
        raise SystemExit(
            f"page sha256 is {digest}\n"
            f"expected           {args.expect_sha256}\n"
            "The tree moved between the soak and this round. A human round on "
            "different bytes measures a page nobody measured.")

    scratch = Path(tempfile.mkdtemp(prefix="candidate-round-"))
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root, {"e2-editor-app.js": page.encode("utf-8")})

    print(json.dumps({
        "profile": args.profile,
        "pageSha256": digest,
        "pinBefore": pin_before,
        "pinAfter": wasm[:16],
        "servedFrom": str(root),
        "note": "This is the page a cutover would ship, built by the same "
                "function build_cutover_page.py writes with. Nothing under "
                "dist/, web/ or sdk/ was written.",
    }, indent=2))
    print()
    print(f"    URL:  http://127.0.0.1:{args.port}/e2-editor.html")
    print(f"    page: {digest[:16]}…")
    print()
    print("Ctrl+C to stop.")

    proc = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(args.port), "--root", str(root)],
        cwd=PROJECT)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
