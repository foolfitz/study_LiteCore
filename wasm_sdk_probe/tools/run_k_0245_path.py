#!/usr/bin/env python3
"""K 0.2.45's product-path runner (specs/SPEC-M3-K-0.2.45.md section 4): tools/run_v83_f3_clipboard.py with two more in-memory
replacements of the bound runner.  run_e2_c_product_path.py (7ba30235...) and run_v83_f3_clipboard.py are not edited; each replacement
must match exactly once, the wrapper's own rule.

1. Single press (finding 178).  `format_arm` presses the format button twice, 3-10 ms apart.  v28 answered too slowly for the cache
   to move between them; v29 answers in 3 ms and the second press takes the first one back.  The first press goes.  A user presses
   once.  From findings/evidence/v29-177/f3-83/diag_single_press.py.
2. The clear wait (finding 178's other race).  The two waits on the 清除格式 label are met by the first of the clear's four steps, so
   the runner can press into the page's own loop.  They wait for the toast 「已清除…」, written once after the fourth.  From
   findings/evidence/v29-177/f3-83/diag_clear_wait.py.

  python3 tools/run_k_0245_path.py --browser chrome --out <new dir>
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_v83_f3_clipboard as r  # noqa: E402

TAIL = '                "return b ? !b.disabled : null; })()")\n'
PRESS = '            evaluate(session, PRESS.replace("ARG_ACTION", action))\n'
NEXT = '            # WAIT ON THE COMPLETION SIGNAL, AND RECORD THE STATE CACHE.\n'
LABEL = 'lambda st: "清除格式" in (st.get("latency") or ""), 30)'
DONE = 'lambda st: "已清除" in (evaluate(session, READ_TOAST) or ""), 30)'
r.REPLACEMENTS = r.REPLACEMENTS + (
    ('k-0245-single-press', TAIL + PRESS + NEXT, TAIL + NEXT),
    ('k-0245-clear-wait-normalise',
     '                evaluate(session, CLEAR_FORMAT)\n                wait_for(session,\n                         ' + LABEL,
     '                evaluate(session, CLEAR_TOAST)\n                evaluate(session, CLEAR_FORMAT)\n                wait_for(session,\n                         ' + DONE),
    ('k-0245-clear-wait-accumulate',
     '        evaluate(session, CLEAR_FORMAT)\n        wait_for(session,\n                 ' + LABEL,
     '        evaluate(session, CLEAR_TOAST)\n        evaluate(session, CLEAR_FORMAT)\n        wait_for(session,\n                 ' + DONE),
)

if __name__ == '__main__':
    raise SystemExit(r.main())
