#!/usr/bin/env python3
"""Unit red cases for release P (spec §16.2 123-U and P-U), each mutation applied alone to web/e2-editor-app.js,
the page's tests run, and the page restored byte for byte (checked by sha256).  Appends to unit-red-cases.txt
beside this file.

  unit_red_cases.py NAME [NAME ...]      (names below; `baseline` runs the tests on the page as it is)
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
PAGE = ROOT / "web" / "e2-editor-app.js"
TESTS = ["editor-shell-v2/tests/page-render-bands.test.mjs", "editor-shell-v2/tests/page-paint-overlay.test.mjs"]
OUT = Path(__file__).resolve().parent / "unit-red-cases.txt"

MUTATIONS = {  # name: (what it reintroduces, find, replace)
    "R-123 no merge": (
        "finding 123: a short last band",
        "  if (bands.length > 1 && bands.at(-1).rows < RENDER_BAND_HEIGHT / 2) {",
        "  if (false && bands.length > 1 && bands.at(-1).rows < RENDER_BAND_HEIGHT / 2) {"),
    "R-P1 paint() back to whole-band blits": (
        "release P undone: every cached band put back and the overlay drawn over all of it, on every state write",
        "function paint() {\n  if (!lastTiles.length) return;\n",
        "function paint() {\n  if (!lastTiles.length) return;\n"
        "  { const c = el.canvas.getContext(\"2d\"); for (const strip of lastTiles) if (strip) c.putImageData(strip.image, 0, strip.y);\n"
        "    const s = overlayShapes() ?? NO_OVERLAY; drawOverlay(c, s); paintedOverlay = s; return; }\n"),
    "R-P2 no old-rect restore": (
        "the old caret and selection left on the canvas",
        "  const areas = [...overlayAreas(paintedOverlay), ...overlayAreas(next)];",
        "  const areas = [...overlayAreas(next)];"),
    "R-P4 no reset in layoutCanvas": (
        "the overlay drawn before a layout still believed to be on the cleared canvas",
        "  lastTiles = [];\n  paintedOverlay = NO_OVERLAY;\n",
        "  lastTiles = [];\n"),
    "R-Px no clip in paint()": (
        "(extra, not a §16.2 red case) the overlay drawn unclipped: the wash lands twice where it was not restored",
        "  for (const [x, y, width, height] of areas) context.rect(x, y, width, height);\n  context.clip();\n",
        "  for (const [x, y, width, height] of areas) context.rect(x, y, width, height);\n"),
}


def run(name: str) -> str:
    original = PAGE.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    head = f"== {name}"
    try:
        if name != "baseline":
            what, find, replace = MUTATIONS[name]
            text = original.decode("utf-8")
            if text.count(find) != 1:
                return f"{head}\nNOT APPLIED: anchor found {text.count(find)} times\n"
            PAGE.write_bytes(text.replace(find, replace).encode("utf-8"))
            head += f" ({what})"
        tests = [t for t in TESTS if (ROOT / t).exists()]
        done = subprocess.run(["node", "--test", *tests], cwd=ROOT, capture_output=True, text=True)
        lines = [l for l in done.stdout.splitlines() if (l.startswith("✖") and "failing tests" not in l) or l.startswith("ℹ pass")
                 or l.startswith("ℹ fail")]
        seen, kept = set(), []
        for l in lines:   # node prints each failing test twice (inline and in the summary)
            key = l.split(" (")[0]
            if key not in seen:
                seen.add(key)
                kept.append(l.split(" (")[0] if l.startswith("✖") else l)
        return "\n".join([head] + kept) + "\n"
    finally:
        PAGE.write_bytes(original)
        assert hashlib.sha256(PAGE.read_bytes()).hexdigest() == digest, "the page was not restored"


def main() -> int:
    names = sys.argv[1:] or ["baseline"]
    stamp = f"## {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} page {hashlib.sha256(PAGE.read_bytes()).hexdigest()[:16]}\n"
    text = stamp + "".join(run(n) for n in names)
    with OUT.open("a") as f:
        f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
