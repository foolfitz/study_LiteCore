#!/usr/bin/env python3
"""C5 comparator (SPEC-M3-production-ui §17.4 C5): did porting the harness change any verdict?

Opens no browser and writes nothing; it reads committed reports.

Product path (`--product-path REF CAND`, two directories of the twelve `e2-editor-{v8,v19}-{browser}-r{1,2,3}.json`):
  a cell is (browser, arm, check), three rounds a side.
  forward  : REF is the base, CAND the candidate, spec SPEC-M3-paragraph-merge §23 with §36.2's row 1' for
             `recovery-returns-what-the-product-promised` exactly as release-0.2.11/product-path/judge.py
             defines it (its window: git-tracked e2-editor-v8-<browser>-r*.json carrying finding038Reproduced);
  reverse  : CAND is the base, REF the candidate, plain §23 (no row 1'), except cells whose outcomes already
             differed between the two committed counts `--noise A B` (same arm, same browser, same check,
             compared as multisets) -- computed here, not listed by hand.
  A difference is a cell red in either direction.

M3 runners (`--m3 NAME REF.json CAND.json`, repeatable): each report's `score` is reduced to its verdict
(`verdict`, or `lands`, or `allPass`) and to every leaf cell carrying pass/runs (or passed/of), keyed by its
path in `score`.  A difference is a different verdict, a cell present on one side only, or a cell whose
counts differ.

Exit 0: no difference.  1: at least one.  2: REFUSED (a report missing or unreadable, check ids differ).
The verdict is the SUMMARY line.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ARMS = ("v8", "v19")
BROWSERS = ("chrome", "firefox")
RECOVERY = "recovery-returns-what-the-product-promised"
EVIDENCE = Path(__file__).resolve().parents[2]          # findings/evidence


class Refused(Exception):
    pass


def load_set(directory: Path) -> tuple[dict, list[str]]:
    reports, ids0 = {}, None
    for b in BROWSERS:
        for a in ARMS:
            for n in (1, 2, 3):
                f = directory / f"e2-editor-{a}-{b}-r{n}.json"
                try:
                    r = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, ValueError) as error:
                    raise Refused(f"{f}: {error}")
                ids = [c["id"] for c in r.get("checks") or []]
                if ids0 is None:
                    ids0 = ids
                elif ids != ids0:
                    raise Refused(f"{f}: check ids differ from the first report of {directory}")
                reports[(b, a, n)] = r
    if not ids0:
        raise Refused(f"{directory}: no checks")
    return reports, ids0


def counts(reports: dict, b: str, a: str, i: int) -> dict:
    c = {"PASS": 0, "FAIL": 0, "NOT_ESTABLISHED": 0}
    for n in (1, 2, 3):
        o = reports[(b, a, n)]["checks"][i]["outcome"]
        c[o] = c.get(o, 0) + 1
    return c


def outcomes(reports: dict, b: str, a: str, i: int) -> list[str]:
    return sorted(reports[(b, a, n)]["checks"][i]["outcome"] for n in (1, 2, 3))


def window_ne(browser: str) -> tuple[int, int]:
    """Row 1''s window, as release-0.2.11/product-path/judge.py computes it."""
    listed = subprocess.run(["git", "-C", str(EVIDENCE), "ls-files", "-z", "--", f"**/e2-editor-v8-{browser}-r*.json"],
                            capture_output=True, check=True).stdout.decode().split("\0")
    total = ne = 0
    for name in filter(None, listed):
        try:
            report = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rec = next((c for c in report.get("checks") or [] if isinstance(c, dict) and c.get("id") == RECOVERY), None)
        if rec is None or "finding038Reproduced" not in (rec.get("observed") or {}):
            continue
        total += 1
        ne += rec.get("outcome") == "NOT_ESTABLISHED"
    return total, ne


def section23(base: dict, cand: dict, row1prime: bool) -> bool:
    if base["FAIL"] > 0:
        return cand["FAIL"] <= base["FAIL"]
    if base["NOT_ESTABLISHED"] > 0:
        return cand["FAIL"] == 0
    if row1prime:
        return cand["FAIL"] == 0
    return cand["PASS"] == 3


def fmt(c: dict) -> str:
    return ", ".join(f"{c[k]} {lab}" for k, lab in (("PASS", "PASS"), ("FAIL", "FAIL"), ("NOT_ESTABLISHED", "NE")) if c.get(k))


def compare_product_path(ref_dir: Path, cand_dir: Path, noise: tuple[Path, Path]) -> list[str]:
    ref, ids = load_set(ref_dir)
    cand, cand_ids = load_set(cand_dir)
    if cand_ids != ids:
        raise Refused("the two sets carry different check ids")
    na, na_ids = load_set(noise[0])
    nb, nb_ids = load_set(noise[1])
    if not (na_ids == nb_ids == ids):
        raise Refused("the noise sets carry different check ids")
    window = {b: window_ne(b) for b in BROWSERS}
    noisy = {(b, a, cid) for b in BROWSERS for a in ARMS for i, cid in enumerate(ids)
             if outcomes(na, b, a, i) != outcomes(nb, b, a, i)}
    print(f"product path: {len(ids)} checks x {len(BROWSERS)} browsers x {len(ARMS)} arms = "
          f"{len(ids) * len(BROWSERS) * len(ARMS)} cells; row 1' window "
          + ", ".join(f"{b} {window[b][1]} NE of {window[b][0]}" for b in BROWSERS)
          + f"; noise cells (differ between {noise[0].parent.name} and {noise[1].parent.name}): {len(noisy)}")
    for cell in sorted(noisy):
        print("   noise:", cell)
    differences = []
    for b in BROWSERS:
        for a in ARMS:
            for i, cid in enumerate(ids):
                r, c = counts(ref, b, a, i), counts(cand, b, a, i)
                forward = section23(r, c, cid == RECOVERY and window[b][1] > 0)
                reverse = (b, a, cid) in noisy or section23(c, r, False)
                if not (forward and reverse):
                    differences.append(f"product path {b} {a} {cid}: reference {fmt(r)} / ported {fmt(c)}"
                                       f" ({'forward' if not forward else ''}{' ' if not forward and not reverse else ''}"
                                       f"{'reverse' if not reverse else ''} red)")
    return differences


def cells_of(score, path=()) -> dict:
    found = {}
    if isinstance(score, dict):
        if "pass" in score and "runs" in score:
            return {"/".join(path): (score["pass"], score["runs"])}
        if "passed" in score and "of" in score:
            return {"/".join(path): (score["passed"], score["of"])}
        for k, v in score.items():
            found.update(cells_of(v, path + (str(k),)))
    return found


def verdict_of(score: dict):
    for key in ("verdict", "lands", "allPass"):
        if key in score:
            return f"{key}={score[key]}"
    return None


def compare_m3(name: str, ref_path: Path, cand_path: Path) -> list[str]:
    try:
        ref = json.loads(ref_path.read_text(encoding="utf-8"))["score"]
        cand = json.loads(cand_path.read_text(encoding="utf-8"))["score"]
    except (OSError, ValueError, KeyError) as error:
        raise Refused(f"{name}: {error}")
    out = []
    if verdict_of(ref) != verdict_of(cand):
        out.append(f"{name}: verdict {verdict_of(ref)} / {verdict_of(cand)}")
    rc, cc = cells_of(ref), cells_of(cand)
    if not rc:
        raise Refused(f"{name}: no cells in the reference score")
    for key in sorted(set(rc) | set(cc)):
        if rc.get(key) != cc.get(key):
            out.append(f"{name}: {key} reference {rc.get(key)} / ported {cc.get(key)}")
    print(f"{name}: {len(rc)} cells, verdict {verdict_of(ref)}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--product-path", nargs=2, type=Path, metavar=("REF", "CAND"))
    ap.add_argument("--noise", nargs=2, type=Path, metavar=("A", "B"),
                    default=[EVIDENCE / "release-0.2.10/product-path", EVIDENCE / "release-0.2.11/product-path"])
    ap.add_argument("--m3", nargs=3, action="append", default=[], metavar=("NAME", "REF", "CAND"))
    a = ap.parse_args()
    if not a.product_path and not a.m3:
        ap.error("nothing to compare")
    differences = []
    try:
        if a.product_path:
            differences += compare_product_path(a.product_path[0], a.product_path[1], tuple(a.noise))
        for name, ref, cand in a.m3:
            differences += compare_m3(name, Path(ref), Path(cand))
    except Refused as error:
        print("REFUSED:", error)
        print("SUMMARY  REFUSED")
        return 2
    for d in differences:
        print("  DIFF:", d)
    print(f"SUMMARY  differences {len(differences)}")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())
