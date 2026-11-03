#!/usr/bin/env python3
"""Compile the native Microsoft-formats harness (specs/SPEC-P-ms-formats.md M0): tools/msformat_native.cpp against the installed
native core (build-native-26-8).

A single-file g++ build of a small harness, no core build: the agent runs it after checking `uptime` and `pgrep -a make`
(AGENTS.md, 2026-10-28), and so does this script, refusing when a make is running.  The flags are build_calc_undo_native.py's.
Receipt: build-receipt.json in --out (argv, exit, seconds, source and output sha256).
  build_msformat_native.py --out DIR
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
SOURCE = SDK / "tools/msformat_native.cpp"
FLAGS = [f"-I{ROOT / 'libreoffice-26-8/include'}", f"-I{CORE / 'config_host'}",
         f"-I{CORE / 'workdir/UnoApiHeadersTarget/udkapi/comprehensive'}",
         f"-I{CORE / 'workdir/UnoApiHeadersTarget/offapi/comprehensive'}", f"-I{CORE / 'workdir/UnpackedTarball/boost'}"]


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
    snapshot = out / "msformat_native.cpp"
    shutil.copyfile(SOURCE, snapshot)
    install = CORE / "instdir/program"
    command = ["g++", "-std=c++20", "-O2", "-DLIBO_INTERNAL_ONLY", "-DCPPU_ENV=gcc3", "-DUNX", "-DLINUX", "-DX86_64", *FLAGS,
               str(snapshot), f"-L{install}", "-lsfxlo", "-lvcllo", "-lcomphelper", "-ltllo",
               *[str(install / n) for n in ("libuno_sal.so.3", "libuno_cppu.so.3", "libuno_cppuhelpergcc3.so.3")],
               f"-Wl,-rpath,{install}", "-ldl", "-o", str(out / "msformat-native")]
    receipt = {"schema": 1, "uptime": subprocess.check_output(["uptime"], text=True).strip(), "makes": makes.stdout,
               "compiler": subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
               "source": sha(SOURCE), "argv": command}
    started = time.monotonic()
    with (out / "compile.log").open("w") as log:
        code = subprocess.run(["taskset", "-c", "0", *command], stdout=log, stderr=subprocess.STDOUT).returncode
    receipt.update(exit=code, seconds=round(time.monotonic() - started, 2))
    if code == 0:
        receipt["output"] = sha(out / "msformat-native")
    receipt["sourceUnchanged"] = sha(SOURCE) == receipt["source"] == sha(snapshot)
    (out / "build-receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    if code:
        raise SystemExit(f"exit {code}; see {out}/compile.log")
    print(json.dumps({"output": receipt["output"], "seconds": receipt["seconds"]}))


if __name__ == "__main__":
    main()
