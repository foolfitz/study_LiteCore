#!/usr/bin/env python3
"""Judge ruling 3 Q6.3's native cells against PREDICTION.md amendment 2 (the stop rule), from the records only.

Usage:
  python3 -I read_q63.py OUT_Q63 OUT_FIRST            verdict per action + the per-cell table (JSON on stdout)
  python3 -I read_q63.py --self-test OUT_Q63 OUT_FIRST

Per-round extraction is read_cells.py's (imported, not edited): clean or not, the saved dispatch paragraph, and the
recorded first-block state.  Then, per action, every G cell that bears on it must have 5 clean rounds whose first
block agrees with the saved paragraph.  Bullet's G cells include the first run's g-a2, g-a3 and g-n1..n3 (OUT_FIRST).
b0 (the fixture control) must save the empty paragraph as a heading, or heading/body is NOT-ESTABLISHED.
"""
import argparse
import copy
import importlib.util
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('read_cells', HERE / 'read_cells.py')
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

ACTIONS = {
    'bullet': [('q63', 'a6g-empty-empty'), ('q63', 'n6g-sham-empty-empty'), ('first', 'g-a2-empty-mid'),
               ('first', 'g-a3-enter-mid'), ('first', 'g-n1-sham-empty-mid'),
               ('first', 'g-n2-sham-empty-before-list'), ('first', 'g-n3-sham-empty-after-list')],
    'number': [('q63', 'g-r3-number-empty-mid')],
    'none': [('q63', 'g-r4-none-empty-bulleted')],
    'heading': [('q63', 'g-r5-heading-empty-mid')],
    'body': [('q63', 'b1g-body-on-empty-heading')],
}
CONTROL = 'b0-heading-control'


def locate(out, name, r):
    path = out / name / f'r{r}.jsonl'
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        if rec.get('rec') == 'locate':
            return {k: rec.get(k) for k in ('selBefore', 'suffix', 'prefix')}
    return None


def judge(sets):
    verdicts, problems = {}, []
    control = sets['q63'][CONTROL]
    control_ok = (sum(s['clean'] for s in control) == rc.ROUNDS
                  and all(s['saved'].get('heading') for s in control if s['clean']))
    if not control_ok:
        problems.append('b0: the fixture does not load as a heading in 5 clean rounds')
    for action, members in ACTIONS.items():
        verdict = 'IN-SCOPE'
        if action in ('heading', 'body') and not control_ok:
            verdict = 'NOT-ESTABLISHED'
        for where, name in members:
            rounds = sets[where][name]
            clean = [s for s in rounds if s['clean']]
            if len(clean) < rc.ROUNDS:
                problems.append(f'{action}: {name} {len(clean)}/{rc.ROUNDS} clean')
                verdict = 'NOT-ESTABLISHED' if verdict != 'OUT-OF-SCOPE' else verdict
                continue
            bad = [s['round'] for s in clean if not rc.first_block_agrees(s)]
            if bad:
                problems.append(f'{action}: {name} first block disagrees in rounds {bad}')
                verdict = 'OUT-OF-SCOPE'
        verdicts[action] = verdict
    return verdicts, problems


def table(sets, out_q63):
    rows = []
    for name, rounds in sets['q63'].items():
        rows.append({'cell': name, 'clean': sum(s['clean'] for s in rounds),
                     'why': sorted({w for s in rounds for w in s['why']}),
                     'saved': sorted({json.dumps(s['saved'], ensure_ascii=False) for s in rounds if s['clean']}),
                     'selectedType': sorted({s.get('selectedType') for s in rounds if s['clean']}, key=str),
                     'blocks': sorted({s.get('blocks') for s in rounds if s['clean']}, key=str),
                     'firstBlock': sorted({f"{s.get('parserListTag')}/{s.get('parserBlockTag')}"
                                           for s in rounds if s['clean']}),
                     'firstBlockAgrees': sorted({rc.first_block_agrees(s) for s in rounds
                                                 if s['clean'] and s.get('parserBlockTag')}),
                     'selectedText': sorted({s.get('selectedText') for s in rounds if s['clean']}, key=str),
                     'undo': sorted({json.dumps([s.get('undoBefore'), s.get('undoAfter')], ensure_ascii=False)
                                     for s in rounds if s['clean']}),
                     'caretAfter': sorted({json.dumps(locate(out_q63, name, s['round']), ensure_ascii=False)
                                           for s in rounds})})
    return rows


def load_both(out_q63, out_first):
    _, q63 = rc.load(out_q63)
    _, first = rc.load(out_first)
    return {'q63': q63, 'first': first}


def self_test(out_q63, out_first):
    base = load_both(out_q63, out_first)
    got, _ = judge(base)
    results, ok = {'as-recorded': got}, True
    cases = {
        'g-r5-disagrees': (lambda s: s['q63']['g-r5-heading-empty-mid'][2].update(parserBlockTag='p'),
                           'heading', 'OUT-OF-SCOPE'),
        'b1g-disagrees': (lambda s: s['q63']['b1g-body-on-empty-heading'][0].update(parserBlockTag='h1'),
                          'body', 'OUT-OF-SCOPE'),
        'first-run-g-n2-disagrees': (lambda s: s['first']['g-n2-sham-empty-before-list'][4].update(parserListTag='ul'),
                                     'bullet', 'OUT-OF-SCOPE'),
        'a6g-one-unclean': (lambda s: s['q63']['a6g-empty-empty'][1].update(clean=False), 'bullet', 'NOT-ESTABLISHED'),
        'control-not-heading': (lambda s: s['q63'][CONTROL][3]['saved'].update(heading=False), 'body',
                                'NOT-ESTABLISHED'),
        'g-r4-saved-in-list': (lambda s: s['q63']['g-r4-none-empty-bulleted'][0]['saved'].update(
            inList=True, listKind='bullet'), 'none', 'OUT-OF-SCOPE'),
    }
    for name, (mutate, action, expected) in cases.items():
        mutated = copy.deepcopy(base)
        mutate(mutated)
        verdicts, _ = judge(mutated)
        results[name] = {'action': action, 'verdict': verdicts[action], 'expected': expected,
                         'ok': verdicts[action] == expected}
        ok = ok and verdicts[action] == expected
    print(json.dumps({'selfTest': 'ALL_AS_EXPECTED' if ok else 'SOME_CASE_WRONG', 'cases': results}, indent=1))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out_q63', type=pathlib.Path)
    ap.add_argument('out_first', type=pathlib.Path)
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test(a.out_q63, a.out_first)
    sets = load_both(a.out_q63, a.out_first)
    verdicts, problems = judge(sets)
    print(json.dumps({'verdicts': verdicts, 'problems': problems, 'cells': table(sets, a.out_q63)},
                     indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
