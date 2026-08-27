#!/usr/bin/env python3
"""Produce -- and, with --write, perform -- a cutover of the product page.

WHY THIS IS A TOOL AND NOT AN EDIT.  A cutover is two lines: the worker URL and
the pinned wasm hash. Editing them by hand is easy and that is the problem --
the page that gets measured before a cutover and the page that gets shipped by
it would be two acts of typing, and "they are the same bytes" would be a claim.

`run_e2_c_product_path.py --candidate-profile <name>` measures the page THIS
tool produces, and writes its sha256 into the report. Running this with --write
produces those bytes again from the same function. So the cutover's evidence is
a hash comparison rather than a memory of having been careful.

Adjudicated 2026-08-27, and it resolves a gate that could not otherwise open:
non-diagnostic evidence for a profile required the cutover, and the cutover
required non-diagnostic evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))

from run_e2_c_product_path import repointed_page  # noqa: E402

PAGE = PROJECT / "web" / "e2-editor-app.js"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True,
                        help="the profile the page should point at")
    parser.add_argument("--out", help="write the candidate page here instead "
                                      "of to web/e2-editor-app.js")
    parser.add_argument("--write", action="store_true",
                        help="PERFORM the cutover: overwrite the product page. "
                             "Without it nothing is written and the sha256 is "
                             "printed, which is what a candidate run measures")
    parser.add_argument("--expect-sha256",
                        help="refuse unless the produced page has this sha256 "
                             "-- pass the `candidateCutover.pageSha256` from "
                             "the run that measured it")
    args = parser.parse_args()

    manifest = PROJECT / "dist" / "profiles" / args.profile / "sdk-manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"profile {args.profile!r} has no manifest at {manifest}")
    source = PAGE.read_text(encoding="utf-8")
    page, pin_before, wasm = repointed_page(source, args.profile, manifest)
    digest = hashlib.sha256(page.encode("utf-8")).hexdigest()

    # BEFORE anything is written: a mismatch here means the tree moved between
    # the measurement and the cutover, and the honest answer is to measure again
    # rather than to ship bytes nobody ran.
    if args.expect_sha256 and digest != args.expect_sha256:
        raise SystemExit(
            f"the candidate page is {digest}, not the {args.expect_sha256} that "
            "was measured. Something in web/e2-editor-app.js changed since that "
            "run; measure the new candidate rather than shipping it unmeasured.")

    target = Path(args.out) if args.out else PAGE
    if args.out or args.write:
        target.write_text(page, encoding="utf-8")

    print(f"profile        {args.profile}")
    print(f"pin            {pin_before} -> {wasm[:16]}")
    print(f"pageSha256     {digest}")
    print(f"unchanged      {page == source}")
    print(f"written        {target if (args.out or args.write) else 'no'}")
    if not (args.out or args.write):
        print("\nNothing was written. This is the page a "
              f"`--candidate-profile {args.profile}` run measures; pass --write "
              "with --expect-sha256 to perform the cutover.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
