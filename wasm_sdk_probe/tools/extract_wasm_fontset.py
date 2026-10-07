#!/usr/bin/env python3
"""The fonts a WASM profile lays out with, as a fontconfig a native run can use.

Why (SPEC-M3-paragraph-merge 25, owner's choice B, 2026-10-07): the merge
runner places the caret at the native R0c caret, which only works where the
native and WASM layouts are the same.  On the owner's document they are not
(WASM lines about 0.79 of the native height), because native LibreOffice lays
out with the machine's fonts and WASM with the profile's.  Re-running the
native round with the profile's fonts makes the coordinates comparable -- and
says whether the 0.79 is the fonts or the engine.

What it writes under OUT (build/, not the repository):
  fonts/          every font file the profile's packs put under
                  /instdir/share/fonts (Liberation, the CJK subset TTC)
  conf.d/         the profile's /instdir/share/fontconfig/conf.d, verbatim
  fonts.conf      the profile's fonts.conf with its <dir> and <cachedir>
                  entries replaced by OUT/fonts and OUT/cache -- nothing of
                  the machine's fonts is visible through it
  MANIFEST.json   source pack sha256s and every written file's sha256

  FONTCONFIG_FILE=OUT/fonts.conf fc-list    # what native will see

Read-only on dist/.  Refuses to write into an existing OUT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
FONT_DIR = "/instdir/share/fonts/"
CONF_DIR = "/instdir/share/fontconfig/"


def packs(profile: str) -> list[tuple[Path, Path, str]]:
    """(data, metadata, id) for every pack the profile loads at startup."""
    root = PROJECT / "dist" / "profiles" / profile
    manifest = json.loads((root / "sdk-manifest.json").read_text(encoding="utf-8"))
    out = []
    base = manifest["artifactFiles"]["soffice.data"]
    metas = sorted((root / base).parent.glob(Path(base).name.split(".")[0] + ".*.metadata"))
    if len(metas) != 1:
        raise SystemExit(f"cannot tell which metadata belongs to {base}: {metas}")
    out.append((root / base, metas[0], "base"))
    for pack in manifest.get("resourcePacks") or []:
        if pack.get("loadAtStartup"):
            out.append((root / pack["data"], root / pack["metadata"], pack["id"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="e2-editor-v16")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit(f"refusing to write into an existing {out}")
    (out / "fonts").mkdir(parents=True)
    (out / "conf.d").mkdir()
    (out / "cache").mkdir()
    record = {"profile": args.profile, "packs": {}, "files": {}}
    conf = None
    for data_path, meta_path, pack_id in packs(args.profile):
        data = data_path.read_bytes()
        record["packs"][pack_id] = hashlib.sha256(data).hexdigest()
        for entry in json.loads(meta_path.read_text(encoding="utf-8"))["files"]:
            name, blob = entry["filename"], data[entry["start"]:entry["end"]]
            if name.startswith(FONT_DIR) and name.lower().endswith((".ttf", ".otf", ".ttc")):
                target = out / "fonts" / Path(name).name
            elif name.startswith(CONF_DIR + "conf.d/"):
                target = out / "conf.d" / Path(name).name
            elif name == CONF_DIR + "fonts.conf":
                conf = blob.decode("utf-8")
                continue
            else:
                continue
            if target.exists():
                raise SystemExit(f"two packs write {target.name}")
            target.write_bytes(blob)
            record["files"][str(target.relative_to(out))] = hashlib.sha256(blob).hexdigest()
    if conf is None or not record["files"]:
        raise SystemExit("the profile's packs hold no fonts.conf or no fonts")
    # Only the profile's fonts, and a cache of our own: every <dir>/<cachedir>
    # the profile declares (/usr/share/fonts, ~/.fonts, xdg ...) is replaced.
    body = re.sub(r"\s*<dir[^>]*>[^<]*</dir>", "", conf)
    body = re.sub(r"\s*<cachedir[^>]*>[^<]*</cachedir>", "", body)
    if body.count("</fontconfig>") != 1:
        raise SystemExit("the profile's fonts.conf has no single </fontconfig>")
    body = body.replace("</fontconfig>",
                        f"  <dir>{out / 'fonts'}</dir>\n  <cachedir>{out / 'cache'}</cachedir>\n"
                        "</fontconfig>")
    if 'include ignore_missing="yes">conf.d<' not in body:
        raise SystemExit("the profile's fonts.conf does not include conf.d where expected")
    (out / "fonts.conf").write_text(body, encoding="utf-8")
    record["files"]["fonts.conf"] = hashlib.sha256(body.encode()).hexdigest()
    (out / "MANIFEST.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    fonts = sorted(k for k in record["files"] if k.startswith("fonts/"))
    print(f"{len(fonts)} fonts, {len(record['files']) - len(fonts) - 1} conf.d files -> {out}")
    for name in fonts:
        print("  ", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
