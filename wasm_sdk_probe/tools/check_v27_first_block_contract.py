#!/usr/bin/env python3
"""Exact v27 successor delta (SPEC-M3-v27-finding-176 4.4, 5): v26's manifest
with only the profile name and the three bindings changed -- no new export, no
new leaf, every leaf (select-all's three gestures and limits, typedInsert)
equal, editor ABI 6.  The engine change (finding 176) is a define, not a
contract change.

A new file, not an edit of check_v25_feature_contract.py: that one names
e2-editor-v25 and the v24 archive, and v25's evidence binds its behaviour.
This is its text with the names changed -- PROFILE, REFERENCE_PROFILE, the
archive (v26, which has no link of its own: its wasm, loader and export list
are v25's bytes), the base worker pin, WORKER, BUILD_DIR, the error strings --
and DEFINES plus -DOXSDK_E2_V27_FIRST_BLOCK.  Its binary readers (via
check_v23_feature_contract) are imported unchanged.
"""
import argparse
import copy
import json
import shlex
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_v23_diagnostic_build import read_feature_build_log, read_wasm
import check_v23_feature_contract as v23

ROOT = Path(__file__).resolve().parent.parent
PROFILE = 'e2-editor-v27'
REFERENCE_PROFILE = 'e2-editor-v26'
ARCHIVE = ROOT / 'build/archive/e2-editor-v26-44cb15ea-worker-95d6e7ae'
BASE_SHA256 = '95d6e7ae375e60ef58de3e1bbeb838f0d4922a0d4737287b262c23f595aed964'
WORKER = ROOT / 'sdk/v27-first-block-worker.js'
BUILD_DIR = 'build/e2/editor-v27'
DEFINES = ('-DOXSDK_E2_V23_FEATURE_ABI6', '-DOXSDK_E2_V24_TYPED_INSERT', '-DOXSDK_E2_V25_FORMAT_PROOF',
           '-DOXSDK_E2_V27_FIRST_BLOCK')
BINDINGS = v23.BINDINGS
sha = v23.sha


def check_base(path=ARCHIVE / 'sdk-worker.js', pin=BASE_SHA256):
    if Path(path).resolve() != (ARCHIVE / 'sdk-worker.js').resolve() or pin != BASE_SHA256 \
            or sha(Path(path)) != BASE_SHA256:
        raise ValueError('v27 worker base must be the exact archived v26 worker')


def expected_exports():
    return (ARCHIVE / 'exports.txt').read_text().splitlines()


def expected_contract(reference):
    return copy.deepcopy(reference['editorContract'])


def contract_problems(candidate, reference):
    problems = []
    if candidate.get('profile') != PROFILE:
        problems.append('wrong successor identity')
    if reference.get('profile') != REFERENCE_PROFILE:
        problems.append('wrong reference identity')
    got = {k: v for k, v in candidate.get('editorContract', {}).items() if k not in BINDINGS}
    wanted = {k: v for k, v in expected_contract(reference).items() if k not in BINDINGS}
    if got != wanted:
        problems.append('contract differs from v26 (ABI 6, typedInsert, select-all and every other leaf equal)')
    top = copy.deepcopy(reference)
    top.pop('editorContract')
    top['profile'] = PROFILE
    suffix = '+' + reference['profile']
    if not reference['sdkVersion'].endswith(suffix):
        problems.append('reference sdkVersion has no exact profile suffix')
    else:
        top['sdkVersion'] = reference['sdkVersion'][:-len(suffix)] + '+' + PROFILE
    if {k: v for k, v in candidate.items() if k != 'editorContract'} != top:
        problems.append('top-level manifest differs from exact successor identity delta')
    return problems


def input_problems(worker, exports, wasm):
    check_base()
    problems = read_wasm(wasm.read_bytes())
    if worker.read_bytes() != WORKER.read_bytes():
        problems.append('worker differs from sdk/v27-first-block-worker.js')
    if exports.read_text().splitlines() != expected_exports():
        problems.append('exports differ from the v26 archive')
    if any(token in worker.read_bytes() for token in (b'oxsdk_v23_diagnostic', b'v23Diagnostic', b'v23-html-result')):
        problems.append('diagnostic worker entrance present')
    return problems


def actual_export_problems(loader, wasm):
    expected = {n for n in expected_exports() if n.startswith(('_oxsdk_', '_probe_'))}
    archived = {n for n in (ARCHIVE / 'exports.txt').read_text().splitlines() if n.startswith(('_oxsdk_', '_probe_'))}
    try:
        reference = v23.public_binary_exports(ARCHIVE / 'probe.js', ARCHIVE / 'probe.wasm')
        actual = v23.public_binary_exports(loader, wasm)
    except (ValueError, IndexError, UnicodeError) as error:
        return ['actual binary public export validation failed: ' + str(error)]
    if reference != archived:
        return ['archived v26 public loader/binary surface disagrees with its sidecar']
    if actual != expected:
        return ['actual public SDK exports differ: missing=' + repr(sorted(expected - actual))
                + ' extra=' + repr(sorted(actual - expected))]
    return []


def binding_problems(candidate, output):
    return [f'{key} does not bind {filename}' for key, filename in BINDINGS.items()
            if candidate.get('editorContract', {}).get(key) != sha(output / filename)]


def feature_log_problems(text):
    problems = read_feature_build_log(text, BUILD_DIR)
    compiles = []
    for line in text.replace('\\\n', ' ').splitlines():
        if ' -c ' in line and f'-o {BUILD_DIR}/' in line:
            args = shlex.split(line)
            compiles.append(args)
            for define in DEFINES:
                if define not in args:
                    problems.append('v27 object lacks ' + define)
            if any('OXSDK_FINDING_016_SCHEDULER_PROBE' in arg for arg in args):
                problems.append('obsolete scheduler instrumentation present')
    expected = {'src/probe_engine.cpp', 'src/sdk_api.cpp', 'src/editor_api.cpp', 'src/unoembind_stub.cpp'}
    if len(compiles) != 4 or {args[args.index('-c') + 1] for args in compiles} != expected:
        problems.append('v27 record must compile each of the four source units exactly once')
    return problems


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check-worker-base', action='store_true')
    g.add_argument('--manifest', type=Path)
    g.add_argument('--build-log', type=Path)
    p.add_argument('--base-worker', type=Path, default=ARCHIVE / 'sdk-worker.js')
    p.add_argument('--base-worker-sha256', default=BASE_SHA256)
    p.add_argument('--exports', type=Path)
    a = p.parse_args()
    if a.check_worker_base:
        check_base(a.base_worker, a.base_worker_sha256)
        problems = []
    elif a.build_log:
        problems = feature_log_problems(a.build_log.read_text())
    else:
        if not a.exports:
            p.error('--manifest requires --exports')
        candidate = json.loads(a.manifest.read_text())
        reference = json.loads((ARCHIVE / 'sdk-manifest.json').read_text())
        problems = (contract_problems(candidate, reference) + binding_problems(candidate, a.manifest.parent)
                    + input_problems(a.manifest.parent / 'sdk-worker.js', a.exports, a.manifest.parent / 'probe.wasm')
                    + actual_export_problems(a.manifest.parent / 'probe.js', a.manifest.parent / 'probe.wasm'))
    for problem in problems:
        print(problem)
    print('v27 preconditions hold' if not problems else 'v27 preconditions failed')
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
