#!/usr/bin/env python3
"""T1's three rounds under the owner's gate (SPEC-M3-v29-tick-pacing append 8), read by judge_p2.py as repinned, and the red case: the
same reports with the constant back at 10 in process must give the two FAILs T1 recorded.  Read-only."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EV = HERE.parents[1]
sys.dont_write_bytecode = True


def run(directory, gate=None):
    spec = importlib.util.spec_from_file_location('judge', EV / 'typing-latency/judge_p2.py')
    judge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(judge)
    if gate is not None:
        judge.BOUNDARIES_COMMIT_MEDIAN = gate
    sys.argv = ['judge_p2.py', '--dir', str(directory)]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = judge.main()
    lines = out.getvalue().splitlines()
    return {'exit': code, 'last': lines[-1], 'failLines': [' '.join(l.split()) for l in lines if l.startswith('  FAIL')], 'gate': judge.BOUNDARIES_COMMIT_MEDIAN}


rows = {f'r{r}': {'gate16': run(EV / f'v29-177/t1/r{r}/ratio-1'), 'gate10': run(EV / f'v29-177/t1/r{r}/ratio-1', 10.0)} for r in (1, 2, 3)}
holds = (all(v['gate16']['exit'] == 0 and v['gate16']['gate'] == 16.0 for v in rows.values())
         and [v['gate10']['exit'] for v in rows.values()] == [0, 1, 1] and all(len(rows[r]['gate10']['failLines']) == 1 for r in ('r2', 'r3')))
report = {'verdict': 'T1_HOLDS_UNDER_GATE_16' if holds else 'T1_DIFFERS', 'rows': rows}
(HERE / 'reading.json').write_text(json.dumps(report, indent=1) + '\n')
print(report['verdict'], {r: (v['gate16']['exit'], v['gate10']['exit'], v['gate10']['failLines']) for r, v in rows.items()})
raise SystemExit(0 if holds else 1)
