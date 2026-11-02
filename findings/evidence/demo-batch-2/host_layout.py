#!/usr/bin/env python3
"""SPEC-P-demo-batch-2 section 3: where Save and Close sit, on the installed host.  T1-T5.

Opens scratch documents from Files as a user does, measures in one window so Writer and Calc are compared with themselves, then
presses Save and Close with a real pointer.  Every check is recorded and the run goes on past a red one.  Chrome also runs a dark
arm by emulating prefers-color-scheme.  Run with host-stack/bin first on PATH.

  python3 -I host_layout.py --out DIR [--browsers chrome,firefox]
"""
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import traceback
import urllib.parse

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
import check_calc_sheet_view as view  # noqa: E402
import check_m3_skeleton_open as s  # noqa: E402
import v21_input as real  # noqa: E402
from create_calc_sheet_view_fixture import create  # noqa: E402

HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
FOLDER = 'LiteCore-layout'
DOCUMENT = ROOT / 'wasm_sdk_probe/test-docs/t3-long.odt'
TOLERANCE = 1
MIN_CONTRAST = 4.5
READ = """(() => { const q = s => document.querySelector(s), root = q('#litecore-editor-root') || q('#litecore-viewer-root');
  const r = root.getBoundingClientRect();
  const box = e => { if (!e) return null; const b = e.getBoundingClientRect();
    return {left: b.left - r.left, right: r.right - b.right, top: b.top, bottom: b.bottom, x: b.x + b.width / 2, y: b.y + b.height / 2, w: b.width, h: b.height}; };
  const shown = e => { const b = e.getBoundingClientRect(), c = getComputedStyle(e); return b.width > 0 && c.display !== 'none' && c.visibility !== 'hidden'; };
  const paint = e => { for (let n = e; n; n = n.parentElement) { const c = getComputedStyle(n).backgroundColor;
      if (c && c !== 'transparent' && !/, 0\\)$/.test(c)) return c; } return 'rgb(255, 255, 255)'; };
  const close = q('#litecore-host-close'), bar = close?.parentElement, toolbar = q('#toolbar');
  const save = q('#toolbar [data-action="save"]') || q('#save-button');
  const bold = q('#toolbar [data-action="set-bold"]') || q('[data-format="bold"]');
  const controls = toolbar ? [...toolbar.querySelectorAll('button,select,input')].filter(shown) : [];
  const after = save?.nextElementSibling;
  return {close: box(close), bar: box(bar), save: box(save), first: controls[0] ? (controls[0].dataset.action || controls[0].id || controls[0].tagName) : null,
    saveIsFirst: Boolean(save) && controls[0] === save, order: controls.map(c => c.dataset.action || c.dataset.format || c.id || c.tagName),
    saveIcon: save?.querySelector('use')?.getAttribute('href') ?? save?.querySelector('path')?.getAttribute('d')?.slice(0, 24) ?? null,
    saveName: save ? (save.getAttribute('aria-label') || save.textContent).trim() : null,
    separator: after ? {tag: after.tagName, cls: after.className, shown: shown(after), width: after.getBoundingClientRect().width} : null,
    toolbarBackground: toolbar ? paint(toolbar) : null,
    saveColor: save ? getComputedStyle(save).color : null, boldColor: bold ? getComputedStyle(bold).color : null,
    saveBackground: save ? paint(save) : null, boldBackground: bold ? paint(bold) : null,
    theme: document.body.dataset.themes ?? null, dark: matchMedia('(prefers-color-scheme: dark)').matches,
    viewport: [innerWidth, innerHeight]}; })()"""
SAVES = "(() => { const v = document.documentElement.getAttribute('data-litecore'); return v ? (JSON.parse(v).saves || []).filter(x => x.settled).length : -1; })()"


def rgb(text):
    numbers = [float(x) for x in re.findall(r'[\d.]+', text)[:3]]
    return numbers if len(numbers) == 3 else None


