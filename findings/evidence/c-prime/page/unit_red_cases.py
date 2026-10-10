#!/usr/bin/env python3
"""Release C′'s unit red cases (SPEC-M3-production-ui §17.5 "unit", §17.9 (a) and (c); ruling conditions 2 and 3).

Each case mutates a copy of the page (exact text replacement, refused when the text is not there exactly once),
runs the three page test files against the copy, and lists the tests that failed.  A case is RED when at least one
test fails; it is printed with every failing test so that "red only where it should be" can be read.

The page and tests are copied to a scratch tree laid out like wasm_sdk_probe/ (the tests read
../../web/e2-editor-app.js); nothing in the repository is written.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4] / "wasm_sdk_probe"
FILES = ["page-paint-overlay.test.mjs", "page-render-bands.test.mjs", "page-render-disposed.test.mjs",
         "page-follow-caret.test.mjs"]

CASES = {
    "drop the floor (C1')": [
        ("Math.max(3 * Math.floor(deskHeight * scale), 4 * RENDER_BAND_HEIGHT)", "3 * Math.floor(deskHeight * scale)")],
    "drop the 3x term (C1')": [
        ("Math.max(3 * Math.floor(deskHeight * scale), 4 * RENDER_BAND_HEIGHT)", "4 * RENDER_BAND_HEIGHT")],
    "drop the y shift (paint and paintBand draw at document rows)": [
        ("      const bandTop = band.top - winTop;", "      const bandTop = band.top;"),
        ("      const stripTop = strip ? strip.y - winTop : 0;", "      const stripTop = strip ? strip.y : 0;"),
        ("  const top = strip.y - winTop;\n  context.putImageData(strip.image, 0, top);", "  const top = strip.y;\n  context.putImageData(strip.image, 0, top);")],
    "drop the staleness test (only an uncached band is stale)": [
        ("const stale = (band) => !lastTiles[band.index] || lastTiles[band.index].label < changes;",
         "const stale = (band) => !lastTiles[band.index];")],
    "drop the cache bound (bands outside the window are kept)": [
        ("\n  for (const band of bands) if (!bandInWindow(band)) lastTiles[band.index] = null;", "\n"),
        ("\n    for (const band of bands) if (!bandInWindow(band)) lastTiles[band.index] = null;", "\n")],
    "label at reply, not at request (condition 3, unit half)": [
        ("        y: band.top,\n        label,\n", "        y: band.top,\n        label: changes,\n")],
    # Finding 124 (§17.4 124-U, §17.9 (e)).
    "124: drop the 'caret changed' comparison (a write with the same caret scrolls)": [
        ("  if (key === followedCaret) return;\n", "")],
    "124: drop the scroll": [
        ("  el.desk.scrollTop = Math.max(0, Math.min(el.desk.scrollHeight - el.desk.clientHeight, centre));", "  void centre;")],
    "124: drop the drag exclusion": [
        ("  if (!caret || !session?.document || drag.active) return;", "  if (!caret || !session?.document) return;")],
}


def run(page_text: str) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "web").mkdir()
        (root / "web" / "e2-editor-app.js").write_text(page_text, encoding="utf-8")
        (root / "editor-shell-v2" / "tests").mkdir(parents=True)
        for name in FILES:
            shutil.copy(ROOT / "editor-shell-v2" / "tests" / name, root / "editor-shell-v2" / "tests" / name)
        out = subprocess.run(["node", "--test", "--test-reporter=tap",
                              *[str(root / "editor-shell-v2" / "tests" / n) for n in FILES]],
                             capture_output=True, text=True).stdout
    return [m.group(1) for m in re.finditer(r"^\s*not ok \d+ - (.*)$", out, re.M) if not m.group(1).endswith(".mjs")]


def main() -> int:
    page = (ROOT / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
    base = run(page)
    print(f"BASELINE (unmutated page): {len(base)} failing" + "".join(f"\n  {t}" for t in base))
    bad = bool(base)
    for name, edits in CASES.items():
        text = page
        for old, new in edits:
            if text.count(old) != 1:
                print(f"REFUSED {name}: the text to mutate is there {text.count(old)} times: {old[:70]!r}")
                return 2
            text = text.replace(old, new)
        failed = run(text)
        print(f"{'RED  ' if failed else 'GREEN'} {name}: {len(failed)} failing" + "".join(f"\n  {t}" for t in failed))
        bad |= not failed
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
