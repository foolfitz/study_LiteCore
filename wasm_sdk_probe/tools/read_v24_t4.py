#!/usr/bin/env python3
"""SPEC-M3-link-batch-v24 6.3 T4: read tools/run_v24_t4.py's output against the v23 baseline.

Rules (findings/evidence/link-batch-v24/pre-count/t4/README.md, fixed before the run):
  1  every insertText request in Chrome's wire record carries a route, has exactly one reply, the
     reply is ok and its method equals the route; both routes occur (else NE)
  2  every check whose step interval holds a paste-route insertText or a replaceSelection /
     pasteMarkdown request (set generated from the wire) is PASS on v24 and has its v23 outcome,
     per browser (Firefox uses Chrome's set); an empty set is NE

  python3 -I tools/read_v24_t4.py --chrome <dir> [--firefox <dir>] [--out <file>]
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE = ROOT / 'findings/evidence/link-batch-v23/feature-protocol/product-four-arms-counted-01'
STEP = re.compile(r'^\[step\]\s+[0-9.]+s (\S+)\s+(\S+)')


def outcomes(report):
    out = defaultdict(list)
    for entry in report['checks']:
        out[entry['id']].append(entry['outcome'])
    return out


def steps(directory, report):
    """The step lines that record a check, in order, bound to the report's check list."""
    lines = json.loads((directory / 'steps.json').read_text())['lines']
    ids = [c['id'] for c in report['checks']]
    found = []
    for item in lines:
        match = STEP.match(item['line'])
        if match and match[1] != 'STARTED' and len(found) < len(ids) and match[2] == ids[len(found)]:
            found.append({'at': item['at'], 'outcome': match[1], 'id': match[2]})
    if [s['id'] for s in found] != ids:
        raise SystemExit(f'{directory}: step lines do not bind to the report checks ({len(found)} of {len(ids)})')
    return found


def attribute(records, bounds):
    """Each request to the first check recorded at or after it."""
    for record in records:
        owner = next((b['id'] + '#' + str(i) for i, b in enumerate(bounds) if b['at'] >= record['at'] / 1000.0), None)
        record['check'] = owner or '<after-the-last-check>'
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--chrome', type=Path, required=True)
    parser.add_argument('--firefox', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = {'schema': 1, 'baseline': str(BASELINE.relative_to(ROOT)), 'browsers': {}}

    chrome = json.loads((args.chrome / 'report.json').read_text())
    bounds = steps(args.chrome, chrome)
    wire = json.loads((args.chrome / 'wire.json').read_text())
    records = attribute(wire['records'], bounds)
    requests = [r for r in records if r['kind'] == 'request']
    replies = defaultdict(list)
    for r in records:
        if r['kind'] == 'response':
            replies[(r['worker'], r['requestId'])].append(r)
    inserts = [r for r in requests if r['operation'] == 'insertText']
    problems = []
    for r in inserts:
        got = replies[(r['worker'], r['requestId'])]
        reply = got[0] if len(got) == 1 else None
        if r['route'] == '<absent>':
            problems.append({'check': r['check'], 'problem': 'request without route', 'request': r})
        elif reply is None:
            problems.append({'check': r['check'], 'problem': f'{len(got)} replies', 'request': r})
        elif reply['ok'] is not True or reply['method'] != r['route']:
            problems.append({'check': r['check'], 'problem': f"route {r['route']!r} vs reply ok={reply['ok']} method={reply['method']!r} code={reply['code']!r}", 'request': r})
    routes = sorted({r['route'] for r in inserts})
    rule1 = 'NOT_ESTABLISHED' if not {'uno-insert-text', 'paste'} <= set(routes) else 'FAIL' if problems else 'PASS'
    by_check = defaultdict(lambda: defaultdict(int))
    for r in requests:
        key = r['operation'] + (':' + str(r['route']) if r['operation'] == 'insertText' else '')
        by_check[r['check'].rsplit('#', 1)[0]][key] += 1
    paste_set = sorted(c for c, ops in by_check.items() if c != '<after-the-last-check>' and (
        ops.get('insertText:paste') or ops.get('replaceSelection') or ops.get('pasteMarkdown')))
    typed_set = sorted(c for c, ops in by_check.items() if ops.get('insertText:uno-insert-text'))
    result['rule1'] = {'verdict': rule1, 'insertTextRequests': len(inserts), 'routes': routes,
                       'byRoute': {k: sum(1 for r in inserts if r['route'] == k) for k in routes},
                       'problems': problems, 'unattributed': sum(r['check'] == '<after-the-last-check>' for r in requests),
                       'dumps': wire['dumps']}
    result['requestsByCheck'] = {c: dict(v) for c, v in sorted(by_check.items())}
    result['pasteRouteChecks'] = paste_set
    result['typedRouteChecks'] = typed_set

    rule2 = []
    for browser, directory in (('chrome', args.chrome), ('firefox', args.firefox)):
        if directory is None:
            continue
        report = chrome if browser == 'chrome' else json.loads((directory / 'report.json').read_text())
        if browser == 'firefox':
            steps(directory, report)
        now, before = outcomes(report), outcomes(json.loads((BASELINE / f'{browser}.json').read_text()))
        table = {cid: {'v23': before.get(cid), 'v24': now.get(cid)} for cid in sorted(set(now) | set(before))}
        changed = {cid: row for cid, row in table.items() if row['v23'] != row['v24']}
        rows = [{'browser': browser, 'check': cid, 'v23': before.get(cid), 'v24': now.get(cid),
                 'ok': bool(now.get(cid)) and all(o == 'PASS' for o in now[cid]) and now.get(cid) == before.get(cid)} for cid in paste_set]
        rule2 += rows
        totals = defaultdict(int)
        for entry in report['checks']:
            totals[entry['outcome']] += 1
        result['browsers'][browser] = {'totals': dict(totals), 'checks': len(report['checks']),
                                       'changedFromV23': changed, 'table': table}
    result['rule2'] = {'verdict': 'NOT_ESTABLISHED' if not paste_set else 'PASS' if all(r['ok'] for r in rule2) else 'FAIL',
                       'rows': rule2}
    result['verdict'] = 'FAIL' if 'FAIL' in (rule1, result['rule2']['verdict']) else \
        'PASS' if (rule1, result['rule2']['verdict']) == ('PASS', 'PASS') else 'NOT_ESTABLISHED'
    text = json.dumps(result, indent=1, ensure_ascii=False) + '\n'
    if args.out:
        args.out.write_text(text)
    print(json.dumps({'verdict': result['verdict'], 'rule1': {k: result['rule1'][k] for k in ('verdict', 'insertTextRequests', 'byRoute')},
                      'rule1Problems': len(problems), 'pasteRouteChecks': paste_set, 'rule2': result['rule2']['verdict'],
                      'changedFromV23': {b: list(v['changedFromV23']) for b, v in result['browsers'].items()}}, indent=1, ensure_ascii=False))
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
