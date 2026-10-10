#!/usr/bin/env python3
"""Dump the ported JS constants, old (a git revision) or new (the working tree), as JSON.

Usage: dump_constants.py TOOLS_DIR > out.json   (TOOLS_DIR holds the three runners to read)
"""
import json, sys
from pathlib import Path
tools = Path(sys.argv[1]).resolve()
real = Path(__file__).resolve().parents[5] / "wasm_sdk_probe" / "tools"
sys.path[:0] = [str(real)]
import importlib.util  # noqa: E402


def load(name):
    # By file, under the name the other two import it by, so that the old page
    # honesty and product path import the old page smoke and not the tree's.
    spec = importlib.util.spec_from_file_location(name, tools / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ps = load("run_e2_c_page_smoke")
pp = load("run_e2_c_product_path")
ph = load("check_m3_page_honesty")
names = ("GEOMETRY", "TOP_INK", "CARET_COLUMNS", "LINE_INK", "INK_ROWS", "POINT_AT", "DRAG",
         "ABORT_DRAG", "INDUCE_047", "INDUCE_EMPTY_PARAGRAPH")
out = {f"pp.{n}": getattr(pp, n) for n in names}
out["ps.POINT_AT"] = ps.POINT_AT
out["ph.DRAG"] = ph.DRAG
out["ph.TEXT_LINES"] = ph.TEXT_LINES
json.dump(out, sys.stdout)
