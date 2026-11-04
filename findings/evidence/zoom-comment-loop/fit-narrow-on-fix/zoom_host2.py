"""Diagnostic (not evidence): the owner's 1-1 on the host -- toolbar zoom-in step by step, text pixels after each step.

  PATH=<repo>/wasm_sdk_probe/host-stack/bin:$PATH python3 -I zoom_host.py <repo> <out-dir> chrome|firefox [doc ...]
Own folder zoom-diag/ on admin; deleted at the end.
"""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import traceback

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
KIND = sys.argv[3]
DOCS = sys.argv[4:] or ['l1', 't3']
OUT.mkdir(parents=True, exist_ok=True)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b8 = load('host_batch8', ROOT / 'findings/evidence/host-0.2.56/host_batch8.py')
h, s, b6 = b8.h, b8.s, b8.b6
from PIL import Image  # noqa: E402


OBSERVER = r"""(() => {
  const rec = window.__zd = {paints: [], toasts: [], errors: []};
  const posted = {};
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) { super(url, options);
      this.addEventListener('message', ev => { const m = ev.data;
        if (m?.kind === 'response' && posted[m.requestId]) { const row = posted[m.requestId]; delete posted[m.requestId];
          row.ms = Math.round(performance.now() - row.at); row.ok = m.ok; row.err = m.ok ? null : (m.error?.code || JSON.stringify(m.error)).slice(0, 120);
          const r = m.result; if (r) { row.res = {w: r.width, h: r.height, changed: r.documentSizeChanged, dw: r.documentWidthTwips, dh: r.documentHeightTwips};
            if (r.pixels) { const p = new Uint8Array(r.pixels); let op = 0, dark = 0, n = 0; for (let i = 3; i < p.length; i += 4 * 97) { n++; if (p[i] > 128) op++; if (p[i] > 128 && p[i-1] + p[i-2] + p[i-3] < 300) dark++; }
              row.res.len = p.length; row.res.opaque = n ? +(op / n).toFixed(3) : null; row.res.dark = dark; } } } }); }
    postMessage(m, ...rest) {
      if (m?.kind === 'request' && m.operation === 'paint') { const p = m.payload;
        const row = {at: performance.now(), y: p.yTwips, hT: p.heightTwips, wT: p.widthTwips, cw: p.canvasWidthPx, ch: p.canvasHeightPx, label: document.querySelector('#zoom-reset')?.textContent};
        rec.paints.push(row); posted[m.requestId] = row; }
      return super.postMessage(m, ...rest); }
  };
  addEventListener('error', e => rec.errors.push(String(e.message)));
  addEventListener('unhandledrejection', e => rec.errors.push('rej ' + String(e.reason?.message || e.reason)));
  const watch = () => { const t = document.querySelector('#toast'); if (!t) return setTimeout(watch, 200);
    new MutationObserver(() => { const s = t.textContent.trim(); if (s && rec.toasts.at(-1) !== s) rec.toasts.push(s); }).observe(t, {childList: true, subtree: true, characterData: true}); };
  watch();
})();"""

FOLDER = 'zoom-diag'
SOURCES = {'l1': ROOT / 'wasm_sdk_probe/test-docs/r7-compat/l1-layout-table-image.odt',
           't3': ROOT / 'wasm_sdk_probe/test-docs/t3-long.odt'}
STATE = """(() => { const c = document.querySelector('#canvas') || document.querySelector('canvas'), p = document.querySelector('#paper'),
  d = document.querySelector('#desk'); const pr = p?.getBoundingClientRect(), cr = c?.getBoundingClientRect(), dr = d?.getBoundingClientRect();
  let ink = null, nonwhite = null;
  try { const g = c.getContext('2d'); const img = g.getImageData(0, 0, c.width, c.height).data; ink = 0; nonwhite = 0;
    for (let i = 0; i < img.length; i += 4) { const v = img[i] + img[i+1] + img[i+2]; if (img[i+3] > 0 && v < 300) ink++; if (img[i+3] > 0 && v < 750) nonwhite++; } } catch (e) { ink = String(e); }
  return {label: document.querySelector('#zoom-reset')?.textContent, zoomIn: document.querySelector('#zoom-in')?.disabled,
    zoomOut: document.querySelector('#zoom-out')?.disabled, dpr: devicePixelRatio, viewport: [innerWidth, innerHeight],
    canvas: c && {w: c.width, h: c.height, css: [Math.round(cr.width), Math.round(cr.height)], at: [Math.round(cr.x), Math.round(cr.y)],
      window: c.dataset.window, bands: c.dataset.bands, changes: c.dataset.changes, style: c.style.cssText, ink, nonwhite},
    paper: p && {css: [Math.round(pr.width), Math.round(pr.height)], at: [Math.round(pr.x), Math.round(pr.y)], style: p.style.cssText},
    desk: d && {client: [d.clientWidth, d.clientHeight], scroll: [d.scrollLeft, d.scrollTop], scrollSize: [d.scrollWidth, d.scrollHeight],
      at: [Math.round(dr.x), Math.round(dr.y), Math.round(dr.width), Math.round(dr.height)]},
    pill: document.querySelector('#state-pill')?.dataset.state, toast: document.querySelector('#toast')?.textContent?.trim() || null}; })()"""


