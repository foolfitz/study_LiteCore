#!/usr/bin/env python3
"""Exact v30 successor delta (SPEC-P-demo-batch-3 section 2, finding 179): v29's manifest with only the profile name and the
worker binding changed, and v29's loader, wasm and exports byte for byte.  No link: the only new bytes are the worker.

Derived from check_v29_tick_pacing_contract.py (v29's evidence binds it; not edited).  The differences are a closed list: this
docstring; PROFILE, REFERENCE_PROFILE, ARCHIVE, BASE_SHA256, WORKER; the base worker's identity in check_base's message; the
strings naming v28 or v29; identical_engine_problems, added; no BUILD_DIR, DEFINES or feature_log_problems, because nothing is
compiled.
"""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_v23_diagnostic_build import read_wasm
import check_v23_feature_contract as v23

ROOT = Path(__file__).resolve().parent.parent
PROFILE = 'e2-editor-v30'
REFERENCE_PROFILE = 'e2-editor-v29'
ARCHIVE = ROOT / 'build/archive/e2-editor-v29-e61e5890-worker-a5df83db'
BASE_SHA256 = 'a5df83dbd0bd4df6b67b81d000da141910b76252fbf2bb8636d9a312edfffcba'
WORKER = ROOT / 'sdk/v30-extend-gate-worker.js'
BINDINGS = v23.BINDINGS
sha = v23.sha


def check_base(path=ARCHIVE / 'sdk-worker.js', pin=BASE_SHA256):
    if Path(path).resolve() != (ARCHIVE / 'sdk-worker.js').resolve() or pin != BASE_SHA256 \
            or sha(Path(path)) != BASE_SHA256:
        raise ValueError('v30 worker base must be the exact archived v29 worker')


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
        problems.append('contract differs from v29 (ABI 6, typedInsert, select-all and every other leaf equal)')
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
        problems.append('worker differs from sdk/v30-extend-gate-worker.js')
    if exports.read_text().splitlines() != expected_exports():
        problems.append('exports differ from the v29 archive')
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
        return ['archived v29 public loader/binary surface disagrees with its sidecar']
    if actual != expected:
        return ['actual public SDK exports differ: missing=' + repr(sorted(expected - actual))
                + ' extra=' + repr(sorted(actual - expected))]
    return []


def binding_problems(candidate, output):
    return [f'{key} does not bind {filename}' for key, filename in BINDINGS.items()
            if candidate.get('editorContract', {}).get(key) != sha(output / filename)]


def identical_engine_problems(directory):
    """The point of this profile: the engine is v29's, so no engine reading made on v29 has to be repeated for this reason."""
    return [f'{name} differs from the v29 archive' for name in ('probe.js', 'probe.wasm')
            if (Path(directory) / name).read_bytes() != (ARCHIVE / name).read_bytes()]


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check-worker-base', action='store_true')
    g.add_argument('--manifest', type=Path)
    p.add_argument('--base-worker', type=Path, default=ARCHIVE / 'sdk-worker.js')
    p.add_argument('--base-worker-sha256', default=BASE_SHA256)
    p.add_argument('--exports', type=Path)
    a = p.parse_args()
    if a.check_worker_base:
        check_base(a.base_worker, a.base_worker_sha256)
        problems = []
    else:
        if not a.exports:
            p.error('--manifest requires --exports')
        candidate = json.loads(a.manifest.read_text())
        reference = json.loads((ARCHIVE / 'sdk-manifest.json').read_text())
        problems = (contract_problems(candidate, reference) + binding_problems(candidate, a.manifest.parent)
                    + input_problems(a.manifest.parent / 'sdk-worker.js', a.exports, a.manifest.parent / 'probe.wasm')
                    + actual_export_problems(a.manifest.parent / 'probe.js', a.manifest.parent / 'probe.wasm')
                    + identical_engine_problems(a.manifest.parent))
    for problem in problems:
        print(problem)
    print('v30 preconditions hold' if not problems else 'v30 preconditions failed')
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
