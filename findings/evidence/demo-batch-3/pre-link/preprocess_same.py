#!/usr/bin/env python3
"""SPEC-P-demo-batch-3: a build without the new defines is the build it was.  em++ -E -P on the v29 and ods-editor-v2 compile lines, on
src/ at 46cf3eaf2 (before this batch's engine work) and on the tree: the preprocessed text must be equal, unit by unit.  A positive
control: the v31 unit with its define must differ.  taskset -c 0.  Run from anywhere.
"""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
import io
import tempfile

ROOT = Path(__file__).resolve().parents[4]
SDK = ROOT / 'wasm_sdk_probe'
BASE = '46cf3eaf2'


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
        if token.startswith('-Oz') or token == '-pthread' and False:
            pass
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
        for obj in ['build/e2/editor-v29/' + u + '.o' for u in ('sdk_api', 'probe_engine', 'unoembind_stub', 'editor_api')] + \
                   ['build/ods/editor-v2/' + u + '.o' for u in ('sdk_api', 'probe_engine', 'unoembind_stub', 'calc_cell_bridge')]:
            argv = compile_line(obj)
            before, after = preprocess(argv, old), preprocess(argv, SDK / 'src')
            rows.append({'unit': obj, 'exit': [before[0], after[0]], 'bytes': [before[2], after[2]], 'equal': before[1] == after[1],
                         'stderr': before[3] + after[3]})
        control = compile_line('build/e2/editor-v31/probe_engine.o')
        c_before, c_after = preprocess(control, old), preprocess(control, SDK / 'src')
        rows.append({'unit': 'control: v31 line, must differ', 'exit': [c_before[0], c_after[0]], 'bytes': [c_before[2], c_after[2]],
                     'equal': c_before[1] == c_after[1]})
    held = all(r['equal'] and r['exit'] == [0, 0] for r in rows[:-1]) and not rows[-1]['equal'] and rows[-1]['exit'] == [0, 0]
    report = {'base': BASE, 'verdict': 'SAME_HOLDS' if held else 'SAME_RED', 'rows': rows}
    (Path(__file__).resolve().parent / 'preprocess-same.json').write_text(json.dumps(report, indent=1) + '\n')
    print(report['verdict'], [(r['unit'].split('/')[-2:] , r['equal'], r['bytes'][1], r['exit']) for r in rows])


if __name__ == '__main__':
    main()
