#!/usr/bin/env python3
"""S1 (specs/SPEC-M3-link-batch-v22.md 5.2): a linked loader hands the engine thread a 1 MiB stack.

The value of -sDEFAULT_PTHREAD_STACK_SIZE does not reach probe.wasm.  Emscripten writes it into the
loader as a literal argument of `_emscripten_thread_init` (the `{{{ DEFAULT_PTHREAD_STACK_SIZE }}}` of
src/lib/libpthread.js), and the C side only stores what it is handed.  So the loader's bytes are where
the fix is, and this reads them, not the Makefile.

The anchor is the call's tail, as finding 089's and 153's mirror patches anchor it.  A bare `65536` is
not an anchor: v21's probe.js holds six of them (`grep -o 65536 | wc -l`, 2026-10-19).

  check_pthread_stack_literal.py PROBE_JS [PROBE_JS ...]

Per file: `,!ENVIRONMENT_IS_WEB,1048576,false)` exactly once, `,!ENVIRONMENT_IS_WEB,65536,false)` zero
times.  Exit 0 every file holds; 1 one does not; 3 a file is missing.  Last line `VERDICT ...`.

Red first (spec 5.1 S1-red): v21's dist/profiles/e2-editor-v21/probe.js must give exit 1.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

WANT = b",!ENVIRONMENT_IS_WEB,1048576,false)"
OLD = b",!ENVIRONMENT_IS_WEB,65536,false)"


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    missing = [p for p in paths if not Path(p).is_file()]
    if missing:
        print(f"VERDICT NOT DONE: missing {missing}")
        return 3
    bad = 0
    for p in paths:
        raw = Path(p).read_bytes()
        want, old = raw.count(WANT), raw.count(OLD)
        ok = want == 1 and old == 0
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {p} sha256 {hashlib.sha256(raw).hexdigest()} "
              f"1048576-anchor {want} (want 1) 65536-anchor {old} (want 0)")
    print("VERDICT PASS" if not bad else f"VERDICT FAIL ({bad} of {len(paths)})")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
