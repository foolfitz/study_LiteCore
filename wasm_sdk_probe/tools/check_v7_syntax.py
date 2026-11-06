#!/usr/bin/env python3
"""SPEC-P-calc-copy, before the ods-editor-v7 link: em++ -fsyntax-only on the four objects `make ods-editor-v7-dev` compiles,
with the Makefile's own command lines (from `make -n`), each `-c SRC -o OBJ` replaced by `-fsyntax-only SRC`.  No object is
written.  Positive control (AGENTS.md, 2026-10-28): a copy of calc_cell_bridge.cpp and of sdk_api.cpp with an error placed
inside their `#ifdef OXSDK_ODS_COPY` block must FAIL with the same flags -- otherwise a green would only mean the copy code was
never compiled.  Refuses when a make is running; pins to one core.  Receipt: receipt.json in --out (argv, exit, seconds, tail of
stderr per command).

  check_v7_syntax.py --out NEW_DIR
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

SDK = Path(__file__).resolve().parents[1]
MARK = {'src/calc_cell_bridge.cpp': '#ifdef OXSDK_ODS_COPY\n// SPEC-P-calc-copy 3.1',
        'src/sdk_api.cpp': '#ifdef OXSDK_ODS_COPY\n         | OXSDK_CAPABILITY_CELL_COPY'}


def run(argv, out, name):
    started = time.monotonic()
    proc = subprocess.run(['taskset', '-c', '0', *argv], cwd=SDK, capture_output=True, text=True)
    (out / f'{name}.stderr.txt').write_text(proc.stderr)
    return {'name': name, 'argv': argv, 'exit': proc.returncode, 'seconds': round(time.monotonic() - started, 2),
            'stderrTail': proc.stderr[-600:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    makes = subprocess.run(['pgrep', '-a', 'make'], capture_output=True, text=True).stdout.strip()
    if makes:
        raise SystemExit(f'a make is running, not checking: {makes}')
    uptime = subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip()
    plan = subprocess.run(['make', '-n', 'ods-editor-v7-dev'], cwd=SDK, capture_output=True, text=True, check=True).stdout
    (out / 'make-n.txt').write_text(plan)
    compiles = {}
    for line in plan.replace('\\\n', ' ').splitlines():  # make -n keeps a recipe's backslash continuations
        match = re.search(r' -c (src/\S+\.cpp) -o (\S+\.o)$', line)
        if match:
            compiles[match.group(1)] = shlex.split(line[:match.start()]) + ['-fsyntax-only', match.group(1)]
    if len(compiles) != 4 or not set(MARK) <= set(compiles):
        raise SystemExit(f'expected four compiles including {sorted(MARK)}, make -n planned {sorted(compiles)}')
    steps = [run(argv, out, Path(src).stem) for src, argv in compiles.items()]
    controls = []
    for src, mark in MARK.items():
        text = (SDK / src).read_text()
        if text.count(mark) != 1:
            raise SystemExit(f'the control mark is not unique in {src}')
        broken = out / f'control-{Path(src).name}'
        broken.write_text(text.replace(mark, mark.replace('#ifdef OXSDK_ODS_COPY\n',
                                                          '#ifdef OXSDK_ODS_COPY\n#error positive control: the copy block is compiled\n')))
        argv = [a if a != src else str(broken) for a in compiles[src]] + ['-I', 'src']
        controls.append(run(argv, out, f'control-{Path(src).stem}'))
    receipt = {'argv': ['check_v7_syntax.py', '--out', str(args.out)], 'uptime': uptime, 'makes': makes, 'compiles': steps,
               'controls': controls,
               'green': all(s['exit'] == 0 for s in steps),
               'controlsRed': all(c['exit'] != 0 and 'positive control' in c['stderrTail'] for c in controls)}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps({'green': receipt['green'], 'controlsRed': receipt['controlsRed'],
                      'seconds': [s['seconds'] for s in steps + controls], 'files': sorted(compiles)}))
    return 0 if receipt['green'] and receipt['controlsRed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
