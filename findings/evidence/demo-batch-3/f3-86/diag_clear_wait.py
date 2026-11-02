#!/usr/bin/env python3
"""A diagnostic, not F3: is F3-86's moved Firefox cell the runner's wait or the engine?  See PREDICTION.md.

Derived from ../../v29-177/f3-83/diag_clear_wait.py (bound by its own evidence; not edited).  Closed list of differences: this docstring;
the runner is run_v86_f3_clipboard.py.  It changes one thing in memory: the two waits on the 清除格式 label, which the first of the clear's
four steps satisfies, wait instead for its toast 「已清除…」, written once after the fourth.  Nothing is edited and nothing here is a count.
  diag_clear_wait.py --browser firefox --out DIR
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "wasm_sdk_probe/tools"))
import run_v86_f3_clipboard as r  # noqa: E402

LABEL = 'lambda st: "清除格式" in (st.get("latency") or ""), 30)'
DONE = 'lambda st: "已清除" in (evaluate(session, READ_TOAST) or ""), 30)'
r.REPLACEMENTS = r.REPLACEMENTS + (
    ("diag-clear-wait-normalise",
     '                evaluate(session, CLEAR_FORMAT)\n                wait_for(session,\n                         ' + LABEL,
     '                evaluate(session, CLEAR_TOAST)\n                evaluate(session, CLEAR_FORMAT)\n                wait_for(session,\n                         ' + DONE),
    ("diag-clear-wait-accumulate",
     '        evaluate(session, CLEAR_FORMAT)\n        wait_for(session,\n                 ' + LABEL,
     '        evaluate(session, CLEAR_TOAST)\n        evaluate(session, CLEAR_FORMAT)\n        wait_for(session,\n                 ' + DONE),
)
raise SystemExit(r.main())
