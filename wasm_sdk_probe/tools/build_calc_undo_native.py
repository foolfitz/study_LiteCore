#!/usr/bin/env python3
"""Compile the native Calc undo harness (SPEC-P-calc-undo 4.4): the Calc bridge and tools/calc_undo_native.cpp against the installed
native core (build-native-26-8), in two variants -- `undo` with OXSDK_ODS_UNDO and `control` without it -- from the same source bytes.

Single-file g++ builds of a small harness, no core build: the agent runs it after checking `uptime` and `pgrep -a make` (AGENTS.md,
2026-10-28), and so does this script, refusing when a make is running.  The commands are the Makefile's calc-style-native rule with the
driver swapped and, for `undo`, one define added.  Receipt: build-receipt.json in --out (argv, exit, seconds, source and output sha256).
  build_calc_undo_native.py --out DIR
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / "wasm_sdk_probe"
CORE = ROOT / "build-native-26-8"
SOURCES = {"bridge": SDK / "src/calc_cell_bridge.cpp", "header": SDK / "src/calc_cell_bridge.h", "driver": SDK / "tools/calc_undo_native.cpp"}
FLAGS = [f"-I{ROOT / 'libreoffice-26-8/include'}", f"-I{CORE / 'config_host'}",
         f"-I{CORE / 'workdir/UnoApiHeadersTarget/udkapi/comprehensive'}",
         f"-I{CORE / 'workdir/UnoApiHeadersTarget/offapi/comprehensive'}", f"-I{CORE / 'workdir/UnpackedTarball/boost'}"]
VARIANTS = {"undo": ["-DOXSDK_ODS_RANGE", "-DOXSDK_ODS_STYLE", "-DOXSDK_ODS_UNDO"], "control": ["-DOXSDK_ODS_RANGE", "-DOXSDK_ODS_STYLE"]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error("build output must be fresh")
    makes = subprocess.run(["pgrep", "-a", "make"], capture_output=True, text=True)
    if makes.returncode == 0:
        raise SystemExit("a make is running; ask the owner before compiling:\n" + makes.stdout)
    out.mkdir(parents=True)
    snapshot = out / "source"  # src/ and tools/ side by side: the driver includes "../src/calc_cell_bridge.h"
    for path in SOURCES.values():
        (snapshot / path.parent.name).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, snapshot / path.parent.name / path.name)
    install = CORE / "instdir/program"
    receipt = {"schema": 1, "uptime": subprocess.check_output(["uptime"], text=True).strip(), "makes": makes.stdout,
               "compiler": subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
               "sources": {k: sha(v) for k, v in SOURCES.items()}, "steps": []}
    for variant, defines in VARIANTS.items():
        target = out / variant
        target.mkdir()
        commands = [
            ["g++", "-std=c++20", "-O2", "-fPIC", "-DLIBO_INTERNAL_ONLY", *defines, "-DCPPU_ENV=gcc3", "-DUNX", "-DLINUX", "-DX86_64",
             *FLAGS, "-c", str(snapshot / "src/calc_cell_bridge.cpp"), "-o", str(target / "bridge.o")],
            ["g++", "-std=c++17", "-O2", *FLAGS, str(snapshot / "tools/calc_undo_native.cpp"), str(target / "bridge.o"),
             f"-L{install}", "-lsfxlo", "-lvcllo", "-lcomphelper", "-ltllo",
             *[str(install / n) for n in ("libuno_sal.so.3", "libuno_cppu.so.3", "libuno_cppuhelpergcc3.so.3")],
             f"-Wl,-rpath,{install}", "-ldl", "-o", str(target / "calc-undo-native")],
        ]
        for i, command in enumerate(commands):
            started = time.monotonic()
            with (target / f"compile-{i}.log").open("w") as log:
                code = subprocess.run(["taskset", "-c", "0", *command], stdout=log, stderr=subprocess.STDOUT).returncode
            receipt["steps"].append({"variant": variant, "argv": command, "exit": code, "seconds": round(time.monotonic() - started, 2)})
            if code:
                (out / "build-receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
                raise SystemExit(f"{variant} step {i} exit {code}; see {target}/compile-{i}.log")
        receipt.setdefault("outputs", {})[variant] = {"bridge.o": sha(target / "bridge.o"), "calc-undo-native": sha(target / "calc-undo-native")}
    receipt["sourcesUnchanged"] = all(sha(v) == receipt["sources"][k] for k, v in SOURCES.items())
    (out / "build-receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({"outputs": receipt["outputs"], "seconds": [s["seconds"] for s in receipt["steps"]]}))


if __name__ == "__main__":
    main()
