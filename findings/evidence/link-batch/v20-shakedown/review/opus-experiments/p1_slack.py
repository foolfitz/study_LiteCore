#!/usr/bin/env python3
"""How wrong can the page's region be and still match P1's expectation at every generated position?
Uses the runner's own parse_rects/span_of/status_text on the committed reports' regions."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "head" / "wasm_sdk_probe" / "tools"))
sys.dont_write_bytecode = True
import run_v20_shakedown as R  # noqa: E402


def text(rects, region):
    return R.status_text(R.span_of(rects, region))


def max_shift(rects, region, sign):
    """Largest |d| (twips, step 1) such that shifting the region by sign*d keeps the text."""
    base = text(rects, region)
    lo, hi = 0, 200000
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if text(rects, {**region, "y": region["y"] + sign * mid}) == base:
            lo = mid
        else:
            hi = mid - 1
    return lo


def min_scale(rects, region, sign):
    base = text(rects, region)
    lo, hi = 0.0, 0.5
    for _ in range(60):
        mid = (lo + hi) / 2
        f = 1 + sign * mid
        if text(rects, {**region, "y": region["y"] * f, "height": region["height"] * f}) == base:
            lo = mid
        else:
            hi = mid
    return lo


for name in ("report-chrome-main.json", "report-firefox-main.json", "report-chrome-mixed.json",
             "report-firefox-mixed.json"):
    r = json.loads((HERE / "reports" / name).read_text())
    arm = "p1-60" if "main" in name else "p1-mixed"
    p1 = r["results"][arm]
    rects = R.parse_rects(p1["reply"]["raw"])
    twips_per_px = p1["reply"]["docH"] / p1["view"]["paperHeightPx"]
    up = down = 10**9
    sc_up = sc_down = 1.0
    recomputed_ok = 0
    for p in p1["positions"]:
        region = p["regionTwips"]
        if text(rects, region) == p["expected"]:
            recomputed_ok += 1
        up = min(up, max_shift(rects, region, -1))
        down = min(down, max_shift(rects, region, +1))
        sc_up = min(sc_up, min_scale(rects, region, +1))
        sc_down = min(sc_down, min_scale(rects, region, -1))
    print(f"{name} {arm}: positions {len(p1['positions'])}, expectation reproduced {recomputed_ok}; "
          f"undetectable constant offset: up {up} / down {down} twips = "
          f"{min(up, down) / twips_per_px:.0f} CSS px; undetectable scale error: "
          f"+{sc_up * 100:.3f}% / -{sc_down * 100:.3f}%")
