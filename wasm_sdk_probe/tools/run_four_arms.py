"""F4 on a frozen generation (--generation N, e2/generations/generation-NN.json): the unchanged product-path suite with
that generation's identity, then its four arms.

One tool for every generation from 90 on (CLAUDE.md, the section on cadence, item 2), in place of the per-generation
copies tools/run_v79..v89_four_arms.py (kept, each bound by its own evidence).  run_v89_four_arms.py's text with the
generation as a parameter: the default shell manifest is the generation's bundle; identity and reader are
four_arms_identity.py and judge_product_four_arms.py; the lock name carries the generation.

Rebind bundle.MANIFEST BEFORE importing the runner. Record the override, never edit bound tools.
The other product-path checks include I-enter-raw-substring (expected frozen-oracle Chrome FAIL).
--preflight-only reads identity without opening a browser. --without-override and --shell-manifest
exist for the declared identity reds; a failing preflight cannot launch a browser.

  run_four_arms.py --generation N --browser chrome|firefox --out NEW_DIR [--preflight-only]
"""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))


def prepare(generation, manifest=None, without_override=False, metadata=None):
    import build_e2_c_shell_bundle as bundle
    default = bundle.MANIFEST.as_posix()
    if 'run_e2_c_product_path' in sys.modules:
        raise ValueError('runner imported before the manifest override')
    # The generation's bundle from its file by plain json: the reader's imports reach the runner.
    generation_file = Path(__file__).resolve().parent.parent / f'e2/generations/generation-{int(generation)}.json'
    used = Path(manifest or json.loads(generation_file.read_text())['bundle'])
    if not without_override:
        bundle.MANIFEST = used
    import hashlib
    raw = Path(__file__).resolve().parent.parent / bundle.MANIFEST
    override = {'default': default, 'used': bundle.MANIFEST.as_posix(), 'applied': not without_override,
                'fileSha256': hashlib.sha256(raw.read_bytes()).hexdigest() if raw.is_file() else None}
    if metadata is not None:
        metadata['shellManifestOverride'] = override
    import run_e2_c_product_path as pp
    import judge_product_four_arms as reader
    gen = reader.bind(generation)
    if metadata is not None:
        metadata['generationFile'] = {'path': gen.path.relative_to(gen.path.parents[2]).as_posix(), 'sha256': gen.file_sha256}
    import v23_product_four_arms as arms
    from v23_feature_selection_cases import digest
    root = pp.PROJECT / 'dist'
    overrides, identity = arms.observer_mirror(root, gen.profile)
    served = {p: digest(overrides[p] if p in overrides else (root / p).read_bytes())
              for p in arms.served_paths(identity)}
    # Only the identity phase; there is no fabricated stream or row verdict here.
    record = object.__new__(reader.Record)
    record.identity = identity
    record.page = {'identity': {'profile': gen.profile, 'served': served}}
    # The unmodified reader supplies the precise lagging-generation reason for the no-override red.
    j23 = reader.j23
    j23.Record._identity(record, pp.PROJECT)
    reader.Record._identity(record, pp.PROJECT)
    return pp, {'shellManifestOverride': override, 'identity': identity, 'preflight': 'READY'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--generation', type=int, required=True)
    parser.add_argument('--browser', choices=('chrome', 'firefox'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--without-override', action='store_true')
    parser.add_argument('--shell-manifest', type=Path)
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    metadata = {'argv': sys.argv, 'tool': {'path': 'wasm_sdk_probe/tools/run_four_arms.py',
                                           'sha256': __import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest()},
                'generation': args.generation, 'browser': args.browser, 'startedAt': time.time(),
                'preflightOnly': args.preflight_only,
                'requestedManifest': str(args.shell_manifest) if args.shell_manifest else None,
                'withoutOverride': args.without_override}
    try:
        pp, prepared = prepare(args.generation, args.shell_manifest, args.without_override, metadata)
        metadata.update(prepared)
        if args.preflight_only:
            return 0
        import v21_shakedown_common as common
        import judge_product_four_arms as reader
        with common.browser_lock(f'gen{args.generation}-four-arms'):
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
