#!/usr/bin/env python3
"""What a counted runner records as `testStatic` (specs/SPEC-M3-K-0.2.44.md, append 1, H2).

`make test-e2-c-static` has been red since v26 on items the K spec already names (section 4.1): they are tools bound to
an older generation or text drift, and the bound ones cannot be edited.  The chain's P6 reads the target with `make -i`
and demands exactly the named set.  The counted runners did not: they ran the plain target and required exit 0, so every
counted verdict would have been red on reds the spec had already judged, and autosave would have refused to start.

This is P6's reading, one implementation, so the two cannot drift: `make -i test-e2-c-static` in the project directory,
read by findings/evidence/k-0.2.44/p6_reds.py, compared with findings/evidence/k-0.2.44/p6-named-reds.txt.  `testStatic`
is 0 only when make itself succeeded AND the red set is exactly the named one; one more red or one fewer is not 0.  The
runners' clause `testStatic != 0` is unchanged.  The set read goes into the report beside it.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

EVIDENCE = Path(__file__).resolve().parent.parent.parent / "findings" / "evidence" / "k-0.2.44"
READER = EVIDENCE / "p6_reds.py"
NAMED = EVIDENCE / "p6-named-reds.txt"


def read_reds(transcript: Path) -> str:
    answer = subprocess.run([sys.executable, str(READER), str(transcript)], capture_output=True, text=True)
    if answer.returncode != 0:
        raise RuntimeError(f"{READER.name} exit {answer.returncode}: {answer.stderr[-400:]}")
    return answer.stdout


def judge(make_exit: int, reds: str, named: str) -> dict[str, Any]:
    same = reds.strip("\n") == named.strip("\n")
    return {"testStatic": 0 if make_exit == 0 and same else (make_exit or 1),
            "testStaticMakeExit": make_exit,
            "testStaticReds": reds.strip("\n").split("\n"),
            "testStaticNamedSha256": hashlib.sha256(named.encode()).hexdigest()}


def static_target(project: Path) -> dict[str, Any]:
    """The runners' `static.update(static_target(PROJECT))`: `testStatic` and what it was read from."""
    with tempfile.NamedTemporaryFile("w+", suffix=".static.txt") as transcript:
        make_exit = subprocess.run(["make", "-i", "test-e2-c-static"], cwd=project, stdout=transcript,
                                   stderr=subprocess.STDOUT, text=True).returncode
        transcript.flush()
        return judge(make_exit, read_reds(Path(transcript.name)), NAMED.read_text(encoding="utf-8"))
