#!/usr/bin/env python3
"""Exact r2 identity; share validated packing without widening the original entry."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_e2_v23_diagnostic_profile import main
if __name__ == "__main__":
    raise SystemExit(main(expected_profile="e2-editor-v23-diag-r2"))
