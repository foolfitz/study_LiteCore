#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 S2 (finding 179): the population is every ABI 6 profile under dist/profiles, generated from the directory
(CLAUDE.md section 1, form two).  Each profile's own worker takes extendSelection on the six moves under its own manifest.

  check_extend_gate_instances.py [--expect-red e2-editor-v29 ...] [--self-test]

Red profiles named by --expect-red are shipped history that cannot be rewritten; a red outside that list, a named one that went
green, or an empty population fails.  --self-test renames a profile to a name no gate knows: the fixed worker has to stay green
and the v29 worker has to go red, otherwise this tool cannot see the defect it exists for.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / 'dist/profiles'
READER = ROOT / 'tools/check_extend_gate_instances.cjs'
PRETEND = 'e2-editor-not-in-any-gate'


def read(worker, manifest, pretend=None):
    argv = ['node', str(READER), str(worker), str(manifest)] + ([pretend] if pretend else [])
    done = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    if done.returncode:
        raise SystemExit(f'{worker}: {done.stderr[-400:]}')
    return json.loads(done.stdout.strip().splitlines()[-1])


def holds(row):
    return len(row['cells']) == 6 and all(c['refused'] is None and c['reachedEngine'] for c in row['cells'])


def population():
    rows = []
    for manifest in sorted(PROFILES.glob('*/sdk-manifest.json')):
        contract = json.loads(manifest.read_text()).get('editorContract')
        if isinstance(contract, dict) and contract.get('abiVersion') == 6 and (manifest.parent / 'sdk-worker.js').is_file():
            rows.append(manifest)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-red', action='append', default=[])
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        fixed = PROFILES / 'e2-editor-v30'
        broken = PROFILES / 'e2-editor-v29'
        a = holds(read(fixed / 'sdk-worker.js', fixed / 'sdk-manifest.json', PRETEND))
        b = holds(read(broken / 'sdk-worker.js', broken / 'sdk-manifest.json', PRETEND))
        print(json.dumps({'fixedWorkerUnderUnknownName': a, 'v29WorkerUnderUnknownName': b}))
        return 0 if a and not b else 1
    rows = population()
    if not rows:
        print('EMPTY: no ABI 6 profile under', PROFILES)
        return 1
    report = {m.parent.name: read(m.parent / 'sdk-worker.js', m) for m in rows}
    red = sorted(name for name, row in report.items() if not holds(row))
    unexpected, cleared = sorted(set(red) - set(args.expect_red)), sorted(set(args.expect_red) - set(red))
    print(json.dumps({'profiles': sorted(report), 'red': red, 'unexpected': unexpected, 'expectedButGreen': cleared}, indent=1))
    return 1 if unexpected or cleared else 0


if __name__ == '__main__':
    sys.exit(main())
