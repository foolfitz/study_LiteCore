#!/usr/bin/env python3
"""Re-read a calc_host_arm.py run (default run-02) with one registered limit of the host route.

check_calc_headers.p_h5 has four clauses per key: the whole column/row is selected, no edit began, B2 is unchanged, and no typed
entry is pending.  The last one reads window.__calcEditor.inputState, which the page exposes only with ?diagnostics=1; the host
route never passes it, so the tool records 'no-diagnostics' and the check is red whatever the keys did.  Here a P-H5 check counts
as held iff its first three clauses hold, recomputed from its recorded `actual`, and its pending reading is exactly
'no-diagnostics' (any other value, including a real pending entry, stays red).  Every other check is read as the tool wrote it.

  read_run.py [RUN_DIR]          prints the reading; exit 0 iff H_CALC_HOLDS_PENDING_UNOBSERVED
"""
import json
from pathlib import Path
import sys

run = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'run-02'
report = json.loads((run / 'report.json').read_text())
WANT = {'P-H5/ctrl-space': ('columns', 'column', 'endColumn'), 'P-H5/ctrl-shift-space': ('columns', 'column', 'endColumn'),
        'P-H5/shift-space': ('rows', 'row', 'endRow')}


def held(check):
    if check['pass'] or check['id'] not in WANT:
        return check['pass']
    kind, low, high = WANT[check['id']]
    a = check['actual']
    s = a['selection']
    return (s['whole'] == kind and s[low] == 1 and s[high] == 1 and a['editing'] is None and a['b2'][0] == a['b2'][1]
            and a['pending'] == 'no-diagnostics')


rows = []
for r in report['runs']:
    red = [c['id'] for c in r['checks'] if not held(c)]
    rows.append({'browser': r['browser'], 'arm': r['arm'], 'error': r['error'], 'checks': len(r['checks']),
                 'heldAsWritten': sum(c['pass'] for c in r['checks']), 'heldWithLimit': len(r['checks']) - len(red), 'red': red})
ok = (len(rows) == 4 and not report.get('error') and not report['cleanup'].get('errors')
      and all(not x['error'] and x['checks'] and not x['red'] for x in rows))
print(json.dumps({'run': run.name, 'verdict': 'H_CALC_HOLDS_PENDING_UNOBSERVED' if ok else 'H_CALC_RED', 'runs': rows,
                  'cleanup': report['cleanup']}, indent=1))
sys.exit(0 if ok else 1)
