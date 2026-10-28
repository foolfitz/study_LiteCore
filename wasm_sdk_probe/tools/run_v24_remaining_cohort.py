#!/usr/bin/env python3
"""Run a fresh R1/S1-S4 cohort with the original launcher's code and the declared verifier adapter."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v24_remaining_counts as remaining

if __name__ == '__main__':
    remaining.install()
    raise SystemExit(remaining.base.main())
