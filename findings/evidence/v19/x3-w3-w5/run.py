#!/usr/bin/env python3
"""X3 of spec SPEC-M3-paragraph-merge 31.4 = W3 and W5 of 28.4 on v19 (copied from ../../v18/w3-w5/run.py
2026-10-08; changed: e2-editor-v18 -> e2-editor-v19, and this docstring).  Four cold Chrome sessions, one at a time, with
../../v17/layout-corpus/fc-request/run.py's own `one_session` (same page, loader edit and readings):
  v19 on the corpus fixture A (W3); v17, the control and v19 on mono-reach's fixed-pitch probe (W5; v17 is there
  for PC-M2b, which names it).
That module's DOCS/EXPECTED/HERE are pointed at the two documents and this directory before any session.
Writes sessions.json and <profile>-<variant>-fc-log.txt beside this file; judge.py applies 28.4."""
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVID = HERE.parents[1]
spec = importlib.util.spec_from_file_location("fcreq", EVID / "v17/layout-corpus/fc-request/run.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.DOCS = {"A": m.DOCS["A"], "P": m.PROBE / "build/mono-reach-probe/fixed-pitch-probe.odt"}
m.EXPECTED = {"A": m.EXPECTED["A"], "P": (EVID / "v17/mono-reach/probe.sha256").read_text().split()[0]}
m.HERE = HERE
SESSIONS = [("e2-editor-v19", "A"), ("e2-editor-v17", "P"), ("e2-editor-v17-cjk-r5-ab", "P"), ("e2-editor-v19", "P")]

if __name__ == "__main__":
    report = {"startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "runSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "fcRequestRunSha256": hashlib.sha256((EVID / "v17/layout-corpus/fc-request/run.py").read_bytes()).hexdigest(),
              "sessions": [m.one_session(p, v) for p, v in SESSIONS]}
    report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (HERE / "sessions.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    sys.exit(0)
