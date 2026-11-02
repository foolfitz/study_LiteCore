#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 P3, T6 on the new controls: every visible control of the Calc page looks the same under Nextcloud's light and dark
themes, with the colour palette open.

Derived from ../demo-batch-2/host_calc_theme.py (bound by T6's evidence; not edited).  Closed list of differences: this docstring; the
palette is opened before the read, because READ measures only what is shown; the alignment buttons and the swatches get names, where
they would all have collapsed into one `BUTTON` key; a swatch is a sample of a colour with no text, so what is read of it is its own
background (`paint` walks past `rgb(0, 0, 0)`, its transparency test takes that for alpha 0), and it is out of the contrast clause.  Chrome emulates prefers-color-scheme.  Run with host-stack/bin first on PATH.

  python3 -I host_calc_theme.py --out DIR
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('host_layout', HERE.parent / 'demo-batch-2/host_layout.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
s, HOST, create, contrast = layout.s, layout.HOST, layout.create, layout.contrast
FOLDER = 'LiteCore-theme'
READ = """(() => { const root = document.querySelector('#litecore-editor-root'), out = {};
  const shown = e => { const b = e.getBoundingClientRect(), c = getComputedStyle(e); return b.width > 0 && c.display !== 'none' && c.visibility !== 'hidden'; };
  const paint = e => { for (let n = e; n; n = n.parentElement) { const c = getComputedStyle(n).backgroundColor;
      if (c && c !== 'transparent' && !/, 0\\)$/.test(c)) return c; } return 'rgb(255, 255, 255)'; };
  const name = e => e.id || (e.dataset.part ? 'tab-' + e.dataset.part : e.dataset.format ? 'format-' + e.dataset.format
    : e.dataset.align ? 'align-' + e.dataset.align : e.dataset.colorMenu ? 'color-menu-' + e.dataset.colorMenu
    : e.dataset.swatch ? 'swatch-' + e.dataset.swatch : e.closest('[data-format]') ? e.tagName + '-in-' + e.closest('[data-format]').dataset.format : e.tagName);
  const items = [...root.querySelectorAll('button,input,textarea'), ...root.querySelectorAll('#toolbar b,#toolbar strong,#toolbar em,#toolbar u')];
  for (const e of items) { if (e.id === 'litecore-host-close' || !shown(e)) continue; const c = getComputedStyle(e);
    out[name(e)] = e.dataset.swatch ? {background: c.backgroundColor, opacity: c.opacity, disabled: e.disabled === true}
      : {color: c.color, background: paint(e), opacity: c.opacity, disabled: e.disabled === true}; }
  return out; })()"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    instance = s.Instance(HOST)
    instance.dav('MKCOL', FOLDER)
    layout.FOLDER = FOLDER
    reads, report = {}, {}
    session = s.EventChrome('cold')
    with tempfile.TemporaryDirectory(dir=ROOT / 'wasm_sdk_probe/build') as scratch:
        ods = create(Path(scratch) / 'fixture')
        instance.dav('PUT', f'{FOLDER}/layout.ods', ods.read_bytes(), {'Content-Type': 'application/vnd.oasis.opendocument.spreadsheet'})
        s.browser_login(session, instance.base, instance.password)
        for scheme in ('light', 'dark'):
            session.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': scheme}]})
            layout.open_calc(session, instance)
            box = s.evaluate(session, '''(()=>{const r=document.querySelector('[data-color-menu="textColor"]').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];})()''')
            layout.real.click(session, 'chrome', box[0], box[1])
            s.wait_until(session, "(() => document.querySelector('#color-popover').hidden === false)()", 5)
            reads[scheme] = s.evaluate(session, READ)
            (out / f'calc-{scheme}.png').write_bytes(session.screenshot())
            s.navigate(session, instance.base + '/index.php/apps/files/', timeout=60)
            time.sleep(3)
    session.close()
    report['removed'] = instance.dav('DELETE', FOLDER)[0]
    light, dark = reads['light'], reads['dark']
    differs = {k: {'light': light.get(k), 'dark': dark.get(k)} for k in sorted(set(light) | set(dark)) if light.get(k) != dark.get(k)}
    low = {k: contrast(v['color'], v['background']) for k, v in dark.items()
           if not k.startswith('swatch-') and contrast(v['color'], v['background']) < 4.5}
    swatches = [k for k in dark if k.startswith('swatch-')]
    new = [k for k in dark if k.startswith('align-') or k in ('text-color', 'back-color', 'text-color-menu', 'back-color-menu')]
    report.update(newControls={'swatches': len(swatches), 'named': sorted(new), 'clear': 'color-clear' in dark})
    faded = {k: v['opacity'] for k, v in light.items() if k.endswith(('-in-bold', '-in-italic', '-in-underline')) and v['opacity'] != '1'}
    report.update(population=sorted(dark), differs=differs, lowContrast=low, fadedLabels=faded, reads=reads,
                  verdict='T6_HOLDS' if dark and not differs and not low and not faded and len(swatches) == 70 and len(new) == 8 and 'color-clear' in dark else 'T6_RED')
    (out / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'], len(dark), 'controls; differ:', sorted(differs), 'low:', low, 'faded:', faded, 'removed', report['removed'])
    return 0 if report['verdict'] == 'T6_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
