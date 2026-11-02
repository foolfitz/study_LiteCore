import json, sys
from pathlib import Path
P = Path.cwd()
sys.path.insert(0, str(P / "tools"))
import build_e2_c_shell_bundle as b
s = b.compute(P)
m = json.loads((P / "e2/editor-shell-v2-bundle-v84.json").read_text())
rec = {i["path"]: i["sha256"] for i in m["included"]}
print("candidateDigest", s["digest"][:16]); print("v84Digest", m["bundleSha256"][:16])
print("added", sorted(set(s["hashes"]) - set(rec))); print("removed", sorted(set(rec) - set(s["hashes"])))
print("changed", sorted(p for p in set(rec) & set(s["hashes"]) if rec[p] != s["hashes"][p]))
print("distDiffersFromSource", [p for p in s["included"] if s["distHashes"].get(p) != s["hashes"][p]])
