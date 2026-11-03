#!/usr/bin/env python3
"""Remove the local, git-ignored raw .json copies under findings/evidence/link-batch-v23 whose tracked .json.gz decompresses to the same bytes.
  remove_raw_v23.py dry|remove
Writes findings/evidence/link-batch-v23/LOCAL-RAW-REMOVED-2026-11-03.json (the list, with sha256) on remove."""
import gzip, hashlib, json, subprocess, sys
from pathlib import Path
REPO = Path("/home/jiajun/LibreOffice/study_LiteCore")
BASE = REPO / "findings/evidence/link-batch-v23"
mode = sys.argv[1]
def sha_file(path, opener=open):
    h = hashlib.sha256(); n = 0
    with opener(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk); n += len(chunk)
    return h.hexdigest(), n
tracked = set(subprocess.run(["git", "-C", str(REPO), "ls-files", "findings/evidence/link-batch-v23"], capture_output=True, text=True, check=True).stdout.splitlines())
candidates = sorted(p for p in BASE.rglob("*.json") if p.stat().st_size > (1 << 20) and p.with_name(p.name + ".gz").exists())
ok, refused = [], []
for p in candidates:
    rel = str(p.relative_to(REPO)); gz = rel + ".gz"
    if rel in tracked: refused.append((rel, "the raw json is tracked")); continue
    if gz not in tracked: refused.append((rel, "its .gz is not tracked")); continue
    ignored = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", rel]).returncode == 0
    if not ignored: refused.append((rel, "not ignored by git")); continue
    raw_sha, raw_n = sha_file(p)
    gz_sha, gz_n = sha_file(REPO / gz, gzip.open)
    if (raw_sha, raw_n) != (gz_sha, gz_n): refused.append((rel, "gz content differs")); continue
    ok.append({"path": rel, "bytes": raw_n, "sha256": raw_sha, "gz": gz, "gzFileSha256": sha_file(REPO / gz)[0]})
total = sum(e["bytes"] for e in ok)
print(json.dumps({"candidates": len(candidates), "removable": len(ok), "removableMB": round(total / 1048576), "refused": refused[:20], "refusedCount": len(refused)}, indent=1))
if mode == "remove" and ok:
    record = {"date": "2026-11-03", "why": "disk full; the owner chose to remove local raw copies whose tracked .json.gz is byte-identical",
              "restore": "gunzip -k <path>.gz (or the storage-index restore commands in STORAGE.md); each file's sha256 is below",
              "removed": ok, "bytes": total}
    (BASE / "LOCAL-RAW-REMOVED-2026-11-03.json").write_text(json.dumps(record, indent=1) + "\n")
    for e in ok:
        (REPO / e["path"]).unlink()
    print("removed", len(ok))
