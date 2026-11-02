#!/usr/bin/env python3
"""Exact v32 successor delta (SPEC-P-demo-batch-4): v31's manifest with the profile name, the three bindings and six appended actions
(wire ids 28-33); every inherited leaf equal, editor ABI 6, the worker sdk/v32-paragraph-read-worker.js.

Derived from check_v31_alignment_contract.py.  The build log carries five units now: the Writer caret bridge is new, and it alone
compiles with the internal-only define.
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
PROFILE = 'e2-editor-v32'
REFERENCE_PROFILE = 'e2-editor-v31'
ARCHIVE = ROOT / 'build/archive/e2-editor-v31-809893a9-worker-54352fad'
BASE_SHA256 = '54352fad3f5434162512d20e64e655a9cce789629495a74cbbe4c8a34e41637e'
WORKER = ROOT / 'sdk/v32-paragraph-read-worker.js'
BUILD_DIR = 'build/e2/editor-v32'
DEFINES = ('-DOXSDK_E2_V23_FEATURE_ABI6', '-DOXSDK_E2_V24_TYPED_INSERT', '-DOXSDK_E2_V25_FORMAT_PROOF',
           '-DOXSDK_E2_V27_FIRST_BLOCK', '-DOXSDK_E2_V28_LAST_BLOCK', '-DOXSDK_E2_V29_TICK_PACING',
           '-DOXSDK_E2_V31_ALIGNMENT', '-DOXSDK_E2_V32_PARAGRAPH_READ')
NEW_ACTIONS = {name: {'id': wire, 'gestures': ['collapsed', 'range-single', 'range-cross'],
                      'limits': ['no-note-paragraphs', 'not-characterised-in-tables']}
               for name, wire in (('toggle-heading-1', 28), ('toggle-heading-2', 29), ('toggle-heading-3', 30),
                                  ('toggle-heading-4', 31), ('toggle-list-unordered', 32), ('toggle-list-ordered', 33))}
BINDINGS = v23.BINDINGS
sha = v23.sha


def check_base(path=ARCHIVE / 'sdk-worker.js', pin=BASE_SHA256):
    if Path(path).resolve() != (ARCHIVE / 'sdk-worker.js').resolve() or pin != BASE_SHA256 \
            or sha(Path(path)) != BASE_SHA256:
        raise ValueError('v32 worker base must be the exact archived v31 worker')


def expected_exports():
    return (ARCHIVE / 'exports.txt').read_text().splitlines()


def expected_contract(reference):
    contract = copy.deepcopy(reference['editorContract'])
    contract['actions'].update(copy.deepcopy(NEW_ACTIONS))
    return contract


def contract_problems(candidate, reference):
    problems = []
    if candidate.get('profile') != PROFILE:
        problems.append('wrong successor identity')
    if reference.get('profile') != REFERENCE_PROFILE:
        problems.append('wrong reference identity')
    got = {k: v for k, v in candidate.get('editorContract', {}).items() if k not in BINDINGS}
    wanted = {k: v for k, v in expected_contract(reference).items() if k not in BINDINGS}
    if got != wanted:
        problems.append('contract differs from v31 plus the six toggles (ABI 6, every inherited leaf equal)')
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
        problems.append('worker differs from sdk/v32-paragraph-read-worker.js')
    if exports.read_text().splitlines() != expected_exports():
        problems.append('exports differ from the v31 archive')
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
        return ['archived v31 public loader/binary surface disagrees with its sidecar']
    if actual != expected:
        return ['actual public SDK exports differ: missing=' + repr(sorted(expected - actual))
                + ' extra=' + repr(sorted(actual - expected))]
    return []


def binding_problems(candidate, output):
    return [f'{key} does not bind {filename}' for key, filename in BINDINGS.items()
            if candidate.get('editorContract', {}).get(key) != sha(output / filename)]


def feature_log_problems(text):
    # The bridge carries no engine define, on purpose: it sees none of the engine's headers.
    engine = '\n'.join(line for line in text.replace('\\\n', ' ').splitlines() if 'src/writer_caret_bridge.cpp' not in line)
    problems = read_feature_build_log(engine, BUILD_DIR)
    compiles = []
    for line in text.replace('\\\n', ' ').splitlines():
        if ' -c ' in line and f'-o {BUILD_DIR}/' in line:
            args = shlex.split(line)
            compiles.append(args)
            bridge = 'src/writer_caret_bridge.cpp' in args
            for define in DEFINES:
                if not bridge and define not in args:
                    problems.append('v32 object lacks ' + define)
            if bridge != ('-DLIBO_INTERNAL_ONLY' in args):
                problems.append('only the caret bridge compiles with the internal-only define')
            if any('OXSDK_FINDING_016_SCHEDULER_PROBE' in arg for arg in args):
                problems.append('obsolete scheduler instrumentation present')
    expected = {'src/probe_engine.cpp', 'src/sdk_api.cpp', 'src/editor_api.cpp', 'src/unoembind_stub.cpp',
                'src/writer_caret_bridge.cpp'}
    if len(compiles) != 5 or {args[args.index('-c') + 1] for args in compiles} != expected:
        problems.append('v32 record must compile each of the five source units exactly once')
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
    print('v32 preconditions hold' if not problems else 'v32 preconditions failed')
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
