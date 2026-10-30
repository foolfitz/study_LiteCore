#!/usr/bin/env python3
"""PL-1's verdict (SPEC-M3-v27-finding-176 7.2), from run_v27_pl1.py's report.json only.

For every run, the ONE engine record of the bullet (`formatBarrier.command == ".uno:DefaultBullet"`) is put through
v27's collapsed-route rule, in the order `finishOrderedFormatReadback` applies it under OXSDK_E2_V27_FIRST_BLOCK
(wasm_sdk_probe/src/ordered_format.inc; the predicate is probe_engine.cpp `formatBarrierReadbackSatisfied`):

  selection type readable, readback parsed, footnoteApparatus / unknownTag / malformedNesting false  (judged first,
  unchanged by v27) -> route collapsed, so `multiBlock` no longer refuses -> the a11y paragraph-identity gate does not
  run (it runs only when dispatchKnown, readbackKnown, dispatchUsable and readbackUsable are all true; it compares
  fingerprints the record does not carry, so a record where it WOULD run is not predictable and is red here)
  -> restoreConfirmed -> the predicate: expectedListTag non-empty => (listTag or "none") == expectedListTag;
  expectedBlockTag non-empty => blockTag == expectedBlockTag.   All true = "would verify".

The record must also BE finding 046's cell on v26 (`error`, failureShape multi-block-readback, dispatched true) and
the recipe's cell (the readback's first block is the empty dispatch paragraph, the second the recipe's next
paragraph).  The clause table CLAUSES is the population: each id has a predicate and a mutation of a holding run
that must make it false; `--self-test REPORT` applies every mutation (plus run-level ones) and needs each to turn
the verdict red; a clause without a mutation cannot be written (the table holds both).

Verdict PL1_WOULD_VERIFY iff every identity is ok and every planned run (browsers x recipes x repetitions) is present,
not fatal, and holds every clause.  Otherwise PL1_RED with the problems.

  read_v27_pl1.py REPORT              (prints the reading; exit 0 iff PL1_WOULD_VERIFY)
  read_v27_pl1.py --self-test REPORT  (exit 0 iff every mutation turns it red)
"""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

BULLET = '.uno:DefaultBullet'
NEXT_PARAGRAPH = {'s3': 'E1-EMPTY-AFTER', 'list-contexts': 'E1-LC-END'}
IDENTITY_INPUTS = ('dispatchKnown', 'readbackKnown', 'dispatchUsable', 'readbackUsable')


def bullet_records(run):
    return [r for r in run.get('raw') or [] if (r.get('barrier') or {}).get('command') == BULLET]


def record(run):
    found = bullet_records(run)
    return found[0] if len(found) == 1 else None


def barrier(run):
    return (record(run) or {}).get('barrier') or {}


def readback(run):
    return barrier(run).get('readback') or {}


def blocks(html):
    body = (html or '')[(html or '').find('<body'):]
    return [re.sub(r'<[^>]+>', '', inner).strip() for _, inner in re.findall(r'<(p|h[1-6])\b[^>]*>(.*?)</\1>', body, re.S)]


def transport_ok(run):
    t = run.get('transport') or {}
    if t.get('transport') == 'cdp-auto-attach':
        return any(w.get('install') == 'installed' for w in t.get('workers') or [])
    return t.get('transport') == 'broadcast-channel' and t.get('channel') == 'open'


def predicate(rb):
    want_list, want_block = rb.get('expectedListTag'), rb.get('expectedBlockTag')
    if not isinstance(want_list, str) or not isinstance(want_block, str):
        return False
    if want_list and (rb.get('listTag') or 'none') != want_list:
        return False
    return not (want_block and rb.get('blockTag') != want_block)


def _set(get, key, value):
    def mutate(run):
        get(run)[key] = value
    return mutate


def _identity_all_true(run):
    for k in IDENTITY_INPUTS:
        barrier(run)['paragraphIdentity'][k] = True


def _second_block(run):
    rb = readback(run)
    rb['html'] = rb['html'].replace(NEXT_PARAGRAPH[run['recipe']], 'Plain first')


def _duplicate(run):
    run['raw'].append(copy.deepcopy(record(run)))


def _drop_transport(run):
    t = run['transport']
    if t['transport'] == 'cdp-auto-attach':
        for w in t['workers']:
            w['install'] = 'TypeError: no JSON'
    else:
        t['channel'] = None


