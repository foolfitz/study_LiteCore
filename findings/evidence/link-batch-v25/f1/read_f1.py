#!/usr/bin/env python3
"""F1's verdict (SPEC-M3-link-batch-v25 6.3), read from a diag_format_v25.py report.json only.

Clauses, per run (B = bullet scenario, F = format scenario):
  B-pill      the page is `ready` after the bullet press (v22's answer; v24 went recoverable-error, finding 171)
  B-page      the worker's projection says dispatched:true for set-list-unordered
  B-raw       the ENGINE's error record for that request has `formatBarrier.dispatched` present and true and a
              stage other than idle (spec v25 4.1 item 171-3; 13 item 4: the serialisation, measured here)
  F-cleared   the saved ODT's MKAFTERCLEAR is not italic (clear-format cleared it)
  F-again     the saved ODT's MKITALAGAIN is italic (pressing italic again turned it on)
  F-no-fail   no set-* reply failed
  F-raw       every set-* engine completion carries `witness` from {uno-success, on-time-item, state-noop}

F1_HOLDS when all of:
  - v24 and v25 identities ok; every planned run present (3 products x 2 scenarios x repetitions) and none fatal;
  - v25: every clause true in every run;
  - v24 (the natural counterexample, finding 171/172 unfixed): B-pill, B-raw, F-cleared, F-again false in every
    run -- so each of those clauses is seen to be red on real data, not only on a mutation;
  - v22 (the reference "= v22"): B-pill, F-cleared, F-again true in every run.
v22's B-raw is reported, not required: the v22 engine does not send `dispatched` (its worker infers it).

--self-test mutates the given report in memory; every mutation must turn the verdict red.
"""
import argparse
import copy
import json
from pathlib import Path
import sys

WITNESSES = {'uno-success', 'on-time-item', 'state-noop'}
CLAUSES = ('B-pill', 'B-page', 'B-raw', 'F-cleared', 'F-again', 'F-no-fail', 'F-raw')


def bullet(run):
    rows = [t for t in run.get('traffic', []) if t.get('action') == 'set-list-unordered']
    row = rows[-1] if rows else {}
    raw = [x for x in (run.get('raw') or []) if x.get('requestId') == row.get('requestId') and x.get('type') == 'error']
    barrier = (raw[-1] if raw else {}).get('barrier') or {}
    return {'B-pill': (run.get('after') or {}).get('pill') == 'ready',
            'B-page': (row.get('barrier') or {}).get('dispatched') is True,
            'B-raw': barrier.get('hasDispatched') is True and barrier.get('dispatched') is True
            and barrier.get('stage') not in (None, 'idle')}


def fmt(run):
    markers = (run.get('saved') or {}).get('markers') or {}
    rows = [t for t in run.get('traffic', []) if str(t.get('action')).startswith('set-')]
    ids = {t.get('requestId') for t in rows}
    raw = [x for x in (run.get('raw') or []) if x.get('requestId') in ids]
    return {'F-cleared': (markers.get('MKAFTERCLEAR') or {}).get('found') is True
            and markers['MKAFTERCLEAR'].get('italic') is False,
            'F-again': (markers.get('MKITALAGAIN') or {}).get('italic') is True,
            'F-no-fail': bool(rows) and all(t.get('ok') is True for t in rows),
            'F-raw': bool(raw) and len(raw) == len(rows) and all(
                x.get('type') == 'editor-action-completed' and x.get('hasWitness') is True
                and x.get('witness') in WITNESSES for x in raw)}


def read(report):
    reps = max([r.get('repetition', 0) for r in report.get('runs', [])] or [0])
    table, problems = {}, []
    for name in ('v24', 'v25'):
        if not (report.get('products', {}).get(name) or {}).get('ok'):
            problems.append(f'{name}: identity not ok')
    if reps < 1:
        problems.append('no runs')
    for name in ('v22', 'v24', 'v25'):
        for scenario in ('bullet', 'format'):
            got = [r for r in report.get('runs', []) if r.get('product') == name and r.get('scenario') == scenario]
            if len(got) != reps:
                problems.append(f'{name} {scenario}: {len(got)} runs, expected {reps}')
            for run in got:
                if run.get('fatal'):
                    problems.append(f"{name} {scenario} {run.get('repetition')}: fatal")
                    continue
                values = bullet(run) if scenario == 'bullet' else fmt(run)
                for clause, value in values.items():
                    table.setdefault(name, {}).setdefault(clause, []).append(value)
    expect = {'v25': {c: True for c in CLAUSES},
              'v24': {'B-pill': False, 'B-raw': False, 'F-cleared': False, 'F-again': False},
              'v22': {'B-pill': True, 'F-cleared': True, 'F-again': True}}
    for name, clauses in expect.items():
        for clause, want in clauses.items():
            seen = table.get(name, {}).get(clause, [])
            if not seen or any(v is not want for v in seen):
                problems.append(f'{name} {clause}: {seen}, expected all {want}')
    return {'verdict': 'F1_HOLDS' if not problems else 'F1_RED', 'repetitions': reps,
            'table': table, 'problems': problems}


def mutations(report):
    def first(r, product, scenario):
        return next(x for x in r['runs'] if x['product'] == product and x['scenario'] == scenario)

    def m_raw_dispatched(r):
        for x in first(r, 'v25', 'bullet')['raw']:
            if x.get('barrier'):
                x['barrier']['hasDispatched'] = False
                x['barrier'].pop('dispatched', None)

    def m_raw_witness(r):
        first(r, 'v25', 'format')['raw'][0]['hasWitness'] = False

    def m_italic(r):
        first(r, 'v25', 'format')['saved']['markers']['MKAFTERCLEAR']['italic'] = True

    def m_pill(r):
        first(r, 'v25', 'bullet')['after']['pill'] = 'recoverable-error'

    def m_v24_fixed(r):  # a counterexample that is no longer red means the reader cannot tell
        first(r, 'v24', 'format')['saved']['markers']['MKAFTERCLEAR']['italic'] = False

    def m_identity(r):
        r['products']['v25']['ok'] = False

    def m_drop_run(r):
        r['runs'].remove(first(r, 'v25', 'format'))

    def m_empty(r):
        r['runs'] = []

    return [m_raw_dispatched, m_raw_witness, m_italic, m_pill, m_v24_fixed, m_identity, m_drop_run, m_empty]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('report', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding='utf-8'))
    result = read(report)
    if args.self_test:
        outcomes = {}
        for mutate in mutations(report):
            mutated = copy.deepcopy(report)
            mutate(mutated)
            outcomes[mutate.__name__] = read(mutated)['verdict']
        result = {'base': result['verdict'], 'mutations': outcomes,
                  'selfTest': 'PASS' if result['verdict'] == 'F1_HOLDS'
                  and all(v == 'F1_RED' for v in outcomes.values()) else 'FAIL'}
        print(json.dumps(result, indent=1))
        return 0 if result['selfTest'] == 'PASS' else 1
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0 if result['verdict'] == 'F1_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
