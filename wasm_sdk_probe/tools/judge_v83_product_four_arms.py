#!/usr/bin/env python3
"""Four-arm reader on v29/frozen 83 (SPEC-M3-v29-tick-pacing section 6 T3).

Derived from tools/judge_v82_product_four_arms.py (bound by F4-82's evidence; not edited).  The differences
are a closed list: this paragraph and the line above it; the identity module v82 -> v83; the four identity
messages (frozen 83, v29 ABI6, frozen v29, the generation-83 page).  Everything below is that file's text
from its own derivation note on.

Four-arm reader on v28/frozen 82 (SPEC-M3-v28-last-line-fallback 7.3 F4-82).

Derived from tools/judge_v81_product_four_arms.py (bound by F4-81's evidence; not edited).  The differences
are a closed list: this paragraph and the line above it; the identity module v81 -> v82; the four identity
messages (frozen 82, v28 ABI6, frozen v28, the generation-82 page).  Everything below is that file's text
from its own derivation note on.

Four-arm reader on v27/frozen 81 (SPEC-M3-v27-finding-176 7.3 F4-81).

Derived from tools/judge_v80_product_four_arms.py (bound by F4-80's evidence; not edited).  The differences
are a closed list: this paragraph and the line above it; the identity module v80 -> v81; the four identity
messages (frozen 81, v27 ABI6, frozen v27, the generation-81 page).  Everything below is that file's text
from its own derivation note on.

Four-arm reader on v26/frozen 80 (SPEC-M3-select-all-v26 5.6 F4-80).

Derived from tools/judge_v79_product_four_arms.py (bound by F4-79's evidence; not edited).  The differences
are a closed list: this paragraph and the line above it; the identity module v79 -> v80; the four identity
messages (frozen 80, v26 ABI6, frozen v26, the generation-80 page).  Everything below is that file's text
from its own derivation note on.

Derived from tools/judge_v25_product_four_arms.py (bound by v25 F4's evidence; not edited).  The differences
are a closed list: this paragraph and the line above it; the identity module v25 -> v79; the two identity
messages (frozen 79, the generation-79 page).  Everything below is that file's text.

Derived from tools/judge_v24_product_four_arms.py (bound by v24's A4 count, not edited): the same
rebinding of v23's reader, with only the identity clause naming v25.  v23's reader code and
raw-evidence rules remain intact.
"""
import argparse
import json
from pathlib import Path
import sys
from types import FunctionType

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_v23_product_four_arms as j23
from v83_four_arms_identity import PROFILE, BUNDLE, BUNDLE_FILE_SHA256, identity


class Record(j23.Record):
    def _identity(self, repo):
        i = self.identity
        shell = i.get('shell') or {}
        j23.need(shell.get('bundle') == BUNDLE and shell.get('bundleFileSha256') == BUNDLE_FILE_SHA256,
                 'shell generation is not frozen 83')
        want = identity()
        j23.need(i.get('profile') == PROFILE and i.get('abiVersion') == 6, 'profile is not v29 ABI6')
        j23.need(i.get('profileArtifacts') == want['artifacts'], 'profile artifacts are not frozen v29')
        j23.need(i.get('productModuleSha256') == want['pageSha256']
                 and i.get('candidatePageSha256') in (None, want['pageSha256']),
                 'product page is not the generation-83 page')
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
