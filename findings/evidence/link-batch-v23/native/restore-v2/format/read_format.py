#!/usr/bin/env python3
"""Exit 0 only when every predeclared FORMAT residue cell establishes restoration."""
import argparse
import copy
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from arms import F_ARMS, expected_ops
from run_format import OLD, FIXTURES, identity
sys.path.insert(0, str(OLD))
from read_results import read_cell, run_log, landing


def undo_top(payload):
    actions = json.loads(payload)['actions']
    if actions in ('', []):
        return None
    assert isinstance(actions, list) and actions and isinstance(actions[0]['comment'], str)
    return actions[0]['comment']


def witness(cell, continuation):
    if continuation == 'shift':
        return cell['caret']
    op = next(op for op in cell['measured']['ops'] if op['op'] == 'Eend')
    return [op['atReturn']['selType'], op['atReturn']['selText']]


def judge(cells, p2):
    expected = {(a['name'], r) for a in F_ARMS for r in range(1, 6)}
    assert expected and set(cells) == expected, 'missing/extra cells'
    problems = [f'{name}/r{r}: {p}' for (name, r), cell in cells.items() for p in cell['problems']]
    failures = []
    if problems:
        return {'verdict': 'NOT_ESTABLISHED', 'problems': problems, 'failures': failures}
    for arm in F_ARMS:
        for r in range(1, 6):
            cell = cells[(arm['name'], r)]
            ops = cell['measured']['ops']
            if [op['op'] for op in ops] != expected_ops(arm):
                problems.append(f'{arm["name"]}/r{r}: op sequence mismatch')
                continue
            variant = arm['name'].split('-')[-1]
            if variant != 'direct':
                selected = ops[2]['atReturn']
                if selected['selType'] != 1 or selected['selText'] not in (p2, p2+'\n', p2+'\r\n'):
                    problems.append(f'{arm["name"]}/r{r}: SelectText did not establish P2 selection')
                restored = ops[3]['atReturn']
                if restored['selType'] != 0 or restored['selText']:
                    failures.append(f'{arm["name"]}/r{r}: restoration did not return NONE')
    if problems:
        return {'verdict': 'NOT_ESTABLISHED', 'problems': problems, 'failures': failures}
    for continuation in ('shift', 'handles'):
        baseline = None
        for r in range(1, 6):
            direct, reset, candidate, wrong = [cells[(f'format-{continuation}-{v}', r)]
                                              for v in ('direct', 'reset', 'candidate', 'wrong')]
            ref = landing(direct)
            ref_witness = witness(direct, continuation)
            expected_witness = ['', p2] if continuation == 'shift' else [1, p2]
            if ref_witness != expected_witness:
                problems.append(f'{continuation}/r{r}: direct selection is not the fixture P2 text')
            if baseline is None:
                baseline = ref
            if baseline != ref:
                problems.append(f'{continuation}/r{r}: unstable direct landing')
            if witness(reset, continuation) == ref_witness:
                problems.append(f'{continuation}/r{r}: RESET-only residue control does not discriminate')
            if witness(wrong, continuation) == ref_witness:
                problems.append(f'{continuation}/r{r}: wrong-point control does not discriminate')
            if landing(candidate) != ref or witness(candidate, continuation) != ref_witness:
                failures.append(f'{continuation}/r{r}: candidate saved shape/caret/next selection differs')
            try:
                top = undo_top(direct['measured']['ops'][0]['atReturn']['undo'])
                other = undo_top(candidate['measured']['ops'][-1]['atReturn']['undo'])
                if not top:
                    problems.append(f'{continuation}/r{r}: direct format lacks undo witness')
                if top != other:
                    failures.append(f'{continuation}/r{r}: candidate undo top differs')
            except (ValueError, TypeError, KeyError, AssertionError):
                problems.append(f'{continuation}/r{r}: unreadable undo top')
    return {'verdict': 'NOT_ESTABLISHED' if problems else 'FORMAT-RESTORE-FAILS' if failures else 'FORMAT-RESTORE-HOLDS',
            'cells': len(cells), 'rounds': 5, 'problems': problems, 'failures': failures}


