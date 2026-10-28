#!/usr/bin/env python3
"""Original raw selection judge, unchanged, with the declared remaining-cohort verifier."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v24_remaining_counts as remaining
import judge_v24_counted_selection as reader

if __name__ == '__main__':
    remaining.install()
    raise SystemExit(reader.main())
