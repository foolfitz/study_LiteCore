#!/usr/bin/env python3
"""SPEC-P-demo-batch-1 sections 3 and 4 on the installed host: Z9 (the zoom controls inside Nextcloud) and C1-C3 on both Calc pages.

Opens scratch documents from Files the way a user does, real pointer and wheel, then leaves so the locks release and removes the
folder.  The Calc arms reuse tools/check_calc_sheet_view.py's Run and Hands, so the same clauses are read on the host.  Writes
nothing to a document.  Run with host-stack/bin first on PATH, from anywhere.

  python3 -I host_batch.py [--browsers chrome,firefox] [--out DIR]
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
import traceback
import urllib.parse

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
import check_calc_sheet_view as view  # noqa: E402
import check_m3_skeleton_open as s  # noqa: E402
import v21_input as real  # noqa: E402
from create_calc_sheet_view_fixture import create  # noqa: E402

HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
OUT = None
FOLDER = 'LiteCore-demo-batch'
DOCUMENT = ROOT / 'wasm_sdk_probe/test-docs/t3-long.odt'
ZOOM = """(() => { const q = s => document.querySelector(s), box = b => { const r = b.getBoundingClientRect();
    return {x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height, disabled: b.disabled,
            visible: getComputedStyle(b).display !== 'none' && r.width > 0}; };
  const p = q('#paper'), t = q('#toolbar').getBoundingClientRect(), d = q('#desk');
  return {deskScrollWidth: d.scrollWidth, deskClientWidth: d.clientWidth, zoomOut: box(q('#zoom-out')), zoomReset: box(q('#zoom-reset')), zoomIn: box(q('#zoom-in')), label: q('#zoom-reset').textContent,
          paper: p.getBoundingClientRect().width, toolbar: [t.x, t.y, t.width, t.height], viewport: [innerWidth, innerHeight]}; })()"""


def check(run, name, passed, actual=None):
    run['checks'].append({'id': name, 'pass': bool(passed), 'actual': actual})


def go(session, instance, name, page):
    s.navigate(session, instance.base + '/index.php/apps/files/files?dir=' + urllib.parse.quote('/' + FOLDER), timeout=120)
    selector = f'[data-cy-files-list-row-name={json.dumps(name)}] [data-cy-files-list-row-name-link]'
    s.wait_until(session, f'(() => document.querySelector({json.dumps(selector)}) !== null)()', 60)
    session.click(selector)
    s.wait_until(session, f'(() => location.pathname.endsWith({json.dumps("/" + page)}))()', 30)


def leave(session, instance):
    s.navigate(session, instance.base + '/index.php/apps/files/', timeout=60)
    time.sleep(3)


def writer(session, kind, instance, run):
    go(session, instance, 'zoom.odt', 'e2-editor.html')
    s.wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore'); return v && JSON.parse(v).done && v; })()", 180)
    time.sleep(2)
    before = s.evaluate(session, ZOOM)
    check(run, 'Z9/all-three-visible', all(before[k]['visible'] and not before[k]['disabled'] for k in ('zoomOut', 'zoomReset', 'zoomIn'))
          and all(before[k]['x'] + before[k]['w'] / 2 <= before['viewport'][0] for k in ('zoomOut', 'zoomReset', 'zoomIn')), before)
    # Spec append 1: only here, on an empty desk, is the first layout measured before the vertical scrollbar exists.
    check(run, 'Z10/fit-has-no-side-scroll', before['deskScrollWidth'] <= before['deskClientWidth'],
          {'scrollWidth': before['deskScrollWidth'], 'clientWidth': before['deskClientWidth'], 'paper': before['paper']})
    (OUT / f'{kind}-writer-rest.png').write_bytes(session.screenshot())
    real.click(session, kind, before['zoomIn']['x'], before['zoomIn']['y'])
    time.sleep(1.5)
    bigger = s.evaluate(session, ZOOM)
    check(run, 'Z9/plus-takes-effect', bigger['paper'] > before['paper'] and bigger['label'] != before['label'],
          {'before': [before['label'], before['paper']], 'after': [bigger['label'], bigger['paper']]})
    real.click(session, kind, bigger['zoomOut']['x'], bigger['zoomOut']['y'])
    time.sleep(1.5)
    smaller = s.evaluate(session, ZOOM)
    check(run, 'Z9/minus-takes-effect', smaller['paper'] < bigger['paper'],
          {'before': [bigger['label'], bigger['paper']], 'after': [smaller['label'], smaller['paper']]})
    real.click(session, kind, smaller['zoomReset']['x'], smaller['zoomReset']['y'])
    time.sleep(1.5)
    reset = s.evaluate(session, ZOOM)
    check(run, 'Z10/fit-returns-to-the-width-it-opened-at', abs(reset['paper'] - before['paper']) < 1 and reset['label'] == before['label'],
          {'before': [before['label'], before['paper']], 'after': [reset['label'], reset['paper']]})
    (OUT / f'{kind}-writer-after.png').write_bytes(session.screenshot())
    leave(session, instance)


def calc(session, kind, instance, run):
    record = {'checks': run['checks']}
    go(session, instance, 'view.ods', 'ods-editor.html')
    s.wait_until(session, '(() => window.__calcEditor?.state?.state === "ready" && Boolean(window.__calcEditor.state.cell))()', 180)
    page = view.Run(session, 'editor', record)
    page.painted(0, 'host-editor/opened')
    first = dict(page.scroll(600, 2500))
    page.hands.click(*page.centre())
    page.idle()
    left = {**view.settle_scroll(session), 'cell': page.cell()}
    check(run, 'setup/host-editor-cell', left['cell'] and left['cell'][1] > 20, {'first': first, 'left': left})
    page.first_visit(1, 'host-editor/first-visit-sheet2', page.tab(1))
    page.returned(0, 'host-editor/back-to-sheet1', page.tab(0), left)
    (OUT / f'{kind}-calc-back-to-sheet1.png').write_bytes(session.screenshot())
    leave(session, instance)


def one(kind, instance, scratch):
    run = {'browser': kind, 'checks': []}
    session = s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(scratch))
    run['version'] = session.version
    try:
        s.browser_login(session, instance.base, instance.password)
        writer(session, kind, instance, run)
        calc(session, kind, instance, run)
    except Exception:  # noqa: BLE001 -- recorded
        run['fatal'] = traceback.format_exc()
        try:
            (OUT / f'{kind}-fatal.png').write_bytes(session.screenshot())
        except Exception:  # noqa: BLE001
            pass
    finally:
        session.close()
    return run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browsers', default='chrome,firefox')
    parser.add_argument('--out', type=Path, default=HERE / 'host-batch')
    args = parser.parse_args()
    global OUT
    OUT = args.out.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    instance = s.Instance(HOST)
    instance.dav('MKCOL', FOLDER)
    report = {'runs': []}
    with tempfile.TemporaryDirectory(dir=ROOT / 'wasm_sdk_probe/build') as scratch:
        ods = create(Path(scratch) / 'fixture')
        # Instance.upload is for files under dist/; these two are not.
        report['uploaded'] = [
            instance.dav('PUT', f'{FOLDER}/zoom.odt', DOCUMENT.read_bytes(), {'Content-Type': 'application/vnd.oasis.opendocument.text'})[0],
            instance.dav('PUT', f'{FOLDER}/view.ods', ods.read_bytes(), {'Content-Type': 'application/vnd.oasis.opendocument.spreadsheet'})[0]]
        for kind in args.browsers.split(','):
            report['runs'].append(one(kind, instance, Path(scratch)))
    report['removed'] = instance.dav('DELETE', FOLDER)[0]
    checks = [c for r in report['runs'] for c in r['checks']]
    report['verdict'] = 'HOST_BATCH_HOLDS' if checks and all(c['pass'] for c in checks) and not any(r.get('fatal') for r in report['runs']) else 'HOST_BATCH_RED'
    (OUT / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    for run in report['runs']:
        print(run['browser'], sum(c['pass'] for c in run['checks']), '/', len(run['checks']), [c['id'] for c in run['checks'] if not c['pass']],
              (run.get('fatal') or '').strip().splitlines()[-1:])
    print(report['verdict'], report.get('removed'))
    return 0 if report['verdict'] == 'HOST_BATCH_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
