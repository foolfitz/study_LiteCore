#!/usr/bin/env python3
"""Is E1-C's shell bundle still exactly what the shipped verdict binds to?

Read-only, and that is the point.  `validate_e1_c.py` answers the same question
but WRITES its findings back into findings/evidence/, so calling it from a
static target rewrites verdict-bound evidence as a side effect of a syntax
check.  Re-deriving bound evidence should be a deliberate act with its own note
(finding 044 is what that looks like), never a thing that happens because
somebody ran `make`.

What this guards, concretely: `editor-shell/editor-client.js` and
`editor-session.js` are hash-registered in `e1/editor-shell-bundle-v1.json`, and
`E1_GO_ODT_EDITOR` holds only while both the source and the dist copies still
hash to the registered values.  SPEC E2-B's v2 shell lives in
`editor-shell-v2/` precisely so it cannot disturb them -- and "precisely so"
is worth a check rather than a comment, because the next person to add a file
will not have read the comment.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

MANIFEST = Path("e1/editor-shell-bundle-v1.json")


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    project = Path(__file__).resolve().parent.parent
    manifest_path = project / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    included = manifest.get("included") or []
    excluded = manifest.get("excluded") or []

    problems: list[str] = []
    hashes: dict[str, str | None] = {}
    for item in included:
        path = str(item["path"])
        expected = item["sha256"]
        for side, base in (("source", project), ("dist", project / "dist")):
            actual = sha256(base / path)
            if actual != expected:
                problems.append(
                    f"{side} {path}: {actual} != registered {expected}")
        hashes[path] = sha256(project / path)

    # The bundle digest, recomputed the way the manifest documents it.
    payload = "".join(f"{p}\0{hashes[p]}\n" for p in sorted(hashes)).encode()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != manifest.get("bundleSha256"):
        problems.append(f"bundle digest {digest[:16]} != registered "
                        f"{str(manifest.get('bundleSha256'))[:16]}")

    # No unaccounted module: this is the condition a new file beside the v1
    # shell would break, which is the whole reason editor-shell-v2/ exists.
    available = sorted(
        p.relative_to(project).as_posix()
        for directory in (project / "editor-shell", project / "input")
        for p in directory.glob("*.js"))
    accounted = {str(i["path"]) for i in included} | {str(i["path"]) for i in excluded}
    unaccounted = sorted(set(available) - accounted)
    if unaccounted:
        problems.append(f"unaccounted shell modules: {unaccounted} -- a v2 file "
                        "must live in editor-shell-v2/, not beside the v1 shell")

    print(json.dumps({
        "bundleSha256": digest[:16],
        "includedFiles": len(included),
        "availableModules": len(available),
        "intact": not problems,
        "problems": problems,
    }, indent=2, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
