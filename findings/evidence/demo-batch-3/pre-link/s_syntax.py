#!/usr/bin/env python3
"""E1 (SPEC-P-demo-batch-3 section 3): em++ -fsyntax-only on the compile lines the owner's link will use.

Derived from findings/evidence/v28-083/pre-link/s_syntax.py.  Rows: each e2-editor-v31 and ods-editor-v3 source (must be clean).
Positive controls: a deliberate error in a copy of src/, inside a block only the new define compiles, must fail WITH the define and
pass WITHOUT it, so "clean" means the new code was compiled; the v31 define without the ABI6 define must hit editor_api.h's #error.
taskset -c 0; argv, exit, seconds and the error tail are recorded per row.
"""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
SDK = ROOT / 'wasm_sdk_probe'
OUT = Path(__file__).resolve().parent
V31, STYLE = '-DOXSDK_E2_V31_ALIGNMENT', '-DOXSDK_ODS_STYLE'


def compile_line(obj):
    text = subprocess.run(['make', '-n', '-B', obj], cwd=SDK, capture_output=True, text=True, check=True).stdout
    lines = [l for l in text.replace('\\\n', ' ').splitlines() if 'em++' in l and ' -c ' in l and obj in l]
    assert len(lines) == 1, (obj, len(lines))
    return shlex.split(lines[0])


def syntax(argv, src_dir, drop=()):
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
    full = ['taskset', '-c', '0', *out, '-fsyntax-only']
    started = time.monotonic()
    run = subprocess.run(full, cwd=SDK, capture_output=True, text=True)
    return {'argvTail': full[-6:], 'exit': run.returncode, 'seconds': round(time.monotonic() - started, 2), 'stderrTail': run.stderr[-600:]}




def main():
    rows = []
    for source in ('sdk_api', 'probe_engine', 'unoembind_stub', 'editor_api'):
        rows.append({'row': f'v31 {source}', **syntax(compile_line(f'build/e2/editor-v31/{source}.o'), SDK / 'src')})
    for source in ('sdk_api', 'probe_engine', 'unoembind_stub', 'calc_cell_bridge'):
        rows.append({'row': f'ods-v3 {source}', **syntax(compile_line(f'build/ods/editor-v3/{source}.o'), SDK / 'src')})
    engine = compile_line('build/e2/editor-v31/probe_engine.o')
    bridge = compile_line('build/ods/editor-v3/calc_cell_bridge.o')
    with tempfile.TemporaryDirectory(prefix='s-demo3-') as directory:
        src = Path(directory) / 'src'
        shutil.copytree(SDK / 'src', src)
        inc = src / 'ordered_format.inc'
        text = inc.read_text()
        anchor = '  gFormatBarrier.alignCaretRead = true;\n'
        assert text.count(anchor) == 1
        inc.write_text(text.replace(anchor, anchor + '  this_symbol_does_not_exist_v31();\n'))
        rows.append({'row': 'control: v31-only error, with define', **syntax(engine, src)})
        rows.append({'row': 'control: v31-only error, without define', **syntax(engine, src, drop=[V31])})
        cell = src / 'calc_cell_bridge.cpp'
        text = cell.read_text()
        anchor = '  const OUString name = OUString::createFromAscii(styleProperty(operation));\n'
        assert text.count(anchor) == 1
        cell.write_text(text.replace(anchor, anchor + '  this_symbol_does_not_exist_style();\n'))
        rows.append({'row': 'control: style-only error, with define', **syntax(bridge, src)})
        rows.append({'row': 'control: style-only error, without define', **syntax(bridge, src, drop=[STYLE])})
    api = compile_line('build/e2/editor-v31/editor_api.o')
    rows.append({'row': 'control: v31 define without ABI6 (editor_api.cpp)',
                 **syntax(api, SDK / 'src', drop=['-DOXSDK_E2_V23_FEATURE_ABI6'])})
    clean = all(r['exit'] == 0 for r in rows[:8])
    controls = (rows[8]['exit'] != 0 and 'this_symbol_does_not_exist_v31' in rows[8]['stderrTail'] and rows[9]['exit'] == 0
                and rows[10]['exit'] != 0 and 'this_symbol_does_not_exist_style' in rows[10]['stderrTail'] and rows[11]['exit'] == 0
                and rows[12]['exit'] != 0)
    report = {'clean': clean, 'controls': controls, 'verdict': 'E1_HOLDS' if clean and controls else 'E1_RED', 'rows': rows}
    (OUT / 'syntax.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'], [(r['row'], r['exit'], r['seconds']) for r in rows])


if __name__ == '__main__':
    main()
