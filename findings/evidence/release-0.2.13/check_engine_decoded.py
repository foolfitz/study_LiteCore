#!/usr/bin/env python3
"""One-time binding measurement for 0.2.13 (findings/evidence/m3-autosave/review/DISPOSITION.md, codex item B4):
the M3 runners take "served" from the host's engine/MANIFEST.json; this reads every packaged file, decodes it
(gzip and zstd), and compares its sha256 -- encoded and decoded -- with the manifest's.  Also compares the decoded
e2-editor-app.js with dist/ and web/.  Reads only.

  python3 findings/evidence/release-0.2.13/check_engine_decoded.py [APP_DIR]
"""
import gzip
import hashlib
import json
import sys
from compression import zstd
from pathlib import Path

app = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Projects" / "Nextcloud_Apps" / "litecore"
repo = Path(__file__).resolve().parents[3]
manifest = json.loads((app / "engine" / "MANIFEST.json").read_text())
h = lambda b: hashlib.sha256(b).hexdigest()
bad, n = [], 0
for path, entry in sorted(manifest["files"].items()):
    for suffix, decode, enc_field in ((".gz", gzip.decompress, "gzSha256"), (".zst", zstd.decompress, "zstSha256")):
        raw = (app / "engine" / "files" / (path + suffix)).read_bytes()
        n += 1
        if h(raw) != entry[enc_field]:
            bad.append(f"{path}{suffix}: encoded {h(raw)[:16]} != manifest {entry[enc_field][:16]}")
        if h(decode(raw)) != entry["sha256"]:
            bad.append(f"{path}{suffix}: decoded {h(decode(raw))[:16]} != manifest {entry['sha256'][:16]}")
on_disk = {p.relative_to(app / "engine" / "files").as_posix() for p in (app / "engine" / "files").rglob("*") if p.is_file()}
named = {p + s for p in manifest["files"] for s in (".gz", ".zst")}
if on_disk != named:
    bad.append(f"files on disk but not in the manifest: {sorted(on_disk - named)}; named but missing: {sorted(named - on_disk)}")
page = manifest["files"]["e2-editor-app.js"]["sha256"]
for tree in ("dist", "web"):
    got = h((repo / "wasm_sdk_probe" / tree / "e2-editor-app.js").read_bytes())
    if got != page:
        bad.append(f"{tree}/e2-editor-app.js {got[:16]} != packaged {page[:16]}")
print(f"buildId {manifest['buildId']}  {len(manifest['files'])} files, {n} encoded copies read and decoded")
print(f"page {page}")
print("\n".join(bad) if bad else "every encoded copy matches the manifest, decoded and encoded; dist/ and web/ pages equal the packaged page")
sys.exit(1 if bad else 0)
