#!/usr/bin/env python3
"""I-enter-raw-substring's replay on v28 (specs/SPEC-M3-K-0.2.44.md section 3, row 8).

tools/check_v24_shift_enter.py is IMPORTED and not edited (v24's evidence binds it).  One in-process change: its
`preflight`, which pins the v24 cutover page, is replaced by tools/v82_four_arms_identity.py's identity() (profile v28,
frozen generation 82).  Everything else, the span-aware oracle and the verdict name V24_ENTER_HOLDS included, is that tool's.

  python3 -I tools/check_v82_shift_enter.py --out <new dir> [--repetitions 3]
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_v24_shift_enter as bound  # noqa: E402
from v82_four_arms_identity import identity  # noqa: E402

bound.preflight = identity

if __name__ == "__main__":
    raise SystemExit(bound.main())
