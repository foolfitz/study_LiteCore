#!/usr/bin/env python3
"""The Calc page criteria on the user's path (Files -> the host's Calc route), one tool for every host release (CLAUDE.md, cadence
item 2).  Parametrised from findings/evidence/host-0.2.58/calc-host-arm/calc_host_arm.py (headers and structure, left as it was):
--arms picks which mirror tools' scenario() run, unchanged, on the host.

The host does not frame the page: EditorController.php scopes the page's <style> with @scope and puts the page's body inside
Nextcloud's own document, so Nextcloud's global CSS reaches the page's DOM.  The mirror cannot see that.  The page is opened the
owner's way: admin logs in, each arm's own fixture is PUT into an owned folder (a fresh copy per browser and per arm), its row in
Files is clicked, and the host route opens it with its lock.

  calc_host_arm.py --out NEW_DIR --arms sheets copy [--browsers chrome firefox]      (host-stack/bin first on PATH)
  calc_host_arm.py --out NEW_DIR --arms zoom copy-html --native-harness BUILD/v8/calc-undo-native

  headers    check_calc_headers.scenario     fixture create_calc_headers_fixture
  structure  check_calc_structure.scenario   fixture create_calc_structure_fixture
  sheets     check_calc_sheets.scenario      fixture create_calc_sheets_fixture     (SPEC-P-calc-sheets)
  copy       check_calc_copy.scenario        fixture create_calc_structure_fixture  (SPEC-P-calc-copy)
  copy-html  check_calc_copy.scenario(html)  fixture create_calc_structure_fixture  (SPEC-P-calc-copy 9-12; 0.2.60)
  zoom       check_calc_zoom.scenario        fixture create_calc_structure_fixture  (SPEC-P-calc-zoom; 0.2.60)

copy-html is the mirror's --html: P-C1..P-C5, then P-H1..P-H3 on the host page, and P-H4 after the browsers close, as the mirror
does it: each browser's read-back HTML of A1:C2 pasted by the native core (check_calc_copy_native.py --paste-html, --native-harness).

With a copy arm, Chrome is granted clipboard permission for the host origin and Firefox runs with
dom.events.testing.asyncClipboard (tools/v21_clipboard.py), the mirror tool's own instrument and its named limit (user activation
is relaxed).  Before leaving a file the page's own save is pressed if the document is dirty.  Cleanup: UNLOCK only this run's
files, DELETE the owned folder.  Verdict H_CALC_HOLDS iff every arm of every browser ran without an error, has checks, and every
check passes.  Exit 0 for H_CALC_HOLDS.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK / 'tools'))
import run_calc_editor_host as host  # noqa: E402
import check_calc_copy as copy_tool  # noqa: E402
import check_calc_headers as headers  # noqa: E402
import check_calc_sheets as sheets  # noqa: E402
import check_calc_structure as structure  # noqa: E402
import check_calc_zoom as zoom_tool  # noqa: E402
from create_calc_headers_fixture import create as create_headers  # noqa: E402
from create_calc_sheets_fixture import create as create_sheets  # noqa: E402
from create_calc_structure_fixture import create as create_structure  # noqa: E402
from probe_m3_gate0_coep import browser_login, firefox_profile  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_browser_probe import FirefoxSession  # noqa: E402
from run_calc_editor_browser import wait  # noqa: E402
from v21_clipboard import FIREFOX_PREFS, grant  # noqa: E402
from v21_shakedown_common import browser_lock, open_browser, close_browser  # noqa: E402

ROOT = 'window.__calcEditor'
ARMS = {'headers': (create_headers, headers, 'headersSupported'), 'structure': (create_structure, structure, 'structureSupported'),
        'sheets': (create_sheets, sheets, 'headersSupported'), 'copy': (create_structure, copy_tool, 'copySupported'),
        'copy-html': (create_structure, copy_tool, 'copySupported'), 'zoom': (create_structure, zoom_tool, 'zoomSupported')}


def run_scenario(arm, module, run, record, out):
    """Each mirror tool's scenario(), called the way its own main() calls it."""
    if arm == 'copy-html':
        run.out, run.record = out, record
        return module.scenario(run, True)
    if arm == 'zoom':
        return module.scenario(run, record)
    return module.scenario(run)


