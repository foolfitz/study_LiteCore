#!/usr/bin/env python3
"""E1 of research/RESEARCH-2026-11-04-calc-row-column-headers.md section 7.2: `.uno:ViewRowColumnHeaders` on the native 26.8 core,
through the existing harness build/calc-range-native/calc-cell-native (no build), on a fresh copy of cell-editing.ods.

Questions: the reply's shape under the bridge's client zoom (op 0 sets it); whether reading headers moves the cell cursor; whether
header px x 15 equals the cursor's twips far down (row 1000); the empty and one-axis rectangles; ms per call.
One request at a time, timed.  Writes only into this directory (or --out).

  python3 -I run_e1.py [--out DIR]
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SDK = ROOT / 'wasm_sdk_probe'
CORE = ROOT / 'build-native-26-8/instdir/program'
HARNESS = SDK / 'build/calc-range-native/calc-cell-native'
sys.path.insert(0, str(SDK / 'tools'))
from create_calc_edit_fixture import create  # noqa: E402

H = '.uno:ViewRowColumnHeaders'
REQUESTS = [
    ('cursor-initial', {'action': 'command-values', 'command': '.uno:CellCursor'}),
    ('op0-A1', {'operation': 0, 'part': 0, 'column': 0, 'row': 0}),
    ('cursor-after-op0', {'action': 'command-values', 'command': '.uno:CellCursor'}),
    ('headers-full', {'action': 'command-values', 'command': f'{H}?x=0&y=0&width=15000&height=6000'}),
    ('cursor-after-full', {'action': 'command-values', 'command': '.uno:CellCursor'}),
    ('headers-columns-only', {'action': 'command-values', 'command': f'{H}?x=0&y=0&width=15000&height=0'}),
    ('headers-empty', {'action': 'command-values', 'command': f'{H}?x=0&y=0&width=0&height=0'}),
    ('headers-row-1000', {'action': 'command-values', 'command': f'{H}?x=0&y=254000&width=15000&height=6000'}),
    ('cursor-after-row-1000', {'action': 'command-values', 'command': '.uno:CellCursor'}),
    ('headers-full-again', {'action': 'command-values', 'command': f'{H}?x=0&y=0&width=15000&height=6000'}),
    ('op0-A1000', {'operation': 0, 'part': 0, 'column': 0, 'row': 999}),
    ('op0-E1', {'operation': 0, 'part': 0, 'column': 4, 'row': 0}),
    ('op0-A5', {'operation': 0, 'part': 0, 'column': 0, 'row': 4}),
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=HERE / 'run-01')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = create(out / 'fixture')
    profile = out / 'profile'
    profile.mkdir()
    env = {**os.environ, 'SAL_USE_VCLPLUGIN': 'svp'}
    receipt = {'tool': {'path': str(Path(__file__).relative_to(ROOT)), 'sha256': sha(__file__), 'argv': sys.argv[1:]},
               'harness': {'path': str(HARNESS.relative_to(ROOT)), 'sha256': sha(HARNESS),
                           'bridgeObjectSha256': sha(HARNESS.parent / 'bridge.o'),
                           'bridgeObjectMtime': os.path.getmtime(HARNESS.parent / 'bridge.o'),
                           'bridgeSourceSha256Now': sha(SDK / 'src/calc_cell_bridge.cpp')},
               'fixture': {'path': str(fixture.relative_to(ROOT)), 'sha256': sha(fixture)},
               'uptime': subprocess.check_output(['uptime'], text=True).strip()}
    started = time.monotonic()
    proc = subprocess.Popen([str(HARNESS), str(CORE), profile.as_uri(), fixture.as_uri()], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=open(out / 'stderr.txt', 'w'), text=True, env=env)
    rows = []
    try:
        for name, request in REQUESTS:
            t0 = time.monotonic()
            proc.stdin.write(json.dumps(request, ensure_ascii=False) + '\n'); proc.stdin.flush()
            line = proc.stdout.readline()
            ms = round((time.monotonic() - t0) * 1000, 2)
            try:
                reply = json.loads(line)
            except json.JSONDecodeError:
                reply = {'unparsed': line}
            rows.append({'name': name, 'request': request, 'ms': ms, 'reply': reply})
    finally:
        proc.stdin.close()
        receipt['exit'] = proc.wait(timeout=60)
        receipt['seconds'] = round(time.monotonic() - started, 2)
    (out / 'observations.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n')
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({'exit': receipt['exit'], 'replies': len(rows), 'seconds': receipt['seconds']}))
    return receipt['exit']


if __name__ == '__main__':
    raise SystemExit(main())
