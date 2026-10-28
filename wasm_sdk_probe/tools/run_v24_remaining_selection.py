#!/usr/bin/env python3
"""Original collector, unchanged, admitted by the fresh R1/S1-S4 verifier."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v24_remaining_counts as remaining
import run_v24_counted_selection as collector

if __name__ == '__main__':
    remaining.install()
    raise SystemExit(collector.main())
