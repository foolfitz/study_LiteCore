#!/usr/bin/env python3
"""SPEC E2-B section 5 item 7: are the four action lists actually the same list?

The freeze condition inherited from E1-B section 6 is that the header, the
manifest, the worker's map and the client's allowlist all agree.  The negative
matrix proves each gate REFUSES when the manifest withholds something; this
proves the four lists were never out of step to begin with, which is a different
question and a cheaper one to answer.

It matters because three of the four are hand-maintained in different languages,
and the one time this project let such a pair drift -- `editor-client.js` gaining
underline and strikethrough while `editor-client.d.ts` did not -- it went
unnoticed across two shipped artifacts and the freeze test kept pinning eight of
ten actions.

Read-only.  Writes nothing, so it can be run from a static target without
touching verdict-bound evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def from_header() -> dict[str, int]:
    """Action ids as the C header defines them, both enums."""
    text = (PROJECT / "src" / "editor_api.h").read_text(encoding="utf-8")
    out: dict[str, int] = {}
    for match in re.finditer(r"OXSDK_EDITOR_V[12]_([A-Z_]+)\s*=\s*(\d+)", text):
        name = match.group(1).lower().replace("_", "-")
        out[name] = int(match.group(2))
    return out


def from_manifest(profile: Path) -> dict[str, int]:
    manifest = json.loads((profile / "sdk-manifest.json").read_text(encoding="utf-8"))
    actions = manifest.get("editorContract", {}).get("actions", {})
    if isinstance(actions, list):
        # A v1 profile carries a name list with no ids; nothing to compare.
        return {name: 0 for name in actions}
    return {name: spec.get("id") for name, spec in actions.items()}


def from_worker() -> dict[str, int]:
    """The worker's v2 map, which spreads the v1 map then adds five."""
    text = (PROJECT / "sdk" / "sdk-worker.js").read_text(encoding="utf-8")
    out: dict[str, int] = {}
    for block in ("EDITOR_V1_ACTION_IDS", "EDITOR_V2_ACTION_IDS"):
        start = text.find(f"const {block} = Object.freeze({{")
        if start < 0:
            continue
        end = text.find("});", start)
        for name, value in re.findall(r'"([a-z-]+)"\s*:\s*(\d+)', text[start:end]):
            out[name] = int(value)
    return out


def from_client() -> dict[str, int]:
    """The client allowlists: v1's ten names and v2's five, ids not carried."""
    names: set[str] = set()
    v1 = (PROJECT / "editor-shell" / "editor-client.js").read_text(encoding="utf-8")
    start = v1.find("export const EDITOR_V1_ACTIONS = Object.freeze([")
    end = v1.find("]);", start)
    names.update(re.findall(r'"([a-z-]+)"', v1[start:end]))
    v2 = (PROJECT / "editor-shell-v2" / "paragraph-editor-client.js").read_text(
        encoding="utf-8")
    start = v2.find("export const EDITOR_V2_PARAGRAPH_ACTIONS = Object.freeze([")
    end = v2.find("]);", start)
    names.update(re.findall(r'"([a-z-]+)"', v2[start:end]))
    return {name: 0 for name in names}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path,
                        default=PROJECT / "dist" / "profiles" / "e2-editor-v2")
    args = parser.parse_args()

    header = from_header()
    manifest = from_manifest(args.profile)
    worker = from_worker()
    client = from_client()

    problems: list[str] = []

    # Names first: all four must name the same set.
    sets = {"header": set(header), "manifest": set(manifest),
            "worker": set(worker), "client": set(client)}
    union = set().union(*sets.values())
    for label, names in sets.items():
        missing = sorted(union - names)
        extra = sorted(names - union)
        if missing:
            problems.append(f"{label} is missing {missing}")
        if extra:
            problems.append(f"{label} has {extra} that no other list has")

    # Then ids, where they are carried.  The client does not carry ids -- it
    # names actions and lets the worker map them -- so it is excluded here
    # rather than compared against a zero it never claimed.
    for name in sorted(set(header) & set(worker)):
        if header[name] != worker[name]:
            problems.append(f"{name}: header says {header[name]}, "
                            f"worker says {worker[name]}")
    for name in sorted(set(header) & set(manifest)):
        if manifest[name] and header[name] != manifest[name]:
            problems.append(f"{name}: header says {header[name]}, "
                            f"manifest says {manifest[name]}")

    print(json.dumps({
        "profile": str(args.profile),
        "counts": {label: len(names) for label, names in sets.items()},
        "actions": sorted(union),
        "agree": not problems,
        "problems": problems,
    }, indent=2, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
