#!/usr/bin/env python3
"""Red cases for judge_p.py (spec §16.3, last point), each run once, output recorded.

Before release P is implemented no report passes, so the base is SYNTHETIC: the four shipped-page red-case reports
(p-release/shipped-*.json, page 18c8afbe...) repaired in a temp directory into what P1 and 123-B ask for --
  p1:   raw.r2.keys / raw.r2.final rewritten so every key re-blits 400 bytes (the counters' other fields untouched);
  123b: the TILE_NOT_PAINTED toasts removed, allCurrentAfterLastKeyMs set to 700.0, and one new-image blit of the
        merged last band (y 35,805, 1,042 rows, the last key's revision) appended 700 ms after the last key.
The committed reports are not touched.  Each case changes ONE thing in ONE report of that base:

  base   the repaired four                                                         PASS (exit 0)
  K1     chrome p1, key 4's bytes raised to 3 % of the canvas                       FAIL chrome p1 bytes only
  K2     firefox 123b, one TILE_NOT_PAINTED toast added                             FAIL firefox 123b toast only
  K3     chrome p1, runner's wrapper hash swapped                                   REFUSED
  K4     firefox 123b, no toast recorded (raw.r2.toasts missing)                   FAIL firefox 123b toast only
  K5     chrome 123b, allCurrentAfterLastKeyMs None                                FAIL chrome 123b all-current only
  K6     chrome 123b, the appended last-band blit removed                          FAIL chrome 123b last band only
  K7     firefox p1, one key's snapshot missing (9 of 10 letters)                  FAIL firefox p1 typed only
  real   the four shipped reports unchanged                                        FAIL, 8 cells (exit 1)

Writes judge-p-red-cases.txt beside this file.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGE = HERE / "judge_p.py"
SHIPPED = "18c8afbe29e8a5472a7a5eb0fdfae8f94a3e7a95147972c83e192fc69ebeef1a"
BROWSERS = ("chrome", "firefox")


def load(browser, slot):
    return json.loads((HERE / "p-release" / f"shipped-{browser}-{slot}.json").read_text())


def letters(report):
    return [k for k in report["raw"]["r2"]["keys"] if len(k[0]) == 1]


def repair_p1(report):
    r = copy.deepcopy(report)
    keys = r["raw"]["r2"]["keys"]
    start = letters(r)[0][2]["staleBytes"]
    n = 0
    for k in keys:
        if len(k[0]) == 1:
            k[2]["staleBytes"] = start + 400 * n
            n += 1
    r["raw"]["r2"]["final"]["staleBytes"] = start + 400 * n
    return r


def repair_123b(report):
    r = copy.deepcopy(report)
    raw = r["raw"]
    raw["r2"]["toasts"] = [t for t in raw["r2"]["toasts"] if "TILE_NOT_PAINTED" not in t[1]]
    last_key = [t for k, t in raw["keys"] if len(k) == 1][-1]
    final = int(r["startRevision"]) + r["chars"]
    raw["blits"].append([round(last_key + 700.0, 1), 35805, 1042, final])
    r["allCurrentAfterLastKeyMs"] = 700.0
    return r


def main() -> int:
    base = {}
    for b in BROWSERS:
        base[(b, "p1")] = repair_p1(load(b, "p1"))
        base[(b, "123b")] = repair_123b(load(b, "123b"))

    def k1(reports):
        r = reports[("chrome", "p1")]
        canvas = r["raw"]["canvasWidth"] * r["raw"]["canvasHeight"] * 4
        ks = letters(r)
        bump = int(canvas * 0.03) - 400
        for k in ks[5:]:
            k[2]["staleBytes"] += bump
        r["raw"]["r2"]["final"]["staleBytes"] += bump

    def k2(reports):
        r = reports[("firefox", "123b")]
        r["raw"]["r2"]["toasts"].append([9000.0, "重繪失敗：TILE_NOT_PAINTED：引擎回了一張沒有畫進去的圖"])

    def k3(reports):
        r = reports[("chrome", "p1")]
        r["runner"] = r["runner"].replace("3dad37cbb03a769c", "0e3258418e5f55c5")

    def k4(reports):
        del reports[("firefox", "123b")]["raw"]["r2"]["toasts"]

    def k5(reports):
        reports[("chrome", "123b")]["allCurrentAfterLastKeyMs"] = None

    def k6(reports):
        reports[("chrome", "123b")]["raw"]["blits"].pop()

    def k7(reports):
        r = reports[("firefox", "p1")]
        keys = r["raw"]["r2"]["keys"]
        i = keys.index(letters(r)[3])
        del keys[i]

    cases = [
        ("base: the four shipped reports repaired (PASS)", None, SHIPPED),
        ("K1 chrome p1, key 4 at 3 % of the canvas (FAIL chrome p1 bytes only)", k1, SHIPPED),
        ("K2 firefox 123b, one TILE_NOT_PAINTED toast added (FAIL firefox 123b toast only)", k2, SHIPPED),
        ("K3 chrome p1, wrapper hash swapped (REFUSED)", k3, SHIPPED),
        ("K4 firefox 123b, no toast recorded (FAIL firefox 123b toast only)", k4, SHIPPED),
        ("K5 chrome 123b, allCurrentAfterLastKeyMs None (FAIL chrome 123b all-current only)", k5, SHIPPED),
        ("K6 chrome 123b, last-band blit removed (FAIL chrome 123b last band only)", k6, SHIPPED),
        ("K7 firefox p1, key 3's snapshot missing (FAIL firefox p1 typed only)", k7, SHIPPED),
    ]
    log = []
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for title, change, page in cases:
            reports = copy.deepcopy(base)
            if change:
                change(reports)
            d = tmp / title.split()[0].rstrip(":")
            d.mkdir()
            for (b, s), r in reports.items():
                (d / f"case-{b}-{s}.json").write_text(json.dumps(r))
            done = subprocess.run([sys.executable, str(JUDGE), "--page", page, "--dir", str(d), "--prefix", "case"],
                                  capture_output=True, text=True)
            out = "".join(l + "\n" for l in done.stdout.splitlines() if "RECORD" not in l)
            log.append(f"=== {title}\n{out.replace(str(tmp), '<tmp>')}exit {done.returncode}\n")
        done = subprocess.run([sys.executable, str(JUDGE), "--page", SHIPPED, "--prefix", "shipped"],
                              capture_output=True, text=True)
        out = "".join(l + "\n" for l in done.stdout.splitlines() if "RECORD" not in l)
        log.append(f"=== real: the four shipped reports unchanged (FAIL, 8 cells)\n{out}exit {done.returncode}\n")
    text = "".join(log)
    (HERE / "judge-p-red-cases.txt").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
