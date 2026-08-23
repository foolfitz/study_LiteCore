#!/usr/bin/env python3
"""Serve the product page against a chosen profile, for a HUMAN to use.

WHY THIS EXISTS, and it is a scar rather than a convenience.  On 2026-08-22 the
operator was handed a preview to confirm finding 068 and reported "no change".
Both of us were right: the fix had two halves, and the half that lived in the
FROZEN profile was not in the build they were given.  They tested a page where
the listener was installed and nobody broadcast.

Two rules came out of it and both are implemented here:

  * A frozen profile keeps a fix out.  Whichever profile is selected is served
    verbatim -- the page is repointed at it, the profile itself is never
    touched -- and the banner names it.
  * "Which build did they actually test" must never again be a guess.  The page
    carries a BANNER, on screen, naming the profile, the wasm and worker
    hashes, and the core.  It is not in a console message and not in a tooltip.

This serves a MIRROR.  dist/ is not modified: the shipped page keeps pinning
the shipped artifact, and this process changes nothing when it exits.

Usage:
  serve_manual_preview.py --profile e2-editor-v5 [--port 8792]
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_e2_c_product_path import build_mirror  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

BANNER_TEMPLATE = """
<script>
// The banner is injected into the PAGE, not printed to the console, because
// its whole job is to be visible to somebody who is not reading a terminal.
(() => {
  const build = BUILD_JSON;
  const bar = document.createElement('div');
  bar.id = 'manual-preview-banner';
  bar.setAttribute('role', 'note');
  bar.style.cssText = [
    'position:fixed', 'left:0', 'right:0', 'top:0', 'z-index:2147483647',
    'background:#1b5e20', 'color:#fff', 'font:13px/1.5 system-ui,sans-serif',
    'padding:6px 12px', 'box-shadow:0 1px 4px rgba(0,0,0,.4)',
  ].join(';');
  bar.textContent =
    'PREVIEW BUILD \\u2014 profile ' + build.profile +
    ' \\u00b7 wasm ' + build.wasm +
    ' \\u00b7 worker ' + build.worker +
    ' \\u00b7 core ' + build.core;
  const attach = () => {
    document.body.appendChild(bar);
    document.body.style.paddingTop = '32px';
  };
  if (document.body) attach();
  else document.addEventListener('DOMContentLoaded', attach);
})();
</script>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--port", type=int, default=8792)
    ap.add_argument("--core", default="(not recorded in the manifest)")
    args = ap.parse_args()

    profile_dir = PROJECT / "dist" / "profiles" / args.profile
    if not profile_dir.is_dir():
        raise SystemExit(f"no such profile: {profile_dir}")
    manifest = json.loads((profile_dir / "sdk-manifest.json")
                          .read_text(encoding="utf-8"))
    contract = manifest["editorContract"]
    wasm_sha = contract["wasmSha256"]
    worker_sha = hashlib.sha256(
        (profile_dir / "sdk-worker.js").read_bytes()).hexdigest()

    page_relative = "e2-editor-app.js"
    source = (PROJECT / "dist" / page_relative).read_text(encoding="utf-8")
    matches = re.findall(r'"\./profiles/[A-Za-z0-9._-]+/sdk-worker\.js"', source)
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one profile worker URL in dist/{page_relative}, "
            f"found {len(matches)}")
    shipped_profile = matches[0]
    page = source.replace(shipped_profile,
                          f'"./profiles/{args.profile}/sdk-worker.js"', 1)
    pin = re.search(r'const PINNED_WASM_SHA256 = "([0-9a-f]+)";', page)
    if not pin:
        raise SystemExit("the page no longer pins a wasm hash")
    page = page.replace(pin.group(0),
                        f'const PINNED_WASM_SHA256 = "{wasm_sha[:16]}";', 1)

    build = {"profile": args.profile, "wasm": wasm_sha[:16],
             "worker": worker_sha[:16], "core": args.core}
    banner = BANNER_TEMPLATE.replace(
        "BUILD_JSON", json.dumps(build, ensure_ascii=False))

    page_html_relative = "e2-editor.html"
    page_html = (PROJECT / "dist" / page_html_relative).read_text(encoding="utf-8")
    if "</body>" in page_html:
        page_html = page_html.replace("</body>", banner + "</body>", 1)
    else:
        page_html += banner

    root = Path(tempfile.mkdtemp(prefix=f"preview-{args.profile}-")) / "root"
    build_mirror(PROJECT / "dist", root, {
        page_relative: page.encode("utf-8"),
        page_html_relative: page_html.encode("utf-8"),
    })

    print(f"profile      : {args.profile}")
    print(f"wasm sha256  : {wasm_sha}")
    print(f"worker sha256: {worker_sha}")
    print(f"was pinned to: {pin.group(1)}  (shipped page unchanged on disk)")
    print(f"mirror root  : {root}")
    print(f"\n  http://127.0.0.1:{args.port}/e2-editor.html\n")
    print("Ctrl-C to stop. Nothing under dist/ was written.", flush=True)
    return subprocess.call(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(args.port), "--root", str(root)], cwd=PROJECT)


if __name__ == "__main__":
    raise SystemExit(main())