def read(out):
    recorded = json.loads((out / 'identity.json').read_text())
    assert recorded == identity(recorded['binary']), 'binary/source/fixture identity changed'
    assert json.loads((out / 'arms.json').read_text()) == F_ARMS, 'recorded arms differ'
    log = run_log(out)
    wanted = {(a['name'], 'unipoll', r) for a in F_ARMS for r in range(1, 6)}
    assert set(log) == wanted, 'run-log population differs'
    cells = {}
    for name, mode, r in sorted(wanted):
        cell = read_cell(out / name, mode, r, log)
        path = out / name / f'{mode}-r{r}.jsonl'
        if path.exists():
            recs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            for kind in ('env', 'init', 'measured', 'saved', 'locate', 'done'):
                if sum(x['rec'] == kind for x in recs) != 1:
                    cell['problems'].append(f'{kind} must occur exactly once')
            env = next((x for x in recs if x['rec'] == 'env'), {})
            if env.get('OC_A11Y') is not None:
                cell['problems'].append('accessibility must remain disabled')
            points = {x['name']: x['rect'] for x in recs if x['rec'] == 'point'}
            try:
                before, wrong, end = [[int(v.strip()) for v in points[n].split(',')]
                                      for n in ('before', 'wrong', 'end')]
                assert all(len(x) == 4 for x in (before, wrong, end))
                assert before[1] > wrong[1] and end[1] == before[1] and end[0] > before[0]
            except (ValueError, KeyError, AssertionError):
                cell['problems'].append('recorded P1/P2/end points are not distinct expected positions')
        cells[(name, r)] = cell
    ns = {'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
          'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
    paragraphs = ET.parse(FIXTURES / 'plain3.fodt').findall('office:body/office:text/text:p', ns)
    assert len(paragraphs) == 3, 'fixture shape changed'
    return judge(cells, ''.join(paragraphs[1].itertext()))


def self_test():
    p2 = 'Bravo second paragraph'
    undo = json.dumps({'actions': [{'comment': 'Apply paragraph style'}]})
    cells = {}
    for arm in F_ARMS:
        continuation, variant = arm['name'].split('-')[1:]
        ops = [{'op': name, 'atReturn': {'selType': 0, 'selText': '', 'undo': undo}}
               for name in expected_ops(arm)]
        if variant != 'direct':
            ops[2]['atReturn'].update(selType=1, selText=p2)
        if continuation == 'handles':
            next(op for op in ops if op['op'] == 'Eend')['atReturn'].update(
                selType=0 if variant == 'reset' else 1,
                selText='' if variant == 'reset' else 'other' if variant == 'wrong' else p2)
        caret = ['', '' if variant == 'reset' and continuation == 'shift' else
                 'other' if variant == 'wrong' else p2]
        for r in range(1, 6):
            cells[(arm['name'], r)] = {'problems': [], 'shape': ['same'], 'caret': caret[:],
                                      'measured': {'ops': copy.deepcopy(ops)}}
    assert judge(cells, p2)['verdict'] == 'FORMAT-RESTORE-HOLDS'
    controls = []
    for mutation in ('empty-shift', 'empty-handles', 'wrong-save', 'wrong-undo', 'not-NONE',
                     'no-selection', 'no-reset-discriminator', 'no-wrong-discriminator',
                     'unclean', 'missing-cell', 'empty-population', 'wrong-op', 'bad-undo'):
        bad = copy.deepcopy(cells)
        cell = bad[('format-shift-candidate', 1)]
        if mutation == 'empty-shift': cell['caret'] = ['', '']
        elif mutation == 'empty-handles':
            next(op for op in bad[('format-handles-candidate', 1)]['measured']['ops'] if op['op'] == 'Eend')['atReturn']['selText'] = ''
        elif mutation == 'wrong-save': cell['shape'] = ['wrong']
        elif mutation == 'wrong-undo': cell['measured']['ops'][-1]['atReturn']['undo'] = '{"actions":[]}'
        elif mutation == 'not-NONE': cell['measured']['ops'][3]['atReturn']['selType'] = 1
        elif mutation == 'no-selection': cell['measured']['ops'][2]['atReturn']['selText'] = ''
        elif mutation == 'no-reset-discriminator': bad[('format-shift-reset', 1)]['caret'] = ['', p2]
        elif mutation == 'no-wrong-discriminator': bad[('format-shift-wrong', 1)]['caret'] = ['', p2]
        elif mutation == 'unclean': cell['problems'] = ['duplicate record']
        elif mutation == 'missing-cell': bad.pop(('format-shift-direct', 1))
        elif mutation == 'empty-population': bad = {}
        elif mutation == 'wrong-op': cell['measured']['ops'][3]['op'] = 'Rbefore'
        elif mutation == 'bad-undo': cell['measured']['ops'][-1]['atReturn']['undo'] = 'bad'
        try: rejected = judge(bad, p2)['verdict'] != 'FORMAT-RESTORE-HOLDS'
        except AssertionError: rejected = True
        assert rejected, mutation
        controls.append({'mutation': mutation, 'rejected': rejected})
    print(json.dumps({'syntheticGreen': True, 'redControls': controls,
                      'nativeAcceptance': 'NOT_ESTABLISHED'}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out', nargs='?', type=Path)
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        self_test()
    else:
        if a.out is None: p.error('out is required')
        result = read(a.out)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result['verdict'] == 'FORMAT-RESTORE-HOLDS' else 1)
