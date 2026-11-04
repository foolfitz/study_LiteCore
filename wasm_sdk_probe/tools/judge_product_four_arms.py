"""Four-arm reader (F4) on a frozen generation, named by --generation (e2/generations/generation-NN.json).

One tool for every generation from 90 on (CLAUDE.md, the section on cadence, item 2), in place of the per-generation
copies tools/judge_v79..v89_product_four_arms.py (kept, each bound by its own evidence).  It is judge_v89's text with
the identity read from tools/four_arms_identity.py: v23's reader and raw-evidence rules unchanged, the identity clause
naming the generation's bundle, profile, artifacts and page.

  judge_product_four_arms.py --generation N RUN_DIR [RUN_DIR ...] --out FILE
"""
import argparse
import json
from pathlib import Path
import sys
from types import FunctionType

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_v23_product_four_arms as j23
from four_arms_identity import Generation

GEN = None


def bind(number):
    global GEN
    GEN = Generation(number)
    return GEN


class Record(j23.Record):
    def _identity(self, repo):
        g = GEN
        i = self.identity
        shell = i.get('shell') or {}
        j23.need(shell.get('bundle') == g.bundle and shell.get('bundleFileSha256') == g.bundle_file_sha256,
                 f'shell generation is not frozen {g.number}')
        want = g.identity()
        j23.need(i.get('profile') == g.profile and i.get('abiVersion') == 6, f'profile is not {g.profile} ABI6')
        j23.need(i.get('profileArtifacts') == want['artifacts'], f'profile artifacts are not frozen {g.profile}')
        j23.need(i.get('productModuleSha256') == want['pageSha256']
                 and i.get('candidatePageSha256') in (None, want['pageSha256']),
                 f'product page is not the generation-{g.number} page')
        super()._identity(repo)


G = dict(vars(j23))
G['Record'] = Record


def rebound(fn):
    return FunctionType(fn.__code__, G, fn.__name__, fn.__defaults__, fn.__closure__)


G['_judge_run'] = rebound(j23._judge_run)
judge_run = G['judge_run'] = rebound(j23.judge_run)
aggregate = rebound(j23.aggregate)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--generation', type=int, required=True)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    bind(args.generation)
    result = aggregate(args.runs, j23.RUNNER.read_text())
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=1, ensure_ascii=False, default=str); stream.write('\n')
    print(json.dumps({k: v['outcome'] for k, v in result['arms'].items()} | {'problems': result['problems']}, indent=1))
    return 0 if not result['problems'] and all(v['outcome'] == j23.PASS for v in result['arms'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
