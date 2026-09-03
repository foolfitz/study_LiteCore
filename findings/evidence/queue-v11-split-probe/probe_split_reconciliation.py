#!/usr/bin/env python3
"""Probe criterion 1 of the v11 split: does v11's image split and reunite?

`PLAN-2026-08-28-the-v11-cutover-horizon.md`, addendum part 2, B-2 criterion 1:
"`create_pack` splits v11's image into base + packs whose file sets and bytes
reunite to v11's image exactly, verified from the metadata."

This asserts rather than prints, so it can go red.  It writes the sliced packs
to a scratch directory and does NOT touch `dist/` -- a probe that mints
artifacts into the tree while the gate is running is how a candidate moves
under its own soak.

Run from `wasm_sdk_probe/`:
  python3 ../findings/evidence/queue-v11-split-probe/probe_split_reconciliation.py --out <scratch>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3] / "wasm_sdk_probe"
sys.path.insert(0, str(PROJECT / "tools"))
from build_r5_profiles import classify, create_pack, sha256_file  # noqa: E402

DEFAULT_PROFILE = PROJECT / "dist" / "profiles" / "e2-editor-v11"
SHARED = PROJECT / "dist" / "profiles" / "resources"

# The product core's packs, for the identity comparison.  Not a dependency of
# the split -- the split profile gets its own files either way (B-2) -- but the
# comparison is what says the font corpus is unchanged between the two cores,
# which is what makes criterion 3 a wiring question rather than a content one.
PRODUCT_PACKS = {
    "cjk": "cjk-r5.b76b0433203017ca.data",
    "fallback-fonts": "fallback-fonts-r5.33856e2a082148dd.data",
    "base": "base-r5.ba15a988a7fec468.data",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True,
                        help="scratch directory for the sliced packs")
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE,
                        help="the profile to split; exists so this probe can "
                             "be pointed at a doctored copy and shown to go "
                             "red. A probe whose red case has never run is a "
                             "green light with no evidence behind it")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    image = args.profile_dir / "soffice.data"
    metadata = json.loads((args.profile_dir / "soffice.data.js.metadata")
                          .read_text(encoding="utf-8"))
    entries = metadata["files"]
    image_bytes = image.stat().st_size

    # classify() raises on non-contiguous or duplicated entries, so reaching
    # the next line is itself part of the result.
    groups = classify(entries)

    packed = {name: sum(e["end"] - e["start"] for e in group)
              for name, group in groups.items()}
    total = sum(packed.values())

    assert total == image_bytes, (
        f"group bytes {total} != image {image_bytes}")
    assert total == metadata["remote_package_size"], (
        f"group bytes {total} != remote_package_size "
        f"{metadata['remote_package_size']}")

    all_names = sorted(e["filename"] for e in entries)
    grouped_names = sorted(e["filename"]
                           for group in groups.values() for e in group)
    assert all_names == grouped_names, "the groups are not a partition"
    assert len(set(grouped_names)) == len(grouped_names), "duplicate filenames"

    made = {name: create_pack(image, group, args.out, f"{name}-v11")
            for name, group in groups.items()}

    identity = {}
    for name, filename in PRODUCT_PACKS.items():
        ours = sha256_file(args.out / made[name]["data"])
        theirs = sha256_file(SHARED / filename)
        identity[name] = {"v11": ours, "product": theirs, "identical": ours == theirs}

    # The two font packs must be byte-identical to the product core's, and the
    # base must NOT be -- the base carries the core's registry and (on v11) the
    # Calc configuration.  A base that matched would mean the wrong image was
    # read; a font pack that did not would mean the corpora differ and
    # criterion 3 is a content question after all.
    assert identity["cjk"]["identical"], "v11's CJK pack differs from the product core's"
    assert identity["fallback-fonts"]["identical"], \
        "v11's fallback-font pack differs from the product core's"
    assert not identity["base"]["identical"], \
        "v11's base pack is identical to the product core's -- wrong image?"

    print(json.dumps({
        "criterion": "B-2 criterion 1 -- reconciliation",
        "imageBytes": image_bytes,
        "entries": len(entries),
        "groups": {name: {"files": len(group), "bytes": packed[name]}
                   for name, group in groups.items()},
        "reunites": True,
        "partitionExact": True,
        "packIdentityAgainstProductCore": identity,
        "verdict": "PASS",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
