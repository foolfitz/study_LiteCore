#!/usr/bin/env python3
"""First look at the icon toolbar inside Nextcloud on 0.2.45 (spec v29 append 4: it was only measured on the mirror).  Not a gate.

Opens a scratch document from Files the way a user does, by real pointer hovers Bold, types with real keys, saves nothing on
purpose beyond what the product does, then leaves and removes the scratch folder.  Screenshots: {browser}-rest.png, -hover.png,
-typed.png.  Run with host-stack/bin first on PATH.
"""
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
import check_m3_skeleton_open as s  # noqa: E402
import v21_input as real  # noqa: E402

HOST = Path('/home/jiajun/Projects/Nextcloud_Apps/litecore')
FOLDER = 'LiteCore-first-look'
NAME = 'look.odt'
FIXTURE = ROOT / 'wasm_sdk_probe/dist/e1-fixtures/list-contexts.odt'
TOOLBAR = """(() => { const t = document.querySelector('#toolbar'); if (!t) return null;
  const rows = [...t.querySelectorAll('button')].map((b) => { const r = b.getBoundingClientRect();
    const svg = b.querySelector('svg'); const v = getComputedStyle(b).visibility !== 'hidden' && r.width > 0;
    return {action: b.dataset.action || b.id, visible: v, x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height,
            icon: svg ? svg.getBoundingClientRect().width : 0, tip: b.getAttribute('data-tip')}; });
  const r = t.getBoundingClientRect();
  return {rect: [r.x, r.y, r.width, r.height], buttons: rows, overflowsRight: rows.some((b) => b.visible && b.x + b.w / 2 > innerWidth),
          viewport: [innerWidth, innerHeight], topIsPage: window === window.top}; })()"""
TIP = """(() => { const b = document.querySelector('#toolbar button[data-tip]:hover'); if (!b) return null;
  const c = getComputedStyle(b, '::after'); return {tip: b.getAttribute('data-tip'), visibility: c.visibility, opacity: c.opacity, content: c.content}; })()"""


def pointer(session, kind, x, y):
    if kind == 'chrome':
        real._cdp_mouse(session, 'mouseMoved', x, y, 0)
    else:
        real._wd_pointer(session, [{'type': 'pointerMove', 'x': int(x), 'y': int(y), 'origin': 'viewport'}])


def one(kind, instance, scratch):
    record = {'browser': kind}
    session = (s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(scratch)))
    record['version'] = session.version
    try:
        s.browser_login(session, instance.base, instance.password)
        s.navigate(session, instance.base + '/index.php/apps/files/files?dir=/' + FOLDER, timeout=120)
        selector = f'[data-cy-files-list-row-name={json.dumps(NAME)}] [data-cy-files-list-row-name-link]'
        s.wait_until(session, f'(() => document.querySelector({json.dumps(selector)}) !== null)()', 60)
        session.click(selector)
        s.wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore'); return v && JSON.parse(v).done && v; })()", 300)
        time.sleep(2)
        rows = s.evaluate(session, TOOLBAR)
        record['toolbar'] = rows
        (HERE / f'{kind}-rest.png').write_bytes(session.screenshot())
        bold = next((b for b in rows['buttons'] if b['action'] == 'set-bold'), None) if rows else None
        if bold:
            pointer(session, kind, bold['x'], bold['y'])
            time.sleep(0.6)
            record['hover'] = s.evaluate(session, TIP)
            (HERE / f'{kind}-hover.png').write_bytes(session.screenshot())
            pointer(session, kind, 700, 700)
        s.evaluate(session, s.POINT_AT.replace('ARG_X', '0.35').replace('ARG_Y', '0.28'))
        time.sleep(1)
        for letter in 'hello':
            real.key(session, kind, letter)
            time.sleep(0.08)
        time.sleep(1)
        record['state'] = s.product_state(session)
        (HERE / f'{kind}-typed.png').write_bytes(session.screenshot())
        s.navigate(session, instance.base + '/index.php/apps/files/', timeout=60)
        time.sleep(3)
    except Exception as error:  # noqa: BLE001 -- recorded
        record['fatal'] = f'{type(error).__name__}: {error}'
    finally:
        session.close()
    return record


def main():
    instance = s.Instance(HOST)
    instance.dav('MKCOL', FOLDER)
    uploaded = instance.upload(FIXTURE, f'{FOLDER}/{NAME}')
    report = {'uploaded': uploaded['putStatus'], 'runs': []}
    with tempfile.TemporaryDirectory(dir=ROOT / 'wasm_sdk_probe/build') as scratch:
        for kind in ('chrome', 'firefox'):
            report['runs'].append(one(kind, instance, Path(scratch)))
    (HERE / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    for run in report['runs']:
        t = run.get('toolbar') or {}
        visible = [b for b in t.get('buttons', []) if b['visible']]
        print(run['browser'], 'fatal', run.get('fatal'), 'rect', t.get('rect'), 'visible', len(visible), 'of', len(t.get('buttons', [])),
              'sizes', sorted({(b['w'], b['h']) for b in visible}), 'icons', sorted({b['icon'] for b in visible}),
              'overflow', t.get('overflowsRight'), 'viewport', t.get('viewport'), 'hover', run.get('hover'), 'latency', (run.get('state') or {}).get('latency'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
