#!/usr/bin/env python3
"""Freeze fresh S5/R1/S1-S4 inputs and commands. Does not run V0, browsers, make or DDEV."""
import argparse
import gzip
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v24_counted_selection_cases import ROOT, PROJECT, config, encoded, digest, sha, KINDS
from v24_feature_selection_cases import sources
from run_v24_counted_cohort import now, stage_spec, verify
from judge_v23_feature_selection import check_pre_red

PRE = ROOT / 'findings/evidence/link-batch-v24/pre-count'
PREREQUISITES = {
    'j-red/run-01/j-red.json': 'RED_CASES_HOLD',
    'm2/run-01.reader.json': 'PASS',
    't5/run-01/report.json': 'T5_HOLDS',
    't4/read-02.json': 'PASS',
    't4/enter-replay-01/report.json': 'V24_ENTER_HOLDS',
    'v0-double-prime/run-04/report.json': 'V0PP_HOLDS',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--pre-red-report', type=Path, default=ROOT / 'findings/evidence/link-batch-v23/feature-pre-red/counted-05/report.json')
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.relative_to(ROOT)
    plan = config()
    pre_red = check_pre_red(args.pre_red_report)
    prerequisites = {}
    controls = ROOT / 'findings/evidence/link-batch-v24/count-preparation/controls-02.receipt.json'
    if json.loads(controls.read_bytes()).get('exit') != [0, 0]:
        raise ValueError('counted/A4 instrument controls have not passed')
    prerequisites[str(controls.relative_to(ROOT))] = sha(controls)
    for name in ('controls-02.stdout.txt', 'controls-02.a4.stdout.txt',
                 'a4-no-override-01/wrapper.json', 'a4-v78-01/wrapper.json', 'a4-old-runs-01.json'):
        path = controls.parent / name
        prerequisites[str(path.relative_to(ROOT))] = sha(path)
    for name, expected in PREREQUISITES.items():
        path = PRE / name
        if json.loads(path.read_bytes()).get('verdict') != expected:
            raise ValueError('prerequisite verdict differs: ' + name)
        prerequisites[str(path.relative_to(ROOT))] = sha(path)
    for path in (PRE / 'page-gates/run-01/report.json', PRE / 'i-red/run-01/report.json',
                 PRE / 'bound-tool-edits.json', PROJECT / 'e2/editor-shell-v2-bundle-v77.json',
                 Path(pre_red['path'])):
        prerequisites[str(path.relative_to(ROOT))] = sha(path)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'frozen-config.json.gz').write_bytes(gzip.compress(encoded(plan), mtime=0))
    served = sources()
    with tarfile.open(args.out / 'frozen-sources.tar.gz', 'x:gz') as archive:
        blobs = {**{'instrument/' + n: (PROJECT / n).read_bytes() for n in plan['instrumentSources']},
                 **{'served/' + n: served[n] for n in plan['servedSources']}}
        for name, raw in sorted(blobs.items()):
            info = tarfile.TarInfo(name); info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    cohort = args.out / 'cohort.json'
    prerequisites.update({str(p.relative_to(ROOT)): sha(p) for p in (
        args.out / 'frozen-config.json.gz', args.out / 'frozen-sources.tar.gz')})
    frozen = {'schema': 1, 'createdAt': now(),
              'gitHead': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'authority': 'SPEC-M3-link-batch-v24 sections 6.4, 17, 18; execution mode awaits owner',
              'scope': 'Fresh full S5, R1, S1-S4; both browsers; first nonpass stops; no retry',
              'cutoff': 'First complete clean population per browser; later concerns become findings',
              'configSha256': digest(encoded(plan)), 'instrumentSources': plan['instrumentSources'],
              'servedSources': plan['servedSources'], 'preRed': pre_red, 'prerequisites': prerequisites,
              'stages': [stage_spec(cohort, kind, plan, pre_red['path']) for kind in KINDS]}
    cohort.write_bytes(encoded(frozen))
    verify(cohort)
    print(encoded({'cohort': str(cohort), 'configSha256': frozen['configSha256'],
                   'cells': {s['population']: s['expectedCells'] for s in frozen['stages']}}).decode(), end='')


if __name__ == '__main__':
    main()
