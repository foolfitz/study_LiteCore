#!/usr/bin/env python3
"""T1's reading: judge_c2.py or judge_p2.py, unedited, with the page pin moved to generation 83's page in process.

Their PAGE line names host 0.2.44's page and belongs to the K 0.2.44 spec (W-b1 style re-pins are the next K spec's); the
derive rule is the handoff's.  --page on judge_c2.py would print a red-case OVERRIDE, and judge_p2.py has no such flag.
  judge_on_83.py c2|p2 --dir DIR
"""
import importlib.util
from pathlib import Path
import sys

PAGE = "022d0cd0b5152f1ee9cabc74b10f5af2eb55935299228119a419ab717957759b"
EVIDENCE = Path(__file__).resolve().parents[2]
TOOL = {"c2": EVIDENCE / "c-prime/c2/judge_c2.py", "p2": EVIDENCE / "typing-latency/judge_p2.py"}[sys.argv[1]]
spec = importlib.util.spec_from_file_location("judge", TOOL)
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)
judge.PAGE = PAGE
sys.argv = [str(TOOL)] + sys.argv[2:]
raise SystemExit(judge.main())
