#!/usr/bin/env python3
"""A diagnostic, not F3: is F3-83's moved Firefox cell the runner's wait or the engine?

run_v83_f3_clipboard.py with one thing changed in memory: the two waits on the 清除格式 label, which the FIRST of the clear's four
steps satisfies, wait instead for its toast 「已清除…」, written once after the fourth (e2-editor-app.js:2324).  If the cell comes back
to PASS with nothing else different, the move was the runner pressing into the page's own loop.  Nothing is edited and nothing
here is a count.
  diag_clear_wait.py --browser firefox --out DIR
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "wasm_sdk_probe/tools"))
import run_v83_f3_clipboard as r  # noqa: E402

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
