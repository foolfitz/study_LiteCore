#!/usr/bin/env python3
"""Run the type-route ruling M1 harness; never compiles. One run into a fresh directory, no retry.

The f168 runner procedure (fixture, environment, pins before/after) with the M1 harness's
compiled sources and this run's own instrument files pinned."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_f168_native_table_type_routes as base
from build_v23_native_s5_owner import TOOLS
base.COMPILED=('f168_native_insert_text_m1.cpp','link_native_extend_signatures.cpp')
base.SOURCES=[TOOLS/n for n in (*base.COMPILED,'build_f168_native_owner.py','build_f168_m1_native.py',
    'run_f168_native_table_type_routes.py','run_f168_m1_native.py','read_f168_m1_native.py','odt_paragraphs.py')]
if __name__=='__main__':raise SystemExit(base.main())
