#!/usr/bin/env python3
"""Package the E2-C round-two product profile (v3).

A separate builder from `build_e2_b_profile.py`, not a flag on it, for the same
reason E2-B 5.8 gave: a builder that can emit either version is a builder whose
output nobody can name.  It reuses that module's machinery -- importing does not
build anything -- and changes exactly what round two changes.

What differs from v2, and nothing else:

  * `abiVersion` 3.  The engine binary reports 3 as well, and the worker
    compares the two with an exact match at init (`sdk-worker.js:810-818`), so a
    v2 client running against this binary fails to start rather than running on
    a contract whose fields mean something else.  That handshake is why the
    contract version and the capability string do NOT move: moving them would
    make this profile unreachable through the worker's operation map, which is
    the defect SPEC E2-C 2.2 exists to record.

  * two `limits` debts the spec recorded as owed to this relink:
      - `no-note-paragraphs` on the five paragraph actions (4.2): a paragraph
        carrying a footnote or endnote cannot be verified, and until now the
        manifest said nothing about it;
      - the ten inherited actions keep `gestures: ["collapsed"]`, which the
        engine now ENFORCES (2.5).  Declaring anything wider needs a
        cross-paragraph measurement that does not exist (9.5.7).

The `enabled` flag now reaches core (finding 045), so the four inline formats
are setters rather than toggles.  That is a behaviour change with no manifest
field of its own -- it rides on `abiVersion`, which is exactly what an ABI
version is for.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_e2_b_profile as v2  # noqa: E402
from e1_support import write_json  # noqa: E402

ABI_VERSION = 3

# The notes limit applies to the five paragraph actions: their barrier is what
# cannot verify a paragraph carrying note apparatus.  The ten inherited actions
# do not go through that barrier, so claiming it for them would be a narrowing
# nobody measured -- the opposite error, and just as bad.
NOTE_LIMIT = "no-note-paragraphs"


def action_map() -> dict:
    actions = v2.action_map(cross_paragraph=True)
    for name, spec in actions.items():
        if name in v2.V2_PARAGRAPH_ACTIONS:
            spec["limits"] = [*spec["limits"], NOTE_LIMIT]
    return actions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--exports", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    # Same refusal as v2's: a profile that exports a diagnostic symbol can never
    # be the product one, and the check runs before anything is written.
    problems = v2.refuse_non_product(args.exports)
    if problems:
        raise SystemExit("refusing to build a v3 product profile:\n  "
                         + "\n  ".join(problems))

    manifest_written = v2.build_profile(
        source_manifest=args.source_manifest, loader=args.loader,
        wasm=args.wasm, worker=args.worker, output=args.output,
        exports=args.exports, cross_paragraph=True)

    manifest_path = args.output / "sdk-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_written is not None
    manifest["profile"] = "e2-editor-v3"
    manifest["sdkVersion"] = manifest["sdkVersion"].replace(
        "+e2-editor-v2", "+e2-editor-v3")
    contract = manifest["editorContract"]
    contract["abiVersion"] = ABI_VERSION
    contract["actions"] = action_map()
    contract["inlineFormatEnabledIsHonoured"] = True
    manifest["editorContract"] = contract
    write_json(manifest_path, manifest)

    # SPEC E2-C 11.3: the manifest is the fifth bound identity this round,
    # because this round changes what is IN it -- abiVersion, limits, gestures
    # -- and the gesture mask is pushed into the engine from it at init.  Its
    # own sha256 therefore has to be reportable, and it is computed here rather
    # than by whoever remembers to.
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    print(json.dumps({
        "profile": "e2-editor-v3",
        "abiVersion": ABI_VERSION,
        "wasmSha256": contract.get("wasmSha256"),
        "manifestSha256": digest,
        "actions": len(contract["actions"]),
        "noteLimitOn": sorted(name for name, spec in contract["actions"].items()
                              if NOTE_LIMIT in spec.get("limits", [])),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
