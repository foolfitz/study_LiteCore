#!/usr/bin/env python3
"""SPEC-P-demo-batch-4: a build without the new define is the build it was.  em++ -E -P on the v31, v29 and ods-editor-v3 compile lines, on
src/ at f3204745e (before this batch's engine work) and on the tree: the preprocessed text must be equal, unit by unit.  A positive
control: the v32 unit with its define must differ.  taskset -c 0.  Run from anywhere.
"""
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[4]
SDK = ROOT / 'wasm_sdk_probe'
OUT = Path(__file__).resolve().parent
BASE = 'f3204745e'


def compile_line(obj):
    text = subprocess.run(['make', '-n', '-B', obj], cwd=SDK, capture_output=True, text=True, check=True).stdout
    lines = [l for l in text.replace('\\\n', ' ').splitlines() if 'em++' in l and ' -c ' in l and obj in l]
    assert len(lines) == 1, (obj, len(lines))
    return shlex.split(lines[0])


def preprocess(argv, src):
    out, skip = [], False
    for token in argv:
        if skip:
            skip = False
            continue
        if token == '-c':
            continue
        if token == '-o':
            skip = True
            continue
        if token.startswith('src/') and token.endswith('.cpp'):
            token = str(src / token[len('src/'):])
        out.append(token)
    full = ['taskset', '-c', '0', *out, '-E', '-P', '-I' + str(src)]
    run = subprocess.run(full, cwd=SDK, capture_output=True)
    return run.returncode, hashlib.sha256(run.stdout).hexdigest(), len(run.stdout), run.stderr[-300:].decode(errors='replace')


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix='pp-base-') as directory:
        tar = subprocess.run(['git', '-C', str(ROOT), 'archive', BASE, 'wasm_sdk_probe/src'], capture_output=True, check=True).stdout
        tarfile.open(fileobj=io.BytesIO(tar)).extractall(directory, filter='data')
        old = Path(directory) / 'wasm_sdk_probe/src'
        units = [f'build/e2/editor-{p}/{u}.o' for p in ('v31', 'v29') for u in ('sdk_api', 'probe_engine', 'unoembind_stub', 'editor_api')] + \
                ['build/ods/editor-v3/' + u + '.o' for u in ('sdk_api', 'probe_engine', 'unoembind_stub', 'calc_cell_bridge')]
        for obj in units:
            argv = compile_line(obj)
            before, after = preprocess(argv, old), preprocess(argv, SDK / 'src')
            rows.append({'unit': obj, 'exit': [before[0], after[0]], 'bytes': [before[2], after[2]], 'equal': before[1] == after[1], 'stderr': before[3] + after[3]})
        argv = compile_line('build/e2/editor-v32/probe_engine.o')
        before, after = preprocess(argv, old), preprocess(argv, SDK / 'src')
        control = {'unit': 'control: v32 probe_engine, its define on the old and the new source', 'exit': [before[0], after[0]], 'bytes': [before[2], after[2]],
                   'differs': before[1] != after[1]}
    held = all(r['equal'] and r['exit'] == [0, 0] for r in rows) and control['differs']
    report = {'base': BASE, 'verdict': 'SAME_HOLDS' if held else 'SAME_RED', 'rows': rows, 'control': control}
    (OUT / 'preprocess-same.json').write_text(json.dumps(report, indent=1) + '\n')
    print(report['verdict'], [(r['unit'], r['equal']) for r in rows if not r['equal']], control['differs'])


if __name__ == '__main__':
    main()
