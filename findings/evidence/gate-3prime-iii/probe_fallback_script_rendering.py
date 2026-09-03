#!/usr/bin/env python3
"""B-2 criterion 3'-iii — what each profile actually draws for fallback-only scripts.

Opens `fallback-script.odt` on a profile's CANDIDATE page and records what the
canvas shows: a PNG, and per-row ink statistics so the comparison is a number
and not only a picture.

WHICH DOCUMENT IS IN FRONT OF YOU, AND ARE YOU READY, ARE DIFFERENT SENTENCES.
The ODT round-trip probe reported a cross-version incompatibility that did not
exist because it waited for `state == "ready"` after handing a file over -- and
the page was ALREADY ready, still showing the previous document. This waits for
the state's `doc` to become the fixture's name, and fails loudly if it does not.

Run from `wasm_sdk_probe/`:
  python3 ../findings/evidence/gate-3prime-iii/probe_fallback_script_rendering.py \
      --profile e2-editor-v12 --out-dir ../findings/evidence/gate-3prime-iii
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3] / "wasm_sdk_probe"
sys.path.insert(0, str(PROJECT / "tools"))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from run_e2_c_product_path import OPEN_FILE, build_mirror, repointed_page  # noqa: E402

FIXTURE = "fallback-script.odt"

# Rows of ink, and the horizontal extent of each band.  A script with no font
# draws either nothing or tofu; both differ from correctly drawn glyphs, and
# the extent says which without needing to recognise letters.
INK_PROFILE = """(() => {
  const canvas = document.querySelector('#canvas');
  if (!canvas) return { missing: true };
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const { width, height } = canvas;
  const data = ctx.getImageData(0, 0, width, height).data;
  const rows = [];
  for (let y = 0; y < height; y++) {
    let count = 0, first = -1, last = -1;
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 4;
      // Anything not near-white counts as ink.
      if (data[i] < 200 || data[i + 1] < 200 || data[i + 2] < 200) {
        count++; if (first < 0) first = x; last = x;
      }
    }
    rows.push([count, first, last]);
  }
  // Collapse to bands of consecutive inked rows.
  const bands = [];
  let start = -1;
  for (let y = 0; y <= height; y++) {
    const inked = y < height && rows[y][0] > 0;
    if (inked && start < 0) start = y;
    if (!inked && start >= 0) {
      const slice = rows.slice(start, y);
      bands.push({
        top: start, bottom: y - 1, height: y - start,
        inkPixels: slice.reduce((a, r) => a + r[0], 0),
        left: Math.min(...slice.map((r) => r[1]).filter((v) => v >= 0)),
        right: Math.max(...slice.map((r) => r[2])),
      });
      start = -1;
    }
  }
  return { width, height, bands };
})()"""

CANVAS_PNG = """(() => {
  const canvas = document.querySelector('#canvas');
  return canvas ? canvas.toDataURL('image/png') : null;
})()"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = PROJECT / "dist" / "profiles" / args.profile / "sdk-manifest.json"
    source = (PROJECT / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
    page, _, _ = repointed_page(source, args.profile, manifest_path)
    page_sha = hashlib.sha256(page.encode("utf-8")).hexdigest()

    scratch = Path(tempfile.mkdtemp(prefix="fallback-script-"))
    mirror = scratch / "dist"
    build_mirror(PROJECT / "dist", mirror, {"e2-editor-app.js": page.encode()})

    record = {"profile": args.profile, "pageSha256": page_sha, "fixture": FIXTURE}
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(mirror)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session = ChromeSession("cold")
        navigate(session, base)

        deadline = time.monotonic() + args.timeout
        state = None
        while time.monotonic() < deadline:
            state = evaluate(session, READ_STATE)
            if state and state.get("state") == "ready":
                break
            time.sleep(0.5)
        assert state and state.get("state") == "ready", f"never ready: {state}"
        record["docBeforeOpen"] = state.get("doc")

        evaluate(session, OPEN_FILE.replace("ARG_URL", f"./e1-fixtures/{FIXTURE}")
                                   .replace("ARG_NAME", FIXTURE))

        # The fixture's NAME, not `ready` -- see the docstring.
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            state = evaluate(session, READ_STATE)
            if state and state.get("doc") == FIXTURE and state.get("state") == "ready":
                break
            time.sleep(0.5)
        assert state and state.get("doc") == FIXTURE, (
            f"the page never showed {FIXTURE}; it is on {state and state.get('doc')!r}. "
            "Nothing below would be about the fixture.")
        record["docAfterOpen"] = state.get("doc")
        time.sleep(3.0)

        record["ink"] = evaluate(session, INK_PROFILE)
        data_url = evaluate(session, CANVAS_PNG)
        if isinstance(data_url, str) and data_url.startswith("data:image/png;base64,"):
            png = base64.b64decode(data_url.split(",", 1)[1])
            path = out_dir / f"canvas-{args.profile}.png"
            path.write_bytes(png)
            record["png"] = path.name
            record["pngBytes"] = len(png)
            record["pngSha256"] = hashlib.sha256(png).hexdigest()
        else:
            record["png"] = None
            record["pngError"] = str(data_url)[:200]
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    (out_dir / f"render-{args.profile}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in record.items() if k != "ink"},
                     ensure_ascii=False, indent=2))
    bands = ((record.get("ink") or {}).get("bands") or [])
    print(f"ink bands: {len(bands)}")
    for band in bands:
        print(f"   top={band['top']:5d} h={band['height']:3d} "
              f"ink={band['inkPixels']:7d} x=[{band['left']},{band['right']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
