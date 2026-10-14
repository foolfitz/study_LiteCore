#!/usr/bin/env python3
"""The real scrollbar thumb, read from a screenshot (SPEC-M3-scroll-page-bubble §5, the N2 instrument).

No DOM API reports where a scrollbar's thumb is, so the criterion reads it from
pixels: in the column x in [desk.right - 12, desk.right - 1], y in [desk.top,
desk.bottom], a row is "ink" when any of its pixels differs from the column's
modal colour by more than 40 in luminance; the thumb is the longest run of ink
rows of at least 12 px (a classic bar's arrow triangles are <= 8 px).  None
when no such run exists -- a number is never invented.

Shared by the probe (D1 presses on the thumb it reads) and the judge (N2).
Self-test: `python3 -I bubble_geometry.py` reads K4's two host screenshots
(scrollTop 4900 of the 60-page fixture) and a flattened column.
"""
from __future__ import annotations

import io
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

COLUMN_PX = 12
INK_LUMINANCE = 40
MIN_THUMB_PX = 12


def luminance(rgb) -> float:
    r, g, b = rgb[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def thumb_centre(png: bytes, desk: dict, column_px: int = COLUMN_PX) -> dict | None:
    """`desk`: {top, bottom, right} in CSS px of a DPR-1 screenshot.  Returns
    {centre, top, bottom, length, ink, mode} for the longest ink run, else None."""
    image = Image.open(io.BytesIO(png)).convert("RGB")
    right = int(round(desk["right"]))
    x0, x1 = max(0, right - column_px), min(image.width, right)
    y0, y1 = max(0, int(round(desk["top"]))), min(image.height, int(round(desk["bottom"])))
    if x1 <= x0 or y1 <= y0:
        return None
    column = image.crop((x0, y0, x1, y1))
    pixels = column.load()
    counts = Counter(pixels[x, y] for y in range(column.height) for x in range(column.width))
    mode = counts.most_common(1)[0][0]
    base = luminance(mode)
    ink_rows = [any(abs(luminance(pixels[x, y]) - base) > INK_LUMINANCE for x in range(column.width))
                for y in range(column.height)]
    best, start = None, None
    for y, ink in enumerate(ink_rows + [False]):
        if ink and start is None:
            start = y
        elif not ink and start is not None:
            length = y - start
            if length >= MIN_THUMB_PX and (best is None or length > best["length"]):
                best = {"top": y0 + start, "bottom": y0 + y, "length": length}
            start = None
    if best is None:
        return None
    best["centre"] = (best["top"] + best["bottom"]) / 2
    best["ink"] = sum(ink_rows)
    best["mode"] = list(mode)
    return best


def self_test() -> int:
    k4 = Path(__file__).resolve().parent.parent / "host-0.2.21" / "k4-host-css"
    desks = {"firefox": {"top": 160, "bottom": 954, "right": 1842}, "chrome": {"top": 160, "bottom": 940, "right": 1842}}
    expected = {"firefox": 230, "chrome": 234}   # the spec's eyeballed predictions, +-8
    ok = True
    out = {}
    for browser, desk in desks.items():
        png = (k4 / f"{browser}-probe-10-14n-long60-page-number-0-mid.png").read_bytes()
        read = thumb_centre(png, desk)
        out[browser] = read
        if read is None or abs(read["centre"] - expected[browser]) > 8:
            ok = False
        # the same column painted flat must read None, not a number
        image = Image.open(io.BytesIO(png)).convert("RGB")
        flat = image.copy()
        flat.paste((243, 245, 247), (desk["right"] - COLUMN_PX, desk["top"], desk["right"], desk["bottom"]))
        buffer = io.BytesIO()
        flat.save(buffer, format="PNG")
        out[f"{browser}-flat"] = thumb_centre(buffer.getvalue(), desk)
        if out[f"{browser}-flat"] is not None:
            ok = False
    print(json.dumps({"ok": ok, "expected": expected, "read": out}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test())