def paste_back(report, out, harness):
    """check_calc_copy.py main()'s P-H4 step: each copy-html run's read-back HTML of A1:C2, pasted by the native core."""
    for r in report['runs']:
        if r['arm'] != 'copy-html':
            continue
        saved = r.get('P-H4-html')
        paste_out = out / f"{r['browser']}-P-H4"
        proc = subprocess.run(['python3', str(SDK / 'tools/check_calc_copy_native.py'), '--paste-html', str(saved or '/dev/null'),
                               '--harness', str(harness), '--out', str(paste_out)], capture_output=True, text=True,
                              timeout=300) if saved else None
        detail = json.loads((paste_out / 'report.json').read_text())['P-H4'] if saved and (paste_out / 'report.json').exists() else None
        r['checks'].append({'id': 'P-H4/paste-back', 'pass': bool(proc and proc.returncode == 0 and detail and detail['ok']),
                            'detail': {'exit': proc.returncode if proc else None, 'L20': detail and detail['L20'],
                                       'target': detail and detail['target'], 'stderr': proc.stderr[-400:] if proc else None}})


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def firefox(h, kind, prefs):
    """run_calc_editor_host.Harness.browser, with prefs: the same mkcert-trusting profile and window."""
    os.environ['MOZ_HEADLESS_WIDTH'] = '1400'
    os.environ['MOZ_HEADLESS_HEIGHT'] = '1000'
    session = FirefoxSession.__new__(FirefoxSession)
    try:
        session.__init__('cold', profile_dir=firefox_profile(h.scratch / kind), extra_prefs=prefs)
        return session
    except Exception:
        close_browser(session)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--arms', nargs='+', choices=sorted(ARMS), required=True)
    p.add_argument('--browsers', nargs='+', choices=['chrome', 'firefox'], default=['chrome', 'firefox'])
    p.add_argument('--native-harness', type=Path)
    args = p.parse_args()
    if 'copy-html' in args.arms and not args.native_harness:
        p.error('copy-html needs --native-harness (P-H4)')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    arms = [(name, ARMS[name][0](out / f'fixture-{name}'), ARMS[name][1], ARMS[name][2]) for name in args.arms]
    clipboard = bool({'copy', 'copy-html'} & set(args.arms))
    report = {'tool': {'path': 'wasm_sdk_probe/tools/calc_host_arm.py', 'sha256': sha(__file__), 'argv': sys.argv[1:]},
              'reused': {m.__name__: sha(m.__file__) for m in (*{a[2] for a in arms}, host)},
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
                if browser == 'chrome':
                    session = open_browser(browser, headers.WINDOW)
                else:
                    session = firefox(h, 'admin', FIREFOX_PREFS) if clipboard else h.browser(browser, 'admin')
                try:
                    login = browser_login(session, h.instance.base, h.instance.password)
                    if clipboard:
                        report.setdefault('clipboardGrant', {})[browser] = grant(session, browser, h.instance.base)
                        if browser == 'chrome':
                            session.call('Emulation.setFocusEmulationEnabled', {'enabled': True})
                    for arm, fixture, module, flag in arms:
                        name = f'{h.folder}/{browser}-{arm}.ods'
                        h.paths.append(name)
                        record = {'browser': browser, 'arm': arm, 'version': session.version, 'login': login, 'checks': [],
                                  'error': None}
                        report['runs'].append(record)
                        try:
                            record['put'] = h.dav('PUT', name, fixture.read_bytes(), {'Content-Type': host.ODS})[0]
                            record['entry'] = h.open_file(session, name, 'ods-editor.html')
                            wait(session, f'Boolean({ROOT}?.state?.cell) && {ROOT}.state.{flag}===true', 180)
                            wait(session, "document.querySelectorAll('#row-headers [role=rowheader]').length>0", 30)
                            record['lockAtOpen'] = {k: v for k, v in h.props(name).items() if k != 'token'}
                            run_scenario(arm, module, module.Run(session, record), record, out)
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
    if 'copy-html' in args.arms:
        paste_back(report, out, args.native_harness.resolve())
    ok = (not report.get('error') and not report['cleanup'].get('errors') and len(report['runs']) == len(arms) * len(args.browsers)
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
