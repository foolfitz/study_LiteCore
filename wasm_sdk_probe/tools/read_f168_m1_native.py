#!/usr/bin/env python3
"""Read type-route ruling M1 runs: .uno:InsertText against the keyboard, natively.

Structure (exit 1 on any problem): artifact hashes, one record per inventory arm and round,
every "before" save equal to the fixture, no settle cap, and the table2/key-x positive control
equal to native run-03's bound shift-Right@cell-end/type save.

Pass condition, from the ruling (verdict M1_PASS / M1_FAIL, both exit 0):
  * every uno-insert-text arm delivers a LOK_CALLBACK_UNO_COMMAND_RESULT naming .uno:InsertText
    in every round (its "success" value is recorded, not required);
  * every arm is stable across rounds;
  * for every shape and every text with a key route, the uno-insert-text save equals the key save;
  * the emoji arm equals the shape's uno-insert-text-x save with x replaced by U+1F600 (inserted
    intact, same place).
The doc-end " teh " pair is recorded (keyboard autocorrect versus none) and does not gate.

Usage: read_f168_m1_native.py RUN_DIR --output FRESH.json
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odt_paragraphs import paragraph_texts_from_xml
from read_f168_native_table_type_routes import ROOT, RUN03, RUN03_REFERENCE, changes, odt_paragraphs, sha

EMOJI = '\U0001F600'


def swap_inserted(before, after):
    """after with x replaced by EMOJI only inside the span that differs from before."""
    i = 0
    while i < min(len(before), len(after)) and before[i] == after[i]:
        i += 1
    j = 0
    while j < min(len(before), len(after)) - i and before[-1 - j] == after[-1 - j]:
        j += 1
    return after[:i] + after[i:len(after) - j].replace('x', EMOJI) + after[len(after) - j:]


def read_run(run, problems):
    def problem(text):
        problems.append(f'{run.name}: {text}')

    completion = json.loads((run / 'completion.json').read_text())
    for name, value in completion['artifacts'].items():
        if not (run / name).is_file():
            problem(f'artifact missing: {name}')
        elif sha(run / name) != value:
            problem(f'artifact hash differs: {name}')
    if completion.get('protectedInputsUnchanged') is not True:
        problem('protected inputs changed during the run')
    rounds = json.loads((run / 'command.json').read_text())['rounds']
    inventory = [json.loads(l) for l in (run / 'inventory.jsonl').read_text().splitlines() if l.strip()]
    fixture = paragraph_texts_from_xml((run / 'fixture.fodt').read_bytes())
    records = {}
    for line in (run / 'native.jsonl').read_text().splitlines():
        row = json.loads(line)
        if 'fatal' in row:
            problem(f'fatal row: {row}')
        elif 'id' in row and 'round' in row:
            if (row['id'], row['round']) in records:
                problem(f'duplicate record {row["id"]} {row["round"]}')
            records[(row['id'], row['round'])] = row
    if len(records) != len(inventory) * rounds:
        problem(f'{len(records)} records for {len(inventory)} arms x {rounds} rounds')
    reference = odt_paragraphs(RUN03 / 'saves' / RUN03_REFERENCE)
    arms = {}
    for arm in inventory:
        outcomes, results = [], []
        for r in range(1, rounds + 1):
            row = records.get((arm['id'], r))
            if row is None:
                problem(f'missing record {arm["id"]} round {r}')
                continue
            files = [run / 'saves' / row[f] for f in ('beforeFile', 'afterFile')]
            if not (row['savedBefore'] and row['savedAfter']) or not all(f.is_file() for f in files):
                problem(f'save missing {arm["id"]} round {r}')
                continue
            if any(v < 0 for v in [row['openedSettleMs'], row['setupSettleMs'], row['finalSettleMs'], *row['shiftSettleMs']]):
                problem(f'settle cap {arm["id"]} round {r}')
            if odt_paragraphs(files[0]) != fixture:
                problem(f'before save differs from fixture {arm["id"]} round {r}')
            after = odt_paragraphs(files[1])
            if arm['id'] == 'table2/key-x' and after != reference:
                problem(f'table2/key-x does not reproduce run-03 (round {r})')
            outcomes.append(json.dumps(changes(fixture, after), ensure_ascii=False, sort_keys=True))
            results.append([json.loads(u['payload']) for u in row['unoCommandResults']])
        arms[arm['id']] = {'route': arm['route'], 'text': arm['text'], 'rounds': len(outcomes),
                           'stable': len(set(outcomes)) == 1,
                           'changes': [json.loads(o) for o in sorted(set(outcomes))],
                           'unoCommandResults': results}
    return {'run': str(run.relative_to(ROOT)) if run.is_relative_to(ROOT) else str(run),
            'rounds': rounds, 'nativeExitCode': completion['exitCode'], 'arms': arms}


def verdict(run):
    arms, failures, comparisons = run['arms'], [], {}
    for arm_id, arm in arms.items():
        if not arm['stable']:
            failures.append(f'{arm_id}: not stable across rounds')
        if arm['route'] == 'uno-insert-text':
            delivered = [any(p.get('commandName') == '.uno:InsertText' for p in rs) for rs in arm['unoCommandResults']]
            if len(delivered) != run['rounds'] or not all(delivered):
                failures.append(f'{arm_id}: UNO_COMMAND_RESULT for .uno:InsertText missing in a round')
    for arm_id, arm in arms.items():
        if arm['route'] != 'uno-insert-text' or arm_id.startswith('doc-end/'):
            continue
        shape, name = arm_id.split('/')[0], arm_id.split('/uno-insert-text-')[1]
        if name == 'emoji':
            base = arms.get(f'{shape}/uno-insert-text-x')
            # changes() maps a paragraph index to [before, after]; replace only the inserted
            # span (the fixture's "text" contains an x of its own).
            expected = [{k: [v[0], swap_inserted(v[0], v[1])] for k, v in c.items()} for c in base['changes']] \
                if base else None
            equal = expected is not None and arm['changes'] == expected
            comparisons[arm_id] = {'against': f'{shape}/uno-insert-text-x with x -> U+1F600', 'equal': equal}
        else:
            key = arms.get(f'{shape}/key-{name}')
            equal = key is not None and arm['changes'] == key['changes']
            comparisons[arm_id] = {'against': f'{shape}/key-{name}', 'equal': equal}
        if not comparisons[arm_id]['equal']:
            failures.append(f'{arm_id}: differs from {comparisons[arm_id]["against"]}')
    teh = {a: arms[a]['changes'] for a in ('doc-end/key-teh', 'doc-end/uno-insert-text-teh') if a in arms}
    success = sorted({json.dumps(p.get('success')) for a in arms.values() for rs in a['unoCommandResults'] for p in rs})
    return {'verdict': 'M1_PASS' if not failures else 'M1_FAIL', 'failures': failures,
            'comparisons': comparisons, 'unoResultSuccessValues': success,
            'autocorrectPair': {'changes': teh, 'equal': len(set(json.dumps(v, ensure_ascii=False) for v in teh.values())) == 1}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('output must be fresh')
    problems = []
    run = read_run(a.run.resolve(), problems)
    result = {'schema': 1, 'readerSha256': sha(Path(__file__)), 'problems': problems,
              **({} if problems else verdict(run)), 'runRecord': run}
    a.output.write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'problems': problems, 'verdict': result.get('verdict'), 'failures': result.get('failures')},
                     ensure_ascii=False))
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
