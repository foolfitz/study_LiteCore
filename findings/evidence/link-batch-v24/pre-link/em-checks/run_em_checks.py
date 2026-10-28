#!/usr/bin/env python3
"""Run the v24 pre-link em++ checks (owner-authorized 2026-10-28) and keep receipts.

  run_em_checks.py syntax          four -fsyntax-only compiles, derived from the
                                   v24 dry run (../s3/dry-run.log): `-c` and `-o OBJ`
                                   removed, `-fsyntax-only` added, `taskset -c 0`
  run_em_checks.py m1-1 LABEL      the M1-1 scope check exactly as `make -n
                                   test-e2-c-static` prints it from the current Makefile
  run_em_checks.py ships           what_the_link_ships.py --since dcffd17d (the tree
                                   v23 was linked from) --variant link-batch-v24

Run from wasm_sdk_probe/.  Nothing here emits an object or runs make other than
`make -n`.  Each step appends to commands.json and writes STEP.stdout/.stderr.
"""
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE.parents[4] / 'wasm_sdk_probe'
LEDGER = HERE / 'commands.json'


def run(name, argv):
    started = time.time()
    done = subprocess.run(argv, cwd=PROBE, capture_output=True, text=True)
    record = {'name': name, 'argv': argv, 'cwd': 'wasm_sdk_probe', 'exitCode': done.returncode,
              'seconds': round(time.time() - started, 1),
              'startedAt': time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(started))}
    (HERE / f'{name}.stdout.txt').write_text(done.stdout)
    (HERE / f'{name}.stderr.txt').write_text(done.stderr)
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
    ledger.append(record)
    LEDGER.write_text(json.dumps(ledger, indent=1) + '\n')
    print(name, 'exit', done.returncode, f"{record['seconds']}s")
    return done


def preflight(step):
    run(f'{step}-uptime', ['uptime'])
    busy = run(f'{step}-make-processes', ['pgrep', '-a', 'make'])
    if busy.returncode == 0:
        raise SystemExit('another make is running; stop and ask')


def syntax():
    preflight('syntax')
    text = (HERE.parent / 's3/dry-run.log').read_text().replace('\\\n', ' ')
    compiles = [shlex.split(line) for line in text.splitlines()
                if ' -c ' in line and '-o build/e2/editor-v24/' in line]
    if len(compiles) != 4:
        raise SystemExit(f'expected four v24 compile lines, found {len(compiles)}')
    for argv in compiles:
        c = argv.index('-c')
        source, obj = argv[c + 1], argv[argv.index('-o') + 1]
        o = argv.index('-o')
        derived = ['taskset', '-c', '0', argv[0], '-fsyntax-only'] + \
            [a for i, a in enumerate(argv[1:], 1) if i not in (c, o, o + 1)]
        assert source in derived and obj not in derived and '-c' not in derived[3:]
        run('syntax-' + Path(source).stem, derived)


def m1_1(label):
    preflight('m1-1-' + label)
    printed = subprocess.run(['make', '-n', 'test-e2-c-static'], cwd=PROBE, capture_output=True, text=True, check=True)
    lines = [line for line in printed.stdout.replace('\\\n', ' ').splitlines() if 'check_merge_key_undo_scope.py' in line]
    if len(lines) != 1:
        raise SystemExit(f'expected one M1-1 line, found {len(lines)}')
    run('m1-1-' + label, ['taskset', '-c', '0'] + shlex.split(lines[0]))


def ships():
    preflight('ships')
    run('ships', ['taskset', '-c', '0', 'python3', 'tools/what_the_link_ships.py', '--since', 'dcffd17d',
                  '--variant', 'link-batch-v24', '--shipped-profile', 'dist/profiles/e2-editor-v23', '--json'])


if __name__ == '__main__':
    step = sys.argv[1]
    {'syntax': syntax, 'ships': ships}.get(step, lambda: m1_1(sys.argv[2]))()
