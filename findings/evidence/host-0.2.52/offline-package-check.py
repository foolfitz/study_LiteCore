#!/usr/bin/env python3
"""Existing K0/Z0/H5 package reader and its red cases, only BUILD_ID rebound for candidate 0.2.52.

Derived from findings/evidence/host-0.2.47/offline-package-check.py (not edited), itself a copy of 0.2.46's, 0.2.45's, 0.2.44's, 0.2.43's,
0.2.42's, 0.2.41's and 0.2.40's.  Closed list of differences: this docstring (0.2.51 -> 0.2.52 in its first line, and
this derivation note).  The reader has no profile names and no delta clause of its own, so nothing else needs
rebinding; the 0.2.52 delta is judged by prepare-release.py inline and by check-delta.py from the two archived
MANIFEST.json files.
"""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
import check_m3_assets as assets

assets.BUILD_ID = json.loads(Path(__file__).with_name('release.json').read_bytes())['buildId']


def main():
    app = Path(sys.argv[1]); package = assets.package_record(app)
    problems = assets.score_package(package, True)
    result = {'scope': 'Offline package only; no full K binding or credit', 'buildId': assets.BUILD_ID,
              'problems': problems, 'redCases': []}
    if not problems:
        for clause, label, mutate in assets.PACKAGE_CASES:
            changed = copy.deepcopy(package); mutate(changed)
            result['redCases'].append({'clause': clause, 'label': label,
                                       'red': any(p.startswith(clause) for p in assets.score_package(changed, True))})
    result['verdict'] = 'PACKAGE_HOLDS' if not problems and result['redCases'] and all(c['red'] for c in result['redCases']) else 'NOT_ESTABLISHED'
    print(json.dumps(result, indent=1)); return 0 if result['verdict'] == 'PACKAGE_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
