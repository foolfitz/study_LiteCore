#!/usr/bin/env python3
"""Red cases for run.py's census/diff (no browser): fed V3's committed fc-debug sessions
(../../v3-v4/run/fc-debug.json) as stand-ins, the summary must (1) report nothing when the arms are identical,
(2) name a single mutated answer, (3) name keys that differ, (4) report a 3 px band shift."""
import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fcreq", HERE / "run.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
v3 = {(p["profile"], p["locale"]): p for p in
      json.loads((HERE.parent.parent / "v3-v4/run/fc-debug.json").read_text())["profiles"]}
same = v3[("e2-editor-v17", "zh-TW")]
fake = lambda p, runs: {**p, "boot": "ready", "state": "ready", "runs": runs, "unsettled": False}  # noqa: E731
flat, shifted = [[0, 5]] * 11, [[0, 5]] * 10 + [[3, 8]]
arms = lambda a, b, c, d: {("e2-editor-v17", "A"): a, ("e2-editor-v17-cjk-r5-ab", "A"): b,  # noqa: E731
                           ("e2-editor-v17", "D"): c, ("e2-editor-v17-cjk-r5-ab", "D"): d}
out = m.summarize(arms(*(fake(same, flat),) * 4))
assert not any("answer differs" in x or "-only" in x for x in out), out
assert "A: bands 11 vs 11; control-minus-v17 top per band [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; max |diff| 0" in out
print("case 1 (identical arms): no difference reported")
mutated = copy.deepcopy(same)
[b for b in mutated["matchBlocks"] if b["phase"] == "fixture"][3]["bestFamily"] = ["Noto Sans Mono CJK TC"]
out = m.summarize(arms(fake(same, flat), fake(mutated, shifted), fake(same, flat), fake(same, flat)))
hits = [x for x in out if "answer differs" in x]
assert len(hits) == 1 and "Noto Sans Mono CJK TC" in hits[0], out
assert any(x.startswith("A: ") and x.endswith("max |diff| 3") for x in out), out
print("case 2 (one mutated answer, 3 px shift):", hits[0][:120], "...")
out = m.summarize(arms(fake(same, flat), fake(same, flat), fake(v3[("e2-editor-v17", "en-US")], flat), fake(same, flat)))
assert any("e2-editor-v17: keys only in A (fixture phase)" in x and not x.endswith("only in D 0") for x in out), out
assert any(x.startswith("  D-only") for x in out) and any(x.startswith("  v17-only") for x in out), out
print("case 3 (different requests): A-only/D-only and v17-only keys reported")
