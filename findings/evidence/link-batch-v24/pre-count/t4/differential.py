#!/usr/bin/env python3
"""T4 Correction 2: run 02 against run 01, every check, per browser (ruling 1 Addendum 1 §6).

Outcome lists per check id (repeated ids as ordered lists) must be equal; any difference is named.
The Enter check's expected Chrome FAIL / Firefox NE is checked separately.  Writes differential.json.
"""
from collections import defaultdict
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = {'run-01': HERE, 'run-02': HERE / 'run-02'}


def outcomes(path):
    out = defaultdict(list)
    for entry in json.loads(path.read_text())['checks']:
        out[entry['id']].append(entry['outcome'])
    return dict(out)


def main():
    result, ok = {}, True
    for browser in ('chrome', 'firefox'):
        a = outcomes(RUNS['run-01'] / browser / 'report.json')
        b = outcomes(RUNS['run-02'] / browser / 'report.json')
        differ = {cid: {'run-01': a.get(cid), 'run-02': b.get(cid)} for cid in sorted(set(a) | set(b)) if a.get(cid) != b.get(cid)}
        enter = b.get('the-enter-key-reaches-the-document')
        want = ['FAIL'] if browser == 'chrome' else ['NOT_ESTABLISHED']
        result[browser] = {'checks': len(b), 'differing': differ, 'enter': enter, 'enterAsExpected': enter == want}
        ok = ok and not differ and enter == want and len(a) == len(b)
    result['verdict'] = 'RUN_02_REPEATS_RUN_01' if ok else 'RUN_02_DIFFERS'
    (HERE / 'differential.json').write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
