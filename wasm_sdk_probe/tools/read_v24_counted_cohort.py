#!/usr/bin/env python3
"""Read a v24 counted cohort's existing raw artifacts; no missing-cell credit or browser work."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v24_counted_selection_cases import ROOT, encoded, digest, sha
from run_v24_counted_cohort import verify
from judge_v24_counted_selection import inspect, judge, load_cell


def read(cohort):
    cohort = Path(cohort).resolve()
    frozen = verify(cohort)
    status = json.loads(cohort.with_name('status.json').read_bytes())
    if status['cohortSha256'] != sha(cohort):
        raise ValueError('status cohort binding differs')
    stages = status['stages']
    if [s['population'] for s in stages] != [s['population'] for s in frozen['stages'][:len(stages)]]:
        raise ValueError('stage order differs')
    output = {'schema': 1, 'scope': 'Existing raw observations only; no missing-cell credit',
              'cohortSha256': sha(cohort), 'statusSha256': sha(cohort.with_name('status.json')),
              'state': status['state'], 'stages': []}
    for stage, receipt in zip(frozen['stages'], stages):
        kind = stage['population']
        for key in ('preflight', 'runner', 'judge'):
            if key in receipt and sha(cohort.parent / receipt[key]['log']) != receipt[key]['logSha256']:
                raise ValueError(key + ' log differs')
        entry = {'population': kind, 'required': stage['expectedCells'], 'observed': 0, 'verdict': 'NOT_ESTABLISHED'}
        output['stages'].append(entry)
        if 'reportSha256' not in receipt:
            entry['reason'] = 'stage has no bound report'; continue
        preflight = cohort.parent / receipt['v0']['path']
        if sha(preflight) != receipt['v0']['sha256'] or json.loads(preflight.read_bytes()).get('verdict') != 'V0PP_HOLDS':
            raise ValueError('V0 receipt differs/nonpassing')
        directory = ROOT / stage['output']
        if sha(directory / 'report.json') != receipt['reportSha256']:
            raise ValueError('report receipt differs')
        report = json.loads((directory / 'report.json').read_bytes())
        plan = report['config']
        if digest(encoded(plan)) != frozen['configSha256'] or report.get('postConfig') != plan:
            raise ValueError('run config differs/incomplete')
        if report.get('preparationOnly') is not False or report.get('countedV24') is not True or report.get('scratch'):
            raise ValueError('unqualified collection')
        if report.get('cohortSha256') != sha(cohort) or report.get('cohort') != str(cohort) or report.get('preRed') != frozen['preRed']:
            raise ValueError('run cohort/prerequisite differs')
        if report.get('population') != kind or report.get('argv') != stage['runnerArgv'][2:]:
            raise ValueError('run command/population differs')
        from v24_counted_selection_cases import verify_mirror
        if report['mirrorBindings'] != verify_mirror(directory / 'mirror', plan):
            raise ValueError('mirror differs')
        cells = [load_cell(directory, item) for item in report['runs']]
        keys = [(c['browser'], c['caseId']) for c in cells]
        expected = [(b, c) for b in stage['browsers'] for c in stage['caseIds']]
        if keys != expected[:len(keys)] or len(set(keys)) != len(keys):
            raise ValueError('observations are not the declared unique prefix')
        for cell in cells:
            if not cell.get('fatal'):
                value = json.loads(encoded(inspect(cell['page'], plan, cell['browser'])))
                if value != cell.get('inspection'):
                    raise ValueError('inspection differs: ' + cell['caseId'])
        result = judge(cells, plan, kind)
        logged = json.loads((cohort.parent / receipt['judge']['log']).read_bytes())
        if json.loads(encoded(result)) != logged:
            raise ValueError('aggregate reread differs')
        entry.update(observed=len(cells), verdict=result['verdict'], populationComplete=result['populationComplete'],
                     groups=result['groups'], reportSha256=receipt['reportSha256'],
                     nonpassing=[{'cell': r['cell'], 'verdict': r['verdict'], 'reason': r.get('reason')}
                                 for r in result['results'] if r['verdict'] != 'PASS'])
        if entry['verdict'] == 'PASS' and (receipt['runner']['exit'] or receipt['judge']['exit']):
            raise ValueError('PASS with nonzero runner/judge')
    complete = len(stages) == len(frozen['stages']) and all(s['verdict'] == 'PASS' for s in output['stages'])
    if complete and status['state'] != 'ALL_COHORTS_PASS':
        raise ValueError('complete population status differs')
    output['verdict'] = 'V24_SELECTION_COUNTS_HOLD' if complete else 'NOT_ESTABLISHED'
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = read(args.cohort)
    except Exception as error:
        result = {'verdict': 'NOT_ESTABLISHED', 'reason': f'{type(error).__name__}: {error}'}
    with args.out.open('x') as stream:
        stream.write(encoded(result).decode())
    print(encoded(result).decode(), end='')
    return 0 if result['verdict'] == 'V24_SELECTION_COUNTS_HOLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
