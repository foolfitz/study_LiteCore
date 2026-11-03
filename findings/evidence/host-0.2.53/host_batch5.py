#!/usr/bin/env python3
"""SPEC-P-demo-batch-5 on the installed host: Enter over a selection, and the sentence for an empty copy.

The owner's path, with ../host-0.2.52/host_batch4.py's helpers: open from Files, real pointer and keys, Save, the file read back over WebDAV.
Run on 0.2.52 first: Enter over a selection is refused there and the copy prints its code, and that is the tool's red.  Run with host-stack/bin
first on PATH.
  python3 -I host_batch5.py --out DIR [--browsers chrome,firefox]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('host_batch4', HERE.parent / 'host-0.2.52/host_batch4.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
s, real = h.s, h.real
from check_writer_toggle import BODY, BODY2, shape  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

FOLDER = 'LiteCore-batch5'
TOAST = "document.querySelector('#toast')?.textContent ?? ''"


def writer(session, kind, instance, run):
    h.open_writer(session, kind, instance)
    real.click(session, kind, *s.evaluate(session, h.PAPER))
    h.time.sleep(.8)
    original = shape(instance.dav('GET', f'{FOLDER}/levels-{kind}.odt')[1])
    h.to_paragraph(session, kind, BODY)
    s.evaluate(session, pp.CLEAR_TOAST)
    s.evaluate(session, pp.COPY)
    h.time.sleep(1)
    toast = s.evaluate(session, TOAST)
    h.check(run, 'H5/copy-on-a-caret-says-a-sentence', '沒有可複製的文字' in toast and 'CLIPBOARD_' not in toast, toast)
    h.to_paragraph(session, kind, BODY2)
    h.key(session, kind, 'Home')
    h.key(session, kind, 'ArrowRight', ('shift',), times=5)
    s.evaluate(session, pp.CLEAR_TOAST)
    h.key(session, kind, 'Enter')
    h.key(session, kind, 'q')
    h.check(run, 'H5/no-red-toast', s.evaluate(session, h.RED) is None, s.evaluate(session, h.RED))
    h.check(run, 'H5/ready', s.evaluate(session, h.STATE) == 'ready', s.evaluate(session, h.STATE))
    h.check(run, 'H5/save-settled', h.save(session, kind))
    raw = instance.dav('GET', f'{FOLDER}/levels-{kind}.odt')[1]
    (h.OUT / f'{kind}-host.odt').write_bytes(raw)
    rows = shape(raw)
    texts = [r['text'] for r in rows]
    h.check(run, 'H5/enter-replaced-the-word', len(rows) == len(original) + 1 and texts[BODY2] == '' and texts[BODY2 + 1] == 'q plain paragraph two',
            texts[:4])
    (h.OUT / f'{kind}-after.png').write_bytes(session.screenshot())
    h.leave(session, instance)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browsers', default='chrome,firefox')
    args = parser.parse_args()
    h.OUT = args.out.resolve()
    h.OUT.mkdir(parents=True, exist_ok=False)
    instance = s.Instance(h.HOST)
    try:
        instance.dav('DELETE', FOLDER)  # this tool's own folder, left by a run that died
    except Exception:  # noqa: BLE001 -- absent, the usual case
        pass
    instance.dav('MKCOL', FOLDER)
    h.FOLDER = FOLDER
    h.layout.FOLDER = FOLDER
    report = {'runs': []}
    with tempfile.TemporaryDirectory(dir=ROOT / 'wasm_sdk_probe/build') as scratch:
        for kind in args.browsers.split(','):
            instance.dav('PUT', f'{FOLDER}/levels-{kind}.odt', h.t.LEVELS.read_bytes(), {'Content-Type': h.ODT})
            run = {'browser': kind, 'checks': []}
            report['runs'].append(run)
            session = s.EventChrome('cold') if kind == 'chrome' else s.FirefoxSession('cold', profile_dir=s.firefox_profile(Path(scratch)))
            run['version'] = session.version
            try:
                s.browser_login(session, instance.base, instance.password)
                writer(session, kind, instance, run)
            except Exception:  # noqa: BLE001 -- recorded
                run['fatal'] = traceback.format_exc()
                (h.OUT / f'{kind}-fatal.png').write_bytes(session.screenshot())
            finally:
                session.close()
    report['removed'] = instance.dav('DELETE', FOLDER)[0]
    checks = [c for r in report['runs'] for c in r['checks']]
    report['verdict'] = 'H5_HOLDS' if checks and all(c['pass'] for c in checks) and not any(r.get('fatal') for r in report['runs']) else 'H5_RED'
    (h.OUT / 'report.json').write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(report['verdict'], [(c['id'], c['pass']) for c in checks], [(r.get('fatal') or '')[-300:] for r in report['runs']])
    return 0 if report['verdict'] == 'H5_HOLDS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
