#!/usr/bin/env python3
"""Read original S5 plus fresh R1/S1-S4 raw artifacts; missing observations never earn credit."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v24_remaining_counts as remaining

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = remaining.read(args.cohort)
    except Exception as error:
        result = {'verdict': 'NOT_ESTABLISHED', 'reason': f'{type(error).__name__}: {error}'}
    with args.out.open('x') as stream:
        stream.write(remaining.encoded(result).decode())
    print(remaining.encoded(result).decode(), end='')
    raise SystemExit(0 if result['verdict'] == 'V24_SELECTION_COUNTS_HOLD' else 1)
