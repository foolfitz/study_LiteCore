#!/usr/bin/env python3
"""Red cases for read_k_0245_merge.py before any counted report exists: the 0.2.26 counted reports as they are must read NOT counted,
and the same reports rebound to K 0.2.45's binding, in a scratch directory, must read counted, and every mutation of that must go red.
The rebinding is what a counted run writes, so it says nothing about behaviour.  Writes merge-on-0226.json, merge-self-test-synthetic.json.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
TOOLS = ROOT / 'wasm_sdk_probe/tools'
OLD = ROOT / 'findings/evidence/release-0.2.26/merge-m2'
proposed = json.loads((HERE.parent / 'k-binding-inventory.json').read_bytes())['proposedMergeBinding']
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOLS))
import k_0244_merge_keying as keying  # noqa: E402

key = keying.read_key(ROOT / 'wasm_sdk_probe/dist/profiles/e2-editor-v29/probe.wasm', b'x-not-in-the-bytes', proposed['wasmSha256'])
key = {**key, 'applied': True, 'table': keying.table_of(key, proposed['wasmSha256'])}


def read(directory, *extra):
    done = subprocess.run([sys.executable, str(TOOLS / 'read_k_0245_merge.py'), '--dir', str(directory), *extra], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


with tempfile.TemporaryDirectory(dir=ROOT / 'wasm_sdk_probe/build') as scratch:
    scratch = Path(scratch)
    code, out, _ = read(OLD)
    (HERE / 'merge-on-0226.json').write_text(out)
    print('0.2.26 as they are: exit', code, 'problems', len(json.loads(out)['problems']))
    for source in OLD.glob('*.json'):
        stem = source.stem
        if stem.startswith('red-'):
            shutil.copy(source, scratch / source.name)
            continue
        if not stem.startswith(('counted-', 'm2-')) or stem.endswith('binding-override'):
            continue
        report = json.loads(source.read_text())
        report.update(counted=True, binding=proposed, bound=dict(proposed))
        report.setdefault('candidate', {})['profile'] = 'e2-editor-v29'
        (scratch / source.name).write_text(json.dumps(report))
        (scratch / (stem + '.stderr.txt')).write_text('')
        (scratch / (source.name + '.binding-override.json')).write_text(json.dumps({'binding': {'applied': True}, 'keying': key}))
    code, out, err = read(scratch)
    print('rebound: exit', code, out[:200].replace('\n', ' '), err[:200])
    code2, out2, err2 = read(scratch, '--self-test')
    (HERE / 'merge-self-test-synthetic.json').write_text(out2 or err2)
    result = json.loads(out2) if out2 else {}
    print('self-test: exit', code2, result.get('selfTest'), len(result.get('results', {})))
raise SystemExit(0 if code == 0 and code2 == 0 else 1)
