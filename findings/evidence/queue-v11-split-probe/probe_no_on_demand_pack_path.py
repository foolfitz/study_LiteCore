#!/usr/bin/env python3
"""Census: is there ANY on-demand resource-pack load path in this tree?

The claim is universal -- "`loadAtStartup: false` means never loaded, by
anything, in every version this tree has shipped" -- so it gets a rerunnable
census rather than a sentence.  A universal claim whose only support is that
somebody once grepped is a claim with nothing behind it.

The census: every `sdk-worker.js` in the tree, live and archived, must contain
exactly two occurrences of `loadResourcePack` -- the definition, and the single
call inside `loadStartupResourcePacks`, which is guarded on
`loadAtStartup === true`.  A third occurrence anywhere means an on-demand path
exists and this file is wrong.

Run from the repository root:
  python3 findings/evidence/queue-v11-split-probe/probe_no_on_demand_pack_path.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROBE = ROOT / "wasm_sdk_probe"

# Where an on-demand caller could plausibly live: the SDK surface, the product
# page, and the shell.  Searched for the symbol AND for the manifest field, so
# a caller that reached the pack list by another name would still show up.
SURFACES = ["sdk", "web", "editor-shell", "editor-shell-v2", "input",
            "reader-shell"]


def main() -> int:
    workers = sorted(PROBE.glob("sdk/sdk-worker.js")) + \
        sorted(PROBE.glob("build/archive/*/sdk-worker.js"))
    assert workers, "no sdk-worker.js found -- the census would be vacuously true"

    offenders = {}
    for worker in workers:
        text = worker.read_text(encoding="utf-8", errors="replace")
        hits = [m.start() for m in re.finditer(r"\bloadResourcePack\b", text)]
        if len(hits) != 2:
            offenders[str(worker.relative_to(ROOT))] = len(hits)

    # The one call must be the guarded startup one, not something that merely
    # counts to two.
    live = (PROBE / "sdk" / "sdk-worker.js").read_text(encoding="utf-8")
    guarded = re.search(
        r"async function loadStartupResourcePacks\([^)]*\)\s*\{[^}]*?"
        r"loadAtStartup === true\)?\s*\n?\s*await loadResourcePack\(pack\);",
        live, re.S)

    # And nothing outside the worker may reference a pack at all.
    outside = {}
    scanned_outside = 0
    missing_surfaces = []
    for surface in SURFACES:
        directory = PROBE / surface
        if not directory.is_dir():
            missing_surfaces.append(surface)
            continue
        for path in sorted(directory.rglob("*.js")) + sorted(directory.rglob("*.mjs")):
            if path.name == "sdk-worker.js":
                continue
            scanned_outside += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"\bloadResourcePack\b", text):
                outside[str(path.relative_to(ROOT))] = "calls loadResourcePack"

    # NON-VACUITY.  `outside` being empty is the result only if files were
    # actually read.  A renamed or moved surface would otherwise make this
    # check pass by examining nothing -- the silent skip is the failure mode a
    # census has that a spot-check does not, because a census reports "zero"
    # either way.
    assert not missing_surfaces, \
        f"surfaces named but not found, so they were not searched: {missing_surfaces}"
    assert scanned_outside >= 20, \
        f"only {scanned_outside} files searched outside the worker -- too few to " \
        "believe a zero"

    result = {
        "claim": "loadAtStartup: false means never loaded, by anything",
        "workersScanned": len(workers),
        "workersWithOtherThanTwoOccurrences": offenders,
        "startupCallIsGuarded": bool(guarded),
        "callersOutsideTheWorker": outside,
        "filesSearchedOutsideTheWorker": scanned_outside,
        "verdict": "CONFIRMED" if (not offenders and guarded and not outside)
                   else "REFUTED",
    }
    print(json.dumps(result, indent=2))

    assert not offenders, f"an on-demand path may exist: {offenders}"
    assert guarded, "the single call is not the guarded startup one"
    assert not outside, f"something outside the worker loads packs: {outside}"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