# (id, predicate over one run, mutation of a run that holds it)
CLAUSES = [
    ('transport-installed', transport_ok, _drop_transport),
    ('one-bullet-record', lambda r: record(r) is not None, _duplicate),
    ('is-046-cell', lambda r: (record(r) or {}).get('type') == 'error' and barrier(r).get('failureShape') == 'multi-block-readback',
     _set(barrier, 'failureShape', 'postcondition-not-met')),
    ('dispatched', lambda r: barrier(r).get('dispatched') is True, _set(barrier, 'dispatched', False)),
    ('selection-type-readable', lambda r: barrier(r).get('selectionTypeReadable') is True,
     _set(barrier, 'selectionTypeReadable', False)),
    ('parsed', lambda r: readback(r).get('parsed') is True, _set(readback, 'parsed', False)),
    ('no-footnote-apparatus', lambda r: readback(r).get('footnoteApparatus') is False, _set(readback, 'footnoteApparatus', True)),
    ('no-unknown-tag', lambda r: readback(r).get('unknownTag') is False, _set(readback, 'unknownTag', True)),
    ('no-malformed-nesting', lambda r: readback(r).get('malformedNesting') is False, _set(readback, 'malformedNesting', True)),
    ('multi-block', lambda r: readback(r).get('multiBlock') is True, _set(readback, 'multiBlock', False)),
    ('route-collapsed', lambda r: barrier(r).get('route') == 'collapsed', _set(barrier, 'route', 'range-single')),
    ('identity-gate-does-not-run', lambda r: all(isinstance((barrier(r).get('paragraphIdentity') or {}).get(k), bool)
                                                 for k in IDENTITY_INPUTS)
     and not all(barrier(r)['paragraphIdentity'][k] for k in IDENTITY_INPUTS), _identity_all_true),
    ('restore-confirmed', lambda r: readback(r).get('restoreConfirmed') is True, _set(readback, 'restoreConfirmed', False)),
    ('action-is-the-bullet', lambda r: readback(r).get('expectedListTag') == 'ul', _set(readback, 'expectedListTag', 'ol')),
    ('predicate-satisfied', lambda r: predicate(readback(r)), _set(readback, 'listTag', '')),
    ('recipe-cell', lambda r: blocks(readback(r).get('html'))[:2] == ['', NEXT_PARAGRAPH.get(r.get('recipe'))],
     _second_block),
]
V27_RULE = ('selection-type-readable', 'parsed', 'no-footnote-apparatus', 'no-unknown-tag', 'no-malformed-nesting',
            'route-collapsed', 'identity-gate-does-not-run', 'restore-confirmed', 'predicate-satisfied')


def judge(run):
    if run.get('fatal'):
        return {'fatal': run['fatal'].strip().splitlines()[-1]}
    results = {}
    for cid, holds, _ in CLAUSES:
        try:
            results[cid] = bool(holds(run))
        except Exception as error:  # noqa: BLE001 -- a clause that cannot be read does not hold
            results[cid] = False
            results[cid + ':error'] = f'{type(error).__name__}: {error}'
    rb = readback(run)
    return {'clauses': results, 'wouldVerify': all(results[c] for c in V27_RULE),
            'record': {k: rb.get(k) for k in ('blockCount', 'itemCount', 'listTag', 'blockTag', 'expectedListTag',
                                               'expectedBlockTag', 'restoreConfirmed')} | {
                'route': barrier(run).get('route'), 'failureShape': barrier(run).get('failureShape'),
                'blocks': blocks(rb.get('html'))[:3]},
            'page': {k: ((run.get('press') or run.get('after') or {}).get(k)) for k in ('pill', 'latency', 'toast')}}


def verdict(report):
    config = report['config']
    problems = []
    for browser in config['browsers']:
        if not (report['products'].get(browser) or {}).get('ok'):
            problems.append(f'{browser}: identity not ok')
    rows = []
    for browser in config['browsers']:
        for recipe in config['recipes']:
            runs = [r for r in report['runs'] if r['browser'] == browser and r['recipe'] == recipe]
            if len(runs) != config['repetitions']:
                problems.append(f'{browser} {recipe}: {len(runs)}/{config["repetitions"]} runs')
            for run in runs:
                reading = judge(run)
                rows.append({'browser': browser, 'recipe': recipe, 'repetition': run.get('repetition'), **reading})
                if 'fatal' in reading:
                    problems.append(f'{browser} {recipe} {run.get("repetition")}: fatal {reading["fatal"]}')
                    continue
                failed = [c for c, ok in reading['clauses'].items() if ok is False]
                if failed:
                    problems.append(f'{browser} {recipe} {run.get("repetition")}: {failed}')
    if not report['runs']:
        problems.append('no runs')
    planned = len(config['browsers']) * len(config['recipes']) * config['repetitions']
    would = sum(1 for r in rows if r.get('wouldVerify'))
    return {'verdict': 'PL1_WOULD_VERIFY' if not problems else 'PL1_RED', 'wouldVerify': f'{would}/{planned}',
            'problems': problems, 'rows': rows}


def self_test(report):
    base = verdict(copy.deepcopy(report))
    if base['verdict'] != 'PL1_WOULD_VERIFY':
        return {'selfTest': 'NEEDS_A_HOLDING_REPORT', 'base': base['verdict']}, 2
    results = {}
    for browser in report['config']['browsers']:
        for recipe in report['config']['recipes']:
            index = next(i for i, r in enumerate(report['runs']) if r['browser'] == browser and r['recipe'] == recipe)
            for cid, _, mutate in CLAUSES:
                mutated = copy.deepcopy(report)
                mutate(mutated['runs'][index])
                got = verdict(mutated)
                results[f'{browser}/{recipe}/{cid}'] = got['verdict']
    run_level = {
        'one-run-dropped': lambda r: r['runs'].pop(0),
        'identity-not-ok': lambda r: r['products'][r['config']['browsers'][-1]].update(ok=False),
        'one-run-fatal': lambda r: r['runs'][-1].update(fatal='Traceback\nRuntimeError: x'),
        'no-runs': lambda r: r.update(runs=[]),
    }
    for name, mutate in run_level.items():
        mutated = copy.deepcopy(report)
        mutate(mutated)
        results[name] = verdict(mutated)['verdict']
    red = all(v == 'PL1_RED' for v in results.values())
    return {'selfTest': 'ALL_RED' if red else 'SOME_MUTATION_HELD', 'base': base['verdict'],
            'mutations': len(results), 'held': sorted(k for k, v in results.items() if v != 'PL1_RED'),
            'results': results}, (0 if red else 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('report', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding='utf-8'))
    if args.self_test:
        out, code = self_test(report)
    else:
        out = verdict(report)
        code = 0 if out['verdict'] == 'PL1_WOULD_VERIFY' else 1
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
