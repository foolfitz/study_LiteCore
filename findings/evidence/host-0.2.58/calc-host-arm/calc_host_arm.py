#!/usr/bin/env python3
"""Host 0.2.58's new arm: the two new Calc features' page criteria on the user's path (Files -> the host's Calc route).

The host does not frame the page: EditorController.php scopes the page's <style> with @scope and puts the page's body inside
Nextcloud's own document, so Nextcloud's global CSS (buttons, dialogs) reaches the DOM header buttons and the context menu.
The mirror cannot see that.  This arm runs check_calc_headers.scenario (P-H1..P-H6) and check_calc_structure.scenario
(P-S1..P-S7), unchanged, against a page opened the owner's way: admin logs in, a fixture is PUT into an owned folder, its row
in Files is clicked, the host route opens it with its lock.  Each tool's own fixture, a fresh copy per browser and per arm.

  calc_host_arm.py --out NEW_DIR [--browsers chrome firefox]       (host-stack/bin first on PATH)

Before leaving a file the page's own save is pressed if the document is dirty (the host asks before leaving unsaved edits).
Cleanup: UNLOCK only this run's files, DELETE the owned folder.  Verdict H_CALC_HOLDS iff every arm of every browser ran without
an error, has checks, and every check passes.  Exit 0 for H_CALC_HOLDS.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import traceback

SDK = Path(__file__).resolve().parents[4] / 'wasm_sdk_probe'
sys.path.insert(0, str(SDK / 'tools'))
import run_calc_editor_host as host  # noqa: E402
import check_calc_headers as headers  # noqa: E402
import check_calc_structure as structure  # noqa: E402
from create_calc_headers_fixture import create as create_headers  # noqa: E402
from create_calc_structure_fixture import create as create_structure  # noqa: E402
from probe_m3_gate0_coep import browser_login  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_calc_editor_browser import wait  # noqa: E402
from v21_shakedown_common import browser_lock, open_browser, close_browser  # noqa: E402

ROOT = 'window.__calcEditor'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--browsers', nargs='+', choices=['chrome', 'firefox'], default=['chrome', 'firefox'])
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    arms = [('headers', create_headers(out / 'fixture-headers'), headers, 'headersSupported'),
            ('structure', create_structure(out / 'fixture-structure'), structure, 'structureSupported')]
    report = {'tool': {'path': 'findings/evidence/host-0.2.58/calc-host-arm/calc_host_arm.py', 'sha256': sha(__file__),
                       'argv': sys.argv[1:]},
              'reused': {m.__name__: sha(m.__file__) for m in (headers, structure, host)},
              'fixtures': {a: sha(f) for a, f, _, _ in arms}, 'runs': [], 'cleanup': {}}
    with browser_lock('calc-host-arm'), tempfile.TemporaryDirectory(prefix='calc-host-arm-', dir=SDK / 'build') as scratch:
        h = host.Harness(out, Path(scratch), tuple(args.browsers))
        h.folder = 'M4-calc-arm-' + time.strftime('%Y%m%dT%H%M%S')
        report['ownedFolder'] = h.folder
        created = False
        try:
            code, _, _ = h.dav('MKCOL', h.folder)
            if code != 201:
                raise RuntimeError(f'MKCOL {code}')
            created = True
            for browser in args.browsers:
                session = open_browser(browser, headers.WINDOW) if browser == 'chrome' else h.browser(browser, 'admin')
                try:
                    login = browser_login(session, h.instance.base, h.instance.password)
                    for arm, fixture, module, flag in arms:
                        name = f'{h.folder}/{browser}-{arm}.ods'
                        h.paths.append(name)
                        record = {'browser': browser, 'arm': arm, 'version': session.version, 'login': login, 'checks': [],
                                  'error': None}
                        report['runs'].append(record)
                        try:
                            record['put'] = h.dav('PUT', name, fixture.read_bytes(), {'Content-Type': host.ODS})[0]
                            record['entry'] = h.open_file(session, name, 'ods-editor.html')
                            wait(session, f'Boolean({ROOT}?.state?.cell) && {ROOT}.state.{flag}===true', 180)  # run-01: no ?. after ROOT threw before the module ran
                            wait(session, "document.querySelectorAll('#row-headers [role=rowheader]').length>0", 30)
                            record['lockAtOpen'] = {k: v for k, v in h.props(name).items() if k != 'token'}
                            module.scenario(module.Run(session, record))
                        except Exception as error:  # noqa: BLE001  a crash is a result; keep the checks already read
                            record['error'] = repr(error)
                            record['traceback'] = traceback.format_exc()
                        finally:
                            (out / f'{browser}-{arm}-last.png').write_bytes(session.screenshot())
                            try:
                                if evaluate(session, f'{ROOT}?.state?.dirty===true'):
                                    evaluate(session, "document.querySelector('#save-button').click()")
                                    wait(session, f'{ROOT}.state && !{ROOT}.state.busy && {ROOT}.state.dirty!==true', 90)
                                    record['savedBeforeLeave'] = True
                                record['leave'] = h.leave(session, name)
                            except Exception as error:  # noqa: BLE001
                                record['leaveError'] = repr(error)
                            (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
                finally:
                    report.setdefault('browserClose', {})[browser] = close_browser(session)
        except Exception as error:  # noqa: BLE001
            report['error'] = repr(error)
            report['traceback'] = traceback.format_exc()
        finally:
            cleanup = report['cleanup']
            cleanup['ownedUnlocks'] = []
            for name in h.paths:
                try:
                    pr = h.props(name)
                    if pr['token']:
                        token = pr['token'] if pr['token'].startswith('opaquelocktoken:') else 'opaquelocktoken:' + pr['token']
                        code, _, _ = h.dav('UNLOCK', name, headers={'Lock-Token': f'<{token}>'})
                        cleanup['ownedUnlocks'].append({'name': name, 'status': code})
                except Exception as error:  # noqa: BLE001
                    cleanup.setdefault('errors', []).append(repr(error))
            if created:
                cleanup['folderDeleteStatus'] = h.dav('DELETE', h.folder)[0]
    ok = (not report.get('error') and not report['cleanup'].get('errors') and len(report['runs']) == 2 * len(args.browsers)
          and all(not r['error'] and r['checks'] and all(c['pass'] for c in r['checks']) for r in report['runs']))
    report['verdict'] = 'H_CALC_HOLDS' if ok else 'H_CALC_RED'
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'error': report.get('error'), 'cleanup': report['cleanup'],
                      'runs': [{'browser': r['browser'], 'arm': r['arm'], 'error': r['error'],
                                'passed': sum(c['pass'] for c in r['checks']), 'checks': len(r['checks']),
                                'red': [c['id'] for c in r['checks'] if not c['pass']][:12]} for r in report['runs']]},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
