#!/usr/bin/env python3
"""Red case for run_fixed.py's summary (no browser): fed fc-request's committed A sessions as stand-ins (v17,
control, v8), it must report K1's shape as DIFF (Liberation Mono vs Noto Sans Mono CJK KR); fed the v17 session
for both arms, it must report no DIFF."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("runfixed", HERE / "run_fixed.py")
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)
base = HERE.parent / "layout-corpus/fc-request"
a = {s["profile"]: s for s in json.loads((base / "fc-request.json").read_text())["sessions"] if s["variant"] == "A"}
a["e2-editor-v8"] = json.loads((base / "fc-request-v8.json").read_text())["session"]
out = rf.summarize(a)
diff = [x for x in out if x.strip().startswith("DIFF")]
assert any("K1-shape" in x and "Liberation Mono" in x and "Noto Sans Mono CJK KR" in x for x in diff), out
print("case 1 (fc-request's arms):", diff)
same = dict(a, **{"e2-editor-v17-cjk-r5-ab": a["e2-editor-v17"]})
out = rf.summarize(same)
assert not any(x.strip().startswith("DIFF") for x in out) and any(x.strip().startswith("SAME") for x in out), out
print("case 2 (identical arms): no DIFF,", sum(x.strip().startswith("SAME") for x in out), "SAME")
