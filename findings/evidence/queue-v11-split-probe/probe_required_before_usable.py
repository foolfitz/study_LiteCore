#!/usr/bin/env python3
"""B-2 criterion 4 — required-before-usable, from every file each manifest references.

The plan's own counting method: "Counted from every file each manifest actually
references."  Startup cost is the loader, the wasm, the base image and its
metadata, plus every resource pack with `loadAtStartup: true`.

A pack with `loadAtStartup: false` is counted in `totalBytes` and NOT in
`requiredBeforeUsable` -- and, per finding 085, it is never fetched at any
later point either, so `totalBytes` is a property of the directory rather than
of anything a client downloads.  The column is reported under a name that says
so.

Run from `wasm_sdk_probe/`:
  python3 ../findings/evidence/queue-v11-split-probe/probe_required_before_usable.py
"""
from __future__ import annotations

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3] / "wasm_sdk_probe"
PROFILES = ["e2-editor-v8", "e2-editor-v11", "e2-editor-v12"]
MIB = 1024 * 1024


def measure(profile: str) -> dict:
    root = PROJECT / "dist" / "profiles" / profile
    manifest = json.loads((root / "sdk-manifest.json").read_text(encoding="utf-8"))

    def size(reference: str) -> int:
        path = (root / reference).resolve()
        assert path.is_file(), f"{profile}: {reference} does not resolve to a file"
        return path.stat().st_size

    startup, deferred, seen = 0, 0, []
    for key, reference in manifest["artifactFiles"].items():
        n = size(reference)
        startup += n
        seen.append((key, reference, n))

    for pack in manifest.get("resourcePacks", []):
        n = size(pack["data"]) + size(pack["metadata"])
        if pack.get("loadAtStartup") is True:
            startup += n
        else:
            deferred += n
        seen.append((pack["id"], pack["data"], n))

    return {
        "profile": profile,
        "filesReferenced": len(seen),
        "requiredBeforeUsable": startup,
        "requiredBeforeUsableMiB": round(startup / MIB, 1),
        "declaredButNeverFetched": deferred,
        "declaredButNeverFetchedMiB": round(deferred / MIB, 1),
        "onDiskTotal": startup + deferred,
    }


def main() -> int:
    rows = [measure(p) for p in PROFILES]
    by = {r["profile"]: r for r in rows}

    # Non-vacuity: a profile whose manifest referenced nothing would report 0
    # and read as "free".
    for r in rows:
        assert r["filesReferenced"] >= 4, f"{r['profile']}: only {r['filesReferenced']} files"
        assert r["requiredBeforeUsable"] > 100 * MIB, f"{r['profile']}: implausibly small"

    base = by["e2-editor-v8"]["requiredBeforeUsable"]
    for r in rows:
        r["deltaAgainstV8"] = r["requiredBeforeUsable"] - base
        r["deltaAgainstV8MiB"] = round(r["deltaAgainstV8"] / MIB, 1)
        r["deltaAgainstV8Percent"] = round(100 * r["deltaAgainstV8"] / base, 1)

    print(json.dumps({"criterion": "B-2 criterion 4 -- the figure",
                      "profiles": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
