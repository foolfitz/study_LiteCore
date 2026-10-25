#!/usr/bin/env python3
"""Separate v23 040/timing recorder; never changes the running bounded cohort graph."""
import argparse
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
from create_long_document import build
from v23_remaining_cases import PROJECT, PROFILE, ARMS, identity, fixtures, sha, instrument_files, served_instruments, verify_bindings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', default=PROFILE)
    p.add_argument('--wasm-sha256', required=True)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--arm', required=True, choices=ARMS)
    p.add_argument('--browser', choices=('chrome', 'firefox', 'both'), default='both')
    p.add_argument('--rounds', type=int, choices=(1, 3), default=1)
    a = p.parse_args()
    expected = identity(a.profile, a.wasm_sha256)
    source, population = fixtures()
    a.output.mkdir(parents=True, exist_ok=False)
    mirror = a.output.resolve() / 'mirror'; mirror.mkdir()
    for path in (PROJECT / 'dist').iterdir():
        if path.name not in ('e2-editor.html', 'sdk', 'editor-shell', 'editor-shell-v2'):
            (mirror / path.name).symlink_to(path, target_is_directory=path.is_dir())
    for name in ('sdk', 'editor-shell', 'editor-shell-v2'):
        (mirror / name).symlink_to(PROJECT / name, target_is_directory=True)
    shutil.copyfile(PROJECT / 'web/v23-remaining.html', mirror / 'e2-editor.html')
    shutil.copyfile(PROJECT / 'web/v23-remaining.js', mirror / 'v23-remaining.js')
    for name, path in source.items(): shutil.copyfile(path, mirror / f'{name}.odt')
    (mirror / 'long60.odt').write_bytes(build(60))
    inputs = {name: sha(mirror / f'{name}.odt') for name in (*source, 'long60')}
    graph = instrument_files()
    report = {'schema': 1, 'profile': a.profile, 'identity': expected, 'fixtures': inputs,
              'population': population, 'instrument': {str(f.relative_to(PROJECT)): sha(f) for f in graph},
              'mirrorInstrument': served_instruments(), 'runs': []}
    def write(): (a.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    with common.browser_lock('run_v23_remaining'):
        report['preRun'] = common.pre_run_checks(); report['foreignCpu'] = common.foreign_cpu()
        if not report['foreignCpu'].get('ok'): write(); raise SystemExit('foreign CPU load; no browser started')
        with common.served(mirror) as base:
            for browser in ('chrome', 'firefox') if a.browser == 'both' else (a.browser,):
                for n in range(1, a.rounds+1):
                    if identity(a.profile, a.wasm_sha256) != expected: raise RuntimeError('candidate drift')
                    verify_bindings(report, mirror, check_pages=False)
                    row = {'browser': browser, 'round': n, 'arm': a.arm}; report['runs'].append(row)
                    session = None
                    print(f'{browser} {a.arm} {n}', flush=True)
                    try:
                        session = common.open_browser(browser)
                        pp.navigate(session, base+'?'+urlencode({'arm':a.arm, 'profile':a.profile}))
                        until = time.monotonic()+360
                        while time.monotonic()<until:
                            if pp.evaluate(session, 'Boolean(globalThis.__v23remaining?.complete)'): break
                            time.sleep(.25)
                        row['page'] = pp.evaluate(session, 'globalThis.__v23remaining || null')
                    except Exception: row['fatal'] = traceback.format_exc()
                    finally:
                        if session is not None: row['cleanup'] = common.close_browser(session)
                        write()
    print(a.output/'report.json')

if __name__ == '__main__': main()
