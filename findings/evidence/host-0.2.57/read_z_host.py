#!/usr/bin/env python3
"""The new arm on the host for 0.2.57 (CLAUDE.md, cadence item 5): the owner's hand-test item 1, automated.

zoom_host2.py (../zoom-comment-loop/fit-narrow-on-fix/, the subagent's host repro, unchanged) opens l1 -- the document with a
comment -- from Files in the installed host, at fit and then zoom-in step by step to the top level, then reset, and records the
canvas after each step.  This reads its <browser>-report.json:

  Z_HOST_HOLDS  no fatal, the folder deleted (204), l1 recorded once, at least fit + one zoom-in + reset recorded, and every
                step's canvas has painted bands (canvas.dataset.bands not empty) and ink (pixels darker than 300 of 765) of at
                least a quarter of the fit step's.  On 0.2.56 a white step had no bands and ink 0 -- or 110, at 125 percent in
                Chrome (z-host-red-on-0256/), which is why "ink > 0" alone is not the rule
  Z_HOST_RED    otherwise; the steps without ink are named

  read_z_host.py REPORT.json [REPORT.json ...]      exit 0 iff every report holds
"""
import json
from pathlib import Path
import sys


def read(path):
    report = json.loads(Path(path).read_text())
    problems = []
    if report.get('fatal'):
        problems.append('fatal: ' + report['fatal'][-200:])
    if report.get('folderDelete') != 204:
        problems.append(f"folder delete {report.get('folderDelete')}")
    docs = {n: r for n, r in report.get('docs', {}).items() if n.startswith('l1-')}
    if len(docs) != 1:
        problems.append(f'l1 not recorded once: {sorted(report.get("docs", {}))}')
    steps = []
    for name, rec in docs.items():
        steps = [(st['step'], (st['state'].get('canvas') or {}).get('ink'), st['state'].get('label'),
                  (st['state'].get('canvas') or {}).get('bands')) for st in rec['steps']]
        kinds = [s for s, _, _, _ in steps]
        if 'fit' not in kinds or 'reset' not in kinds or not any(k.startswith('in') for k in kinds):
            problems.append(f'steps incomplete: {kinds}')
        fit = next((ink for s, ink, _, _ in steps if s == 'fit'), None)
        floor = fit / 4 if isinstance(fit, int) and fit > 0 else None
        if floor is None:
            problems.append(f'no ink at fit: {fit}')
        blank = [f'{s} ({label}: ink {ink}, bands {bands!r})' for s, ink, label, bands in steps
                 if not bands or not isinstance(ink, int) or floor is None or ink < floor]
        if blank:
            problems.append('blank at ' + '; '.join(blank))
    return {'report': str(path), 'browser': report.get('browser'), 'steps': steps, 'problems': problems,
            'verdict': 'Z_HOST_HOLDS' if not problems else 'Z_HOST_RED'}


if __name__ == '__main__':
    results = [read(p) for p in sys.argv[1:]]
    print(json.dumps(results, indent=1, ensure_ascii=False))
    raise SystemExit(0 if results and all(r['verdict'] == 'Z_HOST_HOLDS' for r in results) else 1)