def shot(session, name):
    png = session.screenshot()
    (OUT / f'{name}.png').write_bytes(png)
    im = Image.open(io.BytesIO(png)).convert('L')
    dark = sum(1 for v in im.getdata() if v < 100)
    return {'png': str(OUT / f'{name}.png'), 'darkPixels': dark, 'size': im.size}


def main():
    instance = s.Instance(h.HOST)
    dav = b8.Dav(instance)
    report = {'browser': KIND, 'docs': {}}
    dav.dav('MKCOL', FOLDER)
    for doc in DOCS:
        dav.dav('PUT', f'{FOLDER}/{doc}-{KIND}.odt', SOURCES[doc].read_bytes(), {'Content-Type': b8.ODT})
    with tempfile.TemporaryDirectory() as scratch:
        session = s.EventChrome('cold') if KIND == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(Path(scratch) / KIND))
        report['version'] = session.version
        W, H = int(__import__('os').environ.get('ZW', '1400')), int(__import__('os').environ.get('ZH', '900'))
        if KIND == 'chrome':
            session.call('Page.enable')
            session.call('Page.addScriptToEvaluateOnNewDocument', {'source': OBSERVER})
            win = session.call('Browser.getWindowForTarget')
            session.call('Browser.setWindowBounds', {'windowId': win['windowId'], 'bounds': {'width': W, 'height': H}})
        else:
            session.command('POST', '/window/rect', {'width': W, 'height': H})
        try:
            s.browser_login(session, instance.base, instance.password)
            for doc in DOCS:
                name = f'{doc}-{KIND}.odt'
                rec = report['docs'][name] = {'steps': []}
                rec['entry'] = b8.open_row(session, instance, name, 'e2-editor.html', folder=FOLDER)
                rec['ready'] = b8.writer_ready(session, name)
                time.sleep(2)
                rec['steps'].append({'step': 'fit', 'state': s.evaluate(session, STATE), 'shot': shot(session, f'{KIND}-{doc}-0-fit')})
                for i in range(1, 8):
                    st = s.evaluate(session, STATE)
                    if st['zoomIn']:
                        break
                    h.press(session, KIND, '#zoom-in', 0.3)
                    time.sleep(2.5)
                    rec['steps'].append({'step': f'in{i}', 'state': s.evaluate(session, STATE), 'shot': shot(session, f'{KIND}-{doc}-{i}-in')})
                h.press(session, KIND, '#zoom-reset', 0.3)
                time.sleep(2.5)
                rec['steps'].append({'step': 'reset', 'state': s.evaluate(session, STATE), 'shot': shot(session, f'{KIND}-{doc}-9-reset')})
                rec['observer'] = s.evaluate(session, "(() => window.__zd ? {paints: window.__zd.paints.map(({at, ...r}) => ({t: Math.round(at), ...r})), toasts: window.__zd.toasts, errors: window.__zd.errors} : null)()")
                h.leave(session, instance)
        except Exception:  # noqa: BLE001
            report['fatal'] = traceback.format_exc()
            try:
                (OUT / f'{KIND}-fatal.png').write_bytes(session.screenshot())
            except Exception:  # noqa: BLE001
                pass
        finally:
            session.close()
    time.sleep(2)
    report['folderDelete'] = dav.dav('DELETE', FOLDER)[0]
    (OUT / f'{KIND}-report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False))
    for name, rec in report['docs'].items():
        for st in rec['steps']:
            c = st['state'].get('canvas') or {}
            print(name, st['step'], st['state'].get('label'), 'canvas', c.get('w'), c.get('h'), c.get('css'), 'ink', c.get('ink'),
                  'nonwhite', c.get('nonwhite'), 'shotDark', st['shot']['darkPixels'], 'dpr', st['state'].get('dpr'), 'bands', c.get('bands'))
    print('fatal', report.get('fatal', '')[-600:], 'folderDelete', report['folderDelete'])


main()
