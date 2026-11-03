#!/usr/bin/env python3
"""SPEC-P-calc-undo, before the link: em++ -fsyntax-only on the three sources the ods-editor-v4 objects compile from, with v4's defines
and with v3's (nothing produced, no make; AGENTS.md 2026-10-28).  Positive control: a scratch copy of each source with an undeclared call
inside its OXSDK_ODS_UNDO block must fail with the define and pass without it -- otherwise "green" could mean the block was never compiled.
Refuses while a make runs.  Every command bound to one core: taskset -c 0.  Receipt: --out/report.json (argv, exit, seconds, errors).
  check_calc_undo_syntax.py --out DIR
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

SDK = Path(__file__).resolve().parents[1]
CORE = SDK.parent / "wasm-lite/build-ods-viewer-v2"
EMXX = SDK.parent / "wasm-lite/tools/emsdk/upstream/emscripten/em++"
CPPFLAGS = ["-DLOK_USE_UNSTABLE_API", f"-I{SDK.parent / 'libreoffice-26-8/include'}", f"-I{CORE / 'config_host'}",
            f"-I{CORE / 'workdir/UnoApiHeadersTarget/udkapi/comprehensive'}", f"-I{CORE / 'workdir/UnoApiHeadersTarget/offapi/comprehensive'}",
            f"-I{CORE / 'workdir/UnpackedTarball/boost'}", "-Oz", "-pthread", "-fwasm-exceptions", "-sSUPPORT_LONGJMP=wasm"]
ENGINE_V3 = ["-DOXSDK_READER_PROFILE", "-DOXSDK_ODS_VIEWER", "-DOXSDK_ODS_VIEWER_V2", "-DOXSDK_ODS_EDITOR", "-DOXSDK_ODS_RANGE", "-DOXSDK_ODS_STYLE"]
BRIDGE_V3 = ["-std=c++20", "-DLIBO_INTERNAL_ONLY", "-DOXSDK_ODS_RANGE", "-DOXSDK_ODS_STYLE"]
SOURCES = {"sdk_api.cpp": ENGINE_V3, "probe_engine.cpp": ENGINE_V3, "calc_cell_bridge.cpp": BRIDGE_V3}
# Where the control's undeclared call goes: a line inside each source's OXSDK_ODS_UNDO block, matched exactly once.
CONTROL_ANCHORS = {
    "sdk_api.cpp": "         | OXSDK_CAPABILITY_UNDO\n",
    "probe_engine.cpp": "  gOdsUndo = walk;\n",
    "calc_cell_bridge.cpp": "        if (!names.empty()) {\n",
}
CONTROL_CALL = {"sdk_api.cpp": "         | thisFunctionDoesNotExist()\n", "probe_engine.cpp": "  thisFunctionDoesNotExist();\n",
                "calc_cell_bridge.cpp": "        thisFunctionDoesNotExist();\n"}


def run(argv, label, report):
    started = time.monotonic()
    done = subprocess.run(["taskset", "-c", "0", *argv], capture_output=True, text=True, cwd=SDK)
    errors = [line for line in done.stderr.splitlines() if re.search(r"\berror\b", line)]
    report["runs"].append({"label": label, "argv": argv, "exit": done.returncode, "seconds": round(time.monotonic() - started, 1),
                           "errors": errors[:8]})
    print(label, done.returncode, round(time.monotonic() - started, 1), errors[:1], flush=True)
    return done.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    makes = subprocess.run(["pgrep", "-a", "make"], capture_output=True, text=True)
    report = {"uptime": subprocess.check_output(["uptime"], text=True).strip(), "makes": makes.stdout, "runs": []}
    if makes.returncode == 0:
        (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
        raise SystemExit("a make is running; ask the owner first")
    scratch = out / "scratch"
    scratch.mkdir()
    for name, defines in SOURCES.items():
        source = SDK / "src" / name
        base = [str(EMXX), "-fsyntax-only", *CPPFLAGS, f"-I{SDK / 'src'}", *defines]
        run([*base, "-DOXSDK_ODS_UNDO", str(source)], f"v4/{name}", report)
        run([*base, str(source)], f"v3/{name}", report)
        text = source.read_text()
        anchor = CONTROL_ANCHORS[name]
        if text.count(anchor) != 1:
            raise SystemExit(f"control anchor for {name} occurs {text.count(anchor)} times")
        mutated = scratch / name
        mutated.write_text(text.replace(anchor, anchor + CONTROL_CALL[name]) if name != "sdk_api.cpp"
                           else text.replace(anchor, CONTROL_CALL[name] + anchor))
        run([*base, "-DOXSDK_ODS_UNDO", str(mutated)], f"control-with-define/{name}", report)
        run([*base, str(mutated)], f"control-without-define/{name}", report)
    by = {r["label"]: r for r in report["runs"]}
    report["verdict"] = {
        "v4-clean": all(by[f"v4/{n}"]["exit"] == 0 for n in SOURCES),
        "v3-clean": all(by[f"v3/{n}"]["exit"] == 0 for n in SOURCES),
        "control-caught-with-define": all(by[f"control-with-define/{n}"]["exit"] != 0
                                          and any("thisFunctionDoesNotExist" in e for e in by[f"control-with-define/{n}"]["errors"])
                                          for n in SOURCES),
        "control-silent-without-define": all(by[f"control-without-define/{n}"]["exit"] == 0 for n in SOURCES),
    }
    shutil.rmtree(scratch)
    (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report["verdict"]))
    return 0 if all(report["verdict"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
