#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 section 3: the unchanged product-path suite with frozen-86 identity, then its four arms.

Derived from tools/run_v85_four_arms.py (bound by F4-85's evidence; not edited).  The differences are a closed list:
this paragraph and the line above it; generation 85 -> 86 (default manifest, twice); the identity and reader modules
v85 -> v86; the lock name.  Everything below is that file's text.

SPEC-P-demo-batch-3 section 2: the unchanged product-path suite with frozen-85 identity, then its four arms.

Derived from tools/run_v84_four_arms.py (bound by F4-84's evidence; not edited).  The differences are a closed list:
this paragraph and the line above it; generation 84 -> 85 (default manifest, twice); the identity and reader modules
v84 -> v85; the lock name.  Everything below is that file's text.

SPEC-P-demo-batch-1 section 3: the unchanged product-path suite with frozen-84 identity, then its four arms.

Derived from tools/run_v83_four_arms.py (bound by F4-83's evidence; not edited).  The differences are a closed list:
this paragraph and the line above it; generation 83 -> 84 (default manifest, twice); the identity and reader modules
v83 -> v84; the lock name.  Everything below is that file's text.

SPEC-M3-v29-tick-pacing section 6 T3: the unchanged product-path suite with frozen-83 identity, then its four arms.

Derived from tools/run_v82_four_arms.py (bound by F4-82's evidence; not edited).  The differences are a closed
list: this paragraph and the line above it; generation 82 -> 83 (default manifest, twice); the identity and
reader modules v82 -> v83 (tools/v83_four_arms_identity.py, tools/judge_v83_product_four_arms.py); the lock
name.  Everything below is run_v82_four_arms.py's text from its own derivation note on.

SPEC-M3-v28-last-line-fallback 7.3 F4-82: the unchanged product-path suite with frozen-82 identity, then its four arms.

Derived from tools/run_v81_four_arms.py (bound by F4-81's evidence; not edited).  The differences are a closed
list: this paragraph and the line above it; generation 81 -> 82 (default manifest, twice); the identity and
reader modules v81 -> v82 (tools/v82_four_arms_identity.py, tools/judge_v82_product_four_arms.py); the lock
name.  Everything below is run_v81_four_arms.py's text from its own derivation note on.

SPEC-M3-v27-finding-176 7.3 F4-81: the unchanged product-path suite with frozen-81 identity, then its four arms.

Derived from tools/run_v80_four_arms.py (bound by F4-80's evidence; not edited).  The differences are a closed
list: this paragraph and the line above it; generation 80 -> 81 (default manifest, twice); the identity and
reader modules v80 -> v81 (tools/v81_four_arms_identity.py, tools/judge_v81_product_four_arms.py); the lock
name.  Everything below is run_v80_four_arms.py's text from its own derivation note on.

SPEC-M3-select-all-v26 5.6 F4-80: the unchanged product-path suite with frozen-80 identity, then its four arms.

Derived from tools/run_v79_four_arms.py (bound by F4-79's evidence; not edited).  The differences are a closed
list: this paragraph and the line above it; generation 79 -> 80 (default manifest, twice); the identity and
reader modules v79 -> v80 (tools/v80_four_arms_identity.py, tools/judge_v80_product_four_arms.py); the lock
name.  Everything below is run_v79_four_arms.py's text from its own derivation note on.

Derived from tools/run_v25_four_arms.py (bound by v25 F4's evidence; not edited).  The differences are a closed
list: this paragraph and the line above it; generation 78 -> 79 (default manifest, twice); the identity and
reader modules v25 -> v79 (tools/v79_four_arms_identity.py, tools/judge_v79_product_four_arms.py); the lock
name.  Everything below is run_v25_four_arms.py's text, including its own derivation note.

Derived from tools/run_v24_four_arms.py (bound by v24's A4 count, not edited).  The differences are a closed
list: generation 78 instead of 77; the v25 identity (tools/v25_four_arms_identity.py) and reader
(tools/judge_v25_product_four_arms.py); the lock name; and NO V0'' preflight -- v24's wrapper ran V0''
because A4-v24 was a count against v23's live-asserted records; F4 is a section 6.3 check before any count,
and the v24 counts v25 carries over are re-read by V0' instead (findings/evidence/link-batch-v25/cutover/,
freeze-78/v0/).

Rebind bundle.MANIFEST BEFORE importing the runner. Record the override, never edit bound tools.
The other product-path checks include I-enter-raw-substring (expected frozen-oracle Chrome FAIL).
--preflight-only reads identity without opening a browser. --without-override and --shell-manifest
exist for the declared identity reds; a failing preflight cannot launch a browser.
"""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))


def prepare(manifest=None, without_override=False, metadata=None):
    import build_e2_c_shell_bundle as bundle
    default = bundle.MANIFEST.as_posix()
    if 'run_e2_c_product_path' in sys.modules:
        raise ValueError('runner imported before the manifest override')
    used = Path(manifest or 'e2/editor-shell-v2-bundle-v86.json')
    if not without_override:
        bundle.MANIFEST = used
    import hashlib
    raw = Path(__file__).resolve().parent.parent / bundle.MANIFEST
    override = {'default': default, 'used': bundle.MANIFEST.as_posix(), 'applied': not without_override,
                'fileSha256': hashlib.sha256(raw.read_bytes()).hexdigest() if raw.is_file() else None}
    if metadata is not None:
        metadata['shellManifestOverride'] = override
    import run_e2_c_product_path as pp
    import v23_product_four_arms as arms
    import judge_v86_product_four_arms as reader
    from v86_four_arms_identity import PROFILE
    from v23_feature_selection_cases import digest
    root = pp.PROJECT / 'dist'
    overrides, identity = arms.observer_mirror(root, PROFILE)
    served = {p: digest(overrides[p] if p in overrides else (root / p).read_bytes())
              for p in arms.served_paths(identity)}
    # Only the identity phase; there is no fabricated stream or row verdict here.
    record = object.__new__(reader.Record)
    record.identity = identity
    record.page = {'identity': {'profile': PROFILE, 'served': served}}
    # The unmodified reader supplies the precise lagging-generation reason for the no-override red.
    j23 = reader.j23
    j23.Record._identity(record, pp.PROJECT)
    reader.Record._identity(record, pp.PROJECT)
    return pp, {'shellManifestOverride': override, 'identity': identity, 'preflight': 'READY'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chrome', 'firefox'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--without-override', action='store_true')
    parser.add_argument('--shell-manifest', type=Path)
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    metadata = {'argv': sys.argv, 'browser': args.browser, 'startedAt': time.time(),
                'preflightOnly': args.preflight_only,
                'requestedManifest': str(args.shell_manifest) if args.shell_manifest else 'e2/editor-shell-v2-bundle-v86.json',
                'withoutOverride': args.without_override}
    try:
        pp, prepared = prepare(args.shell_manifest, args.without_override, metadata)
        metadata.update(prepared)
        if args.preflight_only:
            return 0
        import v21_shakedown_common as common
        import judge_v86_product_four_arms as reader
        with common.browser_lock('v86-four-arms'):
            checks, cpu = common.pre_run_checks(), common.foreign_cpu()
            metadata.update(preRun=checks, foreignCpu=cpu)
            if checks['refuse'] or not cpu.get('ok'):
                raise ValueError('browser pre-run refusal')
            report = args.out / 'report.json'
            sys.argv = ['tools/run_e2_c_product_path.py', '--browser', args.browser, '--out', str(report)]
            metadata['runnerExit'] = pp.main()
            directory = pp.four_arms.artifact_dir_for(str(report))
            result = reader.judge_run(directory)
            (args.out / 'four-arms-reader.json').write_text(json.dumps(result, indent=1, default=str) + '\n')
            metadata['fourArms'] = {k: v['outcome'] for k, v in result['arms'].items()}
            return 0 if all(v == 'PASS' for v in metadata['fourArms'].values()) else 1
    except Exception as error:
        metadata.update(preflight='NOT_ESTABLISHED', error=f'{type(error).__name__}: {error}')
        print(metadata['error'], file=sys.stderr)
        return 1
    finally:
        metadata['finishedAt'] = time.time()
        (args.out / 'wrapper.json').write_text(json.dumps(metadata, indent=1, ensure_ascii=False, default=str) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
