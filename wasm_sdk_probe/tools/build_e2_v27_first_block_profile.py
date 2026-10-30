#!/usr/bin/env python3
"""e2-editor-v27 builder (SPEC-M3-v27-finding-176 4.4, 5): exactly what the v25
builder does -- the v23 builder's ABI6 action map through the v5 builder, then
the typedInsert declaration -- then v26's select-all leaf (its three gestures
and limits, SPEC-M3-select-all-v26 4.1), under the v27 identity.

A new file: build_e2_v25_feature_profile.py names e2-editor-v25 and v25's
evidence binds it; v26 had no builder of this kind (a manifest successor of
the v25 archive, no link).  The select-all leaf is read from the archived v26
manifest, not written here.  check_v27_first_block_contract then requires
every leaf but the three bindings to equal that manifest.
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
import check_v27_first_block_contract as contract
import check_v24_feature_contract as v24_contract


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('--profile', required=True)
    for field in ('loader', 'worker', 'wasm', 'exports', 'output'):
        parser.add_argument('--' + field, type=Path, required=True)
    args, _ = parser.parse_known_args(argv[1:])
    if args.profile != contract.PROFILE:
        raise SystemExit('v27 builder requires exactly ' + contract.PROFILE)
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit('existing v27 profile/partial files must be preserved')
    # TOLD, not guessed: v26's export list (v25's), in the list and in the binary.
    problems = contract.input_problems(args.worker, args.exports, args.wasm) \
        + contract.actual_export_problems(args.loader, args.wasm)
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
