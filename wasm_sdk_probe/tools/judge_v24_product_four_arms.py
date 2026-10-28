#!/usr/bin/env python3
"""Four-arm reader on v24/frozen 77; v23's reader code and raw-evidence rules remain intact."""
import argparse
import json
from pathlib import Path
import sys
from types import FunctionType

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_v23_product_four_arms as j23
from v24_feature_selection_cases import PROFILE, BUNDLE, BUNDLE_FILE_SHA256, identity


class Record(j23.Record):
    def _identity(self, repo):
        i = self.identity
        shell = i.get('shell') or {}
        j23.need(shell.get('bundle') == BUNDLE and shell.get('bundleFileSha256') == BUNDLE_FILE_SHA256,
                 'shell generation is not frozen 77')
        want = identity()
        j23.need(i.get('profile') == PROFILE and i.get('abiVersion') == 6, 'profile is not v24 ABI6')
        j23.need(i.get('profileArtifacts') == want['artifacts'], 'profile artifacts are not frozen v24')
        super()._identity(repo)


G = dict(vars(j23))
G['Record'] = Record


def rebound(fn):
    return FunctionType(fn.__code__, G, fn.__name__, fn.__defaults__, fn.__closure__)


G['_judge_run'] = rebound(j23._judge_run)
judge_run = G['judge_run'] = rebound(j23.judge_run)
aggregate = rebound(j23.aggregate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = aggregate(args.runs, j23.RUNNER.read_text())
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=1, ensure_ascii=False, default=str); stream.write('\n')
    print(json.dumps({k: v['outcome'] for k, v in result['arms'].items()} | {'problems': result['problems']}, indent=1))
    return 0 if not result['problems'] and all(v['outcome'] == j23.PASS for v in result['arms'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