def contrast(a, b):
    def luminance(c):
        def channel(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * channel(c[0]) + 0.7152 * channel(c[1]) + 0.0722 * channel(c[2])
    high, low = sorted((luminance(rgb(a)), luminance(rgb(b))), reverse=True)
    return round((high + 0.05) / (low + 0.05), 2)


def check(run, name, passed, actual=None):
    run['checks'].append({'id': name, 'pass': bool(passed), 'actual': actual})


def go(session, instance, name, page):
    s.navigate(session, instance.base + '/index.php/apps/files/files?dir=' + urllib.parse.quote('/' + FOLDER), timeout=120)
    selector = f'[data-cy-files-list-row-name={json.dumps(name)}] [data-cy-files-list-row-name-link]'
    s.wait_until(session, f'(() => document.querySelector({json.dumps(selector)}) !== null)()', 60)
    session.click(selector)
    s.wait_until(session, f'(() => location.pathname.endsWith({json.dumps("/" + page)}))()', 30)


def open_writer(session, instance):
    go(session, instance, 'layout.odt', 'e2-editor.html')
    s.wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore'); return v && JSON.parse(v).done && v; })()", 180)
    time.sleep(2)


def open_calc(session, instance):
    go(session, instance, 'layout.ods', 'ods-editor.html')
    s.wait_until(session, '(() => window.__calcEditor?.state?.state === "ready" && Boolean(window.__calcEditor.state.cell))()', 180)
    time.sleep(2)


def press_save_and_close(session, kind, instance, run, tag, edit):
    before = s.evaluate(session, SAVES)
    edit()
    box = s.evaluate(session, READ)
    real.click(session, kind, box['save']['x'], box['save']['y'])
    until, count = time.monotonic() + 40, before
    while time.monotonic() < until and count <= before:
        count = s.evaluate(session, SAVES)
        time.sleep(0.3)
    check(run, f'T3/{tag}-save-by-pointer', count > before, {'before': before, 'after': count})
    time.sleep(1)
    box = s.evaluate(session, READ)
    real.click(session, kind, box['close']['x'], box['close']['y'])
    until, where = time.monotonic() + 20, ''
    while time.monotonic() < until and '/apps/files' not in where:
        where = s.evaluate(session, 'location.pathname')
        time.sleep(0.3)
    check(run, f'T3/{tag}-close-returns-to-files', '/apps/files' in where, where)
    time.sleep(3)


def one(kind, instance, scratch, out, file_id):
    run = {'browser': kind, 'checks': []}
    session = s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(scratch))
    run['version'] = session.version
    try:
        s.browser_login(session, instance.base, instance.password)
        open_writer(session, instance)
        writer = s.evaluate(session, READ)
        (out / f'{kind}-writer.png').write_bytes(session.screenshot())
        wbox = s.evaluate(session, "(() => { const r = document.querySelector('#paper').getBoundingClientRect(); return [r.left + 200, r.top + 160]; })()")

        def edit_writer():
            real.click(session, kind, *wbox)
            time.sleep(0.6)
            real.key(session, kind, 'q')
            time.sleep(0.8)
        press_save_and_close(session, kind, instance, run, 'writer', edit_writer)
        open_calc(session, instance)
        calc = s.evaluate(session, READ)
        (out / f'{kind}-calc.png').write_bytes(session.screenshot())
        hands = view.Hands(session)

        def edit_calc():
            hands.text('Q')
            time.sleep(0.5)
            hands.key('Enter')
            time.sleep(1.5)
        press_save_and_close(session, kind, instance, run, 'calc', edit_calc)
        s.navigate(session, instance.base + f'/index.php/apps/litecore/r/ods-viewer.html?fileId={file_id}', timeout=60)
        s.wait_until(session, "(() => document.querySelector('#litecore-host-close') !== null)()", 60)
        time.sleep(2)
        viewer = s.evaluate(session, READ)
        (out / f'{kind}-viewer.png').write_bytes(session.screenshot())
        run['read'] = {'writer': writer, 'calc': calc, 'viewer': viewer}
        gaps = {k: v['close']['right'] for k, v in run['read'].items() if v['close']}
        check(run, 'T1/close-right-gap-equal', len(gaps) == 3 and max(gaps.values()) - min(gaps.values()) <= TOLERANCE, gaps)
        for name, read in run['read'].items():
            check(run, f'T1/{name}-close-in-title-row', read['close'] and read['bar'] and read['close']['top'] >= read['bar']['top'] - 1
                  and read['close']['bottom'] <= read['bar']['bottom'] + 1, {'close': read['close'], 'bar': read['bar']})
        check(run, 'T2/save-is-first', writer['saveIsFirst'] and calc['saveIsFirst'], {'writer': writer['first'], 'calc': calc['first']})
        check(run, 'T2/save-left-gap-equal', abs(writer['save']['left'] - calc['save']['left']) <= TOLERANCE,
              {'writer': writer['save']['left'], 'calc': calc['save']['left']})
        check(run, 'T2/save-size-equal', abs(writer['save']['w'] - calc['save']['w']) <= TOLERANCE and abs(writer['save']['h'] - calc['save']['h']) <= TOLERANCE,
              {'writer': [writer['save']['w'], writer['save']['h']], 'calc': [calc['save']['w'], calc['save']['h']]})
        check(run, 'T2/save-same-icon', writer['saveIcon'] and writer['saveIcon'] == calc['saveIcon'], {'writer': writer['saveIcon'], 'calc': calc['saveIcon']})
        check(run, 'T2/save-is-named', '儲存' in (writer['saveName'] or '') and '儲存' in (calc['saveName'] or ''),
              {'writer': writer['saveName'], 'calc': calc['saveName']})
        check(run, 'T5/separator-after-save', writer['separator'] and writer['separator']['shown'] and writer['separator']['width'] >= 1, writer['separator'])
        run['order'] = {'writer': writer['order'], 'calc': calc['order']}
    except Exception:  # noqa: BLE001 -- recorded
        run['fatal'] = traceback.format_exc()
        try:
            (out / f'{kind}-fatal.png').write_bytes(session.screenshot())
        except Exception:  # noqa: BLE001
            pass
    finally:
        session.close()
    return run


