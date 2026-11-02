#!/usr/bin/env python3
"""Exact v31 successor delta (SPEC-P-demo-batch-3 3.2): v30's manifest with the profile name, the three bindings and four appended
actions (wire ids 24-27); every inherited leaf equal, editor ABI 6, the worker sdk/v31-alignment-worker.js.

Derived from check_v30_extend_gate_contract.py.  The engine is a new link, so identical_engine_problems is gone and the build log is
read as check_v29_tick_pacing_contract reads it, with -DOXSDK_E2_V31_ALIGNMENT among the defines.
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
PROFILE = 'e2-editor-v31'
REFERENCE_PROFILE = 'e2-editor-v30'
ARCHIVE = ROOT / 'build/archive/e2-editor-v30-e61e5890-worker-464d129c'
BASE_SHA256 = '464d129c044231c516c666487db32e78f33d3f6393d2afdcc089d36bb0f0fe93'
WORKER = ROOT / 'sdk/v31-alignment-worker.js'
BUILD_DIR = 'build/e2/editor-v31'
DEFINES = ('-DOXSDK_E2_V23_FEATURE_ABI6', '-DOXSDK_E2_V24_TYPED_INSERT', '-DOXSDK_E2_V25_FORMAT_PROOF',
           '-DOXSDK_E2_V27_FIRST_BLOCK', '-DOXSDK_E2_V28_LAST_BLOCK', '-DOXSDK_E2_V29_TICK_PACING',
           '-DOXSDK_E2_V31_ALIGNMENT')
NEW_ACTIONS = {name: {'id': wire, 'gestures': ['collapsed', 'range-single', 'range-cross'],
                      'limits': ['no-note-paragraphs', 'not-characterised-in-tables']}
               for name, wire in (('set-align-left', 24), ('set-align-center', 25),
                                  ('set-align-right', 26), ('set-align-justify', 27))}
BINDINGS = v23.BINDINGS
sha = v23.sha


def check_base(path=ARCHIVE / 'sdk-worker.js', pin=BASE_SHA256):
    if Path(path).resolve() != (ARCHIVE / 'sdk-worker.js').resolve() or pin != BASE_SHA256 \
            or sha(Path(path)) != BASE_SHA256:
        raise ValueError('v31 worker base must be the exact archived v30 worker')


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
        problems.append('contract differs from v30 plus the four alignments (ABI 6, every inherited leaf equal)')
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
        problems.append('worker differs from sdk/v31-alignment-worker.js')
    if exports.read_text().splitlines() != expected_exports():
        problems.append('exports differ from the v30 archive')
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
        return ['archived v30 public loader/binary surface disagrees with its sidecar']
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
                    problems.append('v31 object lacks ' + define)
            if any('OXSDK_FINDING_016_SCHEDULER_PROBE' in arg for arg in args):
                problems.append('obsolete scheduler instrumentation present')
    expected = {'src/probe_engine.cpp', 'src/sdk_api.cpp', 'src/editor_api.cpp', 'src/unoembind_stub.cpp'}
    if len(compiles) != 4 or {args[args.index('-c') + 1] for args in compiles} != expected:
        problems.append('v31 record must compile each of the four source units exactly once')
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
    print('v31 preconditions hold' if not problems else 'v31 preconditions failed')
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
