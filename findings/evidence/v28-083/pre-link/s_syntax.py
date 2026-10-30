#!/usr/bin/env python3
"""S (SPEC-M3-v28-last-line-fallback 7.2): em++ -fsyntax-only on the v27 compile line plus the v28 define.

Derived from findings/evidence/v27-176/pre-link/s_syntax.py (base line v25 -> v27, define v27 -> v28,
control (1) moved to a v28-only block of ordered_format.inc, control (2) drops the v27 define).

Rows: each v27 source with -DOXSDK_E2_V28_LAST_BLOCK (must be clean).  Positive controls:
(1) a copy of src/ with a deliberate error inside a v28-only block of ordered_format.inc
must fail WITH the define and pass WITHOUT it (so "clean" means the v28 code was compiled);
(2) the v28 define without -DOXSDK_E2_V27_FIRST_BLOCK must hit editor_api.h's #error.
taskset -c 0; argv, exit, seconds and the error tail are recorded per row.
"""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
SDK = ROOT / 'wasm_sdk_probe'
SOURCES = ['sdk_api.cpp', 'probe_engine.cpp', 'unoembind_stub.cpp', 'editor_api.cpp']
V28 = '-DOXSDK_E2_V28_LAST_BLOCK'


def compile_line(obj):
    text = subprocess.run(['make', '-n', '-B', obj], cwd=SDK, capture_output=True, text=True, check=True).stdout
    lines = [l for l in text.replace('\\\n', ' ').splitlines() if 'em++' in l and ' -c ' in l and obj in l]
    assert len(lines) == 1, obj
    return shlex.split(lines[0])


def syntax(argv, src_dir, add=(), drop=()):
    out, skip = [], False
    for token in argv:
        if skip:
            skip = False
            continue
        if token == '-c' or token in drop:
            continue
        if token == '-o':
            skip = True
            continue
        if token.startswith('src/') and token.endswith('.cpp'):
            token = str(src_dir / token[len('src/'):])
        out.append(token)
    full = ['taskset', '-c', '0', *out, *add, '-fsyntax-only']
    started = time.monotonic()
    run = subprocess.run(full, cwd=SDK, capture_output=True, text=True)
    return {'argvTail': full[-6:], 'exit': run.returncode, 'seconds': round(time.monotonic() - started, 2),
            'stderrTail': run.stderr[-600:]}


def main():
    rows = []
    for source in SOURCES:
        argv = compile_line(f'build/e2/editor-v27/{source[:-4]}.o')
        rows.append({'row': f'v28 {source}', **syntax(argv, SDK / 'src', add=[V28])})
    engine_argv = compile_line('build/e2/editor-v27/probe_engine.o')
    with tempfile.TemporaryDirectory(prefix='s-v28-') as directory:
        broken = Path(directory) / 'src'
        shutil.copytree(SDK / 'src', broken)
        inc = broken / 'ordered_format.inc'
        text = inc.read_text()
        anchor = '      const SelectionReadback stepBack = readSelection();\n'
        assert text.count(anchor) == 1
        inc.write_text(text.replace(anchor, anchor + '      this_symbol_does_not_exist_v28();\n'))
        rows.append({'row': 'control: v28-only error, with define', **syntax(engine_argv, broken, add=[V28])})
        rows.append({'row': 'control: v28-only error, without define', **syntax(engine_argv, broken)})
    # The guard lives in editor_api.h, which only editor_api.cpp includes (as v24's does); run 01
    # aimed this control at probe_engine.cpp and it stayed green -- the control was wrong, not the guard.
    api_argv = compile_line('build/e2/editor-v27/editor_api.o')
    rows.append({'row': 'control: v28 define without v27 (editor_api.cpp)',
                 **syntax(api_argv, SDK / 'src', add=[V28], drop=['-DOXSDK_E2_V27_FIRST_BLOCK'])})
    clean = all(r['exit'] == 0 for r in rows[:4])
    controls = (rows[4]['exit'] != 0 and 'this_symbol_does_not_exist_v28' in rows[4]['stderrTail']
                and rows[5]['exit'] == 0
                and rows[6]['exit'] != 0 and 'requires the v27 first-block engine' in rows[6]['stderrTail'])
    verdict = 'S_V28_HOLDS' if clean and controls else 'S_V28_FAILS'
    print(json.dumps({'verdict': verdict, 'clean': clean, 'controlsBehave': controls, 'rows': rows}, indent=1))
    return 0 if verdict == 'S_V28_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
