#!/usr/bin/env python3
"""Compile the type-route ruling M1 harness (f168_native_insert_text_m1.cpp); no core build.

The f168 build procedure with a different harness: same receipt form, same retained signature
source check.  Single-file g++; run after `uptime` and `pgrep -a make` (AGENTS.md, 2026-10-28)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_f168_native_owner as base
base.COMPILED=('f168_native_insert_text_m1.cpp','link_native_extend_signatures.cpp')
base.BINARY='f168-native-insert-text-m1'
if __name__=='__main__':raise SystemExit(base.main())
