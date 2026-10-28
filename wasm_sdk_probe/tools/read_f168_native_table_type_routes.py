#!/usr/bin/env python3
"""Read finding 168 native route runs; describes, decides nothing about the product.

For every run directory: every artifact hash in completion.json must match, every inventory
arm must have one record per round, every "before" save must equal the fixture, and the
table2 key arm must reproduce native run-03's bound shift-Right@cell-end/type save (the
positive control that this harness makes the oracle's selection).  Then, per arm, the
distinct saved-paragraph changes across rounds, and per selection group whether each route
equals that group's key route.  Exit 1 on any structural problem.

Usage: read_f168_native_table_type_routes.py RUN_DIR [RUN_DIR ...] --output FRESH.json
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odt_paragraphs import paragraph_texts_from_xml

ROOT = Path(__file__).resolve().parents[2]
RUN03 = ROOT / 'findings/evidence/link-batch-v23/feature-protocol/s5-native/run-03'
RUN03_REFERENCE = 'shift-Right@cell-end_type-after.odt'
TABLE2_SELECTION = 'A1 cell text\tB1 cell text\n'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def odt_paragraphs(path):
    with zipfile.ZipFile(path) as z:
        return paragraph_texts_from_xml(z.read('content.xml'))


def changes(fixture, after):
    if len(fixture) != len(after):
        return {'lengthChanged': [len(fixture), len(after)], 'after': after}
    return {str(i): [a, b] for i, (a, b) in enumerate(zip(fixture, after)) if a != b}


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
    command = json.loads((run / 'command.json').read_text())
    rounds = command['rounds']
    inventory = [json.loads(l) for l in (run / 'inventory.jsonl').read_text().splitlines() if l.strip()]
    fixture = paragraph_texts_from_xml((run / 'fixture.fodt').read_bytes())
    records = {}
    for line in (run / 'native.jsonl').read_text().splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            problem('unparsable native line')
            continue
        if 'fatal' in row:
            problem(f'fatal row: {row}')
        if 'id' in row and 'round' in row and 'fatal' not in row:
            key = (row['id'], row['round'])
            if key in records:
                problem(f'duplicate record {key}')
            records[key] = row
    reference = odt_paragraphs(RUN03 / 'saves' / RUN03_REFERENCE)
    arms = {}
    for arm in inventory:
        outcomes = []
        for r in range(1, rounds + 1):
            row = records.get((arm['id'], r))
            if row is None:
                problem(f'missing record {arm["id"]} round {r}')
                continue
            if not (row['savedBefore'] and row['savedAfter']):
                problem(f'save failed {arm["id"]} round {r}')
                continue
            if not all((run / 'saves' / row[f]).is_file() for f in ('beforeFile', 'afterFile')):
                problem(f'save file missing {arm["id"]} round {r}')
                continue
            settles = [row['openedSettleMs'], row['setupSettleMs'], row['finalSettleMs'], *row['shiftSettleMs']]
            if any(v < 0 for v in settles):
                problem(f'settle cap {arm["id"]} round {r}')
            before = odt_paragraphs(run / 'saves' / row['beforeFile'])
            if before != fixture:
                problem(f'before save differs from fixture {arm["id"]} round {r}')
            after = odt_paragraphs(run / 'saves' / row['afterFile'])
            selection = row['between']['getTextSelection']
            if arm['id'].startswith('table2/') and selection != TABLE2_SELECTION:
                problem(f'table2 selection differs {arm["id"]} round {r}: {selection!r}')
            if arm['id'] == 'table2/key-x' and after != reference:
                problem(f'table2/key-x does not reproduce run-03 {RUN03_REFERENCE} (round {r})')
            outcomes.append({'round': r, 'selection': selection, 'selectionType': row['betweenSelectionType'],
                             'routeResult': row['routeResult'], 'changes': changes(fixture, after),
                             'afterSha256': sha(run / 'saves' / row['afterFile'])})
        distinct = []
        for o in outcomes:
            sig = json.dumps(o['changes'], ensure_ascii=False, sort_keys=True)
            for d in distinct:
                if d['signature'] == sig:
                    d['rounds'].append(o['round'])
                    break
            else:
                distinct.append({'signature': sig, 'changes': o['changes'], 'rounds': [o['round']]})
        arms[arm['id']] = {'route': arm['route'], 'text': arm['text'], 'records': len(outcomes),
                           'stableAcrossRounds': len(distinct) == 1,
                           'selections': sorted({o['selection'] for o in outcomes}),
                           'routeResults': sorted({json.dumps(o['routeResult'], sort_keys=True) for o in outcomes}),
                           'distinctOutcomes': [{k: v for k, v in d.items() if k != 'signature'} for d in distinct]}
    if len(records) != len(inventory) * rounds:
        problem(f'{len(records)} records for {len(inventory)} arms x {rounds} rounds')
    comparisons = {}
    for arm_id, arm in arms.items():
        group = arm_id.split('/')[0]
        key = arms.get(f'{group}/key-x')
        if key is None or arm_id == f'{group}/key-x' or not key['stableAcrossRounds'] or not arm['stableAcrossRounds']:
            continue
        comparisons[arm_id] = {'equalsKeyRoute': arm['distinctOutcomes'][0]['changes'] == key['distinctOutcomes'][0]['changes']}
    return {'run': str(run.relative_to(ROOT)) if run.is_relative_to(ROOT) else str(run),
            'environment': command['environment'], 'rounds': rounds,
            'nativeExitCode': completion['exitCode'], 'arms': arms, 'comparisonsWithKeyRoute': comparisons}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('output must be fresh')
    problems = []
    runs = [read_run(r.resolve(), problems) for r in a.runs]
    result = {'schema': 1, 'readerSha256': sha(Path(__file__)), 'problems': problems,
              'runReference': {'path': str((RUN03 / 'saves' / RUN03_REFERENCE).relative_to(ROOT)),
                               'sha256': sha(RUN03 / 'saves' / RUN03_REFERENCE)},
              'runs': runs}
    a.output.write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'problems': problems, 'output': str(a.output)}, ensure_ascii=False))
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
