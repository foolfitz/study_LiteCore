#!/usr/bin/env python3
"""Run the predeclared bounded v23 no-host cohort only after an actual owner link.

No make, host, service changes, frozen-profile writes or live documents.
The temporary HTTP server/browser are owned subprocesses, closed on every exit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import traceback
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v21_shakedown_common as common
import run_e2_c_product_path as pp
from judge_v23_diagnostic import ARMS, FILES, PROFILE, identity

PROJECT = Path(__file__).resolve().parents[1]


def mirror(target, fixture):
    target.mkdir(parents=True, exist_ok=False)
    # Symlink immutable input directories. The only written files are private.
    for source in (PROJECT / 'dist').iterdir():
        if source.name not in ('e2-editor.html', 'sdk', 'editor-shell', 'editor-shell-v2'):
            (target / source.name).symlink_to(source, target_is_directory=source.is_dir())
    for name in ('sdk', 'editor-shell', 'editor-shell-v2'):
        (target / name).symlink_to(PROJECT / name, target_is_directory=True)
    shutil.copyfile(PROJECT / 'web/v23-diagnostic.html', target / 'e2-editor.html')
    shutil.copyfile(PROJECT / 'web/v23-diagnostic.js', target / 'v23-diagnostic.js')
    shutil.copyfile(fixture, target / 'fixture.odt')
    wd = PROJECT / 'web/v23-diagnostic-wd.js'
    if wd.exists(): shutil.copyfile(wd, target / wd.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wasm-sha256', required=True, help='explicit actual owner-linked candidate pin')
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--fixture-name', help='actual loader filename; defaults to fixture basename')
    parser.add_argument('--output', type=Path, required=True, help='new directory, never overwritten')
    parser.add_argument('--browser', choices=('chrome', 'firefox', 'both'), default='both')
    parser.add_argument('--arm', choices=(*ARMS, 'all', 'wd'), default='all')
    parser.add_argument('--case-id', help='W-D module case id; not part of bounded diagnostic cohort')
    parser.add_argument('--rounds', type=int, choices=(1, 3, 5), default=3,
                        help='bounded cohort requires 3; W-D requires 5; 1 is preparation only')
    args = parser.parse_args()
    if args.rounds == 5 and args.arm != 'wd':
        parser.error('five rounds belong only to the separate W-D protocol')
    if args.arm == 'wd' and not args.case_id:
        parser.error('--arm wd requires --case-id')
    expected = identity(PROJECT / 'dist/profiles' / PROFILE, args.wasm_sha256)
    if not args.fixture.is_file(): parser.error('fixture does not exist')
    args.output.mkdir(parents=True, exist_ok=False)
    target = args.output.resolve() / 'mirror'
    mirror(target, args.fixture.resolve())
    report = {'schema': 1, 'profile': PROFILE, 'identity': expected,
              'fixtureSha256': hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
              'instrumentSha256': {str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [Path(__file__), PROJECT / 'tools/judge_v23_diagnostic.py',
                          PROJECT / 'web/v23-diagnostic.js', PROJECT / 'web/v23-diagnostic.html']},
              'runs': []}
    if args.arm == 'wd':
        from v23_wd_cases import instrument_files
        report['wdInstrumentSha256'] = {str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in instrument_files()}
        report['wdMirrorSha256'] = hashlib.sha256((target / 'v23-diagnostic-wd.js').read_bytes()).hexdigest()
    output = args.output / 'report.json'
    def write(): output.write_text(json.dumps(report, indent=2) + '\n')
    browsers = ('chrome', 'firefox') if args.browser == 'both' else (args.browser,)
    arms = ARMS if args.arm == 'all' else (args.arm,)
    with common.browser_lock('run_v23_diagnostic'):
        report['preRun'] = common.pre_run_checks()
        report['foreignCpu'] = common.foreign_cpu()
        if not report['foreignCpu'].get('ok'):
            write()
            raise SystemExit('foreign CPU load: no browser started; use a fresh output for a later trial')
        with common.served(target) as base:
            for browser in browsers:
                for n in range(1, args.rounds + 1):
                    for arm in arms:
                        print(f'{browser} round {n} {arm}', flush=True)
                        record = {'browser': browser, 'round': n, 'arm': arm}
                        report['runs'].append(record)
                        session = None
                        try:
                            # Re-read identity before every fresh process; stop candidate drift.
                            if identity(PROJECT / 'dist/profiles' / PROFILE, args.wasm_sha256) != expected:
                                raise RuntimeError('candidate artifacts changed during cohort')
                            session = common.open_browser(browser)
                            pp.navigate(session, base + '?' + urlencode({'arm': arm, 'caseId': args.case_id or '',
                                'fixtureName': args.fixture_name or args.fixture.name}))
                            deadline = time.monotonic() + 300
                            while time.monotonic() < deadline:
                                if pp.evaluate(session, 'Boolean(globalThis.__v23?.complete)'):
                                    break
                                time.sleep(0.25)
                            record['page'] = pp.evaluate(session, 'globalThis.__v23 || null')
                            if not record['page'] or not record['page'].get('complete'):
                                record['fatal'] = 'outer 300-second observation bound; not an SDK recovery'
                        except Exception:
                            record['fatal'] = traceback.format_exc()
                        finally:
                            if session is not None: record['cleanup'] = common.close_browser(session)
                            write()
    print(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
