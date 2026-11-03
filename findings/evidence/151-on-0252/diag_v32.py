#!/usr/bin/env python3
"""Finding 151 on the live page.  tools/diag_v21_dirty_move.py is bound by its evidence and not edited: this runs its main() with two things changed in
memory, the default profile the mirror repoints to (e2-editor-v32) and the page prefix its check expects (the live page, f6fd0b75).  Its label `v21` then
names the live page; the report's `pages` block has the true identity.  `dist0224` stays the 0.2.24 package on v20, the red control.
Takes the tool's arguments: diag_v32.py --browser chrome --variants v8d,v8d0224,v1,v7 --rounds 3 --out DIR
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "wasm_sdk_probe/tools"))
import diag_v21_dirty_move as d  # noqa: E402

build = d.common.build_mirror


def v32(target, *, page_profile=None, **kwargs):
    return build(target, page_profile=page_profile or "e2-editor-v32", **kwargs)


d.common.build_mirror = v32
d.V21_PAGE_PREFIX = "f6fd0b75dbf26a09"
raise SystemExit(d.main())
