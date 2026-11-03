#!/usr/bin/env python3
"""SPEC-P-demo-batch-4, the new controls on the installed host: the heading menu, the two list toggles, findings 180, 181 and 182.

The owner's path, from ../host-0.2.51/host_batch3.py: open from Files, real pointer and keys, press Save, then read the file back over WebDAV,
which is what the host holds and not what the page says.  Then the file is opened again from Files and the toolbar is read.  T6 on the menu:
Chrome reads every control with the menu open under the light and the dark theme.  Run on 0.2.51 first: the menu is hidden there, and that is
the tool's red.  Run with host-stack/bin first on PATH.

  python3 -I host_batch4.py --out DIR [--browsers chrome,firefox]
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


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


layout = load('host_layout', HERE.parent / 'demo-batch-2/host_layout.py')
s, real, HOST, contrast = layout.s, layout.real, layout.HOST, layout.contrast
import check_writer_toggle as t  # noqa: E402
from check_writer_toggle import BODY, BODY2, BULLET, H1, H2, H3, JULIET, KILO, NUMBER, frames, shape  # noqa: E402

FOLDER = 'LiteCore-batch4'
ODT = 'application/vnd.oasis.opendocument.text'
MENU = '#heading-menu-button'
BOX = """(() => { const e = document.querySelector(ARG), r = e?.getBoundingClientRect();
  if (!r) return null; const c = getComputedStyle(e);
  return {x: r.x + r.width / 2, y: r.y + r.height / 2, right: r.right, bottom: r.bottom, width: r.width, disabled: e.disabled === true,
          shown: r.width > 0 && c.display !== 'none' && c.visibility !== 'hidden', hit: document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)?.closest(ARG) === e,
          viewport: [innerWidth, innerHeight]}; })()"""
RED = "(() => { const t = document.querySelector('#toast'); return t?.classList.contains('bad') || t?.classList.contains('error') ? t.textContent : null; })()"
STATE = "document.querySelector('#state-pill')?.dataset.state ?? null"
PAPER = """(() => { const r = document.querySelector('#paper').getBoundingClientRect(), d = document.querySelector('#desk').getBoundingClientRect();
  return [r.x + r.width * 0.3, Math.max(r.y, d.y) + 130]; })()"""
THEME = """(() => { const shown = e => { const b = e.getBoundingClientRect(), c = getComputedStyle(e); return b.width > 0 && c.display !== 'none' && c.visibility !== 'hidden'; };
  const paint = e => { for (let n = e; n; n = n.parentElement) { const c = getComputedStyle(n).backgroundColor;
      if (c && c !== 'transparent' && !/, 0\\)$/.test(c)) return c; } return 'rgb(255, 255, 255)'; };
  const out = {}; for (const e of document.querySelectorAll('.toolbar button, #heading-menu button')) { if (!shown(e)) continue; const c = getComputedStyle(e);
    out[e.dataset.action || e.id || e.textContent.trim()] = {color: c.color, background: paint(e), opacity: c.opacity, disabled: e.disabled === true}; }
  return out; })()"""


def check(run, name, passed, actual=None):
    run['checks'].append({'id': name, 'pass': bool(passed), 'actual': actual})


def box(session, selector):
    return s.evaluate(session, BOX.replace('ARG', json.dumps(selector)))


def press(session, kind, selector, wait=1.0):
    b = box(session, selector)
    real.click(session, kind, b['x'], b['y'])
    time.sleep(wait)


def level(session, kind, action):
    press(session, kind, MENU, .4)
    press(session, kind, f'#heading-menu [data-action="{action}"]')


def key(session, kind, name, mods=(), times=1):
    for _ in range(times):
        real.key(session, kind, name, mods)
        time.sleep(.4)


def to_paragraph(session, kind, index):
    key(session, kind, 'Home', ('ctrl',))
    key(session, kind, 'ArrowDown', times=index)


def save(session, kind):
    before = s.evaluate(session, layout.SAVES)
    press(session, kind, '[data-action="save"]')
    until, count = time.monotonic() + 40, before
    while time.monotonic() < until and count <= before:
        count = s.evaluate(session, layout.SAVES)
        time.sleep(.3)
    return count > before


def open_writer(session, kind, instance):
    layout.go(session, instance, f'levels-{kind}.odt', 'e2-editor.html')
    s.wait_until(session, "(() => { const v = document.documentElement.getAttribute('data-litecore'); return v && JSON.parse(v).done && v; })()", 180)
    time.sleep(2)


def leave(session, instance):
    s.navigate(session, instance.base + '/index.php/apps/files/', timeout=60)
    time.sleep(3)


def writer(session, kind, instance, run):
    open_writer(session, kind, instance)
    shown = {n: box(session, n) for n in (MENU, BULLET, NUMBER)}
    check(run, 'H4/controls-shown', all(b and b['shown'] and b['hit'] and b['right'] <= b['viewport'][0] for b in shown.values()), shown)
    if not all(b and b['shown'] for b in shown.values()):
        return
    hidden = s.evaluate(session, "[...document.querySelectorAll('[data-setter-group]')].every(n => n.hidden)")
    check(run, 'H4/the-old-five-are-gone', hidden, hidden)

    real.click(session, kind, *s.evaluate(session, PAPER))
    time.sleep(.8)
    press(session, kind, MENU, .5)
    items = [box(session, f'#heading-menu [data-action="{a}"]') for a in ('set-paragraph-body', 'toggle-heading-1', 'toggle-heading-2', 'toggle-heading-3', 'toggle-heading-4')]
    check(run, 'H4/menu-inside-the-window-and-on-top',
          all(b and b['shown'] and b['hit'] and b['right'] <= b['viewport'][0] and b['bottom'] <= b['viewport'][1] for b in items), items)
    (OUT / f'{kind}-menu.png').write_bytes(session.screenshot())
    key(session, kind, 'Escape')
    check(run, 'H4/menu-closes-on-escape', s.evaluate(session, "document.querySelector('#heading-menu').hidden") is True)

    # Finding 180 and the level: the q lands where the caret was.
    to_paragraph(session, kind, BODY2)
    key(session, kind, 'Home')
    key(session, kind, 'ArrowRight', times=2)
    level(session, kind, 'toggle-heading-2')
    key(session, kind, 'q')
    # A document's own heading comes off through 內文.
    to_paragraph(session, kind, H1)
    level(session, kind, 'set-paragraph-body')
    # One button each way.
    to_paragraph(session, kind, BODY)
    press(session, kind, BULLET)
    press(session, kind, BULLET)
    press(session, kind, NUMBER)
    to_paragraph(session, kind, JULIET)
    press(session, kind, BULLET)
    # Finding 182: from inside a paragraph into the next.
    to_paragraph(session, kind, H2)
    key(session, kind, 'Home')
    key(session, kind, 'ArrowRight', times=2)
    key(session, kind, 'ArrowDown', ('shift',))
    level(session, kind, 'toggle-heading-1')
    check(run, 'H4/range-keeps-the-session', s.evaluate(session, STATE) == 'ready', s.evaluate(session, STATE))
    # Finding 181: a selection at a paragraph's start.
    to_paragraph(session, kind, KILO)
    key(session, kind, 'Home')
    key(session, kind, 'ArrowRight', ('shift',), times=3)
    level(session, kind, 'toggle-heading-3')
    check(run, 'H4/no-red-toast', s.evaluate(session, RED) is None, s.evaluate(session, RED))
    check(run, 'H4/save-settled', save(session, kind))

    raw = instance.dav('GET', f'{FOLDER}/levels-{kind}.odt')[1]
    (OUT / f'{kind}-host.odt').write_bytes(raw)
    rows = shape(raw)
    check(run, 'H4/caret-and-level', rows[BODY2]['level'] == 2 and rows[BODY2]['text'] == 'BRqAVO plain paragraph two', rows[BODY2])
    check(run, 'H4/a-heading-comes-off', rows[H1]['level'] == 0, rows[H1])
    check(run, 'H4/bullet-off-then-number', rows[BODY]['kind'] == 'ol', rows[BODY])
    check(run, 'H4/bullet-on', rows[JULIET]['kind'] == 'ul', rows[JULIET])
    check(run, 'H4/finding-182-both-paragraphs', rows[H2]['level'] == 1 and rows[H3]['level'] == 1, [rows[H2], rows[H3]])
    check(run, 'H4/finding-181-the-whole-paragraph-no-frame', rows[KILO]['level'] == 3 and frames(raw) == 0, {'row': rows[KILO], 'frames': frames(raw)})
    leave(session, instance)

    open_writer(session, kind, instance)
    real.click(session, kind, *s.evaluate(session, PAPER))
    time.sleep(.8)
    to_paragraph(session, kind, BODY2)
    time.sleep(1)
    press(session, kind, MENU, .5)
    checked = s.evaluate(session, "[...document.querySelectorAll('#heading-menu button')].filter(b => b.getAttribute('aria-checked') === 'true').map(b => b.dataset.action)")
    check(run, 'H4/opened-again-the-menu-names-the-level', checked == ['toggle-heading-2'], checked)
    (OUT / f'{kind}-reopened.png').write_bytes(session.screenshot())
    key(session, kind, 'Escape')
    leave(session, instance)


def theme(session, instance, run):
    reads = {}
    for scheme in ('light', 'dark'):
        session.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': scheme}]})
        open_writer(session, 'chrome', instance)
        real.click(session, 'chrome', *s.evaluate(session, PAPER))
        time.sleep(.8)
        press(session, 'chrome', MENU, .6)
        reads[scheme] = s.evaluate(session, THEME)
        (OUT / f'theme-{scheme}.png').write_bytes(session.screenshot())
        key(session, 'chrome', 'Escape')
        leave(session, instance)
    session.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': 'light'}]})
    light, dark = reads['light'], reads['dark']
    (OUT / 'theme.json').write_text(json.dumps(reads, indent=1, ensure_ascii=False) + '\n')
    check(run, 'T6/menu-items-read', all(a in dark for a in ('toggle-heading-1', 'toggle-heading-4', 'set-paragraph-body')), sorted(dark))
    check(run, 'T6/the-same-under-both-themes', light == dark, {k: (light.get(k), dark.get(k)) for k in sorted(set(light) | set(dark)) if light.get(k) != dark.get(k)})
    low = {k: contrast(v['color'], v['background']) for k, v in dark.items() if not v['disabled'] and contrast(v['color'], v['background']) < 4.5}
    check(run, 'T6/contrast', not low, low)


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
            instance.dav('PUT', f'{FOLDER}/levels-{kind}.odt', t.LEVELS.read_bytes(), {'Content-Type': ODT})
            run = {'browser': kind, 'checks': []}
            report['runs'].append(run)
            session = s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(Path(scratch)))
            run['version'] = session.version
            try:
                s.browser_login(session, instance.base, instance.password)
                writer(session, kind, instance, run)
                if kind == 'chrome' and run['checks'] and run['checks'][0]['pass']:
                    theme(session, instance, run)
            except Exception:  # noqa: BLE001 -- recorded
                run['fatal'] = traceback.format_exc()
                (OUT / f'{kind}-fatal.png').write_bytes(session.screenshot())
            finally:
                session.close()
    report['removed'] = instance.dav('DELETE', FOLDER)[0]
    checks = [c for r in report['runs'] for c in r['checks']]
    report['verdict'] = 'H4_HOLDS' if checks and all(c['pass'] for c in checks) and not any(r.get('fatal') for r in report['runs']) else 'H4_RED'
    (OUT / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'], [(c['id'], c['pass']) for c in checks], [(r.get('fatal') or '')[-300:] for r in report['runs']])
    return 0 if report['verdict'] == 'H4_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
