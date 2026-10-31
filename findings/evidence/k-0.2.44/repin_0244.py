#!/usr/bin/env python3
"""K ruling item 7 for host 0.2.44 (SPEC-M3-K-0.2.44 section 2): move every `frozenBy: []` pin of the K inventory, plus the
two C2 judges' PAGE (0.2.26's repin listed them; the AST inventory reads only the names it was given), to host 0.2.44:
page 3b0a2ebb..., narrow session d037eaa4..., buildId dacdfa20fd4ff1ea, host a97724f, version 0.2.44, shell generation 82
a02673fa....  One script, one commit; the old value stays in the line's comment.  The merge BINDING is not here: it is
frozen and is overridden in-process (K ruling item 4).  Refuses unless every pin site matches exactly once.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
inventory = json.loads((HERE / "k-binding-inventory.json").read_bytes())
WHY = "host 0.2.44 (engine v28, shell generation 82), 2026-10-31"
# HOST_COMMIT is a prefix: the runners compare it with `git log --oneline`'s short hash (fixed by execution, see the README).
sites = [(p["path"], p["symbol"], p["current"], p["candidate"][:7] if p["symbol"] == "HOST_COMMIT" else p["candidate"])
         for p in inventory["pinOccurrences"]
         if p["differs"] and not p["frozenBy"] and isinstance(p["current"], str)]  # autosave's `PAGE_SHA256 = None` is its self-test's
PAGE_OLD = "605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f"
PAGE_NEW = inventory["proposedMergeBinding"]["pageSha256"]
sites += [("findings/evidence/c-prime/c2/judge_c2.py", "PAGE", PAGE_OLD, PAGE_NEW),
          ("findings/evidence/typing-latency/judge_p2.py", "PAGE", PAGE_OLD, PAGE_NEW)]
if len(sites) != 24:
    raise SystemExit(f"{len(sites)} sites, not 22 + 2")
texts, changed = {}, []
for rel, symbol, old, new in sites:
    text = texts.setdefault(rel, (ROOT / rel).read_text(encoding="utf-8"))
    pattern = re.compile(rf'^(\s*{symbol}(?:: str \| None)? = ")({re.escape(old)})(".*)$', re.M)
    if len(pattern.findall(text)) != 1:
        raise SystemExit(f"{rel} {symbol}: {len(pattern.findall(text))} sites for {old[:16]}")
    def replace(m):
        tail = m.group(3)
        note = f"{WHY}; was {old[:16]}"
        return f"{m.group(1)}{new}\"   # {note}" + (f"; {tail[1:].lstrip().removeprefix('# ')}" if tail[1:].strip() else "")
    texts[rel] = pattern.sub(replace, text)
    changed.append({"path": rel, "symbol": symbol, "old": old, "new": new})
for rel, text in texts.items():
    (ROOT / rel).write_text(text, encoding="utf-8")
(HERE / "repin-0.2.44.json").write_text(json.dumps({"why": WHY, "sites": changed}, indent=1) + "\n")
print(f"{len(changed)} sites in {len(texts)} files")