def dark(instance, out):
    """T4: Nextcloud's default theme follows the system; only the colours are read, nothing is saved."""
    run = {'browser': 'chrome-dark', 'checks': []}
    session = s.EventChrome('cold')
    try:
        session.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': 'dark'}]})
        s.browser_login(session, instance.base, instance.password)
        reads = {}
        for name, opener in (('writer', open_writer), ('calc', open_calc)):
            opener(session, instance)
            read = s.evaluate(session, READ)
            reads[name] = read
            (out / f'chrome-dark-{name}.png').write_bytes(session.screenshot())
            check(run, f'T4/{name}-contrast', contrast(read['saveColor'], read['saveBackground']) >= MIN_CONTRAST
                  and contrast(read['boldColor'], read['boldBackground']) >= MIN_CONTRAST,
                  {'save': [read['saveColor'], read['saveBackground'], contrast(read['saveColor'], read['saveBackground'])],
                   'bold': [read['boldColor'], read['boldBackground'], contrast(read['boldColor'], read['boldBackground'])],
                   'dark': read['dark'], 'theme': read['theme']})
            s.navigate(session, instance.base + '/index.php/apps/files/', timeout=60)
            time.sleep(3)
    except Exception:  # noqa: BLE001 -- recorded
        run['fatal'] = traceback.format_exc()
    finally:
        session.close()
    return run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browsers', default='chrome,firefox')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    instance = s.Instance(HOST)
    instance.dav('MKCOL', FOLDER)
    report = {'runs': []}
    with tempfile.TemporaryDirectory(dir=ROOT / 'wasm_sdk_probe/build') as scratch:
        ods = create(Path(scratch) / 'fixture')
        instance.dav('PUT', f'{FOLDER}/layout.ods', ods.read_bytes(), {'Content-Type': 'application/vnd.oasis.opendocument.spreadsheet'})
        instance.dav('PUT', f'{FOLDER}/layout.odt', DOCUMENT.read_bytes(), {'Content-Type': 'application/vnd.oasis.opendocument.text'})
        body = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns"><d:prop><oc:fileid/></d:prop></d:propfind>')
        answer = instance.dav('PROPFIND', f'{FOLDER}/layout.ods', body, {'Depth': '0', 'Content-Type': 'application/xml'})[1]
        file_id = int(re.search(rb'<oc:fileid>(\d+)</oc:fileid>', answer).group(1))
        for kind in args.browsers.split(','):
            report['runs'].append(one(kind, instance, Path(scratch), out, file_id))
            (out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
        if 'chrome' in args.browsers:
            report['runs'].append(dark(instance, out))
    report['removed'] = instance.dav('DELETE', FOLDER)[0]
    checks = [c for r in report['runs'] for c in r['checks']]
    report['verdict'] = 'LAYOUT_HOLDS' if checks and all(c['pass'] for c in checks) and not any(r.get('fatal') for r in report['runs']) else 'LAYOUT_RED'
    (out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    for run in report['runs']:
        print(run['browser'], sum(c['pass'] for c in run['checks']), '/', len(run['checks']), [c['id'] for c in run['checks'] if not c['pass']],
              (run.get('fatal') or '').strip().splitlines()[-1:])
    print(report['verdict'], report.get('removed'))
    return 0 if report['verdict'] == 'LAYOUT_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
