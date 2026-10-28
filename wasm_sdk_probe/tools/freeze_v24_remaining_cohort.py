#!/usr/bin/env python3
"""Freeze new R1/S1-S4 output paths and orchestration sources while retaining complete S5."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v24_remaining_counts as remaining

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    frozen = remaining.freeze(args.out)
    print(remaining.encoded({'cohort': str(args.out), 'cells': {s['population']: s['expectedCells'] for s in frozen['stages']},
                             'configSha256': frozen['configSha256'], 'orchestrationFiles': len(frozen['orchestrationSources'])}).decode(), end='')
