#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 P3, the new controls on the installed host: alignment in Writer, colour, fill and alignment in Calc.

The owner's path: open from Files, real pointer and keys, press Save, then read the file back over WebDAV, which is what the host holds
and not what the page says.  Calc is opened again from Files.  A mirror cannot show this: the host hides parts of the toolbar, sizes the
window, and owns the save.  Chrome also reads the Writer buttons under the dark theme.  Run on 0.2.50 first: the buttons are hidden
there, and that is the tool's red.  Run with host-stack/bin first on PATH.

  python3 -I host_batch3.py --out DIR [--browsers chrome,firefox]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'wasm_sdk_probe/tools'))
spec = importlib.util.spec_from_file_location('host_layout', ROOT / 'findings/evidence/demo-batch-2/host_layout.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
s, real, HOST, contrast = layout.s, layout.real, layout.HOST, layout.contrast
import check_writer_align as a  # noqa: E402
from probe_calc_style_native import cell_style  # noqa: E402

FOLDER = 'LiteCore-batch3'
ODT = 'application/vnd.oasis.opendocument.text'
ODS = 'application/vnd.oasis.opendocument.spreadsheet'
FIXTURE_ODS = ROOT / 'findings/evidence/host-0.2.50/files-workflow-01/fixture/cell-editing.ods'
BOX = """(() => { const e = document.querySelector(ARG), r = e?.getBoundingClientRect();
  if (!r) return null; const c = getComputedStyle(e);
  return {x: r.x + r.width / 2, y: r.y + r.height / 2, right: r.right, bottom: r.bottom, width: r.width, disabled: e.disabled === true,
          shown: r.width > 0 && c.display !== 'none' && c.visibility !== 'hidden', hit: document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)?.closest(ARG) === e,
          viewport: [innerWidth, innerHeight]}; })()"""
INK = """(() => { const q = s => document.querySelector(s), paint = e => { for (let n = e; n; n = n.parentElement) { const c = getComputedStyle(n).backgroundColor;
    if (c && c !== 'transparent' && !/, 0\\)$/.test(c)) return c; } return 'rgb(255, 255, 255)'; };
  return ['set-align-left', 'set-align-center', 'set-align-right', 'set-align-justify', 'set-bold'].map(n => { const e = q(`[data-action="${n}"]`);
    return [n, getComputedStyle(e).color, paint(e)]; }); })()"""
RED = "(() => { const t = document.querySelector('#toast'); return t?.classList.contains('bad') || t?.classList.contains('error') ? t.textContent : null; })()"
PAPER = """(() => { const r = document.querySelector('#paper').getBoundingClientRect(), d = document.querySelector('#desk').getBoundingClientRect();
  return [r.x + r.width * 0.3, Math.max(r.y, d.y) + 130]; })()"""


def check(run, name, passed, actual=None):
    run['checks'].append({'id': name, 'pass': bool(passed), 'actual': actual})


def leave(session, instance):
    s.navigate(session, instance.base + '/index.php/apps/files/', timeout=60)
    time.sleep(3)


def box(session, selector):
    return s.evaluate(session, BOX.replace('ARG', json.dumps(selector)))


def press(session, kind, selector):
    b = box(session, selector)
    real.click(session, kind, b['x'], b['y'])
    time.sleep(1.2)


def save(session, kind, selector):
    before = s.evaluate(session, layout.SAVES)
    press(session, kind, selector)
    until, count = time.monotonic() + 40, before
    while time.monotonic() < until and count <= before:
        count = s.evaluate(session, layout.SAVES)
        time.sleep(.3)
    return count > before


def writer(session, kind, instance, run):
    layout.go(session, instance, f'align-{kind}.odt', 'e2-editor.html')
    s.wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore'); return v && JSON.parse(v).done && v; })()", 180)
    time.sleep(2)
    shown = {n: box(session, f'[data-action="set-align-{n}"]') for n in ('left', 'center', 'right', 'justify')}
    check(run, 'P3/writer/four-buttons-shown', all(b and b['shown'] and b['hit'] and b['right'] <= b['viewport'][0] for b in shown.values()), shown)
    if not all(b and b['shown'] for b in shown.values()):
        return
    if kind == 'chrome':
        session.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': 'dark'}]})
        time.sleep(1)
        ink = s.evaluate(session, INK)
        session.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': 'light'}]})
        time.sleep(1)
        check(run, 'P3/writer/dark-theme-reads', all(contrast(c, b) >= 4.5 and c == ink[-1][1] for _, c, b in ink), ink)
    real.click(session, kind, *s.evaluate(session, PAPER))
    time.sleep(.8)
    real.key(session, kind, 'Home', ('ctrl',))
    time.sleep(.6)
    real.key(session, kind, 'ArrowDown')
    time.sleep(.6)
    real.key(session, kind, 'Home')
    time.sleep(.4)
    for _ in range(2):
        real.key(session, kind, 'ArrowRight')
        time.sleep(.4)
    press(session, kind, '[data-action="set-align-right"]')
    real.key(session, kind, 'q')
    time.sleep(1)
    check(run, 'P3/writer/no-red-toast', s.evaluate(session, RED) is None, s.evaluate(session, RED))
    check(run, 'P3/writer/save-settled', save(session, kind, '[data-action="save"]'))
    raw = instance.dav('GET', f'{FOLDER}/align-{kind}.odt')[1]
    aligns, texts = a.aligns(raw), a.texts(raw)
    check(run, 'P3/writer/the-host-holds-it', aligns[1] == 'right' and texts[1] == 'BRqAVO plain paragraph two', {'align': aligns[1], 'text': texts[1]})
    (OUT / f'{kind}-writer.png').write_bytes(session.screenshot())
    leave(session, instance)


def calc_open(session, kind, instance):
    layout.go(session, instance, f'style-{kind}.ods', 'ods-editor.html')
    s.wait_until(session, '(() => window.__calcEditor?.state?.state === "ready" && Boolean(window.__calcEditor.state.cell))()', 180)
    time.sleep(2)


def choose(session, kind, key, color):
    press(session, kind, f'[data-color-menu="{key}"]')
    s.wait_until(session, "(() => document.querySelector('#color-popover').hidden === false)()", 5)
    swatch = box(session, f'[data-swatch="{color}"]')
    inside = swatch and swatch['shown'] and swatch['hit'] and swatch['right'] <= swatch['viewport'][0] and swatch['bottom'] <= swatch['viewport'][1]
    press(session, kind, f'[data-swatch="{color}"]')
    return inside, swatch


def calc(session, kind, instance, run):
    calc_open(session, kind, instance)
    b = box(session, '[data-align="center"]')
    check(run, 'P3/calc/controls-shown', b and b['shown'] and b['hit'] and not b['disabled'], b)
    if not (b and b['shown']):
        return
    inside, swatch = choose(session, kind, 'textColor', '#cc0000')
    check(run, 'P3/calc/palette-inside-the-window-and-on-top', inside, swatch)
    choose(session, kind, 'backColor', '#ffe599')
    press(session, kind, '[data-align="center"]')
    cell = s.evaluate(session, 'window.__calcEditor.state.cell')
    check(run, 'P3/calc/state', (cell.get('textColor'), cell.get('backColor'), cell.get('horizontalAlign')) == ('#cc0000', '#ffe599', 'center'), cell)
    check(run, 'P3/calc/no-red-toast', s.evaluate(session, RED) is None, s.evaluate(session, RED))
    (OUT / f'{kind}-calc.png').write_bytes(session.screenshot())
    check(run, 'P3/calc/save-settled', save(session, kind, '#save-button'))
    path = OUT / f'{kind}-host.ods'
    path.write_bytes(instance.dav('GET', f'{FOLDER}/style-{kind}.ods')[1])
    got = cell_style(path, 0, 0, 0)
    check(run, 'P3/calc/the-host-holds-it', (got.get('color'), got.get('background'), got.get('align')) == ('#cc0000', '#ffe599', 'center'), got)
    leave(session, instance)
    calc_open(session, kind, instance)
    cell = s.evaluate(session, 'window.__calcEditor.state.cell')
    check(run, 'P3/calc/opened-again', (cell.get('textColor'), cell.get('backColor'), cell.get('horizontalAlign')) == ('#cc0000', '#ffe599', 'center'), cell)
    leave(session, instance)


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browsers', default='chrome,firefox')
    args = parser.parse_args()
    OUT = args.out.resolve()
    OUT.mkdir(parents=True, exist_ok=False)
    instance = s.Instance(HOST)
    try:
        instance.dav('DELETE', FOLDER)  # this tool's own folder, left by a run that died
    except Exception:  # noqa: BLE001 -- absent, the usual case
        pass
    instance.dav('MKCOL', FOLDER)
    layout.FOLDER = FOLDER
    report = {'runs': []}
    with tempfile.TemporaryDirectory(dir=ROOT / 'wasm_sdk_probe/build') as scratch:
        for kind in args.browsers.split(','):
            instance.dav('PUT', f'{FOLDER}/align-{kind}.odt', a.FIXTURE.read_bytes(), {'Content-Type': ODT})
            instance.dav('PUT', f'{FOLDER}/style-{kind}.ods', FIXTURE_ODS.read_bytes(), {'Content-Type': ODS})
            run = {'browser': kind, 'checks': []}
            report['runs'].append(run)
            session = s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(Path(scratch)))
            run['version'] = session.version
            try:
                s.browser_login(session, instance.base, instance.password)
                writer(session, kind, instance, run)
                calc(session, kind, instance, run)
            except Exception:  # noqa: BLE001 -- recorded
                run['fatal'] = traceback.format_exc()
                (OUT / f'{kind}-fatal.png').write_bytes(session.screenshot())
            finally:
                session.close()
    report['removed'] = instance.dav('DELETE', FOLDER)[0]
    checks = [c for r in report['runs'] for c in r['checks']]
    report['verdict'] = 'P3_FEATURES_HOLD' if checks and all(c['pass'] for c in checks) and not any(r.get('fatal') for r in report['runs']) else 'P3_FEATURES_RED'
    (OUT / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'], [(c['id'], c['pass']) for c in checks], [(r.get('fatal') or '')[-300:] for r in report['runs']])
    return 0 if report['verdict'] == 'P3_FEATURES_HOLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
