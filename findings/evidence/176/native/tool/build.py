#!/usr/bin/env python3
"""Compile finding 176's native harness from a snapshot of its source; no core build.

A single-file g++ build of a small harness (AGENTS.md, 2026-10-28: the agent runs it after checking `uptime` and
`pgrep -a make`).  The receipt form of wasm_sdk_probe/tools/build_f168_native_owner.py.

Usage: python3 -I build.py --out DIR      (DIR must not exist)
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCE = 'f176_native.cpp'
BINARY = 'f176-native'


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    out = ap.parse_args().out.resolve()
    if out.exists():
        ap.error('build output must be fresh')
    compiler = shutil.which('g++')
    if not compiler:
        ap.error('g++ unavailable')
    include = ROOT / 'libreoffice-26-8/include'
    headers = {str(p.relative_to(ROOT)): sha(p) for p in sorted((include / 'LibreOfficeKit').glob('*.h*')) if p.is_file()}
    if not headers:
        ap.error('LibreOfficeKit headers missing')
    out.mkdir(parents=True)
    snap = out / 'source'
    snap.mkdir()
    shutil.copyfile(HERE / SOURCE, snap / SOURCE)
    binary = out / BINARY
    command = [compiler, '-std=c++17', '-O2', '-Wall', '-I' + str(include), str(snap / SOURCE), '-ldl', '-lpthread',
               '-o', str(binary)]
    receipt = {'schema': 1, 'source': {str((HERE / SOURCE).relative_to(ROOT)): sha(HERE / SOURCE)},
               'headers': headers, 'argv': command,
               'compiler': {'path': compiler, 'sha256': sha(compiler),
                            'version': subprocess.check_output([compiler, '--version'], text=True)},
               'loadavgBefore': open('/proc/loadavg').read().split()[:3]}
    t0 = time.monotonic()
    with (out / 'build.stdout').open('x') as stdout, (out / 'build.stderr').open('x') as stderr:
        result = subprocess.run(command, stdout=stdout, stderr=stderr)
    receipt['seconds'] = round(time.monotonic() - t0, 2)
    receipt['exitCode'] = result.returncode
    receipt['snapshotMatches'] = sha(snap / SOURCE) == sha(HERE / SOURCE)
    receipt['binary'] = {'path': str(binary), 'sha256': sha(binary)} if binary.is_file() else None
    (out / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('exitCode', 'seconds', 'snapshotMatches', 'binary')}, indent=2))
    return result.returncode or int(not receipt['snapshotMatches'])


if __name__ == '__main__':
    raise SystemExit(main())
