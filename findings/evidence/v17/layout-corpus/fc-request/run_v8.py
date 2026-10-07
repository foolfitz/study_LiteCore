#!/usr/bin/env python3
"""v8 on the same document A, one cold Chrome session, with run.py's own `one_session` (V8-PREDICTION.md).
Compares v8's request for the generic `monospace` (the family list of K1 in RESULT.md) and its bands with the two
arms already recorded in fc-request.json.  Writes fc-request-v8.json, e2-editor-v8-A-fc-log.txt, summary-v8.txt."""
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fcreq", HERE / "run.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

base = json.loads((HERE / "fc-request.json").read_text(encoding="utf-8"))
arm = {s["profile"]: s for s in base["sessions"] if s["variant"] == "A"}
v17, control = arm["e2-editor-v17"], arm["e2-editor-v17-cjk-r5-ab"]
k1 = {tuple(b["askedFamily"]) for b in v17["matchBlocks"]
      if b["phase"] == "fixture" and b["askedFamily"][:1] == ["Noto Sans Mono"] and "monospace" in b["askedFamily"]}
if len(k1) != 1:
    sys.exit(f"K1's family list is not unique in fc-request.json: {len(k1)}")
k1 = k1.pop()
started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
r = m.one_session("e2-editor-v8", "A")
report = {"startedAt": started, "completedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
          "runV8Sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "runSha256": hashlib.sha256((HERE / "run.py").read_bytes()).hexdigest(), "session": r}
(HERE / "fc-request-v8.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
runs = r.get("runs") or []
lines = [f"e2-editor-v8 A: boot {r['boot']} state {r['state']} languages {r['navigatorLanguages']} "
         f"confd {len(r['confdLoaded'])} logLines {r['logLines']} matchBlocks {len(r['matchBlocks'])} "
         f"(fixture {sum(1 for b in r['matchBlocks'] if b['phase'] == 'fixture')}) bands {len(runs)} "
         f"unsettled {r.get('unsettled')} band10 {runs[10] if len(runs) > 10 else None}"]
for name, other in (("v17", v17), ("control", control)):
    o = other.get("runs") or []
    d = [a[0] - b[0] for a, b in zip(runs, o)]
    lines.append(f"v8 minus {name} top per band (bands {len(runs)} vs {len(o)}): {d}; "
                 f"max |diff| {max((abs(x) for x in d), default=None) if len(runs) == len(o) else None}")
same_family = [b for b in r["matchBlocks"] if b["phase"] == "fixture" and tuple(b["askedFamily"]) == k1]
lines.append(f"fixture-phase blocks with K1's family list ({len(k1)} names): {len(same_family)}")
for b in same_family:
    lines.append(f"  lang {b['askedLang']} charset {b['askedCharset']} -> {m.answer(b)} score {b['bestScore']}")
others = [b for b in r["matchBlocks"] if b["phase"] == "fixture" and "monospace" in b["askedFamily"]
          and tuple(b["askedFamily"]) != k1]
lines.append(f"other fixture-phase blocks naming monospace: {len(others)}")
for b in others:
    lines.append(f"  {m.show(m.key(b))} -> {m.answer(b)}")
(HERE / "summary-v8.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
