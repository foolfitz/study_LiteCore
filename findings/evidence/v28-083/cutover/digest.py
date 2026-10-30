import json, sys
from pathlib import Path
P = Path.cwd()
sys.path.insert(0, str(P / "tools"))
import build_e2_c_shell_bundle as b
s = b.compute(P)
m = json.loads((P / "e2/editor-shell-v2-bundle-v81.json").read_text())
rec = {i["path"]: i["sha256"] for i in m["included"]}
added = sorted(set(s["hashes"]) - set(rec)); removed = sorted(set(rec) - set(s["hashes"]))
changed = sorted(p for p in set(rec) & set(s["hashes"]) if rec[p] != s["hashes"][p])
print("candidateDigest", s["digest"][:16]); print("v81Digest", m["bundleSha256"][:16])
print("added", added); print("removed", removed); print("changed", changed)
stale = [p for p in s["included"] if s["distHashes"].get(p) != s["hashes"][p]]
print("distDiffersFromSource", stale)
print("problems(vs v81 manifest)", b.problems(P, s, m))
