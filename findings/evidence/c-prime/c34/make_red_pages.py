#!/usr/bin/env python3
"""The two pages ruling condition 3 asks C3 / C4 to turn red on (SPEC-M3-production-ui §17.9 (c)), made from a
C′ page by exact text replacement (refused when a text is not there exactly once).

  never-stale-outside   bands outside the window are kept (both cache bounds removed) AND, at every change,
                        relabelled with the new counter -- "never mark off-window bands stale".  Its data-bands
                        say current; the pixels are from before the change.  C4 must be red.
  label-at-reply        a band is stamped with the counter when its reply ARRIVES, so one in flight across a
                        change counts as current.  C3 (or C4) must be red.

  make_red_pages.py PAGE OUT_DIR    -> OUT_DIR/{never-stale-outside,label-at-reply}.js and their sha256 printed
"""
import hashlib
import sys
from pathlib import Path

RELABEL = ("\nfunction relabelOutside() {\n"
           "  const bands = renderBands(docRows);\n"
           "  lastTiles.forEach((strip, index) => { if (strip && !bandInWindow(bands[index])) strip.label = changes; });\n"
           "}\n")
PAGES = {
    "never-stale-outside": [
        ("\n  for (const band of bands) if (!bandInWindow(band)) lastTiles[band.index] = null;", "\n"),
        ("\n    for (const band of bands) if (!bandInWindow(band)) lastTiles[band.index] = null;", "\n"),
        ("    changes += 1;\n    publishWindow();", "    changes += 1;\n    relabelOutside();\n    publishWindow();"),
        ("        changes += 1;   // §17.9 (c): every band asked for before this is stale\n",
         "        changes += 1;   // §17.9 (c): every band asked for before this is stale\n        relabelOutside();\n"),
        ("\nfunction bandInWindow(band) {", RELABEL + "\nfunction bandInWindow(band) {"),
    ],
    "label-at-reply": [
        ("        y: band.top,\n        label,\n", "        y: band.top,\n        label: changes,\n"),
    ],
}


def main() -> int:
    page = Path(sys.argv[1]).read_text(encoding="utf-8")
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    print(f"from {sys.argv[1]} {hashlib.sha256(page.encode()).hexdigest()[:16]}")
    for name, edits in PAGES.items():
        text = page
        for old, new in edits:
            if text.count(old) != 1:
                print(f"REFUSED {name}: {text.count(old)} occurrences of {old[:60]!r}")
                return 2
            text = text.replace(old, new)
        (out / f"{name}.js").write_text(text, encoding="utf-8")
        print(f"{name} {hashlib.sha256(text.encode()).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
