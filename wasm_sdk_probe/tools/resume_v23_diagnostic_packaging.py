#!/usr/bin/env python3
"""Validate preserved link inputs and optionally pack; never run make/compiler."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_e2_v23_diagnostic_profile as packer
from check_v23_diagnostic_build import logical_lines, read_build_log, read_wasm, read_makefile, rule_body, macros
ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / 'wasm_sdk_probe'
BUILD = Path('wasm_sdk_probe/build/e2/editor-v23-diag')
OBJECTS = {'sdk_api.o', 'probe_engine.o', 'unoembind_stub.o', 'editor_api.o'}
EXPECTED = {str(BUILD / name) for name in OBJECTS | {'probe.js', 'probe.wasm', 'exports.txt'}}
PACKAGING_DELTAS = {'wasm_sdk_probe/Makefile', 'wasm_sdk_probe/tools/build_e2_v23_diagnostic_profile.py'}

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def verify_rows(rows, root=ROOT):
    for row in rows:
        path = root / row['path']
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('input escapes repository: ' + row['path'])
        if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError('preserved input changed: ' + row['path'])

def build_commands(text):
    found = {}
    for line in logical_lines(text):
        args = shlex.split(line)
        if '-o' not in args: continue
        output = args[args.index('-o') + 1]
        if output.startswith('build/e2/editor-v23-diag/') and (output.endswith('.o') or output.endswith('/probe.js')):
            if output in found: raise ValueError('duplicate compile/link output: ' + output)
            found[output] = args
    if set(found) != {'build/e2/editor-v23-diag/' + n for n in OBJECTS | {'probe.js'}}:
        raise ValueError('exact four compiles and one link are required')
    return found

def validate(audit, boundary, build_log, planned_log, root=ROOT):
    if {row['path'] for row in audit['build_artifacts']} != EXPECTED or len(audit['build_artifacts']) != 7:
        raise ValueError('audit must bind exactly seven linked artifacts')
    if (root / audit['link_log']['path']).resolve() != build_log.resolve():
        raise ValueError('build log is not the preserved audited attempt')
    protected = audit['build_artifacts'] + [audit['link_log']]
    verify_rows(protected, root)
    actual, planned = build_log.read_text(), planned_log.read_text()
    problems = read_build_log(actual) + read_build_log(planned)
    if problems: raise ValueError('; '.join(problems))
    if build_commands(actual) != build_commands(planned):
        raise ValueError('planned compile/link commands differ from linked attempt')
    source = json.loads((boundary / 'source-inputs.json').read_text())
    verify_rows([row for row in source['files'] if row['path'] not in PACKAGING_DELTAS], root)
    verify_rows(json.loads((boundary / 'core-inputs.json').read_text())['files'], root)
    current_make = (root / 'wasm_sdk_probe/Makefile').read_text()
    problems = read_makefile(current_make)
    if problems: raise ValueError('; '.join(problems))
    # A stale supplied dry-run cannot conceal changes to current compile/link flags.
    old_make = subprocess.check_output(['git', 'show', source['commit'] + ':wasm_sdk_probe/Makefile'], cwd=root, text=True)
    target = '$(E2_V23D_BUILD)/%.o:'
    if rule_body(current_make, target).replace(' v23-diagnostic-worker-preflight', '') != rule_body(old_make, target):
        raise ValueError('current diagnostic compilation rule changed')
    if macros(current_make)['link_v23_diagnostic'] != macros(old_make)['link_v23_diagnostic']:
        raise ValueError('current diagnostic link macro changed')
    # Only the explicit packaging-base/preflight delta is exempt from the old
    # whole Makefile hash. Header flags and library/source variables also bind.
    normalized = re.sub(r'^E2_V23D_BASE_WORKER := .*\n', '', current_make, flags=re.M)
    normalized = re.sub(r'^\.PHONY: v23-diagnostic-worker-preflight\n.*?\n\n', '', normalized, flags=re.M | re.S)
    normalized = normalized.replace(' v23-diagnostic-worker-preflight', '')
    normalized = normalized.replace('$(E2_V23D_BASE_WORKER)', 'sdk/sdk-worker.js')
    if normalized != old_make:
        raise ValueError('Makefile changed outside the reviewed packaging-only delta')
    problems = read_wasm((root / BUILD / 'probe.wasm').read_bytes())
    if problems: raise ValueError('; '.join(problems))
    packer.checked_base_worker()
    return protected

def package(protected=()):
    worker = ROOT / BUILD / 'sdk-worker.js'
    output = SDK / 'dist/profiles/e2-editor-v23-diag'
    manifest = output / 'sdk-manifest.json'
    temporary = worker.with_suffix('.js.pending')
    failed = [output.with_name(output.name + '.failed'), worker.with_name('sdk-worker.failed.js'), worker.with_name('sdk-worker.pending.failed.js')]
    if (output.exists() and (not output.is_dir() or any(output.iterdir()))) or any(p.exists() for p in [worker, manifest, temporary] + failed):
        raise ValueError('existing worker/manifest/failed bytes require a preserved retry decision')
    for script in ('build_base_no35_pack.py', 'build_cjk_subset_mono_pack.py'):
        subprocess.run([sys.executable, str(SDK / 'tools' / script), '--check'], cwd=SDK, check=True)
    try:
        with temporary.open('xb') as stream:
            stream.write(packer.checked_base_worker() + (SDK / 'sdk/v23-diagnostic-worker-tail.js').read_bytes())
        os.replace(temporary, worker)
        args = ['builder', '--source-manifest', str(SDK / 'sdk/v18-writer-review-manifest.json'),
                '--loader', str(ROOT / BUILD / 'probe.js'), '--wasm', str(ROOT / BUILD / 'probe.wasm'),
                '--worker', str(worker), '--exports', str(ROOT / BUILD / 'exports.txt'),
                '--profile', packer.PROFILE, '--inline-range-gestures', 'all',
                '--page-rectangles', '--paste-markdown', '--output', str(output)]
        previous = Path.cwd()
        try:
            os.chdir(SDK)
            code = packer.main(args)
        finally: os.chdir(previous)
        if code: raise RuntimeError('diagnostic packer returned ' + str(code))
        result = {name: digest(output / name) for name in ('probe.js', 'probe.wasm', 'sdk-worker.js', 'sdk-manifest.json')}
        verify_rows(protected, ROOT)
        return result
    except BaseException as error:
        # Failed bytes remain inspectable under non-target names.
        for path, target in zip([output, worker, temporary], failed):
            try:
                if path.exists():
                    if target.exists(): raise FileExistsError(str(target))
                    os.rename(path, target)
            except OSError as cleanup_error:
                # Continue quarantining other artifacts; retain the primary failure.
                error.add_note(f"quarantine failed for {path}: {cleanup_error}")
        raise

def main():
    parser = argparse.ArgumentParser()
    for name in ('linked-inputs','prelink-boundary','build-log','planned-build-log','receipt'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--package', action='store_true')
    args = parser.parse_args()
    with args.receipt.open('x') as receipt:
        result = {'mode': 'package' if args.package else 'check-only', 'ok': False,
                  'auditSha256': digest(args.linked_inputs)}
        protected = None
        try:
            protected = validate(json.loads(args.linked_inputs.read_text()), args.prelink_boundary, args.build_log, args.planned_build_log)
            if args.package: result['packaged'] = package(protected)
            else: verify_rows(protected, ROOT)
            result['linkedArtifactsUnchanged'] = True
            result['ok'] = True
        except BaseException as error:
            result['error'] = str(error)
            raise
        finally:
            if protected is not None and not (args.package and result['ok']):
                try:
                    verify_rows(protected, ROOT)
                    result['linkedArtifactsUnchanged'] = True
                except BaseException as error:
                    result.update(linkedArtifactsUnchanged=False, preservationError=str(error), ok=False)
            receipt.write(json.dumps(result, indent=2) + '\n')
    return 0 if result['ok'] else 1
if __name__ == '__main__': raise SystemExit(main())
