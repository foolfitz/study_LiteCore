#!/usr/bin/env python3
"""V0-v25 (SPEC-M3-link-batch-v25 6.1): v23 and v24 preprocess exactly as before the v25 edits.

  v0_preprocess.py <baseline-commit> [--mutate]

For every source of the v23-feature and v24 objects, the Makefile's own compile line
(`make -n -B <object>`, joined) is re-run as `-E -P` on the working tree and on
`git archive <baseline> wasm_sdk_probe/src` (headers resolve beside each source, so
the baseline sees only its own src/).  Comparison as the v23 receipt did it:
nonblank lines, trailing whitespace removed.  --mutate is the positive control:
it injects one changed token into a shared, unguarded line of a copy of the
current src/ and must make the v24 probe_engine row differ.
"""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import io
import tempfile

ROOT = Path(__file__).resolve().parents[4]
SDK = ROOT / 'wasm_sdk_probe'
SOURCES = ['sdk_api.cpp', 'probe_engine.cpp', 'unoembind_stub.cpp', 'editor_api.cpp']
VARIANTS = ['editor-v23', 'editor-v24']


def compile_line(obj):
    text = subprocess.run(['make', '-n', '-B', obj], cwd=SDK, capture_output=True, text=True, check=True).stdout
    joined = text.replace('\\\n', ' ')
    lines = [l for l in joined.splitlines() if 'em++' in l and ' -c ' in l and obj in l]
    if len(lines) != 1:
        raise SystemExit(f'expected one compile line for {obj}, found {len(lines)}')
    return shlex.split(lines[0])


def preprocess(argv, src_dir):
    out = []
    skip = False
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
            token = str(src_dir / token[len('src/'):])
        out.append(token)
    run = subprocess.run(['taskset', '-c', '0', *out, '-E', '-P'], cwd=SDK, capture_output=True, text=True)
    if run.returncode:
        return None, run.stderr[-2000:]
    body = '\n'.join(l.rstrip() for l in run.stdout.splitlines() if l.strip())
    return hashlib.sha256(body.encode()).hexdigest(), ''


def main():
    baseline = sys.argv[1]
    mutate = '--mutate' in sys.argv
    resolved = subprocess.run(['git', 'rev-parse', baseline], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='v0-v25-') as directory:
        base = Path(directory) / 'base'
        tar = subprocess.run(['git', 'archive', resolved, 'wasm_sdk_probe/src'], cwd=ROOT, capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as archive:
            archive.extractall(base, filter='data')
        base_src = base / 'wasm_sdk_probe/src'
        current_src = SDK / 'src'
        if mutate:
            current_src = Path(directory) / 'mutated-src'
            shutil.copytree(SDK / 'src', current_src)
            engine = current_src / 'probe_engine.cpp'
            text = engine.read_text()
            needle = 'bool formatBarrierActive() {\n  return gFormatBarrier.target != FormatBarrierTarget::None;'
            if text.count(needle) != 1:
                raise SystemExit('positive-control anchor moved')
            engine.write_text(text.replace(needle, needle.replace('!= FormatBarrierTarget::None', '!= FormatBarrierTarget::None && true')))
        rows = []
        for variant in VARIANTS:
            for source in SOURCES:
                obj = f'build/e2/{variant}/{source[:-4]}.o'
                argv = compile_line(obj)
                current, cerr = preprocess(argv, current_src)
                prior, perr = preprocess(argv, base_src)
                rows.append({'object': obj, 'current': current, 'prior': prior, 'equal': current is not None and current == prior,
                             'errors': [e for e in (cerr, perr) if e]})
    verdict = all(r['equal'] for r in rows)
    record = {'baselineCommit': resolved, 'mutate': mutate,
              'comparison': 'nonblank preprocessed lines, trailing whitespace removed; actual Makefile compile lines, -E -P only',
              'rows': rows, 'verdict': 'V0_V25_HOLDS' if verdict else 'V0_V25_DIFFERS'}
    print(json.dumps(record, indent=1))
    return 0 if verdict else 1


if __name__ == '__main__':
    raise SystemExit(main())
