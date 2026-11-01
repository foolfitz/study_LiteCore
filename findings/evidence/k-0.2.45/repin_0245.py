#!/usr/bin/env python3
"""K ruling item 7 for host 0.2.45 (SPEC-M3-K-0.2.45 sections 2, 3): every `frozenBy: []` pin of the K inventory plus the two C2 judges'
PAGE (as repin_0244.py), and what that list could not see: the two SHELL_MANIFEST constants census_old_identity.py found, and judge_p2's
boundaries commit gate (the owner's ruling, SPEC-M3-v29-tick-pacing append 8).  One script, one commit, the old value stays in the
line's comment.  The merge BINDING is not here: frozen, overridden in process.  Refuses unless every site matches exactly once.
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
inventory = json.loads((HERE / "k-binding-inventory.json").read_bytes())
WHY = "host 0.2.45 (engine v29, shell generation 83), 2026-11-02"
sites = [(p["path"], p["symbol"], p["current"], p["candidate"][:7] if p["symbol"] == "HOST_COMMIT" else p["candidate"])
         for p in inventory["pinOccurrences"]
         if p["differs"] and not p["frozenBy"] and isinstance(p["current"], str)]
PAGE_OLD = "3b0a2ebb92c3db282f9c832ab194249f963592698cf5c73d771998dc10203a6a"
PAGE_NEW = inventory["proposedMergeBinding"]["pageSha256"]
sites += [("findings/evidence/c-prime/c2/judge_c2.py", "PAGE", PAGE_OLD, PAGE_NEW),
          ("findings/evidence/typing-latency/judge_p2.py", "PAGE", PAGE_OLD, PAGE_NEW)]
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

LITERAL = [("wasm_sdk_probe/tools/check_m3_production_ui.py", 'SHELL_MANIFEST = "e2/editor-shell-v2-bundle-v82.json"',
            f'SHELL_MANIFEST = "e2/editor-shell-v2-bundle-v83.json"   # {WHY}; was v82'),
           ("wasm_sdk_probe/tools/check_m3_host_entry.py", 'SHELL_MANIFEST = Path("e2/editor-shell-v2-bundle-v82.json")',
            f'SHELL_MANIFEST = Path("e2/editor-shell-v2-bundle-v83.json")   # {WHY}; was v82'),
           ("findings/evidence/typing-latency/judge_p2.py", 'BOUNDARIES_COMMIT_MEDIAN = 10.0',
            'BOUNDARIES_COMMIT_MEDIAN = 16.0   # the owner, 2026-11-02, SPEC-M3-v29-tick-pacing append 8; was 10.0 (set on v20)'),
           ("findings/evidence/typing-latency/judge_p2.py", '  boundaries gap 200: median revisionMs <= 10 ms                            (§15.2)',
            '  boundaries gap 200: median revisionMs <= 16 ms                            (§15.2; SPEC-M3-v29-tick-pacing append 8)')]
for rel, old, new in LITERAL:
    text = texts.setdefault(rel, (ROOT / rel).read_text(encoding="utf-8"))
    if text.count(old) != 1:
        raise SystemExit(f"{rel}: {text.count(old)} sites for {old[:50]}")
    texts[rel] = text.replace(old, new)
    changed.append({"path": rel, "symbol": old.split(" ")[0], "old": old, "new": new})
for rel, text in texts.items():
    (ROOT / rel).write_text(text, encoding="utf-8")
(HERE / "repin-0.2.45.json").write_text(json.dumps({"why": WHY, "sites": changed}, indent=1) + "\n")
print(f"{len(changed)} sites in {len(texts)} files")
