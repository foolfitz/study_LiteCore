#!/usr/bin/env python3
"""e2-editor-v30 builder (SPEC-P-demo-batch-3 section 2): v29's construction under the v30 identity, from the archived v29
loader, wasm and exports and the fixed worker.  Nothing is compiled or linked.

Derived from build_e2_v29_tick_pacing_profile.py with the names changed (v29's builder and evidence stay byte-identical).
check_v30_extend_gate_contract then requires every leaf but the worker binding and the name to equal v29's manifest.
"""
import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_e2_editor_v5_profile as v5
import build_e2_v23_feature_profile as v23_builder
import check_v30_extend_gate_contract as contract
import check_v24_feature_contract as v24_contract


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('--profile', required=True)
    for field in ('loader', 'worker', 'wasm', 'exports', 'output'):
        parser.add_argument('--' + field, type=Path, required=True)
    args, _ = parser.parse_known_args(argv[1:])
    if args.profile != contract.PROFILE:
        raise SystemExit('v30 builder requires exactly ' + contract.PROFILE)
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit('existing v30 profile/partial files must be preserved')
    # TOLD, not guessed: v29's export list, in the list and in the binary.
    problems = contract.input_problems(args.worker, args.exports, args.wasm) \
        + contract.actual_export_problems(args.loader, args.wasm) \
        + contract.identical_engine_problems(args.loader.parent)
    if problems:
        raise SystemExit('; '.join(problems))
    manifest_path = args.output / 'sdk-manifest.json'
    printed = io.StringIO()
    validated = False
    original = (v5.ABI_VERSION, v5.action_map)
    try:
        reference = json.loads((contract.ARCHIVE / 'sdk-manifest.json').read_text())
        v5.ABI_VERSION = 6
        v5.action_map = v23_builder.action_map
        with contextlib.redirect_stdout(printed):
            code = v5.main(argv)
        if code:
            return code
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['editorContract'][v24_contract.TYPED_INSERT_FIELD] = v24_contract.TYPED_INSERT_DECLARATION
        manifest['editorContract']['actions']['select-all'] = reference['editorContract']['actions']['select-all']
        v5.write_json(manifest_path, manifest)
        candidate = json.loads(manifest_path.read_text())
        problems = contract.contract_problems(candidate, reference) + contract.binding_problems(candidate, args.output)
        if problems:
            raise SystemExit('; '.join(problems))
        summary = json.loads(printed.getvalue())
        # The v5 builder's summary was printed before the select-all leaf was replaced.
        summary['withheld'] = [name for name, action in candidate['editorContract']['actions'].items()
                               if action.get('gestures') == []]
        summary.update(profile=contract.PROFILE, abiVersion=6,
                       typedInsert=v24_contract.TYPED_INSERT_DECLARATION,
                       selectAll=manifest['editorContract']['actions']['select-all'],
                       manifestSha256=contract.sha(manifest_path))
        print(json.dumps(summary, indent=2))
        validated = True
        return 0
    finally:
        v5.ABI_VERSION, v5.action_map = original
        if not validated:
            try:
                if manifest_path.exists():
                    fd, failed = tempfile.mkstemp(prefix='sdk-manifest.failed-', suffix='.json', dir=args.output)
                    os.close(fd)
                    os.replace(manifest_path, failed)
            finally:
                sys.stderr.write(printed.getvalue())


if __name__ == '__main__':
    raise SystemExit(main())
